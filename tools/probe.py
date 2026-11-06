import sys, json, os
sys.path.insert(0,'app')
from catalog import fetch_all,_get,API
os.makedirs('logs/probe',exist_ok=True)
d=fetch_all(); json.dump(d,open('logs/probe/catalog.json','w'),ensure_ascii=False); print('products',len(d))
json.dump(_get(f'{API}/content/categories-tree'),open('logs/probe/cats.json','w'),ensure_ascii=False)
k=[p for p in d if isinstance(p,dict) and p.get('kind')=='single'][:1]
if k: json.dump(_get(f"{API}/products/{k[0]['id']}/kits"),open('logs/probe/kits_sample.json','w'),ensure_ascii=False)
