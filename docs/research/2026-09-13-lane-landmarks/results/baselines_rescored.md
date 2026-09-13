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
