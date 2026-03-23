# Project Research Summary

**Project:** Agend Ops v2.0 — Autonomous Operations
**Domain:** AI-powered personal operations hub (Claude Code + MCP + GitHub Pages)
**Researched:** 2026-03-23
**Confidence:** HIGH

## Executive Summary

Agend Ops v2.0 builds an autonomous operations layer on a working v1 foundation. The core pattern is well-established: Claude Code as the AI runtime, hardened MCP servers for Gmail and GitHub access, NDJSON flat files committed to git as the data layer, and GitHub Pages for a glanceable dashboard. V1 delivered interactive triage, task execution, and activity feed — all manual. V2 adds four autonomous capabilities in strict dependency order: scheduled automation via GitHub Actions, a daily to-do management system, invoice tracking extracted from the triage pipeline, and Telegram as a mobile command interface. The research is unusually high-confidence because the existing v1 system is in production and all new v2 components are verified against official documentation.

The recommended approach is strict layering. Scheduled automation (GitHub Actions) comes first because it is the most impactful autonomous capability and has the most environmental complexity — it requires separate MCP configuration, Google OAuth credentials stored in GitHub Secrets, and explicit testing before any other phases depend on it. The to-do system comes second because it establishes the schema-plus-command-plus-dashboard-tab pattern that invoice tracking reuses identically in Phase 3. Telegram comes last because it is a pure consumption layer over commands that must already exist, and it is a research preview feature whose instability risk should not propagate backward to earlier stable phases.

The top risks are operational, not architectural. Google OAuth testing-mode tokens expire silently after 7 days — switch to production mode before any code is written. Desktop scheduled tasks cannot access MCP servers (confirmed open bug #36327) — use GitHub Actions from the start, never Desktop tasks. Token costs can explode if raw email threads are processed naively — two-tier model selection (Haiku for categorization, Sonnet for drafts) with prompt caching reduces this 5-10x. Prompt injection via email content is mitigated entirely by the hardened-google-workspace-mcp fork, which removes all send and share operations by design. All four of these risks are fully documented with official sources and have clear prevention strategies.

## Key Findings

### Recommended Stack

The v2 stack extends v1 with no new MCP servers. Claude Code (>=2.1.80) is the runtime for both interactive and scheduled operations — v2.1.80 is required for Channels (Telegram). The hardened-google-workspace-mcp fork handles Gmail and Drive access with send/share operations stripped to prevent prompt injection exfiltration. GitHub's official remote HTTP MCP server handles repo operations without Docker. GitHub Actions with claude-code-action@v1 is the only reliable durable scheduling option — Desktop scheduled tasks are ruled out by unresolved platform bug #36327. NDJSON files in git remain the data layer; new domains (todos, invoices) each get their own NDJSON file and schema rather than extending the existing task schema. The critical negative: never use the unmodified taylorwilsdon/google_workspace_mcp (exfiltration vectors), the deprecated @modelcontextprotocol/server-github npm package (abandoned April 2025), or Claude Desktop scheduled tasks for MCP-dependent work.

**Core technologies:**
- Claude Code >=2.1.80: AI runtime and orchestrator — required for Channels (Telegram), /loop scheduling, and cron tools
- hardened-google-workspace-mcp (c0webster fork): Gmail read, Drive access, draft creation — no send/share; required for prompt injection safety
- github/github-mcp-server (remote HTTP): GitHub operations including Pages deployment — official server, no Docker required
- GitHub Actions / claude-code-action@v1: Durable scheduled automation — the only reliable option given Desktop MCP bug #36327
- NDJSON (.jsonl) in git: Activity feed and all domain data — append-only, git-diffable, corruption-isolated
- Plain HTML/CSS/JS: GitHub Pages dashboard — zero build step, Claude generates directly, no framework overhead
- rclone >=1.68: One-way git-to-Drive sync — mobile/cross-device access without build pipeline overhead
- jq >=1.7: NDJSON-to-JSON compilation for dashboard — `jq -s '.' file.jsonl > docs/file.json`

### Expected Features

V2 adds four feature domains to a working v1 system. The v1 baseline (interactive triage, draft generation, task queue, activity feed, static dashboard) is in production and does not need rebuilding.

**Must have (table stakes for v2):**
- GitHub Actions scheduled email triage — an assistant that only runs when manually invoked is not autonomous; this is the headline v2 capability
- .github/mcp-config.json for runner MCP configuration — separate from local config, uses GitHub Secrets for OAuth credentials
- Daily to-do management (/todo add, /todo list, /todo done) — tracks Glen's personal action items Claude cannot execute
- /daily-briefing command — morning compilation of todos, pending tasks, and triage summary
- Invoice tracking extracted from triage pipeline — auto-creates invoice records when email-scanner detects action_type:"invoice"
- invoice-scanner subagent — lazily extracts structured invoice data (amount, due date, vendor) when task is executed
- Dashboard tabs for todos and invoices — extends existing GitHub Pages view with two new domains

**Should have (differentiators for v2):**
- Telegram command channel — send commands from phone, get concise responses, approve/deny permission prompts via phone (v2.1.81+)
- Starred-email priority surfacing in /daily-briefing — maps to Glen's existing Gmail workflow, zero additional MCP cost
- Invoice lifecycle management (detected -> pending-payment -> paid/overdue) — /invoice list, paid, overdue commands
- Context accumulation (client summaries in git) — system builds persistent knowledge, compounds in value over weeks

**Defer (v3+):**
- Autonomous email sending for low-risk categories — requires weeks of proven accuracy first; trust must be earned
- Calendar awareness and meeting scheduling — separate complex domain, enormous scope creep risk
- Multi-step task execution chains
- Google Drive write operations from Claude (versus rclone one-way sync)

**Anti-features (explicitly excluded from v2):**
- Real-time push notifications — adds infrastructure, defeats cognitive-load reduction goal
- Native mobile app — GitHub Pages + Telegram covers the mobile use case entirely
- Multi-user or team features — transforms personal tool into a platform with auth, permissions, and data isolation work
- Any SaaS for data storage — data ownership is a hard constraint; all data in local git repo

### Architecture Approach

V2 is an additive extension of v1, not a redesign. The email-scanner and task-executor agents are modified at the margins only: email-scanner gains invoice record creation for action_type:"invoice" detections; task-executor gains dispatch to the new invoice-scanner subagent. Three new slash commands are added (todo, invoice, daily-briefing). Two GitHub Actions workflows are added. A Telegram channel plugin wraps all existing commands. The existing triage pipeline, task system, activity feed, and dashboard all continue working unchanged. The build-dashboard-data.sh script gains two new compilations (todos.json, invoices.json). The dashboard gains two new tabs.

The key architectural principle across all four v2 phases: separate data domains. Todos, invoices, and tasks each have distinct lifecycles and get separate NDJSON files. Forcing them into the task schema would create ambiguous status values, nullable fields, and confusing queries. Cross-references via ID fields (linked_task, source_email) connect related records across domains without schema pollution.

**Major v2 components:**
1. .github/workflows/daily-triage.yml and daily-briefing.yml — durable cron-triggered automation on GitHub runners
2. .github/mcp-config.json — runner-specific MCP config using GitHub Secrets; cannot inherit Glen's local config
3. data/todos/active.jsonl + schemas/todo-record.json — daily to-do items with human lifecycle (pending/completed/cancelled)
4. data/invoices/active.jsonl + schemas/invoice-record.json — invoice records with financial lifecycle (detected/pending-payment/paid/overdue)
5. .claude/commands/todo.md, invoice.md, daily-briefing.md — three new slash commands
6. .claude/agents/invoice-scanner.md — new subagent for lazy structured data extraction from invoice emails
7. Telegram channel plugin — mobile command bridge via `claude --channels plugin:telegram@claude-plugins-official`
8. Extended build-dashboard-data.sh — adds todos.json and invoices.json compilation
9. Extended docs/index.html — adds to-do and invoice tabs; /status command gains todo count and overdue invoice count

**Key patterns:**
- Lazy invoice extraction: skeleton record created at triage time; full extraction (amount, due date, vendor) deferred to task execution. Avoids processing 50-email triage runs with deep parsing on every email.
- Triage pipeline extension points: the /triage-inbox command's post-triage auto-queue section gains a parallel path for invoice records. The email-scanner agent itself does not change.
- Single-writer NDJSON: only one process writes to any given file at a time. Append-only format means no read-modify-write operations, preventing git merge conflicts from concurrent automated runs.

### Critical Pitfalls

1. **Gmail OAuth testing-mode token expiry (7 days, silent)** — Switch OAuth consent screen to production mode before any code is written. Testing tokens expire silently; the system stops scanning email with no error surfaced. For personal-use apps under 100 users, no Google verification is required.

2. **Desktop scheduled tasks cannot access MCP servers (bug #36327)** — Use GitHub Actions with claude-code-action@v1 for all durable scheduled automation. Desktop tasks fire on schedule but MCP tools fail silently. Confirmed by multiple independent reports, unresolved as of March 2026.

3. **Token cost explosion from naive email processing** — Strip HTML, remove signatures and reply chains, send only the latest message per thread. Use Haiku for initial categorization, escalate to Sonnet for draft generation only. Enable prompt caching (system prompt is identical across all triage requests; cache reads at 10% of input cost). Track cost per scan in the activity feed.

4. **Prompt injection via email content** — Use hardened-google-workspace-mcp (c0webster fork) which removes email sending, file sharing, and filter creation entirely. Claude can create drafts but cannot send them. Log summaries to the activity feed, never raw email content.

5. **Session-scoped /loop silently dies** — CLI scheduled tasks are destroyed on terminal close, have no catch-up for missed fires, and expire after 3 days even in active sessions. Treat /loop as interactive convenience only, never as production scheduling. Use GitHub Actions for everything that must run unattended.

6. **Scope creep disguised as "just a prompt change"** — Cap MCP servers at 3 for v2 (hardened-workspace, github, filesystem built-in). Each new integration adds an OAuth token, an API rate limit, and a failure mode. Each automation must have a clear trigger, defined success state, error handling, and feed logging.

## Implications for Roadmap

The architecture research documents a dependency-driven build order explicitly. The reasoning is sound and the suggested phases below follow it directly. All four phases can be planned and built sequentially without re-research; only Phase 4 (Telegram) warrants a verification pass before implementation given its research-preview status.

### Phase 1: Scheduled Automation (GitHub Actions)

**Rationale:** Highest-impact addition to the system. Converts manual triage into unattended daily automation. Also has the most environmental complexity — GitHub Secrets, runner MCP config, OAuth credential packaging for CI — and benefits from being tested and stable before other phases depend on it. The /triage-inbox command already exists; this phase wraps it in a durable cron trigger.
**Delivers:** Daily weekday triage at 9am UTC (approx 7:30pm ACST) running without Glen's laptop. Results committed to git, dashboard deployed automatically. Optionally chains into /daily-briefing after triage completes.
**Addresses features:** Scheduled/recurring execution (table stakes), automatic dashboard updates after unattended runs
**Avoids:** Pitfall 3 (Desktop MCP bug) by using GitHub Actions; Pitfall 5 (session-scoped /loop) by using persistent workflow triggers
**Needs research-phase:** No. GitHub Actions + claude-code-action@v1 patterns are fully documented with official examples. The hardest part is credential packaging — a configuration task, not a research question. One gap: verify hardened-workspace MCP accepts OAuth credentials from environment variables (vs. local credential files) before starting.

### Phase 2: Daily Task Management (To-Do System)

**Rationale:** Establishes the canonical pattern for adding new data domains to the system: schema definition, NDJSON seed file, slash command, feed-entry type extension, build-dashboard-data.sh addition, dashboard tab. Invoice tracking in Phase 3 follows this pattern identically. Building to-dos first de-risks invoice implementation and has zero external dependencies of its own.
**Delivers:** /todo add/list/done/cancel commands. /daily-briefing command compiling todos, pending tasks, and latest triage summary. Dashboard to-do tab. Feed schema extended with "todo" type and "telegram" trigger.
**Uses:** NDJSON pattern, jq build script, existing feed infrastructure, existing /status command (extended)
**Implements:** data/todos/active.jsonl, schemas/todo-record.json, .claude/commands/todo.md, .claude/commands/daily-briefing.md
**Avoids:** Anti-pattern of overloading the task schema — todos have human lifecycle (pending/done), tasks have Claude-execution lifecycle (pending/in-progress/completed); they are conceptually distinct and get separate files
**Needs research-phase:** No. Standard file operations and Claude Code command authoring. No novel integration.

### Phase 3: Invoice Tracking

**Rationale:** Follows the same schema-plus-command-plus-dashboard-tab pattern established in Phase 2, so the work is more mechanical than novel. Hooks into the existing triage pipeline via the already-detected action_type:"invoice" field — minimal changes to existing code. Introduces the first new subagent since v1. Must come after Phase 2 because it reuses the established domain-extension pattern.
**Delivers:** Invoice records auto-created from triage runs. /invoice list/paid/overdue/scan commands. invoice-scanner subagent for structured data extraction. Dashboard invoice tab. Overdue invoice count surfaced in /status.
**Uses:** Existing triage pipeline (email-scanner unchanged), task-executor agent (extended for invoice dispatch), hardened-workspace MCP for email content access
**Implements:** data/invoices/active.jsonl, schemas/invoice-record.json, .claude/agents/invoice-scanner.md, .claude/commands/invoice.md
**Avoids:** Synchronous extraction during triage (anti-pattern: adds parsing overhead to all 50-email scans for rare invoice case). Uses lazy evaluation: skeleton record at triage, full extraction when task is explicitly executed.
**Needs research-phase:** No. Architecture research details the exact integration points, including which lines of /triage-inbox to extend and what the invoice-scanner subagent receives as input.

### Phase 4: Telegram Mobile Commands

**Rationale:** Purely a consumption layer. Telegram invokes commands that all exist after Phases 1-3. Building it last means all commands are available for Telegram to call. This is also a research preview feature — placing it last means its instability risk does not affect the earlier stable phases. If Channels is not yet GA at implementation time, this phase should be deferred.
**Delivers:** Two-way Telegram bot for sending commands from phone and receiving concise mobile-formatted responses. Permission relay (approve/deny from phone, requires v2.1.81+). CLAUDE.md channel instructions section. Shell alias for channel-enabled Claude Code startup (`agend` alias in .zshrc).
**Uses:** Claude Code Channels feature (v2.1.80+), Telegram channel plugin, all existing commands (/triage-inbox, /todo, /invoice, /task, /status, /daily-briefing)
**Implements:** Telegram bot config, channel plugin pairing, CLAUDE.md additions for Telegram-specific response formatting
**Avoids:** Anti-pattern of routing all operations through Telegram (Telegram for quick commands, CLI for heavy work, dashboard for overview); anti-pattern of treating Telegram as a replacement for GitHub Actions (Channels requires a running local session; Actions is unattended)
**Needs research-phase:** Targeted verification pass recommended (15-30 minutes against current docs), not a full research phase. Channels is research preview as of March 2026. Plugin pairing flow, allowlist security model, and permission relay requirements should be confirmed current before starting implementation.

### Phase Ordering Rationale

- **GitHub Actions first** because autonomous daily triage is the headline v2 capability and its environmental complexity (Secrets, runner MCP config) benefits from early verification. No other phase depends on it being built first, but it delivers the most value earliest.
- **To-dos before invoices** because the pattern is identical and establishing it first creates a template. Also: to-dos have zero external dependencies, making them the lowest-risk new feature.
- **Invoice tracking before Telegram** because Telegram should be able to invoke /invoice, which does not exist until Phase 3.
- **Telegram last** because it depends on all other commands existing and it is a research preview. Its instability should not block or break phases 1-3.
- **No new MCP servers in v2** — all four phases use only the two existing MCP servers (hardened-workspace, github). This deliberately caps integration surface area per Pitfall 6 (scope creep).
- **Interactive validation before scheduling** — Phase 1 wraps an already-validated interactive command. Phases 2 and 3 should be tested interactively before Telegram (Phase 4) invokes them remotely.

### Research Flags

Phases with well-documented patterns — skip `/gsd:research-phase`:
- **Phase 1 (GitHub Actions):** claude-code-action@v1 has official examples and the MCP config passthrough is documented. This is a configuration task. One pre-work gap: verify hardened-workspace MCP accepts env-var OAuth credentials (not just local files).
- **Phase 2 (To-Do System):** Pure Claude Code command authoring and NDJSON file operations. No novel integration.
- **Phase 3 (Invoice Tracking):** Follows the Phase 2 pattern. Architecture research details exact integration points and schemas.

Phases needing a targeted verification pass before implementation:
- **Phase 4 (Telegram):** Channels is a research preview. A 15-30 minute doc check before starting is recommended to verify plugin pairing steps, allowlist security model, and permission relay requirements are current. Not a full research phase — just confirm the API surface has not changed since March 2026 research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technology choices verified against official docs or confirmed bug reports. No inferences or community speculation for critical decisions. |
| Features | HIGH | V2 feature set derived from existing system capabilities and explicit PROJECT.md requirements. Differentiators and anti-features clearly justified. |
| Architecture | HIGH | Existing v1 system is in production — baseline is not speculative. V2 integration points verified against official docs for each component. Schemas fully defined in research. |
| Pitfalls | HIGH | All critical pitfalls verified against official sources (Google OAuth docs, Claude pricing page, GitHub issue tracker with multiple duplicates). One moderate pitfall (MCP ecosystem fragility) rated MEDIUM because specific future breakage is inherently unpredictable. |

**Overall confidence:** HIGH

### Gaps to Address

- **Google OAuth production-mode verification:** Consent screen must be in production status before Phase 1 testing. One-time manual step in Google Cloud Console. Confirm the "unverified app" warning flow and any policy updates since March 2026.
- **Hardened-workspace MCP env-var credentials:** The runner cannot use Glen's local credential files. Verify the hardened fork accepts GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN as environment variables before Phase 1 starts.
- **Channels GA status at Phase 4 time:** Channels is research preview as of March 2026. Confirm GA before planning Phase 4. If still preview, defer.
- **Actual inbox volume for cost modeling:** Token cost projections in PITFALLS.md assume 50 emails/day. Measure Glen's actual inbox volume in the existing v1 system before tuning two-tier model selection and batch sizes for Phase 1 automation.
- **Dashboard privacy decision:** GitHub Pages on a free repo is public. If the new todos.json or invoices.json dashboards display any sensitive data (client names, amounts), either anonymize the data or use GitHub Pro ($4/mo) for private Pages. This decision must be made before Phase 3 commits invoice data to docs/.

## Sources

### Primary (HIGH confidence)
- [Claude Code Scheduled Tasks (official docs)](https://code.claude.com/docs/en/scheduled-tasks) — /loop session scope, 3-day expiry, cron tools
- [Claude Code GitHub Actions (official docs)](https://code.claude.com/docs/en/github-actions) — claude-code-action@v1, MCP config passthrough, scheduled workflow examples
- [Claude Code Channels (official docs)](https://code.claude.com/docs/en/channels) — Telegram plugin setup, pairing, allowlist, research preview status, v2.1.80 requirement
- [Claude Code Channels Reference (official docs)](https://code.claude.com/docs/en/channels-reference) — channel protocol, notification format, reply tools, permission relay (v2.1.81+)
- [Claude Code MCP Configuration (official docs)](https://code.claude.com/docs/en/mcp) — .mcp.json format, scope levels, transport types
- [MCP Scheduled Task Bug #36327 (GitHub)](https://github.com/anthropics/claude-code/issues/36327) — MCP tools unavailable in Desktop scheduled tasks; open as of March 2026; duplicates #35899, #35002, #33773
- [hardened-google-workspace-mcp (GitHub)](https://github.com/c0webster/hardened-google-workspace-mcp) — security removals, installation, OAuth setup
- [github/github-mcp-server (GitHub)](https://github.com/github/github-mcp-server) — remote HTTP endpoint, authentication, toolsets
- [anthropics/claude-code-action (GitHub)](https://github.com/anthropics/claude-code-action) — action configuration, MCP config support, scheduled workflow examples
- [Telegram plugin source (GitHub)](https://github.com/anthropics/claude-plugins-official/tree/main/external_plugins/telegram) — Telegram channel implementation, pairing flow
- [Google OAuth 2.0 Docs](https://developers.google.com/identity/protocols/oauth2) — token expiry policies, testing vs production mode behavior
- [Google Cloud Consent Screen](https://support.google.com/cloud/answer/15549945) — production mode requirements, verification thresholds for personal apps
- [Gmail API Usage Limits](https://developers.google.com/workspace/gmail/api/reference/quota) — quota units per method, rate limit thresholds
- [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing) — per-model token costs, premium long-context pricing threshold
- [Claude Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) — cache read pricing (10% of input), eligible content types
- [peaceiris/actions-gh-pages@v4 (GitHub)](https://github.com/peaceiris/actions-gh-pages) — GitHub Pages deployment configuration
- [NDJSON specification](https://ndjson.com/definition/) — format definition, append-only advantages, corruption isolation
- [rclone Google Drive docs](https://rclone.org/drive/) — one-way sync configuration, OAuth setup

### Secondary (MEDIUM confidence)
- Community reports corroborating Desktop MCP bug duplicates (#35899, #35002, #33773) — corroborates official issue but individual reporter accuracy varies
- MCP ecosystem fragility risk assessment — general inference from protocol maturity and lack of SLA on community servers; specific future breakage is unpredictable

---
*Research completed: 2026-03-23*
*Ready for roadmap: yes*
