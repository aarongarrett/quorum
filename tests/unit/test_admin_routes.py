import importlib
from datetime import datetime, timedelta
from io import BytesIO

from flask import url_for

from app.services import create_election, create_meeting
from app.utils import strftime


def decode_qr_png(img_buffer: BytesIO) -> str:
    """Helper function to decode QR code from image buffer."""
    # numpy is imported this way because of the internal mypy error
    numpy = importlib.import_module("numpy")
    import PIL
    import zxingcpp

    img = PIL.Image.open(img_buffer).convert("L")
    img_data = numpy.asarray(img)
    barcode = zxingcpp.read_barcode(img_data)
    return barcode.text


def test_qr_code_generation(authenticated_client, db_connection, app):
    """Test QR code generation for meetings"""
    # Create a test meeting
    start_time = datetime(2025, 5, 4, 11, 00, 0, 0).astimezone(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Test unauthenticated access
    with authenticated_client.session_transaction() as sess:
        sess.clear()
    response = authenticated_client.get(f"/admin/meetings/{meeting_id}/qr.svg")
    assert response.status_code == 401  # Unauthorized

    # Login as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Test valid QR code generation
    response = authenticated_client.get(f"/admin/meetings/{meeting_id}/qr.png")
    with app.test_request_context():
        expected = (
            url_for("public.auto_checkin", meeting_id=meeting_id, _external=True)
            + f"#{meeting_code}"
        )

    assert response.status_code == 200
    assert "image/png" in response.content_type
    assert decode_qr_png(BytesIO(response.data)) == expected

    # Test with non-existent meeting
    response = authenticated_client.get("/admin/meetings/999999/qr.png")
    assert response.status_code == 404


def test_admin_redirects_to_dashboard(authenticated_client):
    """Test admin route redirects to dashboard"""
    # Test basic redirect
    response = authenticated_client.get("/admin/")
    assert response.status_code == 302
    assert response.headers["Location"] == "/admin/dashboard"

    # Test redirect with query parameters
    response = authenticated_client.get("/admin/?test=123")
    assert response.status_code == 302
    assert response.headers["Location"] == "/admin/dashboard"


def test_admin_login_page_loads(client):
    """Test that the admin login page loads correctly"""
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert b"Login" in response.data
    assert b"password" in response.data.lower()


def test_admin_login_invalid_password(client):
    """Test that login fails with an invalid password"""
    response = client.post(
        "/admin/login", data={"password": "wrong_password"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Invalid password" in response.data

    # Verify not logged in
    with client.session_transaction() as sess:
        assert "is_admin" not in sess or not sess["is_admin"]


def test_admin_login_successful(client, app):
    """Test successful admin login"""
    with client:
        # Initial request - not logged in
        response = client.get("/admin/dashboard", follow_redirects=True)
        assert b"Login" in response.data  # Should redirect to login

        # Log in
        response = client.post(
            "/admin/login",
            data={"password": app.config["ADMIN_PASSWORD"]},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Dashboard" in response.data

        # Verify session
        with client.session_transaction() as sess:
            assert sess.get("is_admin") is True

        # Should be able to access protected route
        response = client.get("/admin/dashboard")
        assert response.status_code == 200
        assert b"Dashboard" in response.data

        # Verify session is set
        with client.session_transaction() as sess:
            assert sess.get("is_admin") is True


def test_admin_logout_redirects_to_login(authenticated_client):
    """Test that logout redirects to the login page"""
    # First log in
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Test logout
    response = authenticated_client.post("/admin/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data


def test_admin_logout_clears_session(authenticated_client):
    """Test that logout clears the admin session"""
    # First log in
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Log out
    authenticated_client.post("/admin/logout")

    # Verify session is cleared
    with authenticated_client.session_transaction() as sess:
        assert "is_admin" not in sess


def test_protected_routes_after_logout(authenticated_client):
    """Test that protected routes redirect to login after logout"""
    # First log in
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Log out
    authenticated_client.post("/admin/logout")

    # Try to access a protected route
    response = authenticated_client.get("/admin/dashboard")

    # Should redirect to login page
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]

    # Follow the redirect
    response = authenticated_client.get("/admin/dashboard", follow_redirects=True)
    assert b"Login" in response.data


def test_admin_dashboard_unauthenticated(authenticated_client):
    """Test that unauthenticated users cannot access the dashboard"""
    # Clear any existing session
    with authenticated_client.session_transaction() as sess:
        sess.clear()

    # Try to access dashboard
    response = authenticated_client.get("/admin/dashboard")

    # Should redirect to login
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_admin_dashboard_displays_meetings_and_elections(
    authenticated_client, db_connection, app
):
    """Test that the dashboard displays meetings and their elections"""
    # Create test data
    start_time = datetime(2025, 5, 4, 11, 00, 0, 0).astimezone(app.config["TZ"])
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)
    create_election(db_connection, meeting_id, "Test Election 1")
    create_election(db_connection, meeting_id, "Test Election 2")

    # Log in as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Access dashboard
    response = authenticated_client.get("/admin/dashboard")
    assert response.status_code == 200

    # Verify meeting date and time are displayed in the correct format
    date_str = strftime(start_time, "%B %d, %Y").encode()
    start_time_str = strftime(start_time, "%I:%M %p").encode()
    end_time_str = strftime(end_time, "%I:%M %p").encode()

    assert date_str in response.data
    assert start_time_str in response.data
    assert end_time_str in response.data

    # Verify elections are displayed
    assert b"Test Election 1" in response.data
    assert b"Test Election 2" in response.data


def test_admin_dashboard_no_meetings(authenticated_client, db_connection):
    """Test dashboard when there are no meetings"""
    # Log in as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Access dashboard
    response = authenticated_client.get("/admin/dashboard")
    assert response.status_code == 200

    # Verify empty state message
    assert b"No meetings found" in response.data


def test_admin_dashboard_multiple_meetings(authenticated_client, db_connection, app):
    """Test dashboard with multiple meetings"""
    # Create multiple test meetings
    now = datetime(2025, 5, 4, 11, 00, 0, 0).astimezone(app.config["TZ"])
    meeting1_start_time = now + timedelta(hours=1)
    meeting1_end_time = now + timedelta(hours=2)
    meeting2_start_time = now + timedelta(days=1)
    meeting2_end_time = now + timedelta(days=1, hours=2)
    meeting1_id, _ = create_meeting(
        db_connection, meeting1_start_time, meeting1_end_time
    )
    meeting2_id, _ = create_meeting(
        db_connection, meeting2_start_time, meeting2_end_time
    )

    # Add elections to second meeting
    create_election(db_connection, meeting2_id, "Future Election 1")
    create_election(db_connection, meeting2_id, "Future Election 2")

    # Log in as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Access dashboard
    response = authenticated_client.get("/admin/dashboard")
    assert response.status_code == 200

    # Verify both meetings are displayed
    # Verify meeting date and time are displayed in the correct format
    for start_time, end_time in [
        (meeting1_start_time, meeting1_end_time),
        (meeting2_start_time, meeting2_end_time),
    ]:
        date_str = strftime(start_time, "%B %d, %Y").encode()
        start_time_str = strftime(start_time, "%I:%M %p").encode()
        end_time_str = strftime(end_time, "%I:%M %p").encode()

        assert date_str in response.data
        assert start_time_str in response.data
        assert end_time_str in response.data

    # Verify elections are displayed for the second meeting
    assert b"Future Election 1" in response.data
    assert b"Future Election 2" in response.data


def test_meeting_create_form_unauthenticated(authenticated_client):
    """Test that unauthenticated users cannot access the meeting creation form"""
    with authenticated_client.session_transaction() as sess:
        sess.clear()

    response = authenticated_client.get("/admin/meetings")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_meeting_create_form_authenticated(authenticated_client):
    """Test that authenticated admins can access the meeting creation form"""
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    response = authenticated_client.get("/admin/meetings")
    assert response.status_code == 200
    assert b"Create Meeting" in response.data
    assert b"Meeting Date" in response.data
    assert b"Meeting Time" in response.data


def test_meeting_creation_success(authenticated_client, app):
    """Test creating a meeting with valid data"""
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    response = authenticated_client.post(
        "/admin/meetings",
        data={
            "date": (datetime.now(app.config["TZ"]) + timedelta(days=7)).strftime(
                "%Y-%m-%d"
            ),
            "time": "14:00",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Meeting created" in response.data


def test_meeting_creation_invalid_data(authenticated_client):
    """Test creating a meeting with invalid data"""
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Test with invalid date format
    response = authenticated_client.post(
        "/admin/meetings",
        data={"date": "not-a-date", "time": "also-not-a-time"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid date/time format" in response.data


def test_meeting_deletion(authenticated_client, db_connection, app):
    """Test deleting an existing meeting"""
    # Create a meeting to delete
    start_time = datetime(2025, 5, 4, 11, 00, 0, 0).astimezone(app.config["TZ"])
    end_time = start_time + timedelta(hours=1)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Delete the meeting
    response = authenticated_client.delete(
        f"/admin/meetings/{meeting_id}", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Meeting deleted" in response.data


def test_meeting_deletion_via_post(authenticated_client, db_connection, app):
    """Test deleting an existing meeting"""
    # Create a meeting to delete
    start_time = datetime(2025, 5, 4, 11, 00, 0, 0).astimezone(app.config["TZ"])
    end_time = start_time + timedelta(hours=1)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Delete the meeting
    response = authenticated_client.post(
        f"/admin/meetings/{meeting_id}",
        data={"_method": "DELETE"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Meeting deleted" in response.data


def test_meeting_deletion_via_post_without_override(
    authenticated_client, db_connection, app
):
    """Test deleting an existing meeting"""
    # Create a meeting to delete
    start_time = datetime(2025, 5, 4, 11, 00, 0, 0).astimezone(app.config["TZ"])
    end_time = start_time + timedelta(hours=1)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Delete the meeting
    response = authenticated_client.post(
        f"/admin/meetings/{meeting_id}",
        follow_redirects=True,
    )
    assert response.status_code == 405


def test_election_create_form_unauthenticated(authenticated_client, db_connection, app):
    """Test that unauthenticated users cannot access the election creation form"""
    # Create a test meeting
    start_time = datetime.now(app.config["TZ"]) + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Clear session to simulate unauthenticated user
    with authenticated_client.session_transaction() as sess:
        sess.clear()

    # Try to access the form
    response = authenticated_client.get(f"/admin/meetings/{meeting_id}/elections")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_election_create_form_authenticated(authenticated_client, db_connection, app):
    """Test that authenticated admins can access the election creation form"""
    # Create a test meeting
    start_time = datetime.now(app.config["TZ"]) + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Login as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Access the form
    response = authenticated_client.get(f"/admin/meetings/{meeting_id}/elections")
    assert response.status_code == 200
    assert b"Create Election" in response.data
    assert b"Name" in response.data


def test_election_creation_success(authenticated_client, db_connection, app):
    """Test creating an election with valid data"""
    # Create a test meeting
    start_time = datetime.now(app.config["TZ"]) + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Login as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Create an election
    response = authenticated_client.post(
        f"/admin/meetings/{meeting_id}/elections",
        data={"name": "Test Election"},
        follow_redirects=True,
    )

    # Verify response
    assert response.status_code == 200
    assert b"Election created" in response.data


def test_election_creation_invalid_data(authenticated_client, db_connection, app):
    """Test creating an election with invalid data"""
    # Create a test meeting
    start_time = datetime.now(app.config["TZ"]) + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Login as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Test with empty name
    response = authenticated_client.post(
        f"/admin/meetings/{meeting_id}/elections",
        data={"name": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Election name cannot be empty" in response.data


def test_election_deletion(authenticated_client, db_connection, app):
    """Test deleting an existing election"""
    # Create a test meeting and election
    start_time = datetime.now(app.config["TZ"]) + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Create an election
    election_id = create_election(db_connection, meeting_id, "Test Election")

    # Login as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Delete the election
    response = authenticated_client.delete(
        f"/admin/meetings/{meeting_id}/elections/{election_id}",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Election deleted" in response.data


def test_election_deletion_via_post(authenticated_client, db_connection, app):
    """Test deleting an existing election"""
    # Create a test meeting and election
    start_time = datetime.now(app.config["TZ"]) + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Create an election
    election_id = create_election(db_connection, meeting_id, "Test Election")

    # Login as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Delete the election
    response = authenticated_client.post(
        f"/admin/meetings/{meeting_id}/elections/{election_id}",
        data={"_method": "DELETE"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Election deleted" in response.data


def test_election_deletion_via_post_without_override(
    authenticated_client, db_connection, app
):
    """Test deleting an existing election"""
    # Create a test meeting and election
    start_time = datetime.now(app.config["TZ"]) + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    meeting_id, _ = create_meeting(db_connection, start_time, end_time)

    # Create an election
    election_id = create_election(db_connection, meeting_id, "Test Election")

    # Login as admin
    with authenticated_client.session_transaction() as sess:
        sess["is_admin"] = True

    # Delete the election
    response = authenticated_client.post(
        f"/admin/meetings/{meeting_id}/elections/{election_id}", follow_redirects=True
    )
    assert response.status_code == 405
