---
description: "Create, list, mark-paid, sync, and track invoices"
allowed-tools: "Read, Write, Edit, Bash(jq *), Bash(date *), Bash(wc *), Bash(mkdir *), Bash(bash scripts/*), Bash(git *), mcp__xero__list-invoices, mcp__xero__list-contacts"
---

Manage invoice records for Glen. Argument: $ARGUMENTS

## Mode Detection

Determine which mode to run based on $ARGUMENTS:

- **If $ARGUMENTS is empty** -> Mode 1 (show outstanding invoices)
- **If $ARGUMENTS equals "list" or starts with "list "** -> Mode 2 (filterable list)
- **If $ARGUMENTS starts with "mark-paid " or "paid "** -> Mode 3 (mark invoice as paid)
- **If $ARGUMENTS equals "sync"** -> Mode 4 (Xero sync)
- **If $ARGUMENTS equals "overdue"** -> Mode 5 (show overdue only)
- **If $ARGUMENTS starts with "link "** -> Mode 6 (link a reminder to a Xero invoice)
- **Otherwise** -> Mode 7 (create new invoice with natural language)

---

## MODE 1: Show Outstanding Invoices (no arguments)

Display outstanding invoices grouped by urgency.

1. Read `data/invoices/active.jsonl`
2. Filter for entries where status is NOT "paid" and NOT "written-off" using jq:
   ```bash
   jq -s '[.[] | select(.status != "paid" and .status != "written-off")]' data/invoices/active.jsonl
   ```
3. Compute overdue dynamically: any record where `status == "sent"` AND `due_date < today`. Do NOT write overdue to the status field -- it is always computed on read per D-02.
   ```bash
   TODAY=$(date +%Y-%m-%d)
   # Get outstanding invoices with computed overdue flag
   jq -s --arg today "$TODAY" '
     [.[] | select(.status != "paid" and .status != "written-off")]
     | [.[] | . + {is_overdue: (.status == "sent" and .due_date != null and .due_date < $today)}]
   ' data/invoices/active.jsonl
   ```
4. Sort: overdue first (by how many days overdue, descending), then sent, then draft, then reminder. Within each group, sort by due_date ascending (soonest first, null last):
   ```bash
   TODAY=$(date +%Y-%m-%d)
   jq -s --arg today "$TODAY" '
     [.[] | select(.status != "paid" and .status != "written-off")]
     | [.[] | . + {
         is_overdue: (.status == "sent" and .due_date != null and .due_date < $today),
         sort_group: (
           if .status == "sent" and .due_date != null and .due_date < $today then 0
           elif .status == "sent" then 1
           elif .status == "draft" then 2
           elif .status == "disputed" then 3
           else 4 end
         )
       }]
     | sort_by(.sort_group, (if .due_date == null then "9999-99-99" else .due_date end))
   ' data/invoices/active.jsonl
   ```
5. Display with project_code prominent (per D-08, user specifics). Format amounts with comma-separated thousands and 2 decimal places, followed by currency code:

```
## Outstanding Invoices

OVERDUE:
  1. [!] PROP-0324 | PROP Pty Ltd | $5,500.00 AUD | Due 2026-03-15 (8 days overdue) | INV-0042
  2. [!] ACME-0401 | Acme Corp | $2,200.00 AUD | Due 2026-03-20 (3 days overdue)

SENT (awaiting payment):
  3. CLUB-0312 | Sporting Club | $3,300.00 AUD | Due 2026-04-01 | INV-0043

DRAFT:
  4. NEW-0401 | New Client | $1,100.00 AUD | No due date

REMINDERS (need to invoice):
  5. [?] -- | Smith & Co | Work completed per email | No amount yet

{N} outstanding. Run /invoice paid N to mark paid, /invoice sync to refresh from Xero.
```

**Amount formatting rules:**
- Amounts display with comma-separated thousands and 2 decimal places: `$5,500.00`
- Always show currency code after amount: `$5,500.00 AUD`
- If amount is null: show "No amount yet"

**Project code rules:**
- Show project_code BEFORE client name (most prominent position per D-08)
- If project_code is null: show `--` in its place

6. If no outstanding invoices: "No outstanding invoices. Run `/invoice sync` to refresh from Xero, or `/invoice <details>` to add one."

---

## MODE 2: List Invoices (list [filter])

Show invoices with optional filtering.

1. Read `data/invoices/active.jsonl`
2. Parse optional filter from arguments after "list":
   - `all` -> show all invoices
   - `paid` -> show only status="paid"
   - `reminders` -> show only status="reminder"
   - `sent` -> show only status="sent"
   - `draft` -> show only status="draft"
   - `disputed` -> show only status="disputed"
   - Any other text -> case-insensitive substring match on client_name or project_code
   - (no filter) -> show all outstanding (not paid, not written-off)

3. Apply filter using jq:
   ```bash
   # Example for status filter:
   jq -s '[.[] | select(.status == "paid")]' data/invoices/active.jsonl
   # Example for client/project search:
   SEARCH="acme"
   jq -s --arg s "$SEARCH" '[.[] | select((.client_name | ascii_downcase | contains($s | ascii_downcase)) or (.project_code // "" | ascii_downcase | contains($s | ascii_downcase)))]' data/invoices/active.jsonl
   ```

4. Display table format:

```
## Invoice List {filter description}

| # | ID | Status | Project | Client | Amount | Due Date | Invoice# |
|---|-----|--------|---------|--------|--------|----------|----------|
| 1 | inv-2026-03-23-001 | sent | PROP-0324 | PROP Pty Ltd | $5,500.00 AUD | 2026-04-22 | INV-0042 |
| 2 | inv-2026-03-22-001 | paid | ACME-0401 | Acme Corp | $2,200.00 AUD | 2026-03-20 | INV-0038 |

{N} invoices shown.
```

5. Show counts at bottom.

---

## MODE 3: Mark Paid (mark-paid/paid text-or-number)

Mark an invoice as paid.

1. Read `data/invoices/active.jsonl`
2. Get outstanding invoices sorted same as Mode 1 (overdue first, then sent, draft, reminder):
   ```bash
   TODAY=$(date +%Y-%m-%d)
   jq -s --arg today "$TODAY" '
     [.[] | select(.status != "paid" and .status != "written-off")]
     | sort_by(
       (if .status == "sent" and .due_date != null and .due_date < $today then 0
        elif .status == "sent" then 1
        elif .status == "draft" then 2
        elif .status == "disputed" then 3
        else 4 end),
       (if .due_date == null then "9999-99-99" else .due_date end)
     )
   ' data/invoices/active.jsonl
   ```
3. Parse argument after "mark-paid " or "paid ":
   - If purely numeric: match by position in the sorted outstanding list (1-indexed)
   - Otherwise: case-insensitive substring match against `client_name` or `project_code`

4. **If single match found:**
   - Get current timestamp:
     ```bash
     NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
     ```
   - Update the record in active.jsonl -- set `status` to `"paid"` and `completed_at` to now:
     ```bash
     INV_ID="{matched id}"
     NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
     jq "if .id == \"$INV_ID\" then .status = \"paid\" | .completed_at = \"$NOW\" else . end" data/invoices/active.jsonl | jq -c '.' > data/invoices/active.jsonl.tmp && mv data/invoices/active.jsonl.tmp data/invoices/active.jsonl
     ```
   - Log to data/feed.jsonl:
     ```bash
     NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
     jq -n -c \
       --arg ts "$NOW" \
       --arg client "{client_name}" \
       --arg project "{project_code}" \
       --arg amount "{amount}" \
       '{ts: $ts, type: "invoice", summary: ("Marked invoice paid: " + $client + " " + $project + " $" + $amount), level: "info", trigger: "manual", details: {invoice_id: "{INV_ID}", client: $client, project_code: $project}}' >> data/feed.jsonl
     ```
   - Display: "Paid: {project_code} | {client_name} | ${amount} {currency}"

5. **If no match:** "No outstanding invoice matching '{input}'. Run `/invoice` to see your list."

6. **If multiple matches:** Show the matching invoices and ask to be more specific.

7. **Trigger Post-Mutation** (see Post-Mutation section below).

---

## MODE 4: Xero Sync (sync)

Pull invoice data from Xero and update local records.

**IMPORTANT:** If the Xero MCP server is not configured, display a helpful error instead of crashing:

```
Xero MCP server is not configured. To set up:

1. Go to developer.xero.com -> My Apps -> New App
2. Create a Custom Connection app (or standard OAuth app)
3. Select scopes: accounting.invoices.read, accounting.contacts.read
4. Complete the authorisation flow
5. Add to ~/.claude.json mcpServers section:
   {
     "xero": {
       "type": "stdio",
       "command": "npx",
       "args": ["-y", "@xeroapi/xero-mcp-server@latest"],
       "env": {
         "XERO_CLIENT_ID": "<your-client-id>",
         "XERO_CLIENT_SECRET": "<your-client-secret>"
       }
     }
   }
6. Restart Claude Code

Run /invoice sync again after configuration.
```

**When Xero MCP is available:**

1. Call `mcp__xero__list-invoices` to get all invoices with status AUTHORISED (outstanding)
2. Also call for status DRAFT and PAID (last 30 days for paid) if needed
3. For each Xero invoice:
   a. Map Xero status to local status:
      - DRAFT/SUBMITTED -> "draft"
      - AUTHORISED -> "sent"
      - PAID -> "paid"
      - VOIDED -> "written-off"
      - DELETED -> skip/remove
   b. Check if `xero_invoice_id` already exists in local NDJSON:
      ```bash
      XERO_ID="{InvoiceID from Xero}"
      EXISTING=$(jq -r "select(.xero_invoice_id == \"$XERO_ID\") | .id" data/invoices/active.jsonl 2>/dev/null | head -1)
      ```
   c. If exists: update status, amount, amount_paid, due_date, invoice_number from Xero data:
      ```bash
      jq "if .xero_invoice_id == \"$XERO_ID\" then
        .status = \"$LOCAL_STATUS\" |
        .amount = $AMOUNT |
        .amount_paid = $AMOUNT_PAID |
        .due_date = \"$DUE_DATE\" |
        .invoice_number = \"$INV_NUM\"
      else . end" data/invoices/active.jsonl | jq -c '.' > data/invoices/active.jsonl.tmp && mv data/invoices/active.jsonl.tmp data/invoices/active.jsonl
      ```
   d. If not exists: create new record with trigger "xero-sync", mapping:
      - Contact.Name -> client_name
      - Reference -> project_code (if matches pattern `[A-Z]{2,5}-\d{2,5}`, per research)
      - Total -> amount
      - TotalTax -> tax_amount
      - DueDate -> due_date
      - InvoiceNumber -> invoice_number
      - AmountPaid -> amount_paid
      - CurrencyCode -> currency
      - FullyPaidOnDate -> completed_at (if paid)

      Generate ID: `inv-{YYYY-MM-DD}-{NNN}` (next available for today)

      ```bash
      TODAY=$(date +%Y-%m-%d)
      EXISTING_COUNT=$(jq -r '.id' data/invoices/active.jsonl 2>/dev/null | grep "inv-$TODAY" | wc -l | tr -d ' ')
      NEXT=$(printf "%03d" $((EXISTING_COUNT + 1)))
      INV_ID="inv-${TODAY}-${NEXT}"
      NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')

      # Check if Reference looks like a project code
      PROJECT_CODE="null"
      if echo "$REFERENCE" | grep -qE '^[A-Z]{2,5}-[0-9]{2,5}$'; then
        PROJECT_CODE="\"$REFERENCE\""
      fi

      jq -n -c \
        --arg id "$INV_ID" \
        --arg ts "$NOW" \
        --arg status "$LOCAL_STATUS" \
        --arg client "$CONTACT_NAME" \
        --argjson amount "$AMOUNT" \
        --arg currency "$CURRENCY_CODE" \
        --argjson tax "$TAX_AMOUNT" \
        --arg due "$DUE_DATE" \
        --arg desc "Synced from Xero" \
        --arg inv_num "$INV_NUM" \
        --argjson project_code "$PROJECT_CODE" \
        --arg xero_id "$XERO_ID" \
        --argjson amount_paid "$AMOUNT_PAID" \
        --arg completed_at "$COMPLETED_AT" \
        '{
          id: $id, ts: $ts, status: $status,
          client_name: $client, amount: $amount, currency: $currency,
          tax_amount: $tax, due_date: (if $due == "" or $due == "null" then null else $due end),
          description: $desc,
          invoice_number: (if $inv_num == "" then null else $inv_num end),
          po_number: null,
          project_code: $project_code,
          payment_terms: null,
          source_email_id: null,
          xero_invoice_id: $xero_id,
          trigger: "xero-sync",
          amount_paid: $amount_paid,
          completed_at: (if $completed_at == "" or $completed_at == "null" then null else $completed_at end)
        }' >> data/invoices/active.jsonl
      ```

4. Report sync results:
   ```
   Synced {N} invoices from Xero. {N} new, {N} updated, {N} overdue.
   ```
5. **Trigger Post-Mutation** (see Post-Mutation section below).

---

## MODE 5: Overdue Invoices (overdue)

Show only overdue invoices with emphasis.

1. Read `data/invoices/active.jsonl`
2. Filter: status=="sent" AND due_date is not null AND due_date < today:
   ```bash
   TODAY=$(date +%Y-%m-%d)
   jq -s --arg today "$TODAY" '
     [.[] | select(.status == "sent" and .due_date != null and .due_date < $today)]
     | sort_by(.due_date)
   ' data/invoices/active.jsonl
   ```
3. Calculate days overdue for each:
   ```bash
   # For each record, compute days between today and due_date
   # days_overdue = (today_epoch - due_date_epoch) / 86400
   ```
4. Display with red emphasis and days-overdue count:

```
## Overdue Invoices

  1. [!] PROP-0324 | PROP Pty Ltd | $5,500.00 AUD | Due 2026-03-15 (8 days overdue) | INV-0042
  2. [!] ACME-0401 | Acme Corp | $2,200.00 AUD | Due 2026-03-20 (3 days overdue)

Total overdue: $7,700.00 AUD
{N} overdue invoices. Run /invoice paid N to mark paid, /invoice sync to refresh from Xero.
```

5. If no overdue invoices: "No overdue invoices. All sent invoices are within their due dates."

6. Show total overdue amount at the bottom.

---

## MODE 6: Link Reminder to Xero Invoice (link reminder-number xero-invoice-id)

Link an email-detected reminder to a real Xero invoice.

1. Parse arguments after "link ": first argument is position number (in outstanding list), second is the Xero invoice ID (UUID)
2. Get outstanding invoices sorted same as Mode 1
3. Find the reminder record by position
4. Validate it is a "reminder" status record. If not: "Invoice #{N} is not a reminder (status: {status}). Only reminders can be linked."
5. Set `xero_invoice_id` on the record:
   ```bash
   INV_ID="{matched id}"
   XERO_ID="{provided xero invoice id}"
   jq "if .id == \"$INV_ID\" then .xero_invoice_id = \"$XERO_ID\" else . end" data/invoices/active.jsonl | jq -c '.' > data/invoices/active.jsonl.tmp && mv data/invoices/active.jsonl.tmp data/invoices/active.jsonl
   ```
6. Optionally: If Xero MCP is available, call `mcp__xero__list-invoices` filtered by the invoice ID to get current status, amount, due date. Update the local record to match Xero data and change status from "reminder" to the mapped Xero status.
7. Log to data/feed.jsonl:
   ```bash
   NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
   jq -n -c \
     --arg ts "$NOW" \
     --arg client "{client_name}" \
     --arg xero_id "$XERO_ID" \
     '{ts: $ts, type: "invoice", summary: ("Linked reminder to Xero invoice: " + $client), level: "info", trigger: "manual", details: {invoice_id: "{INV_ID}", xero_invoice_id: $xero_id}}' >> data/feed.jsonl
   ```
8. Display: "Linked: {client_name} -> Xero invoice {xero_invoice_id}"
9. **Trigger Post-Mutation** (see Post-Mutation section below).

---

## MODE 7: Create New Invoice (natural language)

Parse natural language input and create a new invoice record.

### Step 1: Parse $ARGUMENTS

Extract structured data from the natural language input. Remove matched tokens from the text.

- **Client name:** First unrecognized text segment (not matched by other patterns)
- **Amount:** `$5500`, `$5,500`, `5500 AUD`, `$2,200.00` patterns. Extract number and optional currency.
  ```bash
  # Extract amount patterns
  AMOUNT=$(echo "$ARGS" | grep -oE '\$[0-9,]+(\.[0-9]{2})?' | head -1 | tr -d '$,')
  if [ -z "$AMOUNT" ]; then
    AMOUNT=$(echo "$ARGS" | grep -oE '[0-9,]+(\.[0-9]{2})?\s*(AUD|USD|NZD|GBP|EUR)' | head -1 | grep -oE '[0-9,.]+')
  fi
  ```
- **Currency:** "AUD", "USD", "NZD", "GBP", "EUR" (default AUD per D-07). Extract if present.
  ```bash
  CURRENCY=$(echo "$ARGS" | grep -oE '\b(AUD|USD|NZD|GBP|EUR)\b' | head -1)
  if [ -z "$CURRENCY" ]; then CURRENCY="AUD"; fi
  ```
- **Due date:** `by {date}`, `due {date}`, `net 30` (compute from today + 30 days), `net 14`, `net 7`. Parse relative dates:
  - "tomorrow" -> tomorrow's date
  - "today" -> today's date
  - Day names ("Friday", "Monday") -> next occurrence
  - "net 30" -> today + 30 days
  - "net 14" -> today + 14 days
  - ISO dates ("2026-03-28") -> use directly
  ```bash
  # Extract "net N" payment terms
  NET_DAYS=$(echo "$ARGS" | grep -oE 'net\s*[0-9]+' | grep -oE '[0-9]+')
  if [ -n "$NET_DAYS" ]; then
    DUE_DATE=$(date -v+${NET_DAYS}d +%Y-%m-%d)
    PAYMENT_TERMS="net $NET_DAYS"
  fi
  ```
- **Project code:** Pattern matching `[A-Z]{2,5}-\d{2,5}` per D-08
  ```bash
  PROJECT_CODE=$(echo "$ARGS" | grep -oE '[A-Z]{2,5}-[0-9]{2,5}' | head -1)
  ```
- **Description:** Remaining text after extraction of amount, currency, due date, project code. Trim whitespace.

### Step 2: Generate ID

```bash
TODAY=$(date +%Y-%m-%d)
EXISTING=$(jq -r '.id' data/invoices/active.jsonl 2>/dev/null | grep "inv-$TODAY" | wc -l | tr -d ' ')
NEXT=$(printf "%03d" $((EXISTING + 1)))
INV_ID="inv-${TODAY}-${NEXT}"
```

### Step 3: Get current timestamp

```bash
NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
```

### Step 4: Create record

Create a JSON object with ALL 18 schema fields from `schemas/invoice-record.json`:

- `id`: generated invoice ID
- `ts`: current ISO 8601 timestamp with timezone offset
- `status`: `"draft"`
- `client_name`: extracted client name
- `amount`: extracted amount or `null`
- `currency`: extracted currency or `"AUD"` (default)
- `tax_amount`: `null` (computed by Xero, not locally)
- `due_date`: extracted date or `null`
- `description`: remaining description text or `null`
- `invoice_number`: `null` (assigned by Xero later)
- `po_number`: `null`
- `project_code`: extracted project code or `null`
- `payment_terms`: extracted terms (e.g., "net 30") or `null`
- `source_email_id`: `null`
- `xero_invoice_id`: `null`
- `trigger`: `"manual"`
- `amount_paid`: `null`
- `completed_at`: `null`

Build using jq:
```bash
jq -n -c \
  --arg id "$INV_ID" \
  --arg ts "$NOW" \
  --arg client "$CLIENT_NAME" \
  --argjson amount "${AMOUNT:-null}" \
  --arg currency "$CURRENCY" \
  --arg due_date "$DUE" \
  --arg desc "$DESCRIPTION" \
  --arg project_code "$PROJECT_CODE" \
  --arg payment_terms "$PAYMENT_TERMS" \
  '{
    id: $id, ts: $ts, status: "draft",
    client_name: $client,
    amount: $amount,
    currency: $currency,
    tax_amount: null,
    due_date: (if $due_date == "" or $due_date == "null" then null else $due_date end),
    description: (if $desc == "" then null else $desc end),
    invoice_number: null,
    po_number: null,
    project_code: (if $project_code == "" then null else $project_code end),
    payment_terms: (if $payment_terms == "" then null else $payment_terms end),
    source_email_id: null,
    xero_invoice_id: null,
    trigger: "manual",
    amount_paid: null,
    completed_at: null
  }' >> data/invoices/active.jsonl
```

### Step 5: Log to activity feed

```bash
jq -n -c \
  --arg ts "$NOW" \
  --arg client "$CLIENT_NAME" \
  --arg project "$PROJECT_CODE" \
  --argjson amount "${AMOUNT:-null}" \
  '{ts: $ts, type: "invoice", summary: ("Created invoice: " + $client + (if $project != "" then " " + $project else "" end) + (if $amount != null then " $" + ($amount | tostring) else "" end)), level: "info", trigger: "manual", details: {invoice_id: "'"$INV_ID"'", client: $client, project_code: (if $project != "" then $project else null end)}}' >> data/feed.jsonl
```

### Step 6: Display result

```
Created: {project_code} | {client_name} | ${amount} {currency} | Due: {due_date} | Status: draft
```

If no amount: show "No amount yet" instead of dollar value.
If no due date: show "No due date" instead.
If no project code: omit project code section.

### Step 7: Trigger Post-Mutation (see Post-Mutation section below).

---

## Post-Mutation: Dashboard Rebuild

After any mode that modifies data (Modes 3, 4, 6, 7), rebuild dashboard JSON and commit:

```bash
bash scripts/build-dashboard-data.sh
git add docs/feed.json docs/tasks.json docs/triage.json docs/todos.json docs/invoices.json docs/briefing.json data/invoices/ data/feed.jsonl
git commit -m "data: rebuild dashboard data after invoice update"
```

If the commit fails (nothing changed), continue without error.
