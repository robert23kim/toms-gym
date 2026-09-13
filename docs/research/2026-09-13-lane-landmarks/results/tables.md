## E1 truth

| video | px/board at pins | far width px: hand / pins / all | far centre px: hand / pins / all | hand TL, TR vs pins (px = boards) | annotated quad MAE vs pins (tail) | vs all (tail) | arrows found, abs err boards hand / pins | pins vs arrows agreement (all-fit resid, in) | repeatability over 3 frames (centre px std, width ratio std) |
|---|---|---|---|---|---|---|---|---|---|
| sample_input f117 | 1.56 | 59.4 / 54.0 / 54.5 | 548.7 / 547.3 / 547.3 | -1.4 = -0.9, +4.1 = +2.6 | 0.68 (1.07) | 0.65 (1.05) | 7/7, 0.33 / 0.18 | arrows 0.14, pins 0.37 | 0.1, 0.0039 |
| Chardie f132 | 1.01 | 38.5 / 36.8 / 37.4 | 424.7 / 426.4 / 425.8 | -2.6 = -2.6, -1.2 = -1.2 | 0.58 (1.09) | 0.34 (0.64) | 5/7, 0.29 / 0.5 | arrows 0.57, pins 0.45 | 0.29, 0.0008 |
| tom_old f169 | 1.68 | 63.9 / 68.2 / 67.8 | 528.9 / 532.8 / 532.9 | -2.8 = -1.7, -6.0 = -3.6 | 1.46 (2.36) | 1.5 (2.44) | 7/7, 0.31 / 0.26 | arrows 0.26, pins 0.38 | 0.49, 0.0085 |


## Baselines re-scored

| method | video | frame(s) | MAE vs annotated | vs pins | vs all landmarks | tail (last 20 % of path) vs pins | far width err px vs pins | far centre err px vs pins |
|---|---|---|---|---|---|---|---|---|
| SAM 2 base, even3 ball-path prompts (loop 2) pre-hit | sample_input | f117 | 0.31 | 0.48 | 0.46 | 0.99 | -0.4 | +1.6 |
| SAM 2 base, even3 ball-path prompts (loop 2) pre-hit | Chardie | f132 | 0.68 | 0.49 | 0.39 | 0.16 | -3.2 | +1.1 |
| SAM 2 base, even3 ball-path prompts (loop 2) pre-hit | tom_old | f169 | 2.26 | 0.73 | 0.69 | 1.42 | -6.9 | +2.9 |
| SAM 2 base, even3 ball-path prompts (loop 2) last | sample_input | f128 | 0.25 | 0.42 | 0.41 | 0.91 | -2.2 | +1.5 |
| SAM 2 base, even3 ball-path prompts (loop 2) last | Chardie | f170 | 0.39 | 0.81 | 0.54 | 0.63 | -3.2 | +0.7 |
| SAM 2 base, even3 ball-path prompts (loop 2) last | tom_old | f171 | 1.19 | 0.42 | 0.46 | 0.25 | -5.6 | +0.1 |
| SAM 2 base, far-end crop zoom_lo (loop 2) pre-hit | sample_input | f117 | 0.89 | 0.15 | 0.17 | 0.15 | +1.3 | -0.5 |
| SAM 2 base, far-end crop zoom_lo (loop 2) pre-hit | Chardie | f132 | 0.37 | 0.89 | 0.62 | 0.82 | -1.3 | -0.1 |
| SAM 2 base, far-end crop zoom_lo (loop 2) pre-hit | tom_old | f169 | 1.87 | 0.33 | 0.29 | 0.7 | -6.7 | +1.7 |
| SAM 2 base, far-end crop zoom_lo (loop 2) last | sample_input | f128 | 0.7 | 0.14 | 0.14 | 0.1 | -1.0 | -0.2 |
| SAM 2 base, far-end crop zoom_lo (loop 2) last | Chardie | f170 | 0.31 | 0.97 | 0.7 | 1.01 | -1.2 | -0.1 |
| SAM 2 base, far-end crop zoom_lo (loop 2) last | tom_old | f171 | 0.51 | 1.16 | 1.2 | 1.66 | -1.4 | -2.6 |
| SAM 2 + pin centre pins_m (loop 2) pre-hit | sample_input | f117 | 0.2 | 0.55 | 0.53 | 0.86 | +8.1 | +0.5 |
| SAM 2 + pin centre pins_m (loop 2) pre-hit | Chardie | f132 | 0.9 | 0.33 | 0.45 | 0.28 | +1.3 | +0.6 |
| SAM 2 + pin centre pins_m (loop 2) pre-hit | tom_old | f169 | 0.62 | 0.93 | 0.96 | 1.57 | -6.9 | -2.1 |
| SAM 2 pose+pin landmark prompts (loop 2) pre-hit | sample_input | f117 | 0.39 | 0.37 | 0.35 | 0.71 | +1.5 | +0.9 |
| SAM 2 pose+pin landmark prompts (loop 2) pre-hit | Chardie | f132 | 0.88 | 0.4 | 0.46 | 0.42 | -2.8 | +1.4 |
| SAM 2 pose+pin landmark prompts (loop 2) pre-hit | tom_old | f169 | 2.39 | 0.85 | 0.81 | 1.58 | -4.9 | +3.2 |
| student seg640 gated (loop 3) throw median | sample_input | 180 frames | 1.83 | 1.19 | 1.21 | 2.68 | +10.6 | -6.1 |
| student seg640 gated (loop 3) pre-hit / last | sample_input | pre-hit / last | 1.59 / 2.11 | 0.91 / 1.58 | 0.93 / 1.59 | | | |
| student seg640 gated (loop 3) throw median | Chardie | 162 frames | 0.88 | 0.64 | 0.52 | 0.62 | +5.7 | -0.5 |
| student seg640 gated (loop 3) pre-hit / last | Chardie | pre-hit / last | 0.96 / 1.29 | 0.35 / 0.57 | 0.5 / 0.79 | | | |
| student seg640 gated (loop 3) throw median | tom_old | 406 frames | 3.15 | 1.61 | 1.57 | 1.96 | +4.2 | +4.8 |
| student seg640 gated (loop 3) pre-hit / last | tom_old | pre-hit / last | 3.29 / 1.89 | 1.76 / 0.35 | 1.72 / 0.31 | | | |
| student seg640 +teacher gated (loop 3) throw median | sample_input | 153 frames | 1.18 | 0.51 | 0.52 | 0.79 | +8.7 | -1.8 |
| student seg640 +teacher gated (loop 3) pre-hit / last | sample_input | pre-hit / last | 0.99 / 1.08 | 0.28 / 0.53 | 0.29 / 0.53 | | | |
| student seg640 +teacher gated (loop 3) throw median | Chardie | 139 frames | 0.95 | 0.65 | 0.57 | 0.41 | +2.5 | +0.1 |
| student seg640 +teacher gated (loop 3) pre-hit / last | Chardie | pre-hit / last | 0.82 / 0.61 | 0.4 / 0.58 | 0.42 / 0.34 | | | |
| student seg640 +teacher gated (loop 3) throw median | tom_old | 405 frames | 3.16 | 1.62 | 1.58 | 2.25 | +1.7 | +4.8 |
| student seg640 +teacher gated (loop 3) pre-hit / last | tom_old | pre-hit / last | 3.13 / 1.79 | 1.6 / 0.26 | 1.56 / 0.22 | | | |
| student seg1024 gated (loop 3, tom_old only) throw median | tom_old | 291 frames | 0.91 | 0.64 | 0.68 | 1.27 | +2.7 | -1.9 |
| student seg1024 gated (loop 3, tom_old only) pre-hit / last | tom_old | pre-hit / last | None / 0.33 | None / 1.87 | None / 1.9 | | | |


## E2 detectors

| lane hypothesis | video | frames | pins: fired / standing | pins px err (median) | pin centre err (boards, med) | pin span err (boards, med) | alias frames (>3 boards) | arrows correct / frame | false / frame | arrow recall | arrow dx (boards, med) | ms pins / arrows |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| student seg640 gated (loop 3) | sample_input | 180 | 119 / 119 | 1.44 | 0.56 | 1.47 | 0 | 4.73 | 1.03 | 0.68 | 0.64 | 709 / 57 |
| student seg640 gated (loop 3) | Chardie | 162 | 120 / 126 | 0.81 | 0.69 | 0.14 | 6 | 5.04 | 0.48 | 0.72 | 0.77 | 617 / 51 |
| student seg640 gated (loop 3) | tom_old | 406 | 167 / 168 | 1.41 | 0.36 | 0.63 | 6 | 6.54 | 0.01 | 0.93 | 0.61 | 700 / 43 |
| student +teacher (loop 3) | sample_input | 153 | 92 / 92 | 1.37 | 0.68 | 0.50 | 0 | 5.48 | 1.31 | 0.78 | 0.63 | 706 / 64 |
| student +teacher (loop 3) | Chardie | 139 | 99 / 105 | 0.59 | 0.38 | 0.17 | 5 | 5.12 | 0.47 | 0.73 | 0.67 | 578 / 45 |
| student +teacher (loop 3) | tom_old | 405 | 168 / 169 | 1.42 | 0.36 | 0.63 | 6 | 6.60 | 0.01 | 0.94 | 0.61 | 701 / 44 |
| student 1024 (loop 3) | tom_old | 291 | 110 / 111 | 1.44 | 0.36 | 0.62 | 4 | 6.53 | 0.01 | 0.93 | 0.61 | 704 / 39 |
| two-class student 1024 (this loop) | tom_old | 409 | 169 / 171 | 1.43 | 0.36 | 0.63 | 7 | 6.36 | 0.08 | 0.91 | 0.61 | 699 / 36 |
| SAM 2 even3 (loop 2, 2 frames) | sample_input | 2 | 1 / 1 | 0.56 | 0.02 | 0.40 | 0 | 7.00 | 0.00 | 1.00 | 0.28 | 716 / 51 |
| SAM 2 even3 (loop 2, 2 frames) | Chardie | 2 | 1 / 1 | 0.46 | 0.26 | 0.15 | 0 | 6.50 | 0.00 | 0.93 | 0.46 | 455 / 50 |
| SAM 2 even3 (loop 2, 2 frames) | tom_old | 2 | 1 / 1 | 0.74 | 0.28 | 0.55 | 0 | 3.50 | 0.00 | 0.50 | 0.61 | 740 / 33 |
| SAM 2 crop (loop 2, 2 frames) | sample_input | 2 | 1 / 1 | 0.55 | 0.02 | 0.40 | 0 | 7.00 | 0.00 | 1.00 | 0.28 | 720 / 48 |
| SAM 2 crop (loop 2, 2 frames) | Chardie | 2 | 0 / 1 | - | - | - | 1 | 6.50 | 0.00 | 0.93 | 0.45 | 440 / 47 |
| SAM 2 crop (loop 2, 2 frames) | tom_old | 2 | 1 / 1 | 0.76 | 0.28 | 0.53 | 0 | 3.50 | 0.00 | 0.50 | 0.61 | 757 / 36 |

## E3 fits: loop3

| variant (loop3) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |
|---|---|---|---|---|---|---|---|---|
| corners | sample_input | 82 | 1.83 / 1.19 / 1.21 | 2.68 | 0.91 | 1.58 | 12.2 | 6.1 |
| snapcorners | sample_input | 82 | 2.72 / 1.97 / 1.99 | 2.86 | 1.72 | 2.33 | 12.2 | 6.1 |
| corners+arrows | sample_input | 82 | 2.15 / 1.50 / 1.52 | 3.04 | 1.27 | 1.12 | -4.5 | 3.9 |
| corners+pins | sample_input | 82 | 0.71 / 0.41 / 0.41 | 0.46 | 0.50 | 1.58 | 1.6 | 0.8 |
| corners+pins10 | sample_input | 82 | 0.77 / 0.37 / 0.37 | 0.46 | 0.48 | 1.58 | 0.7 | 0.7 |
| corners+arrows+pins10 | sample_input | 82 | 0.89 / 0.31 / 0.32 | 0.61 | 0.22 | 1.12 | 0.1 | 0.8 |
| foul+arrows+pins10 | sample_input | 81 | 0.88 / 0.31 / 0.32 | 0.61 | 0.22 | - | 0.1 | 0.8 |
| arrows+pins10 | sample_input | 81 | 1.10 / 0.40 / 0.42 | 0.62 | 0.05 | - | 0.7 | 0.7 |
| arrows+pins10+weakfoul | sample_input | 81 | 1.02 / 0.33 / 0.35 | 0.62 | 0.07 | - | -0.4 | 0.7 |
| arrows+pins10+top | sample_input | 81 | 1.10 / 0.40 / 0.41 | 0.62 | 0.05 | - | 0.7 | 0.7 |
| snapfoul+pins10 | sample_input | 81 | 1.66 / 0.98 / 1.00 | 0.85 | 0.66 | - | -1.6 | 0.7 |
| snapfoul+arrows+pins10 | sample_input | 81 | 1.34 / 0.63 / 0.65 | 0.63 | 0.31 | - | -1.0 | 0.7 |
| corners+arrows+pins10+carry | sample_input | 82 | 0.89 / 0.31 / 0.32 | 0.61 | 0.22 | - | 0.1 | 0.8 |
| corners+arrows+pins10+carryLM | sample_input | 82 | 0.89 / 0.31 / 0.32 | 0.61 | 0.22 | - | 0.1 | 0.8 |
| corners+arrows(1pass) | sample_input | 82 | 1.84 / 1.22 / 1.24 | 2.51 | 1.00 | 1.12 | -1.6 | 3.5 |
| foul+arrows+pins(1pass) | sample_input | 81 | 0.94 / 0.36 / 0.37 | 0.76 | 0.28 | - | 0.3 | 1.0 |
| corners | Chardie | 70 | 0.88 / 0.64 / 0.51 | 0.62 | 0.35 | 0.57 | 6.2 | 1.0 |
| snapcorners | Chardie | 70 | 0.95 / 0.49 / 0.49 | 0.56 | 0.33 | 0.60 | 6.2 | 1.0 |
| corners+arrows | Chardie | 70 | 0.75 / 0.71 / 0.56 | 0.68 | 0.50 | 0.38 | 2.8 | 1.1 |
| corners+pins | Chardie | 70 | 0.52 / 0.77 / 0.56 | 0.60 | 0.69 | 0.57 | -0.2 | 0.2 |
| corners+pins10 | Chardie | 70 | 0.53 / 0.78 / 0.52 | 0.63 | 0.67 | 0.57 | 0.1 | 0.2 |
| corners+arrows+pins10 | Chardie | 70 | 0.51 / 0.77 / 0.53 | 0.62 | 0.66 | 0.38 | 0.1 | 0.2 |
| foul+arrows+pins10 | Chardie | 62 | 0.50 / 0.75 / 0.49 | 0.56 | 0.66 | - | 0.1 | 0.2 |
| arrows+pins10 | Chardie | 60 | 0.50 / 0.72 / 0.46 | 0.57 | 0.55 | - | 0.0 | 0.1 |
| arrows+pins10+weakfoul | Chardie | 62 | 0.49 / 0.79 / 0.53 | 0.64 | 0.66 | - | 0.1 | 0.2 |
| arrows+pins10+top | Chardie | 60 | 0.50 / 0.72 / 0.46 | 0.57 | 0.55 | - | 0.0 | 0.1 |
| snapfoul+pins10 | Chardie | 62 | 0.55 / 0.51 / 0.42 | 0.54 | 0.65 | - | 0.5 | 0.2 |
| snapfoul+arrows+pins10 | Chardie | 62 | 0.52 / 0.60 / 0.41 | 0.55 | 0.66 | - | 0.3 | 0.2 |
| corners+arrows+pins10+carry | Chardie | 70 | 0.51 / 0.76 / 0.53 | 0.54 | 0.66 | 0.83 | 0.1 | 0.2 |
| corners+arrows+pins10+carryLM | Chardie | 70 | 0.51 / 0.77 / 0.53 | 0.65 | 0.66 | 0.86 | 0.1 | 0.2 |
| corners+arrows(1pass) | Chardie | 70 | 0.78 / 0.73 / 0.56 | 0.69 | 0.49 | 0.38 | 2.9 | 1.1 |
| foul+arrows+pins(1pass) | Chardie | 62 | 0.55 / 0.72 / 0.47 | 0.53 | 0.64 | - | -0.1 | 0.2 |
| corners | tom_old | 151 | 3.15 / 1.61 / 1.57 | 1.96 | 1.76 | 0.35 | 3.4 | 4.1 |
| snapcorners | tom_old | 151 | 2.69 / 1.18 / 1.14 | 1.96 | 1.26 | 0.33 | 3.4 | 4.1 |
| corners+arrows | tom_old | 151 | 0.45 / 1.77 / 1.80 | 3.45 | 1.75 | 0.35 | -1.1 | 6.0 |
| corners+pins | tom_old | 151 | 1.63 / 0.37 / 0.38 | 0.53 | 0.38 | 0.35 | 2.2 | 0.7 |
| corners+pins10 | tom_old | 151 | 1.51 / 0.41 / 0.43 | 0.71 | 0.51 | 0.35 | 1.1 | 1.0 |
| corners+arrows+pins10 | tom_old | 151 | 1.23 / 0.41 / 0.44 | 0.90 | 0.15 | 0.35 | 1.0 | 1.4 |
| foul+arrows+pins10 | tom_old | 143 | 1.23 / 0.41 / 0.44 | 0.90 | 0.15 | - | 1.0 | 1.4 |
| arrows+pins10 | tom_old | 143 | 1.24 / 0.30 / 0.34 | 0.58 | 0.19 | - | 1.1 | 0.7 |
| arrows+pins10+weakfoul | tom_old | 143 | 1.09 / 0.44 / 0.48 | 0.78 | 0.12 | - | 0.6 | 1.1 |
| arrows+pins10+top | tom_old | 143 | 1.24 / 0.30 / 0.33 | 0.57 | 0.19 | - | 1.1 | 0.7 |
| snapfoul+pins10 | tom_old | 143 | 1.01 / 0.58 / 0.62 | 0.77 | 0.14 | - | 0.7 | 1.1 |
| snapfoul+arrows+pins10 | tom_old | 143 | 1.05 / 0.51 / 0.55 | 0.73 | 0.14 | - | 0.6 | 1.0 |
| corners+arrows+pins10+carry | tom_old | 151 | 1.23 / 0.41 / 0.44 | 0.90 | 0.15 | 0.31 | 0.9 | 1.3 |
| corners+arrows+pins10+carryLM | tom_old | 151 | 1.23 / 0.41 / 0.44 | 0.90 | 0.15 | 0.35 | 1.0 | 1.4 |
| corners+arrows(1pass) | tom_old | 151 | 0.44 / 1.77 / 1.80 | 3.46 | 1.75 | 0.35 | -1.0 | 6.0 |
| foul+arrows+pins(1pass) | tom_old | 143 | 0.98 / 0.65 / 0.68 | 1.38 | 0.51 | - | 1.1 | 2.3 |


| dropped landmark (loop3, foul+arrows+pins base) | sample_input throw median (pins) / tail | Chardie throw median (pins) / tail | tom_old throw median (pins) / tail |
|---|---|---|---|
| foul+arrows+pins | 0.39 / 0.84 | 0.74 / 0.56 | 0.65 / 1.38 |
| foul+arrows+pins10 | 0.31 / 0.61 | 0.75 / 0.56 | 0.41 / 0.90 |
| drop-arrow_5 | 0.35 / 0.72 | 0.74 / 0.56 | 0.60 / 1.30 |
| drop-arrow_10 | 0.36 / 0.77 | 0.72 / 0.56 | 0.60 / 1.30 |
| drop-arrow_15 | 0.38 / 0.80 | 0.74 / 0.56 | 0.61 / 1.30 |
| drop-arrow_20 | 0.38 / 0.83 | 0.72 / 0.54 | 0.62 / 1.32 |
| drop-arrow_25 | 0.39 / 0.85 | 0.72 / 0.56 | 0.63 / 1.33 |
| drop-arrow_30 | 0.39 / 0.86 | 0.72 / 0.56 | 0.64 / 1.35 |
| drop-arrow_35 | 0.39 / 0.86 | 0.74 / 0.57 | 0.65 / 1.37 |
| drop-pin_7 | 0.31 / 0.60 | 0.75 / 0.56 | 0.42 / 0.93 |
| drop-pin_10 | 0.33 / 0.65 | 0.75 / 0.55 | 0.43 / 0.94 |

## E3 fits: loop3_plus

| variant (loop3_plus) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |
|---|---|---|---|---|---|---|---|---|
| corners | sample_input | 75 | 1.18 / 0.51 / 0.52 | 0.79 | 0.28 | 0.53 | 9.8 | 2.0 |
| snapcorners | sample_input | 75 | 1.49 / 0.80 / 0.82 | 0.84 | 0.53 | 0.79 | 9.8 | 2.0 |
| corners+arrows | sample_input | 75 | 0.62 / 0.40 / 0.40 | 0.48 | 0.55 | 0.47 | 3.3 | 0.9 |
| corners+pins | sample_input | 75 | 1.18 / 0.47 / 0.49 | 0.55 | 0.17 | 0.53 | 1.4 | 0.7 |
| corners+pins10 | sample_input | 75 | 1.20 / 0.51 / 0.52 | 0.58 | 0.17 | 0.53 | 0.5 | 0.7 |
| corners+arrows+pins10 | sample_input | 75 | 1.08 / 0.40 / 0.42 | 0.53 | 0.08 | 0.47 | 0.6 | 0.7 |
| foul+arrows+pins10 | sample_input | 74 | 1.08 / 0.40 / 0.42 | 0.53 | 0.08 | - | 0.6 | 0.7 |
| arrows+pins10 | sample_input | 74 | 1.10 / 0.41 / 0.43 | 0.64 | 0.04 | - | 0.7 | 0.7 |
| arrows+pins10+weakfoul | sample_input | 74 | 1.04 / 0.34 / 0.36 | 0.55 | 0.04 | - | 0.6 | 0.7 |
| arrows+pins10+top | sample_input | 74 | 1.10 / 0.41 / 0.42 | 0.64 | 0.03 | - | 0.7 | 0.8 |
| snapfoul+pins10 | sample_input | 74 | 1.55 / 0.84 / 0.86 | 0.72 | 0.49 | - | -0.5 | 0.8 |
| snapfoul+arrows+pins10 | sample_input | 74 | 1.23 / 0.55 / 0.56 | 0.55 | 0.21 | - | 0.1 | 0.7 |
| corners+arrows+pins10+carry | sample_input | 75 | 1.08 / 0.40 / 0.42 | 0.52 | 0.08 | 1.72 | 0.5 | 0.7 |
| corners+arrows+pins10+carryLM | sample_input | 75 | 1.08 / 0.40 / 0.42 | 0.53 | 0.08 | 0.38 | 0.5 | 0.7 |
| corners+arrows(1pass) | sample_input | 75 | 0.61 / 0.41 / 0.40 | 0.48 | 0.54 | 0.47 | 3.4 | 1.0 |
| foul+arrows+pins(1pass) | sample_input | 74 | 1.03 / 0.34 / 0.35 | 0.42 | 0.13 | - | 0.7 | 0.5 |
| corners | Chardie | 72 | 0.95 / 0.65 / 0.57 | 0.41 | 0.39 | 0.58 | 3.2 | 0.5 |
| snapcorners | Chardie | 72 | 0.95 / 0.64 / 0.55 | 0.47 | 0.36 | 0.41 | 3.2 | 0.5 |
| corners+arrows | Chardie | 72 | 0.86 / 0.66 / 0.59 | 0.61 | 0.46 | 0.42 | 2.3 | 1.1 |
| corners+pins | Chardie | 72 | 0.54 / 0.85 / 0.61 | 0.67 | 0.74 | 0.58 | -0.3 | 0.2 |
| corners+pins10 | Chardie | 72 | 0.55 / 0.82 / 0.58 | 0.64 | 0.71 | 0.58 | 0.1 | 0.2 |
| corners+arrows+pins10 | Chardie | 72 | 0.55 / 0.81 / 0.56 | 0.62 | 0.66 | 0.42 | 0.2 | 0.2 |
| foul+arrows+pins10 | Chardie | 64 | 0.52 / 0.78 / 0.52 | 0.59 | 0.66 | - | 0.2 | 0.2 |
| arrows+pins10 | Chardie | 62 | 0.49 / 0.71 / 0.44 | 0.56 | 0.56 | - | 0.0 | 0.2 |
| arrows+pins10+weakfoul | Chardie | 64 | 0.50 / 0.77 / 0.52 | 0.61 | 0.66 | - | 0.2 | 0.2 |
| arrows+pins10+top | Chardie | 62 | 0.49 / 0.71 / 0.44 | 0.56 | 0.56 | - | 0.0 | 0.2 |
| snapfoul+pins10 | Chardie | 64 | 0.56 / 0.64 / 0.48 | 0.53 | 0.70 | - | 0.7 | 0.2 |
| snapfoul+arrows+pins10 | Chardie | 64 | 0.53 / 0.69 / 0.45 | 0.53 | 0.68 | - | 0.6 | 0.2 |
| corners+arrows+pins10+carry | Chardie | 72 | 0.54 / 0.79 / 0.56 | 0.55 | 0.66 | 0.89 | 0.2 | 0.2 |
| corners+arrows+pins10+carryLM | Chardie | 72 | 0.54 / 0.81 / 0.56 | 0.63 | 0.66 | 0.88 | 0.2 | 0.2 |
| corners+arrows(1pass) | Chardie | 72 | 0.89 / 0.67 / 0.58 | 0.52 | 0.48 | 0.42 | 2.5 | 1.0 |
| foul+arrows+pins(1pass) | Chardie | 64 | 0.57 / 0.77 / 0.52 | 0.51 | 0.64 | - | 0.1 | 0.3 |
| corners | tom_old | 152 | 3.16 / 1.62 / 1.58 | 2.25 | 1.60 | 0.26 | 1.3 | 4.6 |
| snapcorners | tom_old | 152 | 2.79 / 1.27 / 1.23 | 2.25 | 1.19 | 0.34 | 1.3 | 4.6 |
| corners+arrows | tom_old | 152 | 0.26 / 1.39 / 1.42 | 2.68 | 1.46 | 0.26 | -1.4 | 4.5 |
| corners+pins | tom_old | 152 | 1.52 / 0.28 / 0.30 | 0.54 | 0.28 | 0.26 | 2.0 | 0.7 |
| corners+pins10 | tom_old | 152 | 1.40 / 0.35 / 0.37 | 0.72 | 0.42 | 0.26 | 1.1 | 1.0 |
| corners+arrows+pins10 | tom_old | 152 | 1.19 / 0.40 / 0.43 | 0.87 | 0.10 | 0.26 | 0.9 | 1.3 |
| foul+arrows+pins10 | tom_old | 146 | 1.19 / 0.40 / 0.43 | 0.86 | 0.10 | - | 0.9 | 1.3 |
| arrows+pins10 | tom_old | 146 | 1.25 / 0.29 / 0.34 | 0.58 | 0.19 | - | 1.1 | 0.8 |
| arrows+pins10+weakfoul | tom_old | 146 | 1.09 / 0.45 / 0.49 | 0.77 | 0.13 | - | 0.6 | 1.1 |
| arrows+pins10+top | tom_old | 145 | 1.25 / 0.29 / 0.33 | 0.58 | 0.19 | - | 1.1 | 0.7 |
| snapfoul+pins10 | tom_old | 146 | 1.01 / 0.58 / 0.62 | 0.77 | 0.14 | - | 0.7 | 1.1 |
| snapfoul+arrows+pins10 | tom_old | 146 | 1.06 / 0.51 / 0.55 | 0.74 | 0.15 | - | 0.6 | 1.0 |
| corners+arrows+pins10+carry | tom_old | 152 | 1.19 / 0.40 / 0.43 | 0.86 | 0.10 | 0.20 | 0.9 | 1.3 |
| corners+arrows+pins10+carryLM | tom_old | 152 | 1.19 / 0.40 / 0.43 | 0.86 | 0.10 | 0.26 | 0.9 | 1.3 |
| corners+arrows(1pass) | tom_old | 152 | 0.26 / 1.38 / 1.42 | 2.67 | 1.46 | 0.26 | -1.4 | 4.5 |
| foul+arrows+pins(1pass) | tom_old | 146 | 1.02 / 0.56 / 0.60 | 1.19 | 0.42 | - | 0.8 | 1.9 |


| dropped landmark (loop3_plus, foul+arrows+pins base) | sample_input throw median (pins) / tail | Chardie throw median (pins) / tail | tom_old throw median (pins) / tail |
|---|---|---|---|
| foul+arrows+pins | 0.34 / 0.42 | 0.74 / 0.51 | 0.56 / 1.19 |
| foul+arrows+pins10 | 0.40 / 0.53 | 0.78 / 0.59 | 0.40 / 0.86 |
| drop-arrow_5 | 0.35 / 0.43 | 0.75 / 0.52 | 0.52 / 1.12 |
| drop-arrow_10 | 0.35 / 0.43 | 0.75 / 0.52 | 0.52 / 1.12 |
| drop-arrow_15 | 0.35 / 0.43 | 0.74 / 0.51 | 0.53 / 1.13 |
| drop-arrow_20 | 0.35 / 0.43 | 0.73 / 0.52 | 0.54 / 1.15 |
| drop-arrow_25 | 0.34 / 0.42 | 0.72 / 0.49 | 0.54 / 1.15 |
| drop-arrow_30 | 0.34 / 0.43 | 0.76 / 0.52 | 0.56 / 1.17 |
| drop-arrow_35 | 0.34 / 0.42 | 0.74 / 0.52 | 0.56 / 1.19 |
| drop-pin_7 | 0.40 / 0.53 | 0.78 / 0.59 | 0.41 / 0.87 |
| drop-pin_10 | 0.39 / 0.51 | 0.78 / 0.57 | 0.42 / 0.90 |

## E3 fits: loop3_1024

| variant (loop3_1024) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |
|---|---|---|---|---|---|---|---|---|
| corners | tom_old | 98 | 0.91 / 0.64 / 0.68 | 1.27 | - | 1.86 | 2.4 | 2.1 |
| snapcorners | tom_old | 98 | 0.79 / 0.82 / 0.85 | 1.27 | - | 2.03 | 2.4 | 2.1 |
| corners+arrows | tom_old | 98 | 0.60 / 0.94 / 0.98 | 1.75 | - | 1.86 | -0.2 | 2.9 |
| corners+pins | tom_old | 98 | 1.28 / 0.29 / 0.32 | 0.66 | - | 1.86 | 2.1 | 0.9 |
| corners+pins10 | tom_old | 98 | 1.21 / 0.35 / 0.38 | 0.74 | - | 1.86 | 1.1 | 1.1 |
| corners+arrows+pins10 | tom_old | 98 | 1.11 / 0.43 / 0.46 | 0.81 | - | 1.86 | 0.9 | 1.2 |
| foul+arrows+pins10 | tom_old | 93 | 1.12 / 0.42 / 0.46 | 0.81 | - | - | 0.9 | 1.2 |
| arrows+pins10 | tom_old | 93 | 1.24 / 0.30 / 0.34 | 0.59 | - | - | 1.1 | 0.8 |
| arrows+pins10+weakfoul | tom_old | 93 | 1.07 / 0.46 / 0.50 | 0.76 | - | - | 0.9 | 1.1 |
| arrows+pins10+top | tom_old | 93 | 1.24 / 0.30 / 0.34 | 0.58 | - | - | 1.1 | 0.8 |
| snapfoul+pins10 | tom_old | 93 | 1.02 / 0.57 / 0.61 | 0.77 | - | - | 1.0 | 1.1 |
| snapfoul+arrows+pins10 | tom_old | 93 | 1.06 / 0.50 / 0.54 | 0.74 | - | - | 0.9 | 1.0 |
| corners+arrows+pins10+carry | tom_old | 98 | 1.12 / 0.42 / 0.46 | 0.80 | - | 0.43 | 0.9 | 1.2 |
| corners+arrows+pins10+carryLM | tom_old | 98 | 1.12 / 0.43 / 0.46 | 0.81 | - | 1.86 | 0.9 | 1.2 |
| corners+arrows(1pass) | tom_old | 98 | 0.60 / 0.94 / 0.98 | 1.75 | - | 1.86 | -0.2 | 2.9 |
| foul+arrows+pins(1pass) | tom_old | 93 | 1.06 / 0.48 / 0.52 | 0.93 | - | - | 0.9 | 1.4 |


| dropped landmark (loop3_1024, foul+arrows+pins base) | sample_input throw median (pins) / tail | Chardie throw median (pins) / tail | tom_old throw median (pins) / tail |
|---|---|---|---|
| foul+arrows+pins | - | - | 0.48 / 0.93 |
| foul+arrows+pins10 | - | - | 0.42 / 0.81 |
| drop-arrow_5 | - | - | 0.47 / 0.91 |
| drop-arrow_10 | - | - | 0.46 / 0.90 |
| drop-arrow_15 | - | - | 0.46 / 0.90 |
| drop-arrow_20 | - | - | 0.47 / 0.90 |
| drop-arrow_25 | - | - | 0.47 / 0.91 |
| drop-arrow_30 | - | - | 0.48 / 0.93 |
| drop-arrow_35 | - | - | 0.49 / 0.94 |
| drop-pin_7 | - | - | 0.43 / 0.82 |
| drop-pin_10 | - | - | 0.44 / 0.83 |

## E3 fits: seg2_1024

| variant (seg2_1024) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |
|---|---|---|---|---|---|---|---|---|
| corners | tom_old | 154 | 1.34 / 0.26 / 0.29 | 0.59 | 0.07 | 2.16 | 2.1 | 0.8 |
| snapcorners | tom_old | 154 | 1.19 / 0.43 / 0.47 | 0.59 | 0.24 | 2.33 | 2.1 | 0.8 |
| corners+arrows | tom_old | 154 | 0.76 / 0.90 / 0.94 | 1.64 | 0.72 | 2.16 | -0.2 | 2.7 |
| corners+pins | tom_old | 154 | 1.29 / 0.31 / 0.34 | 0.65 | 0.06 | 2.16 | 2.0 | 0.9 |
| corners+pins10 | tom_old | 154 | 1.23 / 0.39 / 0.42 | 0.73 | 0.20 | 2.16 | 1.1 | 1.0 |
| corners+arrows+pins10 | tom_old | 154 | 1.13 / 0.44 / 0.48 | 0.83 | 0.09 | 2.16 | 1.0 | 1.2 |
| foul+arrows+pins10 | tom_old | 145 | 1.13 / 0.44 / 0.47 | 0.81 | 0.09 | - | 1.0 | 1.2 |
| arrows+pins10 | tom_old | 141 | 1.24 / 0.31 / 0.35 | 0.60 | 0.19 | - | 1.1 | 0.8 |
| arrows+pins10+weakfoul | tom_old | 145 | 1.08 / 0.47 / 0.51 | 0.76 | 0.16 | - | 0.9 | 1.1 |
| arrows+pins10+top | tom_old | 141 | 1.24 / 0.31 / 0.35 | 0.60 | 0.19 | - | 1.1 | 0.8 |
| snapfoul+pins10 | tom_old | 145 | 1.03 / 0.57 / 0.61 | 0.75 | 0.16 | - | 1.0 | 1.0 |
| snapfoul+arrows+pins10 | tom_old | 145 | 1.07 / 0.51 / 0.54 | 0.75 | 0.17 | - | 0.9 | 1.1 |
| corners+arrows+pins10+carry | tom_old | 154 | 1.14 / 0.43 / 0.47 | 0.81 | 0.09 | 0.23 | 1.0 | 1.2 |
| corners+arrows+pins10+carryLM | tom_old | 154 | 1.13 / 0.44 / 0.47 | 0.81 | 0.09 | 2.16 | 1.0 | 1.2 |
| corners+arrows(1pass) | tom_old | 154 | 0.76 / 0.90 / 0.94 | 1.67 | 0.72 | 2.16 | -0.1 | 2.8 |
| foul+arrows+pins(1pass) | tom_old | 145 | 1.06 / 0.50 / 0.53 | 0.92 | 0.25 | - | 1.0 | 1.4 |


| dropped landmark (seg2_1024, foul+arrows+pins base) | sample_input throw median (pins) / tail | Chardie throw median (pins) / tail | tom_old throw median (pins) / tail |
|---|---|---|---|
| foul+arrows+pins | - | - | 0.50 / 0.92 |
| foul+arrows+pins10 | - | - | 0.44 / 0.81 |
| drop-arrow_5 | - | - | 0.48 / 0.90 |
| drop-arrow_10 | - | - | 0.47 / 0.90 |
| drop-arrow_15 | - | - | 0.48 / 0.89 |
| drop-arrow_20 | - | - | 0.48 / 0.89 |
| drop-arrow_25 | - | - | 0.48 / 0.90 |
| drop-arrow_30 | - | - | 0.49 / 0.90 |
| drop-arrow_35 | - | - | 0.50 / 0.92 |
| drop-pin_7 | - | - | 0.44 / 0.83 |
| drop-pin_10 | - | - | 0.45 / 0.83 |

## E3 fits: sam_even3_k

| variant (sam_even3_k) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |
|---|---|---|---|---|---|---|---|---|
| corners | sample_input | 1 | 0.31 / 0.48 / 0.46 | 0.99 | 0.48 | 0.42 | -0.4 | 1.6 |
| snapcorners | sample_input | 1 | 0.60 / 0.49 / 0.48 | 0.93 | 0.49 | 0.40 | -0.4 | 1.6 |
| corners+arrows | sample_input | 1 | 0.46 / 0.32 / 0.30 | 0.49 | 0.32 | 0.21 | 7.2 | 0.0 |
| corners+pins | sample_input | 1 | 0.82 / 0.10 / 0.12 | 0.05 | 0.10 | 0.42 | -0.2 | 0.0 |
| corners+pins10 | sample_input | 1 | 0.79 / 0.10 / 0.10 | 0.08 | 0.10 | 0.42 | 0.1 | 0.1 |
| corners+arrows+pins10 | sample_input | 1 | 0.75 / 0.09 / 0.09 | 0.12 | 0.09 | 0.21 | 0.8 | 0.0 |
| foul+arrows+pins10 | sample_input | 1 | 0.75 / 0.09 / 0.09 | 0.12 | 0.09 | - | 0.8 | 0.0 |
| arrows+pins10 | sample_input | 1 | 0.77 / 0.05 / 0.06 | 0.02 | 0.05 | - | 0.1 | 0.1 |
| arrows+pins10+weakfoul | sample_input | 1 | 0.70 / 0.10 / 0.08 | 0.16 | 0.10 | - | 1.1 | 0.1 |
| arrows+pins10+top | sample_input | 1 | 0.76 / 0.04 / 0.05 | 0.04 | 0.04 | - | 0.1 | 0.0 |
| snapfoul+pins10 | sample_input | 1 | 1.09 / 0.37 / 0.38 | 0.05 | 0.37 | - | 0.3 | 0.0 |
| snapfoul+arrows+pins10 | sample_input | 1 | 0.83 / 0.20 / 0.19 | 0.18 | 0.20 | - | 0.9 | 0.2 |
| corners+arrows+pins10+carry | sample_input | 1 | 0.75 / 0.09 / 0.09 | 0.12 | 0.09 | 1.78 | 0.8 | 0.0 |
| corners+arrows+pins10+carryLM | sample_input | 1 | 0.75 / 0.09 / 0.09 | 0.12 | 0.09 | 0.11 | 0.8 | 0.0 |
| corners+arrows(1pass) | sample_input | 1 | 0.46 / 0.32 / 0.30 | 0.49 | 0.32 | 0.21 | 7.2 | 0.0 |
| foul+arrows+pins(1pass) | sample_input | 1 | 0.76 / 0.08 / 0.08 | 0.09 | 0.08 | - | 1.0 | 0.0 |
| corners | Chardie | 1 | 0.68 / 0.49 / 0.39 | 0.16 | 0.49 | 0.81 | -3.3 | 1.2 |
| snapcorners | Chardie | 1 | 0.70 / 0.53 / 0.43 | 0.16 | 0.53 | 0.69 | -3.3 | 1.2 |
| corners+arrows | Chardie | 1 | 0.60 / 0.58 / 0.36 | 0.36 | 0.58 | 0.61 | 1.3 | 0.1 |
| corners+pins | Chardie | 1 | 0.49 / 0.72 / 0.45 | 0.52 | 0.72 | 0.81 | -0.5 | 0.1 |
| corners+pins10 | Chardie | 1 | 0.54 / 0.67 / 0.41 | 0.46 | 0.67 | 0.81 | 0.2 | 0.0 |
| corners+arrows+pins10 | Chardie | 1 | 0.55 / 0.66 / 0.41 | 0.44 | 0.66 | 0.61 | 0.4 | 0.0 |
| foul+arrows+pins10 | Chardie | 1 | 0.55 / 0.66 / 0.41 | 0.44 | 0.66 | - | 0.4 | 0.0 |
| arrows+pins10 | Chardie | 1 | 0.55 / 0.56 / 0.33 | 0.39 | 0.56 | - | 0.1 | 0.1 |
| arrows+pins10+weakfoul | Chardie | 1 | 0.56 / 0.65 / 0.40 | 0.42 | 0.65 | - | 0.4 | 0.0 |
| arrows+pins10+top | Chardie | 1 | 0.56 / 0.56 / 0.32 | 0.39 | 0.56 | - | 0.1 | 0.1 |
| snapfoul+pins10 | Chardie | 1 | 0.59 / 0.67 / 0.43 | 0.41 | 0.67 | - | 0.6 | 0.0 |
| snapfoul+arrows+pins10 | Chardie | 1 | 0.59 / 0.63 / 0.39 | 0.38 | 0.63 | - | 0.6 | 0.0 |
| corners+arrows+pins10+carry | Chardie | 1 | 0.55 / 0.66 / 0.41 | 0.44 | 0.66 | 0.69 | 0.4 | 0.0 |
| corners+arrows+pins10+carryLM | Chardie | 1 | 0.55 / 0.66 / 0.41 | 0.44 | 0.66 | 0.51 | 0.4 | 0.0 |
| corners+arrows(1pass) | Chardie | 1 | 0.60 / 0.58 / 0.35 | 0.36 | 0.58 | 0.61 | 1.3 | 0.1 |
| foul+arrows+pins(1pass) | Chardie | 1 | 0.53 / 0.67 / 0.41 | 0.46 | 0.67 | - | 0.2 | 0.0 |
| corners | tom_old | 2 | 1.72 / 0.57 / 0.57 | 0.83 | 0.73 | 0.42 | -6.2 | 1.6 |
| snapcorners | tom_old | 2 | 1.65 / 0.58 / 0.59 | 0.83 | 0.62 | 0.55 | -6.2 | 1.6 |
| corners+arrows | tom_old | 2 | 1.12 / 0.45 / 0.49 | 0.53 | 0.48 | 0.42 | -2.5 | 0.7 |
| corners+pins | tom_old | 2 | 1.32 / 0.26 / 0.30 | 0.20 | 0.09 | 0.42 | -3.2 | 0.1 |
| corners+pins10 | tom_old | 2 | 1.42 / 0.27 / 0.27 | 0.22 | 0.11 | 0.42 | -3.1 | 0.5 |
| corners+arrows+pins10 | tom_old | 2 | 1.36 / 0.26 / 0.27 | 0.18 | 0.09 | 0.42 | -3.0 | 0.4 |
| foul+arrows+pins10 | tom_old | 1 | 1.54 / 0.09 / 0.07 | 0.11 | 0.09 | - | -0.4 | 0.6 |
| arrows+pins10 | tom_old | 1 | 1.43 / 0.19 / 0.20 | 0.07 | 0.19 | - | -0.6 | 0.5 |
| arrows+pins10+weakfoul | tom_old | 1 | 1.52 / 0.15 / 0.14 | 0.17 | 0.15 | - | -0.4 | 0.7 |
| arrows+pins10+top | tom_old | 1 | 1.43 / 0.19 / 0.20 | 0.07 | 0.19 | - | -0.6 | 0.5 |
| snapfoul+pins10 | tom_old | 1 | 1.54 / 0.15 / 0.14 | 0.19 | 0.15 | - | -0.3 | 0.7 |
| snapfoul+arrows+pins10 | tom_old | 1 | 1.52 / 0.15 / 0.14 | 0.17 | 0.15 | - | -0.3 | 0.7 |
| corners+arrows+pins10+carry | tom_old | 2 | 1.54 / 0.15 / 0.14 | 0.17 | 0.09 | 0.22 | -0.2 | 0.8 |
| corners+arrows+pins10+carryLM | tom_old | 2 | 1.36 / 0.26 / 0.27 | 0.18 | 0.09 | 0.42 | -3.0 | 0.4 |
| corners+arrows(1pass) | tom_old | 2 | 1.12 / 0.45 / 0.49 | 0.53 | 0.48 | 0.42 | -2.5 | 0.7 |
| foul+arrows+pins(1pass) | tom_old | 1 | 1.29 / 0.25 / 0.29 | 0.37 | 0.25 | - | 0.3 | 0.3 |


| dropped landmark (sam_even3_k, foul+arrows+pins base) | sample_input throw median (pins) / tail | Chardie throw median (pins) / tail | tom_old throw median (pins) / tail |
|---|---|---|---|
| foul+arrows+pins | 0.08 / 0.09 | 0.67 / 0.46 | 0.25 / 0.37 |
| foul+arrows+pins10 | 0.09 / 0.12 | 0.66 / 0.44 | 0.09 / 0.11 |
| drop-arrow_5 | 0.10 / 0.04 | 0.70 / 0.50 | 0.26 / 0.38 |
| drop-arrow_10 | 0.09 / 0.06 | 0.68 / 0.48 | 0.24 / 0.37 |
| drop-arrow_15 | 0.09 / 0.07 | 0.68 / 0.47 | 0.24 / 0.35 |
| drop-arrow_20 | 0.08 / 0.08 | 0.66 / 0.45 | 0.23 / 0.35 |
| drop-arrow_25 | 0.08 / 0.10 | 0.66 / 0.45 | 0.23 / 0.34 |
| drop-arrow_30 | 0.08 / 0.11 | 0.66 / 0.45 | 0.24 / 0.35 |
| drop-arrow_35 | 0.08 / 0.12 | 0.67 / 0.46 | 0.25 / 0.37 |
| drop-pin_7 | 0.09 / 0.11 | 0.66 / 0.45 | 0.10 / 0.16 |
| drop-pin_10 | 0.11 / 0.17 | 0.64 / 0.42 | 0.10 / 0.14 |

## E3 fits: sam_zoom_lo_k

| variant (sam_zoom_lo_k) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |
|---|---|---|---|---|---|---|---|---|
| corners | sample_input | 1 | 0.89 / 0.15 / 0.17 | 0.15 | 0.15 | 0.14 | 1.3 | 0.5 |
| snapcorners | sample_input | 1 | 1.21 / 0.47 / 0.49 | 0.21 | 0.47 | 0.35 | 1.3 | 0.5 |
| corners+arrows | sample_input | 1 | 0.57 / 0.22 / 0.20 | 0.31 | 0.22 | 0.12 | 7.1 | 0.5 |
| corners+pins | sample_input | 1 | 0.82 / 0.09 / 0.11 | 0.02 | 0.09 | 0.14 | 0.0 | 0.1 |
| corners+pins10 | sample_input | 1 | 0.79 / 0.07 / 0.09 | 0.04 | 0.07 | 0.14 | 0.2 | 0.0 |
| corners+arrows+pins10 | sample_input | 1 | 0.76 / 0.07 / 0.07 | 0.07 | 0.07 | 0.12 | 0.8 | 0.1 |
| foul+arrows+pins10 | sample_input | 1 | 0.76 / 0.07 / 0.07 | 0.07 | 0.07 | - | 0.8 | 0.0 |
| arrows+pins10 | sample_input | 1 | 0.79 / 0.06 / 0.08 | 0.03 | 0.06 | - | 0.2 | 0.2 |
| arrows+pins10+weakfoul | sample_input | 1 | 0.72 / 0.07 / 0.06 | 0.10 | 0.07 | - | 1.0 | 0.0 |
| arrows+pins10+top | sample_input | 1 | 0.79 / 0.06 / 0.08 | 0.03 | 0.06 | - | 0.2 | 0.2 |
| snapfoul+pins10 | sample_input | 1 | 1.12 / 0.39 / 0.41 | 0.05 | 0.39 | - | 0.3 | 0.1 |
| snapfoul+arrows+pins10 | sample_input | 1 | 0.86 / 0.19 / 0.19 | 0.13 | 0.19 | - | 0.9 | 0.1 |
| corners+arrows+pins10+carry | sample_input | 1 | 0.76 / 0.07 / 0.07 | 0.07 | 0.07 | 1.80 | 0.8 | 0.1 |
| corners+arrows+pins10+carryLM | sample_input | 1 | 0.76 / 0.07 / 0.07 | 0.07 | 0.07 | 0.08 | 0.8 | 0.1 |
| corners+arrows(1pass) | sample_input | 1 | 0.57 / 0.22 / 0.20 | 0.31 | 0.22 | 0.12 | 7.1 | 0.5 |
| foul+arrows+pins(1pass) | sample_input | 1 | 0.78 / 0.06 / 0.07 | 0.03 | 0.06 | - | 1.0 | 0.2 |
| corners | Chardie | 1 | 0.37 / 0.89 / 0.62 | 0.82 | 0.89 | 0.97 | -1.4 | 0.1 |
| snapcorners | Chardie | 1 | 0.42 / 0.97 / 0.70 | 0.84 | 0.97 | 0.87 | -1.4 | 0.1 |
| corners+arrows | Chardie | 1 | 0.47 / 0.71 / 0.44 | 0.63 | 0.71 | 0.67 | 1.5 | 0.5 |
| corners+pins | Chardie | 1 | 0.37 / 0.89 / 0.62 | 0.82 | 0.89 | 0.97 | -1.4 | 0.1 |
| corners+pins10 | Chardie | 1 | 0.37 / 0.89 / 0.62 | 0.82 | 0.89 | 0.97 | -1.4 | 0.1 |
| corners+arrows+pins10 | Chardie | 1 | 0.47 / 0.71 / 0.44 | 0.63 | 0.71 | 0.67 | 1.5 | 0.5 |
| foul+arrows+pins10 | Chardie | 0 | - / - / - | - | - | - | - | - |
| arrows+pins10 | Chardie | 0 | - / - / - | - | - | - | - | - |
| arrows+pins10+weakfoul | Chardie | 0 | - / - / - | - | - | - | - | - |
| arrows+pins10+top | Chardie | 0 | - / - / - | - | - | - | - | - |
| snapfoul+pins10 | Chardie | 0 | - / - / - | - | - | - | - | - |
| snapfoul+arrows+pins10 | Chardie | 0 | - / - / - | - | - | - | - | - |
| corners+arrows+pins10+carry | Chardie | 1 | 0.47 / 0.71 / 0.44 | 0.63 | 0.71 | 0.67 | 1.5 | 0.5 |
| corners+arrows+pins10+carryLM | Chardie | 1 | 0.47 / 0.71 / 0.44 | 0.63 | 0.71 | 0.67 | 1.5 | 0.5 |
| corners+arrows(1pass) | Chardie | 1 | 0.47 / 0.71 / 0.44 | 0.63 | 0.71 | 0.67 | 1.5 | 0.5 |
| foul+arrows+pins(1pass) | Chardie | 0 | - / - / - | - | - | - | - | - |
| corners | tom_old | 2 | 1.19 / 0.74 / 0.74 | 1.18 | 0.33 | 1.16 | -4.0 | 2.1 |
| snapcorners | tom_old | 2 | 1.14 / 0.79 / 0.79 | 1.18 | 0.26 | 1.31 | -4.0 | 2.1 |
| corners+arrows | tom_old | 2 | 0.75 / 0.85 / 0.90 | 1.31 | 0.55 | 1.16 | -0.6 | 1.9 |
| corners+pins | tom_old | 2 | 0.99 / 0.61 / 0.65 | 0.89 | 0.06 | 1.16 | -1.2 | 1.4 |
| corners+pins10 | tom_old | 2 | 1.10 / 0.65 / 0.66 | 0.95 | 0.15 | 1.16 | -1.0 | 1.6 |
| corners+arrows+pins10 | tom_old | 2 | 1.04 / 0.63 / 0.64 | 0.90 | 0.10 | 1.16 | -0.9 | 1.6 |
| foul+arrows+pins10 | tom_old | 1 | 1.56 / 0.10 / 0.08 | 0.15 | 0.10 | - | -0.4 | 0.6 |
| arrows+pins10 | tom_old | 1 | 1.45 / 0.20 / 0.20 | 0.11 | 0.20 | - | -0.7 | 0.6 |
| arrows+pins10+weakfoul | tom_old | 1 | 1.54 / 0.17 / 0.15 | 0.21 | 0.17 | - | -0.4 | 0.8 |
| arrows+pins10+top | tom_old | 1 | 1.45 / 0.20 / 0.20 | 0.11 | 0.20 | - | -0.7 | 0.6 |
| snapfoul+pins10 | tom_old | 1 | 1.56 / 0.16 / 0.15 | 0.23 | 0.16 | - | -0.3 | 0.8 |
| snapfoul+arrows+pins10 | tom_old | 1 | 1.54 / 0.17 / 0.15 | 0.21 | 0.17 | - | -0.3 | 0.8 |
| corners+arrows+pins10+carry | tom_old | 2 | 1.56 / 0.16 / 0.14 | 0.22 | 0.10 | 0.22 | -0.3 | 0.8 |
| corners+arrows+pins10+carryLM | tom_old | 2 | 1.04 / 0.63 / 0.64 | 0.90 | 0.10 | 1.16 | -0.9 | 1.6 |
| corners+arrows(1pass) | tom_old | 2 | 0.75 / 0.85 / 0.90 | 1.30 | 0.55 | 1.16 | -0.6 | 1.9 |
| foul+arrows+pins(1pass) | tom_old | 1 | 1.30 / 0.24 / 0.28 | 0.36 | 0.24 | - | 0.1 | 0.3 |


| dropped landmark (sam_zoom_lo_k, foul+arrows+pins base) | sample_input throw median (pins) / tail | Chardie throw median (pins) / tail | tom_old throw median (pins) / tail |
|---|---|---|---|
| foul+arrows+pins | 0.06 / 0.03 | - / - | 0.24 / 0.36 |
| foul+arrows+pins10 | 0.07 / 0.07 | - / - | 0.10 / 0.15 |
| drop-arrow_5 | 0.09 / 0.03 | - / - | 0.25 / 0.37 |
| drop-arrow_10 | 0.07 / 0.02 | - / - | 0.23 / 0.35 |
| drop-arrow_15 | 0.07 / 0.03 | - / - | 0.22 / 0.34 |
| drop-arrow_20 | 0.06 / 0.03 | - / - | 0.22 / 0.34 |
| drop-arrow_25 | 0.06 / 0.04 | - / - | 0.22 / 0.33 |
| drop-arrow_30 | 0.06 / 0.04 | - / - | 0.23 / 0.34 |
| drop-arrow_35 | 0.05 / 0.05 | - / - | 0.24 / 0.36 |
| drop-pin_7 | 0.06 / 0.06 | - / - | 0.11 / 0.19 |
| drop-pin_10 | 0.08 / 0.11 | - / - | 0.11 / 0.18 |

## E4 camera

| video | landmarks per frame (median) | frames with a landmark fit | corner error vs hand per-frame corners: landmarks / ORB (px mean, throw) | top corners: landmarks / ORB | max: landmarks / ORB | vs ORB (px mean, no hand truth) |
|---|---|---|---|---|---|---|
| sample_input | 17.0 | 180/180 | 3.45 / 4.24 | 1.59 / 3.46 | 9.27 / 15.14 | - |
| Chardie | 16.0 | 158/162 | - | - | - | 4.57 |
| tom_old | 7.0 | 401/406 | - | - | - | 7.9 |
