"""Run one engine configuration on the three annotated videos into $EI_SCRATCH/runs/<config>/.
usage: run_engine.py <config> <old|new> [extra flags...] [-- stems...]
Configs used in this loop:
  before      old   --simple-detect                       (what the service runs)
  before_yolo old   --simple-detect --yolo
  after_*     new   --simple-detect --yolo --sam-lane ... (the new pass)
"""
import subprocess
import sys
import time

import common as C


def run(config, which, flags, stems):
    engine = C.OLD_ENGINE if which == "old" else C.NEW_ENGINE
    out = C.RUNS / config
    out.mkdir(parents=True, exist_ok=True)
    for stem in stems:
        video = engine / "videos/input" / f"{stem}.mp4"
        cmd = [str(C.PY), "-m", "scripts.debug_ball_motion", str(video), str(out / f"{stem}.mp4"),
               "--output-summary", str(out / f"{stem}_summary.json"), *flags]
        t0 = time.time()
        with open(out / f"{stem}.log", "w") as fh:
            rc = subprocess.run(cmd, cwd=engine, stdout=fh, stderr=subprocess.STDOUT).returncode
        print(f"{config} {stem}: rc {rc} in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    config, which = sys.argv[1], sys.argv[2]
    rest = sys.argv[3:]
    stems = C.STEMS
    if "--" in rest:
        i = rest.index("--")
        stems = rest[i + 1:] or C.STEMS
        rest = rest[:i]
    run(config, which, rest, stems)
