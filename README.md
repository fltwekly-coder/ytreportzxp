# YouTube Reporter Bot

This repository contains a proof-of-concept Selenium bot that automates reporting YouTube videos or channels. Use it responsibly and only for educational purposes.

## Features

- Loads Google accounts from `accounts.txt` and proxies from `proxies.txt`.
- Logs into each account using a unique proxy and stores session cookies.
- Prompts for target URL, report reason, and number of reports.
- Submits reports against videos or channels.
- Multi-threaded: each report runs in a separate thread using a different account.
- Logs actions to the `logs/` directory and captures screenshots on failures.

## Usage

Install dependencies and run tests:

```bash
pip install -r requirements.txt
pytest
```

Run the bot:

```bash
python yt_report_bot.py
```

### File Formats

`accounts.txt` lines use the format `email:password:recovery_email`.

`proxies.txt` lines use the format `host:port:username:password`.
