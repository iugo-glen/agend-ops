# Project Research Summary

**Project:** Agend Ops — AI-powered personal operations hub
**Domain:** Single-user founder automation (email triage, task execution, activity feed, glanceable dashboard)
**Researched:** 2026-03-23
**Confidence:** HIGH

## Executive Summary

Agend Ops is a personal AI operations hub that runs entirely inside Claude Code. Unlike SaaS competitors (Lindy, Superhuman, OpenClaw), it keeps all data in a local git repository that Glen owns and controls. The system's architecture is simple but requires careful component selection: the hardened Google Workspace MCP server (c0webster fork) replaces the original to eliminate prompt injection exfiltration vectors, and GitHub Actions replaces Claude Desktop scheduled tasks due to a confirmed platform bug (#36327) that prevents MCP tools from working in Desktop-scheduled contexts. The core runtime is Claude Code acting as orchestrator — reading Gmail, generating drafts, logging activity, and committing results to git — with GitHub Pages serving a static dashboard compiled from the activity feed.

The recommended build order follows hard technical dependencies: Google OAuth must be in production mode before anything else (testing tokens expire in 7 days, silently breaking the system), and the NDJSON activity feed schema must be established before any data is written. Email triage runs interactively first (debugged manually), then is automated via GitHub Actions once the flows are verified. The dashboard can be built in parallel using mock data and does not block email triage. The most differentiating capability — starred-email-as-intent-queue mapping to Glen's existing Gmail workflow — is table stakes complexity but genuinely distinct from any commercial tool.

The main risks are all well-documented and preventable: token cost explosion from naive email processing (mitigated by two-tier models and prompt caching), prompt injection from email content (mitigated by the hardened MCP fork), silent scheduling failures (mitigated by GitHub Actions over /loop), and scope creep (mitigated by enforcing a 3-MCP-server cap for v1). All research is HIGH confidence, sourced from official Claude Code docs, official MCP repositories, and verified platform bug reports.

## Key Findings

### Recommended Stack

The system is a Claude Code-native application, not a traditional software project. Claude Code itself is the runtime, orchestrator, and primary interface. MCP servers are the integration layer; GitHub is both version control and deployment infrastructure; and NDJSON flat files in git replace any database. This means the "stack" is primarily a configuration and composition decision rather than a programming language or framework decision.

The two non-obvious stack choices are: (1) using the hardened Google Workspace MCP fork rather than the popular original, which is a security requirement not a preference; and (2) using GitHub Actions rather than Claude Desktop's built-in scheduling, which is a reliability requirement due to confirmed bug #36327.

**Core technologies:**
- Claude Code >=2.1.80: Runtime, orchestrator, primary interface — the entire system runs here
- hardened-google-workspace-mcp (c0webster fork): Gmail read + draft creation, no send/share capability — required for prompt injection safety
- github/github-mcp-server (remote HTTP endpoint): GitHub file ops, repo management, Pages deploy status — use official endpoint, npm package deprecated April 2025
- GitHub Actions + claude-code-action@v1: Durable scheduled automation — only reliable MCP-capable scheduling option due to Desktop bug #36327
- NDJSON flat files committed to git: All structured data storage — append-only, git-diffable, no binary dependencies
- Plain HTML/CSS/JS on GitHub Pages: Mobile-friendly glanceable dashboard — zero build step, Claude generates directly
- rclone + Google Drive: Optional cross-device sync — one-way push only, git is always source of truth
- jq >=1.7: NDJSON-to-JSON compilation for dashboard — `jq -s '.' data/feed.jsonl > docs/feed.json`

### Expected Features

The MVP hypothesis is: if inbox scanning, categorization, and starred-queue surfacing work reliably, the core cognitive load relief is proven. Draft generation and task execution are table stakes for v1 but are validation additions, not MVP blockers. Everything beyond Gmail + Dashboard is explicitly deferred.

**Must have (table stakes):**
- Gmail OAuth (production mode) + hardened MCP — without this nothing works; zero-day decision
- NDJSON activity feed schema — must exist before any data is written; all downstream depends on it
- Inbox scanning with 4-bucket categorization (urgent, needs-response, informational, low-priority) — core value prop
- Starred email priority queue — maps to Glen's existing workflow, unique differentiator, low implementation cost
- Draft reply generation — Claude creates Gmail drafts; Glen reviews and sends manually from Gmail
- Static GitHub Pages dashboard — unread count, starred queue, recent activity; responsive mobile-first
- Manual task kickoff via Claude Code commands (`/triage-inbox`, `/draft-reply`, `/scan-starred`)
- Human-in-the-loop approval before sending — enforced architecturally by hardened MCP fork

**Should have (v1.x — after core validation):**
- GitHub Actions scheduled triage (daily weekday, unattended) — automates the manual flow
- Actionable item detection (contracts, invoices, meeting requests) — goes beyond triage into extraction
- Task suggestion and Google Drive document retrieval — compound value, higher complexity
- Context accumulation (client interaction summaries stored in git) — compounds over weeks
- rclone Drive sync — enhances mobile access beyond read-only dashboard

**Defer (v2+):**
- Telegram/Discord command channel — Channels feature is research preview, not GA; do not block v1
- Calendar awareness — separate complex domain with enormous scope creep risk
- Autonomous sending for low-risk categories — only after weeks of proven accuracy
- Invoice tracking — explicitly out of scope in PROJECT.md
- Multi-step task execution chains

**Explicit anti-features (never build in v1):**
- Autonomous email sending — prompt injection risk and trust destruction if AI sends wrong email to client
- Real-time push notifications — defeats deep-work purpose, adds significant infra complexity
- Native mobile app — GitHub Pages dashboard + Telegram channel is sufficient for single-user
- Multi-user features — transforms personal tool into team platform with massive scope implications

### Architecture Approach

The architecture follows a Command-Skill-Commit Loop: every operation receives a trigger, executes a skill/command, writes NDJSON/JSON data, commits to git, and optionally pushes. Git commit is the atomic unit of state change. Heavy operations (inbox scan, document analysis) run in subagents to preserve the main conversation's context window. The dashboard is a static HTML/JS page with a single JSON data contract (`docs/feed.json`) compiled from NDJSON — no server, no API, no database.

Two-tier scheduling separates interactive use (/loop, session-scoped, acceptable for ad-hoc monitoring) from durable automation (GitHub Actions, persists when laptop is off, has explicit MCP configuration). MCP configuration in GitHub Actions is separate from local configuration and must be set up explicitly using workflow secrets and a `.github/mcp-config.json` file — it does not inherit from local `settings.local.json`.

**Major components:**
1. Claude Code Runtime — orchestrates all operations; CLAUDE.md, hooks, and skills define behavior
2. hardened-google-workspace-mcp — Gmail read + draft, Drive access; cannot send or share by design
3. github/github-mcp-server — file ops, Pages status, repo management via remote HTTP endpoint
4. Local git repo (data/) — source of truth; NDJSON for append logs, JSON for mutable state, `docs/` for Pages
5. GitHub Actions (triage.yml) — durable scheduled automation with own MCP config separate from local
6. GitHub Pages (docs/) — static dashboard served from `docs/` directory, no separate gh-pages branch
7. Hooks + Scripts — PostToolUse hooks enforce JSON validation; build-dashboard-data.sh compiles NDJSON feed
8. Subagents (.claude/agents/) — email-scanner and task-executor isolate heavy context operations from main conversation

### Critical Pitfalls

1. **Gmail OAuth in testing mode** — tokens expire in 7 days silently, system stops scanning email with no alerting; switch consent screen to "In Production" on day one before any code is written
2. **Token cost explosion from naive email processing** — full email threads (HTML, signatures, reply chains) can cost $2-4 per scan; strip HTML to plain text, use Haiku for initial categorization and Sonnet only for drafts, enable prompt caching (10% of input cost for system prompt reads)
3. **Desktop scheduled tasks cannot access MCP servers** — confirmed bug #36327 with multiple duplicates, unresolved as of March 2026; use GitHub Actions for all unattended automation; never rely on Desktop scheduled tasks for MCP-dependent operations
4. **Prompt injection via email content** — attacker embeds instructions in email body that could cause data exfiltration; use c0webster/hardened-google-workspace-mcp exclusively, which removes all send/share/filter-creation tools
5. **Session-scoped /loop silently dies** — destroyed on terminal close, no persistence across restarts, 3-day auto-expiry even in active sessions; treat it as interactive convenience only, not production scheduling
6. **Scope creep** — each new integration feels like "just a prompt change" but adds OAuth, rate limits, and failure modes; cap at 3 MCP servers for v1 and enforce PROJECT.md out-of-scope items ruthlessly

## Implications for Roadmap

Research is unusually prescriptive about build order. ARCHITECTURE.md explicitly defines a 6-phase dependency chain, FEATURES.md identifies the exact MVP feature set, and PITFALLS.md identifies which phases have critical gotchas. The suggested phases below follow hard dependencies, not arbitrary grouping.

### Phase 1: Foundation (Infrastructure and Credentials)

**Rationale:** Everything in the system depends on Google OAuth and the data directory structure. This is the zero-value phase that unblocks all subsequent work. Must be done first, cannot be parallelized.
**Delivers:** Working MCP connections verified interactively, NDJSON schema established, repo structure initialized, CLAUDE.md instructions written, basic validation scripts in place
**Addresses:** Google OAuth (P0), NDJSON schema definition (P0) from FEATURES.md
**Avoids:** Token expiry pitfall (#1 — production mode here), prompt injection pitfall (#4 — install hardened fork here), Desktop scheduling pitfall (#3 — architect for GitHub Actions from the start)
**Research flag:** Standard patterns for MCP setup. Verify the exact "In Production" consent screen steps and the "unverified app" warning flow during implementation.

### Phase 2: Interactive Email Triage

**Rationale:** Depends on Phase 1 (MCP servers + data structure). Core value proposition. Must work interactively before scheduling. Manual invocation allows debugging without automation complexity layered on top.
**Delivers:** Working `/triage-inbox` and `/scan-starred` commands; email-scanner subagent; 4-bucket categorization; starred queue processing; activity feed writing to data/feed.jsonl
**Uses:** hardened-google-workspace-mcp, email-scanner subagent (.claude/agents/email-scanner.md), NDJSON append pattern
**Implements:** Command-Skill-Commit Loop pattern, subagent isolation for heavy operations
**Avoids:** Token cost explosion (#2 — implement two-tier model and HTML stripping here), Gmail rate limits (#7 — incremental sync and exponential backoff from start), triage quality degradation (#14 — suggest-only warmup period first)
**Research flag:** Skip deeper research. Patterns are well-documented in research files. Implementation is primarily command authoring and subagent configuration.

### Phase 3: Draft Generation and Task Execution

**Rationale:** Depends on Phase 2 (emails must exist to act on). Extends triage into action. Unlocks the "draft reply to Sarah" workflow central to the value proposition.
**Delivers:** Working `/draft-reply` command; task-executor subagent; draft storage in data/emails/drafts/ as markdown files; Gmail draft creation via hardened MCP; task records in data/tasks/pending.json
**Uses:** hardened-google-workspace-mcp (Drive access for document retrieval), task-executor subagent (.claude/agents/task-executor.md)
**Implements:** Manual Task Execution Flow from ARCHITECTURE.md
**Avoids:** Autonomous sending (architecturally prevented by hardened MCP fork)
**Research flag:** Validate hardened-google-workspace-mcp draft creation workflow hands-on. Research file notes Claude can create Gmail drafts but implementation details need hands-on verification.

### Phase 4: Static Dashboard

**Rationale:** Can be built in parallel with Phases 2-3 using mock data. Depends only on the feed.json data contract established in Phase 1 (NDJSON schema). Provides mobile access and glanceable status.
**Delivers:** docs/index.html + styles.css + app.js; build-dashboard-data.sh script (jq NDJSON compilation); GitHub Pages configured from docs/ directory; responsive mobile-first layout showing unread count, starred queue, recent activity
**Uses:** Plain HTML/CSS/JS, jq, peaceiris/actions-gh-pages@v4
**Implements:** Static Dashboard via JSON Data Contract pattern from ARCHITECTURE.md
**Avoids:** Dashboard data exposure (#9 — aggregate/anonymize data, add robots.txt, use private repo + GitHub Pro for private Pages)
**Research flag:** Skip deeper research. Static HTML dashboard with jq data compilation is straightforward. GitHub Pages configuration from docs/ directory is well-documented.

### Phase 5: Scheduled Automation

**Rationale:** Depends on Phases 2-3 (operations must exist and be validated before scheduling). Debug interactively first, then automate. GitHub Actions is the only reliable durable scheduling option — this is a hard constraint, not a preference.
**Delivers:** .github/workflows/triage.yml with weekday 9am cron; .github/mcp-config.json for runner MCP configuration; GitHub Actions secrets setup; auto-commit + auto-push pipeline; dashboard auto-deploys after each triage run
**Uses:** anthropics/claude-code-action@v1, GitHub Actions cron schedule, workflow secrets for MCP credentials
**Implements:** Two-Tier Scheduling Architecture (GitHub Actions tier)
**Avoids:** Desktop tasks pitfall (#3 — GitHub Actions only), /loop silently dies pitfall (#5 — /loop is interactive only)
**Research flag:** Needs research phase during planning. GitHub Actions runner-side MCP configuration (separate from local settings, using workflow secrets and explicit mcp-config.json) has specific setup requirements. ARCHITECTURE.md has a workflow template but the exact secret names, mcp-config.json format, and runner environment validation need confirmation before implementation.

### Phase 6: Mobile Commands and Drive Sync (Optional v1.x)

**Rationale:** Quality-of-life additions after core system is validated. Channels is research preview (may not be stable at v1 time). Drive sync is convenient but GitHub Pages already provides mobile read access; git already provides version control.
**Delivers:** Telegram/Discord channel setup (if Channels is GA); rclone one-way push from repo to Google Drive for cross-device file access
**Uses:** Claude Code Channels (v2.1.80+), rclone >=1.68
**Avoids:** Drive sync complexity (#13 — one-way push only, never bidirectional sync, git is always source of truth)
**Research flag:** Needs research phase. Channels is research preview as of March 2026 — stability, allowlist security model, and Telegram setup steps need verification at time of implementation. Do not plan or build this phase until Channels is confirmed GA.

### Phase Ordering Rationale

- Phases 1 through 3 are strictly sequential due to hard dependencies (OAuth before triage, triage before drafts)
- Phase 4 (Dashboard) can run in parallel with Phases 2-3 using mock data, but requires Phase 1 schema definition
- Phase 5 (Scheduling) must come after Phases 2-3 are validated interactively — automating unvalidated flows makes debugging dramatically harder
- Phase 6 is explicitly optional and should not be planned until the Channels feature is confirmed GA
- The "validate interactively before automating" pattern is critical: bugs discovered in the GitHub Actions scheduled context are much harder to debug than bugs discovered in interactive sessions
- NDJSON schema defined in Phase 1 is the data contract that all later phases depend on — changing it after Phase 2 ships is a breaking change

### Research Flags

Phases needing deeper research during planning:
- **Phase 5 (Scheduling):** GitHub Actions runner-side MCP configuration requires workflow secrets and an `.github/mcp-config.json` file that local setup does not generate. The pattern is documented in ARCHITECTURE.md but exact secret names, MCP config format for the runner environment, and how credentials flow from GitHub secrets to MCP server startup need validation before implementation begins.
- **Phase 6 (Channels):** Research preview feature. Stability, allowlist security model, and Telegram/Discord setup steps need fresh verification at time of implementation. Do not plan until confirmed GA.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** MCP server installation documented in official Claude Code docs and MCP server repos. Google OAuth production mode is standard Google Cloud setup.
- **Phase 2 (Interactive Triage):** Subagent pattern, NDJSON append, command authoring — all thoroughly documented in official Claude Code docs.
- **Phase 3 (Drafts/Tasks):** Extension of Phase 2 patterns. Hands-on validation of hardened MCP draft creation is implementation-time work, not planning-time research.
- **Phase 4 (Dashboard):** Static HTML/JS with jq compilation — no novel patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Every technology choice sourced from official docs or verified bug reports. No inferences or community speculation. |
| Features | HIGH | MVP feature set derived from dependency analysis; P0/P1/P2 prioritization is well-justified and grounded in technical constraints. |
| Architecture | HIGH | Official Claude Code docs, official MCP repos, confirmed platform bug #36327. Data flow diagrams in ARCHITECTURE.md are specific and actionable. |
| Pitfalls | HIGH | All critical pitfalls verified against official documentation or confirmed GitHub issues with multiple duplicates. |

**Overall confidence:** HIGH

### Gaps to Address

- **GitHub Actions MCP runner configuration:** ARCHITECTURE.md has a workflow template but the exact format for `.github/mcp-config.json`, which workflow secrets are required, and how MCP server startup works in the runner environment should be validated in Phase 5 planning before implementation begins.
- **Google OAuth production mode flow:** Research states no Google verification is required for fewer than 100 users, but the exact "unverified app" warning screen and any additional Google policy requirements (as of 2026) should be confirmed hands-on during Phase 1.
- **Channels feature GA status:** Telegram/Discord Channels is research preview as of March 2026. Phase 6 planning should not start until GA status is confirmed.
- **Triage accuracy baseline:** No guidance exists from research on expected categorization accuracy. Phase 2 should run in "suggest only" mode for the first 2-4 weeks with lightweight feedback tracking before trusting Claude's triage decisions for unattended automation in Phase 5.
- **Cost modeling with real inbox volume:** Token cost projections in PITFALLS.md assume 50 emails/day. Actual Glen inbox volume should be measured in Phase 2 and used to tune two-tier model selection and batch sizes before Phase 5 automation.

## Sources

### Primary (HIGH confidence)
- [Claude Code Scheduled Tasks (official docs)](https://code.claude.com/docs/en/scheduled-tasks) — /loop session scope, 3-day expiry, cron tools
- [Claude Code MCP Configuration (official docs)](https://code.claude.com/docs/en/mcp) — .mcp.json format, scope levels, transport types
- [Claude Code GitHub Actions (official docs)](https://code.claude.com/docs/en/github-actions) — claude-code-action@v1, scheduled workflows, MCP config passthrough
- [Claude Code Channels (official docs)](https://code.claude.com/docs/en/channels) — Telegram/Discord bridge, research preview status, v2.1.80 requirement
- [hardened-google-workspace-mcp (GitHub)](https://github.com/c0webster/hardened-google-workspace-mcp) — security removals, installation, OAuth setup
- [github/github-mcp-server (GitHub)](https://github.com/github/github-mcp-server) — remote HTTP endpoint, authentication, toolsets
- [MCP Scheduled Task Bug #36327 (GitHub)](https://github.com/anthropics/claude-code/issues/36327) — confirmed MCP tools unavailable in Desktop scheduled tasks; multiple duplicates #35899, #35002, #33773
- [Gmail API Quota Docs](https://developers.google.com/workspace/gmail/api/reference/quota) — quota units per method, rate limit thresholds
- [Google OAuth 2.0 Docs](https://developers.google.com/identity/protocols/oauth2) — testing vs production token expiry policy
- [Google Cloud Consent Screen](https://support.google.com/cloud/answer/15549945) — production mode requirements, verification thresholds
- [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing) — per-model token costs; premium long-context pricing threshold
- [Claude Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) — cache read pricing (10% of input), eligible content types
- [NDJSON specification](https://ndjson.com/definition/) — format advantages for append-only logging
- [peaceiris/actions-gh-pages@v4 (GitHub)](https://github.com/peaceiris/actions-gh-pages) — GitHub Pages deployment from docs/ directory
- [rclone Google Drive docs](https://rclone.org/drive/) — one-way sync configuration, OAuth setup

### Secondary (MEDIUM confidence)
- Community patterns for AI agent scope creep mitigation — well-documented failure mode, general consensus across multiple sources
- MCP ecosystem fragility risk — general inference from protocol maturity level and lack of SLA on community servers

---
*Research completed: 2026-03-23*
*Ready for roadmap: yes*
