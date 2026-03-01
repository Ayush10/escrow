from __future__ import annotations

import os

import httpx


def send_telegram_notification(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        with httpx.Client(timeout=10) as client:
            client.post(url, json=payload)
    except Exception:
        return
