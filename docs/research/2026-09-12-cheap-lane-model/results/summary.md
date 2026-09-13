| video | method | last | pre-hit | clean mean / med | occluded mean / med | <=2 boards (throw) | frames with a lane | per frame |
|---|---|---|---|---|---|---|---|---|
| sample_input | seg640|_anc | 2.06 | 1.55 | 1.88 / 1.78 | 2.16 / 2.18 | 73 % | 180/180 | 32 ms |
| sample_input | hybrid: seg640|_anc prompts -> SAM 2 tiny | 0.64 | 1.07 | 2.55 / 1.43 | no lane | - | 19 clean | ~600 ms |
| sample_input | seg640|_anc_gated | 2.11 | 1.59 | 1.92 / 1.85 | 2.17 / 2.21 | 66 % | 180/180 | 32 ms |
| sample_input | seg640|_anc_video | 0.77 | 0.73 | 1.94 / 2.22 | 3.42 / 3.73 | 29 % | 180/180 | 32 ms |
| sample_input | seg640|_plus_anc_gated | 1.08 | 0.99 | 1.32 / 1.25 | 1.44 / 1.58 | 98 % | 180/180 | 32 ms |
| sample_input | seg640|_plus_anc_video | 0.16 | 0.28 | 1.56 / 1.92 | 3.07 / 3.40 | 72 % | 180/180 | 32 ms |
| sample_input | pose640 | 5.82 | 7.47 | 6.46 / 6.57 | 5.76 / 5.63 | 0 % | 180/180 | 28 ms |
| sample_input | SAM 2 base, even3 prompts (loops 1-2) | 0.24 | 0.31 | - | no lane | - | 1 frame | 2130 ms |
| sample_input | SAM 2 tiny, path prompts (loop 1) | 0.68 | - | - | no lane | - | 1 frame | 2930 ms |
| sample_input | SAM 2 video mode, per frame (loop 1) | 0.21 | - | 1.85 / 0.98 * | - | 66 % | 86/91 | 1359 ms |
| sample_input | SAM 2 gate + carry (loop 2) | 2.40 | - | 0.98 / 0.84 * | carried | 91 % | 86/91 | - |
| Chardie | seg640|_anc | 1.14 | 1.04 | 15.99 / 0.91 | 0.72 / 0.62 | 73 % | 171/171 | 31 ms |
| Chardie | hybrid: seg640|_anc prompts -> SAM 2 tiny | 0.59 | 0.51 | 6.29 / 4.50 | no lane | - | 17 clean | ~600 ms |
| Chardie | seg640|_anc_gated | 1.28 | 0.96 | 1.82 / 0.89 | 0.68 / 0.65 | 80 % | 171/171 | 31 ms |
| Chardie | seg640|_anc_video | 4.97 | 0.84 | 1.88 / 0.82 | 11.49 / 12.18 | 69 % | 171/171 | 31 ms |
| Chardie | seg640|_plus_anc_gated | 0.59 | 0.82 | 2.18 / 0.98 | 0.73 / 0.65 | 77 % | 171/171 | 28 ms |
| Chardie | seg640|_plus_anc_video | 6.37 | 2.06 | 2.43 / 2.02 | 10.29 / 11.00 | 44 % | 171/171 | 28 ms |
| Chardie | pose640 | 8.64 | 10.14 | 29.65 / 12.33 | 9.74 / 10.69 | 0 % | 171/171 | 27 ms |
| Chardie | SAM 2 base, even3 prompts (loops 1-2) | 0.39 | 0.69 | - | no lane | - | 1 frame | 2060 ms |
| Chardie | SAM 2 tiny, path prompts (loop 1) | 1.12 | - | - | no lane | - | 1 frame | 960 ms |
| Chardie | SAM 2 video mode, per frame (loop 1) | 0.38 | - | 16.39 / 4.02 * | - | 38 % | 66/111 | 1343 ms |
| Chardie | SAM 2 gate + carry (loop 2) | 0.38 | - | 0.41 / 0.31 * | carried | 100 % | 66/111 | - |
| tom_old | seg640|_anc | 104.62 | 3.23 | 36.30 / 3.28 | 47.70 / 3.35 | 0 % | 370/409 | 29 ms |
| tom_old | hybrid: seg640|_anc prompts -> SAM 2 tiny | 0.76 | 2.08 | 3.35 / 1.98 | no lane | - | 37 clean | ~600 ms |
| tom_old | seg640|_anc_gated | 1.87 | 3.29 | 3.12 / 3.13 | 3.27 / 3.29 | 1 % | 409/409 | 29 ms |
| tom_old | seg640|_anc_video | 1.71 | 3.06 | 3.08 / 3.13 | 3.11 / 3.13 | 1 % | 370/409 | 29 ms |
| tom_old | seg640|_plus_anc_gated | 1.78 | 3.14 | 3.12 / 3.16 | 3.16 / 3.17 | 1 % | 409/409 | 29 ms |
| tom_old | seg640|_plus_anc_video | - | 2.96 | 3.00 / 3.04 | 3.01 / 3.04 | 0 % | 398/409 | 29 ms |
| tom_old | pose640 | - | - | 8.55 / 8.77 | - / - | 0 % | 33/409 | 40 ms |
| tom_old | SAM 2 base, even3 prompts (loops 1-2) | 1.35 | 2.27 | - | no lane | - | 1 frame | 2070 ms |
| tom_old | SAM 2 tiny, path prompts (loop 1) | 0.61 | - | - | no lane | - | 1 frame | 1020 ms |
| tom_old | SAM 2 video mode, per frame (loop 1) | 1.53 | - | 3.73 / 2.35 * | - | 13 % | 148/154 | 1346 ms |
| tom_old | SAM 2 gate + carry (loop 2) | 1.53 | - | 1.94 / 1.85 * | carried | 53 % | 148/154 | - |

\* SAM per-frame means are over the throw frames the method scored (loop 1 video mode: whole throw incl. occluded frames; loop 2 gate+carry: accepted frames only).

**Unlabeled videos, student vs SAM 2 teacher (teacher corners as truth, detected ball path as the points)**

| video | student | boards mean / med (teacher reliable) | frames | corner px | boards in throw (teacher occluded) |
|---|---|---|---|---|---|
| bowling_video | pose640_all3 | 3.05 / 3.17 | 162/162 | 8.1 | 3.21 / 3.14 |
