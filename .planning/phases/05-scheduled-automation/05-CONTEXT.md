# Phase 5: Scheduled Automation - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up Claude Desktop recurring tasks to run /triage-inbox on a schedule, auto-rebuild dashboard data, and generate a daily morning briefing. Test MCP access — if Desktop tasks can't use hardened-workspace MCP (bug #36327), document GitHub Actions as fallback. No new data domains (to-dos, invoices) — just automation of existing capabilities plus the briefing.

</domain>

<decisions>
## Implementation Decisions

### Schedule Timing
- **D-01:** Triage runs every 2 hours during business hours on weekdays (approximately 7am, 9am, 11am, 1pm, 3pm, 5pm ACST)
- **D-02:** Timezone: ACST (UTC+9:30) — Adelaide, South Australia
- **D-03:** Weekdays only (Monday–Friday). No weekend runs.
- **D-04:** Try Claude Desktop recurring tasks first. If MCP access fails (bug #36327), document GitHub Actions as the fallback approach.

### Daily Briefing
- **D-05:** Morning briefing contains four sections: email summary (counts by bucket, key starred items), pending tasks (auto-queued + approvals), key deadlines (next 48 hours from action detection), yesterday recap (tasks completed, drafts created, triage stats)
- **D-06:** Briefing available in three places: separate daily file (data/briefings/YYYY-MM-DD.md), summary on dashboard, and feed entry
- **D-07:** Briefing generated as the first run of the day (7am triage also generates briefing)

### Failure Handling
- **D-08:** Dashboard staleness indicator (already exists from Phase 4) — if "Last updated" shows >4 hours on a weekday, something's wrong
- **D-09:** Failed scheduled runs log an error-level feed entry visible in /feed and dashboard activity
- **D-10:** No external alerting infrastructure — monitoring via dashboard + feed is sufficient for single-user system

### Claude's Discretion
- Claude Desktop /schedule configuration syntax and options
- Briefing markdown formatting and section structure
- How to detect "first run of the day" for briefing generation vs regular triage
- Dashboard summary card design for briefing content
- Error feed entry format for failed runs
- GitHub Actions fallback workflow file design (if needed)

</decisions>

<specifics>
## Specific Ideas

- The briefing should feel like a morning newspaper — scan it with coffee, know what's on your plate
- "Key deadlines" section is the most actionable part — surface deadlines from action_items in triage records
- Dashboard staleness is the simplest monitoring — no need to overcomplicate it for a single-user system
- The 2-hour cadence keeps the dashboard fresh enough without burning tokens constantly

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing commands (from v1)
- `.claude/commands/triage-inbox.md` — Command that will be scheduled (includes auto-rebuild step)
- `.claude/commands/status.md` — Status command that may need briefing integration
- `.claude/commands/feed.md` — Feed command for viewing triage/briefing entries

### Agents (from v1)
- `.claude/agents/email-scanner.md` — Triage agent dispatched by /triage-inbox

### Data infrastructure (from v1)
- `scripts/build-dashboard-data.sh` — Dashboard data compiler (already wired into /triage-inbox)
- `schemas/feed-entry.json` — Feed entry schema for briefing/error entries
- `docs/index.html` — Dashboard that displays feed and will show briefing summary

### Project context
- `.planning/PROJECT.md` — Core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — SCHED-01 through SCHED-03 acceptance criteria
- `.planning/research/ARCHITECTURE.md` — v2 architecture research (scheduling section)
- `.planning/research/PITFALLS.md` — Scheduling pitfalls (Desktop MCP bug, token costs)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `/triage-inbox` command already runs triage end-to-end with auto-rebuild
- `build-dashboard-data.sh` already compiles all NDJSON to dashboard JSON
- Feed entry schema supports different types (triage, task — briefing/error types can be added)
- Dashboard already has "Last updated" prominence and activity feed column

### Established Patterns
- NDJSON append-only for new data (briefings would follow same pattern)
- Subagent dispatch for complex operations
- Activity feed logging for all operations
- Auto-rebuild + commit after data-modifying commands

### Integration Points
- Claude Desktop /schedule command — new integration point
- data/briefings/ — new directory for daily briefing files
- docs/index.html — may need a briefing summary section or "Today" card
- data/feed.jsonl — briefing and error entries land here

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-scheduled-automation*
*Context gathered: 2026-03-23*
