# Phase 1: Foundation - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up the infrastructure layer for Agend Ops: Google OAuth 2.0 in production mode, hardened Google Workspace MCP server, NDJSON data schema, directory structure, and CLAUDE.md with custom commands. No email triage logic, no task execution, no dashboard UI — just the plumbing everything else depends on.

</domain>

<decisions>
## Implementation Decisions

### Google Account
- **D-01:** Use Agend Systems Google Workspace account (not personal Gmail)
- **D-02:** Glen is Workspace admin — can set OAuth consent screen to production mode and manage API access directly
- **D-03:** No Google verification needed (under 100 users) — set to production mode immediately to avoid 7-day token expiry

### Data Schema
- **D-04:** Triage results stored as separate files (one JSONL per triage run, e.g., data/triage/2026-03-23.jsonl) — feed entries link to them
- **D-05:** Activity feed detail level — Claude's discretion (balance between lean scanning and useful dashboard display)
- **D-06:** Task record structure — Claude's discretion (choose what works best for the task execution and dashboard requirements)

### Custom Commands
- **D-07:** Definite commands: /status (quick summary), /task <description> (kick off a task), /feed (show recent activity)
- **D-08:** Triage command design — Claude's discretion (whether one command does everything or staged steps)
- **D-09:** Claude designs the full command set based on requirements — user wants these three minimum

### Directory Layout
- **D-10:** GitHub Pages dashboard lives in docs/ (standard GitHub Pages from /docs on main branch)
- **D-11:** Top-level repo layout — Claude's discretion (optimize for NDJSON append-only pattern, GitHub Pages, and clean separation of concerns)

### Claude's Discretion
- Activity feed entry detail level (lean vs rich)
- Task record structure (individual files vs JSONL)
- Top-level directory organization
- Triage command design (full vs staged)
- Additional commands beyond /status, /task, /feed
- NDJSON field definitions (informed by dashboard needs)

</decisions>

<specifics>
## Specific Ideas

- Glen already stars emails as a "needs my action" queue — this existing workflow should be preserved and enhanced, not replaced
- Hardened MCP fork (c0webster) is a security requirement, not a preference — must verify no send/share/filter capabilities
- Research flagged Desktop scheduled tasks can't access MCP (bug #36327) — this doesn't affect Phase 1 but informs future automation decisions

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research findings
- `.planning/research/STACK.md` — Technology choices, MCP server recommendation, NDJSON rationale
- `.planning/research/ARCHITECTURE.md` — System structure, component boundaries, data flow
- `.planning/research/PITFALLS.md` — Gmail OAuth pitfalls, token cost warnings, scheduling limitations

### Project context
- `.planning/PROJECT.md` — Core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — FOUND-01 through FOUND-05 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None — patterns will be established by this phase

### Integration Points
- Google Workspace OAuth 2.0 API (admin-controlled)
- hardened-google-workspace-mcp server (c0webster fork)
- GitHub Pages (docs/ directory)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-23*
