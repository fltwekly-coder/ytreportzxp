import json
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

LOG_DIR = Path('logs')
COOKIE_DIR = Path('cookies')
SCREENSHOT_DIR = LOG_DIR / 'screenshots'

def setup_logger() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('yt_report_bot')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(LOG_DIR / 'bot.log')
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger

@dataclass
class Proxy:
    host: str
    port: str
    user: str
    password: str

    def as_url(self) -> str:
        return f"http://{self.user}:{self.password}@{self.host}:{self.port}"


@dataclass
class Account:
    email: str
    password: str
    recovery_email: str
    proxy: Optional[Proxy] = None


def load_accounts(path: str) -> List[Account]:
    accounts: List[Account] = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                email, password, recovery = line.split(':', 2)
            except ValueError:
                continue
            accounts.append(Account(email=email, password=password, recovery_email=recovery))
    return accounts


def load_proxies(path: str) -> List[Proxy]:
    proxies: List[Proxy] = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                host, port, user, password = line.split(':', 3)
            except ValueError:
                continue
            proxies.append(Proxy(host=host, port=port, user=user, password=password))
    return proxies

class YouTubeReporter:
    def __init__(self, accounts_file: str, proxies_file: str, target_url: str, reason: str, report_count: int):
        self.logger = setup_logger()
        self.accounts = load_accounts(accounts_file)
        self.proxies = load_proxies(proxies_file)
        self.target_url = target_url
        self.reason = reason
        self.report_count = report_count
        self.successful_logins = 0
        self.successful_reports = 0
        for acc, proxy in zip(self.accounts, self.proxies):
            acc.proxy = proxy

    def _create_driver(self, proxy: Optional[Proxy] = None) -> webdriver.Chrome:
        options = Options()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        if proxy:
            options.add_argument(f'--proxy-server={proxy.as_url()}')
        driver = webdriver.Chrome(options=options)
        driver.set_window_size(1024, 768)
        return driver

    def _load_cookies(self, driver: webdriver.Chrome, account: Account) -> bool:
        cookie_file = COOKIE_DIR / f"{account.email}.json"
        if not cookie_file.exists():
            return False
        try:
            driver.get('https://www.youtube.com')
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            for cookie in cookies:
                driver.add_cookie(cookie)
            driver.refresh()
            return True
        except WebDriverException:
            return False

    def _save_cookies(self, driver: webdriver.Chrome, account: Account) -> None:
        COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        cookie_file = COOKIE_DIR / f"{account.email}.json"
        with open(cookie_file, 'w', encoding='utf-8') as f:
            json.dump(driver.get_cookies(), f)
    def login(self, driver: webdriver.Chrome, account: Account) -> bool:
        if self._load_cookies(driver, account):
            self.logger.info('Loaded cookies for %s', account.email)
            return True
        try:
            driver.get('https://accounts.google.com/signin/v2/identifier')
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'identifierId')))
            driver.find_element(By.ID, 'identifierId').send_keys(account.email)
            driver.find_element(By.ID, 'identifierNext').click()
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, 'Passwd')))
            driver.find_element(By.NAME, 'Passwd').send_keys(account.password)
            driver.find_element(By.ID, 'passwordNext').click()
            WebDriverWait(driver, 20).until(EC.url_contains('myaccount.google.com'))
            self._save_cookies(driver, account)
            return True
        except Exception as exc:  # pragma: no cover - network interaction
            self.logger.error('Login failed for %s: %s', account.email, exc)
            screenshot_path = SCREENSHOT_DIR / f"login_fail_{account.email}.png"
            driver.save_screenshot(str(screenshot_path))
            return False

    def report_video(self, driver: webdriver.Chrome) -> bool:
        try:
            driver.get(self.target_url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            time.sleep(2)
            menu_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="More actions"]'))
            )
            menu_button.click()
            report_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//yt-formatted-string[text()='Report']"))
            )
            report_button.click()
            reason_radio = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, f"//yt-formatted-string[contains(text(), '{self.reason}')]"))
            )
            reason_radio.click()
            submit_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Submit']"))
            )
            submit_button.click()
            return True
        except Exception as exc:  # pragma: no cover - network interaction
            self.logger.error('Reporting video failed: %s', exc)
            screenshot_path = SCREENSHOT_DIR / 'report_video_fail.png'
            driver.save_screenshot(str(screenshot_path))
            return False

    def report_channel(self, driver: webdriver.Chrome) -> bool:
        try:
            driver.get(self.target_url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            time.sleep(2)
            about_link = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//tp-yt-paper-tab//div[contains(text(),'About')]"))
            )
            about_link.click()
            time.sleep(1)
            menu_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='More actions']"))
            )
            menu_button.click()
            report_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//tp-yt-paper-item//yt-formatted-string[text()='Report user']"))
            )
            report_button.click()
            reason_radio = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, f"//yt-formatted-string[contains(text(), '{self.reason}')]"))
            )
            reason_radio.click()
            submit_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Submit']"))
            )
            submit_button.click()
            return True
        except Exception as exc:  # pragma: no cover - network interaction
            self.logger.error('Reporting channel failed: %s', exc)
            screenshot_path = SCREENSHOT_DIR / 'report_channel_fail.png'
            driver.save_screenshot(str(screenshot_path))
            return False

    def process_account(self, account: Account) -> None:
        driver = self._create_driver(account.proxy)
        try:
            if not self.login(driver, account):
                return
            self.successful_logins += 1
            if 'watch?v=' in self.target_url:
                if self.report_video(driver):
                    self.successful_reports += 1
            else:
                if self.report_channel(driver):
                    self.successful_reports += 1
        finally:
            driver.quit()

    def run(self) -> None:
        threads = []
        accounts_to_use = self.accounts[:self.report_count]
        for account in accounts_to_use:
            t = threading.Thread(target=self.process_account, args=(account,), daemon=True)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        self.logger.info(
            'Summary: %s accounts, %s logins, %s reports',
            len(accounts_to_use),
            self.successful_logins,
            self.successful_reports,
        )

if __name__ == '__main__':
    target_url = input('Target URL (video or channel): ').strip()
    reason = input('Report reason: ').strip()
    count = int(input('Number of reports to submit: ').strip())
    bot = YouTubeReporter('accounts.txt', 'proxies.txt', target_url, reason, count)
    bot.run()
    print('Accounts used:', len(bot.accounts[:count]))
    print('Successful logins:', bot.successful_logins)
    print('Reports submitted:', bot.successful_reports)
