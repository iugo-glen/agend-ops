# Phase 3: Task Execution - Research

**Researched:** 2026-03-23
**Domain:** Claude Code subagent task execution, Google Drive document retrieval, document analysis, draft generation
**Confidence:** HIGH

## Summary

Phase 3 builds the task execution engine: Glen delegates work to Claude via a conversational `/task` command, and Claude analyzes documents, summarizes key terms, flags risks, and drafts communications. The engine also auto-queues tasks from Phase 2 triage results (action items detected in emails) so Glen can approve and execute them from a pending queue.

The core infrastructure is already in place. The hardened-workspace MCP server (verified connected) provides nine Drive tools for document retrieval -- `search_drive_files`, `get_drive_file_content`, `list_drive_items`, and more -- alongside the Gmail tools used in Phase 2. The task-record schema (`schemas/task-record.json`) defines the task lifecycle fields. The `/task` command stub exists with basic create/list logic. The `/status` command can show pending tasks. The email-scanner subagent provides a proven pattern for isolated task execution with restricted tool access.

Real triage data from Phase 2 shows 14 emails with action items across all four action types (contract, invoice, meeting, deadline). These map directly to auto-queued tasks. The task execution engine needs to: parse these into pending task records, let Glen approve from the queue, dispatch a task-executor subagent to perform the work, save output to `data/tasks/{task-id}/`, log to the activity feed, and create Gmail drafts when the task was email-triggered.

**Primary recommendation:** Build a single generalist task-executor subagent (not one per task type) with access to both Gmail and Drive MCP tools. The four task types share too much logic (document retrieval, analysis, output formatting) to justify separate agents. Differentiate behavior through the system prompt based on task type. Extend the task-record schema to track task type, output files, and source email linkage.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Four task types in v1: contract review, meeting prep, document summary, draft communications
- **D-02:** Light write permissions -- tasks can read emails/Drive, analyze, produce drafts/summaries, AND create files in the repo (analysis docs, task records) and update task records
- **D-03:** Contract review: pull contract, summarize key terms, flag unusual clauses, identify obligations and deadlines
- **D-04:** Meeting prep: gather context about attendees/topic, draft talking points or agenda, pull relevant docs
- **D-05:** Document summary: any doc from Drive/email -- summarize, extract key points, highlight action items
- **D-06:** Draft comms: draft an email, proposal response, or client communication based on context
- **D-07:** Triage-detected actions auto-queue as pending tasks in data/tasks/active.jsonl
- **D-08:** Glen reviews the queue and approves which to execute (not auto-execute)
- **D-09:** Manual task kickoff via /task command (structured invocation)
- **D-10:** Executive summary depth by default -- key terms, parties, dates, obligations, red flags, one page max
- **D-11:** Output saved to repo (data/tasks/{task-id}/) AND displayed inline in Claude Code
- **D-12:** On completion: log to activity feed AND create Gmail draft with summary if task was triggered by an email
- **D-13:** On failure: Claude's discretion on handling (mark blocked, ask for input if interactive, etc.)
- **D-14:** Task results persist as markdown files in data/tasks/{task-id}/ committed to git

### Claude's Discretion
- Task executor subagent design (whether one agent handles all types or specialized per type)
- How to parse natural language task descriptions into structured task records
- How auto-queued tasks are presented in /status output
- Failure handling strategy per task type
- Whether to use Google Drive search or rely on email attachments for document retrieval
- Task ID generation scheme

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TASK-01 | Manual task kickoff via natural language commands in Claude Code | Enhanced /task command parses natural language, creates task record, dispatches task-executor subagent. Conversational syntax: `/task review the contract Sarah sent` |
| TASK-02 | Claude proactively suggests tasks from email triage results | Triage records contain action_items arrays and action_type enums. Auto-queue pipeline converts these to pending task records in active.jsonl. /status shows pending queue. |
| TASK-03 | Document retrieval from Google Drive via MCP for task execution | Hardened MCP provides `search_drive_files`, `get_drive_file_content`, `list_drive_items`. Task-executor subagent gets these tools. Can also retrieve email attachments via `get_gmail_message_content`. |
| TASK-04 | Document analysis -- summarize key terms, flag risks, identify obligations, highlight deadlines | Task-executor subagent system prompt includes analysis templates per task type. Output is markdown saved to data/tasks/{task-id}/. Executive summary depth (one page max) per D-10. |
| TASK-05 | Draft response or summary generation for completed task outcomes | On completion: output saved to repo + displayed inline. If email-triggered: Gmail draft created via `draft_gmail_message` with summary. Feed entry logged. |

</phase_requirements>

## Standard Stack

### Core

| Technology | Version | Purpose | Why Standard |
|------------|---------|---------|--------------|
| hardened-workspace MCP | latest (installed) | Gmail read, Drive read, draft creation | Already registered at user scope, verified connected. Provides 9 Drive tools + Gmail tools. |
| Claude Code subagents | Built-in | task-executor subagent for isolated task execution | Keeps document content and analysis out of main conversation context. Returns structured summary. Proven pattern from email-scanner. |
| NDJSON (data/tasks/active.jsonl) | N/A | Task queue and lifecycle records | Append-only. Schema defined in schemas/task-record.json. Existing /task command writes here. |
| NDJSON (data/feed.jsonl) | N/A | Activity feed logging for task events | Schema defined in schemas/feed-entry.json. Existing feed infrastructure from Phase 1. |
| Markdown output files | N/A | Task analysis output (data/tasks/{task-id}/) | Git-trackable, human-readable, displayable inline in Claude Code per D-11. |
| jq | 1.7.1 (installed) | JSON processing in validation and task record management | Already installed and used by validate-data.sh. |

### Supporting

| Technology | Purpose | When to Use |
|------------|---------|-------------|
| Gmail search operators | Find emails referenced in tasks | `from:{sender}`, `subject:{subject}`, `has:attachment` |
| Drive search queries | Find documents for task execution | `search_drive_files` with name or full-text queries |
| data/config/clients.jsonl | Client context enrichment for task execution | Look up client details when processing client-related tasks |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single generalist task-executor | Four specialized subagents (one per task type) | Specialized agents are cleaner in theory but share 80%+ logic (document retrieval, output formatting, feed logging). Single agent with type-specific prompt sections is simpler, uses one file, and avoids coordination overhead. Use single agent. |
| Subagent for task execution | Main conversation | Main context fills with document content after 1-2 tasks. Subagent isolates this. Use subagent. |
| Drive search for document retrieval | Email attachment only | Some tasks reference Drive docs not attached to email. Need both. Prefer email attachment when source_email is known; fall back to Drive search. |
| Sonnet model for task-executor | Haiku for simple tasks | Document analysis and draft generation need Sonnet-level reasoning. Start with Sonnet for all task types. |

## Architecture Patterns

### Recommended Task Execution Flow

```
MANUAL PATH:
Glen runs /task review the contract Sarah sent
    |
    v
/task command parses natural language
    |-- Detects task type from description (contract/meeting/document/comms)
    |-- Searches recent triage data for matching email if referenced
    |-- Creates task record in active.jsonl (status: "pending")
    |-- Immediately dispatches task-executor subagent
    |
    v

AUTO-QUEUE PATH:
Email triage detects action items
    |-- For each triage record with action_items + action_type != "none":
    |-- Create task record in active.jsonl (status: "pending", trigger: "triage-suggestion")
    |-- Link to source email via source_email field
    |
Glen runs /task (no args) -- sees pending queue
    |-- Glen picks task to execute
    |
    v

EXECUTION (both paths converge):
task-executor subagent spawned (Sonnet, Gmail+Drive MCP tools)
    |
    v
PHASE 1: Context Gathering
    |-- If source_email: read full email content via get_gmail_message_content
    |-- If has_attachments: download/read attachments
    |-- Search Drive for referenced documents (search_drive_files)
    |-- Load client context from clients.jsonl if applicable
    |
    v
PHASE 2: Analysis (type-specific)
    |-- contract-review: key terms, unusual clauses, obligations, deadlines
    |-- meeting-prep: attendee context, talking points, relevant docs, agenda draft
    |-- document-summary: summary, key points, action items
    |-- draft-comms: draft email/proposal/communication
    |
    v
PHASE 3: Output
    |-- Create data/tasks/{task-id}/ directory
    |-- Write analysis as markdown (e.g., analysis.md, summary.md, draft.md)
    |-- Update task record: status="completed", outcome=summary, completed_at=now
    |-- If email-triggered: create Gmail draft with summary via draft_gmail_message
    |-- Append feed entry to data/feed.jsonl
    |-- Return formatted summary to main conversation (displayed inline)
```

### Pattern 1: Task Record Schema Extension

**What:** The existing task-record.json schema needs new fields to support task execution lifecycle.

**Current schema fields:** id, ts, status, description, trigger, source_email, outcome, completed_at

**Fields to add:**

```json
{
  "task_type": {
    "type": "string",
    "enum": ["contract-review", "meeting-prep", "document-summary", "draft-comms"],
    "description": "Type of task, determines analysis approach"
  },
  "output_dir": {
    "type": ["string", "null"],
    "description": "Path to task output directory (e.g., data/tasks/task-2026-03-23-001/)"
  },
  "source_triage": {
    "type": ["string", "null"],
    "description": "Triage file path if task originated from triage (e.g., data/triage/2026-03-23T004602.jsonl)"
  },
  "client_name": {
    "type": ["string", "null"],
    "description": "Associated client name if task is client-related"
  },
  "draft_id": {
    "type": ["string", "null"],
    "description": "Gmail draft ID if a draft was created on completion"
  }
}
```

**Rationale:** `task_type` enables the subagent to select the right analysis template. `output_dir` tracks where results are stored. `source_triage` links back to the triage run for provenance. `client_name` enriches context. `draft_id` tracks email-triggered output.

### Pattern 2: Task-Executor Subagent Design

**What:** A single generalist subagent that handles all four task types, differentiated by prompt sections.

**Configuration:**

```yaml
---
name: task-executor
description: Executes delegated tasks -- contract review, meeting prep, document summary, draft communications. Use when /task dispatches work or when executing approved tasks from the queue.
tools: Read, Write, Edit, Bash(jq *), Bash(date *), Bash(mkdir *), mcp__hardened-workspace__search_gmail_messages, mcp__hardened-workspace__get_gmail_message_content, mcp__hardened-workspace__get_gmail_messages_content_batch, mcp__hardened-workspace__search_drive_files, mcp__hardened-workspace__get_drive_file_content, mcp__hardened-workspace__list_drive_items, mcp__hardened-workspace__draft_gmail_message
model: sonnet
---
```

**Key design choices:**
- Single agent, not four specialized ones -- shared logic (document retrieval, output formatting, feed logging) dominates
- Both Gmail AND Drive MCP tools -- tasks may need documents from either source
- Write/Edit tools included -- for creating output files in data/tasks/{task-id}/ and updating task records
- Bash(mkdir) -- for creating task output directories
- Sonnet model -- document analysis needs strong reasoning

### Pattern 3: Natural Language Task Parsing

**What:** The /task command interprets conversational input and maps it to a structured task.

**Parsing strategy:** Use keyword and pattern matching in the command prompt, not a separate NLP pipeline.

**Detection rules:**

| Input Pattern | Detected Task Type |
|---------------|-------------------|
| "review contract", "review agreement", "check the contract", "legal review" | contract-review |
| "prep for meeting", "prepare for", "meeting with", "agenda for" | meeting-prep |
| "summarize", "summary of", "key points from", "what does X say" | document-summary |
| "draft reply", "draft email", "write a response", "draft proposal" | draft-comms |

**Source resolution:** When Glen says "the contract Sarah sent", the command should:
1. Search recent triage records for emails from "Sarah" with action_type="contract"
2. If found: link source_email, extract message_id for attachment retrieval
3. If not found: search Gmail directly with `from:sarah has:attachment`

### Pattern 4: Auto-Queue Pipeline (Triage to Tasks)

**What:** After each triage run, detected action items become pending tasks.

**Pipeline (runs as part of /triage-inbox post-processing or as a separate step):**

1. Read the latest triage output file
2. Filter for records where: `action_items.length > 0` AND `action_type != "none"`
3. For each qualifying record, create a task record:
   - `id`: next available task ID for today
   - `status`: "pending"
   - `trigger`: "triage-suggestion"
   - `source_email`: the triage record's message_id
   - `task_type`: map from triage action_type (contract -> contract-review, meeting -> meeting-prep, deadline/invoice -> document-summary)
   - `description`: first action_item text, enriched with sender/subject context
   - `client_name`: from triage record if available
4. Deduplicate: check if a pending task already exists with same source_email (avoid re-queuing on re-triage)

**Real data example (from existing triage output):**
- Triage record: `{from_name: "Greg Davenport", subject: "Re: Agend x PCA Shopping Centre Online -- SOW Review", action_type: "meeting", action_items: ["Review PCA SOW example files ahead of Tuesday 24 March 2pm meeting"]}`
- Auto-queued task: `{description: "Review PCA SOW example files ahead of Tuesday 24 March 2pm meeting (from Greg Davenport @ Property Council Australia)", task_type: "meeting-prep", trigger: "triage-suggestion", source_email: "19d17c8f98f99484", client_name: "Property Council Australia"}`

### Pattern 5: Task Output Structure

**What:** Each completed task produces output files in a dedicated directory.

**Directory structure:**

```
data/tasks/task-2026-03-23-001/
    analysis.md          # Primary analysis output (contract review, document summary)
    talking-points.md    # For meeting-prep tasks
    draft.md             # For draft-comms tasks, or email draft content
    context.md           # Source material references and metadata
```

**Output file naming by task type:**

| Task Type | Primary Output | Secondary Output |
|-----------|---------------|-----------------|
| contract-review | analysis.md (key terms, clauses, obligations, red flags) | -- |
| meeting-prep | talking-points.md (agenda, talking points, attendee context) | context.md (relevant docs pulled) |
| document-summary | summary.md (executive summary, key points, action items) | -- |
| draft-comms | draft.md (the drafted communication) | -- |

**Formatting:** Executive summary depth per D-10 -- one page max. Structured with headers, bullet points, bold for key terms. Immediately useful -- Glen should be able to glance and act.

### Pattern 6: Enhanced /task Command

**What:** Upgrade the existing /task command stub to support full task execution lifecycle.

**Modes:**

1. `/task` (no args) -- Show pending task queue with approval interface
2. `/task <natural language>` -- Parse, create task, execute immediately
3. `/task run <task-id>` -- Execute a specific pending task from the queue
4. `/task list` -- Show all active tasks (pending + in-progress)

**Queue display format (mode 1):**

```
## Pending Tasks

From triage (2026-03-23 09:00):
  1. [task-2026-03-23-001] Review PCA SOW example files (meeting prep)
     Source: Greg Davenport @ Property Council Australia
     -> /task run task-2026-03-23-001

  2. [task-2026-03-23-002] Review contract renewal Q3 (contract review)
     Source: Sarah Chen @ Acme Corp
     -> /task run task-2026-03-23-002

Manual:
  (none)

Run `/task run <id>` to execute, or `/task <description>` for a new task.
```

### Pattern 7: Enhanced /status Command

**What:** Add pending task count and queue summary to existing /status output.

**Current /status sections:** Recent Activity, Triage Runs, Pending Tasks (count only), System Health

**Enhancement:** Expand "Pending Tasks" from a simple count to include:
- Count of pending tasks
- Breakdown by trigger (triage-suggestion vs manual)
- Top 3 pending tasks with descriptions
- Count of completed tasks today

### Anti-Patterns to Avoid

- **Auto-executing tasks from triage:** Per D-08, tasks are queued as "pending" and require Glen's approval. Never auto-execute.
- **Storing full document content in task records:** Only store metadata and output file paths in active.jsonl. Full analysis goes in data/tasks/{task-id}/ files.
- **Running task execution in the main conversation:** Document content fills context window rapidly. Always delegate to the task-executor subagent.
- **One subagent per task type:** Adds coordination complexity for minimal benefit. Four task types share 80%+ of their logic.
- **Ignoring source_email linkage:** When a task originates from triage, the source_email field is critical for retrieving the right document and threading Gmail drafts correctly.
- **Re-queuing the same action item on re-triage:** Deduplicate by checking source_email before creating pending tasks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gmail access | Custom OAuth + API client | hardened-workspace MCP tools | Already installed, OAuth configured, security-hardened |
| Drive document retrieval | Custom Drive API client | `search_drive_files` + `get_drive_file_content` MCP tools | Already available in hardened fork, read-only access verified |
| Email draft creation | Custom Gmail API calls | `draft_gmail_message` MCP tool | Handles threading via in_reply_to, already proven in Phase 2 |
| Task queue management | Database or external queue | NDJSON append to active.jsonl + jq queries | Existing pattern from Phase 1, git-trackable, simple |
| JSON validation | Custom parser | `scripts/validate-data.sh` + jq | Already built in Phase 1 |
| Task ID generation | UUID or external service | Sequential `task-YYYY-MM-DD-NNN` format | Already defined in schema and /task command stub |
| Document analysis | External NLP pipeline | Claude (Sonnet) in subagent | Claude IS the analysis engine. No external tool needed. |

## Common Pitfalls

### Pitfall 1: Document Retrieval Failure (Attachment Not in Drive)
**What goes wrong:** Task references "the contract Sarah sent" but the document is an email attachment, not a Drive file. `search_drive_files` returns nothing.
**Why it happens:** Not all documents referenced in emails live in Drive. Many are direct email attachments.
**How to avoid:** Two-step retrieval: (1) If source_email exists, read the email via `get_gmail_message_content` to check for attachments. (2) If no attachment or additional docs needed, search Drive. The task-executor subagent should try email attachments first for email-triggered tasks.
**Warning signs:** Task-executor reports "no documents found" for tasks that clearly reference a document.

### Pitfall 2: Task Record Schema Migration
**What goes wrong:** Adding new fields to task-record.json with `additionalProperties: false` means old records fail validation and new code can't write records with the new fields until the schema is updated.
**Why it happens:** Schema update must happen BEFORE any code tries to write records with new fields.
**How to avoid:** Schema extension is the FIRST task in the plan. Update the schema before building any code that writes extended records. Old records (with null/missing optional fields) remain valid because new fields are nullable.
**Warning signs:** validate-data.sh fails after writing new-format task records.

### Pitfall 3: Token Cost from Large Documents
**What goes wrong:** A contract or SOW can be 20-50 pages. Reading the full document into the subagent context burns excessive tokens.
**Why it happens:** `get_drive_file_content` returns the entire document content.
**How to avoid:** For large documents, instruct the subagent to: (1) Read the document, (2) Produce the executive summary immediately (one page max per D-10), (3) Do not store the full document in output files. The subagent's auto-compaction handles context pressure, but prompt the subagent to work efficiently.
**Warning signs:** Task execution taking unusually long. High API costs for single tasks.

### Pitfall 4: Gmail Draft Threading for Email-Triggered Tasks
**What goes wrong:** When a task completes and creates a Gmail draft with the summary, the draft doesn't thread properly with the original email.
**Why it happens:** The `in_reply_to` parameter needs the original message's ID, not the thread ID.
**How to avoid:** Store the source_email (message_id) in the task record. Pass it to `draft_gmail_message` as `in_reply_to` when creating the completion draft. This is the same pattern proven in Phase 2 triage draft creation.
**Warning signs:** Task completion drafts appear as new conversations in Gmail instead of threaded replies.

### Pitfall 5: Auto-Queue Duplicates on Re-Triage
**What goes wrong:** Running /triage-inbox twice in the same day creates duplicate pending tasks for the same action items.
**Why it happens:** The auto-queue pipeline reads the latest triage file and creates tasks without checking if a task for that source_email already exists.
**How to avoid:** Before creating an auto-queued task, check active.jsonl for existing records with the same source_email. Skip creation if found.
**Warning signs:** Duplicate pending tasks with identical descriptions in the queue.

### Pitfall 6: Task Type Misdetection from Natural Language
**What goes wrong:** Glen says "check the proposal Sarah sent" and the system classifies it as a document-summary when he meant a contract-review.
**Why it happens:** Natural language is ambiguous. "Check" could mean review, summarize, or just read.
**How to avoid:** When task type is ambiguous, the /task command should: (1) Make a best guess based on keywords, (2) Display the detected type to Glen, (3) Allow override before execution. This keeps the flow conversational while maintaining accuracy.
**Warning signs:** Task output doesn't match what Glen expected.

## Code Examples

### MCP Tool Usage: Search Drive Files
```
# Via hardened-workspace MCP
search_drive_files(query="name contains 'SOW' and 'Property Council'")
# Returns: list of file IDs, names, types, modified dates

# Search for recent contracts
search_drive_files(query="mimeType='application/pdf' and modifiedTime > '2026-03-01'")
```
Source: [hardened-google-workspace-mcp](https://github.com/c0webster/hardened-google-workspace-mcp), [Google Drive search query syntax](https://developers.google.com/drive/api/guides/search-files)

### MCP Tool Usage: Read Drive File Content
```
# Read a Google Doc, Sheet, or Office file
get_drive_file_content(file_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms")
# Returns: document content as text

# List items in a folder
list_drive_items(folder_id="root")
# Returns: files and folders in the specified directory
```
Source: [hardened-google-workspace-mcp](https://github.com/c0webster/hardened-google-workspace-mcp)

### Task Record Example (extended schema)
```json
{"id":"task-2026-03-23-001","ts":"2026-03-23T10:00:00+10:30","status":"pending","description":"Review PCA SOW example files ahead of Tuesday 24 March 2pm meeting (from Greg Davenport @ Property Council Australia)","trigger":"triage-suggestion","task_type":"meeting-prep","source_email":"19d17c8f98f99484","source_triage":"data/triage/2026-03-23T004602.jsonl","client_name":"Property Council Australia","output_dir":null,"outcome":null,"completed_at":null,"draft_id":null}
```

### Completed Task Record Example
```json
{"id":"task-2026-03-23-001","ts":"2026-03-23T10:00:00+10:30","status":"completed","description":"Review PCA SOW example files ahead of Tuesday 24 March 2pm meeting","trigger":"triage-suggestion","task_type":"meeting-prep","source_email":"19d17c8f98f99484","source_triage":"data/triage/2026-03-23T004602.jsonl","client_name":"Property Council Australia","output_dir":"data/tasks/task-2026-03-23-001/","outcome":"Meeting prep completed: 5 talking points, SOW context summary, attendee notes. See data/tasks/task-2026-03-23-001/talking-points.md","completed_at":"2026-03-23T10:15:00+10:30","draft_id":"r-4521890345"}
```

### Feed Entry Example (task completion)
```json
{"ts":"2026-03-23T10:15:00+10:30","type":"task","summary":"Completed: Meeting prep for PCA SOW review (Property Council Australia). 5 talking points generated.","level":"info","trigger":"manual","details":{"task_id":"task-2026-03-23-001","task_type":"meeting-prep","client_name":"Property Council Australia","output_dir":"data/tasks/task-2026-03-23-001/","draft_created":true},"duration_ms":90000}
```

### Task Output Example: Contract Review (data/tasks/task-2026-03-23-002/analysis.md)
```markdown
# Contract Review: Q3 Renewal -- Acme Corp

**Reviewed:** 2026-03-23
**Source:** Email from Sarah Chen (sarah@acmecorp.com)
**Client:** Acme Corp

## Key Terms

- **Term:** 12 months (1 Jul 2026 -- 30 Jun 2027)
- **Value:** $145,000 ex-GST (up from $130,000 in current term)
- **Payment:** Monthly in arrears, Net 30
- **Auto-renewal:** Yes, 60-day notice to terminate

## Obligations

- [ ] Deliver Phase 2 module by 30 Sep 2026
- [ ] Monthly status reports to PCA steering committee
- [ ] Data migration from legacy system by 31 Aug 2026

## Red Flags

- **Clause 8.3:** Unlimited liability for data breaches -- consider capping
- **Clause 12.1:** IP assignment includes "derivative works" -- overly broad

## Deadlines

- **Sign by:** 28 March 2026 (Friday)
- **Phase 2 delivery:** 30 Sep 2026
- **Legacy migration:** 31 Aug 2026

## Recommendation

Review clauses 8.3 and 12.1 with legal before signing. Otherwise terms are standard and fair. 11.5% price increase reflects expanded scope.
```

### Task Output Example: Meeting Prep (data/tasks/task-2026-03-23-001/talking-points.md)
```markdown
# Meeting Prep: PCA SOW Review & Finalisation

**Meeting:** Tuesday 24 March 2026, 2:00 PM
**With:** Greg Davenport (Property Council Australia)
**Context:** Shopping Centre Online -- SOW Review & Finalisation

## Attendee Context

- **Greg Davenport** -- PCA digital lead, primary contact for Shopping Centre Online project
- Previous emails indicate timeline pressure on member rates deployment (26 March go-live)

## Talking Points

1. **SOW scope confirmation** -- Confirm deliverables align with PCA's current state document
2. **Member rates deployment** -- Confirm 8:15am 26 March go-live timeline, team availability
3. **Pricing screen wording** -- Verify PCA has approved final wording for event/cart screens
4. **Timeline risks** -- Any blockers from PCA side on SOW sign-off?
5. **Next steps** -- Define post-SOW milestones and communication cadence

## Relevant Documents

- SOW example files (attached to Greg's email)
- PCA current state document (attached to earlier thread)

## Action Items from Prior Emails

- Confirm Agend team deployment by 8:15am 26 March for member rates go-live
- Verify wording approved by PCA for event/cart pricing screens
```

### Subagent Task Dispatch (from /task command)
```
# The /task command dispatches to task-executor subagent:
Task tool invocation:
  agent: task-executor
  instruction: |
    Execute task task-2026-03-23-001.
    Task details:
      Type: meeting-prep
      Description: Review PCA SOW example files ahead of Tuesday 24 March 2pm meeting
      Source email: 19d17c8f98f99484
      Client: Property Council Australia

    Follow your system prompt steps. Read the source email, gather documents,
    produce meeting prep output, save to data/tasks/task-2026-03-23-001/,
    update the task record, log to feed, and return a summary.
```

## MCP Tool Reference (Hardened Workspace -- Drive Subset)

| Tool Name | Parameters | Returns | Available |
|-----------|------------|---------|-----------|
| `search_drive_files` | query (string, Drive search syntax) | File IDs, names, types, modified dates | Yes |
| `list_drive_items` | folder_id (string, default "root") | Files and folders in directory | Yes |
| `get_drive_file_content` | file_id (string, required) | Document content as text | Yes |
| `get_drive_file_download_url` | file_id (string, required) | Download URL for the file | Yes |
| `create_drive_file` | name, content, folder_id | Created file metadata | Yes |
| `update_drive_file` | file_id, metadata updates | Updated file metadata | Yes |
| `get_drive_file_permissions` | file_id | Permission details (read-only) | Yes |
| `get_drive_shareable_link` | file_id | Shareable link (read-only retrieval) | Yes |
| `check_drive_file_public_access` | file_id | Public access status | Yes |
| `share_drive_file` | -- | -- | **REMOVED** (security) |
| `batch_share_drive_file` | -- | -- | **REMOVED** (security) |
| `update_drive_permission` | -- | -- | **REMOVED** (security) |
| `remove_drive_permission` | -- | -- | **REMOVED** (security) |
| `transfer_drive_ownership` | -- | -- | **REMOVED** (security) |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One agent per task type | Single generalist agent with type-specific prompts | Best practice 2026 | Reduces maintenance surface from 4 agents to 1. Shared logic stays DRY. |
| Task execution in main conversation | Subagent isolation with summary return | Claude Code subagents 2025+ | Main context stays clean. Documents don't fill conversation window. |
| Manual document lookup | MCP-powered Drive search + email attachment retrieval | hardened-workspace MCP 2025+ | Natural language references resolve to actual documents automatically. |
| Separate task queue system | NDJSON append-only in git | Project convention | Simple, auditable, no infrastructure. Git history = task history. |

## Open Questions

1. **Drive file content format for non-Google-native files**
   - What we know: `get_drive_file_content` works for Google Docs, Sheets, and Office files per upstream docs.
   - What's unclear: How it handles PDFs, images, and other binary formats. Whether it returns text extraction or errors.
   - Recommendation: First task should test `get_drive_file_content` with a PDF and a Google Doc. If PDFs fail, use `get_drive_file_download_url` as fallback (though the subagent cannot download files to disk directly).

2. **Exact Drive search query syntax**
   - What we know: Uses Google Drive API query syntax (`name contains 'X'`, `mimeType='...'`).
   - What's unclear: Whether the MCP tool wraps this in a simpler interface or passes the raw query through.
   - Recommendation: Test with a simple query (`search_drive_files(query="name contains 'SOW'")`) during first task implementation. Adapt parsing based on response.

3. **Auto-queue integration point**
   - What we know: Triage writes action items to triage JSONL. Tasks need to appear in active.jsonl.
   - What's unclear: Whether to auto-queue during /triage-inbox post-processing (simpler, immediate) or as a separate step Glen runs manually (more control).
   - Recommendation: Auto-queue during /triage-inbox as a post-processing step. Glen still approves execution via /task run. This matches D-07 ("auto-queue as pending") and D-08 ("Glen approves which to execute").

4. **Task record update strategy (NDJSON immutability)**
   - What we know: NDJSON is append-only. But task status changes from "pending" to "in-progress" to "completed" require updating existing records.
   - What's unclear: Whether to update-in-place (read file, modify matching line, rewrite) or append status-change entries (event sourcing).
   - Recommendation: Update-in-place using jq. The file is small (dozens of records), and event sourcing adds complexity for no benefit at this scale. Read, filter, modify, rewrite. Move completed tasks to data/tasks/completed/ periodically.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| hardened-workspace MCP | Drive + Gmail access (TASK-03, TASK-05) | Yes | latest | None -- this is the only safe path |
| jq | Task record management, validation | Yes | 1.7.1 | None needed |
| Python 3 | MCP server runtime | Yes | 3.14.3 | None needed |
| Claude Code subagents | Context isolation for task execution | Yes | Built-in | Could run in main conversation (not recommended) |
| git | Commit task outputs | Yes | 2.53.0 | None needed |

**Missing dependencies with no fallback:** None -- all required tools are available.

## Project Constraints (from CLAUDE.md)

- **MCP server:** Use ONLY `hardened-workspace` MCP server for Gmail/Drive. DO NOT use `claude.ai Gmail` or `claude.ai Google Calendar` connectors.
- **Tool prefix:** Gmail/Drive tools use `mcp__hardened-workspace__` prefix.
- **Security model:** Claude can READ emails/Drive files and CREATE drafts, but CANNOT send, share, create filters, or delete.
- **Data conventions:** Feed entries append to `data/feed.jsonl`. Task records in `data/tasks/active.jsonl`. All timestamps ISO 8601 with timezone offset.
- **Schemas:** All records must conform to `schemas/` directory JSON Schema definitions. Schema has `additionalProperties: false` -- new fields must be explicitly added.
- **Commands:** Use YAML frontmatter with `allowed-tools` to constrain tool access per command.
- **GSD workflow:** Do not make direct repo edits outside a GSD workflow unless user explicitly asks.
- **Subagent pattern:** From Phase 2 -- subagents use explicit tool lists (not globs) for security boundary. Dispatch via Task tool from command.

## Sources

### Primary (HIGH confidence)
- [hardened-google-workspace-mcp (GitHub)](https://github.com/c0webster/hardened-google-workspace-mcp) -- verified connected, Drive tool surface confirmed (9 tools available, 5 sharing tools removed)
- [hardened-google-workspace-mcp SECURITY.md](https://github.com/c0webster/hardened-google-workspace-mcp/blob/main/SECURITY.md) -- complete list of removed tools documented
- [google_workspace_mcp README_NEW.md](https://github.com/taylorwilsdon/google_workspace_mcp/blob/main/README_NEW.md) -- Drive tool parameters and capabilities
- [Claude Code subagents docs](https://code.claude.com/docs/en/sub-agents) -- full subagent YAML frontmatter spec, tools, model, MCP scoping, permission modes, hooks
- schemas/task-record.json -- verified existing schema fields, identified extension needs
- schemas/feed-entry.json -- verified existing schema, no changes needed for task events
- .claude/agents/email-scanner.md -- proven subagent pattern to follow
- .claude/commands/task.md -- existing command stub with task creation logic
- .claude/commands/status.md -- existing status command to enhance
- data/triage/2026-03-23T004602.jsonl -- real triage data with 14 action items across 4 types

### Secondary (MEDIUM confidence)
- [Google Drive API search query syntax](https://developers.google.com/drive/api/guides/search-files) -- Drive search query format
- [google_workspace_mcp (PulseMCP)](https://www.pulsemcp.com/servers/taylorwilsdon-google-workspace) -- tool capability overview

### Tertiary (LOW confidence)
- Exact response format of `search_drive_files` -- needs runtime validation
- `get_drive_file_content` behavior with PDF/binary files -- needs runtime testing
- Whether MCP tool wraps Drive search query or passes raw syntax -- needs runtime testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tools verified installed and connected, schemas confirmed, pattern proven in Phase 2
- Architecture: HIGH -- single subagent design follows proven email-scanner pattern, task lifecycle is straightforward NDJSON
- Pitfalls: HIGH -- document retrieval, schema migration, and deduplication are well-understood problems with clear mitigations
- MCP Drive tools: MEDIUM -- tool names confirmed via SECURITY.md and upstream docs, but exact parameter/response formats need runtime verification

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable domain, MCP server pinned at installed version)
