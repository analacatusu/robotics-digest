# Code Review — 2026-04-15

Full findings from the agent-assisted code review before internal team release.
Agents: `code-reviewer` + `python-pro` + `devops-engineer`

**Status: All CRITICAL and HIGH findings fixed. Medium/Low remain open.**

---

## CRITICAL / HIGH — Fixed ✅

### dedup.py — Non-atomic write (CRITICAL)

**Finding:** `SEEN_FILE.write_text(...)` truncates then writes. Crash mid-write → partial JSON → silent reset to `{}` → entire team gets duplicate digests.

**Fix applied:** Write to `.tmp` then `os.replace()` (atomic on NTFS same drive).

```python
def _save(data: dict[str, str]) -> None:
    tmp = SEEN_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, SEEN_FILE)
```

---

### setup.ps1 — PowerShell 5.1 crash (CRITICAL)

**Finding:** `?.Source` null-conditional operator requires PS7. Corporate Windows ships PS5.1. Script aborts before doing anything.

**Fix applied:** Replaced with `if ($claudeCmd) { $claudeCmd.Source } else { $null }`.

---

### setup.ps1 — `claude` not on PATH in Task Scheduler (CRITICAL)

**Finding:** Task Scheduler uses minimal system PATH; user-local `~/.local/bin` is not included. `claude` is found in interactive sessions but not in the scheduled task. Silent failure every morning.

**Fix applied:** `setup.ps1` now auto-writes `CLAUDE_BIN=<detected path>` into `.env` after finding `claude`. `summarizer.py` reads `CLAUDE_BIN` from env first.

---

### main.py — No log file (CRITICAL)

**Finding:** `logging.basicConfig` writes to stdout only. Task Scheduler discards stdout. Failures are completely invisible — user sees only NTSTATUS code in Task Scheduler.

**Fix applied:** Added `RotatingFileHandler` → `digest.log` (max 500KB, 3 backups) alongside stdout.

---

### telegram_bot.py — Token in exception messages (HIGH)

**Finding:** `requests.RequestException` message includes the full URL (with token). Any log, crash report, or Windows Event Viewer entry exposes the token.

**Fix applied:**
```python
safe_msg = str(exc).replace(token, "<REDACTED>")
raise RuntimeError(f"Telegram request failed: {safe_msg}") from exc
```

---

### telegram_bot.py — Bare KeyError on missing env vars (HIGH)

**Finding:** `os.environ["TELEGRAM_BOT_TOKEN"]` raises `KeyError` with no useful message when `.env` isn't loaded.

**Fix applied:** Changed to `os.environ.get()` with explicit `RuntimeError` check.

---

### fetcher.py — Broken double-timeout logic (HIGH)

**Finding:** `as_completed(futures, timeout=60)` raises `TimeoutError` if the iterator isn't exhausted in 60s — could abort the entire RSS fetch. The inner `future.result(timeout=PER_FEED_TIMEOUT)` was effectively dead code since `as_completed` only yields already-finished futures.

**Fix applied:** Removed outer timeout from `as_completed`. Collect results after `executor.__exit__` (which waits for all workers). Real per-request timeout is already enforced by `requests.get(timeout=10)`.

---

### summarizer.py — Hardcoded developer path + unhandled exceptions (HIGH)

**Finding 1:** `CLAUDE_BIN` fell back to `C:\Users\a.lacatusu\.local\bin\claude.exe` — wrong for every teammate, committed to source.

**Fix applied:** Removed fallback. Now raises `EnvironmentError` if neither env var nor `shutil.which()` finds `claude`.

**Finding 2:** `FileNotFoundError` and `subprocess.TimeoutExpired` surfaced as generic exceptions with no actionable message.

**Fix applied:** Explicit `except subprocess.TimeoutExpired` and `except FileNotFoundError` with clear messages pointing to `claude auth status` / `CLAUDE_BIN`.

---

## MEDIUM — Open 🟡

### requirements.txt — Unpinned versions

`>=` bounds mean different team members may get different package versions over time. Risk of breaking changes (e.g. feedparser 7.x API changes).

**Recommended fix:** `pip freeze > requirements-lock.txt` after a known-good install, or switch `>=` to `~=` (compatible release).

### dedup.py — No multi-process lock

Two runners posting to the same group would produce two digests and race on `seen.json`. Currently honor-system ("one runner"). For v2, add `filelock` around load/save.

### summarizer.py — Prompt injection via article fields

Titles/snippets from RSS feeds go directly into the Claude prompt. A malicious feed could embed instructions. Partially addressed by newline-stripping (applied); full mitigation would require clearly delimited article blocks.

---

## LOW / SUGGESTIONS — Open 🟢

### fetcher.py:100 — Old `%d` formatting style
```python
# Was:
"numericFilters": "created_at_i>%d" % int(...)
# Better:
"numericFilters": f"created_at_i>{int(datetime.now(timezone.utc).timestamp() - 86400)}",
```

### All files — No TypedDict for article dicts
Article dicts (`title`, `url`, `snippet`, `source`, `category`, `published`) are passed as untyped `dict`. A `TypedDict` would catch typos at static analysis time and help teammates who extend sources.

### setup.ps1 — No Python version check for Anaconda users
If a colleague uses Anaconda without activating the right environment, `pip install` goes into the wrong env. README note added; could be enforced in script.

### main.py:72 — Redundant dedup branch
Was `if not dry_run and not force: ... elif force and not dry_run: ...` (both resolved to `if not dry_run`). Fixed to single branch.
