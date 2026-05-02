#!/bin/bash
# fswatch wrapper for the vault-sync LaunchAgent.
# Pitfall 5: keep trivial; macOS Bash 3.2 has no associative arrays.
#
# Issue 7: this script invokes vault_writer.py DIRECTLY rather than going through
# the Coolify wrapper (scripts/sync-obsidian dot sh), which requires util-linux
# flock and is therefore Linux-only. On Mac, single-writer discipline is provided
# by KeepAlive=true on the LaunchAgent (one daemon at a time). See mac/README.md.
set -euo pipefail
REPO=/Users/glenr/work/agend-ops
cd "$REPO"

# Use Python from virtual environment
PYTHON="$REPO/.venv/bin/python3"

# fswatch -o emits one line per batch; --latency 2 coalesces 2-second windows.
exec /opt/homebrew/bin/fswatch -o --latency 2 "$REPO/vault-build" \
  | xargs -n1 -I{} "$PYTHON" -m scripts.lib.vault_writer \
      --mode project-to-icloud \
      --build-root "$REPO/vault-build" \
      --data-root "$REPO/data"
