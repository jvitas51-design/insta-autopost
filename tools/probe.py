import os, json, urllib.request
key=os.environ['SITNIKS_API_KEY'].strip()
def g(q):
    req=urllib.request.Request('https://crm.sitniks.com/open-api/products?'+q,headers={'Authorization':'Bearer '+key,'Accept':'application/json','User-Agent':'autopost-bot'})
    return json.loads(urllib.request.urlopen(req,timeout=60).read())
d=g('limit=2'); print('count',d['count'])
p=d['data'][0]; print(json.dumps({'variations':p['variations'][:1],'attachments':p['attachments'][:1],'properties':p['properties'][:3],'category':p['category']},ensure_ascii=False)[:1500])
for q in ['limit=3&offset=3','limit=3&page=2','limit=3&skip=3']:
    try: print(q,[x['id'] for x in g(q)['data']])
    except Exception as e: print(q,e)
