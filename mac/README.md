# Mac Studio Vault Sync Daemon

Phase 10 deliverable: a launchd LaunchAgent that watches `vault-build/` for git pulls and projects managed-section content into the iCloud canonical Obsidian vault.

## What it does

1. The Coolify server commits `vault-build/Clients/*.md` after every triage / task / invoice mutation, then pushes via `bash scripts/push-and-sync.sh`.
2. The Mac Studio runs `git pull --ff-only` every 60s (cron, see below).
3. fswatch (running under launchd) detects the file changes from the pull.
4. The watcher invokes `python3 -m scripts.lib.vault_writer --mode project-to-icloud` directly (NOT the bash wrapper — see below), which splices managed sections from `vault-build/` into `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AgendOps/Clients/`.
5. Apple's `bird`/`cloudd` daemon uploads to iCloud; iPhone Obsidian sees the changes within seconds.

SLA target: <30s end-to-end from Coolify commit to iPhone visibility.

## Do NOT call scripts/sync-obsidian.sh on Mac (Issue 7)

`scripts/sync-obsidian.sh` is the Coolify (Linux) wrapper. It requires util-linux's `flock`, which is NOT installed by default on macOS, AND it includes a portability guard that aborts loud-fast when flock is missing.

On Mac, invoke vault_writer directly (using the virtual environment created by the installer):

```bash
cd /Users/glenr/work/agend-ops
.venv/bin/python3 -m scripts.lib.vault_writer --mode incremental \
  --build-root "$PWD/vault-build" \
  --data-root "$PWD/data"
```

For projection (vault-build/ → iCloud), use:

```bash
.venv/bin/python3 -m scripts.lib.vault_writer --mode project-to-icloud \
  --build-root "$PWD/vault-build" \
  --data-root "$PWD/data"
```

The fswatch watcher script (`mac/vault-sync-watcher.sh`) already invokes vault_writer directly — you don't need to do anything special during normal operation. This note is for ad-hoc debugging.

## One-time install

Run on the Mac Studio that hosts the always-on git clone:

```bash
cd /Users/glenr/work/agend-ops
bash mac/install-daemon.sh
```

The installer is idempotent; re-running is safe.

**What the installer does:**
1. Installs `fswatch` via Homebrew (if missing)
2. Creates a Python virtual environment at `.venv/` in the repo root
3. Installs Python dependencies (`ruamel.yaml`) into the virtual environment
4. Installs the LaunchAgent plist to `~/Library/LaunchAgents/`
5. Loads and starts the daemon

### Verify Installation

After running the installer, verify everything is working:

```bash
# Check daemon is running
launchctl list | grep com.agend.vault-sync
# Expected output: PID, exit-code (0), label
# Example: 29541	0	com.agend.vault-sync

# Check fswatch process is active
ps aux | grep fswatch | grep -v grep
# Should show: /opt/homebrew/bin/fswatch -o --latency 2 /Users/glenr/work/agend-ops/vault-build

# Test manual sync (should complete without errors)
cd /Users/glenr/work/agend-ops
.venv/bin/python3 -m scripts.lib.vault_writer --mode project-to-icloud \
  --build-root "$PWD/vault-build" --data-root "$PWD/data"
# Expected output: vault_writer project-to-icloud complete: {...}
```

## Configure git pull cadence (cron)

The daemon watches `vault-build/` for filesystem changes; something needs to drive the changes by pulling from GitHub. Add a cron entry that pulls every 60s:

```bash
# Open cron editor
crontab -e

# Add this line:
* * * * * cd /Users/glenr/work/agend-ops && /usr/bin/git pull --ff-only --quiet 2>>/Users/glenr/Library/Logs/agend-git-pull.err.log

# Save and exit. cron picks up the new entry on next minute boundary.
```

### Verify Cron

After saving the crontab:

```bash
# Verify crontab entry
crontab -l
# Should show: * * * * * cd /Users/glenr/work/agend-ops && /usr/bin/git pull...

# Check cron daemon is running
ps aux | grep cron | grep -v grep
# Should show: root ... /usr/sbin/cron

# Wait 1-2 minutes, then check error log (should be empty if working)
ls -lh ~/Library/Logs/agend-git-pull.err.log
# Size should be 0B (no errors)

# Verify git status (should be up to date)
git status -sb
# Should show: ## master...origin/master
```

Defensive notes:
- Use `--ff-only` so a divergent local branch fails loud rather than auto-merging.
- If the local clone ever has stray uncommitted changes in `vault-build/` (shouldn't happen — the daemon only writes to iCloud, not back to vault-build/), the pull will fail. Fix by running: `cd /Users/glenr/work/agend-ops && git checkout -- vault-build/ && git pull --ff-only`.

## iCloud Optimize Mac Storage warning (Pitfall 2)

iCloud's "Optimize Mac Storage" feature can evict the canonical vault's files from local disk and replace them with `.icloud` placeholders. The daemon includes defensive `brctl download` retries (3× with 2s wait) but is NOT fully resilient to all eviction scenarios.

Recommended setting: in the Obsidian app on the Mac Studio, after creating the AgendOps vault under iCloud Drive, control-click the `AgendOps` folder in Finder and choose **Keep Downloaded**. This pins the folder to local disk regardless of "Optimize Mac Storage".

Alternative: System Settings → Apple ID → iCloud → iCloud Drive → Optimize Mac Storage = OFF (affects all iCloud Drive content, not just the vault).

## Manual trigger

To force a projection without waiting for fswatch:

```bash
cd /Users/glenr/work/agend-ops
.venv/bin/python3 -m scripts.lib.vault_writer --mode project-to-icloud \
  --build-root "$PWD/vault-build" --data-root "$PWD/data"
```

Use `--dry-run` first to see what would change. Per Issue 5, `--dry-run` is strictly read-only — no brctl invocations, no file writes, no feed-entry appends.

## Troubleshooting

Logs:
- `~/Library/Logs/agend-vault-sync.log` — stdout (fswatch event lines)
- `~/Library/Logs/agend-vault-sync.err.log` — stderr (Python tracebacks, marker-error ABORT messages)
- `~/Library/Logs/agend-git-pull.err.log` — cron pull errors
- `data/feed.jsonl` — system/critical entries from vault_writer.py (marker integrity ABORTs)

Daemon status:
```bash
launchctl list | grep com.agend.vault-sync
```
Expect a line like `42 0 com.agend.vault-sync` (PID, last-exit-status, label).

Daemon stopped or repeatedly crashing:
- Check `agend-vault-sync.err.log` for the failure reason.
- Common: fswatch not on PATH (try `brew reinstall fswatch`).
- Common: Python import error (re-run `bash mac/install-daemon.sh` to recreate the virtual environment).

To force-reload after editing the plist:
```bash
bash mac/install-daemon.sh
```

To uninstall:
```bash
launchctl unload ~/Library/LaunchAgents/com.agend.vault-sync.plist
rm ~/Library/LaunchAgents/com.agend.vault-sync.plist
# Cron pull entry: edit `crontab -e` and remove the line.
```

## Orphan client notes

If a client is removed from `data/config/clients.jsonl`, the corresponding `vault-build/Clients/<slug>.md` becomes orphaned. The daemon does NOT auto-delete from iCloud — Glen must `git rm` from the repo manually if cleanup is desired. Auto-deletion is intentionally out of scope for v1 because Glen may have heavily edited the Overview section and silent loss of that content is dangerous.

## Why fswatch and not WatchPaths?

Apple's `launchd.plist(5)` man page explicitly says: "Use of WatchPaths is highly discouraged, as filesystem event monitoring is highly race-prone, and modifications may be missed entirely, with no guarantee that the file will be in a consistent state when the job is launched."

fswatch wraps Apple's FSEvents API correctly and (combined with `KeepAlive=true`) is the standard solution for reliable filesystem-driven launch agents on macOS.

## Complete Setup Checklist

Use this checklist to verify the entire sync pipeline is operational:

### Step 1: Install the Daemon
```bash
cd /Users/glenr/work/agend-ops
bash mac/install-daemon.sh
```

**Verify:**
- ✅ Virtual environment created at `.venv/`
- ✅ `ruamel.yaml` installed in venv
- ✅ LaunchAgent loaded and running

```bash
# Quick check:
launchctl list | grep vault-sync && echo "✅ Daemon running"
ps aux | grep fswatch | grep -v grep && echo "✅ fswatch active"
```

### Step 2: Configure Cron
```bash
crontab -e
# Add: * * * * * cd /Users/glenr/work/agend-ops && /usr/bin/git pull --ff-only --quiet 2>>/Users/glenr/Library/Logs/agend-git-pull.err.log
```

**Verify:**
```bash
crontab -l | grep agend-ops && echo "✅ Cron configured"
ps aux | grep cron | grep -v grep && echo "✅ cron daemon running"
# Wait 1-2 minutes
ls -lh ~/Library/Logs/agend-git-pull.err.log && echo "✅ Git pull executing"
```

### Step 3: Configure iCloud
In Finder, locate `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AgendOps/`
- Right-click the `AgendOps` folder
- Select "Keep Downloaded"

**Verify:**
```bash
ls -la ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/AgendOps/Clients/
# Should show client .md files, not .icloud placeholders
```

### Step 4: End-to-End Test
1. On the Coolify server (or locally), make a test change and push:
   ```bash
   echo "Test update $(date)" >> vault-build/Clients/test-client.md
   git add vault-build/Clients/test-client.md
   git commit -m "Test: vault sync"
   git push
   ```

2. On Mac Studio, verify the pipeline:
   ```bash
   # Within 60s: cron pulls the change
   git log -1 --oneline  # Should show the test commit
   
   # Within 5s: fswatch detects the change and syncs to iCloud
   cat ~/Library/Logs/agend-vault-sync.log  # Should show fswatch events
   
   # Check iCloud has the update
   grep "Test update" ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/AgendOps/Clients/test-client.md
   ```

3. On iPhone, open Obsidian → AgendOps vault → Clients folder
   - The test-client.md should show the update within ~30 seconds

**Success criteria:**
- ✅ Git pull happens every minute
- ✅ fswatch detects vault-build/ changes
- ✅ Changes appear in iCloud within seconds
- ✅ iPhone Obsidian shows updates within 30s total
- ✅ No errors in any log files

### Common Issues
| Symptom | Check | Fix |
|---------|-------|-----|
| "ModuleNotFoundError: No module named 'ruamel'" | Using system Python instead of venv | Use `.venv/bin/python3` not `python3` |
| Daemon not running | Check `~/Library/Logs/agend-vault-sync.err.log` | Re-run `bash mac/install-daemon.sh` |
| Git not pulling | Check crontab with `crontab -l` | Re-add cron entry |
| iCloud files are `.icloud` placeholders | Optimize Mac Storage evicted files | Right-click folder → Keep Downloaded |
| Changes not syncing | Check fswatch is running | `ps aux | grep fswatch` |
