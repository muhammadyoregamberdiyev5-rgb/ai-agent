---
name: hermes-memory-github-sync
description: Set up automatic GitHub sync for Hermes Agent memory, skills, and config using git + macOS launchd. Runs every 30 minutes in the background. Covers repo init, .gitignore pitfalls, token extraction, and launchd plist setup.
tags: [hermes, memory, github, sync, launchd, macos, backup]
---

# Hermes Memory GitHub Sync (macOS)

Automatically backs up `~/.hermes/memories/`, `~/.hermes/skills/`, and `~/.hermes/config.yaml` to a private GitHub repo every 30 minutes via launchd.

## Key Pitfalls (Learned from Experience)

- **NEVER use `git add -A`** inside `~/.hermes` — it will stage 10,000+ files from `.venv/` and `hermes-agent/`
- **Always use explicit paths**: `git add memories/ skills/ config.yaml SOUL.md .gitignore`
- The `hermes-agent/` subdirectory is a nested git repo — must be in `.gitignore`
- The `.venv/` virtual environment is huge — must be in `.gitignore`
- GitHub token is already stored in `~/.git-credentials` — no need to create a new one

---

## Step 1: Extract GitHub Token

```bash
TOKEN=$(grep github ~/.git-credentials | sed 's/.*:\(ghp_[^@]*\)@.*/\1/')
echo "Token: ${TOKEN:0:10}..."
```

## Step 2: Create Private GitHub Repo via API

```bash
curl -s -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user/repos \
  -d '{"name":"hermes-memory","private":true,"description":"Hermes Agent memory sync"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('clone_url','ERROR:'+str(d.get('message',d))))"
```

## Step 3: Init Git Repo in ~/.hermes

```bash
cd ~/.hermes
git init
git config user.name "yourname"
git config user.email "your@email.com"
git remote add origin "https://USERNAME:${TOKEN}@github.com/USERNAME/hermes-memory.git"
```

## Step 4: Create .gitignore

Write to `~/.hermes/.gitignore`:

```gitignore
# Large directories — DO NOT sync
.venv/
hermes-agent/
sessions/
logs/
cron/
plugins/
__pycache__/

# Temp / sensitive files
*.lock
*.log
*.db
*.db-shm
*.db-wal
.env
auth.json
.DS_Store
.update_check
.hermes_history
.skills_prompt_snapshot.json
```

## Step 5: First Commit & Push

```bash
cd ~/.hermes
# IMPORTANT: use explicit paths, not git add -A
git add .gitignore memories/ skills/ config.yaml SOUL.md
git status --short | wc -l   # should be ~400-500 files, not 10000+
git commit -m "init: sync memories, skills and config"
git branch -M main
git push -u origin main
```

## Step 6: Create Sync Script

Write to `~/.hermes/hermes-sync.sh`:

```bash
#!/bin/bash
set -euo pipefail

HERMES_DIR="$HOME/.hermes"
LOG_FILE="$HERMES_DIR/logs/hermes-sync.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

mkdir -p "$HERMES_DIR/logs"
cd "$HERMES_DIR"

if [ ! -d ".git" ]; then
    echo "[$DATE] ERROR: not a git repo" >> "$LOG_FILE"
    exit 1
fi

# Stage only the important files
git add memories/ skills/ config.yaml SOUL.md .gitignore 2>/dev/null || true

# Skip if nothing changed
if git diff --cached --quiet; then
    echo "[$DATE] 没有变化，跳过提交" >> "$LOG_FILE"
    exit 0
fi

git commit -m "sync: auto backup at $DATE" >> "$LOG_FILE" 2>&1

if git push origin main >> "$LOG_FILE" 2>&1; then
    echo "[$DATE] 推送成功" >> "$LOG_FILE"
else
    echo "[$DATE] 推送失败（网络问题？），下次再试" >> "$LOG_FILE"
    exit 0
fi

# Keep log file small
tail -500 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
```

```bash
chmod +x ~/.hermes/hermes-sync.sh
```

## Step 7: Create launchd Plist

Write to `~/Library/LaunchAgents/com.USERNAME.hermes-sync.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.USERNAME.hermes-sync</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/USERNAME/.hermes/hermes-sync.sh</string>
    </array>

    <!-- Every 30 minutes -->
    <key>StartInterval</key>
    <integer>1800</integer>

    <!-- Run once immediately on load -->
    <key>RunAtLoad</key>
    <true/>

    <!-- PATH is required or git won't be found -->
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
        <key>HOME</key>
        <string>/Users/USERNAME</string>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/USERNAME/.hermes/logs/hermes-sync-launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/USERNAME/.hermes/logs/hermes-sync-launchd.log</string>

    <key>ThrottleInterval</key>
    <integer>60</integer>
</dict>
</plist>
```

## Step 8: Load & Verify

```bash
launchctl load ~/Library/LaunchAgents/com.USERNAME.hermes-sync.plist

# Check it's running (should show com.USERNAME.hermes-sync)
launchctl list | grep hermes

# Wait a few seconds, check the log
sleep 5 && cat ~/.hermes/logs/hermes-sync.log
```

Expected output: `[2026-04-10 17:21:05] 没有变化，跳过提交` (or a push success message)

---

## Management Commands

```bash
# View sync log
cat ~/.hermes/logs/hermes-sync.log

# Manually trigger sync now
~/.hermes/hermes-sync.sh

# Stop the service
launchctl unload ~/Library/LaunchAgents/com.USERNAME.hermes-sync.plist

# Reload after editing plist
launchctl unload ~/Library/LaunchAgents/com.USERNAME.hermes-sync.plist
launchctl load ~/Library/LaunchAgents/com.USERNAME.hermes-sync.plist

# Check what's tracked in git
cd ~/.hermes && git status --short
```

## Notes

- The launchd service **survives reboots** automatically (it's in `LaunchAgents/`, not `LaunchDaemons/`)
- If git push fails (no network), the script exits cleanly and retries next cycle
- Token is embedded in the remote URL — if token rotates, update with:
  ```bash
  cd ~/.hermes && git remote set-url origin "https://USERNAME:NEW_TOKEN@github.com/USERNAME/hermes-memory.git"
  ```
- To sync a second Mac: `git clone https://USERNAME:TOKEN@github.com/USERNAME/hermes-memory.git ~/.hermes` then set up the same launchd service
