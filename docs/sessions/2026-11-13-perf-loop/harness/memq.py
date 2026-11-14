#!/usr/bin/env python3
"""memq.py <start-iso> <end-iso> <revision> [...] - Cloud Run memory utilisation per revision.
Per-minute p99 (ALIGN_PERCENTILE_99) and per-minute max (ALIGN_MAX via the distribution's
bucket upper bound is not exposed, so max = ALIGN_PERCENTILE_99 is the ceiling we can read).
Prints max over the window; zero points is reported as NO-DATA (a failed query, not a low peak)."""
import json, subprocess, sys, urllib.parse, urllib.request
start, end, revs = sys.argv[1], sys.argv[2], sys.argv[3:]
tok = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True).stdout.strip()
out = {}
for rev in revs:
    for aligner in ("ALIGN_PERCENTILE_99", "ALIGN_PERCENTILE_50"):
        q = urllib.parse.urlencode({
            "filter": f'metric.type="run.googleapis.com/container/memory/utilizations" AND resource.labels.revision_name="{rev}"',
            "interval.startTime": start, "interval.endTime": end,
            "aggregation.alignmentPeriod": "60s", "aggregation.perSeriesAligner": aligner})
        req = urllib.request.Request(f"https://monitoring.googleapis.com/v3/projects/toms-gym/timeSeries?{q}",
                                     headers={"Authorization": f"Bearer {tok}"})
        d = json.load(urllib.request.urlopen(req))
        pts = [p["value"]["doubleValue"] for ts in d.get("timeSeries", []) for p in ts["points"]]
        out.setdefault(rev, {})[aligner] = {"points": len(pts), "max": max(pts) if pts else None}
for rev, v in out.items():
    p99 = v["ALIGN_PERCENTILE_99"]
    print(rev, "NO-DATA" if not p99["points"] else f'p99/min max={p99["max"]:.3f} of limit ({p99["max"]*8:.2f} GiB of 8) n={p99["points"]}',
          f'| p50/min max={v["ALIGN_PERCENTILE_50"]["max"]}')
print(json.dumps(out))
