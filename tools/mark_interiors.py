"""Автоматическая разметка интерьеров: где висят картины, какой они формы,
и не закрывает ли их что-то спереди. Результат дописывается в templates.json.
Запуск: python tools/mark_interiors.py <папка с интерьерами> [<папка для проверочных картинок>]"""
import json, os, sys, glob
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
from compose import refine_rect, refine_circle

W = 1024


def candidates(img):
    sm = img.convert('RGB').resize((W, W * img.height // img.width), Image.LANCZOS)
    a = np.asarray(sm).astype(float)
    g = a.mean(2)
    tex = np.sqrt(np.maximum(nd.uniform_filter(g ** 2, 9) - nd.uniform_filter(g, 9) ** 2, 0))
    sat = a.max(2) - a.min(2)
    m = (tex > 9) | (sat > 60) | (g < 70)
    m = nd.binary_closing(m, np.ones((9, 9)))
    m = nd.binary_fill_holes(m)
    m = nd.binary_opening(m, np.ones((15, 15)))
    lab, n = nd.label(m)
    H = m.shape[0]
    out = []
    for k, sl in enumerate(nd.find_objects(lab), 1):
        comp = lab[sl] == k
        h, w = comp.shape
        area = comp.sum()
        if area < 0.012 * W * H or sl[0].start > 0.6 * H:
            continue
        fill = area / (h * w)
        ar = w / h
        box = (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop)
        if 0.72 <= fill <= 0.84 and 0.88 <= ar <= 1.12:
            out.append(['round', box])
        elif fill >= 0.9 and 0.55 <= ar <= 0.95:
            out.append(['rect', box])
        else:
            out.append(['bad', box])
    return sm, out


def edge_ok(img, shape, box, frac=0.8):
    g = np.asarray(img.convert('L')).astype(float)
    gm = np.hypot(nd.sobel(g, 0), nd.sobel(g, 1))
    thr = np.percentile(gm, 75)
    pts = []
    if shape == 'round':
        cx, cy, r = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, (box[2] - box[0]) / 2
        for t in np.linspace(0, 2 * np.pi, 240, endpoint=False):
            pts.append((cx + r * np.cos(t), cy + r * np.sin(t)))
    else:
        x0, y0, x1, y1 = box
        for t in np.linspace(0.05, 0.95, 60):
            pts += [(x0 + t * (x1 - x0), y0), (x0 + t * (x1 - x0), y1), (x0, y0 + t * (y1 - y0)), (x1, y0 + t * (y1 - y0))]
    ok = 0
    for x, y in pts:
        x, y = int(round(x)), int(round(y))
        win = gm[max(0, y - 4):y + 5, max(0, x - 4):x + 5]
        ok += win.size and win.max() > thr
    return ok / len(pts) >= frac, round(ok / len(pts), 2)


def mark(path):
    img = Image.open(path).convert('RGB')
    sm, cands = candidates(img)
    k = img.width / W
    good = [c for c in cands if c[0] != 'bad']
    res = {'file': None, 'slots': [], 'size': list(img.size)}
    if not good:
        res['disabled'] = 'не удалось найти картины'
    else:
        y0 = min(c[1][1] for c in good); y1 = max(c[1][3] for c in good)
        x0 = min(c[1][0] for c in good); x1 = max(c[1][2] for c in good)
        for c in cands:
            if c[0] != 'bad':
                continue
            b = c[1]
            ov = max(0, min(b[3], y1) - max(b[1], y0)) / (y1 - y0)
            covers_all = b[0] <= x0 and b[2] >= x1 and b[1] <= y0 and b[3] >= y1
            if ov > 0.3 and not covers_all:
                res['disabled'] = 'рядом с картинами есть ещё что-то похожее на картину'
            if covers_all and ov > 0.3 and (b[2] - b[0]) * (b[3] - b[1]) < 4 * (x1 - x0) * (y1 - y0):
                res['disabled'] = 'картина слилась с фоном'
    shapes = {c[0] for c in good}
    if len(shapes) > 1:
        res['disabled'] = 'картины разной формы'
    if len(good) > 3:
        res['disabled'] = 'больше 3 картин'
    sizes = [(c[1][2] - c[1][0]) for c in good]
    if sizes and max(sizes) > 1.2 * min(sizes):
        res['disabled'] = 'картины разного размера'
    for sh, b in sorted(good, key=lambda c: c[1][0]):
        b = [v * k for v in b]
        r = refine_circle(img, b, search=int(10 * k)) if sh == 'round' else refine_rect(img, b, search=int(10 * k))
        r = [int(round(v)) for v in r]
        ok, score = edge_ok(img, sh, r)
        if not ok:
            res['disabled'] = f'что-то закрывает картину (края видны на {int(score*100)}%)'
        res['slots'].append([sh, r])
    return img, res


if __name__ == '__main__':
    src, dbg = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    root = os.path.join(os.path.dirname(__file__), '..')
    tj = os.path.join(root, 'library', 'templates', 'templates.json')
    T = json.load(open(tj))
    os.makedirs(os.path.join(root, 'library', 'templates', 'interiors'), exist_ok=True)
    if dbg:
        os.makedirs(dbg, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src, '*'))):
        name = 'i_' + os.path.splitext(os.path.basename(f))[0].replace(' ', '_').replace('(', '').replace(')', '')
        img, res = mark(f)
        img.save(os.path.join(root, 'library', 'templates', 'interiors', name + '.jpg'), quality=92)
        res['file'] = f'interiors/{name}.jpg'
        T['interiors'][name] = res
        print(name, len(res['slots']), res['slots'][0][0] if res['slots'] else '-', res.get('disabled', 'OK'))
        if dbg:
            d = ImageDraw.Draw(img)
            col = (255, 0, 0) if res.get('disabled') else (0, 200, 0)
            for sh, b in res['slots']:
                (d.ellipse if sh == 'round' else d.rectangle)(b, outline=col, width=max(4, img.width // 200))
            img.thumbnail((400, 400)); img.save(os.path.join(dbg, name + '.jpg'))
    json.dump(T, open(tj, 'w'), ensure_ascii=False, indent=1)
