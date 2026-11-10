# Glasses-POV session: round 4 pin-row fix and the feedback-loop plan — 2026-11-10

(Work done the evening of 2026-11-09, 17:30-23:30; saved 2026-11-10.)

## What this was
Continuation of the 2026-11-08 glasses session run (`docs/sessions/2026-11-09-glasses-pov-session.md`). Tom asked why so many throws had no line, then asked for the judge's pin-row hint to be applied and the video re-rendered, then for a dynamic workflow to design a faster, less manual path from the Meta glasses to per-throw feedback.

## What changed
- **Why no line (answer):** of 13 video-only throws, 9 had a full ball track that stopped 2-11 px short of the headpin base row (rule J2 wants a held crossing), 2 had the ball out of the picture (camera on the ceiling / feet), 1 was fully tracked but 3.25 boards off truth, 1 had no track at all (black ball, ORB failed on 23 of 95 pairs).
- **Round 4, commit `1f83eb5`:** `track_v3.py` gained `pin_row_extrapolated_crossing`, a last-resort fallback (pass >= 3, after SAM-to-end, deck re-seed, relaxed hold, gutter channel): least-squares zero of the same-frame gap (ball y minus headpin base row of that frame) over the last 6 real points, accepted when the gap is closing and the zero is within -3..+8 frames of the track end. RULES.md amendment 17:40 (third rerun, over budget, J2 reading). Simulated first on the stored tracks; ran `rerun_r2.sh work/rerun_r2/stems_r4.txt r4` (10 stems, 1837 s, 0 failures). Judge: main loop ran the round-1/3 rule code + score_v2 (`work/judge_r4/`), J6 grids read by eye.
- **Result:** lines 18 -> 20 of 31; Game 3 3 -> 5 of 11; truth pin_row_err mean 8.83 -> 3.67 frames; truth entry_err_pr mean 3.16 -> 3.90 boards (104714's entry inherits bad SAM tail points). `results/judged_round4.json`, `results/judged_final.json` (latest_round 4), `results/rerun_round4_notes.md`.
- **Render bug fixed:** `make_session_video.py` had the video-only stems hard-coded from round 3; the first round-4 render showed the two new passes as video-only. It now reads `judged_final.json`; pin-row label "extrapolated crossing" on those throws.
- **Drive:** same file updated in place (`drive_update.sh`, PATCH to id `1Dx_AuSQvHf5D21UDJM0j6K0UiKVQJZB0`, md5 `3e859aa07744904814e09640d89223c4`, 86,382,219 bytes). Link unchanged: https://drive.google.com/file/d/1Dx_AuSQvHf5D21UDJM0j6K0UiKVQJZB0/view. `drive_upload.sh` and `drive_update.sh` copied into the session folder (commit `054f6e8`).
- **Design workflow `wf_c9d69c22-de8`** (8 agents, 30 min, none empty), commit `c3f27e7`: `docs/plans/2026-11-09-glasses-feedback-loop/` (README = staged plan, `current-pipeline-steps.md`, `meta-glasses-options.md`, `design-now.md`, `design-toolkit.md`, `design-session.md`, `judge-1.md`, `judge-2.md`). Judges split 1-1; the plan takes the shared post-Drive pipeline as Stage 1.
- Memory `glasses_pov_session_2026_11_08.md` and the session README headline updated to the round-4 counts.

## What we learned
- The judge's round-3 "7 of 9 within 8 frames" table measured the gap against a 3-frame median of the base row; at the track end that is a 2-sample mean and reads a false drop under camera pan (113911: median gaps 21 -> 11, same-frame 20.6 -> 20.3). Same-frame gaps rescue 3 of 9. Anchor "gap closing" statistics on same-frame measurements.
- A right pin-row frame does not make the entry right: the entry at an extrapolated crossing inherits the tail points' error (104714: pin row 34 -> 3 frames off, entry 2.47 -> 6.88 boards off). Fix the SAM tail before extrapolating further.
- The renderer must read the verdict file, never a pasted stem list.
- Meta glasses (research, V = fetched): no third-party code on non-display glasses; no API reads stored clips; only the Meta AI app import (glasses folded or cased, phone nearby) gets clips off. Device Access Toolkit 1.0 streams the camera to a phone app (720x1280, developer mode, iOS sample stops on backgrounding). Drive API is not enabled on the `toms-gym` project.
- Canary check for "passers unchanged": compare `frames`, `boards`, `lane`, `base_rows`, `pin_row_frame_est`, not file sha (wall time and newer event fields differ).

## Still broken / next steps
- 11 throws still video-only: 105322, 114631, 114810, 113911 (gap closes too slowly or not at all over the last 6 points; 113911's SAM tail moves with the camera), 112413 (tail jumps to another object), 113716 (static tail), 110622 and 114236 (camera aim), 115105 (black ball never chained), 110224 (entry 3.25 off truth), 104714 (entry 6.88 off truth at the right pin row). Next tracker change: reject SAM tail points that do not advance toward the base row, then re-fit.
- The two new lines (114059, 114438) sit on extrapolated pin rows; their entries moved 1-2 boards and are unvalidated (J6 55 ft points are on the ball).
- Plan Stage 1 not started: Drive-inbox launchd worker, judge code committed out of gitignored `work/`, `make_session_video.py` argparse, publish via existing short-link/email code; proof = re-upload the 11-08 clips and get an unprompted email with the same 20 of 31.
- Decisions for Tom (plan section 4): phones (yours and Chardie's), spoken game tag yes/no, "Chardie" vs "Chris", Mac awake vs Cloud Run CPU, keep the extrapolated crossing as a labelled rule, paid sync app.
- README.md of the session folder: only the headline was updated; the round-3 body text below it still says 18/13 in places.

## Verification
- Round-4 batch: `work/rerun_r2_r4.done` = 10 stems, failed_stems [], 1837 s. Canary 104946 identical on frames/boards/lane/base_rows/pin_row (events gained round-2 fields it never had; `events.how` text differs).
- Judge: `work/judge_r4/rules.py` output and `write_judged.out`; truth scores in `work/judge_r4/score_*.txt`; J6 grids `work/judge_r4/j6_grid_1..3.jpg` read by me, not by an independent judge agent (disclosed in RULES.md).
- Render: `work/session_timeline.json` shows 114059 and 114438 `video_only: false`; `recap_Game_3_Tom.png` and both throw exit frames viewed. Not checked: audio, the other 29 throw frames.
- Drive: md5 and size match between the local file and the Drive `files.get` response.
- Not run: no tests or type checks apply (research scripts); the plan's claims about repo line numbers were verified by the synthesis agent, not by me.
