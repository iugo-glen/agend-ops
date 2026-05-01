#!/usr/bin/env bash
# Idempotent installer for the Agend Ops vault-sync LaunchAgent.
# Usage: bash mac/install-daemon.sh
#
# What this does (each step is idempotent):
#   1. Verifies fswatch is installed; installs via Homebrew if missing.
#   2. Verifies ruamel.yaml is installed; installs via pip3 if missing.
#   3. Copies mac/com.agend.vault-sync.plist to ~/Library/LaunchAgents/ if not already in place.
#   4. Reloads the LaunchAgent (unload-then-load) so changes to the plist or watcher take effect.
#   5. Verifies the daemon is running.
#
# Re-running this script is safe.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_NAME="com.agend.vault-sync.plist"
PLIST_SRC="$REPO_ROOT/mac/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
LOG_DIR="$HOME/Library/Logs"

echo "==> Step 1: fswatch"
if ! command -v fswatch >/dev/null 2>&1; then
  echo "fswatch not found; installing via Homebrew..."
  if ! command -v brew >/dev/null 2>&1; then
    echo "ERROR: Homebrew not found. Install from https://brew.sh and re-run." >&2
    exit 1
  fi
  brew install fswatch
else
  echo "fswatch present: $(fswatch --version | head -1)"
fi

echo "==> Step 2: Python deps"
if ! python3 -c "import ruamel.yaml" 2>/dev/null; then
  echo "ruamel.yaml not found; installing via pip3..."
  pip3 install -r "$REPO_ROOT/scripts/requirements.txt"
else
  echo "ruamel.yaml present"
fi

echo "==> Step 3: install plist"
mkdir -p "$LOG_DIR"
mkdir -p "$(dirname "$PLIST_DEST")"
if [ ! -f "$PLIST_DEST" ] || ! cmp -s "$PLIST_SRC" "$PLIST_DEST"; then
  cp "$PLIST_SRC" "$PLIST_DEST"
  echo "Installed plist: $PLIST_DEST"
else
  echo "Plist already up to date: $PLIST_DEST"
fi

echo "==> Step 4: ensure watcher script is executable"
chmod +x "$REPO_ROOT/mac/vault-sync-watcher.sh"

echo "==> Step 5: reload LaunchAgent (unload-then-load is idempotent)"
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load -w "$PLIST_DEST"

echo "==> Step 6: verify"
sleep 1
if launchctl list | grep -q com.agend.vault-sync; then
  echo "OK: com.agend.vault-sync is loaded."
  echo "Logs: $LOG_DIR/agend-vault-sync.log + agend-vault-sync.err.log"
else
  echo "WARN: launchctl list does not show com.agend.vault-sync. Check $LOG_DIR/agend-vault-sync.err.log" >&2
  exit 1
fi

echo ""
echo "Daemon installed. Next step: configure the git-pull cadence — see mac/README.md §Cron."
