"""Точка входа.
  python app/main.py preview [N]   — план и картинка будущей сетки на N постингов вперёд
  python app/main.py run           — если пора, собрать и опубликовать очередной ряд
"""
import copy, datetime, json, os, subprocess, sys, time, urllib.request
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import catalog as cat
import captions
from library import Library, P
from planner import plan as make_plan
from render import render

KYIV = ZoneInfo('Europe/Kyiv')
CFG = json.load(open(P('config.json')))
HIST = P('state', 'history.json')
TYPES = {'selection': 'Оновлена підбірка', 'news': 'Новинки', 'reel': 'Рилс'}


def load_history():
    return json.load(open(HIST)) if os.path.exists(HIST) else []


def save_history(h):
    os.makedirs(os.path.dirname(HIST), exist_ok=True)
    json.dump(h, open(HIST, 'w'), ensure_ascii=False, indent=1)


def load_lib():
    os.makedirs(P('cache'), exist_ok=True)
    c, s = P('cache', 'catalog.json'), P('cache', 'sets.json')
    if os.environ.get('OFFLINE') != '1':
        json.dump(cat.fetch(), open(c, 'w'), ensure_ascii=False)
        json.dump(cat.fetch('nabory-kartyn'), open(s, 'w'), ensure_ascii=False)
    return Library(json.load(open(c)), json.load(open(s)), offline=os.environ.get('OFFLINE') == '1')


def kind_of(media):
    cap = (media or {}).get('caption') or ''
    if (media or {}).get('media_product_type') == 'REELS' or cap.startswith('Наш бестселер'):
        return 'reel'
    if cap.startswith('Оновлена'):
        return 'selection'
    return None


def order_after(newest_kind):
    """Порядок публикации в ряду: начинаем с того же типа, что сейчас самый свежий в ленте.
    Так «Новинки» всегда в средней колонке, а рилс и подборка чередуются шахматкой."""
    start = newest_kind if newest_kind in ('reel', 'selection') else 'selection'
    other = 'reel' if start == 'selection' else 'selection'
    return [start, 'news', other]


def git(*a):
    subprocess.run(['git', *a], check=True, cwd=P())


def commit(msg, paths):
    git('config', 'user.name', 'autopost-bot'); git('config', 'user.email', 'autopost-bot@users.noreply.github.com')
    git('add', *paths)
    if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=P()).returncode:
        git('commit', '-m', msg)
        for _ in range(3):
            if subprocess.run(['git', 'push'], cwd=P()).returncode == 0:
                return
            git('pull', '--rebase')
        raise RuntimeError('не удалось отправить изменения в GitHub')


def raw_url(path):
    repo = os.environ.get('GITHUB_REPOSITORY', 'jvitas51-design/insta-autopost')
    rel = os.path.relpath(path, P()).replace(os.sep, '/')
    return f'https://raw.githubusercontent.com/{repo}/main/' + urllib.request.quote(rel)


def wait_public(url, timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=30) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(10)
    raise RuntimeError('файл не появился по публичной ссылке: ' + url)


def describe(lib, p, n):
    nm = lambda s: captions.title(lib.products[s]['name']['ua']) if s in lib.products else captions.title(lib.reel_info.get(s, {}).get('name', s))
    sets = ', '.join(f'«{s["name"]}»' for s in p['_sets'])
    w = (' ВНИМАНИЕ: ' + '; '.join(p['_warn'])) if p.get('_warn') else ''
    return (f'Постинг {n}: рилс «{nm(p["reel"])}» ({p["reel"]}); фото со съёмки - {p["photo"]}; '
            f'первый слайд «Новинок» - ' + ' + '.join(f'«{nm(s)}»' for s in p['news_first']) + f'; наборы: {sets}; '
            f'в подборке {len(p["selection"])} картин' + w)


def preview(n=5):
    lib = load_lib()
    hist = load_history()
    sim = copy.deepcopy(hist)
    newest = None
    if os.environ.get('IG_TOKEN'):
        from publish import IG
        newest = kind_of(IG(os.environ['IG_TOKEN']).latest())
    rows, lines = [], []
    for i in range(n):
        p = make_plan(lib, sim)
        files = render(lib, p, P('preview', f'p{i+1}'), seed=len(sim))
        order = order_after(newest)
        rows.append([files['selection'][0] if k == 'selection' else files['news'][0] if k == 'news' else files['cover']
                     for k in reversed(order)])          # в ленте новейший пост слева
        lines.append(describe(lib, p, i + 1) + '; порядок публикации: ' + ' → '.join(TYPES[k] for k in order))
        newest = order[-1]
        sim.append({k: v for k, v in p.items() if not k.startswith('_') and k != 'cards'})
    grid(rows, P('preview', 'preview.jpg'))
    open(P('preview', 'plan.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


def grid(rows, out, w=360, h=480, gap=4):
    def cell(path):
        im = Image.open(path).convert('RGB'); r = max(w / im.width, h / im.height)
        im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
        x, y = (im.width - w) // 2, (im.height - h) // 2
        return im.crop((x, y, x + w, y + h))
    C = Image.new('RGB', (3 * w + 2 * gap, len(rows) * (h + gap)), 'white')
    for r, row in enumerate(reversed(rows)):          # сверху — самый поздний постинг, как в профиле
        for c, f in enumerate(row):
            C.paste(cell(f), (c * (w + gap), r * (h + gap)))
    C.save(out, quality=88)


def run():
    now = datetime.datetime.now(KYIV)
    hist = load_history()
    from publish import IG
    ig = IG(os.environ['IG_TOKEN'])
    latest = ig.latest()
    last = datetime.date.fromisoformat(hist[-1]['date']) if hist else (
        datetime.datetime.fromisoformat(latest['timestamp'].replace('+0000', '+00:00')).astimezone(KYIV).date() if latest else None)
    force = os.environ.get('FORCE') == '1'
    day_due = last is None or (now.date() - last).days >= CFG['every_days']
    target = now.replace(hour=CFG['post_hour'], minute=0, second=0, microsecond=0)
    if not force and day_due and now < target:
        wait = (target - now).total_seconds()
        # GitHub запускает расписание с опозданием на часы, поэтому стартуем заранее и ждём нужного времени
        if wait > CFG.get('max_wait_hours', 5.5) * 3600:
            print(f'Киев {now:%H:%M}: до публикации больше {CFG.get("max_wait_hours", 5.5)} ч, жду следующего запуска'); return
        print(f'Киев {now:%H:%M}: жду до {target:%H:%M}'); time.sleep(wait); now = datetime.datetime.now(KYIV)
    due = force or (day_due and now >= target)
    print(f'Киев {now:%Y-%m-%d %H:%M}, последний постинг {last}, пора: {due}, публикация включена: {CFG["posting_enabled"]}')
    if not due:
        return
    if not CFG['posting_enabled'] and not force:
        print('Публикация выключена в config.json - только предпросмотр'); return
    lib = load_lib()
    p = make_plan(lib, hist)
    out = P('posts', now.strftime('%Y-%m-%d'))
    files = render(lib, p, out, seed=len(hist))
    commit(f'post {now:%Y-%m-%d}: media', [out])
    urls = {k: [raw_url(f) for f in files[k]] for k in ('selection', 'news')}
    urls['reel'], urls['cover'] = raw_url(files['reel']), raw_url(files['cover'])
    for u in urls['selection'] + urls['news'] + [urls['reel'], urls['cover']]:
        wait_public(u)
    texts = {'selection': captions.selection(),
             'news': captions.news(([(1, p['_first_set']['price'])] if p.get('_first_set') else []) +
                                   [(i, s['price']) for i, s in enumerate(p['_sets'], 2)]),
             'reel': captions.reel(lib.reel_info[p['reel']])}
    order = order_after(kind_of(latest))
    ids = {}
    for i, k in enumerate(order):
        if i:
            time.sleep(CFG['gap_minutes'] * 60)
        ids[k] = ig.reel(urls['reel'], urls['cover'], texts['reel']) if k == 'reel' else ig.carousel(urls[k], texts[k])
        print('опубликовано', TYPES[k], ids[k])
    rec = {k: v for k, v in p.items() if not k.startswith('_') and k != 'cards'}
    rec.update(date=now.strftime('%Y-%m-%d'), order=order, media=ids)
    hist.append(rec); save_history(hist)
    commit(f'post {now:%Y-%m-%d}: history', [HIST])


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    if cmd == 'preview':
        preview(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
    elif cmd == 'run':
        run()
