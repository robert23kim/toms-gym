# Automatic lift type: labelled-set result

Candidates: situp,pushup,squat,plank. Clips are numbered; the manifest that maps them to uploads is not in the repository.

- All clips with a person: 48/51 (94.1%): plank 21/22, pushup 16/17, situp 10/11, squat 1/1
- Held-out: 29/32 (90.6%): plank 14/15, pushup 9/10, situp 5/6, squat 1/1
- Held-out, athletes with no development clip: 12/14 (85.7%): plank 9/10, pushup 3/4
- Development: 19/19 (100.0%): plank 7/7, pushup 7/7, situp 5/5
- Correct but below the 0.6 confirm threshold (the app asks): 1
- Wrong at or above the threshold (silent): 2
- Clips with nobody in them, expected no detection: 2/2 (100.0%): none 2/2
- Clips left out because they have no pose cache: 0

| clip | label | split | athlete | detected | confidence | asks | read (s) | result |
|---|---|---|---|---|---|---|---|---|
| c01 | plank | dev | club-b | plank | 1.00 |  | 22 of 76 | ok |
| c02 | plank | holdout | club-b | plank | 1.00 |  | 16 of 73 | ok |
| c03 | plank | dev | club-a | plank | 1.00 |  | 12 of 86 | ok |
| c04 | plank | dev | club-b | plank | 1.00 |  | 14 of 92 | ok |
| c05 | plank | holdout | club-a | plank | 1.00 |  | 12 of 71 | ok |
| c06 | plank | dev | club-a | plank | 1.00 |  | 10 of 62 | ok |
| c07 | plank | holdout | club-a | plank | 1.00 |  | 10 of 66 | ok |
| c08 | plank | holdout | club-b | plank | 1.00 |  | 16 of 68 | ok |
| c09 | pushup | dev | club-a | pushup | 1.00 |  | 34 of 34 | ok |
| c10 | pushup | dev | club-b | pushup | 1.00 |  | 49 of 49 | ok |
| c11 | pushup | holdout | club-b | pushup | 1.00 |  | 58 of 58 | ok |
| c12 | pushup | dev | club-b | pushup | 1.00 |  | 57 of 57 | ok |
| c13 | pushup | holdout | club-a | pushup | 1.00 |  | 34 of 34 | ok |
| c14 | pushup | holdout | club-b | pushup | 1.00 |  | 37 of 37 | ok |
| c15 | pushup | dev | club-a | pushup | 1.00 |  | 28 of 28 | ok |
| c16 | pushup | holdout | club-a | pushup | 1.00 |  | 29 of 29 | ok |
| c17 | pushup | dev | club-b | pushup | 1.00 |  | 65 of 65 | ok |
| c18 | pushup | dev | club-a | pushup | 1.00 |  | 33 of 33 | ok |
| c19 | pushup | holdout | club-b | pushup | 1.00 |  | 51 of 51 | ok |
| c20 | situp | dev | club-b | situp | 1.00 |  | 112 of 112 | ok |
| c21 | situp | dev | club-a | situp | 1.00 |  | 56 of 56 | ok |
| c22 | situp | holdout | club-a | None | 0.00 |  | 57 of 57 | MISS |
| c23 | situp | dev | club-a | situp | 1.00 |  | 66 of 66 | ok |
| c24 | situp | holdout | club-a | situp | 1.00 |  | 48 of 48 | ok |
| c25 | situp | holdout | club-b | situp | 1.00 |  | 129 of 129 | ok |
| c26 | situp | dev | club-a | situp | 1.00 |  | 58 of 58 | ok |
| c27 | situp | holdout | club-b | situp | 1.00 |  | 109 of 109 | ok |
| c28 | squat | holdout | club-b | squat | 1.00 |  | 32 of 32 | ok |
| c29 | plank | dev | club-a | plank | 0.86 |  | 10 of 10 | ok |
| c30 | plank | holdout | other | plank | 1.00 |  | 12 of 71 | ok |
| c31 | plank | holdout | other | plank | 1.00 |  | 14 of 75 | ok |
| c32 | plank | holdout | other | pushup | 1.00 |  | 141 of 141 | MISS |
| c33 | plank | holdout | club-a | plank | 1.00 |  | 18 of 122 | ok |
| c34 | plank | holdout | other | plank | 1.00 |  | 12 of 75 | ok |
| c35 | plank | dev | club-a | plank | 1.00 |  | 10 of 75 | ok |
| c36 | plank | holdout | other | plank | 0.57 | yes | 18 of 75 | ok |
| c37 | plank | holdout | other | plank | 0.75 |  | 16 of 75 | ok |
| c40 | none | - | - | None | 0.00 |  | 60 of 75 | ok |
| c41 | plank | holdout | other | plank | 1.00 |  | 20 of 75 | ok |
| c42 | plank | dev | club-b | plank | 1.00 |  | 16 of 75 | ok |
| c43 | plank | holdout | other | plank | 1.00 |  | 14 of 75 | ok |
| c45 | plank | holdout | other | plank | 1.00 |  | 14 of 75 | ok |
| c46 | plank | holdout | other | plank | 1.00 |  | 12 of 75 | ok |
| c47 | pushup | holdout | club-a | pushup | 1.00 |  | 20 of 20 | ok |
| c48 | pushup | holdout | other | plank | 0.91 |  | 9 of 9 | MISS |
| c49 | pushup | dev | club-a | pushup | 1.00 |  | 39 of 39 | ok |
| c50 | pushup | holdout | other | pushup | 1.00 |  | 45 of 45 | ok |
| c51 | pushup | holdout | other | pushup | 1.00 |  | 58 of 58 | ok |
| c52 | pushup | holdout | other | pushup | 1.00 |  | 26 of 26 | ok |
| c53 | situp | holdout | club-a | situp | 1.00 |  | 101 of 101 | ok |
| c54 | situp | dev | club-a | situp | 1.00 |  | 66 of 66 | ok |
| c55 | situp | holdout | club-a | situp | 1.00 |  | 85 of 85 | ok |
| c56 | none | - | - | None | 0.00 |  | 1 of 1 | ok |
