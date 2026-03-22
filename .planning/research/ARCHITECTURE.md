# Architecture Research

**Domain:** AI-powered personal operations hub (Claude Code + MCP + git data store + GitHub Pages dashboard)
**Researched:** 2026-03-23
**Confidence:** HIGH

## System Overview

```
                          Glen (Operator)
                    +----------+----------+
                    |          |          |
              +-----v--+  +---v----+  +--v----------+
              | Claude  |  | Mobile |  | Telegram/    |
              | Code    |  | Phone  |  | Discord      |
              | (CLI)   |  |        |  | (Channels)   |
              +----+----+  +---+----+  +------+-------+
                   |           |              |
        +----------+      +----v-----+   +----v---------------+
        |          |      | GitHub   |   | Channel Plugin      |
        |     +----v----+ | Pages    |   | (MCP server         |
        |     | Hooks + | | Dashboard|   |  push events)       |
        |     | Skills  | +----+-----+   +----+----------------+
        |     +----+----+      |              |
        |          |      Reads JSON      Push into session
   +----v----------v--------------v-----------v-----------------+
   |                  Claude Code Runtime                        |
   |  +----------+  +----------+  +------------------+          |
   |  | Scheduled|  | Subagents|  | Core Agent Loop   |          |
   |  | Tasks    |  |          |  | (triage, execute, |          |
   |  | /loop    |  | email-   |  |  log, commit)     |          |
   |  | cron     |  | scanner  |  |                   |          |
   |  +----+-----+  | task-    |  +--------+----------+          |
   |       |        | executor |           |                     |
   |       |        +----+-----+           |                     |
   |       |             |                 |                     |
   |  +----v-------------v-----------------v-----------+         |
   |  |              MCP Server Layer                  |         |
   |  |  +--------+  +--------+  +----------------+   |         |
   |  |  | Google |  | Google |  | GitHub         |   |         |
   |  |  | Work-  |  | Work-  |  | MCP Server     |   |         |
   |  |  | space  |  | space  |  | (remote HTTP)  |   |         |
   |  |  |(Gmail) |  |(Drive) |  |                |   |         |
   |  |  +--------+  +--------+  +----------------+   |         |
   |  +------------------------------------------------+         |
   +----------------------+--------------------------------------+
                          |
   +----- GitHub Actions -v--------------------------------------+
   |  claude-code-action@v1 (durable scheduled automation)       |
   |  - Runs daily email triage on cron schedule                 |
   |  - Has own MCP server configuration                         |
   |  - Commits results + pushes to trigger Pages deploy         |
   +-------------------------------------------------------------+
                          |
   +----------------------v--------------------------------------+
   |              Local Git Repository (Data Store)               |
   |                                                              |
   |  data/                                                       |
   |  +-- feed.jsonl          # NDJSON append-only activity log   |
   |  +-- emails/                                                 |
   |  |   +-- inbox.jsonl     # Triaged email records (NDJSON)    |
   |  |   +-- starred.json    # Current starred email queue       |
   |  |   +-- drafts/         # Pending reply drafts              |
   |  +-- tasks/                                                  |
   |  |   +-- pending.json    # Awaiting approval/action          |
   |  |   +-- completed/      # Completed task records            |
   |  +-- config/                                                 |
   |      +-- categories.json # Email categorization rules        |
   |      +-- contacts.json   # Known contacts + context          |
   |                                                              |
   |  docs/                   # GitHub Pages static site          |
   |  +-- index.html          # Dashboard shell                   |
   |  +-- styles.css          # Dashboard styles                  |
   |  +-- app.js              # Dashboard client-side JS          |
   |  +-- feed.json           # Compiled from feed.jsonl          |
   |                                                              |
   |  .claude/                # Claude Code project config        |
   |  +-- CLAUDE.md           # Master project instructions       |
   |  +-- settings.json       # Hooks, permissions                |
   |  +-- settings.local.json # Secrets (gitignored)              |
   |  +-- commands/           # Custom slash commands              |
   |  |   +-- triage-inbox.md                                     |
   |  |   +-- draft-reply.md                                      |
   |  |   +-- scan-starred.md                                     |
   |  +-- agents/             # Subagent definitions               |
   |      +-- email-scanner.md                                    |
   |      +-- task-executor.md                                    |
   +--------------------------------------------------------------+
            |                              |
       git push                      GitHub Pages
       (to remote)                   auto-deploys from docs/
            |                              |
   +--------v------------------------------v---------------------+
   |                   GitHub Remote                              |
   |  +------------------+  +----------------------------+       |
   |  | Repository        |  | GitHub Pages                |       |
   |  | (source of truth  |  | (serves docs/index.html    |       |
   |  |  backup)          |  |  + docs/feed.json)          |       |
   |  +------------------+  +----------------------------+       |
   +--------------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| **Claude Code Runtime** | Orchestrates all operations: email scanning, task execution, activity logging, data commits | Claude Code CLI >=2.1.80 with CLAUDE.md instructions, hooks, and skills |
| **hardened-google-workspace-mcp** | Read Gmail inbox, create drafts, access Drive documents. Cannot send emails or share files (by design). | c0webster/hardened-google-workspace-mcp, Python 3.10+, uv, Google OAuth 2.0 |
| **github/github-mcp-server** | GitHub operations: file ops, repo management, Pages deployment status | Remote HTTP endpoint at api.githubcopilot.com/mcp/, PAT auth |
| **GitHub Actions** | Durable scheduled automation that runs even when laptop is off | anthropics/claude-code-action@v1 with cron schedule trigger |
| **Local Git Repo** | Source of truth for all structured data | NDJSON flat files committed to git with semantic commit messages |
| **GitHub Pages Dashboard** | Mobile-friendly glanceable status view | Static HTML/JS that reads `feed.json`. Served from `docs/` directory. |
| **Channels (Telegram/Discord)** | Push events into running session from phone; two-way command bridge | Research preview feature, requires v2.1.80+, allowlist security |
| **Hooks** | Enforce policies, automate cross-cutting concerns | PostToolUse hooks for JSON validation, dashboard rebuild |
| **Skills/Commands** | Reusable operation templates | Markdown files in `.claude/commands/` |

## Recommended Project Structure

```
todo-list/                              # Root (the git repo IS the data store)
+-- .claude/
|   +-- CLAUDE.md                       # Master project instructions
|   +-- settings.json                   # Hooks, permissions, project config
|   +-- settings.local.json             # Local-only settings (gitignored)
|   +-- commands/
|   |   +-- triage-inbox.md             # Command: full inbox triage workflow
|   |   +-- draft-reply.md              # Command: compose email reply
|   |   +-- scan-starred.md             # Command: check starred queue
|   |   +-- execute-task.md             # Command: run an approved task
|   |   +-- rebuild-dashboard.md        # Command: regenerate dashboard
|   +-- agents/
|       +-- email-scanner.md            # Subagent: inbox triage (Sonnet)
|       +-- task-executor.md            # Subagent: execute approved tasks
+-- data/
|   +-- feed.jsonl                      # NDJSON append-only activity log
|   +-- emails/
|   |   +-- inbox.jsonl                 # Triaged email records (NDJSON, recent)
|   |   +-- starred.json               # Current starred email queue
|   |   +-- drafts/                     # Pending reply drafts (one file per draft)
|   |   |   +-- 2026-03-23-sarah-contract.md
|   |   +-- archive/                    # Monthly archives
|   |       +-- 2026-03.jsonl
|   +-- tasks/
|   |   +-- pending.json                # Tasks awaiting approval
|   |   +-- completed/                  # Completed task records (monthly)
|   |       +-- 2026-03.jsonl
|   +-- config/
|       +-- categories.json             # Email categorization rules/examples
|       +-- contacts.json               # Known contacts + context
+-- docs/                               # GitHub Pages source (served from here)
|   +-- index.html                      # Dashboard shell
|   +-- styles.css                      # Responsive mobile-first CSS
|   +-- app.js                          # Fetch feed.json, render activity
|   +-- feed.json                       # Compiled from feed.jsonl for dashboard
+-- scripts/
|   +-- build-dashboard-data.sh         # Compile NDJSON -> feed.json
|   +-- validate-data.sh                # Validate JSON/NDJSON before commit
+-- .github/
|   +-- workflows/
|       +-- triage.yml                  # Scheduled email triage via GitHub Actions
|       +-- deploy-dashboard.yml        # (optional) separate dashboard deploy
+-- .gitignore                          # .claude/settings.local.json, *.lock, etc.
```

### Structure Rationale

- **`data/`:** All structured data lives here. NDJSON for append-only logs (feed, inbox, archives), JSON for mutable state (starred queue, pending tasks, config). Each domain is a separate directory. Archive subdirectories prevent files from growing unbounded.
- **NDJSON over JSON arrays:** Append-only writes (no read-modify-write cycle), corruption-isolated (bad line does not break file), git-friendly (append = clean diffs), streamable.
- **`.claude/`:** All Claude Code configuration. Checked into git for reproducibility. `settings.local.json` is gitignored for OAuth secrets.
- **`docs/`:** GitHub Pages source. Using `docs/` directory (GitHub Pages setting) instead of `gh-pages` branch. Simpler -- dashboard files live alongside data, one branch, one push.
- **`scripts/`:** Shell scripts for data transformation. Called by hooks or manually. `build-dashboard-data.sh` compiles NDJSON into the single `feed.json` the dashboard consumes.
- **`.github/workflows/`:** GitHub Actions for durable scheduled automation. Separate from Claude Code skills/hooks.

## Architectural Patterns

### Pattern 1: Command-Skill-Commit Loop

**What:** Every operation follows: receive trigger -> execute skill/command -> write data to NDJSON/JSON -> commit to git -> optionally push. The git commit is the atomic unit of state change.

**When to use:** Every automated or manual operation that modifies system state.

**Example:**
```
1. Glen types: /triage-inbox
2. email-scanner subagent spawned
3. Reads Gmail via hardened-google-workspace-mcp
4. Categorizes emails, appends to data/feed.jsonl
5. Updates data/emails/starred.json
6. scripts/build-dashboard-data.sh runs (hook or explicit)
7. git add + git commit -m "triage: scanned 12 emails, 3 flagged"
8. git push origin main -> GitHub Pages auto-deploys
```

### Pattern 2: Subagent Isolation for Heavy Operations

**What:** Context-heavy operations (full inbox scan, document analysis) run in subagents to preserve the main conversation's context window.

**When to use:** Any operation that produces verbose intermediate output (email bodies, document contents, API responses).

**Example subagent definition (`.claude/agents/email-scanner.md`):**
```markdown
---
name: email-scanner
description: Scans Gmail inbox, triages by category and priority.
tools: Read, Write, Edit, Bash, mcp__google-workspace__*
model: sonnet
---

You are an email triage agent for Glen, founder of Agend Systems.
Read the inbox via Google Workspace MCP. For each unread email:
1. Categorize: client, team, sales, admin, noise
2. Extract: sender, subject, actionable items, urgency
3. If starred: flag as highest priority
4. Append to data/feed.jsonl (one JSON object per line)
5. Update data/emails/starred.json if stars changed

Only process email metadata + first 500 chars of body for categorization.
Reserve full body for emails that need draft replies.
```

### Pattern 3: Static Dashboard via JSON Data Contract

**What:** The dashboard is static HTML/JS that fetches a single `feed.json` file. Claude rebuilds `feed.json` from NDJSON after state changes. No server, no API, no database.

**Data contract (`docs/feed.json`):**
```json
{
  "lastUpdated": "2026-03-23T10:30:00+10:00",
  "inbox": {
    "total": 42,
    "unread": 7,
    "flagged": 3,
    "byCategory": { "client": 15, "team": 10, "sales": 8, "admin": 5, "other": 4 }
  },
  "starred": [
    { "from": "Sarah", "subject": "Contract renewal Q3", "received": "2026-03-23T09:00:00Z", "category": "client" }
  ],
  "pendingDrafts": 2,
  "pendingTasks": 1,
  "recentActivity": [
    { "time": "10:30", "type": "triage", "summary": "Scanned inbox: 3 new client emails", "level": "info" },
    { "time": "10:15", "type": "draft", "summary": "Drafted reply to Sarah re: contract renewal", "level": "action" }
  ]
}
```

### Pattern 4: Hooks as Guardrails and Automation Glue

**What:** Claude Code hooks enforce policies and automate cross-cutting concerns.

**Example (`.claude/settings.json`):**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "./scripts/validate-data.sh",
            "statusMessage": "Validating data files..."
          }
        ]
      }
    ]
  }
}
```

## Data Flow

### Email Triage Flow (Interactive)

```
Glen types: /triage-inbox
    |
    v
[email-scanner subagent spawned]
    |
    v
hardened-google-workspace-mcp ------- OAuth 2.0 ------- Gmail API
    | (search inbox, read messages)
    | (CANNOT send, by design)
    v
Categorize + Extract (metadata + first 500 chars)
    |
    +-->  data/emails/inbox.jsonl     (append new email records)
    +-->  data/emails/starred.json    (update starred queue)
    +-->  data/feed.jsonl             (append triage entry)
    |
    v
scripts/build-dashboard-data.sh
    | (jq -s '.' data/feed.jsonl | tail -100 > docs/feed.json)
    v
git add + git commit
    |
    v
git push origin main
    |
    v
GitHub Pages auto-deploys --> docs/feed.json updated
```

### Email Triage Flow (Scheduled via GitHub Actions)

```
GitHub Actions cron: '0 9 * * 1-5' (weekdays 9am UTC)
    |
    v
anthropics/claude-code-action@v1
    | (--mcp-config .github/mcp-config.json)
    | (prompt: "Run /triage-inbox")
    v
Claude Code on GitHub runner
    | (configures hardened-google-workspace-mcp from workflow secrets)
    v
[Same triage flow as interactive]
    |
    v
git commit + git push (from runner)
    |
    v
GitHub Pages auto-deploys
```

**IMPORTANT:** GitHub Actions MCP configuration is separate from local. The workflow must configure MCP servers explicitly using secrets and the `--mcp-config` flag. Local `.claude/settings.local.json` is not available on the runner.

### Manual Task Execution Flow

```
Glen types: "review the contract Sarah sent"
    |
    v
Claude Code main agent
    | (recognizes task, delegates)
    v
[task-executor subagent spawned]
    |
    +-->  Google Workspace MCP: find Sarah's email with attachment
    +-->  Google Workspace MCP: pull contract from Drive
    +-->  Analyze contract content (Claude reasoning)
    +-->  Draft summary + response
    |
    v
Write results:
    +-->  data/tasks/completed/      (task record with outcome)
    +-->  data/emails/drafts/        (draft reply .md file)
    +-->  data/feed.jsonl            (task execution entry)
    |
    v
Return summary to Glen in main conversation
    |
    v
git commit + push (via hook or explicit)
```

### Dashboard Refresh Flow

```
Any data/ file modified (via any flow above)
    |
    v
scripts/build-dashboard-data.sh
    | (reads feed.jsonl, starred.json, pending.json)
    | (aggregates into docs/feed.json)
    v
docs/feed.json updated
    |
    v
git commit + push
    |
    v
GitHub Pages serves updated static site
    |
    v
Glen opens phone browser --> sees current status
```

## Durable Scheduling Architecture

### CRITICAL: Desktop Scheduled Tasks Cannot Access MCP Servers

There is an open bug in Claude Code (GitHub issue #36327, with multiple duplicates #35899, #35002, #33773) where Desktop scheduled tasks cannot access connected MCP servers. The MCP tools fail silently during scheduled execution, even when they work fine in interactive sessions. This bug is unresolved as of March 2026.

**Consequence:** You CANNOT use Desktop scheduled tasks for email triage, because triage requires the Gmail MCP server.

### Recommended: Two-Tier Scheduling

**Tier 1: Session-scoped (interactive use)**
- `/loop 15m check for new starred emails` -- quick polling while working
- One-time reminders: "in 30 minutes, check if Sarah replied"
- Dies when session ends. Acceptable for interactive monitoring.
- 3-day auto-expiry on recurring tasks.

**Tier 2: GitHub Actions (durable, unattended)**
```yaml
# .github/workflows/triage.yml
name: Daily Email Triage
on:
  schedule:
    - cron: '0 9 * * 1-5'  # Weekdays at 9am UTC
  workflow_dispatch: {}      # Manual trigger for testing

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Run the triage-inbox workflow:
            1. Scan Gmail inbox for unread emails
            2. Categorize each email
            3. Update starred queue
            4. Append results to data/feed.jsonl
            5. Rebuild docs/feed.json
            6. Commit and push changes
          claude_args: >
            --model claude-sonnet-4-6
            --max-turns 15
            --mcp-config .github/mcp-config.json
```

- Fully unattended, runs even when laptop is off
- MCP servers configured explicitly in workflow (not inherited from local)
- Commits results back to repo, triggering GitHub Pages deploy
- Manual dispatch for testing

**Why not Desktop scheduled tasks:** Bug #36327. MCP tools are unavailable during scheduled execution. Until this is fixed, GitHub Actions is the only reliable option for MCP-dependent automation.

## Anti-Patterns

### Anti-Pattern 1: Monolithic JSON Files

**What people do:** Store all emails, tasks, and activity in single large JSON arrays.
**Why it breaks:** Git diffs become unreadable. Read-modify-write cycles create race conditions. Claude wastes context parsing irrelevant data.
**Do this instead:** NDJSON for append-only data. Separate files by domain and time period. Keep current files under 100KB.

### Anti-Pattern 2: Running Everything in Main Conversation

**What people do:** Let main Claude Code conversation handle scanning, execution, and dashboard building directly.
**Why it breaks:** Context window fills with email bodies and API responses. After 2-3 triage cycles, compaction needed.
**Do this instead:** Delegate heavy operations to subagents. Main conversation stays clean for Glen's direct interactions.

### Anti-Pattern 3: Relying on /loop for Critical Operations

**What people do:** Use `/loop 30m triage inbox` and assume it will keep running.
**Why it breaks:** Session-scoped. Dies on terminal close. No catch-up for missed fires. 3-day auto-expiry.
**Do this instead:** GitHub Actions for anything that must run unattended. /loop only for interactive ad-hoc monitoring.

### Anti-Pattern 4: Storing Secrets in Git

**What people do:** Put OAuth tokens or API keys in `.claude/settings.json` or data files.
**Why it breaks:** Credentials pushed to GitHub are a security risk.
**Do this instead:** `.claude/settings.local.json` (gitignored) for local secrets. GitHub Actions secrets for CI. MCP servers handle their own OAuth token storage.

### Anti-Pattern 5: Using Unmodified Google Workspace MCP

**What people do:** Use taylorwilsdon/google_workspace_mcp which includes email sending, file sharing, filter creation.
**Why it breaks:** Prompt injection risk. An attacker embeds instructions in an email body; Claude reads the email and follows the injected instructions to forward sensitive data.
**Do this instead:** Use c0webster/hardened-google-workspace-mcp which strips all exfiltration-capable operations.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **1 user, 50 emails/day** (v1) | Current architecture. Single Claude Code session, local git, NDJSON flat files. No scaling needed. |
| **1 user, 200+ emails/day** | NDJSON files grow. Archive by month. Add pagination to dashboard. Two-tier model (Haiku for initial categorization, Sonnet for drafts). |
| **Multiple workstreams** | Separate NDJSON files per workstream/client. Claude skills route to correct files based on context. |
| **Real-time dashboard** | Add `setInterval(fetch('feed.json'), 60000)` to dashboard JS for auto-refresh. Or move to a lightweight server if needed. |

## Build Order (Dependencies)

```
Phase 1: Foundation
+-- Local git repo structure (data/ directories, NDJSON schemas)
+-- CLAUDE.md with project instructions
+-- Google OAuth setup (PRODUCTION mode, not testing)
+-- hardened-google-workspace-mcp installed and configured
+-- github/github-mcp-server configured (remote HTTP)
+-- Basic validation scripts

Phase 2: Email Triage (Interactive)
+-- Depends on: Phase 1 (MCP servers + data structure)
+-- email-scanner subagent
+-- /triage-inbox command
+-- /scan-starred command
+-- Manual trigger, validate accuracy

Phase 3: Draft Generation + Task Execution
+-- Depends on: Phase 2 (emails exist to act on)
+-- /draft-reply command
+-- task-executor subagent
+-- Draft storage in data/emails/drafts/

Phase 4: Dashboard
+-- Depends on: Phase 1 (feed.json contract)
+-- Static HTML/JS dashboard in docs/
+-- build-dashboard-data.sh script
+-- GitHub Pages configuration
+-- CAN be built in parallel with Phase 2-3 using mock data

Phase 5: Scheduling & Automation
+-- Depends on: Phase 2-3 (operations exist to schedule)
+-- GitHub Actions workflow (.github/workflows/triage.yml)
+-- MCP configuration for CI environment
+-- Auto-commit and auto-push pipeline

Phase 6: Mobile & Channels (optional v1.x)
+-- Depends on: Phase 4 (dashboard for read), Phase 5 (session for channels)
+-- Telegram/Discord channel setup
+-- rclone Google Drive sync
```

## Sources

- [Claude Code Scheduled Tasks (official docs)](https://code.claude.com/docs/en/scheduled-tasks) -- /loop, cron tools, session scope, 3-day expiry -- HIGH confidence
- [Claude Code MCP Configuration (official docs)](https://code.claude.com/docs/en/mcp) -- .mcp.json format, scope levels, transport types -- HIGH confidence
- [Claude Code GitHub Actions (official docs)](https://code.claude.com/docs/en/github-actions) -- claude-code-action@v1, scheduled workflows -- HIGH confidence
- [Claude Code Channels (official docs)](https://code.claude.com/docs/en/channels) -- Telegram/Discord, research preview -- HIGH confidence
- [MCP Scheduled Task Bug #36327](https://github.com/anthropics/claude-code/issues/36327) -- MCP tools unavailable in Desktop scheduled tasks -- HIGH confidence
- [hardened-google-workspace-mcp](https://github.com/c0webster/hardened-google-workspace-mcp) -- security removals, installation -- HIGH confidence
- [github/github-mcp-server](https://github.com/github/github-mcp-server) -- remote HTTP, authentication -- HIGH confidence
- [NDJSON specification](https://ndjson.com/definition/) -- format advantages for append-only logging -- HIGH confidence

---
*Architecture research for: Agend Ops -- AI-powered personal operations hub*
*Researched: 2026-03-23*
