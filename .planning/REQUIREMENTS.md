# Requirements: Agend Ops

**Defined:** 2026-03-23
**Core Value:** Offload cognitive load — Claude handles email triage and task execution so Glen can focus on high-value decisions.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundation

- [x] **FOUND-01**: Google OAuth 2.0 configured in PRODUCTION mode for Gmail and Drive access
- [x] **FOUND-02**: Hardened Google Workspace MCP server (c0webster fork) installed and configured with security-stripped capabilities
- [x] **FOUND-03**: NDJSON data schema defined for activity feed, email summaries, and task records
- [ ] **FOUND-04**: CLAUDE.md project configuration with custom commands for common operations
- [x] **FOUND-05**: Git repo directory structure established (data/, dashboard/, scripts/)

### Email Triage

- [ ] **EMAIL-01**: Claude can scan Gmail inbox and retrieve unread and recent emails via MCP
- [ ] **EMAIL-02**: Emails categorized into 4 buckets: urgent, needs-response, informational, low-priority
- [ ] **EMAIL-03**: Starred emails surface as highest-priority "needs my action" queue
- [ ] **EMAIL-04**: Email priority classification based on sender importance (known clients vs unknown) and content intent
- [ ] **EMAIL-05**: Claude generates draft replies saved as local markdown and created as Gmail drafts
- [ ] **EMAIL-06**: Human-in-the-loop approval required before any response is sent (enforced by hardened MCP)
- [ ] **EMAIL-07**: Actionable items detected in emails — contracts, invoices, meeting requests, deadlines — with suggested next steps
- [ ] **EMAIL-08**: Email preprocessing pipeline strips HTML, signatures, and reply chains to control token costs

### Task Execution

- [ ] **TASK-01**: Manual task kickoff via natural language commands in Claude Code
- [ ] **TASK-02**: Claude proactively suggests tasks from email triage results ("Found a contract — want me to review it?")
- [ ] **TASK-03**: Document retrieval from Google Drive via MCP for task execution
- [ ] **TASK-04**: Document analysis — summarize key terms, flag risks, identify obligations, highlight deadlines
- [ ] **TASK-05**: Draft response or summary generation for completed task outcomes

### Visibility

- [ ] **VIS-01**: Activity feed logged as NDJSON (data/feed.jsonl) with timestamp, trigger, action, inputs, outputs, and outcome
- [ ] **VIS-02**: GitHub Pages dashboard auto-deployed from repo
- [ ] **VIS-03**: Dashboard displays: unread email count, starred queue, recent activity feed, pending task suggestions
- [ ] **VIS-04**: Dashboard is mobile-first and responsive — glanceable from phone

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Automation

- **AUTO-01**: Scheduled email triage via GitHub Actions (e.g., every 30 min on weekdays)
- **AUTO-02**: Auto-commit triage results and dashboard data after each scan
- **AUTO-03**: Google Drive one-way sync (repo to Drive) via rclone

### Productivity

- **PROD-01**: Daily task list with add/complete/prioritize operations
- **PROD-02**: POC tracker — status board for proof-of-concept experiments
- **PROD-03**: Invoice tracking — what needs to be billed, when, to whom
- **PROD-04**: Daily digest summary (in dashboard, not email)

### Mobile Commands

- **MOBL-01**: Telegram or Discord command channel for sending tasks from phone
- **MOBL-02**: Two-way approval workflow from mobile (approve/reject drafts)

### Intelligence

- **INTL-01**: Context accumulation — client history, past decisions stored in structured files
- **INTL-02**: Learning from triage corrections — improve categorization over time

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Autonomous email sending | Prompt injection risk — attacker embeds instructions in email. Hardened MCP enforces this. Graduate to auto-send only after proven accuracy. |
| Real-time push notifications | Adds infrastructure complexity, defeats cognitive load reduction purpose |
| Full calendar management | Separate complex domain (timezones, conflicts, attendees). Detect meeting requests in emails instead. |
| Native mobile app | Months of development for single-user read-only status. GitHub Pages + Telegram sufficient. |
| Multi-user / team features | Transforms personal tool into team platform. Auth, permissions, data isolation each a project. |
| Integration with every tool | Each integration is a maintenance surface. Gmail + Drive + GitHub only for v1. |
| Daily digest email | Building email sending for a tool meant to reduce email. Activity feed serves same purpose. |
| Unbounded conversational memory | Context growth is expensive and slow. Use structured summaries in git with bounded lookback. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| FOUND-04 | Phase 1 | Pending |
| FOUND-05 | Phase 1 | Complete |
| EMAIL-01 | Phase 2 | Pending |
| EMAIL-02 | Phase 2 | Pending |
| EMAIL-03 | Phase 2 | Pending |
| EMAIL-04 | Phase 2 | Pending |
| EMAIL-05 | Phase 2 | Pending |
| EMAIL-06 | Phase 2 | Pending |
| EMAIL-07 | Phase 2 | Pending |
| EMAIL-08 | Phase 2 | Pending |
| TASK-01 | Phase 3 | Pending |
| TASK-02 | Phase 3 | Pending |
| TASK-03 | Phase 3 | Pending |
| TASK-04 | Phase 3 | Pending |
| TASK-05 | Phase 3 | Pending |
| VIS-01 | Phase 4 | Pending |
| VIS-02 | Phase 4 | Pending |
| VIS-03 | Phase 4 | Pending |
| VIS-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 after roadmap creation*
