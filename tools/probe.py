import urllib.request, os, re, json
H={'User-Agent':'Mozilla/5.0 (compatible; autopost-bot)'}
def get(u):
    try: return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40).read().decode('utf-8','ignore')
    except Exception as e: return ''
html=get('https://artbynumbers.com.ua/catalog')
js=sorted(set(re.findall(r'/_nuxt/[a-z0-9.]+\.js',html)))
# also lazy chunks referenced from manifest/runtime
rt=''.join(get('https://artbynumbers.com.ua'+p) for p in js)
chunks=set(re.findall(r'"([a-f0-9]{7})"',rt))
out=[]
allt=rt
for c in list(chunks)[:200]:
    allt+=get(f'https://artbynumbers.com.ua/_nuxt/{c}.js')
for m in re.finditer(r'api/server/products["?]|api/server/products",|products/getList|getList:function|catalog/filter|api/server/catalog',allt):
    out.append(allt[max(0,m.start()-500):m.start()+700])
open('logs/probe/ctx2.txt','w').write('\n\n=====\n'.join(out[:30])); print('found',len(out),'chunks',len(chunks))
