import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
import yt_report_bot


def test_load_accounts():
    accounts = yt_report_bot.load_accounts('accounts.txt')
    assert accounts[0].email == 'user1@example.com'
    assert accounts[0].recovery_email == 'recovery1@example.com'
    assert accounts[1].password == 'password2'


def test_load_proxies():
    proxies = yt_report_bot.load_proxies('proxies.txt')
    assert proxies[0].host == 'proxyhost1'
    assert proxies[1].user == 'proxyuser2'
