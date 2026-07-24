from __future__ import annotations

import os
import time

import requests


def send_messages(messages: list[str]) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel = os.getenv("TELEGRAM_CHANNEL")
    if not token or not channel:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL are required in publish mode")

    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    for message in messages:
        response = requests.post(
            endpoint,
            json={
                "chat_id": channel,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "disable_notification": False,
            },
            timeout=30,
        )
        if not response.ok:
            raise RuntimeError(f"Telegram API error {response.status_code}: {response.text[:500]}")
        time.sleep(0.8)
