---
description: Create, manage, and execute tasks -- delegates work to the task-executor subagent
allowed-tools: Read, Write, Edit, Bash(jq *), Bash(date *), Bash(wc *), Task
---

Manage tasks for Agend Ops. Argument: $ARGUMENTS

## Mode Detection

Determine which mode to run based on $ARGUMENTS:

- **If $ARGUMENTS is empty** -> Mode 1 (show pending queue)
- **If $ARGUMENTS starts with "run "** -> Mode 3 (extract task-id from remainder, execute it)
- **If $ARGUMENTS equals "list"** -> Mode 4 (show all tasks)
- **Otherwise** -> Mode 2 (natural language task creation + immediate execution)

---

## MODE 1: Show Pending Task Queue (no arguments)

Display the pending task queue for review and approval.

1. Read `data/tasks/active.jsonl`
2. Filter for entries where `status` is `"pending"`
3. Group by `trigger`: show `"triage-suggestion"` tasks first (labeled "From triage"), then `"manual"` tasks
4. Display each task with: ID, description, task_type (if set), client_name (if set), and a hint to run it

Display format:

```
## Pending Tasks

**From triage:**
  1. [{id}] {description} ({task_type})
     {client_name if set}
     -> /task run {id}

**Manual:**
  (none or list in same format)

Run /task run id to execute, or /task description for a new task.
```

5. If no pending tasks exist, display: "No pending tasks. Run `/task description` to create one, or `/triage-inbox` to scan for action items."

---

## MODE 2: Natural Language Task Creation + Execution

Parse the natural language description, create a task record, and immediately dispatch to the task-executor subagent.

### Step 1: Detect task_type from description keywords

- Contains "review contract" / "review agreement" / "check the contract" / "legal review" / "NDA" / "terms of service" -> task_type = `"contract-review"`
- Contains "prep for meeting" / "prepare for" / "meeting with" / "agenda for" / "talking points" -> task_type = `"meeting-prep"`
- Contains "summarize" / "summary of" / "key points" / "what does X say" / "review the doc" -> task_type = `"document-summary"`
- Contains "draft reply" / "draft email" / "write a response" / "draft proposal" / "write to" -> task_type = `"draft-comms"`
- If no pattern matches -> task_type = `"document-summary"` (safest default)

### Step 2: Resolve source email from triage data

Search recent triage files in `data/triage/` (use the latest file) for matching `from_name` or `subject` keywords from the description:

```bash
jq -r 'select(.from_name | test("keyword"; "i")) | .message_id' data/triage/{latest}.jsonl
```

If a match is found:
- Set `source_email` to the matched `message_id`
- Set `client_name` from the triage record if available

### Step 3: Generate task ID

Generate a task ID in format `task-{YYYY-MM-DD}-{NNN}` where NNN is zero-padded sequence number:

```bash
EXISTING=$(jq -r '.id' data/tasks/active.jsonl 2>/dev/null | grep "task-$(date +%Y-%m-%d)" | wc -l | tr -d ' ')
NEXT=$(printf "%03d" $((EXISTING + 1)))
TASK_ID="task-$(date +%Y-%m-%d)-${NEXT}"
```

### Step 4: Get current timestamp

```bash
date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/'
```

### Step 5: Create task record

Create a JSON object with ALL 13 schema fields from `schemas/task-record.json`:

- `id`: generated task ID
- `ts`: current ISO 8601 timestamp with timezone offset
- `status`: `"pending"`
- `description`: the $ARGUMENTS text
- `trigger`: `"manual"`
- `source_email`: matched message_id from triage, or `null`
- `outcome`: `null`
- `completed_at`: `null`
- `task_type`: detected type from Step 1
- `output_dir`: `null`
- `source_triage`: `null`
- `client_name`: from triage match if available, or `null`
- `draft_id`: `null`

### Step 6: Append to data/tasks/active.jsonl

Append the task record as a single JSON line to `data/tasks/active.jsonl`.

### Step 7: Log to activity feed

Append a feed entry to `data/feed.jsonl`:

```json
{"ts": "{now}", "type": "task", "summary": "Created task: {description}", "level": "info", "trigger": "manual", "details": {"task_id": "{id}", "task_type": "{type}"}}
```

### Step 8: Dispatch to task-executor subagent

Use the **Task** tool to dispatch to the task-executor subagent:

- **Agent:** `task-executor`
- **Instruction:** The full task record as JSON, followed by: "Execute this task following your system prompt step by step. Return the formatted summary when complete."

**Fallback:** If the `task-executor` agent type is not available (agent discovery happens at session start), read `.claude/agents/task-executor.md` and execute the task inline following its system prompt directly. This produces identical results without the subagent dispatch.

### Step 9: Display results

Display the subagent's returned summary directly (inline in the conversation).

### Step 10: Suggest next steps

After displaying results, suggest: "Run `/task` to see your task queue, or `/status` for an overview."

---

## MODE 3: Execute Pending Task by ID (/task run {task-id})

Execute a specific pending task from the queue.

1. Read `data/tasks/active.jsonl`
2. Find the task record matching the given ID (case-sensitive exact match using jq):
   ```bash
   jq -r 'select(.id == "{task-id}")' data/tasks/active.jsonl
   ```
3. **If not found:** Display "Task {id} not found. Run `/task` to see pending tasks."
4. **If found but status is not "pending":** Display "Task {id} is already {status}. Only pending tasks can be executed."
5. **If found and status is "pending":** Dispatch to task-executor subagent using the Task tool:
   - **Agent:** `task-executor`
   - **Instruction:** The full task record as JSON, followed by: "Execute this task following your system prompt step by step. Return the formatted summary when complete."
   - **Fallback:** If `task-executor` agent type is not available, read `.claude/agents/task-executor.md` and execute inline following its system prompt directly.
6. Display the subagent's returned summary directly.

---

## MODE 4: List All Tasks (/task list)

Show all active tasks regardless of status.

1. Read `data/tasks/active.jsonl`
2. Display ALL entries (pending, in-progress, completed, cancelled) in a table format:

| ID | Status | Type | Description | Created |
|----|--------|------|-------------|---------|
| task-2026-03-23-001 | pending | contract-review | Review the PCA SOW | 2026-03-23T10:30:00+10:00 |

3. Show counts at the bottom: "{N} total, {N} pending, {N} completed, {N} in-progress"

Use jq to extract and format the data:
```bash
jq -r '[.id, .status, (.task_type // "untyped"), .description[:60], .ts[:19]] | @tsv' data/tasks/active.jsonl
```
