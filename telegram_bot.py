"""Sends a message to a Telegram chat via the Bot API."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_message(text: str) -> None:
    """Send text to the configured Telegram chat. Raises on failure."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Check your .env file.")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is not set. Check your .env file.")

    try:
        resp = requests.post(
            TELEGRAM_API.format(token=token),
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        # Scrub token from the exception string before surfacing it
        safe_msg = str(exc).replace(token, "<REDACTED>")
        raise RuntimeError(f"Telegram request failed: {safe_msg}") from exc

    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result.get('description', result)}")


def get_chat_id(token: str) -> None:
    """
    Helper to find your TELEGRAM_CHAT_ID.
    Run once after sending your bot a message (or adding it to a group):
        python -c "from telegram_bot import get_chat_id; get_chat_id('YOUR_TOKEN')"
    Group chat IDs are negative numbers (e.g. -1001234567890).
    """
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        safe_msg = str(exc).replace(token, "<REDACTED>")
        print(f"Request failed: {safe_msg}")
        return

    updates = resp.json().get("result", [])
    if not updates:
        print("No updates found. Send your bot a message (or post in the group) first, then run again.")
        return
    for update in updates:
        chat = update.get("message", {}).get("chat", {})
        chat_id = chat.get("id")
        name = chat.get("first_name") or chat.get("title") or "(unknown)"
        chat_type = chat.get("type", "")
        print(f"Chat ID: {chat_id}  |  Name: {name}  |  Type: {chat_type}")
