from datetime import datetime, timedelta

# from app.logic import checkin, create_election, create_meeting, vote_in_election
from app.logic import create_meeting

'''
def test_checkin_stats_unauthorized(authenticated_client, db_connection):
    """Test that unauthorized users cannot access check-in statistics"""
    # Create a test meeting
    start_time = datetime.now() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Clear any existing session
    with authenticated_client.session_transaction() as sess:
        sess.clear()

    # Try to access stats without authentication
    response = authenticated_client.get("/api/stats/checkins")
    assert response.status_code == 401


def test_checkin_stats_initial(authenticated_client, db_connection):
    """Test that initial check-in stats show zero check-ins"""
    # Create a test meeting
    start_time = datetime.now() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Login as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Get initial stats
    response = authenticated_client.get("/api/stats/checkins")
    assert response.status_code == 200
    data = response.get_json()

    # Verify meeting is in the response with zero check-ins
    assert str(meeting_id) in data
    assert data[str(meeting_id)] == 0


def test_checkin_stats_after_checkin(authenticated_client, db_connection):
    """Test that check-in stats update after a check-in"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Login as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Perform a check-in
    checkin(db_connection, meeting_id, meeting_code)

    # Verify check-in count increased
    response = authenticated_client.get("/api/stats/checkins")
    assert response.status_code == 200
    data = response.get_json()
    assert data[str(meeting_id)] == 1


def test_vote_stats_unauthorized(authenticated_client, db_connection):
    """Test that unauthorized users cannot access vote statistics"""
    # Create a test meeting and election
    start_time = datetime.now() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)
    create_election(db_connection, meeting_id, "Test Election")

    # Clear any existing session
    with authenticated_client.session_transaction() as sess:
        sess.clear()

    # Try to access stats without authentication
    response = authenticated_client.get("/api/stats/votes")
    assert response.status_code == 401


def test_vote_stats_initial(authenticated_client, db_connection):
    """Test that initial vote stats show zero votes"""
    # Create a test meeting and election
    start_time = datetime.now() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)
    election_id = create_election(db_connection, meeting_id, "Test Election")

    # Login as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Get initial stats
    response = authenticated_client.get("/api/stats/votes")
    assert response.status_code == 200
    data = response.get_json()

    # Verify election data is present with zero votes
    assert str(election_id) in data
    election_data = data[str(election_id)]
    assert election_data["name"] == "Test Election"
    assert election_data["total_votes"] == 0
    assert all(v == 0 for v in election_data["votes"].values())


def test_vote_stats_after_vote(authenticated_client, db_connection):
    """Test that vote stats update after a vote is cast"""
    # Create a test meeting and election
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)
    election_id = create_election(db_connection, meeting_id, "Test Election")
    vote_token = checkin(db_connection, meeting_id, meeting_code)
    vote_in_election(db_connection, meeting_id, election_id, vote_token, "A")

    # Login as admin and set up voter session
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Verify vote count increased
    response = authenticated_client.get("/api/stats/votes")
    assert response.status_code == 200
    data = response.get_json()
    election_data = data[str(election_id)]
    assert election_data["total_votes"] == 1
    assert election_data["votes"]["A"] == 1


def test_vote_stats_non_admin_access(authenticated_client, db_connection):
    """Test that non-admin users cannot access vote statistics"""
    # Create a meeting and election
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)
    create_election(db_connection, meeting_id, "Test Election")

    # Log out admin user
    authenticated_client.get("/admin/logout")

    # Try to access vote stats
    response = authenticated_client.get("/api/stats/votes")
    assert response.status_code == 401
    assert response.json["error"] == "Unauthorized"
'''


def test_api_checkin_success(client, db_connection):
    """Test successful check-in via API"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Test successful check-in
    response = client.post(f"/api/checkin/{meeting_id}/{meeting_code}")

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


def test_api_checkin_invalid_meeting_id(client, db_connection):
    """Test API check-in with invalid meeting ID"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    _, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Test with non-existent meeting ID
    response = client.post(f"/api/checkin/999999/{meeting_code}")

    # Verify response
    assert response.status_code == 404
    assert "error" in response.json
    assert "Meeting not found" in response.json["error"]


def test_api_checkin_invalid_meeting_code(client, db_connection):
    """Test API check-in with invalid meeting code"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Test with invalid meeting code
    response = client.post(f"/api/checkin/{meeting_id}/INVALID_CODE")

    # Verify response
    assert response.status_code == 404
    assert "error" in response.json
    assert "Invalid meeting code" in response.json["error"]


def test_api_checkin_meeting_ended(client, db_connection):
    """Test API check-in for a meeting that has already ended"""
    # Create a meeting that has already ended
    start_time = datetime.now() - timedelta(hours=2)
    end_time = datetime.now() - timedelta(hours=1)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Try to check in
    response = client.post(f"/api/checkin/{meeting_id}/{meeting_code}")

    # Verify response
    assert response.status_code == 404  # or 400, depending on your error handling
    assert "error" in response.json
    assert "Meeting is not available" in response.json["error"]


def test_api_checkin_missing_meeting_code(client, db_connection):
    """Test API check-in with missing meeting code"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Test with empty meeting code
    response = client.post(f"/api/checkin/{meeting_id}/")

    # Verify response
    assert response.status_code == 404  # 404 because the URL pattern doesn't match


def test_api_checkin_server_error(client, db_connection, monkeypatch):
    """Test API check-in when a server error occurs"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Mock the checkin function to raise an exception
    def mock_checkin(*args, **kwargs):
        raise Exception("Database error")

    from app import logic

    monkeypatch.setattr(logic, "checkin", mock_checkin)

    # Try to check in
    response = client.post(f"/api/checkin/{meeting_id}/{meeting_code}")

    # Verify response
    assert response.status_code == 500
    assert "error" in response.json
    assert "Database error" in response.json["error"]
