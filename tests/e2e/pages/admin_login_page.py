from selenium.webdriver.common.by import By

from .base_page import BasePage


class AdminLoginPage(BasePage):
    def login(self, password):
        pwd_input = self.browser.find_element(By.NAME, "password")
        pwd_input.send_keys(password)
        pwd_input.submit()
