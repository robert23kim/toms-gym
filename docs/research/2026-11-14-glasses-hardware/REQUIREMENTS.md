# Requirements: a t30g capture device (prototype)

Written 2026-11-14 by the lead session, before the research workflow ran. Every number names where it came from.
"t30g" is this app (t30g.com, repo `toms_gym`).

## 1. What it is for

**Assumption (named, not confirmed by the owner):** the device is for first-person bowling capture. That is the only
glasses work in this repo: three research loops under `docs/research/2026-10-10-glasses-pov-tracking`,
`2026-11-07-glasses-pov-hook` and `2026-11-09-glasses-pov-session`. The wearer's head camera sees the ball from release
to the pins, and a tracker turns that into a line on the lane (board at the arrows, breakpoint, entry, exit).

**Not designed for, but worth one paragraph in any plan:** the lifting and 100 Club flows are third-person (a phone
propped up, filming yourself). A head-mounted camera cannot film its wearer. If one device should serve both, it has
to come off the face and stand on something.

## 2. The baseline to beat: what the Meta glasses give today

Measured with ffprobe on all 32 clips of the 2026-11-08 session (`/Users/toka/pov-2026-11-08/drive_raw/`):

| Property | Value |
|---|---|
| Video codec | HEVC, 10-bit (`yuv420p10le`) |
| Frame size | portrait, about 3:4; **15 different sizes in one session**, from 1184x1584 to 1424x1904; 16 of 32 are 1376x1824 |
| Frame rate | 29.9 to 30.0 fps real (the container's `r_frame_rate` says 120) |
| Video bitrate | 14.9 to 15.3 Mbps |
| Audio | AAC stereo, 48 kHz |
| Clip length | 2.6 to 26.4 s, mean 17.3 s |
| Clip size | 5.3 to 50.8 MB, mean 33.4 MB |

The varying frame size is measured. That it comes from a stabilisation crop is the lead session's guess.

How a clip reaches the app today: glasses -> the vendor's phone app -> Google Drive -> a laptop -> research scripts.
Nothing reaches t30g on its own, and the POV tracker is research code, not a product feature.

## 3. What the tracker needs from the camera (tightest constraint first)

From the three loops' `RULES.md` files:

1. **Pixels on the far end.** At the pins the ball is 4 to 13 px in radius at native size. Upscaled 2x/3x crops did
   not help (16-20 % far recall against 91 % native). The pin-row crossing is the weakest stage. A new camera must give
   at least the same pixels per degree down the lane, and more is the single most useful improvement.
2. **Less blur at release.** In the first ~10 frames after release the ball is 60 to 135 px in radius and smeared.
   Shorter exposure, and ideally manual exposure control, would help.
3. **Camera motion.** The head whips during the throw. Every method first has to cancel camera motion with an
   ORB + RANSAC homography per frame pair. A gyro/IMU log time-synced to the video is something a custom device could
   record and the Meta glasses do not expose.
4. **Release and pin-hit events.** Nothing detects them reliably from video: a colour-free release detector tried on
   25 untouched clips got 4 right, 6 wrong and 15 with no answer. Extra channels (IMU, audio of the pin crash) are an
   open opportunity.
5. **Frame rate.** 30 fps works. The ball takes roughly 2.2-2.5 s to travel the lane, about 70 frames. 60 fps is
   desirable, not required.
6. **Field of view.** The lane and pin deck must stay in frame while the head tilts through the approach. Fixed focus
   is fine.

## 4. Session envelope (measured, 2026-11-08)

- 32 clips between 10:47:14 and 11:51:57, a 65-minute span.
- 554.6 s of recording in total (9.2 minutes), 1.07 GB.
- Each clip was started by hand before a throw.

So a device needs at least: 2 hours awake on the face, 15 minutes of recording inside that, 2 GB of storage, and a way
to move about 1 GB to the app in a few minutes. Recording a whole session continuously and letting the app cut it
would remove the per-throw button press, at a cost of roughly 7 GB per hour at today's bitrate.

## 5. What "link directly into t30g" means

- The app: React + Vite frontend, also shipped as a Capacitor 7 Android APK (`frontend/android`); Flask backend on
  Cloud Run; uploads go by signed URL straight to Cloud Storage (Cloud Run caps request bodies at 32 MiB); analysis is
  dispatched through Cloud Tasks to a Cloud Run engine.
- Identity is optional: a user can be just an email address (`POST /upload` accepts `email` or `user_id`).
- Target flow: pair the device once from a phone, with no laptop, and from then on clips land in that person's t30g
  account without opening another app.

## 6. Constraints

- **Budget:** about $1,000, flexible. The owner did not say whether that is the cost of one unit or the whole
  prototype effort, so every plan is costed both ways.
- **Quantity:** 1 to 3 working prototypes. Not a product for sale.
- **Builder:** one software engineer, strong in Python, TypeScript, cloud and computer vision. Assume no PCB layout
  and no CAD experience; a plan must say which skills are bought and which are learned.
- **Location:** United States (shipping, import duty and radio rules follow from that).
- **On the face:** wearable for 2+ hours, a lithium cell beside the head must be handled safely, and a visible
  recording light is expected.
