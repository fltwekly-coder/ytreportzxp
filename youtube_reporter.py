import logging
from dataclasses import dataclass
from typing import List, Optional
import requests
from requests.exceptions import RequestException

TEST_URL = "https://httpbin.org/ip"


@dataclass
class Proxy:
    http: str
    https: str


@dataclass
class Account:
    username: str
    proxy: Optional[Proxy] = None


def check_proxy(proxy: Proxy) -> bool:
    """Check whether a proxy is usable by issuing a lightweight request."""
    try:
        requests.get(TEST_URL, proxies={"http": proxy.http, "https": proxy.https}, timeout=5)
        return True
    except RequestException:
        return False


class YouTubeReporter:
    def __init__(self, accounts: List[Account]):
        self.accounts: List[Account] = []
        for account in accounts:
            if account.proxy and not check_proxy(account.proxy):
                logging.error("Proxy failed for account %s", account.username)
                continue
            self.accounts.append(account)
