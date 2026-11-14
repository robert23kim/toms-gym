import json, os, subprocess, tempfile, glob
from flask import Flask, jsonify, request
from google.cloud import storage
app = Flask(__name__)
BUCKET = os.environ["GCS_BUCKET_NAME"]

def fetch(obj, d):
    p = os.path.join(d, os.path.basename(obj)); storage.Client().bucket(BUCKET).blob(obj).download_to_filename(p); return p

@app.route("/health")
def health(): return jsonify(ok=True)

@app.route("/info")
def info():
    def rd(p):
        try: return open(p).read().strip()
        except Exception as e: return str(e)
    models = sorted({l.split(":", 1)[1].strip() for l in rd("/proc/cpuinfo").splitlines() if l.startswith("model name")})
    return jsonify(cpu_count=os.cpu_count(), affinity=len(os.sched_getaffinity(0)), models=models,
                   cpu_max=rd("/sys/fs/cgroup/cpu.max"), cpu_stat=rd("/sys/fs/cgroup/cpu.stat"),
                   flags_avx=[f for f in ("avx2", "avx512f", "fma") if f in rd("/proc/cpuinfo")], uname=os.uname().release)

@app.route("/profile", methods=["POST"])
def profile():
    d = request.get_json(); tmp = tempfile.mkdtemp(); f = fetch(d["object"], tmp); out = os.path.join(tmp, "out")
    p = subprocess.run(["python", "/app/prof/profile_analyze.py", "/app", f, out], capture_output=True, text=True, timeout=850)
    files = glob.glob(os.path.join(out, "*.profile.json"))
    res = json.load(open(files[0])) if files else None
    return jsonify(rc=p.returncode, result=res, stderr_tail=p.stderr[-1500:])

@app.route("/numposes", methods=["POST"])
def numposes():
    d = request.get_json(); tmp = tempfile.mkdtemp(); f = fetch(d["object"], tmp)
    p = subprocess.run(["python", "/app/prof/numposes.py", "/app/src/lifting/pose/.model_cache/pose_landmarker_full.task", f, str(d.get("frames", 600))],
                       capture_output=True, text=True, timeout=850)
    return jsonify(rc=p.returncode, out=p.stdout[-3000:], err=p.stderr[-800:])
