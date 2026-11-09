# Getting a clip off Meta glasses with fewer manual steps (research notes, 2026-11-09)

Labels used below:
- **[V]** = verified: I fetched the page or file and read it (URL in Sources).
- **[3P]** = a third-party page said it, not Meta/Apple/Google.
- **[INF]** = my own inference, not confirmed by any page.
- **[UNV]** = unverified: I looked and could not confirm it.

## Baseline facts that set the limits

- **Clip length.** Default 30 s. The Meta AI app can raise it to 3 min on most models and 5 min on Oakley Meta Vanguard [V, Meta POV guide]. A third-party report says firmware v127 (Aug 2026) raised the cap to 5 min on Ray-Ban Meta Gen 2, Oakley HSTN, Vanguard and Meta Glasses, at 1080p30 [3P, ubergizmo].
- **Resolution/fps.** Gen 2 and Oakley: up to 3K at 30 fps or 1080p at 60 fps. Gen 1: 1080p, and the resolution cannot be changed [V, Meta POV guide + capture help]. Settings path: Devices icon -> video settings in the Meta AI app [V].
- **Format.** MP4 on Android, HEVC on iOS [V, Meta POV guide].
- **Storage.** Media stays on the glasses' internal storage until it is imported [V]. Gen 2 has 32 GB and Gen 1 has 4 GB [3P, 9to5google; I did not find a Meta page for this].
- **Measured on this machine [V, `ls -l`/`stat`].** `/Users/toka/pov-2026-11-08/drive_raw` holds 33 files (32 clips). Median size 32.6 MB, max 50.8 MB, for 12-26 s throws. RULES.md says they are HEVC portrait, 1184x1584 to 1424x1904, at a true 30 fps. A 32-throw session is about 1 GB, far below 32 GB of storage, so storage does not limit a session. Per-throw clips also stay far below the 30 s default cap.
- **Which phone Tom uses.** [INF] Memory says Tom's phone runs the toms_gym APK, so it is Android. But the clips are HEVC, and Meta's page says HEVC is what iOS produces. Android may also write HEVC inside an `.mp4` file. Check the phone (and Chardie's phone) before choosing between option B and option C.

## Current path (what "fewer steps" is measured against)
- The clips go from the glasses to the phone through Meta AI import, then to Google Drive (method [UNV], probably a manual upload from the phone), then get downloaded to `/Users/toka/pov-2026-11-08/drive_raw` on the Mac for batch analysis. Evidence: the clips are in a folder named `drive_raw` [V], and no session doc says how they reached Drive [V, grep of RULES.md and docs/sessions]. Every option below is compared against this path.

## Options

### A. Meta AI auto-import to the phone gallery (the base that every other "recorded clip" path builds on)
- **Status:** available now [V].
- **How the clip moves:** the glasses must be switched on and either in the charging case or with the hinges closed, with the phone's Bluetooth and Wi-Fi on. The app then moves the media to the phone's photo app and deletes it from the glasses [V, auto-import help + capture help]. Meta recommends more than 30% battery [V]. For big transfers the phone joins the glasses' own Wi-Fi, and iPhone may ask before joining [3P/search summary of Meta help]. On Android the clips land in a "Meta AI" folder in the gallery. If you use Google Photos, you have to back up that device folder yourself [V, Meta View->Meta AI help page]. iOS album name: [UNV].
- **Manual steps:** fold the glasses or put them in the case. The Meta AI app must be installed and paired. Auto-import is on by default on Android 13+ and iOS [V].
- **Latency:** [UNV]. No page gives transfer times. Forum posts say "importing full-quality video" sometimes stalls for a long time [3P, community forum].
- **Gap:** this only gets the clip to the phone. A server still cannot read it from there.

### B. Android: auto-import, then a folder-sync app pushes the "Meta AI" folder to Drive or S3
- **Status:** available now. Each piece exists [V/3P]. Nobody documents the combined chain [UNV].
- **How the clip moves:** auto-import (option A) puts the clip in the "Meta AI" folder. FolderSync "Instant sync" watches the folder pair and pushes new files at once [3P, FolderSync docs via search]. It supports S3-compatible accounts [3P], as well as Google Drive, SFTP and WebDAV [INF]. Autosync for Google Drive uploads new files immediately, but only to Drive [3P]. The server then picks up each clip from a Drive folder through the Drive API, or from GCS through its S3-compatible endpoint plus a bucket notification, and calls the existing `/upload` flow [INF]. The signed-URL direct-to-GCS upload the app already uses is the model for this [INF].
- **Manual steps:** fold the glasses. Nothing else, as long as Android does not kill the sync app [INF].
- **Latency [INF]:** import time + upload time. That is roughly 30 MB per throw over home or alley Wi-Fi or cellular, so tens of seconds per clip after import finishes. Import only starts once the glasses are folded, so you get feedback per batch, not per throw, unless the bowler folds the glasses between throws.
- **Do not use Google Photos for this:** see the dead end below. Google Photos backup of the folder [V] puts the clip somewhere the server cannot read.

### C. iPhone: auto-import, then one of three ways off the phone
- **Status:** available now. Each piece exists. Nobody documents the combined chain [UNV].
- **C1. Shortcuts automation.** iOS personal automations can fire on App (opened/closed), Charger, Wi-Fi, Bluetooth, Time of Day, Arrive/Leave and other events. "Allow Running When Locked" runs them without a notification [V, Apple "create a new personal automation"]. **No trigger fires on a new photo or video** [V, same page]. So the plan is: trigger on Bluetooth (glasses disconnect), Charger or App closed (Meta AI), then Find Photos (videos added recently), then Get Contents of URL with a POST to a backend endpoint [INF]. I did not confirm the Find Photos filters or a multipart file POST on an Apple page [UNV]. Manual steps: none once it is set up, if the trigger fires. Latency: seconds to minutes after the trigger [INF].
- **C2. Dropbox Camera Uploads with "Background Uploading" on.** Uploads videos from the camera roll in the background. Videos do not upload over cellular, and uploads pause off Wi-Fi [3P, Dropbox staff forum posts. I did not read the Help Center page]. The server reads the files through the Dropbox API or webhooks [INF]. Manual steps: none, but iOS background limits make it unreliable [3P].
- **C3. iCloud Photos to a Mac.** iCloud Photos syncs to Photos on Tom's Mac. A launchd job runs `osxphotos export --update --only-movies` (new items only, tracked in `.osxphotos_export.db`). `--download-missing` fetches iCloud originals but is "somewhat buggy" [V, osxphotos README]. The job then uploads the export folder. Scheduling is not covered by osxphotos itself [V]. Latency: iCloud sync delay plus the job interval, so minutes [INF]. Manual steps: none. It needs the Mac to be awake, and iCloud Photos needs to be on for that iPhone [INF].

### D. Custom phone app built on the Wearables Device Access Toolkit (DAT): the real "no manual steps" path, at 720p
- **Status:** **available now for your own unpublished app.** DAT 1.0 is out ("After a year in developer preview ... 1.0 is here", rolling out from 2026-09-30) [V, DAT FAQ]. iOS SDK 1.0.0 shipped 2026-09-24 and 1.0.1 on 2026-10-09 [V, CHANGELOG]. Developer Mode in the Meta AI app lets an unpublished app register with your own glasses without review [V, DAT integration doc]. **Publishing is not open yet** ("You'll soon be able to submit ... more to share on submission and publishing timing soon") [V, FAQ]. That is fine for a hobby app installed with Xcode or as an APK.
- **Supported:** Ray-Ban Meta Gen 1/Gen 2/Optics, Meta glasses, Meta Ray-Ban Display, Oakley HSTN and Vanguard. iOS 17.2+ and Android 10+ [V, DAT integration doc].
- **How the clip moves:** the phone app opens a DeviceSession and a Camera stream, and the glasses stream frames to the phone. **The app records that stream to a file on the phone** (the CameraAccess sample does exactly this, with optional mic audio, "continuing while the app is backgrounded" per changelog 0.9.0) [V, CHANGELOG + sample README]. The app then uploads the file straight to the backend `/upload` [INF]. This removes the Meta AI app import entirely: the clip never touches the glasses' storage or the camera roll [INF].
- **Hands-free trigger:** the experimental Inputs module reports `.capture(pressType)` events from the glasses' capture button, so a press could start or stop a recording [V, inputs SKILL.md]. "Experimental" means it works for development and beta channels but cannot be published to production yet [V]. That is fine for a personal app. Device state now includes `donState`/`hingeState` [V, 1.0.0], so the app could start and stop on its own [INF]. Whether a capture-button press also starts the glasses' own native recording at the same time: [UNV].
- **Hard limits [V, camera-streaming SKILL.md + CHANGELOG]:**
  - Max stream is **720x1280** (`.high`), with 504x896 medium and 360x640 low. Frame rates are 2/7/15/24/30.
  - The stream goes over **Bluetooth Classic**. When bandwidth is short the SDK drops resolution first, then fps, but never below 15. Meta itself says lower resolution gives better per-frame quality because Bluetooth compression is lighter.
  - Raw codec pauses when the app is backgrounded. `hvc1` (HEVC) keeps streaming in the background.
  - iOS 0.8.0 added "WiFi transport" [V]. Whether it lifts the 720p cap: [UNV]. The Android changelog has no Wi-Fi transport line [V, grep].
  - Standalone high-quality photo capture exists (experimental) [V]. Standalone high-quality *video* capture does not appear in the changelog or skills [V, grep for record/resolution].
- **Background caveat (Meta's own sources disagree) [V]:** line 57 of CHANGELOG 0.9.0 says the sample records "continuing while the app is backgrounded". But line 65 of the same release and the current CameraAccess README say "If the app backgrounds while previewing or recording, CameraAccess ends the active session." `hvc1` has streamed in the background since 0.5.0. Whether a custom app on SDK 1.0.x can keep *recording* while the phone is locked or in a pocket is [UNV]. It may need the screen on or the app in the foreground. Test this first.
- **Manual steps:** start the app or session once per session, then wear the glasses. The phone has to stay within Bluetooth range: in a pocket at the alley, which is fine [INF].
- **Latency:** seconds after each throw, because the file is already on the phone when the recording stops. You can upload as soon as the throw ends [INF]. That is the only option here that gives **per-throw** feedback without folding the glasses.
- **Feedback channel back to the bowler [INF]:** the glasses are the phone's Bluetooth audio device, so the app can speak the result through the glasses' speakers. On Meta Ray-Ban Display, DAT also has a Display module for rendering content [V, CHANGELOG 0.4.0+/0.9.0 display APIs].
- **Main risk [INF]:** the tracker was tuned on about 1424x1904 native clips. The DAT stream is at most 720x1280, compressed over Bluetooth, and may drop to 504x896 at 15 fps. Ball and pin detection quality at that input needs a test before committing. A cheap test: build the CameraAccess sample, record 5 throws, and run the existing pipeline offline.

### E. "Hey Meta, send a video to <contact> on WhatsApp" to a WhatsApp Business Cloud API number
- **Status:** the voice command exists [V, Meta sharing help: "Send a video to [contact name]" with a Messenger/WhatsApp/phone destination]. Sending to a Business API number as a contact: [UNV].
- **How the clip moves:** glasses, then phone (it **must be imported first**: "Before sharing media, it must first be imported from your glasses" [V]), then WhatsApp, then the Cloud API webhook with a media id, then the server downloads it from the media URL, which expires in 5 min (re-query the id) [V, Cloud API media reference].
- **Hard limits [V]:** inbound video is capped at **16 MB** and must be H.264 + AAC. Our clips are 28-51 MB HEVC, so WhatsApp would have to transcode or downscale them on the way, and the quality we would get is [UNV].
- **Manual steps:** one voice command per clip. Import still has to happen first, so it does not remove the fold-to-import step [V/INF].
- **Verdict [INF]:** worse than B, C or D. It gives compressed video and still needs an import first.

### F. Live streaming to Instagram/Facebook
- **Status:** **Gen 1 only** ("This feature is only available on Ray-Ban Meta (Gen 1) glasses"). The stream is lower resolution than a recorded video [V, Meta live-stream help].
- **How the clip moves:** to Facebook or Instagram Live. No server-side read path was confirmed [UNV].
- **Verdict:** a dead end for Gen 2, Oakley or Display. Use D for a live stream.

## Dead ends (with the source)
1. **No third-party code on non-display glasses.** DAT "extends iOS and Android mobile apps", so the code runs on the phone [V, DAT FAQ]. Web Apps run on the glasses only for Meta Ray-Ban Display, and their listed capabilities are device position, location and Neural Band wrist motion. No camera access is listed [V, FAQ].
2. **No API to read the glasses' stored gallery.** Neither the DAT FAQ, the iOS/Android changelogs nor the skill docs mention access to media already captured on the glasses [V, read and grepped]. Only the Meta AI app imports. I cannot prove a negative, so this one is [UNV].
3. **No developer access to the glasses' Wi-Fi import link.** The import Wi-Fi is the Meta AI app's private hotspot. DAT's iOS "WiFi transport" is for its own stream, not for file import [V for the changelog line; whether a file-import API exists: UNV].
4. **The server cannot read Google Photos.** Since 2025-03-31 the Library API only lists and reads media the app itself created, and the readonly scopes return 403 [V/3P, Google Photos API updates page via search]. The Picker API needs the user to pick each time. So "back up to Google Photos and poll" does not work, while Drive and GCS do.
5. **iOS Shortcuts has no "new photo added" trigger** [V, Apple automation page]. Use App, Charger or Bluetooth triggers instead (C1). IFTTT polling is the only photo trigger found [3P].
6. **Live streaming is Gen 1 only** [V].
7. **iCloud Photos has no server API** [UNV, my own knowledge; no page was fetched]. A Mac with osxphotos is the workaround (C3).
8. **WhatsApp Cloud API's 16 MB H.264-only video cap** is below our clip sizes [V].

## Ranking for "less manual steps" [INF]
1. **D (DAT phone app)**: per-throw, about seconds of latency, no fold or import. Costs: build a small iOS/Android app, 720p Bluetooth-compressed input, and the tracker must be re-checked at that resolution.
2. **B (Android) or C1/C3 (iPhone)**: full-quality clips with no code on the phone (B, C3) or one shortcut (C1). Feedback comes per batch, because import only runs when the glasses are folded or in the case.
3. E and F: not worth it.

## Sources (fetched unless marked "search only")
- Meta auto-import help: https://www.meta.com/help/ai-glasses/1510723473009423/
- Meta capture photos/videos help: https://www.meta.com/en-gb/help/ai-glasses/272319252352130/
- Meta POV shooting guide (length, res, format, import): https://www.meta.com/ai-glasses/learn/guide-shooting-pov/
- Meta sharing help: https://www.meta.com/en-gb/help/ai-glasses/683425686669295/
- Meta media storage help: https://www.meta.com/help/ai-glasses/1427588664906909/
- Meta View -> Meta AI app help ("Meta AI" folder, Google Photos): https://www.meta.com/help/ai-glasses/1964061290737893/
- Meta live-stream help (Gen 1 only): https://www.meta.com/help/ai-glasses/1384089832459749/
- DAT FAQ: https://developers.meta.com/wearables/faq/
- DAT integration doc: https://wearables.developer.meta.com/docs/develop/dat
- DAT iOS repo, README, CHANGELOG, skills (camera-streaming, camera-capture, inputs), CameraAccess sample: https://github.com/facebook/meta-wearables-dat-ios (raw CHANGELOG and skills fetched via gh api)
- DAT Android CHANGELOG and camera-streaming skill: https://github.com/facebook/meta-wearables-dat-android
- WhatsApp Cloud API media reference: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media/
- Apple, create a personal automation (trigger list): https://support.apple.com/guide/shortcuts/create-a-new-personal-automation-apdfbdbd7123/ios
- osxphotos README: https://github.com/RhetTbull/osxphotos
- [3P] v127 5-minute video: https://www.ubergizmo.com/2026/08/meta-glasses-update-adds-longer-video-and-whatsapp-calls/
- [3P, search only] Gen 2 32 GB storage: https://9to5google.com/2025/09/17/ray-ban-meta-gen-2-battery-video-upgrades/
- [search only] Google Photos API changes: https://developers.googleblog.com/google-photos-picker-api-launch-and-library-api-updates/
- [3P, search only] FolderSync instant sync / S3: https://foldersync.io/changelog ; Autosync: https://metactrl.com/
- [3P, search only] Dropbox background uploading: https://www.dropboxforum.com/discussions/101001014/force-ios-dropbox-app-to-upload-camera-pictures-in-the-background/819364
- [3P, search only] Meta community import stalls: https://communityforums.atmeta.com/discussions/ai-troubleshooting/media-is-taking-longer-to-import-/1354683
