# Lane: build architecture (electronics)

Written 2026-11-14 by a research agent. Status line is at the very end of the file; if the file stops before a
"Status" heading, the agent was cut off and everything above is still usable.

Question: if the owner builds the electronics himself, what goes on a pair of glasses that records video at or above
the baseline in `REQUIREMENTS.md`, and what does it cost?

Conventions used in this file:

- "(page read)" means the agent opened the page with a fetch tool and the quote is from the page text as returned by
  the fetch tool's summariser. "(snippet)" means only a search-result snippet was seen.
- "(from memory, unverified)" marks anything not sourced on 2026-11-14.
- Abbreviations, spelled out once: px = pixels; px/deg = pixels per degree of viewing angle; FOV = field of view
  (HFOV horizontal, VFOV vertical, DFOV diagonal); SoC = system on chip (the main processor); ISP = image signal
  processor; CSI = the MIPI camera serial interface (the ribbon-cable camera connector); H.264 and H.265/HEVC =
  video codecs; IMU = inertial measurement unit (gyroscope + accelerometer); LiPo = lithium polymer cell;
  mAh / Wh = milliamp-hours / watt-hours; BOM = bill of materials; PCB = printed circuit board; UVC = USB video
  class (a plug-and-play USB camera); FCC = the US radio regulator.

## 0. The target number (derived from REQUIREMENTS.md, no web sources)

The tightest tracker constraint is pixels on the ball at the far end of the lane (REQUIREMENTS.md section 3, item 1:
"At the pins the ball is 4 to 13 px in radius at native size"). Converted to a camera-independent figure:

- A bowling ball is about 8.5 to 8.6 inches (0.216 to 0.218 m) in diameter and the head pin is 60 feet (18.29 m)
  from the foul line (both from memory, unverified; these are the standard tenpin figures).
- The wearer's eyes are roughly 1.5 m above the lane and at the foul line at release, so the slant distance to the
  head pin is sqrt(18.29^2 + 1.5^2) = 18.35 m.
- Angular diameter of the ball at the pins = 0.218 / 18.35 = 0.01188 rad = 0.68 degrees. Angular radius = 0.34 degrees.
- Measured radius 4 to 13 px divided by 0.34 degrees = **12 to 38 px/deg** in the encoded frame. The band is 3x wide
  while the frame width only varies about 20 % (1184 to 1424 px), so most of the spread is measurement (blur, halo,
  how far before the pins the ball was measured), not optics.
- Independent cross-check from the optics: if the delivered 1376 x 1824 frame spans roughly a 100-degree diagonal
  (a commonly quoted figure for the Ray-Ban Meta lens; assumed here and unsourced, section (a) found no source for it), the frame diagonal is
  sqrt(1376^2 + 1824^2) = 2285 px, the focal length in pixels is (2285 / 2) / tan(50 deg) = 959 px, and the centre
  of the frame resolves 959 x pi / 180 = **16.7 px/deg**. That gives a ball radius of 0.34 x 16.7 = 5.7 px at the
  pins, which sits inside the measured 4 to 13 px.

**Working target used in the rest of this file:**

| Level | px/deg at frame centre, in the encoded video | Ball radius at the pins |
|---|---|---|
| Baseline (match the Meta glasses) | about 17 | about 6 px |
| Useful improvement | 25 | about 8.5 px |
| Stretch (2x baseline) | 34 | about 11.5 px |

How to compute it for any candidate: px/deg at centre = (lens focal length / effective pixel pitch) x pi / 180, where
"effective pixel pitch" is the sensor's pixel pitch multiplied by any binning or downscale between the sensor and
the encoded frame. Example: a 1.4 micrometre sensor binned 2x2 and then scaled 1.2x has an effective pitch of
1.4 x 2 x 1.2 = 3.36 micrometres. Do not divide horizontal pixels by a diagonal FOV, and do not use sensor megapixels:
only the pixels that survive into the encoded file count.

The other baseline numbers a candidate has to meet (REQUIREMENTS.md section 2): about 2.5 megapixels per frame
(1376 x 1824), portrait, 30 frames per second, about 15 Mbps HEVC, stereo audio. And the session envelope (section
4): 2 hours awake, 15 minutes recording, 2 GB storage, 1 GB off the device in a few minutes.

## (a) Reference: what is inside the Ray-Ban Meta and comparable camera glasses

All rows accessed 2026-11-14. "Gen 1" is the 2023 Ray-Ban Meta, "Gen 2" the 2025 model.

| Item | Gen 1 | Gen 2 | Source and quote |
|---|---|---|---|
| Main chip | Qualcomm Snapdragon AR1 Gen 1 | not found | https://vrarwiki.com/wiki/Ray-Ban_Meta (page read): "The glasses are built on the Qualcomm Snapdragon AR1 Gen 1 platform" |
| Camera | 12 megapixel ultra-wide | 12 megapixel ultra-wide, 3024 x 4032 photos | Same page: "The glasses have a 12-megapixel ultra-wide camera". Gen 2: search snippet attributed to Android Central, https://androidcentral.com/wearables/ray-ban-meta-gen-2 |
| Video | 1440 x 1920 portrait, 30 fps | "3K" up to 60 fps per Meta; 1080p or 3K at 30 fps in a reviewer's test | Gen 1 (page read, vrarwiki): "It records 1080p video in a portrait orientation (1440 by 1920 pixels) at 30 frames per second". Gen 2 (page read) https://about.fb.com/news/2025/09/ray-ban-meta-gen-2-better-battery-life-video-capture/ : "We've added 3K Ultra HD video capture to Ray-Ban Meta (Gen 2)" ... "up to 60 frames per second". Reviewer (snippet, Android Central): "the same video settings: 1080p or 3K at 30 FPS" |
| Clip length limit | 60 s at launch | not found | vrarwiki (page read): "in clips of up to 60 seconds". A later firmware raised this to 3 minutes (from memory, unverified). |
| Battery | 154 mAh, about 4 h mixed use | about 8 h typical use; 50 % charge in 20 min; capacity not found | vrarwiki (page read): "The glasses contain a 154 mAh battery", "Up to 4 hours mixed use (glasses)". Meta (page read): "can last up to eight hours with typical use", "up to 50% in just 20 minutes" |
| Storage | 32 GB | 32 GB | vrarwiki (page read): "32 GB of onboard storage". Gen 2: snippet, Android Central: "32GB; about 500 photos, 100 30-second videos" |
| Radios | Wi-Fi 6, Bluetooth 5.3 | not found | vrarwiki (page read): "Wi-Fi 6 (802.11ax) and Bluetooth 5.3" |
| Weight | 48.6 to 50.8 g | 52 g | vrarwiki (page read): "Weight ranges from about 48.6 grams to 50.8 grams depending on the style". Gen 2: snippet, Android Central: "Weight - 52g" |
| Microphones | five | not found | vrarwiki (page read): "A five-microphone array" |
| Water | IPX4 | not found | vrarwiki (page read): "IPX4 water resistant" |
| Price | from $299 | from $379 | vrarwiki (page read): "Starting at $299 USD"; Meta (page read): "starting at $379 USD" |
| Layout | one temple arm holds the main board and chip; the other holds the battery, a speaker and a microphone | not found | Search snippet attributed to Notebookcheck teardown coverage, https://www.notebookcheck.net/Teardown-of-Meta-Ray-Ban-Smart-Glasses-reveals-innovative-AR-display-in-detail.1134728.0.html (snippet only; that article is mainly about the later Display model) |

What the reference tells a builder:

1. **The energy budget is tiny.** 154 mAh at a nominal 3.85 V is about 0.59 Wh. Four hours of mixed use from 0.59 Wh is
   an average of about 0.15 W. A Raspberry Pi Zero 2 W idles at about 0.6 W (section (b)), four times the Meta
   glasses' whole average. A development-board prototype will therefore carry 3 to 8 times the battery, and that
   battery will not fit inside a temple arm (section (d)).
2. **The measured baseline matches the published video mode.** REQUIREMENTS.md measured frames of 1184 x 1584 up to
   1424 x 1904. All sit inside the published 1440 x 1920, which supports the lead session's guess that the varying
   size is a stabilisation crop out of a 1440 x 1920 frame.
3. **Parts one person cannot buy** (from memory, unverified, but consistent across the industry): the Snapdragon AR1
   chip (sold to device makers under contract, not through distributors); the stacked camera module built for the
   hinge; the custom-shaped battery cell; the rigid-flex circuit that runs through the hinge; the injection-moulded
   frame. Everything in section (b) is a substitute for one of these.

Comparable devices found (all search snippets, not page reads):

| Device | What the snippet says | URL |
|---|---|---|
| Mentra Live | "43-gram device with a 12MP camera and a 119-degree field of view"; another source says "Mediatek MTK8766 CPU, 12MP camera with 112 deg landscape FOV"; open-source operating system with a TypeScript software kit; launch price $299, one site lists $349. Sources conflict on FOV and price. | https://www.engadget.com/wearables/mentras-first-smart-glasses-are-open-source-and-come-with-their-own-app-store-150021126.html , https://www.techspot.com/community/topics/the-open-source-mentra-live-smart-glasses-are-built-for-livestreaming-to-platforms-including-onlyfans.296094/ |
| Brilliant Labs Halo | Does not capture images or video: "low-power optical sensor" for AI models only. Not a candidate. | https://www.uploadvr.com/everyone-is-making-smart-glasses-now/ |
| OpenGlass (BasedHardware) | The repository "is no longer supported and has moved to Omi". Built on a microcontroller camera board (from memory, unverified), so it fails the encoding test in section (b). | https://community.openai.com/t/smart-glasses-for-open-development/681721 |
| Samsung Galaxy Glasses | Reported 155 mAh battery, the same class as the Meta cell. | https://liveinthefuture.org/stories/samsung-galaxy-glasses-bom-clone-ai-subsidy-war |

The Mentra Live is the one comparable device with an open software kit; whether to buy it instead of building is a
question for the "buy" lane, not this one.

## (b) Compute and camera options that can be bought one at a time

"Baseline" below means the REQUIREMENTS.md video: about 1376 x 1824 (2.5 megapixels) at 30 fps, hardware encoded.
All rows accessed 2026-11-14.

### Verdict table

| Option | Max hardware-encoded video | Reaches baseline frame size? | Radios | Power (sourced part) | Size, weight | Unit price | Software maturity |
|---|---|---|---|---|---|---|---|
| Raspberry Pi Zero 2 W | H.264 1920 x 1080 at 30 fps | **No, just short**: 2.07 megapixels against 2.5. It matches the baseline pixels per degree only with a narrower view (section (c)). No HEVC, 8-bit only. | Wi-Fi 2.4 GHz b/g/n, Bluetooth 4.2 | Idle about 0.6 W; full CPU load 2.5 W; recording not measured anywhere found | 65 x 30 mm; about 10 g (from memory, unverified) | $15 | Best of any option: Raspberry Pi OS, Python camera library, large community |
| Raspberry Pi 5 / Compute Module 5 | No hardware encoder; software H.264 1080p30 | No, and far too large and power-hungry for a head | - | - | - | - | Rejected |
| Radxa Zero 3W (Rockchip RK3566) | H.264 and H.265 1920 x 1080 at 60 fps | **No**: same 2.07 megapixel ceiling as the Pi, but adds HEVC and 60 fps | Wi-Fi 6, Bluetooth | Not found | Same 65 x 30 mm outline as the Pi Zero | from $14.90 (2023 article); $61.95 at one US shop, out of stock | Medium. Camera support confirmed only for two older Raspberry Pi cameras |
| Luckfox Pico Ultra W (Rockchip RV1106G3) | H.265 and H.264 "5M" (3072 x 1728) at 30 fps | **Yes**: up to 5.3 megapixels, twice the baseline, in HEVC | Wi-Fi 6 (2.4 GHz only), Bluetooth 5.2 | Forum reports: 0.15 to 0.3 W idle. Recording not found | Board size not on the page read; the bare module version is 30 x 30 mm | $36.99 to $81.99 across variants | Medium-low: vendor Linux (Buildroot), C media library, small community |
| Luckfox Aura (Rockchip RV1126B) | H.265 and H.264 3840 x 2160 at 30 fps | **Yes**: 8.3 megapixels, 3.3 times the baseline | Wi-Fi 6 (2.4 and 5 GHz), Bluetooth 5.4 | Not found | Not found | $50.99 to $145.99 across variants | Medium-low: Buildroot and Debian; a new board (2026 listing) |
| ESP32-P4 boards | H.264 1920 x 1080 at 30 fps on paper | **No**: 2.07 megapixels, and users report 25-27 fps or as low as 9 fps at 1080p | None on the chip itself (from memory, unverified: a second radio chip is added) | Not found | - | - | Low for video. Rejected |
| ESP32-S3 camera boards | Software H.264 320 x 240 at 11 fps | **No, by a factor of about 30 in pixels.** A microcontroller limited to low-resolution motion JPEG. Rejected | Wi-Fi, Bluetooth | - | - | - | Rejected |
| SigmaStar SSC338Q boards (OpenIPC "Thinker", "Mario") | Not sourced (from memory, unverified: about 2688 x 1520 at 30 fps or 4K at about 20 fps) | Probably, unverified | Wi-Fi on the Thinker "Tiny" | Not found; one board ships with a 7.4 g heatsink and a 5.4 g fan, so expect heat | 25 x 25 mm, 8.8 g (Thinker); 9.86 g board (Mario) | Not found | Low for this use: firmware is built for drone video links, not for recording clips |
| Re-housed action camera: RunCam Thumb 2 | 3840 x 2160 at 30 or 60 fps; a 4:3 "4K" mode at 30 fps | **Yes**: 8.3 megapixels or more | **None.** Settings by showing the camera a QR code | Max 3.5 W (700 mA at 5 V), external 5 V only, no battery inside | 26 x 27.5 x 55 mm, 27 g | $119.99 | Closed firmware; nothing to program. Logs its own gyro |
| Re-housed split camera: RunCam Split 4 | 3840 x 2160 at 30 fps or 2.7K at 60 fps | **Yes** | None found | Not found | Lens module 14 x 14 mm on a cable, board 29 x 29 mm, 10.2 g | $89.99 (snippet; official page returned "not found") | Closed firmware. Supports Gyroflow |
| USB camera module cabled to a phone | Whatever the phone encodes; module sends 3840 x 2160 at 30 fps as motion JPEG | **Yes**, if the phone keeps up | The phone's | Draws from the phone | 38 x 38 mm board typical | about $60 to $290 | Depends on writing an Android USB-camera plugin |
| Ingenic, Novatek, Allwinner camera chips | Not researched within budget | - | - | - | - | - | See "Unsourced" |

### Sources for the table

- **Raspberry Pi Zero 2 W.** https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/ (page read): "Your tiny, tiny
  $15 computer"; "H.264, MPEG-4 decode (1080p30); H.264 encode (1080p30)"; "2.4GHz 802.11 b/g/n wireless LAN";
  "Bluetooth 4.2, Bluetooth Low Energy (BLE), onboard antenna"; "CSI-2 camera connector"; "65mm x 30mm".
  Power, all search snippets: https://www.cnx-software.com/2021/12/09/raspberry-pi-zero-2-w-power-consumption/
  "about 120 mA at 5V (600 mW)" idle (the page itself returned HTTP 403 to the fetch tool);
  https://jeffgeerling.com/node/3137 "about 100 mA, or 0.52W" with almost everything turned off;
  https://www.hackster.io/news/raspberry-pi-zero-2-w-review-hands-on-with-the-fastest-zero-ever-b85b155905a5
  "uses 100 mA at idle ... but will use up to 500 mA full-tilt, when all four CPU cores are maxed out". A Raspberry Pi
  product table quoted in a snippet lists "typical bare-board active current consumption of 350mA" (1.75 W).
  One real build: a Pi Zero 2 W camera with a Camera Module 3, a small screen and a single 14500 cell "lasts 70 to 80
  minutes on a charge" (snippet, https://www.cnx-software.com/2026/06/22/optocam-zero-a-raspberry-pi-zero-2-w-based-diy-digital-camera/).
- **Raspberry Pi 5.** Snippet of Raspberry Pi's own white paper,
  https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010033-WP-1-H.264%20encoding%20performance%20on%20Raspberry%20Pi%205_series%20computers.pdf :
  "Raspberry Pi 5 does not feature a hardware H.264 encoder, relying instead on the libx264 software encoder".
- **Radxa Zero 3W.** Snippets: product brief https://dl2.radxa.com/zero3/docs/hw/3w/radxa_zero_3w_product_brief.pdf
  "H.264/H.265 encoding up to 1080p at 60 fps"; https://www.cnx-software.com/2023/12/08/radxa-zero-3w-sbc-rockchip-rk3566-8gb-ram-wifi6-raspberry-pi-zero-2-w-form-factor/
  "as low as $14.90 with 1GB RAM, WiFi 6, no eMMC flash", supports "the Raspberry Pi Camera V1.3 (OV5647) and V2
  (IMX219)" and "unclear whether more recent Raspberry Pi camera modules can also work";
  https://ameridroid.com/collections/vendors/products/radxa-zero-3w $61.95, out of stock. It has a US radio filing:
  https://fcc.report/FCC-ID/2BC6T-RADXAZERO3W/6914352.pdf (URL seen in results, not opened).
- **Luckfox Pico Ultra W.** https://www.waveshare.com/Luckfox-Pico-Ultra.htm (page read): "$36.99 - $81.99";
  "| Processor | RV1106G3 | RV1106G2 |"; "| Memory | 256MB DDR3L | 128MB DDR3L |"; "8GB EMMC"; "Onboard 2.4GHz WiFi
  6 and Bluetooth 5.2/BLE Bluetooth Module"; "the WiFi 6 / Bluetooth module is only available in Luckfox Pico Ultra W
  / Ultra BW series"; "MIPI CSI 2-lane"; "Onboard microphone"; "Built-in self-developed third-generation ISP3.2,
  supports 5-Megapixel". The page does not show the price of each variant or the board size. Encoder limit, snippet
  from https://www.cnx-software.com/2024/06/21/luckfox-pico-ultra-micro-development-board-features-mipi-csi-wifi-6-ethernet-poe-gpio-headers/ :
  "5M@30fps H.265/H.264 encoding, 16M@60FPS JPEG snapshot", with 5M given as 3072 x 1728. Power, forum snippets:
  https://forums.luckfox.com/viewtopic.php?t=1822 about 0.28 W for the Core1106 module, of which "the 0.11W are consumed
  only from RV1106"; https://forums.luckfox.com/viewtopic.php?t=615 "On pico Max I get 30mA@5V (no camera connected)"
  and "the operating current is around 60mA". The same threads say the board "was not designed with low power
  consumption in mind". No measurement of power while recording was found.
- **Luckfox Aura.** https://www.luckfox.com/Luckfox-Aura (page read): "Price Range $50.99 - $145.99"; "Rockchip RV1126B
  Quad-Core 1.6GHz Processor"; "Encoding: 4K@30fps (H.265/HEVC, H.264/AVC)"; "Supports 12MP cameras"; "4-lane MIPI
  CSI camera interface x 2"; "Onboard 2.4GHz/5GHz Wi-Fi 6 and Bluetooth 5.4/BLE Bluetooth Module"; "Onboard
  microphone"; "Options for 0GB / 8GB / 64GB eMMC Flash"; "Buildroot, Debian". Board size, weight, power and the list
  of supported cameras are not on that page. A reseller lists one variant at $66.90 (snippet,
  https://spotpear.com/shop/Luckfox-Aura-RV1126B-3-TOPS/Luckfox-Aura-04064.html).
- **ESP32-P4 and ESP32-S3.** Snippets: https://docs.espressif.com/projects/esp-techpedia/en/latest/esp-friends/solution-introduction/multimedia/component-description/esp-h264.html
  hardware encoder "capable of achieving 1080P@30fps" on the P4 and a software encoder at 320 x 240 at 11 fps on the
  S3; https://esp32.com/viewtopic.php?p=154181 users report "about 25-27 fps on average at 1080p" and "can't get mine
  to work above 9 fps".
- **SigmaStar boards.** Snippets: https://store.openipc.org/OpenIPC-AIO-Thinker-v1-0-p633445803 25 x 25 mm, "Board
  weight 8.8 g"; https://store.openipc.org/OpenIPC-AIO-Mario-v1-0-p633320808 "Main board weight - 9.86 g, radiator
  weight - 7.36 g, fan weight - 5.37".
- **RunCam Thumb 2.** https://www.runcam.com/runcam-thumb-2 (page read; the older shop.runcam.com address redirects
  here): "Sale price $119.99"; "Image Sensor | Sony IMX586 (48 MP)"; "4K: 3840x2160@30/30(4:3)/60(xv)/60fps; 2.7K:
  2688x1512@60(4:3)/60fps"; "1080p: 1920x1080@60/60(xv)/120fps"; "Video Format | MP4"; "Weight | 27g"; "Dimensions |
  26x27.5x55mm"; "Power Input | DC 5V only"; "Current | Max 700mA @ 5V"; "Power Type | External power"; "Wi-Fi | Not
  supported; Supports scanning the app to configure the camera"; "Stabilization | Built-in gyro (not the same as
  in-camera EIS)"; "Max microSD | 512GB". The lens field of view, aperture and bitrate are not on the page. Price
  conflict: a review title calls it "The $99 4K Action Camera" (snippet, https://oscarliang.com/runcam-thumb-2); the
  maker's page today says $119.99. The same review says the gyro data is saved to a separate file for the Gyroflow
  stabiliser and that Gyroflow lacked a lens profile for it.
- **RunCam Split 4.** Snippets only: https://oscarliang.com/runcam-split-4/ "Split 4 only weighs 10.2g";
  retailer listings "PCB Size: 29*29mm", lens module "14*14mm", "Supports GyroFlow", "US$89.99 on RunCam's shop".
  The maker's page https://www.runcam.com/runcam-split-4-v2/ returned HTTP 404, so current availability is unverified.
- **USB camera modules.** Snippets only: https://www.muchvision.com/usb-camera-module/usb2-0-camera-module/imx415-usb-camera-module-4k-compact.html
  $60.00, no minimum order, 102-degree lens, "Android 4.0 or above with UVC" (the page returned HTTP 404 when fetched,
  so the listing may have moved); https://www.sinoseen.com/sony-imx415-8mp-usb-camera-module-compact-38x38mm-with-hdr-for-drone-vision-and-aerial-photography
  38 x 38 mm; an AliExpress listing title "HD 4K USB Camera Module IMX415 100 Degree 30FPS 3840x2160 MJPEG YUY2";
  https://vxb.com/products/usb-30-uvc-camera-module-with-imx415-sensor-no-fus $287.00.

### Sensors and lenses that go with the two programmable survivors

| Camera | Works with | Sensor | Pixels, pixel pitch | Lens | Weight, size | Price | Source |
|---|---|---|---|---|---|---|---|
| Raspberry Pi Camera Module 3 | Pi Zero 2 W | Sony IMX708 | 4608 x 2592, 1.4 micrometres | 4.74 mm, F1.8, 66 x 41 degrees | 4 g, about 25 x 24 x 11.5 mm | $25 list (snippet; the one US-dollar listing found was out of stock) | https://www.raspberrypi.com/documentation/accessories/camera.html (page read): "4608 x 2592 pixels", "1.4 um x 1.4 um", "4.74 mm", "F1.8", "66 degrees", "41 degrees", "4 g" |
| Raspberry Pi Camera Module 3 Wide | Pi Zero 2 W | Sony IMX708 | same | 2.75 mm, F2.2, 102 x 67 degrees | 4 g, about 25 x 24 x 12.4 mm | $35.00, 109 in stock at TME's US site (snippet) | Same page (page read): "2.75 mm", "F2.2", "102 degrees", "67 degrees". Price: https://www.tme.com/us/en-us/details/sc1224/raspberry-pi-acessories/raspberry-pi/camera-module-3-wide/ |
| Raspberry Pi High Quality Camera | Pi Zero 2 W | Sony IMX477 | 4056 x 3040, 1.55 micrometres | interchangeable | 30.4 g without lens: too heavy for a face | not looked up | Same page (page read): "30.4 g", "38 x 38 x 18.4 mm (excluding lens)" |
| Luckfox SC3336 camera (B) | Luckfox Pico boards | SmartSens SC3336, 1/2.8 inch | 2304 x 1296; pitch not on the page | 3.95 mm, F2.0, 98.3 degrees, distortion under 33 % | not on the page | $8.99 | https://www.waveshare.com/product/luckfox/boards-modules/luckfox-pico-core1106/sc3336-3mp-camera-b.htm (page read): "$8.99", "1/2.8", "3MP (2304x1296)", "3.95mm", "F2.0", "98.3 deg", "<33%" |
| Luckfox MIS5001 camera | Luckfox Pico boards | 5 megapixel | not found | "Wide-Angle Lens", no figure found | not found | $9.99 to $12.99 | Snippet of a Waveshare category listing, https://www.waveshare.com/product/luckfox/boards-modules.htm |

Raspberry Pi Camera Module 3 video modes read straight off the sensor are "2304 x 1296p56, 2304 x 1296p30 HDR, 1536 x
864p120" (same documentation page, page read). The 2304 x 1296 mode is the full sensor area with pixels combined two
by two; that matters for the arithmetic in section (c).

### What the table means

- Only four routes clear the baseline frame size with a hardware encoder and can be bought singly: the Rockchip
  RV1106G3 boards (5 megapixels), the Rockchip RV1126B board (4K), a re-housed action camera (4K), and a USB camera
  feeding a phone (4K, phone-dependent).
- The Raspberry Pi Zero 2 W is the easiest to program and the weakest camera: it is stuck at 1080p H.264. It can
  match today's pixels per degree, not improve on them, unless the view is made narrower than the Meta glasses'.
- The microcontroller boards (ESP32 family) do not reach the baseline and should not be considered further.
- Only the programmable Linux boards (Pi, Luckfox) can do the things REQUIREMENTS.md asks for beyond video: a gyro
  log on the same clock, a recording light the software controls, and an upload straight into the app.

## (c) Lens and sensor geometry: the arithmetic

Rule (from section 0): pixels per degree at the frame centre = (focal length / effective pixel pitch) x pi / 180.
Mounting the sensor rotated for a portrait frame swaps the two field-of-view numbers and leaves pixels per degree
unchanged. Target: 17 px/deg to match the Meta glasses, 34 px/deg to double them.

### C1. If the view stays as wide as the Meta glasses, only encoder pixels help

For an ideal (distortion-free) lens that covers 87 degrees along the long side of the frame (the Meta estimate from
section 0), px/deg = (N / 2) / tan(43.5 deg) x pi / 180, where N is the number of encoded pixels on the long side and
tan(43.5 deg) = 0.949:

| Encoded long side N | Which encoder can carry it | px/deg at centre | Ball radius at the pins | Against baseline |
|---|---|---|---|---|
| 1824 (Meta today) | - | 16.8 | 5.7 px | 1.0x |
| 1920 | Pi Zero 2 W, Radxa Zero 3W, ESP32-P4 | 17.7 | 6.0 px | 1.05x |
| 2304 | RV1106G3 with the 3-megapixel SC3336 | 21.2 | 7.2 px | 1.3x |
| 3072 | RV1106G3 at its 5-megapixel limit | 28.2 | 9.6 px | 1.7x |
| 3840 | RV1126B, action camera, USB camera + phone | 35.3 | 12.0 px | 2.1x |

So with a Meta-like view, **doubling the pixels on the far ball needs a 4K encoder**. A 1080p encoder cannot improve
on today at all.

### C2. What a narrower lens buys

Narrowing the view trades framing margin for pixels at no cost in electronics. The same formula at a 60-degree long
side (tan(30 deg) = 0.577): 1920 px gives 29.0 px/deg, 2304 px gives 34.8, 3072 px gives 46.4, 3840 px gives 58.

How narrow is safe is not known, and it is the one number the existing footage can supply. Geometry gives a floor
(the agent's own arithmetic, lane width 1.05 m and eye height 1.5 m from memory): seen from above the foul line, the
lane is about 32 degrees wide at 1 m ahead of the feet and 18 degrees wide at 3 m; the vertical span from a ball 1 m
ahead (56 degrees below horizontal) to the pins (4.7 degrees below horizontal) is about 52 degrees. A perfectly still
head would therefore need about 35 degrees wide by 55 degrees tall. The head is not still. **Suggested measurement for
the next stage:** in the 32 existing clips, record how far the pin deck wanders from the frame centre between release
and pin hit. That wander plus the floor above is the minimum view, and it decides whether the standard (narrow)
lens options below are usable.

### C3. The concrete camera options

| Camera and readout | Effective pitch | Focal length | px/deg at centre | Ball radius at pins | View (portrait mount, wide x tall) | Against baseline |
|---|---|---|---|---|---|---|
| Meta glasses today (estimate, section 0) | - | - | about 17 | 4-13 px measured | about 71 x 87 deg | 1.0x |
| Pi Camera Module 3 Wide, whole sensor scaled to 1920 x 1080 | 1.4 x 2.4 = 3.36 um | 2.75 mm | 14.3 | 4.9 px | 67 x 102 deg | **0.85x: worse than today** |
| Pi Camera Module 3 Wide, centre 1920 x 1080 cut from the 2304 x 1296 mode | 2.8 um | 2.75 mm | 17.1 | 5.8 px | about 58 x 89 deg | 1.0x |
| Pi Camera Module 3 (standard), whole sensor scaled to 1920 x 1080 | 3.36 um | 4.74 mm | 24.6 | 8.4 px | 41 x 66 deg | 1.45x |
| Pi Camera Module 3 (standard), centre 1920 x 1080 cut from the 2304 x 1296 mode | 2.8 um | 4.74 mm | 29.5 | 10.0 px | about 35 x 59 deg | 1.7x |
| Luckfox SC3336, full 2304 x 1296 encoded by the RV1106G3 | about 2.44 um (see note) | 3.95 mm | 28 to 30 | 9.6 to 10.2 px | about 48 x 86 deg (estimate) | about 1.7x |
| RunCam Thumb 2, 4K (lens data not published) | - | - | about 30 (estimate) | about 10 px | very wide (estimate 150 deg diagonal) | about 1.8x, unverified |
| IMX415 USB module with the "102 degree" lens, 3840 x 2160 | - | - | 38 to 43 (estimate) | 13 to 15 px | about 100 deg on the long side | 2.2x to 2.5x, unverified |

**Every "x baseline" figure in this file inherits one unsourced number:** the Meta lens view assumed in section 0.
The predicted ball radii (5 to 12 px) all sit inside the measured 4 to 13 px band, so the measurements cannot yet
tell these options apart. Fix for the next stage: in one existing clip, measure a known length at the far end in
pixels (the lane width at the pin deck, or the spacing of two pins), convert it to px/deg, and rescale the
"against baseline" columns with that.

Worked examples:

- Camera Module 3 Wide, scaled: the sensor is 4608 pixels wide at 1.4 um; fitting it into 1920 pixels is a 2.4x
  reduction, so each encoded pixel stands for 3.36 um. 2.75 mm / 0.00336 mm = 818 pixels of focal length;
  818 x pi / 180 = 14.3 px/deg.
- Camera Module 3 Wide, centre cut: the 2304 x 1296 mode combines pixels two by two (2.8 um). Cutting the middle
  1920 x 1080 out of it without scaling keeps 2.8 um: 2.75 / 0.0028 = 982; 982 x pi / 180 = 17.1 px/deg. The view
  shrinks to 2 x atan((1920 x 0.0028 / 2) / 2.75) = 88.7 degrees by 2 x atan((1080 x 0.0028 / 2) / 2.75) = 57.6 degrees
  (ideal-lens figures; the real lens bends, so the true view is a little wider).
- Camera Module 3 standard, centre cut: 4.74 / 0.0028 = 1693; x pi / 180 = 29.5 px/deg; view 59.1 by 35.4 degrees.
- SC3336: the vendor page gives the focal length (3.95 mm) but not the pixel pitch. A 1/2.8-inch sensor (about
  6.46 mm diagonal) with 2304 x 1296 pixels (2643 on the diagonal) implies 2.44 um; the agent's memory of the
  sensor's data sheet says 2.0 um (unverified). 3.95 / 0.00244 = 1619, giving 28.3 px/deg; 3.95 / 0.0020 = 1975,
  giving 34.5 px/deg. The page's own view figure settles it: 98.3 degrees across the 2643-pixel diagonal with 33 %
  distortion means an ideal lens would have spread that view over 1321 / 0.67 = 1972 pixels of half-diagonal, a
  focal length of 1972 / tan(49.15 deg) = 1704 pixels, so 29.7 px/deg at most. That fits 2.44 um and rules out
  2.0 um; the working figure is 28 to 30 px/deg. The lens is far from ideal ("<33%" distortion on the page), so pixels per degree fall toward the
  frame edges; the far ball is normally near the centre.
- RunCam Thumb 2 and the USB module: no focal length is published, so these divide diagonal pixels by an assumed
  diagonal view (4406 px / 150 deg and 4406 px / 102 deg). That is the crude method section 0 warns against and is
  only a placeholder until a real clip is measured.

The cut-out and the scaling on the Pi are done by the camera software before the encoder (from memory, unverified:
the Pi camera library has a crop control for this).

### C4. What a larger sensor buys

Not pixels per degree: at the same view and the same encoded frame, a bigger sensor shows the ball at exactly the
same size. What it buys is light per pixel, which is what allows a short exposure (REQUIREMENTS.md section 3, item 2:
blur at release). Light per encoded pixel is proportional to (effective pitch / f-number) squared:

| Camera | Effective pitch | f-number | Relative light per encoded pixel |
|---|---|---|---|
| Pi Camera Module 3 standard, 2x2 combined | 2.8 um | F1.8 | 2.4 |
| Pi Camera Module 3 Wide, 2x2 combined | 2.8 um | F2.2 | 1.6 |
| Luckfox SC3336 | about 2.44 um | F2.0 | 1.5 |
| RunCam Thumb 2 (Sony IMX586; 0.8 um pixels combined 2x2 to 1.6 um, from memory, unverified) | 1.6 um | not published | - |

Why exposure matters here (agent's estimate, not sourced): if the head turns at 200 degrees per second during the
throw, a 1/60 s exposure smears 3.3 degrees, which is 56 px at 17 px/deg; 1/500 s smears 0.4 degrees, about 7 px.
A target of 1/250 to 1/500 s in bowling-alley light means high sensor gain and visible noise on every candidate. The
gyro log (section (e)) would give the real head rate. Manual exposure is available on the Pi camera stack and on the
Rockchip camera stack (both from memory, unverified); on a closed action camera it is whatever the vendor app offers.

## (d) Power

### D1. Energy needed per session

REQUIREMENTS.md section 4 gives two cases. Case A, button per throw: 2 hours awake of which 15 minutes recording.
Case B, record everything: 2 hours recording. Formula: energy at the cell = (idle watts x idle hours + recording watts
x recording hours) / 0.85, where 0.85 is an assumed efficiency for stepping a 3.7 V cell up to the 5 V these boards
want. Capacity in mAh = energy in Wh / 3.7 V x 1000.

| Candidate | Idle | Recording | Case A | Case B | Basis |
|---|---|---|---|---|---|
| Meta glasses (reference) | - | - | 0.59 Wh cell lasts "4 hours mixed use" | - | Section (a) |
| Luckfox RV1106G3 + SC3336 | 0.28 W | 0.8 W (assumed; plausible 0.5 to 1.2) | 0.81 Wh = **220 mAh** | 1.9 Wh = **510 mAh** | Idle from a forum report (section (b)); recording is the agent's assumption |
| Raspberry Pi Zero 2 W + Camera Module 3 | 0.6 W | 1.75 W (assumed; plausible 1.3 to 2.2) | 1.75 Wh = **475 mAh** | 4.1 Wh = **1,110 mAh** | Idle from a measured review; recording assumed equal to the "typical active" 350 mA |
| Luckfox Aura RV1126B at 4K | 1.0 W (guess) | 2.5 W (guess) | 2.8 Wh = 755 mAh | 5.9 Wh = 1,590 mAh | No figures found; guesses only |
| RunCam Thumb 2, powered throughout | 3.5 W (maker's maximum) | 3.5 W | 8.2 Wh = 2,225 mAh | 8.2 Wh = 2,225 mAh | "Max 700mA @ 5V"; real draw is probably lower |

Arithmetic for the Pi, case A: 0.6 W x 1.75 h + 1.75 W x 0.25 h = 1.49 Wh; / 0.85 = 1.75 Wh; / 3.7 V = 475 mAh.

**None of the recording-power figures is a measurement.** The first thing to do with any board is put a USB power
meter on it (about $15) while it records. Idle draw dominates case A, and both Linux boards take many seconds to
start (from memory, unverified: 15 to 25 s for the Pi), so the device has to stay awake between throws; a start from
cold before each throw is not usable.

### D2. Which cells fit where

| Cell or pack | Capacity | Size | Weight | Price | Covers | Source |
|---|---|---|---|---|---|---|
| Meta's own cell | 154 mAh (0.59 Wh) | fits a temple arm | - | not sold | - | Section (a) |
| Adafruit lithium polymer 500 mAh | 1.9 Wh | 29 x 36 x 4.75 mm | 10.5 g | $7.95, in stock | Luckfox case A twice over and case B once; Pi case A once | https://www.adafruit.com/product/1578 (page read): "$7.95", "In stock", "500mAh for a total of about 1.9 Wh", "29mm x 36mm x 4.75mm", "Weight: 10.5g", "The included protection circuitry keeps the battery voltage from going too high (over-charging) or low (over-use)" |
| PiSugar 3 for the Pi Zero (cell + charger + power board) | 1,200 mAh (4.4 Wh) | board 65 x 30 x 1.5 mm, cell 52 x 27 x 10 mm | 50 g | $39.99, 54 in stock | Pi case A 2.5 times, case B once | https://www.tindie.com/products/pisugar/pisugar-3-battery-for-raspberry-pi-zero (page read): "$39.99", "PiSugar 3 1200mAh [54 in stock]", "Output Current normal | 3A", "Soft shutdown (hardware notification software shutdown)", "USB Charging Port | type C". Size and weight: snippet of the PiSugar specification table |
| USB power bank in a pocket, 5,000 mAh class | about 18 Wh | pocket | about 100 g | about $15-20 (unsourced) | Anything, including the action camera for about 4 hours | Unsourced |

What fits inside a temple arm: the Adafruit cell works out to 1.9 Wh / 4.96 cm3 = 0.38 Wh per cubic centimetre and
0.18 Wh per gram. A thick temple arm has room for a cell of roughly 5 x 12 x 45 mm = 2.7 cm3 (from memory, unverified),
which at that density is at most 1.0 Wh (about 270 mAh), and less in practice because small cells waste more of their
volume on packaging. So:

- **Inside the temple arm:** only the RV1106 board in case A (220 mAh) is even close, and only with a custom-shaped
  cell and a custom board. No development board fits in a temple arm in the first place.
- **Behind the ear or on the strap at the back of the head:** the 500 mAh cell (10.5 g) for the Luckfox; the PiSugar
  pack (50 g) is too heavy for an ear and belongs on a head strap, a cap or a collar clip.
- **Cabled to a pocket:** the action camera (it has no battery of its own) and anything recording 4K for hours.

### D3. Charging, protection and safety beside the head

Parts:

- Buy cells that already carry a protection circuit (over-charge, over-discharge, short circuit); the Adafruit cell
  above says it does. A bare cell without one should not go on a head.
- Charger: the PiSugar 3 includes charging, protection and a soft-shutdown signal for the Pi. For the Luckfox, which
  takes 5 V in, add a small "charger plus 5 V boost" board between the cell and the board (about $15-20, from memory,
  unsourced; several hobby vendors sell one).
- Charge off the head, at no more than the cell's rated current (500 mA for the cell above: "at a rate of 500mA or
  less").

Safety rules for a prototype (the temperature figures are from a search snippet; the rest is the agent's own list):

- Surface temperature: the international safety standard for this class of equipment (IEC 62368-1) sets touch limits
  of 48 degrees Celsius for a surface worn against the body for more than 1 minute and under 8 hours, and 43 to 48
  degrees for more than 8 hours (snippet, https://www.electronics-cooling.com/2025/07/thermal-design-for-externally-worn-wearable-electronics/ ).
  A Pi Zero 2 W dissipating about 1.75 W in a small closed pod will get warm; measure the pod surface after 15
  minutes of recording before wearing it. The RV1106 at under 1 W has far more margin.
- Keep the processor's heat away from the cell: put them on opposite sides, as the Meta glasses do (board in one arm,
  battery in the other).
- Put the pouch cell in a rigid shell so it cannot be bent, pinched or punctured, and leave it room to swell.
- Never charge it while it is being worn. Stop using a cell that has puffed up.
- The lowest-risk layout keeps the cell off the head entirely: behind the neck on the strap, or in a pocket.

## (e) Extras the requirements ask for

**Gyro and accelerometer, logged in sync with the video.**

- Part: a six-axis motion sensor on a breakout board, for example the Adafruit LSM6DSOX at $11.95 (snippet,
  https://www.adafruit.com/products/4438 ). It connects by four wires (I2C) to either Linux board.
- How sync is achieved: the same computer reads both the camera and the sensor, and stamps both with the same clock.
  The Linux camera stack gives every frame a timestamp from the system's monotonic clock (from memory, unverified, for
  both the Pi and the Rockchip stacks). The logging program reads the motion sensor at 200 to 800 samples per second
  through the sensor's own buffer, stamps each sample with that same clock, and writes a side file next to each clip.
  The remaining fixed offset (a few milliseconds between "frame timestamp" and "middle of the exposure") is found once
  by tapping the glasses sharply on camera, and can be checked per clip by matching gyro rotation against image motion.
- The sensor must be rigidly fixed to the camera, not on the far end of a cable or strap, or it measures the wrong
  motion.
- On the action-camera route the camera records its own gyro file (section (b)); its format and timing are the
  vendor's and were not verified.
- On the phone-tethered route the phone's own motion sensor is in a pocket, not on the head, so it is useless for
  this. A separate head sensor would be needed, with its own clock to reconcile. This is a real cost of that route.

**Microphone.** The Luckfox Pico Ultra W and the Luckfox Aura both have a microphone on the board ("Onboard
microphone", pages read). The Pi Zero 2 W has no audio input; it needs a small digital microphone board on three pins
(about $7, from memory, unsourced). One microphone is enough to hear the pin crash (REQUIREMENTS.md section 3, item
4); the Meta baseline is stereo.

**Recording light.** A light-emitting diode with a resistor on one output pin, facing forward, switched on by the
recording program before the first frame and off after the last. For a personal prototype that is sufficient. It is
controlled by software, so it is a courtesy light and not a guarantee; a custom board can instead wire the light to
the camera's power line so the camera cannot run without it.

**Button.** A push button on one input pin starts and stops a clip. The PiSugar 3 has its own button and a
soft-shutdown line. Recording everything (case B) removes the need for a button during play, at the battery and
storage cost shown above (about 7 GB per hour at today's bitrate, REQUIREMENTS.md section 4).

Parts cost for all four extras: about $25 per unit on the Pi, about $15 on the Luckfox (microphone already there).

## (f) The tethered variant

Three different things are called "tethered". They simplify different problems.

| Variant | What is on the face | What the cable carries | Simplifies | Costs |
|---|---|---|---|---|
| F1. Power only | Camera + computer + radio (BOM 1 or 2 below) | 5 V up from a pocket or neck battery | Battery size, battery safety and heat all leave the head; hours of recording become possible | A thin cable down the back of the neck. Everything else unchanged |
| F2. Self-contained camera, pocket power | An action camera (27 g) | 5 V up from a pocket power bank | No electronics to build at all; 4K today | No radio and no program: clips reach the app by moving a memory card or plugging a cable into the phone. Fails "clips land without opening another app" |
| F3. USB camera to the phone | A USB camera module (board about 38 x 38 mm) | Video down to the phone, power up from it | The phone is the encoder, the storage, the battery, the screen and the uplink. The app's Android build could own the camera and upload by signed URL with no pairing step at all | See below |

Costs of F3, the phone as the computer:

- A cable runs from the head to the phone during a bowling swing. It must be routed behind the neck and down the
  back, and the phone must sit in a back pocket or on a belt. A snag pulls the glasses off.
- It needs an Android phone that accepts USB cameras, and a native plugin in the app's Android build to read the
  camera and drive the phone's video encoder (from memory, unverified: open-source libraries exist for this; iPhones
  do not offer the same access to third-party apps).
- The module sends 4K as motion JPEG ("3840x2160 MJPEG YUY2" in one listing title), which the phone must decode and
  re-encode at 30 fps. Whether a given phone keeps up without dropping frames has to be tested; it is the main
  technical risk.
- No head motion sensor (section (e)) and limited exposure control.
- The phone's battery drains faster, and the phone cannot be used for anything else during play.

A fourth idea, a bare camera on the frame with its ribbon cable running to a computer in the pocket, does not work:
the camera ribbon interface is only reliable over a few tens of centimetres (from memory, unverified). The computer
has to sit within about 30 cm of the camera: on the temple, behind the ear, at the back of the head, or under a
cap brim.

Getting 1 GB off an untethered device "in a few minutes": at a realistic 30 megabits per second over 2.4 GHz Wi-Fi
(agent's estimate, unsourced), 1 GB (8,000 megabits) takes about 4.5 minutes. That is borderline for the Pi Zero
2 W, whose radio is the older 2.4 GHz b/g/n kind; the Luckfox boards have newer Wi-Fi 6 radios, and the Aura adds the
5 GHz band. Encoding HEVC at a lower bitrate than the Meta glasses' 15 megabits per second would shrink the problem
directly, and the Rockchip boards can do that; the Pi cannot (H.264 only).

## Bills of materials

Prices are for one unit, accessed 2026-11-14. "(est.)" marks a small part whose price was not looked up; those are in
the Unsourced list. Sources and quotes for the priced parts are in sections (b), (d) and (e).

### BOM 1. Development-board prototype on the Raspberry Pi Zero 2 W ("easiest to program")

| Part | Vendor | Unit price | URL |
|---|---|---|---|
| Raspberry Pi Zero 2 W | Raspberry Pi resellers | $15 | https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/ |
| Raspberry Pi Camera Module 3 Wide (or the standard lens at $25 list, see section (c)) | TME (US site) | $35.00 | https://www.tme.com/us/en-us/details/sc1224/raspberry-pi-acessories/raspberry-pi/camera-module-3-wide/ |
| Camera ribbon cable for the Pi Zero's small connector | any Pi reseller | $3 (est.) | - |
| PiSugar 3 battery board, 1,200 mAh | Tindie (PiSugar) | $39.99 | https://www.tindie.com/products/pisugar/pisugar-3-battery-for-raspberry-pi-zero |
| Motion sensor board, LSM6DSOX | Adafruit | $11.95 | https://www.adafruit.com/products/4438 |
| Digital microphone board | hobby vendor | $7 (est.) | - |
| Memory card, 32 GB | any | $8 (est.) | - |
| Light, resistor, push button, wire | any | $5 (est.) | - |
| Glasses frame, printed mounts, head strap | print service | $30 (est.) | - |
| **Total** | | **about $155** | |

- Recording: 1920 x 1080 (worn as 1080 x 1920 portrait), 30 fps, H.264, 8-bit, mono sound. With the Wide lens cut to
  the sensor centre: 17 px/deg, the same as today, view about 58 x 89 degrees. With the standard lens: 25 to 30 px/deg
  (1.45x to 1.7x today) but a view only 35 to 41 degrees wide.
- Battery life (estimate from section (d), unmeasured): 1,200 mAh covers about 2.5 sessions of the button-per-throw
  kind, or about 2 hours of continuous recording.
- Weight on the face: camera 4 g, sensor and microphone boards about 3 g, frame about 25 g: about 32 g, if the Pi
  (about 10 g) and the battery board (50 g) ride on a strap at the back of the head, within a 30 cm ribbon cable of
  the camera. All on the frame it would be about 95 g, which is too heavy.
- Main risk: **pixels.** The 1080p encoder ceiling means this build can equal the Meta glasses on the far ball but not
  beat them without narrowing the view. Second risk: 0.6 W idle and a slow start mean it must stay on all session.

### BOM 2. Development-board prototype on the Luckfox Pico Ultra W, Rockchip RV1106G3 ("most pixels per watt")

| Part | Vendor | Unit price | URL |
|---|---|---|---|
| Luckfox Pico Ultra W (RV1106G3, 256 MB memory, 8 GB storage, Wi-Fi 6 and Bluetooth, microphone on board) | Waveshare | $36.99 to $81.99 across variants; the page does not price each variant. Budget $45 to $82 | https://www.waveshare.com/Luckfox-Pico-Ultra.htm |
| SC3336 3-megapixel camera (B) | Waveshare | $8.99 | https://www.waveshare.com/product/luckfox/boards-modules/luckfox-pico-core1106/sc3336-3mp-camera-b.htm |
| Lithium polymer cell, 500 mAh, with protection circuit | Adafruit | $7.95 | https://www.adafruit.com/product/1578 |
| Charger plus 5 V boost board | hobby vendor | $18 (est.) | - |
| Motion sensor board, LSM6DSOX | Adafruit | $11.95 | https://www.adafruit.com/products/4438 |
| Light, resistor, push button, wire | any | $5 (est.) | - |
| Glasses frame, printed mounts, strap | print service | $30 (est.) | - |
| Shipping from China and US import duty on the Waveshare parts | - | $20 to $40 (est.) | - |
| **Total** | | **about $150 to $200** | |

- Recording: 2304 x 1296 (worn portrait), 30 fps, HEVC, mono sound from the on-board microphone. 28 to 30 px/deg at
  the centre (about 1.7x today), view about 48 x 86 degrees with strong lens bending toward the edges. The encoder
  has headroom to 5 megapixels if a 5-megapixel camera (the $9.99 to $12.99 MIS5001) proves to have a suitable lens.
- Battery life (estimate, unmeasured): 500 mAh covers two button-per-throw sessions or about 2 hours of continuous
  recording.
- Weight on the face (agent's estimate; only the cell's 10.5 g is sourced): camera about 2 g, motion sensor board
  about 2 g, frame about 25 g: about 30 g on the face, with the board (about 15 to 20 g; its size is not on the page
  read, about 50 x 50 mm from memory, unverified) and the cell on a strap behind the head, within a 30 cm ribbon cable
  of the camera. With the board as a pod on one temple arm and the cell on the other: about 55 to 60 g.
- Main risk: **software.** The vendor's Linux and its C media library are a much steeper climb than the Pi for a
  Python engineer, the community is small, and the power figures are forum reports. Second risk: the lens bending has
  to be removed in the tracker before measuring the ball.
- Upgrade path on the same vendor's software: the Luckfox Aura (Rockchip RV1126B, $50.99 to $145.99) encodes 4K at
  30 fps, which is the 2x-baseline row of table C1. Its size and power were not found, so it is not costed as a BOM.

### BOM 3. Re-housed action camera, RunCam Thumb 2, powered from a pocket ("best pixels this month, no integration")

| Part | Vendor | Unit price | URL |
|---|---|---|---|
| RunCam Thumb 2 (4K, 27 g, built-in gyro, no battery) | RunCam | $119.99 | https://www.runcam.com/runcam-thumb-2 |
| USB power bank, about 5,000 mAh | any | $18 (est.) | - |
| USB-C cable, 1 m | any | $8 (est.) | - |
| Memory card, 64 GB | any | $10 (est.) | - |
| USB-C card reader for the phone | any | $10 (est.) | - |
| Clip mount for a temple arm or a cap brim | print service | $15 (est.) | - |
| **Total** | | **about $180** | |

- Recording: 3840 x 2160 at 30 or 60 fps, or the 4:3 "4K" mode at 30 fps; about 30 px/deg (estimate, about 1.8x
  today; the lens data is not published, so measure it on the first clip). Gyro logged by the camera to a separate
  file. Bitrate is high (a snippet gives 100 megabits per second at 4K 60 fps), so 15 minutes may be 5 to 11 GB
  instead of today's 1 GB.
- Battery life: about 4 hours of continuous recording from an 18 Wh power bank at the maker's maximum draw of 3.5 W.
- Weight on the face: 27 g hung on one temple arm plus the cable. Lopsided; a cap brim is the better mount.
- Main risk: **it does not link to the app.** No radio and no programmable start or stop: clips move by memory card.
  It answers "do more pixels fix the far end?" quickly and cheaply, and nothing else. How it behaves when power is
  applied (start recording or wait) was not verified.
- A smaller relative, the RunCam Split 4 (14 x 14 mm lens on a cable, 29 x 29 mm board, 10.2 g, $89.99 in a snippet),
  would sit much better on a frame, but its maker's page returned "not found" today.

For comparison, the phone-tethered variant F3 costs about $85 in parts (a $60 4K USB camera module from a snippet
whose page has since moved, a cable and a mount) plus the Android plugin work.

### BOM 4. Custom-board level: a carrier board for the Luckfox Core1106 module

This is the smallest step that counts as "custom": one small board that replaces the loose charger, sensor, light
and button boards of BOM 2 and carries a solder-on computer module.

| Part | Vendor | Unit price | URL |
|---|---|---|---|
| Luckfox Core1106 module (RV1106G3, 30 x 30 mm, 112 solder pads, Wi-Fi 6 and Bluetooth version, 8 GB storage) | Waveshare / Luckfox | $36.99 (Luckfox lists $36.99 to $45.99) | https://www.waveshare.com/core1106.htm , https://www.luckfox.com/Core1106 (snippets: "30 x 30 (mm)", "112 Pin castellated holes", "2.4 GHz WIFI 6 (optional)") |
| Custom carrier board, four layers, five pieces made and assembled: charger, power supplies, motion sensor, microphone, light, button, battery and camera connectors | JLCPCB | Assembly set-up fee $8.18 (economy) or $25.56 / $51.12 (standard, one / two sides), $0.0016 per solder joint, parts extra. Agent's estimate for five boards with parts and shipping: $100 to $250, so $20 to $50 a board | https://jlcpcb.com/solutions/pcb-prototype-assembly (snippet); the price is quote-by-upload, no public fixed figure |
| SC3336 camera on a longer flexible cable | Waveshare | $8.99 | as BOM 2 |
| Lithium polymer cell with protection, 250 to 500 mAh | Adafruit or similar | $8 | https://www.adafruit.com/product/1578 |
| Printed temple pod and frame | print service | $40 (est.) | - |
| **Parts per unit** | | **about $115 to $145** | |
| Board design | learn the free KiCad tool (agent's estimate: three to six weekends for a first board), or hire a designer (agent's estimate, unsourced: $500 to $2,000 for a carrier this simple) | | |

- Recording: as BOM 2 (2304 x 1296 at 30 fps HEVC, up to 5 megapixels with another sensor).
- Battery life: as BOM 2; a 250 mAh cell covers one button-per-throw session.
- Weight on the face (agent's estimate, unsourced): module and carrier about 10 g, camera 2 g, cell 6 to 10 g, frame
  and pod about 30 g: 50 to 55 g, in the range of the Meta glasses (49 to 52 g), with the cell on the opposite arm.
- Main risk: **it is still a pod, not glasses.** A 30 mm square module is wider than a temple arm. Electronics that
  disappear into a frame mean soldering the processor chip itself onto a strip about 10 mm wide with a flexible
  section through the hinge. That is professional hardware design: the agent's unsourced estimate is $3,000 to
  $10,000 in design fees and at least two rounds of boards, which is outside the $1,000 budget unless the skill is
  learned over months. Second risk: a first board that does not work; budget a second round ($100 to $250).
- Radio rules: the module arrives with its radio already on it. Whether that radio carries a US approval was not
  checked. For one to three units built for personal use this is unlikely to matter (from memory, unverified: US rules
  exempt a handful of home-built devices that are not sold), but it would matter for anything sold.

### Cost both ways (REQUIREMENTS.md section 6)

| Plan | One unit | Three units | Whole effort (three units where it makes sense, tools, spares, one wrong purchase) |
|---|---|---|---|
| BOM 1, Pi Zero 2 W | $155 | $465 | about $650 |
| BOM 2, Luckfox RV1106 | $150 to $200 | $450 to $600 | about $750 |
| BOM 3, action camera | $180 | not needed; one is enough to answer the question | about $200 |
| BOM 4, custom carrier | $115 to $145 in parts | $350 to $450 | $500 to $700 if the design is learned; $1,000 to $2,700 if it is bought |
| One of each of BOM 1, 2 and 3 to compare | $485 to $535 | - | about $700 with tools |

Tools assumed in "whole effort" (all est., unsourced): soldering iron $40, USB power meter $15, multimeter $20,
printed parts $25 per design round.

### Skills: bought or learned

| Skill | Plan |
|---|---|
| Soldering wires and header pins | Learned in an evening |
| Camera, encoder and upload program on the Pi | Learned; it is Python on ordinary Linux, the builder's home ground |
| Camera and encoder program on a Rockchip board | Learned, and the largest single cost in time: a vendor build system, C interfaces, cross-compiling |
| Mounts and pods | Bought from a print service; the shapes can be written as code in a programmatic design tool, which suits a programmer better than a drawing program (from memory, unverified) |
| Battery pack | Bought: a protected cell plus a ready-made charger board; nothing designed |
| Radio approval | Avoided by using boards and modules that arrive with the radio on them |
| Carrier board (BOM 4) | Learned or bought; either is realistic |
| Glasses-shaped board with the chip soldered on | Bought only |

### Order that fits $1,000 (agent's suggestion for the next stage to weigh)

1. BOM 3 first, one unit, about $180: it tests the claim in REQUIREMENTS.md that more pixels at the far end is the
   most useful improvement, with real 4K footage and a gyro file, before anything is built.
2. BOM 2 as the device that links into the app, with BOM 1 as the fallback if the Rockchip software costs too much
   time. Both together are about $350.
3. BOM 4 only after a development-board unit has survived real sessions.

## Unsourced

Everything here was stated above from memory or as the agent's estimate, or was asked for and not found. None of it
should be treated as fact.

- **Meta glasses:** the image sensor's maker and model; the lens field of view (about 100 degrees diagonal is the
  figure section 0 assumed); the Gen 2 battery capacity; heat limits and overheating behaviour; the later 3-minute
  clip limit. No teardown of the camera module and no regulatory filing was opened. The task asked for these and
  the searches run did not find them.
- **Chip families not researched within the budget:** Ingenic, Novatek and Allwinner camera chips. From memory,
  unverified: Ingenic T31-class chips are 2 to 3 megapixel H.264/H.265 parts with a community firmware; Allwinner
  V851/V853 are 4 to 5 megapixel parts with a few hobby boards; Novatek parts sit inside dash cameras and action
  cameras and are not sold with a public software kit. The RunCam cameras are the practical way to buy that class.
- **SigmaStar SSC338Q:** maximum encoded resolution and frame rate, power, price.
- **Power while recording** for every board (Pi Zero 2 W, Luckfox Pico Ultra W, Luckfox Aura). Idle figures are
  sourced; recording figures are assumptions. Luckfox Aura idle is also a guess.
- **Sizes and weights:** Raspberry Pi Zero 2 W weight (about 10 g); Luckfox Pico Ultra W size (about 50 x 50 mm) and
  weight; Luckfox Aura size and weight; SC3336 camera size and weight; inner space of a temple arm; BOM 4 weights.
- **SC3336 pixel pitch** (2.0 um from memory against 2.44 um implied by the stated sensor size; the page's view and distortion figures favour 2.44 um).
- **RunCam Thumb 2:** lens field of view, aperture, codec, bitrate at 4K 30 fps, gyro file format, what it does when
  power is applied, the pixel dimensions of its 4:3 mode. **RunCam Split 4:** current price and availability.
- **USB camera route:** that a given Android phone can take 4K motion JPEG at 30 fps and re-encode it; the open-source
  Android libraries for USB cameras; iPhone behaviour. The $60 listing's page returned "not found" when fetched.
- **Software capabilities from memory:** the Pi camera library's centre-crop control and manual exposure; manual
  exposure on the Rockchip camera stack; frame timestamps on the system monotonic clock on both; Pi start-up time;
  that the ESP32-P4 has no radio of its own.
- **Camera ribbon cable length limit** (a few tens of centimetres).
- **Wi-Fi throughput** of about 30 megabits per second used for the transfer estimate.
- **Bowling dimensions** used in section 0 (ball 8.5 to 8.6 inches, 60 feet to the head pin, lane 1.05 m wide) and
  the 200 degrees per second head rate.
- **Small-part prices** marked (est.): camera cable, microphone board, memory cards, charger/boost board, power bank,
  cables, card reader, printed parts, tools. **Shipping and import duty** on parts from China.
- **Raspberry Pi Camera Module 3 standard at $25:** the only US-dollar listing found was out of stock; US shop
  SparkFun listed a Wide variant at $45.05, also out of stock (snippets).
- **Custom board:** five-board assembled cost at JLCPCB (quote only; the figure is an estimate built from the public
  set-up fees); freelance design fees; the US rule on home-built radio devices; the Core1106 radio's US approval.
- **Compute Module 4 and Compute Module 5** encoder limits (inferred from the Pi 4 and Pi 5, not sourced).

## Source ledger

Counts: 23 web searches run; 16 page fetches attempted, 10 pages read, 6 failed. Date for all: 2026-11-14.

Pages read (the text came through the fetch tool's summariser, which was asked for verbatim lines):

1. https://www.raspberrypi.com/documentation/accessories/camera.html - camera sensor, pitch, focal length, view, weight.
2. https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/ - price, encoder limit, radios, size.
3. https://www.luckfox.com/Luckfox-Aura - RV1126B board: price range, 4K encode, radios, microphone.
4. https://www.waveshare.com/Luckfox-Pico-Ultra.htm - RV1106G3 board: price range, memory, radio, microphone.
5. https://www.waveshare.com/product/luckfox/boards-modules/luckfox-pico-core1106/sc3336-3mp-camera-b.htm - camera price and lens.
6. https://vrarwiki.com/wiki/Ray-Ban_Meta - Gen 1 specification (a wiki, not a primary source).
7. https://about.fb.com/news/2025/09/ray-ban-meta-gen-2-better-battery-life-video-capture/ - Gen 2, the maker's announcement.
8. https://www.tindie.com/products/pisugar/pisugar-3-battery-for-raspberry-pi-zero - battery board price and stock.
9. https://www.adafruit.com/product/1578 - 500 mAh cell price, size, weight, protection.
10. https://www.runcam.com/runcam-thumb-2 - action camera price and specification.

Fetches that failed: https://shop.runcam.com/runcam-thumb-2 and https://shop.runcam.com/runcam-split-4-v2/ (redirect
to www.runcam.com; the first was then read, the second returned HTTP 404);
https://www.cnx-software.com/2021/12/09/raspberry-pi-zero-2-w-power-consumption/ and
https://www.cnx-software.com/2025/01/21/solderable-rockchip-rv1106-system-on-module-features-112-castellated-pins-offers-wifi-6-and-bluetooth-5-2-connectivity/
(HTTP 403); https://www.muchvision.com/usb-camera-module/usb2-0-camera-module/imx415-usb-camera-module-4k-compact.html
(HTTP 404).

Everything else cited in this file is a search-result snippet, as marked where it is used. Snippets were produced by
the search tool's own summary of the result pages, so a quoted phrase from a snippet is one step further from the
page than a quote from a page read.

## Status

**PARTIAL.** Every section (a) to (f) and all four bills of materials are written, and the tool budget (about 50
calls) was reached. What is missing against the brief: (1) no teardown or regulatory filing was read, so the Meta
glasses' sensor model, lens view and heat limits are unsourced; (2) the Ingenic, Novatek and Allwinner chip families
were not researched; (3) no measurement of power while recording was found for any board, so every battery-life figure
rests on an assumed recording power; (4) several small-part prices are estimates.

Headline: a 1080p-class board (Raspberry Pi Zero 2 W, about $155 a unit) can only equal the Meta glasses on the far
ball; a Rockchip RV1106G3 board with a $9 camera (about $150 to $200 a unit) should reach about 1.7x the pixels per
degree (an estimate) at a quarter to a half of the Pi's idle power but with harder software; a $120 action camera gives 4K and a gyro log now
but cannot link to the app. No development board fits inside a temple arm, and electronics that do are a
professional design job outside the $1,000 budget.

## Corrections made after review (2026-11-14)

- Section 0 no longer claims the Meta lens view is sourced in section (a); it is an assumption.
- The Luckfox SC3336 estimate was narrowed from "28 to 35 px/deg, 1.7x to 2x" to "28 to 30 px/deg, about 1.7x" after
  checking the 2.0 um pixel pitch against the vendor page's own view and distortion figures.
- The status headline said the RV1106 idles at "a third" of the Pi; the sourced figures (0.15 to 0.3 W against
  0.6 W) give a quarter to a half.
- BOM 2 now carries a labelled weight estimate.
