import json, sys, math
L='/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
def P(v): return v if isinstance(v,list) else [v.get('x'),v.get('y'),v.get('r')]
stem=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 14
d=json.load(open(f'{X}/tracks/{stem}.json')) if False else json.load(open(sys.argv[3] if len(sys.argv)>3 else f'{L}/experiments/appearance-prior/tracks/{stem}.json'))
tr=json.load(open(f'{L}/truth/{stem}.json'))
print('track meta', d['meta']['track'])
tb={int(k):P(v) for k,v in tr['ball'].items()}
tk={p['f']:p for p in d['frames']}
fs=sorted(set(tb)|set(tk))
rows=[]
for f in fs:
    t=tb.get(f); p=tk.get(f)
    if t and t[0] is None: t=None
    dist=round(math.hypot(p['x']-t[0],p['y']-t[1])) if (t and p) else None
    rows.append(f"{f}: truth {[round(v) for v in t] if t else '-'} track {[round(p['x']),round(p['y']),round(p['r']),p['src']] if p else '-'} d={dist}")
print('\n'.join(rows[:n])); print('...'); print('\n'.join(rows[-8:]))
