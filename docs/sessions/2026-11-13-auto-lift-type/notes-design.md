# Design critic notes: automatic lift type, Change + re-analyse, remembered email (2026-11-14)

Verdict: the happy path fits the app (same select, helper, chip and CTA styles as the neighbours, Automatic is the
default with no extra tap, the upload button moves UP the screen). Three majors, all in the "could not tell the lift" corner: the status page dresses it as success (D1), an owner
the device does not recognise gets no Change and no hint (D2), and the video page shows "0.00 lbs" on a bodyweight
board (D3). Separately, minor: the longest label ("Counted as Pushups · Automatic") drops its Change chip onto a
second line at 390 (D4). 3 major, 10 minor. Nothing was fixed, staged or committed by this pass.

## How this was checked, and what it does not cover
- Read all 64 PNGs in shots/ on 12 contact sheets (4 phone shots per sheet at native 390 px; the 1280 shots 2x2 at
  0.94 scale; the 20 "-el" strips on one sheet, 44 full shots + 20 strips = 64). Contact sheets carried a broken-image canary (first build read 0 loaded
  images and was rebuilt).
- Rendered 42 more shots myself -> shots/critic-*.png, log shots/critic-render-log.txt (one JSON line per shot with
  bounding boxes and computed styles). 26 are the working tree on a local vite DEV server (port 5199, started and
  stopped by me) with API GETs proxied to production and the new fields injected, same method as the doer; 16 are
  production (8 screens x 390/1280: board, board upload form = the capture flow (Record now / Choose existing video
  live inside it), the /upload chooser (critic-prod-capture-*), status, challenge video, Find Profile,
  /lift/upload, Home). Fresh context per shot, page.unrouteAll first, function matcher, every non-GET stubbed
  (1-2 stubbed per shot: boot telemetry and the lift-type POST), 37 of 42 shots asserted a known text (0 failed; the 5 without an assert are status-confirm-viewer,
  video-yes-fail, signin, feedback and home, judged from the pixels and the logged line/email values); 0 page errors,
  0 horizontal overflow. In the Pushups shots the "YOUR PLANK 56.4s" hero above the line is an injection artefact
  (only lift_type was overridden); only the line's width is being judged there.
- NOT covered: a production build of the new code (dev server only, fields injected, not a real Auto attempt); the
  APK / native restore; a real upload or re-analysis; the Auto completion toast; the board's upload list row for a
  pending Auto attempt; Home for a known athlete (only the signed-out Home was shot); pre-fill on Golf, Bowling,
  Registration, CreateProfile, PasswordReset (SignIn, Feedback, /lift/upload were rendered at 390 only).
  critic-board-picked-off-390 came back in a different page state (scrollY 0) and is not relied on. The 409 text in
  critic-video-sheet-409-390 is mine; the backend's real text is "Analysis is still running; try again when it finishes".
- Owner shots set localStorage userId to a real club athlete (read-only render, writes stubbed), as the doer did.

## Per-surface answers (evidence in shots/)

### 1. Upload form, board (ChallengeDetail) and /challenges/:id/upload (UploadVideo)
- Same component and metrics as neighbours: yes. Select 38 px high, 16 px text, radius 12 px, border rgb(39,39,42) in
  Automatic, switch-off and production alike. Helper "We'll work out the lift from your video. You can change it after."
  is 12 px / rgb(161,161,170) / margin-top 4 px, identical to "0 for air squats." and "No account needed! ..."
  (critic-render-log: critic-board-fold-auto-390 vs critic-prod-board-upload-390).
- Copy: one line of intent, sentence case, same length as the email helper; wraps to 2 lines at 390 exactly like the
  email helper on the same page. Fits.
- Fold at 390: improves. Board form submit button bottom edge 478 px (Automatic) vs 544 (switch off) vs 545
  (production), all above the sticky "Log this week's lifts" at 712. With a video picked: 510, enabled, bright blue
  (critic-board-picked-auto-390). On /challenges/:id/upload with a video picked the button sits at 720-760, above the
  tab bar (779); with the switch off it is at 778-818, under the tab bar (critic-challenge-upload-picked-auto-390 vs
  -off-390).
- Automatic the obvious default with no extra tap: yes. select value "Auto" on load, weight field gone, path is
  pick video -> Upload Video (email pre-filled or already hidden).
- Pre-existing, not from this change, noted only: /challenges/:id/upload lists the generic lifts (Bench Press,
  Deadlift ...) under Automatic and picking Squat there brings back "Weight (kg) 60" on a bodyweight club; the sticky
  "Log this week's lifts" stays on screen under the open form.

### 2. "Counted as ... · Change" line (status page, challenge video page)
- Findable but quiet: yes for Plank. 14 px muted text, type name in white 600, chip = the board's own pill
  (11 px, rgba(255,255,255,.7) on .05, border .1, 4px 10px, radius full; weight 500 vs 400 on the board chips,
  30 px high vs 27). Viewer sees the line without Change (video-viewer-390).
- Wrap: FAILS for the longest label. "Counted as Pushups · Automatic" is 213 px, + 8 gap + 63 chip = 284 in a 278 px
  line, so Change drops to its own row on both pages (critic-status-pushup-automatic-390,
  critic-video-pushup-automatic-390; wrapped=true, line 54 px high). At 320 it is three rows. Plank fits with 13 px
  to spare. Squats and Situps were not rendered; by character count they should land within a few px of the edge
  (estimate, not measured). -> D4.

### 3. Confirm prompt
- Reads as a question, not an error: yes. Muted text, blue "Yes" pill, neutral "Change", no red or amber, no icon
  (status-confirm-390, video-confirm-390, critic-status-pushup-confirm-390; no wrap, 30 px high).
- But the page has already answered it: "YOUR PLANK 56.4s ... +5 lifts banked" / "<name>'s Plank" sits directly above
  "Is this a plank?" -> D5. Yes (41x30) and Change (63x30) are 6 px apart -> D6. A failed Yes opens the Change sheet
  with no message -> D7. After Yes the line settles to "Counted as Plank [Change]" (critic-video-after-yes-390). Good.

### 4. Could-not-tell state (needs_lift_type)
- Status page: green tick, "Analysis complete! Your results are ready to view.", then "Which lift is this? [Change]"
  (status-unknown-390 / -1280). Success framing for a lift that scored nothing, and nothing on this page says so -> D1.
- Video page: "<name>'s lift", "Which lift is this? [Change]", a stray "0.00 lbs", then the card "Not counted until the
  lift type is set" (video-unknown-390, critic-video-unknown-owner-full-390) -> D3, D8.
- Not recognised as the owner: status page shows only the success screen; video page shows "0.00 lbs" and "Not counted
  until the lift type is set" with no control (critic-status-unknown-viewer-390, critic-video-unknown-viewer-390) -> D2.

### 5. Change sheet
- Bottom sheet at 390 (radius 16 top, card surface, covers the tab bar), centred dialog at 1280. Options 46 px high,
  radius 12, selected = blue border + 15 % blue fill + #7fb0ff text (the YouRow blue), CTA #2f7bf6 48 px, Cancel as quiet
  text. Reads as part of the app. Error line is 14 px red-400 between the grid and the CTA, sheet stays open, CTA stays
  usable (critic-video-sheet-409-390). Not a dead end.
- Opens with the current type selected and "Re-analyse" enabled (pixels + log: checked=['Plank'], ctaDisabled=false).
  That pressing it re-analyses nothing comes from the component code and the endpoint's idempotent path in the design
  doc, not from a click here -> D9.
- Copy: "Re-analyse" next to "Analyzing your form..." / "to be analyzed" -> D10; plural labels vs singular elsewhere -> D11.
- After Re-analyse: status page drops to its normal "Queued for analysis" (good); video page shows title + amber
  "Pending" + "Analyzing your form... This usually takes 30-60 seconds." -> D12.

### 6. Pre-filled email
- Clearly editable: yes. Same input, white text, not read-only or disabled, on Find Profile, Sign in (auto-focused,
  blue ring), Feedback, /lift/upload, board form, challenge upload (findprofile-remembered-390,
  critic-signin-remembered-390, critic-liftupload-remembered-390; log: readOnly false, disabled false). Find Profile's
  button goes from grey to white, so it is one tap. First run shows the placeholder as in production.
- Email remembered but no userId (seeded by hand here via localStorage userEmail; per notes-impl-frontend the real
  path is a bowling upload, which remembers the typed email without a userId; not reproduced): desktop board shows "Find your profile - This device doesn't know who you are yet"
  directly above a form already holding that email (board-upload-automatic-1280) -> D13.

## Walks
- First-time phone user: board -> Log this week's lifts -> type email -> Automatic already selected -> Record/Choose ->
  Upload Video (above the fold) -> queued -> result with "Counted as Plank · Automatic [Change]". Smooth. Most awkward
  moment: when the engine cannot tell, the status page celebrates ("Analysis complete! Your results are ready to view."
  + green tick) and the only cue is a small "Which lift is this? Change" (D1).
- Returning phone user: email hidden or pre-filled -> pick video -> Upload. Most awkward moment: opening their result in
  any browser without their userId (another device, cleared storage, the APK after losing its WebView storage; where
  the completion email's link lands was not checked): the line reads "Counted as
  Plank · Automatic" with no Change and no reason why, and in the could-not-tell state it is a dead end (D2).

## Findings
MAJOR
D1 AnalysisStatus.tsx: could-not-tell state shown as success. status-unknown-390.png, status-unknown-1280.png.
   Fix: when needs_lift_type / lift type still Auto, no green tick; heading "Which lift was this?", sub "We couldn't
   tell from the video. Pick one and we'll count it.", the pick control as the primary button, "See your result"
   secondary.
D2 LiftTypeLine.tsx (+ AnalysisStatus.tsx, ConsistencyResult.tsx): an owner the device does not recognise gets no Change
   and no hint; dead end in the could-not-tell state. critic-status-unknown-viewer-390.png,
   critic-video-unknown-viewer-390.png, video-viewer-390.png.
   Fix: when there is no remembered userId, add a quiet link after the line / under the "Not counted" card:
   "Yours? Find your profile to change it" -> /find-profile (returning here); never show the success screen for an
   uncounted attempt.
D3 pages/VideoPlayer.tsx: "0.00 lbs" under the title of an Auto attempt on a bodyweight board. video-unknown-390.png,
   video-unknown-1280.png, critic-video-unknown-viewer-390.png (video-unchanged-390.png shows no weight line).
   Source: frontend/src/pages/VideoPlayer.tsx:581 `!isBodyweightLift(videoData.lift_type) && videoData.weight`: "Auto" is
   not in the bodyweight list and the weight string "0.00" is truthy (line 135 builds the share text the same way).
   Fix: skip the weight when isAutoLiftType(videoData.lift_type) at both lines.
MINOR
D4 LiftTypeLine.tsx: Change wraps to its own row for Pushups at 390 (and 3 rows at 320).
   critic-status-pushup-automatic-390.png, critic-video-pushup-automatic-390.png, critic-status-pushup-automatic-320.png.
   Fix (layout, keeps the contract copy): the line is 6 px short (284 needed, 278 available): gap-x-1.5 and px-2 on
   the chip, or let the line bleed 4 px each side (-mx-1), and keep text + chip on one row with flex-nowrap at >= 360.
   Shortening the copy ("· Auto", dropping "Counted as") changes the design doc's wording and is Tom's call.
D5 LiftTypeLine.tsx: "Is this a plank?" directly under "YOUR PLANK ... +5 lifts banked" / "<name>'s Plank".
   status-confirm-390.png, video-confirm-390.png. The design doc fixes the prompt as "Is this a pushup?", so any
   rewording is a contract change for Tom to decide; option: "Counted as Plank. Right?" [Yes] [Change] (says what was
   done, then asks). No-copy option: leave as is.
D6 LiftTypeLine.tsx: Yes 41x30 and Change 63x30, 6 px apart, opposite outcomes. critic-status-pushup-confirm-390.png.
   Fix: in the confirm state min-height 36, px-3, gap-2.
D7 LiftTypeLine.tsx confirmYes catch: a failed Yes opens "Change lift type" with no message.
   critic-video-yes-fail-390.png. Fix: set the error text ("Couldn't save that. Try again.") when opening the sheet
   from the catch, or show it inline and keep the sheet closed.
D8 LiftTypeLine.tsx + ConsistencyResult.tsx: in the could-not-tell state the one required action is the quiet 11 px chip
   labelled "Change" (nothing has been chosen), the sheet is titled "Change lift type", and the card says "Not counted
   until the lift type is set". video-unknown-390.png, critic-video-sheet-unknown-390.png.
   Fix: chip label "Pick the lift" in the blue Yes-chip style, sheet title "Which lift is this?", CTA "Count it", card
   headline "Not banked yet".
D9 LiftTypeLine.tsx: sheet opens on the current type with "Re-analyse" enabled; per the code and the idempotent
   endpoint it re-analyses nothing (not clicked here).
   critic-status-sheet-open-390.png, critic-video-sheet-open-1280.png. Fix: disable the CTA until the pick differs.
D10 LiftTypeLine.tsx: "Re-analyse" / "We'll re-analyse" beside "Analyzing your form...", "to be analyzed", "What are you
   analyzing?". video-sheet-390.png, video-after-change-390.png, critic-prod-capture-390.png. Fix: "Re-analyze".
D11 LiftTypeLine.tsx (sheet option label): sheet says Situps/Pushups/Squats, the select, board chips and title say
   Situp/Pushup/Squat ("<name>'s Situp" right after tapping "Situps"). video-sheet-390.png, video-after-change-390.png,
   critic-prod-board-390.png. Fix: label the sheet options with the same names as the select (the DB names) instead of
   liftTypeCountedAs; leave liftTypeCountedAs for the "Counted as Pushups" line, which the design doc fixes.
D12 pages/VideoPlayer.tsx: after Re-analyse the page promises "This usually takes 30-60 seconds." while the status
   page says about 2 minutes, planks up to 10. video-after-change-390.png vs status-after-change-390.png.
   Fix: reuse the status page sentence.
D13 YouRow.tsx: "This device doesn't know who you are yet" above a form pre-filled with the remembered email.
   board-upload-automatic-1280.png. Fix: when an email is remembered without a userId, say "Is this you?
   <email>" and link Find Profile, or drop the sub-line.
