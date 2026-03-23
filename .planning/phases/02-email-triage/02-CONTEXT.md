# Phase 2: Email Triage - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Glen runs a single command (/triage-inbox) and gets his inbox categorized into priority buckets with starred emails surfaced first, draft replies generated for urgent/client emails, and actionable items flagged with suggested next steps. Everything logged to the activity feed. No task execution, no dashboard — just the triage engine.

</domain>

<decisions>
## Implementation Decisions

### Email Categorization
- **D-01:** Rules + AI hybrid classification — known client domains get priority boost via rules, AI classifies the rest
- **D-02:** Client-facing emails are the primary urgency signal — anything from a client (especially about deadlines, issues, contracts) is urgent
- **D-03:** Seed list of ~30 client domains stored in a config file (data/config/clients.jsonl or similar), with Claude suggesting new domains as it discovers frequent senders
- **D-04:** Four buckets: urgent, needs-response, informational, low-priority
- **D-05:** Starred emails surface as highest-priority "needs my action" queue (carried from Phase 1)

### Draft Reply Generation
- **D-06:** Claude mirrors Glen's writing style — study sent emails to match tone (professional but approachable)
- **D-07:** Create Gmail drafts only (via hardened MCP) — no local markdown copies
- **D-08:** Draft replies only for urgent emails and known client emails — not all needs-response items
- **D-09:** Human-in-the-loop enforced by hardened MCP (cannot send, only create drafts)

### Email Preprocessing
- **D-10:** Batch scope: last 24 hours of emails per triage run
- **D-11:** Moderate stripping — remove HTML and signatures, keep one level of reply chain for context
- **D-12:** Token cost management through preprocessing, not through limiting email count

### Action Detection
- **D-13:** Detect four action types: contracts/legal documents, invoice requests, meeting requests, deadline mentions
- **D-14:** Match emails to client names/domains from the seed list — tag triage results with client name
- **D-15:** Detected actions presented as suggested next steps (e.g., "Contract from Acme Corp — review by Friday")

### Claude's Discretion
- Exact classification prompt/system message design
- How to study Glen's sent emails for tone mirroring (sample size, frequency)
- Preprocessing implementation details (HTML parser choice, signature detection approach)
- How to present triage results in the /triage-inbox command output
- Activity feed entry format for triage events
- Client domain suggestion mechanism (how often, where to surface suggestions)

</decisions>

<specifics>
## Specific Ideas

- Glen stars emails as a "needs my action" queue — this existing Gmail workflow must be detected and surfaced prominently
- The client seed list is a key differentiator — it turns generic email triage into business-aware triage
- Tone mirroring should feel natural, not robotic — Glen is professional but approachable
- Triage results should feel like a briefing, not a data dump

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data schemas (from Phase 1)
- `schemas/feed-entry.json` — Activity feed schema, triage events must conform to this
- `schemas/triage-record.json` — Email triage record schema, defines required fields per email
- `schemas/task-record.json` — Task record schema, for suggested actions from detected items

### Commands (from Phase 1)
- `.claude/commands/triage-inbox.md` — Existing stub command to be implemented
- `.claude/commands/feed.md` — Feed command that will display triage results

### Project context
- `.planning/PROJECT.md` — Core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — EMAIL-01 through EMAIL-08 acceptance criteria
- `.planning/research/FEATURES.md` — Feature landscape, table stakes, anti-features

### Phase 1 context
- `.planning/phases/01-foundation/01-CONTEXT.md` — Foundation decisions (data schema, commands, directory layout)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `schemas/triage-record.json` — Pre-defined schema for triage results with required fields
- `schemas/feed-entry.json` — Activity feed schema for logging triage events
- `.claude/commands/triage-inbox.md` — Stub command ready to be implemented
- `scripts/validate-data.sh` — Can validate triage output against schema
- `scripts/build-dashboard-data.sh` — Will compile triage data for dashboard (Phase 4)

### Established Patterns
- NDJSON append-only files in data/ directories
- One triage JSONL per run (data/triage/YYYY-MM-DD.jsonl) — from Phase 1 decision D-04
- Activity feed entries in data/feed.jsonl
- Claude Code commands with YAML frontmatter and allowed-tools

### Integration Points
- Hardened Google Workspace MCP server — gmail_list, gmail_read, gmail_create_draft tools
- data/triage/ directory — output destination for triage results
- data/feed.jsonl — activity feed logging destination
- data/config/ — client domain seed list location

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-email-triage*
*Context gathered: 2026-03-23*
