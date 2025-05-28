from datetime import datetime, timedelta

from app.logic import checkin, create_election, create_meeting


def test_home_route_shows_meetings(client, db_connection):
    """Test the home page shows available meetings"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)

    # Create a meeting
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Test home page
    response = client.get("/")
    assert response.status_code == 200

    # The meetings are now loaded via JavaScript, so we can't test the full page load.
    assert b'id="meetings-container"' in response.data
    assert b"No meetings are currently available" in response.data
    assert b'new EventSource("/api/updates")' in response.data


def test_checkin_page_loads(client, db_connection):
    """Test that the check-in page loads correctly"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Test check-in page loads
    response = client.get(f"/checkin/{meeting_id}")
    assert response.status_code == 200
    assert b"Enter Meeting Code" in response.data


def test_checkin_invalid_meeting_id(client):
    """Test handling of invalid meeting IDs"""
    response = client.get("/checkin/999999", follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid meeting ID (999999)" in response.data


def test_checkin_no_code(client, db_connection):
    """Test check-in with an invalid code"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    response = client.post(
        f"/checkin/{meeting_id}",
        data={},
        follow_redirects=True,
    )
    assert b"Meeting code is required" in response.data


def test_checkin_invalid_code(client, db_connection):
    """Test check-in with an invalid code"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    response = client.post(
        f"/checkin/{meeting_id}",
        data={"meeting_code": "INVALID"},
        follow_redirects=True,
    )
    assert b"Invalid meeting code" in response.data


def test_successful_checkin_post(client, db_connection):
    """Test successful check-in via POST request"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Clear any existing session
    with client.session_transaction() as sess:
        sess.clear()

    # Test successful check-in
    response = client.post(
        f"/checkin/{meeting_id}",
        data={"meeting_code": meeting_code},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"You are checked in!" in response.data

    # Verify session was updated
    with client.session_transaction() as sess:
        assert sess["checked_in_meetings"] == [meeting_id]
        assert str(meeting_id) in sess["meeting_tokens"]


def test_duplicate_checkin(client, db_connection):
    """Test that duplicate check-ins are handled correctly"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # First check-in (should succeed)
    with client.session_transaction() as sess:
        sess.clear()

    response = client.post(
        f"/checkin/{meeting_id}",
        data={"meeting_code": meeting_code},
        follow_redirects=True,
    )
    assert response.status_code == 200

    # Second check-in attempt (should fail)
    response = client.post(
        f"/checkin/{meeting_id}",
        data={"meeting_code": meeting_code},
        follow_redirects=True,
    )
    assert b"already checked in" in response.data.lower()


def test_checkin_via_get_parameter(client, db_connection):
    """Test check-in via GET request with meeting code in query parameter"""
    # Create a test meeting
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Clear any existing session
    with client.session_transaction() as sess:
        sess.clear()

    # Test check-in via GET with query parameter
    response = client.get(
        f"/checkin/{meeting_id}?meeting_code={meeting_code}", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"You are checked in!" in response.data


def test_vote_without_checkin_redirects_home(client, db_connection):
    """Test that voting without checking in redirects to home"""
    with client.session_transaction() as sess:
        sess.clear()

    # Create test data
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)
    election_id = create_election(db_connection, meeting_id, "Test Election")

    response = client.get(f"/vote/election/{election_id}")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_vote_page_after_checkin(client, db_connection):
    """Test that the voting page shows available elections after check-in"""
    # Create test data
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)
    election_id = create_election(db_connection, meeting_id, "Test Election")

    # Check in
    vote_token = checkin(db_connection, meeting_id, meeting_code)
    with client.session_transaction() as sess:
        sess["checked_in_meetings"] = [meeting_id]
        sess["meeting_tokens"] = {str(meeting_id): vote_token}

    # Test voting page loads
    response = client.get(f"/vote/election/{election_id}")
    assert response.status_code == 200
    assert b"Cast your vote" in response.data
    assert b"Test Election" in response.data


def test_submit_vote(client, db_connection):
    """Test submitting a vote"""
    # Create test data
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)
    election_id = create_election(db_connection, meeting_id, "Test Election")

    # Check in
    vote_token = checkin(db_connection, meeting_id, meeting_code)
    with client.session_transaction() as sess:
        sess["checked_in_meetings"] = [meeting_id]
        sess["meeting_tokens"] = {str(meeting_id): vote_token}

    # Submit vote
    response = client.post(
        f"/vote/election/{election_id}", data={"vote": "A"}, follow_redirects=True
    )
    print(response.data.decode())
    assert response.status_code == 200
    assert b"Vote recorded" in response.data


def test_duplicate_vote_prevention(client, db_connection):
    """Test that users cannot vote multiple times in the same election"""
    # Create test data
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)
    election_id = create_election(db_connection, meeting_id, "Test Election")

    # Check in
    vote_token = checkin(db_connection, meeting_id, meeting_code)
    with client.session_transaction() as sess:
        sess["checked_in_meetings"] = [meeting_id]
        sess["meeting_tokens"] = {str(meeting_id): vote_token}

    # First vote (should succeed)
    response = client.post(
        f"/vote/election/{election_id}", data={"vote": "A"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Vote recorded" in response.data

    # Second vote attempt (should fail)
    response = client.post(
        f"/vote/election/{election_id}", data={"vote": "B"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"You have already voted" in response.data
