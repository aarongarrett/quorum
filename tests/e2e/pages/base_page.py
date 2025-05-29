class BasePage:
    def __init__(self, browser, base_url):
        self.browser = browser
        self.base_url = base_url

    def visit(self, path=""):
        self.browser.get(f"{self.base_url}{path}")
