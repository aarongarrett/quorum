import os
from datetime import datetime, timedelta

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from app import create_app


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
def seed_via_api(app, base_url, admin_user):
    s = requests.Session()
    # 1) Log in as admin
    login_response = s.post(f"{base_url}/api/login", json={"password": admin_user})
    assert login_response.status_code == 200
    # 2) Create your meeting & election exactly as your UI does
    start_time = datetime.now(app.config["TZ"])
    meeting_response = s.post(
        f"{base_url}/api/admin/meetings",
        json={
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(hours=2)).isoformat(),
        },
    )
    assert meeting_response.status_code == 201
    # get the meeting id out of the json response
    meeting_json = meeting_response.json()
    meeting_id = meeting_json["meeting_id"]
    meeting_code = meeting_json["meeting_code"]
    election_response = s.post(
        f"{base_url}/api/admin/meetings/{meeting_id}/elections", json={"name": "Test"}
    )
    assert election_response.status_code == 201
    # get the election id from the election response
    election_id = election_response.json()["election_id"]
    # 3) Check in as a user
    checkin_response = s.post(
        f"{base_url}/api/meetings/{meeting_id}/checkins",
        json={"meeting_code": meeting_code},
    )
    assert checkin_response.status_code == 200
    # get the checkin token from the checkin response
    checkin_token = checkin_response.json()["token"]
    # 4) Vote in the election
    s.post(
        f"{base_url}/api/meetings/{meeting_id}/elections/{election_id}/votes",
        json={"token": checkin_token, "vote": "F"},
    )
    return {
        "session": s,
        "meeting_id": meeting_id,
        "meeting_code": meeting_code,
        "election_id": election_id,
        "checkin_token": checkin_token,
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
