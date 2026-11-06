import urllib.request, os, re
os.makedirs('logs/probe',exist_ok=True)
H={'User-Agent':'Mozilla/5.0 (compatible; autopost-bot)'}
urls={'home':'https://artbynumbers.com.ua/','catalog':'https://artbynumbers.com.ua/catalog','search':'https://artbynumbers.com.ua/catalog?search=ABN-039K',
'product':'https://artbynumbers.com.ua/product/7efcee2e-ec11-48bb-8781-34862c110046','sitemap':'https://artbynumbers.com.ua/sitemap.xml','robots':'https://artbynumbers.com.ua/robots.txt'}
for k,u in urls.items():
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40); b=r.read()
        open(f'logs/probe/{k}.html','wb').write(b); print(k,r.status,len(b))
    except Exception as e: print(k,'ERR',e)
