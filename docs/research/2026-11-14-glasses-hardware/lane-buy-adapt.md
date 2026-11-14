# Lane: buy or adapt (no hardware design)

Written 2026-11-14. Status: PARTIAL. The tool budget was reached (15 web search calls, one of which ran two queries; 22 pages read). Tiers (a) and (b) are sourced from pages read; tier (c) rests on one factory page and one hands-on review, with no marketplace listing opened, and Meta's developer terms were not read. Gaps are listed in section 6.

Question: what can the owner get WITHOUT designing hardware, and how close does each option come to the numbers in
`REQUIREMENTS.md` (sections 2 and 3)?

## 0. How to read this file

- Every price, spec, availability and software capability carries a URL, the access date (all 2026-11-14) and a short
  quote. "page read" means the page itself was opened and the quote comes from it. "snippet only" means only a search
  result summary was seen; treat those as leads, not facts.
- Anything written from the author's memory is labelled "(from memory, unverified)".
- Claims that could not be sourced are collected under "Unsourced" at the end; they are not presented as fact.

### The yardstick: pixels per degree down the lane

The tightest requirement (REQUIREMENTS.md section 3.1) is pixels on the far end of the lane. The comparable number
across cameras is **pixels per degree (px/deg)**: recorded pixels along one axis divided by the field of view (FOV)
along that same axis. Two traps:

1. Vendors quote the **diagonal** FOV of the lens, and often the **sensor megapixels**, not the recorded video size.
2. Electronic image stabilisation (EIS) crops the sensor, so the recorded FOV is narrower than the lens FOV.

How this file computes it. Vendors quote the diagonal field of view, so the like-for-like number is **pixels along
the frame diagonal divided by the diagonal field of view** ("diagonal px/deg"). It is an average over the frame; on a
very wide lens the centre of the frame, where the pins are, gets somewhat fewer pixels per degree than the average.
Treat every figure as good to about plus or minus 20 %, and trust the **ratio to the baseline** more than the
absolute number.

The baseline, two ways:

- Geometry: the recorded clip is 1376x1824 (diagonal 2,285 px); the uncropped Gen 1 video is 1440x1920 (diagonal
  2,400 px; Android Central lists Gen 1 as "1440 x 1920 pixels at 30 fps",
  https://www.androidcentral.com/apps-software/meta/ray-ban-meta-smart-glasses-gen-2-vs-gen-1, snippet only). Meta publishes a "100° field
  of view" for the Gen 2 lens and none for Gen 1; assuming Gen 1 is the same, the baseline is about **24 diagonal
  px/deg**. (Assumption: Gen 1 lens = Gen 2 lens, and the stabilisation crop is small.)
- Measured floor, from REQUIREMENTS.md itself: a bowling ball is 8.5 inches (21.6 cm) across; from the foul line the
  head pin is 60 feet (18.3 m) away, so the ball subtends about 0.68 degrees. A measured radius of 4 px (8 px across)
  is then about 12 px/deg. The tracker's radius is taken on a blurred, partly hidden ball, so 12 is a floor, not a
  contradiction of 24.

Neither Meta nor Mentra says whether its field-of-view figure is diagonal, horizontal or vertical. This file assumes
diagonal for both (the usual convention). If a vendor's figure is really horizontal, that device has fewer pixels per
degree than stated here.

Scores below are given as a **ratio to the baseline** (1.0x = today's clips). Below 1.0x fails REQUIREMENTS.md
section 3.1; the requirement asks for "at least the same" and says more is "the single most useful improvement".

## 1. Tier (a): the Meta glasses he already owns, plus Meta's Wearables Device Access Toolkit

This tier matters most: any custom build has to beat it. Short version: **the toolkit does not give an app the
recorded clips, and its live stream is far below the recorded clips; but the vendor's phone app already copies the
full-quality clips into the phone's photo library by default, where a companion app can pick them up.** The second
path, not the toolkit, is the real zero-hardware baseline.

### 1.1 What the Wearables Device Access Toolkit (the "toolkit", Meta's software kit for third-party phone apps) gives

| Item | Finding | Source (all accessed 2026-11-14) |
|---|---|---|
| Status | Version 1.0.0 dated 2026-09-24, 1.0.1 dated 2026-10-09. Meta's FAQ calls 1.0 stable: "Wearables Device Access Toolkit 1.0 is here — a stable, supported release to build on." The GitHub README still says "The Wearables Device Access Toolkit is in developer preview." The two Meta sources disagree; the FAQ is the newer statement. | FAQ https://developers.meta.com/wearables/faq/ (page read). README https://raw.githubusercontent.com/facebook/meta-wearables-dat-android/main/README.md (page read). Changelog https://raw.githubusercontent.com/facebook/meta-wearables-dat-android/main/CHANGELOG.md (page read). |
| Platforms | Android and iOS: "iOS 15.2+ and Android 10+" (same as the Meta AI app). A community Flutter wrapper exists (`flutter_meta_wearables_dat`). No Capacitor plugin was found, so the app's Capacitor Android build would need a small native plugin. | Search snippet of https://wearables.developer.meta.com/docs/develop/dat/getting-started-toolkit/ (snippet only); https://pub.dev/packages/flutter_meta_wearables_dat (snippet only). "No Capacitor plugin" is an absence in one search, not a verified negative. |
| Supported glasses | "We support our portfolio of AI glasses:" Ray-Ban Meta (Gen 1 and Gen 2), Meta Ray-Ban Display, Oakley Meta HSTN, Oakley Meta Vanguard. "Capability availability varies by device." So the first-generation pair he is believed to own is supported. | FAQ (page read). Changelog 0.8.0 lists `RAYBAN_META, OAKLEY_META_HSTN, OAKLEY_META_VANGUARD, RAYBAN_META_OPTICS, META_GLASSES` (page read). |
| Live camera stream | Three sizes: "`.high` as 720 x 1280, `.medium` as 504 x 896 and `.low` as 360 x 640". Frame rate: "Valid values: 2, 7, 15, 24, 30 FPS." Ceiling per a third-party project's README: "720x1280 portrait at 30 fps is the ceiling for the glasses". Changelog 0.5.0: "High resolution (720x1280) video can be requested." | https://mixed-news.com/en/meta-dat-camera-720x1280-lower-resolution-higher-quality/ dated 2026-10-13 (page read; it quotes Meta's camera-streaming doc file). Changelog (page read). |
| Stream transport and quality | Meta's doc file says resolution and frame rate "are constrained by Bluetooth Classic bandwidth" and "Lower resolution and frame rate yield higher visual quality due to less Bluetooth compression." The stream uses adaptive bitrate and steps down resolution first, then frame rate, "never below 15 FPS". A third-party project claims "since DAT SDK 0.8 the glasses send video over a direct Wi-Fi link" (not confirmed in Meta's changelog). A compressed HEVC pass-through exists since 0.6.0 ("compressed HEVC video streaming, bypassing decoding"); 1.0.1 fixed "Buffer corruption while streaming compressed HEVC buffers, causing sporadic frame freezes." | Same mixed-news article (page read); changelog (page read). |
| Recording that stream | The Camera Access sample app (0.9.0) can "record video with optional sound-in-video, continuing while the app is backgrounded." This records the 720x1280 stream on the phone. It is not the on-glasses recording. | Changelog (page read). |
| Photo capture | In-stream: "Capturing a single frame during a stream and delivering it to your app". Standalone (1.0.0): "Camera.photo captures standalone high-quality photos" with a `PhotoResolution` setting; the pixel values are not in the changelog. Marked "(experimental; unavailable for production publishing)". Format HEIC. | Build overview https://wearables.developer.meta.com/docs/develop/dat/build-overview/ (page read); README and changelog (page read). |
| **Full-quality recorded clips** | **Not available through the toolkit.** No media-library, gallery or file-import function appears in the README feature list, the changelog from 0.1.0 to 1.0.1, the build overview or the FAQ. The only related sentence is about privacy: "Meta does not access photos/videos or audio that is transferred directly from the glasses to the third-party mobile app." This is a negative from four Meta pages, not an explicit statement by Meta that it is impossible. | README, changelog, build overview, FAQ (all page read). |
| Motion sensors | New in 1.0.0: a Motion module "streaming device orientation and movement as MotionSample values"; the README lists "Motion — Stream accelerometer, gyroscope, magnetometer, and orientation samples with explicit lifecycle control". The changelog marks Motion experimental. Sample rates (`MotionSamplingRate`) are not listed in the pages read, and nothing says whether a motion stream can run at the same time as a button-press recording on the glasses, or how it is time-aligned to a recorded clip. | README, changelog (page read). FAQ: 1.0 includes "camera, microphone, audio, motion and IMU capabilities" (page read). IMU = inertial measurement unit, the accelerometer and gyroscope. |
| Microphone | "Audio is streamed as 8 kHz mono from the device to your app" over the Bluetooth hands-free profile; 1.0.0 adds audio frames alongside the video stream (experimental). | Build overview, changelog (page read). |
| Giving the app to other people | Not through an app store yet. FAQ: "You'll soon be able to submit your Device Access Toolkit and Web Apps experiences to be published on these surfaces." Today: "create organizations and release channels to share with test users." Changelog: experimental features "can be built and tested against, though apps using them cannot be published yet." The number of test users allowed was not found. | FAQ, README (page read); changelog quote via mixed-news (page read). |
| iOS obstacle | A news article dated 2026-09-28 reports Apple rejecting an app that declares the Meta accessory protocol pending Made-for-iPhone authorisation, and a Meta-affiliated reply that 1.0 "doesn't change this yet" and Meta "isn't able to add third-party apps to its MFi Product Plan or issue PPIDs at this time." A third-party project reports a build signed with a free Apple ID "registers and connects over Bluetooth but never receives a frame." So on iOS: development builds on your own devices with a paid developer account appear to work (the author's inference from the third-party report, not tested); App Store distribution does not yet. | https://vr.org/articles/fall-glasses-platforms-stores-without-hardware-sdk-status-2026 (page read, secondary source); mixed-news (page read); https://raw.githubusercontent.com/facebook/meta-wearables-dat-android/main/LICENSE is cited in the next row. |
| Licence limits | "All integrations and apps must comply with the Meta Wearables Developer Acceptable Use Policy"; Wearables Developer Terms apply. "only those in AI glasses supported countries will have access to the full capabilities of the toolkit" (the United States is one). The repository's LICENSE file is not an open-source licence: it is titled "DEVELOPER TERMS" and says "By using the Wearables Device Access Toolkit, you agree to our Meta Wearables Developer Terms". The text of those terms and of the Acceptable Use Policy was not read, so specific limits (commercial use, redistribution, data use) are unknown; see section 6. | FAQ (page read); https://raw.githubusercontent.com/facebook/meta-wearables-dat-android/main/LICENSE (page read). |

**What this means against REQUIREMENTS.md.** The best the toolkit stream can do is 720x1280 at 30 fps, compressed for a
radio link. The clips the tracker works on today are about 1376x1824 at 15 Mbps. On the width axis that is 720 against
1376 pixels over the same lens, about 0.52 times the pixels per degree (0.5x to 0.6x the baseline, if the stream covers the same field of view as the recorded clip, which Meta does not state), so a
ball that is 4 px in radius at the pins becomes about 2 px. REQUIREMENTS.md section 3.1 says upscaled crops already
fail; a stream at half the native scale fails the tightest requirement. **The toolkit stream is not a replacement for
the recorded clips.** What the toolkit could add is side channels: a motion-sensor stream and a button or voice
trigger, both still experimental and not publishable.

### 1.2 The path that does deliver full-quality clips: the vendor app's auto-import, plus a companion app

Meta's own help content says the vendor phone app (Meta AI) copies recordings into the phone's photo library:

- "Most Android (13+) and iOS phones have auto-import on by default." "This moves recordings from your glasses to
  your phone’s photo app." "After importing, your videos and photos will appear in your phone’s photo app." Manual
  fallback: "If your glasses have unimported media, tap the Import button next to Gallery to transfer your clips."
  Source: https://www.meta.com/ai-glasses/learn/guide-shooting-pov/ (page read twice, 2026-11-14). Meta's help page
  https://www.meta.com/help/ai-glasses/272319252352130/ came back truncated and was not read.
- The same page does not say whether auto-import runs without opening the Meta AI app. Its manual steps begin "Open
  the app and tap Menu in the bottom right." So "clips appear in the phone's photo library" is sourced; "with no
  action by the user" is not. **Rank 1 below hinges on a one-minute check on his own phone:** record a clip, do not
  open the Meta AI app, and see whether the clip appears in the phone's gallery.
- "AI glasses from Meta save videos as MP4 on Android and HEVC on iOS." Same guide (page read).

So the full-quality file is already on the phone, in shared media storage, minutes after a session. A companion
feature in the app's existing Android build could watch the phone's media library for new videos from the glasses
(Android's MediaStore with the read-media-video permission; on iOS the Photos framework with library permission) and
upload each one by the signed-URL path the app already uses. No toolkit, no Meta approval, no hardware.

Limits of this path, stated plainly:

- The transfer glasses -> phone is still done by Meta's app (over a temporary Wi-Fi link to the glasses: from
  memory, unverified; the guide mentions only Bluetooth pairing). Whether it runs
  unattended in the background on his phone, and how long 1 GB takes, was not measured here.
- The folder or album name the Meta AI app writes to on Android was not verified (from memory, unverified: a
  "Meta AI" or "Meta View" album under DCIM or Pictures). The companion app would filter on that or on the file's
  metadata.
- Still one button press per throw, clips capped at "up to 30 seconds" by default, extendable in the app "to 3 minutes
  on most devices, or 5 minutes on Oakley Meta Vanguard" (guide, page read). No whole-session recording.
- No exposure control, no synchronised motion log inside the clip.
- An iOS app cannot upload reliably in the background the way Android can (from memory, unverified).

### 1.3 A "buy" option the brief did not list: a newer Meta or Oakley pair

Meta's guide (page read, https://www.meta.com/ai-glasses/learn/guide-shooting-pov/, 2026-11-14):

- Ray-Ban Meta (Gen 1): "1080p". "You cannot adjust resolution settings for Ray-Ban Meta (Gen 1)" (help page, snippet only).
- Ray-Ban Meta (Gen 2) and Oakley Meta: "Up to 3K Ultra HD at 30 frames per second (fps), or 1080p at 60fps".
- Stabilisation: "Choose low, medium, high or auto depending on what you're recording."
- Field of view: Gen 2 and Oakley Meta HSTN "100° field of view"; Oakley Meta Vanguard "122° centered field of view".

Prices: Ray-Ban Meta (Gen 2) "$379", Oakley Meta Vanguard "$499", Meta Ray-Ban Display "$799" (third-party tracker last updated 2026-06-01, https://testlisting.pages.dev/ai-glasses-toolkit.htm, page read; not checked on Meta's own store today).
Battery: Gen 2 "up to 8 hours per charge", Vanguard about 9 hours (search summary only; the summary did not
say which result page carried the figures, the likeliest being
https://www.androidcentral.com/apps-software/meta/ray-ban-meta-gen-2-vs-oakley-meta-vanguard; treat as unverified).

**First, check which model he owns.** The clip sizes do not settle it: press reports list a 1440p at 30 fps mode on
Gen 2 as well, and Meta's guide says only Gen 1 has no resolution setting. If the Meta AI app shows a video
resolution setting under Device settings > Media > Video settings, he owns a Gen 2 or Oakley model and can switch
to 3K today at no cost.

Why it matters: the tightest requirement is pixels on the far end. TechRadar reports the 3K mode as about 6.4
million pixels per frame (snippet only, https://www.techradar.com/computing/virtual-reality-augmented-reality/meta-ray-ban-gen-2-smart-glasses-are-official-here-are-5-key-upgrades-you-need-to-know-about);
at 3:4 that is about 2,190x2,920 (derived, not a published size), 1.5 times the Gen 1 frame on each axis. Over the
same 100 degree lens a Gen 2 pair gives roughly 1.5 times the pixels per degree for $379, with the same auto-import path, the same toolkit
support, selectable stabilisation strength (which may also remove the 15-different-frame-sizes problem) and a 60 fps
mode at 1080p. Nothing in tier (b) or (c) below beats that on pixels per dollar. The Vanguard's wider 122 degree lens
spreads the same pixels over more degrees, so it is the worse pick for the far end despite the higher price.

## 2. Tier (b): open or developer-friendly camera glasses sold as single units

Only one device in this tier is in stock, records video, and lets a third-party phone app drive it: Mentra Live.
Everything else fails on a first-order test (no video, no camera, no software kit, or not obtainable in the United
States), so each of those gets one sourced line.

### 2.1 Mentra Live (the only serious candidate)

| Item | Finding | Source (accessed 2026-11-14) |
|---|---|---|
| Price | "$449" for glasses, charging case and cable. Launch coverage in January 2026 said $299; the vendor page now says $449. | https://mentraglass.com/live (page read). $299: https://www.engadget.com/wearables/mentras-first-smart-glasses-are-open-source-and-come-with-their-own-app-store-150021126.html and https://www.techspot.com/news/110955-new-mentra-live-smart-glasses-built-livestreaming-platforms.html (snippet only). |
| Availability | "Ships in 2–5 business days." The page does not list countries; the company is United States based (from memory, unverified). | https://mentraglass.com/live (page read). |
| Hardware | "MTK8766 chipset" (a MediaTek chip of the kind used in Android devices; that the glasses run Android is the author's inference from the chip and from the downloadable "ASG APK", not a statement by Mentra in the pages read), "Weight: 43 grams", "WiFi + Bluetooth", "RGB feedback plus white privacy light". | Product page and https://docs.mentraglass.com/mentra-live/hardware.md (both page read). |
| Camera | "HD 1080p videos", "HD 3264 × 2448 images" (8 megapixels; press coverage says 12), "119° field of view, landscape orientation". Sensor model, bitrate, codec and stabilisation are not published. | Product page (page read). 9to5Google says 112 degrees (https://9to5google.com/2026/01/15/mentra-live-smart-glasses-youtube-livestream/, snippet only). |
| Battery | "45 minutes video calling · 8+ hours normal use". Continuous recording time is not published; 45 minutes of streaming suggests the 15 minutes of recording inside a 2 hour session fits, and a whole 65 minute session recorded continuously does not. | Product page (page read); the inference is the author's. |
| Phone software kit | A "Bluetooth SDK" for a direct phone-to-glasses connection: "scanning, pairing, device status, microphone audio, camera capture, speaker playback, streaming, Wi-Fi, and hardware events". Platforms: native Android, native iOS, macOS, React Native and Expo. No Capacitor plugin is mentioned; the Android library would be wrapped in a small plugin. | https://docs.mentraglass.com/bluetooth-sdk/overview.md (page read). |
| Start and stop recording from an app | Yes. `startVideoRecording(...)` with per-recording width, height, fps and `maxRecordingTimeMinutes`; "`0` or an omitted value records until your app stops recording or the glasses interrupt it." Defaults via `setVideoRecordingDefaults({width, height, fps})`. The allowed sizes are not listed; examples use 1280x720 at 30 fps. | https://docs.mentraglass.com/bluetooth-sdk/camera-streaming.md and .../api-reference.md (page read). |
| Getting the full file | Two documented routes. (1) Direct upload: at stop time "Pass the webhook URL and auth token"; the glasses POST the file as multipart form data with a `video` field, straight from the glasses over Wi-Fi to an endpoint you own. (2) Gallery: files stay on the glasses; the phone joins the glasses' Wi-Fi hotspot and queries `/api/gallery` (each entry has `name`, `url`, `mime_type`, `size`). "The gallery server is only reachable over the glasses Wi-Fi hotspot." | camera-streaming.md, and https://docs.mentraglass.com/app-devs/core-concepts/camera/videos.md (page read). |
| Live stream | RTMP, SRT or WebRTC to endpoints you own. | overview.md (page read). |
| Exposure control | Documented for photos: `exposureTimeNs` "sets sensor exposure in nanoseconds", `iso` sets sensitivity ("one-shot manual exposure"). Not documented for video. | camera-streaming.md, api-reference.md (page read). |
| Field-of-view control | "`setCameraFov({fov, roiPosition})` clamps `fov` to 62-118 degrees"; presets "82, 102, and 118 degrees with center ROI". Warning in the docs: "output resolution and effective detail can vary by capture path, firmware, and camera mode". Whether it applies to recorded video is not stated. | api-reference.md (page read). |
| Motion sensors | Not exposed in a useful form. The phone kit lists only "Head-up state changes." The cloud kit's raw accelerometer stream "is G2-only today" (a different, camera-less product) and "Gyroscope, magnetometer, and fused orientation aren't exposed yet." | api-reference.md and https://docs.mentraglass.com/app-devs/core-concepts/imu.md (page read). |
| Recording light | "The capture light is always enabled for photo, video, and stream capture as a privacy indicator." | camera-streaming.md (page read). |
| Licence and openness | MentraOS repository: "Every component is open source under the Apache License 2.0." (One search summary described the code as MIT-licensed; the repository page, read directly, says Apache 2.0, and that is the one used here.) It holds the phone app, the software kits and the cloud. The on-glasses Android client is offered as a downloadable "ASG APK" nightly build, which suggests the glasses' camera service is an ordinary Android app (inference); whether its source is in the same repository, and whether an owner can install a modified build, was not confirmed (see Unsourced). | https://github.com/Mentra-Community/MentraOS (page read). |
| Independent test of the footage | None found. One search for reviews, teardowns and sample footage returned only launch coverage and vendor documents. | Search, 2026-11-14. |

**Pixels on the far end.** A 1920x1080 frame has a diagonal of 2,203 px. Over 119 degrees that is about 18.5 diagonal
px/deg, **0.77x the baseline**: at the default wide setting Mentra Live is worse than the glasses he owns. The
field-of-view control might recover it: the still sensor is 3264x2448 (diagonal 4,080 px over 119 degrees = 34 px/deg
at the sensor), so a 1080p video cropped from the centre 62 to 82 degrees could carry 27 to 34 px/deg (1.1x to 1.4x).
That is arithmetic, not a measurement: the documents do not say the crop applies to video, nor that a cropped video
is read from the sensor at full detail. A 62 degree view may also lose the lane as the head tilts (REQUIREMENTS.md
section 3.6). This is the first thing to test on a bought unit.

**How a clip would reach the app.** The app's Android build wraps the Mentra Android library in a Capacitor plugin,
pairs once, and then either (1) tells the glasses to POST each clip to an upload endpoint, or (2) pulls files from
the glasses' hotspot gallery and uploads them through the existing signed-URL path. Route 1 needs a new receiving
endpoint, because the glasses send a multipart POST with a bearer token rather than a PUT to a signed Cloud Storage
URL, and Cloud Run's 32 MiB body cap (REQUIREMENTS.md section 5) is close to the size of a 20 second clip. Route 2
reuses the app's upload as it is. Either way no vendor app sits in the path, which is the one thing the Meta route
cannot offer.

### 2.2 The rest, one line each

| Device | Verdict | Evidence (accessed 2026-11-14) |
|---|---|---|
| Brilliant Labs Halo ($299, preorder) | Fails: camera is not a video camera. | UploadVR: a "low-power optical sensor" for AI, "rather than capturing images and videos"; a tracker lists "VGA POV camera", "Open SDK" (https://www.uploadvr.com/everyone-is-making-smart-glasses-now/ snippet only; https://testlisting.pages.dev/ai-glasses-toolkit.htm page read). Brilliant Labs Frame (older) also has a low-resolution camera (from memory, unverified). |
| Omi Glass Dev Kit ($499, "ships now") | Fails: a small microcontroller board (Seeed XIAO ESP32-S3 Sense) that takes periodic stills; continuous 30 fps video at lane resolution is out of its reach. The older OpenGlass kit "is not available for purchase". | https://omi.me/products/omi-glass-dev-kit, https://docs.omi.me/doc/hardware/omiGlass, https://www.layer3labs.io/guides/omi-glass (all snippet only). The Omi product page advertises "full-day camera recording"; a third-party guide says "periodic camera stills". |
| SeeIt Glass 1 (preorder "$50" Founder, "$150" Research Edition) | Not obtainable: preorder only, page says both "Shipping Summer 2025" and "Shipping Summer 2026". Camera "Sony 13MP with EIS", no video size given; "39g"; "270mAh, up to 13-hour moderate usage". The maker's blog claims an open camera driver with raw sensor access. Interesting on paper, no evidence it ships. | https://seeit-landing-page.pages.dev/ (page read); blog (snippet only; it says 5MP, which conflicts with the landing page). |
| Rokid Glasses (with display) | Unclear and hard to get: "$599" in an undated review; a guide checked 2026-11-01 says the display model is sold out at the US store; Newegg lists $849.98 shipped from Hong Kong. Phone kit (CXR-M) documents connection, audio stream and settings; camera recording by a third-party app was not confirmed. | https://www.phonearena.com/reviews/rokid-glasses-review_id7961, https://idevice.com/guide-text/rokid-glasses-display.md, https://www.newegg.com/p/215-047E-00001; kit details from a search summary of Chinese-language developer articles such as https://juejin.cn/post/7577461079597694995 (all snippet only). |
| Rokid AI Glasses Style ($299, sold on Rokid's site and Amazon US) | No third-party software kit listed. | Tracker marks third-party support with a cross (page read); price and channels from https://tools.prnewswire.com/en-us/live/20813/release/20260119EN66215 (snippet only). |
| RayNeo V3 / V4 | No third-party software kit listed; no US price found for V3. V4 "$325–$412". | Tracker (page read); the V4 price is from a search summary that did not name its source page (unverified). |
| Xiaomi AI Glasses (about $278) | No official release outside China; app and assistant are Chinese-language; no software kit. | https://dymesty.com/de/blogs/articles/xiaomi-ai-glasses-review-specs-price-2026 (snippet only); tracker (page read). |
| Even Realities G1 / G2 | No camera. | Tracker lists G2 without a camera (page read). G1: from memory, unverified. |
| Alibaba Quark G1 / S1, Huawei, iFLYTEK, Acer, Willit | Cameras, no third-party kit listed. | Tracker (page read). |
| B by Lenskart ($265–$325) and INMO GO 3 ($430–$460) | Listed as having a camera and a software kit ("12 MP ultra-wide, 1080p/1440p video" for Lenskart). Lenskart is India-based; neither was researched further, and US availability is unknown. | Tracker (page read). |
| Snap Specs ($2,195), XREAL AURA (up to $1,500), Android XR glasses | Over budget or not yet shipping; display-first devices. | https://vr.org/articles/fall-glasses-platforms-stores-without-hardware-sdk-status-2026 (page read). |

## 3. Tier (c): white-label "AI camera glasses" from contract manufacturers

| Item | Finding | Source (accessed 2026-11-14) |
|---|---|---|
| Typical chips | Low end: an Allwinner V821 (camera, video encoder and Wi-Fi) beside a JieLi JL7018F (Bluetooth and audio). Mid range: a Bestechnic BES2800 with a separate image signal processor. Top end: Qualcomm AR1 (that the Meta glasses use this chip is from memory, unverified). | microwear.info lists "Allwinner V821" (page read); a retail review lists "JL7018F Stereo chipset" and "Allwinner V821 AI processor" (page read); BES2800 and AR1 from https://www.smartglassesfactory.com/blog/technical-analysis-of-smart-glasses-solutions-qualcomm-ar1-and-bes-chips and https://www.lisleapex.com/solution-ai-smart-glasses-chip-solutions (snippet only). |
| Typical camera | "Sony IMX219 8MP (13MP interpolated)", "1200p @ 30fps with EIS stabilization", "300mAh", "44g", Wi-Fi 4 in the spec table and "WiFi 6" in the banner of the same page. | https://microwear.info/ai-glasses (page read). The IMX219 is the 8 megapixel sensor of the Raspberry Pi Camera Module 2 (from memory, unverified). |
| Sample price, 1 to 5 units | Quote only on the factory page ("Get Quote"). Public ballparks: a Global Sources listing with the same two chips shows a headline price of $34.52 (snippet only; the page refused the fetch with HTTP 429, so tiers and minimum order were not read); the same hardware sold at retail under a brand costs "USD 199" (Padmate ViewMate, page read). Expect $35 to $80 a unit plus shipping from a marketplace, or about $200 from a retail rebrand (the $80 upper figure is the author's guess, see Unsourced). | microwear.info (page read); https://www.globalsources.com/Smart-glasses/AI-smart-glasses-1229175658p.htm (snippet only); https://musicphotolife.com/2026/01/padmate-viewmate-review-ai-smart-glasses/ (page read). |
| Minimum order for a branded run | "MOQ starts from 200pcs for select models." Timing: "7-day sample delivery", "15-25 day bulk production". | microwear.info (page read). One factory only. |
| Software kit or firmware source | The factory page promises "Full SDK documentation for app integration" and "Full customization services" without saying what the kit covers or whether firmware source is included. No public documentation was found. A hobbyist repository documents a V821 glasses design (github.com/Nopiskl/V821_AIGlassess, snippet only), which suggests firmware work on this chip is possible but is an embedded-Linux project, not a phone-app task. | microwear.info (page read); search (snippet only). |
| How real the specs are | Not very. In the one hands-on review that measured files: advertised "1080p HD recording", but "the video output is actually 1600 x 1200"; advertised "8MP", but "the resolution of the photo output is actually 6560 x 4928" (an 8 megapixel sensor upscaled to 32). Storage "2GB". Clips "from 15 seconds to 12 minutes max". Transfer over "WiFI 5GHz", and the vendor app must stay in the foreground or the transfer stops. Verdict: "Image quality is average". Frame rate, bitrate and codec were not reported. | https://musicphotolife.com/2026/01/padmate-viewmate-review-ai-smart-glasses/ (page read). |
| Teardowns | None found for this class. The teardowns that exist are of Ray-Ban Stories and Ray-Ban Meta. | Search (snippet only). |

**Against the requirements.** 1600x1200 has a 2,000 px diagonal. The field of view is not published; at a typical 100
to 110 degrees (from memory, unverified) that is 18 to 20 diagonal px/deg, about **0.8x the baseline**, before
counting a weaker lens and encoder. Storage of 2 GB only just meets the session envelope. Clips reach the phone only
through the vendor's closed app, the same place the Meta route ends up, with worse video. A white-label unit is
useful for one thing: as a $35 to $200 donor frame (shell, battery, hinge wiring) for a custom build. As a
buy-and-use device it loses to everything in tier (a).

## 4. Comparison against REQUIREMENTS.md sections 2 and 3

"px/deg ratio" is diagonal pixels per degree relative to today's clips (1.0x; method and error bars in section 0).
Costs are hardware only, list price, before tax and shipping.

| Option | px/deg ratio (tightest) | Frame rate | Blur / exposure control | Motion log synced to video | Extra channels | Field of view | Battery vs 2 h on face, 15 min recording | Storage and transfer | App can start/stop and get the full file? | Cost: 1 unit / 3 units | Obtainable now (US) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0. Owned Meta glasses, as used today (baseline) | 1.0x (1376x1824 clips, about 15 Mbps HEVC) | 30 | None | None | Stereo audio in clip | Works today | Proven on 2026-11-08 session | Proven: 1.07 GB session; vendor app imports to phone | No: button press; file via vendor app, Drive, laptop | $0 | Owned |
| A1. Owned Meta glasses + companion uploader in the app (reads vendor app's auto-import from the phone photo library) | 1.0x | 30 | None | None | Stereo audio in clip | Same | Same | Vendor app imports ("auto-import on by default"), the app uploads by signed URL | Start/stop: no. Full file: yes, indirectly | $0 / $0 for owners of Meta glasses | Yes |
| A2. Meta toolkit live stream recorded on the phone | 0.5x to 0.6x (720x1280 ceiling, radio-compressed) | 30 max, drops to 15 | None | Motion module exists (experimental); sync and rates undocumented | 8 kHz mono audio; button and voice events | Same lens | Unknown, streaming drains faster | No on-glasses file; phone records | Start/stop: yes. Full-quality file: **no** | $0 | Yes for own devices; no store publishing yet; iOS blocked for distribution |
| A3. Buy Ray-Ban Meta (Gen 2) | about 1.5x in "3K" at 30 fps (about 6.4 megapixels a frame); about 0.8x in the 60 fps mode (TechRadar: "1200p at 60 fps") | 30, or 60 at lower size | No exposure control; stabilisation "low, medium, high or auto" | None in clip | As A1 | "100° field of view" | "up to 8 hours per charge" (snippet) | As A1; 3K files are larger (size not sourced) | As A1 | $379 / $1,137 | Yes (retail) |
| A4. Buy Oakley Meta Vanguard | about 1.25x (3K over "122°") | 30 / 60 | As A3 | None | As A1 | Wider, centred camera | about 9 hours (snippet) | As A1; clips up to 5 minutes | As A1 | $499 / $1,497 | Yes (retail) |
| B1. Mentra Live, default wide view | 0.77x (1920x1080 over 119 degrees) | Settable; maximum not documented | Manual exposure documented for photos only | None (no gyroscope or accelerometer stream) | Microphone stream, button events | "119°" landscape, wider than needed | "45 minutes video calling · 8+ hours normal use" | Storage size not published; direct Wi-Fi upload from glasses, or hotspot gallery pull | **Yes and yes**, from his own app, no vendor app in the path | $449 / $1,347 | Yes, "Ships in 2–5 business days" |
| B1'. Mentra Live with the view narrowed to 62-82 degrees | 1.1x to 1.4x **if** the crop applies to video at sensor detail (untested) | As B1 | As B1 | None | As B1 | Narrow; lane may leave frame during the approach | As B1 | As B1 | As B1 | As B1 | As B1 |
| C1. White-label V821 glasses (factory sample or retail rebrand) | about 0.8x (measured 1600x1200; field of view assumed) | 30 claimed | None | None | None | Unknown | "300mAh"; about 30 minutes of on-and-off video per charge in one review | "2GB"; vendor app over 5 GHz Wi-Fi, foreground only | No (closed vendor app; kit contents unknown) | about $35-$200 / $105-$600; branded run from 200 units | Samples by quote; retail rebrands yes |
| Omi Glass Dev Kit | Fails (periodic stills) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | Open firmware | $499 / $1,497 | "ships now" (snippet) |
| Brilliant Labs Halo | Fails (VGA-class sensor, not for video) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | Open kit | $299 | Preorder |
| SeeIt Glass 1 | Unknown (13 megapixel sensor claimed, video size unpublished) | Unknown | Raw sensor access claimed | Unknown | Unknown | Unknown | "270mAh" | Unknown | Open driver claimed | $50-$150 preorder | No evidence of shipping |

Reading the table against the six needs in REQUIREMENTS.md section 3:

1. **Pixels on the far end:** only A3 (Gen 2 at 3K) clearly beats the baseline. A4 beats it slightly. B1' might. A2,
   B1 and C1 are worse than what he has.
2. **Blur at release:** nothing bought gives exposure control over video. Mentra Live documents it for photos, which
   makes it the only place it could plausibly be extended. A3's 60 fps mode shortens the frame interval but drops
   below baseline resolution.
3. **Camera motion (a gyroscope log synced to the video):** nothing bought provides it. The Meta toolkit's Motion
   module is the nearest thing, and it is experimental, undocumented on timing, and separate from the recorded clip.
   This is the clearest thing a custom device could offer that no bought device does.
4. **Release and pin-hit events:** every option records audio (the pin crash); none adds a motion channel.
5. **Frame rate:** all reach 30; only the newer Meta models reach 60, at reduced size.
6. **Field of view:** all are wide enough; Mentra Live narrowed to 62 degrees is the only risky one.

## 5. Ranked top three

**1. Keep the Meta glasses and build a companion uploader into the app (option A1). Cost: $0. Effort: software only.**
(Premise to confirm on his phone before any work: imported clips appear in the phone's gallery, ideally without
opening the Meta AI app; see section 1.2.)
Wins because it matches the baseline by definition and removes the laptop, Google Drive and research-script hops,
which is most of what "link directly into the app" means: Meta's phone app already places full-quality clips in the
phone's photo library by default, and the app's Android build can pick up new clips there and upload them by the
signed-URL path it already has. It also works for any other user who owns Meta glasses. Loses on: the vendor app is
still in the chain (pairing and import are Meta's, and background behaviour is unmeasured), one button press per
throw, no exposure control, no motion log, and nothing improves at the far end. Do this first regardless; it is also
the yardstick for whether custom hardware is worth it. Do **not** build on the toolkit's live stream for tracking: at
720x1280 it has about half the pixels per degree. The toolkit is worth a short experiment only for its Motion stream.

**2. Buy a Ray-Ban Meta (Gen 2) and use it with the same uploader (option A3). Cost: $379 for one, $1,137 for three, or $0 if he already owns one.**
Check first which model he has (section 1.3): if the Meta AI app offers a video resolution setting, the 3K mode is a
settings change, not a purchase.
Wins because it is the only purchasable option that clearly improves the tightest requirement: about 1.5 times the
pixels per degree in the 3K mode, from a camera pipeline already known to work for this tracker, plus selectable
stabilisation strength and a 60 fps mode to test against release blur. Same software as option 1, so nothing is
wasted. Loses on: still closed, still no exposure control or motion log, still the vendor app in the path, and the
3K figure rests on a press report of about 6.4 megapixels a frame; the actual file size, bitrate and whether detail
really rises 1.5 times need one ffprobe and one lane session to confirm. If option 1 is built, this is a $379
experiment that sets the bar any custom camera must clear: roughly 36 diagonal px/deg.

**3. Buy one Mentra Live as the open test platform (option B1). Cost: $449 for one, $1,347 for three.**
Wins on everything about control and integration: it is in stock, the app itself can pair, start and stop
recording, set size and frame rate, and receive the full file with no vendor app in the path; the phone stack is
Apache 2.0; the glasses appear to run Android (an inference); a recording light is always on. It is the closest bought thing to "a custom
device" and is the cheapest way to prototype the whole pairing-to-upload flow before designing hardware. Loses on
the tightest requirement at its default setting (0.77x the baseline), has no motion-sensor stream, publishes no
bitrate, codec or stabilisation details, has no independent footage review, and its battery figure (45 minutes of
video calling) rules out whole-session recording. Whether the 62 to 82 degree view recovers pixel density for video
is the test that decides if it is a tracker camera or only a software test bed.

**What loses outright.** White-label glasses (worse video than the baseline, closed app, 200-unit minimum for
anything custom; useful only as donor frames). Omi Glass Dev Kit and Brilliant Labs Halo (not video cameras). SeeIt
Glass 1 (no evidence it ships). Rokid, RayNeo, Xiaomi, Alibaba Quark and similar (no usable third-party kit for
recording, or not sold in the United States). The Meta toolkit stream as the video source (half the pixels).

**What this implies for a custom build.** No bought device offers (a) a gyroscope log time-synced to the video,
(b) manual exposure for video, (c) whole-session continuous recording, or (d) direct upload with no vendor app
together with baseline-or-better pixel density. A custom device is only worth building if it delivers at least two
of those while reaching about 24 diagonal px/deg (parity) and ideally 36 (Gen 2). If it cannot, options 1 and 2
together cost $379 and a few days of app work.

## 6. Unsourced, unverified and not done

Unsourced or from memory (not presented as fact above):

- Which Meta model the owner has. First-generation Ray-Ban Meta is the lead's inference from clip sizes, and the
  clip sizes do not settle it (Gen 2 also has a 1440p mode). This changes the cost of the second-ranked option to $0.
- Whether the field-of-view figures quoted by Meta (100 and 122 degrees) and Mentra (119 degrees) are diagonal.
- Gen 2 and Vanguard battery life, and the RayNeo V4 price: search summaries that did not name their source page.
- That Mentra Live runs Android, and that iOS development builds of a toolkit app work: inferences, not sourced.
- The Gen 1 lens field of view. Meta's guide gives 100 degrees for Gen 2 only; the baseline of 24 diagonal px/deg
  assumes Gen 1 is the same.
- The exact pixel size, bitrate and codec of Gen 2 "3K" video. About 2,190x2,920 is derived from a press figure of
  about 6.4 megapixels. "2203x2938" (from memory, unverified).
- The folder or album the Meta AI app writes imported clips to on Android, whether auto-import runs with the app in
  the background, and how long 1 GB takes to import.
- The text of the Meta Wearables Developer Terms and Acceptable Use Policy (not read); the number of test users a
  release channel allows; when store publishing opens (Meta says "soon").
- The Meta toolkit Motion module's sample rate, timestamps, and whether it can run while the glasses record a clip
  to their own storage.
- Mentra Live: sensor model, video bitrate and codec, stabilisation, storage size, maximum video size and frame
  rate, whether manual exposure and the field-of-view crop apply to video, whether the unit contains a motion sensor
  that is simply not exposed, whether the on-glasses Android client's source is published and can be replaced by the
  owner, and which countries it ships to.
- White-label field of view (100 to 110 degrees assumed), frame rate, bitrate and codec; the $80 upper sample
  price; Alibaba, Made-in-China and 1688 listings were not opened (only one Global Sources listing was tried, and it
  returned HTTP 429). The minimum order of 200 units comes from a single factory page.
- Background upload limits on iOS (from memory, unverified).

Checks that would settle the biggest unknowns without buying anything: ffprobe one Gen 2 3K sample clip from any
public source; look in the phone's file manager for the Meta AI album path after one import; read the two Meta
policy documents.

Tool use: 15 web search calls (one of them ran two queries internally), 22 pages read with content (one more,
Meta's help page, came back truncated and one Global Sources page returned HTTP 429). No sign-ups, forms or purchases. No private names in any query.
