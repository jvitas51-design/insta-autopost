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
    # картины, видимые в сетке в 2 соседних рядах, не повторяем ни в какой роли
    seen = set().union(*[recent(history, k, 2) for k in ('reel_sku', 'photo_sku', 'news_first')]) if history else set()
    reels = [s for s in valid if s not in recent(history, 'reel') and sku_of(s) not in recent(history, 'reel_sku') and sku_of(s) not in seen]
    if not reels:
        reels = [s for s in valid if s not in recent(history, 'reel') and sku_of(s) not in recent(history, 'reel_sku')]
    if not reels:
        reels = valid; warn.append('рилсов мало: пришлось повторить раньше, чем через %d постинга' % MIN_GAP)
    import zlib
    reel = max(reels, key=lambda s: (min(last_used(history, 'reel', s), 50), zlib.crc32(s.encode()) % 1000))
    # цвет рилса и фото считаем по самой картине (ровная картинка с сайта), а не по кадру с фоном
    col = lambda item, kind: F.get(sku_of(item)) or F[kind + ':' + item]
    anchor = [col(reel, 'reel')]
    # 2. фото со съёмки: другая картина, ближе всего по цвету к рилсу
    photos = [s for s in lib.photos if sku_of(s) != sku_of(reel) and s not in recent(history, 'photo')
              and sku_of(s) not in recent(history, 'photo_sku') and sku_of(s) not in seen]
    if not photos:
        photos = [s for s in lib.photos if sku_of(s) != sku_of(reel)]
        warn.append('фото со съёмки мало: пришлось повторить раньше, чем через %d постинга' % MIN_GAP)
    if not photos:
        raise RuntimeError('нет фото со съёмки')
    photo = min(photos, key=lambda s: palette.group_distance(anchor, col(s, 'photo')) - 0.003 * min(last_used(history, 'photo', s), 20))
    anchor.append(col(photo, 'photo'))
    busy = {sku_of(reel), sku_of(photo)}
    kinds = interior_kinds(lib)
    dist = lambda items: sum(palette.group_distance(anchor, F[i]) for i in items) / len(items)
    # 3. «Новинки», первый слайд: то 1 картина, то набор из 2 — чередуем; интерьер целиком виден в сетке
    fit = lambda n, sh: any(fits_grid(lib.templates['interiors'][t]) for t in kinds.get((n, sh), []))
    prev_n = len(history[-1].get('news_first') or []) if history and isinstance(history[-1].get('news_first'), list) else 1
    want_first = 2 if prev_n == 1 else 1
    free = lambda items: not (set(items) & (busy | seen | recent(history, 'news_first')))
    singles = [[s] for s, p in pool.items() if fit(1, p['shape']) and free([s])]
    duos = [st for st in lib.sets if len(st['items']) == 2 and fit(2, st['shape']) and free(st['items'])]
    first_set = None
    if want_first == 2 and duos:
        first_set = min(duos, key=lambda st: dist(st['items']))
        first = list(first_set['items'])
    else:
        first = min(singles, key=lambda it: dist(it) - (0.1 if pool[it[0]]['new'] else 0))
    busy |= set(first)
    # 4. наборы: размеры чередуются 2-3-2-3 (после первого слайда из 1 картины начинаем с 2, после пары — с 3)
    def set_score(st, used):
        return dist(st['items']) + (0.3 if last_used(history, 'news_sets', st['sku']) <= 2 else 0) \
            - (0.1 if any(pool[i]['new'] for i in st['items']) else 0) + 0.5 * len(used & set(st['items']))
    chosen, used_items = [], set(busy)
    size = 3 if len(first) == 2 else 2
    left = [st for st in lib.sets if (len(st['items']), st['shape']) in kinds and st is not first_set]
    while left and len(chosen) < NEWS_SLIDES - 1:
        pool_n = [st for st in left if len(st['items']) == size and not set(st['items']) <= used_items] or \
                 [st for st in left if not set(st['items']) <= used_items]
        if not pool_n:
            break
        st = min(pool_n, key=lambda s: set_score(s, used_items))
        left.remove(st); chosen.append(st); used_items |= set(st['items'])
        size = 5 - size
    # 5. «Оновлена підбірка»: пары одной формы, ближе всего к цвету фото
    ph = [col(photo, 'photo')]
    cand = sorted([s for s in pool if s not in busy], key=lambda s: palette.group_distance(ph, F[s]) - 0.01 * min(last_used(history, 'selection', s), 10))
    def pairs(shape):
        g = [s for s in cand if pool[s]['shape'] == shape]
        return [[g[i], g[i + 1]] for i in range(0, len(g) - 1, 2)]
    rp, qp = pairs('round'), pairs('rect')
    cards = []
    while len(cards) < SELECTION_CARDS and (rp or qp):
        want = rp if (len(cards) % 2 == 0 and rp) or not qp else qp
        cards.append(want.pop(0))
    return {'reel': reel, 'photo': photo, 'reel_sku': sku_of(reel), 'photo_sku': sku_of(photo), 'news_first': first, 'news_sets': ([first_set['sku']] if first_set else []) + [s['sku'] for s in chosen],
            'selection': [s for c in cards for s in c], 'cards': cards,
            '_sets': chosen, '_first_set': first_set, '_warn': warn}
