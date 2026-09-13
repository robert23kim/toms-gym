# Lane-landmarks loop wrap-up, housekeeping and the alley-face brief — 2026-09-13

## What this was
The `/loop` run of `docs/research/2026-09-13-lane-landmarks/BRIEF.md` (E1-E5, autonomous), then Tom's
follow-up questions (where is the video, was it good news, how did the new model do and why, did the
extra features help), two standing housekeeping rules, and a handoff brief for the next loop. The
loop's own findings are in `2026-09-13-lane-landmarks-loop.md` and the folder README; this file
records what happened after that doc was written.

## What changed
- **Commits on `main`** (nothing pushed; `origin` is 12 commits behind after these):
  - `276a59e` docs(bowling): cheap lane model loop (2026-09-12) — 206 files, the previously untracked loop-3 folder + its session log
  - `52fe2cd` docs(bowling): lane landmarks loop (2026-09-13) — 149 files, this loop's folder + session log + the CLAUDE.md "Cheap Lane Model" and "Lane Landmarks" sections
  - `5463b6a` docs(bowling): brief for the alley-face constellation loop — `docs/research/2026-09-14-alley-face/BRIEF.md`
- **Result files trimmed for git:** the eight per-frame E3 files (69 MB) are gzipped to 4.4 MB
  (`results/e3_fit_*.json.gz`); `common.load` / `common.has_result` read either form; `results/e3_fit_*.json`
  added to the folder `.gitignore`. Weights and `review.mp4` stay ignored.
- **README additions after the loop doc:** measured causes of the learned-arrow failure (E2), the
  per-frame pin-refit floor (finding 9), the two-class 1024 px student aside (finding 8), and the
  no-mosaic folds' numbers (Blocked). Same facts propagated to the CLAUDE.md section and the memory note.
- **Memories written** (`~/.claude/projects/-Users-toka-code-toms-gym/memory/`, not yet committed there):
  `lane_landmarks_loop.md` (project), `feedback_review_video_one_minute.md`, `feedback_commit_experiments.md`.
- **Handoff brief** `docs/research/2026-09-14-alley-face/BRIEF.md`: the lane's landmarks (foul corners,
  guide dots, arrows, pin bases, gutter lines) as one planar constellation — find it with no lane prior,
  align jointly, persist through the throw, learn it heatmap-style; carries loop 4's numbers to beat.
- `review.mp4` (3 min 14 s) delivered twice via SendUserFile; the brief sent once.

## What we learned
- **Why the learned arrow class scored zero, per class on the training videos' own val split:** with
  mosaic on, arrow AP 0 and recall 0 even in-distribution (half-scale tiles put a ~6 px arrow under the
  8 px stride, so it never trains); with mosaic off, AP50 0.68-0.71 in-distribution and 0 correct
  detections on the held-out video at conf 0.001 (17-115 boxes per 12 frames, none within 1.5 boards of
  a real arrow). It memorises positions, like loop 3's pose head. Mosaic off also costs the lane class
  a fifth to a third of its accuracy.
- **The per-frame pin refit floors at ~0.4 boards on tom_old** regardless of the input lane
  (0.26-1.62 → 0.35-0.41): rack-fit noise. Pool the rack over the standing-pin frames next time.
- **The two-class 1024 px student (batch 4, no flip)** gives a lane on all 409 tom_old frames at
  0.26 boards vs pins (loop 3's 1024 model: 60 confident frames, 0.64). Three recipe changes at once;
  a lead, not a result.
- `rtk`'s git wrapper printed `ok` for `git status --porcelain` on paths with real changes again this
  session; the commit script's own `git status` (run via `bash script.sh`) showed the truth.
- Tom's framing for the next loop: arrows should add value "the way features on a face help identify
  the face" — arrangement, not a far-end ruler.

## Still broken / next steps
- **Nothing is pushed.** 12 commits on `main` exist only on this laptop (oldest ~23 h). Push when
  ready; nothing here needs a PR.
- **The alley-face loop is briefed, not started:** `docs/research/2026-09-14-alley-face/BRIEF.md`
  (start command at its top). Its two standing rules: ~1 min review video, commit at loop end.
- **Near-end landmark detector** (foul line / gutter edges): the mask student's foul-line corners are
  2-3 boards off on two videos and now cap everything; the brief's E4 targets it.
- **Pool the rack over frames** instead of per-frame refits (the 0.4-board floor); brief E4/E5.
- **Isolate the 1024 px student's recipe** (batch 4 vs no-flip vs second class) before believing it.
- Memory files under `~/.claude` are uncommitted (the SessionStart hook flags 5); that repo is
  separate from this one and was left alone.
- Ten older untracked session docs (2026-08-28 … 2026-09-08) in `docs/sessions/` are not experiments
  and were not committed here.

## Verification
- E1-E4 scripts, `rescore_baselines.py`, `eval_seg2.py`, `tables.py`, `fill_readme.py`,
  `video_script.py`, `review_video.py` all ran to completion; every README number traces to a
  `results/*.json(.gz)` row. Overlays and a 16-frame contact sheet of `review.mp4` were inspected.
- After gzipping, `tables.py` + `fill_readme.py` + `video_script.py` re-ran successfully against the
  `.gz` files (the README's nine table blocks refilled).
- Commits verified with `git log --oneline -4` and `git show --stat`; the staged sets contained no
  `.pt`, `.mp4` or `__pycache__` (checked before each commit).
- Not verified: no push, so nothing is confirmed on `origin`; the 1024 px student's result was not
  reproduced under an isolated recipe; the arrow-class analysis used 12 held-out frames per video.
