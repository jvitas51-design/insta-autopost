"""Проверка токена Instagram: ничего не публикует, только читает."""
import os, sys, json, urllib.request, urllib.parse
T=os.environ.get('IG_TOKEN','').strip()
V='v21.0'
def get(path, **p):
    p['access_token']=T
    u=f'https://graph.facebook.com/{V}/{path}?'+urllib.parse.urlencode(p)
    try:
        with urllib.request.urlopen(u,timeout=30) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        return {'error':json.loads(e.read() or b'{}').get('error',{})}
if not T: print('НЕТ ТОКЕНА: секрет IG_TOKEN пустой или не найден'); sys.exit(1)
me=get('me',fields='id,name'); print('Пользователь токена:',me)
dbg=get('debug_token',input_token=T)
d=dbg.get('data',{}); print('Права токена:',d.get('scopes')); print('Истекает:',d.get('expires_at'),'(0 = никогда)')
acc=get('me/accounts',fields='name,instagram_business_account{id,username}')
print('Страницы:',json.dumps(acc,ensure_ascii=False))
ig=[a['instagram_business_account'] for a in acc.get('data',[]) if a.get('instagram_business_account')]
if not ig: print('ОШИБКА: к токену не привязан ни один Instagram'); sys.exit(1)
for x in ig:
    lim=get(f"{x['id']}/content_publishing_limit",fields='quota_usage,config')
    print('Instagram:',x['username'],'ID',x['id'],'лимит публикаций:',lim)
print('ТОКЕН РАБОТАЕТ')
