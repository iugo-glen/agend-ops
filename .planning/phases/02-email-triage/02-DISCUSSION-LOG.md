# Phase 2: Email Triage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 2-Email Triage
**Areas discussed:** Categorization, Draft Replies, Preprocessing, Action Detection

---

## Categorization

### Classification approach

| Option | Description | Selected |
|--------|-------------|----------|
| Pure AI | Claude reads each email and classifies based on content, sender, context | |
| Rules + AI | Known client domains = higher priority, newsletters = low-priority, AI classifies rest | ✓ |
| You decide | Claude designs the best classification approach | |

**User's choice:** Rules + AI

### Urgency criteria

| Option | Description | Selected |
|--------|-------------|----------|
| Client-facing | Anything from a client, especially about deadlines, issues, contracts | ✓ |
| Money or legal | Invoices, contracts, legal matters, financial impact | |
| Time-sensitive | Anything with deadline within 48 hours | |
| Let me explain | Custom criteria | |

**User's choice:** Client-facing

### Client domain list

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, I can provide | Have a list or can create one | |
| Infer from inbox | Let Claude learn from patterns | |
| Both | Seed list + Claude suggests additions | ✓ |

**User's choice:** Both — seed list with discovery

---

## Draft Replies

### Tone

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror mine | Study sent emails and match writing style | ✓ |
| Professional | Standard business tone | |
| You decide | Claude picks appropriate tone per context | |

**User's choice:** Mirror mine

### Draft destination

| Option | Description | Selected |
|--------|-------------|----------|
| Both (Recommended) | Local markdown + Gmail draft | |
| Local only | Markdown files in data/drafts/ | |
| Gmail draft only | Create draft directly in Gmail via MCP | ✓ |

**User's choice:** Gmail draft only

### Draft scope

| Option | Description | Selected |
|--------|-------------|----------|
| All needs-response | Draft for everything in needs-response bucket | |
| Urgent + client only | Only draft for urgent and known client emails | ✓ |
| You decide | Claude determines based on complexity/importance | |

**User's choice:** Urgent + client only

---

## Preprocessing

### Batch size

| Option | Description | Selected |
|--------|-------------|----------|
| All unread | Every unread email | |
| Last 24 hours | Only emails from last 24 hours | ✓ |
| Capped at 50 | Up to 50 most recent unread | |
| You decide | Claude picks sensible default | |

**User's choice:** Last 24 hours

### Stripping level

| Option | Description | Selected |
|--------|-------------|----------|
| Aggressive | Strip HTML, signatures, reply chains, footers — just latest message | |
| Moderate | Strip HTML and signatures, keep one reply level for context | ✓ |
| You decide | Claude picks for cost vs accuracy balance | |

**User's choice:** Moderate

---

## Action Detection

### Action types

| Option | Description | Selected |
|--------|-------------|----------|
| Contracts/legal | Documents requiring review or signature | ✓ |
| Invoice requests | Clients or vendors asking for/sending invoices | ✓ |
| Meeting requests | Someone wants to schedule a meeting or call | ✓ |
| Deadlines | Any email mentioning a specific date | ✓ |

**User's choice:** All four types

### Client matching

| Option | Description | Selected |
|--------|-------------|----------|
| Yes | Match to client names/domains from seed list, tag results | ✓ |
| Not in v1 | Just classify, don't match to specific client | |

**User's choice:** Yes — tag triage results with client name

---

## Claude's Discretion

- Classification prompt design
- Tone mirroring methodology
- Preprocessing implementation
- Triage output presentation
- Activity feed entry format
- Client domain suggestion mechanism

## Deferred Ideas

None — discussion stayed within phase scope
