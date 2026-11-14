# 2026-11-13: Caleb's feedback on The 100 Club (group chat screenshots)

Source: three screenshots Tom pasted on 2026-11-13. Caleb = user b7bb417c-9407-42c5-9cee-be7816d03f13 (board name caleb.li.larson), rank 1, 375 pts, 14 attempts, this week 147/125 at the time of writing.

## C1. "Not logged yet" after he submitted (frontend)
His screenshot of /challenges/<club> shows himself on the podium at 375 pts and, below it, the YOU row saying "Not logged yet". "made me think it wasn't working for a second".
Known: `ChallengeDetail.tsx` derives the viewer from `localStorage.userId` only (line ~95); `YouRow entered={false}` renders "Not logged yet" whenever no leaderboard row matches, including when there is no viewerId at all. The live board has his row and `pending: 0`, so his browser had no (or a different) userId: this is an identity gap, not an analysis delay.
Fix wanted:
- (a) Root cause: find every path by which someone can upload to the club and land back on the board without `localStorage.userId` set (challenge upload flow, camera-first capture, email-based upload, AnalysisStatus / completion-email / share links opened in another browser, the APK WebView vs the browser, MagicLink). Only `UploadVideo.tsx:158`, Login, FindProfile(+Page), GolfUpload and MagicLink call `setItem('userId')`. Close each gap that can be closed in the frontend (for example: persist the id from any upload response; links in the completion email / status page that carry the user's identity should establish it). Name the gaps that cannot be closed.
- (b) Honest empty state: with NO viewerId the row must not claim "Not logged yet". Show a prompt that says the app does not know who they are and leads to Find Profile (returning to this board), with `data-testid="you-row-unknown"`. With a viewerId but no row: keep "Not logged yet", or "Analysing your upload…" when the viewer has a processing attempt.

## C2. "Most of a lift type in a week: +25." is confusing (frontend copy)
He read it as "spread the 100 evenly across the 4 lifts", not "an extra 25 for leading a type". Source: `components/challenge/metric.ts:199` (`consistencyNote`). Reword so it is unmistakably a bonus for doing more of one lift type than anyone else that week, per type (so up to 4 x 25), and that it is extra, not a requirement for the 100. Grep every other place the rule is worded (ConsistencyHero, clubBreakdown, ConsistencyMeta, the bonus-lock line "Type bonuses (+25 each) are added when the week ends on Sunday.", share text, docs/reference/100-club.md, the Competition description in prod if the copy is stored there: read-only, report it, do not edit the live row) and make them agree. One short line each.

## C3. Squat counted 12, he did 10 (analysis engine)
Attempt f47a8848-dba0-42ce-9f31-7ef9ac585fbd (lift_type squat, total_reps 12, grade D, 2026-11-12T16:55Z). "Maybe it was the angle."
Wanted: reproduce 12 on his clip with the engine prod runs (unmerged `feat/situp-config`), find which two reps are spurious and why, fix the counter, show 10 on his clip. Deploy the engine ONLY if (1) the miscount reproduces locally, (2) the fix gives 10, and (3) a labelled set of other squat clips (at least 3 with known true counts) shows no count change for the worse. If no such set exists the regression check cannot fail: ship nothing to the engine and report "Decision needed". Never re-analyse or edit his live attempt; report whether 12 vs 10 changes his points (he is over the weekly cap and leads Squat either way).

## Deferred by name
- D1. Auto-detect the exercise type so the user does not pick it (Caleb's question, which he half-retracts; a feature, not a defect). Needs a design decision from Tom.
