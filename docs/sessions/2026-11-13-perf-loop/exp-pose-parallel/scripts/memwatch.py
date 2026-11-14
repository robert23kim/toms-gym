"""Run a command, sample RSS of its whole process tree every 0.25 s, report the peak sum."""
import subprocess, sys, time, json

def tree(root):
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,rss="], capture_output=True, text=True).stdout
    rows = [tuple(int(x) for x in l.split()) for l in out.splitlines() if l.strip()]
    kids = {}
    for pid, ppid, rss in rows:
        kids.setdefault(ppid, []).append(pid)
    rss = {pid: r for pid, _pp, r in rows}
    seen, stack = [], [root]
    while stack:
        p = stack.pop()
        if p in rss:
            seen.append(p)
        stack.extend(kids.get(p, []))
    return {p: rss[p] for p in seen}

p = subprocess.Popen(sys.argv[2:])
peak_sum, peak_n, peak_each = 0, 0, 0
while p.poll() is None:
    t = tree(p.pid)
    s = sum(t.values())
    if s > peak_sum:
        peak_sum, peak_n = s, len(t)
    kid = [v for k, v in t.items() if k != p.pid]
    if kid:
        peak_each = max(peak_each, max(kid))
    time.sleep(0.25)
print(json.dumps({"label": sys.argv[1], "peak_tree_rss_mb": round(peak_sum / 1024), "procs_at_peak": peak_n,
                  "largest_child_rss_mb": round(peak_each / 1024), "exit": p.returncode}))
