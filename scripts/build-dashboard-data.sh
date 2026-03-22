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

echo "Dashboard data build complete."
