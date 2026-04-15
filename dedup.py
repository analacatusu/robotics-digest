"""Tracks already-sent article URLs to avoid duplicates across runs."""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SEEN_FILE = Path(__file__).parent / "seen.json"
RETENTION_DAYS = 7


def _load() -> dict[str, str]:
    """Load seen URLs from disk. Returns {url: date_string}."""
    if not SEEN_FILE.exists():
        return {}
    try:
        return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read seen.json: %s", exc)
        return {}


def _save(data: dict[str, str]) -> None:
    """Write seen URLs atomically to avoid corruption on crash or timeout."""
    tmp = SEEN_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    # os.replace is atomic on the same filesystem (NTFS included)
    os.replace(tmp, SEEN_FILE)


def _prune(data: dict[str, str]) -> dict[str, str]:
    """Remove entries older than RETENTION_DAYS. Skips malformed date values."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")
    return {
        url: date for url, date in data.items()
        if date and len(date) == 10 and date >= cutoff
    }


def filter_new(articles: list[dict]) -> list[dict]:
    """Return only articles whose URLs haven't been seen before."""
    seen = _load()
    return [a for a in articles if a["url"] not in seen]


def mark_sent(articles: list[dict]) -> None:
    """Persist article URLs as seen, pruning old entries."""
    seen = _prune(_load())
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for a in articles:
        seen[a["url"]] = today
    _save(seen)
