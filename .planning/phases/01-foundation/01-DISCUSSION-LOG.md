# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 1-Foundation
**Areas discussed:** Google Account, Data Schema, Custom Commands, Directory Layout

---

## Google Account

| Option | Description | Selected |
|--------|-------------|----------|
| Personal Gmail | Your personal email — mix of business and personal | |
| Workspace account | An Agend Systems Google Workspace account | ✓ |
| Both eventually | Start with one, add the other later | |

**User's choice:** Workspace account
**Notes:** Glen is Workspace admin, can set OAuth to production mode directly. No Google verification needed (under 100 users).

### Follow-up: Admin access

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, I'm admin | Can create OAuth credentials, set consent screen to production | ✓ |
| No / not sure | Someone else manages it | |
| It's just Gmail | Regular Gmail with custom domain, not full Workspace | |

**User's choice:** Yes, I'm admin

---

## Data Schema

### Feed detail level

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal (Recommended) | timestamp, type, summary, status — lean entries | |
| Rich | Full inputs/outputs, related emails, metadata | |
| You decide | Claude picks the right balance | ✓ |

**User's choice:** You decide

### Email storage

| Option | Description | Selected |
|--------|-------------|----------|
| Separate files | One JSONL file per triage run, feed just links to it | ✓ |
| Inline in feed | Email summaries embedded directly in feed entries | |
| You decide | Claude picks based on dashboard needs | |

**User's choice:** Separate files

### Task records

| Option | Description | Selected |
|--------|-------------|----------|
| Individual files | Each task gets its own file | |
| Single JSONL | All tasks in data/tasks.jsonl — append-only | |
| You decide | Claude picks the right structure | ✓ |

**User's choice:** You decide

---

## Custom Commands

### Triage command design

| Option | Description | Selected |
|--------|-------------|----------|
| Full triage | One command does everything | |
| Staged triage | Separate scan, draft, actions commands | |
| You decide | Claude designs the best command flow | ✓ |

**User's choice:** You decide

### Other commands

| Option | Description | Selected |
|--------|-------------|----------|
| /status | Quick summary: unread count, pending tasks, recent activity | ✓ |
| /task <description> | Kick off a task | ✓ |
| /feed | Show recent activity feed entries | ✓ |
| You decide | Claude designs the command set based on requirements | ✓ |

**User's choice:** All four — /status, /task, /feed are definite, Claude designs the full set

---

## Directory Layout

### Repo organization

| Option | Description | Selected |
|--------|-------------|----------|
| Flat data/ | Everything under one data directory | |
| Domain folders | Separate top-level directories by domain | |
| You decide | Claude designs the layout | ✓ |

**User's choice:** You decide

### Dashboard location

| Option | Description | Selected |
|--------|-------------|----------|
| docs/ (Recommended) | GitHub Pages from /docs on main branch | ✓ |
| dashboard/ | Separate directory, configure GitHub Pages | |
| You decide | Claude picks best location | |

**User's choice:** docs/ (Recommended)

---

## Claude's Discretion

- Activity feed entry detail level
- Task record structure
- Top-level directory organization
- Triage command design (full vs staged)
- Additional commands beyond /status, /task, /feed
- NDJSON field definitions

## Deferred Ideas

None — discussion stayed within phase scope
