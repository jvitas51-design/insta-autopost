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
eps=set()
for p in js:
    st,b=get('https://artbynumbers.com.ua'+p); t=b.decode('utf-8','ignore')
    for m in re.findall(r'["\x60]((?:/api)?/(?:v\d/)?[a-zA-Z\-_/]*(?:product|categor|kit|catalog|set|search)[a-zA-Z\-_/${}.]*)["\x60]',t): eps.add(m)
open('logs/probe/endpoints.txt','w').write('\n'.join(sorted(eps)))
print('endpoints',len(eps))
