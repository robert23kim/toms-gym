"""Standalone test runner for the golf parser — bypasses conftest / DB setup.

Run with: cd backend && venv/bin/python tools/run_golf_parser_tests.py
"""
import json
import pathlib
import sys

# Ensure backend is on path
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from toms_gym.routes.golf_routes import (  # noqa: E402
    _parse_scorecard_symbols,
    _cluster_by_x,
    _deduplicate_symbols,
    _extract_pars,
    _find_par_label,
)

FIXTURE = ROOT / "tests" / "fixtures" / "golf_scorecard_ocr.json"
FIXTURE_SAGAMORE = ROOT / "tests" / "fixtures" / "golf_sagamore_ocr.json"


def load_fixture():
    with open(FIXTURE) as f:
        return json.load(f)


def load_sagamore():
    with open(FIXTURE_SAGAMORE) as f:
        return json.load(f)


def test_cluster_by_x():
    syms = [
        {'text': '1', 'x': 100, 'y': 0, 'conf': 1.0},
        {'text': '0', 'x': 130, 'y': 0, 'conf': 1.0},
        {'text': '5', 'x': 160, 'y': 0, 'conf': 1.0},
        {'text': '7', 'x': 400, 'y': 0, 'conf': 1.0},
    ]
    clusters = _cluster_by_x(syms, gap_threshold=70)
    assert len(clusters) == 2, f"Expected 2 clusters, got {len(clusters)}"
    assert [s['text'] for s in clusters[0]] == ['1', '0', '5']
    assert [s['text'] for s in clusters[1]] == ['7']
    print("  ✓ _cluster_by_x groups adjacent symbols")


def test_dedup():
    syms = [
        {'text': '5', 'x': 970, 'y': 1690, 'conf': 0.9},
        {'text': '5', 'x': 970, 'y': 1690, 'conf': 0.95},
        {'text': '5', 'x': 1118, 'y': 1690, 'conf': 0.9},
    ]
    out = _deduplicate_symbols(syms)
    assert len(out) == 2, f"Expected 2 after dedup, got {len(out)}"
    dup = [s for s in out if abs(s['x'] - 970) < 5][0]
    assert dup['conf'] == 0.95
    print("  ✓ _deduplicate_symbols keeps high-confidence copy")


def _holes_by_num(player):
    return {h['hole_number']: h for h in player['holes']}


def test_both_players_detected():
    fx = load_fixture()
    result = _parse_scorecard_symbols(fx['symbols'], fx['width'], fx['height'])
    names = [p['name'] for p in result['players']]
    print(f"  detected players: {names}")
    assert 'TOM' in names
    assert 'CHRIS' in names
    print("  ✓ detects both TOM and CHRIS")


def test_tom_scores():
    fx = load_fixture()
    result = _parse_scorecard_symbols(fx['symbols'], fx['width'], fx['height'])
    tom = next((p for p in result['players'] if p['name'] == 'TOM'), None)
    assert tom is not None, "TOM not detected"
    by = _holes_by_num(tom)
    expected = {1:5, 2:8, 3:4, 4:6, 5:7, 6:8, 7:6, 8:4, 9:8,
                10:6, 11:5, 12:8, 13:5, 14:4, 15:4, 16:9, 17:4, 18:4}
    errors = []
    for hole, want in expected.items():
        got = by[hole]['strokes']
        if got != want:
            errors.append(f"hole {hole}: expected {want} got {got}")
    if errors:
        print("  ✗ TOM mismatches:")
        for e in errors:
            print(f"    - {e}")
        raise AssertionError("TOM scores incorrect")
    front = sum(by[h]['strokes'] for h in range(1, 10))
    back = sum(by[h]['strokes'] for h in range(10, 19))
    print(f"  TOM: front={front} back={back} total={front + back}")
    assert front == 56 and back == 49
    print("  ✓ TOM scores correct")


def test_chris_scores():
    fx = load_fixture()
    result = _parse_scorecard_symbols(fx['symbols'], fx['width'], fx['height'])
    chris = next((p for p in result['players'] if p['name'] == 'CHRIS'), None)
    assert chris is not None, "CHRIS not detected"
    by = _holes_by_num(chris)
    expected = {1:6, 2:5, 3:5, 4:5, 5:6, 6:7, 7:3, 8:3, 9:6,
                10:4, 11:6, 12:5, 13:5, 14:6, 15:4, 16:5, 17:8, 18:4}
    errors = []
    for hole, want in expected.items():
        got = by[hole]['strokes']
        if got != want:
            errors.append(f"hole {hole}: expected {want} got {got}")
    if errors:
        print("  ✗ CHRIS mismatches:")
        for e in errors:
            print(f"    - {e}")
        raise AssertionError("CHRIS scores incorrect")
    front = sum(by[h]['strokes'] for h in range(1, 10))
    back = sum(by[h]['strokes'] for h in range(10, 19))
    print(f"  CHRIS: front={front} back={back} total={front + back}")
    assert front == 46 and back == 47
    print("  ✓ CHRIS scores correct")


def test_no_label_rows_as_players():
    fx = load_fixture()
    result = _parse_scorecard_symbols(fx['symbols'], fx['width'], fx['height'])
    labels = {'PAR', 'HANDICAP', 'HDCP', 'HCP', 'BLACK', 'GOLD', 'GREEN',
              'WHITE', 'HOLE', 'OUT', 'IN', 'TOT', 'TOTAL', 'PLAYER'}
    for p in result['players']:
        assert p['name'] not in labels, f"Label {p['name']} misclassified"
    print("  ✓ no label rows treated as players")


def test_valid_structure():
    fx = load_fixture()
    result = _parse_scorecard_symbols(fx['symbols'], fx['width'], fx['height'])
    for p in result['players']:
        assert len(p['holes']) == 18
        hole_nums = sorted(h['hole_number'] for h in p['holes'])
        assert hole_nums == list(range(1, 19))
    print("  ✓ all players have 18 holes")


def test_find_par_label():
    fx = load_fixture()
    anchor = _find_par_label(fx['symbols'])
    assert anchor is not None, "PAR label not located"
    p, a, r = anchor
    assert p['text'].upper() == 'P'
    assert a['text'].upper() == 'A'
    assert r['text'].upper() == 'R'
    assert p['x'] < a['x'] < r['x'], "PAR letters not in left-to-right order"
    print(f"  PAR label at ({p['x']:.0f},{p['y']:.0f}) -> ({r['x']:.0f},{r['y']:.0f})")
    print("  ✓ finds PAR label anchor")


def test_extract_pars_fixture():
    """Fixture has a par-72 course (front 36 / back 36). Parser must recover it."""
    fx = load_fixture()
    gap = max(40, min(90, fx['width'] * 0.018))
    pars = _extract_pars(fx['symbols'], fx['width'], fx['height'], gap)
    assert pars is not None, "Par extraction returned None on real fixture"
    assert len(pars) == 18
    for i, v in enumerate(pars):
        assert v is not None, f"Hole {i+1} par is None"
        assert 3 <= v <= 6, f"Hole {i+1} par {v} out of 3..6 range"
    front = sum(pars[:9])
    back = sum(pars[9:])
    print(f"  pars: {pars}")
    print(f"  front={front} back={back} total={front + back}")
    assert front == 36, f"Front par should be 36, got {front}"
    assert back == 36, f"Back par should be 36, got {back}"
    print("  ✓ recovers par-72 layout from fixture")


def test_extract_pars_returns_none_without_label():
    """If there's no PAR label in the symbols, the extractor should return None
    so callers fall back to the default par-4 assumption."""
    symbols_no_par = [
        {'text': 'T', 'x': 100, 'y': 100, 'conf': 1.0},
        {'text': 'O', 'x': 150, 'y': 100, 'conf': 1.0},
        {'text': 'M', 'x': 200, 'y': 100, 'conf': 1.0},
        {'text': '4', 'x': 400, 'y': 100, 'conf': 1.0},
    ]
    pars = _extract_pars(symbols_no_par, 1000, 1000, 70)
    assert pars is None
    print("  ✓ returns None when PAR label is absent")


def test_holes_carry_extracted_par():
    """End-to-end: the player-row 'par' field reflects the OCR-extracted pars
    (not the hardcoded 4 fallback). Guards against regressions in the wiring
    between _extract_pars and _parse_scorecard_symbols."""
    fx = load_fixture()
    result = _parse_scorecard_symbols(fx['symbols'], fx['width'], fx['height'])
    tom = next((p for p in result['players'] if p['name'] == 'TOM'), None)
    chris = next((p for p in result['players'] if p['name'] == 'CHRIS'), None)
    assert tom is not None and chris is not None

    # Both players must share the same par sequence (pars are per hole, not per player).
    tom_by = _holes_by_num(tom)
    chris_by = _holes_by_num(chris)
    for h in range(1, 19):
        assert tom_by[h]['par'] == chris_by[h]['par'], (
            f"Hole {h}: TOM par={tom_by[h]['par']} != CHRIS par={chris_by[h]['par']}"
        )

    pars = [tom_by[h]['par'] for h in range(1, 19)]
    # Not the all-4 default — prove extraction ran.
    assert pars != [4] * 18, "Pars came from the default fallback, not OCR"
    # Par-72 layout totals, all values legal.
    assert sum(pars[:9]) == 36 and sum(pars[9:]) == 36
    assert all(3 <= v <= 6 for v in pars)
    # A par-72 layout has at least one par-3 and one par-5 on each nine.
    assert any(v == 3 for v in pars[:9]) and any(v == 5 for v in pars[:9])
    assert any(v == 3 for v in pars[9:]) and any(v == 5 for v in pars[9:])
    print(f"  pars: {pars}")
    print("  ✓ players' holes carry the extracted par values")


def test_sagamore_detects_all_four_players():
    """Sagamore Hampton card has JON, PAUL, CHRIS, TOM — four handwritten rows
    stacked close together with the yardage/tee rows only ~25 px below each
    player. Without the row-span cap in _group_rows, TOM's row daisy-chains
    into the yardages below it and TOM gets rejected."""
    fx = load_sagamore()
    from toms_gym.routes.golf_routes import _parse_scorecard_symbols
    result = _parse_scorecard_symbols(fx['symbols'], fx['width'], fx['height'])
    names = [p['name'] for p in result['players']]
    print(f"  detected: {names}")
    for expected in ['JON', 'PAUL', 'CHRIS', 'TOM']:
        assert expected in names, f"{expected} not detected on Sagamore card"
    print("  ✓ detects JON, PAUL, CHRIS, TOM on Sagamore Hampton card")


if __name__ == '__main__':
    tests = [
        ('cluster_by_x', test_cluster_by_x),
        ('dedup', test_dedup),
        ('both_players_detected', test_both_players_detected),
        ('tom_scores', test_tom_scores),
        ('chris_scores', test_chris_scores),
        ('no_label_rows', test_no_label_rows_as_players),
        ('valid_structure', test_valid_structure),
        ('find_par_label', test_find_par_label),
        ('extract_pars_fixture', test_extract_pars_fixture),
        ('extract_pars_none_without_label', test_extract_pars_returns_none_without_label),
        ('holes_carry_extracted_par', test_holes_carry_extracted_par),
        ('sagamore_detects_all_four_players', test_sagamore_detects_all_four_players),
    ]
    failed = 0
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            fn()
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    if failed == 0:
        print(f"PASSED {len(tests)}/{len(tests)}")
        sys.exit(0)
    else:
        print(f"FAILED {failed}/{len(tests)}")
        sys.exit(1)
