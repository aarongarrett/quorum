import time
from datetime import datetime, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tests.e2e.pages.admin_login_page import AdminLoginPage


def test_admin_login_and_dashboard(browser, base_url, admin_user):
    """Test admin login and dashboard access"""
    login = AdminLoginPage(browser, base_url + "/admin")
    login.visit("/login")
    login.login(admin_user)
    assert browser.current_url.endswith("/admin/dashboard")
    assert "Create Meeting" in browser.page_source


def test_admin_login_wrong_password(browser, base_url):
    """Test admin login and dashboard access"""
    login = AdminLoginPage(browser, base_url + "/admin")
    login.visit("/login")
    login.login("WRONGPASSWORD")
    assert browser.current_url.endswith("/admin/login")
    assert "Invalid password" in browser.page_source


def test_create_meeting(browser, base_url, admin_user):
    """Test creating a new meeting through the admin interface."""
    # Login as admin
    login = AdminLoginPage(browser, base_url + "/admin")
    login.visit("/login")
    login.login(admin_user)

    # Navigate to create meeting page
    browser.find_element(By.LINK_TEXT, "Create Meeting").click()
    assert "Create Meeting" in browser.page_source

    # Fill out meeting form
    meeting_date = datetime.now() + timedelta(days=7)
    meeting_time = "14:00"
    meeting_date_str = meeting_date.strftime("%m/%d/%Y")
    browser.find_element(By.NAME, "date").send_keys(meeting_date_str)
    browser.find_element(By.NAME, "time").send_keys(meeting_time)

    # Submit form
    browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Verify redirect to dashboard and success message
    WebDriverWait(browser, 5).until(EC.url_contains("/admin/dashboard"))

    assert "Meeting created (code:" in browser.page_source

    # Verify meeting appears in the dashboard
    mstr = meeting_date.strftime("%B {day}, %Y").format(day=meeting_date.day)
    assert mstr in browser.page_source


def test_create_poll(browser, base_url, admin_user, admin_meeting):
    """Test creating a new poll for a meeting."""
    # Login as admin
    login = AdminLoginPage(browser, base_url + "/admin")
    login.visit("/login")
    login.login(admin_user)

    meeting_id = admin_meeting["meeting_id"]
    # Find the test meeting and click create poll
    WebDriverWait(browser, 5).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, f"[data-meeting-id='{meeting_id}']")
        )
    )

    create_poll_btn = WebDriverWait(browser, 5).until(
        EC.presence_of_element_located(
            (By.XPATH, ".//a[contains(normalize-space(.), 'Create Poll')]")
        )
    )

    create_poll_btn.click()

    # Fill out poll form
    poll_name = "Test Poll " + datetime.now().strftime("%Y-%m-%d %H:%M")
    browser.find_element(By.NAME, "name").send_keys(poll_name)

    # Submit form
    browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Verify redirect to dashboard and success message
    WebDriverWait(browser, 5).until(EC.url_contains("/admin/dashboard"))

    assert 'Poll created (name: "Test Poll' in browser.page_source

    # Verify poll appears in the meeting card
    assert poll_name in browser.page_source


def test_delete_poll(browser, base_url, admin_user, admin_meeting):
    """Test deleting an poll."""
    # Login as admin
    login = AdminLoginPage(browser, base_url + "/admin")
    login.visit("/login")
    login.login(admin_user)

    poll_id = admin_meeting["poll_id"]
    meeting_id = admin_meeting["meeting_id"]

    # Find the meeting card that contains our poll
    meeting_card = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, f"div[data-meeting-id='{meeting_id}']")
        )
    )

    # Scroll the meeting card into view
    browser.execute_script(
        "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
        meeting_card,
    )

    # Wait for the delete button to be clickable and visible in the viewport
    delete_btn = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, f"button[data-poll-id='{poll_id}']")
        )
    )

    # Add a small delay to ensure the UI is ready
    time.sleep(0.5)

    # Click the button using ActionChains to ensure it's properly clicked
    from selenium.webdriver.common.action_chains import ActionChains

    ActionChains(browser).move_to_element(delete_btn).click().perform()

    # Wait for modal to be present in the DOM
    modal = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, "deletePollModal"))
    )

    # Use JavaScript to ensure modal is visible
    WebDriverWait(browser, 10).until(
        lambda d: d.execute_script(
            'return window.getComputedStyle(arguments[0]).display !== "none" && '
            'window.getComputedStyle(arguments[0]).visibility !== "hidden" && '
            'document.querySelector(".modal-backdrop") !== null',
            modal,
        )
    )

    # Find and click the delete button directly
    delete_btn = browser.find_element(
        By.CSS_SELECTOR, "#deletePollForm button[type='submit']"
    )
    delete_btn.click()

    # Wait for success message and page update
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-success"))
    )

    # Verify success message
    assert "Poll deleted" in browser.page_source


def test_delete_meeting(browser, base_url, admin_user, admin_meeting):
    """Test deleting a meeting."""
    # Login as admin
    login = AdminLoginPage(browser, base_url + "/admin")
    login.visit("/login")
    login.login(admin_user)

    meeting_id = admin_meeting["meeting_id"]

    # Wait for the delete button to be clickable and visible in the viewport
    delete_btn = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, f"button[data-meeting-id='{meeting_id}']")
        )
    )

    browser.execute_script(
        "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
        delete_btn,
    )

    # Add a small delay to ensure the UI is ready
    time.sleep(0.5)

    # Click the button using ActionChains to ensure it's properly clicked
    from selenium.webdriver.common.action_chains import ActionChains

    ActionChains(browser).move_to_element(delete_btn).click().perform()

    # Wait for modal to be present in the DOM
    modal = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, "deleteMeetingModal"))
    )

    # Use JavaScript to ensure modal is visible
    WebDriverWait(browser, 10).until(
        lambda d: d.execute_script(
            'return window.getComputedStyle(arguments[0]).display !== "none" && '
            'window.getComputedStyle(arguments[0]).visibility !== "hidden" && '
            'document.querySelector(".modal-backdrop") !== null',
            modal,
        )
    )

    # Find and click the delete button directly
    delete_btn = browser.find_element(
        By.CSS_SELECTOR, "#deleteMeetingForm button[type='submit']"
    )
    delete_btn.click()

    # Wait for success message and page update
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-success"))
    )

    # Verify success message
    assert "Meeting deleted" in browser.page_source
    assert f'data-meeting-id="{meeting_id}"' not in browser.page_source
