# Architecture Research: v2.0 Integration

**Domain:** Autonomous operations layer on existing Agend Ops (Claude Code + MCP + NDJSON git store + GitHub Pages dashboard)
**Researched:** 2026-03-23
**Confidence:** HIGH (existing system well-understood, new features verified against official docs)

## Existing System Summary (v1 Baseline)

Before mapping v2 integration, here is what already exists and works:

```
Glen
 |
 +--- Claude Code CLI (/triage-inbox, /task, /status, /feed)
 |        |
 |        +--- email-scanner subagent (Sonnet) --- hardened-workspace MCP --- Gmail API
 |        +--- task-executor subagent (Sonnet) --- hardened-workspace MCP --- Gmail + Drive
 |        +--- github MCP (remote HTTP) --- GitHub API
 |        |
 |        +--- data/feed.jsonl      (activity log, NDJSON)
 |        +--- data/triage/*.jsonl  (triage runs, NDJSON)
 |        +--- data/tasks/active.jsonl + data/tasks/{id}/ (task records + output)
 |        +--- data/config/clients.jsonl (client lookup)
 |        |
 |        +--- scripts/build-dashboard-data.sh (NDJSON -> JSON)
 |        +--- scripts/validate-data.sh
 |
 +--- GitHub Pages dashboard (docs/index.html reads docs/feed.json, tasks.json, triage.json)
```

**What works today:** Interactive email triage, task execution (manual and auto-queued from triage), activity feed logging, static dashboard with mobile view. All manual -- Glen types commands, Claude executes, data commits to git.

**What does NOT exist yet:** Scheduled automation, daily to-do management, invoice tracking, Telegram mobile commands, GitHub Actions workflows.

## v2 System Overview

```
                          Glen (Operator)
                   +----------+----------+-----------+
                   |          |          |           |
             +-----v--+  +---v----+  +--v--------+  |
             | Claude  |  | Mobile |  | Telegram  |  |
             | Code    |  | Phone  |  | Bot       |  |
             | (CLI)   |  |        |  | (Channel) |  |
             +----+----+  +---+----+  +-----+-----+  |
                  |            |            |         |
                  |       +----v-----+  +---v---------v---+
                  |       | GitHub   |  | Claude Code     |
                  |       | Pages    |  | w/ --channels   |
                  |       | Dashboard|  | (local session) |
                  |       +----+-----+  +---+-------------+
                  |            |            |
   +--------------v------------v------------v-----------------------------+
   |                  Claude Code Runtime                                  |
   |                                                                       |
   |  +------------------+  +------------------+  +------------------+     |
   |  | Existing Agents  |  | NEW: Daily       |  | NEW: Invoice     |    |
   |  |                  |  | Task Agent       |  | Scanner Agent    |    |
   |  | email-scanner    |  | (manages to-do   |  | (extracts from   |    |
   |  | task-executor    |  |  lists, daily    |  |  triage data)    |    |
   |  +--------+---------+  |  priorities)     |  +--------+---------+    |
   |           |             +--------+---------+           |              |
   |           |                      |                     |              |
   |  +--------v----------------------v---------------------v---------+   |
   |  |                   MCP Server Layer                            |   |
   |  |  +-----------+  +-----------+  +-----------+                  |   |
   |  |  | hardened-  |  | github    |  | (no new   |                  |   |
   |  |  | workspace  |  | MCP       |  |  MCPs     |                  |   |
   |  |  | (Gmail+    |  | (remote   |  |  needed)  |                  |   |
   |  |  |  Drive)    |  |  HTTP)    |  |           |                  |   |
   |  |  +-----------+  +-----------+  +-----------+                  |   |
   |  +---------------------------------------------------------------+   |
   +---------------------------+-------------------------------------------+
                               |
   +--- GitHub Actions --------v-------------------------------------------+
   |  claude-code-action@v1 (durable scheduled automation)                 |
   |  +-- daily-triage.yml   (weekday 9am: run /triage-inbox)             |
   |  +-- daily-briefing.yml (weekday 8:30am: compile daily task list)    |
   +-----------------------------------------------------------------------+
                               |
   +--- Local Git Repository --v-------------------------------------------+
   |                                                                        |
   |  data/                                                                 |
   |  +-- feed.jsonl           # Existing: activity log                     |
   |  +-- triage/*.jsonl       # Existing: triage run results               |
   |  +-- tasks/active.jsonl   # Existing: task queue                       |
   |  +-- tasks/{id}/          # Existing: task output files                |
   |  +-- config/clients.jsonl # Existing: client lookup                    |
   |  +-- NEW: todos/active.jsonl    # Daily to-do items                    |
   |  +-- NEW: invoices/active.jsonl # Invoice tracking records             |
   |  +-- NEW: invoices/archive/     # Monthly invoice archives             |
   |                                                                        |
   |  .github/workflows/                                                    |
   |  +-- NEW: daily-triage.yml      # Scheduled triage via Actions         |
   |  +-- NEW: daily-briefing.yml    # Daily task compilation               |
   |                                                                        |
   |  .claude/                                                              |
   |  +-- commands/                                                         |
   |  |   +-- triage-inbox.md        # Existing                             |
   |  |   +-- task.md                # Existing                             |
   |  |   +-- status.md              # Existing (will be extended)          |
   |  |   +-- feed.md                # Existing                             |
   |  |   +-- NEW: todo.md           # Daily to-do management               |
   |  |   +-- NEW: invoice.md        # Invoice tracking                     |
   |  |   +-- NEW: daily-briefing.md # Morning briefing command             |
   |  +-- agents/                                                           |
   |  |   +-- email-scanner.md       # Existing                             |
   |  |   +-- task-executor.md       # Existing                             |
   |  |   +-- NEW: invoice-scanner.md # Invoice extraction agent            |
   +------------------------------------------------------------------------+
```

## Integration Analysis: Feature by Feature

### Feature 1: Scheduled Email Triage (GitHub Actions)

**Integration type:** New automation layer on top of existing triage command.
**Modifies existing components:** None. Wraps the existing `/triage-inbox` flow.
**New components:** `.github/workflows/daily-triage.yml`, `.github/mcp-config.json`

**How it works:**

The existing `/triage-inbox` command dispatches to the `email-scanner` subagent, which reads Gmail, categorizes emails, creates drafts, writes triage NDJSON, logs to feed, and auto-queues tasks. This entire flow already works interactively.

GitHub Actions adds a cron trigger that runs this same flow on a headless GitHub runner. The runner gets its own MCP server configuration (passed via `--mcp-config`), its own Anthropic API key (via secrets), and its own Google OAuth credentials (via secrets). After triage completes, the runner commits results and pushes, which triggers GitHub Pages to redeploy.

```
GitHub Actions cron (0 9 * * 1-5, weekday 9am UTC -- roughly 7:30pm ACST)
    |
    v
actions/checkout@v4 (gets repo with data/ directory)
    |
    v
anthropics/claude-code-action@v1
    | --mcp-config .github/mcp-config.json
    | --model claude-sonnet-4-6
    | --max-turns 20
    | prompt: "Run /triage-inbox. After triage, run /daily-briefing to compile today's task list."
    |
    v
Claude Code on runner
    | (reads CLAUDE.md, loads commands, configures MCP from .github/mcp-config.json)
    | (executes email-scanner subagent via /triage-inbox)
    | (auto-queues tasks from triage)
    | (runs scripts/build-dashboard-data.sh)
    |
    v
git commit + git push (from runner)
    |
    v
GitHub Pages redeploys (docs/ updated with fresh triage + tasks)
```

**Critical integration detail: MCP config for runners.**

The runner cannot use Glen's local MCP config. A separate `.github/mcp-config.json` must be created with:
- `hardened-google-workspace-mcp`: configured with OAuth credentials passed as environment variables from GitHub Secrets
- `github/github-mcp-server`: configured with a GitHub PAT from secrets

The Google OAuth credentials (client ID, client secret, refresh token) must be stored as GitHub Actions secrets. The hardened-workspace MCP server needs to read these from environment variables rather than local files.

**Dependency on existing system:** Uses `/triage-inbox` as-is. No changes to the command or agent needed.

**What needs to change in the existing system:** The `email-scanner` agent needs its feed.jsonl trigger field to support `"scheduled"` in addition to `"manual"`. Currently the feed-entry schema already has `"scheduled"` in its trigger enum, so this is already supported.

### Feature 2: Daily Task Management (To-Do List)

**Integration type:** New data domain + new command, extending existing task infrastructure.
**Modifies existing components:** `/status` command (add to-do summary), `build-dashboard-data.sh` (compile todos.json), `docs/index.html` (add to-do tab)
**New components:** `data/todos/active.jsonl`, `schemas/todo-record.json`, `.claude/commands/todo.md`, `.claude/commands/daily-briefing.md`

**How it integrates with existing system:**

The existing task system (`data/tasks/active.jsonl`) handles email-derived work items: contract reviews, meeting prep, document analysis. These are delegated-to-Claude tasks. The to-do system is different: it tracks Glen's personal action items that may or may not involve Claude.

These are conceptually separate but linked:
- A triage run may detect "client asked for status update" -- this becomes a pending **task** (Claude can execute it)
- Glen adds "call accountant about GST" -- this is a **to-do** (Claude cannot execute it, just tracks it)
- Some items bridge both: "review PCA contract" starts as a to-do, can be delegated to Claude as a task

**Recommended data flow:**

```
/todo add "call accountant about GST"
    |
    v
Append to data/todos/active.jsonl
    + Log to data/feed.jsonl (type: "todo")
    + Rebuild dashboard data
    |
    v
/todo (show today's list)
    |
    v
Read data/todos/active.jsonl
    + Filter: due today OR no due date + status pending
    + Sort: priority desc, created asc
    + Display grouped by priority

/todo done <id>
    |
    v
Update status in data/todos/active.jsonl
    + Log completion to data/feed.jsonl
    + Rebuild dashboard data

/daily-briefing
    |
    v
Compile morning briefing:
    1. Read pending todos (sorted by priority)
    2. Read pending tasks from data/tasks/active.jsonl
    3. Read latest triage summary from data/feed.jsonl
    4. Optionally check Gmail for overnight emails (via email-scanner)
    5. Format as daily briefing
```

**Schema: `schemas/todo-record.json`**

```json
{
  "id": "todo-YYYY-MM-DD-NNN",
  "ts": "ISO 8601 created timestamp",
  "status": "pending | completed | cancelled",
  "description": "Human-readable text",
  "priority": "high | medium | low",
  "due_date": "YYYY-MM-DD or null",
  "completed_at": "ISO 8601 or null",
  "source": "manual | triage | telegram",
  "tags": ["client:PCA", "billing"],
  "linked_task": "task-YYYY-MM-DD-NNN or null"
}
```

**Key design choice:** To-dos are separate from tasks. Tasks are Claude-executable work items with types (contract-review, meeting-prep, etc.) and require MCP access. To-dos are human action items that Claude tracks but does not execute. The `linked_task` field bridges them when a to-do gets delegated.

**Feed entry type extension:** Add `"todo"` to the feed-entry schema's `type` enum: `["triage", "task", "draft", "system", "command", "todo", "invoice"]`.

### Feature 3: Invoice Tracking

**Integration type:** New data domain + new command + new agent, with hooks into existing triage pipeline.
**Modifies existing components:** `email-scanner` agent (enhance invoice action_type detection), `/status` command (add invoice summary), `build-dashboard-data.sh` (compile invoices.json), `docs/index.html` (add invoice tab)
**New components:** `data/invoices/active.jsonl`, `data/invoices/archive/`, `schemas/invoice-record.json`, `.claude/commands/invoice.md`, `.claude/agents/invoice-scanner.md`

**How it integrates with existing system:**

The email-scanner already detects `action_type: "invoice"` during triage. Today, this creates a pending task of type `"document-summary"`. For v2, invoice-flagged emails should additionally create invoice tracking records.

**Integration points:**

1. **Triage pipeline hook:** After the email-scanner detects `action_type: "invoice"`, the `/triage-inbox` command's auto-queue section creates both:
   - A pending task in `data/tasks/active.jsonl` (as it does today)
   - A new invoice record in `data/invoices/active.jsonl` (new for v2)

2. **Invoice-scanner agent:** A new lightweight subagent that extracts structured invoice data from email content. Called when a task with `action_type: "invoice"` is executed, or manually via `/invoice scan <email-id>`.

3. **Invoice command:** `/invoice` manages the invoice lifecycle: list pending, mark as paid, show overdue, search by client.

```
Email arrives with invoice
    |
    v
email-scanner detects action_type: "invoice"
    |
    +---> Existing: auto-queue as pending task
    |
    +---> NEW: create invoice record in data/invoices/active.jsonl
              (status: "detected", amount: null, due_date: null)
    |
    v
/task run <id> (existing task execution)
    |
    v
task-executor sees task_type from invoice
    |
    +---> NEW: dispatch to invoice-scanner subagent
              - Extract: amount, currency, due date, invoice number, vendor/client
              - Update invoice record with extracted data
              - Flag if overdue
    |
    v
Invoice record updated (status: "pending-payment")
    |
    v
/invoice list (show all pending invoices with amounts and due dates)
/invoice paid <id> (mark as paid, update record)
/invoice overdue (show overdue items)
```

**Schema: `schemas/invoice-record.json`**

```json
{
  "id": "inv-YYYY-MM-DD-NNN",
  "ts": "ISO 8601 created timestamp",
  "status": "detected | pending-payment | paid | overdue | cancelled",
  "source_email": "Gmail message_id",
  "source_triage": "triage file path",
  "linked_task": "task-YYYY-MM-DD-NNN or null",
  "client_name": "string or null",
  "vendor_name": "string (who sent the invoice)",
  "invoice_number": "string or null",
  "amount": "number or null",
  "currency": "string (default AUD)",
  "due_date": "YYYY-MM-DD or null",
  "paid_date": "YYYY-MM-DD or null",
  "description": "Brief description of what the invoice is for",
  "notes": "string or null"
}
```

**Key design choice:** Invoice records are separate from tasks. An invoice has a lifecycle (detected -> pending-payment -> paid/overdue) that is independent of the task lifecycle (pending -> completed). The `linked_task` field connects them. This means Glen can mark an invoice as paid without needing to "complete a task."

### Feature 4: Telegram Mobile Commands

**Integration type:** New interface layer on top of existing commands. No data changes.
**Modifies existing components:** None initially. Claude Code session start command changes to include `--channels`.
**New components:** Telegram bot configuration, channel plugin installation, pairing setup, CLAUDE.md channel instructions section.

**How it integrates with existing system:**

Channels are a Claude Code plugin feature. The Telegram channel is a two-way bridge: Glen sends a message from Telegram, it arrives in the running Claude Code session as a `<channel source="telegram">` event, Claude processes it (with full MCP and file access), and replies through the Telegram reply tool.

**Critical constraint:** The Claude Code session must be running on Glen's machine with `--channels` enabled. Channels do NOT work with GitHub Actions (Actions has no terminal). This means Telegram commands only work while Glen's laptop is open and Claude Code is running.

```
Glen (phone, Telegram)
    |
    "triage my inbox"
    |
    v
Telegram Bot API (polls for messages)
    |
    v
Telegram Channel Plugin (local, running in Claude Code process)
    |
    v
<channel source="telegram" chat_id="12345" sender="glen">
triage my inbox
</channel>
    |
    v
Claude Code session (recognizes as /triage-inbox equivalent)
    |
    v
email-scanner subagent runs full triage
    |
    v
Telegram reply tool sends briefing back to Glen's phone
    |
    v
Permission prompts relay to Telegram (v2.1.81+)
    Glen approves/denies from phone
```

**What Glen can do from Telegram:**
- Send any command: "triage my inbox", "show my tasks", "add a todo: call accountant"
- Approve/deny permission prompts (permission relay, v2.1.81+)
- Get briefing summaries pushed back to the chat
- Review task output summaries

**What Glen cannot do from Telegram:**
- Review full dashboard (use GitHub Pages for that)
- Edit files directly
- Approve draft emails (use Gmail for that)

**CLAUDE.md additions needed:**

```markdown
## Telegram Channel

When messages arrive via <channel source="telegram">, treat them as operator commands.
Respond concisely -- Telegram messages should be scannable on a phone screen.
For long outputs (full triage briefings, task details), provide a summary in Telegram
and note that full details are on the dashboard or in the repo.

Supported commands via Telegram:
- "triage inbox" or "check email" -> run /triage-inbox
- "show tasks" or "what's pending" -> run /task (show queue)
- "add todo: <text>" -> run /todo add <text>
- "status" or "what's happening" -> run /status
- "show invoices" -> run /invoice list
- "mark invoice <id> paid" -> run /invoice paid <id>
```

**Startup change:** Glen starts Claude Code with:
```bash
claude --channels plugin:telegram@claude-plugins-official
```

This can be aliased in `.zshrc` for convenience:
```bash
alias agend="cd ~/work/todo-list && claude --channels plugin:telegram@claude-plugins-official"
```

## Component Responsibilities (v2 Changes)

| Component | v1 Responsibility | v2 Changes |
|-----------|-------------------|------------|
| **email-scanner agent** | Scan inbox, categorize, draft replies, detect action items | ADD: create invoice records for action_type:"invoice" emails |
| **task-executor agent** | Execute contract-review, meeting-prep, document-summary, draft-comms | ADD: dispatch to invoice-scanner for invoice tasks |
| **NEW: invoice-scanner agent** | N/A | Extract structured invoice data from email content |
| **/triage-inbox command** | Dispatch to email-scanner, auto-queue tasks | ADD: auto-create invoice records alongside tasks |
| **/task command** | Create, list, execute tasks | No changes |
| **NEW: /todo command** | N/A | Add, complete, list, prioritize daily to-dos |
| **NEW: /invoice command** | N/A | List, mark paid, show overdue, search invoices |
| **NEW: /daily-briefing command** | N/A | Compile morning briefing from todos + tasks + triage |
| **/status command** | Show feed, triage, tasks summary | ADD: todo count, overdue invoice count |
| **/feed command** | Show recent activity | ADD: support "todo" and "invoice" feed types |
| **build-dashboard-data.sh** | Compile feed.json, tasks.json, triage.json | ADD: compile todos.json, invoices.json |
| **docs/index.html** | Display feed, tasks, triage tabs | ADD: to-do tab, invoice tab |
| **GitHub Actions** | N/A | NEW: daily-triage.yml, daily-briefing.yml |
| **Telegram channel** | N/A | NEW: two-way command bridge from phone |

## Data Flow Changes

### New Data Files

| File | Format | Purpose | Created By | Read By |
|------|--------|---------|------------|---------|
| `data/todos/active.jsonl` | NDJSON | Daily to-do items | /todo command, Telegram | /todo, /status, /daily-briefing, dashboard |
| `data/invoices/active.jsonl` | NDJSON | Invoice tracking records | /triage-inbox (auto), /invoice (manual) | /invoice, /status, dashboard |
| `data/invoices/archive/*.jsonl` | NDJSON | Monthly invoice archives | Archive script (when file > 100 records) | Historical queries |
| `docs/todos.json` | JSON | Dashboard to-do data | build-dashboard-data.sh | docs/index.html |
| `docs/invoices.json` | JSON | Dashboard invoice data | build-dashboard-data.sh | docs/index.html |
| `.github/workflows/daily-triage.yml` | YAML | Scheduled triage workflow | Manual creation | GitHub Actions |
| `.github/mcp-config.json` | JSON | MCP config for GitHub runner | Manual creation | claude-code-action@v1 |

### Modified Data Files

| File | Change |
|------|--------|
| `data/feed.jsonl` | New type values: "todo", "invoice". New trigger value: "scheduled", "telegram" |
| `schemas/feed-entry.json` | Extend type enum, extend trigger enum |
| `docs/feed.json` | Compiled from feed.jsonl (no schema change needed, dashboard reads dynamically) |

### Unchanged Data Files

| File | Why Unchanged |
|------|---------------|
| `data/triage/*.jsonl` | Triage schema already supports invoice detection (action_type: "invoice") |
| `data/tasks/active.jsonl` | Task schema unchanged, invoice tasks use existing task_type: "document-summary" |
| `data/config/clients.jsonl` | No changes needed for v2 |
| `schemas/task-record.json` | No new fields needed |
| `schemas/triage-record.json` | Already has action_type: "invoice" |

## Build Dashboard Data Changes

The `scripts/build-dashboard-data.sh` script needs two additions:

```bash
# NEW: Compile active todos -> docs/todos.json
if [ -s "$REPO_ROOT/data/todos/active.jsonl" ]; then
  jq -s '.' "$REPO_ROOT/data/todos/active.jsonl" > "$REPO_ROOT/docs/todos.json"
else
  echo "[]" > "$REPO_ROOT/docs/todos.json"
fi

# NEW: Compile active invoices -> docs/invoices.json
if [ -s "$REPO_ROOT/data/invoices/active.jsonl" ]; then
  jq -s '.' "$REPO_ROOT/data/invoices/active.jsonl" > "$REPO_ROOT/docs/invoices.json"
else
  echo "[]" > "$REPO_ROOT/docs/invoices.json"
fi
```

## Architectural Patterns (New for v2)

### Pattern 1: Scheduled Automation via GitHub Actions

**What:** Durable cron-triggered automation that runs Claude Code on a GitHub runner with full MCP access, independent of Glen's laptop state.

**When to use:** Any operation that must run unattended: daily triage, morning briefing compilation.

**Why not Desktop scheduled tasks:** Bug #36327 (MCP tools unavailable in Desktop scheduled tasks) remains open as of March 2026. The official Desktop docs claim MCP access works, but multiple confirmed reports say otherwise. GitHub Actions is the safe choice.

**Trade-offs:**
- PRO: Runs regardless of laptop state, survives restarts, free tier sufficient (approx 300 min/month)
- CON: Requires separate MCP config with credentials in GitHub Secrets, 30-60s cold start per run, cannot interact with Glen (fire-and-forget)

### Pattern 2: Channel as Mobile Command Interface

**What:** Telegram bot bridged into a running Claude Code session via the Channels plugin. Glen sends natural language commands from phone; Claude executes with full MCP + file access and replies in chat.

**When to use:** Ad-hoc commands from phone when away from laptop (but laptop must be running).

**Trade-offs:**
- PRO: Full Claude Code capabilities from phone, permission relay (v2.1.81+), natural language
- CON: Requires running session on laptop, research preview (may change), single-user only
- IMPORTANT: Not a replacement for GitHub Actions. Channels = interactive mobile interface. Actions = unattended automation.

### Pattern 3: Separate Data Domains with Cross-References

**What:** Each new feature (todos, invoices) gets its own NDJSON file rather than extending the existing task system. Cross-references via ID fields (`linked_task`, `source_email`) connect related records.

**When to use:** When a new data type has a different lifecycle from existing types.

**Why not extend tasks:** Tasks have a lifecycle tied to Claude execution (pending -> in-progress -> completed). To-dos have a human lifecycle (created -> done). Invoices have a financial lifecycle (detected -> pending-payment -> paid). Forcing these into the task schema would require nullable fields, confusing status values, and type-checking everywhere.

**Trade-offs:**
- PRO: Clean schemas, each domain has its own semantics, easier to query and display
- CON: More files to manage, build script grows, dashboard adds tabs

### Pattern 4: Triage Pipeline Extension Points

**What:** The existing triage pipeline (email-scanner -> auto-queue tasks) gains extension points where new features hook in. Invoice detection is the first extension.

**When to use:** When a new feature needs to react to triage data without modifying the core triage logic.

**How it works:** The `/triage-inbox` command's post-triage auto-queue section already iterates over triage records with `action_type != "none"`. For v2, add a parallel path: for records where `action_type == "invoice"`, also create an invoice record in `data/invoices/active.jsonl`. The email-scanner agent itself does not change -- the extension happens in the calling command.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Overloading the Task Schema

**What people do:** Add to-do fields and invoice fields to `schemas/task-record.json` to avoid creating new files.
**Why it breaks:** Task records are Claude-executable work items. Mixing in human-only to-dos and financial invoices creates confusion: "Is this task pending because Claude hasn't run it, or because Glen hasn't paid it?" Status values become ambiguous. Queries require type-checking on every read.
**Do this instead:** Separate NDJSON files per domain. Link via `linked_task` field when needed.

### Anti-Pattern 2: Telegram as Primary Interface

**What people do:** Route all operations through Telegram and stop using Claude Code directly.
**Why it breaks:** Telegram messages are ephemeral, have limited formatting, and the channel requires a running session. If the session dies, Telegram goes silent with no warning. Long outputs (full triage briefings, contract analyses) are unreadable in chat.
**Do this instead:** Telegram for quick commands and status checks. Claude Code CLI for heavy work. Dashboard for glanceable overview.

### Anti-Pattern 3: Desktop Scheduled Tasks for MCP-Dependent Work

**What people do:** Use Claude Desktop's built-in scheduled tasks for daily email triage.
**Why it breaks:** Bug #36327 -- MCP tools fail silently during Desktop scheduled task execution. The official docs say it should work; the bug reports say it does not. Multiple duplicates (#35899, #35002, #33773) confirm the issue.
**Do this instead:** GitHub Actions with `claude-code-action@v1` and explicit `--mcp-config`.

### Anti-Pattern 4: Synchronous Invoice Extraction During Triage

**What people do:** Have the email-scanner agent extract full invoice details (amount, due date, etc.) during the triage pass.
**Why it breaks:** Triage scans 40-60 emails. Adding invoice parsing to the triage loop increases token cost and execution time significantly. Most emails are not invoices.
**Do this instead:** During triage, just flag `action_type: "invoice"` and create a skeleton invoice record. Full extraction happens when the task is explicitly executed (lazy evaluation).

## Build Order (Dependency-Driven)

```
Phase 1: Scheduled Automation (GitHub Actions)
  Depends on: Existing /triage-inbox (already complete)
  +-- .github/workflows/daily-triage.yml
  +-- .github/mcp-config.json
  +-- GitHub Secrets (ANTHROPIC_API_KEY, Google OAuth creds, GitHub PAT)
  +-- Test: trigger manually via workflow_dispatch, verify triage runs

Phase 2: Daily Task Management (To-Do System)
  Depends on: Nothing new (extends existing infrastructure)
  +-- schemas/todo-record.json
  +-- data/todos/active.jsonl (empty seed file)
  +-- .claude/commands/todo.md
  +-- .claude/commands/daily-briefing.md
  +-- Extend schemas/feed-entry.json (add "todo" type)
  +-- Extend scripts/build-dashboard-data.sh (todos.json)
  +-- Extend /status command (add todo summary)
  +-- Extend docs/index.html (add to-do tab)

Phase 3: Invoice Tracking
  Depends on: Phase 2 patterns (same schema + command + dashboard extension pattern)
  +-- schemas/invoice-record.json
  +-- data/invoices/active.jsonl (empty seed file)
  +-- .claude/agents/invoice-scanner.md
  +-- .claude/commands/invoice.md
  +-- Extend /triage-inbox auto-queue (create invoice records for action_type:"invoice")
  +-- Extend schemas/feed-entry.json (add "invoice" type)
  +-- Extend scripts/build-dashboard-data.sh (invoices.json)
  +-- Extend /status command (add invoice summary)
  +-- Extend docs/index.html (add invoice tab)

Phase 4: Telegram Mobile Commands
  Depends on: All commands exist (Phases 1-3 complete, so Telegram can invoke them)
  +-- Install Telegram channel plugin
  +-- Create and configure Telegram bot
  +-- Pair Glen's account
  +-- Add channel instructions to CLAUDE.md
  +-- Extend /daily-briefing to support Telegram-formatted output
  +-- Create shell alias for channel-enabled startup
  +-- Test: send commands from phone, verify responses
```

**Build order rationale:**

1. **GitHub Actions first** because it is the most impactful: automated daily triage runs without Glen touching anything. It also has the longest setup (GitHub Secrets, MCP runner config, OAuth credential packaging) and benefits from early testing.

2. **To-do system second** because it establishes the pattern for adding new data domains (schema -> NDJSON file -> command -> dashboard tab -> feed extension). Invoice tracking follows the same pattern, so building to-dos first creates a template.

3. **Invoice tracking third** because it hooks into the existing triage pipeline and follows the pattern established in Phase 2. It also introduces the first new subagent since v1.

4. **Telegram last** because it is a consumption layer: it invokes existing commands. Building it last means all commands exist for Telegram to call. It is also a research preview feature and the most likely to have breaking changes.

## GitHub Actions MCP Configuration

The runner needs its own MCP config because it cannot access Glen's local `~/.claude.json`:

**`.github/mcp-config.json`:**
```json
{
  "mcpServers": {
    "hardened-workspace": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/hardened-google-workspace-mcp",
        "run", "main.py"
      ],
      "env": {
        "GOOGLE_CLIENT_ID": "${GOOGLE_CLIENT_ID}",
        "GOOGLE_CLIENT_SECRET": "${GOOGLE_CLIENT_SECRET}",
        "GOOGLE_REFRESH_TOKEN": "${GOOGLE_REFRESH_TOKEN}"
      }
    },
    "github": {
      "type": "url",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GITHUB_TOKEN}"
      }
    }
  }
}
```

**Note:** The hardened-workspace MCP server needs to be installed on the runner. This means either:
- Option A: Install it as a step in the workflow (`pip install` or `uv sync` from the repo)
- Option B: Package it as a Docker container and reference it
- Option C: Use the MCP server's remote HTTP transport if available

Option A is simplest and recommended. The workflow installs the server, then Claude Code connects to it.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **Current (1 user, 50 emails/day)** | Current architecture handles this easily. Single NDJSON file per domain. No pagination needed. |
| **Growing data (6 months of daily triage)** | NDJSON files grow. Add monthly archiving for triage and invoices. Keep only last 30 days in active files. Dashboard shows last 7 days by default. |
| **Multiple daily triage runs** | If Glen triggers manual triage in addition to scheduled, dedup by `message_id` prevents double-processing. Already implemented in auto-queue logic. |
| **Telegram message volume** | Not a concern for single-user. But if Glen adds team members to Telegram, the allowlist + sender gating prevents unauthorized access. |

## Sources

- [Claude Code Channels (official docs)](https://code.claude.com/docs/en/channels) -- Telegram plugin setup, pairing, allowlist security, research preview requirements -- HIGH confidence
- [Claude Code Channels Reference (official docs)](https://code.claude.com/docs/en/channels-reference) -- Channel protocol, notification format, reply tools, permission relay (v2.1.81+) -- HIGH confidence
- [Claude Code Scheduled Tasks (official docs)](https://code.claude.com/docs/en/scheduled-tasks) -- /loop, cron tools, session scope, 3-day expiry -- HIGH confidence
- [Claude Code Desktop (official docs)](https://code.claude.com/docs/en/desktop) -- Desktop scheduled tasks documentation, claims MCP access works -- HIGH confidence
- [Claude Code GitHub Actions (official docs)](https://code.claude.com/docs/en/github-actions) -- claude-code-action@v1 setup, MCP config passthrough via claude_args --mcp-config -- HIGH confidence
- [MCP Scheduled Task Bug #36327 (GitHub)](https://github.com/anthropics/claude-code/issues/36327) -- MCP tools unavailable in Desktop scheduled tasks, open as of March 2026, duplicates #35899, #35002, #33773 -- HIGH confidence
- [anthropics/claude-code-action (GitHub)](https://github.com/anthropics/claude-code-action) -- Action configuration, MCP config support, scheduled workflow examples -- HIGH confidence
- [Telegram plugin source (GitHub)](https://github.com/anthropics/claude-plugins-official/tree/main/external_plugins/telegram) -- Telegram channel implementation, pairing flow -- HIGH confidence
- Existing v1 architecture research (`.planning/research/ARCHITECTURE.md`) -- baseline system understanding -- HIGH confidence

---
*Architecture research for: Agend Ops v2.0 -- Autonomous Operations*
*Researched: 2026-03-23*
