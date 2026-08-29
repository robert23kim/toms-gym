"""DB-free tests for the composite upload fast paths (signing cache, single
list_blobs verification, background part cleanup)."""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from toms_gym.routes import upload_routes


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(upload_routes.upload_bp)
    return app.test_client()


def _creds(expiry):
    c = MagicMock()
    c.token = "tok"
    c.expiry = expiry
    c.service_account_email = "sa@test"
    return c


def test_signing_credentials_are_cached_until_near_expiry(monkeypatch):
    upload_routes._signing_credentials = None
    fresh = _creds(datetime.utcnow() + timedelta(hours=1))
    default = MagicMock(return_value=(fresh, "proj"))
    monkeypatch.setattr("google.auth.default", default)
    upload_routes._get_signing_credentials()
    upload_routes._get_signing_credentials()
    assert default.call_count == 1
    assert fresh.refresh.call_count == 0

    fresh.expiry = datetime.utcnow() + timedelta(minutes=2)
    upload_routes._get_signing_credentials()
    assert fresh.refresh.call_count == 1
    upload_routes._signing_credentials = None


def test_composite_sign_issues_hour_long_urls_for_every_part(client, monkeypatch):
    seen = []

    def fake_sign(object_name, content_type, expires_minutes=15):
        seen.append((object_name, expires_minutes))
        return f"https://signed/{object_name}", "public"

    monkeypatch.setattr(upload_routes, "_generate_signed_upload_url", fake_sign)
    monkeypatch.setattr(upload_routes, "_get_signing_credentials", lambda: None)
    monkeypatch.setattr(upload_routes, "bucket", SimpleNamespace(name="b"))
    resp = client.post('/upload/composite/sign',
                       json={'filename': 'v.mp4', 'content_type': 'video/mp4', 'parts': 5})
    assert resp.status_code == 200, resp.get_json()
    parts = resp.get_json()['parts']
    assert [p['part_number'] for p in parts] == [1, 2, 3, 4, 5]
    assert all(exp == 60 for _, exp in seen)
    assert len(seen) == 5


def test_composite_complete_verifies_with_one_listing_and_defers_deletes(client, monkeypatch):
    bucket = MagicMock()
    bucket.name = "b"
    names = ["videos/x.mp4.part001", "videos/x.mp4.part002"]
    bucket.list_blobs.return_value = [SimpleNamespace(name=n) for n in names]
    deleted = []
    monkeypatch.setattr(upload_routes, "bucket", bucket)
    monkeypatch.setattr(upload_routes, "_delete_in_background", lambda objs: deleted.extend(objs))

    resp = client.post('/upload/composite/complete', json={
        'final_object': 'videos/x.mp4', 'content_type': 'video/mp4',
        'part_object_names': names,
    })
    assert resp.status_code == 200, resp.get_json()
    bucket.list_blobs.assert_called_once_with(prefix="videos/x.mp4.part")
    assert bucket.blob.return_value.exists.call_count == 0
    bucket.blob.return_value.compose.assert_called_once()
    assert deleted == names


def test_composite_complete_rejects_missing_part(client, monkeypatch):
    bucket = MagicMock()
    bucket.list_blobs.return_value = [SimpleNamespace(name="videos/x.mp4.part001")]
    monkeypatch.setattr(upload_routes, "bucket", bucket)
    resp = client.post('/upload/composite/complete', json={
        'final_object': 'videos/x.mp4',
        'part_object_names': ["videos/x.mp4.part001", "videos/x.mp4.part002"],
    })
    assert resp.status_code == 400
    bucket.blob.return_value.compose.assert_not_called()
