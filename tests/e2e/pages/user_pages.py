from selenium.webdriver.common.by import By

from .base_page import BasePage


class UserHomePage(BasePage):
    MEETING_CARDS = (By.CSS_SELECTOR, ".meeting-card")
    MEETING_CODE_INPUT = (By.ID, "meeting_code")
    CHECK_IN_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
    ERROR_MESSAGE = (By.CSS_SELECTOR, ".alert.alert-danger")
    SUCCESS_MESSAGE = (By.CSS_SELECTOR, ".alert.alert-success")
    ELECTION_OPTIONS = (By.CSS_SELECTOR, "input[name^='election_']")
    VOTE_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
    VOTE_CONFIRMATION = (By.CSS_SELECTOR, ".vote-confirmation")

    def get_meeting_cards(self):
        """Return all meeting cards on the page"""
        return self.browser.find_elements(*self.MEETING_CARDS)

    def get_meeting_card_by_id(self, meeting_id):
        """Find a meeting card by its ID"""
        return self.browser.find_element(
            By.CSS_SELECTOR, f"[data-meeting-id='{meeting_id}']"
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

    def select_vote_option(self, election_id, option):
        """Select a voting option for a specific election"""
        option_selector = f"input[name='election_{election_id}'][value='{option}']"
        self.browser.find_element(By.CSS_SELECTOR, option_selector).click()

    def submit_vote(self):
        """Submit the vote form"""
        self.browser.find_element(*self.VOTE_BUTTON).click()

    def is_vote_confirmed(self):
        """Check if vote confirmation is displayed"""
        return len(self.browser.find_elements(*self.VOTE_CONFIRMATION)) > 0
