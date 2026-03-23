# Phase 3: Task Execution - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 3-Task Execution
**Areas discussed:** Task Types, Proactive Flow, Document Analysis, Task Lifecycle

---

## Task Types

### Task scope

| Option | Description | Selected |
|--------|-------------|----------|
| Contract review | Pull contract, summarize, flag clauses, identify obligations | ✓ |
| Meeting prep | Gather context, draft talking points, pull relevant docs | ✓ |
| Document summary | Any doc — summarize, extract key points, highlight actions | ✓ |
| Draft comms | Draft email, proposal response, client communication | ✓ |

**User's choice:** All four types

### Task permissions

| Option | Description | Selected |
|--------|-------------|----------|
| Read + draft only | Read emails/Drive, analyze, produce drafts. No modifications. | |
| Light writes | Also create repo files and update task records | ✓ |
| You decide | Claude determines per task type | |

**User's choice:** Light writes

---

## Proactive Flow

### After triage detects action

| Option | Description | Selected |
|--------|-------------|----------|
| List in briefing | Show in triage output, manual /task later | |
| Ask inline | Claude asks "Want me to do X?" after triage | |
| Auto-queue | Detected actions become pending tasks, Glen approves from queue | ✓ |
| You decide | Claude designs flow | |

**User's choice:** Auto-queue

### Manual trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Natural language | Type freely in Claude Code | |
| /task command | Structured: /task review Acme contract | ✓ |
| Both | Either works | |

**User's choice:** /task command

---

## Document Analysis

### Analysis depth

| Option | Description | Selected |
|--------|-------------|----------|
| Executive summary | Key terms, parties, dates, obligations, red flags — one page max | ✓ |
| Full analysis | Section-by-section, risk assessment, comparison | |
| Adaptive | Summary default, full if risks detected | |

**User's choice:** Executive summary

### Output destination

| Option | Description | Selected |
|--------|-------------|----------|
| Repo files | Save to data/tasks/{task-id}/ | |
| Inline only | Display in Claude Code only | |
| Both | Display inline AND save to repo | ✓ |

**User's choice:** Both

---

## Task Lifecycle

### On completion

| Option | Description | Selected |
|--------|-------------|----------|
| Log + notify | Log to feed, results in repo | |
| Log + draft | Log to feed AND create Gmail draft if email-triggered | ✓ |
| You decide | Per task type | |

**User's choice:** Log + draft

### On failure

| Option | Description | Selected |
|--------|-------------|----------|
| Mark blocked | Set status to blocked, surface in /status | |
| Ask immediately | Ask Glen if interactive, block if queued | |
| You decide | Claude handles appropriately | ✓ |

**User's choice:** You decide

---

## Claude's Discretion

- Task executor subagent design
- Natural language parsing for task descriptions
- Auto-queued task presentation in /status
- Failure handling per task type
- Document retrieval strategy (Drive search vs email attachments)
- Task ID generation

## Deferred Ideas

None — discussion stayed within phase scope
