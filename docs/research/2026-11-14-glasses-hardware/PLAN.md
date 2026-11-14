# Plan: your own camera glasses for t30g (prototype)

Written 2026-11-14 for the owner, from [REQUIREMENTS.md](REQUIREMENTS.md), [candidates.md](candidates.md) and the two
checker files ([verify-sources.md](verify-sources.md), [verify-feasibility.md](verify-feasibility.md)). No new web
research. "(unverified)" beside a number means no checker could confirm it. px = pixels; IMU = inertial measurement
unit, a gyroscope and accelerometer chip that logs head motion; Gen 1 / Gen 2 = the first and second Ray-Ban Meta
models.

**Correction, 2026-11-14 (lead session, after the workflow):** the "4 to 13 px" figure is the ball's radius over the
far part of the lane, not a measurement at the pin row. The requirements file handed to the agents said "at the
pins"; this file and REQUIREMENTS.md are fixed, while candidates.md and the two verify files still carry the old
wording. No cost or recommendation depends on it. If the 4 px end of that range is the pin row, today's camera is
below the 5.4 px estimate used here, which stage 0(c) settles.

## 1. The answer in five lines

1. **First, spend nothing for two weeks:** in your existing clips, measure one known far-end length to learn the
   Meta camera's real pixels at the pins, check which Meta model you own, and speed-test your phone's hotspot at the
   alley. Every pixel ratio in this plan rests on an unmeasured guess about the Meta lens.
2. **Then build the app half (no hardware, $0, 6 to 10 weeks of evenings) and, in parallel, a $125 to $145
   "shoot-out":** a bare camera board on a cap brim next to your Meta glasses on the same throws (two weekends).
3. **Only if the shoot-out passes, build one custom pod:** about $160 to $215 in parts per unit, **$600 to $1,200
   total to the first working unit** (the shoot-out's parts are the first part of that total), **30 to 40 calendar
   weeks** at 8 hours a week (22 to 30 if the app half is done). Three units in a printed frame: $1,300 to $2,200.
4. **It will prove:** that clips go from your head straight into your t30g account with phone-only setup, and whether
   a camera you chose beats Meta's at the pins (about 9.2 px against 5.4 px today, both unverified), with a
   head-motion log no bought glasses give. **It will not prove:** a glasses-shaped product (the electronics ride in a
   pack behind your head), a ball line inside the app, or anything about building more than five.
5. **What the checkers changed:** the first step (free checks, then the app half) is unchanged; after it, two options
   were dropped (Mentra Live glasses, and your own circuit board), a cheap shoot-out gate was added before any pod, and
   the pod was re-costed upward by about 1.4x in money and time.

## 2. The options compared

"Ball at the pins" is the ball's radius in pixels at the head pin, at the centre of the frame. Today's clips measure
4 to 13 px over the far part of the lane (the tracking notes' "far ball" range, not the pin row alone), and the
tracker's weakest stage is the pin-row crossing. Every figure in that column assumes the
Gen 1 lens covers about 100 degrees diagonally (claim C5, unverified), so all of them are unverified until stage 0.

| Option | Per-unit cost | Total to first working unit | Calendar weeks | Ball at the pins vs Meta today (all unverified, C5) | How clips reach the app | Feasibility verdict |
|---|---|---|---|---|---|---|
| A. Your Meta glasses + an upload page in t30g | $0 | $0 | 6 to 10 | 5.4 px, the baseline | Glasses -> Meta's phone app -> phone gallery -> you pick clips on a t30g page | HOLDS WITH CHANGES |
| A + a Gen 2 pair recording "3K" | $379 clear lenses; $409 to $459 tinted | same | +2 to 3 | about 8.2 px, 1.5x (press figure, not measured on a file) | as A | HOLDS WITH CHANGES (measure one 3K clip before buying) |
| B. Mentra Live (open camera glasses) | $449 | about $480 | 14 to 20 | **3.7 px, 0.68x**; at best 6.8 px if its view-narrowing works on video (undocumented) | Glasses post each clip to a web address over Wi-Fi | **FAILS: dropped** as a capture device |
| Shoot-out (an experiment, not a device; its board and camera carry into C-pod) | - | $125 to $145 | 2 weekends; about a month if the board's software must be rebuilt | measures both cameras on the same throws | laptop in a backpack | proposed by the feasibility check |
| C-pod: camera on your glasses, board and battery in a pack behind your head | $160 to $215 | $600 to $1,200 | 30 to 40 (22 to 30 after A) | about 9.2 px: 1.68x Gen 1, only **1.12x a Gen 2**; view 44 degrees across against Meta's 71 | Device uploads each clip itself over the phone's hotspot | HOLDS WITH CHANGES |
| C-frame: three units in a 3D-printed nylon frame | about $430 to $730 (total for three divided by three) | $1,300 to $2,200 for three | +8 to 16 | as C-pod | as C-pod | HOLDS WITH CHANGES (judge the 37 to 44 g on the face, not the 90 to 115 g total) |
| C-board: your own circuit board, so the electronics fit a temple arm | $115 to $145 in parts | $1,500 to $3,300 for three | 54 to 88 from scratch | as C-pod | as C-pod | **FAILS: dropped** from this plan |

The honest framing: against a $379 Gen 2, the custom pod's pixel gain is small (1.12x, unverified). **The case for
building is the head-motion log, manual exposure against release blur, and upload with no other app**, not pixels.

## 3. The recommended path, in stages

Step-by-step detail: [candidates.md](candidates.md) section 3 (stage 0), [verify-feasibility.md](verify-feasibility.md)
section 6 (shoot-out), [lane-app-integration.md](lane-app-integration.md) sections 5.3 and 5.4 (app work and demo).

### Stage 0. Free checks ($0, nothing to buy, 1 to 2 weeks)

(a) Look for a video-resolution setting in the Meta AI app (if present you own a Gen 2 and 3K is a setting).
(b) Record a clip without opening the Meta app; does it reach the gallery (C4)? (c) In one existing clip, measure the
pixel width of something of known size at the pin deck and compute the focal length in pixels (the lens's zoom, in
pixels). (d) Measure how far the pin deck wanders from the frame centre across the 32 clips of 2026-11-08; that sets
the narrowest safe view. (e) Speed-test the hotspot on the lane. Skills: yours. **Done:** a measured focal length
replacing the 959 px guess, and a measured uplink. **Gate:** always continue; if (c) shows today's camera already
gives about 9 px at the pins (the custom camera's estimate), the pixel case for a custom camera is gone.

### Stage 1. App half ($0, nothing to buy, 6 to 10 weeks), alongside stage 2

Build B1, B2, B5, B6, F1, F2, F4 (section 4): sessions, a "Session upload" page that sends clips with compression off
(a mean clip is 33.4 MB, above the app's 24 MiB compression threshold), and an export to the tracker's folders. Keep
the screen awake and show per-clip progress (an iPhone browser likely stops uploading in the background,
unverified). Skills: yours. **Done:** the 32 clips of one session are listed in capture order, play on the phone, and
match the source size and SHA-256 hash. **Gate:** none; this is the backend every later device uses.

### Stage 2. Shoot-out ($125 to $145, 2 weekends)

The Luckfox Pico Ultra W is a 50 x 50 mm Linux computer on a Rockchip RV1106 chip with a hardware video encoder (the
part that compresses video to HEVC, also called H.265). The SC3336 is a 3-megapixel camera with a fixed-focus lens.

| Part | Vendor | Price | URL |
|---|---|---|---|
| Luckfox Pico Ultra W (Wi-Fi 6 2.4 GHz, Bluetooth 5.2, 8 GB eMMC soldered flash) | Waveshare / Luckfox | about $45 to $51 (unverified; family range $36.99 to $81.99) | https://www.waveshare.com/Luckfox-Pico-Ultra.htm |
| SC3336 3 MP camera (B), with ribbon cable | Waveshare | $8.99 | https://www.waveshare.com/product/luckfox/boards-modules/luckfox-pico-core1106/sc3336-3mp-camera-b.htm |
| USB-C inline power meter about $15; infrared thermometer about $15 | any | about $30 (unverified) | no URL in the lanes |
| Shipping, and about 37.5 % duty (no low-value exemption since 24 June 2026; rate not checked for a finished development board) | - | about $40 to $55 | - |

Weekend 1 (bench): stock image, no software build; set the stream to 2304x1296, 30 fps, about 18 Mbps and save it on
a laptop with `ffmpeg`. Record a 1.00 m stick at 10.0 m with both cameras; focal length = stick pixels x 10. Test
**sustained 30 fps at full size** (the one report is about 23 fps, C19) and **manual exposure on video** (C26). Read
recording and idle power, boot time, and the hottest point at 15 minutes. If the stock stream cannot be reconfigured,
the board's software must be rebuilt on a Linux machine (1 to 3 weeks) and this stage becomes a month.
Weekend 2 (lane): both cameras on every throw; ball radius at the pin-row crossing in each, throws where the pin deck
leaves the Luckfox frame, the tracker's far-end stage on both (count frozen before any rule change), hotspot speed.
**Done and gate:** pass if the Luckfox radius is at least 1.5x Meta's on the same throws, the pin deck stays in frame
on at least 95 % of throws, far recall is at least equal, and 30 fps holds. **Fail:** stop; buy a Gen 2 for pixels.

### Stage 3. C-pod, one wearable unit ($600 to $1,200 including stage 2; 22 to 30 more weeks)

The camera clips to your glasses; board, cell and charger ride in a printed pack behind your head, joined by the
camera's flat flexible cable (FFC, a thin ribbon). Required by the feasibility check: strap pack only (a 50 mm board
does not fit a temple arm); a 1,200 mAh cell unless stage 2's boot time proves a cold start per throw is acceptable;
strain relief and five spare cables at the neck; a 43 °C two-hour heat gate.

| Part | Vendor | Price | URL |
|---|---|---|---|
| Board and camera | - | bought in stage 2 | - |
| LSM6DSOX motion sensor (IMU) board | Adafruit | $11.95 | https://www.adafruit.com/product/4438 |
| Protected lithium-polymer cell: 1,200 mAh default; the 500 mAh only if cold start is proven | any / Adafruit | $10 to $15 (unverified) / $7.95 | no URL in the lanes / https://www.adafruit.com/product/1578 |
| Spare board, three cameras and cables | Waveshare | $70 to $110 | as stage 2 |
| Pod and pack prints, 8 to 15 tries (or a $200 to $300 home printer) | print service | $150 to $300 (unverified) | https://jlc3dp.com/news/drastic-material-price-cuts-and-adjusted-post-processing-service-fees |
| Charger plus 5 V boost board (raises 3.7 V to 5 V), inline fuse, button, recording light, wire; bench tools (iron, multimeter, flux, calipers, USB-serial adapter); Linux build machine or cloud VM | any | about $23 + $125 to $200 + $0 to $180 (unverified) | no URL in the lanes |

Steps: a recorder in C on Rockchip's media library (camera to MP4 on a button press); its first milestone is the
section 4 demo. Then the IMU log as a Gyroflow `.gcsv` sidecar on the frame clock (C25, unverified), QR pairing, and
the pod in beginner CAD (computer-aided design: Onshape or a Python CAD library). A Raspberry Pi Zero 2 W is the
easier software fallback, but at 1080p it can at best equal today. Skills learned: soldering (an evening), Buildroot
(the vendor's Linux build system), C media code, CAD. Bought: printing; for hired help see
[lane-manufacturing.md](lane-manufacturing.md) sections 3.3 and 4.2. **Done:** a clip recorded at T plays on
`/sessions` by T + 60 s; a hotspot cut mid-upload recovers with no duplicate; on one charge, 2 hours on the head, 15
minutes recorded across 32 presses, all clips uploaded; pack surface under 43 °C over 2 hours (the limit is
unverified); ball radius at least 1.5x Meta's on the same throws. **Gate:** at least two of {motion log, manual
video exposure, whole-session recording, upload with no other app} work, and you still want it after a session.

### Stage 4. C-frame, three units (+$700 to $1,000, 8 to 16 more weeks)

Buy two more stage-3 part sets (about $175 each) and 3 to 5 frame prints in MJF PA12 nylon ($20 to $110 each; MJF,
Multi Jet Fusion, is a powder 3D-printing process, PA12 the nylon), from the JLC3DP link above. A camera temple that
does not fold, still feeding the strap pack. Skills: frame CAD and print tolerances; hired frame design is $1,500 to
$8,000 (not checked) and breaks the budget. **Done:** a second person wears it for 2 hours; face weight 37 to 44 g
(the whole head load is 90 to 115 g against Meta's 49 to 52 g); three units work.

## 4. How it links into the app

**Transfer** ("architecture 2", lane-app-integration section 2.2). The device joins your phone's hotspot. On clip
close it calls `POST /capture/clips` with `Authorization: Bearer <device token>`, gets a Google Cloud Storage
resumable upload address (its own credential for a week, so no cloud key on the device), sends 8 MiB pieces, and
calls `.../complete`. This reuses the signed-URL path that moved a 372 MB file and avoids Cloud Run's 32 MiB cap. A
mean clip at 18 Mbps is about 39 MB, about 63 s at a 5 Mbps uplink, so it goes between throws. Below about 2.6 Mbps
the backlog grows; the 8 GB storage holds about six sessions for upload at home. Bluetooth is too slow (0.3 to
1.2 Mbps measured: 2 to 6 hours a session).

**Pairing.** A t30g "Devices" page shows a QR code with the hotspot name, password and a one-time claim code; the
device's camera reads it and swaps the code for a revocable token. The lens is sharp from about 0.8 m, so **hold the
phone at arm's length**. No native phone code, so it works from an iPhone browser.

**Changes** (full-time days from the lane, unchecked, C12): B1 capture tables (0.5); B2 capture routes (2); B3/B4
device and claim tables, token, revoke, heartbeat routes (2.5); B5 tests in `tools/run_ci_tests.sh` (1); B6 tracker
export (0.5); B7 device routes must not inherit today's trust in a `user_id` in the body; F1 sessions pages (2 to 3);
F2 session upload (1); F3 devices page with QR (2); F4 a real-browser render check (0.5). A ball line in the app (B9)
is a separate project.

**Smallest end-to-end demo.** (0) F2 uploads the 32 clips of 2026-11-08 as one session with matching hashes.
(1) Stage 3's first milestone: the board on a cap with a hand-inserted token and hand-typed hotspot, recording on a
button press and uploading as above; pass when the clip appears by T + 60 s and survives the hotspot being cut
mid-upload (read a non-zero saved offset before resuming, so the test can fail). (2) A second person pairs it by QR
to their own email-only account from an iPhone and their clip lands there.

## 5. Getting it manufactured

**At 1 to 3 units it is print-and-hand-assemble** ([lane-manufacturing.md](lane-manufacturing.md)): the frame and
pack from an online nylon print service (JLC3DP's $0.275 per gram is an August 2025 price; re-check), bought
development and breakout boards from Waveshare and Adafruit, and assembly by you. The US radio regulator (FCC)
requires no approval for five or fewer devices for personal use, not marketed and "not constructed from a kit"
(47 CFR 15.23); the radio is a pre-made module. Assembled boards from China pay about 37.5 % duty; a Section 301
exclusion for some bare boards runs to 9 January 2027 (snippet).

**At 50 to 100 units** (lane-manufacturing sections 2.4 and 7): print frames in one batch ($2,000 to $4,000 for 100);
injection moulding pays only from several hundred units, after $9,000 to $40,000 of tooling (not checked); a custom
carrier board becomes worth it, assembled by a board house; final assembly stays by hand; radio testing is needed
because the exemption ends at five. The lane's total is $8,000 to $35,000 over 12 to 20 weeks (unverified). A
factory customising an existing glasses platform starts at "200 pieces for select models"; a design house at about
$25,000 (not checked); hired board design at $2,000 to $12,000 (lane arithmetic; the "$10,000+" quote is not on its page).

## 6. Risks and unknowns

**What the checkers refuted or corrected, and what it moved here.**

- The SC3336 view in portrait is **44 x 84 degrees** by the maker (C21), not 48 x 86: about 27 degrees narrower across
  the lane than Meta's 71. Stage 0(d) and the shoot-out's 95 % in-frame test exist because of this.
- The $36.99 to $81.99 board price is the whole family's range (C20); the Wi-Fi board is about $45 to $51 (unverified).
- Gen 2 is $379 with clear lenses only (C7); three pairs are $1,137 to $1,377.
- The Section 301 exclusion date moved to 9 January 2027 (C30, stale); 37.5 % stays the planning rate.
- "200 pieces per model" is "200 pieces for select models" (C33); the "$10,000+" design quote is not on its page (C31).
- Feasibility review: Mentra Live fails (3.7 px); the carrier board fails (cost, time, heat); the app half is 6 to 10
  weeks, not 6 to 7; the pod is $600 to $1,200 and 30 to 40 weeks, not $500 to $700 and 21 to 27; three units are
  $1,300 to $2,200, not $1,000 to $1,800; the battery holds only for cold-start, one-clip-per-press use.

**Still unverified, and how to check each by hand.**

| Claim | What it says | Check |
|---|---|---|
| C5 | Gen 1 lens about 100 degrees, so 959 px focal length; every pixel ratio | Stage 0(c), or the stick test in stage 2 |
| C4 | Meta auto-import runs without opening the Meta app | Stage 0(b) |
| C6 | Gen 2 3K is about 6.4 megapixels, 1.5x | ffprobe one real 3K clip before buying |
| C19 | 30 fps at 2304x1296 to file on the RV1106 (one report: about 23 fps) | Stage 2 bench |
| C23 | Recording power about 0.8 W; idle about 0.3 W | Stage 2 power meter |
| C25 | IMU on the same clock as video frames | Stage 3: tap the device on a table on camera, compare spike times |
| C26 | Manual exposure for video | Stage 2 bench |
| C15, C16 | Mentra's view-narrowing on video; webhook transport | Only if Mentra is bought as a test bed |
| C29, C31, C35 | Board-spin cost, hired-design range, bench-tool cost | Get quotes |
| C10, C12, C18, C24, C27 | Hotspot sizing, effort estimates, safe view (never checked) | Stage 0(e), your own time log, stage 0(d) |

Also unverified: the 43 °C two-hour skin limit, the cell's usable fraction, boot time, how many neck bends the camera
ribbon survives (buy five), and whether the vendor's software needs an x86 Ubuntu build machine.

**What no lane answered:** whether more far-end pixels actually raise tracker recall (the shoot-out is built to
answer it); the hotspot uplink inside your alley; how far the pin deck wanders; prescription lenses in a printed
rim; duty on printed nylon and finished glasses; cheaper chip families (Ingenic, Novatek, Allwinner V85x,
SigmaStar); Meta's developer terms; how long an Android background gallery watcher would take; and a sourced
50-to-100-unit cost.

## 7. Decisions needed from you

1. **Does "$1,000" mean per unit or the whole effort?** Recommendation: the whole effort. Stages 0 to 3 ($600 to
   $1,200 to one pod) fit only at the low end; three units in a frame ($1,300 to $2,200) do not. If per unit, every surviving option fits.
2. **First-person bowling only, or must the device also film lifts from a stand?** Recommendation: bowling only for
   now, but draw the pod clip to also take a small tripod thread, which costs nothing and keeps the 100 Club option.
3. **Android only, or iPhone too?** Recommendation: both, because the recommended design needs no native phone code:
   pairing and viewing are browser pages. Only the stage-1 upload page is weaker on iPhone (keep the screen on).
4. **If the shoot-out fails on pixels, is the motion log alone worth 30 to 40 weeks of evenings?** Recommendation: no;
   buy a Gen 2 and put the time into the tracker instead.
5. **One clip per button press, or record the whole session and let the app cut it?** Recommendation: per press.
   Whole-session recording needs a microSD card (65 minutes at 18 Mbps is 8.8 GB against 8 GB on board), about 35 GB
   a month of hotspot data, app-side cutting, and rules out ever moving the electronics into a temple arm (53 to 61 °C).
6. **Buy a Gen 2 now?** Recommendation: not yet. Run stage 0(a) first; if you already own one, 3K is a setting.
