"""Stage profile of analyze_lift on base code (perf_counter wrappers, no source edits)."""
import json, os, sys, time, shutil, tempfile, collections
def main():
    global T, N, ctx, _VW, _ov
    wt = os.path.realpath(sys.argv[1]); fixture = sys.argv[2]; out = sys.argv[3]
    sys.path.insert(0, wt)
    import cv2
    T = collections.defaultdict(float); N = collections.defaultdict(int)
    def add(k, dt): T[k] += dt; N[k] += 1
    ctx = ["other"]  # current phase label

    class CapProxy:
        def __init__(self, cap): self._c = cap
        def read(self):
            t = time.perf_counter(); r = self._c.read(); add(f"decode[{ctx[0]}]", time.perf_counter() - t); return r
        def grab(self):
            t = time.perf_counter(); r = self._c.grab(); add(f"decode[{ctx[0]}]", time.perf_counter() - t); return r
        def set(self, *a):
            t = time.perf_counter(); r = self._c.set(*a); add(f"seek[{ctx[0]}]", time.perf_counter() - t); return r
        def __getattr__(self, n): return getattr(self._c, n)

    class WriterProxy:
        def __init__(self, *a, **k): self._w = _VW(*a, **k)
        def write(self, f):
            t = time.perf_counter(); self._w.write(f); add(f"encode_write[{ctx[0]}]", time.perf_counter() - t)
        def release(self):
            t = time.perf_counter(); self._w.release(); add(f"encode_write[{ctx[0]}]", time.perf_counter() - t)
        def __getattr__(self, n): return getattr(self._w, n)
    _VW = cv2.VideoWriter

    from src.bowling.video import io as vio
    _ov = vio.open_video
    def open_video(p): return CapProxy(_ov(p))
    from src.lifting import pipeline, plank_analyzer
    from src.lifting.pose import estimator as est
    from src.lifting.pose import tracking
    for m in (pipeline, est, plank_analyzer, vio):
        if hasattr(m, "open_video"): m.open_video = open_video
    pipeline.cv2.VideoWriter = WriterProxy  # same cv2 module everywhere

    class LmProxy:
        def __init__(self, lm): self._l = lm
        def detect_for_video(self, img, ts):
            t = time.perf_counter(); r = self._l.detect_for_video(img, ts); add("pose_inference", time.perf_counter() - t)
            N["poses_returned"] += len(r.pose_landmarks or []); return r
        def detect(self, img):
            t = time.perf_counter(); r = self._l.detect(img); add("pose_inference", time.perf_counter() - t); return r
        def close(self): return self._l.close()
    _init = est.PoseEstimator.__init__
    def init(self, *a, **k):
        t = time.perf_counter(); _init(self, *a, **k); add("model_init", time.perf_counter() - t)
        self._landmarker = LmProxy(self._landmarker)
    est.PoseEstimator.__init__ = init
    _mpl = plank_analyzer._mp_landmarker
    def mpl(p):
        t = time.perf_counter(); r = _mpl(p); add("model_init", time.perf_counter() - t); return LmProxy(r)
    plank_analyzer._mp_landmarker = mpl

    def timed(mod, name, key, phase=None):
        fn = getattr(mod, name)
        def w(*a, **k):
            prev = ctx[0]
            if phase: ctx[0] = phase
            t = time.perf_counter()
            try: return fn(*a, **k)
            finally:
                add(key, time.perf_counter() - t); ctx[0] = prev
        setattr(mod, name, w)
    timed(est.PoseEstimator, "estimate_video", "pose_pass_total", "pose")
    timed(est.PoseEstimator, "estimate_video_candidates", "pose_pass_total", "pose")
    timed(tracking, "track_person", "track_person")
    timed(tracking, "clean_pose_track", "clean_pose_track")
    timed(pipeline, "detect_camera_view", "camera_view")
    timed(pipeline, "detect_active_arm", "active_arm")
    timed(pipeline, "analyze_from_skeletons", "rep_detect_score")
    timed(pipeline, "_generate_alerts", "alerts")
    timed(pipeline, "_render_output_video", "render_video_total", "render_video")
    timed(pipeline, "_render_metric_clips", "render_clips_total", "render_clips")
    timed(pipeline, "render_skeleton", "draw_skeleton")
    timed(plank_analyzer, "_extract_frames_parallel", "plank_pose_parallel_total", "plank_pose")
    timed(plank_analyzer, "_render_output", "plank_render_total", "plank_render")
    timed(plank_analyzer, "analyze_plank", "plank_analyze_total", "plank")
    import mediapipe as mp
    _cvt = cv2.cvtColor

    tmp = tempfile.mkdtemp(prefix="prof_"); inp = os.path.join(tmp, "input.mp4"); shutil.copyfile(fixture, inp)
    name = os.path.splitext(os.path.basename(fixture))[0]; lift = name.split("_")[0]
    cap = cv2.VideoCapture(inp); meta = dict(frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), fps=cap.get(cv2.CAP_PROP_FPS),
        w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))); cap.release()
    t0 = time.perf_counter()
    a = pipeline.analyze_lift(inp, output_video=os.path.join(tmp, "annotated.mp4"), camera_view_override=None, no_overlay=False, lift_type=lift)
    total = time.perf_counter() - t0
    from src.lifting.summary import build_lift_summary
    rep = build_lift_summary(a)
    nclips = len([f for f in os.listdir(os.path.join(tmp, "clips"))]) if os.path.isdir(os.path.join(tmp, "clips")) else 0
    shutil.rmtree(tmp, ignore_errors=True)
    res = dict(fixture=name, meta=meta, analyze_total_s=round(total, 2), clips_written=nclips,
               total_reps=rep.get("total_reps"), total_in_plank_s=rep.get("total_in_plank_s"),
               stages={k: round(v, 2) for k, v in sorted(T.items())}, counts=dict(N))
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, f"{name}.profile.json"), "w"), indent=2); print(json.dumps(res))

if __name__ == '__main__':
    main()
