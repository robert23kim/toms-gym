# Design: fix the expensive human steps inside the pipeline, keep the transfer (2026-11-09)

Lens: the glasses -> phone -> Drive transfer stays as Tom does it today. Everything after the clips land in Drive runs without a person, and the four human-judgment stages inside the pipeline (release read, bowler/game map, judge-and-rerun, render-and-share) are replaced by code or by one cheap capture-time habit.

Evidence tags: **V** = read from a file in the repo or the session folder this pass (path given); **I** = inferred; **UNV** = looked and could not confirm.

## One-line pitch
Make the Drive folder the start button: a laptop worker picks up the session, reads each release with a codified vision call cross-checked by audio, takes the bowler from a two-word voice tag at the start of each throw, runs the frozen tracker + judge once with no human amendments, and mails one short link to the session video about 90 minutes after the upload lands, instead of a day later.

## Research or plumbing? The test, applied
A target is **plumbing** when a frozen rule or script already exists and was scored on untouched data, so building it changes time and not accuracy. It is **research** when the rule does not exist or its only score is post-hoc.

| target | verdict | why (V unless marked) |
|---|---|---|
| Release detection without eye reads | **research core, plumbing bridge** | `auto_cuts.py` v3 frozen on September clips scored 4 right / 6 wrong / 15 null on 25 untouched clips; every wrong cut said `verified: true`; v3.1 (`MIN_ROLL=45`) is a post-hoc fit with no holdout (`results/cuts_notes.md` secs 1-2, `README.md`). 24 of 31 releases were read by a Claude agent from frame grids. The bridge is to codify that read as a pinned-prompt vision call and make a wrong read visible with two independent checks. |
| Bowler + game assignment | **plumbing (voice tag), half-research (scoreboard OCR)** | The 27-minute structure stage used clothing clusters, lane alternation and 15 board reads; game 1 has no board read at all, and the board says "Chris" where the brief says "Chardie" (`results/structure_notes.md`). Clips carry audio: `auto_cuts.py` already runs a 40-300 Hz thud and 300-2000 Hz crash detector on it. A spoken tag at clip start is a transcription problem, not a vision problem. |
| Judge-and-rerun unattended | **plumbing, accuracy unchanged** | J1-J5 are code: `work/judge_r1/judge_rules.py` (79 lines) and `work/judge_r4/rules.py` (62 lines). The per-clip fallback ladder already lives inside `track_v3.py` as a `MAX_PASSES` loop keyed on measured conditions (docstring, rounds 1-2 and 4). What was human was the agents amending rules at 12:50 and 17:40 and launching reruns. |
| One link per session | **plumbing, all parts exist** | `make_session_video.py` hard-codes `CLIPS`, `VIDEO_ONLY` and group order (lines 4-6); GCS signed/public URL code in `upload_routes.py:171-190`; `ShortLink` with OG tags at `/s/<code>` (`short_link_routes.py`); `analysis_notify.py` already creates a short link and sends a "ready" email (`_create_short_link`, `_send_ready_email`, `notify_analysis_complete`). |
| The trigger (not named as a target, but it is the 21.6 h) | **plumbing** | Steps 5 and 7 of the current pipeline are "Tom prompts Claude" and "an agent starts the workflow". The Drive listing/download was curl + a gcloud token in a reclaimed scratchpad (`current-pipeline-steps.md` step 6, 24). A folder watch plus a launchd worker removes the laptop-session dependency without touching the transfer. |

## End-to-end flow (H = human, M = machine)

1. **H** Record one clip per throw on the glasses, as today. New habit, ~1 s: say the tag as the clip starts: "Tom, game two" (or "Chardie, game two, frame five" when a frame matters). Nothing else changes at the lane.
2. **H** Fold the glasses or case them so the Meta AI app imports to the phone (kept as is; `meta-glasses-options.md` option A).
3. **H** Upload the day's clips from the phone to the fixed Drive folder `bowling-pov/inbox` (kept as is, ~6 min for 1 GB measured 11-09).
4. **M** Laptop worker (`launchd`, every 2 min): Drive v3 `files.list` on the inbox, skips names still ending `.adding` (the 11-09 `wait_drive.sh` rule), downloads new clips with an md5 check into `~/pov-<date>/drive_raw`, and marks the session "open" until no new file for 10 min. Repo script, moved out of the scratchpad.
5. **M** Cuts: `auto_cuts.py` v3.1 runs first (`--no-cut`) for the classical candidate and the audio onsets. A new `grid_write.py` makes the two grids the agents read by hand on 11-09 (a whole-clip overview at 1 frame per 0.5 s and a frame-by-frame grid of one 2 s window; 82 such JPGs exist in `work/cuts/grids/` but no script that wrote them survives, V). Then `release_read.py` (new): one vision call on the overview grid to pick the 2 s window, one on the fine grid to name the release frame, with the pinned convention from `cuts_notes.md` sec 3 (ball at the frame bottom = X, release = X+1; upright POV = first frame on the lane). Accept when (a) the mid-band crash onset `auto_cuts` already computes sits in release+50..+130, and (b) the tracker's first chained residual point (step 7) sits in release+1..+15. Otherwise the clip is flagged `release: unresolved` and rendered video-only with that reason. A classical auto read within 1 frame of the vision read keeps `release_source: auto`, as the 7 clips did on 11-09.
6. **M** Bowler/game: speech-to-text on the first 4 s of each clip's audio; parse `<name> [game N] [frame N]`. Missing tag: inherit from the previous clip when the gap is under 3 min and the lane alternates (lanes 27/28 rule from `structure_notes.md`); a gap over 3 min opens a new game. Appearance cluster A/B (`work/structure/person_A.jpg`, `person_B.jpg`) is a consistency check that can only lower confidence, never assign. Confidence under 0.7 prints on the card, as RULES.md already requires.
7. **M** Tracker: `track_v3.py <stem> --device mps`, one invocation per clip, serial, on the laptop. Its internal pass loop is the whole rerun budget (far seed, pin-row second pass, deck re-seed, deck gate, gutter row, dark seed, round-4 extrapolated crossing).
8. **M** Judge: one process, `judge_rules.judge` with the 12:50 dead-band and the 17:40 extrapolated-crossing readings frozen as the product rules. No amendments, no reruns beyond what step 7 already did. A failing throw is `video-only` with `rules_failed` and `rerun_hint` kept for the card. The truth checks (T-entry, T-pinrow) do not run: truth is quarantined and a product has none.
9. **M** Render: `make_session_video.py` taking `--clips`, `--map session_map.json`, `--judged judged_final.json`, deriving `VIDEO_ONLY` from the judge file and group order from the map, with the fail reason on every video-only card (Tom's 17:29 question "why so many throws have no ball line" answered on screen).
10. **M** Publish: upload `session.mp4` to the Toms Gym GCS bucket (the `public_url` pattern in `upload_routes.py`), `POST /short-link` with OG title "Bowling session 2026-11-08: 18 of 31 lined", and `notify_analysis_complete`-style email to Tom with the `/s/<code>` link. Optionally also the resumable Drive upload (`drive_upload.sh`, moved into the repo).
11. **H** Tom opens one link on the phone.

## Manual steps that remain
- Start/stop a clip per throw (as today) and speak the two-word tag at clip start (new, ~1 s).
- Fold or case the glasses so the Meta AI app imports (as today).
- Upload from the phone to the Drive inbox folder (as today; the lens keeps it).
- Keep the laptop awake and on Wi-Fi (`caffeinate` or a wake schedule); nothing runs if it sleeps.
- One-off: `gcloud auth login --enable-gdrive-access` already done on 11-07 (`docs/sessions/2026-11-07-glasses-pov-hook-loop.md:42`); token refresh is the worker's problem.

## Expected time from last throw to feedback
Measured inputs (V): tracker per clip 59 s first pass, 97-165 s with reruns, SAM 2 is 92.6 of 119.2 s on 112413 in the round-4 log; 31 throws; Drive download 4 min; render + critic 23 min by hand (render alone a few minutes, I).

| segment | minutes | basis |
|---|---|---|
| last throw -> glasses folded -> import -> phone upload done | 15-30 (I) | kept as today; depends on when Tom folds the glasses and has Wi-Fi |
| Drive watch fires, download, dedupe | 6 | 2 min poll + 4 min measured download |
| cuts + 62 vision calls, 4 in parallel | 10 (I) | the grids are already written by auto_cuts |
| STT on 31 x 4 s | 2 (I) | |
| tracker, 31 clips serial on MPS | 60-85 | 120-165 s/clip including the internal pass loop; laptop otherwise idle |
| judge + render + upload + link + email | 8 (I) | |
| **total after the upload lands** | **~90 (range 85-110)** | laptop awake |
| **total after the last throw** | **~105-140, call it 120** | versus ~27.5 h on 11-08/09 |

With `--no-sam` (the flag exists in `experiments/motion-only/run.py`) the tracker segment would drop to roughly 15 min, but its J1-J5 pass rate is unknown (UNV, see week-1 experiments).

## Reused from the repo (by file)
- `docs/research/2026-11-09-glasses-pov-session/auto_cuts.py`: classical release candidate, `--release N`, audio thud/crash onsets (it writes no grids: V, grep for imwrite/grid is empty).
- `.../work/cuts/grids/`: 82 overview/fine/hand/au grids for the 31 clips, enough for the week-1 validation without decoding video.
- `.../work/cuts/eye_releases.json`: 31 release labels (V, dict of 31), the validation set for the vision read.
- `.../track_v3.py` + `experiments/motion-only/run.py` (+ loop-1 `sam_track`, loop-2 `track_v2`): the tracker and its fallback ladder; `--no-sam` and `--device`.
- `.../work/judge_r1/judge_rules.py`, `.../work/judge_r4/rules.py`: J1-J5 and the independent J4 dead-band statistic.
- `.../make_session_video.py`: the renderer, to be parametrized.
- `.../results/session_map.json`, `judged_final.json`: the two files the renderer consumes; their shapes stay.
- `backend/toms_gym/routes/upload_routes.py:171-190` (`_generate_signed_upload_url`, public URL), `routes/short_link_routes.py` (`POST /short-link`, `GET /s/<code>`), `integrations/analysis_notify.py` (`_create_short_link`, `_send_ready_email`).
- `.claude/workflows/bowling-pov-session.js`: the phase order Cuts -> Structure -> Integrate -> JudgeAll -> Render is the product order; Truth, Experiments and Critic drop out as one-off research.
- `docs/sessions/2026-11-07-glasses-pov-hook-loop.md:42`: the Drive auth and resumable-upload recipe.

## What must be built
1. `tools/pov_worker.sh` + launchd plist: Drive inbox watch, `.adding` skip, md5 dedupe, session-close rule, then the stages below in order. (~1 day)
2. `grid_write.py` (overview + fine grid per clip, cv2 only) and `release_read.py`: two pinned-prompt vision calls per clip, audio and tracker-seed cross-checks, `release_source` in {auto, vision, unresolved}. (~2.5 days plus validation)
3. `tag_read.py`: STT on the first 4 s, tag grammar, gap/lane inheritance, writes `session_map.json` in the existing shape. (~1 day)
4. Judge freeze: one `judge_session.py` importing `judge_rules.judge` with the amendments as constants, writing `judged_final.json` in the existing shape, no truth block. (~0.5 day)
5. `make_session_video.py` argparse (`--clips`, `--map`, `--judged`, `--out`), `VIDEO_ONLY` from the judge file, fail reason on the card. (~1 day)
6. Publish step: GCS upload, `POST /short-link`, email; move `drive_upload.sh` into `tools/`. (~0.5 day)
7. Copy the research scripts into one importable package (`tools/pov/`) so the worker does not depend on `docs/research/.../work/` paths; `track_v3.py` and `run.py` hard-code `S`, `L1`, `L2` today. (~1 day)
Total: about 8 working days of plumbing before any accuracy work.

## Depends on unverified or preview-only capabilities
- Vision read of the release at or near the agent's accuracy: untested. The 31 labels were themselves produced by a Claude agent with a stated convention and +-1 ambiguity on 3 clips (`cuts_notes.md` sec 3), so passing the validation is model-vs-model agreement, not truth.
- `--no-sam` J1-J5 pass rate: unknown; could not be run this session (tracker batch in progress, rule of this task).
- STT on alley audio (music, crashes on neighbouring lanes) for a two-word tag: untested.
- Drive watch latency and the `.adding` placeholder behaviour: observed once on 11-09, not characterised.
- Meta AI auto-import latency: UNV per `meta-glasses-options.md`; forum posts report stalls.
- Laptop awake and on Wi-Fi when the upload lands.
- Cloud GPU: L4 quota in us-east1 pending since 2026-06-07 (memory `plank_analysis_perf.md`); `analysis-engine/Dockerfile.gpu` header says "DRAFT, UNTESTED"; `bowling-service` is CPU (8 CPU, 8 Gi, 600 s timeout in `deploy.sh`). Do not plan on cloud compute for SAM 2 this month.
- Phone OS: the clips are HEVC, which Meta documents for iOS, while memory says Tom's phone runs the APK (Android). Irrelevant under this lens (the transfer is kept) but it decides any later phone-side automation.

## First-week deliverable: the riskiest assumption
**Assumption:** a codified vision read can replace the agent's eye on the release frame. If it cannot, 24 of 31 releases stay human, every downstream stage (cut window, tracker seed window, J1 window, pin-row search) keys on that frame, and "unattended" does not exist.

**Deliverable:** `release_read.py` run on the 31 clips of 2026-11-08 using the grids already on disk in `work/cuts/grids/` (no new video decode, no GPU; `grid_write.py` can follow once the read is shown to work), scored against `work/cuts/eye_releases.json`: hits within +-2 frames, misses, and how many misses the audio cross-check (crash onset in release+50..+130) would have caught. Report the as-first-run number before any prompt change, in the style RULES.md lesson 1 demands. Pass bar to proceed: >= 28 of 31 within +-2 and no undetected miss larger than 5 frames. Second output, if the laptop is free: `--no-sam` on the 31 clips, judged with the frozen rules, pass count beside the 18 of 31 baseline.

## Cost (rough)
- Money: vision calls, 62 per 31-throw session, plus 31 short STT calls: order of a few dollars per session at most (I; verify against current pricing before quoting). GCS storage for an 86 MB video per session: cents. No new cloud compute.
- Effort: 7-8 days plumbing (above), 2-3 days for the release-read validation, and the research items below are open-ended.
- Ongoing: the laptop is busy for 60-85 min per session.

## Where the accuracy problems survive this design
- **Release detection.** The classical detector still scores 4/6/15 on untouched clips; the design routes around it with a vision read, which inherits the agent's own +-1 ambiguity on upright POVs (111631, 112936 and the black-ball clips) and on 110224/110442/110948. A wrong vision read is now caught only when the audio crash and the tracker seed disagree with it; a read that is wrong by a few frames and still consistent with both passes silently. The post-hoc `MIN_ROLL=45` gate stays post-hoc.
- **60 ft crossing short on 9 throws (J2).** Untouched. The ball stage ends a few px short of the headpin base row with the gap still closing; 13 of 31 throws render video-only today and the 17:40 extrapolated-crossing rule fired on 3 in simulation. Unattended operation makes the failure visible on the card ("no held crossing: 2.0 px below the base row at f382"), it does not reduce it. Fixing J2 at the source is the first real research item after week 1.
- **Judge rules are post-hoc.** 11 of 15 round-2 passes depended on the 12:50 amendments; freezing them into the product is honest only if the doc says so, and it does here. The truth checks cannot run in a product.
- **Bowler identity.** The voice tag resolves it by construction when spoken; a forgotten tag falls back to inheritance plus the lane rule, which cannot see a wearer swap inside a game. The 115157 "ball 2 or 3 of frame 10" ambiguity survives unless the tag carries the frame.
- **Tracker verdict.** No experiment reached `works`; the pick is the best `partial` and stays flagged on the title card.

## Payback order
1. Trigger + publish (items 1, 5, 6, 7): zero accuracy risk, removes steps 5, 7, 23-24 of the current pipeline and the dependency on Tom being at the laptop. Pays back on the first session.
2. Judge freeze (item 4): removes the ~3 h judge/amend/rerun loop; pays back on the first session, with the stated honesty cost.
3. Voice tag (item 3): a 1 s habit that replaces the 27-minute structure stage and settles the name question; pays back on the first session where Tom remembers to say it.
4. Release read (item 2): gates whether the whole thing runs unattended; it is first in the week because it is the riskiest, not because it pays back soonest.
5. Research, after the above: J2 pin-row crossing at the source; a release detector with a holdout; `--no-sam` or a cheaper ball stage to get the laptop hour down; truth on green/red balls and upright non-black POV.
