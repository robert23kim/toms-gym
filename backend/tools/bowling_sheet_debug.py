"""Bowling score-sheet parser harness — OCR fixture photos, cache the dump, score vs truth.

Usage:
    GOOGLE_APPLICATION_CREDENTIALS=credentials.json venv/bin/python tools/bowling_sheet_debug.py [--refresh] [--rotate DEG] [stem ...]

Defaults to every `tests/fixtures/bowling/*_truth.json`. Without --refresh it replays the
cached `<stem>_ocr.json` (no network). --rotate re-OCRs a rotated copy to probe orientation
handling (result is not cached).
"""
import argparse
import io
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from toms_gym.services import bowling_sheet_parser as bp  # noqa: E402

FIXTURES = ROOT / 'tests' / 'fixtures' / 'bowling'


def ocr_photo(stem, rotate=0):
    from PIL import Image
    from toms_gym.services.vision_ocr import run_document_ocr, extract_words_and_symbols

    img = Image.open(FIXTURES / f'{stem}.jpg')
    if rotate:
        img = img.rotate(rotate, expand=True)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    words, symbols, w, h = extract_words_and_symbols(run_document_ocr(buf.getvalue()))
    return {'words': words, 'symbols': symbols, 'page_w': w, 'page_h': h, 'rotation': rotate}


def score_night(parsed, truth):
    got = {p['name']: p for p in parsed['players']}
    hits = total = 0
    lines = []
    for tp in truth['players']:
        p = got.get(tp['name'])
        cells = list(zip(['g1', 'g2', 'g3', 'scratch', 'hdcp', 'total'],
                         tp['games'] + [tp['scratch'], tp['hdcp'], tp['total']]))
        row_hits = 0
        for key, want in cells:
            total += 1
            have = None
            if p:
                have = (p['games'] + [p['scratch'], p['hdcp'], p['total']])[['g1', 'g2', 'g3', 'scratch', 'hdcp', 'total'].index(key)]
            if have == want:
                hits += 1
                row_hits += 1
        flag = f" FLAGGED: {p['flag_reason']}" if p and p['flagged'] else ''
        inf = f" inferred={p['inferred']}" if p and p['inferred'] else ''
        lines.append(f"  {tp['name']:<8} {row_hits}/6{inf}{flag}" + ('' if p else '  (missing)'))
    return hits, total, lines


def score_game(parsed, truth):
    got = {p['name'].upper(): p for p in parsed['players']}
    hits = total = 0
    lines = []
    for tp in truth['players']:
        p = got.get(tp['name'].upper())
        fh = sum(1 for i in range(10) if p and p['frames'][i] == tp['frames'][i])
        ch = sum(1 for i in range(10) if p and p['printed_cumulative'][i] == tp['cumulative'][i])
        hits += fh + ch
        total += 20
        flag = f" FLAGGED: {p['flag_reason']}" if p and p['flagged'] else ''
        lines.append(f"  {tp['name']:<8} frames {fh}/10 cum {ch}/10{flag}" + ('' if p else '  (missing)'))
    return hits, total, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stems', nargs='*')
    ap.add_argument('--refresh', action='store_true')
    ap.add_argument('--rotate', type=int, default=0)
    args = ap.parse_args()
    stems = args.stems or sorted(p.name[:-11] for p in FIXTURES.glob('*_truth.json'))
    grand_hits = grand_total = 0
    for stem in stems:
        truth = json.loads((FIXTURES / f'{stem}_truth.json').read_text())
        cache = FIXTURES / f'{stem}_ocr.json'
        if args.rotate or args.refresh or not cache.exists():
            if not (FIXTURES / f'{stem}.jpg').exists():
                print(f"{stem}: no photo on disk, skipping")
                continue
            ocr = ocr_photo(stem, args.rotate)
            if not args.rotate:
                cache.write_text(json.dumps(ocr))
        else:
            ocr = json.loads(cache.read_text())
        sheet_type = truth['sheet_type']
        try:
            parsed = bp.parse_sheet(sheet_type, ocr['words'], ocr['symbols'], ocr['page_w'], ocr['page_h'])
        except bp.SheetParseError as e:
            print(f"{stem}: PARSE ERROR {e}")
            grand_total += 6 * len(truth['players']) if sheet_type == 'night' else 20 * len(truth['players'])
            continue
        hits, total, lines = (score_night if sheet_type == 'night' else score_game)(parsed, truth)
        grand_hits += hits
        grand_total += total
        print(f"{stem} ({sheet_type}, rotate={args.rotate}): {hits}/{total} cells, team={parsed['team_name']!r}")
        print('\n'.join(lines))
    print(f"\nTOTAL {grand_hits}/{grand_total}")


if __name__ == '__main__':
    main()
