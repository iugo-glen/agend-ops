---
description: Scan Gmail inbox and categorize emails into priority buckets
allowed-tools: Read, Write, Edit, Bash(jq *), Bash(date *), mcp__hardened-workspace__*
---

PHASE 2 STUB -- This command will be fully implemented in Phase 2 (Email Triage).

When Phase 2 is complete, this command will:
1. Use hardened-workspace MCP to read unread and recent Gmail messages
2. Categorize each email into priority buckets: urgent, needs-response, informational, low-priority
3. Surface starred emails as highest-priority "needs my action" queue
4. Detect actionable items (contracts, invoices, meeting requests, deadlines)
5. Write triage results to data/triage/{timestamp}.jsonl
6. Log a feed entry to data/feed.jsonl
7. Display a summary of the triage results

For now, display this message:
"Triage inbox is not yet implemented. It will be available after Phase 2 (Email Triage) is complete.
Run /status to see current system state."
