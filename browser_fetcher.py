"""
Scrapes blog/news listing pages for companies that have no RSS feed.
Uses requests + BeautifulSoup (server-rendered pages only — no JS execution needed).

Confirmed server-rendered (verified via live fetch 2026-04-15):
  Figure AI, 1X Technologies, Sanctuary AI, Physical Intelligence,
  Unitree, Gecko Robotics
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from sources import SCRAPE_TARGETS

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RoboticsDigestBot/1.0)"
}
FETCH_TIMEOUT = 15

# Patterns used to find date strings in nearby text
_DATE_PATTERNS = [
    # 2026-04-15, 2025-03-18
    (re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"), "%Y-%m-%d"),
    # April 1, 2026 / January 27, 2026
    (re.compile(r"\b([A-Za-z]+ \d{1,2},? \d{4})\b"), None),
    # MAR 17 '26 / JAN 12 '26
    (re.compile(r"\b([A-Z]{3} \d{1,2} '\d{2})\b"), None),
    # 03/17/2026 or 17/03/2026
    (re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b"), None),
]


def _extract_date(text: str) -> str:
    """Try to parse a date from arbitrary text. Returns YYYY-MM-DD or ''."""
    for pattern, fmt in _DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        raw = m.group(1)
        if fmt:
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
        else:
            # Try a set of common formats
            for f in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y",
                      "%b %d '%y", "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    return datetime.strptime(raw, f).strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return ""


def _nearby_text(tag) -> str:
    """Collect text from the tag's parent and siblings to find a date."""
    parts = []
    parent = tag.parent
    if parent:
        parts.append(parent.get_text(" ", strip=True))
        grandparent = parent.parent
        if grandparent:
            parts.append(grandparent.get_text(" ", strip=True))
    return " ".join(parts)


def _href_matches(href: str, prefix: str | list[str]) -> bool:
    """Return True if href starts with any of the given prefix(es)."""
    if isinstance(prefix, list):
        return any(href.startswith(p) for p in prefix)
    return href.startswith(prefix)


def _scrape_site(target: dict) -> list[dict]:
    """Fetch a single listing page and extract article links."""
    try:
        resp = requests.get(
            target["listing_url"],
            headers=HEADERS,
            timeout=FETCH_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", target["name"], exc)
        return []

    # Use apparent encoding (chardet-based) to handle non-UTF-8 sites correctly
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    articles = []
    seen_hrefs: set[str] = set()

    for a in soup.find_all("a", href=True):
        href: str = a["href"].strip()  # strip whitespace to prevent URL construction bugs
        if not _href_matches(href, target["link_prefix"]):
            continue
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)

        title = a.get_text(" ", strip=True)
        if not title or len(title) < 5:
            # Link text too short — try aria-label or title attribute
            title = a.get("aria-label") or a.get("title") or ""
        if not title:
            continue

        url = target["base_url"] + href if href.startswith("/") else href
        date = _extract_date(_nearby_text(a))

        articles.append({
            "title": title,
            "url": url,
            "snippet": "",
            "source": target["name"],
            "category": target["category"],
            "published": date,
        })

        if len(articles) >= target.get("max_articles", 10):
            break

    logger.info("Scraped %d articles from %s", len(articles), target["name"])
    return articles


def fetch_scraped() -> list[dict]:
    """Scrape all SCRAPE_TARGETS concurrently and return a flat article list."""
    all_articles: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_scrape_site, target): target for target in SCRAPE_TARGETS}
    for future, target in futures.items():
        try:
            all_articles.extend(future.result())
        except Exception as exc:
            logger.warning("Failed to scrape %s: %s", target["name"], exc)
    return all_articles
