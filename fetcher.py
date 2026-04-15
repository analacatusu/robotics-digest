"""Fetches articles from RSS feeds and Hacker News."""

import concurrent.futures
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

from browser_fetcher import fetch_scraped
from sources import HN_MAX_RESULTS, HN_SEARCH_QUERY, RSS_FEEDS

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RoboticsDigestBot/1.0)"
}
FETCH_TIMEOUT = 10   # seconds per HTTP request
PER_FEED_TIMEOUT = 12  # max seconds allowed per feed (including parse)


def _parse_date(entry) -> str | None:
    """Extract a readable date string from a feedparser entry."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc).strftime("%Y-%m-%d")
            except Exception:
                pass
    return None


def _snippet(entry) -> str:
    """Extract a short plain-text snippet from a feedparser entry."""
    raw = ""
    if hasattr(entry, "summary"):
        raw = entry.summary
    elif hasattr(entry, "content") and entry.content:
        raw = entry.content[0].get("value", "")
    text = BeautifulSoup(raw, "html.parser").get_text(separator=" ")
    return text[:300].strip()


def _fetch_one_feed(feed_cfg: dict) -> list[dict]:
    """Download and parse a single RSS feed. Returns list of article dicts."""
    # Download with requests so we control the timeout
    resp = requests.get(
        feed_cfg["url"],
        headers=HEADERS,
        timeout=FETCH_TIMEOUT,
    )
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)

    articles = []
    for entry in feed.entries[:15]:
        url = entry.get("link", "")
        if not url:
            continue
        articles.append({
            "title": entry.get("title", "").strip(),
            "url": url,
            "snippet": _snippet(entry),
            "source": feed_cfg["name"],
            "category": feed_cfg["category"],
            "published": _parse_date(entry) or "",
        })
    return articles


def fetch_rss() -> list[dict]:
    """Fetch all RSS feeds concurrently. Each feed is bounded by FETCH_TIMEOUT (requests)."""
    articles = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_fetch_one_feed, cfg): cfg for cfg in RSS_FEEDS}
    # Collect results after all workers have finished (executor.__exit__ waits for them)
    for future, cfg in futures.items():
        try:
            result = future.result()
            articles.extend(result)
            logger.info("Fetched %d articles from %s", len(result), cfg["name"])
        except concurrent.futures.TimeoutError:
            logger.warning("Timed out fetching %s", cfg["name"])
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", cfg["name"], exc)
    return articles


def fetch_hacker_news() -> list[dict]:
    """Query Hacker News Algolia API for robotics stories."""
    try:
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={
                "query": HN_SEARCH_QUERY,
                "tags": "story",
                "numericFilters": "created_at_i>%d" % int(
                    datetime.now(timezone.utc).timestamp() - 86400
                ),
                "hitsPerPage": HN_MAX_RESULTS,
            },
            timeout=FETCH_TIMEOUT,
            headers=HEADERS,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        articles = []
        for hit in hits:
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            articles.append({
                "title": hit.get("title", "").strip(),
                "url": url,
                "snippet": "",
                "source": "Hacker News",
                "category": "community",
                "published": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })
        return articles
    except Exception as exc:
        logger.warning("Failed to fetch Hacker News: %s", exc)
        return []


def fetch_all(max_total: int = 140) -> list[dict]:
    """Fetch from all sources concurrently, deduplicate by URL, cap total."""
    articles = fetch_rss() + fetch_hacker_news() + fetch_scraped()

    # Deduplicate by URL within this fetch
    seen_urls: set[str] = set()
    unique = []
    for a in articles:
        if a["url"] not in seen_urls:
            seen_urls.add(a["url"])
            unique.append(a)

    return unique[:max_total]
