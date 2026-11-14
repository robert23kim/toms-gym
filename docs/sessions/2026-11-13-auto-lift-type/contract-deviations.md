# Contract deviations / clarifications (auto-lift-type run)

## backend (doer), written before coding, 2026-11-14

None of these change a field name or shape; they pin semantics the contract left open.

1. "All bodyweight" for Auto eligibility = every declared lift type is Pushup, Situp or Plank,
   and in `mode == "consistency"` (The 100 Club) Squat also counts as bodyweight (club squats are air
   squats). So the club (Situp, Pushup, Squat, Plank) IS eligible; a non-consistency board with Squat
   or any weighted lift is NOT.
2. `GET /competitions/<id>` -> `competition.auto_lift_type_enabled` is true only when
   `AUTO_LIFT_TYPE=1` on the backend AND the competition is eligible per (1). The frontend can rely
   on this flag alone; it should not re-derive eligibility (its `isBodyweightLift` excludes Squat
   and would hide Automatic on the club).
3. `needs_lift_type` = attempt `lift_type == "Auto"` AND analysis is not `queued`/`processing`
   (i.e. completed, failed, or never queued). Carried on both `GET /lifting/result/<attempt_id>` and
   `GET /competitions/<cid>/participants/<uid>/attempts/<aid>` (the latter because /lifting/result
   is 404 before a result row exists). Low confidence (< 0.6) does NOT set needs_lift_type: the attempt
   already carries the detected type; the UI asks from `lift_type_confidence < 0.6`.
4. `GET /lifting/result/<attempt_id>` additionally returns `lift_type` (the attempt's current type),
   additive, so the result page can render "Counted as ..." without a second call.
5. Idempotent path of `POST /attempts/<id>/lift-type` (same type, completed result) also writes
   `lift_type_source='user'` and clears `lift_type_confidence` (this is the "Yes" dismiss), returns
   `{status: "unchanged"}` and does not re-queue. Same type with a failed or missing result re-queues.
6. `PUT /attempts/<id>` rejects `lift_type: "Auto"` with 400 (design: do not extend PUT).
7. A type change sets `Attempt.status = 'pending'` while re-analysis runs, so the board shows it as
   pending instead of silently scoring 0.

## Engine (engine doer, branch feat/auto-lift-type in /Users/toka/code/bowling-app/auto-engine)

Nothing below changes a field name or type in the wire contract. These are the points where the contract or the design doc is silent or cannot be met as written.

1. **Plank needs a second pose pass (design doc: "no second pose pass").** The plank analyzer runs its own heavy-model pass at 15 fps on 8 parallel workers; the rep lifts use the full model on every frame. The two cannot share a track without changing plank scores. In auto mode the classification pass stops as soon as a hold is recognised (bounded prefix of the video), then the unchanged plank analyzer runs. Situp, pushup and squat reuse the single pass.
2. **New summary keys only in auto mode.** `detected_lift_type`, `lift_type_confidence`, `lift_type_scores` are added to the summary only when the request said `lift_type: "auto"`. An explicit lift type returns exactly today's summary (no new keys), so read them with `.get()`.
3. **`report.lift_type` in auto mode is the detected type** (engine name, lowercase: `situp`, `pushup`, `squat`, `plank`), same value as `detected_lift_type`. A low-confidence guess (below 0.6) still runs the full pipeline for the best guess, so the result is ready if the user answers Yes.
4. **No detection (`detected_lift_type: null`)**: HTTP 200 with `report = {"lift_type": "auto", "detected_lift_type": null, "lift_type_confidence": 0.0, "lift_type_scores": {...}}`, `annotated_video_url: null`, `summary_url` set. No rep or plank fields. Happens only when no usable body pose is found or none of the candidates is a type the classifier knows.
5. **Candidates**: names are matched case-insensitively with spaces or hyphens as underscores. Names the classifier does not know (anything other than situp, pushup, squat, plank) are ignored and never returned. `lift_type: "auto"` with a missing or empty `candidates` is a 400.

## Frontend (doer: frontend impl)
- F1 "all-bodyweight" rule (the contract does not define it). Frontend offers Automatic when `auto_lift_type_enabled === true`
  AND the challenge has >= 2 lift types AND every type is in {Plank, Pushup, Situp}, or the challenge is `mode: "consistency"`
  and every type is in {Plank, Pushup, Situp, Squat} (club squats are air squats, weight 0). With the backend's existing
  `BODYWEIGHT_LIFT_TYPES = {pushup, situp, plank}` alone the 100 Club (Situp, Pushup, Squat, Plank) would never qualify.
  Backend should accept `Auto` on the same rule. Code: frontend/src/lib/autoLiftType.ts `offersAutomatic`.
- F2 `auto_lift_type_enabled` is read from `data.competition.auto_lift_type_enabled` OR top-level `data.auto_lift_type_enabled`
  (GET /competitions/<id> returns `{competition: {...}}`); only a literal `true` counts.
- F3 `lift_type_source`, `lift_type_confidence`, `needs_lift_type` are read from GET /lifting/result/<attempt_id> first, then
  from GET /competitions/<cid>/participants/<uid>/attempts/<aid> (`.attempt` or top level) as fallback.
- F4 Auto uploads post `weight: "0"` (Auto is not in the backend weight guard's set, so the client never relies on it).
6. **For the prove step (engine doer, after the eval):** the plank fixture `backend/tests/fixtures/test_video_plank_10s.mp4` is detected as `plank` at confidence 0.86 with macOS pose but **0.56 with the production Linux image's pose** (measured offline in `gcr.io/toms-gym/bowling-service:situp-13b49b5`), i.e. just under the 0.6 confirm threshold. A canary upload of that fixture with Automatic should therefore expect `detected_lift_type: "plank"` with the "Is this a plank?" prompt, not the silent "Counted as" line. A longer plank clip reads 1.00 on both.
7. The engine branch is `feat/auto-lift-type` (4 commits on top of `feat/situp-config` 93378b0), not pushed, not built, not deployed. Until it is deployed the live engine treats `lift_type: "auto"` as an unknown type and falls back to bicep-curl analysis, so `AUTO_LIFT_TYPE` must stay `"0"`.

## Fix pass (fixer, 2026-11-14)
8. `POST /attempts/<id>/lift-type` answers 400 "Changing the lift type is not available on this challenge" unless
   AUTO_LIFT_TYPE is on and the board is eligible (checked after 404, before 403). With the switch off nothing changes.
9. Eligibility (backend `eligible()`, and so `auto_lift_type_enabled`) needs two or more declared types, the same rule as the frontend's `offersAutomatic`.
10. 409 also when the shared re-queue helper finds the analysis in progress (rolled back, nothing enqueued, Attempt unchanged).
11. The result pages show the lift type line only when `auto_lift_type_enabled` is true (GET /competitions/<id>).
