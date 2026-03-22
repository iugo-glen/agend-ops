---
description: Quick summary of current Agend Ops state
allowed-tools: Read, Bash(jq *), Bash(wc *), Bash(ls *), Bash(tail *)
---

Show a quick status summary for Agend Ops:

1. Recent Activity: Read last 5 entries from data/feed.jsonl using `tail -n 5 data/feed.jsonl | jq -s '.'`
2. Triage Runs: List files in data/triage/ sorted by date (most recent first) using `ls -t data/triage/*.jsonl 2>/dev/null | head -5`
3. Pending Tasks: Count entries with status "pending" in data/tasks/active.jsonl using `jq -r 'select(.status=="pending")' data/tasks/active.jsonl 2>/dev/null | wc -l`
4. System Health: Confirm hardened-workspace MCP server is available

Format output as a clean, scannable summary with counts and timestamps.
If any data file is empty or missing, report "No data yet" for that section.
