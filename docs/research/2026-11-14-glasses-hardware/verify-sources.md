# Source verification of the candidates claims ledger

Written 2026-11-14 by the adversarial source-check stage. Every URL below was accessed on 2026-11-14.
"Read" means the page itself was fetched and read; "snippet" means only a search-result summary was seen.
Verdicts: CONFIRMED, REFUTED, STALE, UNVERIFIED, or CONFIRMED (snippet only). Default is UNVERIFIED.
Kinds in scope: price, availability, spec, capability, minimum-order, lead-time. Effort and physics claims
(C10, C12, C18, C24, C27) are out of scope for this stage and are listed as NOT CHECKED (out of scope).

Status: DONE (see the Status section at the end). Headline: nothing found changes the recommendation.
Refuted details: the SC3336 portrait view is 44 x 84 degrees by the maker (not 48 x 86); the C20 price range is
for the whole board family, not the Wi-Fi variant; C33's "per model" and C31's "$10,000+" are not on the cited
pages. Stale: the Section 301 exclusion date in C30 moved to 9 January 2027 (snippet). Gen 2 is $379 only with
clear lenses; Mentra's view crop for video is still undocumented; 30 fps at full size and manual video exposure on
the RV1106 are unproven.

## 1. Verdict table, part 1: candidate A (Meta glasses + app uploader) and candidate B (Mentra Live)

All pages accessed 2026-11-14. "Read" = page fetched and read; "snippet" = search summary only.

| id | verdict | evidence quote (how read) | URL | corrected value |
|---|---|---|---|---|
| C1 | CONFIRMED | Read: the `.high` stream setting is "720 x 1280"; frame rates "Valid values: `2`, `7`, `15`, `24`, `30` FPS"; default `StreamConfiguration()` is `.medium`, 504 x 896. Article dated 13 October 2026. The changelog (C2 URL) independently says "High resolution (720x1280) video can be requested" (0.5.0). The "about 0.5x" ratio is lane arithmetic, not checked here | https://mixed-news.com/en/meta-dat-camera-720x1280-lower-resolution-higher-quality/ | none. Note the default is 504x896, so an app must ask for `.high` explicitly |
| C2 | CONFIRMED (as a negative, from this one page) | Read the Android changelog through "[1.0.1] - 2026-10-09". No entry reads recorded media from glasses storage. Closest items: "`Camera.photo` captures standalone high-quality photos" (1.0.0, Experimental) and a sample that can "record video ... while the app is backgrounded" (the page does not say where that recording is saved; that it is the phone recording the live stream is this stage's inference). The other three Meta pages the lane cited were not re-read | https://raw.githubusercontent.com/facebook/meta-wearables-dat-android/main/CHANGELOG.md | none. New fact: toolkit is now 1.0.1 (2026-10-09), and has an experimental high-quality still-photo call |
| C3 | CONFIRMED | Read: "Most Android (13+) and iOS phones have auto-import on by default"; importing "moves recordings from your glasses to your phone's photo app" | https://www.meta.com/ai-glasses/learn/guide-shooting-pov/ | none |
| C4 | UNVERIFIED (and doubtful) | No primary source. Meta's guide (read) does not say whether the app must be open; its manual-import steps start with opening the Meta AI app and tapping Import. A third-party troubleshooting blog (snippet only, not Meta) says media "often syncs only while the app is actively open" and pauses when the app is swiped away or the screen locks. A third-party guide (snippet) says auto-import needs glasses on, Bluetooth and Wi-Fi on, photo-library permission, and works best above 30 % glasses battery | https://www.meta.com/ai-glasses/learn/guide-shooting-pov/ ; https://evezone.evetech.co.za/quick-bytes/ray-ban-meta-photos-and-videos-not-syncing-to-the-app-how-to-fix-the-transfer (snippet) | Treat as likely false until the stage-0(b) phone test. A-watch's value depends on it |
| C5 | UNVERIFIED | Meta's own guide (read) lists Ray-Ban Meta (Gen 1) video as "1080p", while the measured baseline is 1376x1824. The follow-up search below (snippet) found retailers giving Gen 1 video as 1440 x 1920, footnoted as "1080p", so "1080p" is a class label and there is no contradiction. No Gen 1 field-of-view figure was found; "100°" is attached to Gen 2 only | https://www.meta.com/ai-glasses/learn/guide-shooting-pov/ | Unchanged (about 100 degrees, unsourced). Stage 0(c) still has to measure it |
| C6 | CONFIRMED for "3K at 30 fps"; UNVERIFIED for "6.4 megapixels" and "1.5x" | Read (Meta guide): Gen 2 and Oakley Meta "Up to 3K Ultra HD at 30 frames per second (fps), or 1080p at 60fps"; "3K video is supported on Oakley Meta HSTN, Oakley Meta Vanguard and Ray-Ban Meta (Gen 2) models." Read (Meta newsroom, 17 Sep 2025): "3K Ultra HD video capture", "up to 60 frames per second", and a pixel count "more than double the previous generation's", with no pixel dimensions. The TechRadar page fetched only its headline | https://www.meta.com/ai-glasses/learn/guide-shooting-pov/ ; https://about.fb.com/news/2025/09/ray-ban-meta-gen-2-better-battery-life-video-capture/ ; TechRadar URL (headline only, UNVERIFIED) | No primary source gives 3K pixel dimensions. "More than double the pixel count" implies more than about 1.41x linear, so 1.5x is plausible but is still an inference |
| C7 | CONFIRMED (Meta newsroom, read) ; CONFIRMED (snippet only) for current Meta store | Read: "starting at $379 USD" (Meta newsroom, 17 Sep 2025). Read: the tracker page "Last Updated: 1 June 2026" lists $379; it is a product-manager toolkit apparently run by an app studio, not a retailer. Snippet: Meta's Gen 2 store page "starting at $379"; a guide dated 30 Sep 2026 says $379 on Meta's US store and that Gen 2 is "no longer Meta's newest pair". Snippet: Walmart lists some styles at $459; Target $409.99 for polarized. Meta's store page itself fetched only its title | https://about.fb.com/news/2025/09/ray-ban-meta-gen-2-better-battery-life-video-capture/ ; https://www.meta.com/ai-glasses/ray-ban-meta-gen-2/ (title only) ; https://testlisting.pages.dev/ai-glasses-toolkit.htm | $379 is the starting price with clear lenses; polarized or Transitions lenses raise it to about $409 to $459 (snippet). Three pairs: $1,137 to about $1,377 |
| C13 | CONFIRMED | Read: "$449." with no sale price; "Ships in 2–5 business days." | https://mentraglass.com/live | none. Launch coverage (Engadget, TechSpot, 9to5Google, January 2026) said $299 for a first batch of 1,000 shipping 15 February (snippet); the price has since risen to $449 |
| C14 | CONFIRMED for the quoted specs; the 0.68x is synthesis arithmetic | Read: "HD 1080p videos"; "119° field of view, landscape orientation"; "HD 3264 × 2448 images"; "45 minutes video calling · 8+ hours normal use"; "43 grams"; "MTK8766 chipset"; "WiFi + Bluetooth". Storage not listed. The always-on privacy light the candidates file cites is **not on this page** | https://mentraglass.com/live | Privacy light: unsourced on today's page |
| C15 | UNVERIFIED (the docs do not say) | Read: `setCameraFov` "clamps `fov` to 62-118 degrees", presets "82, 102, and 118 degrees with center ROI", listed under gallery-mode capture settings; "output resolution and effective detail can vary by capture path, firmware, and camera mode." Nothing says it applies to video. New: video size is set by `setVideoRecordingDefaults({width, height, fps})`, with no documented maximum (the only example is 1280x720 at 30). Manual `exposureTimeNs`/`iso` are documented for photos and camera warm-up only | https://docs.mentraglass.com/bluetooth-sdk/api-reference.md | none: the docs are silent on video, as candidates.md already said (the same doc says gallery mode starts video on a long press, so it may apply). Stays the first thing to test after buying |
| C16 | CONFIRMED (multipart webhook); transport UNVERIFIED | Read: the webhook "should accept multipart form data with a `video` field and `requestId`"; with a webhook, `stopVideoRecording(...)` "waits for the video upload to finish successfully". The page does not name the HTTP method or say Wi-Fi. `/api/gallery` is documented for photos only and "is only reachable over the glasses Wi-Fi hotspot"; no video download path is documented | https://docs.mentraglass.com/bluetooth-sdk/camera-streaming.md ; https://docs.mentraglass.com/bluetooth-sdk/api-reference.md | Route (2) in candidate B (pull videos from `/api/gallery` over the hotspot) is **not documented** for videos; only route (1), the webhook, is |
| C17 | CONFIRMED | Read: "Gyroscope, magnetometer, and fused orientation aren't exposed yet." Raw accelerometer `onAccel` exists but "This is G2-only today." Mentra Live is not listed; "On glasses without an exposed IMU stream the subscription succeeds and no events arrive." The Bluetooth SDK reference has no IMU call | https://docs.mentraglass.com/app-devs/core-concepts/imu.md | none |

## 2. Verdict table, part 2: shared app claims and candidate C (custom pod, frame, carrier board)

| id | verdict | evidence quote (how read) | URL | corrected value |
|---|---|---|---|---|
| C8 | CONFIRMED (internal source, not a web page) | Read the repository memory note: "Verified e2e incl. a real 372 MB Pixel HEVC video through the browser (resumable, ~80 chunks) + a simulated drop/resume." Same note: `shouldCompress()` skips compression on iOS and above 200 MiB, but on other platforms `uploadVideo()` compresses files of 24 MiB and up unless called with `compression: 'off'` | repository memory note `upload_32mb_limit.md` | none. A mean Meta clip (33.4 MB) is above the 24 MiB compression threshold, so the uploader must pass `compression: 'off'`, as candidate A already says |
| C9 | CONFIRMED | Read: "A session URI expires after one week but can be cancelled prior to expiring"; the URI "acts as an authentication token, so the requests that use it don't need to be signed and can be used by anyone to upload data to the target bucket without any further authentication" | https://docs.cloud.google.com/storage/docs/resumable-uploads | none |
| C10 | NOT CHECKED (physics, out of scope); arithmetic re-done | 1.07 GB over a 65-minute span = about 2.2 Mbps; a 33.4 MB mean clip takes about 13 s at 20 Mbps and 53 s at 5 Mbps. The arithmetic holds; the hotspot speed in the alley is unmeasured | - | - |
| C11 | CONFIRMED | Read: on iOS 18.2 (iPhone 16 Pro Max, 2M PHY, MTU 244, 15 ms interval) "the maximum achievable throughput is around 300-400 kbps"; other iPhones on iOS 18 "around 400-600"; Android and Windows "stable throughput of 1000-1200 kbps". The Infineon page returned HTTP 403 (not read) | https://developer.apple.com/forums/thread/770717 ; https://community.infineon.com/t5/ModusToolbox-Blog/BLE-Throughput-Rate-Benchmark-Test-for-Cypress-BT-SoCs/bc-p/267238 (403) | none. At 1.2 Mbps, 1.07 GB takes about 2 hours; at 0.4 Mbps about 6 hours |
| C19 | CONFIRMED for Wi-Fi 6 and Bluetooth 5.2; CONFIRMED (snippet only) for 3072x1728 at 30 fps H.265 | Read (Waveshare): "2.4GHz WiFi 6", Bluetooth 5.2 with BLE, 8GB eMMC, "Onboard microphone"; the page **does not state** the encoder resolution. Read (Luckfox wiki): ISP "Max input 5M @30fps", W models "2.4 GHz Wi-Fi 6, Bluetooth 5.2, and BLE". Snippet (CNX Software, Pico Pro/Max article): "3072×1728 (5M) @ 30fps H.265/H.264 encoding". The CNX Ultra article returned 403 and the Rockchip datasheet PDF came back empty. **Adverse:** Luckfox's own MPI wiki reports that capturing 2304 × 1296 and encoding H.264 for RTSP with an opencv-mobile frame-rate overlay "can reach about 23 frames" on the Pico Pro | https://www.waveshare.com/Luckfox-Pico-Ultra.htm ; https://wiki.luckfox.com/Luckfox-Pico-Ultra/ ; https://wiki.luckfox.com/Luckfox-Pico-Pi/MPI/ ; https://www.cnx-software.com/2024/02/29/luckfox-pico-pro-pico-max-rockchip-rv1106-boards-100m-ethernet-5mp-camera/ (snippet) | The rated encoder figure is secondary-sourced only. 30 fps at full SC3336 size is not shown by any page; the one measured figure, with an OpenCV overlay in the loop, is about 23 fps. Add "30 fps at 2304x1296 to file" as a stage-3 bench test |
| C20 | CONFIRMED as the family's range; REFUTED as the price of the Wi-Fi variant | Read: "$36.99 - $81.99", with no per-variant price and no stock shown. Variants are Ultra (RV1106G3, 256 MB) or Ultra B (RV1106G2, 128 MB), with or without Wi-Fi/Bluetooth ("only available in Luckfox Pico Ultra W / Ultra BW series"), PoE and display options. Snippet: a bare Pico Ultra W at $50.99 on Luckfox's own store; Newegg $74.99 for the W PoE kit | https://www.waveshare.com/Luckfox-Pico-Ultra.htm ; https://www.luckfox.com (snippet) | REFUTED as a price for the part C needs: the range covers the whole family (with and without Wi-Fi, PoE, display). A snippet gives $50.99 on Luckfox's store, variant unclear. Luckfox's store (read) lists "Luckfox Pico Ultra W LCD Kit A: $68.99" and the 480x480 display alone at $23.99, which suggests about $45 for a bare W board (this stage's inference). That the $36.99 floor is a non-W variant is also an inference. The lane's $45 to $82 budget holds |
| C21 | CONFIRMED for the camera specs and price; the 1.7x arithmetic checks out; REFUTED for the 48 x 86 degree portrait view stated in candidates.md | Read (Waveshare): "$8.99", SC3336, "3MP (2304×1296)", "3.95mm", "F2.0", "98.3°", "<33%". Read (Luckfox wiki): FOV-D "98.3°", FOV-H "84°", FOV-V "44°". Snippet (third-party listings, no SmartSens datasheet): pixel "2.45 µm x 2.45 µm", 1/2.8-inch. Arithmetic: focal length 3.95 mm / 2.45 µm = 1,612 px, so about 28.1 px/deg at the centre, 1.68x the baseline's 959 px | https://www.waveshare.com/product/luckfox/boards-modules/luckfox-pico-core1106/sc3336-3mp-camera-b.htm ; https://wiki.luckfox.com/SC3336-3MP-Camera/ ; https://www.gophotonics.com/products/cmos-image-sensors/smartsens-technology/21-1025-sc3336 (snippet) | Portrait view is **about 44 x 84 degrees** by the maker's figures, not 48 x 86 |
| C22 | CONFIRMED | Read: "Your tiny, tiny $15 computer"; "H.264, MPEG-4 decode (1080p30); H.264 encode (1080p30)"; no H.265; "2.4GHz 802.11 b/g/n wireless LAN", "Bluetooth 4.2"; "will remain in production until at least January 2030". The "can at best equal the baseline" part is lane arithmetic | https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/ | none |
| C23 | UNVERIFIED | The cited forum thread returned HTTP 403. A different Luckfox forum thread (snippet only) has a user on a Pico Pi A W (RV1106G3) saying that "in sleep mode, the board consumes approximately 0.3 W". No page gives power while recording | https://forums.luckfox.com/viewtopic.php?t=1822 (403) ; https://forums.luckfox.com/viewtopic.php?p=8201 (snippet) | Idle or sleep about 0.3 W (anecdotal); recording power unsourced. The 500 mAh battery-life figure remains an estimate |
| C25 | CONFIRMED for the file format; the capability is UNVERIFIED | Read (Gyroflow): `.gcsv` needs a `GYROFLOW IMU LOG` or `CAMERA IMU LOG` first line, `version`, `id`, `orientation`, `tscale`/`gscale`/`ascale`, and columns `t,gx,gy,gz[,ax,ay,az]`; timestamps "should come from the same time source as the video capture to prevent drift"; the page defines no time-offset field. Read (Adafruit 4438): LSM6DSOX "$11.95", in stock, data rate up to 6.7 kHz | https://docs.gyroflow.xyz/app/technical-details/gcsv-format ; https://www.adafruit.com/product/4438 | That the RV1106 media stack exposes per-frame capture timestamps on the same clock is not sourced |
| C26 | UNVERIFIED (Rockchip and Pi) | Rockchip: Luckfox's MPI wiki (read) shows only `SAMPLE_COMM_ISP_Init/Run/Stop` and says the ISP handles "automatic exposure control, automatic gain control"; it has no manual-exposure example, and no rkaiq manual-exposure API page was found. Pi: Raspberry Pi's camera documentation (read, first 100,000 of 242,232 characters) shows `--shutter`/`--gain` only in a `rpicam-still` example. A snippet says libcamera clips a manual exposure time to the frame-duration limits | https://wiki.luckfox.com/Luckfox-Pico-Pi/MPI/ ; https://www.raspberrypi.com/documentation/computers/camera_software.html | (from memory, unverified) `rpicam-vid` accepts `--shutter`, and Rockchip's rkaiq has a manual AE mode. Treat C's "Better" on release blur as unproven until the bench test |
| C27 | NOT CHECKED (physics, out of scope), but its input changed | See C21: the maker's portrait view is 44 x 84 degrees. That still exceeds the lane's 35 x 55 degree floor, with less head-wander margin | https://wiki.luckfox.com/SC3336-3MP-Camera/ | 44 x 84 degrees |
| C28 | CONFIRMED (dated August 2025) | Read: MJF-PA12 "$0.275/g (adjusted)", "Prices exclude tax", dated "Aug 13, 2025"; no minimum order is mentioned. Today's price was not checked against the instant-quote tool (no quote forms used) | https://jlc3dp.com/news/drastic-material-price-cuts-and-adjusted-post-processing-service-fees | none; it is 15 months old, so re-check at order time. "$20 to $110 per iteration landed" is lane arithmetic |
| C29 | CONFIRMED for $25 per 5 flex boards; the $150 to $500 per spin is UNVERIFIED | Read: a starting price of "$25 USD" for 5 flexible PCBs with a "4 to 5 day build"; board size and layers behind it are not stated; tooling and setup are charged once per design; no assembly prices | https://jlcpcb.com/blog/flex-pcb-cost-pricing-guide | Assembled-spin cost: quote only |
| C30 | CONFIRMED (two law-firm and vendor blogs, not CBP or USTR directly) | Read (AtlasPCB, 21 Aug 2026): "approximately 37.5%" on China-origin PCBs and PCBAs = 12.5 % Section 301 base layer + 25 % product tariff on HTS 8534; PCBAs "the full 37.5% combined tariff has applied throughout 2026". Read (Thompson Hine): the de minimis suspension "is effective as of June 24, 2026" and is "indefinite", with an international-mail compliance date of 22 October 2026. Snippet (KPMG, 9 Nov 2026; Federal Register 2026-22925): the 178 Section 301 exclusions under 9903.88.69 were extended to 9 January 2027 | https://www.atlaspcb.com/news/news-pcb-tariff-section-301-exclusion-expiry-november-2026/ ; https://www.thompsonhinesmartrade.com/2026/06/cbp-issues-interim-final-rules-indefinitely-suspending-the-de-minimis-exemption-for-imports/ ; https://kpmg.com/us/en/taxnewsflash/news/2026/11/ustr-section-301-china-product-exclusions.html (snippet) | 37.5 % holds for assembled and flex boards. The page gives 12.5 % for excluded bare rigid boards and 37.5 % otherwise; the 25 % figure from the other blog matches neither total (it is the product layer alone), so it is not a planning rate. STALE part: the exclusion's 9 November 2026 expiry was extended to 9 January 2027 (snippet). Duty on a finished development board (not HTS 8534) was not checked |
| C31 | UNVERIFIED (range); REFUTED for the "$10,000+" input (not on the cited page); the $750 and $45 to $80 an hour inputs are CONFIRMED (read and snippet) | Read (Cad Crowd job): budget "$750", "Fixed-rate (USD)", job "Ended", client "Payment not ready"; the "$10,000+" figure is **not** on this page. Fiverr guide returned 403; snippet: PCB design "$45 to $80" an hour, and a fixed price "about $185.92"; individual profiles list $10 to $128 an hour | https://www.cadcrowd.com/job/9896-camera-smart-glasses-pcb-design ; https://www.fiverr.com/resources/guides/costs/electronics-design-engineer (403; snippet) | The $2,000 to $12,000 range is lane arithmetic on hours. "$10,000+" is unsourced on the cited page |
| C32 | CONFIRMED, with a condition the ledger leaves out | Read: "Equipment authorization is not required for devices that are not marketed, are not constructed from a kit, and are built in quantities of five or less for personal use." Paragraph (b): the builder "is expected to employ good engineering practices", and § 15.5 (no harmful interference) applies | https://www.law.cornell.edu/cfr/text/47/15.23 | Add "not constructed from a kit". Whether development boards count as a kit was not checked; the radio itself is a pre-made module |
| C33 | CONFIRMED for "200 pieces"; REFUTED for "per model" (not on the page) | Read (Microwear): "MOQ starts from 200pcs for select models"; "per model" is **not** stated, and the models are not named. The MENAFN article was not read | https://microwear.info/ai-glasses | "200 pieces for select models" (not per model) |
| C34 | CONFIRMED | Read (review, January 2026): the unit's video is "1600 x 1200", "not '1080p'" as marketed; "Allwinner V821 AI processor"; price "USD 199". The app is not named | https://musicphotolife.com/2026/01/padmate-viewmate-review-ai-smart-glasses/ | none |
| C35 | UNVERIFIED | Lane estimate; no price was sourced for this stage | - | - |

### Claims not checked

- C12, C18 and C24 (effort estimates): NOT CHECKED, out of this stage's scope (not price, availability, spec,
  capability, minimum-order or lead-time).
- C10 and C27 (physics): NOT CHECKED as claims; their inputs were re-checked above.
- C5 (Gen 1 lens 100 degrees): no source was searched for the field of view itself (see the C5 row); it stays
  UNVERIFIED.

### Follow-up on C5 (one search, snippet only)

A search (2026-11-14, snippet only) found retailer listings (B&H Photo, Best Buy) giving Ray-Ban Meta Gen 1 video
as 1440 x 1920 at 30 fps and 12 MP stills at 3024 x 4032, with Best Buy footnoting this as "1080p". So Meta's
"1080p" for Gen 1 is a class label, and the measured 1376x1824 baseline fits a Gen 1 recording 1440x1920 with a
crop. The contradiction flagged in the C5 row is therefore probably not real. The same snippet says Meta and
Ray-Ban attach "100°" to Gen 2 only; no Gen 1 field of view was found. **C5 stays UNVERIFIED.**
Source: https://www.bhphotovideo.com/c/product/1848477-REG/meta_899_00605_01_ray_ban_wayfarer_glasses_shiny.html (snippet).

## 3. Load-bearing facts missing from the ledger

These are used in candidates.md, would move a cost or a verdict, and have no ledger row. Checked where noted.

| Fact in candidates.md | Status today | Source |
|---|---|---|
| Adafruit 500 mAh protected cell at $7.95 | CONFIRMED, read: "Lithium Ion Polymer Battery - 3.7v 500mAh", $7.95 (1 to 9), "include[s] the necessary protection circuitry", in stock, 10.5 g, 29 x 36 x 4.75 mm | https://www.adafruit.com/product/1578 |
| LSM6DSOX board at $11.95 (candidates.md says "snippet") | CONFIRMED, read: $11.95, in stock | https://www.adafruit.com/product/4438 |
| Luckfox Core1106 module at $36.99 (stage C3) | Page shows a range "$26.99 - $44.99" across variants, 30 x 30 mm, "Hardware encoding, supports MJPEG, H264, H265", Wi-Fi optional. $36.99 is inside the range but is not tied to a variant on the page | https://www.waveshare.com/core1106.htm |
| Gen 2 battery "up to eight hours" | CONFIRMED, read: "can last up to eight hours with typical use" | https://about.fb.com/news/2025/09/ray-ban-meta-gen-2-better-battery-life-video-capture/ |
| Mentra Live's always-on "white privacy light" | Not on today's product page (read). Unsourced | https://mentraglass.com/live |
| Mentra Live storage, and maximum video size through `setVideoRecordingDefaults` | Not published. The only documented example is 1280x720 at 30 fps | https://docs.mentraglass.com/bluetooth-sdk/camera-streaming.md |
| Candidate B route (2): pulling videos from `/api/gallery` over the glasses hotspot | Documented for photos only | same |
| Gen 1 battery "154 mAh, up to 4 hours mixed use" (vrarwiki) | NOT CHECKED | - |
| Charger plus boost board about $18, printed pod about $30, China shipping and duty $20 to $40, JLCPCB 5 assembled 4-layer boards $100 to $250 | Lane estimates, NOT CHECKED. Duty on a finished development board (not a bare PCB, HTS 8534) was not checked | - |
| RunCam Thumb 2 at $180 with a gyro file (roadmap stage 2) | NOT CHECKED | - |
| 30 fps at full SC3336 size on the RV1106 | No source shows it. The one measured figure is about 23 fps with an OpenCV overlay (see C19) | https://wiki.luckfox.com/Luckfox-Pico-Pi/MPI/ |
| Toolkit default stream is 504 x 896, not 720 x 1280 | New fact, read (see C1) | https://mixed-news.com/en/meta-dat-camera-720x1280-lower-resolution-higher-quality/ |
| Design house at $25,000 and up; injection-mould tooling at $9,000 to $40,000 (they carry the closed-route verdict) | NOT CHECKED | - |
| Hired frame design at $1,500 to $8,000 | NOT CHECKED | - |
| Duty $0 on Mentra Live because it is bought from a US vendor (the US base is "from memory") | NOT CHECKED | - |
| Phone hotspot uplink of 5 to 20 Mbps (carries B's and C's transfer score) | NOT CHECKED; unmeasured in the alley | - |

## 4. Unsourced

Nothing here is presented as fact.

- C5: the Gen 1 lens field of view (about 100 degrees diagonal). Every pixels-per-degree ratio rests on it.
- C4: whether Meta's auto-import runs without the Meta AI app open.
- C23: power while recording on any RV1106 board.
- C26: manual video exposure on either camera stack.
- C35: bench-tool cost.
- C31: the "$10,000+" Cad Crowd figure; the $2,000 to $12,000 range.
- C29: the $150 to $500 landed cost of a spin of 5 assembled boards (quote only).
- The 3K pixel dimensions of a Gen 2 clip (C6's "6.4 megapixels").

## 5. What this changes

1. **Candidate A stands.** Its claims that could be checked hold: the toolkit stream is capped at 720x1280 (and
   defaults to 504x896), the toolkit gives no access to recorded clips, auto-import into the phone's photo app is on
   by default on most Android 13+ and iOS phones, and the resumable GCS path has moved a 372 MB file. The A-web
   uploader does not depend on anything that failed.
2. **A-watch is weaker than the file says.** C4 has no primary source either way, and the only evidence found
   (third-party, snippet) says imports often stall unless the Meta app is open. Run stage 0(b) before any A-watch
   work; expect it to fail.
3. **The Gen 2 test (roadmap stage 2) holds but costs a little more.** $379 is confirmed as the starting price;
   polarized or Transitions lenses take it to about $409 to $459 (snippet). "3K at 30 fps" is Meta's own words;
   the pixel size of a 3K frame is not published anywhere found, so the 1.5x stays an estimate ("more than double
   the pixel count" implies at least 1.41x linear). A snippet says Gen 2 is no longer Meta's newest pair, so the
   choice of model to buy may be worth one more look.
4. **Candidate B: $449 is confirmed, with "Ships in 2–5 business days"** (no stock count is shown), up from a
   $299 launch price. The view-narrowing control is still undocumented for video, as candidates.md said. One point
   is worse than candidates.md says: only the webhook route is documented for video (the hotspot gallery pull is
   documented for photos only).
   The privacy light is not on today's product page. No IMU stream (C17) is confirmed.
5. **Candidate C's 1.7x pixel gain checks out on arithmetic** (2.45 µm pixels, 3.95 mm lens: about 28 px/deg at
   the centre, 1.68x), but its view is **about 44 x 84 degrees**, not 48 x 86, which narrows the head-wander
   margin and makes stage 0(d) more important. Two of C's "Better" scores are unproven: 30 fps at full sensor size
   on the RV1106 (only a secondary source rates it; a Luckfox example measured about 23 fps), and manual video
   exposure (no page shows it on either stack). The stage-3 gate should add both as bench tests, beside power and
   heat.
6. **Costs barely move.** The Wi-Fi Ultra W is about $45 to $51 bare (snippet and inference), inside the $45 to
   $82 budget. Small parts are confirmed at the listed prices. Duty on assembled boards is 37.5 %; excluded bare
   rigid boards pay 12.5 % under an exclusion now extended to 9 January 2027 (snippet); 25 % matches neither. The hired-design range (C31) is softer than
   stated: its "$10,000+" input is not on the cited page, and Fiverr rates start lower than $45 an hour.
7. **The radio exemption has one more condition:** besides "five or less" and "personal use", the device must not
   be "constructed from a kit". This does not obviously exclude a build from development boards, but the ledger
   should carry it.
8. **Nothing found changes the recommendation** ("do not build hardware yet; run the free checks, then build A").
   The verification strengthens the case for stage 0, because the three most load-bearing unknowns (C5 lens view,
   C4 background import, C23 recording power) remain unsourced after a search.

## Status

DONE within budget (about 63 tool calls). Every ledger row C1 to C35 has a verdict or a NOT CHECKED reason:
C12, C18 and C24 are effort claims and C10 and C27 are physics claims, outside this stage's scope.
Pages that could not be read (HTTP 403 or empty): the CNX Software Ultra article, the Luckfox forum thread for C23,
the Infineon BLE blog, the Fiverr cost guide, Meta's store and help pages (title only), TechRadar (headline only),
and the Rockchip datasheet PDF.
