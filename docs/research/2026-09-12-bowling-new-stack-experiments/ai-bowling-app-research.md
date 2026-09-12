# AI Bowling (App Store id 6475312282) — how it claims to work

Researched 2026-09-12. 7 web searches, 15 fetches (6 failed: `aibowling.app` and
`alejandroarjonilla.com` do not resolve, `appadvice.com` does not resolve,
`trackmyroll.com` has an expired TLS cert, Maverick forum returns 403, App Store `il`
locale returned 429). Claims are tagged **[confirmed]** (read on a source page) or
**[inference]** (my reading between the lines).

Basic facts [confirmed]:
- iOS/iPadOS/macOS/watchOS only, iOS 17+. First released 2024-01-25, current 1.12.0
  (release note dated "August 22"), 122.7 MB. Developer: Alejandro Arjonilla Garcia (solo
  indie; also ships "BowlingDrill" and "Bowling 80"). App Store subtitle: "AI Shot Tracker
  & Coach". 3 ratings, 4.0/5, "< 1k" downloads. Free tier 10 shots/week + 5 AI chats/month.
  Sources: https://apps.apple.com/us/app/ai-bowling/id6475312282 ,
  https://apps.apple.com/kw/app/ai-bowling/id6475312282 ,
  https://mwm.ai/apps/ai-bowling/6475312282
- **mwm.ai is not the publisher.** It is an app-intelligence aggregator ("Live market data
  by MWM Intelligence — 15M+ apps tracked"); its page just mirrors the App Store text.
  There is no MWM engineering blog for this app. [confirmed]
- Android: no Google Play listing found in any search. [confirmed absence, 2 searches]

## 1. What it measures

[confirmed, App Store description + release notes]
- "Real-time ball tracking from your phone camera or gallery videos"
- "Speed, entry angle, and trajectory metrics for every shot"
- "Line projection overlay to visualize your shot path"
- "Breakpoint tracking to dial in your mark"
- Release note: "improved board tracking accuracy with enhanced precision in calculating
  **board positions at arrows and breakpoint**"
- Live Training HUD shows "real-time ball speed"; a "Target Line overlay showing ideal
  ball path on live camera"; "Target Board Challenge" mini-game (hit a chosen board).
- "Per-joint tracking status with confidence indicators" and reports with "joint tracking
  data" → it also runs body-pose tracking on the bowler, not just the ball.
- Output is **both**: per-shot numbers (speed, entry angle, board at arrows, breakpoint
  board) *and* an overlay (projected line drawn on the video), plus an exportable
  "narrated replay video" and a shareable HTML coaching report.

[inference]
- **Rev rate is NOT measured from video.** Every mention of rev rate is in the AI-coach
  context ("advice based on your ball speed and rev rate", "profile-based
  recommendations"); the tracking bullets never list it. Almost certainly a user-entered
  profile field.
- "Entry angle" from a rear camera is the angle of the last tracked segment before the pin
  deck in lane coordinates, i.e. derived from the same calibrated homography as the boards,
  not an independent measurement.
- Speed is likely the lane-length (60 ft foul line to head pin) divided by the frame-count
  between calibrated lane landmarks, so it depends entirely on lane calibration + frame
  timestamps.

## 2. How the user must film

[confirmed, release notes]
- **Portrait.** Release note: "better tutorial guidance on **vertical camera orientation,
  lane visibility, and phone stability**". So: vertical phone, keep the lane visible, hold
  it still (tripod implied by "phone stability"; not stated outright).
- **Manual lane calibration by dragging corner handles.** "Lane corner handles now snap to
  the actual lane corners and stay put across sessions" and "Direct drag controls for
  target handles on video". Onboarding "walks you through **camera framing, lane
  calibration, target selection, and pinch-to-zoom**". So the user places four lane-corner
  handles (with an auto-snap assist), picks a target (arrow/board), and can zoom.
- **Whole lane in frame.** Four corner handles + "lane visibility" ⇒ foul line and pin deck
  both visible. Not stated as a rule, but the calibration model requires it. [inference on
  the "requires" part]
- **Gallery import supported.** "phone camera or gallery videos" / "Point your camera at the
  lane or import from your gallery" [confirmed]. One App Store review (US) says "the video
  upload feature keeps glitching on iPhone... This is the whole reason I downloaded the
  app" ⇒ gallery import is a headline use case and was unreliable at review time.
- Where to stand: **not stated anywhere I could read.** Corner-based calibration + entry
  angle + board at arrows only make sense from **behind the bowler on the approach**,
  looking down the lane [inference]. The competitors below all say exactly that.
- Calibration persists "across sessions" ⇒ it assumes a fixed camera position for a session
  (tripod). [inference]

## 3. Technology disclosure

[confirmed]
- Marketing says only "AI". No model names, no CoreML/YOLO/Vision framework mention, no
  patent, no on-device-vs-cloud statement in the listing text.
- "Per-joint tracking status with confidence indicators" is a strong tell for Apple
  Vision `VNDetectHumanBodyPoseRequest` (per-joint confidence is exactly what that API
  returns) running on-device. [inference, high confidence]
- Apple-only platform matrix (iPhone/iPad/Mac/Watch, iOS 17+, 122 MB binary) plus
  "real-time" on the live camera feed ⇒ on-device tracking (a 122 MB app is consistent
  with bundled ML models). The AI coach chat is obviously cloud (LLM). [inference]
- No developer GitHub, blog, Reddit, or YouTube write-up of the method was found. The
  developer's personal site `alejandroarjonilla.com` no longer resolves; Twitter
  `@arjonillaxter` exists but was not fetched. [confirmed absence within budget]

## 4. What users say about accuracy

[confirmed]
- Almost no signal: 3 ratings total on the US store, one written review, about the upload
  bug, not accuracy. No r/Bowling threads, no YouTube demos, no forum posts naming "AI
  Bowling" surfaced in 4 searches. The Maverick forum thread "Mobile Shot Tracking App"
  (https://forum.maverickbowling.com/viewtopic.php?t=12117) exists but returned 403.
- The developer's own release note admits a prior accuracy problem: "improved board
  tracking accuracy... board positions at arrows and breakpoint".

[inference] With <1k downloads the app has essentially no independent accuracy evidence.
Treat its claims as untested.

### Accuracy evidence from the nearest competitor (Track My Roll, same camera geometry)
Track My Roll's own "best results" page (via search snippet; site cert expired) is the
most candid description of what breaks phone-video ball tracking:
- "lighting, camera angle, camera movements and boundary settings can all affect the way
  the shot is tracked"
- Ball colour: "may have difficulty tracking bowling balls with two highly contrasting
  colors (black and silver for instance) or a single light color like orange or light
  blue, and **darker colored balls will generally produce the best results**"
- "Do not focus on the bowler — when you tap on the screen to set your own area of focus,
  be sure to do so on the back end of the lane."
Source: http://trackmyroll.com/bestresults.htm (snippet via WebSearch).

## 5. Competitors doing ball-path tracking from a phone

| App | Measures | Filming / calibration | Notes |
|---|---|---|---|
| **Track My Roll** (iOS, since ~2016) [confirmed] | "launch angle, break point, entry angle, ball position and speed" | Camera "just off the approach behind the gutter of the **adjacent** lane (lane to the right for a right hander)", "no more than one half lane left or right of the target lane"; "**All four corners of the lane should stay in frame** at all times"; auto lane-boundary detection with a **manual mode** if a corner is blocked; "can adjust for small camera movements so there's no need for setting up equipment or lengthy calibrations" | Handheld tolerated, but the site's guidance is a long list of caveats (ball colour, lighting, tap-to-focus on back end). http://www.trackmyroll.com/ , http://trackmyroll.com/bestresults.htm |
| **LaneTrax** (iOS) [confirmed] | "over 15 key metrics" incl. "ball speed, entry angle, rev rate, and breakpoint board" | "stable **tripod**", "aligned with the right gutter for righties, left gutter for lefties", "well behind the end of approach behind the ball return, and setup **as high as possible**", NOT directly behind the lane (bowler occludes); framing rule: "bottom of the lane should be above the 'Detect Lane' button, and the top of the pins near the top of the camera feed", full rack of ten pins visible, don't over-zoom; lane detection "automatic" with manual fallback | Rev rate claimed from video (only one doing so). No on-device/cloud disclosure. https://docs.lanetrax.app/getting-started |
| **BowlSense** (iOS/Android) [confirmed] | "Speed Check" = speed + rev rate from a phone video, "without uploading it" (on-device); no ball-path/boards | No calibration details published; the real product is a 9-axis IMU puck (XIAO nRF52840 + ISM330DHCX, 416 Hz, BLE) inside the ball | Ball path/boards come from the puck, not the camera. https://www.bowlsense.io/blog/building-bowlsense , https://apps.apple.com/us/app/bowlsense/id6760173811 |
| **Kegel Specto / Specto Go** [confirmed] | full path, speed, entry angle, rev rate | Fixed overhead/side cameras installed at the centre; Specto Go is a "portable version... suitable for temporary set-ups", still dedicated hardware, not a phone | The gold standard everyone compares against. https://www.spectobowling.com/specto-bowling |
| **LaneTalk** [confirmed] | scores/pin leaves synced from 1,500+ centres' scoring systems | none (no camera) | Not a tracker. https://gobowling.com/blog/guides-tips/the-best-bowling-tracking-apps/ |
| BOSC, PinPal, BowlSheet, SnapStrike, StrikeMaster [confirmed] | manual score entry | none | Noise in search results; not video trackers. |

Common pattern across every phone tracker [confirmed]: camera **behind the approach,
offset toward the bowling-hand gutter** (so the bowler's body does not occlude the ball),
**as high as possible**, **entire lane from foul line to pin deck in frame**, lane
boundary found automatically with a **manual corner override**, tripod strongly preferred.
None asks the user to tap the arrows or the foul line; the four lane corners (plus,
implicitly, the known 60 ft × 39-board lane) are the whole calibration.

## What this implies for a phone-video board tracker

Confirmed patterns to copy:
1. **Calibration = 4 lane corners, nothing else.** Every app that reports boards uses the
   lane rectangle as the homography; boards, arrows (15 ft), breakpoint and entry angle
   are all *derived* from lane-plane coordinates plus known lane geometry. Ship auto
   corner detection, but the shipping UX is draggable corner handles with snap-to-edge,
   remembered per session. AI Bowling only got there in 1.9.x after "improved board
   tracking accuracy", i.e. auto-only was not good enough.
2. **Camera placement is prescribed, not detected.** Behind the approach, offset to the
   bowling-hand side by up to half a lane, high, whole lane in frame, portrait, on a
   tripod. Say it in onboarding with a framing guide (LaneTrax's "bottom of lane above
   the button, pins near the top" is a concrete, checkable rule). A back-of-lane
   focus/exposure tap matters because the pin deck is the bright, far, small end.
3. **Portrait is the norm for phone trackers** (AI Bowling says "vertical camera
   orientation"); a lane is ~1.5:26 in aspect from behind, so portrait maximises pixels
   on the far end where the breakpoint and entry angle live.
4. **Gallery import is table stakes and the first thing users break.** AI Bowling's only
   written review is about upload failing.

What they avoided solving (and you can too):
- **Rev rate from video.** AI Bowling takes it as profile input; BowlSense uses a sensor;
  only LaneTrax claims it from phone video. Skip it.
- **Side-view or arbitrary-angle filming.** Nobody supports it; all guidance is "rear,
  offset, high". Reject or warn on clips that fail the framing rule instead of trying to
  be angle-agnostic.
- **Light-coloured and two-tone balls, dark lighting.** Track My Roll just documents that
  these fail. Expect it; surface a "low tracking confidence" state rather than a wrong
  board (matches our SILENT-WRONG-is-the-enemy stance on score sheets).
- **Handheld camera motion.** Only Track My Roll claims compensation for "small" motion;
  the others require a tripod. Cheap option: detect corner drift over the clip and flag.
- **Ground truth.** With <1k downloads and no reviews, AI Bowling has no public accuracy
  evidence. Any accuracy claim we make needs our own labelled clips; nobody's numbers can
  be borrowed.

Open items not resolved within budget: the developer's own site and Track My Roll's site
are down (DNS / expired cert), so verbatim setup text for both comes from search snippets;
the Maverick forum thread (403) is the one place real bowlers compare these apps.
