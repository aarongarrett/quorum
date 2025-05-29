from datetime import datetime, timedelta

import pytest

from app import create_app
from app.models import Election, Meeting
from tests.e2e.pages.admin_login_page import AdminLoginPage
from tests.e2e.pages.user_pages import UserHomePage

MEETING_CODE = "TEST1234"
ELECTION_NAME = "Test Election"


@pytest.fixture
def admin_user():
    """Fixture to create an admin user for testing"""
    app = create_app("testing")
    with app.app_context():
        yield app.config["ADMIN_PASSWORD"]


@pytest.fixture
def test_meeting(app, db_connection):
    """Fixture to create a test meeting with an election"""
    with app.app_context():
        # Create a test meeting
        start = datetime.now(app.config["TZ"])
        end = start + timedelta(hours=app.config["MEETING_DURATION_HOURS"])
        meeting = Meeting(start_time=start, end_time=end, meeting_code=MEETING_CODE)
        db_connection.add(meeting)
        db_connection.flush()  # Get the meeting ID

        # Create a test election
        election = Election(meeting_id=meeting.id, name=ELECTION_NAME)
        db_connection.add(election)
        db_connection.commit()

        yield meeting.id, election.id

        # Cleanup
        db_connection.delete(election)
        db_connection.delete(meeting)
        db_connection.commit()


def test_admin_login_and_dashboard(browser, base_url, admin_user):
    """Test admin login and dashboard access"""
    login = AdminLoginPage(browser, base_url + "/admin")
    login.visit("/login")
    login.login(admin_user)
    assert browser.current_url.endswith("/admin/dashboard")
    assert "Create Meeting" in browser.page_source


def test_view_available_meetings(browser, base_url, test_meeting):
    """Test that users can view available meetings"""
    meeting_id, _ = test_meeting
    user_home = UserHomePage(browser, base_url)
    user_home.visit("/")

    # Verify meeting is listed
    print(browser.page_source)
    meeting_card = user_home.get_meeting_card_by_id(meeting_id)
    assert meeting_card.is_displayed(), "Meeting card should be visible"
    assert False


def test_checkin_with_valid_code(browser, base_url, test_meeting):
    """Test checking in with a valid meeting code"""
    meeting_id, _ = test_meeting
    print(f"{meeting_id=}")
    user_home = UserHomePage(browser, base_url)
    user_home.visit(f"/checkin/{meeting_id}")

    # Enter meeting code and submit
    print(f"{MEETING_CODE=}")
    user_home.enter_meeting_code(MEETING_CODE)
    user_home.click_check_in()

    # Verify success message and redirection
    assert "checked in successfully" in user_home.get_success_message().lower()
    assert "home" in browser.current_url


def test_checkin_with_invalid_code(browser, base_url, test_meeting):
    """Test checking in with an invalid meeting code"""
    meeting_id, _ = test_meeting
    user_home = UserHomePage(browser, base_url)
    user_home.visit(f"/meeting/{meeting_id}/checkin")

    # Enter invalid meeting code and submit
    user_home.enter_meeting_code("INVALID123")
    user_home.click_check_in()

    # Verify error message
    assert "invalid meeting code" in user_home.get_error_message().lower()


def test_vote_in_election(browser, base_url, test_meeting):
    """Test the complete voting flow"""
    meeting_id, election_id = test_meeting
    user_home = UserHomePage(browser, base_url)

    # First, check in to the meeting
    user_home.visit(f"/meeting/{meeting_id}/checkin")
    user_home.enter_meeting_code(MEETING_CODE)
    user_home.click_check_in()

    # Select a vote option and submit
    user_home.select_vote_option(election_id, "A")
    user_home.submit_vote()

    # Verify vote was recorded
    assert user_home.is_vote_confirmed(), "Vote confirmation should be displayed"

    # Verify cookie was set
    cookies = browser.get_cookies()
    vote_cookie = next(
        (c for c in cookies if c["name"] == f"meeting_{meeting_id}"), None
    )
    assert vote_cookie is not None, "Vote cookie should be set"


# Note: The test fixtures and test data are defined at the top of the file
