# Requirements: Agend Ops

**Defined:** 2026-03-23
**Core Value:** Offload cognitive load -- Claude handles email triage and task execution so Glen can focus on high-value decisions.

## v1 Requirements (Complete)

All 22 v1 requirements delivered across 4 phases. See PROJECT.md Validated section for full list.

## v2 Requirements

Requirements for milestone v2.0: Autonomous Operations.

### Scheduling

- [ ] **SCHED-01**: Claude Desktop recurring task runs /triage-inbox on a configurable schedule (test MCP access, document fallback to GitHub Actions)
- [ ] **SCHED-02**: Dashboard data auto-rebuilds after each scheduled triage run
- [ ] **SCHED-03**: Daily briefing generated each morning -- email status, pending tasks, today's to-dos, key deadlines

### Daily Task Management

- [ ] **TODO-01**: /todo command supports add, complete, list, and prioritize operations
- [ ] **TODO-02**: To-do items stored in NDJSON (data/todos/active.jsonl) with schema
- [ ] **TODO-03**: Daily briefing integrates to-do items alongside email and task status
- [ ] **TODO-04**: Dashboard "Today" tab shows daily to-dos with completion status

### Invoice Tracking

- [ ] **INV-01**: /invoice command supports create, list, mark-paid, and list-overdue operations
- [ ] **INV-02**: Invoice records stored in NDJSON (data/invoices/active.jsonl) with schema
- [ ] **INV-03**: Triage pipeline auto-detects invoice requests and creates invoice records
- [ ] **INV-04**: Dashboard "Invoices" tab shows pending, overdue, and recently paid invoices

### Telegram Mobile Commands

- [ ] **TELE-01**: Telegram channel configured with Claude Code Channels plugin
- [ ] **TELE-02**: Two-way command execution -- /triage, /task, /todo, /status, /invoice from Telegram
- [ ] **TELE-03**: Approval flow -- Claude sends draft previews to Telegram, Glen approves/rejects from phone

## Future Requirements

Deferred beyond v2. Tracked but not in current roadmap.

### Intelligence

- **INTL-01**: Context accumulation -- client history, past decisions stored in structured files
- **INTL-02**: Learning from triage corrections -- improve categorization over time

### Productivity

- **PROD-01**: POC tracker -- status board for proof-of-concept experiments
- **PROD-02**: Google Drive sync -- repo to Drive via rclone

## Out of Scope

| Feature | Reason |
|---------|--------|
| Autonomous email sending | Security risk -- hardened MCP enforces human-in-the-loop |
| Real-time push notifications | Complexity without proportional value -- Telegram + dashboard sufficient |
| Full calendar management | Separate complex domain -- detect meeting requests instead |
| Native mobile app | GitHub Pages + Telegram covers mobile needs |
| Multi-user / team features | Single-user tool -- share dashboard URL if needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCHED-01 | Phase 5 | Pending |
| SCHED-02 | Phase 5 | Pending |
| SCHED-03 | Phase 5 | Pending |
| TODO-01 | Phase 6 | Pending |
| TODO-02 | Phase 6 | Pending |
| TODO-03 | Phase 6 | Pending |
| TODO-04 | Phase 6 | Pending |
| INV-01 | Phase 7 | Pending |
| INV-02 | Phase 7 | Pending |
| INV-03 | Phase 7 | Pending |
| INV-04 | Phase 7 | Pending |
| TELE-01 | Phase 8 | Pending |
| TELE-02 | Phase 8 | Pending |
| TELE-03 | Phase 8 | Pending |

**Coverage:**
- v2 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 after v2.0 roadmap creation*
