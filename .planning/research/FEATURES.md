# Feature Landscape

**Domain:** AI-powered personal operations hub (single-user, founder-focused)
**Researched:** 2026-03-23
**Confidence:** HIGH

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Gmail inbox scanning and categorization | Core value proposition. Every competitor (Lindy, Superhuman, SaneBox, OpenClaw) does this. Without it, there is no cognitive load relief. | MEDIUM | Requires hardened-google-workspace-mcp + Google OAuth 2.0 (PRODUCTION mode). Categories: urgent/action-required, needs-response, informational, low-priority. |
| Email priority classification | Users expect AI to distinguish "client contract needs signature" from "newsletter update." | MEDIUM | Combine sender importance (known client vs unknown), content intent analysis. Start with simple heuristics (starred = needs action, known senders = higher priority), layer Claude classification on top. |
| Draft reply generation | Lindy's core feature. Superhuman's Ghostwriter. Missing this = "why not just use Gmail filters?" | MEDIUM | Claude generates draft based on email context. hardened-google-workspace-mcp can create Gmail drafts (but not send). Store drafts locally as markdown for review. |
| Human-in-the-loop approval before sending | Industry standard. No serious AI email tool sends without approval. | LOW | Present draft, user approves/edits/rejects. Non-negotiable for v1. The hardened MCP fork enforces this -- it literally cannot send emails. |
| Activity feed / audit trail | Every AI agent platform logs what the AI did. Without this, the system is a black box. | LOW | NDJSON append-only file (data/feed.jsonl). Each entry: timestamp, trigger, action, inputs, outputs, outcome. |
| Mobile-friendly status view | Founder checks status from phone constantly. Some glanceable interface is expected. | MEDIUM | GitHub Pages dashboard. Static HTML/JS fetches feed.json. Responsive, mobile-first. Key info: unread count, pending actions, recent activity. |
| Scheduled/recurring execution | An assistant that only works when manually invoked is not an assistant. | MEDIUM | GitHub Actions with claude-code-action@v1 for durable scheduling. NOT Desktop scheduled tasks (bug #36327: MCP unavailable). /loop for interactive ad-hoc. |
| Manual task kickoff | "Review the contract Sarah sent" -- conversational triggers. | LOW | Claude Code is the interface. User types natural language, Claude executes. Custom commands formalize common patterns. |

## Differentiators

Features that make Agend Ops distinct from Lindy/OpenClaw/Superhuman.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Local git repo as source of truth | Full data ownership. Unlike Lindy (SaaS) or Superhuman (email-only), all data lives in a directory Glen controls. Git history = free versioning + audit trail. | LOW | Architectural decision. NDJSON/JSON files committed to git. Git log IS the audit trail. |
| Starred-email-as-intent queue | Maps to Glen's existing Gmail workflow. No other tool treats stars as a "needs my attention" queue driving AI prioritization. | LOW | Query Gmail via MCP for STARRED label. Surface starred emails first in dashboard and feed. |
| Actionable item detection and task suggestion | Goes beyond triage into task extraction. "This email contains a contract needing review by Friday." | HIGH | Claude-powered intent extraction: contracts, invoices, meeting requests, deadlines. Suggest concrete next steps. |
| Task execution with document analysis | Actually execute tasks: "Pull the contract, summarize key terms, flag unusual clauses, draft response." | HIGH | Requires Google Drive access via MCP, Claude's long-context for analysis. Start simple, graduate to multi-step. |
| Context accumulation over time | System builds persistent knowledge in git repo. Claude references past decisions, client history, prior triage. | MEDIUM | Store triage decisions and client summaries in structured files. Load recent context on demand. Compounds in value. |
| Telegram/Discord command channel | Send Claude commands from phone. Two-way bridge for approvals. | MEDIUM | Channels feature (research preview, v2.1.80+). Complements read-only dashboard with write capability from mobile. |
| Hybrid git + Drive sync | Git for version control, Drive for cross-device accessibility. | LOW | rclone one-way push (repo -> Drive). Git is always source of truth. |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Autonomous email sending | Prompt injection risk: attacker embeds instructions in email body causing data exfiltration. The hardened-google-workspace-mcp removes send capability entirely. Even without the security concern, trust destruction if AI sends wrong email to client. | Claude creates drafts. Glen reviews and sends manually from Gmail. Graduate to auto-send for low-risk categories only after weeks of proven accuracy. |
| Real-time push notifications | Adds infrastructure complexity (Pub/Sub, webhook server, push service). Defeats the purpose of reducing cognitive load -- interrupts deep work. | Scheduled polling + glanceable dashboard. Glen checks when he wants to. |
| Full calendar management | Separate complex domain (timezone handling, attendee preferences, conflict resolution). Scope creep risk is enormous. | Detect meeting requests in emails, surface with suggested times. Actual calendar management deferred. |
| Native mobile app | Months of development. App store process. Massive over-engineering for single-user read-only status. | GitHub Pages responsive dashboard. Telegram channel for commands. |
| Multi-user / team features | Transforms personal tool into team platform. Auth, permissions, data isolation -- each is a project. | Single-user. Share dashboard URL (read-only) with managers if needed. |
| Integration with every tool | Each integration is a maintenance surface. OAuth flows, API changes, rate limits. OpenClaw has 50+ and a full team. | Gmail + Drive + GitHub only for v1. Add integrations only when specific repeated need demonstrated. |
| Daily digest email | Building email sending infrastructure for a tool meant to reduce email. | Activity feed in dashboard serves same purpose. |
| Conversational memory across all sessions | Unbounded context growth. Slow and expensive. Privacy risk. | Structured summaries in git. Load recent (7 days) plus client-specific files on demand. Bounded, searchable, deletable. |

## Feature Dependencies

```
[Google OAuth + hardened-google-workspace-mcp Setup]
    |
    +----> [Inbox Scanning / Polling]
    |          |
    |          +----> [Email Categorization / Priority Classification]
    |          |          |
    |          |          +----> [Starred Email Priority Queue]
    |          |          |
    |          |          +----> [Actionable Item Detection]
    |          |                     |
    |          |                     +----> [Task Suggestion]
    |          |                                |
    |          |                                +----> [Task Execution]
    |          |
    |          +----> [Draft Reply Generation]
    |                     |
    |                     +----> [Human Approval (inherent -- MCP can't send)]
    |
    +----> [Activity Feed Logging (NDJSON)]
               |
               +----> [Dashboard Data Compilation (jq)]
                          |
                          +----> [GitHub Pages Dashboard]

[NDJSON Schema Definition]
    |
    +----> [Activity Feed Logging]
    |
    +----> [Dashboard Data Contract]

[GitHub Actions + claude-code-action@v1]
    |
    +----> [Scheduled Inbox Scanning (durable)]
    |
    +----> [Auto-commit + Dashboard Deploy]

[rclone Setup]
    |
    +----> [Google Drive Sync (optional)]

[Claude Code Channels v2.1.80+]
    |
    +----> [Telegram Command Channel (optional)]
```

### Key Dependency Notes

- **Everything requires Google OAuth in PRODUCTION mode**: Testing mode tokens expire after 7 days. This is the Phase 1, step 1 blocker.
- **NDJSON schema must be defined before any data is written**: The dashboard contract and all logging depend on a stable schema.
- **Dashboard can be built with mock data**: Does not need live email triage to exist. Can develop in parallel.
- **Scheduled automation comes AFTER interactive flows work**: Debug interactively, then automate.
- **Channels are optional and experimental**: Research preview feature. Do not block v1 on this.

## MVP Recommendation

### Launch With (v1 -- validates core hypothesis)

- [ ] Google OAuth in PRODUCTION mode + hardened-google-workspace-mcp configured
- [ ] NDJSON activity feed schema defined and working
- [ ] Inbox scanning via Claude Code command (/triage-inbox)
- [ ] Email categorization into 4 buckets (urgent, needs-response, informational, low-priority)
- [ ] Starred email detection as highest-priority queue
- [ ] Draft reply generation (saved as markdown, created as Gmail draft)
- [ ] Human approval (inherent -- hardened MCP cannot send)
- [ ] Activity feed logged to data/feed.jsonl
- [ ] Manual task kickoff via Claude Code commands
- [ ] Static GitHub Pages dashboard (unread count, starred queue, recent activity)

### Add After Validation (v1.x)

- [ ] GitHub Actions scheduled triage (daily weekday, unattended)
- [ ] Actionable item detection (contracts, invoices, meeting requests)
- [ ] Task suggestion based on detected items
- [ ] Google Drive document retrieval for task execution
- [ ] Context accumulation (client interaction summaries)
- [ ] Dashboard filtering/search
- [ ] rclone Drive sync

### Future (v2+)

- [ ] Telegram/Discord command channel (depends on Channels GA)
- [ ] Autonomous sending for low-risk categories (after trust established)
- [ ] Calendar awareness
- [ ] Invoice tracking (deferred per PROJECT.md)
- [ ] Multi-step task execution chains

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Gmail OAuth + MCP setup | HIGH | MEDIUM | P0 |
| NDJSON schema definition | HIGH | LOW | P0 |
| Inbox scanning (interactive) | HIGH | MEDIUM | P1 |
| Email categorization (4 buckets) | HIGH | MEDIUM | P1 |
| Starred email priority queue | HIGH | LOW | P1 |
| Draft reply generation | HIGH | MEDIUM | P1 |
| Activity feed (NDJSON) | HIGH | LOW | P1 |
| Manual task kickoff | MEDIUM | LOW | P1 |
| GitHub Pages dashboard | MEDIUM | MEDIUM | P1 |
| Scheduled triage (GitHub Actions) | HIGH | HIGH | P2 |
| Actionable item detection | HIGH | HIGH | P2 |
| Google Drive integration | MEDIUM | MEDIUM | P2 |
| Context accumulation | MEDIUM | MEDIUM | P2 |
| Telegram channel | MEDIUM | MEDIUM | P3 |
| Autonomous low-risk sending | MEDIUM | LOW | P3 |
| Calendar awareness | MEDIUM | HIGH | P3 |

## Sources

- [hardened-google-workspace-mcp](https://github.com/c0webster/hardened-google-workspace-mcp) -- security model, available tools, what's removed
- [Claude Code Channels docs](https://code.claude.com/docs/en/channels) -- Telegram/Discord capabilities, research preview
- [Claude Code Scheduled Tasks docs](https://code.claude.com/docs/en/scheduled-tasks) -- /loop limitations, session scope
- [MCP Scheduled Task Bug #36327](https://github.com/anthropics/claude-code/issues/36327) -- Desktop tasks can't access MCP
- [Claude Code GitHub Actions docs](https://code.claude.com/docs/en/github-actions) -- durable scheduling alternative
- PROJECT.md -- requirements, out-of-scope items, constraints

---
*Feature research for: AI-powered personal operations hub*
*Researched: 2026-03-23*
