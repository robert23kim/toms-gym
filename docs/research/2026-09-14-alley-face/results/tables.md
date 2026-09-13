## E1 constellation

| feature | lane position (in) | count | source | visible on sample_input (pre-hit) | visible on Chardie (pre-hit) | visible on tom_old (pre-hit) |
|---|---|---|---|---|---|---|
| foul-line corners | (0, 0), (41.5, 0) | 2 | rule | 2/2 | 2/2 | 2/2 |
| foul-line dots (approach side) | y = -0.15 ft (-1.8 in), x = 20.75 + k x 5.32 in (5 boards), k = -3..3 | 7 (7 observed) | measured on sample_input f117 (+ pooled frames), symmetric completion; measured centre -0.66 in from the lane centre | 6/7 | 0/7 | 7/7 |
| guide dots | y = 7.04 ft (84.5 in), x = 20.75 + k x 3.19 in (3 boards), k = -5..5 | 11 (8 observed) | measured on tom_old f165 (+ pooled frames), symmetric completion; measured centre -0.41 in from the lane centre | 0/11 | 0/11 | 8/11 |
| approach dots | y = -11.74 ft (-140.9 in), x = 20.75 + k x 5.32 in (5 boards), k = -3..3 | 7 (5 observed) | measured on Chardie f130 (+ pooled frames), symmetric completion; measured centre -1.78 in from the lane centre | 0/7 | 5/7 | 0/7 |
| seven arrows | boards 5..35, V centre 15.52 ft, 0.45 ft per 5 boards (per video: sample_input 15.36/0.48, Chardie 15.42/0.37, tom_old 15.78/0.50) | 7 | rule-book boards, depth from loop 4 | 7/7 | 5/7 | 7/7 |
| ten pin bases | rule-book rack, head pin at 60 ft | 10 | rule | 10/10 | 10/10 | 10/10 |
| gutter edges, foul line | x = 0, x = 41.5, y = 0 | lines | rule | all | all | all |

## E1 visibility timeline

| video | class | points | clear per frame (median, throw) | frames with >= half clear (of throw frames) | hidden by the bowler | by the ball | pins in motion |
|---|---|---|---|---|---|---|---|
| sample_input | foul | 2 | 2 | 82/82 | 31-125 (42 frames) | - | - |
| sample_input | fdot | 7 | 5 | 68/82 | 34-121 (83 frames) | 43-43 (1 frames) | - |
| sample_input | dot | 11 | 11 | 82/82 | 41-102 (31 frames) | 49-53 (5 frames) | - |
| sample_input | adot | 7 | 0 | 0/82 | - | - | - |
| sample_input | arrow | 7 | 7 | 82/82 | 89-101 (2 frames) | 59-63 (5 frames) | - |
| sample_input | pin | 10 | 10 | 81/82 | - | 114-128 (15 frames) | 119-179 (61 frames) |
| Chardie | foul | 2 | 1 | 75/75 | 45-128 (64 frames) | - | - |
| Chardie | fdot | 7 | 4 | 66/75 | 47-122 (76 frames) | - | - |
| Chardie | dot | 11 | 6 | 38/75 | 56-111 (56 frames) | 68-74 (7 frames) | - |
| Chardie | adot | 7 | 5 | 75/75 | - | - | - |
| Chardie | arrow | 7 | 6 | 51/75 | 58-106 (43 frames) | 74-83 (10 frames) | - |
| Chardie | pin | 10 | 6 | 40/75 | 75-93 (19 frames) | 101-134 (34 frames) | 135-170 (36 frames) |
| tom_old | foul | 2 | 2 | 154/154 | 8-154 (44 frames) | - | - |
| tom_old | fdot | 7 | 5 | 127/154 | 10-141 (132 frames) | - | - |
| tom_old | dot | 11 | 11 | 154/154 | 22-121 (55 frames) | 30-36 (7 frames) | - |
| tom_old | adot | 7 | 0 | 0/154 | - | - | - |
| tom_old | arrow | 7 | 7 | 154/154 | 61-91 (5 frames) | 43-58 (16 frames) | - |
| tom_old | pin | 10 | 10 | 104/154 | - | 115-171 (56 frames) | 171-408 (238 frames) |

## E2 candidates

| video | frames | ms | dark marks / frame (strong) | precision of the pool (strong) | rack blobs / frame, precision | rack recall (standing) | arrow recall, px | guide dots | foul dots | approach dots | true gutter / foul-line segments per frame |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sample_input | 180 | 206 | 1388 (826) | 0.006 (0.007) | 34.4, 0.019 | 0.958 | 0.69, 2.6 | 0.16 | 0.28 | - | L 1.24 R 0.48 foul 0.9 |
| Chardie | 171 | 89 | 663 (383) | 0.006 (0.004) | 20.3, 0.035 | 0.896 | 0.44, 2.0 | 0.00 | 0.09 | 0.03 | L 1.36 R 1.13 foul 0.01 |
| tom_old | 409 | 78 | 532 (274) | 0.033 (0.049) | 26.9, 0.011 | 0.655 | 0.96, 3.2 | 0.43 | 0.96 | - | L 2.2 R 2.57 foul 3.17 |
| bowling_video | 139 (every 3rd) | 225 | 1536 (924) | - | 26.2, - | - | - | - | - | - | - |
| IMG_0242 | 310 (every 3rd) | 74 | 458 (260) | - | 14.0, - | - | - | - | - | - | - |

## E3 finding the face

| video | feature set | frames | lanes found / frame (median) | right lane found (throw frames) | top score is the right lane | bowler's feet pick it | frame centre | widest | board MAE median: annotated / pins / all | tail (pins) | pre-hit (pins) | far width err px | far centre err px | ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sample_input | arrows+dots+rack+gutters | 180 | 5 | 0.26 | 0.01 | 0.23 | 0.00 | 0.00 | 2.41 / 1.73 / 1.74 | 0.56 | 1.43 | 11.5 | 0.8 | 3469 |
| sample_input | arrows (every 5th frame) | 36 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 2870 |
| sample_input | arrows+dots (every 5th frame) | 36 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 3240 |
| sample_input | arrows+rack (every 5th frame) | 36 | 4 | 0.25 | 0.00 | 0.20 | 0.00 | 0.00 | 2.10 / 1.73 / 1.73 | 0.64 | - | 11.6 | 0.8 | 2894 |
| sample_input | arrows+dots+rack (every 5th frame) | 36 | 5 | 0.25 | 0.00 | 0.20 | 0.00 | 0.00 | 2.10 / 1.73 / 1.73 | 0.64 | - | 11.6 | 0.8 | 3446 |
| Chardie | arrows+dots+rack+gutters | 171 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 1323 |
| Chardie | arrows (every 5th frame) | 35 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 938 |
| Chardie | arrows+dots (every 5th frame) | 35 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 1300 |
| Chardie | arrows+rack (every 5th frame) | 35 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 944 |
| Chardie | arrows+dots+rack (every 5th frame) | 35 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 1339 |
| tom_old | arrows+dots+rack+gutters | 409 | 5 | 0.50 | 0.40 | 0.28 | 0.29 | 0.09 | 1.29 / 0.62 / 0.65 | 0.49 | 0.31 | 2.0 | 0.7 | 995 |
| tom_old | arrows (every 5th frame) | 82 | 0 | 0.13 | 0.13 | 0.50 | 0.50 | 0.50 | 4.32 / 2.83 / 2.79 | 3.38 | - | 51.2 | 10.0 | 294 |
| tom_old | arrows+dots (every 5th frame) | 82 | 1 | 0.13 | 0.07 | 0.09 | 0.17 | 0.12 | 6.46 / 5.43 / 5.39 | 9.14 | - | 39.0 | 13.6 | 616 |
| tom_old | arrows+rack (every 5th frame) | 82 | 4 | 0.45 | 0.35 | 0.23 | 0.41 | 0.14 | 1.29 / 0.58 / 0.59 | 0.43 | - | 3.0 | 0.7 | 353 |
| tom_old | arrows+dots+rack (every 5th frame) | 82 | 4 | 0.55 | 0.39 | 0.29 | 0.23 | 0.13 | 1.28 / 0.53 / 0.57 | 0.36 | - | 0.9 | 0.7 | 1003 |
| tom_old | arrows+dots+rack+gutters - pool = class heatmap model's arrows (held-out) | 409 | 3 | 0.56 | 0.56 | 0.46 | 0.65 | 0.14 | 1.77 / 0.43 / 0.43 | 0.40 | 0.41 | 1.5 | 0.5 | 14 |
| tom_old | arrows+dots+rack+gutters - pool = landmark heatmap model's arrows (held-out) | 409 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 0 |

| video | feature set | frames | lanes / frame (median, max) | frames with >= 1 lane | ball's lane found | ball's lane is the top score | ms |
|---|---|---|---|---|---|---|---|
| bowling_video | arrows+dots+rack+gutters | 139 | 4, 10 | 0.98 | 0.55 | 0.10 | 4499 |
| IMG_0242 | arrows+dots+rack+gutters | 310 | 1, 6 | 0.84 | - | - | 429 |

## E4 aligning the face

| video | variant | frames | throw median: annotated / pins / all | tail (pins) | pre-hit (pins) | last (pins) | far width err px | far centre err px | near corners err px (L / R) |
|---|---|---|---|---|---|---|---|---|---|
| sample_input | e3 | 40 | 2.41 / 1.73 / 1.74 | 0.56 | 1.43 | - | 11.5 | 0.8 | - |
| sample_input | rows+pins | 39 | 2.56 / 1.92 / 1.94 | 0.83 | 1.47 | - | 4.3 | 1.0 | 12.3 / 34.3 |
| sample_input | refit | 38 | 2.56 / 1.92 / 1.94 | 0.83 | 1.47 | - | 4.3 | 1.0 | 12.3 / 34.3 |
| sample_input | no-near | 38 | 2.56 / 1.92 / 1.94 | 0.83 | 1.47 | - | 4.3 | 1.0 | 12.3 / 34.3 |
| sample_input | rows-only | 19 | 27.07 / 26.37 / 26.39 | 22.03 | 136.68 | - | 49.2 | 753.1 | 674.1 / 938.8 |
| sample_input | pins-pooled | 38 | 2.48 / 1.87 / 1.89 | 0.81 | 1.45 | - | 4.0 | 1.0 | 13.0 / 33.2 |
| Chardie | e3 | 6 | - / - / - | - | - | - | - | - | - |
| Chardie | rows+pins | 6 | - / - / - | - | - | - | - | - | - |
| Chardie | refit | 6 | - / - / - | - | - | - | - | - | - |
| Chardie | no-near | 6 | - / - / - | - | - | - | - | - | - |
| Chardie | rows-only | 1 | - / - / - | - | - | - | - | - | - |
| Chardie | pins-pooled | 6 | - / - / - | - | - | - | - | - | - |
| tom_old | e3 | 187 | 1.29 / 0.62 / 0.65 | 0.49 | 0.31 | - | 2.0 | 0.7 | - |
| tom_old | rows+pins | 178 | 1.27 / 0.81 / 0.85 | 0.85 | 0.25 | - | 2.6 | 1.2 | 14.4 / 24.4 |
| tom_old | refit | 177 | 1.27 / 0.81 / 0.84 | 0.85 | 0.29 | - | 2.5 | 1.2 | 14.4 / 24.2 |
| tom_old | no-near | 177 | 1.27 / 0.81 / 0.84 | 0.85 | 0.29 | - | 2.5 | 1.2 | 14.4 / 24.2 |
| tom_old | rows-only | 172 | 2.56 / 2.21 / 2.20 | 2.33 | 3.82 | - | 21.4 | 9.8 | 38.8 / 35.0 |
| tom_old | pins-pooled | 178 | 1.10 / 0.81 / 0.85 | 0.85 | 0.33 | - | 2.0 | 1.3 | 11.5 / 22.6 |

## E5 persistence

| video | frames | camera fits | landmarks in common (median; after the hit) | pooled rack (pins, frames) | lane on every frame: throw median annotated / pins / all | tail (pins) | after the hit (pins) | last (pins) | camera vs hand corners px: landmarks / ORB (pin end) | max |
|---|---|---|---|---|---|---|---|---|---|---|
| sample_input | 40 | 39 | 16; 5 | 10, 36 | 2.51 / 1.91 / 1.93 | 0.81 | - (0 f) | - | 10.42 / 4.15 (7.88 / 3.7) | 138.0 / 15.05 |
| Chardie | 6 | 6 | 14; - | 10, 6 | - / - / - | - | - (0 f) | - | - | - |
| tom_old | 187 | 185 | 7; 7 | 10, 74 | 1.09 / 0.81 / 0.85 | 0.90 | - (0 f) | - | - | - |

## E6 heatmap model

| model | held-out video | class | clear points | recall (6 px) | px err median | precision | classical E2 recall, same frames | in-distribution recall (training videos' held-back frames) |
|---|---|---|---|---|---|---|---|---|
| class | tom_old | foul | 774 | 0.04 | 5.6 | 0.400 | - | 0.95 |
| class | tom_old | fdot | 2528 | 0.00 | - | 0.000 | 0.92 | 0.73 |
| class | tom_old | dot | 4280 | 0.00 | - | 0.000 | 0.38 | 0.73 |
| class | tom_old | adot | 0 | - | - | 0.000 | - | 0.00 |
| class | tom_old | arrow | 2824 | 0.92 | 3.7 | 0.853 | 0.95 | 0.98 |
| class | tom_old | pin | 1306 | 0.37 | 2.7 | 0.442 | - | 0.17 |
| landmark | tom_old | foul | 774 | 0.06 | 3.8 | 0.880 | - | 1.00 |
| landmark | tom_old | fdot | 2528 | 0.00 | 4.7 | 0.250 | 0.92 | 0.77 |
| landmark | tom_old | dot | 4280 | 0.00 | - | 0.000 | 0.38 | 0.96 |
| landmark | tom_old | adot | 0 | - | - | - | - | 0.00 |
| landmark | tom_old | arrow | 2824 | 0.20 | 2.5 | 0.151 | 0.95 | 0.98 |
| landmark | tom_old | pin | 1306 | 0.96 | 3.6 | 0.152 | - | 1.00 |

| model | held-out video | frames fitted (throw) | named points / frame | constellation fit: throw median annotated / pins / all | tail (pins) | pre-hit (pins) | far width err px | ms / frame |
|---|---|---|---|---|---|---|---|---|
| landmark | tom_old | 84 | 8 | 11.96 / 12.57 / 12.61 | 14.03 | 10.32 | 137.1 | 74 |

