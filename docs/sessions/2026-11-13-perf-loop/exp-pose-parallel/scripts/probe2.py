import sys, json
sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0])
from probe import run

def per_pose(entry):
    n, _b, vals = entry
    if n == 0:
        return []
    k = len(vals) // n  # 33*5 + 33*3 per pose, landmarks first then world
    lm = vals[: n * 165]
    return [tuple(lm[i * 165:(i + 1) * 165]) for i in range(n)]

path, n = sys.argv[1], int(sys.argv[2])
a = run(path, 0, n)
for off, ln in [(int(x.split(":")[0]), int(x.split(":")[1])) for x in sys.argv[3].split(",")]:
    c = run(path, off, min(off + ln, n))
    rows = []
    prev = None
    for i in sorted(c):
        sa, sc = per_pose(a[i]), per_pose(c[i])
        cold_in_seq = [sa.index(p) if p in sa else -1 for p in sc]
        key = (len(sa), len(sc), tuple(cold_in_seq), c[i][1] == a[i][1])
        if key != prev:
            rows.append({"rel": i - off, "seq_n": len(sa), "cold_n": len(sc), "cold_pose_idx_in_seq": cold_in_seq, "identical": c[i][1] == a[i][1]})
            prev = key
    print(json.dumps({"offset": off, "len": len(c), "transitions": rows[:14]}))
