# Phase 4: Dashboard - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a GitHub Pages dashboard that Glen can check on his phone for a glanceable view of: unread email count, starred queue, recent activity feed, and pending task suggestions. Static HTML/CSS/JS, no framework. Data compiled from NDJSON to JSON by build script. No backend, no auth — privacy via private repo.

</domain>

<decisions>
## Implementation Decisions

### Layout & Density
- **D-01:** Status board layout — Kanban-style columns: Starred | Urgent | Pending Tasks | Recent Activity. Data-dense, everything visible at once.
- **D-02:** Medium item density — subject, sender, first line of summary, priority badge. No tap needed for most items.
- **D-03:** Mobile-first responsive design — columns stack vertically on phone, expand horizontally on desktop.

### Visual Style
- **D-04:** System auto dark/light mode — follows phone's prefers-color-scheme setting
- **D-05:** Notion-style aesthetics — content-focused, warm, readable. Less tool-like, more document-like. Clean typography, subtle borders, rounded corners.
- **D-06:** Plain HTML/CSS/JS — no framework, no build step. Claude generates directly.

### Data Freshness
- **D-07:** Auto-rebuild after triage/task commands — /triage-inbox and /task automatically run build-dashboard-data.sh and commit
- **D-08:** Manual rebuild also available (scripts/build-dashboard-data.sh)
- **D-09:** Prominent "Last updated" timestamp at the top of the dashboard

### Privacy
- **D-10:** Private GitHub repo — use GitHub Pro/Team for private repo with GitHub Pages. Full data visible (client names, email subjects) since access is restricted.

### Claude's Discretion
- Exact HTML structure and CSS styling within Notion-style guidelines
- Column widths and breakpoints for responsive layout
- Color palette for dark/light modes
- How summary cards display numbers (badges, counts, etc.)
- Animation/transition choices (if any — keep minimal)
- Favicon and page title

</decisions>

<specifics>
## Specific Ideas

- The dashboard should feel like checking a Notion page on your phone — warm, readable, not clinical
- "Last updated: 2 hours ago" should be prominent enough that you notice if data is stale
- Status board columns should prioritize what needs attention (Starred first, then Urgent)
- No JavaScript frameworks — Claude generates vanilla HTML/CSS/JS that GitHub Pages serves directly

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data contracts (from Phase 1)
- `schemas/feed-entry.json` — Activity feed schema, dashboard reads compiled JSON
- `schemas/triage-record.json` — Triage record schema for email display
- `schemas/task-record.json` — Task record schema for task queue display

### Build infrastructure (from Phase 1)
- `scripts/build-dashboard-data.sh` — Compiles NDJSON to docs/feed.json and docs/tasks.json
- `docs/` — GitHub Pages root directory, dashboard files go here

### Project context
- `.planning/PROJECT.md` — Core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — VIS-01 through VIS-04 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/build-dashboard-data.sh` — Already compiles feed.jsonl → docs/feed.json and active.jsonl → docs/tasks.json (last 100 entries)
- `docs/feed.json` — Pre-compiled feed data ready for dashboard consumption
- `docs/tasks.json` — Pre-compiled task data ready for dashboard consumption

### Established Patterns
- NDJSON → JSON compilation via jq in build script
- docs/ directory for GitHub Pages deployment
- ISO 8601 timestamps with timezone in all data files

### Integration Points
- docs/index.html — main dashboard page (to be created)
- docs/feed.json — activity feed data source
- docs/tasks.json — task queue data source
- scripts/build-dashboard-data.sh — may need enhancement for triage summary stats
- /triage-inbox and /task commands — need post-run hook to rebuild dashboard data

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-dashboard*
*Context gathered: 2026-03-23*
