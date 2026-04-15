# Robotics Digest — Project Context

## Index

| Section | Contents |
|---------|----------|
| [Purpose & Scope](#purpose--scope) | What this project is and key decisions |
| [File Structure](#file-structure) | All files and their roles |
| [Setup Walkthrough](#setup-walkthrough) | Step-by-step first-time setup |
| [News Sources](#news-sources) | RSS feeds, scraped sites, broken sources |
| [CLI Options](#cli-options) | Commands and flags |
| [Troubleshooting](#troubleshooting) | Known problems and fixes |
| [Agents](#installed-claude-code-agents) | Installed agents and when to use them |
| [Enhancements](#enhancements-discussed) | Future work |
| [Detailed Docs](./docs/) | Agent session logs, code reviews, insights |

---

## Purpose & Scope

Daily AI-written robotics industry briefing delivered to Telegram every morning at 9:30 AM.
Covers big established players AND small emerging companies. Runs as a Windows scheduled task.

- **Delivery**: Telegram bot (`@RoboticsDigest_bot`) → **team group chat** (Roboverse Reply colleagues)
- **Frequency**: Once daily at **11:30 AM** via Windows Task Scheduler (`StartWhenAvailable`)
- **On-demand command**: `/scrape` in group chat → fetches only articles NOT in `seen.json` → sends "Fresh Updates" to group
- **Bot listener**: `bot_listener.py` long-polls Telegram for commands; runs as "Robotics Digest Listener" scheduled task (at log on, restarts on failure)
- **Format**: One cohesive AI-written digest (newsletter style), not individual headlines
- **Summarizer**: `claude` CLI via subprocess — company OAuth subscription (Roboverse Reply GmbH), no API credits needed
- **Hosting**: Local Windows PC — Ana's machine is the designated runner
- **Deduplication**: `seen.json` tracks sent URLs for 7 days; nothing is sent twice
- **Article cap**: 140 articles per run

---

## File Structure

```
robotics-digest/
├── main.py              # Orchestrator: fetch → dedup → summarize → send; --on-demand flag
├── fetcher.py           # Concurrent RSS + Hacker News fetching (ThreadPoolExecutor)
├── browser_fetcher.py   # Scrapes companies with no RSS (concurrent, ThreadPoolExecutor)
├── sources.py           # All feed URLs and scrape targets — edit this to add sources
├── dedup.py             # seen.json load/save/prune — atomic writes via os.replace()
├── summarizer.py        # Calls claude CLI via subprocess → Telegram-ready digest
├── telegram_bot.py      # POST to Telegram Bot API + chat ID helper
├── bot_listener.py      # Long-polls Telegram for /scrape commands → triggers --on-demand
├── setup.ps1            # One-time Windows setup script for new team members
├── README.md            # Teammate onboarding doc (join group vs self-host)
├── seen.json            # Auto-created; persists sent article URLs (7-day window)
├── digest.log           # Auto-created; rotating log — check here when things go wrong
├── .env                 # TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID + CLAUDE_BIN
├── .env.example         # Template showing required keys
├── .gitignore           # Excludes .env, seen.json, digest.log, __pycache__
├── requirements.txt     # feedparser, requests, beautifulsoup4, python-dotenv
└── docs/                # Detailed project insights (see below)
    ├── agent-sessions.md       # Log of all agent analysis sessions
    └── code-review-2026-04-15.md  # Full code review findings + fix status
```

---

## Setup Walkthrough

### New teammate (self-host)

1. Install Python 3.10+ from [python.org](https://python.org) — **not** Microsoft Store
2. Install [Claude Code](https://claude.ai/download), sign in with Roboverse Reply account
3. Enable PowerShell scripts (once per machine):
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
4. Run setup as **Administrator**:
   ```powershell
   cd path\to\robotics-digest
   .\setup.ps1
   ```
   Setup auto-detects Python, installs deps, creates `.env`, writes `CLAUDE_BIN`, registers the 9:30 AM task.
5. Fill in `.env` with bot token + chat ID (ask Ana)
6. Test: `python main.py --dry-run`
7. Send real test: `python main.py --force`

### Just want to read the digest?

Ask Ana for the Telegram group invite link. No setup needed.

### Recreate scheduled task manually

```powershell
$ScriptDir = "C:\path\to\robotics-digest"
$action = New-ScheduledTaskAction -Execute (Get-Command python).Source -Argument "main.py" -WorkingDirectory $ScriptDir
$trigger = New-ScheduledTaskTrigger -Daily -At "09:30AM"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "Robotics Digest" -Action $action -Trigger $trigger -Settings $settings -Force
```

---

## News Sources (verified 2026-04-15)

### RSS Feeds
| Source | URL | Category |
|--------|-----|----------|
| The Robot Report | therobotreport.com/feed/ | industry |
| IEEE Spectrum | spectrum.ieee.org/rss/fulltext | industry |
| TechCrunch Robotics | techcrunch.com/category/robotics/feed/ | industry |
| NVIDIA Robotics Blog | blogs.nvidia.com/blog/category/robotics/feed/ | big_player |
| Boston Dynamics | bostondynamics.com/feed/ | big_player |
| arXiv cs.RO | arxiv.org/rss/cs.RO | research |
| Reddit r/robotics | reddit.com/r/robotics/top/.rss?t=day | community |

### Scraped Sites (no RSS)
| Company | Listing URL | Link prefix | Category |
|---------|------------|-------------|----------|
| Figure AI | figure.ai/news | /news/ | big_player |
| Unitree | unitree.com/news | /news/ | big_player |
| 1X Technologies | 1x.tech/discover | /discover/ | emerging |
| Sanctuary AI | sanctuary.ai/blog | /blog/ | emerging |
| Physical Intelligence | pi.website/blog | /blog/, /research/ | emerging |
| Apptronik | apptronik.com/press-release | /news-collection/ | emerging |

### Other
- **Hacker News** — Algolia API, "robotics" query, last 24h

### Removed sources (broken as of 2026-04-15)
| Source | Reason |
|--------|--------|
| MIT News Robotics | 404 |
| Wired Robotics | Blocked |
| New Atlas Robotics | 404 |
| Universal Robots Blog | DNS failure |
| ABB Robotics News | Timeout |
| Agility Robotics | Rebranded to agility.ai (DNS unreachable) |
| Gecko Robotics | 404 |

### How to add a source

RSS feed:
```python
# sources.py → RSS_FEEDS
{"name": "Company", "url": "https://example.com/feed/", "category": "emerging"}
```

No RSS (scraped):
```python
# sources.py → SCRAPE_TARGETS
{"name": "Company", "listing_url": "https://example.com/blog",
 "base_url": "https://example.com", "link_prefix": "/blog/",
 "category": "emerging", "max_articles": 10}
```

Valid categories: `industry`, `big_player`, `emerging`, `research`, `community`

---

## CLI Options

| Command | Effect |
|---------|--------|
| `python main.py` | Normal run: fetch → summarize → send |
| `python main.py --dry-run` | Print digest to terminal, don't send, don't update seen.json |
| `python main.py --force` | Skip dedup, send all fetched articles |
| `python main.py --on-demand` | Send only articles not in seen.json; "no new articles" message if empty |
| `python bot_listener.py` | Start command listener (normally managed by Task Scheduler) |
| `/scrape` (in Telegram group) | Triggers `--on-demand` run via bot_listener.py |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `.\setup.ps1` blocked | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` first |
| Microsoft Store Python error in setup | Uninstall from Store, install from python.org |
| `claude CLI not found` error | Re-run `setup.ps1` after installing Claude Code — it writes `CLAUDE_BIN` to `.env` |
| `claude: not logged in` | Run `claude auth login`, sign in with Roboverse Reply account |
| Task Scheduler fires but nothing arrives | **Check `digest.log`** in the project folder — every run is logged there |
| Digest not arriving | Check `digest.log`; verify `TELEGRAM_CHAT_ID` is correct (group IDs are negative) |
| Wrong chat receiving digest | Run `python -c "from telegram_bot import get_chat_id; get_chat_id('TOKEN')"` to find group ID |
| Empty digest | Run `--force` to bypass dedup; check `digest.log` for errors |
| Multiple digests per day | Only one runner at a time — tell Ana if you set up your own copy |
| `load_dotenv` not picking up `.env` | `override=True` is already set; check working directory |
| Scraped source returns 0 articles | Site structure changed — check `link_prefix` in `SCRAPE_TARGETS` |
| seen.json corrupted / articles re-sending | Delete `seen.json` and run again; it will rebuild |

---

## Installed Claude Code Agents

Agents live in `C:\Users\a.lacatusu\Desktop\Claude\LabCamp\.claude\agents\`

| Agent | Use for | Sessions |
|-------|---------|---------|
| `code-reviewer` | Code quality, security, best practices | [2026-04-15](./docs/agent-sessions.md) |
| `python-pro` | Python idioms, type safety, concurrency | [2026-04-15](./docs/agent-sessions.md) |
| `devops-engineer` | Deployment, scheduling, infra, setup scripts | [2026-04-15](./docs/agent-sessions.md) |
| `fullstack-developer` | Building features end-to-end | — |
| `debugger` | Tracking down errors | — |

**How to invoke:** Ask Claude to use a specific agent, e.g. _"use the code-reviewer agent to review browser_fetcher.py"_

---

## Detailed Docs

| File | Contents |
|------|----------|
| [`docs/agent-sessions.md`](./docs/agent-sessions.md) | Log of every agent session: task, findings, changes made |
| [`docs/code-review-2026-04-15.md`](./docs/code-review-2026-04-15.md) | Full code review findings, fix status (open/closed), code snippets |

---

## Enhancements Discussed (not yet implemented)

- **Skills**: `/add-source`, `/check-feeds`, `/show-stats`, `/test-digest`
- **Hooks**: Validate `sources.py` after edits; log run timestamps
- **TypedDict for articles**: Define `Article` TypedDict in `models.py` for type safety across modules
- **Pinned requirements**: `pip freeze > requirements-lock.txt` for reproducible installs
- **File lock for dedup**: `filelock` around `seen.json` read/write for true multi-runner safety
- **Crunchbase API**: Funding rounds for robotics startups
- **Cloud hosting**: Move off local PC for 24/7 reliability (devops-engineer agent can help)
- **Re-check broken sources**: Agility Robotics (agility.ai), Gecko Robotics — may work from cloud
