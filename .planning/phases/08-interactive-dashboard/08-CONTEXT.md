# Phase 8: Interactive Dashboard - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the static GitHub Pages dashboard with a Next.js app deployed on Coolify (home server). Auth-protected, reads NDJSON directly from disk, queues actions for Claude to execute. Same repo (/dashboard directory). Evolve the Notion-style design for interactivity. No Telegram, no new data domains — just the interactive frontend.

</domain>

<decisions>
## Implementation Decisions

### Actions & Mutations
- **D-01:** Four dashboard actions: mark invoice paid, complete todo, view/approve Gmail draft, trigger triage
- **D-02:** Mutation strategy: queue for Claude — dashboard writes action requests to a queue file, Claude picks them up on next triage run or manual check. Claude remains the single writer to data files.
- **D-03:** View/approve draft links directly to Gmail (already built) — no server-side email sending

### Architecture
- **D-04:** Same repo — Next.js app in /dashboard directory alongside data files
- **D-05:** Direct file read — Next.js reads data/*.jsonl from disk (home server has direct access). No compilation step needed for the app (build-dashboard-data.sh can remain for GitHub Pages backward compat).
- **D-06:** Coolify deploys from the /dashboard directory of the same repo
- **D-07:** API routes in Next.js handle action queuing and data reads

### Auth & Access
- **D-08:** Single user only — Google OAuth locked to glen@iugo.com.au via NextAuth
- **D-09:** Custom subdomain on a domain Glen owns (e.g., ops.agendsystems.com or ops.iugo.com.au)
- **D-10:** No manager access for now — single-user tool

### Design
- **D-11:** Evolve the Notion aesthetic for interactivity — keep the warm tones and clean typography but redesign layout for an action-focused experience. Think Linear meets Notion.
- **D-12:** Kanban board style — columns by domain (Today, Emails, Tasks, Invoices, Activity). Cards within each column have action buttons.
- **D-13:** Better mobile UX — touch targets for action buttons. On mobile, columns become swipeable tabs (same as current dashboard pattern).
- **D-14:** Same data domains but cards gain action buttons (mark paid, complete, view draft, trigger triage)

### Claude's Discretion
- Next.js project structure (App Router vs Pages Router)
- NextAuth configuration details (providers, callbacks, session strategy)
- Action queue file format and location (data/queue/actions.jsonl or similar)
- How Claude discovers and processes queued actions (scheduled task, triage hook, or new command)
- Coolify deployment configuration (Dockerfile, build settings, env vars)
- CSS framework choice (Tailwind recommended for rapid development, or keep hand-rolled CSS)
- Whether to use a UI component library (shadcn/ui, Radix) or stay minimal
- Server-side data parsing strategy (stream NDJSON or read-all-at-once)
- Real-time refresh approach (polling interval, SWR, or manual refresh button)

</decisions>

<specifics>
## Specific Ideas

- The dashboard should feel like a mission control panel — see everything, act on anything
- "Queue for Claude" means Glen taps "Mark Paid" → sees "Queued" badge → Claude processes it within the next scheduled run or when Glen runs /status
- The existing Gmail links (thread_id, draft_id) carry over — they're already the best UX for email actions
- Consider a "Run now" button that triggers triage immediately (via Claude Desktop or a webhook)
- Notion meets Linear: warm readable content with crisp action affordances

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Current dashboard (to evolve from)
- `docs/index.html` — Current 1500+ line static dashboard with all tab/card patterns
- `.planning/phases/04-dashboard/04-UI-SPEC.md` — Original UI design contract (spacing, typography, colors)

### Data contracts
- `schemas/feed-entry.json` — Activity feed schema
- `schemas/triage-record.json` — Email triage schema (has message_id, thread_id, draft_id for Gmail links)
- `schemas/task-record.json` — Task record schema
- `schemas/todo-record.json` — Todo record schema
- `schemas/invoice-record.json` — Invoice record schema (18 fields)

### Existing infrastructure
- `data/config/clients.jsonl` — Client domain list
- `scripts/build-dashboard-data.sh` — Current build pipeline (may keep for backward compat)
- `.claude/commands/` — All commands that the queue actions would map to

### Project context
- `.planning/PROJECT.md` — Core value, constraints
- `.planning/REQUIREMENTS.md` — DASH-01 through DASH-04

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/index.html` — 1500+ lines of Notion-style CSS and card rendering logic to port
- UI-SPEC.md tokens (spacing, typography, colors) can be converted to CSS variables / Tailwind config
- Gmail link patterns (thread_id → mail.google.com URL) already proven
- All NDJSON schemas define the data contract for server-side parsing

### Established Patterns
- NDJSON append-only files in data/ directories
- Schema validation via jq
- Auto-rebuild + git commit after data changes
- Activity feed logging for all operations

### Integration Points
- /dashboard directory — new Next.js app root
- data/*.jsonl — read directly from disk via Node.js fs
- data/queue/ — new directory for action queue
- Coolify — deployment target (home server)
- Google OAuth — reuse existing Workspace OAuth credentials
- Git — mutations committed and pushed after Claude processes queue

</code_context>

<deferred>
## Deferred Ideas

- Real-time WebSocket updates — polling is fine for v1 of the interactive dashboard
- Manager read-only access — single user for now
- PWA / installable app — just a responsive web app for now

</deferred>

---

*Phase: 08-interactive-dashboard*
*Context gathered: 2026-03-24*
