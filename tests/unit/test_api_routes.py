from datetime import datetime, timedelta, timezone

from app.services import checkin, create_meeting


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
    from app.models import Checkin

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

    # 3) Hit the stream
    resp = client.get("/api/meetings/stream")
    assert resp.status_code == 200

    # 4) Pull first chunk
    first = next(resp.response)
    data = json.loads(first.split(b"data: ", 1)[1])
    # should only include meeting 1
    assert isinstance(data, list)
    ids = [m["id"] for m in data]
    assert m1_id in ids and m2_id not in ids
    assert data[0]["checked_in"]
    assert len(data[0]["elections"]) == 0


def test_admin_stream_sse(client, db_connection, monkeypatch, app):
    import json
    import time

    from app.models import Election, ElectionVote

    # seed an admin session
    with client.session_transaction() as sess:
        sess["is_admin"] = True

    now = datetime.now(timezone.utc)
    m_id, _ = create_meeting(
        db_connection, now - timedelta(minutes=1), now + timedelta(hours=1)
    )
    # create an election and some votes
    election = Election(meeting_id=m_id, name="Test")
    db_connection.add(election)
    db_connection.flush()
    # cast votes
    for i, opt in enumerate(["A", "B", "A"]):
        db_connection.add(
            ElectionVote(election_id=election.id, vote=opt, vote_token=f"T{i}")
        )
    db_connection.commit()

    monkeypatch.setattr(time, "sleep", lambda s: None)

    print(f"HERE:  {app.config}")

    resp = client.get("/api/admin/meetings/stream")
    assert resp.status_code == 200
    chunk = next(resp.response)
    print(chunk)
    data = json.loads(chunk.split(b"data: ", 1)[1])
    # data should be a list of meeting summaries
    summary = next(m for m in data if m["id"] == m_id)
    assert summary["checkins"] == 0  # no checkins in this example
    assert summary["elections"][0]["total_votes"] == 3
    assert summary["elections"][0]["votes"]["A"] == 2
    assert summary["elections"][0]["votes"]["B"] == 1
