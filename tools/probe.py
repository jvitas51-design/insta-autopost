import urllib.request, json, urllib.parse, re
H={'User-Agent':'Mozilla/5.0 (compatible; autopost-bot)','Accept':'application/json'}
B='https://api.artbynumbers.com.ua/api/server/products'
def g(p):
    u=B+'?'+urllib.parse.urlencode(p)
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40); d=json.loads(r.read())
        return r.headers.get('x-total'), [(x.get('articul'),x.get('availableForSale')) for x in d][:6]
    except Exception as e: return 'ERR',str(e)[:80]
for p in [{'search':'ABN-044K'},{'search':'044K'},{'search':'Сила роду'},{'search':'ABN-039K','available':'all'},{'search':'ABN-039K','inStock':'false'},
          {'search':'ABN-039K','showAll':'true'},{'search':'ABN-039K','availability':'all'},{'category':'krugli-kartyny','limit':100},{'category':'kartyny-za-nomeramy/krugli-kartyny','limit':100}]:
    print(p,g(p))
# product page by html search
html=urllib.request.urlopen(urllib.request.Request('https://artbynumbers.com.ua/catalog?search=ABN-044K',headers={'User-Agent':H['User-Agent']}),timeout=40).read().decode('utf-8','ignore')
print('html ids',set(re.findall(r'/product/([0-9a-f\-]{36})',html)))
