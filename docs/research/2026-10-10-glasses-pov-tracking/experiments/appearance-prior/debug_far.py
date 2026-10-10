import json, sys
import cv2, numpy as np
sys.path.insert(0, '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking/experiments/appearance-prior')
from apptrack import hsv_fixed_mask
X='/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking/experiments/appearance-prior'
L='/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
stem=sys.argv[1]; fs=[int(v) for v in sys.argv[2].split(',')]; half=int(sys.argv[3]) if len(sys.argv)>3 else 120
c={c['stem']:c for c in json.load(open(f'{L}/work/cuts/cuts.json'))}[stem]
tr=json.load(open(f'{L}/truth/{stem}.json')); tk={p['f']:p for p in json.load(open(f'{X}/tracks/{stem}.json'))['frames']}
def P(v): return v if isinstance(v,list) else [v.get('x'),v.get('y'),v.get('r')]
cap=cv2.VideoCapture(c['cut_path']); frames=[]
while True:
    ok,f=cap.read()
    if not ok: break
    frames.append(f)
tiles=[]
for f in fs:
    k=f-c['cut_start']; im=frames[k]; m=cv2.cvtColor(hsv_fixed_mask(cv2.cvtColor(im,cv2.COLOR_BGR2HSV)),cv2.COLOR_GRAY2BGR)
    t=P(tr['ball'][str(f)]) if str(f) in tr['ball'] else None
    cx,cy=(int(t[0]),int(t[1])) if t else (int(tk[f]['x']),int(tk[f]['y']))
    for a in (im.copy(),m):
        if t: cv2.circle(a,(int(t[0]),int(t[1])),max(3,int(t[2])),(0,255,0),1)
        if f in tk: cv2.circle(a,(int(tk[f]['x']),int(tk[f]['y'])),max(3,int(tk[f]['r'])),(0,165,255),1)
        crop=a[max(0,cy-half):cy+half, max(0,cx-half):cx+half]
        crop=cv2.copyMakeBorder(crop,0,2*half-crop.shape[0],0,2*half-crop.shape[1],cv2.BORDER_CONSTANT)
        crop=cv2.resize(crop,(300,300),interpolation=cv2.INTER_NEAREST)
        cv2.putText(crop,f'f{f}',(5,20),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,255),2)
        tiles.append(crop)
n=len(fs); img=np.vstack([np.hstack(tiles[0::2]),np.hstack(tiles[1::2])])
cv2.imwrite(f'{X}/debug/far_{stem[9:15]}.jpg',img,[cv2.IMWRITE_JPEG_QUALITY,80]); print('ok')
