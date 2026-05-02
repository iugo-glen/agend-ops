---
phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr
verified: 2026-05-02T14:17:31Z
status: human_needed
score: 24/24 must-haves verified (code surface complete; 2 deferred items routed to human verification per Glen 2026-05-02 override)
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run mapping pass on Coolify to populate cm_client_id (Plan 02 Task 3)"
    expected: "data/config/clients.jsonl contains cm_client_id for resolvable domains; any unresolvable domains have a level=warning entry in data/feed.jsonl"
    why_human: "Requires real CM API key and Coolify host access — Glen's 2026-05-02 'don't stop! I'll add keys later' override deferred this from autonomous execution; the code path is proven by 4 mocked TestRunMapCmClients tests but the data outcome cannot be produced without the live key."
    addresses: "Plan 02 Task 3 — DEFERRED PER GLEN OVERRIDE 2026-05-02"
    runbook: ".planning/phases/11-contract-manager-integration-seed-and-refresh-client-note-fr/11-02-PLAN.md (Task 3 <how-to-verify>)"
  - test: "Run live CM-aware backfill on Coolify and verify on iPhone (Plan 04 Task 3)"
    expected: "vault-build/Clients/*.md contains CM-TODOS-START + USAGE-START markers, contract events with 📄 emoji, frontmatter populated with contract_start/contract_end/primary_contact/deployed_modules/sites=[]; no SITES section anywhere; cache file gitignored; iPhone Obsidian renders correctly"
    why_human: "Requires Coolify SSH + live CM API key + Glen's iPhone for visual verification — Glen's 2026-05-02 'don't stop! I'll add keys later' override deferred this; the code path is proven by 17 mocked-CM tests (TestContractMerge, TestInvoiceMerge via TestGatherEventsCmIntegration, TestCacheFallbackEnd2End, TestProjectionDoesNotImportCm, TestBackfillIdempotentPhase11, TestJitMapping)."
    addresses: "Plan 04 Task 3 — DEFERRED PER GLEN OVERRIDE 2026-05-02"
    runbook: ".planning/phases/11-contract-manager-integration-seed-and-refresh-client-note-fr/11-04-PLAN.md (Task 3 <how-to-verify>)"
---

# Phase 11: Contract Manager Integration — Verification Report

**Phase Goal:** Integrate the contract-manager MCP (https://contracts.agend.info/api/mcp) to seed and refresh client-note frontmatter (deployed_modules, contract_start, contract_end, primary_contact, sites[] — sites[] ships as [] only; the Sites section is deferred per D-C2-REVISED until CM exposes a per-client sites tool). Log contract events (renewals, expiries) to the Activity Log with the new 📄 emoji. Add Usage section sourced from get_sla_status per client (D-C3-REVISED). Reconcile invoice data between data/invoices/active.jsonl (canonical, unchanged) and CM list_overdue_invoices (read-only merge into Activity Log; dedup by invoice_number with case-fold + trim only).

**Verified:** 2026-05-02T14:17:31Z
**Status:** human_needed (code surface complete; 2 deferred live-CM items require Glen)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

#### Plan 11-01 (Wave 0 Bootstrap)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | schemas/feed-entry.json `level` enum accepts "warning" | VERIFIED | `enum: ['critical','warning','info','debug']` confirmed via Python json.load — all 4 values present |
| 2 | data/.cm-cache.json gitignored before any cache write | VERIFIED | `git check-ignore data/.cm-cache.json` returns the path; `data/.cm-cache.json` line found in .gitignore |
| 3 | scripts/sync-obsidian.sh fails loudly if CONTRACT_MANAGER_API_KEY unset | VERIFIED | `: "${CONTRACT_MANAGER_API_KEY:?...}"` idiom present at line 33 of sync-obsidian.sh, BEFORE REPO_ROOT assignment |
| 4 | render_frontmatter accepts new optional cm_extra and cm_stale_since args | VERIFIED | Signature at vault_writer.py:747-749: `cm_extra: dict \| None = None, cm_stale_since: str \| None = None`; default 2-arg path produces Phase 10 byte-identical output |

#### Plan 11-02 (CM Client + Mapping)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 5 | scripts/lib/cm_client.py exists with _cm_post, call_with_retry, exception classes, atomic cache helpers | VERIFIED | File exists (229 lines); all named exports importable; `RETRY_DELAYS == (1,5,30)`, `CM_ENDPOINT == "https://contracts.agend.info/api/mcp"` |
| 6 | Unit tests verify retry timing, 429 Retry-After, atomic cache write, corruption tolerance, orphan GC | VERIFIED | 14 tests across TestCmClient/TestCallWithRetry/TestCmCache/TestCmSummaryAdapter — all pass |
| 7 | vault_writer accepts --mode map-cm-clients wired to run_map_cm_clients | VERIFIED | argparse choices includes "map-cm-clients"; main() dispatches to run_map_cm_clients; lazy import `from . import cm_client as _cm` at line 1084 (inside function body) |
| 8 | Running map-cm-clients populates cm_client_id idempotently | VERIFIED (mocked) — DEFERRED LIVE | TestRunMapCmClients passes 4/4 with mocked search_clients_for_domain; live run on Coolify is deferred per Glen 2026-05-02 (Plan 02 Task 3) — see human_verification |

#### Plan 11-03 (Managed-Section Rendering Surface)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 9 | MANAGED_SECTIONS = ("CM-TODOS","OPEN-ITEMS","USAGE","ACTIVITY-LOG") — Sites OMITTED | VERIFIED | Confirmed via Python import; tuple matches exact spec; no SITES marker anywhere |
| 10 | EMOJI_BY_KIND includes "contract": "📄" | VERIFIED | `EMOJI_BY_KIND['contract'] == '📄'` confirmed via Python import |
| 11 | render_cm_todos returns three-state output | VERIFIED | render_cm_todos(None) == "_(CM data unavailable; will refresh next sync)_"; full populated → "_(no missing CM data)_"; partial → bullet list — 5/5 TestCmTodosSection tests pass |
| 12 | render_usage returns formatted SLA status or "_(no usage data)_" | VERIFIED | render_usage(None, "x") == "_(no usage data)_"; case-insensitive substring filter — 5/5 TestUsageSection tests pass |
| 13 | _NOTE_TEMPLATE includes CM-TODOS and USAGE marker pairs in display order | VERIFIED | grep CM-TODOS-START in _NOTE_TEMPLATE: present; SITES-START not in _NOTE_TEMPLATE; D-C1 order confirmed |
| 14 | Existing notes regenerate by run_backfill with Phase 10 four keys + new sections | VERIFIED | TestBackfillIdempotentPhase11 passes — two consecutive runs produce byte-identical managed sections (modulo last_synced + cm_data_stale_since) |

#### Plan 11-04 (CM-aware run_backfill + JIT + Pitfall 1)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 15 | _gather_events streams local + CM contract + CM-tracked invoice events into per-slug buckets | VERIFIED | TestGatherEventsCmIntegration passes 6/6; signature accepts cm_expiring + cm_invoices kwargs; Phase 10 callers byte-identical |
| 16 | CM invoices deduped against local by invoice_number with case-fold + trim only (Pitfall 4) | VERIFIED | _normalize_invoice_number = `(s or "").strip().lower()`; INV-0042 == inv-0042 (case-fold) AND INV-0042 != 0042 (NO prefix-strip) — verified by 3 tests including test_gather_events_dedup_does_not_strip_prefixes |
| 17 | Contract events render as `### [YYYY-MM-DD HH:MM] 📄 ...` via render_log_line(kind="contract") | VERIFIED | TestContractMerge.test_render_log_line_accepts_contract_kind asserts output starts with `### [2026-06-15 00:00] 📄`; tuple shape verified |
| 18 | run_backfill calls CM with try/except, falls back to cache, stamps cm_data_stale_since | VERIFIED | TestCacheFallbackEnd2End.test_cache_fallback_stamps_stale_since_and_writes_warning passes — cache hit on retry exhaustion stamps frontmatter with cm_data_stale_since AND emits level=warning feed entry |
| 19 | Cache hit on retry exhaustion logs system/warning feed entry | VERIFIED | 3 occurrences of `"level": "warning"` in vault_writer.py at lines 1126, 1141, 1231 covering global tools + per-client + JIT failures |
| 20 | On successful CM read, cm_data_stale_since OMITTED from frontmatter | VERIFIED | TestCacheFallbackEnd2End.test_cache_clears_stale_since_when_cm_succeeds passes — assertion: assertNotIn("cm_data_stale_since", ex_text) when CM succeeds |
| 21 | run_projection MUST NOT call CM (Pitfall 1) | VERIFIED | (a) `grep '^from .cm_client'` returns 0 module-top imports — both imports lazy at lines 1084, 1210; (b) TestProjectionDoesNotImportCm subprocess test passes — fresh Python process confirms cm_client NOT in sys.modules after run_projection; (c) in-process Python invocation also passes |
| 22 | run_backfill regenerate-from-full byte-identical (excluding last_synced + cm_data_stale_since) per D-14/D-16 | VERIFIED | TestBackfillIdempotentPhase11 passes — _snapshot helper strips both last_synced and cm_data_stale_since lines; two runs produce identical output |
| 23 | New client without cm_client_id auto-maps via JIT or emits warning (D-G1) | VERIFIED | TestJitMapping.test_jit_maps_new_domain (success path), test_jit_no_match_warns, test_jit_search_fails_warns all pass — 3/3; "JIT-mapped" info entry + "JIT mapping failed" warning entries both present in vault_writer.py |
| 24 | Live CM-aware backfill produces correct vault notes on Coolify + iPhone Obsidian renders correctly | DEFERRED LIVE | Code path proven by 17 mocked tests; live HTTP + iPhone visual verification deferred per Glen 2026-05-02 (Plan 04 Task 3) — see human_verification |

**Score:** 24/24 must-haves verified (22 fully VERIFIED in code + 2 routed to human_verification with mocked-test backing)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `schemas/feed-entry.json` | `level` enum has "warning" | VERIFIED | Plan 11-01 — 4 enum values present |
| `.gitignore` | data/.cm-cache.json line | VERIFIED | Plan 11-01 — `git check-ignore` returns path |
| `scripts/sync-obsidian.sh` | CONTRACT_MANAGER_API_KEY env validation | VERIFIED | Plan 11-01 — 1 occurrence of `${VAR:?msg}` idiom at line 33 |
| `scripts/lib/vault_writer.py` | render_frontmatter signature ext, MANAGED_SECTIONS ext, _NOTE_TEMPLATE ext, render_cm_todos, render_usage, _gather_events ext, _fetch_cm_data_for_run, JIT mapping, lazy cm_client import | VERIFIED | All 11 critical extensions present in 1815-line file; all imports of cm_client are inside function bodies (lines 1084, 1210) |
| `scripts/lib/cm_client.py` | NEW: _cm_post, call_with_retry, load_cache, write_cache, gc_cache_orphans, cm_summary_to_frontmatter_extra, search_clients_for_domain, CmTransportError, CmRpcError, CmRateLimitError, CM_ENDPOINT, RETRY_DELAYS | VERIFIED | File exists at 229 lines; all named exports importable; constants match spec |
| `scripts/tests/test_cm_client.py` | NEW: 4 test classes, 14 tests | VERIFIED | File exists at 199 lines; TestCmClient, TestCallWithRetry, TestCmCache, TestCmSummaryAdapter — all 14 tests pass |
| `scripts/tests/test_vault_writer.py` | TestRenderFrontmatterPhase11, TestRunMapCmClients, TestCmTodosSection, TestUsageSection, TestGatherEventsCmIntegration, TestContractMerge, TestProjectionDoesNotImportCm, TestCacheFallbackEnd2End, TestBackfillIdempotentPhase11, TestJitMapping | VERIFIED | All 10 new test classes present in 1310-line file; all tests pass under unittest discover |
| `data/config/clients.jsonl` | Should have cm_client_id after Plan 02 Task 3 (Coolify) | DEFERRED LIVE | File currently has 3 records WITHOUT cm_client_id — expected per Glen 2026-05-02 deferral |
| `vault-build/Clients/*.md` | Should have CM-TODOS + USAGE markers after Plan 04 Task 3 (Coolify) | DEFERRED LIVE | Current notes are Phase 10 shape (no CM-TODOS, no USAGE) — expected per Glen 2026-05-02 deferral; live backfill on Coolify will regenerate |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| schemas/feed-entry.json | level=warning emitters | JSON Schema enum | WIRED | 7 occurrences of `"warning"` in vault_writer.py covering CM stale + JIT failures + map-cm-clients failures |
| sync-obsidian.sh | Coolify env var | `${VAR:?msg}` bash idiom | WIRED | line 33: validates BEFORE REPO_ROOT, BEFORE python exec |
| render_frontmatter | run_backfill | additive kwargs cm_extra + cm_stale_since | WIRED | line 1020-1021: run_backfill threads both kwargs into render_frontmatter |
| run_map_cm_clients | search_clients_for_domain | lazy import inside function | WIRED | line 1084: `from . import cm_client as _cm` inside run_map_cm_clients body |
| _fetch_cm_data_for_run | cm_client (call_with_retry, load_cache, etc.) | lazy import inside function | WIRED | line 1210: `from .cm_client import (...)` inside _fetch_cm_data_for_run body |
| run_backfill | _fetch_cm_data_for_run | called once per run | WIRED | line ~990 of run_backfill calls _fetch_cm_data_for_run; threads cm_data through render_frontmatter, render_cm_todos, render_usage, _gather_events, build_note_initial_markdown |
| run_projection | cm_client | NEGATIVE invariant (must NOT import) | VERIFIED NOT WIRED | TestProjectionDoesNotImportCm subprocess test confirms; in-process verification confirms; Pitfall 1 enforced |
| _gather_events | invoice dedup helper | _normalize_invoice_number called twice (local + CM) | WIRED | lines 929 + 935: both normalisations use the same helper |
| JIT mapping branch | search_clients_for_domain + clients.jsonl atomic rewrite | runs once per unmapped domain per sync | WIRED | lines ~1267-1305: all three paths (success, no-match, transport-fail) tested by TestJitMapping |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| render_frontmatter cm_extra | cm_extra dict | cm_summary_to_frontmatter_extra(summary) ← call_with_retry("get_client_summary", ...) | YES (proven by TestCacheFallbackEnd2End — fresh CM data populates Alice + AMS Core) | FLOWING (mocked) |
| render_cm_todos cm_extra | cm_extra dict (or None) | _fetch_cm_data_for_run bucket → run_backfill | YES — live → cache fallback → None three-state pattern | FLOWING (mocked) |
| render_usage sla_status | sla_result dict | call_with_retry("get_sla_status", {"clientId": cm_id}) | YES — TestUsageSection asserts hours/percent rendering | FLOWING (mocked) |
| Activity Log contract events | (ts, "contract", summary, detail) tuple | _cm_contract_event_tuple(contract) ← list_contracts_expiring | YES — TestContractMerge.test_cm_contract_event_tuple_shape verifies | FLOWING (mocked) |
| Activity Log CM invoices | (ts, "invoice", summary, detail) tuple | _cm_invoice_event_tuple(inv) ← list_overdue_invoices, AFTER dedup against local | YES — 3 dedup tests verify case-fold pass + prefix-strip fail | FLOWING (mocked) |
| Frontmatter cm_data_stale_since | str (ISO ts) | bucket["stale_since"] from cache.fetched_at | YES — only stamped on cache fallback path; cleared on success | FLOWING (mocked) |
| vault-build/Clients/*.md (live) | full rendered note | run_backfill on Coolify | DEFERRED — current vault-build is Phase 10 shape; Coolify run pending | DISCONNECTED (Plan 04 Task 3 deferred) |

**Live data-flow note:** All data sources flow correctly under mocked CM in tests. The single gap is `vault-build/Clients/*.md` on this worktree — it has not been regenerated against live CM yet because Glen deferred Plan 04 Task 3. When Glen runs `bash scripts/sync-obsidian.sh --backfill` on Coolify, the data will flow end-to-end. The CODE that produces this flow is verified.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full unit test suite | `python3 -m unittest discover scripts/tests` | Ran 74 tests in 0.181s, OK | PASS |
| Schema enum extension | `python3 -c 'import json; e=json.load(open("schemas/feed-entry.json"))["properties"]["level"]["enum"]; assert "warning" in e'` | exit 0 | PASS |
| cache file gitignored | `touch data/.cm-cache.json && git check-ignore data/.cm-cache.json` | prints `data/.cm-cache.json` | PASS |
| MANAGED_SECTIONS structure | `python3 -c 'from scripts.lib.vault_writer import MANAGED_SECTIONS; assert MANAGED_SECTIONS == ("CM-TODOS","OPEN-ITEMS","USAGE","ACTIVITY-LOG")'` | exit 0 | PASS |
| EMOJI contract | `python3 -c 'from scripts.lib.vault_writer import EMOJI_BY_KIND; assert EMOJI_BY_KIND["contract"] == "📄"'` | exit 0 | PASS |
| Pitfall 4 dedup invariants | `python3 -c '...; assert _normalize_invoice_number("INV-0042") == _normalize_invoice_number("inv-0042"); assert _normalize_invoice_number("INV-0042") != _normalize_invoice_number("0042")'` | exit 0 | PASS |
| Pitfall 1 in-process | `python3 -c 'import sys; from scripts.lib.vault_writer import run_projection; ...; run_projection(...); assert "scripts.lib.cm_client" not in sys.modules'` | exit 0 | PASS |
| Graceful skip (no key) | `CONTRACT_MANAGER_API_KEY= python3 -c '...; r=_fetch_cm_data_for_run(...); assert r["global_expiring"] is None'` | exit 0 | PASS |
| Sites omitted | `grep -F "SITES" scripts/lib/vault_writer.py; grep -F "render_sites" scripts/lib/vault_writer.py` | both empty | PASS |
| No module-top cm_client import | `grep '^from .cm_client' scripts/lib/vault_writer.py` | exit 1 (no matches) | PASS |
| --mode map-cm-clients available | `python3 -m scripts.lib.vault_writer --help \| grep -F "map-cm-clients"` | matches | PASS (per SUMMARY) |
| `bash -n scripts/sync-obsidian.sh` | parse-only check | exit 0 (per Plan 01 SUMMARY self-check) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INTL-01 (extended) | All 4 plans | Context accumulation — client history, past decisions stored in structured files (mapped to Phase 10, extended by Phase 11) | PARTIALLY SATISFIED | Code surface complete (frontmatter has all 5 new keys when CM data flows; CM-TODOS surfaces missing data; Activity Log carries contract events). Live data flow deferred per Glen 2026-05-02 — Plans 02+04 Task 3. REQUIREMENTS.md status remains "Context locked" pending live CM run. |
| CM-WAVE0 | 11-01 | Wave 0 bootstrap (schema enum, gitignore, env validation, render_frontmatter signature) | SATISFIED | All 4 truths verified for Plan 01 |
| CM-CLIENT | 11-02 | scripts/lib/cm_client.py JSON-RPC client with retry + cache + adapter | SATISFIED (code) — DEFERRED (live key) | 14 tests pass; all exports importable; live key deferred per Glen |
| CM-MAPPING | 11-02 | --mode map-cm-clients populates cm_client_id idempotently | SATISFIED (code) — DEFERRED (Coolify run) | 4 mocked tests pass; live mapping pass deferred to Glen |
| CM-FRONTMATTER | 11-03 | render_frontmatter wired to cm_extra; CM-TODOS section added | SATISFIED | Plan 01 signature + Plan 03 templates + Plan 04 wiring all present |
| CM-SECTIONS | 11-03 | MANAGED_SECTIONS ext, _NOTE_TEMPLATE ext, render_cm_todos, render_usage | SATISFIED | All 4 sections wired; Sites correctly OMITTED per D-C2-REVISED |
| CM-EVENTS | 11-04 | Contract events render with 📄 in Activity Log | SATISFIED (code) — DEFERRED (live data) | TestContractMerge passes; live backfill deferred to Glen |
| CM-INVOICES | 11-04 | CM invoices merged with local active.jsonl, deduped by invoice_number (case-fold + trim only) | SATISFIED | Pitfall 4 enforced via _normalize_invoice_number; 3 dedup tests pass including the no-prefix-strip pinning test |
| CM-CACHE | 11-04 | data/.cm-cache.json fallback on retry exhaustion + cm_data_stale_since stamping | SATISFIED | TestCacheFallbackEnd2End passes both scenarios (stamp + clear); cache file gitignored |
| CM-INTEGRATION-TESTS | 11-04 | TestContractMerge, TestInvoiceMerge (via TestGatherEventsCmIntegration), TestCacheFallbackEnd2End, TestProjectionDoesNotImportCm, TestBackfillIdempotentPhase11, TestJitMapping | SATISFIED | All 6 test classes present and passing (15 tests total in this group) |

**Note on REQUIREMENTS.md mapping:** Only INTL-01 is formally tracked in `.planning/REQUIREMENTS.md` for Phase 11. The other CM-* IDs (CM-WAVE0, CM-CLIENT, CM-MAPPING, CM-FRONTMATTER, CM-SECTIONS, CM-EVENTS, CM-INVOICES, CM-CACHE, CM-INTEGRATION-TESTS) are plan-level tracking IDs declared in plan frontmatter — they are NOT formal v2 requirements. This is consistent with how Phase 10 used internal D-XX decision IDs without registering each one in REQUIREMENTS.md. Recommendation: do not flag as ORPHANED — these are plan-tracking artifacts, not unmapped requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none surfaced during the scan) | — | — | — | — |

Per-file scans of the modified files (vault_writer.py, cm_client.py, sync-obsidian.sh) for TODO/FIXME/placeholder/empty implementations returned no real stubs:

- The strings `_(no missing CM data)_`, `_(no usage data)_`, `_(CM data unavailable; will refresh next sync)_` are documented three-state output of the renderers (Plan 03 D-B3, D-C3-REVISED), NOT stubs.
- Empty `[]` defaults in `cm_extra.get("deployed_modules", [])` etc. are D-B2 specified empty-array behaviour, NOT stubs.
- `if cm_extra is not None: ... else: ...` branching in render_cm_todos is the documented three-state pattern, NOT a stub.
- The `sites: []` field in frontmatter is the D-C2-REVISED documented behaviour (Sites section deferred until CM exposes a per-client sites tool), NOT a stub.

### Human Verification Required

Two items deferred from autonomous execution per Glen's explicit "don't stop! I'll add keys later" override on 2026-05-02. Both have full mocked-test backing in the codebase; only the live HTTP + Coolify + iPhone steps are deferred.

#### 1. Plan 02 Task 3 — Run mapping pass on Coolify to populate cm_client_id

**Test:**
1. Mint a CM API key at https://contracts.agend.info/settings/mcp
2. Inject `CONTRACT_MANAGER_API_KEY` into Coolify env config for agend-ops service
3. SSH to Coolify (`ssh root@103.249.238.17`, `cd /opt/agend-ops`)
4. Run `python3 -m scripts.lib.vault_writer --mode map-cm-clients --data-root data`
5. Confirm `data/config/clients.jsonl` now has `"cm_client_id": <int>` on at least one record
6. Commit clients.jsonl and run `bash scripts/push-and-sync.sh`

**Expected:** Each domain either resolves to a numeric `cm_client_id` (success) or has a `level=warning` entry in `data/feed.jsonl` with `summary: "map-cm-clients: failed for <domain>"` or `"no CM match for <domain>"`.

**Why human:** Requires real CM API key (only Glen can mint), Coolify SSH access, and a real CM instance with client records to match against. The CODE is proven — TestRunMapCmClients (4/4 mocked tests) verifies idempotency, per-client failure tolerance, and dry-run safety.

**Runbook:** `.planning/phases/11-contract-manager-integration-seed-and-refresh-client-note-fr/11-02-PLAN.md` (Task 3 `<how-to-verify>` block)

#### 2. Plan 04 Task 3 — Run live CM-aware backfill on Coolify and verify on iPhone

**Test:**
1. SSH to Coolify, confirm `CONTRACT_MANAGER_API_KEY` is exported
2. Run `bash scripts/sync-obsidian.sh --backfill`
3. Inspect `vault-build/Clients/property-council-australia.md` (or similar):
   - Frontmatter has Phase 10 keys (domain, client_name, status, last_synced) + Phase 11 keys (contract_start, contract_end, primary_contact, deployed_modules, sites: [])
   - `## TODO: Missing CM Data` section between Overview and Open Items
   - `## Usage` section between Open Items and Activity Log
   - Activity Log includes contract events with `📄` emoji + CM-tracked invoices not present locally
   - NO `## Sites` section anywhere (D-C2-REVISED)
4. Optional resilience test: temporarily set `CONTRACT_MANAGER_API_KEY="cm_live_invalid"` and re-run; expect warning entries + `cm_data_stale_since` stamped (cache hit) OR CM-TODOS shows "data unavailable" (cache miss). Restore real key after.
5. Confirm `git check-ignore data/.cm-cache.json` returns the path; `git status` does NOT show it
6. Commit + push regenerated `vault-build/Clients/*.md` via `bash scripts/push-and-sync.sh`
7. Open Obsidian on iPhone and verify a client note: frontmatter readable as property table, CM-TODOS / Usage / Activity Log render correctly with 📄 emoji on contract events, Glen-owned Overview/Decisions sections preserved unchanged

**Expected:** Live CM data flows end-to-end into vault notes; iPhone Obsidian renders correctly; cache file is gitignored; no critical feed entries from this sync run.

**Why human:** Requires live CM API key + Coolify host + Glen's iPhone for visual verification of Obsidian rendering. The CODE that produces this flow is proven by 17 mocked-CM tests:
- TestContractMerge (2 tests) — kind="contract" rendering + tuple shape
- TestGatherEventsCmIntegration (6 tests) — contract event routing + invoice dedup invariants
- TestCacheFallbackEnd2End (2 tests) — stale_since stamp + clear
- TestProjectionDoesNotImportCm (1 test) — Pitfall 1 subprocess invariant
- TestBackfillIdempotentPhase11 (1 test) — D-14/D-16 byte-equality
- TestJitMapping (3 tests) — D-G1 success + no-match + transport-failure paths
- TestRenderFrontmatterPhase11 (6 tests) — Plan 01 surface backwards-compat + Phase 11 ext

**Runbook:** `.planning/phases/11-contract-manager-integration-seed-and-refresh-client-note-fr/11-04-PLAN.md` (Task 3 `<how-to-verify>` block)

### Gaps Summary

**No code-level gaps found.** The phase goal is achieved at the code-surface level: the contract-manager MCP integration is fully wired through `scripts/lib/cm_client.py` (JSON-RPC client + retry + cache + adapter), `scripts/lib/vault_writer.py` (frontmatter extension, MANAGED_SECTIONS extension, run_backfill CM integration with cache fallback, JIT mapping fallback, Pitfall 1 isolation), and is tested by 74 unit tests including 6 mocked-CM end-to-end test classes (TestContractMerge, TestGatherEventsCmIntegration, TestCacheFallbackEnd2End, TestProjectionDoesNotImportCm, TestBackfillIdempotentPhase11, TestJitMapping) — all passing on master.

The two deferred items (Plan 02 Task 3 mapping pass on Coolify, Plan 04 Task 3 live CM-aware backfill + iPhone Obsidian verification) are NOT gaps — they were authorized deferrals per Glen's 2026-05-02 "don't stop! I'll add keys later" override and are explicitly documented in both 11-02-SUMMARY.md and 11-04-SUMMARY.md. They are routed to `human_verification` so they remain visible in `/gsd-progress` and `/gsd-audit-uat` until Glen runs them post-build.

**Critical invariants verified:**
- ✓ Pitfall 1 (Mac daemon does NOT import cm_client during run_projection) — both subprocess test AND in-process invocation confirm
- ✓ Pitfall 4 (invoice dedup is case-fold + trim only, NEVER prefix-stripping) — `_normalize_invoice_number` is the single source of truth; 3 pinning tests including the explicit no-prefix-strip test
- ✓ D-G1 JIT mapping fallback — wired into `_fetch_cm_data_for_run`, all 3 paths (success/no-match/transport-fail) tested
- ✓ D-14/D-16 byte-identical regenerate-from-full — TestBackfillIdempotentPhase11 strips both `last_synced:` and `cm_data_stale_since:` lines and asserts byte equality across two consecutive runs
- ✓ D-C2-REVISED (no Sites section in templates, no SITES marker pair, no render_sites function) — `grep "SITES"` and `grep "render_sites"` both return zero matches
- ✓ Lazy-import discipline — module-top imports of cm_client are 0; both lazy imports (line 1084 in run_map_cm_clients, line 1210 in _fetch_cm_data_for_run) are inside function bodies

**Test surface:** 74 tests pass (49 Phase 10 + Phase 11 baseline → 74 with all 4 plans). All 6 mocked-CM integration test classes (15 tests total) cover the data-flow paths that the deferred live-CM verification will exercise on Coolify.

---

*Verified: 2026-05-02T14:17:31Z*
*Verifier: Claude (gsd-verifier)*
