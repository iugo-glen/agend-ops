---
description: Create or manage a task
allowed-tools: Read, Write, Edit, Bash(jq *), Bash(date *), Bash(wc *)
---

Create a new task record from the description: $ARGUMENTS

If arguments are provided:
1. Generate a task ID: task-{YYYY-MM-DD}-{NNN} where NNN is zero-padded sequence based on count of existing entries for today in data/tasks/active.jsonl
2. Get current timestamp in ISO 8601 with timezone offset (e.g., 2026-03-23T10:45:00+10:00)
3. Create a JSON object with these exact fields:
   - id: the generated task ID
   - ts: current ISO 8601 timestamp with timezone
   - status: "pending"
   - description: the $ARGUMENTS text
   - trigger: "manual"
   - source_email: null
   - outcome: null
   - completed_at: null
4. Append the JSON object as a single line to data/tasks/active.jsonl
5. Append a feed entry to data/feed.jsonl with: ts=now, type="task", summary="Created task: (description)", level="info", trigger="manual", details={"task_id":"(id)"}
6. Display the created task with its ID

If no arguments provided:
1. Read data/tasks/active.jsonl
2. Filter for entries where status is "pending" or "in-progress"
3. Display as a formatted list with ID, status, description, and creation time
4. If no tasks found, display "No active tasks."
