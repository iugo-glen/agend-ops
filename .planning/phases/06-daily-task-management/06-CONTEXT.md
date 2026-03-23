# Phase 6: Daily Task Management - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a personal to-do system alongside the existing Claude task system. /todo command with full features (priorities, due dates, categories, recurring). Linked to /task — to-dos can spawn Claude tasks. Separate briefing sections. New dashboard "Today" tab. No invoice tracking, no Telegram — just to-dos.

</domain>

<decisions>
## Implementation Decisions

### Todo Operations
- **D-01:** Full-featured to-dos: text + priority (high/normal/low) + optional due date + category (business/personal/marketing) + recurring support
- **D-02:** Syntax: `/todo book flight to Sydney by Friday !high #business`
- **D-03:** Completion via text match OR number: `/todo done book flight` or `/todo done 3`
- **D-04:** Operations: add, complete, list, prioritize (matching TODO-01 requirement)

### Todo vs Task Relationship
- **D-05:** Separate systems — to-dos are human action items, tasks are Claude-executable work. Different NDJSON files, different commands.
- **D-06:** Linked — a to-do can spawn a /task (e.g., "research flight options" to-do spawns Claude task) and a task completion can resolve a related to-do
- **D-07:** Daily briefing shows separate sections: "Your to-dos" + "Claude tasks" — clear distinction between human and AI work

### Dashboard "Today" Tab
- **D-08:** Claude's discretion on tab content — design the best "Today" view based on available data (to-dos, pending tasks, deadlines)

### Claude's Discretion
- Exact /todo command syntax parsing (how to detect priority, due date, category from natural language)
- Todo NDJSON schema field design (follows established pattern from task-record.json)
- How recurring to-dos work (daily reset, weekly, custom)
- Dashboard "Today" tab layout and what data to combine
- How to-do ↔ task linking works mechanically (field references, spawn syntax)
- Build script extension for todos.json

</decisions>

<specifics>
## Specific Ideas

- To-dos should feel lightweight — not a project management tool, just "things Glen needs to do today"
- The /todo command should be as fast as typing a thought — minimal friction to add an item
- Categories help Glen see at a glance: is my day dominated by business ops, marketing, or personal stuff?
- Recurring to-dos (daily standup, weekly invoice review) save repetitive entry

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing patterns to follow
- `schemas/task-record.json` — Task schema pattern to replicate for to-dos
- `.claude/commands/task.md` — /task command pattern (4 modes) to follow for /todo
- `.claude/commands/daily-briefing.md` — Briefing command that needs to-do integration (TODO-03)
- `scripts/build-dashboard-data.sh` — Needs todos.json compilation added
- `docs/index.html` — Dashboard that needs "Today" tab added

### Project context
- `.planning/PROJECT.md` — Core value, constraints
- `.planning/REQUIREMENTS.md` — TODO-01 through TODO-04 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `schemas/task-record.json` — Schema template to replicate
- `.claude/commands/task.md` — Command pattern (add, list, run, complete modes)
- `scripts/build-dashboard-data.sh` — Already compiles feed, tasks, triage, briefing JSON
- `scripts/validate-data.sh` — Schema validation pattern
- `docs/index.html` — Dashboard with tab system ready for new tabs

### Established Patterns
- NDJSON append-only in data/ directories
- Schema-validated records with jq
- Commands with YAML frontmatter and allowed-tools
- Dashboard tabs (mobile) / columns (desktop)
- Build script compiles NDJSON → JSON in docs/

### Integration Points
- data/todos/active.jsonl — new data file
- schemas/todo-record.json — new schema
- .claude/commands/todo.md — new command
- .claude/commands/daily-briefing.md — add to-do section
- docs/index.html — add "Today" tab
- scripts/build-dashboard-data.sh — add todos.json compilation

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-daily-task-management*
*Context gathered: 2026-03-23*
