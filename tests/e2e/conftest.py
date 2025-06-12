from datetime import datetime, timedelta

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from testcontainers.compose import DockerCompose


# Spin up your entire e2e stack via the compose file
@pytest.fixture(scope="session")
def compose(pytestconfig):
    compose = DockerCompose(
        pytestconfig.rootpath,
        compose_file_name="docker-compose.e2e.yml",
        pull=False,
        build=True,
        wait=True,
    )
    compose.start()  # equivalent to `docker compose up -d`
    yield compose
    compose.stop()  # tear everything down


@pytest.fixture(scope="session")
def base_url():
    return "http://web:5000"


@pytest.fixture(scope="session")
def browser(compose):
    import time

    selenium_host = compose.get_service_host("selenium", 4444)
    selenium_port = compose.get_service_port("selenium", 4444)
    selenium_url = f"http://{selenium_host}:{selenium_port}"

    status_url = selenium_url + "/status"
    for i in range(30):  # try for up to 30 seconds
        try:
            r = requests.get(status_url, timeout=1)
            data = r.json()
            if r.status_code == 200 and data.get("value", {}).get("ready", False):
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        pytest.fail(f"Selenium never became ready at {status_url}")

    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Remote(command_executor=selenium_url + "/wd/hub", options=opts)
    yield driver
    driver.quit()


@pytest.fixture(autouse=True)
def clear_cookies(browser):
    """Clear cookies before and after each test"""
    browser.delete_all_cookies()
    yield
    browser.delete_all_cookies()


@pytest.fixture(autouse=True)
def close_sse(browser):
    yield
    # after each test, if the page ever created a SSE, close it
    browser.execute_script(
        """
      if (window.userSSE) {
        window.userSSE.close();
        window.userSSE = null;
      }
      if (window.adminSSE) {
        window.adminSSE.close();
        window.adminSSE = null;
      }
    """
    )


@pytest.fixture(scope="session", autouse=True)
def reset_database_via_http(compose):
    """
    Before running any E2E tests, hit POST /_test/reset-db on web container.
    Since base_url points to the web container, this call empties the DB.
    """
    host = compose.get_service_host("web", 5000)
    port = compose.get_service_port("web", 5000)

    import time

    health_url = f"http://{host}:{port}/_test/health"
    # Wait for the web service to be live
    for i in range(30):  # try for up to 30 seconds
        try:
            r = requests.get(health_url, timeout=1)
            data = r.json()
            if r.status_code == 200 and data.get("status", "down") == "up":
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        pytest.fail(f"Web never became ready at {health_url}")

    # — SETUP: drop & recreate before any tests —
    reset_url = f"http://{host}:{port}/_test/reset-db"
    resp = requests.post(reset_url)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to reset DB: {resp.status_code} {resp.text}")

    yield

    # — TEARDOWN: drop & recreate one final time —
    resp = requests.post(reset_url)
    if resp.status_code != 200:
        # you can log or raise here depending on how critical this is
        raise RuntimeError(f"Failed to tear down DB: {resp.status_code} {resp.text}")


@pytest.fixture(scope="session")
def admin_user():
    """Fixture to create an admin user for testing"""
    return "testadminpwd"


@pytest.fixture(scope="session")
def tz():
    """Fixture to create the proper time zone"""
    from zoneinfo import ZoneInfo

    return ZoneInfo("America/New_York")


@pytest.fixture(scope="session")
def api_login(admin_user, compose):
    """
    1) Logs in as admin and returns a dict containing:
       - session: an authenticated requests.Session
       - base_url: where the web server is listening
    2) Does NOT create any meeting/poll/checkin.
       Those will be created per-test (admin_meeting, user_meeting).
    """
    sess = requests.Session()
    host = compose.get_service_host("web", 5000)
    port = compose.get_service_port("web", 5000)
    base_url = f"http://{host}:{port}"
    login_resp = sess.post(
        f"{base_url}/admin/login",
        data={"password": admin_user},
        allow_redirects=True,
    )
    assert login_resp.status_code == 200

    return {
        "session": sess,
        "base_url": base_url,
    }


@pytest.fixture
def admin_meeting(api_login, tz):
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
def user_meeting(api_login, tz):
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
