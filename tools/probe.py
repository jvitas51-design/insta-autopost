import os, json, urllib.request, urllib.parse
names=['SITNIKS_API_KEY','SITNIKS_KEY','SITNIKS_TOKEN','SITNIKS_API_TOKEN','SITNIKS','SITNIKS_API']
key=None
for n in names:
    v=(os.environ.get(n) or '').strip()
    print(n, 'есть' if v else '-')
    if v and not key: key=v
if not key: raise SystemExit('ключ не найден')
bases=['https://crm.sitniks.com/open-api','https://api.sitniks.com/open-api','https://crm.sitniks.com/api/open-api']
paths=['/products?limit=2','/products?page=1&limit=2','/product?limit=2','/products/list?limit=2','/goods?limit=2']
for b in bases:
    for p in paths:
        for auth in ('Bearer '+key, key):
            req=urllib.request.Request(b+p,headers={'Authorization':auth,'Accept':'application/json','User-Agent':'autopost-bot'})
            try:
                r=urllib.request.urlopen(req,timeout=30); d=json.loads(r.read())
                shape=list(d.keys())[:10] if isinstance(d,dict) else ('list',len(d))
                items=d.get('data') if isinstance(d,dict) else d
                if isinstance(items,dict): items=items.get('items') or items.get('data') or items.get('results')
                one=items[0] if isinstance(items,list) and items else {}
                print('OK',b+p,auth[:6],shape,'| поля товара:',list(one.keys())[:40] if isinstance(one,dict) else one)
                if isinstance(one,dict): print(json.dumps({k:one[k] for k in list(one)[:25] if not isinstance(one[k],(list,dict))},ensure_ascii=False)[:800])
                raise SystemExit
            except urllib.error.HTTPError as e: print(e.code,b+p,auth[:6])
            except SystemExit: raise
            except Exception as e: print('ERR',b+p,str(e)[:60])
