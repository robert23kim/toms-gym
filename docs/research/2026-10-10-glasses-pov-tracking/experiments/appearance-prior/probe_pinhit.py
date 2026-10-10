"""Does the camera-compensated motion energy around/above the ball spike at the pin hit? (dev truth for the reference frame only)"""
import json, sys
import cv2, numpy as np
sys.path.insert(0, '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking/experiments/appearance-prior')
from apptrack import motion_map
from src.bowling.trajectory.yolo_chain import reliable_shift, ChainConfig
L='/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'; X=f'{L}/experiments/appearance-prior'
cuts={c['stem']:c for c in json.load(open(f'{L}/work/cuts/cuts.json'))}
for stem in sys.argv[1:]:
    c=cuts[stem]; tr=json.load(open(f'{L}/truth/{stem}.json')); d=json.load(open(f'{X}/tracks/{stem}.json'))
    shifts={int(k):v for k,v in json.load(open(f'{X}/cache/{stem}.json'))['shifts'].items()}
    cap=cv2.VideoCapture(c['cut_path']); grays=[]
    while True:
        ok,f=cap.read()
        if not ok: break
        grays.append(cv2.cvtColor(f,cv2.COLOR_BGR2GRAY))
    cc=ChainConfig(); prev=None; vals=[]
    tk={p['f']-c['cut_start']:p for p in d['frames']}
    for k in range(1,len(grays)):
        sh,ok=reliable_shift(shifts,k,cc,prev); prev=sh
        if k not in tk: vals.append((k,None)); continue
        p=tk[k]; x,y,r=p['x'],p['y'],max(p['r'],5)
        mm=motion_map(grays[k-1],grays[k],sh)
        H,W=mm.shape
        box=mm[int(max(0,y-10*r)):int(min(H,y+2*r)), int(max(0,x-8*r)):int(min(W,x+8*r))]
        vals.append((k, round(float(box.mean()),1) if box.size else None))
    pin=tr['pin_hit_frame']-c['cut_start']
    print(stem[9:15],'truth pin k',pin, 'vals k:v', [(k,v) for k,v in vals if pin-12<=k<=pin+8])
