<#
.SYNOPSIS
    One-time setup for the Robotics Digest Bot on Windows.
    Run from the robotics-digest\ directory as Administrator (for Task Scheduler).

.USAGE
    # If scripts are blocked, first run (once per machine):
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

    # Then run setup:
    cd path\to\robotics-digest
    .\setup.ps1
#>

$ErrorActionPreference = "Stop"
# $MyInvocation.MyCommand.Path is always set when run as .\setup.ps1
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "=== Robotics Digest Bot — Setup ===" -ForegroundColor Cyan
Write-Host ""

# ── [1/5] Python ───────────────────────────────────────────────────────────
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow

$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    Write-Error "Python not found. Install from https://python.org and ensure it is on PATH."
    exit 1
}

$pythonPath = $pyCmd.Source

# Detect Microsoft Store Python stub — it is sandboxed and does not work in Task Scheduler
if ($pythonPath -like "*WindowsApps*") {
    Write-Host "      ERROR: Microsoft Store Python detected." -ForegroundColor Red
    Write-Host "      Path: $pythonPath" -ForegroundColor Red
    Write-Host "      Store Python is sandboxed and will silently fail in Task Scheduler." -ForegroundColor Red
    Write-Host "      Install Python from https://python.org instead, then re-run this script." -ForegroundColor Red
    exit 1
}

# Validate Python >= 3.10
$pyVersionRaw = & python --version 2>&1
if ($pyVersionRaw -match "Python (\d+)\.(\d+)") {
    $pyMajor = [int]$Matches[1]
    $pyMinor = [int]$Matches[2]
    if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 10)) {
        Write-Error "Python 3.10+ required. Found: $pyVersionRaw. Install a newer version from https://python.org."
        exit 1
    }
    Write-Host "      Found: $pyVersionRaw ($pythonPath)" -ForegroundColor Green
} else {
    Write-Host "      WARNING: Could not parse Python version from: $pyVersionRaw" -ForegroundColor Yellow
}

# ── [2/5] Dependencies ────────────────────────────────────────────────────
Write-Host "[2/5] Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install -r "$ScriptDir\requirements.txt" --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install failed. Run manually: python -m pip install -r requirements.txt"
    exit 1
}
Write-Host "      Done." -ForegroundColor Green

# ── [3/5] Claude CLI ──────────────────────────────────────────────────────
Write-Host "[3/5] Checking for claude CLI..." -ForegroundColor Yellow

# Compatible with PowerShell 5.1 and 7+ (avoid ?. null-conditional operator)
$claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
$claudePath = if ($claudeCmd) { $claudeCmd.Source } else { $null }

if ($claudePath) {
    Write-Host "      Found: $claudePath" -ForegroundColor Green
} else {
    Write-Host "      WARNING: 'claude' not found on PATH." -ForegroundColor Red
    Write-Host "      Install Claude Code: https://claude.ai/download" -ForegroundColor Red
    Write-Host "      After installing, open a new terminal and re-run this script." -ForegroundColor Yellow
    Write-Host "      Continuing — you can also set CLAUDE_BIN manually in .env after setup." -ForegroundColor Gray
}

# ── [4/5] .env ────────────────────────────────────────────────────────────
Write-Host "[4/5] Checking .env..." -ForegroundColor Yellow
$envFile = "$ScriptDir\.env"
if (Test-Path $envFile) {
    Write-Host "      .env already exists — skipping creation." -ForegroundColor Green
} else {
    Copy-Item "$ScriptDir\.env.example" $envFile
    Write-Host "      Created .env from .env.example" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  *** ACTION REQUIRED ***" -ForegroundColor Red
    Write-Host "  Open $envFile in a text editor and fill in:" -ForegroundColor Red
    Write-Host "    TELEGRAM_BOT_TOKEN  — ask Ana" -ForegroundColor Red
    Write-Host "    TELEGRAM_CHAT_ID    — ask Ana (the group chat ID, a negative number)" -ForegroundColor Red
    Write-Host ""
    Read-Host "  Press Enter once you have saved .env to continue"
}

# Auto-write CLAUDE_BIN into .env so Task Scheduler can find claude
# (Task Scheduler runs with a minimal PATH that often excludes user-local installs)
if ($claudePath) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -notmatch "(?m)^CLAUDE_BIN=.+") {
        # Append or replace the commented-out CLAUDE_BIN line
        $escapedPath = $claudePath -replace "\\", "\\"
        if ($envContent -match "(?m)^#\s*CLAUDE_BIN=") {
            $envContent = $envContent -replace "(?m)^#\s*CLAUDE_BIN=.*", "CLAUDE_BIN=$claudePath"
            $envContent | Set-Content $envFile -NoNewline
        } else {
            Add-Content $envFile "`nCLAUDE_BIN=$claudePath"
        }
        Write-Host "      Wrote CLAUDE_BIN=$claudePath to .env" -ForegroundColor Green
        Write-Host "      (ensures Task Scheduler finds claude regardless of PATH)" -ForegroundColor Gray
    } else {
        Write-Host "      CLAUDE_BIN already set in .env — skipping." -ForegroundColor Green
    }
}

# ── [5/5] Task Scheduler ──────────────────────────────────────────────────
Write-Host "[5/5] Registering Windows Task Scheduler task..." -ForegroundColor Yellow
$taskName = "Robotics Digest"
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    $overwrite = Read-Host "      Task '$taskName' already exists. Overwrite? (y/N)"
    if ($overwrite -notin @('y', 'Y')) {
        Write-Host "      Skipped Task Scheduler registration." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "=== Setup complete (Task Scheduler skipped) ===" -ForegroundColor Cyan
        Write-Host "  Test:  python main.py --dry-run"
        Write-Host "  Send:  python main.py --force"
        Write-Host ""
        exit 0
    }
}

$action = New-ScheduledTaskAction `
    -Execute $pythonPath `
    -Argument "main.py" `
    -WorkingDirectory $ScriptDir

$trigger = New-ScheduledTaskTrigger -Daily -At "11:30AM"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Daily robotics news digest via Claude AI to Telegram" `
    -Force | Out-Null

Write-Host "      Registered — runs daily at 11:30 AM (StartWhenAvailable)." -ForegroundColor Green
Write-Host "      Verify: open Task Scheduler → Task Scheduler Library → confirm 'Robotics Digest' shows Status: Ready" -ForegroundColor Gray

# ── [6/6] Bot listener task (at log on, runs continuously) ────────────────
Write-Host "[6/6] Registering bot listener task (at log on)..." -ForegroundColor Yellow
$listenerTaskName = "Robotics Digest Listener"
$existingListener = Get-ScheduledTask -TaskName $listenerTaskName -ErrorAction SilentlyContinue
$registerListener = $true
if ($existingListener) {
    $overwriteListener = Read-Host "      Task '$listenerTaskName' already exists. Overwrite? (y/N)"
    if ($overwriteListener -notin @('y', 'Y')) {
        Write-Host "      Skipped listener task registration." -ForegroundColor Yellow
        $registerListener = $false
    }
}

if ($registerListener) {
    $listenerAction = New-ScheduledTaskAction `
        -Execute $pythonPath `
        -Argument "bot_listener.py" `
        -WorkingDirectory $ScriptDir

    $listenerTrigger = New-ScheduledTaskTrigger -AtLogOn

    $listenerSettings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit ([System.TimeSpan]::Zero) `
        -RestartCount 10 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -MultipleInstances IgnoreNew

    Register-ScheduledTask `
        -TaskName $listenerTaskName `
        -Action $listenerAction `
        -Trigger $listenerTrigger `
        -Settings $listenerSettings `
        -Description "Robotics Digest — polls Telegram for /scrape commands" `
        -Force | Out-Null

    Write-Host "      Registered — starts at log on, restarts on failure." -ForegroundColor Green
    Write-Host "      To start now without rebooting:" -ForegroundColor Gray
    Write-Host "        Start-ScheduledTask -TaskName 'Robotics Digest Listener'" -ForegroundColor Gray
}

# ── Done ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Verify your .env has TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID filled in."
Write-Host "  2. Test (prints digest to terminal, no Telegram send):"
Write-Host "       python main.py --dry-run"
Write-Host "  3. Send a real test message to the group:"
Write-Host "       python main.py --force"
Write-Host "  4. Start the bot listener now (or it starts automatically on next login):"
Write-Host "       Start-ScheduledTask -TaskName 'Robotics Digest Listener'"
Write-Host "  5. Test /scrape in the group — send the command and watch for a reply."
Write-Host "  6. If something goes wrong, check digest.log and listener.log in this folder."
Write-Host ""
