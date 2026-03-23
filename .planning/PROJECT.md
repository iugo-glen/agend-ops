# Agend Ops

## What This Is

A personal operations hub for the founder of Agend Systems — a small tech company (~30 clients, 2 managers) that builds and deploys association management system (AMS) modules under the "Agend" brand. The system uses Claude as an AI executive assistant that proactively manages email triage, executes delegated tasks, and logs everything to an activity feed. Data lives in a local git repo (source of truth) with a GitHub Pages dashboard for mobile-friendly glanceable access.

## Core Value

Offload cognitive load — Claude handles email triage and task execution so Glen can focus on high-value decisions instead of drowning in operational noise.

## Requirements

### Validated

- Google OAuth 2.0 configured in PRODUCTION mode (Internal user type) — Phase 1
- Hardened Google Workspace MCP server installed and verified (no send/share/filter) — Phase 1
- NDJSON data schemas defined (feed, triage, task records) — Phase 1
- CLAUDE.md with custom commands (/status, /task, /feed, /triage-inbox) — Phase 1
- Git repo directory structure established (data/, docs/, scripts/, schemas/) — Phase 1
- Gmail inbox scanning and categorization into 4 priority buckets via MCP — Phase 2
- Starred emails surfaced as highest-priority "needs my action" queue — Phase 2
- Draft reply generation for urgent/client emails (Gmail drafts only, mirrors Glen's tone) — Phase 2
- Actionable item detection (contracts, invoices, meetings, deadlines) with client tagging — Phase 2
- Email preprocessing pipeline (HTML/signature stripping, token cost management) — Phase 2
- Human-in-the-loop enforced (hardened MCP cannot send) — Phase 2
- Manual task kickoff via /task command with natural language parsing — Phase 3
- Proactive task suggestions auto-queued from email triage action items — Phase 3
- Document retrieval from Gmail/Drive with two-step fallback — Phase 3
- Document analysis with executive summary output (contracts, meetings, docs, comms) — Phase 3
- Task output saved to repo (data/tasks/{id}/) and displayed inline — Phase 3
- Task lifecycle: pending → in-progress → completed with activity feed logging — Phase 3
- NDJSON compiled to JSON for dashboard consumption (feed, tasks, triage) — Phase 4
- GitHub Pages dashboard auto-deployed from docs/ — Phase 4
- Mobile-first responsive dashboard (tabs on phone, Kanban on desktop) — Phase 4
- Notion-style aesthetics with system auto dark/light mode — Phase 4

### Active

- [ ] Scheduled email triage via Claude Desktop recurring tasks (validate MCP access)
- [ ] Daily task list / to-do management (add, complete, prioritize tasks beyond email)
- [ ] Invoice tracking (which clients, amounts, due dates, billing status)
- [ ] Mobile commands via Telegram channel (send tasks, approve drafts from phone)

### Out of Scope

- POC tracker — deferred to v3, lower urgency
- Daily digest email summaries — activity feed + dashboard covers this
- Push notifications — using in-app feed and Telegram instead
- Building a native mobile app — GitHub Pages dashboard + Telegram sufficient
- Google Drive sync — deferred, GitHub Pages provides mobile access
- Full calendar management — detect meeting requests in emails instead

## Current Milestone: v2.0 Autonomous Operations

**Goal:** Transform Agend Ops from a manual tool into an autonomous assistant — scheduled triage, daily task management, invoice tracking, and mobile commands.

**Target features:**
- Scheduled email triage via Claude Desktop recurring tasks
- Daily task list / to-do management
- Invoice tracking
- Mobile commands via Telegram

## Context

- Glen runs multiple concurrent workstreams: business ops, marketing (active rebrand), sales, invoicing, AI tool evaluation, POC creation, team coordination
- Currently uses Gmail starred emails as a "needs my action" queue
- Wants to leverage Claude's emerging capabilities: Dispatch, Schedule/Loop, remote MCP, Gmail/Drive/GitHub access
- Inspired by OpenClaw concept but wants full ownership — data in a directory he controls, not a third-party SaaS
- Access patterns: Claude Code from desktop, GitHub Pages dashboard from mobile phone
- Two managers handle day-to-day team operations, but Glen still needs to stay across everything at a strategic level

## Constraints

- **Ecosystem**: Must work within Claude Code ecosystem (MCP servers, Claude Dispatch/Schedule)
- **Data ownership**: Local git repo as source of truth — Glen must own and control all data
- **Auth**: Gmail OAuth required for inbox access, Google Drive API for document sync, GitHub for dashboard deployment
- **Mobile**: Dashboard must be phone-friendly (responsive, glanceable)
- **Privacy**: Email content and business data must not leak to third-party services beyond Claude's own infrastructure
- **Incremental**: Must be buildable incrementally — email triage first, then task execution, then dashboard

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid storage (local + Drive sync) | Local for control and git history, Drive for mobile/cross-device access | — Pending |
| GitHub Pages for mobile dashboard | Free, auto-deployable from repo, no infrastructure to manage | — Pending |
| In-app activity feed (not push/digest) | Lower complexity for v1, Glen can check feed on his own schedule | — Pending |
| Both proactive + manual task triggers | Proactive catches things Glen might miss, manual gives him control | — Pending |
| v1 = email triage + kickoff tasks only | Highest cognitive load relief per effort invested | — Pending |
| Claude Code as primary interface | Glen already lives there, natural fit for command-style interaction | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-23 after v2.0 milestone start*
