import json, sys
import cv2, numpy as np
sys.path.insert(0, '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking/experiments/appearance-prior')
from apptrack import hsv_fixed_mask
X='/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking/experiments/appearance-prior'; L='/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
stem=sys.argv[1]; ks=[int(v) for v in sys.argv[2].split(',')]
c={c['stem']:c for c in json.load(open(f'{L}/work/cuts/cuts.json'))}[stem]
cap=cv2.VideoCapture(c['cut_path']); frames=[]
while True:
    ok,f=cap.read()
    if not ok: break
    frames.append(f)
tr=json.load(open(f'{L}/truth/{stem}.json'))
def P(v): return v if isinstance(v,list) else [v.get('x'),v.get('y'),v.get('r')]
tiles=[]
for k in ks:
    im=frames[k]; hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV); m=hsv_fixed_mask(hsv)
    vis=cv2.cvtColor(m,cv2.COLOR_GRAY2BGR)
    t=tr['ball'].get(str(k+c['cut_start']))
    for a in (im.copy(),vis):
        if t:
            x,y,r=P(t); cv2.circle(a,(int(x),int(y)),max(3,int(r)),(0,255,0),4)
        cv2.putText(a,f'k{k} f{k+c["cut_start"]}',(10,60),cv2.FONT_HERSHEY_SIMPLEX,2,(0,255,255),4)
        tiles.append(cv2.resize(a,None,fx=0.3,fy=0.3))
n=len(ks); row1=np.hstack(tiles[0::2]); row2=np.hstack(tiles[1::2])
cv2.imwrite(f'{X}/debug/mask_{stem[9:15]}.jpg',np.vstack([row1,row2]),[cv2.IMWRITE_JPEG_QUALITY,70])
