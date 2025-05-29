import os

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from app import create_app


@pytest.fixture(scope="session")
def app():
    return create_app("testing")


@pytest.fixture
def admin_user():
    """Fixture to create an admin user for testing"""
    app = create_app("testing")
    with app.app_context():
        yield app.config["ADMIN_PASSWORD"]


@pytest.fixture(scope="session")
def base_url():
    return os.environ["BASE_URL"]


@pytest.fixture(scope="session", autouse=True)
def seed_via_api(base_url, admin_user):
    s = requests.Session()
    # 1) Log in as admin
    s.post(f"{base_url}/admin/login", data={"password": admin_user})
    # 2) Create your meeting & election exactly as your UI does
    s.post(
        f"{base_url}/admin/meetings/create",
        data={
            "start_time": "2025-05-28T22:00-04:00",
            "end_time": "2025-05-28T23:59-04:00",
        },
    )
    s.post(f"{base_url}/admin/create_election/1", data={"name": "Test"})
    return s


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
