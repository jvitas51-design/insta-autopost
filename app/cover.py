import subprocess
import numpy as np
from PIL import Image
def _frames(video, fps=4, w=96, h=170):
    raw=subprocess.run(['ffmpeg','-v','error','-i',video,'-vf',f'fps={fps},scale={w}:{h},format=gray','-f','rawvideo','-'],capture_output=True).stdout
    return np.frombuffer(raw,np.uint8).reshape(-1,h,w).astype(float)
def last_scene_start(video, fps=4):
    f=_frames(video,fps); d=np.abs(np.diff(f,axis=0)).mean((1,2))
    n=len(f); thr=max(12.0, np.percentile(d,90))
    # walk back from the end: the last shot is where frames stay similar to the final frame
    ref=f[-1]; sim=np.abs(f-ref).mean((1,2))
    i=n-1
    while i>0 and sim[i-1]<25: i-=1
    return i/fps, n/fps
def cover_frame(video, out_jpg):
    start,dur=last_scene_start(video)
    t=start+(dur-start)*0.5
    subprocess.run(['ffmpeg','-v','error','-y','-ss',f'{t:.2f}','-i',video,'-frames:v','1','-vf','scale=1080:-2','-q:v','2',out_jpg],check=True)
    img=Image.open(out_jpg); 
    return {'last_scene_start':round(start,2),'cover_time':round(t,2),'duration':round(dur,2)}
