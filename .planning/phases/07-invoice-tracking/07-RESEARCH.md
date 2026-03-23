# Phase 7: Invoice Tracking - Research

**Researched:** 2026-03-23
**Domain:** Xero API integration, invoice NDJSON schema, Claude command patterns
**Confidence:** HIGH

## Summary

Phase 7 adds invoice tracking to Agend Ops by following the exact pattern established in Phase 6 (to-dos): schema + command + briefing section + dashboard tab. The critical new element is Xero integration -- an official Xero MCP server (`@xeroapi/xero-mcp-server`) exists on npm (v0.0.14) that provides `list-invoices`, `create-invoice`, and `update-invoice` tools out of the box. This eliminates the need to build custom API integration.

The architecture has two data flows: (1) email triage detects `action_type: "invoice"` and creates local invoice records as "you should invoice this" reminders, and (2) the Xero MCP server pulls real invoice data (status, amounts, payment tracking) as the source of truth for "what's outstanding." Local NDJSON serves as a cache/mirror for the dashboard display, combining both email-detected reminders and Xero-synced invoice records.

Xero's Custom Connections feature (client_credentials grant) is the recommended auth approach for single-organisation M2M use. Access tokens expire every 30 minutes but the MCP server handles token refresh automatically using the client ID and secret. Glen will need to create a Custom Connection in the Xero Developer Portal and provide the credentials as environment variables.

**Primary recommendation:** Use the official `@xeroapi/xero-mcp-server` via npx with Custom Connections auth. Design the local invoice schema to mirror key Xero fields (InvoiceID, Status, AmountDue, DueDate, Contact) while adding Agend-specific fields (project_code, source_email_id, trigger). The /invoice command handles both local reminder creation and Xero sync operations.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Standard lifecycle: draft -> sent -> overdue -> paid. Plus disputed and written-off states.
- **D-02:** Overdue auto-detected based on due_date vs current date
- **D-03:** Primary data source is Xero (Glen's accounting software) -- sync invoice status from Xero API, not just email detection
- **D-03b:** Two problems to solve: (1) forgetting to invoice after work is done, (2) losing track of unpaid/overdue invoices
- **D-04:** Core fields: client_name, amount, due_date, status, description
- **D-05:** Reference fields: invoice_number, po_number, source_email_id, project_code (e.g., PROP-0324)
- **D-06:** Financial fields: currency (AUD default), tax_amount, payment_terms (e.g., "net 30")
- **D-07:** Mostly AUD but support other currencies (currency field with AUD default)
- **D-08:** Project code is a key field -- Glen's clients use codes like PROP-0324 for cross-referencing
- **D-09:** Best-effort extraction from invoice-related emails -- try to extract client, amount, due date, project code. Flag uncertain fields for Glen to confirm.
- **D-10:** Auto-create invoice records from triage-detected invoice emails (action_type: "invoice")
- **D-11:** Connect to Xero API to pull real invoice data (status, amounts, due dates, payment status)
- **D-12:** Xero is the source of truth for invoice lifecycle -- local NDJSON is a cache/mirror for dashboard display
- **D-13:** Email detection serves as a "you should invoice this" reminder, Xero serves as "here's what's outstanding"

### Claude's Discretion
- Invoice NDJSON schema exact field design (following todo-record.json pattern)
- /invoice command modes (following /todo pattern: list, create, mark-paid, list-overdue)
- How best-effort extraction works (regex patterns, AI analysis, confidence flags)
- Dashboard "Invoices" tab layout (overdue highlighted, grouped by status)
- How overdue detection triggers (on command run, on triage, on briefing)
- Invoice-scanner subagent design (if needed, or extend existing triage pipeline)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INV-01 | /invoice command supports create, list, mark-paid, and list-overdue operations | Follows /todo command pattern (5 modes). Xero MCP provides `list-invoices` for sync. |
| INV-02 | Invoice records stored in NDJSON (data/invoices/active.jsonl) with schema | Schema design mirrors todo-record.json + task-record.json with Xero-specific and financial fields. |
| INV-03 | Triage pipeline auto-detects invoice requests and creates invoice records | Email-scanner already detects `action_type: "invoice"`. Triage-inbox maps to "document-summary" -- needs new "invoice-reminder" path. |
| INV-04 | Dashboard "Invoices" tab shows pending, overdue, and recently paid invoices | Follows existing tab pattern. Build script compiles invoices.json. Dashboard tab added to docs/index.html. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @xeroapi/xero-mcp-server | 0.0.14 | Xero API access via MCP protocol | Official Xero MCP server, published by XeroAPI org. Provides list-invoices, create-invoice, update-invoice tools. Handles OAuth token refresh internally. |
| jq | 1.7.1 | JSON/NDJSON processing in shell | Already installed and used throughout the project. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| npx | 10.9.4 (via npm) | Run @xeroapi/xero-mcp-server without install | MCP server launched via `npx -y @xeroapi/xero-mcp-server@latest` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @xeroapi/xero-mcp-server (official) | john-zhang-dev/xero-mcp (community) | Community version exists but official is maintained by XeroAPI org directly. Use official. |
| Xero MCP server | Direct Xero REST API calls via curl | MCP server handles OAuth token lifecycle, provides typed tools, integrates natively with Claude. Direct curl would require manual token management. |
| Custom Connections (client_credentials) | Standard auth code flow | Custom Connections are M2M, no user interaction needed for token refresh. Perfect for single-org automation. Standard flow requires browser-based login. |

**Installation:**
MCP server is configured in `~/.claude.json`, not npm-installed:
```json
{
  "mcpServers": {
    "xero": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@xeroapi/xero-mcp-server@latest"],
      "env": {
        "XERO_CLIENT_ID": "<from-xero-developer-portal>",
        "XERO_CLIENT_SECRET": "<from-xero-developer-portal>"
      }
    }
  }
}
```

**Version verification:** `@xeroapi/xero-mcp-server` version 0.0.14 confirmed via `npm view` on 2026-03-23.

## Architecture Patterns

### Recommended Project Structure (new files for Phase 7)
```
schemas/
  invoice-record.json          # New: invoice NDJSON schema
data/
  invoices/
    active.jsonl               # New: invoice records (NDJSON)
.claude/
  commands/
    invoice.md                 # New: /invoice command
    triage-inbox.md            # Modified: add invoice auto-queue path
    daily-briefing.md          # Modified: add invoice section
scripts/
  build-dashboard-data.sh      # Modified: add invoices.json compilation
docs/
  index.html                   # Modified: add Invoices tab
```

### Pattern 1: Dual Data Flow (Email Reminders + Xero Sync)
**What:** Two separate data sources feed the invoice NDJSON:
1. **Email triage** creates "reminder" records (trigger: "triage-suggestion") when action_type "invoice" is detected -- these represent "you should invoice this client"
2. **Xero sync** pulls real invoice data (trigger: "xero-sync") with actual status, amounts, payment tracking -- these represent "here's what's outstanding in Xero"

**When to use:** Always -- this is the core architecture decision from D-12/D-13.

**How it works:**
- Email-detected reminders have `xero_invoice_id: null` and `status: "reminder"` until Glen creates the actual invoice in Xero
- Xero-synced records have `xero_invoice_id` populated and statuses that mirror Xero (draft, sent/authorised, overdue, paid)
- When Glen invoices a client in Xero after a reminder, he can link the reminder to the Xero invoice via `/invoice link`

### Pattern 2: Xero Status Mapping
**What:** Map Xero's 6 invoice statuses to the local lifecycle from D-01.

| Xero Status | Local Status | Description |
|-------------|-------------|-------------|
| DRAFT | draft | Invoice created but not approved/sent |
| SUBMITTED | draft | Awaiting approval (treated as draft locally) |
| AUTHORISED | sent | Approved and sent to client, awaiting payment |
| PAID | paid | Fully paid |
| VOIDED | written-off | Cancelled/voided |
| DELETED | (remove record) | Deleted in Xero, remove from local cache |

**Additional local statuses (not in Xero):**
- `reminder` -- email-detected, not yet created in Xero
- `overdue` -- derived from `status == "sent"` AND `due_date < today` (per D-02)
- `disputed` -- manually flagged by Glen (not a Xero status)
- `written-off` -- bad debt written off (maps from VOIDED or manual)

### Pattern 3: MCP Tool Usage for Xero Operations
**What:** Use the Xero MCP server tools directly from command implementations.

```
# List outstanding invoices from Xero
mcp__xero__list-invoices  (with status filter)

# Sync: pull Xero data and update local NDJSON
# The /invoice sync command would:
# 1. Call list-invoices via MCP
# 2. For each Xero invoice, update/create local NDJSON record
# 3. Mark overdue based on due_date comparison
```

### Pattern 4: Invoice Schema (following todo-record.json pattern)
**What:** NDJSON schema with `additionalProperties: false`, required fields, Xero + Agend fields.

```json
{
  "id": "inv-2026-03-23-001",
  "ts": "2026-03-23T10:30:00+10:00",
  "status": "sent",
  "client_name": "PROP Pty Ltd",
  "amount": 5500.00,
  "currency": "AUD",
  "tax_amount": 500.00,
  "due_date": "2026-04-22",
  "description": "March AMS module deployment",
  "invoice_number": "INV-0042",
  "po_number": "PO-2026-003",
  "project_code": "PROP-0324",
  "payment_terms": "net 30",
  "source_email_id": "msg-abc123",
  "xero_invoice_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "trigger": "xero-sync",
  "amount_paid": 0.00,
  "completed_at": null
}
```

### Anti-Patterns to Avoid
- **Duplicating Xero logic locally:** Do not build payment tracking, tax calculation, or invoice numbering locally. Xero handles these -- sync from it.
- **Overdue as a stored status:** Overdue is computed (`status == "sent" AND due_date < today`), not stored. If you store it, it goes stale immediately. Always compute on read.
- **Polling Xero on every dashboard load:** Dashboard reads static `invoices.json`. Xero sync happens on `/invoice sync`, during briefing, or during triage -- never on page load.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Xero API integration | Custom REST client with OAuth token management | @xeroapi/xero-mcp-server | Token refresh, scope management, API versioning all handled. MCP tools integrate natively with Claude. |
| OAuth token storage/refresh | Token file management, expiry tracking, refresh logic | Xero MCP server Custom Connections | Custom Connections use client_credentials grant -- the MCP server requests fresh tokens automatically using client ID and secret. No refresh token rotation needed. |
| Invoice numbering | Sequential numbering system | Xero's InvoiceNumber | Xero auto-generates invoice numbers. For email-detected reminders, use the local ID pattern (inv-YYYY-MM-DD-NNN). |
| Currency conversion | Exchange rate lookup, conversion math | Xero's CurrencyRate field | Xero handles multi-currency with exchange rates. Just store and display what Xero provides. |
| Tax calculation | GST/VAT computation | Xero's TotalTax field | Xero computes tax based on contact/line-item tax rates. Just mirror the computed values. |

**Key insight:** Xero is a full accounting system. The local NDJSON is a read-only cache for dashboard display and briefing integration. Never duplicate accounting logic that Xero already handles.

## Common Pitfalls

### Pitfall 1: Xero Custom Connections Require Premium
**What goes wrong:** Custom Connections (client_credentials grant) may require a Xero partner or premium tier.
**Why it happens:** Custom Connections are a Xero premium option for M2M integrations.
**How to avoid:** Verify Glen's Xero subscription supports Custom Connections. If not, fall back to standard auth code flow (requires initial browser login, then refresh token rotation).
**Warning signs:** 403 errors or "insufficient permissions" when trying to create a Custom Connection in the Developer Portal.

### Pitfall 2: Xero Access Tokens Expire Every 30 Minutes
**What goes wrong:** API calls fail after 30 minutes of token issuance.
**Why it happens:** Xero access tokens have a strict 30-minute TTL. With Custom Connections, the MCP server should auto-request new tokens. With standard auth flow, refresh tokens must be rotated.
**How to avoid:** The Xero MCP server handles this internally for Custom Connections. For standard auth, unused refresh tokens expire after 60 days -- a sync must run at least every 60 days.
**Warning signs:** 401 errors after ~30 minutes of first successful call.

### Pitfall 3: Granular Scopes Change (March 2026)
**What goes wrong:** Apps created after March 2, 2026 must use new granular scopes. Old broad scopes (accounting.transactions) don't work.
**Why it happens:** Xero is transitioning to granular scopes for security.
**How to avoid:** Use the new granular scopes when creating the Custom Connection:
- `accounting.invoices.read` (list/get invoices)
- `accounting.contacts.read` (resolve contact names)
- `accounting.transactions.read` (if broader access needed -- may still work for existing apps)
**Warning signs:** Scope-related errors during OAuth, "invalid_scope" responses.

### Pitfall 4: Xero Rate Limits
**What goes wrong:** Too many API calls hit rate limits.
**Why it happens:** Xero enforces 60 calls/minute/org and 5,000 calls/day/org with max 5 concurrent requests.
**How to avoid:** For ~30 clients, a single list-invoices call with status filter retrieves all outstanding invoices. Sync once during briefing/triage, not repeatedly. Cache results in NDJSON.
**Warning signs:** HTTP 429 responses, "rate limit exceeded" errors.

### Pitfall 5: Dashboard Privacy with Invoice Amounts
**What goes wrong:** Client names and invoice amounts visible on public GitHub Pages dashboard.
**Why it happens:** STATE.md flags: "Dashboard privacy decision needed before Phase 7 -- invoices may contain sensitive client/amount data on public GitHub Pages."
**How to avoid:** Either (a) make the repo/Pages private, (b) redact sensitive fields in invoices.json, or (c) accept the risk given the URL is not publicly discoverable. This is a decision Glen needs to make.
**Warning signs:** Sensitive financial data visible at the public dashboard URL.

### Pitfall 6: Storing Overdue as a Status
**What goes wrong:** Records marked "overdue" never get updated back to "sent" if the due date is extended, or remain "overdue" after payment.
**Why it happens:** Overdue is a function of time, not a state transition. It should be computed dynamically.
**How to avoid:** Per D-02, overdue is derived: `status == "sent" && due_date < today`. The /invoice list and dashboard should compute this on render. Never write "overdue" to the status field.
**Warning signs:** Inconsistent overdue counts between dashboard refreshes.

## Code Examples

### Invoice Record Schema (schemas/invoice-record.json)

Based on todo-record.json and task-record.json patterns, with Xero + financial fields from D-04 through D-08:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "invoice-record",
  "title": "Invoice Record",
  "description": "One line in data/invoices/active.jsonl. Tracks invoices for Glen's clients.",
  "type": "object",
  "required": ["id", "ts", "status", "client_name", "trigger"],
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique invoice ID in format inv-YYYY-MM-DD-NNN",
      "pattern": "^inv-\\d{4}-\\d{2}-\\d{2}-\\d{3}$"
    },
    "ts": {
      "type": "string",
      "description": "ISO 8601 timestamp with timezone offset when record was created"
    },
    "status": {
      "type": "string",
      "enum": ["reminder", "draft", "sent", "paid", "disputed", "written-off"],
      "description": "Current invoice state. 'reminder' = email-detected, not yet in Xero. Overdue is computed from status=sent + due_date < today."
    },
    "client_name": {
      "type": "string",
      "description": "Client or company name"
    },
    "amount": {
      "type": ["number", "null"],
      "description": "Invoice total amount (tax-inclusive). Null for reminders where amount is unknown."
    },
    "currency": {
      "type": "string",
      "default": "AUD",
      "description": "ISO 4217 currency code. Default AUD."
    },
    "tax_amount": {
      "type": ["number", "null"],
      "description": "Tax component of the invoice amount. Null if unknown."
    },
    "due_date": {
      "type": ["string", "null"],
      "description": "Payment due date in YYYY-MM-DD format.",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
    },
    "description": {
      "type": ["string", "null"],
      "description": "Brief description of what the invoice is for."
    },
    "invoice_number": {
      "type": ["string", "null"],
      "description": "Invoice number (from Xero or manual). E.g., INV-0042."
    },
    "po_number": {
      "type": ["string", "null"],
      "description": "Client's purchase order number if provided."
    },
    "project_code": {
      "type": ["string", "null"],
      "description": "Project code for cross-referencing. E.g., PROP-0324."
    },
    "payment_terms": {
      "type": ["string", "null"],
      "description": "Payment terms. E.g., 'net 30', 'net 14', 'due on receipt'."
    },
    "source_email_id": {
      "type": ["string", "null"],
      "description": "Gmail message ID if invoice record originated from email triage."
    },
    "xero_invoice_id": {
      "type": ["string", "null"],
      "description": "Xero InvoiceID (UUID) if synced from Xero. Null for email-detected reminders."
    },
    "trigger": {
      "type": "string",
      "enum": ["manual", "triage-suggestion", "xero-sync"],
      "description": "How the record was created."
    },
    "amount_paid": {
      "type": ["number", "null"],
      "description": "Amount paid so far (from Xero). Null if unknown."
    },
    "completed_at": {
      "type": ["string", "null"],
      "description": "ISO 8601 timestamp when invoice was fully paid or written off."
    }
  },
  "additionalProperties": false
}
```

### Triage Auto-Queue Extension (for triage-inbox.md)

The current mapping for `action_type: "invoice"` is `"document-summary"`. This should change to create an invoice reminder record instead of (or in addition to) a task:

```bash
# When action_type is "invoice":
# 1. Create an invoice reminder record in data/invoices/active.jsonl
# 2. Extract best-effort fields from the email (client_name from triage client_name,
#    amount/project_code from snippet parsing)

INV_ID="inv-$(date +%Y-%m-%d)-${NEXT}"
NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')

jq -n -c \
  --arg id "$INV_ID" \
  --arg ts "$NOW" \
  --arg client "$CLIENT_NAME" \
  --arg desc "$ACTION_ITEM_TEXT" \
  --arg email_id "$MESSAGE_ID" \
  '{
    id: $id, ts: $ts, status: "reminder",
    client_name: $client, amount: null, currency: "AUD",
    tax_amount: null, due_date: null, description: $desc,
    invoice_number: null, po_number: null, project_code: null,
    payment_terms: null, source_email_id: $email_id,
    xero_invoice_id: null, trigger: "triage-suggestion",
    amount_paid: null, completed_at: null
  }' >> data/invoices/active.jsonl
```

### Xero Sync Pattern (for /invoice sync mode)

```
# Conceptual flow for /invoice sync:
# 1. Call mcp__xero__list-invoices to get all AUTHORISED invoices
# 2. For each Xero invoice:
#    a. Check if xero_invoice_id exists in local NDJSON
#    b. If exists: update status, amount_paid, amount_due
#    c. If not exists: create new record with trigger "xero-sync"
# 3. Check local records with xero_invoice_id against Xero data
#    - If Xero shows PAID: update local to "paid", set completed_at
#    - If Xero shows VOIDED: update local to "written-off"
# 4. Compute overdue: any "sent" record where due_date < today
```

### Build Script Addition (for build-dashboard-data.sh)

```bash
# Compile active invoices -> docs/invoices.json
if [ -s "$REPO_ROOT/data/invoices/active.jsonl" ]; then
  jq -s '.' "$REPO_ROOT/data/invoices/active.jsonl" > "$REPO_ROOT/docs/invoices.json"
  echo "Built docs/invoices.json ($(jq length "$REPO_ROOT/docs/invoices.json") entries)"
else
  echo "[]" > "$REPO_ROOT/docs/invoices.json"
  echo "Built docs/invoices.json (empty -- no invoice data yet)"
fi
```

## Xero MCP Server Configuration

### Setup Steps for Glen

1. **Go to Xero Developer Portal** (developer.xero.com)
2. **Create a Custom Connection app** (or standard OAuth app if Custom Connections require premium)
3. **Select scopes:** For apps created after March 2, 2026:
   - `accounting.invoices.read` (read invoices)
   - `accounting.contacts.read` (resolve contact names)
   - Optionally `accounting.invoices` (if write access needed)
4. **Follow the authorisation flow** to connect to Glen's Xero organisation
5. **Copy Client ID and Client Secret** from the app configuration
6. **Add to MCP configuration** in `~/.claude.json`:

```json
{
  "xero": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@xeroapi/xero-mcp-server@latest"],
    "env": {
      "XERO_CLIENT_ID": "<client-id>",
      "XERO_CLIENT_SECRET": "<client-secret>"
    }
  }
}
```

### Available Xero MCP Tools (relevant to Phase 7)

| Tool | Purpose | Use Case |
|------|---------|----------|
| `list-invoices` | List invoices with optional filters | Sync: pull all outstanding invoices |
| `create-invoice` | Create a new invoice in Xero | Not needed for Phase 7 (track-only) |
| `update-invoice` | Update invoice status/fields | Not needed for Phase 7 (track-only) |
| `list-contacts` | List Xero contacts | Resolve client names during sync |
| `list-payments` | List payment records | Check payment status on invoices |
| `list-aged-receivables-by-contact` | Aged receivables report | Dashboard: who owes money, how long |

### Xero Invoice Data Model (key fields for local schema)

| Xero Field | Type | Maps To Local |
|------------|------|---------------|
| InvoiceID | UUID | xero_invoice_id |
| InvoiceNumber | String | invoice_number |
| Status | Enum (DRAFT/SUBMITTED/AUTHORISED/PAID/VOIDED/DELETED) | status (mapped) |
| Contact.Name | String | client_name |
| Reference | String | project_code (or po_number) |
| Total | Decimal | amount |
| TotalTax | Decimal | tax_amount |
| AmountDue | Decimal | (computed: amount - amount_paid) |
| AmountPaid | Decimal | amount_paid |
| DueDate | Date | due_date |
| CurrencyCode | String | currency |
| FullyPaidOnDate | Date | completed_at |
| UpdatedDateUTC | DateTime | (used for sync staleness) |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Broad OAuth scopes (accounting.transactions) | Granular scopes (accounting.invoices.read) | March 2, 2026 | Apps created after this date MUST use granular scopes. Existing apps must migrate by Sept 2027. |
| Build custom Xero API client | Use @xeroapi/xero-mcp-server | Late 2025 | No custom integration code needed. Official MCP server provides typed tools for all Xero operations. |
| Standard OAuth auth flow (browser login) | Custom Connections (client_credentials) | Available since ~2024 | M2M auth without user interaction. Best for single-org automation like this project. |

**Deprecated/outdated:**
- `accounting.transactions` scope: Being replaced by `accounting.invoices`, `accounting.payments`, `accounting.banktransactions`
- Direct REST API calls to Xero: Use MCP server instead for Claude integration

## Open Questions

1. **Custom Connections availability**
   - What we know: Custom Connections are a premium Xero feature for M2M auth. The MCP server supports them natively.
   - What's unclear: Whether Glen's Xero subscription includes Custom Connections access.
   - Recommendation: Check Glen's Xero plan first. If Custom Connections unavailable, use standard auth code flow (initial browser login, refresh token stored in env var).

2. **Dashboard privacy**
   - What we know: STATE.md flags this concern. Invoice data (client names, amounts) would be in public GitHub Pages dashboard.
   - What's unclear: Whether Glen wants to make the repo private, redact data, or accept the risk.
   - Recommendation: Make this a decision before implementing the dashboard tab. The data file (invoices.json) is committed to git and served publicly.

3. **Project code extraction from emails**
   - What we know: Glen's clients use codes like PROP-0324. These appear in email subjects and bodies.
   - What's unclear: How reliable regex extraction will be (format consistency varies by client).
   - Recommendation: Best-effort regex `[A-Z]{2,5}-\d{2,5}` extraction with confidence flag. Glen confirms uncertain matches.

4. **Xero Reference field as project_code**
   - What we know: Xero invoices have a "Reference" field that's a free-text string.
   - What's unclear: Whether Glen consistently uses the Reference field for project codes in Xero.
   - Recommendation: During sync, check if Reference matches a project code pattern. If so, map to project_code. Otherwise, store as-is and let Glen manually associate.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Xero MCP server (npx) | Yes | v22.22.1 | -- |
| npm/npx | Running @xeroapi/xero-mcp-server | Yes | 10.9.4 | -- |
| jq | NDJSON processing, build scripts | Yes | 1.7.1 | -- |
| @xeroapi/xero-mcp-server | Xero API access | Available on npm | 0.0.14 | Direct REST API (not recommended) |
| Xero Developer Account | OAuth credentials | Unknown | -- | Glen must create if not existing |
| Xero Custom Connections | M2M auth | Unknown (premium feature) | -- | Standard auth code flow |

**Missing dependencies with no fallback:**
- Xero Developer Account with Custom Connection (or standard OAuth app) -- Glen must set this up in Xero Developer Portal

**Missing dependencies with fallback:**
- Custom Connections: If unavailable, use standard auth code flow (one-time browser login, refresh token rotation)

## Project Constraints (from CLAUDE.md)

- **MCP server usage:** Use ONLY `hardened-workspace` for Gmail/Drive, but Xero MCP server (`xero`) is a new addition alongside it. Both coexist in `~/.claude.json`.
- **Data conventions:** All data in NDJSON, append-only, schema-validated, committed to git. Invoices follow this pattern exactly.
- **Security:** Email content and business data must not leak to third-party services beyond Claude's infrastructure. Xero is Glen's own accounting software, so syncing from it is within scope. The Xero MCP server communicates directly with Xero's API using Glen's credentials.
- **Dashboard:** Plain HTML/CSS/JS on GitHub Pages. No frameworks. Invoices tab follows existing pattern.
- **Commands:** Markdown files in `.claude/commands/`. /invoice follows /todo pattern.
- **GSD workflow:** All changes through GSD commands (plan -> execute).

## Sources

### Primary (HIGH confidence)
- [XeroAPI/xero-mcp-server (GitHub)](https://github.com/XeroAPI/xero-mcp-server) -- Official Xero MCP server, README, tool list, auth configuration
- [@xeroapi/xero-mcp-server (npm)](https://www.npmjs.com/package/@xeroapi/xero-mcp-server) -- Version 0.0.14, package metadata
- [XeroAPI/xero-ruby Invoice model (GitHub)](https://github.com/XeroAPI/xero-ruby/blob/master/lib/xero-ruby/models/accounting/invoice.rb) -- Complete invoice field list extracted from official SDK
- [Xero Accounting API Invoices (Official docs)](https://developer.xero.com/documentation/api/accounting/invoices) -- Invoice endpoints, statuses, query parameters
- [Xero Invoice Status best practices (Official docs)](https://developer.xero.com/documentation/best-practices/user-experience/invoice-status/) -- Status lifecycle (DRAFT, SUBMITTED, AUTHORISED, PAID, VOIDED, DELETED)
- [Xero OAuth 2.0 Overview (Official docs)](https://developer.xero.com/documentation/guides/oauth2/overview/) -- OAuth setup, token handling
- [Xero Custom Connections (Official docs)](https://developer.xero.com/documentation/guides/oauth2/custom-connections/) -- Client credentials grant, M2M auth
- [Xero Rate Limits (Official docs)](https://developer.xero.com/documentation/guides/oauth2/limits/) -- 60/min, 5000/day, 5 concurrent

### Secondary (MEDIUM confidence)
- [Xero Granular Scopes Blog Post (Xero Dev Blog, Feb 2026)](https://devblog.xero.com/upcoming-changes-to-xero-accounting-api-scopes-705c5a9621a0) -- accounting.invoices.read replaces accounting.transactions for new apps post March 2, 2026
- [OdataLink Xero Invoices Field Reference](https://help.odatalink.com/index.php?title=Xero_Accounting_Endpoint:_Invoices) -- Cross-referenced invoice field types and descriptions
- [Xero MCP Server announcement (Xero Dev Blog)](https://devblog.xero.com/xero-introduces-new-model-context-protocol-server-for-smarter-accounting-4d195ccaeda5) -- Launch announcement, feature overview

### Tertiary (LOW confidence)
- [Xero OAuth 2.0 FAQs](https://developer.xero.com/faq/oauth2) -- Token expiry details (30 min access, 60 day refresh) -- verified by multiple sources
- [Xero Custom Integration FAQs](https://developer.xero.com/faq/custom-integration) -- Custom Connections may require premium tier

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Official Xero MCP server exists, confirmed on npm, well-documented
- Architecture: HIGH -- Follows established Phase 6 patterns exactly, dual data flow is clearly defined by user decisions
- Xero API/Auth: HIGH -- Multiple sources confirm invoice model, OAuth flow, rate limits
- Pitfalls: MEDIUM -- Custom Connections premium requirement and granular scopes transition need runtime verification
- Dashboard privacy: LOW -- Flagged concern but no decision yet from user

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (30 days -- Xero API is stable, MCP server is early but actively maintained)
