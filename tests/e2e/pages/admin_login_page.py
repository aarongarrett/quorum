from selenium.webdriver.common.by import By

from .base_page import BasePage


class AdminLoginPage(BasePage):
    def login(self, password):
        pwd_input = self.browser.find_element(By.NAME, "password")
        pwd_input.send_keys(password)
        print(pwd_input.get_attribute("name"))
        print(pwd_input.get_attribute("value"))
        pwd_input.submit()
