"""Публикация в Instagram через официальный Graph API."""
import json, os, time, urllib.request, urllib.parse

V = 'v21.0'
G = f'https://graph.facebook.com/{V}'


class IG:
    def __init__(self, token):
        self.t = token
        acc = self.get('me/accounts', fields='instagram_business_account{id,username}')
        ig = [a['instagram_business_account'] for a in acc.get('data', []) if a.get('instagram_business_account')]
        if not ig:
            raise RuntimeError('к токену не привязан Instagram')
        self.id, self.username = ig[0]['id'], ig[0]['username']

    def _req(self, method, path, params):
        params = dict(params, access_token=self.t)
        data = urllib.parse.urlencode(params).encode()
        url = f'{G}/{path}' + ('' if method == 'POST' else '?' + data.decode())
        req = urllib.request.Request(url, data=data if method == 'POST' else None, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            err = json.loads(e.read() or b'{}').get('error', {})
            raise RuntimeError(f'Instagram API: {err.get("message")} (код {err.get("code")}/{err.get("error_subcode")})')

    def get(self, path, **p):
        return self._req('GET', path, p)

    def post(self, path, **p):
        return self._req('POST', path, p)

    def latest(self):
        d = self.get(f'{self.id}/media', fields='caption,media_type,media_product_type,timestamp', limit=1).get('data', [])
        return d[0] if d else None

    def wait(self, cid, timeout=900):
        t0 = time.time()
        while time.time() - t0 < timeout:
            st = self.get(cid, fields='status_code,status').get('status_code')
            if st == 'FINISHED':
                return
            if st in ('ERROR', 'EXPIRED'):
                raise RuntimeError(f'Instagram не принял файл: {self.get(cid, fields="status")}')
            time.sleep(10)
        raise RuntimeError('Instagram слишком долго обрабатывает файл')

    def carousel(self, urls, caption):
        kids = []
        for u in urls[:10]:
            kids.append(self.post(f'{self.id}/media', image_url=u, is_carousel_item='true')['id'])
        for k in kids:
            self.wait(k)
        cid = self.post(f'{self.id}/media', media_type='CAROUSEL', children=','.join(kids), caption=caption)['id']
        self.wait(cid)
        return self.post(f'{self.id}/media_publish', creation_id=cid)['id']

    def reel(self, video_url, cover_url, caption):
        cid = self.post(f'{self.id}/media', media_type='REELS', video_url=video_url, cover_url=cover_url,
                        caption=caption, share_to_feed='true')['id']
        self.wait(cid)
        return self.post(f'{self.id}/media_publish', creation_id=cid)['id']
