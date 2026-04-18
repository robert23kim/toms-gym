"""Debug the golf parser — print per-row analysis."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from toms_gym.routes.golf_routes import _group_rows, _cluster_by_x, _deduplicate_symbols, SCORECARD_LABELS

fx = json.load(open(ROOT / "tests" / "fixtures" / "golf_scorecard_ocr.json"))
symbols = fx['symbols']
page_w = fx['width']
page_h = fx['height']

rows = _group_rows(symbols, page_h)
gap_threshold = max(40, min(90, page_w * 0.018)) if page_w else 70
print(f"page: {page_w}x{page_h}, gap_threshold={gap_threshold}, rows={len(rows)}\n")

for i, row in enumerate(rows):
    letters = sorted([s for s in row if s['text'].isalpha()], key=lambda x: x['x'])
    digits = sorted([s for s in row if s['text'].isdigit()], key=lambda x: x['x'])
    y = int(sum(s['y'] for s in row) / len(row))
    print(f"Row {i:2d} y={y}: letters={len(letters)} digits={len(digits)}")

    if not letters or len(digits) < 15:
        print(f"   SKIP: not enough digits (need 15+)")
        continue

    # Name extraction
    name_letters = [letters[0]]
    for l in letters[1:]:
        gap = l['x'] - name_letters[-1]['x']
        if gap < 80:
            name_letters.append(l)
        else:
            break
    name = ''.join(l['text'] for l in name_letters).strip().upper()
    name = ''.join(c for c in name if c.isalpha())
    print(f"   name_letters (x<80 cluster): {[(l['text'], int(l['x'])) for l in name_letters[:10]]}{'...' if len(name_letters)>10 else ''}")
    print(f"   raw name = {name!r}")

    if not name or name in SCORECARD_LABELS or len(name) < 2:
        print(f"   SKIP: name rejected (empty, label, or <2 chars)")
        continue

    name_end_x = name_letters[-1]['x'] + 50
    score_digits = [d for d in digits if d['x'] > name_end_x]
    score_digits = _deduplicate_symbols(score_digits)
    score_digits.sort(key=lambda s: s['x'])

    clusters = _cluster_by_x(score_digits, gap_threshold)
    multi_idx = [i for i, c in enumerate(clusters) if len(c) > 1]

    cluster_desc = []
    for c in clusters:
        if len(c) == 1:
            cluster_desc.append(f"{c[0]['text']}@{int(c[0]['x'])}")
        else:
            txt = ''.join(x['text'] for x in c)
            cluster_desc.append(f"[{txt}]@{int(c[0]['x'])}")
    print(f"   clusters ({len(clusters)}, multi at {multi_idx}): {cluster_desc[:30]}")
    print()
