#!/usr/bin/env bash
# Compile NDJSON data files into JSON for GitHub Pages dashboard consumption.
# Usage: ./scripts/build-dashboard-data.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Compile feed.jsonl -> docs/feed.json (last 100 entries for dashboard)
if [ -s "$REPO_ROOT/data/feed.jsonl" ]; then
  tail -n 100 "$REPO_ROOT/data/feed.jsonl" | jq -s '.' > "$REPO_ROOT/docs/feed.json"
  echo "Built docs/feed.json ($(wc -l < "$REPO_ROOT/docs/feed.json") lines)"
else
  echo "[]" > "$REPO_ROOT/docs/feed.json"
  echo "Built docs/feed.json (empty -- no feed data yet)"
fi

# Compile active tasks -> docs/tasks.json
if [ -s "$REPO_ROOT/data/tasks/active.jsonl" ]; then
  jq -s '.' "$REPO_ROOT/data/tasks/active.jsonl" > "$REPO_ROOT/docs/tasks.json"
  echo "Built docs/tasks.json ($(jq length "$REPO_ROOT/docs/tasks.json") entries)"
else
  echo "[]" > "$REPO_ROOT/docs/tasks.json"
  echo "Built docs/tasks.json (empty -- no active tasks)"
fi

# Compile latest triage run -> docs/triage.json
LATEST_TRIAGE=$(ls -t "$REPO_ROOT/data/triage/"*.jsonl 2>/dev/null | head -1)
if [ -n "$LATEST_TRIAGE" ] && [ -s "$LATEST_TRIAGE" ]; then
  jq -s '.' "$LATEST_TRIAGE" > "$REPO_ROOT/docs/triage.json"
  TRIAGE_COUNT=$(jq 'length' "$REPO_ROOT/docs/triage.json")
  echo "Built docs/triage.json ($TRIAGE_COUNT entries from $(basename "$LATEST_TRIAGE"))"
else
  echo "[]" > "$REPO_ROOT/docs/triage.json"
  echo "Built docs/triage.json (empty -- no triage data yet)"
fi

echo "Dashboard data build complete."
