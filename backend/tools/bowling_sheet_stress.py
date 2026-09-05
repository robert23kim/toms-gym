"""Perturb cached OCR dumps and measure how the score-sheet parser degrades.

Usage: venv/bin/python tools/bowling_sheet_stress.py [--seeds N] [stem ...]

Perturbations (applied to every word/symbol of a cached `<stem>_ocr.json`):
  tilt <slope>     y += slope * (x - page_w/2)
  scale <f>        multiply every coordinate/size by f
  jitter <frac>    y += uniform(-frac, frac) * h            (seeded)
  drop <frac>      delete that fraction of symbols          (seeded; words untouched)
  dropw <frac>     delete that fraction of words            (seeded)
Outcome per (stem, perturbation): exact / inferred / flagged / SILENT-WRONG / parse-error.
Silent wrongs are the ones that matter: wrong cells with no flag raised.
"""
import argparse
import copy
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))

from toms_gym.services import bowling_sheet_parser as bp  # noqa: E402
from toms_gym.services.bowling_score import score_frames  # noqa: E402

FIXTURES = ROOT / 'tests' / 'fixtures' / 'bowling'


def perturb(ocr, kind, arg, seed=0):
    o = copy.deepcopy(ocr)
    rng = random.Random(seed)
    cx = o['page_w'] / 2
    for coll in ('words', 'symbols'):
        items = o[coll]
        if kind == 'tilt':
            for w in items:
                w['y'] += arg * (w['x'] - cx)
        elif kind == 'scale':
            for w in items:
                for k in ('x', 'y', 'w', 'h'):
                    if k in w:
                        w[k] *= arg
        elif kind == 'jitter':
            for w in items:
                w['y'] += rng.uniform(-arg, arg) * w['h']
        elif kind == 'drop' and coll == 'symbols':
            o[coll] = [w for w in items if rng.random() >= arg]
        elif kind == 'dropw' and coll == 'words':
            o[coll] = [w for w in items if rng.random() >= arg]
    if kind == 'scale':
        o['page_w'] *= arg
        o['page_h'] *= arg
    return o


def compare(sheet_type, parsed, truth):
    """Return (wrong_cells, flagged_rows, missing_rows, wrong_cells_marked_inferred)."""
    got = {p['name'].upper(): p for p in parsed['players']}
    wrong = flagged = missing = inferred_wrong = 0
    for tp in truth['players']:
        p = got.get(tp['name'].upper())
        if not p:
            missing += 1
            continue
        if p['flagged']:
            flagged += 1
        if sheet_type == 'night':
            have = p['games'] + [p['scratch'], p['hdcp'], p['total']]
            want = tp['games'] + [tp['scratch'], tp['hdcp'], tp['total']]
            wrong += sum(1 for a, b in zip(have, want) if a != b)
        else:
            inferred = set(p.get('inferred_frames') or [])
            wrong += sum(1 for i in range(10) if p['frames'][i] != tp['frames'][i] and i + 1 not in inferred)
            inferred_wrong += sum(1 for i in range(10) if p['frames'][i] != tp['frames'][i] and i + 1 in inferred)
            # what the reviewer sees is the running score recomputed from the frames
            cum = score_frames(p['frames'])['cumulative']
            wrong += sum(1 for i in range(10) if (cum[i] if i < len(cum) else None) != tp['cumulative'][i])
    return wrong, flagged, missing, inferred_wrong


def outcome(sheet_type, ocr, truth):
    try:
        parsed = bp.parse_sheet(sheet_type, ocr['words'], ocr['symbols'], ocr['page_w'], ocr['page_h'])
    except bp.SheetParseError as e:
        return 'error', str(e)
    except Exception as e:  # noqa: BLE001 - a crash is a finding
        return 'crash', f'{type(e).__name__}: {e}'
    wrong, flagged, missing, inferred_wrong = compare(sheet_type, parsed, truth)
    if missing:
        return 'missing-row', f'{missing} row(s) missing'
    if wrong == 0 and inferred_wrong == 0:
        return 'exact', ''
    if wrong == 0:
        return 'inferred', f'{inferred_wrong} guessed roll split(s), marked inferred'
    if flagged:
        return 'flagged', f'{wrong} wrong cell(s), flagged'
    return 'SILENT-WRONG', f'{wrong} wrong cell(s), no flag'


PERTURBATIONS = [
    ('tilt', -0.06), ('tilt', -0.03), ('tilt', 0.03), ('tilt', 0.06),
    ('scale', 0.5), ('scale', 0.75), ('scale', 1.5), ('scale', 2.0),
    ('jitter', 0.15), ('jitter', 0.3),
    ('drop', 0.05), ('drop', 0.1), ('drop', 0.2),
    ('dropw', 0.05), ('dropw', 0.1),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stems', nargs='*')
    ap.add_argument('--seeds', type=int, default=3)
    args = ap.parse_args()
    stems = args.stems or sorted(p.name[:-9] for p in FIXTURES.glob('*_ocr.json')
                                 if (FIXTURES / f'{p.name[:-9]}_truth.json').exists())
    totals = {}
    for stem in stems:
        ocr = json.loads((FIXTURES / f'{stem}_ocr.json').read_text())
        truth = json.loads((FIXTURES / f'{stem}_truth.json').read_text())
        st = truth['sheet_type']
        base, _ = outcome(st, ocr, truth)
        print(f'{stem} ({st}) baseline={base}')
        for kind, arg in PERTURBATIONS:
            seeds = range(args.seeds) if kind in ('jitter', 'drop', 'dropw') else [0]
            results = [outcome(st, perturb(ocr, kind, arg, s), truth) for s in seeds]
            kinds = [r[0] for r in results]
            worst = next((k for k in ('crash', 'SILENT-WRONG', 'missing-row', 'error', 'flagged', 'inferred', 'exact') if k in kinds), 'exact')
            detail = next((d for k, d in results if k == worst), '')
            label = f'{kind} {arg}'
            print(f'  {label:<12} {"/".join(kinds):<40} {detail}')
            totals.setdefault(worst, 0)
            totals[worst] += 1
    print('\nWORST-CASE TALLY', dict(sorted(totals.items())))


if __name__ == '__main__':
    main()
