"""Загрузка каталога с сайта artbynumbers.com.ua (публичные данные)."""
import urllib.request, re, json, time
API='https://api.artbynumbers.com.ua/api/server'
H={'User-Agent':'Mozilla/5.0 (compatible; autopost-bot)','Accept':'application/json'}
def _get(u, raw=False):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40) as r:
                b=r.read(); return b if raw else json.loads(b)
        except Exception as e:
            if i==2: raise
            time.sleep(2)
def product_ids():
    sm=_get('https://artbynumbers.com.ua/sitemap.xml',raw=True).decode()
    return re.findall(r'/product/([0-9a-f\-]{36})',sm)
def fetch_all():
    out=[]
    for pid in product_ids():
        try: out.append(_get(f'{API}/products/{pid}'))
        except Exception as e: print('skip',pid,e)
    return out
if __name__=='__main__':
    import sys
    data=fetch_all()
    json.dump(data,open(sys.argv[1] if len(sys.argv)>1 else 'catalog.json','w'),ensure_ascii=False)
    print('products',len(data))
