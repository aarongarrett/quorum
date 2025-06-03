from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .base_page import BasePage


class UserHomePage(BasePage):
    MEETING_CARDS = (By.CSS_SELECTOR, ".meeting-card")
    MEETING_CODE_INPUT = (By.ID, "meeting_code")
    CHECK_IN_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
    ERROR_MESSAGE = (By.CSS_SELECTOR, ".alert.alert-danger")
    SUCCESS_MESSAGE = (By.CSS_SELECTOR, ".alert.alert-success")
    ELECTION_OPTIONS = (By.CSS_SELECTOR, "input[name^='election_']")
    VOTE_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
    VOTE_CONFIRMATION = (By.CSS_SELECTOR, ".vote-cast")

    def get_meeting_cards(self):
        """Return all meeting cards on the page"""
        return self.browser.find_elements(*self.MEETING_CARDS)

    def get_meeting_card_by_id(self, meeting_id):
        """Find a meeting card by its ID"""
        return self.browser.find_element(
            By.CSS_SELECTOR, f'[data-meeting-id="{meeting_id}"]'
        )

    def enter_meeting_code(self, code):
        """Enter meeting code in the check-in form"""
        self.browser.find_element(*self.MEETING_CODE_INPUT).send_keys(code)

    def click_check_in(self):
        """Click the check-in button"""
        self.browser.find_element(*self.CHECK_IN_BUTTON).click()

    def get_error_message(self):
        """Get error message text if present"""
        return self.browser.find_element(*self.ERROR_MESSAGE).text

    def get_success_message(self):
        """Get success message text if present"""
        return self.browser.find_element(*self.SUCCESS_MESSAGE).text

    def select_vote_option(self, option):
        """Select a voting option"""
        label = self.browser.find_element(By.CSS_SELECTOR, f'label[for="opt{option}"]')
        label.click()

    def is_vote_option_selected(self, option):
        return self.browser.find_element(By.ID, f"opt{option}").is_selected()

    def submit_vote(self):
        """Submit the vote form"""
        submit_btn = WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located(self.VOTE_BUTTON)
        )
        WebDriverWait(self.browser, 10).until(
            lambda d: submit_btn.is_enabled() and submit_btn.is_displayed()
        )
        self.browser.execute_script("arguments[0].click();", submit_btn)

    def is_vote_confirmed(self):
        """Check if vote confirmation is displayed"""
        return len(self.browser.find_elements(*self.VOTE_CONFIRMATION)) > 0

    def get_checkin_url(self, meeting_id):
        """Get the check-in URL for a specific meeting"""
        meeting_card = self.get_meeting_card_by_id(meeting_id)
        checkin_button = meeting_card.find_element(By.CSS_SELECTOR, "a.btn.btn-primary")
        return checkin_button.get_attribute("href")

    def get_vote_url(self, election_id):
        """Get the vote URL for a specific election"""
        election_div = self.browser.find_element(
            By.CSS_SELECTOR, f"[data-election-id='{election_id}']"
        )
        vote_button = election_div.find_element(By.CSS_SELECTOR, "a.btn.btn-primary")
        return vote_button.get_attribute("href")
