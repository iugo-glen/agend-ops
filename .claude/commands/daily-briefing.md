---
description: Generate daily morning briefing from existing data
allowed-tools: Read, Bash(jq *), Bash(date *), Bash(wc *), Bash(ls *), Bash(tail *), Bash(cat *), Bash(mkdir *), Write, Edit, Bash(git *), Bash(bash scripts/*)
---

Compile the daily morning briefing from existing Agend Ops data. This command reads feed, triage, and task data to produce a formatted briefing file, logs a feed entry, rebuilds dashboard data, and commits.

## Execution

1. **Determine trigger context:**
   Check whether this is running inside a GitHub Actions workflow or manually:
   ```bash
   if [ -n "${GITHUB_ACTIONS:-}" ]; then
     echo "TRIGGER=scheduled"
   else
     echo "TRIGGER=manual"
   fi
   ```
   Use `"scheduled"` for the feed entry trigger if running in CI, `"manual"` otherwise. Store this for step 5.

2. **Check if briefing already exists for today:**
   ```bash
   TODAY=$(date +%Y-%m-%d)
   if [ -f "data/briefings/${TODAY}.md" ]; then
     echo "BRIEFING_EXISTS"
   fi
   ```
   If the file exists, read and display its contents, then stop. Do NOT regenerate.

3. **Ensure briefings directory exists:**
   ```bash
   mkdir -p data/briefings
   ```

4. **Compile four briefing sections:**

   a. **Email Summary** -- Read the most recent triage file:
      ```bash
      LATEST_TRIAGE=$(ls -t data/triage/*.jsonl 2>/dev/null | head -1 || true)
      ```
      If a triage file exists, use jq to extract:
      - Total emails scanned: `jq -s 'length' "$LATEST_TRIAGE"`
      - Counts by priority bucket:
        ```bash
        jq -s '[.[] | .priority] | group_by(.) | map({(.[0]): length}) | add' "$LATEST_TRIAGE"
        ```
        Map to buckets: urgent, needs-response, informational, low-priority
      - Starred items (sender + subject):
        ```bash
        jq -r 'select(.starred == true) | "  - \(.from) -- \(.subject)"' "$LATEST_TRIAGE"
        ```

      If no triage file exists, note "No triage data available."

   b. **Pending Tasks** -- Read active tasks:
      ```bash
      jq -r 'select(.status=="pending")' data/tasks/active.jsonl 2>/dev/null | jq -s '.'
      ```
      List pending tasks grouped by trigger:
      - Triage-suggested: `select(.trigger=="triage-suggestion")`
      - Manual: `select(.trigger=="manual")`

      For each task, include: task ID, description, and task_type. If no pending tasks, note "No pending tasks."

   c. **Key Deadlines (Next 48 Hours)** -- Scan recent triage records for action items with deadlines:
      Look at triage files from the last 48 hours:
      ```bash
      CUTOFF=$(date -v-2d +%Y-%m-%d 2>/dev/null || date -d "2 days ago" +%Y-%m-%d)
      ```
      From recent triage files, extract records where `action_type` includes "deadline", "contract", or "meeting":
      ```bash
      jq -r 'select(.action_type != null and (.action_type | test("deadline|contract|meeting"))) | "  - \(.action_items[0] // .subject) -- from \(.from)"' data/triage/*.jsonl 2>/dev/null
      ```
      For each match, show the action item description and sender. If none found, note "No upcoming deadlines detected."

   d. **Yesterday Recap** -- Read yesterday's feed entries:
      ```bash
      YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
      jq -r "select(.ts | startswith(\"${YESTERDAY}\"))" data/feed.jsonl 2>/dev/null | jq -s '.'
      ```
      Summarize from the feed entries:
      - Number of triage runs: `select(.type=="triage") | length`
      - Emails scanned: sum of `.details.emails_scanned` from triage entries
      - Tasks completed: `select(.type=="task" and (.summary | test("completed|done"))) | length`
      - Drafts created: `select(.type=="draft") | length`
      - Any errors: `select(.level=="critical")` -- if any, note them

      If no entries for yesterday, note "No activity recorded yesterday."

5. **Write briefing file** to `data/briefings/${TODAY}.md` using this format:

   ```
   # Daily Briefing: {YYYY-MM-DD}

   ## Email Summary
   - {N} emails scanned in latest triage
   - Urgent: {N} | Needs Response: {N} | Informational: {N} | Low: {N}
   - Starred:
     - {sender} -- {subject}

   ## Pending Tasks
   - {N} pending ({N} from triage, {N} manual)
   - [{task-id}] {description} ({task_type})

   ## Key Deadlines (Next 48 Hours)
   - {deadline description} -- from {sender}
   (or "No upcoming deadlines detected.")

   ## Yesterday Recap
   - {N} triage runs, {N} emails scanned
   - {N} tasks completed
   - {N} drafts created
   (or "No activity recorded yesterday.")
   ```

6. **Log briefing to feed** -- Append a feed entry to `data/feed.jsonl`:
   Use the trigger value determined in step 1 (either `"scheduled"` or `"manual"`).
   ```json
   {
     "ts": "{ISO 8601 with timezone offset, e.g. 2026-03-24T07:00:00+10:30}",
     "type": "briefing",
     "summary": "Daily briefing: {N} emails ({N} urgent), {N} pending tasks, {N} deadlines in next 48h",
     "level": "info",
     "trigger": "{scheduled or manual}",
     "details": {
       "briefing_file": "data/briefings/{TODAY}.md",
       "emails_scanned": {N},
       "urgent": {N},
       "pending_tasks": {N},
       "deadlines_48h": {N}
     }
   }
   ```
   Append as a single line to `data/feed.jsonl` using jq compact output (`jq -c`).

7. **Rebuild dashboard data and commit:**
   ```bash
   bash scripts/build-dashboard-data.sh
   git add data/briefings/ data/feed.jsonl docs/feed.json docs/briefing.json docs/tasks.json docs/triage.json
   git commit -m "data: generate daily briefing for ${TODAY}"
   ```
   If the commit fails (nothing changed), continue without error.

8. **Display the briefing** -- Read and output the generated briefing file so Glen can scan it immediately.
