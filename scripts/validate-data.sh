#!/usr/bin/env bash
# Validate NDJSON data files are well-formed JSON (one object per line).
# Usage: ./scripts/validate-data.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ERRORS=0

validate_jsonl() {
  local file="$1"
  local label="$2"
  if [ ! -f "$file" ]; then
    echo "SKIP: $label ($file not found)"
    return
  fi
  if [ ! -s "$file" ]; then
    echo "OK:   $label (empty file)"
    return
  fi
  local line_count
  line_count=$(wc -l < "$file")
  if jq -e '.' "$file" > /dev/null 2>&1; then
    # jq succeeded on whole file -- but for NDJSON we need per-line validation
    :
  fi
  local bad_lines
  bad_lines=$(while IFS= read -r line; do
    echo "$line" | jq -e '.' > /dev/null 2>&1 || echo "bad"
  done < "$file" | wc -l)
  bad_lines=$(echo "$bad_lines" | tr -d ' ')
  if [ "$bad_lines" -eq 0 ]; then
    echo "OK:   $label ($line_count lines, all valid JSON)"
  else
    echo "FAIL: $label ($bad_lines of $line_count lines are invalid JSON)"
    ERRORS=$((ERRORS + 1))
  fi
}

validate_jsonl "$REPO_ROOT/data/feed.jsonl" "Activity feed"
validate_jsonl "$REPO_ROOT/data/tasks/active.jsonl" "Active tasks"

# Validate all triage run files
for f in "$REPO_ROOT"/data/triage/*.jsonl; do
  [ -f "$f" ] || continue
  validate_jsonl "$f" "Triage: $(basename "$f")"
done

if [ "$ERRORS" -gt 0 ]; then
  echo ""
  echo "VALIDATION FAILED: $ERRORS file(s) have invalid JSON lines."
  exit 1
else
  echo ""
  echo "All data files valid."
fi
