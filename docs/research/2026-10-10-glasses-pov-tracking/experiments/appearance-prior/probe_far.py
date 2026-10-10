"""Offline probe (dev truth): at the far end, which map puts its strongest peak on the ball within +-W px of the
camera-shifted previous truth position? blackhat (dark disc at scale r), motion (camera-compensated diff), product."""
import json, sys, math
import cv2, numpy as np
sys.path.insert(0, '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking/experiments/appearance-prior')
from apptrack import motion_map
from src.bowling.trajectory.yolo_chain import apply_shift, reliable_shift, ChainConfig
L='/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
X=f'{L}/experiments/appearance-prior'
W=int(sys.argv[2]) if len(sys.argv)>2 else 80
def P(v): return v if isinstance(v,list) else [v.get('x'),v.get('y'),v.get('r')]
cuts={c['stem']:c for c in json.load(open(f'{L}/work/cuts/cuts.json'))}
stem=sys.argv[1]; c=cuts[stem]; tr=json.load(open(f'{L}/truth/{stem}.json'))
cache=json.load(open(f'{X}/cache/{stem}.json')); shifts={int(k):v for k,v in cache['shifts'].items()}
cap=cv2.VideoCapture(c['cut_path']); frames=[]
while True:
    ok,f=cap.read()
    if not ok: break
    frames.append(f)
grays=[cv2.cvtColor(f,cv2.COLOR_BGR2GRAY) for f in frames]
hsvs=[cv2.cvtColor(f,cv2.COLOR_BGR2HSV) for f in frames]
tb={int(k):P(v) for k,v in tr['ball'].items()}
pin=tr['pin_hit_frame']; fs=[f for f in sorted(tb) if pin-22<=f<=pin and f-1 in tb]
res={'blackhat':[], 'motion':[], 'product':[], 'hue':[], 'prod_hue':[]}
cc=ChainConfig(); prev=None
for f in fs:
    k=f-c['cut_start']; x,y,r=tb[f]; x0,y0,_=tb[f-1]
    sh,ok=reliable_shift(shifts,k,cc,prev); prev=sh
    px,py=apply_shift(sh,x0,y0)
    rp=max(4.0,float(tb[f-1][2] or 6))
    g=grays[k]
    ks=int(2*rp)*2+1
    bh=cv2.morphologyEx(g,cv2.MORPH_BLACKHAT,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(ks,ks))).astype(np.float32)
    bh=cv2.GaussianBlur(bh,(0,0),max(1.0,rp/2))
    mm=motion_map(grays[k-1],g,sh).astype(np.float32)
    mm=cv2.GaussianBlur(mm,(0,0),max(1.0,rp/2))
    h,s,v=cv2.split(hsvs[k]); hue=(((h>=125)&(h<=175)&(s>=25)).astype(np.float32)); hue=cv2.GaussianBlur(hue,(0,0),max(1.0,rp/2))
    maps={'blackhat':bh,'motion':mm,'product':bh*mm,'hue':hue*bh,'prod_hue':bh*mm*hue}
    H,Wd=g.shape
    xa,xb,ya,yb=int(max(0,px-W)),int(min(Wd,px+W)),int(max(0,py-W)),int(min(H,py+W))
    for name,m in maps.items():
        win=m[ya:yb,xa:xb]
        if win.size==0: res[name].append(None); continue
        iy,ix=np.unravel_index(np.argmax(win),win.shape)
        d=math.hypot(xa+ix-x,ya+iy-y); res[name].append(round(d))
print(stem,'frames',fs[0],'-',fs[-1],'window +-',W)
for name,v in res.items():
    hit=sum(1 for d in v if d is not None and d<=max(12,0))
    print(f'  {name:9s} within 12px: {hit}/{len(v)}  dists {v}')
