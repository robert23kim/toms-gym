# Verify: upload branch (perf/upload-analysis-2026-11-13, 5ef44cb..HEAD)

Verdict: PASS. Every gate passes, the mutation was killed, and my own log query matches the report's baseline. Three objections below, none blocking. Nothing was deployed or written to prod. I did not test on a phone, in iOS Safari or in the APK.

## Gates (run by me, worktree /Users/toka/code/toms_gym-perf)
- `npx tsc --noEmit`: exit 0, 0 lines. **This check is hollow:** the root tsconfig.json has `files: []` plus references, so it type-checks nothing and could not have failed.
- `npx tsc --noEmit -p tsconfig.app.json`: exit 2 with 43 `error TS` (49 output lines). The report says "49 errors"; that is the line count. **0 errors in any changed file** (uploadTiming, resumableUpload, parallelUpload, upload.ts, telemetry.ts). I did not rerun base to diff the output; that byte-identical check is the report's.
- jest, full suite, `--maxWorkers=4 --json`: 113 suites, 811 tests, 811 passed, 0 failed. Matches the report's 811.
- Backend `tools/run_ci_tests.sh`: 402 passed, 8 deselected. No backend file changed. There is no venv in the worktree, so I used the main tree's venv (read-only). That venv lacks `coverage`, so I passed `PYTEST_ADDOPTS="-p no:pytest_cov -p no:cov"`. Without that flag the gate exits 1 on the import, before running any test.

## Mutation check
- Target: `resumableUpload.ts:259`, `fastPathOnly: true`. I reverted it to the base expression `fastPathOnly: mode === 'fast-only'` and re-read the file, which confirmed line 259 changed.
- `uploadVideoCompression.test.ts`: 6 tests, 1 failed: "'auto': a failed hardware encode sends the original and never tries MediaRecorder". This is the expected kill. The default and 'fast-only' cases still pass, because the default is now fast-only.
- I restored the file from an in-memory copy. A re-read shows `fastPathOnly: true`, and `git diff --stat` on the file is empty.

## Log check (my own query)
- Query: `gcloud logging read` over the request log of my-python-backend, POSTs whose URL contains `/upload/`, 2026-10-30 to 2026-11-14.
- Result: 28 `upload/signed-url` 200 and 28 `upload/finalize` 200. There were 0 resumable-url requests and 0 composite requests, although the filter would have matched both. That confirms 28 single PUTs, 0 composite and 0 resumable.
- I paired each sign with the next finalize from the same UA:
  - Android: n=14, median 3.5 s, max 11.8 s. The report says 3.4 / 11.7.
  - iOS: n=14, median 9.9 s, max 88.3 s. The report says 9.7 / 88.1.
  - My window includes the sign server time, which explains the roughly 0.1 to 0.2 s gap.

## Diff review
- **iOS Safari:** no behaviour change. `shouldCompress` still skips iOS. The timing adds a `visibilitychange` listener and `navigator.connection` reads, which come back null on iOS. Both run outside the transfer try, but neither can realistically throw.
- **Android WebView:** the transport (sendBeacon as text/plain, cross-origin) is already proven there: 15 capacitor boot pings in the report's window. The beacon is fire-and-forget and sits inside try/catch after the transfer, so it cannot block or fail an upload. The test "a telemetry failure does not fail a finished upload" covers this.
- **Optional-auth / email-only upload:** `fields` (email or user_id) still spreads into finalize unchanged. The event carries no email, user_id or file name; a test covers the file name.
- **100 Club one-tap (PromptList, ChallengeDetail):** call sites are untouched, and PromptList still posts weight "0". Non-Plank lifts pass `auto`, which now behaves like fast-only (see objection 1).
- **Payload:** a test asserts the body stays under the 2 KB backend cap with a huge UA and URL. The headless harness sent 623 to 634 bytes. `upload-timing` does not consume the global error budget, which applies only to the window error handlers.
- **Comment claim checked:** PARALLEL_THRESHOLD and RESUMABLE_THRESHOLD are both 32 MiB, as the new comment says.

## Objections (non-blocking)
1. **What gets analysed can change on one rare path.** The path: `auto` mode, a browser with WebCodecs, and an encode that throws or saves under 10 %. Before this change, MediaRecorder could upload a 720p re-encode (webm). Now the original goes up, which can be up to 200 MiB through the parallel path. The change is intentional and the report documents it, including that the loss case is unmeasured.
   - Prod evidence that this path did not upload in the window: all 14 Android objects were `video/mp4`, and Chrome's MediaRecorder writes webm. iOS never compresses.
   - The evidence cannot rule out the other half of the old pathology: MediaRecorder runs, then the original is kept anyway.
   - For the 100 Club, the analyzer now sees the original instead of a re-encode, so if anything the input is closer to the source. I did not test whether rep counts differ between the two.
2. **Log noise.** Every successful upload now logs a WARNING line, `FRONTEND_ERROR action=upload-timing`. `gcloud logging metrics list` returns 0 items, so no log-based metric counts these lines. I could not list alert policies (the `gcloud monitoring policies` group is missing on this CLI). Anyone who counts FRONTEND_ERROR lines as errors, such as the delight-loop bug triage, must now filter out `action=upload-timing`. Not verified: no alert policy fires on FRONTEND_ERROR.
3. **Hollow gate:** plain `npx tsc --noEmit` checks nothing in this repo (see Gates). The real check is `-p tsconfig.app.json`.

## Not covered
- A real phone, iOS Safari, the APK, and the event landing in prod logs: nothing is deployed.
- A tsc diff against base: I relied on the report for that.
