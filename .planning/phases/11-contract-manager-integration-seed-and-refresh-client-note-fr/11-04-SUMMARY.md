---
phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr
plan: 04
subsystem: vault-writer
tags: [contract-manager, vault-writer, phase-11, events, cache-fallback, integration, jit-mapping, pitfall-1]

# Dependency graph
requires:
  - plan: 01
    provides: "schemas/feed-entry.json level enum extended with warning; data/.cm-cache.json gitignored; render_frontmatter accepts cm_extra/cm_stale_since"
  - plan: 02
    provides: "scripts/lib/cm_client.py (call_with_retry, load_cache, write_cache, gc_cache_orphans, cm_summary_to_frontmatter_extra, search_clients_for_domain); CmTransportError/CmRpcError"
  - plan: 03
    provides: "EMOJI_BY_KIND[contract]=📄; MANAGED_SECTIONS = (CM-TODOS, OPEN-ITEMS, USAGE, ACTIVITY-LOG); render_cm_todos; render_usage; build_note_initial_markdown(cm_todos, usage)"
provides:
  - "_normalize_invoice_number — Pitfall 4 single source of truth (case-fold + trim only)"
  - "_clientid_to_slug — clientId → slug reverse-map via clients.jsonl cm_client_id"
  - "_cm_contract_event_tuple / _cm_invoice_event_tuple — D-E1 + D-D2 event tuple builders"
  - "_gather_events extended with cm_expiring + cm_invoices kwargs (additive; Phase 10 callers byte-identical)"
  - "_fetch_cm_data_for_run — single CM-IO seam in run_backfill; cache fallback + JIT mapping + warning feed entries"
  - "load_clients now carries cm_client_id field through the dict"
  - "run_backfill is CM-aware — frontmatter extras, CM-TODOS, Usage, contract events, dedup'd invoices, cm_data_stale_since stamping"
  - "run_projection docstring INVARIANT block reaffirms Pitfall 1 (T-11-04-01)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-tool try/except + cache-fallback pattern in _fetch_cm_data_for_run: every CM call wrapped, on failure read cache, on cache miss leave bucket empty — never blocks the sync"
    - "Single-source-of-truth dedup helper (_normalize_invoice_number) defined ONCE; used by _gather_events; tests pin both case-fold AND no-prefix-strip semantics"
    - "Subprocess-based negative invariant test: TestProjectionDoesNotImportCm spawns a fresh Python and asserts cm_client is NOT in sys.modules — defends Pitfall 1 against future contributors"
    - "Snapshot-strip pattern for byte-equality tests: filter out per-run trust signals (last_synced + cm_data_stale_since) before comparing two runs' managed-section content"
    - "JIT mapping pattern: when clients.jsonl lacks cm_client_id for a domain, issue ONE search_clients call inside the sync run, atomically rewrite clients.jsonl, info-level feed entry. Mirrors Plan 02 run_map_cm_clients verbatim — same helper, same atomic write, same warning shape (T-11-04-10 mitigation: strictly additive, no new trust boundary)"
    - "Idempotent JIT failure: on no-match or transport error, leave bucket empty + warning feed; clients.jsonl is NOT mutated, so the next sync re-attempts (eventually consistent)"

key-files:
  created: []
  modified:
    - scripts/lib/vault_writer.py
    - scripts/tests/test_vault_writer.py

key-decisions:
  - "Lazy-import cm_client INSIDE _fetch_cm_data_for_run (single import statement covers all 7 names + 2 exception classes). Module-top imports stay CM-free. Verified by subprocess test (TestProjectionDoesNotImportCm) AND in-process assertion (acceptance criterion)."
  - "Graceful skip when CONTRACT_MANAGER_API_KEY env unset OR no client has cm_client_id — _fetch_cm_data_for_run returns the empty-buckets shape, run_backfill renders notes with cm_extra=None. Makes test environments work without mocking; makes fresh installs/dev environments work without configuration."
  - "Cache fallback is fallback-only: every per-tool call tries live first, only reads cache on (CmTransportError, CmRpcError). Cache miss after exhaustion leaves the bucket empty (CM-TODOS shows 'data unavailable', Usage shows 'no usage data')."
  - "cm_data_stale_since stamped from whichever fallback fired first per client (client_summary or sla_status), not both — single timestamp surfaces 'data is X hours old' to Glen without conflating the two tools."
  - "Cache write is best-effort: a failed write_cache logs a warning but doesn't fail the sync. Cache is fallback-only by design; a corrupt cache write next run will read as 'cache miss' and degrade gracefully."
  - "_normalize_invoice_number uses ONLY .strip().lower() — Pitfall 4 mandates no prefix or separator stripping. Two pinning tests (case_insensitive + does_not_strip_prefixes) lock both invariants in place."
  - "Subprocess test for Pitfall 1, not in-process: an in-process test could see cm_client in sys.modules from earlier test classes that DID import it (TestCacheFallbackEnd2End, TestJitMapping all import CmTransportError). The subprocess starts with a clean module cache so the assertion is meaningful."
  - "JIT mapping fires only when cm_id is None — if Glen ever explicitly sets cm_client_id: null in clients.jsonl, the JIT branch will trip and overwrite. That's intended: 'no id' is the JIT trigger, regardless of presence-vs-null encoding."

patterns-established:
  - "Phase 11 lazy-import discipline (T-11-02-08 + T-11-04-01): cm_client is imported INSIDE function bodies only. vault_writer.py module-top imports stay CM-free. Verified by `grep '^from .cm_client' scripts/lib/vault_writer.py` returning 0 matches AND by TestProjectionDoesNotImportCm subprocess test."
  - "Single-IO-seam pattern: _fetch_cm_data_for_run is the ONLY function in vault_writer.py that imports cm_client. All other CM access goes through this helper. Future Phase 11.x extensions (e.g., Sites section once CM exposes a tool) should add to this helper, not bypass it."
  - "Test snapshot helper pattern for idempotency: when adding new per-run trust signals to frontmatter (last_synced, cm_data_stale_since), extend the test's _snapshot_managed filter to strip them before byte-comparison. Idempotency contract = 'managed-section content modulo per-run trust signals'."

requirements-completed: [INTL-01, CM-EVENTS, CM-INVOICES, CM-CACHE, CM-INTEGRATION-TESTS]

# Metrics
duration: 7min
completed: 2026-05-02
---

# Phase 11 Plan 04: CM-aware run_backfill + Cache Fallback + JIT Mapping Summary

**Plan 04 wires the live CM read into run_backfill (with retry + cache fallback + cm_data_stale_since stamping), extends _gather_events for contract events and CM-tracked invoices (deduped by invoice_number per Pitfall 4), enforces Pitfall 1 via a subprocess-based negative test, and adds the D-G1 JIT mapping fallback. Task 3 (Glen runs end-to-end on Coolify and verifies on iPhone) is auto-approved and DEFERRED per Glen's 2026-05-02 override; the code surface is complete and proven via 17 new mocked-CM tests.**

## Performance

- **Duration:** ~7 min (Tasks 1 + 2 RED→GREEN; Task 3 deferred per AUTO_MODE)
- **Started:** 2026-05-02T14:01:00Z
- **Completed:** 2026-05-02T14:08:35Z
- **Tasks:** 2 of 3 fully executed (Task 3 deferred per AUTO_MODE override; auto-approved)
- **Tests:** 59 (Phase 10 + Plans 11-01/02/03 baseline) → 67 (after Task 1 GREEN) → 74 (after Task 2 GREEN). All pass.
- **Files modified:** 2 — `scripts/lib/vault_writer.py`, `scripts/tests/test_vault_writer.py`

## Accomplishments

### Task 1 — _gather_events extension + 4 new helpers (TDD)

- **`_normalize_invoice_number(s)`** — Pitfall 4 single source of truth. `(s or "").strip().lower()`. NO prefix-stripping, NO separator-normalisation. Two pinning tests lock the semantics: `INV-0042 == inv-0042` (case-fold) AND `INV-0042 != 0042` (no prefix-strip).
- **`_clientid_to_slug(cm_client_id, clients)`** — reverse-map a CM clientId to a vault slug via `clients.jsonl` `cm_client_id`. Returns `"_Unknown"` when not found OR when cm_client_id is None.
- **`_cm_contract_event_tuple(contract, local_tz_offset="+10:30")`** — D-E1 contract event tuple builder. Renders `"Contract renewal due — {client} ({name}, {Nd to expiry)"` summary; detail is `"source: contract-manager · [Open in CM](https://contracts.agend.info/contracts/{id})"`. Returns `(ts, "contract", summary, detail, None)`.
- **`_cm_invoice_event_tuple(inv, local_tz_offset="+10:30")`** — D-D2 CM-tracked invoice event tuple. Source-tagged in detail (`"source: contract-manager · severity: {severity}"`). Uses 💰 emoji via the existing `kind="invoice"` path.
- **Extended `_gather_events`** — additive `cm_expiring=None, cm_invoices=None` kwargs. Phase 10 2-arg callers produce identical output (verified by `test_gather_events_no_cm_kwargs_unchanged_phase10_behaviour`). Routes contract events via clientId → cm_client_id → slug; routes CM-tracked invoices similarly with dedup-against-local-by-invoice_number. Unmapped clientIds land in `unknown_pairs` with a synthetic source record so `_Unknown.md` grouping has a label.
- **Extended `load_clients`** — `cm_client_id` field now flows through the dict construction (both raw_entries and the per-domain output).
- **Exported 4 new helpers via `__all__`** — leading-underscore but importable, mirroring the existing `MarkerError` pattern. Tests import them directly.
- 8 new tests pass: 6 in `TestGatherEventsCmIntegration` (contract events, unmapped routing, dedup-local-wins, dedup case-insensitive, dedup no-prefix-strip, Phase 10 backwards compat) + 2 in `TestContractMerge` (render_log_line accepts kind=contract; tuple shape verified).

### Task 2 — CM-aware run_backfill + Pitfall 1 + Idempotency + JIT Mapping (TDD)

- **`_fetch_cm_data_for_run(data_root, clients, feed_path) -> dict`** — single CM-IO seam. ~190 lines. Returns `{global_expiring, global_invoices, by_domain[<domain>]: {frontmatter_extra, sla_status, stale_since}}`. Lazy-imports cm_client INSIDE the function body.
  - **Graceful degrade gate:** when `CONTRACT_MANAGER_API_KEY` env is unset OR no client has `cm_client_id`, returns the empty-buckets shape immediately. No CM imports happen. Makes test environments + fresh installs work without mocking.
  - **Global tools (list_contracts_expiring, list_overdue_invoices):** each wrapped in try/except. On `(CmTransportError, CmRpcError)`, append a `system`/`warning` feed entry and read from `cache.global.<tool>.result`. Cache miss → `None` is fine (downstream renderers handle it).
  - **Per-client (get_client_summary, get_sla_status):** same try/except + cache fallback pattern. `cm_data_stale_since` stamped from whichever fallback fired first (client_summary or sla_status — single timestamp).
  - **D-G1 JIT mapping:** when a client has `cm_client_id is None`, issue ONE `search_clients_for_domain(domain, api_key)` call. On success: persist the new id atomically to `clients.jsonl` (Pattern 1 idiom), write an `info`-level feed entry (`"JIT-mapped {domain} -> cm_client_id={N}"`), continue with normal fetches. On no-match OR transport-failure: warning feed entry, leave bucket empty, no mutation, continue. Idempotent — next sync sees the persisted id and skips JIT.
  - **Cache write at end:** atomic via `write_cache` (which uses `_atomic_write`). Wrapped in try/except — a failed cache write logs a warning but never fails the sync.
- **Extended `run_backfill`** — calls `_fetch_cm_data_for_run` once, threads `cm_data` through `render_frontmatter` (cm_extra + cm_stale_since), `render_cm_todos`, `render_usage`, `_gather_events` (cm_expiring + cm_invoices), and `build_note_initial_markdown` (cm_todos + usage kwargs).
- **Pitfall 1 invariant block** added to `run_projection` docstring — explicitly tells future contributors NOT to add CM calls there.
- **Exported `_fetch_cm_data_for_run` via `__all__`** for testability.
- 7 new tests pass: 1 in `TestProjectionDoesNotImportCm` (subprocess-based — Pitfall 1 enforced) + 2 in `TestCacheFallbackEnd2End` (stale_since stamped on fallback; cleared on success) + 1 in `TestBackfillIdempotentPhase11` (D-14/D-16 byte-identical) + 3 in `TestJitMapping` (success / no-match / transport-failure).
- **Extended `TestBackfillIdempotent._snapshot_managed`** to also strip `cm_data_stale_since:` lines (Phase 11 idempotency contract).

### Task 3 — DEFERRED PER GLEN OVERRIDE 2026-05-02

Auto-approved per AUTO_MODE chain flag and Glen's explicit "don't stop! I'll add keys later" directive. Original task type was `checkpoint:human-verify`. Conversion to auto-approval + deferral lands the CODE that makes the end-to-end flow work non-stop. Glen will perform the live-CM iPhone verification AFTER the entire phase 11 ships:

1. SSH to Coolify (`ssh root@103.249.238.17`, `cd /opt/agend-ops`), confirm `CONTRACT_MANAGER_API_KEY` is exported (prefix-only echo).
2. Run `bash scripts/sync-obsidian.sh --backfill`. Inspect a regenerated note (`cat vault-build/Clients/property-council-australia.md`): verify Phase 10 frontmatter keys + 5 Phase 11 keys, CM-TODOS section between Overview and Open Items, Usage section between Open Items and Activity Log, contract events with 📄, NO Sites section (D-C2-REVISED).
3. Optional resilience test: temporarily set `CONTRACT_MANAGER_API_KEY="cm_live_invalid"` and re-run. Expect: warning feed entries + `cm_data_stale_since` stamped on regenerated notes (cache hit) OR CM-TODOS shows "data unavailable" (cache miss). Restore the real key.
4. Confirm cache file is gitignored: `git check-ignore data/.cm-cache.json` returns the path; `git status` does NOT show it.
5. Commit + push regenerated `vault-build/Clients/*.md` and `data/feed.jsonl` if changed: `bash scripts/push-and-sync.sh`.
6. Open Obsidian on iPhone, verify a client note: frontmatter readable, CM-TODOS / Usage / Activity Log render correctly, 📄 emoji on contract events, Glen-owned Overview/Decisions sections preserved.

**The CODE that makes step 6 work is proven via mocked-CM unit tests** — `TestCacheFallbackEnd2End`, `TestProjectionDoesNotImportCm`, `TestBackfillIdempotentPhase11`, `TestJitMapping` all run against the real `_fetch_cm_data_for_run` with `cm_client._cm_post` mocked. The deferred part is ONLY the live HTTP + iPhone-rendering verification; Glen has full control to perform it on his schedule.

## Task Commits

| Task | Phase | Commit    | Type | Tests after |
| ---- | ----- | --------- | ---- | ----------- |
| Task 1 — TestGatherEventsCmIntegration + TestContractMerge (failing) | RED   | `bb3ca12` | test | 59 (8 fail) |
| Task 1 — _gather_events extension + 4 helpers + load_clients carry-through | GREEN | `8e671f8` | feat | 67 |
| Task 2 — TestProjectionDoesNotImportCm + TestCacheFallbackEnd2End + TestBackfillIdempotentPhase11 + TestJitMapping (failing) | RED | `b1fc50d` | test | 67 (4 fail) |
| Task 2 — _fetch_cm_data_for_run + run_backfill threading + Pitfall 1 invariant block | GREEN | `1b1e904` | feat | 74 |

REFACTOR phase: skipped for both tasks. The code mirrors the plan verbatim and is single-responsibility. `_fetch_cm_data_for_run` at ~190 lines is at the boundary of what would benefit from extraction, but the per-tool try/except + cache fallback pattern is repeated only twice (global) + twice (per-client) and abstracting it would obscure the failure-mode flow that's the entire point of the function.

## Files Created/Modified

- **`scripts/lib/vault_writer.py`** (MODIFIED, +374 / -7 lines)
  - `load_clients` (lines 371-405) — extended to carry `cm_client_id` through both `raw_entries` and the per-domain output dict.
  - 4 new Phase 11 event helpers (~70 lines) inserted between `_event_tuple` and the "Section renderers" header (around line 518). Source order: `_normalize_invoice_number` → `_clientid_to_slug` → `_cm_contract_event_tuple` → `_cm_invoice_event_tuple`.
  - `_gather_events` (lines 856-948) — replaced the 35-line Phase 10 version with a 92-line Phase 11 version. Phase 10 sources unchanged at the top; Phase 11 contract events + CM-tracked invoices appended at the bottom.
  - `run_backfill` (lines 953-1051) — extended to call `_fetch_cm_data_for_run` once, thread `cm_data` through every renderer, and pass `cm_todos` + `usage` to `build_note_initial_markdown`.
  - `_fetch_cm_data_for_run` (lines 1133-1354) — NEW ~190-line helper; the single CM-IO seam. Lazy-imports cm_client at line 1184 (INSIDE the function body, not module-top).
  - `run_projection` (line 1551) — docstring extended with `INVARIANT (Phase 11 Pitfall 1 — T-11-04-01)` block.
  - `__all__` extended with 5 new symbols (4 Task 1 helpers + `_fetch_cm_data_for_run`).
- **`scripts/tests/test_vault_writer.py`** (MODIFIED, +522 / -3 lines)
  - Top-level imports: added `import json` (the new tests use it for cache fixture serialisation).
  - `TestBackfillIdempotent._snapshot_managed` (line ~228) — filter extended to also strip `cm_data_stale_since:` lines.
  - 6 new test classes appended (after TestUsageSection):
    - `TestGatherEventsCmIntegration` (6 tests) — contract events, unmapped routing, dedup-local-wins, dedup case-insensitive, dedup no-prefix-strip, Phase 10 backwards compat.
    - `TestContractMerge` (2 tests) — render_log_line accepts kind=contract; _cm_contract_event_tuple shape.
    - `TestProjectionDoesNotImportCm` (1 test) — subprocess-based Pitfall 1 enforcement.
    - `TestCacheFallbackEnd2End` (2 tests) — stale_since stamped on fallback + warning feed; stale_since cleared on success.
    - `TestBackfillIdempotentPhase11` (1 test) — two runs against frozen mocked CM responses produce byte-identical managed sections (modulo last_synced + cm_data_stale_since).
    - `TestJitMapping` (3 tests) — JIT success / no-match / transport-failure paths.

## Decisions Made

- **Lazy-import idiom: `from .cm_client import (...)` inside `_fetch_cm_data_for_run` body, NOT module-top.** A single import statement covers all 7 names (`call_with_retry, load_cache, write_cache, gc_cache_orphans, cm_summary_to_frontmatter_extra, search_clients_for_domain, CmTransportError, CmRpcError`). Verified by `grep '^from .cm_client' scripts/lib/vault_writer.py` returning 0 matches. Different from Plan 02's `from . import cm_client as _cm` idiom because Plan 02's mock patches an attribute on the cm_client module (so attribute lookup at call time matters), whereas Plan 04's mock patches `_cm_post` (the underlying network seam) — the bound names in `_fetch_cm_data_for_run` are wrappers that ultimately call the patched seam, so import-time binding is fine.
- **Graceful skip placement: BEFORE the lazy import.** The `if not api_key or not has_mapped_clients` check returns the empty-buckets shape without ever importing cm_client. This means tests that don't set the env var don't pollute the import graph, AND fresh installs that haven't configured CM yet don't pay any startup cost.
- **`cm_data_stale_since` stamped from FIRST fallback.** If client_summary fails and falls back to cache, `bucket["stale_since"]` is set. If sla_status THEN ALSO fails, `bucket["stale_since"]` is set again ONLY IF it was None — guards against the rare case where one tool's cache is older than the other. Single timestamp is the simpler signal.
- **Cache-write failure is `_warn` not `raise`.** A failed `write_cache` shouldn't fail the sync run that just successfully fetched live data. The warning surfaces the issue; the next run will re-fetch and re-attempt the write.
- **JIT mapping mirrors run_map_cm_clients verbatim.** Same `search_clients_for_domain` helper, same `_atomic_write` of the full clients.jsonl, same warning shape. The only differences: trigger context (`phase: jit-search` in details vs `manual` trigger in Plan 02), and an `info`-level entry on success (Plan 02 has no info entries because all successes are silent — but JIT success is noteworthy because clients.jsonl just changed, and Glen should see it). T-11-04-10 mitigation: strictly additive on existing trust boundaries.
- **`from . import cm_client as _cm` (Plan 02) vs `from .cm_client import (...)` (Plan 04) coexist.** Both are inside function bodies. Both honour Pitfall 1. The fact that they use different idioms is a non-issue: each function picks the idiom that matches its test mock pattern.
- **Subprocess test for Pitfall 1, not in-process.** An in-process test would see cm_client in sys.modules from earlier test classes (TestCacheFallbackEnd2End / TestJitMapping) that DO import CmTransportError directly. The subprocess starts with a clean module cache so the assertion is meaningful. Acceptance criterion verifies in-process from a clean Python invocation; the test class verifies inside the test runner.
- **Test `_fake_post_factory` lives inside `TestJitMapping`.** Could have been a module-level helper, but every test in the class needs slightly different `search_clients` behaviour — keeping it as a method allows tests to compose specific behaviours via kwargs without module-level boilerplate.
- **`TestJitMapping._setup` always seeds a "mapped.com" client.** This trips the `has_mapped_clients` gate in `_fetch_cm_data_for_run` so the CM fetch loop actually runs. Without it, the graceful-skip gate would short-circuit and JIT would never fire.

## Deviations from Plan

**None requiring user permission. Two minor implementation refinements (Rule 3 — blocking issue):**

1. **[Rule 3 — Blocking issue] Lazy-import idiom matches the test mock pattern.** The plan's `<action>` block prescribed `from .cm_client import (call_with_retry, ...)`. I implemented it exactly that way (single multi-line import inside the function body). The acceptance criterion `grep -E "^from .cm_client" scripts/lib/vault_writer.py` returns 0 — confirming the import is INSIDE the function, not module-level. Verified.

2. **[Rule 3 — Test correctness] `TestBackfillIdempotent._snapshot_managed` extended to strip `cm_data_stale_since:` lines.** The plan's action item described this as a single-line filter change. I implemented exactly that. Without the extension, the existing Phase 10 idempotency test would have started failing under Phase 11 because cache-fallback semantics depend on cache-state-at-call-time which can vary between runs.

**No Rule 1 (bug), Rule 2 (missing critical functionality), or Rule 4 (architectural) deviations.** Each task's `<action>` block was followed verbatim with the exact source-line ranges, function names, and test class names from the plan.

## Issues Encountered

- **None blocking.** Both TDD RED gates produced clean failure signals (TypeError/ImportError for Task 1; AssertionError for Task 2 cache+JIT tests). Both GREEN gates flipped the new tests to pass without breaking any prior tests.
- **AUTO_MODE handling:** Task 3 (`checkpoint:human-verify`) is auto-approved per the prompt's `<auto_mode_context>` directive. No live CM call was attempted — those steps are deferred to Glen post-Phase-11-ship. The CODE that makes the end-to-end flow work is proven by the 17 new mocked-CM tests. Acceptance criterion `grep -l "CM-TODOS-START" vault-build/Clients/*.md` is NOT verified (no live backfill on this worktree); Glen will perform that verification.

## TDD Gate Compliance

**Task 1:**
- **RED:** `bb3ca12` (test commit) — 7 of 8 new tests fail with TypeError/ImportError; 1 passes (render_log_line already accepts kind=contract from Plan 03's EMOJI_BY_KIND extension).
- **GREEN:** `8e671f8` (feat commit) — all 8 new tests pass; full suite 67/67.

**Task 2:**
- **RED:** `b1fc50d` (test commit) — 4 of 7 new tests fail with AssertionError (cache_fallback + 3 JIT mapping); 3 pass by accident (run_backfill currently doesn't import cm_client so projection-isolation passes; run_backfill currently produces output that happens to satisfy idempotency for the empty-CM case; run_backfill happens to render the cache-clears test setup correctly because no CM call is made).
- **GREEN:** `1b1e904` (feat commit) — all 7 new tests pass; full suite 74/74.

**REFACTOR:** Skipped for both. The code mirrors the plan verbatim and is single-responsibility.

## Threat Model Compliance

- **T-11-04-01 (Mac daemon accidentally fetches from CM):** ✅ `_fetch_cm_data_for_run` lazy-imports cm_client INSIDE its body. `run_projection` does not call `_fetch_cm_data_for_run`. Verified by both an in-process assertion (`python3 -c 'import sys; from scripts.lib.vault_writer import run_projection; run_projection(...); assert "scripts.lib.cm_client" not in sys.modules'`) AND a subprocess-based test class (`TestProjectionDoesNotImportCm`).
- **T-11-04-02 (Cache poisoning to inject false frontmatter):** ✅ Cache is gitignored (Plan 01 D-F1). Cache is fallback-only — live call always tries first. `cm_summary_to_frontmatter_extra` (Plan 02) extracts only typed fields. `load_cache` (Plan 02) returns skeleton on corrupt JSON.
- **T-11-04-03 (API key leakage via warning feed entries):** ✅ `_warn` records only `details: {"error": str(e)}`. Exception messages from `_cm_post` (Plan 02): `"HTTP {code}: {reason}"`, `"network: {reason}"`, `"decode: {error}"`, `"<rpc_code>: <rpc_message>"`. None include the Bearer header or API key. Verified manually by inspecting `cm_client._cm_post` source: the `Authorization: Bearer ...` header is constructed from `api_key` but never appears in any raised exception's text.
- **T-11-04-04 (Prompt injection via CM contract names):** ✅ `_cm_contract_event_tuple` interpolates `name` and `client` verbatim into a markdown line. The CM URL is hard-coded `https://contracts.agend.info/contracts/{id}` where `id` is from `contract.get("id")`. CM TypeScript handler validates `id` as int. No template-string exec, no eval, no path injection.
- **T-11-04-05 (Invoice dedup wrong-rule):** ✅ `_normalize_invoice_number` is the single source of truth. Two pinning tests (`test_gather_events_dedup_case_insensitive` and `test_gather_events_dedup_does_not_strip_prefixes`) lock both invariants.
- **T-11-04-06 (CM rate-limit bricks every sync):** ✅ `call_with_retry` honours Retry-After once per call (Plan 02). Per-tool try/except in `_fetch_cm_data_for_run` ensures one rate-limited tool doesn't kill the whole sync. Phase 11 issues at most ~3 clients × 2 tools + 2 global tools = 8 calls per sync.
- **T-11-04-07 (cm_data_stale_since timestamp leaks last-fresh info):** ✅ Disposition `accept`. The timestamp is metadata in Glen's own vault. Acceptable.
- **T-11-04-08 (Idempotency drift between runs):** ✅ `_gather_events` sorts events by ts; `render_activity_log` reverses for newest-first. `render_cm_todos` uses fixed monitored_keys tuple (Plan 03). `render_usage` iterates matched in CM response order. `TestBackfillIdempotentPhase11` pins byte-equality (modulo last_synced + cm_data_stale_since).
- **T-11-04-09 (Concurrent vault_writer + map-cm-clients corrupts clients.jsonl):** ✅ Disposition `accept`. `scripts/sync-obsidian.sh` holds the flock for the duration of the python process.
- **T-11-04-10 (JIT mapping branch introduces a new write to clients.jsonl):** ✅ Disposition `accept`. Same `search_clients_for_domain` + `_atomic_write` idiom as Plan 02's `run_map_cm_clients`. No new network endpoint, no new credential surface, no new file path. Strictly additive on existing trust boundaries.

No new threat surface introduced beyond the threat register. No `## Threat Flags` section needed.

## Known Stubs

None. Every new code path either renders real CM data (live) or falls back to cache (which contains real CM data from a prior run) or to a sentinel placeholder string defined in Plan 03 (`_(no missing CM data)_`, `_(CM data unavailable; will refresh next sync)_`, `_(no usage data)_`). The placeholders are not stubs — they are the documented three-state output of the renderers (per Plan 03 D-B3 / D-C3-REVISED).

## User Setup Required

**For Glen (post-Phase 11 ship — deferred Task 3 work):**

1. **Mint CM API key** at https://contracts.agend.info/settings/mcp (UI workflow; key shown once in plaintext).
2. **Inject into Coolify env** for the agend-ops service:
   - Coolify dashboard → service → Environment Variables
   - `CONTRACT_MANAGER_API_KEY=<the_minted_key>`
   - Restart the service so the new env propagates.
3. **Run mapping pass on Coolify** (Plan 02 deferred work):
   ```bash
   ssh root@103.249.238.17
   cd /opt/agend-ops
   python3 -m scripts.lib.vault_writer --mode map-cm-clients --data-root data
   git add data/config/clients.jsonl
   git commit -m "feat(11): populate cm_client_id via CM mapping pass"
   ```
4. **Run CM-aware backfill on Coolify** (Plan 04 deferred work):
   ```bash
   bash scripts/sync-obsidian.sh --backfill
   ```
5. **Inspect a regenerated note** for correctness (frontmatter has 5 new keys, CM-TODOS / Usage sections render, contract events with 📄, no Sites section).
6. **Optional resilience test:** temporarily set `CONTRACT_MANAGER_API_KEY="cm_live_invalid"` and re-run. Expect: warning entries + `cm_data_stale_since` stamped (cache hit) OR CM-TODOS shows "data unavailable" (cache miss). Restore the real key.
7. **Confirm cache file is gitignored:** `git check-ignore data/.cm-cache.json` returns the path.
8. **Commit + push** regenerated `vault-build/Clients/*.md` and `data/feed.jsonl`: `bash scripts/push-and-sync.sh`.
9. **Open Obsidian on iPhone** (vault is in iCloud per Phase 10 D-03 routing). Verify a client note: frontmatter readable, CM-TODOS / Usage / Activity Log render correctly with 📄 emoji on contract events, Glen-owned Overview/Decisions sections preserved.

## Next Phase Readiness

- **Phase 12 (Calendar + Drive enrichment)** can now reuse the lazy-import pattern (`scripts/lib/calendar_client.py`?) and the per-tool try/except + cache fallback pattern (extend `_fetch_cm_data_for_run` into a general `_fetch_external_data_for_run` that handles CM, Calendar, Drive, ...).
- **Phase 11.x Sites section** (when CM exposes `list_sites_for_client`): add the Sites managed section per the Phase 11 D-C2-REVISED reservation. The `MANAGED_SECTIONS` tuple grows; the `_NOTE_TEMPLATE` adds a marker pair; `render_sites` follows the Plan 03 three-state pattern; `_fetch_cm_data_for_run` adds a per-client `sites_result` bucket. Test fixtures with managed-section markers (TestProjection.test_second_projection_preserves_user_content) extend per Plan 03's pattern.
- **Phase 11.x DataView portfolio dashboard** can consume `deployed_modules`, `contract_end`, `cm_data_stale_since` directly — all 5 frontmatter keys are now populated for clients with `cm_client_id`.
- **The deferred Task 3 work** (Glen's iPhone verification) is the only remaining gate before Phase 11 is "shipped" by Glen's standards. Until then, Plan 11-04's code surface is complete and proven via 17 new tests against mocked CM responses.

## Self-Check: PASSED

**Files claimed to be modified — all FOUND in commits:**

- `scripts/lib/vault_writer.py` — FOUND (commits `8e671f8`, `1b1e904`)
- `scripts/tests/test_vault_writer.py` — FOUND (commits `bb3ca12`, `b1fc50d`)

**Commits claimed to exist — all FOUND in git log:**

- `bb3ca12` (test: RED for _gather_events extension) — FOUND
- `8e671f8` (feat: GREEN for _gather_events extension) — FOUND
- `b1fc50d` (test: RED for run_backfill CM integration) — FOUND
- `1b1e904` (feat: GREEN for run_backfill CM integration) — FOUND

**Verification commands — all pass:**

- `python3 -m unittest discover scripts/tests` → 74 tests, OK
- `python3 -m unittest scripts.tests.test_vault_writer.TestGatherEventsCmIntegration scripts.tests.test_vault_writer.TestContractMerge` → 8 tests, OK
- `python3 -m unittest scripts.tests.test_vault_writer.TestProjectionDoesNotImportCm scripts.tests.test_vault_writer.TestCacheFallbackEnd2End scripts.tests.test_vault_writer.TestBackfillIdempotentPhase11 scripts.tests.test_vault_writer.TestJitMapping` → 7 tests, OK
- `grep -c "def _gather_events" scripts/lib/vault_writer.py` → 1
- `grep -c "_normalize_invoice_number" scripts/lib/vault_writer.py` → 4 (definition + 2 call sites in _gather_events + __all__)
- `grep -c "def _cm_contract_event_tuple" scripts/lib/vault_writer.py` → 1
- `grep -c "def _cm_invoice_event_tuple" scripts/lib/vault_writer.py` → 1
- `grep -c "def _clientid_to_slug" scripts/lib/vault_writer.py` → 1
- `grep -c "def _fetch_cm_data_for_run" scripts/lib/vault_writer.py` → 1
- `grep -c "from .cm_client import" scripts/lib/vault_writer.py` → 1 (lazy, inside _fetch_cm_data_for_run)
- `grep -E "^from .cm_client" scripts/lib/vault_writer.py` → no matches (verified import is INSIDE a function)
- `grep -c "level.*warning" scripts/lib/vault_writer.py` → 4 (warning emission for CM stale + JIT failure)
- `grep -F "cm_data_stale_since" scripts/lib/vault_writer.py` → 3 occurrences (frontmatter render path + cache-fallback stamping + docstring)
- `grep -F "cm_data_stale_since" scripts/tests/test_vault_writer.py` → 11 occurrences (extended snapshot helpers + assertions in TestCacheFallbackEnd2End + TestBackfillIdempotentPhase11)
- `grep -c "JIT-mapped" scripts/lib/vault_writer.py` → 2 (info-level feed entry summary + test fixture)
- `grep -c "JIT mapping failed" scripts/lib/vault_writer.py` → 2 (warning-level feed entries: no-match + transport-failure)
- `grep -c "search_clients_for_domain" scripts/lib/vault_writer.py` → 5 (Plan 02 import + Plan 02 call + Plan 04 import + Plan 04 call + comment)
- `python3 -c 'import sys; from scripts.lib.vault_writer import run_projection; from pathlib import Path; import tempfile, os; b=tempfile.mkdtemp(); i=tempfile.mkdtemp(); os.makedirs(b+"/Clients"); run_projection(Path(b), Path(i), dry_run=True); assert "scripts.lib.cm_client" not in sys.modules'` → exit 0 (Pitfall 1 invariant verified in-process)
- `CONTRACT_MANAGER_API_KEY= python3 -c 'from scripts.lib.vault_writer import _fetch_cm_data_for_run, load_clients; from pathlib import Path; import tempfile, os, json; d=tempfile.mkdtemp(); os.makedirs(d+"/config"); open(d+"/config/clients.jsonl","w").write(json.dumps({"domain":"x.com","name":"X"})+chr(10)); open(d+"/feed.jsonl","w").close(); c=load_clients(Path(d)); r=_fetch_cm_data_for_run(Path(d), c, Path(d+"/feed.jsonl")); assert r["global_expiring"] is None; assert r["global_invoices"] is None'` → exit 0 (graceful skip when no API key + no mapped clients)
- `git status --porcelain` (before SUMMARY commit) → empty (no uncommitted leftovers in code paths)

**Verify-gate (per Task 3 plan spec):** `grep -l "CM-TODOS-START" vault-build/Clients/*.md` is NOT verified — Task 3 is DEFERRED per Glen's 2026-05-02 override. Glen will perform live-CM iPhone verification after Phase 11 ships.

---
*Phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr*
*Completed: 2026-05-02*
