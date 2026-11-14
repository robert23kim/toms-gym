# Verify: adversarial feasibility review of the three candidates

Written 2026-11-14 by the feasibility-review stage. Inputs: `REQUIREMENTS.md`, `candidates.md` and the lane files in
this folder, plus web pages read on 2026-11-14 (each fact below says whether the page itself was read or only a search
snippet). Status line at the end.

Abbreviations, spelled out once: px = pixels; px/deg = pixels per degree of view; f = focal length (in pixels unless
a unit is given); FOV = field of view; IMU = inertial measurement unit; HEVC = High Efficiency Video Coding (H.265);
FFC = flat flexible cable; MIPI CSI = the camera serial interface used by phone-class image sensors; eMMC = soldered
flash storage; Wh = watt-hours; mAh = milliamp-hours; BOM = bill of materials; PCB = printed circuit board; CAD =
computer-aided design; LTE = 4G cellular.

## 1. One yardstick: the ball's radius in pixels at the pins

The tracker's tightest need (REQUIREMENTS.md 3.1) is pixels on the far end. Everything below reduces to one number:
the ball's radius in pixels when it reaches the head pin.

Assumptions (stated, not measured):

- Ball radius 0.108 m (a regulation ball is about 8.5 in, 21.6 cm, across; from memory, unverified).
- Eye to head pin about 19 m: foul line to head pin is 60 ft (18.29 m, from memory, unverified), plus the bowler's
  eye a little behind and about 1.6 m above the foul line.
- Angular radius = 0.108 / 19 = 0.00568 rad = **0.326 degrees**. At the centre of the frame, radius in px = f x 0.00568.

| Camera | f at the centre (px) | How f was obtained | Ball radius at the pins | Ratio to baseline |
|---|---|---|---|---|
| Meta Gen 1 today (baseline) | 959 | candidates.md 2.0: (2285/2)/tan(50 deg), assuming a 100 deg diagonal lens (unsourced, claim C5) | 959 x 0.00568 = **5.4 px** | 1.00x |
| Mentra Live, default 1080p, 119 deg | 649 | (2203/2)/tan(59.5 deg), distortion-free | 649 x 0.00568 = **3.7 px** | 0.68x |
| Mentra Live, best case narrowed | 1,201 | still sensor 3264x2448, (4080/2)/tan(59.5 deg); a video crop cannot exceed sensor detail | 1,201 x 0.00568 = **6.8 px** | 1.25x (untested) |
| Meta Gen 2 at "3K" | about 1,440 | 959 x 1.5 (linear pixel gain from "about 6.4 million pixels per frame", snippet) | about **8.2 px** | about 1.5x |
| Candidate C: SC3336 sensor, 3.95 mm lens | 1,612 | 3.95 mm / 2.45 um pixel = 1,612 px (physical, independent of the FOV claim) | 1,612 x 0.00568 = **9.2 px** | 1.68x |

The SC3336 line is the one fact in this table that does not lean on a FOV figure. Its inputs:

- Lens 3.95 mm, F2.0, "98.3°" diagonal, "84°" horizontal, distortion "< 33%", sensor "1/2.8 inch", "2304 × 1296".
  Source: https://wiki.luckfox.com/SC3336-3MP-Camera/ (page read, 2026-11-14). The same lens figures and "$8.99" are on
  https://www.waveshare.com/product/luckfox/boards-modules/luckfox-pico-core1106/sc3336-3mp-camera-b.htm (page read).
- Pixel 2.45 um: **search snippet only** (a module vendor's spec table, https://www.sinoseen.com/sc3336-3mp-cmos-camera-module-low-light--wide-dynamic-range-sensor-compact-for-ai-vision-camera ).
  It is consistent with the optical format: 2304 x 2.45 um = 5.64 mm and 1296 x 2.45 um = 3.18 mm, a 6.48 mm
  diagonal, which is what "1/2.8 inch" means in practice.
- Cross-check against the vendor FOV: a distortion-free 3.95 mm lens on this sensor would see 2 x atan(2.82/3.95) =
  71 deg horizontally. The vendor says 84 deg, so the lens is barrel-distorted, as "< 33%" says. The centre f is still
  about 1,612 px; the edges get fewer px/deg.

**The attack on the 1.7x.** The 1.68x ratio is only as good as the baseline's f, which is the unsourced 100 degree
figure (C5). The measured radius range does not pin it down: today's clips show **4 to 13 px** at the pins
(REQUIREMENTS.md 3.1). Inverting that at 19 m gives a baseline f anywhere from 4 / 0.00568 = **704 px** to 13 / 0.00568
= **2,287 px**. Candidate C's 9.2 px sits *inside* today's measured range. If the true baseline f is near the top of
that span, C is no better than today; if it is near 959, C is 1.7x. Until a known far-end length is measured in an
existing clip (candidates.md stage 0(c), free), **no candidate's pixel claim is proven**, including the 1.5x of Gen 2.

**What C gives up for the pixels: view.** In portrait (the long axis vertical, as candidates.md proposes) the
across-lane view is the sensor's 1,296-px short axis. Distortion-free that is 2 x atan(648/1612) = 44 deg; with the
barrel distortion, about 48 to 52 deg (estimate). Meta's portrait frame across is 2 x atan(688/959) = **71 deg**. So C
trades about 20 to 25 deg of side-to-side view for its pixels. Gen 2 at 3K keeps the 71 deg and still gets about 1.5x.
That is the comparison C has to win, not the 1.0x baseline.

## 2. Candidate A: Meta glasses plus an app-side uploader

A is the baseline itself, so most of the attack is on its promises, not its hardware.

**Video.** Unchanged: 1376x1824 HEVC 10-bit, 30 fps, about 15 Mbps (REQUIREMENTS.md 2). Ball at the pins about 5.4 px
by the section 1 yardstick. The Gen 2 option: "3K Ultra HD" at about "6.4 million pixels per frame" and 30 fps
(search snippets, TechRadar / Android Central, listed in section 8). No source gave the exact 3K frame size, bitrate or file
size, and reviewers disagree on the modes ("1080p or 3K at 30 FPS"; another lists 1200p60 and 1440p30). The 1.5x
(about 8.2 px) is therefore a press-figure derivation. It must be ffprobed on a real 3K clip before anyone relies on it.
Price $379 "starting price" (TechRadar, snippet); Meta's own store was not read.

**Power and heat.** Meta's problem, and proven: the 2026-11-08 session ran 65 minutes with 32 clips. Nothing to attack.

**Weight and fit.** 48.6 to 50.8 g (Gen 1, vrarwiki, lane quote, page read by the lane); 52 g (Gen 2, snippet, lane
quote). This is the bar every other candidate is measured against.

**Transfer.** Two hops, and only the second is measured. Glasses to phone runs over Meta's own link; its time for
1 GB is unmeasured anywhere in the lanes. Phone to cloud: 1 GB is 8,000 megabits, so 8,000 / 5 = 1,600 s
(**27 min**) at a 5 Mbps cellular uplink and 8,000 / 20 = 400 s (**6.7 min**) at 20 Mbps. In an alley with no Wi-Fi it simply
waits for home Wi-Fi, which is acceptable because nothing on the lane depends on the upload. The weak point is the
uploader, not the link: a 1 GB batch from a browser page (A-web) on an iPhone stops when the page leaves the
foreground or the screen locks (from memory, unverified). The resumable client survives the stop but does not
continue in the background, so "a few minutes" in practice means "with the phone held awake on that page".

**Effort.** 6 to 7 full-time days is plausible for this owner: it is React, Flask and a migration, his home ground.
I would put it at 6 to 10 calendar weeks, not 6 to 7. The gallery picker for 32 clips, telling glasses clips from
phone clips, and the foreground-upload problem above are each a few evenings that the item list does not show. A-watch
(Android background watcher) is unsized; 5 to 10 more weeks is a borrowed figure.

**Hidden cost.** None beyond $379 for the Gen 2 option. Cellular data: 1.07 GB per session is inside any plan.

**Against the baseline.** A is the baseline. With a Gen 2 it beats the baseline on need 3.1 only (about 1.5x,
unverified) and arguably 3.5 (60 fps, at fewer pixels). It does nothing for 3.2, 3.3 or 3.4, and it fails the "without
opening another app" target in REQUIREMENTS.md 5 by design.

**Verdict: HOLDS WITH CHANGES.** Deciding number: **5.4 px at the pins for $0**, or about 8.2 px for $379, the
cheapest pixel gain of any candidate. Changes:

1. Before buying a Gen 2, get one real 3K clip (a store demo or a friend's pair) and ffprobe it; the 1.5x is a press figure.
2. Measure glasses-to-gallery time for a 30-clip batch; it is the unmeasured hop.
3. Design the A-web page to keep the screen awake and show resumable progress per clip, or accept that A-watch is required.
4. State plainly that A never meets "no other app"; it is the backend half of every other path, not the end state.

## 3. Candidate B: Mentra Live

**Video.** The vendor page (read 2026-11-14, https://mentraglass.com/live) says "HD 1080p videos", "119° field of
view, landscape orientation", "HD 3264 × 2448 images", "MTK8766 chipset". No codec, bitrate or frame rate is
published. Ball at the pins: f = (2203/2)/tan(59.5 deg) = 1101.5/1.698 = 649 px, so 649 x 0.00568 = **3.7 px**. That
is below the **4 px floor** of today's measured range, where far recall already struggles. Barrel distortion in a
119 degree lens would raise the centre f a little (the lanes' 0.77x diagonal figure gives about 4.2 px), which still
leaves it below the baseline's 5.4 px.

The narrowed view (`setCameraFov`, 62 to 118 degrees, from the SDK reference cited in candidates.md C15) cannot beat
the still sensor's own detail: f = 2040/tan(59.5 deg) = 1,201 px, **6.8 px** at best, 1.25x. At that f a 1920x1080
landscape frame sees 2 x atan(960/1201) = 77 deg across but only 2 x atan(540/1201) = **48 deg vertically**,
against Meta's portrait 2 x atan(912/959) = 87 deg. The approach and the follow-through pitch the head up and down,
so the lane leaving the top or bottom of the frame is the likely failure. Whether the crop applies to video at all
is unstated.

**Power and heat.** The vendor page says "260 mAh (glasses)" and "45 minutes video calling · 8+ hours normal use".
260 mAh x 3.7 V = 0.96 Wh. Video calling (camera, encoder and radio all running) drains it in 45 minutes, about 1.3 W.
The session needs 15 minutes of recording (about 0.32 Wh at that rate) plus uploading about 1 GB over Wi-Fi, which is
13 to 27 minutes of radio at 5 to 10 Mbps (another 0.3 to 0.6 Wh at video-call power), plus 2 hours of standby. That
is 0.6 to 0.9 Wh of the 0.96 Wh before standby is counted. It probably survives one session; it cannot record a whole
session continuously (65 min x 1.3 W = 1.4 Wh). The charging case (2,200 mAh) means a break mid-session to recharge.
Heat: about 1.3 W in a 43 g frame for 15 minutes in short bursts is what the vendor designed for; not attacked.

**Weight and fit.** 43 g (vendor page, read). Better than Meta. Not attacked.

**Transfer.** Wi-Fi only for bytes; same arithmetic as A (27 min at 5 Mbps, 6.7 min at 20 Mbps for 1 GB), but each
clip goes at stop time (33 MB average: 53 s at 5 Mbps). With no Wi-Fi in the alley it needs the phone's hotspot,
which works but drains the phone and the 260 mAh glasses together. Storage is not published, so "buffer the whole
session and upload at home" is unproven.

**Effort.** 14 to 20 weeks is plausible: a Capacitor plugin around a vendor Android SDK and a webhook receiver are
software tasks he can do. The stall risk is vendor SDK churn, not his skills.

**Hidden cost.** Low: $449, a US seller, no duty (company base from memory, unverified). Three units about $1,400.

**Against the baseline.** It beats "existing glasses plus the vendor's kit" on **no numbered need in section 3**.
It is worse on 3.1 (3.7 against 5.4 px), equal on 3.2 (manual exposure documented for photos only), 3.3 (no gyroscope
stream, C17) and 3.5, and possibly worse on 3.6 if narrowed. Its only win is integration (section 4 transfer and
section 5 pairing), which is not a camera need.

**Verdict: FAILS.** Deciding number: **3.7 px at the pins against 5.4 px today**. It loses on the
tightest constraint at its default setting and has no IMU. It is worth buying only as an integration test bed, and
then it is not a capture device.

## 4. Candidate C: custom Linux camera pod, then a printed frame, then a carrier board

C is the only candidate that answers the question asked, so it gets the hardest attack. The three stages earn
different verdicts and are judged separately.

### 4.1 Video: can the RV1106G3 and SC3336 match the baseline?

- **Encoder.** The official Luckfox Core1106 page (read, https://wiki.luckfox.com/Core1106/Introduction/) says only
  "Supports H264/H265 video encoder", with no resolution, frame rate or bit depth, and lists the RV1106G3 ISP at
  "Up to 8 MP @ 15 fps". The Pico Ultra page (read, https://wiki.luckfox.com/Luckfox-Pico-Ultra/) lists the ISP at
  "Max input 5M @30fps". The "3072×1728 (5M) @ 30fps H.265/H.264" encoder figure exists only in third-party coverage
  (CNX Software, search snippet; the page returned HTTP 403). The Rockchip datasheet PDF on LCSC returned an empty
  body. So the encoder ceiling is **lane quote, not re-verified against a Rockchip document**.
- **The sensor sets the real ceiling, not the encoder.** The SC3336 is 2304x1296 (page read) at a 30 fps maximum
  (GoPhotonics listing, snippet). The encoded frame is 2304x1296 = 2.99 megapixels against the baseline's
  1376x1824 = 2.51 megapixels, so **1.19x the pixel count**. The 1.68x at the pins comes from the narrower lens, not
  from more pixels (section 1).
- **Bitrate.** Pixel rate 2304 x 1296 x 30 = 89.6 megapixels/s against Meta's 75.3. Equal bits per pixel needs
  15.2 x 89.6 / 75.3 = **18 Mbps**. The encoder bitrate is set in software; no source gives the RV1106's maximum.
- **Bit depth and audio.** No page read mentions 10-bit video on the RV1106 (the only "10-bit" items on the Core1106
  page are the ADC and I2C addressing). Expect 8-bit HEVC against Meta's 10-bit, and a mono on-board microphone
  against stereo. Neither touches a numbered need directly; 8-bit costs some shadow detail at the dim pin deck.
- **Frame rate.** 30 fps, equal. No 60 fps at full frame (sensor maximum 30, snippet).
- **Focus.** Fixed-focus M12 lens, "manual focus" (page read). Hyperfocal distance with a 2-pixel blur circle:
  3.95^2 / (2.0 x 0.0049 mm) = 1,590 mm, so everything from about 0.8 m to infinity is sharp. The QR-code pairing in the plan
  only works with the phone held at **arm's length or more**; at 30 cm the code is blurred.

### 4.2 Power and heat

The plan's number is 220 mAh needed against a 500 mAh cell, from 0.28 W idle and an assumed 0.8 W while recording.
Both inputs are weak: the 0.28 W is a forum figure for the bare Core1106 module (lane quote; the forum returned
HTTP 403 to this stage), with no Wi-Fi association and no camera streaming, and no recording figure exists anywhere.

Session energy, with the boost converter at 85 % efficiency (assumed) and the 2-hour envelope of REQUIREMENTS.md 4:

| Case | Idle | Recording | Upload radio | At the cell | Against 1.9 Wh (500 mAh) |
|---|---|---|---|---|---|
| Plan | 0.28 W x 1.75 h = 0.49 Wh | 0.8 W x 0.25 h = 0.20 Wh | not counted | 0.69 / 0.85 = **0.81 Wh** | 2.3x margin |
| Stressed: Wi-Fi associated to the hotspot all session (2x idle), 1.5 W recording, 1.26 GB uploaded at 10 Mbps | 0.56 W x 1.75 h = 0.98 Wh | 1.5 W x 0.25 h = 0.38 Wh | +0.5 W x 1,008 s (0.28 h) = 0.14 Wh | 1.50 / 0.85 = **1.76 Wh** | 1.08x nominal; **negative** against about 1.7 Wh usable before the protection circuit cuts off (usable fraction from memory, unverified) |
| Camera pipeline kept warm so a press records instantly | 1.2 W x 2 h | (included) | 0.14 Wh | 2.54 / 0.85 = **3.0 Wh** | **0.63x: fails** |
| Whole-session recording (one of the four "custom-only" wins in the stage-3 gate) | - | 1.2 to 1.5 W x 2 h = 2.4 to 3.0 Wh | 0.14 Wh | **3.0 to 3.7 Wh** | **fails**; needs a 1,200 mAh cell (4.4 Wh nominal, about 4.0 Wh usable), about 20 to 25 g |

(1.26 GB is C's session at 18 Mbps: 554.6 s x 18.2 Mbps = 10,094 megabits.) The plan's 500 mAh cell holds only for
cold-started, button-per-throw recording with the radio off between uploads. Boot time on the stock Buildroot image
is unmeasured, so whether a cold start per throw is acceptable is unknown.

**Heat.** Surface temperature rise ≈ P / (h x A), with h ≈ 10 W/m^2/K for still air plus radiation (textbook order of
magnitude, from memory, unverified), ambient 22 °C (assumed):

| Where the heat is | Pod | Area | 1.0 W | 1.5 W |
|---|---|---|---|---|
| Pico Ultra W (50 x 50 mm) in a strap pack behind the head | 55 x 55 x 15 mm | 2 x 55 x 55 + 4 x 55 x 15 = 9,350 mm^2 | +11 K, about 33 °C | +16 K, about 38 °C; about 42 °C with the skin-side face insulated |
| Core1106 module (30 x 30 mm) in a temple-arm pod (stage C3) | 35 x 35 x 10 mm | 2 x 1,225 + 4 x 350 = 3,850 mm^2 | +26 K, about **48 °C** | +39 K, about **61 °C** |
| Camera alone on the temple (stage C1) | sensor only, about 0.1 to 0.2 W (from memory, unverified) | - | a few K | - |

The 1.0 and 1.5 W columns are steady state, which applies only to the warm-pipeline and whole-session cases. In
button-per-throw use the pod averages its bursts (a 17 s clip is short against a small pod's thermal time constant of
minutes, an assumption), so the session-average power from the table above is what counts:

| Case, Core1106 module in the 3,850 mm^2 temple-arm pod | Session-average power | Rise | Surface |
|---|---|---|---|
| Plan (0.69 Wh over 2 h, cell and boost on the other arm) | about 0.35 W | +9 K | about **31 °C** |
| Stressed (1.50 Wh over 2 h) | about 0.75 W | +19 K | about **41 °C**, at the limit |
| Warm pipeline or whole-session recording | 1.2 to 1.5 W | +31 to +39 K | about **53 to 61 °C**, fails |

These are averages; the processor's own patch is hotter. The roadmap's gate of "under 48 degrees C after 15 minutes"
is a short-contact figure, but the device is worn for 2 hours. Prolonged-contact limits for plastic in the
IEC 62368-1 family are around 43 °C (from memory, unverified; the search found the table's structure, "tabulated by
material ... and contact duration", but not its values). **A strap pack behind the head is safe in every case.
Electronics in a temple arm are safe only for cold-start, button-per-throw recording; any mode that keeps about 1 W
or more running (warm pipeline, whole-session recording) is not.** The same logic is why Mentra's about 1.3 W in
short bursts inside a frame is not attacked in section 3. Commercial glasses that do put the processor in the arm limit how long one clip
can record (from memory, unverified; heat as the reason is an inference).

**Lithium cell beside the head.** The Adafruit 500 mAh pouch cell has protection against over-charge and over-discharge
(lane quote of the product page: "keeps the battery voltage from going too high (over-charging) or low (over-use)").
Nothing in that quote covers puncture, crushing or over-temperature. Rules for a prototype: rigid printed enclosure
around the pouch (no strap buckle or edge pressing on it), never charge on the head, an inline fuse or PTC on the
battery lead, cell and processor on opposite sides of the pack, and a charger with a temperature input if the cell has
a thermistor (not confirmed for this cell). Behind the head the cell is about 10 cm from the scalp through the pack
wall; that is acceptable for a prototype, a temple-arm cell beside the temple is not without proper cell protection.

### 4.3 Weight and fit

- **Board.** Pico Ultra is "50 x 50mm" (Liliputing, page read). A temple arm is about 5 to 7 mm thick and 10 to 15 mm tall
  (from memory, unverified). **The "pods on both arms" option in the plan does not fit:** a 50 mm square hung on a
  temple arm sticks 35 to 40 mm below it. Only the strap pack is buildable at stage C1 and C2.
- **Camera.** Waveshare lists the camera at "0.012 kg" (page read), likely the shipping weight with the cable. The
  lane's "camera about 2 g" is unsourced; plan on 5 to 12 g.
- **Totals (estimates; only the cell's 10.5 g and the camera listing are sourced).** On the face: his own frame
  (about 25 g, assumed) + camera 5 to 12 g + IMU board 2 g + temple pod 5 g = **37 to 44 g**. Behind the head: board
  15 to 20 g + cell 10.5 g (or 20 to 25 g for the bigger cell the power table demands) + charger and boost 5 g + pack
  shell 10 g + strap 10 g = **50 to 70 g**. All on the head: **about 90 to 115 g** against Meta's 49 to 52 g. The face
  weight is fine; the strap is a gadget, which is acceptable for a prototype.
- **The camera cable.** The plan runs the camera's ribbon about 30 cm from the temple to the back of the head. The
  camera ships "with FFC cable" (page read), length and pin count not stated. Electrically a 2-lane link at about
  0.45 Gbps per lane (2304 x 1296 x 30 x 10 bits / 2, before blanking) usually survives 30 cm of FFC (from memory,
  unverified). Mechanically it is the real risk: a flat flexible cable bending at the neck every time the head turns
  will crack long before 2-hour sessions add up. This is the "flexible circuit across a hinge" problem moved to the
  neck. Strain relief at both ends and five spare cables are mandatory.

### 4.4 Transfer

- The radio is "2.4GHz WiFi6" only (Luckfox Pico Ultra page, read). Over a phone hotspot the cellular uplink, not the
  2.4 GHz link, is the bottleneck.
- 1.26 GB (C's session at 18 Mbps) = 10,094 megabits: **84 min at 2 Mbps, 34 min at 5, 17 min at 10, 8.4 min at 20.**
  Per clip (about 39 MB at 18 Mbps for a 17.3 s mean clip): 63 s at 5 Mbps. Fine between throws.
- **Break point:** the session produces bytes at an average of 10,094 megabits / 3,883 s = **2.6 Mbps**. Below that
  uplink the backlog grows all session. A large steel-roofed building can push indoor LTE uplink under that (from memory,
  unverified); nobody has measured his alley (candidates.md gap 9).
- **No signal at all:** the 8 GB eMMC holds about 6 button-per-throw sessions at 1.26 GB, and uploads at home. It
  does **not** hold a 65-minute continuous recording at 18 Mbps (65 x 60 x 18 / 8 = 8.8 GB). Whole-session recording
  needs a microSD card or a lower bitrate.
- Hotspot allowances run from 15 GB to 250 GB of high-speed tethering a month on the big US carriers (affiliate-blog
  snippets that conflict). Button-per-throw (about 5 GB a month at four sessions) fits; continuous recording (about
  35 GB a month) breaks the smaller tiers.

### 4.5 Effort: is 21 to 27 weeks honest?

No; it is optimistic by about 1.4x. The plan counts 8 productive hours a week and two to four prints. The steps most
likely to stall, in order:

1. **The build host.** The Luckfox SDK is a Buildroot tree that expects an x86-64 Ubuntu host (from memory,
   unverified). His machine is a Mac. A Linux virtual machine or a cloud build box, and learning Buildroot's
   rebuild cycle, is 1 to 3 weeks of evenings before any of his own code runs.
2. **The recorder in C on Rockchip's media library** (camera input, encoder, MP4 muxing, rotation tag) plus manual
   exposure through Rockchip's ISP library. The camera *driver* is low risk: the SC3336 is the default camera for these
   boards (Waveshare search snippet). The pipeline and exposure control are the 10 to 15 weeks the plan names, and
   that estimate assumes the vendor examples cover recording to a file.
3. **IMU timestamps.** Reading a motion sensor at 200 to 800 Hz from Linux user space on a single Cortex-A7 core while
   it encodes and uploads gives millisecond jitter. It needs the sensor's own buffer with timestamps and a clock
   alignment against the frame timestamps. 2 to 4 weeks, not in the plan.
4. **Power and brownouts.** A boost converter from a pouch cell sagging under Wi-Fi transmit bursts resets boards. 1 to
   2 weeks of debugging with a meter.
5. **The pod in CAD.** A first-time CAD user needs 8 to 15 prints, not 2 to 4. At 3 to 5 working days plus shipping
   per print from a service, that is months; a $200 to $300 home printer makes it weekends (from memory, unverified).

My estimate: **30 to 40 calendar weeks** to a first working pod from scratch, or 22 to 30 if A is already built.
Stage C2 adds the plan's 8 to 16 weeks; stage C3 adds 16 to 32 weeks and two to three board spins at 3 to 5 weeks
each (fabrication, shipping from China and customs).

### 4.6 Hidden cost: re-total to the first working pod

| Item | Plan | This review | Basis |
|---|---|---|---|
| C1 parts | $150 to $200 | $150 to $200 | candidates.md BOM |
| Bench tools: iron, multimeter, USB-C power meter, flux, wire, USB-serial adapter, an IR thermometer for the heat gate | about $200 | $125 to $200 | from memory, unverified |
| Spares: a second board (first-timers kill one), three cameras and cables | $20 | $70 to $110 | board $36.99 to $81.99 range (page read), camera $8.99 (page read) |
| Pod prints: 8 to 15 iterations, or a home printer | $40 | $150 to $300 | from memory, unverified |
| Linux build host | $0 | $0 to $180 | a spare PC, or a cloud VM for about 6 months (unsourced) |
| Shipping and duty: 2 to 3 orders from China at 37.5 % duty, plus courier brokerage | $40 | $100 to $190 | duty rate is the lane's; the $800 exemption "suspension is effective as of June 24, 2026" (Thompson Hine, page read) |
| Bigger cell for the power table | - | $10 to $15 | unsourced |
| Wrong purchase | $50 | included above | |
| **Total to first working pod** | **$500 to $700** | **about $600 to $1,200** | |

Three units in a printed frame: about **$1,300 to $2,200**. With a self-designed carrier board: the plan's
$1,500 to $3,300, plus the heat result below that makes it unwearable. "Under $1,000" holds only if it means the whole
effort to one pod, and only at the low end.

### 4.7 Against the baseline

| Need | C1 against Meta Gen 1 | C1 against a Gen 2 at 3K ($379, no engineering) |
|---|---|---|
| 3.1 far-end pixels | 9.2 against 5.4 px (1.68x), if the 100 degree assumption holds | 9.2 against about 8.2 px (**1.12x**), with a 20 to 25 degree narrower view |
| 3.2 release blur | Probably better: 2.45 um pixels gather more light, so a shorter exposure is possible, and Rockchip's ISP exposes manual exposure (from memory, unverified) | same |
| 3.3 camera motion | **Better**: an IMU log, the one thing no bought device gives | same |
| 3.4 events | **Better**: IMU impulse at release; mono microphone | same |
| 3.5 frame rate | Equal (30 fps) | Equal or worse (Gen 2 claims 60 fps at lower resolution) |
| 3.6 view | **Worse**: about 48 to 52 deg across against 71 deg; unproven safe | same |

C1 beats the baseline on 3.3 and 3.4 for certain, on 3.2 probably, and on 3.1 only by 1.12x once a $379 Gen 2 is the
comparison. **The case for C is the IMU and exposure, not the pixels.**

### 4.8 Verdicts for C

- **C-pod (stage C1): HOLDS WITH CHANGES.** Deciding number: **9.2 px at the pins against 5.4 px (and 8.2 px for a
  Gen 2)**, unproven until the baseline f is measured. Changes:
  1. Measure the baseline f (stage 0(c)) and run the experiment in section 6 before any pod work.
  2. Judge C against the Gen 2 bar (about 8.2 px), not against 5.4 px; sell it on the IMU log and exposure.
  3. Strap pack only; drop the "pods on both arms" option (a 50 x 50 mm board does not fit a temple arm).
  4. Size the cell for the stressed or warm-pipeline case: 1,200 mAh on the strap, or prove cold start per
     throw is acceptable.
  5. Heat gate at 43 °C for 2-hour contact, measured with a thermometer, not 48 °C at 15 minutes.
  6. Strain relief and spare cables for the neck-crossing camera ribbon; a microSD card if whole-session recording
     is wanted.
  7. Re-plan at 30 to 40 weeks and $600 to $1,200 to the first pod; budget a Linux build host.
- **C-frame (stage C2): HOLDS WITH CHANGES.** Deciding number: **90 to 115 g on the head against Meta's 49 to 52 g.**
  The electronics cannot move into the frame at this stage (the board is 50 x 50 mm), so the plan's gate of "2 hours
  worn at or under about 55 g" can only be met by counting the face weight (37 to 44 g) and accepting the strap pack.
  Restate the gate that way, or this stage fails its own test.
- **C-board (stage C3): FAILS.** Deciding number: **$1,500 to $3,300 for three units (1.5x to 3.3x the budget) and
  54 to 88 calendar weeks from scratch** (C1 30 to 40, C2 8 to 16, C3 16 to 32), or $2,500 to $13,000 more if the board
  is hired. Heat does not kill it on its own: in button-per-throw use the temple-arm pod averages about 31 °C (plan)
  to 41 °C (stressed). But heat and the on-face cell confine it to that one mode: the warm-pipeline and whole-session
  modes run at 53 to 61 °C in a temple arm, so C3 gives up one of the four "custom-only" wins the stage-3 gate counts.
  It only pays where the electronics leave the strap pack, and that is exactly where the budget, the calendar and the
  first-timer's 2 to 3 board spins all break.

## 5. Verdicts at a glance

| Candidate | Verdict | The number that decides it |
|---|---|---|
| A. Meta glasses + app uploader | HOLDS WITH CHANGES | 5.4 px at the pins for $0; about 8.2 px with a $379 Gen 2 (press figure, not ffprobed) |
| B. Mentra Live | FAILS | 3.7 px at the pins at its default view, against 5.4 px today and a 4 px measured floor |
| C-pod (stage C1) | HOLDS WITH CHANGES | 9.2 px at the pins (1.68x Gen 1, 1.12x Gen 2), unproven until the baseline focal length is measured |
| C-frame (stage C2) | HOLDS WITH CHANGES | 90 to 115 g on the head against 49 to 52 g; passes only if the gate counts face weight (37 to 44 g) |
| C-board (stage C3) | FAILS | $1,500 to $3,300 for three units and 54 to 88 calendar weeks from scratch; heat (53 to 61 °C in a temple arm) also rules out its warm-pipeline and whole-session modes |

Cross-cutting findings the candidates file understated:

1. **Every pixel ratio is unproven.** The measured 4 to 13 px at the pins allows a baseline focal length anywhere
   from 704 to 2,287 px. C's 9.2 px sits inside today's range.
2. **Against a $379 Gen 2, C's pixel gain is about 1.12x.** C's real value is the IMU log and exposure control.
3. **C's battery holds only for cold-start, button-per-throw use.** Warm pipeline or whole-session recording needs
   about 1,200 mAh, and in a temple arm those modes also run at 53 to 61 °C.
4. **C's money and time are about 1.4x the plan's estimate:** $600 to $1,200 and 30 to 40 weeks to the first pod.

## 6. The single experiment that removes the most risk (under $150, two weekends)

**Side-by-side far-end shoot-out: a bare Luckfox board and SC3336 camera on a cap brim, next to the Meta glasses,
on the same throws.**

What it settles at once: whether C's 1.68x is real (both cameras measured on the same target at the same distance),
whether more far-end pixels raise tracker recall (candidates.md gap 7), whether the narrower view keeps the pin deck
in frame (gap 2), and the recording power and heat (gap 4), which decide the battery and the C3 verdict.

| Item | Cost | Basis |
|---|---|---|
| Luckfox Pico Ultra, the cheapest variant with eMMC (Wi-Fi not needed for this test) | about $37 to $45 | range "$36.99 - $81.99" (Waveshare, page read); per-variant price not shown |
| SC3336 3MP Camera (B) | $8.99 | Waveshare, page read |
| USB-C inline power meter | about $15 | lane estimate |
| Infrared thermometer | about $15 | from memory, unverified |
| Shipping from Waveshare | about $15 to $25 | unsourced |
| Duty at 37.5 % on about $50 of boards | about $19 | lane's planning rate; no de minimis since 24 June 2026 |
| Cap, zip ties, tape; laptop, USB cable and backpack (owned) | about $5 | assumed owned |
| **Total** | **about $115 to $135** | |

Weekend 1 (bench):

1. Use the stock image; **no SDK build**. It "will automatically run the rkipc demo, and the motherboard will be set
   as a streaming server after booting up", at `rtsp://172.32.0.93/live/0` over USB (Waveshare camera wiki,
   snippet). Set the main stream to 2304x1296, 30 fps, about 18 Mbps in the demo's config file on the board (that
   these are editable without a rebuild is from memory, unverified), and save it on a laptop with
   `ffmpeg -rtsp_transport tcp -i rtsp://172.32.0.93/live/0 -c copy out.mkv`. At the lane the laptop rides in a
   backpack on the USB cable, which also powers the board. **This is the step that can break the two-weekend
   limit:** if the stock stream cannot be set to full resolution or drops frames, the fallback is the SDK build
   (1 to 3 weeks, section 4.5), and the experiment becomes a month.
2. Focal-length test: tape a 1.00 m stick at exactly 10.0 m. Record it with both the Meta glasses and the Luckfox
   camera from the same spot, stick at frame centre. Then f = (stick length in px) x 10.0 / 1.00. This replaces the
   unsourced 100 degree assumption for every candidate.
3. Read recording power on the meter for 15 minutes, idle power with the camera streaming and with it stopped, and
   the boot time. Read the board's hottest point with the thermometer at 15 minutes.

Weekend 2 (lane): one session with both cameras recording every throw.

4. On the same throws, measure the ball radius in px at the pin-row crossing in both cameras.
5. Count throws where the pin deck leaves the Luckfox's narrower frame.
6. Run the research tracker's far-end stage on both sets, with the count frozen before any rule change (per `RULES.md`).
7. Run a phone speed test on the lane for the hotspot uplink.

**Pass, and build C1:** the Luckfox ball radius at the pins is at least 1.5x Meta's on the same throws; the pin deck
stays in frame on at least 95 % of throws; and far recall is at least equal. **Fail:** stop before any pod, and spend
$379 on a Gen 2 for pixels. Build hardware only if the IMU log alone is worth 30 to 40 weeks of evenings.

## 7. Unsourced (stated, not proven)

- Ball radius 0.108 m and foul line to head pin 18.29 m, with the eye about 19 m from the head pin.
- The Meta Gen 1 lens at about 100 degrees diagonal (C5, carried from the lanes): the baseline's f = 959 px.
- The RV1106 encoder at 3072x1728 at 30 fps: third-party only; no Rockchip document read. 8-bit-only HEVC is an
  inference from silence.
- RV1106 recording power (the 0.8 W, 1.2 W and 1.5 W cases are assumptions), the 2x idle with Wi-Fi associated,
  85 % boost efficiency, about 90 % usable cell energy, and boot time.
- The heat coefficient h ≈ 10 W/m^2/K and 22 °C ambient; the 43 °C prolonged-contact limit; that Meta limits clip
  length for heat.
- Temple-arm dimensions (5 to 7 mm by 10 to 15 mm), his frame's 25 g, board weight 15 to 20 g, camera 5 to 12 g.
- That 30 cm of camera ribbon cable works electrically, and how many bends the cable survives.
- The Luckfox SDK's x86-64 Ubuntu host requirement; vendor file-recording examples; manual exposure in Rockchip's ISP
  library.
- That indoor LTE uplink in a steel-roofed building can fall below 2.6 Mbps; that an iPhone browser stops uploading
  when the page leaves the foreground.
- Prices for bench tools, a home printer, spare parts, shipping, brokerage, a cloud build host, the IR thermometer
  and the power meter.
- Mentra Live's "always-on white privacy light" (in candidates.md): not on the vendor page this stage read.
- Mentra Live ships from a US company, so pays no duty.

## 8. Sources (all accessed 2026-11-14)

| URL | Read or snippet | Quote that supports the claim |
|---|---|---|
| https://wiki.luckfox.com/SC3336-3MP-Camera/ | page read | "1/2.8 inch"; "2304 × 1296"; "3.95 mm"; "F2.0"; "98.3°"; "84°"; "< 33%"; compatible with "Luckfox Pico Ultra / Ultra B / Ultra W / Ultra BW" |
| https://www.waveshare.com/product/luckfox/boards-modules/luckfox-pico-core1106/sc3336-3mp-camera-b.htm | page read | "$8.99"; "Onboard 98.3° wide angle lens"; "manual focus"; "rolling shutter"; "(with FFC cable) x1"; weight "0.012 kg" |
| https://www.sinoseen.com/sc3336-3mp-cmos-camera-module-low-light--wide-dynamic-range-sensor-compact-for-ai-vision-camera | snippet only | pixel size 2.45 µm with 2304 × 1296 |
| https://www.gophotonics.com/products/cmos-image-sensors/smartsens-technology/21-1025-sc3336 | snippet only | 30 fps maximum frame rate |
| https://www.waveshare.com/Luckfox-Pico-Ultra.htm | page read | "$36.99 - $81.99"; "supports 5-Megapixel"; "Onboard 2.4GHz WiFi 6 and Bluetooth 5.2/BLE"; "8GB EMMC"; "external 5V power supply"; no encoder resolution stated |
| https://wiki.luckfox.com/Luckfox-Pico-Ultra/ | page read | ISP "Max input 5M @30fps"; "2.4GHz WiFi6 Bluetooth 5.2/BLE"; "256MB DDR3L"; "eMMC(8GB)"; "MIPI CSI 2-lane" |
| https://wiki.luckfox.com/Core1106/Introduction/ | page read | "Supports H264/H265 video encoder" (no resolution); RV1106G3 ISP "Up to 8 MP @ 15 fps"; "30 mm × 30 mm"; "-20~60 ℃" |
| https://liliputing.com/luckfox-pico-ultra-is-a-micro-dev-board-with-poe-and-a-rockchip-rv1106-arm-risc-v-chip/ | page read | the board "measures just 50 x 50mm (2″ x 2″)"; 2024 prices from $18 |
| https://www.cnx-software.com/2024/06/21/luckfox-pico-ultra-micro-development-board-features-mipi-csi-wifi-6-ethernet-poe-gpio-headers/ | snippet only (page returned HTTP 403) | "3072×1728 (5M) @ 30fps H.265/H.264 encoding"; "50 x 50 mm" |
| https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2405141706_Rockchip-RV1106G3_C5328706.pdf | fetch returned an empty body | nothing read |
| https://forums.luckfox.com/viewtopic.php?t=1822 | not re-read (HTTP 403); lane quote | about 0.28 W for the Core1106 module, "the 0.11W are consumed only from RV1106" |
| https://www.waveshare.com/luckfox-pico-pro.htm?sku=25719 | snippet only | Pico Max "$14.99"; RV1106G3; default camera SC3336 |
| https://mentraglass.com/live | page read | "$449"; "Ships in 2–5 business days"; "HD 1080p videos"; "119° field of view, landscape orientation"; "HD 3264 × 2448 images"; "Weight: 43 grams"; "260 mAh (glasses)"; "2,200 mAh (case)"; "45 minutes video calling · 8+ hours normal use"; "MTK8766 chipset" |
| https://www.techradar.com/computing/virtual-reality-augmented-reality/meta-ray-ban-gen-2-smart-glasses-are-official-here-are-5-key-upgrades-you-need-to-know-about | snippet only | starting price "$379"; 3K video |
| https://androidcentral.com/wearables/ray-ban-meta-gen-2 | snippet only | "1080p or 3K at 30 FPS"; 1200p at 60 fps promised but "still hasn't arrived as of late October" |
| https://www.thompsonhinesmartrade.com/2026/06/cbp-issues-interim-final-rules-indefinitely-suspending-the-de-minimis-exemption-for-imports/ | page read | "This suspension is effective as of June 24, 2026"; postal "delayed compliance date ... of October 22, 2026"; "statutorily eliminated effective July 1, 2027" |
| https://japan.ul.com/wp-content/uploads/sites/27/2014/06/1_techbrief_touchtemp.pdf | snippet only | TS1 limits tabulated by material and contact duration; based on ISO 13732-1 (values not shown) |
| https://www.waveshare.com/wiki/ISG1321_Camera and https://wiki.luckfox.com/Luckfox-Pico-Pi/CSI-Camera/ | snippets only | "the default image on the board will automatically run the rkipc demo, and the motherboard will be set as a streaming server after booting up"; `rtsp://172.32.0.93/live/0`; nothing on saving to a file on the board |
| Hotspot allowances | search summary, pages not identified (results included usmobile.com, tomsguide.com, androidauthority.com plan guides) | high-speed hotspot allowances from 15 GB to 250 GB a month on the big US carriers |
| Lane files in this folder (vrarwiki weights, Adafruit cell, Meta toolkit limits) | lane quotes, not re-read | as quoted inline |

## Status

**DONE.** All three candidates were attacked on all seven axes, with verdicts split by stage for C, and the
experiment is costed. About 45 tool calls. Weak points: the Rockchip encoder ceiling and every power figure rest on
third-party or lane quotes (two primary pages returned HTTP 403 and the datasheet PDF came back empty), and the
skin-temperature limit is unsourced.
