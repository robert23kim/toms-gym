# Lane: linking a head-worn camera to the app

Written 2026-11-14. Question: what is the simplest reliable way for a clip to get from a head-worn camera into the
owner's account in the app with a phone-only setup, and what has to be built on the app side?

Conventions used in this file:

- "The app" is the web app in this repository (React + Vite frontend, Flask backend on Cloud Run, Capacitor 7 Android
  wrapper). "The device" is the prototype camera glasses.
- Every outside fact carries its URL, the access date 2026-11-14, a short quote, and whether I read the page itself
  ("page read") or only a search-result summary ("snippet only"). Facts I could not source are under "Unsourced" at
  the end and are labelled "(from memory, unverified)" where they appear.
- Abbreviations, spelled out once: BLE = Bluetooth Low Energy; AP = access point (the device acts as a Wi-Fi router);
  UVC = USB Video Class (the standard that makes a camera look like a webcam); GCS = Google Cloud Storage;
  IMU = inertial measurement unit (gyroscope + accelerometer); SDK = software development kit;
  POV = point of view (first-person video); APK = Android application package; MCU = microcontroller;
  RTMP = Real-Time Messaging Protocol (a live-streaming protocol); JWT = JSON Web Token.
- Mbps = megabits per second. MB = megabytes (10^6 bytes), MiB = mebibytes (2^20 bytes).

## 1. What the repository has today (read 2026-11-14, branch `feat/100-club`)

### 1.1 The upload path

All in `backend/toms_gym/routes/upload_routes.py` unless noted.

| Route | What it does | Limits and notes |
|---|---|---|
| `POST /upload` (line 211) | Multipart upload through Flask, creates a lifting `Attempt` | Dies at Cloud Run's 32 MiB request cap with an HTML 413 and no server log. Kept for small files. |
| `POST /upload/signed-url` (line 503) | Mints a V4 signed PUT URL for one object `videos/<timestamp>_<filename>` | URL lives 15 minutes; `Content-Type` on the PUT must match what was signed; extension must be one of `mov, mp4, avi, mkv` (`storage.py` line 64). |
| `POST /upload/resumable-url` (line 539) | Starts a GCS resumable upload session server-side and returns the `session_uri` | The session is scoped to the caller's `Origin` header for browser cross-origin rules; a client that sends no `Origin` gets `*`. Chunks of 8 MiB in the browser client (`frontend/src/lib/resumableUpload.ts`, must be a multiple of 256 KiB). |
| `POST /upload/composite/sign` and `/upload/composite/complete` (lines 654, 725) | N signed part URLs (60-minute life), then a GCS compose into one object | Browser sends 16 MiB parts four at a time. |
| `POST /upload/finalize` (line 584) | Checks the object exists in GCS, resolves the user, creates the `Attempt` | Takes `user_id` or `email` in the JSON body. |
| `POST /bowling/upload` (`bowling_routes.py` line 32) | Multipart upload, creates `Attempt` + `BowlingResult`, calls `enqueue_analysis_job('bowling', ...)` | **Multipart only, so it is under the 32 MiB cap.** The bowling page (`frontend/src/pages/BowlingUpload.tsx` line 55) still uses it. There is no signed-URL finalize that creates a `BowlingResult`. |

Three facts that matter for a device:

1. **None of the upload routes authenticates the caller.** There is no `require_auth` decorator, no rate limit and no
   token check on `/upload/signed-url`, `/upload/resumable-url`, `/upload/finalize` or `/bowling/upload`. The account a
   clip lands in is whatever `user_id` or `email` the caller writes in the body (`_resolve_user_id`, line 78: `user_id`
   wins, then `email` is looked up or a guest user is created, and with neither the clip goes to user `'1'`).
   So today a device could upload with nothing more than the owner's email. That is the cheapest possible demo and
   also means "how a device proves which account it uploads to" has no existing answer: it has to be built.
2. **The signed-URL path already does what a device needs.** A device (or a phone on its behalf) can call
   `/upload/resumable-url`, PUT bytes straight to GCS and call `/upload/finalize`. No backend change is needed to move
   bytes. Measured in this repo's notes: a real 372 MB phone HEVC video went through the resumable path in about 80
   chunks with a simulated drop and resume (memory note `upload_32mb_limit.md`).
3. **The measured clips straddle the 32 MiB cap.** Mean clip 33.4 MB (31.9 MiB), largest 50.8 MB (48.4 MiB)
   (`REQUIREMENTS.md` section 2). So the multipart bowling route would reject the larger clips; a device path must use
   the signed or resumable routes.

### 1.2 Identity

- Optional sign-in. A user can be only an email address; the browser keeps `userId` and `userEmail` in localStorage,
  and the Android app mirrors both to native storage through `@capacitor/preferences` (`frontend/src/lib/identity.ts`).
- Password users get a JWT: access token 7 days, refresh token 90 days (`auth_routes.py` lines 36-37).
- Magic-link sign-in exists: `POST /auth/magic-link`, `GET /auth/magic/<token>`, single-use, stored hashed in a
  `MagicLinkToken` table (`auth_routes.py` line 519 onward). The same hashed-token-in-a-table pattern is the natural
  model for a device token.
- There is one shared admin secret (`X-Admin-Token`) for ticket and leaderboard-preview routes. There is **no device
  table, no per-device token and no API-key concept** anywhere in `backend/toms_gym` (searched for `Device`,
  `device_token`, `api_key`: no hits).

### 1.3 The Android app

- Capacitor 7 project in `frontend/android` (`appId com.tomsgym.app`, targetSdk 35), debug APK only, no release
  keystore, distributed by a short link to a signed GCS URL (`docs/reference/android-app.md`).
- Installed Capacitor plugins (`frontend/package.json`): `@capacitor/app`, `core`, `preferences`, `splash-screen`,
  `status-bar`. **No Bluetooth, Wi-Fi, USB, filesystem, native HTTP or background-task plugin.**
- Manifest permissions: `INTERNET`, `CAMERA`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`. No Bluetooth, location,
  nearby-devices, Wi-Fi-state or foreground-service permission.
- **There is no iOS project** (`frontend/ios` does not exist). On an iPhone the app is the website in Safari.
- The newest APK is "proven on the emulator only; not yet installed on a phone" (`android-app.md`, 2026-11-14 note),
  and the bundled web assets go stale with every frontend deploy until the APK is rebuilt.

### 1.4 Upload limits and telemetry

`docs/reference/easy-upload-flows.md` (the file the brief pointed at) covers camera-first capture only and has no
limits or telemetry; those live in the code and in the memory note:

- Cloud Run rejects request bodies over 32 MiB before Flask sees them; hence direct-to-GCS.
- Browser routing in `frontend/src/lib/resumableUpload.ts`: compress at 24 MiB and above (never on iOS, never above
  200 MiB), single PUT under 32 MiB, parallel composite at 32 MiB and above with the serial resumable path as fallback.
  **A device clip must not go through the browser compressor**: it re-encodes to 720p and drops audio, which would
  throw away the far-end pixels that `REQUIREMENTS.md` section 3 ranks first.
- Telemetry: `POST /log-error` logs a `FRONTEND_ERROR` line with `build` and `platform=web|capacitor`; a per-stage
  upload journey is kept in localStorage and reported on the next boot as `action=upload-died`
  (`frontend/src/lib/telemetry.ts`, `uploadJourney.ts`). The payload cap is 2 KB. A device uploader can reuse this
  endpoint with `platform=device` for its own failure reports.

### 1.5 How glasses clips are processed today, and what "appears in the app" can honestly mean

- Today's route (`REQUIREMENTS.md` section 2): glasses, then the vendor's phone app, then Google Drive, then a laptop,
  then research scripts. Nothing reaches the app.
- The first-person tracker is **research code**: `docs/research/2026-11-09-glasses-pov-session/track_v3.py`,
  `auto_cuts.py`, `make_session_video.py` and shell runners, driven by a workflow and a rule-based judge
  (`RULES.md`). It needs a per-clip cut window and release frame (the auto cutter got 4 right, 6 wrong and 15 with no
  answer on untouched clips), a SAM 2 pass, up to two judge-driven reruns, and it ended with a line on 20 of 31 throws.
  It reads local files, writes local JSON and renders one session video. It is not in the analysis engine, not behind
  an endpoint, and has no database table.
- The app's existing bowling feature is a **third-person** analyzer: `POST /bowling/upload` creates a `BowlingResult`
  and queues the Cloud Run engine, which expects a camera behind the bowler. Sending a first-person clip down that
  route would run the wrong analyzer on it.

So for a first prototype "appears in the app" should be defined as three things the product can actually do:
**(a)** the clip is stored in the app's bucket under the owner's account, **(b)** it is listed and playable on a
session page in the app, grouped by session with its capture time, and **(c)** it is exported in a shape the research
scripts read (one folder per session, original bytes, a manifest with timestamps and the motion log). A ball line on
the lane appearing in the app is a second project: productising the tracker (a job type in the engine, a results
table, a rerun policy that works without a human judge). This lane sizes (a) to (c) and notes the hooks for the rest.

### 1.6 The session envelope restated as link speeds

From `REQUIREMENTS.md` section 4: 32 clips, 1.07 GB (8,560 megabits), over a 65-minute span, mean clip 33.4 MB
(267 megabits). Derived numbers used throughout this file (arithmetic, not measurements):

| Link speed | Whole session at the end (1.07 GB) | One mean clip (33.4 MB) | One hour of continuous recording (7 GB) |
|---|---|---|---|
| 0.3 Mbps (BLE, typical iPhone) | 7.9 hours | 14.8 minutes | 52 hours |
| 0.7 Mbps (BLE, good Android) | 3.4 hours | 6.4 minutes | 22 hours |
| 1.2 Mbps (BLE, best case measured) | 2.0 hours | 3.7 minutes | 13 hours |
| 5 Mbps (poor Wi-Fi or weak cellular uplink) | 28.5 minutes | 53 seconds | 3.1 hours |
| 10 Mbps | 14.3 minutes | 27 seconds | 93 minutes |
| 20 Mbps | 7.1 minutes | 13 seconds | 47 minutes |
| 40 Mbps | 3.6 minutes | 7 seconds | 23 minutes |
| 100 Mbps | 1.4 minutes | 3 seconds | 9 minutes |

**The number that decides the architecture:** spread over the session, the clips are produced at an average of
8,560 megabits / 3,900 seconds = **2.2 Mbps**. Any link that sustains more than about 3 Mbps can send each clip in the
gap before the next throw (mean gap about 2 minutes) and finish the session with nothing left to transfer. Any link
slower than 2.2 Mbps falls further behind with every throw. Wi-Fi clears that bar by a wide margin; Bluetooth Low
Energy does not.

## 2. Five transfer architectures

Source tags like [S15] point at the source table in section 6. Speeds marked "derived" come from the table in 1.6.

### 2.0 Summary table

| | 1. Device AP to phone app, BLE control | 2. Device straight to cloud | 3. BLE only | 4. Tethered USB camera | 5. Vendor glasses kit |
|---|---|---|---|---|---|
| Device must | Run a BLE service, a Wi-Fi access point and a file server; store clips | Join a Wi-Fi network, hold a device token, do HTTPS uploads with resume; store clips | Run a BLE service and push files through it | Be a UVC camera on a cable; nothing else | Be the vendor's glasses |
| Phone must | Native app: BLE, join the device's Wi-Fi, download, then upload | Share a hotspot; a web page for the one-time pairing | Native app or Chrome on Android holding a BLE link for hours | Native Android app that records from the USB camera, then uploads | Native app built on the vendor SDK |
| Backend must | Session and clip records (bytes use the existing resumable route) | Device table, pairing, device-authenticated upload route, session and clip records | Same as 1 | Same as 1 | Same as 1, or a webhook that takes the vendor's upload |
| Session transfer (1.07 GB) | Hop 1: 1.4 to 7 min at 20-100 Mbps; hop 2 (phone to cloud): 7 to 28 min at 5-20 Mbps, can wait for home Wi-Fi | No end-of-session transfer: each clip goes in 13 to 53 s at 5-20 Mbps, between throws | 2 to 8 hours | No device hop; phone to cloud 7 to 28 min | Meta kit: live stream, no file. Mentra kit: glasses upload each recording over Wi-Fi |
| Android via Capacitor | BLE plugin exists [S6]; Wi-Fi join plugins exist [S8][S9]; background transfer needs custom native code | Nothing native needed | BLE plugin exists [S6] | No Capacitor plugin found; custom plugin over an Android UVC library [S11] | Custom native plugin wrapping the vendor SDK |
| iPhone | Needs a native iOS app (none exists in the repo) | Works: hotspot plus Safari | Needs a native iOS app; 0.3-0.5 Mbps [S7] | Not possible: iPhone has no UVC support [S12] | Vendor SDKs have iOS support [S1][S4]; needs a native iOS app |
| Plain mobile browser | No | **Yes** (pairing page only) | Chrome on Android only; not iOS Safari [S10] | No | No |
| Meets the camera baseline? | Depends on the device | Depends on the device | Depends on the device | Depends on the camera module | Meta kit no (720x1280 ceiling [S2][S3]); Mentra Live to be measured |
| New native phone code | 1-2 weeks Android, plus an iOS project | None | 1 week Android | 1-2 weeks Android | 1-2 weeks per platform |
| Verdict | Long-term product shape | **First prototype** | Control channel only | Best rig for evaluating camera modules | Shortcut if the hardware lane picks Mentra Live |

### 2.1 Architecture 1: device to phone app over the device's own Wi-Fi, BLE for control; the phone uploads

This is the pattern the Meta glasses use. What I could source about Meta's version is from low-authority support
sites, not Meta: "The initial transfer handshake occurs over Bluetooth Low Energy (BLE) before switching to Wi-Fi",
and the phone is asked to join a temporary network named like "Meta_Glasses_XXXX" [S13, snippet only].

**Device must:** advertise over BLE; expose a small BLE service (status, battery, clip list, set the clock, start and
stop recording, "turn on your access point"); bring up a Wi-Fi access point on request with a random passphrase that
it hands to the phone over the encrypted BLE link; serve clips over HTTP with byte-range support so a broken download
resumes; delete a clip only after the phone confirms it.

**Phone must:** scan and connect over BLE; join the device's network; download every clip to phone storage; then
upload each to GCS through the app's existing resumable route; do all of this while the screen is off (on Android, a
foreground service).

**Backend must:** nothing new to move bytes. It needs the session and clip records in section 5.

**Transfer time (derived):** hop 1 depends on the device's radio. A microcontroller access point is the slow case:
Espressif's own figure is "20 MBit/s TCP throughput", and forum measurements on the ESP32-S3 are far lower (about
4.5 Mbps as server) [S18, snippet only], so 7 to 32 minutes for the session. A Raspberry Pi Zero 2 W measured about
33.5 Mbps [S22, snippet only]: about 4.3 minutes. An Android-class glasses chip with 5 GHz Wi-Fi should do the
session in under 2 minutes (from memory, unverified). Hop 2, phone to cloud, is the phone's uplink: 7 to 28 minutes at
5 to 20 Mbps, and it can be deferred until the phone is on home Wi-Fi.

**Android through Capacitor:**

- BLE: `@capacitor-community/bluetooth-le`, 7.x line for Capacitor 7 ("7.0.0 (2025-01-25) BREAKING CHANGES update
  plugin to capacitor 7") [S6, snippet only]. No custom code needed for control.
- Joining the device's Wi-Fi: `@capgo/capacitor-wifi` ("On Android, this creates a temporary connection that doesn't
  route traffic through the network by default"; with `autoRouteTraffic` it "binds the app process to the connected
  network using ConnectivityManager.bindProcessToNetwork()"; "Location permission is required for Wi-Fi operations on
  both platforms") [S8, page read; the page does not state which Capacitor versions it supports]. An alternative is
  `@capawesome-team/capacitor-wifi` [S9, snippet only]. Underneath is Android's peer-to-peer Wi-Fi request: the system
  shows an approval dialog the first time, remembers the approval for that access point, and "creating a connection
  using this API does not provide an internet connection to the app or to the device" [S19, snippet only].
- The catch: binding the whole app process to the device's network cuts the app off from the internet for the
  duration, so the app cannot download from the glasses and upload to the cloud at once through a stock plugin.
  Doing both at once needs per-connection network binding, which means a **custom native plugin** (roughly 300-500
  lines of Kotlin with a foreground service). Downloading first and uploading afterwards avoids that.
- File handling: the WebView should not hold 1 GB in memory; clips must be written to disk natively
  (`@capacitor/filesystem`, from memory, unverified) and uploaded natively or in 8 MiB slices.
- New manifest permissions: Bluetooth scan and connect, fine location, nearby Wi-Fi devices, foreground service
  (exact names from memory, unverified). Today's manifest has none of them (section 1.3).

**iPhone and browser:** an iPhone needs a native iOS app (CoreBluetooth plus `NEHotspotConfiguration` [S9, snippet
only]); the repository has no iOS project. A plain browser cannot join a Wi-Fi network or keep a transfer alive in
the background. Chrome on Android could do the BLE half through Web Bluetooth [S10], but not the Wi-Fi half.

**Pairing for a non-technical user:** open the app, "Add glasses", the app lists nearby devices by BLE, tap one, type
the 6-digit code printed inside the temple arm (proof of possession, the pattern Espressif's provisioning uses
[S14]). Afterwards the app reconnects by itself.

**Security:** the account binding lives entirely in the phone app: the phone uploads as its signed-in user, and the
device holds no cloud credential. A lost device leaks only the clips still on it. The BLE link must be bonded and
encrypted, and the access-point passphrase must be random per session.

**Failure handling:** hop 1 is local, so a bowling alley with no signal does not matter; hop 2 waits. The known weak
point is the one Meta's users hit: phones abandon a Wi-Fi network that has no internet (support sites blame
"Android's intelligent Wi-Fi switching to mobile data" and low-battery throttling of the glasses' Wi-Fi at roughly
15-20 % [S13, snippet only]). Byte-range resume on hop 1 and the existing GCS resume on hop 2 cover interruptions.
On low battery the device should refuse to start its access point and keep recording.

### 2.2 Architecture 2: device straight to the cloud over Wi-Fi or a phone hotspot, with a per-device token

**Device must:** join a known Wi-Fi network (the phone's hotspot at the alley, home Wi-Fi while charging); keep a
device token; after each clip closes, ask the backend for an upload session, PUT the file to GCS in chunks, confirm;
keep a queue on local storage and retry until confirmed; keep its clock right (network time, or the phone's time at
pairing).

**Phone must:** share its hotspot. For the one-time pairing it only shows a web page. No app install is required, so
this works on Android, on an iPhone and in any browser.

**Backend must:** a `Device` table and pairing endpoints; a device-authenticated route that creates the clip record
and returns a GCS resumable session; a completion route; session and clip pages (section 5).

**Transfer time (derived):** there is no end-of-session transfer. The clips are produced at an average of 2.2 Mbps;
a hotspot uplink of 5 to 20 Mbps sends a mean clip in 13 to 53 seconds, inside the roughly 2-minute gap between
throws. Continuous recording (7 GB per hour) needs a sustained 15.6 Mbps just to keep pace, which a cellular hotspot
will not reliably give; that mode would upload at home.

**Why the existing upload path fits:** GCS resumable sessions are made for this. "This session URI acts as an
authentication token, so the requests that use it don't need to be signed" and "A session URI expires after one week
but can be cancelled prior to expiring"; after an error the client can "query the server for the persisted offset and
resume uploading remaining bytes from that offset"; "The buffer size must be a multiple of 256 KiB" [S15, page read].
So the device never holds a cloud credential: its device token buys one session URI per clip, good for that one
object for a week. The app's `POST /upload/resumable-url` already creates such sessions (section 1.1); the device
version is the same call behind a device-token check.

**Pairing for a non-technical user, three options, cheapest first:**

1. **The device reads a QR code off the phone screen.** A camera device can scan. In the app (any browser, signed in
   or known by email): Me, Devices, "Add glasses"; type the hotspot name and password once; the page shows a QR code
   holding the Wi-Fi details and a one-time claim code. Put the glasses in pairing mode (long press, light blinks),
   look at the phone. The device joins the hotspot, redeems the claim code at the backend and receives its token.
   Needs no radio code on the phone at all. This is a design proposal, not a sourced practice; QR decoding on a Linux
   or Android device is a library call (from memory, unverified). The Wi-Fi password sits in the QR on screen for a
   moment, which is acceptable for a prototype.
2. **BLE provisioning.** The phone sends Wi-Fi details and the claim code over BLE. On a microcontroller this exists
   ready-made: Espressif's "Unified provisioning subsystem supports Wi-Fi (SoftAP+HTTP server) and BLE (GATT based)
   transport schemes", with open-source Android and iOS apps and a QR sticker for proof of possession [S14, snippet
   only]. From the web it works in Chrome on Android through Web Bluetooth and not in iOS Safari ("Safari on iOS: not
   supported, see webkit.org/b/101034") [S10, snippet only]; in the Capacitor app it works through the BLE plugin
   [S6].
3. **The device's own setup page.** The device starts an access point; the user joins it in the phone's Wi-Fi
   settings and a page served by the device asks for the hotspot details and the claim code. Works on every phone,
   but leaving the app for system settings is the step people get wrong (Espressif notes the same about SoftAP on
   iOS [S14]).

**Security: how the device proves which account it uploads to.** The model is the OAuth device grant (RFC 8628: a
code is shown, the user approves it on a second device, optionally through a QR that encodes the complete
verification address) [S20, snippet only], turned around because the glasses have no screen: the signed-in user's app
mints a one-time claim code (5-minute life, single use, stored hashed, the same pattern as the repository's
`MagicLinkToken`); the device redeems it and gets a random 256-bit device token; the backend stores only its hash in
`Device.token_hash` beside `user_id`. Every later device call carries `Authorization: Bearer <token>`, and **the
device never sends a user id or an email**: the account comes from the token row. The Devices page lists each device
with last-seen time and a Revoke button. This is stricter than the app's current uploads, which trust whatever
`user_id` or `email` the caller writes (section 1.1); the device route should not copy that.

**Failure handling:**

- No signal in the alley: clips queue on the device. 2 GB holds a whole session (`REQUIREMENTS.md` section 4); a
  32 GB card holds about 4.5 hours of continuous recording at 7 GB per hour. Upload resumes whenever a known network
  appears, including home Wi-Fi on the charger, which is the "sync in the case" behaviour Meta ships [S13].
- A dropped upload: ask GCS for the persisted offset and continue [S15]. A session URI older than a week: request a
  new one.
- Duplicates: the clip id is generated on the device, so a retried "create clip" call returns the same record.
- Visibility: before the bytes, the device posts a tiny manifest ("32 clips recorded, 12 confirmed"), which gets
  through on a weak signal, so the app can say "20 clips still on the glasses" instead of looking empty.
- Low battery: stop uploading below a threshold and keep recording; uploading is the deferrable half.
- Hotspot quirks: an iPhone hotspot may stop advertising when nothing is connected and may need its "Maximize
  Compatibility" switch for 2.4 GHz-only radios such as the Pi Zero 2 W (from memory, unverified; the 2.4 GHz-only
  radio is sourced [S22]).
- Costs: about 1 GB of cellular data per session, and Wi-Fi transmit power and heat on the face. Uploading only
  between throws, or only on the charger, is a firmware setting.
- Venue Wi-Fi with a sign-in page is unusable for a device with no screen; do not plan on it.

**iPhone and browser:** fully supported, because the phone does nothing but share its connection and show pages.

### 2.3 Architecture 3: Bluetooth only

**Real throughput.** The theoretical ceiling for BLE on its 2-megabit radio mode is about 1.4 Mbps of application
data. Measured: an iPhone 11 about 311 kbps and a Galaxy S10 Plus 1,222 kbps in one vendor benchmark; 340 kbps
(phone to device) and about 700 kbps (device to phone) on Android in a chip-vendor forum; "around 300-400 kbps" on a
recent iPhone against "well over 1000 kbps" on Android in an Apple forum thread; and about 53 kilobytes per second
(425 kbps) on an iPhone 13 Pro in another vendor's file-transfer test [S7, all snippet only, forum and vendor notes
rather than controlled studies].

**Is about 1 GB per session workable? No.** At 0.3 to 1.2 Mbps the measured session takes 2 to 8 hours, one mean
clip takes 3.7 to 14.8 minutes against a 2-minute gap between throws, and the link is slower than the 2.2 Mbps at
which clips are produced, so the backlog only grows. The phone would also have to hold the link in the foreground
for hours. Meta's developer kit shows the same ceiling from the other side: its live stream runs over Bluetooth and
tops out at 720x1280 at 30 frames per second, dropping resolution first when bandwidth is short [S2][S3].

**What Bluetooth is right for:** control and status (start, stop, battery, storage, clock); a thumbnail per clip (a
50 KB image is about a second); event markers; and the motion log, which is small (section 4.2). Every architecture
with a native app should keep BLE for these.

**Platforms:** Capacitor on Android through the BLE plugin [S6]; a native app on iPhone; Web Bluetooth in Chrome on
Android only [S10]. Third-party iOS browsers and a Safari extension polyfill exist [S10] but are not something to
ask a non-technical user to install.

### 2.4 Architecture 4: tethered, the camera is a USB video device and the phone records

**Device must:** be a UVC camera module on a thin cable to the phone in a pocket. No battery, storage, radio or
firmware of its own, so nothing lithium beside the head.

**Phone must:** act as USB host, open the camera, encode and save video, then upload. On Android the open-source
route is AUSBC ("AndroidUSBCamera", a UVC engine with preview and video capture; the only stated device requirement
is USB On-The-Go support) built on the older UVCCamera library [S11, snippet only]. **I found no Capacitor plugin for
UVC**; a Flutter wrapper exists, which shows the shape of the custom plugin that would be needed [S11]. Estimated
1-2 weeks including recording with the screen off.

**Backend must:** only the session and clip records.

**Transfer time:** no device hop. Phone to cloud as in 2.1 hop 2.

**iPhone:** not possible. An Apple engineer's forum answer: "it is expected that iPhone 15 Pro does not support
external cameras", and "iOS does not support DriverKit or include UVC support"; external cameras are an iPad feature
[S12, snippet only, forum posts from 2025; I found no statement that newer iPhones changed this].

**Browser:** WebUSB exists in Chrome on Android [S10], but browsers block web pages from claiming video-class USB
interfaces (from memory, unverified), so a web page cannot drive the camera this way.

**Limits:** a cable from the temple to a pocket during a bowling approach; the phone must stay awake; a plain UVC
camera carries no motion sensor, so a time-synced motion log needs a small microcontroller on the same cable
presenting a second USB function; exposure control depends on what the module exposes over UVC.

**Where it earns its place:** as the cheapest test bench for the question `REQUIREMENTS.md` ranks first. A UVC module
on a cap, recorded by a phone or a laptop, answers "does this sensor and lens put more pixels on the pins than the
Meta glasses" in an afternoon, before any board, battery or firmware exists. Use it to choose the camera, not as the
product.

### 2.5 Architecture 5: a third-party glasses software kit

**Meta Wearables Device Access Toolkit.** A phone app (native iOS or Android guides only; no web or Capacitor
mention) reaches the glasses "over Bluetooth", can start a video stream and receive frames, and can capture a photo
during a stream; the overview does not mention the motion sensor or the media stored on the glasses [S1, page read].
The stream presets are 720x1280, 504x896 and 360x640 at 2, 7, 15, 24 or 30 frames per second, and the kit lowers
resolution and then frame rate when Bluetooth bandwidth is short [S2, snippet only]; "the maximum resolution is 720p
and the maximum frame rate is 30 FPS" and the kit was reported as a public preview [S3, snippet only]; I found no
source confirming general availability. **This fails the tightest requirement:** the owner's recorded clips are
mostly 1376x1824 at 15 Mbps (`REQUIREMENTS.md` section 2), so the kit's stream has about half the linear resolution,
through a narrower and adaptive pipe, on a tracker whose weakest stage is a ball 4 to 13 pixels in radius at the
pins. It also gives no file: the phone app would have to record the stream itself, and it gives no motion log. It is
a route to a live preview, not to tracker-grade clips.

**MentraOS and Mentra Live.** The phone-side Bluetooth kit (React Native, Android, iOS) names Mentra Live as the
supported camera glasses. An app can start a video recording with a chosen width, height and frame rate (the examples
use 1280x720 at 30), and "Upload happens at stop time if you pass a webhook URL": the glasses send the file as a
multipart `video` field with a `requestId`, directly over Wi-Fi, with the phone's Bluetooth as a fallback for photos.
It also streams to RTMP, SRT or WebRTC ingest addresses, and `setCameraFov` accepts 62 to 118 degrees [S4, page
read; the page gives no maximum resolution]. The hardware page lists a 1080p camera and Wi-Fi [S5, snippet only].
**In effect this is architecture 2 already built by a vendor**: the app's backend would be the webhook. Two things to
check before relying on it: (a) the upload is a multipart POST, and the app's backend sits behind Cloud Run's 32 MiB
request cap (section 1.4), so the webhook needs its own small receiver that streams to GCS, or clips must stay under
the cap; (b) whether 1080p at the narrowest field of view gives more pixels per degree down the lane than the Meta
glasses is a measurement for the hardware lane, not something the documents answer. Motion-sensor access is not
described on the page I read.

**What every vendor kit costs the app:** a native plugin per phone platform, an account or review process with the
vendor, and a dependency on their app and firmware versions (Meta's 1.0 release reportedly shipped a frame-freeze
bug [search-result summary of mixed-news.com, date unclear]).

### 2.6 Architecture 0, for comparison: keep today's glasses and fix only the app half

Not in the brief, but it is the baseline every option should be compared with. The Meta app already imports clips to
the phone. A "Session upload" page in the app that takes many videos at once from the phone's gallery and sends each
through the existing resumable route (compression off) would put today's clips in the app with zero hardware and
zero native code. It still takes a second app and a manual step, so it does not meet the target flow in
`REQUIREMENTS.md` section 5, but it builds and proves the whole backend half, and every other architecture reuses it.

## 3. Firmware effort by device class

Effort is my estimate for this builder (strong Python, TypeScript, cloud; no embedded C), to reach "a clip recorded
on the face is confirmed in the app's bucket". It is a judgement, not a sourced figure.

| Device class | Example | What the software is | Can it meet the camera baseline (1376x1824, 30 fps, about 15 Mbps HEVC)? | Open-source starting points | Effort to first clip in the app | Which architectures fit |
|---|---|---|---|---|---|---|
| Microcontroller | ESP32-S3 with a small camera, as in the Omi Glass / OpenGlass design (Seeed XIAO ESP32 S3 Sense, firmware is an Arduino sketch) [S16] | C or Arduino on a real-time kernel; JPEG frames, no general-purpose operating system | **No.** Espressif's guidance: about 20 frames per second for 720p motion-JPEG on the S3; raw formats limited to about 1 megapixel; a 2026 bench measured a sustained Wi-Fi ceiling of 6-7 Mbit/s [S18, snippet only]. No hardware H.264 encoder on the S3 (from memory, unverified; the newer ESP32-P4 has one, also from memory) | Omi Glass firmware (photo capture over BLE) [S16]; Brilliant Labs Frame firmware [S17]; Espressif's provisioning component and phone apps [S14]; an ESP32 motion logger that writes Gyroflow logs ("esplog") [S21] | 3-5 weeks, in an unfamiliar language, and the result fails requirement 1 | 3 (photos only), a slow 1 or 2. Useful as a companion: BLE remote button, motion logger |
| Linux camera chip | Raspberry Pi Zero 2 W with a camera module; Rockchip- or SigmaStar-based camera boards | Linux; the recorder, uploader, BLE service and motion logger can all be **Python** | **Partly.** The Zero 2 W has hardware video encoders [S22]; a community report has 1080p at about 25 frames per second [S22, snippet only]. That is fewer pixels than the baseline frame unless the lens is narrower; whether a narrower lens wins on pixels per degree is the hardware lane's question | The Raspberry Pi camera stack and its Python library (from memory, unverified); MediaMTX for streaming [S22]; OpenIPC firmware for camera chips (from memory, unverified); Gyroflow's log format for the motion file [S21] | **1-2 weeks.** Record, queue, resumable upload and retry are about 300 lines of Python | 2 natively; 1 with more work (access point plus BLE service on Linux) |
| Android-based glasses | Mentra Live (runs an Android "ASG Client" app; MentraOS is "open source under the Apache License 2.0" [S23, page read]) | An Android app on the glasses, or only the vendor's phone-side kit | **To be measured.** 1080p camera [S5]; adjustable field of view 62-118 degrees [S4] | MentraOS repository (phone app, kit, glasses client builds) [S23]; the kit's record-and-upload-to-webhook call [S4] | Days with the vendor kit (the backend becomes the webhook); 2-4 weeks for a custom Android app on the glasses, and only if the vendor allows side-loading (not verified) | 5, which behaves like 2 |

Reading the table against the builder's skills: the Linux class is the only one where the device software is in a
language he already writes, and where the device can do HTTPS, resumable upload, a retry queue and a motion log
with ordinary libraries. The costs of Linux are boot time (tens of seconds) and idle power, both on the face (from
memory, unverified; the hardware lane should measure them). The Android-glasses class removes the hardware project
entirely if the camera passes the pixel test.

## 4. Motion log and per-throw clipping

### 4.1 Why it belongs in the design now

`REQUIREMENTS.md` section 3 lists camera motion (item 3) and release and pin-hit detection (item 4) as things the
Meta glasses cannot help with. Both become data problems once the device records a motion log on the same clock as
the video. The transfer design has to carry that log from day one, or it will be bolted on later with a second clock.

### 4.2 A time-synced motion log

- **Format.** Use a sidecar file per clip in Gyroflow's `.gcsv` text format: first line `GYROFLOW IMU LOG` (format
  version 1.3), a header with a Unix start time and the sensor orientation, then timestamped gyroscope and
  accelerometer rows; for `clip.mp4` the log is `clip.gcsv`, which Gyroflow detects automatically. Its guidance for
  cameras: "the timestamps should be based on the same time source as the video capture. This prevents drift between
  the two"; suggested logging rate 500 Hz with a 50-100 Hz low-pass filter [S21, snippet only]. Choosing an existing
  format means an existing desktop tool can check the sync visually before any tracker code is written.
- **Clock.** On a Linux device, stamp every video frame and every motion sample with the same monotonic clock and
  write the per-frame timestamps to a second sidecar (`clip.frames.csv`). Wall-clock time comes from the network or
  from the phone at pairing, and is only used to order clips and name sessions.
- **Size (derived).** Six axes at 500 Hz in text is roughly 25 kilobytes per second: about 14 MB for the session's
  554.6 seconds of recording, about 1 % of the video. In binary it is about 8 kilobytes per second (64 kbps), small
  enough to stream live over BLE if a later design wants it.
- **Transport.** The sidecars upload exactly like the clip: one more resumable session each, named after the clip.
  The clip record lists them (section 5.1).
- **Audio.** The clip already has a sound track (the Meta clips carry stereo AAC at 48 kHz). Keep it: the pin crash
  is a candidate end-of-throw marker, and it costs nothing extra to carry.

### 4.3 Continuous recording cut by the app, against an on-device trigger

| | A. Continuous recording, the app cuts | B. On-device trigger, short clips | C. Manual button (today) |
|---|---|---|---|
| Data per 65-minute session | about 7.6 GB (7 GB per hour) | about 1.2 GB (32 clips of about 20 s at 15.6 Mbps) | 1.07 GB (measured) |
| Upload | 51 minutes at 20 Mbps; needs 15.6 Mbps just to keep pace; not a hotspot job | each clip in 13-53 s at 5-20 Mbps | same as B |
| Camera and encoder on-time | 65 minutes | about 11 minutes | 9.2 minutes (measured) |
| Who decides the cut | The app. The research auto cutter got 4 right, 6 wrong and 15 with no answer on 25 untouched clips (`RULES.md`), from video alone | The device, from motion and sound, with padding; the app refines | The wearer |
| Missed throws | None; everything is recorded | Possible if the trigger misses | Possible if the wearer forgets |
| What it needs first | A cutter that works | Labelled motion and sound data to build the trigger on | Nothing |

**How an on-device trigger would work.** The device records continuously into a rolling buffer of the last 30
seconds and keeps a clip only when told to. Candidate "keep" signals, cheapest first: a button (as today); a BLE
button on the bowling hand or a phone tap; the motion sensor seeing the approach (a few seconds of head held still
facing down the lane, then the stride pattern); the microphone hearing a pin crash, which says "the throw that just
ended is worth keeping: save the last 12 seconds and the next 3". The sound trigger will also fire on neighbouring
lanes, so it needs the motion signal as a gate. None of these is tested; each is an experiment.

**Recommendation for sequencing.** Do not choose between A and B yet; make the first prototype produce the data that
decides it:

1. Prototype 1 keeps the manual button (it produced 32 usable clips in the measured session) and adds a 10-second
   pre-roll from the rolling buffer, so a late press still catches the release.
2. Every clip carries the motion log and sound. In addition the device keeps one low-rate motion log for the whole
   session (2 hours at 50 Hz is a few megabytes) and uploads it with the session manifest.
3. With two or three such sessions, the button presses are free labels: train or hand-tune the trigger offline
   against them and report hits and misses the way `RULES.md` already requires (freeze the count before changing the
   rule).
4. Only when an offline trigger beats the button does it move onto the device. The app-side cutter then has an easier
   job than today's: it refines release and pin-hit inside a 20-second window using motion and sound, instead of
   finding a throw in raw video.

Continuous recording stays available as a firmware switch for sessions on home Wi-Fi or for collecting trigger
training data, with upload on the charger.

## 5. Recommendation

### 5.1 First prototype: architecture 2, on a Linux-class or Android-class device

**The device uploads each clip straight to the app's bucket over the phone's hotspot (or home Wi-Fi), using a
per-device token and the GCS resumable sessions the backend already creates. Pairing is one QR code shown by the app
and read by the device's own camera.**

Why this one:

1. **It needs no native phone code.** The repository has an Android debug APK that has never been installed on a
   real phone and no iOS project (section 1.3). Architecture 2 works on Android, iPhone and any browser on day one.
2. **All the work is in languages the builder already uses:** Python on the device, Flask and React in the app.
3. **The link is fast enough with a wide margin.** Clips are produced at 2.2 Mbps on average; a 5 Mbps hotspot sends
   each clip in under a minute, so the session ends with nothing to transfer (section 1.6).
4. **The byte path exists and is proven**: resumable direct-to-GCS upload, already exercised with a 372 MB phone
   video including a drop and resume (section 1.1).
5. **It meets the target flow in `REQUIREMENTS.md` section 5** (pair once from a phone, no laptop, clips land in the
   account without opening another app) more literally than Meta's own pattern, which needs the phone app open.

What it gives up: live control and status from the phone (no BLE in prototype 1; the device's light is the only
feedback, plus the app's "clips arrived" count), and it depends on a hotspot or a known network. The mitigation is
the on-device queue: no signal means "later", never "lost".

If the hardware lane selects Mentra Live, the same architecture is reached through the vendor kit's
record-then-upload-to-webhook call (section 2.5), subject to the two checks listed there.

**Fallback that ships in the same work:** the "Session upload" page of section 2.6 (pick many clips from the phone,
upload with compression off). It rescues a session when the device cannot reach a network at all (pull the card or
copy over USB), and it puts today's Meta clips in the app immediately.

### 5.2 Long-term product: BLE for control, Wi-Fi for bytes, two byte routes

The mature shape is the one Meta converged on, with one addition:

- **BLE, always on:** pairing, status, battery, clock, start and stop, a thumbnail per clip, and the live trigger
  signal if the trigger ends up on the phone or a wrist button.
- **Bytes, route A (preferred):** the device uploads by itself whenever it sees a network it knows (home Wi-Fi on the
  charger, or the hotspot). This is architecture 2 unchanged.
- **Bytes, route B (on demand):** when the user opens the app at the alley and there is no usable network for the
  device, the app pulls clips over the device's own access point and uploads from the phone. This is architecture 1,
  and it is the part that needs the native plugins and an iOS app.

Order of work that keeps each step useful on its own: architecture 0 page, then architecture 2, then BLE status in
the Android app, then route B, then iOS.

### 5.3 Changes to the app, with rough size

Sizes are lines of new code excluding tests, and working days for this builder; estimates, not measurements.

**Backend (Flask, startup migrations in `app.py`, latest migration is 020):**

| # | Change | Size | Needed for |
|---|---|---|---|
| B1 | Migration 021: tables `CaptureSession` (id, user_id, device_id, started_at, ended_at, source, clips_expected), `CaptureClip` (id chosen by the uploader, session_id, object_name, captured_at, duration_s, bytes, sha256, sidecars as JSON, status, attempt_id nullable) | about 80 lines, 0.5 day | everything, including architecture 0 |
| B2 | `capture_routes.py`: `POST /capture/clips` (create the record idempotently, return a resumable session URI for the clip and one per sidecar), `POST /capture/clips/<id>/complete` (verify the object exists and its size, mark stored), `POST /capture/sessions/<id>/manifest`, `GET /capture/sessions`, `GET /capture/sessions/<id>` | about 300 lines, 2 days | everything |
| B3 | Migration 022: tables `Device` (id, user_id, name, token_hash, created_at, last_seen_at, revoked_at, firmware, battery_pct) and `DeviceClaim` (code_hash, user_id, expires_at, used_at), modelled on `MagicLinkToken` | about 60 lines, 0.5 day | architecture 2 |
| B4 | `device_routes.py`: `POST /devices/claims` (the app mints a one-time claim code), `POST /devices/redeem` (the device swaps it for a token, shown once), `GET /devices`, `DELETE /devices/<id>` (revoke), `POST /devices/heartbeat`; a `require_device` decorator that resolves the account from the token hash; rate limits | about 300 lines, 2 days | architecture 2 |
| B5 | Register the new test suites in `tools/run_ci_tests.sh` (database-free, per the repository's working rules) | 1 day | all |
| B6 | `tools/pull_capture_session.py`: download a session into the folder layout the research tracker reads | about 80 lines, 0.5 day | closing the loop with the research code |
| B7 | Decide who may call B2 from a browser. The existing upload routes trust a `user_id` or `email` in the body (section 1.1). For an owner-only prototype that is tolerable; say so in the code, and do not let the device route inherit it | a decision, not code | architecture 0 |
| B8 | If the Mentra webhook route is used: a receiver that is not behind the 32 MiB request cap and streams the multipart body to GCS | about 150 lines plus deployment, 1-2 days | architecture 5 only |
| B9 | Later: a first-person analysis job (a job type in the Cloud Run engine, a results table, a rerun policy with no human judge). This is productising research code and is weeks, not days | large | a ball line in the app; not part of "appears in the app" as defined in 1.5 |

Important: a first-person clip must **not** be sent to `POST /bowling/upload` or given a `BowlingResult`, because
that queues the third-person analyzer (section 1.5). `CaptureClip.attempt_id` stays empty until B9 exists.

**Frontend (React; phone layout below 768 px):**

| # | Change | Size | Needed for |
|---|---|---|---|
| F1 | `/sessions` list and `/sessions/:id` detail: clips in capture order with time, playback, "n of m arrived", owner-gated like the bowling pages (`useIsOwner`) | about 400 lines, 2-3 days | everything |
| F2 | "Session upload": multi-file picker that sends each file through the existing resumable client with compression forced off, into one `CaptureSession` | about 200 lines, 1 day | architecture 0, fallback |
| F3 | `/devices`: list, "Add glasses" (hotspot name and password form, QR code with Wi-Fi details and claim code), rename, revoke, last seen, battery | about 300 lines plus a QR library, 2 days | architecture 2 |
| F4 | Render check in a real browser for each new page (the repository's rule: the type checker does not catch scope bugs) | 0.5 day | all |

**Native (only for the long-term route B or the tethered rig):**

| # | Change | Size |
|---|---|---|
| N1 | Add `@capacitor-community/bluetooth-le` 7.x [S6], a Wi-Fi join plugin [S8][S9], a filesystem plugin; new manifest permissions; a BLE status card in the app | 3-5 days including tests on a real phone |
| N2 | Custom Kotlin plugin: foreground service that downloads from the device's network and uploads to GCS with per-connection network binding | 1-2 weeks |
| N3 | An iOS project (none exists), CoreBluetooth and hotspot-configuration code, a developer account and signing | 2 weeks or more |
| N4 | Custom Capacitor plugin over an Android UVC library for the tethered rig [S11] | 1-2 weeks; skip if a laptop is acceptable as the camera test bench |

**Device software for architecture 2 (Python on a Linux-class device):** recorder with rolling buffer and button,
about 150 lines; uploader with queue, resumable PUT, offset query and retry, about 150 lines; QR pairing and Wi-Fi
join, about 100 lines; motion logger writing `.gcsv`, about 100 lines; a status light. About 1-2 weeks including the
motion-sensor wiring.

**Total for prototype 1 on the app side:** B1-B7 and F1-F4, roughly 8-10 working days, with no native code.

### 5.4 The smallest end-to-end demo: "recorded on the face, appears in the app"

Three steps; each one is a working result, and each reuses the one before.

**Step 0, no hardware (1-2 days): the app half.** Build B1, B2, F1 and F2. On the phone, pick the 32 clips of the
2026-11-08 session from the gallery and upload them as one session. Pass when: all 32 are listed in capture order
and play on the phone; each stored object's size and hash equal the source file (proves the compressor was
bypassed); `tools/pull_capture_session.py` (B6) recreates a folder the research scripts accept.

**Step 1, about $60-100 of parts, taped to a cap (2-3 days after step 0): the face half.** A Raspberry Pi Zero 2 W,
a camera module, a push button and a USB power bank in a pocket. Hand-insert one `Device` row and paste its token
into a config file; type the hotspot name and password into the device's Wi-Fi config by hand. A Python script of
about 150 lines: on a button press, record 20 seconds of 1080p video to MP4; call `POST /capture/clips` with the
token; PUT the file to the returned session URI in 8 MiB chunks; call complete. No pairing screen, no BLE, no motion
log yet. Part prices are from memory and unverified; the hardware lane owns them.

Pass when, with the cap on and the phone in a pocket sharing its hotspot:

1. A clip recorded at time T is listed and playable on the phone's `/sessions` page by T + 60 seconds.
2. The stored object's hash equals the file on the device, and its capture time is within 1 second of the phone's
   clock.
3. Thirty-two presses over 65 minutes produce 32 clips with none missing (the measured session, replayed).
4. Turning the hotspot off in the middle of an upload and back on a minute later ends with the clip complete and not
   duplicated (the check must be able to fail: confirm the upload was really interrupted by reading a non-zero
   persisted offset before resuming).
5. With the hotspot off for the whole session, the clips arrive after it is turned on, and the session page showed
   "0 of n arrived" in between rather than nothing.

**Step 2 (about 1 week): make it something a phone can set up.** Add B3, B4 and F3: the QR pairing, the Devices
page, revoke. Then add the motion sidecar and the pre-roll. Pass when a second person pairs the device to their own
email-only account from an iPhone browser with no help, and their clip lands in their account and not the owner's.

What the demo deliberately does not prove: that the camera is good enough for the tracker (the hardware lane's
question; step 1's clips can be run through the research scripts as a first reading), wearability, battery life on
the face, or a ball line in the app.

## 6. Sources, unsourced claims and open questions

### 6.1 Sources (all accessed 2026-11-14)

"Page read" means the page was opened and the quote comes from a reading of its content through a summarising
fetch tool, so wording may be lightly paraphrased. "Snippet only" means I saw only a search-result summary; the
quotes are the text the search returned and the page itself was not opened.

| Tag | URL | How read | Supporting text |
|---|---|---|---|
| S1 | https://wearables.developer.meta.com/docs/develop/dat/build-overview/ | Page read | "Use mobile platform functions to access the device over Bluetooth."; "Meta does not access photos/videos or audio that is transferred directly from the glasses to the third-party mobile app."; "Audio is streamed as 8 kHz mono from the device to your app." The page lists no maximum resolution, no motion sensor, no public-distribution terms. |
| S2 | https://mixed-news.com/en/meta-dat-camera-720x1280-lower-resolution-higher-quality/ | Snippet only | Title: "Meta says lower resolution gives better glasses video, and its ceiling is 720x1280"; presets 720x1280, 504x896, 360x640; "Valid frameRate values are 2, 7, 15, 24, or 30 FPS"; lowers resolution first, then frame rate. |
| S3 | https://www.uploadvr.com/meta-wearables-device-access-toolkit-public-preview/ | Snippet only | "the maximum resolution is 720p and the maximum frame rate is 30 FPS", a limit tied to Bluetooth; toolkit "now available as a public preview". |
| S4 | https://docs.mentraglass.com/bluetooth-sdk/camera-streaming | Page read | "Photo upload sends a JPEG from supported glasses to a webhook URL."; video recording takes `width`, `height`, `fps`, `maxRecordingTimeMinutes` ("an auto-stop guard"); upload at stop to a webhook as a multipart `video` field with `requestId`; RTMP/RTMPS, SRT, WHIP/WebRTC ingest; `setCameraFov` 62 to 118 degrees; React Native, Android, iOS; only Mentra Live named. |
| S5 | https://docs.mentraglass.com/app-devs/core-concepts/hardware-capabilities/camera-glasses | Snippet only | Mentra Live "has a 1080p camera with streaming support, a microphone with VAD, and WiFi". |
| S6 | https://github.com/capacitor-community/bluetooth-le (also https://app.unpkg.com/@capacitor-community/bluetooth-le@7.1.1/files/README.md) | Snippet only | "7.0.0 (2025-01-25) BREAKING CHANGES update plugin to capacitor 7 (#744)"; compatibility table lists plugin 7.x for Capacitor 7.x. |
| S7 | https://community.infineon.com/t5/ModusToolbox-Blog/BLE-Throughput-Rate-Benchmark-Test-for-Cypress-BT-SoCs/bc-p/267238 ; https://devzone.nordicsemi.com/f/nordic-q-a/86154/measured-android-to-nrf52-maximum-throughput-over-ble-5-0/359949 ; https://developer.apple.com/forums/thread/770717 ; https://onlinedocs.microchip.com/oxy/GUID-13B7D217-F2CA-43C3-9716-7F4B7F99CD53-en-US-1/GUID-154F9CF6-B1C8-498D-859E-7E3A8BF923B9.html ; https://novelbits.io/ble-throughput-calculator/ | Snippet only | iPhone 11 about 311 kbps, Galaxy S10 Plus 1222 kbps (Infineon); 340 kbps to and about 700 kbps from an nRF52 on Android (Nordic forum); "around 300-400 kbps" on iPhone against "well over 1000 kbps" on Android (Apple forum); "53.11 Kbytes/sec" iPhone 13 Pro (Microchip); theoretical ceiling about 1402 kbps on the 2-megabit mode. |
| S8 | https://capgo.app/docs/plugins/wifi/getting-started/ | Page read | "On Android, this creates a temporary connection that doesn't route traffic through the network by default."; "binds the app process to the connected network using ConnectivityManager.bindProcessToNetwork()"; "Location permission is required for Wi-Fi operations on both platforms."; "On iOS, this creates a persistent connection." Supported Capacitor versions not stated. |
| S9 | https://capawesome.io/plugins/wifi/ ; https://developer.apple.com/documentation/networkextension/nehotspotconfiguration.md | Snippet only | "Capacitor plugin to manage Wi-Fi connectivity, including adding, connecting, and disconnecting networks."; Apple's class holds "configuration properties and credentials required to connect to Wi-Fi networks". |
| S10 | https://caniuse.com/web-bluetooth ; https://caniuse.com/webusb ; https://web-platform-dx.github.io/web-features-explorer/features/webusb | Snippet only | Web Bluetooth: Chrome since 70; "Safari on iOS: not supported, see webkit.org/b/101034". WebUSB: Chrome since 61 with matching Chrome for Android support; "very unlikely to ever become Baseline in this current form". Third-party iOS browser (Bluefy) and a Safari extension polyfill exist. |
| S11 | https://github.com/jiangdongguo/AndroidUSBCamera (via search listing) ; https://pub.dev/documentation/uvccamera | Snippet only | AUSBC: "flexible UVC camera engine for Android", preview and capture, requires USB On-The-Go; Flutter plugin "based on UVCCamera library for Android". No Capacitor UVC plugin appeared in the results. |
| S12 | https://developer.apple.com/forums/thread/780459 ; https://developer.apple.com/forums/thread/776912 ; https://developer.apple.com/forums/thread/740066 | Snippet only | "it is expected that iPhone 15 Pro does not support external cameras"; "iOS does not support DriverKit or include UVC support." |
| S13 | https://anexplorer.io/solve/meta-glasses-transfer-failed ; https://evezone.evetech.co.za/build-lab/connecting-ray-ban-meta-glasses-to-wi-fi-and-your-phone-a-first-time-owner-s-guide | Snippet only, low authority (not Meta) | "The initial transfer handshake occurs over Bluetooth Low Energy (BLE) before switching to Wi-Fi."; temporary network named like "Meta_Glasses_XXXX"; automatic sync over Wi-Fi in the charging case; low-battery throttling of Wi-Fi below roughly 15-20 %. |
| S14 | https://docs.espressif.com/projects/esp-idf/en/latest/api-reference/provisioning/provisioning.html | Snippet only | "Unified provisioning subsystem supports Wi-Fi (SoftAP+HTTP server) and BLE (GATT based) transport schemes."; "BLE transport consumes ~110KB memory at runtime"; credentials delivered "for example QR code sticker"; SoftAP provisioning "requires the phone-app user to go to System Settings"; open-source Android and iOS provisioning apps. |
| S15 | https://docs.cloud.google.com/storage/docs/resumable-uploads | Page read | "A session URI expires after one week but can be cancelled prior to expiring."; "This session URI acts as an authentication token, so the requests that use it don't need to be signed."; "The buffer size must be a multiple of 256 KiB (256 x 1024 bytes)."; "query the server for the persisted offset and resume uploading remaining bytes from that offset". |
| S16 | https://docs.omi.me/doc/hardware/omiGlass ; https://github.com/BasedHardware/OpenGlass | Snippet only | Firmware is an Arduino sketch for the XIAO ESP32 S3 Sense board; the OpenGlass repository has moved into the Omi repository and "isn't supported anymore". |
| S17 | https://arxiv.org/html/2606.07431 ; https://www.github.com/TeamOpenSmartGlasses/OpenSourceSmartGlasses | Snippet only | A paper extends "the open-source Brilliant Labs Frame firmware"; a repository with mechanical, electrical and software files for open-source smart glasses. |
| S18 | https://docs.espressif.com/projects/esp-idf/en/v5.5.6/esp32s3/api-guides/wifi.html ; https://esp32.com/viewtopic.php?p=101785 ; https://docs.espressif.com/projects/esp-techpedia/en/latest/esp-friends/solution-introduction/camera/dvp-camera-solution.html ; https://components.espressif.com/components/mushbraindave/esp_cam_sensor_imx/versions/0.1.2/examples/imx708_wifi_snapshot | Snippet only | "20 MBit/s TCP throughput and 30 MBit/s UDP throughput over the air"; forum iperf on ESP32-S3 about 4.5 Mbps as TCP server; about 20 fps for 720p motion-JPEG; raw formats limited to about 1 megapixel; a 2026 bench "sustained Wi-Fi ceiling of about 6-7 Mbit/s". |
| S19 | https://developer.android.com/develop/connectivity/wifi/wifi-bootstrap | Snippet only | The request "launches a dialog box on the same device"; "creating a connection using this API does not provide an internet connection to the app or to the device"; the approval is stored for that access point. |
| S20 | https://rfc-editor.org/rfc/rfc8628 (described through implementer documents such as https://www.ory.com/docs/oauth2-oidc/device-authorization) | Snippet only; the RFC text itself was not read | Devices "that have limited or no browser"; a QR code can encode `verification_uri_complete`; the verification page should ask the user to confirm the code. |
| S21 | https://docs.gyroflow.xyz/app/technical-details/gcsv-format ; https://old-docs.gyroflow.xyz/logging/gcsv/ ; https://old-docs.gyroflow.xyz/logging/customlogger/ | Snippet only | "text-based gyro log format that can be implemented in custom hardware/firmware called .gcsv"; first line "GYROFLOW IMU LOG"; version 1.3; "the timestamps should be based on the same time source as the video capture. This prevents drift between the two"; "logging rate: 500 Hz, Low pass filter cutoff: 50 to 100 Hz"; an ESP32 logger "esplog". |
| S22 | https://picockpit.com/raspberry-pi/?p=1508 ; https://arxiv.org/html/2507.12487v1 ; https://forum.core-electronics.com.au/t/pi-zero-w-2-camera-3-cctv/22982 | Snippet only | "Zero 2 W: 33.5 Mbps" (secondary write-up of another tester's figures, method not stated); "Zero 2W only has 2.4G Wi-Fi"; the Zero 2 W "provides hardware-based image and video encoders"; community report of 1080p at about 25 fps; streaming with MediaMTX. |
| S23 | https://github.com/Mentra-Community/MentraOS | Page read | "Every component is open source under the Apache License 2.0"; nightly builds include a "Download ASG APK"; supported glasses listed: Mentra Live, Even Realities G2, Vuzix Z100, Even Realities G1. The page does not name the glasses' Android version or chip. |

One page could not be read: https://docs.mentraglass.com/asg-client/README returned HTTP 404.

No prices, minimum orders or lead times are stated as fact in this lane; they belong to the hardware lanes.

### 6.2 Unsourced (from memory, unverified; not to be treated as fact)

- An Android-class glasses chip with 5 GHz Wi-Fi moving 1 GB in under 2 minutes.
- The ESP32-S3 having no hardware H.264 encoder and the ESP32-P4 having one.
- Browsers blocking WebUSB access to video-class interfaces.
- The exact Android permission names needed for BLE scanning, nearby Wi-Fi devices and foreground services, and
  `@capacitor/filesystem` being the right plugin for native file writes.
- iPhone Personal Hotspot behaviour (stops advertising when idle; "Maximize Compatibility" for 2.4 GHz).
- Linux boot time of tens of seconds and idle power draw on a Pi Zero 2 W.
- The Raspberry Pi camera Python library, OpenIPC as a firmware base for camera chips, and QR decoding being a
  one-library job on Linux.
- Parts for the step 1 demo costing about $60-100.
- Whether Mentra Live allows side-loading a custom Android app, and whether its kit exposes the motion sensor.
- Cellular signal and hotspot uplink speed inside the owner's bowling alley: not known; measure with a phone speed
  test on the lane before choosing between "upload between throws" and "upload at home".
- All effort estimates (days, lines of code) are judgement.

### 6.3 What was not verified, and how to check it

- Nothing in this lane was run. The repository findings are from reading source files on branch `feat/100-club` on
  2026-11-14, not from calling production; the claim that the upload routes accept unauthenticated calls comes from
  the absence of any auth decorator in `upload_routes.py`, and a single unauthenticated `POST /upload/signed-url`
  against a local server would confirm it.
- The plugin facts (S6, S8, S9) were not tested against this project's Capacitor 7.6.9; install each in a branch and
  build the APK before planning on it.
- BLE and Wi-Fi speeds are other people's measurements on other hardware. The first hour with any candidate device
  should include an `iperf3` run over the hotspot at the alley.

### 6.4 Open questions for the owner and the next stage

1. Is phone-hotspot upload acceptable at the alley (about 1 GB of cellular data per session), or should prototype 1
   upload only at home?
2. Android phone, iPhone, or both for the people who will wear it? Architecture 2 does not care; the long-term route
   B does.
3. Does "appears in the app" for prototype 1 mean stored, listed and playable (sized here), or must it include a
   ball line (which needs the tracker productised, item B9)?
4. May the device route be the first authenticated upload path in the app while the browser routes stay open, or
   should the browser routes be closed in the same change?
5. If the hardware lane favours Mentra Live: does its video upload fit under the 32 MiB cap at tracker-grade
   settings, and does its kit expose the motion sensor?
