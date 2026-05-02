# Phase 11 Discussion Log

**Date:** 2026-05-02
**Mode:** discuss (default — 4 areas selected, ~2-3 questions per area)

This is a human-reference log of how decisions were reached. Downstream agents read CONTEXT.md, not this file.

---

## Areas selected

Glen selected all 4 gray areas: MCP integration model, Frontmatter merge + missing-data behavior, Sites + Usage section placement, Invoice reconciliation source of truth.

## Area 1: MCP integration model

**Q1 — Connection model:** Live MCP read per sync run / Scheduled mirror to local NDJSON / Hybrid / Claude Code session reads MCP
**A:** Live MCP read per sync run.
**Note:** Glen accepted the tradeoffs (CM downtime is a real failure mode; auth must work headless on Coolify). This drove follow-ups on auth and failure handling.

**Q2 — Auth (originally a multi-option question, became an investigation):** Glen asked "can you investigate? It's under ~/work/contract-manager/contract-manager"
**A (after investigation):** MCP-scoped static API key `cm_live_...`, sent as `Authorization: Bearer ...` or `X-API-Key` header. Verified at `~/work/contract-manager/src/app/api/mcp/route.ts:42-83`. Glen mints from `https://contracts.agend.info/settings/mcp` and stores on Coolify as env var `CONTRACT_MANAGER_API_KEY`. JSON-RPC 2.0 over POST, no SSE, per-key rate limited, audit-logged. 15 MCP tools available across 5 categories — most relevant for Phase 11: `search_clients`, `get_client_summary`, `list_contracts_expiring`, `list_overdue_invoices`, `get_utilization_summary`, `get_capacity_summary`.

**Q3 — Failure mode:** Fail loud / Soft-fail / Cache fallback / Retry+backoff
**A:** Cache fallback (with explicit staleness marker). Combined with Q3's recommended "retry with backoff" to lock the full failure-mode contract: 3 retries (1s, 5s, 30s) → on exhaustion, fall back to `data/.cm-cache.json` last-known-good response → stamp `cm_data_stale_since: <ts>` in frontmatter → append `system`/`warning` (not `critical`) to feed.jsonl → continue sync. Phase 10's marker-error `critical` path is unchanged.

## Area 2: Frontmatter merge + missing-data behavior

**Q1 — Empty CM fields:** Omit / Empty value / Empty string + TODO marker / Per-field strategy
**A:** Empty string + TODO marker (Glen's choice — explicit data-quality flagging).

**Q2 — TODO placement (two combined sub-questions):**
- Where: Managed section at top / Frontmatter property only / Inline callout in Overview / Both
- Empty arrays: Empty array `[]` / Omit / Empty string `""`

**A:** Managed section at top, auto-cleared when all fields populate. Empty array `[]` for arrays (since "empty string" doesn't apply cleanly to YAML arrays — Glen picked the YAML-idiomatic option, conflicting slightly with Q1's empty-string choice for scalars but semantically correct).

## Area 3: Sites + Usage section placement

**Q1 — Section design:** New top-level managed sections / Sub-sections inside Overview / Frontmatter only / One combined Account section
**A:** New top-level managed sections between Open Items and Activity Log. Cleanest separation, both auto-rebuilt from CM, marker discipline applies.

**Q2 — Usage content:** Consultant utilization / Module usage / Both / Defer Usage to Phase 11.1
**A:** Consultant utilization (hours billed / capacity / pipeline). Module usage deferred (needs CM data source first).

## Area 4: Invoice reconciliation

**Q1 — Source of truth:** CM canonical / data/invoices/ canonical with CM read-only / Bidirectional / Defer to 11.1
**A:** data/invoices/ stays canonical (Phase 7 unchanged). CM is read-only — CM-tracked invoices appear in the Activity Log alongside local ones. No write tools needed from CM.

---

## Deferred ideas captured

- Bidirectional invoice writes (Glen explicitly deferred via choice)
- Module usage telemetry in Usage section (requires CM data source first)
- CM webhook → real-time push (current model: pull-on-sync)
- One-click CM dashboard links from CM-TODO bullets (Claude's discretion)
- Mapping `client_domain` → `cm_client_id` automation refresh

## Claude's discretion items

Recorded in CONTEXT.md `### Claude's Discretion` for the planner to handle:
- HTTP client lib (urllib vs requests)
- JSON-RPC client structure
- Cache-file lock strategy
- Invoice dedup algorithm refinement
- Frontmatter render order with new keys
- How `cm_data_stale_since` gets cleared after fresh read
- One-time `client_domain` → `cm_client_id` mapping mechanism
- Test scaffolding additions (TestContractMerge, TestCmCacheFallback, etc.)

## Investigation note

The contract-manager MCP investigation was the most valuable part of this discussion — it transformed an open auth question into a locked decision. Future phases should aggressively investigate referenced repos rather than speculate about their interfaces.
