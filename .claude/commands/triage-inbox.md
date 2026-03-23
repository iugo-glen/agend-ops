---
description: Scan Gmail inbox and categorize emails into priority buckets
allowed-tools: Read, Write, Edit, Bash(jq *), Bash(date *), Bash(wc *), mcp__hardened-workspace__*, Task, Bash(bash scripts/*), Bash(git *)
---

Scan Glen's Gmail inbox, categorize emails by priority, generate draft replies for urgent/client emails, detect action items, auto-queue actionable items as pending tasks, and display a formatted triage briefing.

## Execution

1. **Record start time** for duration tracking: note the current time before dispatching.

2. **Dispatch to the email-scanner subagent** using the Task tool:
   - Agent: `email-scanner`
   - Instruction: "Run a full inbox triage scan. Follow your system prompt step by step. Return the formatted briefing summary when complete."
   - The email-scanner subagent handles all triage logic internally:
     - Loads client domains from `data/config/clients.jsonl`
     - Scans Gmail inbox (last 24 hours) via hardened-workspace MCP
     - Classifies emails using rules + AI hybrid approach
     - Surfaces starred emails as highest-priority items
     - Detects actionable items (contracts, invoices, meetings, deadlines)
     - Generates Gmail draft replies for urgent and known-client emails
     - Writes triage results to `data/triage/{timestamp}.jsonl`
     - Logs a summary entry to `data/feed.jsonl`
     - Returns a formatted briefing

3. **Display the subagent's returned briefing** directly -- it is already formatted as a structured triage summary with priority buckets, action items, and draft status.

4. **Post-triage suggestions:**
   - After the briefing, suggest: "Run `/feed` to see the logged triage entry, or review your Gmail Drafts folder to approve/edit draft replies."
   - If the subagent detected unknown frequent sender domains that might be clients, surface them: "Potential new client domains detected: {domains}. Add to `data/config/clients.jsonl` if these are clients."

5. **Auto-queue detected action items as pending tasks:**

   Read the triage output file that the email-scanner subagent just created (the most recent file in `data/triage/`):

   ```bash
   LATEST_TRIAGE=$(ls -t data/triage/*.jsonl 2>/dev/null | head -1)
   ```

   For each triage record where `action_items` array is non-empty AND `action_type` is not `"none"`:

   a. **Check for duplicates:** Search `data/tasks/active.jsonl` for any existing task with the same `source_email` (matching the triage record's `message_id`). If found, skip to avoid re-queuing on re-triage:
      ```bash
      jq -r 'select(.source_email == "{message_id}") | .id' data/tasks/active.jsonl 2>/dev/null
      ```

   b. **Invoice auto-queue path:** If `action_type == "invoice"`, create an invoice reminder record instead of a task:

      i. **Check for invoice duplicates:** Search `data/invoices/active.jsonl` for any existing record with the same `source_email_id` matching the triage record's `message_id`. If found, skip:
         ```bash
         jq -r "select(.source_email_id == \"{message_id}\") | .id" data/invoices/active.jsonl 2>/dev/null
         ```

      ii. **Generate invoice ID:** `inv-{YYYY-MM-DD}-{NNN}` (next available for today):
         ```bash
         EXISTING=$(jq -r '.id' data/invoices/active.jsonl 2>/dev/null | grep "inv-$(date +%Y-%m-%d)" | wc -l | tr -d ' ')
         NEXT=$(printf "%03d" $((EXISTING + 1)))
         INV_ID="inv-$(date +%Y-%m-%d)-${NEXT}"
         ```

      iii. **Best-effort field extraction** from the triage record (per D-09):
         - `client_name`: from the triage record's `client_name` field (already extracted by email-scanner)
         - `description`: from the first `action_items` entry text
         - `project_code`: attempt regex extraction `[A-Z]{2,5}-\d{2,5}` from the email subject or action_items text. Set to null if no match.
         - `amount`: attempt regex extraction of dollar amounts `\$[\d,]+(\.\d{2})?` from action_items or snippet. Set to null if no match.
         - All uncertain/unmatched fields: set to null. Per D-09, flag uncertain fields for Glen to confirm.

      iv. **Create invoice reminder record** with ALL 18 schema fields:
         ```bash
         NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
         jq -n -c \
           --arg id "$INV_ID" \
           --arg ts "$NOW" \
           --arg client "$CLIENT_NAME" \
           --arg desc "$ACTION_ITEM_TEXT" \
           --arg email_id "$MESSAGE_ID" \
           --arg project "$PROJECT_CODE" \
           '{
             id: $id, ts: $ts, status: "reminder",
             client_name: $client, amount: null, currency: "AUD",
             tax_amount: null, due_date: null,
             description: $desc,
             invoice_number: null, po_number: null,
             project_code: (if $project == "" then null else $project end),
             payment_terms: null,
             source_email_id: $email_id,
             xero_invoice_id: null, trigger: "triage-suggestion",
             amount_paid: null, completed_at: null
           }' >> data/invoices/active.jsonl
         ```

      v. **Do NOT also create a task record** for this email. Skip to the next triage record.

   c. **Map action_type to task_type** (for non-invoice action types only):
      - `"contract"` -> `"contract-review"`
      - `"meeting"` -> `"meeting-prep"`
      - `"deadline"` -> `"document-summary"`

   d. **Generate task ID:** `task-{YYYY-MM-DD}-{NNN}` (next available for today):
      ```bash
      EXISTING=$(jq -r '.id' data/tasks/active.jsonl 2>/dev/null | grep "task-$(date +%Y-%m-%d)" | wc -l | tr -d ' ')
      NEXT=$(printf "%03d" $((EXISTING + 1)))
      TASK_ID="task-$(date +%Y-%m-%d)-${NEXT}"
      ```

   e. **Create task record** with ALL 13 schema fields:
      - `id`: generated ID
      - `ts`: current ISO 8601 timestamp with timezone offset
      - `status`: `"pending"`
      - `description`: first action_item text, enriched with sender context -- e.g., `"{action_item} (from {from_name} @ {client_name})"` if client_name available, or `"(from {from_name})"` otherwise
      - `trigger`: `"triage-suggestion"`
      - `source_email`: the triage record's `message_id`
      - `task_type`: mapped from `action_type` per step (c)
      - `output_dir`: `null`
      - `source_triage`: path to the triage file just created (e.g., `"data/triage/2026-03-23T004602.jsonl"`)
      - `client_name`: from triage record if available, else `null`
      - `outcome`: `null`
      - `completed_at`: `null`
      - `draft_id`: `null`

   f. **Append to `data/tasks/active.jsonl`**

   After queuing, if any tasks were created, add to the post-triage output:

   ```
   ### Queued Tasks
   {N} action items queued as pending tasks:
   - [{id}] {description} ({task_type})
   Run /task to review and execute.
   ```

   If no tasks were queued (all duplicates or no actionable items): do not display this section.

   After queuing, if any invoice reminders were created, add to the post-triage output:

   ```
   ### Queued Invoice Reminders
   {N} invoice reminder(s) created:
   - [inv-2026-03-23-001] {client_name}: {description}
   Run /invoice to review.
   ```

   If no invoice reminders were queued (all duplicates or no invoice items): do not display this section.

6. **Rebuild dashboard data (per D-07):**
   After all triage processing and auto-queue is complete, rebuild dashboard JSON files and commit:
   ```bash
   bash scripts/build-dashboard-data.sh
   ```
   Then stage and commit the updated dashboard data files:
   ```bash
   git add docs/feed.json docs/tasks.json docs/triage.json docs/briefing.json docs/invoices.json data/invoices/
   git commit -m "data: rebuild dashboard data after triage"
   ```
   If the commit fails (nothing changed), that is fine -- continue without error.
