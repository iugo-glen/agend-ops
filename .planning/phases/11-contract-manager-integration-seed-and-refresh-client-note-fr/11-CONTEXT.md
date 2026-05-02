# Phase 11: Contract Manager Integration - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate the Contract Manager MCP (`https://contracts.agend.info/api/mcp`) into the Phase 10 vault-writer pipeline so client notes acquire **CM-sourced frontmatter** (`deployed_modules`, `contract_start`, `contract_end`, `primary_contact`, `sites[]`), **two new managed body sections** (Sites + Usage), **contract events in the Activity Log** (renewals, signings, terminations), and **CM-tracked invoices appended to the Activity Log** alongside the existing Phase 7 invoice records.

**In scope:**
- Live MCP read on every `/sync-obsidian` run with retry+cache fallback
- 5 new frontmatter keys sourced from CM `get_client_summary`
- 2 new managed body sections: Sites + Usage
- Contract events from CM `list_contracts_expiring` rendered as Activity Log entries (D-12 line shape, new emoji 📄)
- CM-tracked invoices (CM `list_overdue_invoices`) appended to the Activity Log alongside local invoice records
- Missing-CM-data TODO surface (auto-cleared as CM data lands)
- Cache layer at `data/.cm-cache.json` for failure-mode fallback only
- Extension of vault_writer.py — same module, mirrors Phase 10 marker discipline

**Out of scope (deferred to later phases — see Deferred Ideas):**
- Bidirectional invoice writes back to CM (data/invoices/ stays canonical per Phase 7)
- Contract creation/edit from Agend Ops (CM dashboard owns the write surface)
- Module usage telemetry (per-module activity, last-login, version) — needs CM data source first
- DataView portfolio dashboard inside Obsidian — earliest fit is post-Phase 11 once CM fields populate
- CM webhook → real-time push (current model is pull-on-sync)

</domain>

<decisions>
## Implementation Decisions

### MCP integration (Area 1)
- **D-A1: Connection model — live MCP read per sync run.** vault_writer (or a small Python wrapper module) calls the CM MCP via JSON-RPC 2.0 over POST during every `/sync-obsidian` invocation. **No primary local mirror.** This contradicts the standard "data/ is source of truth" pattern by design — CM IS the source of truth for the 5 frontmatter fields and contract events. The local cache (D-A3) is fallback only, never the read path.
- **D-A2: Auth — MCP-scoped static API key.** The CM endpoint accepts `Authorization: Bearer cm_live_...` OR `X-API-Key: cm_live_...` headers (verified at `~/work/contract-manager/src/app/api/mcp/route.ts:42-83`). Glen mints a key from the CM dashboard at `/settings/mcp`, stores it on Coolify as the env var `CONTRACT_MANAGER_API_KEY`, and vault_writer sends it as `Authorization: Bearer ${CONTRACT_MANAGER_API_KEY}`. Keys are MCP-scoped (`verifyApiKeyFull(apiKey, 'mcp')`), per-key rate limited, and audit-logged on the CM side.
- **D-A3: Failure mode — retry with exponential backoff, fall back to cache, log warning.** On a CM request:
  1. Retry 3 times with 1s → 5s → 30s backoff (catches transient blips automatically).
  2. On exhaustion: read last-known-good response from `data/.cm-cache.json`.
  3. Stamp `cm_data_stale_since: <ts-of-last-fresh-read>` in the affected note's frontmatter.
  4. Append a `system`/`warning` (not `critical`) entry to `data/feed.jsonl` per `schemas/feed-entry.json`.
  5. Continue the rest of the sync — never block the entire vault on CM downtime.
  Phase 10's D-08a (marker errors → `critical`) is unchanged. CM staleness is a `warning`, not a `critical`.

### Frontmatter merge + missing-data behavior (Area 2)
- **D-B1: Empty scalar CM fields → empty string.** `contract_start: ""`, `contract_end: ""`, `primary_contact: ""` when CM has no value. Glen's chosen behavior: explicit signal that we tried CM and it had no value, distinct from "key not yet attempted".
- **D-B2: Empty array CM fields → empty array.** `deployed_modules: []`, `sites: []` when CM returns an empty array. YAML-idiomatic, DataView-queryable. The "empty string" rule from D-B1 only applies to scalars.
- **D-B3: Missing-CM-data TODO managed section.** New top-level managed section `<!-- CM-TODOS-START -->` / `<!-- CM-TODOS-END -->` between Overview and Open Items. Auto-rebuilt every sync. Lists missing fields as bullets:
  ```markdown
  ## TODO: Missing CM Data
  - `contract_start` — set in Contract Manager
  - `primary_contact` — set in Contract Manager
  ```
  When CM has values for all fields: section body is `_(no missing CM data)_`. Phase 10 D-08/D-08a marker discipline applies — malformed markers ABORT and log critical. Phase 10 D-14/D-16 idempotency continues to hold (regenerate-from-full produces byte-identical content modulo timestamps).

### Sites + Usage section design (Area 3)
- **D-C1: Two new top-level managed sections.** Sites and Usage are NOT sub-sections inside Overview (which would conflict with Phase 10 D-07 Glen-owned separation). They sit between Open Items and Activity Log. Updated note structure:
  1. Frontmatter (Phase 10 D-09 + 5 new keys)
  2. Overview (Glen-owned, Phase 10 D-07)
  3. CM-TODOS (managed, D-B3 — only when missing data)
  4. Open Items (managed, Phase 10)
  5. **Sites** (managed, NEW — D-C2)
  6. **Usage** (managed, NEW — D-C3)
  7. Activity Log (managed, Phase 10 — extended per D-D2)
  8. Decisions (Glen-owned, Phase 10)
- **D-C2: Sites section sourced from CM `get_client_summary` `sites[]` field.** Per-site rendering shows site URL, environment (prod/staging/etc), modules deployed at that site, and current status. When CM returns `sites: []`: render `_(no sites recorded in CM)_`.
- **D-C3: Usage section = consultant utilization.** Sources: CM `get_utilization_summary` and `get_capacity_summary` for this client. Render fields: hours billed this month, hours YTD, % of contracted capacity, upcoming committed hours. The "how am I tracking against the contract" lens, not module usage telemetry. Module usage is deferred (see Deferred Ideas).

### Invoice reconciliation (Area 4)
- **D-D1: data/invoices/ stays canonical. CM is read-only.** Phase 7 unchanged: `/invoice` slash command, `data/invoices/active.jsonl` schema, dashboard "Invoices" tab (Phase 8 DASH-03), and triage auto-detection (Phase 7 INV-03) all keep behaving as today. **No write tools needed from CM.** Phase 11 only READS from CM via `list_overdue_invoices` and merges those invoices into the Activity Log alongside local ones.
- **D-D2: CM-tracked invoices appear in Activity Log.** Same D-12 line shape as Phase 10 invoices: `### [YYYY-MM-DD HH:MM] 💰 {summary}`. Source-tagged in the detail block: `> source: contract-manager` (vs the implicit "local" for Phase 7 invoices). Dedup against `data/invoices/active.jsonl` by invoice number — when both sources have the same invoice, local wins (Claude's discretion on the matching algorithm; default to invoice-number string equality with case-fold).

### Contract events (carried-forward decision from Phase 10 D-12)
- **D-E1: Contract events in Activity Log use D-12 line shape with new emoji 📄.** Source: CM `list_contracts_expiring` for upcoming events. Event types: `renewal_due`, `signing_pending`, `terminated`, `expired`. Examples:
  ```
  ### [2026-06-15 00:00] 📄 Contract renewal due — Property Council Australia (12-month MSA)
  > source: contract-manager
  > [Open in Contract Manager](https://contracts.agend.info/contracts/{id})
  ```
  Phase 10 emoji set is now: 📧 triage, ✅ task, 💰 invoice, 📄 contract.

### Caching + cache file shape (D-A3 implementation contract)
- **D-F1: `data/.cm-cache.json` schema.** Single JSON file, not NDJSON. Schema: `{ "<client_domain>": { "fetched_at": "<iso-ts>", "client_summary": {...}, "utilization_summary": {...}, "capacity_summary": {...}, "expiring_contracts": [...] }, ... }`. Updated atomically via tempfile+rename per Phase 10 Pattern 1. **Not committed to git** — `.gitignore` extension required (cache is per-host runtime state, like Coolify's PID files). Equivalent on the Mac Studio is unused (Mac runs `project-to-icloud` which does NOT call CM).

### Claude's Discretion
- HTTP client library choice (urllib stdlib vs `requests` add to requirements.txt — pick the lower-dependency option that supports retries cleanly)
- JSON-RPC client wrapper structure (single function vs class)
- Exact retry timing (D-A3 specifies 1s/5s/30s — Claude may tune within reason)
- Cache file lock strategy if any (Coolify is single-writer per D-13(4))
- Invoice dedup algorithm refinement beyond invoice-number equality (e.g., case-fold, trim, prefix-strip — pick a robust default)
- Whether contract events come from `list_contracts_expiring` polled per-sync OR a future CM webhook + new tool (v1: poll per-sync)
- Frontmatter render order — D-09 4 keys first, then 5 new CM keys in some sensible order (chronological? logical grouping?)
- Test scaffolding additions (extending `TestProjection`, adding `TestContractMerge`, mocking the CM HTTP layer)
- How `cm_data_stale_since` is cleared once a fresh read succeeds
- Whether the `## TODO: Missing CM Data` section's body bullets link to the CM dashboard for one-click fix

</decisions>

<specifics>
## Specific Ideas

- iPhone glance pattern: open client note → see Frontmatter (status, contract dates) → scroll → see Overview (Glen's notes) → see CM-TODOS (action items if any) → see Open Items → see Sites (which envs) → see Usage (am I tracking against capacity) → see Activity Log (what just happened)
- Contract events should feel different from triage emails — that's why they get their own emoji (📄) instead of overloading 📧 or 💰
- Phase 7 and Phase 11 invoice paths should both render to the Activity Log without any visible difference to Glen UNTIL he taps in for detail (then the `source:` line discloses origin) — preserves the "one log per client" UX
- The CM-TODOS section should self-clear, not accumulate — Glen sees the section disappear when he completes the data, no manual cleanup
- API key rotation should be a one-liner: edit env var on Coolify, restart, done. No code changes.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context (carry-forward from Phase 10)
- `.planning/PROJECT.md` — Core value, data ownership, privacy constraints
- `.planning/REQUIREMENTS.md` — INTL-01 (Context accumulation, mapped to Phase 10 + extended by Phase 11)
- `.planning/STATE.md` — Prior phase decisions and accumulated context
- `.planning/phases/10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli/10-CONTEXT.md` — D-04..D-18 carry forward in full. Specifically: D-04/D-05 routing, D-07 section order, D-08/D-08a marker discipline (applies to all new managed sections — CM-TODOS, Sites, Usage), D-09 frontmatter v1 (5 new keys extend it), D-12 Activity Log line shape (contract events + CM invoices follow it), D-14/D-16 idempotency
- `.planning/phases/10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli/10-VERIFICATION.md` — Phase 10 must-haves all PASSED; Phase 11 builds on a verified foundation
- `.planning/phases/07-invoice-tracking/07-CONTEXT.md` — invoice schema and `/invoice` flow (kept canonical per D-D1)

### Contract Manager MCP (NEW — Glen owns this codebase at `~/work/contract-manager`)
- `~/work/contract-manager/src/app/api/mcp/route.ts` — Auth model (Bearer / X-API-Key), JSON-RPC 2.0 dispatch, rate limit, audit logging. **Read this before writing any MCP client code.**
- `~/work/contract-manager/src/lib/mcp/types.ts` — JsonRpcRequest/Response/ErrorCode contracts
- `~/work/contract-manager/src/lib/mcp/server.ts` — Server-side handler (informs what tool args/responses look like)
- `~/work/contract-manager/src/lib/mcp/tools/index.ts` — Full tool registry. 15 tools across 5 categories.
- `~/work/contract-manager/src/lib/mcp/tools/lookups.ts` — `search_clients`, `get_client_summary` (frontmatter source)
- `~/work/contract-manager/src/lib/mcp/tools/operations.ts` — `list_contracts_expiring` (Activity Log events), `get_capacity_summary`, `get_utilization_summary` (Usage section)
- `~/work/contract-manager/src/lib/mcp/tools/financial.ts` — `list_overdue_invoices` (Activity Log invoice merge per D-D1)
- `~/work/contract-manager/.env.example` — env var conventions (informs how Coolify exposes `CONTRACT_MANAGER_API_KEY`)
- `https://contracts.agend.info/settings/mcp` — Glen's UI for minting/rotating MCP API keys

### Existing infrastructure (extend, don't reinvent)
- `scripts/lib/vault_writer.py` — Phase 10 sync engine. Phase 11 extends `render_frontmatter`, adds `render_sites`, `render_usage`, `render_cm_todos`, threads CM client through `_gather_events`. **Do NOT rewrite — extend.**
- `scripts/lib/vault_writer.py:1077-1092` — Per-file try/except pattern for `_update_frontmatter_last_synced`. Mirror this for CM-fetch failures within `run_backfill`.
- `scripts/lib/vault_writer.py:777-788` — `_acquire_projection_lock` fcntl pattern. Reuse for any new daemon-side concurrency if needed.
- `scripts/sync-obsidian.sh` — Linux flock wrapper. Phase 11 may need to extend the no-op-delta gate to also consider CM data freshness (Claude's discretion).
- `scripts/tests/test_vault_writer.py` — 25 tests today. Phase 11 adds: `TestContractMerge` (CM tools mocked), `TestCmCacheFallback`, `TestCmTodosSection`, `TestSitesSection`, `TestUsageSection`, `TestInvoiceMerge` (Phase 7 + CM dedup).
- `data/config/clients.jsonl` — Canonical client registry (Phase 10 D-04). Phase 11 needs to map our `client_domain` → CM `client_id` — likely via a one-time mapping run that calls `search_clients` per client and caches the IDs in `clients.jsonl` itself (extension to the schema; Claude's discretion on mechanism).
- `data/invoices/active.jsonl` — Local canonical invoice store (Phase 7, kept per D-D1)
- `schemas/feed-entry.json` — `system`/`warning` and `system`/`critical` shape; CM staleness uses `warning`, marker errors use `critical`
- `schemas/triage-record.json` — referenced for understanding cross-domain data shape conventions; not modified by Phase 11

### Phase 10 implementation patterns (mirror, don't deviate)
- Atomic write: tempfile + os.replace + fsync(file) + fsync(dir) — `_atomic_write` and `replace_managed_section`
- Marker-aware splice: `replace_managed_section` for managed sections, `_extract_managed_section` for source reads
- `--feed-path` threading through every code path that may write a critical/warning entry (Phase 10 Issue 1) — extend to CM warnings
- Idempotent regenerate-from-full: every CM-sourced section must be byte-identical when re-run with same CM responses
- `MarkerError` ABORT path → critical feed entry, skip file, continue loop

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/lib/vault_writer.py` — engine, all 18 public symbols. Extend `__all__` with new render functions.
- `scripts/sync-obsidian.sh` — wrapper. May need to set `CONTRACT_MANAGER_API_KEY` env var via `set -a; source .env.local 2>/dev/null; set +a` pattern (or similar; Claude's discretion).
- `scripts/requirements.txt` — current pin: `ruamel.yaml>=0.18,<0.19`. Phase 11 may add an HTTP client lib (or stay on stdlib `urllib`).
- `data/config/clients.jsonl` — extend each client record with optional `cm_client_id` field (one-time mapping pass) so we don't `search_clients` on every sync.
- `data/.cm-cache.json` — NEW (gitignored), per D-F1
- `data/feed.jsonl` — extended via existing `append_feed_entry` for CM warnings. No schema change required.

### Established Patterns
- Single-writer discipline (Phase 10 D-13(4) + Coolify flock) — CM cache writes must respect the flock if multiple sync runs could overlap
- `--feed-path` threading at CLI boundary (Phase 10 Issue 1) — extend pattern to also cover CM warning paths
- Marker discipline (D-08/D-08a) — applies unchanged to CM-TODOS, Sites, Usage sections
- Per-file try/except in `run_projection` (Phase 10 review fix) — mirror for `run_backfill` when CM fetch fails for one client; do not halt entire backfill
- Atomic NDJSON append via `append_feed_entry` open(...,'a') ≤ PIPE_BUF — applies to CM warning entries

### Integration Points
- `vault-build/Clients/*.md` — Coolify writes (Phase 10 D-02). Phase 11 adds 3 new managed sections (CM-TODOS, Sites, Usage) and 5 frontmatter keys; transport rail unchanged.
- `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AgendOps/Clients/*.md` — Mac daemon's projection target (Phase 10 D-03). Mac daemon does NOT call CM; it only projects what's already in `vault-build/`.
- `mac/vault-sync-watcher.sh` — UNCHANGED for Phase 11 (Mac is read-only on CM data, runs `project-to-icloud` only)
- `scripts/sync-obsidian.sh` — UNCHANGED interface but vault_writer's CLI gains a CM-fetch step before the existing pipeline
- `.claude/commands/sync-obsidian.md` — minimal doc-only update to mention CM fields appearing
- `.claude/commands/triage-inbox.md`, `task.md`, `invoice.md` — UNCHANGED (their hook still calls `bash scripts/sync-obsidian.sh --incremental || true`; vault_writer's internal CM step is invisible to them)
- `.gitignore` — add `data/.cm-cache.json`

### Network / runtime concerns
- Coolify is a Linux container. `CONTRACT_MANAGER_API_KEY` env var injected via Coolify's UI. No KMS / secrets manager in scope for v1.
- CM endpoint is HTTPS. Cert validation via Python's default `ssl` module is acceptable.
- CM enforces rate limits per API key (`RATE_LIMITS.EXTERNAL_API` in CM source). Phase 11's per-sync read pattern issues at most ~30 requests per backfill (one `get_client_summary` per client + a few list-style calls). Well under any reasonable limit but worth budgeting for.
- CM is owned by Glen — both production failures and dev-environment access are within his control. No external SLA to negotiate.

</code_context>

<deferred>
## Deferred Ideas

- **Bidirectional invoice writes back to CM** — D-D1 keeps data/invoices/ canonical. If Glen later wants `/invoice mark-paid` to also update CM, that's a separate phase requiring CM write tools (`create_invoice`, `mark_paid`). Tracked but not in v1.
- **Module usage telemetry in Usage section** — current D-C3 limits Usage to consultant utilization. Per-module activity (last login, version deployed, feature usage) needs a CM data source first. Future phase once CM tracks this.
- **CM webhook → real-time push** — current model is pull-on-sync. A CM webhook would let CM events appear in the Activity Log within seconds of happening rather than within seconds of the next sync. Future phase; requires CM webhook infrastructure.
- **One-click CM data fix from CM-TODOS bullets** — Claude's discretion currently. Future enhancement: each TODO bullet links directly to the CM dashboard's "edit client" page for the missing field.
- **DataView portfolio dashboard** — Already noted in Phase 10 deferred ideas. Earliest fit is post-Phase 11 once `deployed_modules`, `contract_end`, `cm_data_stale_since` populate.
- **Mapping `client_domain` → `cm_client_id` automation** — Claude will likely add a one-time mapping pass per D-A2/D-A3 implementation. If CM IDs change or new clients arrive frequently, automate the mapping refresh as a Phase 11.x.
- **Backing the canonical vault to git** — already in Phase 10 deferred ideas. Same logic applies post-Phase 11.

</deferred>

---

*Phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr*
*Context gathered: 2026-05-02*
