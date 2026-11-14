# 2026-11-14 Automatic lift type: rep-count guard, switch on, auto on the parallel pose workers

**Status first:** Automatic lift type is **on in prod** (`AUTO_LIFT_TYPE=1`, backend `my-python-backend-00199-tg7`, engine `bowling-service-00061-ram`). Blocked: the Change sheet click in Chrome (the tooling failed after sign-in), so Change and re-analyse are proven by API only. Not covered: no real athlete's Automatic upload was checked or observed (canary only; prod was not queried for one), no squat went through the backend, no phone and no phone width. Knee pushups read as a plank still score silently. Plank is not faster. `00061-ram` was deployed although Tom only asked whether a speedup existed.

Numbers, contract and proofs live in `docs/reference/auto-lift-type.md`; this file is the log.

## What this was
Tom asked why Automatic was missing from the upload form (the switch was off because the engine was not deployed, held back on review finding M4: silent confident misclassification). He then asked, in order: add the guard, rebase and deploy the engine, push and merge to `main`, switch it on, test on a practice board, look for a way to cut Automatic's analysis time without losing accuracy, delete the practice board and canary, clean up the leftovers. Previous session: `docs/sessions/2026-11-13-auto-lift-type.md`.

## What changed
**Engine** (`toka13902/bowling_app`, worktree `~/code/bowling-app/auto-perf-engine`)
- `feat/auto-lift-type-perf` = `feat/auto-lift-type` rebased onto `perf/engine-2026-11-13` `f198bac`.
- `7e0169c` rep-count guard: a rep count more than 2.5x the busiest joint's cycle count and at least 5 above it returns no detection plus `lift_type_rejected`, so the attempt stays `Auto` and the app asks. Deployed as `bowling-service-00057-qag` (image `auto-7e0169c`).
- `ffcc4de`, `f4d0059` (branch `perf/auto-parallel-pose`): the stoppable auto pass runs on the chunked pose workers; later-chunk workers run at nice 10 while a stop is possible. Deployed as `bowling-service-00061-ram` (image `auto-f4d0059`), 100% traffic. Rollback target `00057-qag`.
- Engine `main` fast-forwarded twice, now `f4d0059`.

**toms_gym** (`robert23kim/toms-gym`)
- `cdd76a9` `deploy.py` commits `AUTO_LIFT_TYPE=1`; `b146e43` `test_deploy_py_commits_the_switch_on` pins it. The env var was set on Cloud Run the same hour (new revision `00199-tg7`).
- Docs: `1eeae93`, `bca3ced`, `5299954`, `47862f9`, `216f10f` (reference doc, `CLAUDE.md` engine line and table row, superseded note in `docs/perf/2026-11-14-engine-perf-deploy.md`).
- `main` and `feat/100-club` both at `216f10f` before this file. The first push moved `main` about 112 commits, almost all earlier sessions' work.

**Prod data, created and removed the same day**
- Practice board `78167bbc-286d-401e-9153-acf393d53752` and a canary user: 9 Automatic uploads of Tom's own labelled clips (API, plus the site's upload form in Chrome at desktop width).
- Deleted in one transaction after a rolled-back dry run: 9 notifications, 9 results, 9 attempts, 1 `UserCompetition`, the user, the board (users 159 -> 158, competitions 8 -> 7), then 26 bucket objects.
- Cleanup: 810 objects in 48 `lifting/auto-proof-*` folders, Cloud Run tags `auto` and `autopar`, revision `bowling-service-00060-cix`.

**Cloud Run, same clip, explicit / auto on one worker / auto now**

| Clip | Explicit | Auto before | Auto now |
|---|---|---|---|
| Pushup | 23 s | 60 s | 26 s |
| Situp, 31 reps | 65 s | 154 s | 63 s |
| Squat | 19 s | 40 s | 23 s |
| 141 s plank misread as pushups (asks) | n/a | 231 s | 100 s |
| Plank, 82 s hold | 40 s | 50-63 s | 60-63 s |

## What we learned
- A pass that may stop early can still be chunked if the stop hook sees exactly the prefixes a sequential pass offers: the first chunk is true as it is read, so check it live; check later prefixes after the splice. Without nice 10 on the later workers the first chunk read at about two thirds speed and the plank prefix got slower.
- Lowering the confidence would not have closed M4: a sub-0.6 guess still carries the detected type and scores. The guard has to return no detection.
- The same engine call on one Cloud Run revision varied 49 to 74 s. Compare revisions with alternating runs, not one call each.
- Linux pose reads the 10 s plank fixture at 0.556 (macOS 0.86), so that fixture asks in prod.
- The first Cloud Run proof run proved nothing on 8 of 10 calls: the bench copies of the fixtures had been cleaned out of the bucket (404). Check the input object exists before reading a result.
- There is no admin override for a wrong type: `POST /attempts/<id>/lift-type` is 403 for anyone but the uploader. Fixing someone else's lift is SQL.
- "Log this week's lifts" opens a native file picker the Chrome tooling cannot drive; `/upload` works. After the upload signed in, clicks and screenshots failed with "Cannot access a chrome-extension:// URL of different extension".
- The Cloud SQL proxy left on port 5433 by an earlier session answers "network error"; a fresh proxy on another port works.
- Backend gate is `backend/tools/run_ci_tests.sh`; the venv has no coverage plugin, so run it with `PYTEST_ADDOPTS="-p no:pytest_cov -p no:cov"`.

## Still broken / next steps
1. **Knee pushups from the front quarter read plank at 0.91 and score silently.** A plank has no rep count for the guard to compare.
2. **No real athlete Automatic upload has been observed.** Read the first one's `ANALYSIS_TIMING` line and result page.
3. **Squat rests on one labelled clip** and never ran through the backend as Automatic.
4. **Change sheet in a browser, phone width and a real phone are untested.** Install the current APK on a phone.
5. **Plank is not faster and may be a few seconds slower**; Automatic still costs a plank about 20 s over explicit (the prefix pass).
6. The guard's threshold was chosen knowing its only positive example. The nice-10 tweak has no test of its own.
7. **Rollback order:** set `AUTO_LIFT_TYPE=0` before routing the engine to anything older than `00057-qag` (older revisions treat `auto` as bicep curl).
8. Three glasses-research commits from another session (`c6a2eba`, `66c42f7`, `d30b72f`) were already on the branch and went to `main` with this work.
9. Chrome was left signed in as the deleted canary on the gym site (not re-checked at save time): click "Forget Me". The stale proxy (PID 13926) still listens on port 5433 (`lsof` at save time).
10. Laptop only in toms_gym: `.claude/settings.json`, `frontend/.env.production`, 109 untracked files. Decision needed (Tom): which go up. Never the clips, sheets, pose caches or engine summaries under `docs/sessions/2026-11-13-auto-lift-type/`.
11. Outside `main`: engine `fix/squat-rep-count` (needs rebasing onto `f4d0059`); toms_gym `feat/analysis-pipeline-hardening`, `test`.
12. The proof scripts lived in the session scratchpad and are not preserved.

## Verification
- **Re-read at save time:** backend `00199-tg7` at 100% with `AUTO_LIFT_TYPE=1`; `GET /competitions/<100 Club>` returns `auto_lift_type_enabled: true`; engine `00061-ram` at 100% on image `auto-f4d0059` with the three perf env flags; practice board 404; `lifting/auto-proof-*` matches nothing (73 folders under `lifting/`); revisions listed are 00061, 00057, 00054, 00053, 00052; `git ls-remote` shows engine `main` = `perf/auto-parallel-pose` = `f4d0059` and toms_gym `main` = `feat/100-club` = `216f10f`; CI on toms_gym `main` green at `216f10f`.
- **Guard:** 11 of 11 mutations killed. On the 51 labelled clips it drops only the plank from the feet (162 against 38); widest gap on a correct clip is 39 against 21. On Cloud Run that clip returned no detection (164 against 40). The backend path that keeps a rejected lift pending was exercised offline, not in prod.
- **Explicit types unchanged:** squat, pushup, situp, plank reports on `00057` equal the `00054` proof apart from clip URLs; 4 explicit calls on `00061` equal `00057` the same way.
- **Parallel auto:** byte-identical summaries on 9 labelled clips on the laptop (4 workers vs 1) and on 7 auto Cloud Run calls against `00057`, apart from clip URLs; 9 of 9 mutations of the stop logic killed.
- **Engine tests:** 343 passed, 4 skipped on `tests/test_lifting tests/test_service_app.py tests/test_lift_summary.py` at `f4d0059`. The full suite was run at `7e0169c`: 9 failures, all bowling tests from the known failing set; no full run is recorded at `f4d0059`. The engine repo has no CI.
- **Backend gate:** 483 passed after the switch change.
- **Practice board:** detection, scoring, "Is this a plank?" Yes, pending-until-Change, Change re-analysis (13 reps, board 17.5 -> 30.5) and 403 / 400 / 409 all through the prod backend; one upload through the site's form in Chrome. Deletion checked by API 404s for the board, a result and the canary, and an empty bucket listing (earlier reads, except the board 404 above).
- **Not run:** everything in the status paragraph.
