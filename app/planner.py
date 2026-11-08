"""Выбор содержимого для одного постинга (ряд из 3 постов) по правилам магазина."""
import palette
from library import sku_of

MIN_GAP = 4            # рилс, фото со съёмки и первая картина «Новинок» не повторяются 4 постинга подряд
NEWS_SLIDES = 10       # 1 одиночная картина + до 9 наборов
SELECTION_CARDS = 9    # фото со съёмки + до 9 слайдов-карточек по 2 картины
GRID_CROP = 0.125      # сетка на телефоне показывает центральные 3:4 квадрата


def recent(history, key, n=MIN_GAP):
    out = set()
    for h in history[-n:]:
        v = h.get(key)
        out.update(v if isinstance(v, list) else [v])
    return out


def last_used(history, key, value):
    for i in range(len(history) - 1, -1, -1):
        v = history[i].get(key)
        if value == v or (isinstance(v, list) and value in v):
            return len(history) - i
    return 10 ** 6


def interior_kinds(lib):
    kinds = {}
    for name, t in lib.templates['interiors'].items():
        if t.get('disabled'):
            continue
        shapes = {s[0] for s in t['slots']}
        if len(shapes) != 1:
            continue
        kinds.setdefault((len(t['slots']), shapes.pop()), []).append(name)
    return kinds


def fits_grid(t, size=None):
    size = size or t.get('size', [2048])[0]
    l, r = size * (GRID_CROP + 0.02), size * (1 - GRID_CROP - 0.02)
    return all(s[1][0] >= l and s[1][2] <= r for s in t['slots'])


def plan(lib, history):
    F = lib.feat
    pool = lib.paintings
    # 1. рилс: дольше всех не выходивший, товар есть в каталоге
    warn = []
    valid = [s for s in lib.reel_info if 'reel:' + s in F]
    if not valid:
        raise RuntimeError('нет ни одного рилса с названием и ценой')
    reels = [s for s in valid if s not in recent(history, 'reel') and sku_of(s) not in recent(history, 'reel_sku')]
    if not reels:
        reels = valid; warn.append('рилсов мало: пришлось повторить раньше, чем через %d постинга' % MIN_GAP)
    import zlib
    reel = max(reels, key=lambda s: (min(last_used(history, 'reel', s), 50), zlib.crc32(s.encode()) % 1000))
    anchor = [F['reel:' + reel]]
    # 2. фото со съёмки: другая картина, ближе по цвету
    photos = [s for s in lib.photos if sku_of(s) != sku_of(reel) and s not in recent(history, 'photo')
              and sku_of(s) not in recent(history, 'photo_sku')]
    if not photos:
        photos = [s for s in lib.photos if sku_of(s) != sku_of(reel)]
        warn.append('фото со съёмки мало: пришлось повторить раньше, чем через %d постинга' % MIN_GAP)
    if not photos:
        raise RuntimeError('нет фото со съёмки')
    photo = min(photos, key=lambda s: palette.group_distance(anchor, F['photo:' + s]) - 0.02 * min(last_used(history, 'photo', s), 20))
    anchor.append(F['photo:' + photo])
    busy = {sku_of(reel), sku_of(photo)}
    kinds = interior_kinds(lib)
    # 3. «Новинки»: первый слайд — 1 картина в интерьере, который целиком виден в сетке
    singles = {sh: [n for n in kinds.get((1, sh), []) if fits_grid(lib.templates['interiors'][n])] for sh in ('round', 'rect')}
    prev_shape = pool.get(history[-1].get('news_first'), {}).get('shape') if history else None
    first_c = [s for s, p in pool.items() if s not in busy and s not in recent(history, 'news_first') and singles[p['shape']]]
    alt = [s for s in first_c if pool[s]['shape'] != prev_shape]
    first_c = alt or first_c
    first = min(first_c, key=lambda s: palette.group_distance(anchor, F[s]) - (0.15 if pool[s]['new'] else 0))
    busy.add(first)
    # 4. наборы для «Новинок»
    sets = [st for st in lib.sets if (len(st['items']), st['shape']) in kinds]
    def set_score(st):
        d = sum(palette.group_distance(anchor, F[i]) for i in st['items']) / len(st['items'])
        return d + (0.3 if last_used(history, 'news_sets', st['sku']) <= 2 else 0) - (0.1 if any(pool[i]['new'] for i in st['items']) else 0)
    chosen, used_items = [], set(busy)
    left = sorted(sets, key=set_score)
    while left and len(chosen) < NEWS_SLIDES - 1:
        st = min(left, key=lambda s: set_score(s) + 0.35 * len(used_items & set(s['items'])))
        left.remove(st)
        if set(st['items']) <= used_items:
            continue
        chosen.append(st); used_items |= set(st['items'])
    # 5. «Оновлена підбірка»: пары одной формы, ближе всего к цвету фото
    ph = [F['photo:' + photo]]
    cand = sorted([s for s in pool if s not in busy], key=lambda s: palette.group_distance(ph, F[s]) - 0.01 * min(last_used(history, 'selection', s), 10))
    def pairs(shape):
        out = []
        for met in (True, False):
            g = [s for s in cand if pool[s]['shape'] == shape and pool[s]['metallic'] == met]
            out += [[g[i], g[i + 1]] for i in range(0, len(g) - 1, 2)]
        return sorted(out, key=lambda pr: cand.index(pr[0]))
    rp, qp = pairs('round'), pairs('rect')
    cards = []
    while len(cards) < SELECTION_CARDS and (rp or qp):
        want = rp if (len(cards) % 2 == 0 and rp) or not qp else qp
        cards.append(want.pop(0))
    return {'reel': reel, 'photo': photo, 'reel_sku': sku_of(reel), 'photo_sku': sku_of(photo), 'news_first': first, 'news_sets': [s['sku'] for s in chosen],
            'selection': [s for c in cards for s in c], 'cards': cards,
            '_sets': chosen, '_warn': warn}
