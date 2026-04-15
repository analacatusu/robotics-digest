"""
Telegram bot command listener.

Long-polls for /scrape commands in the configured group chat and triggers
`main.py --on-demand`, which fetches and sends only articles that have not
appeared in the regular morning digest.

Run as a persistent background scheduled task (at log on, no end time).
setup.ps1 registers this automatically as "Robotics Digest Listener".
"""

import logging
import os
import re
import subprocess
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=True)

# Comma-separated Telegram user IDs allowed to trigger /scrape from any chat
# (group or private DM). Both must appear in this list.
_raw = os.environ.get("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS: set[int] = {int(uid.strip()) for uid in _raw.split(",") if uid.strip()}

_log_file = Path(__file__).parent / "listener.log"
_file_handler = RotatingFileHandler(_log_file, maxBytes=500_000, backupCount=2, encoding="utf-8")
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
_file_handler.setFormatter(_fmt)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), _file_handler],
)
logger = logging.getLogger("bot_listener")

POLL_TIMEOUT = 30  # seconds — Telegram long-poll window


def _get_updates(token: str, offset: int | None) -> list[dict]:
    try:
        params: dict = {"timeout": POLL_TIMEOUT, "allowed_updates": ["message"]}
        if offset is not None:
            params["offset"] = offset
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params=params,
            timeout=POLL_TIMEOUT + 5,
        )
        resp.raise_for_status()
        return resp.json().get("result", [])
    except requests.RequestException as exc:
        safe = str(exc).replace(token, "<REDACTED>")
        logger.warning("getUpdates failed: %s", safe)
        return []


def _send(token: str, chat_id: str, text: str) -> None:
    """Best-effort acknowledgment send — errors are logged but not raised."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.warning("Failed to send acknowledgment: %s", exc)


def _handle(update: dict, token: str, group_chat_id: str) -> None:
    msg = update.get("message", {})
    text = (msg.get("text") or "").strip()
    msg_chat_id = str(msg.get("chat", {}).get("id", ""))
    chat_type = msg.get("chat", {}).get("type", "")

    # Accept /scrape only from whitelisted users, in either the group chat or a private DM
    sender_id = msg.get("from", {}).get("id")
    if sender_id is None:
        return  # channel post or service message — silently ignore
    if sender_id not in ALLOWED_USER_IDS:
        logger.warning("Ignored /scrape from unauthorised user %s", sender_id)
        return
    if chat_type in ("group", "supergroup") and msg_chat_id != group_chat_id:
        return

    if text.startswith("/scrape"):
        if not re.fullmatch(r"-?\d+", msg_chat_id):
            logger.error("Unexpected chat_id format: %s — ignoring /scrape", msg_chat_id)
            return
        logger.info("Received /scrape from chat %s (%s)", msg_chat_id, chat_type)
        _send(token, msg_chat_id, "Fetching fresh articles — this takes about a minute...")
        try:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).parent / "main.py"),
                 "--on-demand", "--chat-id", msg_chat_id],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            logger.error("/scrape timed out after 180 s")
            _send(token, msg_chat_id, "Scrape timed out — check listener.log for details.")
            return

        if result.returncode != 0:
            safe_stderr = result.stderr[:500].replace(token, "<REDACTED>")
            logger.error("on-demand run failed (exit %d):\n%s", result.returncode, safe_stderr)
            _send(token, msg_chat_id, "Scrape failed — check digest.log for details.")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID not set in .env")

    if not ALLOWED_USER_IDS:
        logger.warning("ALLOWED_USER_IDS is empty — /scrape will be blocked for everyone. Set it in .env.")

    logger.info("Bot listener started. Polling for /scrape in group %s + private DMs.", chat_id)

    offset: int | None = None
    while True:
        updates = _get_updates(token, offset)
        for update in updates:
            _handle(update, token, chat_id)
            offset = update["update_id"] + 1
        if not updates:
            time.sleep(1)  # brief pause when long-poll returns empty


if __name__ == "__main__":
    main()
