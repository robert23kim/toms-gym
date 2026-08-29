import io
import json
import pathlib
import uuid
from datetime import datetime

import pytest
from sqlalchemy import text

from toms_gym.routes import bowling_sheet_routes

NIGHT_PLAYERS = [
    {"name": "Jess", "games": [116, 133, 91], "scratch": 340, "hdcp": 270, "total": 610},
    {"name": "Jon", "games": [190, 163, 164], "scratch": 517, "hdcp": 204, "total": 721},
    {"name": "Paul", "games": [134, 151, 150], "scratch": 435, "hdcp": 216, "total": 651},
    {"name": "Tom", "games": [164, 236, 196], "scratch": 596, "hdcp": 111, "total": 707},
]

TOM_FRAMES = [["X"], ["8", "1"], ["X"], ["9", "/"], ["X"], ["6", "3"], ["8", "/"], ["X"], ["9", "-"], ["7", "/", "9"]]


def _night_parse():
    return {
        "team_name": "Team 28",
        "players": [
            {**p, "inferred": [], "flagged": False, "flag_reason": None} for p in NIGHT_PLAYERS
        ],
    }


def _night_games(played_on):
    rows = []
    for player in NIGHT_PLAYERS:
        for i, score in enumerate(player["games"], start=1):
            rows.append({
                "player_name": player["name"],
                "game_number": i,
                "total_score": score,
                "hdcp": None,
                "frames": None,
                "computed_total": None,
                "flagged": False,
                "flag_reason": None,
                "confidence": 0.95,
            })
    return rows


def _game_parse():
    return {
        "team_name": "Team 11",
        "players": [{
            "name": "TOM",
            "frames": TOM_FRAMES,
            "printed_cumulative": [19, 28, 48, 68, 87, 96, 116, 135, 144, 163],
            "total": 163,
            "flagged": False,
            "flag_reason": None,
        }],
    }


def _game_games(played_on):
    return [{
        "player_name": "TOM",
        "game_number": 1,
        "total_score": 163,
        "hdcp": None,
        "frames": TOM_FRAMES,
        "computed_total": 163,
        "flagged": False,
        "flag_reason": None,
        "confidence": 0.9,
    }]


@pytest.fixture(autouse=True)
def _no_gcs(monkeypatch):
    monkeypatch.setattr(
        bowling_sheet_routes, "_store_sheet_image",
        lambda image_bytes, content_type, path: f"https://storage.example/{path}",
    )


@pytest.fixture
def stub_night(monkeypatch):
    def fake(image_bytes, sheet_type, played_on):
        return _night_parse(), _night_games(played_on), 0
    monkeypatch.setattr(bowling_sheet_routes, "_ocr_and_parse", fake)


@pytest.fixture
def stub_game(monkeypatch):
    def fake(image_bytes, sheet_type, played_on):
        return _game_parse(), _game_games(played_on), 90
    monkeypatch.setattr(bowling_sheet_routes, "_ocr_and_parse", fake)


def _make_user(db_session):
    user_id = str(uuid.uuid4())
    unique = uuid.uuid4().hex[:8]
    db_session.execute(
        text("""
            INSERT INTO "User" (id, username, email, name, auth_method, created_at, status, role)
            VALUES (:id, :username, :email, :name, 'password', :created_at, 'active', 'user')
        """),
        {
            "id": user_id,
            "username": f"bowler_{unique}",
            "email": f"bowler_{unique}@example.com",
            "name": "Bowling Test User",
            "created_at": datetime.utcnow(),
        },
    )
    db_session.commit()
    return user_id


def _upload(client, user_id, sheet_type="night", played_on="2026-08-28", filename="sheet.jpg"):
    return client.post(
        '/bowling/scoresheet/upload',
        data={
            "image": (io.BytesIO(b"not-a-real-jpeg"), filename),
            "user_id": user_id,
            "sheet_type": sheet_type,
            "played_on": played_on,
        },
        content_type='multipart/form-data',
    )


def test_upload_night_sheet(client, db_session, stub_night):
    user_id = _make_user(db_session)
    res = _upload(client, user_id)
    assert res.status_code == 200
    body = res.get_json()
    assert body["sheet_type"] == "night"
    assert body["played_on"] == "2026-08-28"
    assert body["team_name"] == "Team 28"
    assert body["processing_status"] == "parsed"
    assert body["flagged_count"] == 0
    assert [p["name"] for p in body["players"]] == ["Jess", "Jon", "Paul", "Tom"]
    tom = [p for p in body["players"] if p["name"] == "Tom"][0]
    assert [g["total_score"] for g in tom["games"]] == [164, 236, 196]
    assert tom["games"][0]["frames"] is None
    assert body["image_url"].endswith(f"{body['sheet_id']}.jpg")


def test_get_sheet_matches_upload(client, db_session, stub_night):
    user_id = _make_user(db_session)
    uploaded = _upload(client, user_id).get_json()
    fetched = client.get(f'/bowling/scoresheet/{uploaded["sheet_id"]}')
    assert fetched.status_code == 200
    assert fetched.get_json() == uploaded


def test_get_missing_sheet_404(client):
    assert client.get(f'/bowling/scoresheet/{uuid.uuid4()}').status_code == 404
    assert client.get('/bowling/scoresheet/not-a-uuid').status_code == 404


def test_upload_game_sheet_stores_frames(client, db_session, stub_game):
    user_id = _make_user(db_session)
    body = _upload(client, user_id, sheet_type="game").get_json()
    game = body["players"][0]["games"][0]
    assert game["frames"] == TOM_FRAMES
    assert game["computed_total"] == 163
    assert body["sheet_type"] == "game"


def test_upload_rejects_bad_sheet_type(client, db_session, stub_night):
    user_id = _make_user(db_session)
    res = _upload(client, user_id, sheet_type="league")
    assert res.status_code == 400
    assert "sheet_type" in res.get_json()["error"]


def test_upload_rejects_bad_played_on(client, db_session, stub_night):
    user_id = _make_user(db_session)
    res = _upload(client, user_id, played_on="28-08-2026")
    assert res.status_code == 400


def test_upload_requires_user(client, stub_night):
    res = client.post(
        '/bowling/scoresheet/upload',
        data={"image": (io.BytesIO(b"x"), "sheet.jpg"), "sheet_type": "night"},
        content_type='multipart/form-data',
    )
    assert res.status_code == 400


def test_upload_requires_image(client, db_session, stub_night):
    user_id = _make_user(db_session)
    res = client.post(
        '/bowling/scoresheet/upload',
        data={"user_id": user_id, "sheet_type": "night"},
        content_type='multipart/form-data',
    )
    assert res.status_code == 400


def test_upload_rejects_oversize_image(client, db_session, stub_night):
    user_id = _make_user(db_session)
    res = client.post(
        '/bowling/scoresheet/upload',
        data={
            "image": (io.BytesIO(b"0" * (20 * 1024 * 1024 + 1)), "sheet.jpg"),
            "user_id": user_id,
            "sheet_type": "night",
        },
        content_type='multipart/form-data',
    )
    assert res.status_code == 413


def test_upload_resolves_user_by_email(client, db_session, stub_night):
    email = f"newbowler_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post(
        '/bowling/scoresheet/upload',
        data={
            "image": (io.BytesIO(b"x"), "sheet.jpg"),
            "email": email,
            "sheet_type": "night",
        },
        content_type='multipart/form-data',
    )
    assert res.status_code == 200
    created = db_session.execute(
        text('SELECT id FROM "User" WHERE LOWER(email) = :e'), {"e": email}
    ).fetchone()
    assert created is not None


def test_failed_parse_still_stores_sheet(client, db_session, monkeypatch):
    user_id = _make_user(db_session)

    def boom(image_bytes, sheet_type, played_on):
        raise RuntimeError("no player rows found")

    monkeypatch.setattr(bowling_sheet_routes, "_ocr_and_parse", boom)
    res = _upload(client, user_id)
    assert res.status_code == 200
    body = res.get_json()
    assert body["processing_status"] == "failed"
    assert body["players"] == []
    assert "no player rows" in body["error_message"]


def test_confirm_claims_rows_and_feeds_games_and_insights(client, db_session, stub_night):
    user_id = _make_user(db_session)
    sheet_id = _upload(client, user_id).get_json()["sheet_id"]

    res = client.put(f'/bowling/scoresheet/{sheet_id}/confirm', json={
        "claim_player": "Tom",
        "players": [
            {"name": p["name"], "games": [
                {"game_number": i, "total_score": s, "hdcp": None}
                for i, s in enumerate(p["games"], start=1)
            ]}
            for p in NIGHT_PLAYERS
        ],
    })
    assert res.status_code == 200
    assert res.get_json()["processing_status"] == "confirmed"

    games = client.get(f'/bowling/games?user_id={user_id}').get_json()
    assert games["total"] == 3
    assert [g["total_score"] for g in games["games"]] == [196, 236, 164]
    assert all(g["has_frames"] is False for g in games["games"])
    assert games["games"][0]["sheet_id"] == sheet_id

    insights = client.get(f'/bowling/insights/{user_id}').get_json()
    assert insights["games"] == 3
    assert insights["high"] == 236
    assert insights["average"] == 198.7
    assert insights["frame_stats"] is None
    assert len(insights["recent"]) == 3


def test_confirm_edits_scores(client, db_session, stub_night):
    user_id = _make_user(db_session)
    sheet_id = _upload(client, user_id).get_json()["sheet_id"]
    res = client.put(f'/bowling/scoresheet/{sheet_id}/confirm', json={
        "claim_player": "Tom",
        "players": [{"name": "Tom", "games": [
            {"game_number": 1, "total_score": 170, "hdcp": 37},
            {"game_number": 2, "total_score": 236, "hdcp": 37},
        ]}],
    })
    assert res.status_code == 200
    body = res.get_json()
    assert len(body["players"]) == 1
    assert [g["total_score"] for g in body["players"][0]["games"]] == [170, 236]
    assert body["players"][0]["games"][0]["hdcp"] == 37


def test_confirm_with_frames_recomputes_total(client, db_session, stub_game):
    user_id = _make_user(db_session)
    sheet_id = _upload(client, user_id, sheet_type="game").get_json()["sheet_id"]
    res = client.put(f'/bowling/scoresheet/{sheet_id}/confirm', json={
        "claim_player": "TOM",
        "players": [{"name": "TOM", "games": [
            {"game_number": 1, "total_score": None, "frames": TOM_FRAMES},
        ]}],
    })
    assert res.status_code == 200
    game = res.get_json()["players"][0]["games"][0]
    assert game["computed_total"] == 163
    assert game["total_score"] == 163

    insights = client.get(f'/bowling/insights/{user_id}').get_json()
    assert insights["frame_stats"]["frames_analyzed"] == 10
    assert insights["frame_stats"]["clean_games"] == 0


def test_confirm_rejects_invalid_frames(client, db_session, stub_game):
    user_id = _make_user(db_session)
    sheet_id = _upload(client, user_id, sheet_type="game").get_json()["sheet_id"]
    res = client.put(f'/bowling/scoresheet/{sheet_id}/confirm', json={
        "claim_player": None,
        "players": [{"name": "TOM", "games": [
            {"game_number": 1, "total_score": 100, "frames": [["9", "9"]] + [["-", "-"]] * 9},
        ]}],
    })
    assert res.status_code == 400
    assert "frame 1" in json.dumps(res.get_json())


def test_confirm_requires_players_list(client, db_session, stub_night):
    user_id = _make_user(db_session)
    sheet_id = _upload(client, user_id).get_json()["sheet_id"]
    assert client.put(f'/bowling/scoresheet/{sheet_id}/confirm', json={}).status_code == 400
    assert client.put(f'/bowling/scoresheet/{uuid.uuid4()}/confirm',
                      json={"players": []}).status_code == 404


def test_games_pagination_and_cap(client, db_session, stub_night):
    user_id = _make_user(db_session)
    sheet_id = _upload(client, user_id).get_json()["sheet_id"]
    client.put(f'/bowling/scoresheet/{sheet_id}/confirm', json={
        "claim_player": "Tom",
        "players": [{"name": "Tom", "games": [
            {"game_number": i, "total_score": s} for i, s in enumerate([164, 236, 196], start=1)
        ]}],
    })
    page = client.get(f'/bowling/games?user_id={user_id}&limit=2&offset=1').get_json()
    assert page["limit"] == 2 and page["offset"] == 1 and page["total"] == 3
    assert len(page["games"]) == 2
    capped = client.get(f'/bowling/games?user_id={user_id}&limit=500').get_json()
    assert capped["limit"] == 50


def test_games_requires_user_id(client):
    assert client.get('/bowling/games').status_code == 400


def test_unconfirmed_games_are_not_listed(client, db_session, stub_night):
    user_id = _make_user(db_session)
    _upload(client, user_id)
    assert client.get(f'/bowling/games?user_id={user_id}').get_json()["total"] == 0
    empty = client.get(f'/bowling/insights/{user_id}').get_json()
    assert empty["games"] == 0
    assert [t["key"] for t in empty["tips"]] == ["no_games"]
    assert empty["recent"] == []


def test_delete_sheet(client, db_session, stub_night):
    user_id = _make_user(db_session)
    sheet_id = _upload(client, user_id).get_json()["sheet_id"]
    assert client.delete(f'/bowling/scoresheet/{sheet_id}').status_code == 204
    assert client.get(f'/bowling/scoresheet/{sheet_id}').status_code == 404
    assert client.delete(f'/bowling/scoresheet/{sheet_id}').status_code == 404
    remaining = db_session.execute(
        text('SELECT count(*) FROM "BowlingGame" WHERE sheet_id = :s'), {"s": sheet_id}
    ).scalar()
    assert remaining == 0


# --- real parser wiring (Task 3), OCR replayed from the cached fixture -------

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "bowling"


def _ocr_fixture(stem):
    return json.loads((FIXTURES / f"{stem}_ocr.json").read_text())


def _truth(stem):
    return json.loads((FIXTURES / f"{stem}_truth.json").read_text())


def _real_jpeg():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(buf, format="JPEG")
    return buf.getvalue()


def _replay(monkeypatch, passes):
    """Feed _ocr_and_parse a canned (words, symbols, page_w, page_h) per rotation."""
    from toms_gym.services import vision_ocr

    calls = []

    def fake_ocr(image_bytes):
        calls.append(len(image_bytes))
        return f"annotation-{len(calls)}"

    def fake_extract(annotation):
        data = passes[len(calls) - 1]
        if data is None:
            return [], [], 0, 0
        return data["words"], data["symbols"], data["page_w"], data["page_h"]

    monkeypatch.setattr(vision_ocr, "run_document_ocr", fake_ocr)
    monkeypatch.setattr(vision_ocr, "extract_words_and_symbols", fake_extract)
    return calls


def test_upload_uses_real_parser_on_night_fixture(client, db_session, monkeypatch):
    user_id = _make_user(db_session)
    _replay(monkeypatch, [_ocr_fixture("night_01")])
    res = client.post(
        '/bowling/scoresheet/upload',
        data={
            "image": (io.BytesIO(_real_jpeg()), "night_01.jpg"),
            "user_id": user_id,
            "sheet_type": "night",
            "played_on": "2026-08-28",
        },
        content_type='multipart/form-data',
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["processing_status"] == "parsed"
    assert body["flagged_count"] == 0
    truth = {p["name"]: p["games"] for p in _truth("night_01")["players"]}
    parsed = {p["name"]: [g["total_score"] for g in p["games"]] for p in body["players"]}
    assert parsed == truth


def test_upload_retries_rotations_when_first_pass_is_blank(client, db_session, monkeypatch):
    user_id = _make_user(db_session)
    calls = _replay(monkeypatch, [None, _ocr_fixture("night_01")])
    res = client.post(
        '/bowling/scoresheet/upload',
        data={
            "image": (io.BytesIO(_real_jpeg()), "night_01.jpg"),
            "user_id": user_id,
            "sheet_type": "night",
        },
        content_type='multipart/form-data',
    )
    assert res.status_code == 200
    body = res.get_json()
    assert len(calls) == 2
    assert body["processing_status"] == "parsed"
    assert len(body["players"]) == 4


def test_upload_uses_real_parser_on_game_fixture(client, db_session, monkeypatch):
    user_id = _make_user(db_session)
    _replay(monkeypatch, [_ocr_fixture("game_01")])
    res = client.post(
        '/bowling/scoresheet/upload',
        data={
            "image": (io.BytesIO(_real_jpeg()), "game_01.jpg"),
            "user_id": user_id,
            "sheet_type": "game",
        },
        content_type='multipart/form-data',
    )
    assert res.status_code == 200
    body = res.get_json()
    truth = {p["name"]: p for p in _truth("game_01")["players"]}
    assert {p["name"] for p in body["players"]} == set(truth)
    for player in body["players"]:
        game = player["games"][0]
        assert game["frames"] == truth[player["name"]]["frames"]
        assert game["computed_total"] == truth[player["name"]]["total"]
