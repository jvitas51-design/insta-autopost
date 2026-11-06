"""Сборка картинок для постинга по плану."""
import os
from PIL import Image
from compose import render_template
from cover import cover_frame
from planner import interior_kinds, fits_grid
from library import P


def _tpl(lib, group, name):
    t = lib.templates[group][name]
    return Image.open(P('library', 'templates', t['file'])).convert('RGB'), t['slots']


def render(lib, plan, outdir, seed=0):
    os.makedirs(outdir, exist_ok=True)
    files = {'selection': [], 'news': [], 'reel': None, 'cover': None}
    # подборка: фото со съёмки + карточки
    ph = Image.open(lib.photos[plan['photo']]).convert('RGB').resize((1080, 1080), Image.LANCZOS)
    f = os.path.join(outdir, 'sel_00.jpg'); ph.save(f, quality=92); files['selection'].append(f)
    cards = lib.templates['cards']
    by_shape = {'round': [n for n, t in cards.items() if t['slots'][0][0] == 'round'],
                'rect': [n for n, t in cards.items() if t['slots'][0][0] == 'rect']}
    used = {'round': seed, 'rect': seed}
    for i, pair in enumerate(plan['cards'], 1):
        sh = lib.paintings[pair[0]]['shape']
        name = by_shape[sh][used[sh] % len(by_shape[sh])]; used[sh] += 1
        img, slots = _tpl(lib, 'cards', name)
        out = render_template(img, slots, [lib.art(s) for s in pair])
        f = os.path.join(outdir, f'sel_{i:02d}.jpg'); out.save(f, quality=92); files['selection'].append(f)
    # новинки
    kinds = interior_kinds(lib)
    fs = lib.paintings[plan['news_first']]
    singles = [n for n in kinds[(1, fs['shape'])] if fits_grid(lib.templates['interiors'][n])]
    name = singles[seed % len(singles)]
    img, slots = _tpl(lib, 'interiors', name)
    out = render_template(img, slots, [lib.art(plan['news_first'])]).resize((1440, 1440), Image.LANCZOS)
    f = os.path.join(outdir, 'news_01.jpg'); out.save(f, quality=92); files['news'].append(f)
    cnt = {}
    for i, st in enumerate(plan['_sets'], 2):
        k = (len(st['items']), st['shape']); names = kinds[k]
        name = names[(seed + cnt.get(k, 0)) % len(names)]; cnt[k] = cnt.get(k, 0) + 1
        img, slots = _tpl(lib, 'interiors', name)
        out = render_template(img, slots, [lib.art(s) for s in st['items']]).resize((1440, 1440), Image.LANCZOS)
        f = os.path.join(outdir, f'news_{i:02d}.jpg'); out.save(f, quality=92); files['news'].append(f)
    # рилс
    files['reel'] = lib.reels[plan['reel']]
    files['cover'] = os.path.join(outdir, 'reel_cover.jpg')
    cover_frame(files['reel'], files['cover'])
    return files
