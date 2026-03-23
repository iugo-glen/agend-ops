---
phase: 06-daily-task-management
plan: 02
subsystem: ui
tags: [dashboard, briefing, todo, jq, html, css, javascript]

# Dependency graph
requires:
  - phase: 06-daily-task-management
    provides: "todo-record.json schema, /todo command, data/todos/ storage, docs/todos.json build"
  - phase: 05-scheduled-automation
    provides: "daily-briefing.md command structure with 4 sections"
  - phase: 04-dashboard
    provides: "docs/index.html Kanban dashboard with 4-column layout and tab navigation"
provides:
  - "Daily briefing 'Your To-Dos' section with priority sorting and due-date flags"
  - "Dashboard 'Today' tab combining to-dos and pending Claude tasks"
  - "Todo card rendering: checkbox, priority pill, due badge, category tag"
  - "5-column desktop dashboard grid"
  - "Summary bar to-do count pill"
affects: [07-invoice-tracking, 08-telegram-mobile]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Today tab as default view combining multiple data sources", "Section-label dividers for grouped card layouts", "Todo card component with priority/due-date/category visual indicators"]

key-files:
  modified:
    - .claude/commands/daily-briefing.md
    - docs/index.html

key-decisions:
  - "Today tab placed as first/default tab instead of Starred"
  - "Today column combines to-dos and Claude tasks with section dividers per D-08"
  - "Briefing to-do section placed between Pending Tasks and Key Deadlines per D-07"

patterns-established:
  - "Section-label pattern: uppercase labels with count dividing card groups within a single column"
  - "Combined view pattern: multiple data sources merged into one tab with labeled sections"

requirements-completed: [TODO-03, TODO-04]

# Metrics
duration: 5min
completed: 2026-03-23
---

# Phase 6 Plan 2: Briefing Todo Integration + Dashboard Today Tab Summary

**Daily briefing gains 'Your To-Dos' section with priority/due-date queries; dashboard gains default 'Today' tab combining to-do cards and Claude tasks in a 5-column layout**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-23T11:15:00Z
- **Completed:** 2026-03-23T11:25:41Z
- **Tasks:** 3 (2 auto + 1 visual verification checkpoint)
- **Files modified:** 2

## Accomplishments
- Added "Your To-Dos" section to daily briefing command with jq queries for active.jsonl, priority sorting, and due-date flagging (overdue/today)
- Added "Today" tab as the default dashboard view combining YOUR TO-DOS and CLAUDE TASKS sections with section-label dividers
- Built todo card component with checkbox, priority pill (high/normal/low), due badge (overdue/today), and category tag -- all using textContent-only XSS-safe rendering
- Extended desktop grid to 5 columns and added summary bar to-do count pill

## Task Commits

Each task was committed atomically:

1. **Task 1: Add to-do section to daily briefing command** - `9974979` (feat)
2. **Task 2: Add Today tab to dashboard** - `7b51890` (feat)
3. **Task 3: Verify dashboard Today tab renders correctly** - checkpoint:human-verify (approved)

## Files Created/Modified
- `.claude/commands/daily-briefing.md` - Added "Your To-Dos" section (step 4e) with jq queries for active todos, priority sorting, due-date flagging; updated briefing template and feed entry details with active_todos count; updated git add to include data/todos/
- `docs/index.html` - Added Today tab (default), Today column with section labels, todo card CSS (priority pills, due badges, category tags, checkbox), createTodoCard() function, todos.json fetch in Promise.allSettled, summary bar to-do count pill, 5-column desktop grid

## Decisions Made
- Today tab placed as first/default tab (replacing Starred as default) -- most actionable view for daily use
- Briefing to-do section positioned between "Pending Tasks" and "Key Deadlines" -- creates clear separation between human to-dos and Claude tasks per D-07
- Today column combines to-dos and Claude tasks with labeled sections per D-08 -- single "what needs attention" view

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data paths are wired. Dashboard fetches todos.json at load, briefing queries active.jsonl, and both render gracefully when no to-dos exist (empty state messages).

## Next Phase Readiness
- Phase 6 complete: all 4 requirements (TODO-01 through TODO-04) delivered
- Dashboard pattern established for adding additional tabs (Phase 7: Invoices tab)
- Briefing pattern established for adding additional sections (Phase 7: Invoice summary)
- Desktop grid can accommodate a 6th column if needed for invoices

## Self-Check: PASSED

- All 2 modified files verified present on disk
- Commits 9974979 and 7b51890 verified in git log
- SUMMARY.md created at expected path

---
*Phase: 06-daily-task-management*
*Completed: 2026-03-23*
