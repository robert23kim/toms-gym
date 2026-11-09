# Judge: ball-colour-model on the 6 truth clips (2026-11-09)

Verdict: **fails** (pick rule: mean recall 74.2 < 85, and entry_err <= 3 on 1 of 6, need 4).

Run: `experiments/ball-colour-model/run.py <stem> --device mps`, fresh (no cached work for these stems existed), one
stem at a time via `work/judge_bcm/batch.py` (waits for any other experiment run.py to exit; 600 s per-stem timeout).
No crash, no path fix. Wall 10-36 s per clip. Scored with `L2/score_v2.py <track> <quarantine>/<stem>.json`.
All 6 truth files present; none skipped. Numbers only below; no truth coordinates.

| stem | ball branch | recall % | far recall % | entry_err | pin_row_err (frames) | median px err | path rms | pin row source |
|---|---|---|---|---|---|---|---|---|
| 104714 | dark | 100.0 | 100.0 | 3.0 | 34 | 5.1 | 0.74 | fallback |
| 110224 | dark | 100.0 | 100.0 | 10.3 | 10 | 2.4 | 1.19 | fallback |
| 111238 | dark | 100.0 | 100.0 | 5.5 | 21 | 3.3 | 0.69 | fallback |
| 111420 | dark | 45.0 | 0.0 | 4.2 | 8 | 19.8 | 0.86 | fallback |
| 112638 | colour | 0.0 | 0.0 | n/a (no entry) | 12 | n/a | n/a | fallback |
| 113716 | dark | 100.0 | 100.0 | 9.55 | 14 | 2.3 | 0.75 | fallback |

Means (over stems with a value): recall 74.2, far recall 66.7, entry_err 6.51 (5 stems), pin_row_err 16.5.
entry_err <= 3: 1/6 (104714 at exactly 3.0). entry_err <= 2.5 (RULES truth-clip bar): 0/6. pin_row_err <= 4: 0/6.

## What failed
- **Colour branch, first real use: 0 points.** 112638 took the `colour` branch (model from 3 frames, chroma far from
  wood); the mask found nothing, LGB had no seed, lane fell back too: detection 0.0. The NOTES flagged this branch as
  untested on 0/8 dev clips; on the truth set it is 1/6 and it fails outright.
- **Far end on 111420:** recall 45, far recall 0, median 19.8 px. Check image: the circle is on the ball at 20 ft,
  under it at 40 ft, and on empty lane well short of the ball at 55 ft (SAM re-prompt lag, the same drift the NOTES
  saw on 105652/115157 in dev).
- **Pin row is a fallback on 6/6** (J2 fails on every throw): no held crossing detected; the cut pin_hit is used.
  Checked (differences only): on all 5 tracked clips the truth pin-row frame is 8-34 frames AFTER the cut pin_hit, the
  truth path runs to its pin row (truth entry = its last path board within 0.6), and the track's board series ends
  before the truth pin row on 4/5 (2-11 frames short; 111238 runs 6 past it). The track's own tail is flat (110224
  ~7-11, 113716 ~9-11 over its last 20 frames), so the entry miss is the ball's late movement in frames the tracker never
  covers, not a lane-mapping or frame-jitter error on covered frames (path rms 0.7-1.2 where scored).
- **Recall overstates coverage:** score_v2 windows use the truth pin_hit, which equals the cut pin_hit (window_err 0,0),
  so recall 100 on four clips is scored only up to the early pin_hit; the last 8-34 frames before the pin row are
  unscored by recall and are exactly where entry is decided.
- Dev proxy claim vs truth: dev detection 0.986 held on the 4 dark clean clips (recall 100), but pin row 4/8 on dev
  became 0/6 here, and the colour branch broke a whole clip.

## Overlay read (J6, two required + one extra)
- 110224 (`overlays/check__` + `final__`): visual read: circle on the ball at 20/40/55 ft (depth labels come from the
  fallback pin-row frame, so "55 ft" is approximate). Number read, not visual: the green path ends near board 10
  about 7 frames before the truth pin row, entry_err 10.3, so it does not end where the ball is at the pin row.
- 111420: on the ball at 20 ft only; at 40 ft below it, at 55 ft on empty lane short of the ball. Does not end at the
  ball.
- 113716 (extra): on the ball at all three depths; entry_err 9.55 regardless, consistent with the pin-row frame,
  not the ball, being the error.

## What would move it
1. The named change: track past the cut pin_hit to a detected pin row (LGB SAM re-prompts stop at k_pin; the cut
   pin_hit is 8-34 frames early on these clips). The ball detection itself is close (4 dark clips at recall 100, path
   rms <= 1.2); what fails is the two outputs downstream of it, so this stage could also be composed with a
   pin-row/far-end stage that reaches the real pin row.
2. The colour branch needs a working mask before it can be the session ball stage (1 of 6 truth clips is a coloured
   ball).

Quarantine: this judge opened the truth folder only through score_v2.py and a key listing; the repo gets numbers only.
Files: `results/judge_ball-colour-model.json`, `work/judge_bcm/` (batch runner, per-stem logs; gitignored), tracks in
`experiments/ball-colour-model/tracks/`, overlays `experiments/ball-colour-model/overlays/{final,check}__<stem>.jpg`.
