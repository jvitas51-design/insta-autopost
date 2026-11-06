"""Каталог сайта artbynumbers.com.ua через его публичный API."""
import urllib.request, urllib.parse, json, time
API='https://api.artbynumbers.com.ua/api/server/products'
H={'User-Agent':'Mozilla/5.0 (compatible; autopost-bot)','Accept':'application/json'}
def _get(params):
    u=API+'?'+urllib.parse.urlencode(params)
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=60) as r:
                return int(r.headers.get('x-total') or 0), json.loads(r.read())
        except Exception:
            if i==2: raise
            time.sleep(3)
def fetch(category=None, limit=100):
    out=[]; page=1
    while True:
        p={'page':page,'limit':limit}
        if category: p['category']=category
        total,items=_get(p); out+=items
        if not items or len(out)>=total: break
        page+=1
    return out
if __name__=='__main__':
    import sys, os
    d=sys.argv[1] if len(sys.argv)>1 else 'data'; os.makedirs(d,exist_ok=True)
    allp=fetch(); json.dump(allp,open(f'{d}/catalog.json','w'),ensure_ascii=False)
    sets=fetch('nabory-kartyn'); json.dump(sets,open(f'{d}/sets.json','w'),ensure_ascii=False)
    print('catalog',len(allp),'sets',len(sets))
