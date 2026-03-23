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

# Compile latest briefing -> docs/briefing.json
LATEST_BRIEFING=$(ls -t "$REPO_ROOT/data/briefings/"*.md 2>/dev/null | head -1 || true)
if [ -n "$LATEST_BRIEFING" ] && [ -s "$LATEST_BRIEFING" ]; then
  # Extract briefing metadata from the corresponding feed entry
  BRIEFING_DATE=$(basename "$LATEST_BRIEFING" .md)
  # Find the briefing feed entry for this date
  jq -s "[.[] | select(.type==\"briefing\" and (.ts | startswith(\"${BRIEFING_DATE}\")))] | if length > 0 then .[0] else null end" "$REPO_ROOT/data/feed.jsonl" > "$REPO_ROOT/docs/briefing.json"
  # If no feed entry found, create a minimal JSON with the file path
  if [ "$(cat "$REPO_ROOT/docs/briefing.json")" = "null" ]; then
    echo "{\"briefing_file\": \"${LATEST_BRIEFING}\", \"date\": \"${BRIEFING_DATE}\"}" > "$REPO_ROOT/docs/briefing.json"
  fi
  echo "Built docs/briefing.json (from ${BRIEFING_DATE})"
else
  echo "null" > "$REPO_ROOT/docs/briefing.json"
  echo "Built docs/briefing.json (empty -- no briefing data yet)"
fi

# Compile active todos -> docs/todos.json
if [ -s "$REPO_ROOT/data/todos/active.jsonl" ]; then
  jq -s '.' "$REPO_ROOT/data/todos/active.jsonl" > "$REPO_ROOT/docs/todos.json"
  echo "Built docs/todos.json ($(jq length "$REPO_ROOT/docs/todos.json") entries)"
else
  echo "[]" > "$REPO_ROOT/docs/todos.json"
  echo "Built docs/todos.json (empty -- no active todos)"
fi

# Compile active invoices -> docs/invoices.json
if [ -s "$REPO_ROOT/data/invoices/active.jsonl" ]; then
  jq -s '.' "$REPO_ROOT/data/invoices/active.jsonl" > "$REPO_ROOT/docs/invoices.json"
  echo "Built docs/invoices.json ($(jq length "$REPO_ROOT/docs/invoices.json") entries)"
else
  echo "[]" > "$REPO_ROOT/docs/invoices.json"
  echo "Built docs/invoices.json (empty -- no invoice data yet)"
fi

echo "Dashboard data build complete."
