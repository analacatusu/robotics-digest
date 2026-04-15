# Robotics Digest Bot

Daily AI-written robotics news briefing delivered to Telegram every morning at 11:30 AM.
Covers big players (Boston Dynamics, NVIDIA, Figure AI, Unitree), emerging startups, and research.
Powered by Claude AI via the Roboverse Reply company subscription — no API credits needed.

---

## Just Want to Read the Digest?

**Ask Ana for the Telegram group invite link.** Join the group and you'll receive the digest automatically every morning. No setup, no accounts, no code required.

---

## Bot Commands (in the group)

| Command | What it does |
|---------|-------------|
| `/scrape` | Fetches articles that arrived **after** this morning's digest and sends them to the group. Only new content — nothing already in the morning digest. |

The bot listener (`bot_listener.py`) runs as a background task on Ana's machine and processes these commands.

---

## Setting Up a New Telegram Group

If you need to create a new group or migrate to a different one:

1. Open Telegram → tap the pencil icon → **New Group**
2. Add the bot by searching for its username (e.g. `@RoboticsDigest_bot`) and any team members
3. Make the bot an **admin** — it needs permission to post messages:
   Group Settings → Administrators → Add Administrator → find the bot → confirm
4. Send any message in the group (e.g. `/start`) to generate an update
5. Get the group chat ID:
   ```powershell
   python -c "from telegram_bot import get_chat_id; get_chat_id('YOUR_BOT_TOKEN')"
   ```
   Look for the entry with `Type: supergroup` — the ID is a **negative number**
6. Update `.env`:
   ```
   TELEGRAM_CHAT_ID=-1001234567890
   ```
7. Test: `python main.py --force`

---

## Run Your Own Copy (Optional)

Follow these steps if you want the bot to run on your own machine — useful as a backup runner, or if you want to experiment with adding custom sources.

### Prerequisites

- Windows 10/11
- **Python 3.10+** from [python.org](https://python.org) — **not** the Microsoft Store version (it is sandboxed and breaks Task Scheduler)
- **[Claude Code](https://claude.ai/download)** installed and signed in with your Roboverse Reply account
  - Verify: open a terminal and run `claude --version`
- Bot token + group chat ID — ask Ana

### Quick Setup

**Step 1** — Allow PowerShell scripts (one-time, per machine). Open PowerShell and run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Step 2** — Run setup as **Administrator** (required for Task Scheduler registration):
```powershell
cd path\to\robotics-digest
.\setup.ps1
```

The script will:
- Verify Python and the `claude` CLI
- Install Python dependencies (`pip install -r requirements.txt`)
- Create your `.env` file from the template and prompt you to fill in credentials
- Register a daily 9:30 AM Windows Task Scheduler task

### Manual Setup

If you prefer to set things up yourself:

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create credentials file
copy .env.example .env
# Open .env in a text editor and fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# 3. Test — prints digest to terminal, does NOT send to Telegram
python main.py --dry-run

# 4. Send a real test
python main.py --force

# 5. Register the scheduled task (run as Administrator)
$ScriptDir = (Get-Location).Path
$action = New-ScheduledTaskAction -Execute (Get-Command python).Source -Argument "main.py" -WorkingDirectory $ScriptDir
$trigger = New-ScheduledTaskTrigger -Daily -At "09:30AM"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "Robotics Digest" -Action $action -Trigger $trigger -Settings $settings -Force
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `.\setup.ps1` blocked with "running scripts is disabled" | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` first |
| `claude CLI not found` | Open a **new** terminal after installing Claude Code; verify with `claude --version`. `setup.ps1` auto-writes `CLAUDE_BIN` to `.env` — re-run it after installing Claude Code |
| `claude: not logged in` | Run `claude auth login` and sign in with your Roboverse Reply account |
| Task Scheduler fires but nothing arrives | Check `digest.log` in the project folder for the full error. Also open Task Scheduler → "Robotics Digest" → "Last Run Result" |
| `/scrape` command does nothing | Check `listener.log` — the listener may have crashed. Restart it: `Start-ScheduledTask -TaskName 'Robotics Digest Listener'` |
| Bot listener keeps crashing | Check `listener.log` for the error. Common cause: bad `.env` values or network issue |
| Digest not arriving | Check `digest.log` — it logs every run with timestamps. Also verify `.env` has the correct `TELEGRAM_CHAT_ID` (group IDs are negative numbers) |
| Bot sends to wrong chat | Run `python -c "from telegram_bot import get_chat_id; get_chat_id('YOUR_TOKEN')"` to list all chats and confirm the group chat ID |
| Empty digest / 0 articles | Run `python main.py --force` to bypass dedup; check `digest.log` for errors |
| Multiple digests per day | **Only one person should run the bot.** If you set up your own copy, tell Ana so the team has one designated runner. Multiple runners each send a separate digest to the group |
| Microsoft Store Python error | Uninstall Python from the Windows Store and install from [python.org](https://python.org) |

---

## How It Works

```
sources.py           → defines RSS feeds and scrape targets (edit here to add sources)
fetcher.py           → fetches RSS + Hacker News concurrently (ThreadPoolExecutor)
browser_fetcher.py   → scrapes company sites with no RSS feed (requests + BeautifulSoup)
dedup.py             → filters already-sent URLs via seen.json (7-day rolling window)
summarizer.py        → calls 'claude' CLI to write a cohesive digest
telegram_bot.py      → POSTs the digest to the Telegram group
main.py              → orchestrates all of the above
```

Runs are deduped: the same article will never appear in two consecutive digests.

---

## Adding a News Source

Open `sources.py`. For an RSS feed:
```python
# RSS_FEEDS list
{"name": "Company Name", "url": "https://example.com/feed/", "category": "emerging"}
```

For a site with no RSS:
```python
# SCRAPE_TARGETS list
{"name": "Company Name", "listing_url": "https://example.com/blog",
 "base_url": "https://example.com", "link_prefix": "/blog/",
 "category": "emerging", "max_articles": 10}
```

Valid categories: `industry`, `big_player`, `emerging`, `research`, `community`.

---

## CLI Reference

| Command | Effect |
|---------|--------|
| `python main.py` | Normal run: fetch → summarize → send |
| `python main.py --dry-run` | Print digest to terminal, do not send |
| `python main.py --force` | Skip dedup, send all fetched articles |
| `python main.py --on-demand` | Send only articles not yet in seen.json (used by `/scrape` command) |
| `python bot_listener.py` | Start the command listener manually (normally runs as a scheduled task) |

---

## Files

| File | Purpose |
|------|---------|
| `.env` | Your credentials — never committed to git |
| `.env.example` | Template — copy to `.env` |
| `seen.json` | Auto-created; tracks sent article URLs for 7 days |
| `digest.log` | Auto-created; rotating log file — check this for morning digest failures |
| `listener.log` | Auto-created; rotating log file — check this for `/scrape` command failures |
| `setup.ps1` | One-time Windows setup script |
| `requirements.txt` | Python package dependencies |
| `CLAUDE.md` | Full project context for Claude Code agents |
