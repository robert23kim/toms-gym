
## Results (verified in production, build `v2026-08-29 16:40 UTC`)

Verification: `.playwright-mcp/verify2.js` (390×844; `?challenge=` waiting state
produced by intercepting `/lifting/result/*` → `processing`). `after-*.jpeg`
sit next to the `before-*.jpeg` captures.

| Moment | Before | After (prod, real data) |
|---|---|---|
| Result page, owner (pushup) | grade + breakdown, no rank | **"#2 of 5 · 4 reps to pass rob"**, ladder rob 39 / You 35 / caleb 20, **▲ New best · up from 11 reps** (Tom's Aug 1 attempt really was 11) |
| Result page, visitor | same page, no way in | "Where Toka stands", same ladder, **Beat this →** → `/challenges/…/upload` (only while the challenge is open) |
| Result page, plank (time) | — | "#4 of 7 · 37.8s to pass robert23kim · 37.8s from the podium · New best · up from 115.4s" |
| Waiting screen | spinner + ETA | + **"rob leads at 39 reps · 5 on the board"** |
| Completion | green check, "Analysis complete!" | **35 reps** (spring settle) → Grade C → ladder → "See your result" |

Gates: frontend **72 suites / 506 tests** (+16: standing additions 7,
ResultLadder 6, AnalysisStatus 3), `tsc --noEmit` clean. Backend untouched.

Commits on `main`: `90a58a9` (standing lib + ResultLadder), `64581b5` (result
page), `c3393f7` (status target + reveal + upload param), `5c4e22f` (pill wrap).

## Bug log (new this iteration; iteration 01's B5–B14 remain open)

| # | Where | Bug | Status |
|---|---|---|---|
| B15 | Units, app-wide | Challenge boards, the standing card and the result header print **lbs** for a value the upload form collects as **kg** (`metric.ts` documents the aliasing); the Hall of Champions and profile history print **kg** for the same numbers. The ladder follows the board it links to (lbs) so it is internally consistent — but the app is not. | Open — decide one unit, convert at the edge |
| B16 | `UploadVideo.tsx:138` | Direct uploads (`/lift/upload`, no challenge) post `competition_id: '1'`. Whatever the backend does with that, the status page then has no board to target (by design it shows nothing extra). | Open — confirm backend behaviour |
| B17 | Result page | Plank time is shown as `201.3s` on the result surfaces but `3:21` in the profile list and Hall of Champions. Same family as B15. | Open |
| B18 | Lost work, process | `lib/standing.ts` + `StandingCard.tsx` + their test already existed (challenge-page "Your standing" card, `a7b9ebb`); my first draft overwrote all three. Restored from HEAD, no code lost, but ~15 min burned. | Fixed — see retro |

## Retro

**Went well**
- The moment-first rule changed the output: every shipped item is something a
  person *feels* (a rank, a name to chase, a "new best"), and the real data made
  the copy land — "up from 11 reps" is Tom's actual August.
- One pure derivation (`standing.ts`) now feeds three surfaces (challenge page,
  result page, completion screen); 16 tests pin the copy.
- Route interception (`page.route`) verified the waiting state in production
  without uploading a video — the recipe for any transient state.

**Didn't**
- I wrote a new `standing.ts` without checking whether one existed; the Write
  tool's "updated" (not "created") was the only tell and I missed it until
  `git status` said `M`. **Check `git ls-files <path>` before creating a file
  with a generic name.**
- The completion-screen check used `innerText`, which returns CSS-uppercased
  text; the attribute selector (`section[aria-label^="Where"]`) is the robust
  probe. False negative cost one screenshot round.
- Ran two `tsc` passes in parallel with a file edit; one result was stale. Chain
  edit → check in one command.

**Change next time**
- Iteration 03 candidates from the idea list: welcome-back moment on
  `/find-profile` (P5), "best game since…" on bowling sheet confirm (P2), and a
  result-page cleanup pass (B5 bodyweight tips, B6 owner-only Re-analyze, B8
  page title) because those now sit *beside* the ladder and dilute it.
- Do the first real end-to-end upload with a fixture video on a throwaway
  account so the waiting → reveal sequence is seen live, not mocked.
