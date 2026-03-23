# Roadmap: Agend Ops

## Overview

Agend Ops delivers cognitive load relief in four phases: first lay the infrastructure foundation (OAuth, MCP, data schema), then build interactive email triage (the core value proposition), extend into task execution and draft generation (acting on what triage surfaces), and finally ship a mobile-friendly dashboard for glanceable visibility. Each phase delivers a complete, verifiable capability. The dashboard can run in parallel with earlier phases using mock data, but is sequenced last because email triage and task execution are the primary value drivers.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Google OAuth, hardened MCP server, data schema, repo structure, and project configuration
- [ ] **Phase 2: Email Triage** - Claude scans inbox, categorizes emails, surfaces starred queue, generates drafts, detects actionable items
- [ ] **Phase 3: Task Execution** - Manual and proactive task kickoff, document retrieval from Drive, analysis, and response generation
- [ ] **Phase 4: Dashboard** - GitHub Pages mobile-first dashboard showing email status, starred queue, activity feed, and pending tasks

## Phase Details

### Phase 1: Foundation
**Goal**: Glen has a working Claude Code environment with verified Gmail/Drive access, a hardened MCP server that cannot send emails, and a data schema ready to receive activity logs
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05
**Success Criteria** (what must be TRUE):
  1. Claude can read Gmail messages and list inbox via MCP without token expiry (production OAuth)
  2. Claude can access Google Drive files via MCP
  3. The MCP server has no send, share, or filter-creation capabilities (hardened fork verified)
  4. NDJSON schema files exist with documented field definitions for feed, email summaries, and task records
  5. Custom Claude Code commands (e.g., /triage-inbox) are defined in CLAUDE.md and executable
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md -- Directory structure, .gitignore, NDJSON schemas, and utility scripts
- [x] 01-02-PLAN.md -- Google OAuth setup and hardened MCP server installation
- [x] 01-03-PLAN.md -- CLAUDE.md enhancement and custom slash commands

### Phase 2: Email Triage
**Goal**: Glen can run a single command and get his inbox categorized into priority buckets with starred emails surfaced first, draft replies generated, and actionable items flagged -- all logged to the activity feed
**Depends on**: Phase 1
**Requirements**: EMAIL-01, EMAIL-02, EMAIL-03, EMAIL-04, EMAIL-05, EMAIL-06, EMAIL-07, EMAIL-08
**Success Criteria** (what must be TRUE):
  1. Glen runs /triage-inbox and sees unread emails categorized into urgent, needs-response, informational, and low-priority buckets
  2. Starred emails appear as highest-priority items in a separate "needs my action" queue
  3. Claude generates draft replies as local markdown files and creates corresponding Gmail drafts -- no email is ever sent automatically
  4. Actionable items (contracts, invoices, meeting requests, deadlines) are detected and presented with suggested next steps
  5. Every triage action is logged to data/feed.jsonl with timestamp, trigger, action, and outcome
**Plans:** 2 plans

Plans:
- [x] 02-01-PLAN.md -- Triage data contracts: schema extensions, client domain seed list, email-scanner subagent definition
- [ ] 02-02-PLAN.md -- Triage engine: full subagent prompt, triage-inbox command update, live verification

### Phase 3: Task Execution
**Goal**: Glen can delegate tasks to Claude ("review the contract Sarah sent", "prep for Thursday meeting") and receive analyzed documents, summaries, and draft responses
**Depends on**: Phase 2
**Requirements**: TASK-01, TASK-02, TASK-03, TASK-04, TASK-05
**Success Criteria** (what must be TRUE):
  1. Glen can kick off tasks via natural language in Claude Code and see them execute to completion
  2. After triage, Claude proactively suggests tasks based on detected actionable items ("Found a contract -- want me to review it?")
  3. Claude retrieves documents from Google Drive and produces analysis (key terms, risks, obligations, deadlines)
  4. Completed tasks produce a draft response or summary that Glen can review and use
**Plans**: TBD

### Phase 4: Dashboard
**Goal**: Glen can check his phone and see at a glance: unread email count, starred queue, recent activity, and pending task suggestions -- without opening Claude Code
**Depends on**: Phase 1
**Requirements**: VIS-01, VIS-02, VIS-03, VIS-04
**Success Criteria** (what must be TRUE):
  1. Activity feed is logged as NDJSON and compiled to JSON for dashboard consumption
  2. GitHub Pages dashboard auto-deploys from the repo's docs/ directory
  3. Dashboard displays unread email count, starred queue items, recent activity feed entries, and pending task suggestions
  4. Dashboard is readable and usable on a phone screen without horizontal scrolling or tiny text
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete | 2026-03-23 |
| 2. Email Triage | 0/2 | Planned | - |
| 3. Task Execution | 0/? | Not started | - |
| 4. Dashboard | 0/? | Not started | - |
