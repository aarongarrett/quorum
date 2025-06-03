from urllib.parse import urlsplit

from tests.e2e.pages.user_pages import UserHomePage


def test_view_available_meetings(user_meeting, browser, base_url):
    """Test that users can view available meetings"""
    meeting_id = user_meeting["meeting_id"]
    user_home = UserHomePage(browser, base_url)
    user_home.visit("/")

    # Verify meeting is listed
    meeting_card = user_home.get_meeting_card_by_id(meeting_id)
    assert meeting_card.is_displayed(), "Meeting card should be visible"


def test_checkin_with_valid_code(user_meeting, browser, base_url):
    """Test checking in with a valid meeting code"""
    meeting_id = user_meeting["meeting_id"]
    user_home = UserHomePage(browser, base_url)
    user_home.visit("/")

    meeting_card = user_home.get_meeting_card_by_id(meeting_id)
    assert meeting_card.is_displayed(), "Meeting card should be visible"
    checkin_url = user_home.get_checkin_url(meeting_id)
    assert checkin_url is not None, "Checkin URL should be visible"
    browser.get(checkin_url)

    # Enter meeting code and submit
    user_home.enter_meeting_code(user_meeting["meeting_code"])
    user_home.click_check_in()
    # Verify cookie was set
    cookies = browser.get_cookies()
    checkin_cookie = next(
        (c for c in cookies if c["name"] == f"meeting_{meeting_id}"), None
    )
    assert checkin_cookie is not None, "Checkin cookie should be set"

    # Verify success message and redirection
    assert "you are checked in!" in user_home.get_success_message().lower()
    url_parts = urlsplit(browser.current_url)
    assert url_parts.path == "/"


def test_checkin_with_invalid_code(user_meeting, browser, base_url):
    """Test checking in with an invalid meeting code"""
    meeting_id = user_meeting["meeting_id"]
    user_home = UserHomePage(browser, base_url)
    user_home.visit("/")
    meeting_card = user_home.get_meeting_card_by_id(meeting_id)
    assert meeting_card.is_displayed(), "Meeting card should be visible"
    checkin_url = user_home.get_checkin_url(meeting_id)
    assert checkin_url is not None, "Checkin URL should be visible"
    browser.get(checkin_url)

    # Enter invalid meeting code and submit
    user_home.enter_meeting_code("INVALID123")
    user_home.click_check_in()
    cookies = browser.get_cookies()
    checkin_cookie = next(
        (c for c in cookies if c["name"] == f"meeting_{meeting_id}"), None
    )
    assert checkin_cookie is None, "Checkin cookie should not be set"
    # Verify error message
    assert "invalid meeting code" in user_home.get_error_message().lower()


def test_vote_in_election(user_meeting, browser, base_url):
    """Test the complete voting flow"""
    meeting_id = user_meeting["meeting_id"]
    user_home = UserHomePage(browser, base_url)
    # First, check in to the meeting
    user_home.visit("/")
    meeting_card = user_home.get_meeting_card_by_id(meeting_id)
    assert meeting_card.is_displayed(), "Meeting card should be visible"
    checkin_url = user_home.get_checkin_url(meeting_id)
    assert checkin_url is not None, "Checkin URL should be visible"
    browser.get(checkin_url)
    user_home.enter_meeting_code(user_meeting["meeting_code"])
    user_home.click_check_in()
    cookies = browser.get_cookies()
    checkin_cookie = next(
        (c for c in cookies if c["name"] == f"meeting_{meeting_id}"), None
    )
    assert checkin_cookie is not None, "Checkin cookie should be set"

    vote_url = user_home.get_vote_url(user_meeting["election_id"])
    assert vote_url is not None, "Vote URL should be visible"
    browser.get(vote_url)

    # Select a vote option and submit
    user_home.select_vote_option("C")
    assert user_home.is_vote_option_selected("C")
    user_home.submit_vote()

    # Verify vote was recorded
    assert user_home.is_vote_confirmed(), "Vote confirmation should be displayed"
