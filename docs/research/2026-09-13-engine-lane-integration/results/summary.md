| config | video | lane | throw MAE ann mean/med | throw MAE pins mean/med | <=2 bd (pins) | clean med (pins) | tail med (pins) | pre-hit / last (pins) | far-end width err px | final board engine / truth (err) | pass s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| before | sample_input | static classical lane | 6.79 / 7.05 | 6.09 / 6.37 | 0.0 % | 6.3 | 10.54 | 4.51 / None | 65.3 | 15.0 / 17.43 (2.43) | - |
| before | Chardie | static classical lane | 180.88 / 165.44 | 181.74 / 166.31 | 0.0 % | 161.56 | 354.89 | 143.11 / None | 29.3 | 27.0 / 13.59 (13.41) | - |
| before | tom_old | static classical lane | 11.72 / 11.69 | 13.25 / 13.22 | 0.0 % | 13.22 | 21.56 | 13.22 / 14.48 | 22.1 | 28.0 / 20.24 (7.76) | - |
| before_yolo | sample_input | static classical lane | 6.79 / 7.05 | 6.09 / 6.37 | 0.0 % | 6.3 | 10.54 | 4.51 / None | 65.3 | 13.0 / 17.43 (4.43) | - |
| before_yolo | Chardie | static classical lane | None / None | None / None | 0.0 % | None | None | None / None | None | 23.0 / 13.59 (9.41) | - |
| before_yolo | tom_old | static classical lane | 3.32 / 3.28 | 4.86 / 4.82 | 0.0 % | 4.82 | 5.55 | 4.87 / 5.93 | 20.1 | 1.0 / 20.24 (19.24) | - |
| after | sample_input | sam_full+crop | 1.38 / 1.27 | 0.76 / 0.59 | 96.3 % | 0.65 | 0.67 | 0.15 / 0.15 | 1.2 | 15.0 / 17.43 (2.43) | 78.78 |
| after | Chardie | sam_full+crop | 0.84 / 0.65 | 1.1 / 1.09 | 97.3 % | 1.09 | 1.32 | 0.83 / 1.26 | 2.7 | 10.0 / 13.59 (3.59) | 219.01 |
| after | tom_old | sam_full+crop | 1.95 / 1.97 | 0.43 / 0.44 | 100.0 % | 0.44 | 1.04 | 0.43 / 0.59 | 7.5 | 18.0 / 20.24 (2.24) | 73.15 |
| after_full | sample_input | sam_full | 1.53 / 1.44 | 0.86 / 0.76 | 95.1 % | 0.78 | 1.08 | 0.25 / 0.24 | 4.9 | 15.0 / 17.43 (2.43) | 81.91 |
| after_full | Chardie | sam_full | 0.87 / 0.62 | 0.98 / 0.92 | 100.0 % | 0.92 | 1.13 | 0.6 / 1.02 | 1.2 | 11.0 / 13.59 (2.59) | 219.42 |
| after_full | tom_old | sam_full | 2.06 / 2.08 | 0.53 / 0.55 | 100.0 % | 0.55 | 1.3 | 0.53 / 0.7 | 9.4 | 18.0 / 20.24 (2.24) | 94.61 |
| after_pins | sample_input | sam_full+crop | 1.38 / 1.27 | 0.76 / 0.59 | 96.3 % | 0.65 | 0.67 | 0.15 / 0.15 | 1.2 | 15.0 / 17.43 (2.43) | 83.69 |
| after_pins | Chardie | sam_full+crop | 0.84 / 0.65 | 1.1 / 1.09 | 97.3 % | 1.09 | 1.32 | 0.83 / 1.26 | 2.7 | 10.0 / 13.59 (3.59) | 215.64 |
| after_pins | tom_old | sam_full+crop | 1.95 / 1.97 | 0.43 / 0.44 | 100.0 % | 0.44 | 1.04 | 0.43 / 0.59 | 7.5 | 18.0 / 20.24 (2.24) | 73.07 |
| after_back2 | sample_input | sam_full+crop | 1.45 / 1.48 | 0.8 / 0.8 | 97.6 % | 0.83 | 0.82 | 0.34 / 0.22 | 1.1 | 15.0 / 17.43 (2.43) | 74.8 |
| after_back2 | Chardie | sam_full+crop | 0.84 / 0.65 | 1.1 / 1.09 | 97.3 % | 1.09 | 1.32 | 0.83 / 1.26 | 2.7 | 10.0 / 13.59 (3.59) | 212.2 |
| after_back2 | tom_old | sam_full+crop | 1.54 / 1.56 | 0.15 / 0.12 | 100.0 % | 0.12 | 0.31 | 0.12 / 0.87 | 5.9 | 16.0 / 20.24 (4.24) | 71.21 |
| after_back8 | sample_input | sam_full+crop | 1.26 / 1.25 | 0.62 / 0.57 | 100.0 % | 0.61 | 0.7 | 0.16 / 0.16 | 3.1 | 14.0 / 17.43 (3.43) | 74.89 |
| after_back8 | Chardie | sam_full+crop | 0.84 / 0.65 | 1.1 / 1.09 | 97.3 % | 1.09 | 1.32 | 0.83 / 1.26 | 2.7 | 10.0 / 13.59 (3.59) | 213.37 |
| after_back8 | tom_old | sam_full+crop | 1.64 / 1.65 | 0.17 / 0.15 | 100.0 % | 0.15 | 0.48 | 0.12 / 0.22 | 6.8 | 15.0 / 20.24 (5.24) | 71.52 |
