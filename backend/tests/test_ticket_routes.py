import uuid
from datetime import datetime

import bcrypt
from sqlalchemy import text


def _make_user(db_session):
    """Insert a minimal user and return its id."""
    user_id = str(uuid.uuid4())
    unique = uuid.uuid4().hex[:8]
    hashed = bcrypt.hashpw(b"TestPassword123!", bcrypt.gensalt()).decode('utf-8')
    db_session.execute(
        text("""
            INSERT INTO "User" (id, username, email, password_hash, name, auth_method, created_at, status, role)
            VALUES (:id, :username, :email, :password, :name, 'password', :created_at, 'active', 'user')
        """),
        {
            "id": user_id,
            "username": f"ticketuser_{unique}",
            "email": f"ticketuser_{unique}@example.com",
            "password": hashed,
            "name": "Ticket Test User",
            "created_at": datetime.utcnow(),
        },
    )
    db_session.commit()
    return user_id


def test_create_bug_happy_path(client):
    """Creating a bug ticket returns 201 with a ticket_id."""
    response = client.post('/tickets', json={
        "type": "bug",
        "title": "Upload button does nothing",
        "description": "Clicking upload on the golf page silently fails.",
        "page_url": "https://example.com/golf/upload",
    })
    assert response.status_code == 201
    data = response.get_json()
    assert "ticket_id" in data
    # Returned id is a valid UUID.
    uuid.UUID(data["ticket_id"])

    # And it's retrievable.
    fetched = client.get(f'/tickets/{data["ticket_id"]}')
    assert fetched.status_code == 200
    body = fetched.get_json()
    assert body["type"] == "bug"
    assert body["title"] == "Upload button does nothing"
    assert body["status"] == "open"
    assert body["page_url"] == "https://example.com/golf/upload"


def test_create_feature_with_email_no_user(client):
    """A feature request with an email but no user_id is stored in contact_email."""
    response = client.post('/tickets', json={
        "type": "feature",
        "title": "Dark mode",
        "description": "Please add a dark theme.",
        "email": "requester@example.com",
    })
    assert response.status_code == 201
    ticket_id = response.get_json()["ticket_id"]

    fetched = client.get(f'/tickets/{ticket_id}').get_json()
    assert fetched["type"] == "feature"
    assert fetched["contact_email"] == "requester@example.com"
    assert fetched["user_id"] is None


def test_create_with_valid_user(client, db_session):
    """A valid, existing user_id is attached to the ticket."""
    user_id = _make_user(db_session)
    response = client.post('/tickets', json={
        "type": "bug",
        "title": "Profile crash",
        "description": "My profile page 500s.",
        "user_id": user_id,
    })
    assert response.status_code == 201
    ticket_id = response.get_json()["ticket_id"]
    fetched = client.get(f'/tickets/{ticket_id}').get_json()
    assert fetched["user_id"] == user_id


def test_create_with_garbage_user_id_is_ignored(client):
    """A non-UUID user_id is dropped, not rejected."""
    response = client.post('/tickets', json={
        "type": "bug",
        "title": "Something broke",
        "description": "Details here.",
        "user_id": "not-a-uuid",
    })
    assert response.status_code == 201
    ticket_id = response.get_json()["ticket_id"]
    fetched = client.get(f'/tickets/{ticket_id}').get_json()
    assert fetched["user_id"] is None


def test_create_with_nonexistent_user_id_falls_back(client):
    """A well-formed but nonexistent user_id is dropped via FK retry, still 201."""
    response = client.post('/tickets', json={
        "type": "feature",
        "title": "Ghost user",
        "description": "user does not exist.",
        "user_id": str(uuid.uuid4()),
    })
    assert response.status_code == 201
    ticket_id = response.get_json()["ticket_id"]
    fetched = client.get(f'/tickets/{ticket_id}').get_json()
    assert fetched["user_id"] is None


def test_create_bad_type(client):
    response = client.post('/tickets', json={
        "type": "question",
        "title": "Hi",
        "description": "Not a bug or feature.",
    })
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_missing_title(client):
    response = client.post('/tickets', json={
        "type": "bug",
        "title": "   ",
        "description": "Whitespace title.",
    })
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_oversized_description(client):
    response = client.post('/tickets', json={
        "type": "bug",
        "title": "Too much text",
        "description": "x" * 5001,
    })
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_list_and_status_filter(client):
    """List returns tickets and honors ?status= filtering."""
    marker = f"filtertest-{uuid.uuid4().hex[:8]}"
    # Create two tickets, move one to in_progress.
    r1 = client.post('/tickets', json={
        "type": "bug", "title": f"{marker}-open", "description": "still open",
    })
    r2 = client.post('/tickets', json={
        "type": "feature", "title": f"{marker}-progress", "description": "working on it",
    })
    id2 = r2.get_json()["ticket_id"]
    client.put(f'/tickets/{id2}/status', json={"status": "in_progress"})

    # Unfiltered list includes both.
    all_titles = [t["title"] for t in client.get('/tickets?limit=100').get_json()["tickets"]]
    assert f"{marker}-open" in all_titles
    assert f"{marker}-progress" in all_titles

    # status=in_progress excludes the open one.
    in_progress = client.get('/tickets?status=in_progress&limit=100').get_json()["tickets"]
    titles = [t["title"] for t in in_progress]
    assert f"{marker}-progress" in titles
    assert f"{marker}-open" not in titles
    assert all(t["status"] == "in_progress" for t in in_progress)


def test_create_oversized_title(client):
    response = client.post('/tickets', json={
        "type": "bug",
        "title": "x" * 201,
        "description": "Title over the 200-char cap.",
    })
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_list_type_filter(client):
    """?type= returns only tickets of that type."""
    marker = f"typetest-{uuid.uuid4().hex[:8]}"
    client.post('/tickets', json={
        "type": "bug", "title": f"{marker}-bug", "description": "a bug",
    })
    client.post('/tickets', json={
        "type": "feature", "title": f"{marker}-feature", "description": "an idea",
    })

    bugs = client.get('/tickets?type=bug&limit=100').get_json()["tickets"]
    titles = [t["title"] for t in bugs]
    assert f"{marker}-bug" in titles
    assert f"{marker}-feature" not in titles
    assert all(t["type"] == "bug" for t in bugs)

    bad = client.get('/tickets?type=bogus')
    assert bad.status_code == 400


def test_list_limit_validation(client):
    """Non-integer and non-positive limits are rejected; large limits are capped."""
    assert client.get('/tickets?limit=abc').status_code == 400
    assert client.get('/tickets?limit=0').status_code == 400
    assert client.get('/tickets?limit=-5').status_code == 400
    # Over-cap limit is clamped, not rejected.
    capped = client.get('/tickets?limit=5000')
    assert capped.status_code == 200
    assert len(capped.get_json()["tickets"]) <= 100


def test_status_update_bumps_updated_at(client):
    created = client.post('/tickets', json={
        "type": "bug", "title": "Bump me", "description": "check updated_at",
    })
    ticket_id = created.get_json()["ticket_id"]
    before = client.get(f'/tickets/{ticket_id}').get_json()

    updated = client.put(f'/tickets/{ticket_id}/status', json={"status": "in_progress"})
    assert updated.status_code == 200
    after = updated.get_json()
    assert after["updated_at"] > before["updated_at"]
    assert after["created_at"] == before["created_at"]


def test_list_bad_status_filter(client):
    response = client.get('/tickets?status=bogus')
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_get_single_and_404(client):
    # Nonexistent but valid UUID -> 404.
    missing = client.get(f'/tickets/{uuid.uuid4()}')
    assert missing.status_code == 404
    assert missing.get_json()["error"] == "Ticket not found"

    # Invalid UUID -> 404, not 500.
    bad = client.get('/tickets/not-a-uuid')
    assert bad.status_code == 404


def test_status_update_and_invalid(client):
    created = client.post('/tickets', json={
        "type": "bug", "title": "Status me", "description": "flip my status",
    })
    ticket_id = created.get_json()["ticket_id"]

    # Valid transition.
    updated = client.put(f'/tickets/{ticket_id}/status', json={"status": "closed"})
    assert updated.status_code == 200
    assert updated.get_json()["status"] == "closed"

    # Invalid status -> 400.
    bad = client.put(f'/tickets/{ticket_id}/status', json={"status": "nope"})
    assert bad.status_code == 400
    assert "error" in bad.get_json()

    # Status update on missing ticket -> 404.
    missing = client.put(f'/tickets/{uuid.uuid4()}/status', json={"status": "open"})
    assert missing.status_code == 404
