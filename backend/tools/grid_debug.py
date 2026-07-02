"""Grid parser debug harness — run on fixture cards, render overlays, score vs ground truth.

Usage:
    venv/bin/python tools/grid_debug.py [card_stem ...]

Defaults to both fixture cards. Uses the cached OCR dumps (no network).
Writes overlay images to tools/grid_debug_out/.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np

from toms_gym.services import scorecard_grid as sg

FIXTURES = ROOT / 'tests' / 'fixtures' / 'scorecards'
OUT_DIR = pathlib.Path(__file__).parent / 'grid_debug_out'
OUT_DIR.mkdir(exist_ok=True)


def render_overlay(stem, image_bytes, result):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    dbg = result['debug']
    H = np.array(dbg['homography'], dtype=np.float32) if dbg['homography'] else None
    if H is not None:
        w, h = dbg['warped_size']
        canvas = cv2.warpPerspective(image, H, (w, h))
    else:
        canvas = image.copy()
    for x in dbg['col_xs']:
        cv2.line(canvas, (int(x), 0), (int(x), canvas.shape[0]), (0, 200, 0), 2)
    for y in dbg['row_ys']:
        cv2.line(canvas, (0, int(y)), (canvas.shape[1], int(y)), (0, 128, 255), 2)
    st = dbg['structure']
    col_xs, row_ys = dbg['col_xs'], dbg['row_ys']

    def cell_center(r, c):
        cx = (col_xs[c] + col_xs[c + 1]) // 2 if c + 1 < len(col_xs) else col_xs[c] + 20
        cy = (row_ys[r] + row_ys[r + 1]) // 2 if r + 1 < len(row_ys) else row_ys[r] + 20
        return int(cx), int(cy)

    if st['par_row'] is not None:
        for i, c in enumerate(st['hole_cols']):
            cx, cy = cell_center(st['par_row'], c)
            cv2.putText(canvas, f"H{i+1}", (cx - 20, cy - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
    out_path = OUT_DIR / f'{stem}_overlay.jpg'
    cv2.imwrite(str(out_path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return out_path


def score_vs_truth(result, truth):
    """Cell-level hit rate: correct strokes on correct holes."""
    report = []
    total_cells = correct_cells = 0
    truth_players = {p['name']: p for p in truth['players']}
    got_players = {p['name']: p for p in result['players']}

    for name, tp in truth_players.items():
        gp = got_players.get(name)
        n_written = sum(1 for v in tp['holes'] if v is not None)
        ambiguous = {int(k): v for k, v in tp.get('ambiguous_readings', {}).items()}
        if not gp:
            report.append(f"  {name}: NOT DETECTED (0/{n_written})")
            total_cells += n_written
            continue
        hit = 0
        misses = []
        for i, tv in enumerate(tp['holes']):
            if tv is None:
                continue
            total_cells += 1
            gv = next((h['strokes'] for h in gp['holes'] if h['hole_number'] == i + 1), None)
            ok = gv == tv or (i + 1 in ambiguous and gv in ambiguous[i + 1])
            if ok:
                hit += 1
                correct_cells += 1
            else:
                misses.append(f"h{i+1}:{gv}!={tv}")
        extra = [f"h{h['hole_number']}:{h['strokes']}" for h in gp['holes']
                 if h['strokes'] is not None and tp['holes'][h['hole_number'] - 1] is None]
        flags = [h['hole_number'] for h in gp['holes'] if h.get('flagged')]
        report.append(f"  {name}: {hit}/{n_written} correct"
                      + (f" | misses: {' '.join(misses)}" if misses else "")
                      + (f" | spurious: {' '.join(extra)}" if extra else "")
                      + (f" | flagged: {flags}" if flags else ""))
    for name in got_players:
        if name not in truth_players:
            report.append(f"  {name}: SPURIOUS PLAYER")

    par_hits = sum(1 for a, b in zip(result.get('pars') or [], truth['pars']) if a == b)
    report.append(f"  pars: {par_hits}/{len(truth['pars'])}")

    truth_tees = {t['name']: t for t in truth['tees']}
    tee_hits = sum(1 for t in result.get('tees', [])
                   if t['name'] in truth_tees
                   and truth_tees[t['name']]['rating'] == t['rating']
                   and truth_tees[t['name']]['slope'] == t['slope'])
    report.append(f"  tees: {tee_hits}/{len(truth_tees)}")
    return correct_cells, total_cells, par_hits, tee_hits, report


def main():
    stems = sys.argv[1:] or ['1000005113', '1000005117']
    grand_correct = grand_total = 0
    for stem in stems:
        print(f"\n=== {stem} ===")
        image_bytes = (FIXTURES / f'{stem}.jpg').read_bytes()
        ocr = json.load(open(FIXTURES / f'{stem}_ocr.json'))
        truth = json.load(open(FIXTURES / f'{stem}_truth.json'))
        try:
            result = sg.parse_scorecard_grid(
                image_bytes, ocr['symbols'], ocr['width'], ocr['height'])
        except sg.GridParseError as e:
            print(f"  GRID PARSE FAILED: {e}")
            grand_total += sum(sum(1 for v in p['holes'] if v is not None)
                               for p in truth['players'])
            continue
        out_path = render_overlay(stem, image_bytes, result)
        correct, total, par_hits, tee_hits, report = score_vs_truth(result, truth)
        grand_correct += correct
        grand_total += total
        print('\n'.join(report))
        print(f"  overlay: {out_path}")
        for p in result['players']:
            cs = p.get('checksums', {})
            print(f"  checksums {p['name']}: {cs}")
    print(f"\nTOTAL SCORE CELLS: {grand_correct}/{grand_total} "
          f"({100.0 * grand_correct / grand_total if grand_total else 0:.1f}%)")


if __name__ == '__main__':
    main()
