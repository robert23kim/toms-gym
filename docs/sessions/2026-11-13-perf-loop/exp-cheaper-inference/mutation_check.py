"""Mutation check for tests/test_lifting/test_pose_options.py. Run from the engine worktree with no
other job using it. Bytecode caching is off: a same-size, same-second restore leaves a stale .pyc
that makes the NEXT mutation look killed (seen on the first pass, M2)."""
import glob, os, subprocess
PY = "/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python"
E, P = "src/lifting/pose/estimator.py", "src/lifting/pipeline.py"
MUT = [
    ("M1 default num_poses 5->1", E, "DEFAULT_NUM_POSES = 5", "DEFAULT_NUM_POSES = 1", 1),
    ("M2 pipeline drops options", P, "PoseEstimator(**resolve_pose_options(lift_type))", "PoseEstimator()", 1),
    ("M3 per-lift env ignored", E, 'raw = os.environ.get(f"{env}_{lift_type.upper()}")', "raw = None", 1),
    ("M4 num_poses not passed to landmarker", E, "num_poses=num_poses,", "num_poses=5,", 1),
    ("M5 stride ignored", E, "if frame_number % self._frame_stride:", "if False:", 2),
    ("M6 resize skipped", E, "if self._max_side and max(h, w) > self._max_side:", "if False:", 1),
    ("M7 interpolation weight zero", E, "t = (i - lo) / stride if hi < n else 0.0", "t = 0.0", 1),
    ("M8 invalid value accepted", E, "if value is None or (value < minimum and value != default):", "if value is None:", 1),
    ("M9 landmarks scaled by the resized frame", E, "        h, w = frame.shape[:2]\n        results = self._detect(frame, timestamp_ms)\n\n        if not results.pose_landmarks or len", "        results = self._detect(frame, timestamp_ms)\n        h, w = (360, 640)\n\n        if not results.pose_landmarks or len", 1),
]


def run():
    for f in glob.glob("src/lifting/**/__pycache__/*.pyc", recursive=True):
        os.remove(f)
    r = subprocess.run([PY, "-B", "-m", "pytest", "tests/test_lifting/test_pose_options.py", "-q", "-p", "no:cacheprovider", "--no-header"],
                       capture_output=True, text=True,
                       env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"})
    return r.returncode, [l.split("::", 1)[-1] for l in r.stdout.splitlines() if l.startswith("FAILED")], r.stdout.strip().splitlines()[-1]


print("clean:", run())
for name, path, old, new, count in MUT:
    orig = open(path).read()
    assert orig.count(old) == count, (name, orig.count(old))
    mutated = orig.replace(old, new)
    open(path, "w").write(mutated)
    assert open(path).read() == mutated and mutated != orig
    try:
        rc, failed, last = run()
    finally:
        open(path, "w").write(orig)
    assert open(path).read() == orig
    print("KILLED" if rc != 0 else "SURVIVED", "|", name, "|", failed)
print("clean after:", run())
