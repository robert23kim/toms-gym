"""Grid parser end-to-end tests against real scorecard fixtures.

Fully offline: images + cached Vision OCR dumps live in
tests/fixtures/scorecards/. Ground truth was human-transcribed from the
photos (see *_truth.json `notes` for genuinely-ambiguous cells).
"""
import json
import pathlib

import pytest

from toms_gym.services import scorecard_grid as sg

FIXTURES = pathlib.Path(__file__).parent / 'fixtures' / 'scorecards'


def _parse(stem):
    image_bytes = (FIXTURES / f'{stem}.jpg').read_bytes()
    ocr = json.loads((FIXTURES / f'{stem}_ocr.json').read_text())
    return sg.parse_scorecard_grid(
        image_bytes, ocr['symbols'], ocr['width'], ocr['height'])


def _truth(stem):
    return json.loads((FIXTURES / f'{stem}_truth.json').read_text())


@pytest.fixture(scope='module')
def full_card():
    return _parse('1000005113'), _truth('1000005113')


@pytest.fixture(scope='module')
def sparse_card():
    return _parse('1000005117'), _truth('1000005117')


def _assert_players_match(result, truth):
    got = {p['name']: p for p in result['players']}
    for tp in truth['players']:
        assert tp['name'] in got, f"player {tp['name']} not detected"
        gp = got[tp['name']]
        ambiguous = {int(k): v for k, v in tp.get('ambiguous_readings', {}).items()}
        for i, tv in enumerate(tp['holes']):
            gv = gp['holes'][i]['strokes']
            if tv is None:
                assert gv is None, f"{tp['name']} h{i+1}: spurious {gv}"
            elif i + 1 in ambiguous:
                assert gv in ambiguous[i + 1], f"{tp['name']} h{i+1}: {gv}"
            else:
                assert gv == tv, f"{tp['name']} h{i+1}: {gv} != {tv}"


class TestFullCard:
    def test_all_players_all_holes(self, full_card):
        result, truth = full_card
        _assert_players_match(result, truth)

    def test_pars(self, full_card):
        result, truth = full_card
        assert result['pars'] == truth['pars']

    def test_tees(self, full_card):
        result, truth = full_card
        got = {t['name']: t for t in result['tees']}
        for tt in truth['tees']:
            assert tt['name'] in got
            assert got[tt['name']]['rating'] == tt['rating']
            assert got[tt['name']]['slope'] == tt['slope']

    def test_checksum_catches_scorer_arithmetic_error(self, full_card):
        """Tom's front nine sums to 48 but the scorer wrote 49 — the
        mismatch must be flagged, not silently accepted."""
        result, _ = full_card
        tom = next(p for p in result['players'] if p['name'] == 'TOM')
        assert tom['checksums']['out']['ok'] is False
        assert any(h['flagged'] for h in tom['holes'] if h['hole_number'] <= 9)

    def test_checksum_passes_consistent_player(self, full_card):
        result, _ = full_card
        paul = next(p for p in result['players'] if p['name'] == 'PAUL')
        assert paul['checksums']['out'] == {'sum': 50, 'written': 50, 'ok': True}
        assert paul['checksums']['in'] == {'sum': 47, 'written': 47, 'ok': True}


class TestSparseCard:
    def test_back_nine_only_scores_on_correct_holes(self, sparse_card):
        """The legacy parser assigned these to holes 1-9; the grid parser
        must place them on 10-18 with empty front nines."""
        result, truth = sparse_card
        _assert_players_match(result, truth)

    def test_single_score_player_detected(self, sparse_card):
        result, _ = sparse_card
        nick = next((p for p in result['players'] if p['name'] == 'NICK'), None)
        assert nick is not None
        assert nick['holes'][9]['strokes'] == 5

    def test_pars_and_tees(self, sparse_card):
        result, truth = sparse_card
        assert result['pars'] == truth['pars']
        assert {t['name'] for t in result['tees']} == {t['name'] for t in truth['tees']}


class TestOrientedReencode:
    """The upload route re-encodes images (_auto_orient_image, JPEG q95)
    before OCR. The softer JPEG drops some thin horizontal grid lines and
    merges grid rows — the PAR row must still be found via text-line
    banding. Regression for the prod fallback 'PAR row not found in grid'."""

    def test_sparse_card_reencoded_still_grid_parses(self):
        image_bytes = (FIXTURES / '1000005117_oriented.jpg').read_bytes()
        ocr = json.loads((FIXTURES / '1000005117_oriented_ocr.json').read_text())
        result = sg.parse_scorecard_grid(
            image_bytes, ocr['symbols'], ocr['width'], ocr['height'])
        assert result['pars'] == _truth('1000005117')['pars']
        got = {p['name']: p for p in result['players']}
        assert set(got) == {'TOM', 'PAUL', 'NICK'}
        tom = got['TOM']
        assert all(h['strokes'] is None for h in tom['holes'][:9])
        assert [h['strokes'] for h in tom['holes'][9:17]] == [4, 5, 5, 7, 7, 5, 5, 6]
        assert len(result['tees']) == 5


class TestFallbackBehavior:
    def test_garbage_image_raises_grid_parse_error(self):
        with pytest.raises(sg.GridParseError):
            sg.parse_scorecard_grid(b'not an image', [], 0, 0)

    def test_blank_image_raises_grid_parse_error(self):
        import cv2
        import numpy as np
        blank = np.full((800, 1200, 3), 255, np.uint8)
        ok, buf = cv2.imencode('.jpg', blank)
        assert ok
        with pytest.raises(sg.GridParseError):
            sg.parse_scorecard_grid(buf.tobytes(), [], 1200, 800)
