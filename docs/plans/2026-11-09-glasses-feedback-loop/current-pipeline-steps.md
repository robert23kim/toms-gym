# Current pipeline: Meta-glasses session -> per-throw feedback video (as run 2026-11-08/09)

All times are America/New_York (the session transcript is UTC, 5 h ahead; file mtimes are local).

**Headline.** Last throw recorded 2026-11-08 11:51. Tom's first message about it: 2026-11-09 09:30 (about 21.6 h later). Video 1 in Drive: 15:40, so about **370 min** from his first message. Tom typed about 6 messages all day and did about 15 min of hands-on work. Nearly everything else was done by Claude agents making judgment calls on grid images. Those calls were not codified, so they cannot run unattended in a product. The round-4 rerun Tom asked for at 17:32 was still running at 17:59.

Actor tags: **[Tom]** = a human; **[agent]** = a Claude agent's uncodified judgment (manual for design purposes); **[script]** = code that already runs without judgment.
Evidence tags: **V** = verified from a file, a log or the session transcript; **I** = inferred.

## Steps

| # | step | actor | manual | wall min | evidence | what automating it needs now | fundamentally hard? |
|---|---|---|---|---|---|---|---|
| 1 | Record one clip per throw on the glasses (32 clips, 12-26 s, 10:47-11:51 on 11-08) | Tom | yes | ~64 (during play, about 5 s of effort per throw) | I: start/stop per throw is implied by "one throw apiece"; no source says how it was triggered | Continuous capture is impossible (glasses clip length limit, battery: I). Keep one clip per throw but make the clip boundary irrelevant (detect the release inside any clip). | no |
| 2 | Glasses -> phone import in the Meta AI app | Tom / app | yes | unknown | I: Tom's 09:30 message "now they are on my phone" | Meta AI app auto-import plus "save to camera roll" (I: app setting, unverified) | no |
| 3 | Gap until Tom is at the laptop | Tom | yes (latency) | ~1300 (21.6 h) | V: clip names vs. first message 09:30. Cause I: no phone path. At 09:31 he asked "is it possible to upload them to toms gym ... or is it better to do on the laptop" | A phone-side trigger (upload from the share sheet, or watch a folder) so nothing waits for a laptop session | no |
| 4 | Phone -> Google Drive upload of 32 files (1.0 GB) | Tom | yes | <=6 (done by 09:36; Drive still showed ".adding" names at 09:37) | V: 09:36 message; the `.adding`-suffix poll in the scratchpad `wait_drive.sh` | Camera-roll auto-backup to one Drive folder, or a direct signed-URL upload to Toms Gym (see the plumbing notes) | no |
| 5 | Ask Claude, paste the Drive link, approve the plan | Tom | yes | ~7 (09:30-09:37) | V: transcript | Not needed once 3 and 4 trigger the pipeline | no |
| 6 | Find and download the clips by Drive API (filtered on name `20261108_`, md5 duplicate check) | script (agent-typed curl) | no | ~4 (09:36:46 listing, files 09:39:43-09:40:26, dup check 09:40) | V: transcript tool calls, `drive_raw/drive_list.json`, file mtimes | Already scripted (gcloud token + Drive v3). Needs a durable script and a trigger. | no |
| 7 | Contact sheets, then start the `bowling-pov-session` workflow under `/loop` | agent | yes | ~3 (sheets 09:41-09:42, loop 09:43) | V: `/Users/toka/pov-2026-11-08/sheets` mtimes, transcript | Fixed entry point with args (`today`, clip dir) | no |
| 8 | Fix the judge rules before any tracker run (RULES.md) | agent | yes | in 7-9 | V: RULES.md | One-off. A product reuses the frozen J1-J5 code (`judge_rules.py`, `rules.py`, per the 17:40 amendment). | no |
| 9 | Run auto cuts v3 on the clips (frozen score: 4 right, 6 wrong, 15 null of 25) | script | no | ~20 (09:44-10:05, includes a September regression run) | V: `work/entries_v1` 09:49, `entries_v3` 10:05, cuts_notes section 1 | Already a script (`auto_cuts.py <src> [--release N]`) | **yes: release detection** |
| 10 | Read the release frame by eye on 24 of 31 throws from frame grids, add `--release N` and the v3.1 gate | agent | yes | ~36 (grids 10:13-10:28, final cuts 10:41) | V: `work/cuts/grids` mtimes, cuts_notes sections 2-3. "Eye" means a Claude agent reading `ov*/fn*/au*` grid JPGs, not Tom | Make it one LLM-vision call per clip on the grids `auto_cuts` already writes (release-6..+6 strip), with the answer validated against the audio pin hit. Or run detection over the whole clip after the tracker (the ball on the lane is easier to find than the release). | **yes**: walk-back blips, an upright POV where the ball appears already clear of the hand, head tilts. A "verified: true" wrong cut is invisible. |
| 11 | Ball colour per clip (on-lane sample), with 4 eye overrides | script + agent | partly | in 10 | V: cuts_notes section 5 | The script part exists. The overrides need a vision check or have to be dropped (the motion-only tracker does not need colour). | no |
| 12 | Game / bowler / frame map: clothing clusters, the lane 27/28 alternation, the overhead monitor names, pin counts against the boards | agent | yes | ~27 (10:44-11:11) | V: `work/structure` mtimes, structure_notes | Bowler: a per-clip LLM-vision classifier against two reference crops (person_A/B.jpg), plus a lane-alternation prior. Game and frame: an OCR or vision read of the overhead monitor when it is in view. Or Tom tags the wearer at capture (one voice note or tap per game). | **yes: bowler identity.** One pair of glasses is shared by two wearers and the file carries no wearer metadata. In game 1 the wearer never looked up at the board. The monitor says "Chris" while the brief says "Chardie". |
| 13 | Truth on 6 clips, quarantined | agent | yes | unknown (between 10:41 and 11:33; Q not opened by this agent) | V: README "Truth method" | **One-off research, not a recurring step** | n/a |
| 14 | Three ball-stage experiments, judged on truth, then the pick | agent | yes | ~65 (10:46-11:51) | V: `experiments/*` mtimes | **One-off research.** Consequence: no experiment reached `works`, so the recurring pipeline has no validated tracker (motion-only is `partial`, flagged). | **yes**: the tracker itself |
| 15 | Integrate `track_v3.py` (motion-only + per-clip fallbacks) | agent | yes | ~5 (11:50-11:55) | V: run_all start 11:55 | One-off. It is now code. | no |
| 16 | Tracker batch 1, 22 clips, laptop GPU (`--device mps`), serialized behind other torch processes | script | no | 21.6 (11:55-12:17; ~59 s per clip) | V: `work/run_all.done` wall_s 1298 | Runs only on the laptop. SAM 2 is ~46 of 58 s per clip (r4 log). Cloud `bowling-service` is CPU only (plank heavy model ~8.8 min on CPU; L4 GPU quota pending, from memory notes). Needs a GPU Cloud Run job or a laptop worker that watches a queue. | no (compute) |
| 17 | Judge round 1 (J1-J5), re-issued, amended at 12:50 after seeing the results | agent | yes | ~45 (12:20-13:04) | V: `work/judge_r1` mtimes, RULES amendments | The judge rules are code. What is manual is the agent deciding amendments and naming each rerun's change. A product runs the code judge and maps a fixed fail-class to its fallback. | partly: J2, the pin-row crossing |
| 18 | Rerun round 1 (12 clips) | script | no | 25 (13:01-13:26; ~124 s per clip) | V: `rerun_r1.done` wall_s 1490 | Same as 16 | no |
| 19 | Run the 9 clips a workflow filter had skipped | script (an agent noticed the gap) | no | 14.5 (13:26-13:40) | V: `run_missing.done` 872 s; RULES amendment | Bug, not a step: never filter stems on a free-text field | no |
| 20 | Judge round 2, all 31 | agent | yes | ~25 (to 14:03) | V: `work/judge_r2_all` mtimes | Same as 17 | partly |
| 21 | Rerun round 2: smoke 5 clips, then the "rest" 10 (that batch was only launched after an agent found it had never run) | script + agent | partly | ~50 (14:20-14:34, 14:42-15:10; ~165 s per clip) | V: `.done` files 823 s and 1681 s; transcript message at 14:41 | Same as 16 | no |
| 22 | Judge round 3 (two concurrent judges overwrote each other's files) | agent | yes | ~50 (14:23-15:14) | V: `work/judge_r3` mtimes, transcript 15:14 | One judge process, in code | partly |
| 23 | Render `session.mp4` (paths, the VIDEO_ONLY list and the group order are hard-coded in the script), critic pass, must-fix items, re-render | script + agent | partly | ~23 (render log 15:21, final 15:37) | V: `make_session_video.py` header (no argparse), render_notes | Script it: take `session_map.json` and `judged_final.json` as arguments and derive VIDEO_ONLY from the judge. The critic's must-fix items are now rules in the renderer. | no |
| 24 | Upload the video to Drive (resumable Drive API) | script (agent-run) | no | ~2 (15:40) | V: transcript 20:40Z. The script `drive_upload.sh` lives in the session scratchpad, which is reclaimed, so it is **not durable**. Correction to the brief: the video was not uploaded back by hand; the Drive scope was granted by Tom's one-time `gcloud auth login --enable-gdrive-access` (11-07 session doc) | Move it into the repo | no |
| 25 | Tom watches it and asks why so many throws have no ball line | Tom | yes | ~3 (17:29-17:32) | V: transcript | Show the fail reason per throw in the video (already partly on the cards) | no |
| 26 | Round 4 rerun (pin-row extrapolation, over the rerun budget) and a re-render | script + agent | partly | >=20 (17:39, still writing at 17:59) | V: `work/rerun_r2_r4.log` mtime | Same as 16 and 23 | yes (J2) |

Times are mostly the gap between the first and last file a stage wrote. Stages overlapped: experiments ran alongside the structure stage.

## Tracker compute (measured)
- Five batches before round 4 took 6164 s, about **103 min** of tracker wall time.
- Per clip: 59 s in the first pass, 97 s for the missing 9, 124 s in rerun 1, and about 165 s in rerun 2. The brief's "about 3 min per clip" matches the reruns, not the first pass.
- Across the 116 per-clip log lines: median 71 s, max 273 s.
- Per-clip wall time includes the "wait for other torch process" spin. That is a serialization cost, not compute.

## Existing Toms Gym plumbing (verified by reading the code)
- `POST /bowling/upload` (`bowling_routes.py:32`) takes a multipart upload of one video per attempt, with `competition_id` required. It goes through `blob.upload_from_string(file.read())`, so it passes through Cloud Run's 32 MiB request cap. These clips are 27-50 MB, so most would fail (I: not tried).
- It has no session or batch concept and no bowler-per-clip field. It queues `enqueue_analysis_job('bowling', id)`.
- The signed-URL direct-to-GCS upload exists only for lifting (`upload_routes.py:183`).
- `bowling-service` (analysis-engine on Cloud Run) runs the older bowling analyzer. None of the POV tracking (`track_v3`, SAM 2, motion-only) is deployed. The POV engine branch `exp/r2-glasses-pov` is unmerged.
- Annotation, reanalyze and lane-edge routes exist (`/result/<id>/annotation/*`, `/reanalyze`, `/lane-edges`). They could carry a per-throw correction UI (for example a release-frame tap) in place of agent eye-reads.

## What is fundamentally hard (not just unbuilt)
1. **Release detection.**
   - The colour-free v3 got 4 right, 6 wrong and 15 null on 25 untouched clips.
   - Every wrong cut said `verified: true`.
   - The v3.1 gate is post-hoc with no holdout.
   - Failure modes: walk-back blips near the clip end, head tilts, and the upright POV where the ball never crosses the frame bottom in the hand.
2. **Bowler identity.**
   - Two wearers share one pair of glasses, and the clip carries no wearer field.
   - It was inferred from clothing, stance, ball, lane alternation and the monitors.
   - Game 1 had no board read.
   - The scoreboard name ("Chris") differs from the brief ("Chardie").
3. **The tracker itself.**
   - Nothing reached `works`.
   - J2 (the pin-row crossing) is the dominant fail, and 13 of 31 throws render with no line.
   - The stage that consumed the most agent time (judge and reruns) exists to compensate for this.

## Three biggest manual time costs (wall clock, within 09:30-15:40)
1. **Judge, amend, rerun loop, about 3 h (12:17-15:14).** Three judge rounds by agents, rule amendments, two rerun batches, a skipped-9 workflow bug and a batch that was never launched. Round 4 at 17:39 added more.
2. **Release eye-reads plus the game/bowler map, about 87 min (09:44-11:11).** This is agent vision on frame grids standing in for a release detector and a wearer ID that do not work.
3. **Waiting for Tom to start from a laptop, about 21.6 h of latency (I: cause), though only about 15 min of his labour.** Steps 2-5 (phone import, Drive upload, the Claude prompt) gate everything. This is the number "faster" is mostly about.

The render, critic and re-render pass (~23 min) comes next. The one-off research stages (truth plus experiments, ~65+ min) would not recur in a product.
