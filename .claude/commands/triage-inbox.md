---
description: Scan Gmail inbox and categorize emails into priority buckets
allowed-tools: Read, Write, Edit, Bash(jq *), Bash(date *), mcp__hardened-workspace__*
---

Scan Glen's Gmail inbox, categorize emails by priority, generate draft replies for urgent/client emails, detect action items, and display a formatted triage briefing.

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
