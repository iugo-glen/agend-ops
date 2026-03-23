---
phase: 06-daily-task-management
plan: 01
subsystem: commands
tags: [todo, ndjson, jq, slash-command, schema]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "NDJSON data schemas, directory structure, build/validate scripts"
  - phase: 03-task-execution
    provides: "/task command pattern, task-record schema pattern"
provides:
  - "schemas/todo-record.json -- JSON Schema for to-do records"
  - ".claude/commands/todo.md -- /todo command with add, complete, list, prioritize, show modes"
  - "data/todos/ directory for to-do NDJSON storage"
  - "docs/todos.json compilation in build pipeline"
  - "feed-entry.json 'todo' type for activity logging"
affects: [06-02-briefing-dashboard, 07-invoice-tracking]

# Tech tracking
tech-stack:
  added: []
  patterns: ["natural language parsing for /todo (priority, category, due date, recurring extraction)"]

key-files:
  created:
    - schemas/todo-record.json
    - .claude/commands/todo.md
    - data/todos/.gitkeep
    - docs/todos.json
  modified:
    - schemas/feed-entry.json
    - scripts/build-dashboard-data.sh
    - scripts/validate-data.sh

key-decisions:
  - "Followed D-01 through D-07 from 06-CONTEXT.md without modification"
  - "Todo schema uses 11 fields with additionalProperties:false matching task-record pattern"

patterns-established:
  - "Todo command mirrors task command pattern: YAML frontmatter, mode detection from arguments, jq for NDJSON operations"
  - "Natural language token extraction: !priority, #category, due/by date clauses, recurring keywords"

requirements-completed: [TODO-01, TODO-02]

# Metrics
duration: 3min
completed: 2026-03-23
---

# Phase 6 Plan 1: Todo Schema + Command + Pipeline Summary

**To-do record schema with 11 fields, 5-mode /todo slash command (show/list/complete/prioritize/add with natural language parsing), and build+validation pipeline for todos.json**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-23T11:04:10Z
- **Completed:** 2026-03-23T11:07:38Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created todo-record.json schema with all 11 fields (id, ts, status, text, priority, trigger, due_date, category, recurring, completed_at, linked_task_id)
- Created /todo command (301 lines) with 5 modes: show today's to-dos, list with filters, complete by number/text, reprioritize, add with natural language parsing
- Extended build-dashboard-data.sh to compile todos.json alongside existing feed/tasks/triage/briefing
- Extended validate-data.sh to check todos/active.jsonl for valid NDJSON
- Added "todo" type to feed-entry.json enum for activity feed logging

## Task Commits

Each task was committed atomically:

1. **Task 1: Create todo-record.json schema and /todo command** - `3e5bdbb` (feat)
2. **Task 2: Extend build and validation scripts for todos.json** - `fb29a6f` (feat)

## Files Created/Modified
- `schemas/todo-record.json` - JSON Schema draft-07 for to-do records (11 fields, additionalProperties: false)
- `schemas/feed-entry.json` - Added "todo" to type enum array
- `.claude/commands/todo.md` - 5-mode /todo command with YAML frontmatter and allowed-tools
- `data/todos/.gitkeep` - Directory placeholder for to-do NDJSON storage
- `scripts/build-dashboard-data.sh` - Added todos.json compilation block
- `scripts/validate-data.sh` - Added active todos validation line
- `docs/todos.json` - Generated empty array (initial state)

## Decisions Made
None - followed plan as specified. All decisions (D-01 through D-07) from 06-CONTEXT.md applied directly.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data paths are wired (todos.json compiles from active.jsonl, validation checks active.jsonl, feed logging on add/complete).

## Next Phase Readiness
- To-do schema and command ready for Plan 02 (briefing integration + dashboard "Today" tab)
- Build pipeline produces todos.json for dashboard consumption
- Feed logging supports "todo" type for briefing aggregation

## Self-Check: PASSED

- All 7 files verified present on disk
- Commits 3e5bdbb and fb29a6f verified in git log

---
*Phase: 06-daily-task-management*
*Completed: 2026-03-23*
