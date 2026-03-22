# Agend Ops

## What This Is

A personal operations hub for the founder of Agend Systems — a small tech company (~30 clients, 2 managers) that builds and deploys association management system (AMS) modules under the "Agend" brand. The system uses Claude as an AI executive assistant that proactively manages email triage, executes delegated tasks, and logs everything to an activity feed. Data lives in a local git repo (source of truth) with a GitHub Pages dashboard for mobile-friendly glanceable access.

## Core Value

Offload cognitive load — Claude handles email triage and task execution so Glen can focus on high-value decisions instead of drowning in operational noise.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Claude scans Gmail inbox on a schedule, categorizes emails, and surfaces important items
- [ ] Claude drafts replies for emails that need responses
- [ ] Claude detects actionable items in emails (contracts, invoices, meeting requests) and suggests tasks
- [ ] Claude executes suggested tasks when approved (pull document, analyze, draft response)
- [ ] Manual task kickoff via Claude Code (e.g., "review the contract Sarah sent", "prep for Thursday meeting")
- [ ] Activity feed logging everything Claude did, why, and the outcome
- [ ] GitHub Pages dashboard — mobile-friendly, glanceable status view
- [ ] Starred emails treated as "I need to do something first" queue
- [ ] Hybrid data storage — local git repo as source of truth, synced to Google Drive for access

### Out of Scope

- Daily task list / to-do management — deferred to v2, want email + tasks working first
- POC tracker — deferred to v2, lower urgency than email triage
- Invoice tracking — deferred to v2, important but not the biggest cognitive drain right now
- Daily digest email summaries — deferred to v2, activity feed covers this for now
- Push notifications — using in-app feed instead for v1
- Building a native mobile app — GitHub Pages dashboard is sufficient for v1

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
*Last updated: 2026-03-23 after initialization*
