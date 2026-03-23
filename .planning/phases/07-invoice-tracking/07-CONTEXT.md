# Phase 7: Invoice Tracking - Context

**Gathered:** 2026-03-23
**Status:** Complete

<domain>
## Phase Boundary

Add invoice tracking to Agend Ops — /invoice command, NDJSON schema, triage pipeline integration for auto-detection, and dashboard "Invoices" tab. Track-only (no sending). Follows the exact pattern established by Phase 6 (to-dos): schema + command + briefing + dashboard tab.

</domain>

<decisions>
## Implementation Decisions

### Invoice Lifecycle
- **D-01:** Standard lifecycle: draft → sent → overdue → paid. Plus disputed and written-off states.
- **D-02:** Overdue auto-detected based on due_date vs current date
- **D-03:** Primary data source is Xero (Glen's accounting software) — sync invoice status from Xero API, not just email detection
- **D-03b:** Two problems to solve: (1) forgetting to invoice after work is done, (2) losing track of unpaid/overdue invoices

### Invoice Data
- **D-04:** Core fields: client_name, amount, due_date, status, description
- **D-05:** Reference fields: invoice_number, po_number, source_email_id, project_code (e.g., PROP-0324)
- **D-06:** Financial fields: currency (AUD default), tax_amount, payment_terms (e.g., "net 30")
- **D-07:** Mostly AUD but support other currencies (currency field with AUD default)
- **D-08:** Project code is a key field — Glen's clients use codes like PROP-0324 for cross-referencing

### Triage Integration
- **D-09:** Best-effort extraction from invoice-related emails — try to extract client, amount, due date, project code. Flag uncertain fields for Glen to confirm.
- **D-10:** Auto-create invoice records from triage-detected invoice emails (action_type: "invoice")

### Xero Integration
- **D-11:** Connect to Xero API to pull real invoice data (status, amounts, due dates, payment status)
- **D-12:** Xero is the source of truth for invoice lifecycle — local NDJSON is a cache/mirror for dashboard display
- **D-13:** Email detection serves as a "you should invoice this" reminder, Xero serves as "here's what's outstanding"

### Claude's Discretion
- Invoice NDJSON schema exact field design (following todo-record.json pattern)
- /invoice command modes (following /todo pattern: list, create, mark-paid, list-overdue)
- How best-effort extraction works (regex patterns, AI analysis, confidence flags)
- Dashboard "Invoices" tab layout (overdue highlighted, grouped by status)
- How overdue detection triggers (on command run, on triage, on briefing)
- Invoice-scanner subagent design (if needed, or extend existing triage pipeline)

</decisions>

<specifics>
## Specific Ideas

- Project codes (PROP-0324) are how Glen thinks about work — they should be prominent in the invoice view
- Overdue invoices should be visually prominent — red badges, sorted to top
- The dashboard Invoices tab should feel like a quick "who owes me money" glance
- Track-only means low friction — Glen just needs to know what's outstanding, not manage a full accounting system

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 6 is the exact template: schema → command → build script → dashboard tab

### Established Patterns
- NDJSON append-only, schema-validated
- Command with multiple modes
- Dashboard tabs with cards

### Integration Points
- data/invoices/active.jsonl — new data file
- schemas/invoice-record.json — new schema
- .claude/commands/invoice.md — new command

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-invoice-tracking*
*Context gathered: 2026-03-23*
