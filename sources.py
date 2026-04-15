# All RSS feeds and web sources for the robotics digest.
# Add or remove entries here to customize coverage.
# Last verified: 2026-04-15

RSS_FEEDS = [
    # --- Industry News ---
    {
        "name": "The Robot Report",
        "url": "https://www.therobotreport.com/feed/",
        "category": "industry",
    },
    {
        "name": "IEEE Spectrum",
        "url": "https://spectrum.ieee.org/rss/fulltext",
        "category": "industry",
    },
    {
        "name": "TechCrunch Robotics",
        "url": "https://techcrunch.com/category/robotics/feed/",
        "category": "industry",
    },
    # --- Big Players ---
    {
        "name": "Boston Dynamics",
        "url": "https://bostondynamics.com/feed/",
        "category": "big_player",
    },
    {
        "name": "NVIDIA Robotics Blog",
        "url": "https://blogs.nvidia.com/blog/category/robotics/feed/",
        "category": "big_player",
    },
    # --- Research ---
    {
        "name": "arXiv – Robotics (cs.RO)",
        "url": "https://arxiv.org/rss/cs.RO",
        "category": "research",
    },
    # --- Community ---
    {
        "name": "Reddit r/robotics",
        "url": "https://www.reddit.com/r/robotics/top/.rss?t=day",
        "category": "community",
    },
]

# Hacker News Algolia API — searched separately in fetcher.py
HN_SEARCH_QUERY = "robotics"
HN_MAX_RESULTS = 10

# Companies with no RSS feed — scraped directly from their listing pages.
# link_prefix: only <a href> tags starting with this string are treated as articles.
# Multiple link_prefixes can be given as a list.
# Last verified: 2026-04-15
SCRAPE_TARGETS = [
    # --- Big Players (no RSS) ---
    {
        "name": "Figure AI",
        "listing_url": "https://www.figure.ai/news",
        "base_url": "https://www.figure.ai",
        "link_prefix": "/news/",
        "category": "big_player",
        "max_articles": 10,
    },
    {
        "name": "Unitree",
        "listing_url": "https://www.unitree.com/news",
        "base_url": "https://www.unitree.com",
        "link_prefix": "/news/",
        "category": "big_player",
        "max_articles": 10,
    },
    # --- Emerging Players (no RSS) ---
    {
        "name": "1X Technologies",
        "listing_url": "https://www.1x.tech/discover",
        "base_url": "https://www.1x.tech",
        "link_prefix": "/discover/",
        "category": "emerging",
        "max_articles": 10,
    },
    {
        "name": "Sanctuary AI",
        "listing_url": "https://sanctuary.ai/blog",
        "base_url": "https://sanctuary.ai",
        "link_prefix": "/blog/",
        "category": "emerging",
        "max_articles": 10,
    },
    {
        "name": "Physical Intelligence",
        "listing_url": "https://www.pi.website/blog",
        "base_url": "https://www.pi.website",
        "link_prefix": ["/blog/", "/research/"],
        "category": "emerging",
        "max_articles": 10,
    },
    {
        "name": "Apptronik",
        "listing_url": "https://apptronik.com/press-release",
        "base_url": "https://apptronik.com",
        "link_prefix": "/news-collection/",
        "category": "emerging",
        "max_articles": 10,
    },
]
