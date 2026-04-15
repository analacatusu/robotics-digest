"""
Robotics News Digest Bot — entry point.

Usage:
    python main.py              # normal run: fetch, summarize, send
    python main.py --dry-run    # fetch & summarize but don't send to Telegram
    python main.py --force      # ignore dedup, send even if articles were seen before
    python main.py --on-demand  # send only articles not in today's morning digest
                                # (triggered by /scrape command via bot_listener.py)
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the same directory as this script
load_dotenv(Path(__file__).parent / ".env", override=True)

import dedup
import fetcher
import summarizer
import telegram_bot

# Log to both terminal and a rotating file (so Task Scheduler failures are diagnosable)
_log_file = Path(__file__).parent / "digest.log"
_file_handler = RotatingFileHandler(
    _log_file, maxBytes=500_000, backupCount=3, encoding="utf-8"
)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
_file_handler.setFormatter(_fmt)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), _file_handler],
)
logger = logging.getLogger("main")


def run(dry_run: bool = False, force: bool = False, on_demand: bool = False, chat_id: str | None = None) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    mode = "on-demand" if on_demand else ("forced" if force else "scheduled")
    logger.info("Starting robotics digest [%s] for %s", mode, today)

    # 1. Fetch
    logger.info("Fetching articles...")
    all_articles = fetcher.fetch_all()
    logger.info("Fetched %d articles total", len(all_articles))

    # 2. Filter already-seen (unless forced)
    if force:
        new_articles = all_articles
        logger.info("--force: skipping dedup, using all %d articles", len(new_articles))
    else:
        new_articles = dedup.filter_new(all_articles)
        logger.info("%d new articles after dedup", len(new_articles))

    if not new_articles:
        logger.info("No new articles. Nothing to send.")
        if on_demand:
            telegram_bot.send_message("No new articles since the morning digest. Check back later!", chat_id=chat_id)
        return

    # 3. Summarize
    logger.info("Generating digest with Claude...")
    digest = summarizer.generate_digest(new_articles, today, on_demand=on_demand)
    logger.info("Digest generated (%d chars)", len(digest))

    # 4. Send (or print)
    if dry_run:
        sys.stdout.buffer.write(("\n" + "=" * 60 + "\n").encode("utf-8"))
        sys.stdout.buffer.write(digest.encode("utf-8"))
        sys.stdout.buffer.write(("\n" + "=" * 60 + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
        logger.info("Dry run — digest printed, not sent to Telegram.")
    else:
        logger.info("Sending to Telegram...")
        telegram_bot.send_message(digest, chat_id=chat_id)
        logger.info("Sent successfully.")

    # 5. Mark as seen (never modify state on a dry run)
    if not dry_run:
        dedup.mark_sent(new_articles)
        logger.info("Marked %d articles as seen.", len(new_articles))
    else:
        logger.info("Dry run — seen.json not updated.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Robotics News Digest Bot")
    parser.add_argument("--dry-run", action="store_true", help="Print digest without sending")
    parser.add_argument("--force", action="store_true", help="Ignore dedup and send all fetched articles")
    parser.add_argument("--on-demand", action="store_true", help="Send only articles not in today's morning digest")
    parser.add_argument("--chat-id", default=None, help="Override TELEGRAM_CHAT_ID for this run (used for DM replies)")
    args = parser.parse_args()

    try:
        run(dry_run=args.dry_run, force=args.force, on_demand=args.on_demand, chat_id=args.chat_id)
    except Exception:
        logger.exception("Digest bot failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
