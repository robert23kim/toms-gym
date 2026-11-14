import subprocess, sys, os, json
root = sys.argv[1]
PY = "/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python"
par = os.path.join(root, "src/lifting/pose/parallel.py")
est = os.path.join(root, "src/lifting/pose/estimator.py")
muts = [
 ("M1 sync on a single matching frame", par, "            if run == sync_frames:\n                return f - sync_frames + 1\n", "            if run == min(sync_frames, 1):\n                return f\n"),
 ("M1b sync on four matching frames", par, "            if run == sync_frames:\n                return f - sync_frames + 1\n", "            if run == sync_frames - 1:\n                return f - sync_frames + 2\n"),
 ("M12 sync search ignores the owner's own sync frame", par, "range(max(cand.start, owner.start, start), min(owner.hi, cand.hi))", "range(max(cand.start, owner.start), min(owner.hi, cand.hi))"),
 ("M2 splice drops one frame", par, "        cursor = f\n", "        cursor = f + 1\n"),
 ("M3 adopt chunk at its bound unverified", par, "        f = _find_sync(owner, cand, sync_frames, cursor)\n        while f is None and not owner.eof and owner.hi < cand.hi:", "        f = cand.start if cand.hi > cand.start else None\n        while f is None and not owner.eof and owner.hi < cand.hi:"),
 ("M4 never extend the owner", par, "        while f is None and not owner.eof and owner.hi < cand.hi:", "        while False:"),
 ("M5 digest ignores the frame", par, "    h.update(zlib.crc32(np.ascontiguousarray(frame[::4, ::4]).tobytes()).to_bytes(4, \"little\"))\n", ""),
 ("M6 digest ignores presence", par, "for v in (p.x, p.y, p.z, p.visibility, p.presence):", "for v in (p.x, p.y, p.z, p.visibility):"),
 ("M7 replay timestamp drift (estimate_video)", est, "                timestamp_ms = n * (1000.0 / fps)\n", "                timestamp_ms = n * (1001.0 / fps)\n"),
 ("M8 replay timestamp drift (candidates)", est, "self._points_to_skeleton(points, h, w, n, n * (1000.0 / fps)) for points in poses]", "self._points_to_skeleton(points, h, w, n, n * (1001.0 / fps)) for points in poses]"),
 ("M9 flag ignored (always sequential)", est, "        if workers <= 1:\n            return None\n", "        if workers <= 99:\n            return None\n"),
 ("M11 swallow worker failure silently into empty result", est, "            logger.exception(\"Parallel pose failed, running sequentially\")\n            return None\n", "            return [], 30.0\n"),
]
def run():
    r = subprocess.run([PY, "-m", "pytest", "tests/test_lifting/test_pose_parallel.py", "-q", "-p", "no:cacheprovider", "--no-header", "-k", "not real_video"],
                       cwd=root, env={**os.environ, "PYTHONPATH": root, "MPLBACKEND": "Agg"}, capture_output=True, text=True)
    failed = sorted(l.split("::")[-1].split(" ")[0] for l in r.stdout.splitlines() if l.startswith("FAILED"))
    return r.returncode, failed or [l for l in r.stdout.splitlines() if " passed" in l]
print("baseline", run())
for name, path, old, new in muts:
    orig = open(path).read()
    assert orig.count(old) == 1, (name, orig.count(old))
    open(path, "w").write(orig.replace(old, new))
    assert open(path).read() != orig
    rc, tail = run()
    open(path, "w").write(orig)
    assert open(path).read() == orig
    print(("KILLED " if rc != 0 else "SURVIVED ") + name, tail)
print("restored baseline", run())
