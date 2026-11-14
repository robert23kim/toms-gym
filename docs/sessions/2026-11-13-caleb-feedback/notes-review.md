# Review: C1/C2 frontend (5ef44cb..ab3c2ee) and C3 engine (feat/situp-config..73852de)

Reviewer, 2026-11-13. Read-only. Did NOT run jest (QA owns it).

## What I ran, and what it does not cover
- `npx tsc --noEmit` (root): rc 0, but frontend/tsconfig.json has `"files": []`, so it checks nothing.
- `npx tsc --noEmit -p tsconfig.app.json`: rc 2, 43 errors, none in a changed file (grep on ChallengeDetail|YouRow|FindProfilePage|metric|ConsistencyHero|liveClubBoard returned nothing). `include: ["src"]` covers __tests__, so the new tests are type-checked. The doer's "43 = baseline" is not evidenced: tsc-baseline.log is 0 bytes and notes-gate.md records only the vacuous root rc 0.
- Engine: my own run was `pytest tests/test_lifting/test_squat_real_footage.py` in squat-engine, 8 passed. That ran on the committed keypoint fixture, not the video.
- The 12 before and 10 after come from the doer's artifacts (c3/prod-image/before_e2e.json total_reps 12, after_e2e.json 10), which I read. I did not re-run the prod image.
- I opened two contact sheets:
  - caleb_0.jpg shows the walk-in at 1.75-4.5 s; he faces the camera at 4.75 s.
  - caleb_4.jpg shows squat bottoms at 24.0 and 26.0 s and the walk-out from 27.0 s.
  - Together they confirm the two spurious windows and the last two squats. They do not give an independent count of 10.
- Not re-run: the pushup/situp/plank before/after comparisons and the whole engine suite.

## Frontend
C1 does what the bug log asks:
- With no viewerId, the row is `you-row-unknown`, a link to `/find-profile?next=/challenges/<id>`.
- With a viewerId but no row, it says "Not logged yet", or "Analysing your upload…" while an attempt is processing.
- The inline board form now saves `data.user_id` only when nothing is stored, and never overwrites a different stored id (ChallengeDetail.tsx:241-246). The board row is matched on `viewerId` (ChallengeDetail.tsx:867-870), so a viewer who already has a stored id is never re-pointed.
- Signed-in users keep their userId (`setTokens` in auth/tokenUtils.ts:19-23 writes it), so they render as before. Logout and Forget Me both do a full reload (AuthContext.tsx:152, Navbar.tsx:22).

- R1 (major) Legacy boards changed for anonymous viewers.
  - ChallengeDetail.tsx:1039-1048 applies the Find-profile row to every metric, not just consistency. The legacy "Plank Off" test (ChallengeDetail.consistency.test.tsx ~line 250) was edited from `you-row` data-entered=false to `you-row-unknown`, and the notes do not call this a legacy change.
  - The row that used to be a one-tap upload now sends a brand-new visitor round a loop: "Find your profile", then not found, then "Upload something" (FindProfilePage.tsx:164 goes to `next`), back on the board with the same row and no form open.
  - The header CTA (ChallengeDetail.tsx:772) and the mobile sticky CTA (~1180) still upload.
- R5 (major) Identity adoption from the inline form is sticky and then drives writes.
  - On a device with no stored id, the email typed in the board form is adopted (ChallengeDetail.tsx:243-245), even if it is a friend's or a typo (the backend creates the user).
  - After that, PromptList.tsx:147 and UploadVideo.tsx:148 post `user_id` with no email prompt. Later lifts from Home or /upload are silently logged to that person on the live scored board.
  - Before this change, a device that only used the board form asked for an email on every upload. UploadVideo.tsx:157 already adopted, and overwrote, so this is the same class of risk extended to one more path, not a new one.
  - It never re-points a viewer who already has an id.
- R2 (minor) The copy does not state the tie rule. metric.ts:69 says "Log more of a lift type than anyone else", and ConsistencyHero.tsx:348 says "Each type you log more of than anyone else". But consistency.py:231-238 gives ties at the top a shared bonus, and docs/reference/100-club.md still says "Ties at the top share a bonus". Otherwise the rule is right: extra per type led, not required for the quota, any mix fills the quota, locks when the week ends.
- R3 (minor) The cap in metric.ts:65 is `type_bonus * liftTypes.length`, but the backend scores `lift_types ∩ COUNTED_LIFT_TYPES` (consistency.py:180-181). A club listing a type that does not count would overstate "up to +N". The live club has the 4 counted types, so +100 is right today.
- R4 (minor) viewerId is now frozen at mount (ChallengeDetail.tsx:95-97). Before, it was read on every render. Every current identity-clearing path reloads the page, so I found no live impact. Note it for future in-page sign-out.
- R6 (minor) The root cause for the reporter himself is not proven. The notes show the inline form dropped user_id, but not that Caleb used that path. The APK/browser localStorage split fits his symptoms just as well. The unknown-viewer prompt covers both.
- R7 (minor) FindProfilePage.tsx:98-105 labels any `next` as "Back to the challenge →". Only the board builds `next` today. The guard `/^\/(?![/\\])/` (line 31) plus a react-router Link is fine.
- R8 (minor) Privacy:
  - frontend/src/__fixtures__/liveClubBoard.ts:45-46,134,157 commits the friend's production user_id and board name (his email local part).
  - The engine fixture squat_walk_in_out_real_keypoints.npz is his body pose (disclosed by the doer).
- R9 (minor) docs/reference/100-club.md:16 reads awkwardly ("on top of a quota any mix fills").

Wording elsewhere: nothing else words the bonus. A grep of frontend/src and backend found only clubBreakdown field names and the hero line "if the lead holds".

## Engine
The rule is in rep_segmenter.py:79-131, enabled at config.py:132 inside the "squat" block (126-139). No other config copies the squat dict. A rep is dropped only when both hold:
- the other knee bends less than half as much as the counted knee, and
- the ankle midpoint travels more than 0.25 leg lengths.

A NaN on either test keeps the rep. That is a general biomechanical test, not a frame-index hack, but both thresholds come from one clip.

The new tests assert real things: 10 bottoms within 0.35 s of hand-marked times, nothing before 4.65 s or after 27.1 s, and keep/drop on synthetic cases. Pushup, situp and plank do not read the key. The doer reports byte-identical before/after for them; I did not re-run that.

- E1 (major, deploy gate) labelled_set_size is 0. The reporter's clip is the only squat ever analysed, so the regression check cannot fail. Not deployable under the contract. Decision needed (Tom).
- E2 (minor) Untested failure mode: a side-on squat where the pose reads the occluded far leg as straight AND the camera moves (handheld or panning) meets both conditions, so real reps would be dropped (rep_segmenter.py:122-125).
- E3 (minor) The drop runs after the "more reps wins" view choice (analyze.py:306-316). Strides can still decide which view wins.

engine_deploy_ok = false.
