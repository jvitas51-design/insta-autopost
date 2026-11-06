import urllib.request, json, urllib.parse
H={'User-Agent':'Mozilla/5.0 (compatible; autopost-bot)','Accept':'application/json'}
B='https://api.artbynumbers.com.ua/api/server/products'
tries=[{},{'page':2},{'category':'kartyny-za-nomeramy/krugli-kartyny'},{'category':'kartyny-za-nomeramy'},{'category':'nabory-kartyn'},
 {'category':'nabory-kartyn/kompozytsii-z-farbamy-metalik'},{'category':'kartyny-za-nomeramy','page':5},{'category':'kartyny-za-nomeramy','limit':100},{'category':'kartyny-za-nomeramy','perPage':100},{'category':'kartyny-za-nomeramy','pageSize':100},{'search':'ABN-039K'}]
for p in tries:
    u=B+('?'+urllib.parse.urlencode(p) if p else '')
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40); d=json.loads(r.read())
        print(p,'total',r.headers.get('x-total'),'n',len(d),'first',[x.get('articul') for x in d[:4]])
    except Exception as e: print(p,'ERR',e)
