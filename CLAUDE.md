<!-- GSD:project-start source:PROJECT.md -->
## Project

**Agend Ops**

A personal operations hub for the founder of Agend Systems — a small tech company (~30 clients, 2 managers) that builds and deploys association management system (AMS) modules under the "Agend" brand. The system uses Claude as an AI executive assistant that proactively manages email triage, executes delegated tasks, and logs everything to an activity feed. Data lives in a local git repo (source of truth) with a GitHub Pages dashboard for mobile-friendly glanceable access.

**Core Value:** Offload cognitive load — Claude handles email triage and task execution so Glen can focus on high-value decisions instead of drowning in operational noise.

### Constraints

- **Ecosystem**: Must work within Claude Code ecosystem (MCP servers, Claude Dispatch/Schedule)
- **Data ownership**: Local git repo as source of truth — Glen must own and control all data
- **Auth**: Gmail OAuth required for inbox access, Google Drive API for document sync, GitHub for dashboard deployment
- **Mobile**: Dashboard must be phone-friendly (responsive, glanceable)
- **Privacy**: Email content and business data must not leak to third-party services beyond Claude's own infrastructure
- **Incremental**: Must be buildable incrementally — email triage first, then task execution, then dashboard
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Claude Code | >=2.1.80 | AI runtime, task orchestration, scheduling | The entire system runs inside Claude Code sessions. v2.1.80+ required for Channels (Telegram/Discord bridge), /loop scheduling, and cron tools. This is not a library choice -- it IS the platform. |
| hardened-google-workspace-mcp | latest (fork of taylorwilsdon/google_workspace_mcp) | Gmail read, Drive access, Calendar view | Security-hardened fork that strips all data-exfiltration vectors: no email sending, no file sharing, no filter creation. Claude can read Gmail and draft replies, but cannot send -- preventing prompt injection attacks from forwarding sensitive data. |
| github/github-mcp-server | latest (remote HTTP) | GitHub operations: commits, Pages deployment, file ops | GitHub's official MCP server. Use the remote HTTP endpoint (`https://api.githubcopilot.com/mcp/`) -- no Docker required. Handles pushing generated dashboard files, managing issues, and repo operations. |
| GitHub Actions (claude-code-action@v1) | v1 | Durable scheduled automation | Session-scoped /loop tasks die when you exit and expire after 3 days. For reliable daily email triage that runs unattended, GitHub Actions with `schedule` cron triggers is the only production-grade option. Runs Claude Code on GitHub-hosted runners with full MCP access. |
| NDJSON (.jsonl) | N/A (format spec) | Activity feed data storage | Append-only, one-JSON-object-per-line. Perfect for activity logs: `echo '{"ts":"...","action":"..."}' >> feed.jsonl`. Git-friendly (append-only = clean diffs), corruption-isolated (bad line does not break the file), streamable. |
| Plain HTML/CSS/JS | N/A | GitHub Pages dashboard | Zero build step. Claude generates the HTML directly. No framework overhead for what is fundamentally a read-only status display. Fetches `feed.json` (compiled from NDJSON) at page load. |
### Supporting Libraries / Tools
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rclone | >=1.68 | Sync local data directory to Google Drive | Hybrid storage requirement: local git repo as source of truth, Drive for mobile/cross-device access. Run as post-commit hook or cron job. |
| peaceiris/actions-gh-pages | @v4 | Deploy static dashboard to GitHub Pages | Used in the GitHub Actions workflow that regenerates the dashboard after email triage runs. Pushes to `gh-pages` branch. |
| jq | >=1.7 | JSON processing in shell scripts | Transform NDJSON feed into dashboard-consumable JSON. Used in build scripts: `jq -s '.' feed.jsonl > docs/feed.json`. |
| anthropics/claude-code-action | @v1 | Run Claude Code in GitHub Actions | The official action for running Claude Code on GitHub runners. Supports `prompt`, `claude_args` (model, max-turns), and MCP config passthrough via `--mcp-config`. |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| Claude Code Skills (.claude/commands/) | Custom slash commands for ops workflows | Create `/triage-inbox`, `/draft-reply`, `/check-starred` commands as Markdown files. Skills invoke automatically when context matches; commands invoke explicitly. |
| Claude Code /loop | Session-scoped recurring tasks | Good for interactive monitoring ("check inbox every 30m while I work"). Not for unattended automation -- use GitHub Actions for that. |
| Git hooks (post-commit) | Trigger Drive sync after data changes | After Claude writes to the activity feed and commits, a post-commit hook runs `rclone copy` to sync to Drive. |
## Installation
# Claude Code (already installed -- verify version)
# Add hardened Google Workspace MCP server
# Register with Claude Code (user scope so it works across projects)
# Add GitHub MCP server (remote HTTP -- no Docker needed)
# Install rclone for Drive sync (macOS)
# Install jq for JSON processing
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| hardened-google-workspace-mcp | taylorwilsdon/google_workspace_mcp (original) | Only if you need Claude to SEND emails directly. The hardened fork deliberately removes send capability to prevent prompt injection exfiltration. For this project, "draft but don't send" is the right security posture. |
| Plain HTML/CSS/JS dashboard | Astro or 11ty static site generator | Only if the dashboard grows beyond 3-4 views and needs component reuse, templating, or partial hydration. For a single-page glanceable status view, a framework adds complexity without value. |
| NDJSON flat files | SQLite via better-sqlite3 | Only if you need to query across thousands of records with complex filters. For an activity feed that is primarily append + recent-N display, NDJSON is simpler and fully git-trackable. |
| GitHub Actions scheduled workflows | Claude Desktop scheduled tasks | Desktop tasks are persistent and survive restarts, but there is a known open bug (issue #36327) where MCP servers are not accessible during scheduled task execution. GitHub Actions is more reliable for now. |
| GitHub Actions scheduled workflows | Claude Code /loop | /loop is session-scoped (dies when you exit), expires after 3 days, and has no catch-up for missed fires. Fine for ad-hoc monitoring, not for daily email triage that must run unattended. |
| rclone sync to Google Drive | Google Drive MCP write tools | MCP tools work file-by-file through Claude's context. rclone does bulk directory sync efficiently without burning tokens. Use rclone for the automated sync; use MCP for ad-hoc document access. |
| GitHub remote HTTP MCP | @modelcontextprotocol/server-github (npm) | Never. The npm package is deprecated as of April 2025. Use the official remote HTTP endpoint. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| taylorwilsdon/google_workspace_mcp (unmodified) | Has email sending, file sharing, filter creation tools that are vulnerable to prompt injection. An attacker could embed instructions in email body that cause Claude to forward sensitive data. | hardened-google-workspace-mcp (c0webster fork) |
| @modelcontextprotocol/server-github (npm) | Deprecated since April 2025. No longer maintained. | github/github-mcp-server remote HTTP endpoint |
| Claude Desktop scheduled tasks (for production) | Open bug #36327: scheduled tasks cannot access MCP servers. MCP tools fail silently during scheduled execution. Multiple duplicate issues confirm this is unresolved as of March 2026. | GitHub Actions with claude-code-action@v1 |
| Any JavaScript SPA framework (React, Vue, Svelte) for dashboard | Massive overkill for a read-only status page. Adds build toolchain, node_modules, bundler config. Claude can generate plain HTML faster and more reliably than framework code. | Plain HTML + CSS + vanilla JS that fetches feed.json |
| SQLite or any database | Adds a binary dependency that is not git-diffable, requires backup strategy, and adds complexity for what is fundamentally an append-only log. | NDJSON files committed to git |
| External SaaS for data storage (Notion, Airtable, etc.) | Violates the "data ownership" constraint. Glen must own and control all data in a local git repo. | Local NDJSON files + git + rclone to Drive |
| Composio, Rube, or MCP aggregator services | Adds a third-party intermediary for auth and data flow. Privacy constraint: business data must not leak beyond Claude's own infrastructure. | Direct MCP server connections (hardened workspace + GitHub) |
## Stack Patterns by Variant
- Use Claude Code CLI directly with MCP servers
- Use /loop for monitoring tasks ("check inbox every 30m")
- Trigger operations manually: "triage my inbox", "draft a reply to Sarah's email"
- Activity feed updates commit to local git immediately
- Use GitHub Actions with `schedule` cron trigger
- claude-code-action@v1 with `--mcp-config` pointing to MCP configuration
- Prompt instructs Claude to: read inbox, categorize, log to feed, commit, push
- peaceiris/actions-gh-pages@v4 deploys updated dashboard
- Note: MCP servers must be configured in the GitHub Actions environment (not inherited from local)
- GitHub Pages dashboard (responsive HTML)
- Dashboard reads `feed.json` (static file, no API needed)
- Claude Code Channels via Telegram for ad-hoc commands (requires v2.1.80+, research preview)
## Version Compatibility
| Component | Compatible With | Notes |
|-----------|-----------------|-------|
| Claude Code >=2.1.80 | claude-code-action@v1 | Action runs Claude Code on GitHub runners. Ensure runner installs correct version. |
| hardened-google-workspace-mcp | Python 3.10+, uv package manager | Uses `uv sync` for dependency management. Google Cloud OAuth 2.0 credentials required. |
| github/github-mcp-server (remote HTTP) | Claude Code >=2.1.72 | HTTP transport supported since early 2026. Requires GitHub PAT with `repo` scope. |
| peaceiris/actions-gh-pages@v4 | actions/checkout@v4 | Must checkout repo before deploying. Push to `gh-pages` branch. |
| rclone >=1.68 | Google Drive API v3 | Requires OAuth app or service account. Configure via `rclone config`. |
| jq >=1.7 | NDJSON files | Use `jq -s '.'` to convert NDJSON to JSON array for dashboard consumption. |
## Known Issues and Caveats
### MCP Servers in Scheduled Tasks (CRITICAL)
### Hardened Workspace MCP Limitations
- Claude can READ emails but not SEND them (by design)
- Claude can CREATE drafts that Glen reviews and sends manually from Gmail
- Data leakage is still possible through shared folders or attacker-owned documents
- User must review tool permissions before approval each time
### Three-Day /loop Expiry
### GitHub Actions Cost
- GitHub Actions minutes (free tier: 2,000 min/month for private repos)
- Anthropic API tokens (proportional to inbox size and task complexity)
- Running daily at 9am with a 10-minute timeout: ~300 min/month (well within free tier)
## Sources
- [Claude Code Scheduled Tasks (official docs)](https://code.claude.com/docs/en/scheduled-tasks) -- /loop, cron tools, session scope, 3-day expiry -- HIGH confidence
- [Claude Code MCP Configuration (official docs)](https://code.claude.com/docs/en/mcp) -- .mcp.json format, scope levels, transport types -- HIGH confidence
- [Claude Code GitHub Actions (official docs)](https://code.claude.com/docs/en/github-actions) -- claude-code-action@v1 setup, scheduled workflows, MCP config -- HIGH confidence
- [Claude Code Channels (official docs)](https://code.claude.com/docs/en/channels) -- Telegram/Discord push messages, research preview, v2.1.80 requirement -- HIGH confidence
- [hardened-google-workspace-mcp (GitHub)](https://github.com/c0webster/hardened-google-workspace-mcp) -- security removals, installation, OAuth setup -- HIGH confidence
- [github/github-mcp-server (GitHub)](https://github.com/github/github-mcp-server) -- remote HTTP endpoint, authentication, toolsets -- HIGH confidence
- [MCP Scheduled Task Bug #36327 (GitHub)](https://github.com/anthropics/claude-code/issues/36327) -- MCP tools unavailable in Desktop scheduled tasks -- HIGH confidence
- [peaceiris/actions-gh-pages (GitHub)](https://github.com/peaceiris/actions-gh-pages) -- v4 for GitHub Pages deployment -- HIGH confidence
- [NDJSON specification](https://ndjson.com/definition/) -- format definition, append-only advantages -- HIGH confidence
- [rclone Google Drive docs](https://rclone.org/drive/) -- configuration, sync commands -- HIGH confidence
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

## MCP Server Usage

CRITICAL: Use ONLY the `hardened-workspace` MCP server for Gmail and Drive access.
DO NOT use `claude.ai Gmail` or `claude.ai Google Calendar` connectors -- they can
send emails and route data through external servers.

When accessing Gmail or Drive, use tools prefixed with `mcp__hardened-workspace__`.

Security model: Claude can READ emails and CREATE drafts, but CANNOT send emails,
share files, create filters, or delete anything. This is enforced by the hardened MCP
fork and is the primary defense against prompt injection attacks.

## Data Conventions

- Activity feed: Append to `data/feed.jsonl` (NDJSON, one JSON object per line)
  - Required fields: ts, type, summary, level, trigger
  - Types: triage, task, draft, system, command
  - All timestamps in ISO 8601 with timezone offset (e.g., 2026-03-23T10:30:00+10:00)
- Triage results: Create new file in `data/triage/` named by ISO timestamp (e.g., `2026-03-23T0900.jsonl`)
  - One record per email. Required fields: message_id, thread_id, from, subject, received, priority
- Task records: Append to `data/tasks/active.jsonl`
  - Required fields: id (task-YYYY-MM-DD-NNN), ts, status, description, trigger
- Action queue: `data/queue/actions.jsonl` (pending actions from dashboard), `data/queue/processed.jsonl` (completed actions)
  - Required fields: id, ts, action, target_id, status, requested_by
  - Actions: mark-paid, complete-todo, complete-task, trigger-triage
  - Schema: `schemas/action-queue-entry.json`
- Schemas: See `schemas/` directory for full JSON Schema definitions of all record types
- Dashboard data: Run `scripts/build-dashboard-data.sh` to compile NDJSON into `docs/feed.json` and `docs/tasks.json`

## Commands

Custom operations available as slash commands:

- `/status` -- Quick summary: recent activity count, triage runs, pending tasks
- `/task <description>` -- Create and execute a task via task-executor subagent. Supports: `/task` (show queue), `/task run id` (execute pending), `/task list` (show all), `/task natural language` (create + execute)
- `/feed [count]` -- Show recent activity feed entries (default: 10)
- `/triage-inbox` -- Scan Gmail inbox via email-scanner subagent: categorize emails, generate draft replies, detect action items, auto-queue actionable items as pending tasks
- `/process-queue` -- Process pending actions queued from the interactive dashboard (mark-paid, complete-todo, complete-task, trigger-triage)

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
