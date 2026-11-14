# Automatic lift type, fix-it-after, and a remembered identity

Date: 2026-11-13. Asked by Tom after Caleb's feedback ("Is the vision smart enough to figure out what exercise type without me specifying? Less clicks good").

## What Tom asked for

1. Lift type is **Automatic by default**; the user can still pick one.
2. After analysis the user can **change the lift type and re-analyse**, so a wrong guess (or a wrong manual pick) is fixable.
3. The APK (and the web app) **remembers who you are** and **pre-fills the email**, so it is never typed twice.
4. All of it has to **fit the existing app design**: same components, same tone, phone first.

## Scope

- v1 covers bodyweight challenge uploads, i.e. The 100 Club (candidates = the challenge's own lift types: Situp, Pushup, Squat, Plank). The candidate set always comes from the competition, never a hardcoded list.
- The generic weighted `/upload` page keeps its manual picker (weight depends on the lift, and a wrong guess on a PR is what Caleb warned about). Not in v1.
- Bowling and golf untouched.

## 1. Automatic lift type

### Frontend
- Every lift-type picker reachable for a club upload (find them all: the challenge upload block in `ChallengeDetail.tsx`, `UploadVideo.tsx` when opened with a `competition_id`, the camera-first capture flow in `docs/reference/easy-upload-flows.md`, `LiftHub`) gets a first option **Automatic**, selected by default, with one helper line: "We'll work out the lift from your video. You can change it after."
- The manual options stay exactly as they are. The last explicit choice is not remembered: Automatic is the default every time.
- With Automatic the weight field stays hidden (all candidates are bodyweight). If a challenge has any weighted lift type, Automatic is not offered there.
- Sends `lift_type: "Auto"`.

### Backend
- Migration **020** (inline startup migration in `app.py`, same pattern as 019): add `Auto` to the lift type enum; add `Attempt.lift_type_source` text not null default `'user'` (`'user' | 'auto'`), and `Attempt.lift_type_confidence` real null.
- Upload paths (all insert sites, the same ones the weight guard covers) accept `Auto` only when the competition's lift types are all bodyweight; otherwise 400 with a clear message.
- Dispatch passes `lift_type: "auto"` and `candidates: [...]` (the competition's lift types) to the engine.
- On completion, the result handler reads `detected_lift_type` + `lift_type_confidence` from the engine summary and sets `Attempt.lift_type` to the detected type, `lift_type_source = 'auto'`. If the engine returns no detection, the attempt stays `Auto` and the result is marked `needs_lift_type` (see fix-it flow).
- **Scoring invariant:** an attempt whose lift type is still `Auto` scores nothing and is counted as pending everywhere (`services/consistency.py`, `_leaderboard_payload`, type leaders, profile history). It can never be counted as a default lift. Add `Auto` to `_prow`-style tests in the same change.

### Engine (`~/code/bowling-app/analysis-engine`, clean worktree, never `deploy.sh`)
- New branch `feat/auto-lift-type` in a clean worktree.
- `lift_type == "auto"`: run pose once, classify among `candidates`, then run the normal pipeline for the detected type on the same pose track (no second pose pass). Summary gains `detected_lift_type`, `lift_type_confidence` (0..1), `lift_type_scores` per candidate.
- Classifier is rule-based on the tracked pose, no new model: torso orientation (upright vs horizontal), prone vs supine, and which joint cycles (knee flexion = squat, elbow flexion while prone = pushup, hip flexion while supine = situp, horizontal with no cycles = plank).
- An explicit `lift_type` behaves byte-for-byte as today.
- **Ship bar:** labelled set = every club attempt video in production (the user-chosen lift type is the label; fetch read-only; include uploaded-but-never-analysed videos and legacy squat uploads) plus engine fixtures. Target at least 20 clips. Accuracy >= 90 % overall and every miss either below the confirm threshold or explained. Run 1 found only ONE analysed squat clip in production, so a per-type minimum cannot be demanded: report the per-type clip counts and accuracy in the first line of the notes, and name every type with fewer than 3 clips as "thinly tested". A wrong guess is recoverable by design (section 2), which is why thin coverage does not block the deploy; accuracy below the bar does.
- **Switch:** the backend reports `auto_lift_type_enabled` on the competition detail payload, from the non-secret env var `AUTO_LIFT_TYPE` in `deploy.py` (`"1"` only if the engine with auto support is deployed, else `"0"`). The frontend offers Automatic only when it is true and the challenge is all-bodyweight; otherwise the picker is exactly as today. The backend rejects `Auto` uploads when the switch is off.
- Base branch for the engine work is `feat/situp-config` (what production runs). The squat stride fix on `fix/squat-rep-count` is NOT included: it is waiting on Tom's decision.

## 2. Change the lift type and re-analyse

- New `POST /attempts/<id>/lift-type` body `{lift_type, user_id}`:
  - 404 unknown attempt; 403 unless `user_id` is the attempt's owner (the app's optional-auth model: same trust level as upload); 400 unless `lift_type` is one of the competition's lift types (never `Auto`); 409 while an analysis is queued or processing.
  - Sets `lift_type`, `lift_type_source = 'user'`, clears confidence, applies the bodyweight weight guard, and re-queues analysis through the same code path as `POST /analyze/<attempt_id>` (extract the shared function, do not duplicate the SQL).
  - Idempotent: same type as current and a completed result returns 200 without re-queueing.
- Do not extend `PUT /attempts/<id>` (it nulls every field not sent).
- Frontend, on the result surfaces (`AnalysisStatus.tsx`, the challenge video page, `ConsistencyResult.tsx`): a single line under the title, e.g. "Counted as **Pushups** · Automatic" with a **Change** control, owner only (viewer's `userId` equals the attempt's user). Change opens the existing picker style as a sheet, lists the competition's lift types, and on confirm calls the endpoint and drops the page back into its existing analysing state. Manual picks show "Counted as Pushups" + Change, no "Automatic".
- Low confidence (below the confirm threshold) or `needs_lift_type`: the same line becomes a prompt, "Is this a pushup?" with Yes / Change. Yes just dismisses (stores nothing server-side beyond `lift_type_source = 'user'` via the endpoint's idempotent path).
- Leaderboard caches must reflect a type change after re-analysis (check the in-process TTL cache noted in `competition_routes.py`).

## 3. Remembered identity and pre-filled email

- One module `lib/identity.ts` owns identity: `getUserId()`, `getEmail()`, `remember({userId, email})`, `forget()`. Every existing `localStorage.getItem/setItem('userId')` call site moves to it (no behaviour change), and "Forget Me" calls `forget()`.
- `remember` is called wherever identity becomes known: upload responses, Find Profile, sign-in, magic link, registration, and after a profile fetch (which gives the email for a known `userId`).
- Every email input (upload, find profile, sign-in, feedback, bowling and golf uploads) is pre-filled from `getEmail()`; still editable. Where `userId` is known the email field stays hidden as today.
- Never overwrite a different remembered `userId` silently: if an upload by email resolves to a different user, the new identity wins only because the user typed that email, and that is the one case allowed.
- APK: WebView localStorage has been lost before (`docs/reference/android-app.md`). Mirror identity to `@capacitor/preferences` (native, survives WebView storage clears and app updates): write-through on `remember/forget`, restore into localStorage on boot before the router renders when localStorage has no `userId`. Web builds skip the plugin (`Capacitor.isNativePlatform()`). Requires `npx cap sync` and an APK rebuild + publish.
- This builds on whatever identity gaps the 2026-11-13 feedback run closed (`docs/sessions/2026-11-13-caleb-feedback/notes-fix-frontend.md`); read it first and do not undo it.

## 4. Design fit

- Phone first at 390x844, then 1280. Use what exists: the picker/segmented control already used for lift type, `StatusPill`, the chip style of the "weeks" toggles, the blue highlight of `YouRow`, the dark card surfaces. No new colours, fonts or icon sets.
- Copy: one short line each, sentence case, same voice as the club page.
- Automatic must not add a tap: the shortest upload path is pick video then submit.
- Screenshots of every changed surface at both widths go to the notes dir and are reviewed against a screenshot of an unchanged neighbouring screen.

## Tests and gates

- Backend: `tests/test_lift_type_auto.py` (upload accepts/rejects Auto, completion writes the detected type, Auto scores nothing, change endpoint 200/400/403/404/409/idempotent, re-queue), registered in `tools/run_ci_tests.sh`; `_prow` updated.
- Frontend: picker default, payload `Auto`, result line in its three states, owner-only Change, identity module, email pre-fill on each form, Preferences restore (plugin mocked at the module boundary only).
- Engine: classifier unit tests per type, the labelled-set eval script with its table committed, existing suite unchanged.
- Every new guard is mutation-checked.

## Proof in production

- Never touches a real athlete's row. Canary: an `is_test` user created for the run, uploading a fixture clip with Automatic to the club, then changing its type and re-analysing, then SQL cleanup. This needs Cloud SQL access; if the gate says it is not writable, create NO rows in production: prove the flow with scripted browser sessions whose writes are stubbed, the deployed engine called directly on a scratch object, and the route tests, and say plainly that a real end-to-end upload was not exercised.
- Browser proof with scripted Playwright at 390 and 1280: Automatic is the default, the result line shows the detected type, Change re-analyses, email pre-fill from a remembered identity, empty-storage first run.
- APK: the built APK contains the Preferences plugin and the new bundle; identity restore is exercised in the emulator smoke test from `docs/reference/android-app.md` if the emulator is available, otherwise stated as not covered. Installing on a real phone is not covered.

## Out of scope

- Automatic on weighted lifts and the generic `/upload` page.
- A learned classifier.
- Re-analysing any existing attempt.
