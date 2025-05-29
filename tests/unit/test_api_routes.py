from datetime import datetime, timedelta

from app.services import create_meeting


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
