# Roadmap: Agend Ops

## Milestones

- [x] **v1.0 MVP** - Phases 1-4 (shipped 2026-03-23)
- [ ] **v2.0 Autonomous Operations** - Phases 5-8 (shipped) + Phases 10-12 (in progress: Obsidian knowledge layer)
- [ ] **v3.0 Mobile Commands** - Phase 9 (Telegram, deferred)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-4) - SHIPPED 2026-03-23</summary>

- [x] **Phase 1: Foundation** - Google OAuth, hardened MCP server, data schema, repo structure, and project configuration
- [x] **Phase 2: Email Triage** - Claude scans inbox, categorizes emails, surfaces starred queue, generates drafts, detects actionable items
- [x] **Phase 3: Task Execution** - Manual and proactive task kickoff, document retrieval from Drive, analysis, and response generation
- [x] **Phase 4: Dashboard** - GitHub Pages mobile-first dashboard showing email status, starred queue, activity feed, and pending tasks

### Phase 1: Foundation
**Goal**: Glen has a working Claude Code environment with verified Gmail/Drive access, a hardened MCP server that cannot send emails, and a data schema ready to receive activity logs
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05
**Success Criteria** (what must be TRUE):
  1. Claude can read Gmail messages and list inbox via MCP without token expiry (production OAuth)
  2. Claude can access Google Drive files via MCP
  3. The MCP server has no send, share, or filter-creation capabilities (hardened fork verified)
  4. NDJSON schema files exist with documented field definitions for feed, email summaries, and task records
  5. Custom Claude Code commands (e.g., /triage-inbox) are defined in CLAUDE.md and executable
**Plans:** 3/3 plans complete

Plans:
- [x] 01-01-PLAN.md -- Directory structure, .gitignore, NDJSON schemas, and utility scripts
- [x] 01-02-PLAN.md -- Google OAuth setup and hardened MCP server installation
- [x] 01-03-PLAN.md -- CLAUDE.md enhancement and custom slash commands

### Phase 2: Email Triage
**Goal**: Glen can run a single command and get his inbox categorized into priority buckets with starred emails surfaced first, draft replies generated, and actionable items flagged -- all logged to the activity feed
**Depends on**: Phase 1
**Requirements**: EMAIL-01, EMAIL-02, EMAIL-03, EMAIL-04, EMAIL-05, EMAIL-06, EMAIL-07, EMAIL-08
**Success Criteria** (what must be TRUE):
  1. Glen runs /triage-inbox and sees unread emails categorized into urgent, needs-response, informational, and low-priority buckets
  2. Starred emails appear as highest-priority items in a separate "needs my action" queue
  3. Claude generates draft replies as local markdown files and creates corresponding Gmail drafts -- no email is ever sent automatically
  4. Actionable items (contracts, invoices, meeting requests, deadlines) are detected and presented with suggested next steps
  5. Every triage action is logged to data/feed.jsonl with timestamp, trigger, action, and outcome
**Plans:** 2/2 plans complete

Plans:
- [x] 02-01-PLAN.md -- Triage data contracts: schema extensions, client domain seed list, email-scanner subagent definition
- [x] 02-02-PLAN.md -- Triage engine: full subagent prompt, triage-inbox command update, live verification

### Phase 3: Task Execution
**Goal**: Glen can delegate tasks to Claude ("review the contract Sarah sent", "prep for Thursday meeting") and receive analyzed documents, summaries, and draft responses
**Depends on**: Phase 2
**Requirements**: TASK-01, TASK-02, TASK-03, TASK-04, TASK-05
**Success Criteria** (what must be TRUE):
  1. Glen can kick off tasks via natural language in Claude Code and see them execute to completion
  2. After triage, Claude proactively suggests tasks based on detected actionable items ("Found a contract -- want me to review it?")
  3. Claude retrieves documents from Google Drive and produces analysis (key terms, risks, obligations, deadlines)
  4. Completed tasks produce a draft response or summary that Glen can review and use
**Plans:** 4/4 plans complete

Plans:
- [x] 03-01-PLAN.md -- Task execution contracts: extended schema and task-executor subagent definition
- [x] 03-02-PLAN.md -- Task execution commands: enhanced /task, auto-queue pipeline, /status update, live verification
- [x] 03-03-PLAN.md -- Gap closure: execute auto-queue pipeline against existing triage data (TASK-02)
- [x] 03-04-PLAN.md -- Gap closure: run task to full completion with output files (TASK-04, TASK-05)

### Phase 4: Dashboard
**Goal**: Glen can check his phone and see at a glance: unread email count, starred queue, recent activity, and pending task suggestions -- without opening Claude Code
**Depends on**: Phase 1
**Requirements**: VIS-01, VIS-02, VIS-03, VIS-04
**Success Criteria** (what must be TRUE):
  1. Activity feed is logged as NDJSON and compiled to JSON for dashboard consumption
  2. GitHub Pages dashboard auto-deploys from the repo's docs/ directory
  3. Dashboard displays unread email count, starred queue items, recent activity feed entries, and pending task suggestions
  4. Dashboard is readable and usable on a phone screen without horizontal scrolling or tiny text
**Plans:** 2/2 plans complete
**UI hint**: yes

Plans:
- [x] 04-01-PLAN.md -- Build pipeline: triage.json compilation and auto-rebuild wiring into slash commands
- [x] 04-02-PLAN.md -- Dashboard HTML: single-page responsive dashboard with Kanban layout and visual verification

</details>

### v2.0 Autonomous Operations

**Milestone Goal:** Transform Agend Ops from a manual tool into an autonomous assistant -- scheduled triage, daily task management, invoice tracking, and mobile commands.

- [x] **Phase 5: Scheduled Automation** - GitHub Actions daily triage, auto-dashboard rebuild, and morning briefing (completed 2026-03-23)
- [ ] **Phase 6: Daily Task Management** - /todo commands, NDJSON storage, briefing integration, and dashboard to-do tab
- [x] **Phase 7: Invoice Tracking** - /invoice commands, triage pipeline hook, Xero sync, and dashboard invoice tab (completed 2026-03-23)
- [x] **Phase 8: Interactive Dashboard** - Next.js on Coolify with auth, actions, and live data (completed 2026-03-25)
- [ ] **Phase 9: Telegram Mobile Commands** - Two-way command execution and approval flow from phone (deferred to v3.0)
- [x] **Phase 10: Obsidian Knowledge Layer — Client Notes** - Per-client markdown vault sourced from data/ NDJSON; iCloud canonical, Mac Studio launchd daemon projects updates (completed 2026-05-02)
- [x] **Phase 11: Contract Manager Integration** - Seed/refresh frontmatter and log contract events from contracts.agend.info MCP (completed 2026-05-02)
- [ ] **Phase 12: Calendar + Drive Activity Enrichment** - Pull meetings + documents matched to clients via existing hardened-workspace MCP

## Phase Details

### Phase 5: Scheduled Automation
**Goal**: The system runs daily without Glen's involvement -- triage fires on schedule, dashboard data rebuilds automatically, and a morning briefing is waiting when Glen starts his day
**Depends on**: Phase 4 (v1 complete)
**Requirements**: SCHED-01, SCHED-02, SCHED-03
**Success Criteria** (what must be TRUE):
  1. Email triage runs automatically on weekday mornings via GitHub Actions without Glen's laptop being open
  2. Dashboard JSON data and GitHub Pages deployment refresh after every automated triage run
  3. Glen can read a daily briefing summarizing email status, pending tasks, and key deadlines each morning
  4. Scheduled runs are logged to the activity feed with trigger type "scheduled"
**Plans:** 3/3 plans complete

Plans:
- [x] 05-01-PLAN.md -- Data contracts: feed schema extension, build script update, /daily-briefing command
- [x] 05-02-PLAN.md -- GitHub Actions scheduled triage workflow (fallback) and Desktop scheduled task (primary, MCP works with full binary paths)
- [x] 05-03-PLAN.md -- Dashboard briefing summary banner and visual verification

### Phase 6: Daily Task Management
**Goal**: Glen can track personal to-dos (things Claude cannot execute) alongside Claude-managed tasks, with to-dos visible in the briefing and on the dashboard
**Depends on**: Phase 5
**Requirements**: TODO-01, TODO-02, TODO-03, TODO-04
**Success Criteria** (what must be TRUE):
  1. Glen can add, complete, list, and prioritize to-do items via /todo command in Claude Code
  2. To-do items persist in NDJSON with a defined schema and survive across sessions
  3. The daily briefing includes today's to-do items alongside email and task status
  4. Dashboard shows a "Today" tab with to-dos and their completion status
**Plans:** 2 plans
**UI hint**: yes

Plans:
- [x] 06-01-PLAN.md -- Todo schema, /todo command, build script and validation extension
- [x] 06-02-PLAN.md -- Daily briefing todo integration and dashboard Today tab

### Phase 7: Invoice Tracking
**Goal**: Invoice-related emails are automatically detected during triage and tracked through their lifecycle, with Glen able to manage invoices via commands and see overdue items on the dashboard
**Depends on**: Phase 6
**Requirements**: INV-01, INV-02, INV-03, INV-04
**Success Criteria** (what must be TRUE):
  1. Glen can create, list, mark-paid, and view overdue invoices via /invoice command
  2. Invoice records persist in NDJSON with a defined schema covering amount, due date, client, and status
  3. When triage detects an invoice-related email, a skeleton invoice record is auto-created without manual intervention
  4. Dashboard shows an "Invoices" tab with pending, overdue, and recently paid invoices
**Plans:** 3/3 plans complete
**UI hint**: yes

Plans:
- [x] 07-01-PLAN.md -- Invoice schema, /invoice command, build script extension, and Xero MCP config
- [x] 07-02-PLAN.md -- Triage pipeline invoice auto-queue and daily briefing invoice section
- [x] 07-03-PLAN.md -- Dashboard "Invoices" tab with overdue highlighting and visual verification

### Phase 8: Interactive Dashboard
**Goal**: Glen has a secured, actionable dashboard on Coolify — auth-protected, with buttons to mark invoices paid, complete todos, approve drafts, and trigger triage from his phone
**Depends on**: Phase 7
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04
**Success Criteria** (what must be TRUE):
  1. Next.js app deployed on Coolify with Google OAuth login (only Glen can access)
  2. Dashboard reads live NDJSON data directly from the git repo on the home server
  3. Glen can take actions from the dashboard: mark invoice paid, complete todo, approve/view draft, trigger triage
  4. Clickable Gmail links open emails and drafts directly from dashboard cards
**Plans:** 4/4 plans complete
**UI hint**: yes

Plans:
- [x] 08-01-PLAN.md -- Next.js scaffold with auth, data layer, API routes, action queue endpoint, and Dockerfile
- [x] 08-02-PLAN.md -- Dashboard UI: Kanban board, card components, action buttons, Gmail links, mobile tabs
- [x] 08-03-PLAN.md -- Action queue schema, /process-queue command, and triage/status integration
- [x] 08-04-PLAN.md -- Coolify deployment configuration and production verification

### Phase 9: Telegram Mobile Commands (deferred)
**Goal**: Glen can send commands and approve actions from his phone via Telegram, without opening a laptop or the dashboard
**Depends on**: Phase 8
**Requirements**: TELE-01, TELE-02, TELE-03
**Success Criteria** (what must be TRUE):
  1. A Telegram channel is configured and paired with Claude Code via the Channels plugin
  2. Glen can execute /triage, /task, /todo, /status, and /invoice from Telegram and receive concise mobile-formatted responses
  3. Claude sends draft previews and permission prompts to Telegram, and Glen can approve or reject from his phone
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 5 -> 6 -> 7 -> 8 -> 10 -> 11 -> 12 (Phase 9 deferred to v3.0)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | Complete | 2026-03-23 |
| 2. Email Triage | v1.0 | 2/2 | Complete | 2026-03-23 |
| 3. Task Execution | v1.0 | 4/4 | Complete | 2026-03-23 |
| 4. Dashboard | v1.0 | 2/2 | Complete | 2026-03-23 |
| 5. Scheduled Automation | v2.0 | 3/3 | Complete | 2026-03-23 |
| 6. Daily Task Management | v2.0 | 2/2 | Complete | 2026-03-23 |
| 7. Invoice Tracking | v2.0 | 3/3 | Complete | 2026-03-23 |
| 8. Interactive Dashboard | v2.0 | 4/4 | Complete | 2026-03-25 |
| 9. Telegram (deferred) | v3.0 | 0/? | Not started | - |
| 10. Obsidian Knowledge Layer | v2.0 | 5/5 | Complete    | 2026-05-02 |
| 11. Contract Manager Integration | v2.0 | 4/4 | Complete    | 2026-05-02 |
| 12. Calendar + Drive Enrichment | v2.0 | 0/? | Queued | - |

### Phase 10: Obsidian Knowledge Layer — Client Notes

**Goal:** Build a per-client markdown knowledge base in an iCloud Obsidian vault. Backfill from `data/` NDJSON history; auto-append on new triage / task / invoice events. Each canonical client gets one durable note accumulating context (status, recent activity, open items) that's mobile-readable on iPhone and updates automatically via a Mac Studio launchd daemon. Scope: client notes only — project portfolio, daily notes, and inbox bridge are deferred.
**Requirements**: INTL-01 (Context accumulation — client history, past decisions stored in structured files)
**Depends on:** Phase 8 (action queue + dashboard data layer reused)
**Plans:** 5/5 plans complete
**Canonical refs:** `.planning/phases/10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli/10-CONTEXT.md`

Plans:
- [x] 10-01-PLAN.md — Bootstrap: vault-build/.gitkeep, .gitignore extension, Python test scaffold + dependency manifest
- [x] 10-02-PLAN.md — vault_writer.py sync engine: slugify, marker splice, atomic write, backfill, incremental, frontmatter round-trip
- [x] 10-03-PLAN.md — Coolify integration: /sync-obsidian command + flock wrapper, slash command hooks, push-and-sync annotation
- [x] 10-04-PLAN.md — Mac Studio daemon: project-to-icloud mode, LaunchAgent plist, fswatch wrapper, idempotent installer, README
- [x] 10-05-PLAN.md — End-to-end backfill execution + Mac install + iPhone verification

### Phase 11: Contract Manager Integration

**Goal:** Integrate the contract-manager MCP (`https://contracts.agend.info/api/mcp`) to seed and refresh client-note frontmatter (`deployed_modules`, `contract_start`, `contract_end`, `primary_contact`, `sites[]` — `sites[]` ships as `[]` only; the Sites section is deferred per D-C2-REVISED until CM exposes a per-client sites tool). Log contract events (renewals, expiries) to the Activity Log with the new 📄 emoji. Add Usage section sourced from `get_sla_status` per client (D-C3-REVISED). Reconcile invoice data between `data/invoices/active.jsonl` (canonical, unchanged) and CM `list_overdue_invoices` (read-only merge into Activity Log; dedup by invoice_number with case-fold + trim only).
**Requirements**: INTL-01 (extended)
**Depends on:** Phase 10
**Plans:** 4/4 plans complete

Plans:
- [x] 11-01-PLAN.md — Wave 0 bootstrap: schema warning level, .gitignore cache exclusion, sync-obsidian.sh env validation, render_frontmatter signature extension
- [x] 11-02-PLAN.md — cm_client.py JSON-RPC client + retry + cache + adapter + `--mode map-cm-clients` mapping pass (Glen runs once on Coolify)
- [x] 11-03-PLAN.md — vault_writer rendering: MANAGED_SECTIONS extension, EMOJI 📄 contract, _NOTE_TEMPLATE with CM-TODOS + USAGE marker pairs (no SITES), render_cm_todos, render_usage
- [x] 11-04-PLAN.md — _gather_events CM extension + invoice dedup + run_backfill CM integration + cache fallback + cm_data_stale_since stamp + Pitfall 1 Mac-daemon isolation test (Glen runs end-to-end backfill + iPhone verification)

### Phase 12: Calendar + Drive Activity Enrichment

**Goal:** Enrich client notes with meetings (Google Calendar, matched by attendee email -> canonical `client_domain`) and documents (Google Drive, matched by filename substring to clients per D-A4-REVISED) appended to the Activity Log section. Uses Google Calendar v3 + Drive v3 REST APIs directly via OAuth blob from hardened-workspace credentials per D-X1.
**Requirements**: INTL-01-CAL, INTL-01-DRIVE, INTL-01-PRIVACY, INTL-01-WORKSPACE-CACHE, INTL-01-PROJECTION-ISOLATION (all extend INTL-01)
**Depends on:** Phase 10, Phase 11
**Plans:** 4 plans

Plans:
- [ ] 12-01-PLAN.md -- Wave 0 bootstrap: .gitignore cache exclusions, sync-obsidian.sh GOOGLE_MCP_CREDENTIALS_DIR validation, EMOJI_BY_KIND extension (meeting+doc), load_clients aliases plumbing
- [ ] 12-02-PLAN.md -- workspace_client.py: HTTPS GET seam + retry/cache + OAuth refresh + privacy-filter adapters (D-D1/D-D2/D-D3) + endpoint allowlist (D-X1) + Drive walker
- [ ] 12-03-PLAN.md -- vault_writer rendering surface: D-A4-REVISED filename matching + word-boundary helper + stop-list, D-A2 attendee-domain calendar router, _cal_meeting_event_tuple + _drive_doc_event_tuple, _gather_events extension with cal_events/drive_files kwargs (D-B2 top-20 cap)
- [ ] 12-04-PLAN.md -- _fetch_external_data_for_run rename + Calendar/Drive integration into run_backfill, cache fallback chain, workspace_data_stale_since stamp, idempotency tests, Pitfall 1 invariant subprocess test (Mac daemon does not import workspace_client)

## Backlog

### Phase 999.1: Capability Index Vault — graphify-driven RFP response system (BACKLOG)

**Goal:** Index every Agend Systems app (internal modules + select client deployments) with [graphify](https://github.com/safishamsi/graphify), then layer Claude-extracted capability frontmatter (`capabilities[]`, `deployed_at[]`, `maturity`, `stack`, `last_indexed`) into `vault-build/Projects/<slug>.md`. Surfaces in iCloud Obsidian for mobile RFP prep AND becomes a Claude-readable corpus for "what do we have that solves X" queries during sales response. Mirrors the Phase 10 client-note marker pattern.

**Three-layer architecture:**
- **Layer 1** — graphify raw extraction (free, deterministic, tree-sitter AST + Claude subagents over docs)
- **Layer 2** — opinionated capability index (the moat: `Capabilities.md` controlled vocabulary + structured frontmatter)
- **Layer 3** — query surface (Obsidian DataView + Claude Desktop reading the vault)

**Phase shape (when promoted):**
1. `Capabilities.md` controlled vocabulary + tag schema
2. Extend `vault_writer.py` with `Projects/` mode (mirrors `Clients/` pattern from Phase 10)
3. `scripts/index-project.sh` wrapper — runs graphify, then Claude subagent that writes capability frontmatter
4. First 5 projects indexed end-to-end (most-pitched apps)
5. Real RFP test — time vault-assisted response vs without; ROI proof gate

**Hard questions to resolve in /gsd-discuss-phase:**
- Privacy boundary: do we index client deployment code (graphify subagents see source) or internal-only?
- Capability tag governance: Claude proposes vs Glen confirms; freshness vs accuracy tradeoff
- Freshness gate: must not claim capabilities from stale indexes in sales docs

**Trigger condition:** Revisit during v3.0 milestone planning, after Phase 10 (Obsidian client notes) is verified AND at least one real RFP response has tested the manual workflow (manually drop graphify output into iCloud, see if it actually helps draft a response).

**Why backlog and not active:** Strong ROI case (one won deal pays for years of indexing) but unproven without manual spike. Don't build the pipeline before validating the value.

**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with `/gsd-review-backlog` when ready)
