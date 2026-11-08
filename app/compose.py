import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as nd

def refine_circle(img, box, search=14):
    g=np.asarray(img.convert('L')).astype(float)
    gm=np.hypot(nd.sobel(g,0),nd.sobel(g,1))
    cx0=(box[0]+box[2])/2; cy0=(box[1]+box[3])/2; r0=(box[2]-box[0])/2
    t=np.linspace(0,2*np.pi,360,endpoint=False)
    best=(-1,None)
    for dr in range(-search,search+1,2):
        for dx in range(-search,search+1,2):
            for dy in range(-search,search+1,2):
                r=r0+dr; x=(cx0+dx+r*np.cos(t)).astype(int); y=(cy0+dy+r*np.sin(t)).astype(int)
                ok=(x>=0)&(y>=0)&(x<g.shape[1])&(y<g.shape[0])
                s=gm[y[ok],x[ok]].mean()
                if s>best[0]: best=(s,(cx0+dx,cy0+dy,r))
    cx,cy,r=best[1]
    return (cx-r,cy-r,cx+r,cy+r)

def canvas_look(a, shape, seed=0):
    """Объём холста как на фото-макетах: фактура ткани, мягкое затемнение и блик по краю, лёгкий свет сверху-слева."""
    a = np.asarray(a).astype(float) / 255
    h, w = a.shape[:2]
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    # фактура холста: мелкая сетка нитей + шум
    period = max(2.2, w / 260)
    tex = 0.5 * np.sin(xx * np.pi / period) * np.sin(yy * np.pi / period) + nd.gaussian_filter(rng.normal(0, 1, (h, w)), 0.7)
    a *= (1 + 0.025 * tex)[..., None]
    # расстояние до края и направление к краю
    if shape == 'round':
        cx, cy, r = (w - 1) / 2, (h - 1) / 2, min(w, h) / 2
        d = r - np.hypot(xx - cx, yy - cy)
        nx, ny = (xx - cx) / r, (yy - cy) / r
    else:
        d = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy])
        nx = np.where(xx < w - 1 - xx, -1.0, 1.0) * (np.minimum(xx, w - 1 - xx) == d)
        ny = np.where(yy < h - 1 - yy, -1.0, 1.0) * (np.minimum(yy, h - 1 - yy) == d)
    e = max(4.0, 0.022 * min(w, h))
    t = np.clip(1 - d / e, 0, 1) ** 1.6                    # 1 у самого края, 0 внутри
    side = (nx + ny) / 1.414                               # >0 правый/нижний край (в тень), <0 левый/верхний (к свету)
    shade = 1 - t * np.where(side > 0, 0.30 * side + 0.10, 0.10) + t * np.where(side < 0, -0.10 * side, 0)
    light = 1 + 0.045 * (0.5 - (xx / w + yy / h) / 2)
    a *= (shade * light)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype('uint8'))


def _round_corners(m, r):
    if r < 1:
        return m
    big = Image.new('L', (m.width * 4, m.height * 4), 0)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, big.width - 1, big.height - 1), radius=r * 4, fill=255)
    rr = np.asarray(big.resize(m.size, Image.LANCZOS))
    return Image.fromarray(np.minimum(np.asarray(m), rr).astype('uint8'))


def fit_round(art):
    """crop circle from site image (white corners)"""
    a=np.asarray(art.convert('RGB')).min(2)<245
    ys,xs=np.where(a); return art.crop((xs.min(),ys.min(),xs.max()+1,ys.max()+1))

def paste_round(base, art, box, grow=2):
    b=[int(round(v)) for v in (box[0]-grow,box[1]-grow,box[2]+grow,box[3]+grow)]
    w,h=b[2]-b[0],b[3]-b[1]
    a=canvas_look(fit_round(art).convert('RGB').resize((w,h),Image.LANCZOS),'round')
    m=Image.new('L',(w*4,h*4),0); ImageDraw.Draw(m).ellipse((0,0,w*4-1,h*4-1),fill=255)
    m=m.resize((w,h),Image.LANCZOS)
    base.paste(a,(b[0],b[1]),m); return base

def paste_rect(base, art, box, keep_mask=None):
    b=[int(v) for v in box]; w,h=b[2]-b[0],b[3]-b[1]
    # cover-fit
    ar=art.width/art.height; tr=w/h
    if ar>tr: nw=int(art.height*tr); art=art.crop(((art.width-nw)//2,0,(art.width-nw)//2+nw,art.height))
    else: nh=int(art.width/tr); art=art.crop((0,(art.height-nh)//2,art.width,(art.height-nh)//2+nh))
    a=canvas_look(art.convert('RGB').resize((w,h),Image.LANCZOS),'rect')
    m=Image.new('L',(w,h),255)
    if keep_mask is not None: m=Image.fromarray(np.where(keep_mask[b[1]:b[3],b[0]:b[2]],0,255).astype('uint8'))
    m=_round_corners(m, max(2, int(0.012*min(w,h))))
    base.paste(a,(b[0],b[1]),m); return base

def sheet_mask(img, box):
    """pixels inside rect box covered by the contour sheet lying on top"""
    a=np.asarray(img.convert('RGB')).astype(float)
    x0,y0,x1,y1=[int(v) for v in box]
    sub=a[y0:y1,x0:x1]
    br=nd.uniform_filter(sub.mean(2),7); sat=nd.uniform_filter(sub.max(2)-sub.min(2),7)
    paper=(br>205)&(sat<14)
    paper=nd.binary_opening(paper,np.ones((7,7)))
    lab,n=nd.label(paper); keep=np.zeros_like(paper)
    for k in range(1,n+1):
        c=lab==k; ys,xs=np.where(c)
        if c.sum()>1500 and xs.min()<=3 and ys.max()>=sub.shape[0]-6: keep|=c
    keep=nd.binary_closing(keep,np.ones((9,9)))
    # extend down to the box bottom under the detected paper columns
    for x in range(keep.shape[1]):
        ys=np.where(keep[:,x])[0]
        if len(ys): keep[ys.min():,x]=True
    keep=nd.binary_dilation(keep,np.ones((3,3)))
    M=np.zeros(a.shape[:2],bool); M[y0:y1,x0:x1]=keep; return M

def poly_mask(size, poly, grow=1):
    m=Image.new('L',size,0); ImageDraw.Draw(m).polygon([tuple(p) for p in poly],fill=255)
    m=m.filter(ImageFilter.MaxFilter(grow*2+1))
    return np.asarray(m)>0

def render_template(tpl_img, slots, arts):
    base=tpl_img.copy(); orig=tpl_img
    for slot,a in zip(slots,arts):
        shape,box=slot[0],slot[1]
        if shape=='round': paste_round(base,a,refine_circle(orig,box))
        else:
            keep=poly_mask(orig.size,slot[2]) if len(slot)>2 else None
            paste_rect(base,a,box,keep)
    return base

def refine_rect(img, box, search=30):
    g=np.asarray(img.convert('L')).astype(float)
    gx=np.abs(nd.sobel(g,1)); gy=np.abs(nd.sobel(g,0))
    x0,y0,x1,y1=[int(v) for v in box]
    def best_v(xc,ya,yb):
        xs=range(max(1,xc-search),min(g.shape[1]-1,xc+search)); return max(xs,key=lambda x: gx[ya:yb,x].mean())
    def best_h(yc,xa,xb):
        ys=range(max(1,yc-search),min(g.shape[0]-1,yc+search)); return max(ys,key=lambda y: gy[y,xa:xb].mean())
    for _ in range(2):
        my=(y1-y0)//6; mx=(x1-x0)//6
        x0=best_v(x0,y0+my,y1-my); x1=best_v(x1,y0+my,y1-my)
        y0=best_h(y0,x0+mx,x1-mx); y1=best_h(y1,x0+mx,x1-mx)
    return (x0,y0,x1,y1)
