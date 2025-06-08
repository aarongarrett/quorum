import json
import time
from datetime import datetime, timedelta, timezone

from app.models import Checkin, Poll, PollVote
from app.services import checkin, create_meeting


def test_api_meetings_get_checked_in_status(client, db_connection, app):
    """Test GET /api/meetings reflects check-in status based on session"""
    # 1. Create a test meeting and check-in
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    poll = Poll(meeting_id=meeting_id, name="Test Poll")
    db_connection.add(poll)
    db_connection.flush()

    # Perform check-in to obtain token
    token = checkin(db_connection, meeting_id, meeting_code)

    # Manually store the token in session to simulate a user with a valid token
    with client.session_transaction() as sess:
        sess["meeting_tokens"] = {meeting_id: token}

    # 2. Call GET /api/meetings
    response = client.get("/api/meetings")
    assert response.status_code == 200
    data = response.get_json()

    # 3. Verify the meeting is present and marked as checked_in
    matching = [m for m in data if m["id"] == meeting_id]
    assert matching, "Meeting should be returned"
    assert matching[0]["checked_in"] is True
    assert isinstance(matching[0]["polls"], list)
    assert len(matching[0]["polls"]) == 1
    assert matching[0]["polls"][0]["id"] == poll.id


def test_api_meetings_post_with_token_map(client, db_connection, app):
    """Test POST /api/meetings accepts token map and returns polls if valid"""
    # 1. Create meeting and check-in
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    poll = Poll(meeting_id=meeting_id, name="Test Poll")
    db_connection.add(poll)
    db_connection.flush()

    # Perform check-in to obtain token
    token = checkin(db_connection, meeting_id, meeting_code)

    # 2. POST to /api/meetings with the token
    response = client.post("/api/meetings", json={str(meeting_id): token})
    assert response.status_code == 200
    data = response.get_json()

    # 3. Verify returned meeting reflects the token-based access
    matching = [m for m in data if m["id"] == meeting_id]
    assert matching, "Meeting should be returned"
    assert matching[0]["checked_in"] is True
    assert isinstance(matching[0]["polls"], list)
    assert len(matching[0]["polls"]) == 1
    assert matching[0]["polls"][0]["id"] == poll.id


def test_api_meetings_post_with_invalid_token_map(client, db_connection, app):
    """Test POST /api/meetings accepts token map and returns polls if valid"""
    # 1. Create meeting and check-in
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Perform check-in to obtain token
    token = checkin(db_connection, meeting_id, meeting_code)

    # 2. POST to /api/meetings with the invalid token map
    response = client.post("/api/meetings", json={str("Invalid ID"): token})
    assert response.status_code == 400
    data = response.get_json()

    # 3. Verify returned meeting reflects the token-based access
    assert "error" in data
    assert data["error"] == "Invalid token map"


def test_api_meetings_wrong_token_for_meeting(client, db_connection, app):
    """Token issued for Meeting A should not allow access to Meeting B"""
    # Create two meetings
    now = datetime.now(app.config["TZ"])
    m1_id, m1_code = create_meeting(db_connection, now, now + timedelta(hours=1))
    m2_id, m2_code = create_meeting(db_connection, now, now + timedelta(hours=1))

    # Check in to Meeting A
    token = checkin(db_connection, m1_id, m1_code)

    # POST to /api/meetings with token for wrong meeting
    response = client.post("/api/meetings", json={str(m2_id): token})
    assert response.status_code == 200
    data = response.get_json()

    # Meeting B should be listed, but marked as not checked in
    match = [m for m in data if m["id"] == m2_id]
    assert match, "Meeting B should be returned"
    assert match[0]["checked_in"] is False


def test_api_meetings_invalid_token(client, db_connection, app):
    """Invalid token should not grant access"""
    # Create a meeting
    now = datetime.now(app.config["TZ"])
    meeting_id, meeting_code = create_meeting(
        db_connection, now, now + timedelta(hours=1)
    )

    # Use a made-up token
    fake_token = "INVALID8"

    # POST with invalid token
    response = client.post("/api/meetings", json={str(meeting_id): fake_token})
    assert response.status_code == 200
    data = response.get_json()

    match = [m for m in data if m["id"] == meeting_id]
    assert match, "Meeting should be returned"
    assert match[0]["checked_in"] is False


def test_api_meetings_no_polls(client, db_connection, app):
    """Meeting with no polls should still return empty polls list"""
    # Create meeting and check in
    now = datetime.now(app.config["TZ"])
    meeting_id, meeting_code = create_meeting(
        db_connection, now, now + timedelta(hours=1)
    )

    token = checkin(db_connection, meeting_id, meeting_code)

    # POST with valid token
    response = client.post("/api/meetings", json={str(meeting_id): token})
    assert response.status_code == 200
    data = response.get_json()

    match = [m for m in data if m["id"] == meeting_id]
    assert match, "Meeting should be returned"
    assert match[0]["checked_in"] is True
    assert isinstance(match[0]["polls"], list)
    assert len(match[0]["polls"]) == 0


def test_api_checkin_success(client, db_connection, app):
    """Test successful check-in via API"""
    # Create a test meeting
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Test successful check-in
    response = client.post(
        f"/api/meetings/{meeting_id}/checkins", json={"meeting_code": meeting_code}
    )

    # Verify response
    assert response.status_code == 200
    assert "token" in response.json
    assert isinstance(response.json["token"], str)
    assert len(response.json["token"]) > 0

    # Verify the check-in was recorded in the database
    checkin = (
        db_connection.query(Checkin)
        .filter(
            Checkin.meeting_id == meeting_id,
            Checkin.vote_token == response.json["token"],
        )
        .first()
    )
    assert checkin is not None


def test_api_checkin_invalid_meeting_id(client, db_connection, app):
    """Test API check-in with invalid meeting ID"""
    # Create a test meeting
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    _, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Test with non-existent meeting ID
    response = client.post(
        "/api/meetings/999999/checkins", json={"meeting_code": meeting_code}
    )

    # Verify response
    assert response.status_code == 404
    assert "error" in response.json
    assert "Meeting not found" in response.json["error"]


def test_api_checkin_invalid_meeting_code(client, db_connection, app):
    """Test API check-in with invalid meeting code"""
    # Create a test meeting
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Test with invalid meeting code
    response = client.post(
        f"/api/meetings/{meeting_id}/checkins", json={"meeting_code": "INVALID_CODE"}
    )

    # Verify response
    assert response.status_code == 404
    assert "error" in response.json
    assert "Invalid meeting code" in response.json["error"]


def test_api_checkin_meeting_ended(client, db_connection, app):
    """Test API check-in for a meeting that has already ended"""
    # Create a meeting that has already ended
    start_time = datetime.now(app.config["TZ"]) - timedelta(hours=2)
    end_time = datetime.now(app.config["TZ"]) - timedelta(hours=1)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Try to check in
    response = client.post(
        f"/api/meetings/{meeting_id}/checkins", json={"meeting_code": meeting_code}
    )

    # Verify response
    assert response.status_code == 404  # or 400, depending on your error handling
    assert "error" in response.json
    assert "Meeting is not available" in response.json["error"]


def test_api_checkin_missing_meeting_code(client, db_connection, app):
    """Test API check-in with missing meeting code"""
    # Create a test meeting
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Test with empty meeting code
    response = client.post(
        f"/api/meetings/{meeting_id}/checkins", json={"meeting_code": ""}
    )

    # Verify response
    assert response.status_code == 400


def test_api_checkin_server_error(client, db_connection, monkeypatch, app):
    """Test API check-in when a server error occurs"""
    # Create a test meeting
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Mock the checkin function to raise an exception
    def mock_checkin(*args, **kwargs):
        raise Exception("Database error")

    import app.blueprints.api.routes

    monkeypatch.setattr(app.blueprints.api.routes, "checkin", mock_checkin)

    # Try to check in
    response = client.post(
        f"/api/meetings/{meeting_id}/checkins", json={"meeting_code": meeting_code}
    )

    # Verify response
    assert response.status_code == 500
    assert "error" in response.json
    assert "Database error" in response.json["error"]


def test_api_vote_success(client, db_connection, app):
    """Test successful vote submission via API"""
    # Create a test meeting and poll
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Create an poll
    poll = Poll(meeting_id=meeting_id, name="Test Poll")
    db_connection.add(poll)
    db_connection.flush()

    # Create a check-in to get a valid token
    token = checkin(db_connection, meeting_id, meeting_code)

    response = client.post(
        f"/api/meetings/{meeting_id}/polls/{poll.id}/votes",
        json={"token": token, "vote": "E"},
    )

    assert response.status_code == 200
    assert response.json == {"success": True}


def test_api_vote_invalid_token(client, db_connection, app):
    """Test vote submission with invalid token"""
    # Create a test meeting and poll
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    poll = Poll(meeting_id=meeting_id, name="Test Poll")
    db_connection.add(poll)
    db_connection.flush()

    response = client.post(
        f"/api/meetings/{meeting_id}/polls/{poll.id}/votes",
        json={"token": "invalid-token", "vote": "C"},
    )

    assert response.status_code == 404
    assert "error" in response.json


def test_api_vote_missing_fields(client):
    """Test vote submission with missing required fields"""
    response = client.post(
        "/api/meetings/1/polls/1/votes",
        json={"token": "test-token"},  # Missing vote
    )
    assert response.status_code == 400

    response = client.post(
        "/api/meetings/1/polls/1/votes", json={"vote": "A"}  # Missing token
    )
    assert response.status_code == 400


def test_api_login_success(client, app):
    """Test successful login via API"""
    with client.session_transaction() as sess:
        sess["is_admin"] = False

    response = client.post(
        "/api/login", json={"password": app.config["ADMIN_PASSWORD"]}
    )

    assert response.status_code == 200
    assert "success" in response.json
    with client.session_transaction() as sess:
        assert sess["is_admin"] is True


def test_api_login_no_password(client, app):
    """Test successful login via API"""
    with client.session_transaction() as sess:
        sess["is_admin"] = False

    response = client.post("/api/login", json={"pwd": app.config["ADMIN_PASSWORD"]})

    assert response.status_code == 400
    assert "error" in response.json
    assert response.json["error"] == "Password is required"
    with client.session_transaction() as sess:
        assert sess["is_admin"] is False


def test_api_login_wrong_password(client, app):
    """Test successful login via API"""
    with client.session_transaction() as sess:
        sess["is_admin"] = False

    response = client.post("/api/login", json={"password": "INVALID_PWD"})

    assert response.status_code == 400
    assert "error" in response.json
    assert response.json["error"] == "Invalid password"
    with client.session_transaction() as sess:
        assert sess["is_admin"] is False


def test_api_create_meeting_success(client, app):
    """Test successful meeting creation via API"""
    with client.session_transaction() as sess:
        sess["is_admin"] = True

    start_time = (datetime.now(app.config["TZ"]) + timedelta(hours=1)).isoformat()
    end_time = (datetime.now(app.config["TZ"]) + timedelta(hours=2)).isoformat()

    response = client.post(
        "/api/admin/meetings", json={"start_time": start_time, "end_time": end_time}
    )

    assert response.status_code == 201
    assert "meeting_id" in response.json
    assert "meeting_code" in response.json
    assert isinstance(response.json["meeting_id"], int)
    assert len(response.json["meeting_code"]) > 0


def test_api_create_meeting_unauthorized(client):
    """Test meeting creation without admin privileges"""
    response = client.post(
        "/api/admin/meetings",
        json={"start_time": "2023-01-01T10:00:00", "end_time": "2023-01-01T12:00:00"},
    )
    assert response.status_code == 403
    assert "error" in response.json
    assert "Unauthorized" in response.json["error"]


def test_api_create_meeting_missing_times(client):
    """Test meeting creation with missing required fields"""
    with client.session_transaction() as sess:
        sess["is_admin"] = True

    # Missing start_time
    response = client.post(
        "/api/admin/meetings", json={"end_time": "2023-01-01T12:00:00"}
    )
    assert response.status_code == 400

    # Missing end_time
    response = client.post(
        "/api/admin/meetings", json={"start_time": "2023-01-01T10:00:00"}
    )
    assert response.status_code == 400


def test_api_create_poll_success(client, db_connection, app):
    """Test successful poll creation via API"""
    # Create a test meeting
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    with client.session_transaction() as sess:
        sess["is_admin"] = True

    response = client.post(
        f"/api/admin/meetings/{meeting_id}/polls", json={"name": "Test Poll"}
    )

    assert response.status_code == 201
    assert "poll_id" in response.json
    assert isinstance(response.json["poll_id"], int)


def test_api_create_poll_unauthorized(client, db_connection, app):
    """Test poll creation without admin privileges"""
    # Create a test meeting
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)
    response = client.post(
        f"/api/admin/meetings/{meeting_id}/polls",
        json={"name": "Test Poll"},
    )
    assert response.status_code == 403
    assert "error" in response.json
    assert "Unauthorized" in response.json["error"]


def test_api_create_poll_missing_name(client, db_connection, app):
    """Test successful poll creation via API"""
    # Create a test meeting
    start_time = datetime.now(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    with client.session_transaction() as sess:
        sess["is_admin"] = True

    response = client.post(f"/api/admin/meetings/{meeting_id}/polls", json={"name": ""})

    assert response.status_code == 400
    assert "error" in response.json
    assert "Name is required and must not be empty" in response.json["error"]


def test_api_create_poll_invalid_meeting(client):
    """Test poll creation for non-existent meeting"""
    with client.session_transaction() as sess:
        sess["is_admin"] = True

    response = client.post(
        "/api/admin/meetings/999999/polls", json={"name": "Test Poll"}
    )

    assert response.status_code == 500


def test_user_stream_sse(client, db_connection, monkeypatch):
    import json
    import time

    tz = timezone.utc
    now = datetime.now(tz)
    m1_id, m1_code = create_meeting(
        db_connection, now - timedelta(minutes=1), now + timedelta(hours=1)
    )
    m2_id, m2_code = create_meeting(
        db_connection, now - timedelta(hours=3), now - timedelta(hours=2)
    )

    chk_token = checkin(db_connection, m1_id, m1_code)
    client.set_cookie(f"meeting_{m1_id}", chk_token)

    monkeypatch.setattr(time, "sleep", lambda s: None)
    from app.blueprints.api import routes

    monkeypatch.setattr(
        routes,
        "sessionmaker",
        lambda bind=None, **kw: (lambda *args, **kwargs: db_connection),
    )

    with client.get("/api/meetings/stream") as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

        chunk = next(resp.response)
        data = json.loads(chunk.split(b"data: ", 1)[1])

        # should only include meeting 1
        assert isinstance(data, list)
        ids = [m["id"] for m in data]
        assert m1_id in ids and m2_id not in ids
        assert data[0]["checked_in"]
        assert len(data[0]["polls"]) == 0


def test_admin_stream_sse(client, db_connection, monkeypatch, app):
    # seed an admin session
    with client.session_transaction() as sess:
        sess["is_admin"] = True

    now = datetime.now(timezone.utc)
    m_id, _ = create_meeting(
        db_connection, now - timedelta(minutes=1), now + timedelta(hours=1)
    )
    # create an poll and some votes
    poll = Poll(meeting_id=m_id, name="Test")
    db_connection.add(poll)
    db_connection.flush()
    # cast votes
    for i, opt in enumerate(["A", "B", "A"]):
        db_connection.add(PollVote(poll_id=poll.id, vote=opt, vote_token=f"T{i}"))
    db_connection.commit()

    monkeypatch.setattr(time, "sleep", lambda s: None)
    from app.blueprints.api import routes

    monkeypatch.setattr(
        routes,
        "sessionmaker",
        lambda bind=None, **kw: (lambda *args, **kwargs: db_connection),
    )

    with client.get("/api/admin/meetings/stream") as resp:
        assert resp.status_code == 200
        chunk = next(resp.response)
        data = json.loads(chunk.split(b"data: ", 1)[1])
        # data should be a list of meeting summaries
        summary = next(m for m in data if m["id"] == m_id)
        assert summary["checkins"] == 0  # no checkins in this example
        assert summary["polls"][0]["total_votes"] == 3
        assert summary["polls"][0]["votes"]["A"] == 2
        assert summary["polls"][0]["votes"]["B"] == 1
