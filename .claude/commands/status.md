---
description: Quick summary of current Agend Ops state
allowed-tools: Read, Bash(jq *), Bash(wc *), Bash(ls *), Bash(tail *)
---

Show a quick status summary for Agend Ops:

1. **Recent Activity:** Read last 5 entries from `data/feed.jsonl` using:
   ```bash
   tail -n 5 data/feed.jsonl | jq -s '.'
   ```
   Display each entry with timestamp, type, and summary.

2. **Triage Runs:** List files in `data/triage/` sorted by date (most recent first):
   ```bash
   ls -t data/triage/*.jsonl 2>/dev/null | head -5
   ```
   Show the most recent triage run timestamp and email count.

3. **Pending Tasks:**

   a. Count total pending:
      ```bash
      jq -r 'select(.status=="pending")' data/tasks/active.jsonl 2>/dev/null | jq -s 'length'
      ```

   b. Count by trigger:
      - Triage-suggested:
        ```bash
        jq -r 'select(.status=="pending" and .trigger=="triage-suggestion")' data/tasks/active.jsonl 2>/dev/null | jq -s 'length'
        ```
      - Manual:
        ```bash
        jq -r 'select(.status=="pending" and .trigger=="manual")' data/tasks/active.jsonl 2>/dev/null | jq -s 'length'
        ```

   c. Top 3 pending tasks with description and task_type:
      ```bash
      jq -r 'select(.status=="pending") | "- [\(.id)] \(.description) (\(.task_type // "untyped"))"' data/tasks/active.jsonl 2>/dev/null | head -3
      ```

   d. Completed today:
      ```bash
      TODAY=$(date +%Y-%m-%d)
      jq -r "select(.status==\"completed\" and (.completed_at // \"\" | startswith(\"$TODAY\")))" data/tasks/active.jsonl 2>/dev/null | jq -s 'length'
      ```

   e. Display format:
      ```
      Pending Tasks: {N} ({N} from triage, {N} manual)
      - [task-id] description (type)
      - [task-id] description (type)
      - [task-id] description (type)
      Completed today: {N}
      ```

4. **Dashboard Actions:**
   Check `data/queue/actions.jsonl` for queued entries:

   ```bash
   if [ -f data/queue/actions.jsonl ] && [ -s data/queue/actions.jsonl ]; then
     jq -s '[.[] | select(.status == "queued")]' data/queue/actions.jsonl
   else
     echo "[]"
   fi
   ```

   Report pending action count:
   - If pending actions exist: "{N} pending dashboard actions" followed by a brief list:
     ```
     Dashboard Actions: {N} pending
     - mark-paid: {target_id}
     - complete-todo: {target_id}
     Run /process-queue to execute pending actions.
     ```
   - If no pending actions: "No pending dashboard actions"

5. **System Health:** Confirm hardened-workspace MCP server is available.

Format output as a clean, scannable summary with counts and timestamps.
If any data file is empty or missing, report "No data yet" for that section.
