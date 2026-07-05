"""Tests for /log-error. DB-free: run with --noconftest.

    venv/bin/python -m pytest tests/test_telemetry_routes.py --noconftest
"""
import json

import pytest
from flask import Flask

from toms_gym.routes.telemetry_routes import telemetry_bp


@pytest.fixture()
def client():
    app = Flask(__name__)
    app.register_blueprint(telemetry_bp)
    return app.test_client()


def _payload():
    return {
        "page": "UploadVideo",
        "action": "upload-died",
        "error": "session died at compress-start",
        "details": {"fileSizeMB": 412.5},
        "userAgent": "test-agent",
        "url": "https://t30g.com/upload",
        "build": 1783091547,
        "platform": "web",
    }


def test_log_line_carries_build_and_platform(client, caplog):
    # The build stamp is how a stale client in the wild gets identified —
    # it must survive into the Cloud Run log line, not just the payload.
    resp = client.post("/log-error", json=_payload())
    assert resp.status_code == 204
    assert "build=1783091547" in caplog.text
    assert "platform=web" in caplog.text


def test_accepts_application_json(client, caplog):
    resp = client.post("/log-error", json=_payload())
    assert resp.status_code == 204
    assert "FRONTEND_ERROR" in caplog.text
    assert "upload-died" in caplog.text


def test_accepts_text_plain_beacon_body(client, caplog):
    # navigator.sendBeacon can only send CORS-safelisted content types
    # cross-origin without a preflight, so the payload arrives as text/plain.
    resp = client.post(
        "/log-error",
        data=json.dumps(_payload()),
        content_type="text/plain",
    )
    assert resp.status_code == 204
    assert "FRONTEND_ERROR" in caplog.text
    assert "upload-died" in caplog.text
    assert "412.5" in caplog.text


def test_unparseable_body_still_204s(client, caplog):
    resp = client.post("/log-error", data="{not json", content_type="text/plain")
    assert resp.status_code == 204
    assert "FRONTEND_ERROR" in caplog.text  # logs with unknown fields


def test_oversized_body_dropped(client):
    big = json.dumps({"error": "x" * 5000})
    resp = client.post("/log-error", data=big, content_type="text/plain")
    assert resp.status_code == 204
