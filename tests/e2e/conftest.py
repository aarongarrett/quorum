import os
from datetime import datetime, timedelta

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from app import create_app


@pytest.fixture(scope="session", autouse=True)
def reset_database_via_http(base_url):
    """
    Before running any E2E tests, hit POST /_test/reset-db on the web container.
    Since base_url points to the web container, this call empties the DB.
    """
    url = f"{base_url}/_test/reset-db"
    resp = requests.post(url)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to reset DB: {resp.status_code} {resp.text}")
    yield


@pytest.fixture(scope="session")
def app():
    return create_app("testing")


@pytest.fixture(scope="session")
def admin_user(app):
    """Fixture to create an admin user for testing"""
    with app.app_context():
        yield app.config["ADMIN_PASSWORD"]


@pytest.fixture(scope="session")
def base_url():
    return os.environ["BASE_URL"]


@pytest.fixture(scope="session")
def api_login(app, base_url, admin_user):
    """
    1) Logs in as admin and returns a dict containing:
       - session: an authenticated requests.Session
       - app: the Flask app instance
       - base_url: where the web server is listening
    2) Does NOT create any meeting/poll/checkin.
       Those will be created per-test (admin_meeting, user_meeting).
    """
    sess = requests.Session()
    login_resp = sess.post(
        f"{base_url}/admin/login",
        data={"password": admin_user},
        allow_redirects=True,
    )
    assert login_resp.status_code == 200

    return {
        "session": sess,
        "app": app,
        "base_url": base_url,
    }


@pytest.fixture
def admin_meeting(api_login):
    """
    Creates one meeting and poll for admin tests. Returns:
      {
        "session":      requests.Session(),
        "meeting_id":   int,
        "meeting_code": str,
        "poll_id":  int
      }
    """
    s = api_login["session"]
    base = api_login["base_url"]
    tz = api_login["app"].config["TZ"]

    # 1) Create a new meeting
    now = datetime.now(tz)
    meeting_payload = {
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(hours=2)).isoformat(),
    }
    m_resp = s.post(
        f"{base}/api/admin/meetings",
        json=meeting_payload,
    )
    m_resp.raise_for_status()
    m_data = m_resp.json()
    mid = m_data["meeting_id"]
    mcode = m_data["meeting_code"]

    # 2) Create exactly one poll on that meeting
    e_resp = s.post(
        f"{base}/api/admin/meetings/{mid}/polls",
        json={"name": "Admin Test Poll"},
    )
    e_resp.raise_for_status()
    e_data = e_resp.json()
    eid = e_data["poll_id"]

    return {
        "session": s,
        "meeting_id": mid,
        "meeting_code": mcode,
        "poll_id": eid,
    }


@pytest.fixture
def user_meeting(api_login):
    """
    Creates a separate meeting + poll for user-flow tests. Returns:
      {
        "session":      requests.Session(),
        "meeting_id":   int,
        "meeting_code": str,
        "poll_id":  int
      }
    """
    s = api_login["session"]
    base = api_login["base_url"]
    tz = api_login["app"].config["TZ"]

    # 1) Create a new meeting
    now = datetime.now(tz)
    meeting_payload = {
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(hours=2)).isoformat(),
    }
    m_resp = s.post(
        f"{base}/api/admin/meetings",
        json=meeting_payload,
    )
    m_resp.raise_for_status()
    m_data = m_resp.json()
    mid = m_data["meeting_id"]
    mcode = m_data["meeting_code"]

    # 2) Create exactly one poll on that meeting
    e_resp = s.post(
        f"{base}/api/admin/meetings/{mid}/polls",
        json={"name": "User Test Poll"},
    )
    e_resp.raise_for_status()
    e_data = e_resp.json()
    eid = e_data["poll_id"]

    return {
        "session": s,
        "meeting_id": mid,
        "meeting_code": mcode,
        "poll_id": eid,
    }


@pytest.fixture(scope="session")
def browser():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    selenium_url = os.environ.get("SELENIUM_REMOTE_URL", "http://selenium:4444/wd/hub")
    driver = webdriver.Remote(command_executor=selenium_url, options=opts)
    yield driver
    driver.quit()


@pytest.fixture(autouse=True)
def clear_cookies(browser):
    """Clear cookies before and after each test"""
    browser.delete_all_cookies()
    yield
    browser.delete_all_cookies()
