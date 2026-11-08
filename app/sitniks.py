"""Товары из CRM Sitniks: название и цена по артикулу (даже если на сайте товара нет).
Читаются только товары, заказы и клиенты не запрашиваются."""
import json, os, time, urllib.request

URL = 'https://crm.sitniks.com/open-api/products'


def fetch_index(key, page=100):
    H = {'Authorization': 'Bearer ' + key, 'Accept': 'application/json', 'User-Agent': 'autopost-bot'}
    out, skip, total = {}, 0, None
    while total is None or skip < total:
        for i in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(f'{URL}?limit={page}&skip={skip}', headers=H), timeout=60) as r:
                    d = json.load(r); break
            except Exception:
                if i == 2:
                    raise
                time.sleep(3)
        total = d.get('count') or 0
        items = d.get('data') or []
        if not items:
            break
        for p in items:
            for v in p.get('variations') or []:
                sku = (v.get('sku') or '').strip().upper()
                if sku:
                    out[sku] = {'name': v.get('title') or p.get('title'), 'price': v.get('price'),
                                'category': (p.get('category') or {}).get('title')}
        skip += len(items)
    return out
