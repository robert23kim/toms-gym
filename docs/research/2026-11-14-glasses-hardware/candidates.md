# Candidates: how to get a t30g capture device

Written 2026-11-14 by the synthesis stage. No web searches were run for this file. Every fact comes from
`REQUIREMENTS.md` and the four lane files in this folder, and the lanes' sourcing (URL and quote) is carried forward.
Lane status: buy-adapt PARTIAL, build-electronics PARTIAL, manufacturing DONE, app-integration DONE.
The status line is at the end of this file.

**Naming.** "C1" to "C35" are claim ids in the ledger (section 4) and nothing else. The stages of candidate C are
called C-pod (clip-on pod), C-frame (printed frame) and C-board (carrier board); "stage C1", "C2" or "C3" in prose
also mean those stages.

**Values in the structured reply.** `total_spend_usd` and `weeks` mean "to the first working unit, from scratch".
Each is one point value from the ranges below: A is $0 and 7 weeks; B is $449 per unit, $480 and 17 weeks; C-pod is
$175 per unit, $600 and 24 weeks.

Abbreviations, spelled out once: px/deg = pixels per degree of view; FOV = field of view; IMU = inertial measurement
unit (gyroscope and accelerometer); BOM = bill of materials; PCB = printed circuit board; CAD = computer-aided
design; GCS = Google Cloud Storage; BLE = Bluetooth Low Energy; SDK = software development kit; MJF = Multi Jet
Fusion, a nylon 3D-printing process; PA12 = polyamide 12, the nylon it prints; MOQ = minimum order quantity;
FCC = the US radio regulator.

**How hours become weeks in this file.** The owner has about 8 hours a week. The lanes estimate effort in full-time
working days and weeks. One full-time working day (8 hours) is therefore **one calendar week** here, and one
full-time week is **five calendar weeks**. Print and shipping lead times are added on top where they do not overlap.

**"Appears in the app" means stored, listed and playable** on a session page, plus an export the research tracker
reads (app-integration lane, section 1.5). A ball line on the lane inside the app means productising the tracker,
which is a separate project of several weeks full-time (item B9 in that lane) and is the same cost for every
candidate below. It is not costed here.

## 1. What the lanes established

1. The Meta toolkit (Meta's Wearables Device Access Toolkit) cannot give an app the recorded clips. Its live stream
   tops out at 720x1280 at 30 fps over Bluetooth, about 0.5x the baseline pixels per degree, so it fails need 1
   (buy-adapt 1.1; app-integration 2.5).
2. Meta's own phone app already copies full-quality clips into the phone's photo library ("auto-import on by
   default"). An app-side uploader can take them from there with no hardware. It is not known whether this runs
   without opening the Meta app (buy-adapt 1.2).
3. The app's resumable direct-to-GCS upload already moves large clips; a 372 MB file has been proven. A device needs
   no new byte path. It does need a device table and a token, because the upload routes do not authenticate anyone
   (app-integration 1.1, 1.2).
4. Clips are produced at an average of 2.2 Mbps over a session. Wi-Fi or a phone hotspot (5 to 20 Mbps) sends each
   clip before the next throw. BLE (0.3 to 1.2 Mbps) cannot keep up (app-integration 1.6, 2.3).
5. At a Meta-like view, only an encoder above 1080p improves the far end, and doubling it needs 4K. A 1080p board
   (such as the Raspberry Pi Zero 2 W) can only equal the baseline unless the lens is narrower. Candidate C gets its
   1.7x from a 3-megapixel camera behind a narrower, strongly distorted lens (build-electronics section (c)).
6. No bought device offers an IMU log synchronised to the video, manual exposure for video, or whole-session
   recording. These are what a custom build can add (buy-adapt 4 and 5; build-electronics (e)).
7. A Ray-Ban Meta Gen 2 recording in "3K" gives about 1.5x the baseline pixels per degree for $379, or for $0 if he
   already owns one. This is the cheapest improvement on need 1 (buy-adapt 1.3).
8. One to three units is a print-and-hand-assemble job. Every route through a factory or design house starts at five
   figures or at 200 units. No development board fits inside a temple arm (manufacturing 1; build-electronics D2).
9. Fabrication is cheap: a 5-piece flex PCB costs $25 and a nylon frame $20 to $110. Design labour and import duty
   (25 % to 37.5 %, with no low-value exemption) are the real costs (manufacturing 4.1, 6.2).
10. Every pixels-per-degree ratio in every lane rests on one unsourced number: the Gen 1 lens covering about
    100 degrees diagonally. One measurement of a known far-end length in an existing clip would fix all of them, at
    no cost (build-electronics section (c)).

## 2. Candidate paths

### 2.0 One yardstick for pixels on the far end, and where the lanes disagree

The two hardware lanes measure pixels per degree in two different ways, so their ratios do not compare directly.

- **buy-adapt** divides the diagonal pixels by the diagonal FOV. The baseline comes out at about **24 diagonal
  px/deg**.
- **build-electronics** uses the focal length in pixels at the centre of the frame, which is where the pins are.
  The baseline comes out at about **17 px/deg at the centre**. This lane warns against the diagonal method.

**This file uses the centre (focal-length) method** and recomputes the buy-adapt devices with it. The arithmetic is
the synthesis stage's own and is shown so it can be checked:

- Meta today: f = (2285/2)/tan(50 deg) = 959 px.
- Mentra Live at its default wide view (1920x1080, 119 degrees diagonal): f = (2203/2)/tan(59.5 deg) = 649 px. That is
  **0.68x** the baseline by the centre method, against 0.77x by buy-adapt's diagonal method.
- Mentra Live with its view narrowed: the still sensor (3264x2448, 4,080 px diagonal over 119 degrees) has
  f = 2040/tan(59.5 deg) = 1,201 px. Any crop is capped at that sensor detail, so the most it can reach is
  **about 1.25x**. buy-adapt gives 1.1x to 1.4x. Both assume the crop applies to video at full sensor detail, which
  the documents do not state.
- The 0.68x assumes a distortion-free lens at 119 degrees. Treat 0.68x to 0.77x as the range. The verdict, worse
  than the baseline, does not change.
- Gen 2 at "3K" with the same lens: about **1.5x** by either method, because only the linear pixel count changes.

When a ratio below carries no label, it is by the centre method. Every ratio inherits the unsourced Gen 1 lens
figure of about 100 degrees diagonal (section 1, item 10).

### 2.1 Comparison at a glance

"First unit" means total spend to one working unit, including tools, shipping and duty. "Three units" means total
spend to three. Weeks are calendar weeks at 8 hours a week, to the first working unit.

| | A. Meta glasses + app uploader (zero hardware) | B. Mentra Live (open glasses bought off the shelf) | C. Custom Linux camera pod, then a printed frame |
|---|---|---|---|
| Per-unit BOM | $0 (owned); $379 for a Gen 2 | $449 | $150 to $200 (dev-board pod); $115 to $145 in parts (carrier board) |
| Total spend, first unit | $0 ($379 if he buys a Gen 2) | about $480 | about $500 to $700 (pod) |
| Total spend, three units | $0 for one wearer; $1,137 for three Gen 2 | about $1,400 | about $1,000 to $1,800 (printed frame); $1,500 to $3,300 with a self-designed carrier board |
| Weeks to first unit | about 6 to 7 | about 14 to 20 | about 21 to 27 (14 to 20 if A's app work is already done) |
| Far-end px/deg vs baseline | 1.0x (Gen 2 at 3K: 1.5x) | 0.68x default; up to about 1.25x narrowed (untested) | about 1.7x (Luckfox estimate); 1.0x (Pi Zero fallback) |
| IMU log synchronised to video | No | No (not exposed) | Yes |
| Clip reaches the app without another app | No (Meta's app stays in the path) | Yes | Yes |
| Proves the hardware design path | No | No | Yes |

### 2.2 Candidate A: the Meta glasses he owns plus an app-side uploader (the zero-hardware baseline)

**What it is.** He keeps the Meta glasses. The app gains capture sessions and an uploader that takes the
full-quality clips Meta's phone app has already put in the phone's gallery. The toolkit's live stream is **rejected
as the video source**, because it carries about 0.5x the pixels (section 1, item 1). The toolkit is kept only as an
optional experiment with its Motion stream.

**The lanes describe two different uploaders.**

- *A-web.* app-integration lane 2.6 and item F2: a "Session upload" page in the app. It picks many clips from the
  gallery and sends each through the existing resumable client with compression off. No native code is needed, and it
  works on an iPhone browser.
- *A-watch.* buy-adapt lane 1.2: a feature in the Android build that watches the phone's media library through
  Android's MediaStore and uploads new glasses clips by itself. This needs a native Capacitor plugin and the
  read-media-video permission. It is the only form that drops the manual step.

**This file uses A-web first and A-watch second.** A-web is no-native-code work and is reused by every later
candidate as the fallback path.

**Architecture.**

| Part | What it is |
|---|---|
| Camera | Meta's: 1376x1824 portrait, HEVC 10-bit, 30 fps, about 15 Mbps |
| Compute and power | Meta's. Gen 1: 154 mAh, "up to 4 hours mixed use" (vrarwiki). Gen 2: "up to eight hours" (Meta) |
| Radio | Meta's. The clip goes from the glasses to Meta's phone app, then into the phone gallery |
| Frame | Ray-Ban, 49 to 52 g |
| Route to the app | Phone gallery, then A-web picker (or A-watch), then `/upload/resumable-url` to GCS, then a new `CaptureSession` / `CaptureClip` record, then the `/sessions` page |

**Bill of materials.**

| Part | Vendor | Unit price | URL |
|---|---|---|---|
| Ray-Ban Meta (owned) | - | $0 | - |
| Optional: Ray-Ban Meta (Gen 2), only if the owned pair has no resolution setting | Meta / retail | $379 (a third-party tracker updated 2026-06-01; Meta's store was not checked) | https://testlisting.pages.dev/ai-glasses-toolkit.htm |

**Cost both ways.** (i) Per unit: $0, or $379 for a Gen 2. (ii) Total spend: $0 to the first working unit, or $379
with a Gen 2. Three units: $0 if only he wears them, $1,137 for three Gen 2 pairs. There are no tools, duty or respins.
Cloud cost is negligible.

**Calendar weeks at 8 h/week.** The items are from the app-integration lane, section 5.3:

- A-web needs B1 (0.5 day), B2 (2 days), F1 (2 to 3 days), F2 (1 day) and F4 (0.5 day): 6 to 7 days, so **about 6 to
  7 weeks**.
- Adding B5 (test registration, 1 day) and B6 (an export for the tracker, 0.5 day) makes about 8 weeks.
- A-watch is not sized in any lane. By analogy with the lane's other native plugins (N4: 1 to 2 weeks full-time) it
  is 5 to 10 more weeks.
- The app-integration lane calls step 0 "1-2 days", but its own item sizes add up to 6 to 7 days. This file uses the
  item sum.

**Skills.** Bought: none. Learned: nothing new. React, Flask and migrations are his home ground. A-watch adds a little
Kotlin.

**Score against REQUIREMENTS.md.**

| Need or envelope | Score against the Meta baseline |
|---|---|
| 3.1 Far-end pixels | Equal, 1.0x by definition. A Gen 2 at 3K is better, at about 1.5x (a press figure of about 6.4 megapixels per frame; not ffprobed) |
| 3.2 Release blur | Equal: no exposure control. A Gen 2 adds 60 fps, but only at about 0.8x the pixels |
| 3.3 Camera motion | Equal: no IMU in the clip. The toolkit's Motion module is experimental, with undocumented timing |
| 3.4 Release and pin-hit events | Equal: stereo audio only |
| 3.5 Frame rate | Equal: 30 fps |
| 3.6 FOV | Equal (proven on 32 clips) |
| 4 Awake 2 h and record 15 min | Equal: proven in the 2026-11-08 session |
| 4 Storage 2 GB | Equal: 32 GB on the glasses |
| 4 Move 1 GB in minutes | Equal or worse. The glasses-to-phone import is Meta's and its time is unmeasured. Phone to cloud takes 7 to 28 minutes at 5 to 20 Mbps and can wait for home Wi-Fi |

**What it proves toward "links into the app, easy setup, mobile".** It builds and proves the whole backend half:
sessions, clip records, the resumable upload with the compressor bypassed, and the export to the tracker. Every
other candidate reuses that work. It does not meet "without opening another app": Meta's app and a manual pick stay
in the path, and A-watch only partly removes them. Pairing is Meta's own.

**Top three risks.**

1. Auto-import may need the Meta app opened by hand. If so, A-watch saves little over A-web.
2. Gallery album naming and file metadata on Android are unverified, so filtering for glasses clips may be fiddly.
3. It leaves needs 3.2 to 3.4 untouched for good. A Gen 2 helps only need 3.1, and its 3K gain rests on a press
   figure.

### 2.3 Candidate B: Mentra Live, open camera glasses bought off the shelf

**What it is.** Mentra Live is a $449 pair of camera glasses with an open (Apache 2.0) phone stack and a Bluetooth
SDK. The app itself can pair with them, start and stop recording, and get the full file with no vendor app in the
path. It is the closest bought thing to a custom device. It costs nothing in hardware design, but it is worse than
the baseline on need 1 unless its view-narrowing control works for video.

**Architecture.**

| Part | What it is |
|---|---|
| Camera | "HD 1080p videos", "119° field of view, landscape orientation", stills "3264 × 2448". `setCameraFov` clamps 62 to 118 degrees. It is not stated whether that applies to video. Bitrate, codec and sensor are not published |
| Compute | "MTK8766 chipset". That it runs Android is an inference |
| Power | "45 minutes video calling · 8+ hours normal use" |
| Radio | Wi-Fi and Bluetooth |
| Frame | 43 g, with an always-on "white privacy light" |
| Route to the app | The app's Android build wraps Mentra's Android library in a Capacitor plugin and pairs once. Then either (1) `startVideoRecording(...)` with a webhook, where the glasses POST each clip as multipart over Wi-Fi to a new receiver that streams to GCS (it must sit outside Cloud Run's 32 MiB cap, item B8), or (2) the phone joins the glasses' hotspot, pulls from `/api/gallery`, and uploads by the existing resumable path |

**Bill of materials.**

| Part | Vendor | Unit price | URL |
|---|---|---|---|
| Mentra Live (glasses, charging case, cable) | Mentra | $449 ("Ships in 2–5 business days") | https://mentraglass.com/live |
| USB power meter (to measure battery drain) | any | about $15 (lane estimate) | - |

There is a price conflict. The vendor page read on 2026-11-14 says $449. January 2026 launch coverage said $299
(Engadget and TechSpot, snippets), and one site listed $349. **This file uses $449.**

**Cost both ways.** (i) Per unit: $449. (ii) Total spend: about $480 to the first working unit (the unit plus a meter
and sales tax not counted), and about $1,400 for three. Duty is $0, because it is bought from a US vendor
(the company's US base is from memory, unverified). There are no respins.

**Calendar weeks at 8 h/week: about 14 to 20.**

| Work | Full-time estimate (app-integration lane, judgement) | Calendar weeks |
|---|---|---|
| App half: B1, B2, F1 | about 5 days | 5 |
| Capacitor plugin over Mentra's Android SDK | 1 to 2 weeks | 5 to 10 |
| Webhook receiver, B8 | 1 to 2 days | 1 to 2 |
| View-crop test and one lane session | synthesis estimate | about 2 |

If A has already been built, the app-half line drops out.

**Skills.** Bought: the whole device. Learned: Kotlin for a Capacitor plugin, and the vendor SDK.

**Score against REQUIREMENTS.md.**

| Need or envelope | Score against the Meta baseline |
|---|---|
| 3.1 Far-end pixels | **Worse**: 0.68x by the centre method (0.77x diagonal) at the default view. Up to about 1.25x if a narrowed view keeps sensor detail in video, which is untested |
| 3.2 Release blur | Equal for video. Manual exposure (`exposureTimeNs`, `iso`) is documented for photos only |
| 3.3 Camera motion | Equal: no gyroscope stream. The phone kit gives only "Head-up state changes" |
| 3.4 Events | Equal: microphone stream and button events |
| 3.5 Frame rate | Equal at 30 fps. The maximum is not documented |
| 3.6 FOV | Equal at 119 degrees. Worse if narrowed to 62 degrees: the lane may leave the frame |
| 4 Awake 2 h, record 15 min | Probably equal: "8+ hours normal use", and 45 minutes of video calling covers 15 minutes of recording. A whole 65-minute session recorded continuously does not fit |
| 4 Storage | Unknown: not published |
| 4 Transfer | **Better**: each clip is uploaded over Wi-Fi at stop time, so there is no end-of-session transfer and no vendor app |

**What it proves toward "links into the app, easy setup, mobile".** Nearly all of the integration story: one-time
pairing from the app, app-driven recording, and the clip landing in the account with no other app. This is
architecture 2 already built by a vendor (app-integration 2.5). It proves nothing about designing or making hardware.
It is Android-first: there is no iOS project in the repo.

**Top three risks.**

1. The far end is worse than today unless the view crop works for video at sensor detail. This is the first thing to
   test after buying.
2. There is no IMU stream, so need 3.3 is never met. Whether the unit has an IMU that is simply not exposed is unknown.
3. Vendor dependence. There is no independent footage review. The multipart webhook needs a receiver outside the
   32 MiB cap. Side-loading a custom on-glasses app is unverified.

### 2.4 Candidate C: a custom Linux camera pod, then a printed frame, then a carrier board

**What it is.** He builds his own device from bought development boards. It starts as a clip-on pod on his own
glasses, carrying a Rockchip RV1106G3 board, a $9 camera, a motion sensor and a protected cell. The device uploads
each clip straight to the app over the phone's hotspot with a per-device token. Only once the pod beats A does it
move to a nylon-printed frame, and later to his own small carrier PCB. This is the only path that answers "how do I
design and get manufactured", and at 1 to 3 units "manufactured" means printed and hand-assembled (manufacturing
lane, headline 1).

**Architecture.** This is BOM 2 in the build-electronics lane, with architecture 2 from the app-integration lane.

| Part | What it is |
|---|---|
| Camera | SmartSens SC3336 camera, 2304x1296, 3.95 mm lens at F2.0, 98.3 degrees diagonal, "<33%" distortion. Mounted for portrait at about 48x86 degrees, about 28 to 30 px/deg at the centre (about 1.7x, estimate) |
| Compute | Luckfox Pico Ultra W (RV1106G3). Hardware H.265 encoding up to 3072x1728 at 30 fps, 8 GB eMMC storage, on-board microphone. The fallback is a Raspberry Pi Zero 2 W (BOM 1): easier software, 1080p H.264 only, so 1.0x |
| Motion and controls | Adafruit LSM6DSOX six-axis IMU read on the same clock as the frames, written as a Gyroflow `.gcsv` sidecar. Push button, forward light |
| Power | Adafruit 500 mAh (1.9 Wh) protected cell plus a charger/boost board. Estimated at two button-per-throw sessions, or about 2 hours continuous. Recording power is assumed (0.8 W), not measured |
| Radio | On-board Wi-Fi 6 (2.4 GHz only) and Bluetooth 5.2, as a pre-made module. For 5 units or fewer built for personal use, no FCC filing is needed (47 CFR 15.23) |
| Frame | Stage C1: a printed pod clipped to the temple of his own glasses, with the board and cell on a strap behind the head (about 30 g on the face), or as pods on both arms (55 to 60 g). Stage C2: an MJF PA12 nylon frame with a non-folding camera temple. Stage C3: his own carrier board for the 30x30 mm Core1106 module |
| Route to the app | On each clip close, the device calls `POST /capture/clips` with `Authorization: Bearer <device token>` and gets a GCS resumable session URI. It PUTs the file in 8 MiB chunks, then calls complete. Pairing: the app shows a QR code holding the hotspot details and a one-time claim code; the device's camera reads it. No native phone code; works from an iPhone browser |

**Bill of materials, stage C1 (one unit).** Prices are from the build-electronics lane, BOM 2.

| Part | Vendor | Unit price | URL |
|---|---|---|---|
| Luckfox Pico Ultra W (RV1106G3) | Waveshare | $36.99 to $81.99 across variants; budget $45 to $82 | https://www.waveshare.com/Luckfox-Pico-Ultra.htm |
| SC3336 3 MP camera (B) | Waveshare | $8.99 | https://www.waveshare.com/product/luckfox/boards-modules/luckfox-pico-core1106/sc3336-3mp-camera-b.htm |
| Lithium polymer cell, 500 mAh, protected | Adafruit | $7.95 | https://www.adafruit.com/product/1578 |
| Charger plus 5 V boost board | hobby vendor | about $18 (lane estimate) | - |
| LSM6DSOX motion sensor board | Adafruit | $11.95 (snippet) | https://www.adafruit.com/products/4438 |
| Light, resistor, button, wire | any | about $5 (lane estimate) | - |
| Printed pod and strap | print service | about $30 (lane estimate) | - |
| Shipping from China and duty on the Waveshare parts | - | $20 to $40 (lane estimate) | - |
| **Total** | | **about $150 to $200** | |

**Stage C3 parts (per unit).**

| Part | Vendor | Unit price | URL |
|---|---|---|---|
| Luckfox Core1106 module | Waveshare / Luckfox | $36.99 | https://www.waveshare.com/core1106.htm |
| Four-layer carrier board, 5 assembled | JLCPCB | $100 to $250 per 5 (lane estimate on public set-up fees) | https://jlcpcb.com/solutions/pcb-prototype-assembly |
| Camera, cell, printed parts | as above | about $57 | - |
| **Total** | | **about $115 to $145 in parts** | |

**Cost both ways.**

(i) Per unit: $150 to $200 for the pod; $115 to $145 in parts for the carrier board.

(ii) Total spend:

| Stage | Spend |
|---|---|
| To the first working pod | **about $500 to $700**: the C1 BOM ($175 midpoint), bench tools (about $200), 2 to 4 pod prints (about $40), spare cell and camera (about $20), one wrong purchase (about $50), extra shipping (about $40). The upper end adds a Pi Zero fallback ($155) or the RunCam camera test ($180, roadmap stage 2) |
| To three units in a printed frame | **about $1,000 to $1,800**: two more C1 BOMs ($350), 3 to 5 frame iterations at $20 to $110, and $0 to $300 for prescription lenses (a clip-on design keeps his own lenses) |
| Adding a self-designed carrier board | +$500 to $1,500 (2 to 3 spins at $150 to $500 landed), so **$1,500 to $3,300** for three units |
| Hiring the carrier-board design instead | +$2,500 to $13,000 (manufacturing lane) |
| Hiring the frame design | +$1,500 to $8,000 |

Where the lanes disagree on cost inputs:

- **Bench tools.** build-electronics says about $75 (iron $40, meter $15, multimeter $20). manufacturing says $300 to
  $800, which includes a microscope and an optional printer. This file uses about $200: the manufacturing list at its
  low end, without the printer, microscope or hot-air station.
- **A hired carrier-board design.** build-electronics says $500 to $2,000, unsourced. manufacturing says $2,000 to
  $12,000, from Fiverr rates of $45 to $80 an hour, a Cad Crowd figure of "$10,000+", and a comparable job post with a
  "$750" budget that it reads as a floor. This file uses manufacturing's range.
- **Duty on boards from China.** It is 25 % or 37.5 % depending on the source. This file uses 37.5 %, the lane's own
  planning rate.

**Calendar weeks at 8 h/week.**

| Work | Full-time estimate | Calendar weeks |
|---|---|---|
| App half including device pairing: B1 to B7 and F1 to F4 | 8 to 10 days (app-integration 5.3) | 8 to 10; 2 to 3 more if A is done |
| Device software in Python on the Pi: recorder, uploader, QR pairing, motion logger | 1 to 2 weeks (app-integration 5.3) | 5 to 10 |
| The same on the Rockchip board | the build-electronics lane calls this "the largest single cost in time"; synthesis estimate 1.5 to 2x the Pi | 10 to 15 |
| Bench work and soldering | about 1 week | 1 |
| Pod in beginner CAD (Onshape or Python CAD), with 2 to 4 prints at 3 to 5 working days each plus shipping | "a few weekends" | 3 to 4, overlapping |

That gives **about 21 to 27 weeks** to the first working pod with hand-inserted credentials, or 14 to 20 weeks if A
is already built. The Pi fallback saves about 5 weeks and loses the pixel gain.

The manufacturing lane gives later stages as 4 to 8 weeks (printed frame) and 8 to 16 weeks (carrier board) at an
unstated pace. This file doubles them for 8 hours a week: **8 to 16 more weeks** for three units in a printed frame,
and **16 to 32 more** for the carrier board.

**Skills.**

- Bought: printing (MJF nylon), the radio module, a pre-made battery charger, and optionally hourly help for CAD or
  layout.
- Learned: soldering (an evening); beginner CAD; Rockchip Buildroot and its C media library (or Pi Linux); camera
  exposure control; and at stage C3, KiCad for a simple carrier board (one to two months).
- Never learned at this budget: a glasses-shaped board with the processor soldered on. That is bought only, at $3,000
  to $10,000 (build-electronics, unsourced).

**Score against REQUIREMENTS.md (stage C1, Luckfox).**

| Need or envelope | Score against the Meta baseline |
|---|---|
| 3.1 Far-end pixels | **Better**, about 1.7x (28 to 30 against about 17 px/deg). This is an estimate from the vendor's lens figures, and the lens distortion must be removed in the tracker |
| 3.2 Release blur | **Better**: manual exposure on the Rockchip camera stack (from memory, unverified). F2.0 gives a relative light of 1.5 per encoded pixel |
| 3.3 Camera motion | **Better**: an IMU at 200 to 800 Hz stamped on the frame clock, as a `.gcsv` sidecar |
| 3.4 Events | **Better**: IMU plus microphone. The microphone is mono, against Meta's stereo |
| 3.5 Frame rate | Equal: 30 fps |
| 3.6 FOV | **Possibly worse**: about 48x86 degrees against Meta's about 71x87. It needs the pin-deck wander measurement before it is trusted |
| 4 Awake 2 h, record 15 min | Probably equal: a 500 mAh cell against an estimated 220 mAh need. Recording power is unmeasured |
| 4 Storage | Meets the need (8 GB eMMC against 2 GB needed); less than Meta's 32 GB |
| 4 Transfer | **Better**: each clip goes in 13 to 53 s at 5 to 20 Mbps, between throws, with no end-of-session transfer. The radio is 2.4 GHz only |

**What it proves toward "links into the app, easy setup, mobile".** Everything in the target flow of REQUIREMENTS.md
section 5. Pairing is from any phone browser by QR, with no laptop. Clips land in the paired account with no other
app. The device proves which account it belongs to by a revocable token. It also proves the parts the user asked
about: that a camera he chose beats Meta's, and what designing and making one costs.

**Top three risks.**

1. **Software time on the Rockchip.** It needs a vendor build system, C interfaces and a small community. Falling back
   to the Pi loses the pixel gain.
2. **The pixel and view numbers are estimates.** The 1.7x rests on the assumed Meta lens figure. A narrower view may
   lose the lane during the approach.
3. **Wearability.** Recording power and heat are unmeasured, the pod is one-sided, and the prototype looks like a
   gadget. A frame that hides the electronics is professional design work, outside the budget.

## 3. Staged roadmap

**The honest answer is: do not build hardware yet.** Run the free checks, then build A. Build C only if two pieces
of evidence come back, both described below:

- more far-end pixels measurably improve the tracker, **and**
- something only a custom device gives (the IMU log, exposure control, or upload with no other app) is worth about
  20 weeks of evenings.

B is a side branch, worth buying only if the integration flow matters more than the pixels.

| Stage | What | Spend at the stage (cumulative) | Calendar weeks | Gate to go on |
|---|---|---|---|---|
| 0. Free checks | (a) In the Meta AI app, look for a video resolution setting under Device settings > Media > Video settings. If it is there, he owns a Gen 2 or Oakley and 3K is a settings change. (b) Record a clip, do not open the Meta app, and see whether it reaches the gallery. (c) In one existing clip, measure a known far-end length in pixels (the lane width at the pin deck is 1.05 m, from memory), convert it to px/deg, and rescale every ratio in this file. (d) Measure how far the pin deck wanders from the frame centre across the 32 clips; that is the minimum safe view. (e) Run a phone speed test (or `iperf3`) on the lane to see the hotspot uplink. | $0 | 1 to 2 | Always go on to stage 1. Results (c) and (d) decide whether C's narrower lens is usable |
| 1. Candidate A-web | Capture sessions, clip records, the Session-upload page, the `/sessions` pages, and the tracker export (B1, B2, B5, B6, F1, F2, F4) | $0 | 6 to 8 | **Pass**: the 32 clips of one real session are listed in capture order, play on the phone, and match the source file's size and SHA-256 hash (proving the compressor was bypassed). The export recreates a folder the research scripts accept |
| 2. Does pixels pay? | Record one bowling session at 3K on a Gen 2: $0 if stage 0(a) found one, otherwise $379. Optionally, as the cheapest custom-camera test, a RunCam Thumb 2 on a cap with a power bank ($180; 4K with its own gyro file, but no link to the app) | $0 to $560 | 2 to 3 | **Pass**: the more-pixel clips improve far-end recall or pin-row crossing on a freshly labelled set from that session, scored against a same-day baseline session on the owned glasses. Freeze the count before changing any rule (per `RULES.md`). **Fail**: the main hardware case collapses. Stop, unless the IMU or release-blur case is wanted on its own |
| 2b. Optional, B | Buy Mentra Live only if pairing-to-upload with no other app is the priority. Its first test is the view crop on video, measured against the stage-0(c) number | +$480 | 14 to 20 (8 to 14 after A) | Keep it only if the narrowed view reaches at least 1.0x with the lane in frame. Otherwise use it as an integration test bed only |
| 3. Candidate C1, the pod | Luckfox pod plus architecture 2, hand-provisioned token first, QR pairing second | +$500 to $700 (so about $500 to $1,260 cumulative) | 14 to 20 after A | **Pass** (the buy-adapt lane's bar): parity or better on far-end pixels (at least 1.0x, ideally at least 1.5x, the Gen 2 bar), **plus** at least two of {IMU log synchronised to video, manual exposure for video, whole-session recording, direct upload with no other app}. Also: a clip recorded at time T is playable at T + 60 s; a hotspot dropped mid-upload recovers with no duplicate; the pod surface stays under 48 degrees C after 15 minutes of recording |
| 4. C2, printed frame | MJF PA12 nylon frame, non-folding camera temple, front light wired in hardware; three units | +$500 to $1,100 (about $1,000 to $1,800 for three units) | 8 to 16 | **Pass**: 2 hours worn at or under about 55 g, a second person can wear it, and three units work |
| 5. C3, carrier board | A self-taught KiCad carrier for the Core1106 module; plan 2 to 3 spins | +$500 to $1,500 (about $1,500 to $3,300) | 16 to 32 | Only if C2 is too bulky to use. Hiring this design (+$2,500 to $13,000) breaks either reading of the $1,000 budget |
| Closed routes | Factory customisation of an existing glasses platform (200-unit minimum order), a design house ($25,000 and up), injection moulding ($9,000 to $40,000 in tooling) | - | - | Only for 50+ units given to other people. Beyond 5 units the radio exemption also ends |

**Budget reading.**

- If "$1,000" means the whole effort, stages 0 to 3 fit: about $500 to $700 without the optional Gen 2 and RunCam, and
  over $1,000 (up to about $1,260) with both.
- Stage 4 reaches $1,000 to $1,800.
- If "$1,000" means one unit's parts, every candidate fits, including the carrier board.

**The third-person case** (lifting and the 100 Club). Only C serves it, and only if the stage-1 pod's clip is drawn to
also fit a tripod thread or a phone clamp (manufacturing lane, section 7).

## 4. Claims ledger

A claim is listed if its failure would change the recommendation or move a cost by more than 20 %. "Lane estimate"
means the lane's own arithmetic or memory, with no source. Candidates: A, B, C (stages C-pod, C-frame, C-board).

| id | claim | kind | source | lane | candidates |
|---|---|---|---|---|---|
| C1 | The Meta toolkit's live stream tops out at 720x1280 at 30 fps, about 0.5x the baseline pixels per degree | spec | https://mixed-news.com/en/meta-dat-camera-720x1280-lower-resolution-higher-quality/ | buy-adapt, app-integration | A (rejects the toolkit as video source) |
| C2 | The toolkit gives no access to the full-quality clips recorded on the glasses (a negative from four Meta pages) | capability | https://raw.githubusercontent.com/facebook/meta-wearables-dat-android/main/CHANGELOG.md | buy-adapt | A |
| C3 | The Meta AI app imports recordings into the phone's photo app, with auto-import "on by default" on most Android 13+ and iOS phones | capability | https://www.meta.com/ai-glasses/learn/guide-shooting-pov/ | buy-adapt | A |
| C4 | Auto-import delivers clips to the phone gallery without the Meta AI app being opened (unverified) | capability | lane estimate | buy-adapt | A (A-watch) |
| C5 | The Gen 1 lens covers about 100 degrees diagonally, giving a baseline of about 17 px/deg at the centre (24 diagonal) | spec | lane estimate (Meta publishes 100 degrees for Gen 2 only) | build-electronics, buy-adapt | A, B, C |
| C6 | Ray-Ban Meta Gen 2 records "Up to 3K Ultra HD at 30 fps", about 6.4 megapixels per frame, so about 1.5x the baseline pixels per degree | spec | https://www.meta.com/ai-glasses/learn/guide-shooting-pov/ ; https://www.techradar.com/computing/virtual-reality-augmented-reality/meta-ray-ban-gen-2-smart-glasses-are-official-here-are-5-key-upgrades-you-need-to-know-about | buy-adapt | A (Gen 2 variant), roadmap stage 2 |
| C7 | A Ray-Ban Meta Gen 2 costs $379 | price | https://testlisting.pages.dev/ai-glasses-toolkit.htm ; https://about.fb.com/news/2025/09/ray-ban-meta-gen-2-better-battery-life-video-capture/ | buy-adapt, build-electronics | A |
| C8 | The app's resumable direct-to-GCS upload handled a 372 MB video with a drop and a resume | capability | lane estimate (repo memory note `upload_32mb_limit.md`) | app-integration | A, B, C |
| C9 | A GCS resumable session URI acts as its own credential and lasts one week, so a device needs no cloud key | capability | https://docs.cloud.google.com/storage/docs/resumable-uploads | app-integration | C |
| C10 | Clips are produced at an average of 2.2 Mbps over a session, so a 5 to 20 Mbps hotspot clears each clip between throws | physics | lane estimate (from REQUIREMENTS.md section 4) | app-integration | B, C |
| C11 | Measured BLE throughput is 0.3 to 1.2 Mbps, too slow for 1 GB per session | spec | https://developer.apple.com/forums/thread/770717 ; https://community.infineon.com/t5/ModusToolbox-Blog/BLE-Throughput-Rate-Benchmark-Test-for-Cypress-BT-SoCs/bc-p/267238 | app-integration | C (excludes BLE for bytes) |
| C12 | The app-side work for A-web is 6 to 7 full-time days, and the whole device app half is 8 to 10 days | effort | lane estimate | app-integration | A, B, C |
| C13 | Mentra Live costs $449 and "Ships in 2–5 business days" | price | https://mentraglass.com/live | buy-adapt | B |
| C14 | Mentra Live records "HD 1080p" over a "119° field of view", 0.68x the baseline by the centre method | spec | https://mentraglass.com/live | buy-adapt | B |
| C15 | Mentra's `setCameraFov` (62 to 118 degrees) applies to recorded video at sensor detail (unstated in the docs) | capability | https://docs.mentraglass.com/bluetooth-sdk/api-reference.md | buy-adapt | B |
| C16 | Mentra's SDK lets an app start recording and have the glasses POST the file to a webhook over Wi-Fi | capability | https://docs.mentraglass.com/bluetooth-sdk/camera-streaming.md | buy-adapt, app-integration | B |
| C17 | Mentra exposes no gyroscope or accelerometer stream for Live ("Gyroscope, magnetometer, and fused orientation aren't exposed yet") | capability | https://docs.mentraglass.com/app-devs/core-concepts/imu.md | buy-adapt | B |
| C18 | A Capacitor plugin wrapping a vendor SDK is 1 to 2 full-time weeks per platform | effort | lane estimate | app-integration | B, A (A-watch) |
| C19 | The Luckfox Pico Ultra W (RV1106G3) hardware-encodes H.265 up to 3072x1728 at 30 fps and has Wi-Fi 6 and Bluetooth 5.2 | spec | https://www.waveshare.com/Luckfox-Pico-Ultra.htm ; https://www.cnx-software.com/2024/06/21/luckfox-pico-ultra-micro-development-board-features-mipi-csi-wifi-6-ethernet-poe-gpio-headers/ | build-electronics | C |
| C20 | The Luckfox Pico Ultra W costs $36.99 to $81.99 across variants | price | https://www.waveshare.com/Luckfox-Pico-Ultra.htm | build-electronics | C |
| C21 | The SC3336 camera ($8.99, 3.95 mm, 98.3 degrees, "<33%" distortion) gives 28 to 30 px/deg at the centre, about 1.7x | spec | https://www.waveshare.com/product/luckfox/boards-modules/luckfox-pico-core1106/sc3336-3mp-camera-b.htm (the px/deg figure is lane arithmetic) | build-electronics | C |
| C22 | The Raspberry Pi Zero 2 W ($15) encodes only H.264 at 1080p30, so it can at best equal the baseline at a Meta-like view | spec | https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/ | build-electronics | C (fallback) |
| C23 | The RV1106 board idles at 0.15 to 0.3 W, and recording draws about 0.8 W, so 500 mAh covers two button-per-throw sessions | physics | https://forums.luckfox.com/viewtopic.php?t=1822 (idle only; recording power is a lane estimate) | build-electronics | C |
| C24 | Writing the device software on the Rockchip stack takes 1.5 to 2x the Pi's 1 to 2 full-time weeks | effort | lane estimate | build-electronics, app-integration | C |
| C25 | A six-axis IMU stamped on the same monotonic clock as the video frames gives a synchronised motion log | capability | lane estimate (format: https://docs.gyroflow.xyz/app/technical-details/gcsv-format) | build-electronics, app-integration | C |
| C26 | Manual video exposure is available on the Rockchip and Pi camera stacks | capability | lane estimate (from memory) | build-electronics | C |
| C27 | The safe view must be at least about 35x55 degrees plus head wander. The SC3336 portrait view of about 48x86 degrees fits | physics | lane estimate | build-electronics | C, B (narrowed) |
| C28 | MJF PA12 printing costs $0.275 per gram at JLC3DP, so a frame set is $20 to $110 per iteration landed | price | https://jlc3dp.com/news/drastic-material-price-cuts-and-adjusted-post-processing-service-fees | manufacturing | C-frame |
| C29 | A 5-piece flex PCB is $25 at JLCPCB, and a landed spin of 5 assembled boards is $150 to $500 | price | https://jlcpcb.com/blog/flex-pcb-cost-pricing-guide (the per-spin figure is a lane estimate) | manufacturing | C-board |
| C30 | Assembled and flex boards from China pay 37.5 % duty (25 % in a second blog), with the $800 de minimis exemption suspended since 24 June 2026 | price | https://www.atlaspcb.com/news/news-pcb-tariff-section-301-exclusion-expiry-november-2026/ ; https://www.thompsonhinesmartrade.com/2026/06/cbp-issues-interim-final-rules-indefinitely-suspending-the-de-minimis-exemption-for-imports/ | manufacturing | C-pod, C-board |
| C31 | A hired board design for a small camera carrier costs $2,000 to $12,000 (the other lane says $500 to $2,000) | price | https://www.fiverr.com/resources/guides/costs/electronics-design-engineer ; https://www.cadcrowd.com/job/9896-camera-smart-glasses-pcb-design | manufacturing, build-electronics | C-board |
| C32 | Five or fewer home-built, unmarketed radio devices for personal use need no FCC equipment authorisation | availability | https://www.law.cornell.edu/cfr/text/47/15.23 | manufacturing | C |
| C33 | Customising a factory glasses platform requires at least 200 units per model | minimum-order | https://microwear.info/ai-glasses ; https://menafn.com/1111956109/Top-10-Wearable-Odms-Now-Customize-Both-Hardware-And-Firmware-From-200-Pieces-As-Glasses-Shipments-Rise-54 | buy-adapt, manufacturing | closed route |
| C34 | White-label V821 glasses record about 1600x1200 (about 0.8x the baseline), behind a closed vendor app | spec | https://musicphotolife.com/2026/01/padmate-viewmate-review-ai-smart-glasses/ | buy-adapt, manufacturing | closed route (donor frame only) |
| C35 | The bench tools cost about $200 (the lanes say $75 and $300 to $800) | price | lane estimate | build-electronics, manufacturing | C |

## 5. Gaps

### 5.1 What no lane answered

1. **The real far-end pixels per degree of today's clips.** Every ratio rests on the assumed 100-degree Gen 1 lens
   (C5). This is fixable at no cost in stage 0(c).
2. **How far the pin deck wanders across the frame during a throw**, so nobody knows how narrow a lens is safe for
   C, or for B narrowed. This is fixable at no cost in stage 0(d).
3. **Which Meta model he owns**, and whether auto-import runs in the background. This is a one-minute phone check.
4. **Power and heat while recording** on any board (Pi, Luckfox, Aura). Every battery figure for C assumes a
   recording power.
5. **Gen 2 3K files.** The exact pixel size, bitrate and file size were not found. The 1.5x is derived from a
   press figure of about 6.4 megapixels.
6. **Mentra Live.** Its sensor, video bitrate, codec, stabilisation, storage, maximum video size, whether the view
   crop and manual exposure apply to video, whether it has an IMU that is not exposed, and whether a custom
   on-glasses app can be side-loaded.
7. **Whether more far-end pixels actually raise tracker recall.** REQUIREMENTS.md asserts this. No lane can test it,
   and roadmap stage 2 is built to test it.
8. **Meta's Wearables Developer Terms and Acceptable Use Policy** were not read. This matters only if the toolkit's
   Motion stream is used.
9. **Hotspot uplink speed inside his bowling alley.**
10. **A-watch effort.** No lane sized a MediaStore-watching Android plugin. This file borrows the 1 to 2 week figure
    for other native plugins.
11. **Prescription lenses in a printed frame.** No source confirmed that a lens lab accepts a home-designed printed
    rim.
12. **Duty on 3D-printed nylon parts and on finished glasses from China**, and courier brokerage fees.
13. **Chip families not researched**: Ingenic, Novatek, Allwinner V85x and SigmaStar. These could hold a cheaper
    4K-class encoder.

### 5.2 What is weaker because two lanes are PARTIAL

**buy-adapt (PARTIAL; 15 searches, 22 pages).**

- Tier (c), white-label, rests on one factory page and one review.
- The Gen 2 battery figures and the RayNeo price are search summaries.
- Meta's developer terms were not read.
- Effect on this file: the closed-route verdict on white-label glasses (C33, C34) is thinner than the rest, but
  every lane reaches it independently. B's numbers come from vendor documents only, with no independent footage
  review.

**build-electronics (PARTIAL; about 50 calls).**

- No teardown or regulatory filing was read, so the Meta sensor, lens and heat limits are unsourced (C5).
- No power-while-recording measurement was found (C23).
- Several small-part prices are estimates.
- Effect on this file: C's battery life, its pixel ratio and about $60 of its BOM are estimates. The stage-3 gate
  therefore has to measure power, heat and px/deg rather than assume them.

### 5.3 Where the lanes disagree, and what this file used

| Topic | One lane says | The other says | This file used |
|---|---|---|---|
| Pixels-per-degree method | Diagonal pixels over diagonal FOV (buy-adapt; baseline 24 px/deg) | Centre focal length (build-electronics; baseline 17 px/deg) | The centre method, recomputing Mentra as 0.68x instead of 0.77x |
| Toolkit status | "1.0 is here — a stable, supported release" (Meta FAQ, page read) | README "developer preview"; "public preview" (UploadVR, snippet) | Stable 1.0, the newer statement. The recommendation does not depend on it |
| Mentra Live price | $449 (vendor page, read) | $299 launch price; $349 at one site (snippets) | $449 |
| Mentra Live FOV | 119 degrees (vendor) | 112 degrees (9to5Google, snippet) | 119 degrees |
| Mentra Live still camera | 8 MP, 3264x2448 (vendor) | 12 MP (press) | 8 MP |
| Gen 2 video modes | "3K at 30 fps, or 1080p at 60" (Meta guide) | "3K up to 60 fps" (Meta announcement); "1080p or 3K at 30" (a reviewer) | 3K at 30 fps for the far-end test |
| Bench tools | $75 (build-electronics) | $300 to $800 (manufacturing) | about $200 |
| Hired carrier-board design | $500 to $2,000 (build-electronics, unsourced) | $2,000 to $12,000 plus spins (manufacturing, from rates and a job post) | manufacturing's range |
| Step-1 demo parts | $60 to $100 (app-integration, from memory) | $155 for BOM 1 (build-electronics, priced) | $155 |
| Step-0 app effort | "1-2 days" (app-integration, prose) | 6 to 7 days (the same lane's item sizes) | the item sum |
| Duty on PCBs from China | 25 % (ourpcb blog) | 37.5 % (AtlasPCB blog) | 37.5 % |

## Status

**DONE.** Every section asked for is written, and the claims ledger holds 35 rows. No web searches were run. All
facts are carried from the lanes, and this file's own arithmetic is marked as such.
