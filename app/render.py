"""Сборка картинок для постинга по плану."""
import os
from PIL import Image
from compose import render_template
from cover import cover_frame
from planner import interior_kinds, fits_grid
from library import P
import headers


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
    used = {}
    for i, pair in enumerate(plan['cards'], 1):
        sh = lib.paintings[pair[0]]['shape']
        names = [n for n, t in cards.items() if t['slots'][0][0] == sh]
        name = names[(seed + used.get(sh, 0)) % len(names)]; used[sh] = used.get(sh, 0) + 1
        img, slots = _tpl(lib, 'cards', name)
        out = render_template(img, slots, [lib.art(s) for s in pair])
        headers.apply(out, sh, [(lib.paintings[s]['metallic'], lib.paintings[s]['author']) for s in pair])
        f = os.path.join(outdir, f'sel_{i:02d}.jpg'); out.save(f, quality=92); files['selection'].append(f)
    # новинки
    kinds = interior_kinds(lib)
    fset = plan.get('_first_set')
    items = fset['items'] if fset else [plan['news_first'][0]]
    sh = lib.paintings[items[0]]['shape']
    fits = [n for n in kinds[(len(items), sh)] if fits_grid(lib.templates['interiors'][n])]
    name = fits[seed % len(fits)]
    img, slots = _tpl(lib, 'interiors', name)
    out = render_template(img, slots, [lib.art(s) for s in items]).resize((1440, 1440), Image.LANCZOS)
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
