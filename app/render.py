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


def center_crop(img, slots, width_share=None, cy_share=0.42):
    """Квадрат вокруг картин: по центру по горизонтали, чуть выше середины по вертикали,
    как на первых слайдах «Новинок» в ленте. Нужен, чтобы в сетке картина стояла ровно по центру."""
    x0 = min(s[1][0] for s in slots); x1 = max(s[1][2] for s in slots)
    y0 = min(s[1][1] for s in slots); y1 = max(s[1][3] for s in slots)
    gw, gh = x1 - x0, y1 - y0
    share = width_share or (0.5 if len(slots) == 1 else 0.68)
    S = int(max(gw / share, gh / 0.62))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # квадрат должен помещаться в фото так, чтобы картины остались строго по центру по горизонтали
    S = int(min(S, img.width, img.height, 2 * cx, 2 * (img.width - cx), cy / cy_share, (img.height - cy) / (1 - cy_share)))
    S = max(S, int(max(gw, gh) / 0.8))
    left = int(round(cx - S / 2)); top = int(round(cy - cy_share * S))
    left = max(0, min(left, img.width - S)); top = max(0, min(top, img.height - S))
    return img.crop((left, top, left + S, top + S))


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
    out = center_crop(render_template(img, slots, [lib.art(s) for s in items]), slots).resize((1440, 1440), Image.LANCZOS)
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
