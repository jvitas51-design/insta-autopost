"""Всё, из чего собираются посты: каталог сайта, картины, рилсы, фото со съёмки, шаблоны."""
import json, os, re, urllib.request
from PIL import Image
import palette

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
H = {'User-Agent': 'Mozilla/5.0 (compatible; autopost-bot)'}

ROUND_RE = re.compile(r'^ABN-\d{3}[KB]$')
RECT_RE = re.compile(r'^ABN-\d{4}$')


def norm_sku(s):
    s = s.strip().upper().replace('К', 'K').replace('В', 'B')   # кириллица в именах файлов
    if not s.startswith('ABN-'):
        s = 'ABN-' + s
    return s


def sku_of(item_id):
    return item_id.split('_v')[0]


def shape_of(p):
    a = p.get('articul') or ''
    if ROUND_RE.match(a) and (p.get('size') or '').startswith('40x40'):
        return 'round'
    if RECT_RE.match(a) and (p.get('size') or '').startswith('40x50'):
        return 'rect'
    return None


class Library:
    def __init__(self, catalog, sets, offline=False):
        self.offline = offline
        self._raw_sets = sets
        self.products = {p['articul']: p for p in catalog if p.get('articul')}
        self.paintings = {}
        for a, p in self.products.items():
            sh = shape_of(p)
            imgs = ((p.get('gallery') or {}).get('images') or [])
            if sh and imgs:
                self.paintings[a] = {'sku': a, 'shape': sh, 'product': p, 'image': imgs[0],
                                     'new': 'new' in (p.get('label') or {}),
                                     'metallic': 'metallic' in (p.get('label') or {})}
        self.reels = {norm_sku(os.path.splitext(f)[0]): P('library', 'reels', f)
                      for f in sorted(os.listdir(P('library', 'reels'))) if f.lower().endswith('.mp4')}
        self.photos = {norm_sku(os.path.splitext(f)[0]): P('library', 'photos', f)
                       for f in sorted(os.listdir(P('library', 'photos'))) if f.lower().endswith('.jpg')}
        self.reel_info = {}
        self.templates = json.load(open(P('library', 'templates', 'templates.json')))
        self.feat = self._load_features()
        self._resolve_reels()
        self.sets = []
        for s in self._raw_sets:
            ks = [k['product']['articul'] for k in (s.get('kitProducts') or []) if k.get('product')]
            shapes = {self.paintings[k]['shape'] for k in ks if k in self.paintings}
            if len(ks) in (2, 3) and all(k in self.paintings for k in ks) and len(shapes) == 1:
                self.sets.append({'sku': s['articul'], 'name': s['name']['ua'], 'price': s.get('discountPrice') or s['price'],
                                  'items': ks, 'shape': shapes.pop()})

    # --- картинки картин ---
    def art_path(self, sku):
        return P('cache', 'art', sku + '.jpg')

    def art(self, sku):
        path = self.art_path(sku)
        if not os.path.exists(path):
            if self.offline:
                raise FileNotFoundError(path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with urllib.request.urlopen(urllib.request.Request(self.paintings[sku]['image'], headers=H), timeout=60) as r:
                data = r.read()
            open(path, 'wb').write(data)
        return Image.open(path).convert('RGB')

    def _load_features(self):
        path = P('cache', 'features.json')
        feat = json.load(open(path)) if os.path.exists(path) else {}
        changed = False
        for sku in list(self.paintings):
            if sku not in feat:
                try:
                    feat[sku] = palette.features(self.art(sku)); changed = True
                except Exception as e:
                    print('нет картинки', sku, e); self.paintings.pop(sku)
        for sku, f in self.photos.items():
            key = 'photo:' + sku
            if key not in feat:
                feat[key] = palette.features(Image.open(f)); changed = True
        if changed:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            json.dump(feat, open(path, 'w'))
        return feat

    # --- данные для подписи рилса: название, размер, цена ---
    def _resolve_reels(self):
        import collections, urllib.parse
        self.sitniks = {}
        sp = P('cache', 'sitniks.json')
        key = os.environ.get('SITNIKS_API_KEY', '').strip()
        if key and not self.offline:
            try:
                import sitniks
                self.sitniks = sitniks.fetch_index(key)
                json.dump(self.sitniks, open(sp, 'w'), ensure_ascii=False)
            except Exception as e:
                print('Sitniks недоступен:', e)
        if not self.sitniks and os.path.exists(sp):
            self.sitniks = json.load(open(sp))
        manual_p = P('library', 'reels', 'info.json')
        manual = json.load(open(manual_p)) if os.path.exists(manual_p) else {}
        typical = {}
        for sh in ('round', 'rect'):
            prices = [p['product'].get('discountPrice') or p['product']['price'] for p in self.paintings.values() if p['shape'] == sh]
            typical[sh] = collections.Counter(prices).most_common(1)[0][0] if prices else None
        for rid in self.reels:
            sku = sku_of(rid)
            sh = 'round' if ROUND_RE.match(sku) else 'rect' if RECT_RE.match(sku) else None
            size = 'd40' if sh == 'round' else '40*50'
            if sku in manual:
                self.reel_info[rid] = dict({'size': size, 'price': typical.get(sh)}, **manual[sku]); continue
            sk = self.sitniks.get(sku)
            if sku not in self.products and sk and sk.get('name') and sk.get('price'):
                self.reel_info[rid] = {'name': sk['name'], 'size': size, 'price': sk['price'], 'in_stock': False, 'source': 'sitniks'}
                continue
            if sku in self.products:
                p = self.products[sku]
                self.reel_info[rid] = {'name': p['name']['ua'], 'size': size, 'price': p.get('discountPrice') or p['price'], 'in_stock': True}
                continue
            # нет в наличии: название берём у премиум-набора той же картины (артикул + P)
            name = None
            if not self.offline:
                try:
                    u = 'https://api.artbynumbers.com.ua/api/server/products?' + urllib.parse.urlencode({'search': sku})
                    with urllib.request.urlopen(urllib.request.Request(u, headers=dict(H, Accept='application/json')), timeout=40) as r:
                        for x in json.load(r):
                            if x.get('articul') in (sku, sku + 'P'):
                                name = re.sub(r'^Premium\s+набір\s+', '', x['name']['ua'], flags=re.I); break
                except Exception as e:
                    print('поиск', sku, e)
            if name and typical.get(sh):
                self.reel_info[rid] = {'name': name, 'size': size, 'price': typical[sh], 'in_stock': False}
            else:
                print('рилс', rid, 'пропущен: не нашёл название или цену; можно задать вручную в library/reels/info.json')
        # цвет рилса: по последнему кадру видео
        from cover import cover_frame
        changed = False
        for sku in self.reel_info:   # здесь sku = id файла рилса
            key = 'reel:' + sku
            if key not in self.feat:
                tmp = P('cache', 'reel_' + sku + '.jpg')
                try:
                    cover_frame(self.reels[sku], tmp)
                    self.feat[key] = palette.features(Image.open(tmp)); changed = True
                except Exception as e:
                    print('кадр', sku, e)
        if changed:
            json.dump(self.feat, open(P('cache', 'features.json'), 'w'))
