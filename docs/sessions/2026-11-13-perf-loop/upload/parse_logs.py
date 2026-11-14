import json, re, collections, os, sys
# Reads and writes next to the raw gcloud pulls, which hold emails, IPs and UAs and stay outside the repo.
os.chdir('/Users/toka/code/bowling-app/perf-fixtures-2026-11-13/upload-logs')
d = json.load(open('upload-logs-raw.json'))
d.sort(key=lambda e: e['timestamp'])
from datetime import datetime
def ts(s):
    s = s.rstrip('Z')
    if '.' in s:
        a, b = s.split('.')
        s = a + '.' + (b + '000000')[:6]
    else:
        s += '.000000'
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')
signed = {}
rows = []
fe = collections.Counter()
fe_rows = []
for e in d:
    t = e.get('textPayload', '')
    m = re.search(r'Issued signed upload URL for (\S+) \(type=([^)]*)\)', t)
    if m:
        signed[m.group(1)] = (ts(e['timestamp']), m.group(2)); continue
    m = re.search(r'Finalize upload: object=(\S+), competition=(\S+), user_id=(\S+), email=(\S+), lift_type=(\S+)', t)
    if m:
        obj = m.group(1)
        s = signed.get(obj)
        rows.append(dict(obj=obj, comp=m.group(2)[:8], lift=m.group(5), ctype=s[1] if s else None,
                         signed_at=s[0].isoformat() if s else None, finalize_at=ts(e['timestamp']).isoformat(),
                         gap_s=(ts(e['timestamp']) - s[0]).total_seconds() if s else None))
        continue
    if 'FRONTEND_ERROR' in t:
        m = re.search(r'page=(\S+) action=(\S+) error=(.*?) url=(\S*) build=(\S+) platform=(\S+) details=(.*) userAgent=(.*)$', t, re.S)
        if m:
            fe[(m.group(2), m.group(6))] += 1
            fe_rows.append(dict(ts=e['timestamp'], page=m.group(1), action=m.group(2), error=m.group(3)[:200], build=m.group(5), platform=m.group(6), details=m.group(7)[:600], ua=m.group(8)[:160]))
        else:
            fe[('UNPARSED', '')] += 1
json.dump(rows, open('uploads-paired.json', 'w'), indent=1)
json.dump(fe_rows, open('frontend-events.json', 'w'), indent=1)
print('uploads', len(rows), 'unpaired', sum(1 for r in rows if r['gap_s'] is None))
for r in rows: print(r['signed_at'], r['gap_s'], r['lift'], r['ctype'], r['comp'], r['obj'])
print(fe)
