# Analysis Engine Re-architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Remove the subprocess-per-request + stdout-regex design from `bowling-service` and replace the toms_gym backend's daemon-thread pollers with Cloud Tasks push dispatch, so analyses run warm, return structured results, and get retries/backpressure from managed infrastructure.

**Architecture:** Two repos. In `bowling-app/analysis-engine`, the Flask service calls the lifting pipeline in-process (shared summary serializer) and reads bowling metrics from a summary JSON instead of regex-scraping stdout. In `toms_gym/backend`, job creation enqueues a Cloud Tasks HTTP task targeting a new `/jobs/<kind>/<result_id>` handler on the backend itself; the handler runs the existing `_process_job`/`process_bowling_video` functions. The DB status contract (`LiftingResult`/`BowlingResult` rows with `queued/processing/completed/failed`) is unchanged, so the frontend polling endpoints keep working. A `ANALYSIS_DISPATCH_MODE` env flag gates cutover; pollers are deleted after a soak period.

**Tech Stack:** Python 3.10/Flask/gunicorn (engine), Flask + SQLAlchemy text() (backend), google-cloud-tasks, MediaPipe PoseLandmarker, Cloud Run, GCS.

## Global Constraints

- **Prerequisite:** commit/land the currently-uncommitted work on branch `plank/poller-timeouts` (both repos have dirty trees). Each task below assumes a clean tree and its own feature branch or continuation branch.
- Engine repo: `/Users/toka/code/bowling-app/analysis-engine`. Tests: `.venv/bin/pytest tests/ -v -m "not slow"` from repo root (fast suite, ~40s). Never break it.
- Backend repo: `/Users/toka/code/toms_gym/backend`. The main pytest suite is DB-bound (conftest imports the app and needs Dockerized Postgres). New unit tests in this plan run with `venv/bin/python -m pytest --noconftest <file> -v` so they stay DB-free; run `./run_tests.sh` once before the deploy task.
- DB status values (`queued`, `processing`, `completed`, `failed`) and the JSON response shapes of `/lifting/result/*`, `/bowling/*` endpoints must not change.
- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `test(scope):`, `chore(scope):`.
- Deploys: engine via `./deploy.sh` (engine repo), backend via `python3 deploy.py --backend-only --skip-iam` (toms_gym root). Production backend URL: `https://my-python-backend-quyiiugyoq-ue.a.run.app`.
- Cloud Run constraint: engine stays `--concurrency=1 --max-instances=3`; the Cloud Tasks queue must cap concurrent dispatches at 3 to match.

---

### Task 1: Shared lift-summary serializer (`build_lift_summary`)

The CLI (`scripts/analyze_lift.py`) builds the summary dict inline; the service needs the same shape without a subprocess. Extract it.

**Files:**
- Create: `/Users/toka/code/bowling-app/analysis-engine/src/lifting/summary.py`
- Modify: `/Users/toka/code/bowling-app/analysis-engine/scripts/analyze_lift.py` (lines 84–171)
- Test: `/Users/toka/code/bowling-app/analysis-engine/tests/test_lift_summary.py`

**Interfaces:**
- Consumes: `LiftAnalysis` (from `src.lifting.pose.data_types`) — has `.report` (LiftReport) and `.plank_result` (dict | None).
- Produces: `build_lift_summary(analysis: LiftAnalysis) -> dict` — plank shape `{"lift_type": "plank", **plank_result}`; rep-based shape matches the CLI's existing JSON exactly (keys: `camera_view`, `active_arm`, `total_reps`, `overall_grade`, `overall_score`, `lift_type`, `rep_metrics`, `insights`). Task 3 imports this.

- [x] **Step 1: Write the failing test**

```python
# tests/test_lift_summary.py
"""build_lift_summary serializes a LiftAnalysis to the service/CLI JSON shape."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lifting.summary import build_lift_summary


def _plank_analysis():
    return SimpleNamespace(
        report=SimpleNamespace(lift_type="plank"),
        plank_result={
            "total_in_plank_s": 5.5, "longest_run_s": 5.5,
            "plank_type": "forearm", "overall_form_score": 0.85,
            "pose_detection_rate": 0.97,
        },
    )


def _rep_analysis():
    metric = SimpleNamespace(
        key="rom", label="Range of motion", value=95.0, unit="%",
        target=90.0, status="good", description=None,
        best_time_s=None, worst_time_s=None, clip_url="/tmp/clips/rom.mp4",
    )
    rep = SimpleNamespace(
        rep_number=1, elbow_angle_range=(40.0, 160.0), tempo_ratio=1.1,
        elbow_drift_pct=88.0, body_sway_pct=92.0, momentum_score=90.0,
        rom_score=95.0, shoulder_flexion_avg=15.0, form_grade="A",
        form_score=93.0, metrics=[metric],
    )
    report = SimpleNamespace(
        lift_type="bicep_curl", camera_view="side", active_arm="left",
        reps=[object()], overall_form_grade="A", overall_form_score=93.0,
        rep_metrics=[rep], insights=["Nice tempo"],
    )
    return SimpleNamespace(report=report, plank_result=None)


def test_plank_summary_flattens_plank_result():
    summary = build_lift_summary(_plank_analysis())
    assert summary["lift_type"] == "plank"
    assert summary["total_in_plank_s"] == 5.5
    assert summary["overall_form_score"] == 0.85


def test_rep_summary_matches_cli_shape():
    summary = build_lift_summary(_rep_analysis())
    assert summary["lift_type"] == "bicep_curl"
    assert summary["total_reps"] == 1
    assert summary["overall_grade"] == "A"
    rm = summary["rep_metrics"][0]
    assert rm["elbow_angle_range"] == [40.0, 160.0]
    assert rm["metrics"][0]["clip_url"] == "/tmp/clips/rom.mp4"
    # Optional keys are omitted when absent, not emitted as null
    assert "description" not in rm["metrics"][0]
    assert "best_time_s" not in rm["metrics"][0]
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/toka/code/bowling-app/analysis-engine && .venv/bin/pytest tests/test_lift_summary.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.lifting.summary'`

- [x] **Step 3: Create `src/lifting/summary.py`**

Copy the dict construction verbatim from `scripts/analyze_lift.py` lines 100 and 135–167 into:

```python
"""Serialize a LiftAnalysis into the JSON summary shape shared by the CLI and the Cloud Run service."""


def build_lift_summary(analysis) -> dict:
    report = analysis.report
    if report.lift_type == "plank" and analysis.plank_result is not None:
        return {"lift_type": "plank", **analysis.plank_result}
    return {
        "camera_view": report.camera_view,
        "active_arm": report.active_arm,
        "total_reps": len(report.reps),
        "overall_grade": report.overall_form_grade,
        "overall_score": report.overall_form_score,
        "lift_type": report.lift_type,
        "rep_metrics": [
            {
                "rep_number": rm.rep_number,
                "elbow_angle_range": list(rm.elbow_angle_range),
                "tempo_ratio": rm.tempo_ratio,
                "elbow_drift_pct": rm.elbow_drift_pct,
                "body_sway_pct": rm.body_sway_pct,
                "momentum_score": rm.momentum_score,
                "rom_score": rm.rom_score,
                "shoulder_flexion_avg": rm.shoulder_flexion_avg,
                "form_grade": rm.form_grade,
                "form_score": rm.form_score,
                "metrics": [
                    {"key": m.key, "label": m.label, "value": m.value,
                     "unit": m.unit, "target": m.target, "status": m.status,
                     **({"description": m.description} if m.description else {}),
                     **({"best_time_s": m.best_time_s} if m.best_time_s is not None else {}),
                     **({"worst_time_s": m.worst_time_s} if m.worst_time_s is not None else {}),
                     **({"clip_url": m.clip_url} if m.clip_url else {})}
                    for m in rm.metrics
                ],
            }
            for rm in report.rep_metrics
        ],
        "insights": report.insights,
    }
```

(No type annotation on `analysis` — plank path is duck-typed the same way `scripts/analyze_lift.py` treats it, and importing `LiftAnalysis` would pull cv2 into this leaf module.)

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_lift_summary.py -v`
Expected: 2 PASSED

- [x] **Step 5: Use it from the CLI**

In `scripts/analyze_lift.py`: add `from src.lifting.summary import build_lift_summary` next to the existing `from src.lifting.pipeline import analyze_lift` import. Replace the plank-branch summary construction (line 100: `summary = {"lift_type": "plank", **pr}`) with `summary = build_lift_summary(analysis)`, and replace the rep-branch `summary = { ... }` literal (lines 135–167) with `summary = build_lift_summary(analysis)`. Keep all the `print(...)` reporting untouched.

- [x] **Step 6: Run the fast suite**

Run: `.venv/bin/pytest tests/ -v -m "not slow"`
Expected: all pass (same count as before this task, +2).

- [x] **Step 7: Commit**

```bash
git add src/lifting/summary.py scripts/analyze_lift.py tests/test_lift_summary.py
git commit -m "refactor(lifting): extract build_lift_summary shared by CLI and service"
```

---

### Task 2: Bowling pipeline writes a machine-readable summary JSON

`service/app.py` currently regex-scrapes bowling metrics from stdout (`_parse_detection_rate`, `Final board:` patterns). Give `scripts/debug_ball_motion.py` an `--output-summary` flag that writes the same numbers as JSON.

**Files:**
- Modify: `/Users/toka/code/bowling-app/analysis-engine/scripts/debug_ball_motion.py` (argparse block starting line 50; end of `main()` near line 990)
- Test: `/Users/toka/code/bowling-app/analysis-engine/tests/test_service_summary.py`

**Interfaces:**
- Produces: `_write_service_summary(path, total_frames, detections, birds_eye_renderer, active_lane) -> None` writing JSON `{"total_frames": int, "detections": int, "detection_rate": float|None, "final_board": float|None}`. Task 4 reads this file. (`lane_edges` intentionally stays on the existing stdout-regex path — see Task 4 fallback.)

- [x] **Step 1: Write the failing test**

```python
# tests/test_service_summary.py
"""_write_service_summary emits the metrics service/app.py needs, as JSON."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.debug_ball_motion import _write_service_summary


class FakeRenderer:
    def get_trail_summary(self):
        return {"final_board": 17.5, "trail_points": 42}


def test_writes_detection_stats_and_final_board(tmp_path):
    out = tmp_path / "summary.json"
    _write_service_summary(str(out), total_frames=120, detections=90,
                           birds_eye_renderer=FakeRenderer(), active_lane=None)
    data = json.loads(out.read_text())
    assert data["total_frames"] == 120
    assert data["detections"] == 90
    assert data["detection_rate"] == 75.0
    assert data["final_board"] == 17.5


def test_handles_missing_renderer_and_zero_frames(tmp_path):
    out = tmp_path / "summary.json"
    _write_service_summary(str(out), total_frames=0, detections=0,
                           birds_eye_renderer=None, active_lane=None)
    data = json.loads(out.read_text())
    assert data["detection_rate"] is None
    assert data["final_board"] is None
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_service_summary.py -v`
Expected: FAIL with `ImportError: cannot import name '_write_service_summary'`

- [x] **Step 3: Implement**

In `scripts/debug_ball_motion.py`, add a module-level helper (place it next to `_write_telemetry`, around line 180):

```python
def _write_service_summary(path, total_frames, detections, birds_eye_renderer, active_lane):
    """Write machine-readable detection metrics for service/app.py (replaces stdout regex)."""
    import json
    data = {
        "total_frames": total_frames,
        "detections": detections,
        "detection_rate": round(detections / total_frames * 100, 1) if total_frames else None,
        "final_board": None,
    }
    if birds_eye_renderer is not None:
        trail = birds_eye_renderer.get_trail_summary()
        if trail.get("final_board") is not None:
            data["final_board"] = float(trail["final_board"])
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
```

Add the CLI flag in the argparse block (after the existing `output_video` positional, line ~51):

```python
    parser.add_argument(
        "--output-summary",
        help="Write machine-readable detection summary JSON to this path",
    )
```

At the end of `main()`, immediately after the trajectory-PNG block (after line ~991, where `total_frames`, `detections`, `birds_eye_renderer`, and `active_lane` are all still in scope):

```python
    if args.output_summary:
        _write_service_summary(args.output_summary, total_frames, detections,
                               birds_eye_renderer, active_lane)
        print(f"Service summary written to: {args.output_summary}")
```

- [x] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_service_summary.py -v` → 2 PASSED, then `.venv/bin/pytest tests/ -v -m "not slow"` → all pass.

- [x] **Step 5: End-to-end sanity check on the fixture video**

Run: `.venv/bin/python -m scripts.debug_ball_motion sample_input.mp4 /tmp/debug.mp4 --simple-detect --output-summary /tmp/summary.json && cat /tmp/summary.json`
Expected: JSON with non-null `detection_rate` (fixture historically ~100%) and `final_board`.

- [x] **Step 6: Commit**

```bash
git add scripts/debug_ball_motion.py tests/test_service_summary.py
git commit -m "feat(bowling): add --output-summary JSON so the service stops scraping stdout"
```

---

### Task 3: Service runs lifting analysis in-process (no subprocess)

**Files:**
- Modify: `/Users/toka/code/bowling-app/analysis-engine/service/app.py` (`analyze_lift` route, lines 252–393)
- Test: `/Users/toka/code/bowling-app/analysis-engine/tests/test_service_app.py`

**Interfaces:**
- Consumes: `analyze_lift(video_path, output_video=, camera_view_override=, no_overlay=, lift_type=) -> LiftAnalysis` from `src.lifting.pipeline`; `build_lift_summary` from Task 1.
- Produces: unchanged HTTP contract — `POST /analyze-lift` returns `{"annotated_video_url", "summary_url", "report", "processing_time_s"}`.

- [x] **Step 1: Write the failing test**

```python
# tests/test_service_app.py
"""POST /analyze-lift runs the pipeline in-process and returns structured results."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from service import app as service_app


class FakeBlob:
    def __init__(self, path):
        self.path = path
    def upload_from_filename(self, filename, **kwargs):
        pass


class FakeBucket:
    def __init__(self):
        self.blobs = {}
    def blob(self, path):
        b = FakeBlob(path)
        self.blobs[path] = b
        return b


class FakePlankAnalysis:
    class _Report:
        lift_type = "plank"
    report = _Report()
    plank_result = {
        "total_in_plank_s": 5.5, "longest_run_s": 5.5, "plank_type": "forearm",
        "overall_form_score": 0.85, "pose_detection_rate": 0.97,
    }


@pytest.fixture
def client(monkeypatch):
    bucket = FakeBucket()

    def fake_download(video_url, dest_path):
        Path(dest_path).write_bytes(b"fake video bytes")
        return bucket

    def fake_analyze(video_path, output_video=None, camera_view_override=None,
                     no_overlay=False, lift_type="bicep_curl"):
        Path(output_video).write_bytes(b"fake annotated video")
        return FakePlankAnalysis()

    monkeypatch.setattr(service_app, "GCS_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(service_app, "_download_from_gcs", fake_download)
    monkeypatch.setattr("src.lifting.pipeline.analyze_lift", fake_analyze)
    service_app.app.config["TESTING"] = True
    return service_app.app.test_client(), bucket


def test_analyze_lift_returns_structured_plank_report(client):
    c, bucket = client
    resp = c.post("/analyze-lift", json={
        "video_url": "https://storage.googleapis.com/test-bucket/lifting/a1/input.mp4",
        "attempt_id": "attempt-1",
        "lift_type": "plank",
    })
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["report"]["lift_type"] == "plank"
    assert body["report"]["total_in_plank_s"] == 5.5
    assert "lifting/attempt-1/annotated.mp4" in bucket.blobs
    assert "lifting/attempt-1/summary.json" in bucket.blobs


def test_analyze_lift_pipeline_error_returns_500(client, monkeypatch):
    c, _ = client
    def boom(*args, **kwargs):
        raise RuntimeError("pose model exploded")
    monkeypatch.setattr("src.lifting.pipeline.analyze_lift", boom)
    resp = c.post("/analyze-lift", json={
        "video_url": "https://storage.googleapis.com/test-bucket/x.mp4",
        "attempt_id": "attempt-2",
    })
    assert resp.status_code == 500
    assert "pose model exploded" in resp.get_json()["error"]
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_service_app.py -v`
Expected: FAIL — the current implementation shells out to `python -m scripts.analyze_lift`, which "succeeds" or fails differently; the structured-report assertions fail. (If the subprocess path errors first, that also counts as red.)

- [x] **Step 3: Replace the subprocess block**

In `service/app.py` `analyze_lift()` route, replace lines 294–333 (the `cmd = [...]` build, `subprocess.run`, stdout/stderr logging, returncode check, and summary-file read) with:

```python
        # Run the lifting pipeline in-process. No subprocess: imports and model
        # download-cache stay warm across requests (concurrency=1 makes this safe),
        # failures carry real tracebacks, and results are structured objects.
        from src.lifting import pipeline as lifting_pipeline
        from src.lifting.summary import build_lift_summary

        camera_override = camera_view if camera_view and camera_view != 'auto' else None
        analysis = lifting_pipeline.analyze_lift(
            input_path,
            output_video=output_path,
            camera_view_override=camera_override,
            no_overlay=bool(no_overlay),
            lift_type=lift_type or 'bicep_curl',
        )
        report = build_lift_summary(analysis)
        with open(summary_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
```

Notes for the implementer:
- Import via `from src.lifting import pipeline as lifting_pipeline` and call the attribute (not `from ... import analyze_lift`) so tests can monkeypatch `src.lifting.pipeline.analyze_lift`. **This attribute-call form is required for the test to pass.**
- The rest of the route (H.264 re-encode, clip upload loop reading `report['rep_metrics']`, summary upload, response JSON) is unchanged — `report` is now a plain dict exactly like the old `json.load` produced.
- The subprocess's 540s timeout is gone; gunicorn's `--timeout 600` (Dockerfile line 41) is now the only watchdog and still kills a stuck worker. Add a comment saying exactly that where the timeout comment used to be.

- [x] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_service_app.py tests/test_lift_summary.py -v` → PASSED, then the fast suite `.venv/bin/pytest tests/ -v -m "not slow"`.

- [x] **Step 5: Real-video smoke test (slow, local)**

Run: `GCS_BUCKET_NAME= MPLBACKEND=Agg .venv/bin/python -c "
from src.lifting.pipeline import analyze_lift
from src.lifting.summary import build_lift_summary
a = analyze_lift('test_video_plank_10s.mp4', output_video='/tmp/plank_annotated.mp4', lift_type='plank')
print(build_lift_summary(a))
"`
Expected: dict printed with `total_in_plank_s` in the 5.1–6.1s band (matches `test_plank_analyzer.py` sentinels).

- [x] **Step 6: Commit**

```bash
git add service/app.py tests/test_service_app.py
git commit -m "refactor(service): run lifting analysis in-process instead of subprocess"
```

---

### Task 4: Service reads bowling summary JSON (regex kept as fallback)

**Files:**
- Modify: `/Users/toka/code/bowling-app/analysis-engine/service/app.py` (`analyze` route, lines 137–237)
- Test: extend `/Users/toka/code/bowling-app/analysis-engine/tests/test_service_app.py`

**Interfaces:**
- Consumes: the summary JSON from Task 2 (`{"total_frames", "detections", "detection_rate", "final_board"}`).
- Produces: unchanged `POST /analyze` response shape.

- [x] **Step 1: Write the failing test** (append to `tests/test_service_app.py`)

```python
def test_analyze_bowling_prefers_summary_json(client, monkeypatch):
    c, bucket = client
    import json as jsonlib
    import subprocess as real_subprocess

    def fake_run(cmd, **kwargs):
        # The bowling pipeline is still a subprocess; simulate it writing outputs.
        if cmd[0] == 'ffmpeg':
            return real_subprocess.CompletedProcess(cmd, 1, stdout='', stderr='no real video')
        out_idx = cmd.index('--output-summary') + 1
        Path(cmd[out_idx]).write_text(jsonlib.dumps(
            {"total_frames": 100, "detections": 97, "detection_rate": 97.0, "final_board": 17.5}))
        # output video positional arg is cmd[3] (python -m scripts.debug_ball_motion IN OUT ...)
        Path(cmd[4]).write_bytes(b"fake debug video")
        return real_subprocess.CompletedProcess(cmd, 0, stdout='no parseable metrics here', stderr='')

    monkeypatch.setattr(service_app.subprocess, "run", fake_run)
    resp = c.post("/analyze", json={
        "video_url": "https://storage.googleapis.com/test-bucket/bowling/b1/input.mp4",
        "attempt_id": "b1",
    })
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["detection_rate"] == 97.0
    assert body["board_at_pins"] == 17.5
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_service_app.py::test_analyze_bowling_prefers_summary_json -v`
Expected: FAIL — `--output-summary` is not in `cmd`, so `cmd.index` raises `ValueError` (the route doesn't pass the flag yet).

- [x] **Step 3: Implement**

In the `analyze()` route:
1. After `output_path = ...` (line 141) add `summary_path = os.path.join(tmp_dir, 'summary.json')`.
2. Extend the command (after `'--simple-detect'`, line 157): `cmd.extend(['--output-summary', summary_path])`.
3. Replace the metric-parsing block (lines 178–194) with:

```python
        # Prefer the structured summary written by the pipeline; fall back to the
        # legacy stdout regexes for any value the summary doesn't carry (lane_edges
        # is still stdout-only).
        summary = {}
        if os.path.isfile(summary_path):
            with open(summary_path) as f:
                summary = json.load(f)

        detection_rate = summary.get('detection_rate')
        if detection_rate is None:
            detection_rate = _parse_detection_rate(stdout)
        board_at_pins = summary.get('final_board')
        if board_at_pins is None:
            board_at_pins = _parse_metric(stdout, r'board_at_pins[=:]\s*([\d.]+)')
        if board_at_pins is None:
            board_at_pins = _parse_metric(stdout, r'Final board:\s*([\d.]+)')
        entry_board = _parse_metric(stdout, r'entry_board[=:]\s*([\d.]+)')

        detected_lane_edges = None
        le_match = re.search(r'lane_edges=(\{.*\})', stdout)
        if le_match:
            try:
                detected_lane_edges = json.loads(le_match.group(1))
            except json.JSONDecodeError:
                logger.warning("Failed to parse lane_edges from stdout")
```

- [x] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_service_app.py -v` → all PASSED; then the fast suite.

- [x] **Step 5: Commit**

```bash
git add service/app.py tests/test_service_app.py
git commit -m "feat(service): read bowling metrics from summary JSON with stdout-regex fallback"
```

---

### Task 5: GPU readiness — `POSE_DELEGATE` env flag

Centralize delegate selection so flipping to GPU (L4 quota pending) is a deploy flag, not a code change. CPU remains the default and behavior is bit-identical.

**Files:**
- Modify: `/Users/toka/code/bowling-app/analysis-engine/src/lifting/pose/estimator.py` (PoseLandmarker options, lines 124–136)
- Modify: `/Users/toka/code/bowling-app/analysis-engine/src/lifting/plank_analyzer.py` (its own PoseLandmarker options — find with the grep in Step 1)
- Test: `/Users/toka/code/bowling-app/analysis-engine/tests/test_pose_delegate.py`

**Interfaces:**
- Produces: `resolve_pose_delegate() -> mp.tasks.BaseOptions.Delegate` in `src/lifting/pose/estimator.py`, reading env `POSE_DELEGATE` (`cpu` default | `gpu`). Both landmarker construction sites call it.

- [x] **Step 1: Locate every landmarker construction site**

Run: `grep -rn "BaseOptions\|create_from_options" src/lifting/ | grep -v test`
Expected: hits in `estimator.py` (~line 129–136) and `plank_analyzer.py`. If `onnx_plank_pose.py`/`cigpose_backend.py` also hit, leave those alone (dead-end backends).

- [x] **Step 2: Write the failing test**

```python
# tests/test_pose_delegate.py
"""POSE_DELEGATE env selects the MediaPipe delegate; default stays CPU."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import mediapipe as mp

from src.lifting.pose.estimator import resolve_pose_delegate


def test_default_is_cpu(monkeypatch):
    monkeypatch.delenv("POSE_DELEGATE", raising=False)
    assert resolve_pose_delegate() == mp.tasks.BaseOptions.Delegate.CPU


def test_gpu_when_requested(monkeypatch):
    monkeypatch.setenv("POSE_DELEGATE", "GPU")
    assert resolve_pose_delegate() == mp.tasks.BaseOptions.Delegate.GPU
```

- [x] **Step 3: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_pose_delegate.py -v`
Expected: FAIL with `ImportError: cannot import name 'resolve_pose_delegate'`

- [x] **Step 4: Implement**

In `estimator.py`, add near the top (module already imports `os`):

```python
def resolve_pose_delegate():
    """MediaPipe inference delegate from env: POSE_DELEGATE=cpu (default) | gpu."""
    import mediapipe as mp
    if os.environ.get("POSE_DELEGATE", "cpu").lower() == "gpu":
        return mp.tasks.BaseOptions.Delegate.GPU
    return mp.tasks.BaseOptions.Delegate.CPU
```

Then in both construction sites (estimator `__init__` ~line 129 and the plank analyzer's options), add `delegate=resolve_pose_delegate()` as a keyword to the existing `mp.tasks.BaseOptions(...)` call (plank_analyzer imports it: `from src.lifting.pose.estimator import resolve_pose_delegate`). Do not change any other option.

- [x] **Step 5: Run tests**

Run: `.venv/bin/pytest tests/test_pose_delegate.py -v` → 2 PASSED, then the fast suite → all pass (CPU default means zero behavior change).

- [x] **Step 6: Commit**

```bash
git add src/lifting/pose/estimator.py src/lifting/plank_analyzer.py tests/test_pose_delegate.py
git commit -m "feat(pose): POSE_DELEGATE env flag for CPU/GPU delegate selection"
```

---

### Task 6: Engine repo hygiene — weights and media out of git

**Files:**
- Modify: `/Users/toka/code/bowling-app/analysis-engine/.gitignore`
- Create: `/Users/toka/code/bowling-app/analysis-engine/scripts/fetch_dev_assets.sh`
- Modify: `/Users/toka/code/bowling-app/analysis-engine/CLAUDE.md` (dev-assets note)

- [x] **Step 1: Upload the assets to GCS before untracking them**

```bash
cd /Users/toka/code/bowling-app/analysis-engine
gsutil -m cp yolov8n.pt yolov8s-worldv2.pt yolov9t.pt yolov10n.pt yolo11n.pt \
  sample_input.mp4 test_video_plank_10s.mp4 20260112_121117.mp4 \
  gs://jtr-lift-u-4ever-cool-bucket/dev-assets/analysis-engine/
```
Expected: 8 uploads complete. (Skip any file `git ls-files` says isn't tracked *and* doesn't exist.)

- [x] **Step 2: Create the fetch script**

```bash
#!/bin/bash
# scripts/fetch_dev_assets.sh — pull model weights and fixture videos that are
# no longer tracked in git (moved to GCS to keep the repo small).
set -euo pipefail
cd "$(dirname "$0")/.."
gsutil -m cp "gs://jtr-lift-u-4ever-cool-bucket/dev-assets/analysis-engine/*" .
```

Run `chmod +x scripts/fetch_dev_assets.sh`.

- [x] **Step 3: Untrack and ignore**

```bash
git rm --cached yolov8n.pt yolov8s-worldv2.pt yolov9t.pt yolov10n.pt yolo11n.pt \
  sample_input.mp4 test_video_plank_10s.mp4 20260112_121117.mp4
cat >> .gitignore <<'EOF'

# Large dev assets — fetch with scripts/fetch_dev_assets.sh
*.pt
/*.mp4
/*.png
/*.jpg
.venv/
bowlingenv/
EOF
```

Then verify nothing needed by the fast suite broke: `.venv/bin/pytest tests/ -v -m "not slow"` (files still exist on disk — only untracked). Add one line to CLAUDE.md under the test-video section: `If fixture videos/weights are missing locally, run scripts/fetch_dev_assets.sh.`

**Do NOT commit or discard the in-flight `src/bowling/` relocation** (`git status` shows `src/detectors/` → `src/bowling/` moves unstaged) — that's Tom's in-progress refactor; leave it and flag it in the task report.

- [x] **Step 4: Commit**

```bash
git add .gitignore scripts/fetch_dev_assets.sh CLAUDE.md
git commit -m "chore(repo): move model weights and fixture videos out of git to GCS"
```

---

### Task 7: Backend Cloud Tasks enqueue service (`analysis_dispatch`)

From here on, repo = `/Users/toka/code/toms_gym/backend`.

**Files:**
- Create: `toms_gym/services/analysis_dispatch.py`
- Modify: `requirements.txt` (add `google-cloud-tasks==2.16.*`)
- Test: `tests/unit/test_analysis_dispatch.py` (new `tests/unit/` dir; run with `--noconftest`)

**Interfaces:**
- Produces: `dispatch_enabled() -> bool` (true iff env `ANALYSIS_DISPATCH_MODE == 'tasks'`) and `enqueue_analysis_job(kind: str, result_id: str) -> None` (kind ∈ `'lifting' | 'bowling'`; no-op when disabled; never raises — logs and swallows enqueue errors so job creation still succeeds and the poller/manual retry can pick it up). Tasks 8–9 consume both.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_analysis_dispatch.py
"""enqueue_analysis_job builds an OIDC HTTP task targeting /jobs/<kind>/<id>."""
import pytest

from toms_gym.services import analysis_dispatch


class FakeTasksClient:
    created = []
    def create_task(self, parent=None, task=None):
        FakeTasksClient.created.append((parent, task))


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("ANALYSIS_DISPATCH_MODE", "tasks")
    monkeypatch.setenv("ANALYSIS_TASKS_QUEUE",
                       "projects/toms-gym/locations/us-east1/queues/analysis-jobs")
    monkeypatch.setenv("TASKS_TARGET_BASE_URL",
                       "https://my-python-backend-quyiiugyoq-ue.a.run.app")
    monkeypatch.setenv("TASKS_SERVICE_ACCOUNT",
                       "toms-gym-service@toms-gym.iam.gserviceaccount.com")
    FakeTasksClient.created = []


def test_noop_when_mode_is_poller(monkeypatch):
    monkeypatch.setenv("ANALYSIS_DISPATCH_MODE", "poller")
    monkeypatch.setattr(analysis_dispatch, "_tasks_client", lambda: FakeTasksClient())
    analysis_dispatch.enqueue_analysis_job("lifting", "r-1")
    assert FakeTasksClient.created == []


def test_enqueues_oidc_http_task(monkeypatch):
    monkeypatch.setattr(analysis_dispatch, "_tasks_client", lambda: FakeTasksClient())
    analysis_dispatch.enqueue_analysis_job("lifting", "r-1")
    (parent, task), = FakeTasksClient.created
    assert parent.endswith("queues/analysis-jobs")
    http = task["http_request"]
    assert http["url"] == ("https://my-python-backend-quyiiugyoq-ue.a.run.app/jobs/lifting/r-1")
    assert http["oidc_token"]["service_account_email"].startswith("toms-gym-service@")
    assert task["dispatch_deadline"]["seconds"] == 900


def test_enqueue_errors_are_swallowed(monkeypatch):
    class Boom:
        def create_task(self, **kwargs):
            raise RuntimeError("tasks API down")
    monkeypatch.setattr(analysis_dispatch, "_tasks_client", lambda: Boom())
    analysis_dispatch.enqueue_analysis_job("bowling", "r-2")  # must not raise
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/toka/code/toms_gym/backend && venv/bin/python -m pytest --noconftest tests/unit/test_analysis_dispatch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'toms_gym.services.analysis_dispatch'`

- [x] **Step 3: Implement**

```python
# toms_gym/services/analysis_dispatch.py
"""Enqueue analysis jobs onto Cloud Tasks.

Replaces the in-process daemon pollers (integrations/lifting_processor.py,
integrations/bowling_processor.py): job creation enqueues an OIDC-authenticated
HTTP task that POSTs back to this backend's /jobs/<kind>/<result_id> handler.
Gated by ANALYSIS_DISPATCH_MODE=tasks so cutover is a config change.
"""
import logging
import os

logger = logging.getLogger(__name__)

# All env reads happen at call time (not import) so tests and Cloud Run
# revisions can flip modes without module reloads.


def dispatch_enabled() -> bool:
    return os.environ.get('ANALYSIS_DISPATCH_MODE', 'poller') == 'tasks'


def _tasks_client():
    from google.cloud import tasks_v2
    return tasks_v2.CloudTasksClient()


def enqueue_analysis_job(kind: str, result_id: str) -> None:
    """kind: 'lifting' | 'bowling'. No-op unless ANALYSIS_DISPATCH_MODE=tasks.

    Never raises: an enqueue failure must not fail the user-facing request
    that created the job row; the row stays 'queued' for manual re-trigger.
    """
    if not dispatch_enabled():
        return
    if kind not in ('lifting', 'bowling'):
        logger.error(f"enqueue_analysis_job: unknown kind {kind!r}")
        return
    try:
        from google.cloud import tasks_v2
        queue = os.environ['ANALYSIS_TASKS_QUEUE']
        base_url = os.environ['TASKS_TARGET_BASE_URL'].rstrip('/')
        sa_email = os.environ['TASKS_SERVICE_ACCOUNT']
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{base_url}/jobs/{kind}/{result_id}",
                "oidc_token": {
                    "service_account_email": sa_email,
                    "audience": base_url,
                },
            },
            # Must exceed the longest analysis hold (~620s poller timeout today).
            "dispatch_deadline": {"seconds": 900},
        }
        _tasks_client().create_task(parent=queue, task=task)
        logger.info(f"Enqueued {kind} analysis job {result_id}")
    except Exception as e:
        logger.error(f"Failed to enqueue {kind} job {result_id}: {e}")
```

Add to `requirements.txt`: `google-cloud-tasks==2.16.5` and run `venv/bin/pip install google-cloud-tasks==2.16.5`.

- [x] **Step 4: Run tests**

Run: `venv/bin/python -m pytest --noconftest tests/unit/test_analysis_dispatch.py -v`
Expected: 3 PASSED

- [x] **Step 5: Commit**

```bash
git add toms_gym/services/analysis_dispatch.py requirements.txt tests/unit/test_analysis_dispatch.py
git commit -m "feat(backend): Cloud Tasks enqueue service for analysis jobs (flag-gated)"
```

---

### Task 8: `/jobs` push handlers

**Files:**
- Create: `toms_gym/routes/jobs_routes.py`
- Modify: `toms_gym/app.py` (register blueprint next to the other `register_blueprint` calls)
- Test: `tests/unit/test_jobs_routes.py`

**Interfaces:**
- Consumes: `_process_job(get_connection, result_id, attempt_id, video_url, lift_type)` from `toms_gym.integrations.lifting_processor`; `process_bowling_video(result_id, attempt_id, video_url, lane_edges_manual)` from `toms_gym.integrations.bowling_processor`. Both already write `completed`/`failed` to the DB themselves.
- Produces: `POST /jobs/lifting/<result_id>` and `POST /jobs/bowling/<result_id>`. Returns 200 when the row finished `completed` (or is gone/already done — don't retry those), 403 on bad OIDC, 500 when the run failed (Cloud Tasks retries up to the queue's max-attempts).

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_jobs_routes.py
"""Cloud Tasks push handlers: auth, status transitions, retry semantics."""
import pytest
from flask import Flask

import toms_gym.routes.jobs_routes as jobs_routes


class FakeRow:
    def __init__(self, status="queued"):
        self.id = "r-1"
        self.attempt_id = "a-1"
        self.processing_status = status
        self.video_url = "https://storage.googleapis.com/b/v.mp4"
        self.lift_type = "Plank"


class FakeSession:
    def __init__(self, row, final_status="completed"):
        self._row = row
        self._final_status = final_status
        self.executed = []
    def execute(self, stmt, params=None):
        self.executed.append((str(stmt), params))
        outer = self
        class R:
            def fetchone(self):
                return outer._row
            def scalar(self):
                return outer._final_status
        return R()
    def commit(self):
        pass
    def rollback(self):
        pass
    def close(self):
        pass


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(jobs_routes.jobs_bp)
    app.config["TESTING"] = True
    return app


def _allow_auth(monkeypatch):
    monkeypatch.setattr(jobs_routes, "_verify_oidc", lambda req: True)


def test_rejects_unauthenticated(app):
    resp = app.test_client().post("/jobs/lifting/r-1")
    assert resp.status_code == 403


def test_completed_job_returns_200(app, monkeypatch):
    _allow_auth(monkeypatch)
    session = FakeSession(FakeRow(), final_status="completed")
    monkeypatch.setattr("toms_gym.db.get_db_connection", lambda: session)
    calls = []
    monkeypatch.setattr("toms_gym.integrations.lifting_processor._process_job",
                        lambda *a, **k: calls.append(a))
    resp = app.test_client().post("/jobs/lifting/r-1")
    assert resp.status_code == 200
    assert len(calls) == 1


def test_failed_job_returns_500_for_retry(app, monkeypatch):
    _allow_auth(monkeypatch)
    session = FakeSession(FakeRow(), final_status="failed")
    monkeypatch.setattr("toms_gym.db.get_db_connection", lambda: session)
    monkeypatch.setattr("toms_gym.integrations.lifting_processor._process_job",
                        lambda *a, **k: None)
    resp = app.test_client().post("/jobs/lifting/r-1")
    assert resp.status_code == 500


def test_missing_row_returns_200_no_retry(app, monkeypatch):
    _allow_auth(monkeypatch)
    session = FakeSession(None)
    monkeypatch.setattr("toms_gym.db.get_db_connection", lambda: session)
    resp = app.test_client().post("/jobs/lifting/r-gone")
    assert resp.status_code == 200
```

- [x] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest --noconftest tests/unit/test_jobs_routes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'toms_gym.routes.jobs_routes'`

- [x] **Step 3: Implement**

```python
# toms_gym/routes/jobs_routes.py
"""Cloud Tasks push handlers for analysis jobs.

Cloud Tasks POSTs here with an OIDC token (see services/analysis_dispatch.py).
Handlers run the same process functions the daemon pollers used; Cloud Tasks
owns retries: 200 = done/don't retry, 500 = retry (up to queue max-attempts).
"""
import logging
import os

import sqlalchemy
from flask import Blueprint, jsonify, request

jobs_bp = Blueprint('jobs', __name__, url_prefix='/jobs')
logger = logging.getLogger(__name__)


def _verify_oidc(req) -> bool:
    """Verify the Cloud Tasks OIDC token: audience + expected service account."""
    auth = req.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return False
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as gauth_requests
        claims = id_token.verify_oauth2_token(
            auth.split(' ', 1)[1],
            gauth_requests.Request(),
            audience=os.environ.get('TASKS_TARGET_BASE_URL', ''),
        )
        return (claims.get('email') == os.environ.get('TASKS_SERVICE_ACCOUNT', '')
                and claims.get('email_verified', False))
    except Exception as e:
        logger.warning(f"/jobs OIDC verification failed: {e}")
        return False


def _load_and_mark_processing(select_sql, update_sql, result_id):
    """Fetch the job row and flip it to 'processing'. Returns row or None."""
    from toms_gym.db import get_db_connection
    session = get_db_connection()
    try:
        row = session.execute(sqlalchemy.text(select_sql), {"id": result_id}).fetchone()
        if not row or row.processing_status == 'completed':
            return row, False
        session.execute(sqlalchemy.text(update_sql), {"id": result_id})
        session.commit()
        return row, True
    finally:
        session.close()


def _final_status(table, result_id):
    from toms_gym.db import get_db_connection
    session = get_db_connection()
    try:
        return session.execute(
            sqlalchemy.text(f'SELECT processing_status FROM "{table}" WHERE id = :id'),
            {"id": result_id},
        ).scalar()
    finally:
        session.close()


@jobs_bp.route('/lifting/<string:result_id>', methods=['POST'])
def run_lifting_job(result_id):
    if not _verify_oidc(request):
        return jsonify({"error": "unauthorized"}), 403
    row, should_run = _load_and_mark_processing(
        """
        SELECT lr.id, lr.attempt_id, lr.processing_status, a.video_url, a.lift_type
        FROM "LiftingResult" lr JOIN "Attempt" a ON a.id = lr.attempt_id
        WHERE lr.id = :id
        """,
        'UPDATE "LiftingResult" SET processing_status = \'processing\', updated_at = now() WHERE id = :id',
        result_id,
    )
    if row is None:
        return jsonify({"status": "gone"}), 200  # deleted row: don't retry
    if not should_run:
        return jsonify({"status": "already completed"}), 200

    from toms_gym.db import get_db_connection
    from toms_gym.integrations import lifting_processor
    lifting_processor._process_job(get_db_connection, row.id, row.attempt_id,
                                   row.video_url, row.lift_type)

    status = _final_status("LiftingResult", result_id)
    if status == 'completed':
        return jsonify({"status": "completed"}), 200
    return jsonify({"status": status}), 500  # Cloud Tasks retries


@jobs_bp.route('/bowling/<string:result_id>', methods=['POST'])
def run_bowling_job(result_id):
    if not _verify_oidc(request):
        return jsonify({"error": "unauthorized"}), 403
    row, should_run = _load_and_mark_processing(
        """
        SELECT br.id, br.attempt_id, br.processing_status, a.video_url, br.lane_edges_manual
        FROM "BowlingResult" br JOIN "Attempt" a ON a.id = br.attempt_id
        WHERE br.id = :id
        """,
        'UPDATE "BowlingResult" SET processing_status = \'processing\', updated_at = now() WHERE id = :id',
        result_id,
    )
    if row is None:
        return jsonify({"status": "gone"}), 200
    if not should_run:
        return jsonify({"status": "already completed"}), 200

    from toms_gym.integrations import bowling_processor
    bowling_processor.process_bowling_video(str(row.id), str(row.attempt_id),
                                            row.video_url, row.lane_edges_manual)

    status = _final_status("BowlingResult", result_id)
    if status == 'completed':
        return jsonify({"status": "completed"}), 200
    return jsonify({"status": status}), 500
```

Note for the test: the handlers must call `_process_job`/`process_bowling_video` **as module attributes** (`lifting_processor._process_job(...)`), not via `from ... import _process_job`, so monkeypatching the module attribute works.

Register in `toms_gym/app.py` next to the existing blueprint registrations:

```python
from toms_gym.routes.jobs_routes import jobs_bp
app.register_blueprint(jobs_bp)
```

- [x] **Step 4: Run tests**

Run: `venv/bin/python -m pytest --noconftest tests/unit/ -v`
Expected: all PASSED (dispatch + jobs tests).

- [ ] **Step 5: Commit**

```bash
git add toms_gym/routes/jobs_routes.py toms_gym/app.py tests/unit/test_jobs_routes.py
git commit -m "feat(backend): /jobs push handlers for Cloud Tasks analysis dispatch"
```

---

### Task 9: Enqueue at job creation; pollers stand down in tasks mode

**Files:**
- Modify: `toms_gym/routes/lifting_routes.py` (two sites: requeue commit ~line 60, insert commit ~line 82)
- Modify: `toms_gym/routes/bowling_routes.py` (the `INSERT INTO "BowlingResult" ... 'queued'` site at ~line 150; grep for any requeue `UPDATE ... 'queued'` in the same file and wire it too)
- Modify: `toms_gym/integrations/lifting_processor.py` (`start_lifting_processor`), `toms_gym/integrations/bowling_processor.py` (`start_bowling_processor`)
- Test: `tests/unit/test_enqueue_wiring.py`

**Interfaces:**
- Consumes: `enqueue_analysis_job(kind, result_id)` from Task 7.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_enqueue_wiring.py
"""Pollers no-op in tasks mode so dispatch isn't duplicated."""
import toms_gym.integrations.lifting_processor as lp
import toms_gym.integrations.bowling_processor as bp


def test_lifting_poller_stands_down_in_tasks_mode(monkeypatch):
    monkeypatch.setenv("ANALYSIS_DISPATCH_MODE", "tasks")
    monkeypatch.setattr(lp, "LIFTING_PROCESSOR_ENABLED", True)
    started = []
    monkeypatch.setattr(lp.threading, "Thread", lambda **k: started.append(k))
    lp.start_lifting_processor()
    assert started == []


def test_bowling_poller_stands_down_in_tasks_mode(monkeypatch):
    monkeypatch.setenv("ANALYSIS_DISPATCH_MODE", "tasks")
    monkeypatch.setattr(bp, "BOWLING_PROCESSOR_ENABLED", True)
    started = []
    monkeypatch.setattr(bp.threading, "Thread", lambda **k: started.append(k))
    bp.start_bowling_processor()
    assert started == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest --noconftest tests/unit/test_enqueue_wiring.py -v`
Expected: FAIL — threads get created (the poller doesn't check the mode yet). Note: patching `Thread` means the "failure" shows `started` non-empty.

- [ ] **Step 3: Stand down the pollers in tasks mode**

At the top of `start_lifting_processor()` (before the `LIFTING_PROCESSOR_ENABLED` check), add:

```python
    if os.environ.get('ANALYSIS_DISPATCH_MODE', 'poller') == 'tasks':
        logger.info("Lifting processor disabled: Cloud Tasks dispatch mode is active")
        return
```

Mirror the same three lines in `start_bowling_processor()` (bowling_processor.py already imports `os`).

- [ ] **Step 4: Wire enqueue at the three creation/requeue sites**

`lifting_routes.py` — add the import at the top: `from toms_gym.services.analysis_dispatch import enqueue_analysis_job`, then:

Site 1, after the requeue `session.commit()` (line 60), before the `return`:
```python
                enqueue_analysis_job('lifting', str(existing.id))
```

Site 2, after the insert `session.commit()` (line 82), before the `return`:
```python
        enqueue_analysis_job('lifting', result_id)
```

`bowling_routes.py` — same import; after the commit following the `INSERT INTO "BowlingResult" ... VALUES (:id, :attempt_id, 'queued')` (line ~150):
```python
        enqueue_analysis_job('bowling', result_id)
```
Also run `grep -n "'queued'" toms_gym/routes/bowling_routes.py` — if there is a requeue UPDATE site, add the same call after its commit.

(Enqueue-after-commit ordering matters: the task handler reads the row, so the row must be committed first. `enqueue_analysis_job` swallows its own errors, so these calls can't break the endpoints; in poller mode they're no-ops.)

- [ ] **Step 5: Run tests**

Run: `venv/bin/python -m pytest --noconftest tests/unit/ -v` → all PASSED.
Then the full DB-bound suite once: `./run_tests.sh` → same pass/fail state as before this plan (no new failures).

- [ ] **Step 6: Commit**

```bash
git add toms_gym/routes/lifting_routes.py toms_gym/routes/bowling_routes.py \
  toms_gym/integrations/lifting_processor.py toms_gym/integrations/bowling_processor.py \
  tests/unit/test_enqueue_wiring.py
git commit -m "feat(backend): enqueue Cloud Tasks at job creation; pollers stand down in tasks mode"
```

---

### Task 10: Provision, deploy, and cut over

No code — infra + verification. Run from `/Users/toka/code/toms_gym` unless noted.

- [ ] **Step 1: Create the queue and grant IAM**

```bash
gcloud tasks queues create analysis-jobs --location=us-east1 --project=toms-gym \
  --max-attempts=3 --max-concurrent-dispatches=3 --max-dispatches-per-second=5

gcloud projects add-iam-policy-binding toms-gym \
  --member=serviceAccount:toms-gym-service@toms-gym.iam.gserviceaccount.com \
  --role=roles/cloudtasks.enqueuer

# The runtime SA mints OIDC tokens as itself for the task's http_request:
gcloud iam service-accounts add-iam-policy-binding \
  toms-gym-service@toms-gym.iam.gserviceaccount.com \
  --member=serviceAccount:toms-gym-service@toms-gym.iam.gserviceaccount.com \
  --role=roles/iam.serviceAccountUser
```

`--max-concurrent-dispatches=3` deliberately matches the engine's `--max-instances=3 --concurrency=1` so tasks queue instead of piling onto cold starts.

- [ ] **Step 2: Deploy the engine** (new in-process/summary code from Tasks 1–5)

```bash
cd /Users/toka/code/bowling-app/analysis-engine && ./deploy.sh
```

- [ ] **Step 3: Add backend env vars and deploy**

Locate where `deploy.py` builds backend `--set-env-vars` (grep for `ANALYSIS_SERVICE_URL` in `deploy.py` / `deploy-config.json`) and add, alongside it:

```
ANALYSIS_DISPATCH_MODE=tasks
ANALYSIS_TASKS_QUEUE=projects/toms-gym/locations/us-east1/queues/analysis-jobs
TASKS_TARGET_BASE_URL=https://my-python-backend-quyiiugyoq-ue.a.run.app
TASKS_SERVICE_ACCOUNT=toms-gym-service@toms-gym.iam.gserviceaccount.com
```

Then: `python3 deploy.py --backend-only --skip-iam`

- [ ] **Step 4: Verify in production**

1. Upload a lifting video (plank) through the frontend, or re-trigger an existing attempt: `curl -X POST https://my-python-backend-quyiiugyoq-ue.a.run.app/lifting/analyze/<attempt_id>`.
2. Confirm a task appears and drains: `gcloud tasks queues describe analysis-jobs --location=us-east1 --project=toms-gym` and `gcloud logging read 'resource.labels.service_name="my-python-backend" "Enqueued lifting"' --project=toms-gym --limit=5 --freshness=15m`.
3. Poll `GET /lifting/result/<attempt_id>` until `completed`; confirm `annotated_video_url` plays.
4. Repeat once for bowling.
5. Confirm the pollers stood down: `gcloud logging read '"Lifting processor disabled: Cloud Tasks dispatch mode is active"' --project=toms-gym --limit=1 --freshness=1h`.

- [ ] **Step 5: Commit deploy config and record the soak**

```bash
git add deploy.py deploy-config.json
git commit -m "chore(deploy): Cloud Tasks dispatch env for analysis jobs"
```

Report: cutover done; pollers are dormant (mode check) but code remains for rollback (`ANALYSIS_DISPATCH_MODE=poller` reverts instantly). Schedule Task 11 after ~1 week of clean runs.

---

### Task 11 (post-soak, ~1 week later): Delete the poller loops

**Files:**
- Modify: `toms_gym/integrations/lifting_processor.py` — delete `start_lifting_processor`, `_run_processor`, `_poll_and_process`; keep `_sanitize_for_json`, `_get_id_token`, `_normalize_lift_type`, `_process_job` (now used only by jobs_routes).
- Modify: `toms_gym/integrations/bowling_processor.py` — delete `start_bowling_processor`, `run_bowling_processor`, `_poll_and_process`; keep `_get_id_token`, `process_bowling_video`.
- Modify: `toms_gym/app.py` — remove the two imports (lines 25–26) and the `start_bowling_processor()` / `start_lifting_processor()` calls (lines 207, 210).
- Modify: `tests/unit/test_enqueue_wiring.py` — delete (it tests the removed stand-down path).

- [ ] **Step 1: Verify soak** — `gcloud logging read 'resource.labels.service_name="my-python-backend" severity>=ERROR "job"' --project=toms-gym --freshness=7d` shows no dispatch-related errors, and no `LiftingResult`/`BowlingResult` rows are stuck in `queued` (check via the app or Cloud SQL console).
- [ ] **Step 2: Make the deletions above.** Run `grep -rn "start_lifting_processor\|start_bowling_processor\|_run_processor\|run_bowling_processor" toms_gym/` — expect zero hits.
- [ ] **Step 3: Tests** — `venv/bin/python -m pytest --noconftest tests/unit/ -v` and `./run_tests.sh` pass.
- [ ] **Step 4: Deploy** — `python3 deploy.py --backend-only --skip-iam`; re-run one lifting verification from Task 10 Step 4.
- [ ] **Step 5: Commit**

```bash
git add toms_gym/integrations/ toms_gym/app.py tests/unit/
git commit -m "refactor(backend): remove daemon-thread pollers superseded by Cloud Tasks"
```
