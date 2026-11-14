import json, re, statistics as st
RAW = '/Users/toka/code/bowling-app/perf-fixtures-2026-11-13/upload-logs'  # raw pulls hold emails, IPs and UAs: kept outside the repo
from datetime import datetime, timedelta
def ts(s):
    s = s.rstrip('Z')
    a, _, b = s.partition('.')
    return datetime.strptime(a + '.' + (b + '000000')[:6], '%Y-%m-%dT%H:%M:%S.%f')
def lat(s): return float(s.rstrip('s'))
rows = json.load(open(RAW + '/uploads-paired.json'))
sizes = {}
for line in open(RAW + '/objects-ls.txt'):
    p = line.split()
    if len(p) == 3 and p[2].startswith('gs://'):
        sizes[p[2].split('/', 3)[3]] = (int(p[0]), p[1])
req = json.load(open(RAW + '/request-logs-raw.json'))
R = []
for e in req:
    h = e['httpRequest']
    u = re.sub(r'https?://[^/]+', '', h['requestUrl'])
    # request log timestamp = request arrival; latency = server time
    R.append(dict(t=ts(e['timestamp']), m=h['requestMethod'], u=u, lat=lat(h.get('latency', '0s')), ua=h.get('userAgent', ''), ip=h.get('remoteIp', '')))
R.sort(key=lambda r: r['t'])
def nearest(m, upat, t0, lo=-3, hi=3, after=False):
    best = None
    for r in R:
        if r['m'] != m or not re.search(upat, r['u']): continue
        dt = (r['t'] - t0).total_seconds()
        if lo <= dt <= hi and (best is None or abs(dt) < abs((best['t'] - t0).total_seconds())): best = r
    return best
def dev(ua):
    if 'iPhone' in ua or 'iPad' in ua: d = 'iOS'
    elif 'Android' in ua: d = 'Android'
    elif 'Macintosh' in ua: d = 'Mac'
    else: d = 'other'
    if '; wv)' in ua: d += '-webview'
    return d
out = []
for r in rows:
    signed_at = datetime.fromisoformat(r['signed_at']); fin_at = datetime.fromisoformat(r['finalize_at'])
    sreq = nearest('POST', r'^/upload/signed-url', signed_at, -5, 1)
    spre = nearest('OPTIONS', r'^/upload/signed-url', signed_at, -8, 1)
    freq = nearest('POST', r'^/upload/finalize', fin_at, -3, 1)
    fpre = nearest('OPTIONS', r'^/upload/finalize', fin_at, -6, 1)
    # analyze: first POST /lifting/analyze after finalize arrival, within 30s
    areq = None
    for q in R:
        if q['m'] == 'POST' and '/lifting/analyze/' in q['u'] and 0 <= (q['t'] - freq['t']).total_seconds() <= 60:
            areq = q; break
    size, created = sizes.get(r['obj'], (None, None))
    sign_done = sreq['t'] + timedelta(seconds=sreq['lat'])
    # sign response sent -> finalize preflight arrival: the PUT plus one client<->backend round trip,
    # so the Mbit/s below is a lower bound on the real transfer rate
    put_window = (((fpre or freq)['t']) - sign_done).total_seconds()
    fin_done = freq['t'] + timedelta(seconds=freq['lat'])
    o = dict(day=r['signed_at'][:10], lift=r['lift'], ctype=r['ctype'], device=dev(sreq['ua']), size_mb=round(size / 1e6, 2) if size else None,
             sign_preflight_to_post_s=round((sreq['t'] - spre['t']).total_seconds(), 3) if spre else None,
             sign_server_s=round(sreq['lat'], 3), put_window_s=round(put_window, 2),
             mbit_s=round(size * 8 / 1e6 / put_window, 1) if size and put_window > 0 else None,
             finalize_preflight_to_post_s=round((freq['t'] - fpre['t']).total_seconds(), 3) if fpre else None,
             finalize_server_s=round(freq['lat'], 3),
             finalize_done_to_analyze_arrival_s=round((areq['t'] - fin_done).total_seconds(), 3) if areq else None,
             analyze_server_s=round(areq['lat'], 3) if areq else None,
             total_sign_to_analyze_accepted_s=round(((areq['t'] + timedelta(seconds=areq['lat'])) - (spre['t'] if spre else sreq['t'])).total_seconds(), 2) if areq else None,
             obj=r['obj'])
    out.append(o)
json.dump(out, open(RAW + '/baseline-uploads-with-objects.json', 'w'), indent=1)
json.dump([{k: v for k, v in o.items() if k != 'obj'} for o in out], open('baseline-uploads.json', 'w'), indent=1)
cols = ['day', 'lift', 'device', 'ctype', 'size_mb', 'sign_preflight_to_post_s', 'sign_server_s', 'put_window_s', 'mbit_s', 'finalize_preflight_to_post_s', 'finalize_server_s', 'finalize_done_to_analyze_arrival_s', 'analyze_server_s', 'total_sign_to_analyze_accepted_s']
print('| ' + ' | '.join(cols) + ' |'); print('|' + '---|' * len(cols))
for o in out: print('| ' + ' | '.join(str(o[c]) for c in cols) + ' |')
def summ(name, xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs: print(name, 'n=0'); return
    print(f"{name}: n={len(xs)} min={xs[0]} median={st.median(xs)} p90={xs[int(0.9 * (len(xs) - 1))]} max={xs[-1]}")
for c in cols[4:]: summ(c, [o[c] for o in out])
for d in sorted(set(o['device'] for o in out)):
    sub = [o for o in out if o['device'] == d]
    print('--', d, 'n=', len(sub))
    for c in ['size_mb', 'put_window_s', 'mbit_s', 'total_sign_to_analyze_accepted_s']: summ('   ' + c, [o[c] for o in sub])

# pre-sign evidence on the fixtures: container creation_time and filename timestamps
from datetime import timezone
FX = {  # object suffix -> (ffprobe duration s, container creation_time UTC)
 '20261106_081902.mp4': (86.4667, '2026-11-06T13:20:39'), '20261110_094245.mp4': (28.3667, '2026-11-10T14:43:19'),
 '20261102_074237.mp4': (34.1, '2026-11-02T12:43:26'), '20261110_093900.mp4': (66.1667, '2026-11-10T14:40:11'),
 '20261106_082251.mp4': (57.4667, '2026-11-06T13:23:53'),
 'E1536547-0097-4B7F-97E0-C8D2AAA2FA84.MOV': (109.0817, '2026-11-13T16:47:05'), '02820866-F48E-4B30-AE62-0CE945961023.MOV': (51.3317, '2026-11-13T16:45:38'),
 '946C5722-1686-4634-B6F3-83A4A5590CA7.MOV': (31.9567, '2026-11-12T16:54:50')}
paired = {r['obj']: r for r in rows}
pre = []
print()
print('| fixture | device | clip_s | creation_time -> sign_s | per clip second | what the gap is |'); print('|---|---|---|---|---|---|')
for o in out:
    for suf, (dur, ct) in FX.items():
        if o['obj'].endswith(suf):
            signed = datetime.fromisoformat(paired[o['obj']]['signed_at'])
            gap = (signed - datetime.fromisoformat(ct)).total_seconds()
            if o['device'].startswith('Android'):
                row = dict(lift=o['lift'], device=o['device'], clip_s=round(dur, 1), gap_s=round(gap, 1), per_clip_s=round(gap / dur, 2), meaning='mp4-muxer stamps creation_time when the encode starts, so this is decode+scale+encode+mux (+ sign round trip), +-1 s')
            else:
                after_end = gap - dur
                row = dict(lift=o['lift'], device=o['device'], clip_s=round(dur, 1), gap_s=round(after_end, 1), per_clip_s=round(after_end / dur, 2), meaning='creation_time is recording start, so this is recording end -> sign: taps plus the iOS picker export')
            pre.append(row)
            print(f"| {row['lift']} | {row['device']} | {row['clip_s']} | {row['gap_s']} | {row['per_clip_s']} | {row['meaning']} |")
json.dump(pre, open('presign-fixtures.json', 'w'), indent=1)
