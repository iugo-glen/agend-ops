# Phase 2: Email Triage - Research

**Researched:** 2026-03-23
**Domain:** Gmail MCP integration, email classification, draft generation, NDJSON data pipeline
**Confidence:** HIGH

## Summary

Phase 2 implements the core email triage engine: Glen runs `/triage-inbox`, Claude scans the last 24 hours of Gmail via the hardened-workspace MCP server, classifies emails into four priority buckets using a rules + AI hybrid approach, detects starred emails as highest-priority, identifies actionable items (contracts, invoices, meetings, deadlines), generates Gmail drafts for urgent/client emails that mirror Glen's writing style, and logs everything to the activity feed.

The hardened-workspace MCP server is already installed and connected (verified). It exposes `search_gmail_messages`, `get_gmail_message_content`, `get_gmail_messages_content_batch`, and `draft_gmail_message` as the key Gmail tools. The server blocks sending, filter creation, and deletion -- enforcing human-in-the-loop by design. The triage command stub exists at `.claude/commands/triage-inbox.md` with correct `allowed-tools` frontmatter. Data directories (`data/triage/`, `data/config/`) exist with `.gitkeep` files. Schemas for triage records and feed entries are defined and validated by `scripts/validate-data.sh`.

**Primary recommendation:** Build the triage engine as a subagent (`email-scanner`) using Sonnet model with restricted MCP tool access, invoked by the `/triage-inbox` command. Use a two-pass approach: first pass fetches metadata + snippets for all emails (cheap), second pass reads full body only for emails needing classification or draft replies (controlled cost). Store the client domain seed list in `data/config/clients.jsonl` as decided.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Rules + AI hybrid classification -- known client domains get priority boost via rules, AI classifies the rest
- **D-02:** Client-facing emails are the primary urgency signal -- anything from a client (especially about deadlines, issues, contracts) is urgent
- **D-03:** Seed list of ~30 client domains stored in a config file (data/config/clients.jsonl or similar), with Claude suggesting new domains as it discovers frequent senders
- **D-04:** Four buckets: urgent, needs-response, informational, low-priority
- **D-05:** Starred emails surface as highest-priority "needs my action" queue (carried from Phase 1)
- **D-06:** Claude mirrors Glen's writing style -- study sent emails to match tone (professional but approachable)
- **D-07:** Create Gmail drafts only (via hardened MCP) -- no local markdown copies
- **D-08:** Draft replies only for urgent emails and known client emails -- not all needs-response items
- **D-09:** Human-in-the-loop enforced by hardened MCP (cannot send, only create drafts)
- **D-10:** Batch scope: last 24 hours of emails per triage run
- **D-11:** Moderate stripping -- remove HTML and signatures, keep one level of reply chain for context
- **D-12:** Token cost management through preprocessing, not through limiting email count
- **D-13:** Detect four action types: contracts/legal documents, invoice requests, meeting requests, deadline mentions
- **D-14:** Match emails to client names/domains from the seed list -- tag triage results with client name
- **D-15:** Detected actions presented as suggested next steps (e.g., "Contract from Acme Corp -- review by Friday")

### Claude's Discretion
- Exact classification prompt/system message design
- How to study Glen's sent emails for tone mirroring (sample size, frequency)
- Preprocessing implementation details (HTML parser choice, signature detection approach)
- How to present triage results in the /triage-inbox command output
- Activity feed entry format for triage events
- Client domain suggestion mechanism (how often, where to surface suggestions)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EMAIL-01 | Claude can scan Gmail inbox and retrieve unread and recent emails via MCP | `search_gmail_messages` with query `newer_than:1d` + `get_gmail_messages_content_batch` for up to 25 at a time. Hardened MCP verified connected. |
| EMAIL-02 | Emails categorized into 4 buckets: urgent, needs-response, informational, low-priority | Rules engine matches client domains first (D-01), then AI classifies remainder. Priority enum already defined in triage-record.json schema. |
| EMAIL-03 | Starred emails surface as highest-priority "needs my action" queue | Gmail query `is:starred newer_than:1d` fetches starred subset. Starred field exists in triage-record.json schema. |
| EMAIL-04 | Email priority classification based on sender importance and content intent | Client domain seed list (data/config/clients.jsonl) provides sender importance. AI classification prompt handles content intent analysis. |
| EMAIL-05 | Claude generates draft replies saved as Gmail drafts | `draft_gmail_message` tool accepts to, subject, body, in_reply_to params. D-07 says Gmail drafts only, no local markdown. |
| EMAIL-06 | Human-in-the-loop approval required before any response is sent | Enforced by hardened MCP -- `send_gmail_message` is completely removed from the fork. Claude physically cannot send. |
| EMAIL-07 | Actionable items detected -- contracts, invoices, meeting requests, deadlines -- with suggested next steps | AI classification prompt detects four action types (D-13). action_items array and suggested_action enum already in triage-record.json. |
| EMAIL-08 | Email preprocessing pipeline strips HTML, signatures, and reply chains | Claude handles preprocessing in the subagent: strip HTML tags, detect `-- ` signature delimiter, keep only first reply in chain. No external library needed. |
</phase_requirements>

## Standard Stack

### Core (Phase 2 Specific)

| Technology | Version | Purpose | Why Standard |
|------------|---------|---------|--------------|
| hardened-workspace MCP | latest (installed) | Gmail read, draft creation, label queries | Already registered at user scope, verified connected. Security-hardened fork prevents send/share/filter. |
| Claude Code subagents | Built-in | email-scanner subagent for triage isolation | Keeps email body content out of main conversation context. Subagent returns structured summary only. |
| NDJSON (data/triage/) | N/A | Triage result storage | One JSONL file per triage run (e.g., `2026-03-23T0900.jsonl`). Schema defined in schemas/triage-record.json. |
| NDJSON (data/feed.jsonl) | N/A | Activity feed logging | Append triage summary entry. Schema defined in schemas/feed-entry.json. |
| jq | 1.7.1 (installed) | JSON processing in validation and build scripts | Already installed. Used by validate-data.sh and build-dashboard-data.sh. |

### Supporting

| Technology | Purpose | When to Use |
|------------|---------|-------------|
| Gmail search operators | Query syntax for inbox scanning | `newer_than:1d`, `is:starred`, `is:unread`, `in:sent` (for tone study) |
| data/config/clients.jsonl | Client domain seed list | Rules engine matches sender domains before AI classification |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Subagent for triage | Main conversation | Main context fills with email bodies after 2-3 runs. Subagent isolates this. Use subagent. |
| Claude for HTML stripping | External library (html2text, w3m) | Adds dependency. Claude can strip HTML inline during processing. Claude is simpler for moderate stripping. |
| Single-pass (read all bodies) | Two-pass (metadata first, bodies second) | Single pass burns tokens on low-priority emails. Two-pass reads full body only when needed. Use two-pass. |
| Haiku for all classification | Sonnet for all | Haiku is cheaper but less accurate for nuanced classification. Start with Sonnet, optimize to Haiku later if cost is a concern. |

## Architecture Patterns

### Recommended Triage Flow

```
/triage-inbox command triggered
    |
    v
email-scanner subagent spawned (Sonnet, restricted tools)
    |
    v
PASS 1: Metadata scan
    |-- search_gmail_messages(query="newer_than:1d")
    |-- search_gmail_messages(query="is:starred newer_than:1d")
    |-- get_gmail_messages_content_batch(message_ids=[...])  (batches of 25)
    |-- For each email: extract sender domain, check against clients.jsonl
    |-- Rules engine: client domain match? -> boost priority
    |-- Result: list of emails with metadata + priority hints
    |
    v
PASS 2: Content analysis (selective)
    |-- For urgent/client/starred emails only: read full body
    |-- Preprocess: strip HTML, remove signatures, keep one reply level
    |-- AI classification: detect action items, refine priority
    |-- For urgent + known client: generate draft reply
    |
    v
OUTPUT:
    |-- Write triage JSONL to data/triage/{timestamp}.jsonl
    |-- Append feed entry to data/feed.jsonl
    |-- Create Gmail drafts via draft_gmail_message (urgent + client only)
    |-- Return summary to main conversation
    |
    v
Main conversation displays triage briefing
```

### Pattern 1: Client Domain Rules Engine

**What:** A JSONL config file at `data/config/clients.jsonl` with one record per client. The triage engine checks sender email domain against this list before AI classification.

**When to use:** Every triage run. This is the first classification step.

**Schema for clients.jsonl:**
```json
{"domain": "acmecorp.com", "name": "Acme Corp", "priority_boost": true}
{"domain": "widgetsinc.com.au", "name": "Widgets Inc", "priority_boost": true}
```

**Logic:**
1. Extract sender domain from email `from` field
2. Look up domain in clients.jsonl
3. If match: set category="client", boost priority to at least "needs-response"
4. If starred AND client: set priority="urgent"
5. If no match: proceed to AI classification

### Pattern 2: Subagent Definition for email-scanner

**What:** A subagent in `.claude/agents/email-scanner.md` that handles the entire triage workflow in isolated context.

**Configuration:**
```yaml
---
name: email-scanner
description: Scans Gmail inbox, triages by category and priority, generates draft replies for urgent/client emails
tools: Read, Write, Edit, Bash(jq *), Bash(date *), mcp__hardened-workspace__search_gmail_messages, mcp__hardened-workspace__get_gmail_message_content, mcp__hardened-workspace__get_gmail_messages_content_batch, mcp__hardened-workspace__draft_gmail_message, mcp__hardened-workspace__list_gmail_labels
model: sonnet
---
```

**Key design choices:**
- Restrict MCP tools to only the Gmail tools needed (no Drive, Calendar, etc.)
- Use Sonnet model for accurate classification (not Haiku)
- Include Read/Write/Edit for data file access
- Include Bash(jq) for client list lookups and data validation

### Pattern 3: Tone Mirroring from Sent Emails

**What:** Before first triage run (or periodically), sample Glen's recent sent emails to learn writing style.

**Approach:**
1. Query `in:sent newer_than:30d` to get recent sent messages
2. Read 10-15 sent email bodies
3. Extract patterns: greeting style, sign-off, sentence length, formality level, common phrases
4. Store style notes in the subagent's system prompt or a reference file
5. Use extracted style when generating draft replies

**Frequency:** Once at setup, refresh monthly or on demand. Style rarely changes.

**Implementation:** This can be a one-time step in the triage command or a separate `/study-tone` utility command.

### Pattern 4: Preprocessing Pipeline

**What:** Strip email bodies to reduce token cost before AI classification.

**Steps:**
1. **HTML to text:** Remove all HTML tags. Claude can do this inline -- no external tool needed for moderate stripping (D-11).
2. **Signature removal:** Detect common signature delimiters: `-- ` (standard), `---`, `Sent from my iPhone`, `Get Outlook for`, `This email and any attachments`. Truncate at first match.
3. **Reply chain trimming:** Keep only the latest message plus one level of quoted reply. Detect reply markers: `On [date] [name] wrote:`, `From:`, `>` prefix lines. Keep first block of `>` lines, discard subsequent.
4. **Length cap:** If body still exceeds ~2000 chars after stripping, truncate with `[...truncated]` marker.

**Why no external library:** The email preprocessing here is "moderate" per D-11. We strip HTML (regex is sufficient for email HTML which is typically simple), detect standard signature patterns, and trim reply chains. This does not require a full HTML parser. Claude handles this inline during the subagent's processing.

### Pattern 5: Triage Output Presentation

**What:** The triage results displayed back to Glen should feel like a briefing, not a data dump.

**Format recommendation:**
```
## Inbox Triage - March 23, 2026 (9:00 AM)

### Starred (Needs Your Action)
- [Sarah @ Acme Corp] Contract renewal Q3 -- review requested by Friday
  -> Draft reply created

### Urgent
- [Mike @ Widgets Inc] Invoice #4521 overdue notice
  Action: Invoice needs attention
  -> Draft reply created
- [Legal @ Acme Corp] Updated terms of service
  Action: Contract/legal review needed

### Needs Response
- [Jane @ Team] Project status update request
- [Tom @ Vendor] Proposal follow-up

### Informational (5 emails)
- Newsletter: TechCrunch daily digest
- GitHub: PR merged in agend-app
- 3 more...

### Low Priority (8 emails)
- Marketing: SaaS tool promo (x3)
- Notifications: LinkedIn (x2)
- 3 more...

---
Scanned 24 emails | 3 drafts created | 2 action items detected
Triage file: data/triage/2026-03-23T0900.jsonl
```

### Anti-Patterns to Avoid

- **Reading all email bodies upfront:** Burns tokens on newsletters and spam. Use two-pass: metadata first, selective body reads second.
- **Classifying in the main conversation:** Email bodies fill context window. Always delegate to email-scanner subagent.
- **Hardcoding client list in prompts:** Makes updates require code changes. Use the external clients.jsonl file.
- **Creating drafts for every email:** Per D-08, only urgent + known client emails get drafts. Not all "needs-response" items.
- **Storing raw email content in triage JSONL:** Only store snippet (200 chars per schema). Raw content stays in subagent context only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gmail access | Custom OAuth + API client | hardened-workspace MCP tools | Already installed, OAuth configured, security-hardened |
| Email sending prevention | Permission checks in code | Hardened MCP fork (tools physically removed) | Code checks can be bypassed. Removed tools cannot. |
| Gmail search syntax | Custom date filtering logic | Gmail query operators (`newer_than:1d`, `is:starred`) | Gmail API supports full search operator syntax natively |
| Batch email retrieval | Loop of individual reads | `get_gmail_messages_content_batch` (up to 25/call) | Single API call vs 25 individual calls. Reduces quota usage. |
| JSON validation | Custom parsers | `scripts/validate-data.sh` + jq | Already built in Phase 1. Validates NDJSON line-by-line. |
| Dashboard data compilation | Custom build script | `scripts/build-dashboard-data.sh` | Already built in Phase 1. Compiles NDJSON to dashboard JSON. |

## Common Pitfalls

### Pitfall 1: Token Cost Explosion from Naive Email Processing
**What goes wrong:** Feeding entire email threads (HTML + signatures + full reply chains) into Claude burns excessive tokens. A busy inbox of 50+ emails with long threads can cost $10-30/day.
**Why it happens:** Email bodies are deceptively large. A single thread with 5 replies can be 15-30K tokens.
**How to avoid:** Two-pass approach (metadata first, selective body reads). Preprocess bodies (strip HTML, signatures, reply chains per D-11). Track token usage in feed entries.
**Warning signs:** Triage runs taking unusually long. Unexpectedly high API bills.

### Pitfall 2: Gmail API Rate Limits on First Run
**What goes wrong:** First triage run processes many emails, hitting Gmail API quota (15,000 units/minute). Partial failures leave inconsistent state.
**Why it happens:** Each messages.list + messages.get costs quota units. Large inboxes exhaust quota quickly.
**How to avoid:** Use batch retrieval (get_gmail_messages_content_batch, 25 at a time). Limit to last 24 hours (D-10) which naturally bounds volume. If rate-limited, the subagent should pause and retry.
**Warning signs:** 429 errors from Gmail API. Incomplete triage results.

### Pitfall 3: Client Domain Matching Edge Cases
**What goes wrong:** Client emails come from personal Gmail addresses, subdomains (support.acmecorp.com), or third-party services (acmecorp.freshdesk.com). Domain matching misses these.
**How to avoid:** Match on base domain (strip subdomains). Allow the clients.jsonl to include alternate domains per client. Have Claude flag frequent unknown senders as potential client domain suggestions (D-03).
**Warning signs:** Known client emails classified as "informational" or "low-priority".

### Pitfall 4: Draft Reply Threading Broken
**What goes wrong:** Gmail drafts created via MCP don't thread properly with the original email. Glen sees orphaned drafts instead of in-line replies.
**How to avoid:** Use the `in_reply_to` parameter of `draft_gmail_message` with the original message's message_id. This ensures Gmail threads the draft correctly.
**Warning signs:** Drafts appear as new conversations in Gmail instead of threaded replies.

### Pitfall 5: Triage JSONL File Naming Collisions
**What goes wrong:** Two triage runs in the same minute produce the same filename, overwriting the first run's results.
**How to avoid:** Use ISO 8601 timestamp with seconds in filename: `data/triage/2026-03-23T090015.jsonl`. Or use format `YYYY-MM-DDTHHMM.jsonl` as specified in the triage-record schema description and ensure only one run per minute (practical for interactive use).
**Warning signs:** Missing triage records. Feed entries reference files that don't match expected content.

### Pitfall 6: Starred Email Sync Delay
**What goes wrong:** Glen stars an email on phone. Next triage run hasn't happened yet. Starred queue appears stale.
**How to avoid:** Each triage run re-queries `is:starred newer_than:1d`. The starred field in triage records reflects the state at scan time. Document that starred status is refreshed per-run, not real-time.
**Warning signs:** Glen reports starred emails not appearing in triage results.

## Code Examples

### MCP Tool Usage: Search Emails (last 24 hours)
```
# Via hardened-workspace MCP
search_gmail_messages(query="newer_than:1d")
# Returns: list of message IDs + thread IDs + subjects + snippets

# Starred emails specifically
search_gmail_messages(query="is:starred newer_than:1d")
```
Source: [Gmail search operators](https://support.google.com/mail/answer/7190), [hardened-workspace MCP](https://github.com/c0webster/hardened-google-workspace-mcp)

### MCP Tool Usage: Batch Read Email Content
```
# Read up to 25 emails at once
get_gmail_messages_content_batch(message_ids=["msg1", "msg2", ...])
# Returns: subject, sender, body content, attachments for each
```
Source: [google_workspace_mcp tools](https://github.com/taylorwilsdon/google_workspace_mcp)

### MCP Tool Usage: Create Gmail Draft (threaded reply)
```
# Create a draft reply to a specific email
draft_gmail_message(
  to="sarah@acmecorp.com",
  subject="Re: Contract renewal Q3",
  body="Hi Sarah,\n\nThanks for sending this over. I've reviewed the key terms...",
  in_reply_to="<original-message-id>"
)
```
Source: [google_workspace_mcp tools](https://github.com/taylorwilsdon/google_workspace_mcp)

### Triage Record Example (one line in JSONL)
```json
{"message_id":"18e1234abc","thread_id":"18e1234abc","from":"sarah@acmecorp.com","from_name":"Sarah Chen","subject":"Contract renewal Q3","received":"2026-03-23T09:15:00+10:00","category":"client","priority":"urgent","starred":true,"has_attachments":true,"snippet":"Hi Glen, Please find attached the Q3 contract renewal...","action_items":["Review contract by Friday","Check updated payment terms"],"suggested_action":"draft-reply"}
```
Source: schemas/triage-record.json

### Feed Entry Example (triage event)
```json
{"ts":"2026-03-23T09:30:00+10:00","type":"triage","summary":"Scanned 24 emails: 2 urgent, 5 needs-response, 9 informational, 8 low-priority. 3 drafts created.","level":"info","trigger":"manual","details":{"emails_scanned":24,"urgent":2,"needs_response":5,"informational":9,"low_priority":8,"drafts_created":3,"action_items_detected":4,"triage_file":"data/triage/2026-03-23T0930.jsonl"},"duration_ms":45000}
```
Source: schemas/feed-entry.json

### Client Domain Seed List (data/config/clients.jsonl)
```json
{"domain":"acmecorp.com","name":"Acme Corp","aliases":["acme.com"],"contact":"Sarah Chen"}
{"domain":"widgetsinc.com.au","name":"Widgets Inc","aliases":[],"contact":"Mike Williams"}
{"domain":"example.org","name":"Example Foundation","aliases":["example.org.au"],"contact":"Jane Doe"}
```

### Subagent Definition (.claude/agents/email-scanner.md)
```markdown
---
name: email-scanner
description: Scans Gmail inbox via hardened MCP, triages emails by priority, generates draft replies for urgent/client emails. Use when /triage-inbox is invoked.
tools: Read, Write, Edit, Bash, mcp__hardened-workspace__search_gmail_messages, mcp__hardened-workspace__get_gmail_message_content, mcp__hardened-workspace__get_gmail_messages_content_batch, mcp__hardened-workspace__draft_gmail_message, mcp__hardened-workspace__list_gmail_labels
model: sonnet
---

You are an email triage agent for Glen, founder of Agend Systems (~30 clients).

[System prompt with classification rules, client list loading, preprocessing steps, draft generation instructions...]
```

## MCP Tool Reference (Hardened Workspace -- Gmail Subset)

| Tool Name | Parameters | Returns | Available |
|-----------|------------|---------|-----------|
| `search_gmail_messages` | query (string, required) | Message IDs, thread IDs, subjects, snippets | Yes |
| `get_gmail_message_content` | message_id (string, required) | Full email: subject, sender, body, attachments | Yes |
| `get_gmail_messages_content_batch` | message_ids (array, max 25) | Batch of full email contents | Yes |
| `draft_gmail_message` | to, subject, body (required); cc, bcc, in_reply_to (optional) | Created draft ID | Yes |
| `list_gmail_labels` | (none) | All system and user labels | Yes |
| `list_gmail_drafts` | (none) | Existing drafts | Yes |
| `send_gmail_message` | -- | -- | **REMOVED** (security) |
| `create_gmail_filter` | -- | -- | **REMOVED** (security) |
| `modify_gmail_message_labels` | message_id, add_labels, remove_labels | Updated label state | Yes (read starred status) |

## Schema Compatibility Notes

### triage-record.json Extensions Needed

The existing schema covers most needs but should be extended for Phase 2:

| Field | Current State | Needed For |
|-------|---------------|------------|
| `client_name` | Not in schema | D-14: Tag triage results with client name |
| `client_domain` | Not in schema | D-14: Domain match tracking |
| `action_type` | Not in schema (action_items is array of strings) | D-13: Structured action type enum (contract, invoice, meeting, deadline) |
| `draft_id` | Not in schema | Track which emails got draft replies |

**Recommendation:** Extend the schema with these optional fields. The schema uses `"additionalProperties": false` so fields must be explicitly added.

### feed-entry.json -- No Changes Needed

The existing schema handles triage events via:
- `type: "triage"`
- `details` object (additionalProperties: true) for triage-specific metadata
- All required fields (ts, type, summary, level, trigger) are straightforward

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Claude processes emails in main conversation | Subagent isolation for email processing | Claude Code subagents (2025+) | Keeps main context clean, prevents compaction issues |
| Individual message reads | Batch read (get_gmail_messages_content_batch) | google_workspace_mcp 2026 | Reduces API calls from N to ceil(N/25) |
| Full HTML email processing | Preprocess + selective body reads | Best practice | 5-10x token cost reduction |
| Unmodified MCP server | Hardened fork with removed tools | c0webster fork 2025 | Eliminates prompt injection exfiltration vector |

## Open Questions

1. **Exact MCP tool name format for subagent tools field**
   - What we know: The command stub uses `mcp__hardened-workspace__*` prefix. Subagent tools use explicit tool names.
   - What's unclear: Whether the glob pattern (`mcp__hardened-workspace__*`) works in subagent tools field, or whether each tool must be listed individually.
   - Recommendation: List tools individually in subagent definition. Test glob pattern. If glob works, use it for simplicity.

2. **Gmail search_gmail_messages result format**
   - What we know: Returns message IDs, thread IDs, subjects, snippets.
   - What's unclear: Exact JSON structure of the response. Whether it includes sender, date, labels, or just IDs.
   - Recommendation: First task should include a discovery step -- run `search_gmail_messages(query="newer_than:1d")` and inspect the response structure. Adapt parsing accordingly.

3. **draft_gmail_message in_reply_to parameter behavior**
   - What we know: Parameter exists for threading. Needs the original message ID or Message-ID header.
   - What's unclear: Whether `in_reply_to` expects the Gmail message_id or the RFC 2822 Message-ID header value.
   - Recommendation: Test with a known email. Try message_id first, fall back to Message-ID header if threading doesn't work.

4. **Tone mirroring sample size**
   - What we know: Need to study Glen's sent emails (D-06). `in:sent newer_than:30d` gets recent samples.
   - What's unclear: How many sent emails provide enough style signal without excessive token cost.
   - Recommendation: Sample 10-15 recent sent emails. Extract style notes once. Store in subagent prompt or a reference file. Refresh monthly.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| hardened-workspace MCP | Gmail access (EMAIL-01 through EMAIL-07) | Yes | latest | None -- this is the only safe Gmail path |
| jq | Data validation, dashboard build | Yes | 1.7.1 | None needed |
| Python 3 | MCP server runtime | Yes | 3.14.3 | None needed |
| uv | MCP server package manager | Yes | 0.8.4 | None needed |
| Claude Code subagents | Context isolation | Yes | Built-in | Could run in main conversation (not recommended) |

**Missing dependencies with no fallback:** None -- all required tools are available.

## Project Constraints (from CLAUDE.md)

- **MCP server:** Use ONLY `hardened-workspace` MCP server for Gmail/Drive. DO NOT use `claude.ai Gmail` or `claude.ai Google Calendar` connectors.
- **Tool prefix:** Gmail tools use `mcp__hardened-workspace__` prefix.
- **Security model:** Claude can READ emails and CREATE drafts, but CANNOT send, share, create filters, or delete.
- **Data conventions:** Feed entries append to `data/feed.jsonl`. Triage results go to `data/triage/{timestamp}.jsonl`. All timestamps ISO 8601 with timezone offset.
- **Schemas:** All records must conform to `schemas/` directory JSON Schema definitions.
- **Commands:** Use YAML frontmatter with `allowed-tools` to constrain tool access per command.
- **GSD workflow:** Do not make direct repo edits outside a GSD workflow unless user explicitly asks.

## Sources

### Primary (HIGH confidence)
- [hardened-google-workspace-mcp (GitHub)](https://github.com/c0webster/hardened-google-workspace-mcp) -- verified connected, tool surface confirmed
- [hardened-google-workspace-mcp SECURITY.md](https://github.com/c0webster/hardened-google-workspace-mcp/blob/main/SECURITY.md) -- removed tools documented
- [google_workspace_mcp README_NEW.md](https://github.com/taylorwilsdon/google_workspace_mcp/blob/main/README_NEW.md) -- Gmail tool parameters
- [Claude Code subagents docs](https://code.claude.com/docs/en/sub-agents) -- subagent YAML frontmatter, tools, model, MCP scoping
- [Gmail search operators (Google)](https://support.google.com/mail/answer/7190) -- query syntax: newer_than, is:starred, is:unread, in:sent
- [Gmail API messages.get (Google)](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get) -- format options: full, minimal, metadata
- schemas/triage-record.json -- verified existing schema fields and enums
- schemas/feed-entry.json -- verified existing schema fields and enums
- .claude/commands/triage-inbox.md -- verified existing stub with allowed-tools

### Secondary (MEDIUM confidence)
- [Gmail API quota docs](https://developers.google.com/workspace/gmail/api/reference/quota) -- 15,000 quota units/minute/user rate limit
- [google_workspace_mcp (PulseMCP)](https://www.pulsemcp.com/servers/taylorwilsdon-google-workspace) -- tool capability overview

### Tertiary (LOW confidence)
- Exact response format of `search_gmail_messages` -- needs runtime validation
- `in_reply_to` parameter threading behavior -- needs runtime testing
- Glob pattern support in subagent tools field -- needs runtime testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tools verified installed and connected, schemas confirmed
- Architecture: HIGH -- subagent pattern well-documented, MCP tool interface confirmed
- Pitfalls: HIGH -- token cost, rate limits, and threading issues are well-known problems with documented mitigations
- MCP tool parameters: MEDIUM -- tool names confirmed via docs and SECURITY.md, but exact response structures need runtime verification

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable domain, MCP server pinned at installed version)
