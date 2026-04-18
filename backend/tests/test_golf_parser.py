"""Tests for the golf scorecard OCR parser.

These tests drive the refactor from a single-player, word-level parser to a
symbol-level, multi-player parser. They use a saved fixture of real OCR output
from `golf_scorecard.jpg` (two handwritten players: TOM and CHRIS).

Expected scores (verified against totals printed on the card):
  TOM:   front [5,8,4,6,7,8,6,4,8]=56 / back [6,5,8,5,4,4,9,4,4]=49 / total 105
  CHRIS: front [6,5,5,5,6,7,3,3,6]=46 / back [4,6,5,5,6,4,5,8,4]=47 / total 93
"""
import json
import pathlib

import pytest

from toms_gym.routes.golf_routes import (
    _parse_scorecard_symbols,
    _group_rows,
    _cluster_by_x,
    _deduplicate_symbols,
)


FIXTURE_PATH = pathlib.Path(__file__).parent / "fixtures" / "golf_scorecard_ocr.json"


@pytest.fixture
def real_ocr():
    """Symbol-level OCR output from Vision API on golf_scorecard.jpg."""
    with open(FIXTURE_PATH) as f:
        return json.load(f)


# ---- Unit tests for helper functions ----


def test_cluster_by_x_groups_adjacent_symbols():
    syms = [
        {'text': '1', 'x': 100, 'y': 0, 'conf': 1.0},
        {'text': '0', 'x': 130, 'y': 0, 'conf': 1.0},
        {'text': '5', 'x': 160, 'y': 0, 'conf': 1.0},
        {'text': '7', 'x': 400, 'y': 0, 'conf': 1.0},
    ]
    clusters = _cluster_by_x(syms, gap_threshold=70)
    assert len(clusters) == 2
    assert [s['text'] for s in clusters[0]] == ['1', '0', '5']
    assert [s['text'] for s in clusters[1]] == ['7']


def test_deduplicate_symbols_removes_same_text_same_position():
    syms = [
        {'text': '5', 'x': 970, 'y': 1690, 'conf': 0.9},
        {'text': '5', 'x': 970, 'y': 1690, 'conf': 0.95},
        {'text': '5', 'x': 1118, 'y': 1690, 'conf': 0.9},
    ]
    out = _deduplicate_symbols(syms)
    assert len(out) == 2
    # Keeps the higher-confidence duplicate
    dup_survivor = [s for s in out if abs(s['x'] - 970) < 5][0]
    assert dup_survivor['conf'] == 0.95


# ---- Integration tests against real OCR fixture ----


def test_parser_detects_both_players(real_ocr):
    result = _parse_scorecard_symbols(
        real_ocr['symbols'], real_ocr['width'], real_ocr['height']
    )
    assert 'players' in result
    names = [p['name'] for p in result['players']]
    assert 'TOM' in names, f"Expected TOM in detected players, got {names}"
    assert 'CHRIS' in names, f"Expected CHRIS in detected players, got {names}"


def _holes_by_num(player):
    return {h['hole_number']: h for h in player['holes']}


def test_tom_scores_match_expected(real_ocr):
    result = _parse_scorecard_symbols(
        real_ocr['symbols'], real_ocr['width'], real_ocr['height']
    )
    tom = next(p for p in result['players'] if p['name'] == 'TOM')
    by_hole = _holes_by_num(tom)

    expected = {
        1: 5, 2: 8, 3: 4, 4: 6, 5: 7, 6: 8, 7: 6, 8: 4, 9: 8,
        10: 6, 11: 5, 12: 8, 13: 5, 14: 4, 15: 4, 16: 9, 17: 4, 18: 4,
    }
    for hole, expected_strokes in expected.items():
        assert by_hole[hole]['strokes'] == expected_strokes, (
            f"TOM hole {hole}: expected {expected_strokes}, "
            f"got {by_hole[hole]['strokes']}"
        )

    # Totals sanity check
    front = sum(by_hole[h]['strokes'] for h in range(1, 10))
    back = sum(by_hole[h]['strokes'] for h in range(10, 19))
    assert front == 56, f"TOM front 9 total: {front}"
    assert back == 49, f"TOM back 9 total: {back}"
    assert front + back == 105


def test_chris_scores_match_expected(real_ocr):
    result = _parse_scorecard_symbols(
        real_ocr['symbols'], real_ocr['width'], real_ocr['height']
    )
    chris = next(p for p in result['players'] if p['name'] == 'CHRIS')
    by_hole = _holes_by_num(chris)

    expected = {
        1: 6, 2: 5, 3: 5, 4: 5, 5: 6, 6: 7, 7: 3, 8: 3, 9: 6,
        10: 4, 11: 6, 12: 5, 13: 5, 14: 6, 15: 4, 16: 5, 17: 8, 18: 4,
    }
    for hole, expected_strokes in expected.items():
        assert by_hole[hole]['strokes'] == expected_strokes, (
            f"CHRIS hole {hole}: expected {expected_strokes}, "
            f"got {by_hole[hole]['strokes']}"
        )

    front = sum(by_hole[h]['strokes'] for h in range(1, 10))
    back = sum(by_hole[h]['strokes'] for h in range(10, 19))
    assert front == 46
    assert back == 47
    assert front + back == 93


def test_parser_does_not_treat_label_rows_as_players(real_ocr):
    """PAR, HANDICAP, BLACK, GOLD, GREEN, WHITE rows must not show up as players."""
    result = _parse_scorecard_symbols(
        real_ocr['symbols'], real_ocr['width'], real_ocr['height']
    )
    labels = {'PAR', 'HANDICAP', 'HDCP', 'HCP', 'BLACK', 'GOLD', 'GREEN',
              'WHITE', 'HOLE', 'OUT', 'IN', 'TOT', 'TOTAL', 'PLAYER'}
    for p in result['players']:
        assert p['name'] not in labels, f"Label {p['name']} misclassified as player"


def test_all_holes_have_valid_structure(real_ocr):
    result = _parse_scorecard_symbols(
        real_ocr['symbols'], real_ocr['width'], real_ocr['height']
    )
    for p in result['players']:
        assert len(p['holes']) == 18
        hole_nums = sorted(h['hole_number'] for h in p['holes'])
        assert hole_nums == list(range(1, 19))
        for h in p['holes']:
            assert 'par' in h and 'strokes' in h and 'ocr_confidence' in h
