import numpy as np
from PIL import Image
from scipy import ndimage as nd
def detect(img, x0, x1, y0=0, y1=None, thr=225):
    a=np.asarray(img.convert('RGB')).astype(int)
    y1=y1 or a.shape[0]
    m=a[y0:y1,x0:x1].min(2)<thr
    m=nd.binary_opening(m,structure=np.ones((21,21)))
    lab,n=nd.label(m)
    if n==0: return None
    sizes=nd.sum(m,lab,range(1,n+1)); k=int(np.argmax(sizes))+1
    ys,xs=np.where(lab==k)
    b=(xs.min()+x0,ys.min()+y0,xs.max()+x0,ys.max()+y0)
    fill=sizes[k-1]/((b[2]-b[0]+1)*(b[3]-b[1]+1))
    return ('round' if fill<0.88 else 'rect'), b, round(float(fill),3)
