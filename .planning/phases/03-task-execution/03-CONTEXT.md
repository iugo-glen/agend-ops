# Phase 3: Task Execution - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Glen delegates tasks to Claude via /task command and receives analyzed documents, summaries, and draft responses. Triage-detected actions auto-queue as pending tasks. Results saved to repo and displayed inline. Gmail drafts created for email-triggered tasks. No dashboard, no scheduled automation — just the task execution engine.

</domain>

<decisions>
## Implementation Decisions

### Task Types
- **D-01:** Four task types in v1: contract review, meeting prep, document summary, draft communications
- **D-02:** Light write permissions — tasks can read emails/Drive, analyze, produce drafts/summaries, AND create files in the repo (analysis docs, task records) and update task records
- **D-03:** Contract review: pull contract, summarize key terms, flag unusual clauses, identify obligations and deadlines
- **D-04:** Meeting prep: gather context about attendees/topic, draft talking points or agenda, pull relevant docs
- **D-05:** Document summary: any doc from Drive/email — summarize, extract key points, highlight action items
- **D-06:** Draft comms: draft an email, proposal response, or client communication based on context

### Proactive Flow
- **D-07:** Triage-detected actions auto-queue as pending tasks in data/tasks/active.jsonl
- **D-08:** Glen reviews the queue and approves which to execute (not auto-execute)
- **D-09:** Manual task kickoff via /task command (structured invocation)

### Document Analysis
- **D-10:** Executive summary depth by default — key terms, parties, dates, obligations, red flags, one page max
- **D-11:** Output saved to repo (data/tasks/{task-id}/) AND displayed inline in Claude Code

### Task Lifecycle
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

</decisions>

<specifics>
## Specific Ideas

- Proactive suggestions from triage ("Contract from Acme Corp — review by Friday") should feel like an assistant briefing, not a task management system
- The /task command should be conversational: `/task review the contract Sarah sent` not `/task --type=contract --source=email --from=sarah`
- Task output should be immediately useful — Glen should be able to glance at it and act, not wade through analysis

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data schemas (from Phase 1)
- `schemas/task-record.json` — Task record schema, defines required fields
- `schemas/feed-entry.json` — Activity feed schema for task events

### Commands (from Phase 1)
- `.claude/commands/task.md` — Existing /task command to be enhanced
- `.claude/commands/status.md` — /status command that should show pending tasks

### Agents (from Phase 2)
- `.claude/agents/email-scanner.md` — Email triage agent that produces action items for auto-queuing

### Project context
- `.planning/PROJECT.md` — Core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — TASK-01 through TASK-05 acceptance criteria
- `.planning/phases/02-email-triage/02-CONTEXT.md` — Triage decisions (action detection, client tagging)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `schemas/task-record.json` — Pre-defined schema for task records with status, description fields
- `.claude/commands/task.md` — Stub command ready to be implemented
- `.claude/commands/status.md` — Status command that can show pending tasks
- `.claude/agents/email-scanner.md` — Triage agent that detects action items (pattern to follow for task executor)
- `data/config/clients.jsonl` — Client domain list for enriching task context
- `scripts/validate-data.sh` — Can validate task records against schema

### Established Patterns
- Subagent with YAML frontmatter and MCP tool scoping (from email-scanner)
- NDJSON append-only for task records (data/tasks/active.jsonl)
- Activity feed logging to data/feed.jsonl
- Gmail draft creation via hardened MCP (draft_gmail_message)
- Client domain matching from seed list

### Integration Points
- Hardened Google Workspace MCP — gmail_read, drive_list, drive_read for document retrieval
- data/tasks/active.jsonl — task queue (triage writes, /task writes, executor reads)
- data/tasks/{task-id}/ — task output directory
- data/feed.jsonl — activity feed for task events
- Triage output (data/triage/) — source of auto-queued action items

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-task-execution*
*Context gathered: 2026-03-23*
