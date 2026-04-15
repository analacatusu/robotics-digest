# Agent Session Log

Record of Claude Code agent sessions run on this project — what was asked, what was found, and what changed.

---

## 2026-04-15 — Internal Team Release Review

**Task:** Analyze code and the internal release plan before sharing with the Roboverse Reply team.

**Agents used:** `code-reviewer`, `python-pro`, `devops-engineer`

**Trigger:** User ran `/save` then asked agents to review code + release plan.

### code-reviewer findings (8 files reviewed)

Full findings → [`code-review-2026-04-15.md`](./code-review-2026-04-15.md)

**Verdict:** BLOCK — 4 CRITICAL/HIGH issues before team release.

Top issues:
- `dedup.py` non-atomic write → `seen.json` corruption on crash
- `telegram_bot.py` token leaking into exception messages
- `telegram_bot.py` bare `KeyError` on missing env vars
- `requirements.txt` unpinned deps (`>=` bounds)

### python-pro findings

Top issues:
- `fetcher.py` broken double-timeout: `as_completed(timeout=60)` outer timeout could abort entire RSS fetch; the inner `future.result(timeout=12)` was effectively dead code
- `summarizer.py` `FileNotFoundError` / `TimeoutExpired` not explicitly caught
- `dedup.py` non-atomic write (same as code-reviewer finding)
- `browser_fetcher.py` sequential scraping — up to 90s worst case with 6 targets × 15s timeout

### devops-engineer findings

Top issues:
- `setup.ps1` used `?.Source` null-conditional operator — **crashes on PowerShell 5.1** (default on Windows)
- `claude` not on PATH in Task Scheduler context — silent failure with no log
- No log file — Task Scheduler stdout is discarded; failures completely invisible
- Microsoft Store Python is sandboxed and breaks scheduled tasks
- PowerShell execution policy (`Restricted`) not documented as prerequisite

### Fixes applied in session

All CRITICAL and HIGH findings were implemented immediately:

| File | Change |
|------|--------|
| `dedup.py` | Atomic write via temp file + `os.replace()` |
| `dedup.py` | `_prune()` guards against malformed/empty date strings |
| `telegram_bot.py` | Token redacted from exception messages |
| `telegram_bot.py` | Helpful `RuntimeError` on missing env vars |
| `summarizer.py` | Removed hardcoded dev username path; hard `EnvironmentError` if claude not found |
| `summarizer.py` | Explicit `TimeoutExpired` + `FileNotFoundError` handling |
| `summarizer.py` | Logs full stderr before raising; explicit `cwd` |
| `summarizer.py` | Newline-strips article fields to prevent prompt injection |
| `fetcher.py` | Removed outer `as_completed(timeout=60)`; collect after executor shuts down |
| `fetcher.py` | Removed `Optional` import; uses `str \| None` (Python 3.10+) |
| `browser_fetcher.py` | Concurrent scraping with `ThreadPoolExecutor(max_workers=6)` |
| `browser_fetcher.py` | `resp.apparent_encoding` for charset detection |
| `browser_fetcher.py` | `href.strip()` to prevent URL construction bugs |
| `browser_fetcher.py` | Typed `prefix: str \| list[str]` |
| `main.py` | `RotatingFileHandler` → `digest.log` (Task Scheduler failures now visible) |
| `main.py` | Simplified `mark_sent` logic to single `if not dry_run` |
| `setup.ps1` | PS5.1-compatible `claudeCmd` detection |
| `setup.ps1` | Auto-writes `CLAUDE_BIN` to `.env` (solves Task Scheduler PATH issue) |
| `setup.ps1` | Detects Microsoft Store Python and aborts with clear message |
| `setup.ps1` | Python 3.10+ version validation |
| `setup.ps1` | Explicit exit code check on `pip install` |
| `.gitignore` | Added `digest.log`, `*.bak`, test artifacts |
| `README.md` | PowerShell execution policy prerequisite added |
| `README.md` | Updated troubleshooting; added `digest.log` reference |

---

## 2026-04-15 — Initial Build

**Task:** Build the entire robotics-digest bot from scratch.

**Agents used:** Built directly (no subagents).

**What was built:**
- Full pipeline: RSS fetch → scrape → dedup → Claude CLI summarize → Telegram send
- 7 RSS feeds, 6 scraped sites, Hacker News
- Windows Task Scheduler setup at 9:30 AM
- `seen.json` 7-day dedup
- `--dry-run` and `--force` CLI flags
- `.claude/commands/save.md` skill
- `.claude/settings.json` Stop hook
- 5 agent templates installed via `claude-code-templates`

**Key problems solved:**
- `feedparser` hanging → switched to `requests.get()` first, then pass content
- Anthropic API 400 error → switched from SDK to `claude` CLI subprocess (company OAuth)
- Windows CLI length limit → pass prompt via stdin
- Windows emoji encode error → `sys.stdout.buffer.write()`
- Task Scheduler `schtasks` failing in Git Bash → switched to PowerShell `Register-ScheduledTask`
