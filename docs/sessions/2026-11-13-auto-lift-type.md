# 2026-11-13 Automatic lift type, change-and-reanalyse, remembered identity

**Status first:** deployed (backend 00198-8kd, frontend 00207-h4l, APK `/s/zFFWCs`, migration 020 ok) but **switched off** (`AUTO_LIFT_TYPE=0`) and the **engine was not deployed** (prod `bowling-service-00053-fxm`, no auto support). Nothing was blocked and no gate target was skipped. Not exercised in prod: a real automatic upload, a real re-analysis, the owner 403 branch (switch gate answers 400 first), APK on a real phone. Engine finding M4 (silent misclassification guard) is deferred.

## Asked
Athletes should not have to pick a lift type; let them fix a wrong guess; stop forgetting who they are. Design: `docs/plans/2026-11-13-auto-lift-type.md`.

## Decisions
- Switch gates everything (Automatic, Change, re-analyse) so the code can ship ahead of the engine.
- Auto attempts never score until a type is set; missing detection leaves the attempt Auto.
- Change checks the switch and board eligibility before the owner (400 before 403).
- Engine classifies only situp, pushup, squat, plank, rule-based on the tracked pose.
- Identity goes through one module with a native Preferences mirror.

## Shipped
Migration 020; Auto insert guards; dispatch and completion write; change endpoint; scoring exclusion; Automatic pickers; result line and sheet; `lib/identity.ts`, email pre-fill, phone Forget Me, Preferences mirror; engine classifier on `feat/auto-lift-type` (undeployed); new APK. Reference: `docs/reference/auto-lift-type.md`.

## Verified, and what was not covered
- Live board unchanged against the pre-run snapshot (only `days_left` differs); no rows created, no videos uploaded. Switch-off API and browser state proven at 390 and 1280 with a positive control; Auto POSTs rejected 400; unknown attempt 404.
- Result line states, Change body and queued state proven with stubbed GET/POST on the prod bundle, not a real re-analysis.
- Engine: 48/51 on a labelled set (held-out 29/32); explicit-type output sha256-identical on 5 clips. Not covered: squat (one clip), other 44 clips on Linux pose, real GCS and Cloud Run.
- Backend SQL ran on a throwaway Postgres (7 tests), not prod beyond the migration columns.
- Emulator: identity survives restart, restores from Preferences, Forget Me clears both. Not a real phone.
- Prover's "E" claim was refuted as too broad (two pre-existing layout defects).

## Still broken
- Two silent engine misses (plank from the feet read pushup at 1.00; knee pushups read plank at 0.91). Decision needed (Tom): ship relying on Change, or add a rep-count vs cycle-count guard first.
- Pre-existing: `/profile` overflows at 390 with a long email handle; `/challenges/<id>/upload` submit under the tab bar; Upload Another opens the form on Squat; status page says "YOUR PUSHUP" to strangers; phone Forget Me is 84x20 with no confirm.
- A first-boot migration lock timeout would 500 result endpoints on that instance until a later boot.

## Retro
- Went well: a QA, review, fix, prove, refute chain caught gate-order, lock and Auto-in-profile bugs before prod; mutation checks on every guard; switch-off deploy kept the live club untouched.
- Did not: engine eval is small (51 clips, one squat) and its silent misses surfaced late; the 403 branch is unprovable in prod by design; prove round 1 missed the BowlingChallenge pre-fill.
- Next time: label more squat clips before building a classifier; decide the "ask when unsure" guard in the design doc; put the owner check before the switch gate only if a prod proof needs it.
