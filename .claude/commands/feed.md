---
description: Show recent activity feed entries
allowed-tools: Read, Bash(jq *), Bash(tail *), Bash(wc *)
---

Display the most recent activity feed entries from data/feed.jsonl.

Default: last 10 entries. If $ARGUMENTS contains a number, show that many entries.

Steps:
1. Determine count: parse $ARGUMENTS for a number, default to 10
2. Read entries: `tail -n {count} data/feed.jsonl`
3. Parse each line as JSON
4. Format each entry showing:
   - Timestamp (formatted as relative time if today, absolute date otherwise)
   - Type icon: triage=inbox, task=checkbox, draft=pencil, system=gear, command=terminal
   - Summary text
   - Level (only show if "critical")
5. Group by date if entries span multiple days

If data/feed.jsonl is empty or does not exist, display "No activity recorded yet."
