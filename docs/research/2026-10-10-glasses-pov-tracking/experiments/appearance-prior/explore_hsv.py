"""HSV of the ball along the truth track (dev only, exploration): what does the ball look like near, mid, far?"""
import json, sys
import cv2, numpy as np
L='/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
cuts={c['stem']:c for c in json.load(open(f'{L}/work/cuts/cuts.json'))}
def P(v): return v if isinstance(v,list) else [v.get('x'),v.get('y'),v.get('r')]
for stem in sys.argv[1:]:
    c=cuts[stem]; tr=json.load(open(f'{L}/truth/{stem}.json'))
    cap=cv2.VideoCapture(c['cut_path']); frames=[]
    while True:
        ok,f=cap.read()
        if not ok: break
        frames.append(f)
    pts=sorted(((int(k),P(v)) for k,v in tr['ball'].items()),key=lambda kv:kv[0])
    pts=[(f,p) for f,p in pts if p[2] and p[2]>=4]
    sel=pts[::max(1,len(pts)//10)]
    print(stem)
    for f,(x,y,r) in sel:
        k=f-c['cut_start']
        if not (0<=k<len(frames)): continue
        hsv=cv2.cvtColor(frames[k],cv2.COLOR_BGR2HSV)
        H,W=hsv.shape[:2]
        yy,xx=np.mgrid[0:H,0:W]
        inner=((xx-x)**2+(yy-y)**2)<=(0.6*r)**2
        ring=(((xx-x)**2+(yy-y)**2)<=(2.5*r)**2)&(((xx-x)**2+(yy-y)**2)>(1.4*r)**2)
        a=hsv[inner].reshape(-1,3); b=hsv[ring].reshape(-1,3)
        q=lambda m: np.percentile(m,[10,50,90],axis=0).astype(int).tolist()
        print(f'  f{f} k{k} r{r:.0f} ball H/S/V p10/50/90 {q(a)}  bg {q(b)}')
