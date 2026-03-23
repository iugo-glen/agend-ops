---
description: "Process pending actions from dashboard queue"
allowed-tools: "Read, Write, Edit, Bash(jq *), Bash(date *), Bash(wc *), Bash(bash scripts/*), Bash(git *), Bash(mv *)"
---

Process pending actions queued from the interactive dashboard. These are actions Glen triggered via dashboard buttons (mark-paid, complete-todo, complete-task, trigger-triage).

## Step 1: Read Queue

Read `data/queue/actions.jsonl`. If the file does not exist or is empty, report "No pending actions" and exit.

```bash
if [ ! -f data/queue/actions.jsonl ] || [ ! -s data/queue/actions.jsonl ]; then
  echo "NO_ACTIONS"
fi
```

## Step 2: Filter Pending

Parse each line. Filter to entries where `status === "queued"`:

```bash
jq -s '[.[] | select(.status == "queued")]' data/queue/actions.jsonl
```

If none are queued, report "No pending actions" and exit.

## Step 3: Process Each Action

For each queued action, execute based on action type:

### mark-paid

1. Read `data/invoices/active.jsonl`
2. Find the invoice matching `target_id`
3. Update its status to "paid", set `completed_at` to current ISO timestamp
4. Rewrite the file:
   ```bash
   INV_ID="{target_id}"
   NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
   jq "if .id == \"$INV_ID\" then .status = \"paid\" | .completed_at = \"$NOW\" else . end" data/invoices/active.jsonl | jq -c '.' > data/invoices/active.jsonl.tmp && mv data/invoices/active.jsonl.tmp data/invoices/active.jsonl
   ```
5. Log to `data/feed.jsonl`:
   ```bash
   jq -n -c --arg ts "$NOW" --arg inv "$INV_ID" '{ts: $ts, type: "command", summary: ("Marked invoice " + $inv + " as paid (dashboard action)"), level: "info", trigger: "hook"}' >> data/feed.jsonl
   ```

### complete-todo

1. Read `data/todos/active.jsonl`
2. Find the todo matching `target_id`
3. Update status to "completed", set `completed_at` to current ISO timestamp
4. Rewrite the file:
   ```bash
   TODO_ID="{target_id}"
   NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
   jq "if .id == \"$TODO_ID\" then .status = \"completed\" | .completed_at = \"$NOW\" else . end" data/todos/active.jsonl | jq -c '.' > data/todos/active.jsonl.tmp && mv data/todos/active.jsonl.tmp data/todos/active.jsonl
   ```
5. Log to `data/feed.jsonl`:
   ```bash
   TODO_TEXT=$(jq -r "select(.id == \"$TODO_ID\") | .text" data/todos/active.jsonl)
   jq -n -c --arg ts "$NOW" --arg text "$TODO_TEXT" '{ts: $ts, type: "todo", summary: ("Completed to-do: " + $text + " (dashboard action)"), level: "info", trigger: "hook"}' >> data/feed.jsonl
   ```

### complete-task

1. Read `data/tasks/active.jsonl`
2. Find the task matching `target_id`
3. Update status to "completed", set `completed_at` to current ISO timestamp
4. Rewrite the file:
   ```bash
   TASK_ID="{target_id}"
   NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
   jq "if .id == \"$TASK_ID\" then .status = \"completed\" | .completed_at = \"$NOW\" else . end" data/tasks/active.jsonl | jq -c '.' > data/tasks/active.jsonl.tmp && mv data/tasks/active.jsonl.tmp data/tasks/active.jsonl
   ```
5. Log to `data/feed.jsonl`:
   ```bash
   TASK_DESC=$(jq -r "select(.id == \"$TASK_ID\") | .description" data/tasks/active.jsonl)
   jq -n -c --arg ts "$NOW" --arg desc "$TASK_DESC" '{ts: $ts, type: "task", summary: ("Completed task: " + $desc + " (dashboard action)"), level: "info", trigger: "hook"}' >> data/feed.jsonl
   ```

### trigger-triage

1. Run the /triage-inbox flow (dispatch to email-scanner subagent)
2. Log to `data/feed.jsonl`:
   ```bash
   NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
   jq -n -c --arg ts "$NOW" '{ts: $ts, type: "triage", summary: "Triage triggered from dashboard", level: "info", trigger: "hook"}' >> data/feed.jsonl
   ```

**IMPORTANT:** If this action is encountered during a /triage-inbox run (i.e., triage called process-queue), skip `trigger-triage` actions to prevent recursion.

## Step 4: Update Queue Entries

For each processed action:

1. Update `status` to "completed", set `processed_at` to current timestamp, set `result` to a description of what was done
2. Move completed entries from `data/queue/actions.jsonl` to `data/queue/processed.jsonl` (append)
3. Remove them from `actions.jsonl`
4. If an action failed, set `status` to "failed" with error in `result`, leave in `actions.jsonl`

```bash
# Move completed entries to processed.jsonl
jq 'select(.status == "completed")' data/queue/actions.jsonl >> data/queue/processed.jsonl
# Keep only non-completed entries in actions.jsonl
jq -c 'select(.status != "completed")' data/queue/actions.jsonl > data/queue/actions.jsonl.tmp && mv data/queue/actions.jsonl.tmp data/queue/actions.jsonl
```

## Step 5: Rebuild Dashboard Data

```bash
bash scripts/build-dashboard-data.sh
```

## Step 6: Commit and Report

```bash
git add data/queue/ data/invoices/ data/todos/ data/tasks/ data/feed.jsonl docs/
git commit -m "feat: process {N} dashboard actions"
```

Report summary: how many actions processed, what was done for each.

```
## Queue Processing Complete

Processed {N} actions:
- mark-paid: {target_id} -> invoice marked as paid
- complete-todo: {target_id} -> to-do completed
- ...

{N} actions processed successfully. {N} failed (if any).
```
