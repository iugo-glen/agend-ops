---
phase: 07-invoice-tracking
plan: 02
subsystem: commands
tags: [ndjson, invoicing, triage, briefing, email-detection]

# Dependency graph
requires:
  - phase: 07-invoice-tracking
    provides: "Invoice NDJSON schema (schemas/invoice-record.json), data file (data/invoices/active.jsonl), build script extension"
provides:
  - "Triage pipeline auto-creates invoice reminders for action_type 'invoice'"
  - "Daily briefing includes Invoice Status section with overdue/outstanding counts"
affects: [07-03, dashboard, briefing, triage]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Invoice auto-queue from triage: email detection -> reminder record", "Overdue computed in briefing (never stored)", "Invoice dedup via source_email_id"]

key-files:
  created: []
  modified:
    - .claude/commands/triage-inbox.md
    - .claude/commands/daily-briefing.md

key-decisions:
  - "Invoice action_type creates invoice reminder record instead of task record -- cleaner separation of concerns"
  - "Invoice dedup uses source_email_id (not task source_email) against data/invoices/active.jsonl"
  - "Invoice Status section placed between Your To-Dos and Key Deadlines in briefing for logical flow"

patterns-established:
  - "Invoice auto-queue path: triage detects action_type invoice -> best-effort field extraction -> append to active.jsonl"
  - "Briefing invoice section: compute overdue dynamically, show reminders needing action"

requirements-completed: [INV-03]

# Metrics
duration: 2min
completed: 2026-03-23
---

# Phase 7 Plan 2: Triage & Briefing Invoice Integration Summary

**Triage pipeline auto-creates invoice reminders from email detection, daily briefing shows Invoice Status section with overdue/outstanding amounts and reminder list**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-23T12:22:48Z
- **Completed:** 2026-03-23T12:25:14Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Triage pipeline creates invoice reminder records (not tasks) when action_type is "invoice"
- Invoice dedup via source_email_id prevents re-queuing on re-triage
- Best-effort extraction of client_name, project_code, amount from triage data per D-09
- Daily briefing shows Invoice Status with overdue/outstanding counts and total amounts
- Both commands include data/invoices/ and docs/invoices.json in git add

## Task Commits

Each task was committed atomically:

1. **Task 1: Triage pipeline invoice auto-queue** - `d5f94f6` (feat)
2. **Task 2: Daily briefing invoice section** - `9070c48` (feat)

## Files Created/Modified
- `.claude/commands/triage-inbox.md` - Added invoice auto-queue path with dedup, ID generation, field extraction, and reminder output
- `.claude/commands/daily-briefing.md` - Added Invoice Status section, invoice counts in feed entry, invoice data in git add

## Decisions Made
- Invoice action_type creates invoice reminder record instead of task record -- the old "invoice" -> "document-summary" task mapping is replaced by a dedicated invoice path
- Invoice dedup checks source_email_id in data/invoices/active.jsonl (separate from task dedup in data/tasks/active.jsonl)
- Invoice Status section placed between "Your To-Dos" and "Key Deadlines" in briefing for logical flow (human tasks -> invoices -> deadlines)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Triage and briefing integration complete, ready for dashboard invoice tab (07-03)
- Invoice data flows: email detection -> triage-inbox creates reminder -> briefing shows status -> dashboard displays tab
- Xero sync from 07-01 enriches the same data that triage creates and briefing reads

## Self-Check: PASSED

All 2 modified files verified present. Both task commits verified in git log (d5f94f6, 9070c48).

---
*Phase: 07-invoice-tracking*
*Completed: 2026-03-23*
