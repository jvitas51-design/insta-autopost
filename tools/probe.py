import urllib.request, os, re, json
os.makedirs('logs/probe',exist_ok=True)
H={'User-Agent':'Mozilla/5.0 (compatible; autopost-bot)','Accept':'application/json, text/plain, */*'}
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40); return r.status,r.read()
    except urllib.error.HTTPError as e: return e.code,e.read()
    except Exception as e: return 'ERR',str(e).encode()
html=open('logs/probe/product.html',encoding='utf-8').read()
js=sorted(set(re.findall(r'/_nuxt/[a-z0-9.]+\.js',html)))
out=[]
for p in js:
    st,b=get('https://artbynumbers.com.ua'+p); t=b.decode('utf-8','ignore')
    for m in re.finditer(r'api/server/products|kits',t):
        out.append(p+' :: '+t[max(0,m.start()-300):m.start()+300])
open('logs/probe/ctx.txt','w').write('\n\n'.join(out[:40]))
for u in ['https://api.artbynumbers.com.ua/api/server/products','https://api.artbynumbers.com.ua/api/server/products/?page=1&limit=5',
          'https://artbynumbers.com.ua/api/server/products/?page=1&limit=5','https://artbynumbers.com.ua/kits','https://api.artbynumbers.com.ua/api/server/content/categories-tree']:
    st,b=get(u); print(u,st,len(b)); open('logs/probe/'+re.sub(r'\W+','_',u)[-60:]+'.txt','wb').write(b[:300000])
