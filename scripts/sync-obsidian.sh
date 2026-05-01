#!/usr/bin/env bash
# Sync Obsidian vault-build/ from data/ NDJSON history.
# Usage:
#   bash scripts/sync-obsidian.sh                              # default: --mode incremental
#   bash scripts/sync-obsidian.sh --backfill                   # full regenerate from history
#   bash scripts/sync-obsidian.sh --incremental                # explicit incremental (subject to no-op-delta guard)
#   bash scripts/sync-obsidian.sh --incremental --record-id X  # hooks may pass record-id (v1 ignores)
#   bash scripts/sync-obsidian.sh --dry-run                    # print what would change, write nothing
#
# Concurrency: flock advisory lock on scripts/.vault-sync.lock per D-13/Pattern 9.
# On lock contention, fail loudly with exit code 1 (caller's responsibility to retry).
# All paths that mutate vault-build/ go through this wrapper.
#
# PORTABILITY (Issue 7): this wrapper REQUIRES util-linux's `flock`. macOS does
# NOT ship flock by default. On Mac, invoke vault_writer.py directly:
#     python3 -m scripts.lib.vault_writer --mode incremental \
#         --build-root "$REPO/vault-build" --data-root "$REPO/data"
# See mac/README.md (Plan 04) for the canonical Mac instructions.
set -euo pipefail

# ----- Issue 7: portability guard -----
if ! command -v flock >/dev/null 2>&1; then
  echo "scripts/sync-obsidian.sh requires util-linux's flock (Coolify/Linux only)." >&2
  echo "On Mac, invoke vault_writer directly: python3 -m scripts.lib.vault_writer --mode <mode>" >&2
  echo "See mac/README.md for the canonical macOS instructions." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK_FILE="$REPO_ROOT/scripts/.vault-sync.lock"
DATA_ROOT="$REPO_ROOT/data"
BUILD_ROOT="$REPO_ROOT/vault-build"

# Parse first positional flag — translate --backfill / --incremental into --mode for python.
# Capture --dry-run separately so we can decide whether to bypass the no-op guard.
# All other flags pass through unchanged.
MODE="incremental"
DRY_RUN=0
EXTRA_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --backfill)     MODE="backfill"; shift ;;
    --incremental)  MODE="incremental"; shift ;;
    --mode)         MODE="$2"; shift 2 ;;
    --dry-run)      DRY_RUN=1; EXTRA_ARGS+=("$1"); shift ;;
    *)              EXTRA_ARGS+=("$1"); shift ;;
  esac
done

# ----- Issue 3: no-op-delta guard (only for --mode incremental, NOT --dry-run, NOT --backfill) -----
# Read-only slash-command modes (e.g. /task list, /task show-queue) invoke this wrapper
# but produce no NDJSON changes. Without this guard, every read-only invocation would
# rebuild vault-build/ and create empty no-op commits. Compare the most recent NDJSON
# mtime under the data/ directories we read against the most recent last_synced timestamp
# parsed out of vault-build/Clients/*.md. If no deltas, exit 0 silently.
if [ "$MODE" = "incremental" ] && [ "$DRY_RUN" -eq 0 ]; then
  # Most recent NDJSON modification under the data/ dirs vault_writer reads.
  # Use Linux GNU stat (Coolify-only by Issue 7's portability guard above).
  LAST_DATA_MTIME=0
  for sub in triage tasks invoices todos config; do
    if [ -d "$DATA_ROOT/$sub" ]; then
      while IFS= read -r f; do
        t=$(stat -c %Y "$f" 2>/dev/null || echo 0)
        if [ "$t" -gt "$LAST_DATA_MTIME" ]; then
          LAST_DATA_MTIME=$t
        fi
      done < <(find "$DATA_ROOT/$sub" -type f \( -name '*.jsonl' -o -name '*.json' \) 2>/dev/null)
    fi
  done

  # Most recent last_synced timestamp parsed out of vault-build/Clients/*.md
  # (epoch seconds). If vault-build/ has no notes yet (first run before backfill),
  # fall through and let the real backfill run.
  LAST_SYNCED_EPOCH=0
  if [ -d "$BUILD_ROOT/Clients" ]; then
    while IFS= read -r line; do
      # Strip 'last_synced: ' prefix; expect ISO 8601 with TZ offset
      ts=${line#last_synced: }
      ts=${ts%$'\r'}
      # H3: ruamel.yaml may emit timestamps wrapped in single or double quotes.
      # Strip both so `date -d` parses cleanly instead of silently falling back to 0.
      ts=${ts//[\"\']/}
      # Convert ISO 8601 -> epoch via GNU date (Coolify/Linux)
      epoch=$(date -d "$ts" +%s 2>/dev/null || echo 0)
      if [ "$epoch" -gt "$LAST_SYNCED_EPOCH" ]; then
        LAST_SYNCED_EPOCH=$epoch
      fi
    done < <(grep -h '^last_synced: ' "$BUILD_ROOT"/Clients/*.md 2>/dev/null || true)
  fi

  # H2: Clock-skew defense. Future-dated last_synced (server clock drift, FS
  # mount with bad clock, copying notes between machines) would otherwise make
  # LAST_SYNCED_EPOCH > LAST_DATA_MTIME forever, silently dropping all updates
  # until real time catches up. Cap the parsed value to "now" before comparing.
  CURRENT_EPOCH=$(date +%s)
  if [ "$LAST_SYNCED_EPOCH" -gt "$CURRENT_EPOCH" ]; then
    echo "scripts/sync-obsidian.sh: last_synced ($LAST_SYNCED_EPOCH) is in the future; capping to now ($CURRENT_EPOCH). Investigate clock sources." >&2
    LAST_SYNCED_EPOCH=$CURRENT_EPOCH
  fi

  # If vault-build was synced AFTER the most recent NDJSON change, this is a no-op.
  # (>= so equal timestamps also short-circuit; mtimes have 1-second resolution.)
  if [ "$LAST_SYNCED_EPOCH" -gt 0 ] && [ "$LAST_SYNCED_EPOCH" -ge "$LAST_DATA_MTIME" ]; then
    # Silent no-op: read-only invocations should not produce log spam either.
    # Print a single line to stderr so a human running directly sees what happened.
    echo "scripts/sync-obsidian.sh: no NDJSON deltas since last sync ($(date -d "@$LAST_SYNCED_EPOCH" -Iseconds 2>/dev/null || echo "$LAST_SYNCED_EPOCH")); exiting 0." >&2
    exit 0
  fi
fi

# ----- Acquire lock; wait up to 30s. If we don't get it, abort. -----
exec 9>"$LOCK_FILE"
if ! flock --timeout 30 9; then
  echo "ERROR: another vault-sync is in progress; aborting after 30s wait." >&2
  exit 1
fi

# vault_writer's main() handles its own try/except and writes to data/feed.jsonl on failure.
# We exec into it so the lock fd inherits and is released on the python process's exit.
exec /usr/bin/env python3 -m scripts.lib.vault_writer \
  --mode "$MODE" \
  --data-root "$DATA_ROOT" \
  --build-root "$BUILD_ROOT" \
  "${EXTRA_ARGS[@]}"
