# 2026-11-13: Caleb's feedback on The 100 Club

Not deployed: the squat engine fix (C3) is committed on `fix/squat-rep-count` (73852de, unpushed) but `bowling-service` stays on `00053-fxm`, because only one labelled squat clip exists and the 3-clip regression gate cannot fail. Backend not redeployed (no backend change; `00196-mtt`). Deferred: D1 auto-detect lift type; QA-6 UploadVideo page test, R4. Blocked: nothing at the write gate. The APK was published but never installed on a device.

## Asked
Three screenshots from a friend (Caleb, rank 1): "Not logged yet" after uploading (C1), a confusing bonus line (C2), squat counted 12 for 10 (C3). Fix, test, deploy, verify. Log: `2026-11-13-caleb-feedback/bugs.md`.

## Decisions
- C1: root cause is the board's inline upload form dropping `user_id`; fix it there and add an honest `you-row-unknown` prompt. Kept the unknown row on legacy boards too (Tom may want it consistency-only).
- C3: do not deploy the engine without a labelled set (contract). Decision needed (Tom): collect 3+ squat clips, or deploy on one.
- Never touched his live attempt or the live board.

## Shipped
- Frontend `my-frontend-00205-95c`: C1 (store id, Not me, Find Profile `?next=` limited to challenge boards, `?upload=1` round trip), C2 (one shared bonus clause, up to +100). Commits include 5c0cfc1, 26fc964, be2b683, 808029b, ef3ce94, 668529b.
- APK `tomsgym-debug-20261113-221223.apk`, link `/s/oVzVrt`.
- Docs: `docs/reference/100-club.md`, `situp-challenge.md`.

## Verified and what was not covered
- Live board and his lifts byte-equal to before, three reads (DB rows not read).
- Headless Chromium at 390 and 1280 on prod: anonymous shows `you-row-unknown` and no "Not logged yet"; random id still shows it; Find Profile and inline upload flows land back recognised, all writes stubbed. Bundle has the new clause once and the old sentence zero times (old bundle had it, so the check could fail).
- Not covered: WebKit/iOS, his device (iPhone Chrome on t30g.com), the APK on a device, prod finalize really returning `user_id` (code-dated only), a live off-podium viewer (B2 refuted as worded: podium viewers get no YOU row, same as before). Engine result is offline only; HTTP route and GCS upload were not exercised.

## Still broken
- Identity gaps needing backend: email links (analysis-ready, upload-by-email); separate storage across APK/browser/origins; Forget Me.
- Live squat still reads 12 (points unchanged: he is over 125 and leads Squat either way).
- Bonus line may still read as "log each type"; docs line was stale until this commit; `?upload=1` persists after upload; Find Profile copy says "profile".
- His id and name are in unpushed history at 589dfb3.

## Retro
- Went well: reproduce-first on the engine, adversarial refute rounds caught a stale docs line and a bogus B2 claim, live data stayed untouched.
- Did not: round 1 bonus wording needed a second pass; the labelled-set gate was unmeetable from the start.
- Next time: collect labelled clips before promising an engine deploy; assert podium viewers separately from row viewers; pin copy and docs from one source.
