| fixture | base s (r1, r2) | cand s (r1, r2) | speedup (mean) | base class/inst | cand class/inst | cand vs base compare | stages cand: analyze / reencode / clips / upload |
|---|---|---|---|---|---|---|---|
| squat_f47a8848 | 44.1, 44.8 | 23.2, 20.9 | 2.01x | A+B/56f1be, A+B/56f1be | A+B/5e4b1a, A+B/5e4b1a | 4/4 MATCH | 22.18 / 0.0 / 0.76 / 0.13; 19.73 / 0.0 / 0.85 / 0.17 |
| pushup_3c66c85e | 74.4, 89.9 | 26.6, 27.6 | 3.03x | B/56f1be, A/eb01ce | A/5e4b1a, A/5e4b1a | 2/4 MATCH | 26.33 / 0.0 / 0.0 / 0.16; 27.34 / 0.0 / 0.0 / 0.17 |
| pushup_97b4aaf2 | 132.8, 112.9 | 24.6, 25.4 | 4.92x | A/eb01ce, B/56f1be | A/5e4b1a, A/5e4b1a | 2/4 MATCH | 24.04 / 0.0 / 0.0 / 0.19; 25.0 / 0.0 / 0.0 / 0.19 |
| pushup_e18a31d1 | 145.8, 132.5 | 30.4, 32.4 | 4.43x | A/eb01ce, B/56f1be | A/5e4b1a, A/5e4b1a | 2/4 MATCH | 29.91 / 0.0 / 0.0 / 0.24; 31.81 / 0.0 / 0.0 / 0.25 |
| situp_16b6ca35 | 143.6, 142.2 | 52.5, 52.2 | 2.73x | B/56f1be, B/56f1be | A/5e4b1a, A/5e4b1a | 0/4 MATCH | 51.89 / 0.0 / 0.0 / 0.22; 51.78 / 0.0 / 0.0 / 0.21 |
| situp_667a8480 | 223.7, 226.5 | 62.9, 61.4 | 3.62x | A/eb01ce, A/eb01ce | A/5e4b1a, A/5e4b1a | 4/4 MATCH | 62.22 / 0.0 / 0.0 / 0.29; 60.72 / 0.0 / 0.0 / 0.31 |
| situp_c9dec98b | 153.1, 155.5 | 45.4, 46.9 | 3.34x | A/eb01ce, A/eb01ce | A/5e4b1a, A/5e4b1a | 4/4 MATCH | 44.7 / 0.0 / 0.0 / 0.24; 45.92 / 0.0 / 0.0 / 0.2 |
| plank_9600f455 | 42.8, 41.5 | 39.5, 49.1 | 0.95x | B/56f1be, B/? | A/5e4b1a, A/5e4b1a | 0/4 MATCH | 38.75 / 0.0 / 0.0 / 0.27; 38.86 / 0.0 / 0.0 / 9.75 |

sum of per-fixture means: base 953.0 s, cand 310.7 s, 3.07x, -67%
non-200 responses: 0; fixtures with any cand-vs-base DIFF: ['pushup_3c66c85e', 'pushup_97b4aaf2', 'pushup_e18a31d1', 'situp_16b6ca35', 'plank_9600f455']
