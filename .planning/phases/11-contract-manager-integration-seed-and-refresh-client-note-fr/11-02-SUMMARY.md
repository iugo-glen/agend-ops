---
phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr
plan: 02
subsystem: infra
tags: [contract-manager, vault-writer, mcp-client, json-rpc, retry, cache, mapping, phase-11]

# Dependency graph
requires:
  - plan: 01
    provides: schemas/feed-entry.json level enum extended with "warning"; data/.cm-cache.json gitignored; sync-obsidian.sh fails fast on missing CONTRACT_MANAGER_API_KEY; render_frontmatter accepts cm_extra/cm_stale_since
provides:
  - scripts/lib/cm_client.py (CM JSON-RPC client + retry + cache + adapter + mapping helper)
  - scripts/lib/vault_writer.py --mode map-cm-clients + run_map_cm_clients (D-G1 idempotent mapping pass)
affects: [11-03, 11-04, future cm-cache writers, future CM-sourced frontmatter populators]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-network-seam test isolation: tests patch _cm_post (production wrapper), not urllib.request.urlopen at the bottom"
    - "Lazy-import inside function body (run_map_cm_clients imports cm_client) — Mac daemon's project-to-icloud path NEVER loads cm_client (T-11-02-08 mitigation)"
    - "JSON-RPC tools/call envelope: method=tools/call, params={name, arguments} — wraps the high-level tool name; single _cm_post handles both tools/call and tools/list"
    - "Retry-After-once semantics: D-A3 retries 3 times with 1s/5s/30s; on CmRateLimitError, sleeps for retry_after_seconds first, then re-attempts via the regular delay loop"
    - "Cache fallback-only with corruption tolerance: load_cache returns skeleton on missing OR malformed JSON; never raises (Pitfall: don't make cache the source of truth)"
    - "Idempotent atomic full-file rewrite: rec.get('cm_client_id') gate prevents re-querying; whole-file rewrite via _atomic_write (Pattern 1 reuse)"

key-files:
  created:
    - scripts/lib/cm_client.py
    - scripts/tests/test_cm_client.py
  modified:
    - scripts/lib/vault_writer.py
    - scripts/tests/test_vault_writer.py

key-decisions:
  - "Lazy-import cm_client INSIDE run_map_cm_clients (not at vault_writer module top) — Mac daemon's project-to-icloud path never loads cm_client.py, isolating the network surface from systems that have no API key"
  - "search_clients_for_domain queries the second-level domain stem (e.g. 'propertycouncil' for 'propertycouncil.com.au') and prefers exact website-substring match over name-based query — CM stores websites with assorted prefixes (https://, www.), so substring beats name fuzzy-match"
  - "Cache `load_cache` defensively `setdefault('global', {})` and `setdefault('by_client', {})` even when schema_version matches — guards against half-written caches from a future writer that drops a key"
  - "TestCmClient uses lower-cased header lookup (`headers[k.lower()]`) — urllib.request.Request normalises header names internally; matching the plan's literal `request_obj.headers['Authorization']` would fail with KeyError"

patterns-established:
  - "Phase 11 lazy-import discipline: any new CM-touching helper imports cm_client INSIDE its function body. vault_writer.py module-top imports must remain CM-free. Test for it: `python3 -c 'import scripts.lib.vault_writer; assert \"scripts.lib.cm_client\" not in sys.modules'`"
  - "JSON-RPC test seam: production code splits 'envelope construction + HTTP transport' (`_cm_post`) from 'retry policy' (`call_with_retry`). Tests patch `_cm_post` for retry tests; only the envelope tests patch `urllib.request.urlopen`. Future MCP clients should mirror this seam."
  - "Failed-mapping warning shape: type=system, level=warning, trigger=manual (not 'hook' — map-cm-clients is run manually by Glen on Coolify, not by a sync hook). Plan 03+ should respect this trigger taxonomy when adding new manual modes."

requirements-completed: []
# Note: INTL-01, CM-CLIENT, CM-MAPPING from the plan frontmatter remain partially open
# until Task 3 (the human mapping pass on Coolify) executes. Code surface is complete;
# the data outcome is deferred per Glen 2026-05-02 override.

# Metrics
duration: 5min
completed: 2026-05-02
---

# Phase 11 Plan 02: CM Client + Mapping Pass Summary

**Plan 02 lands the JSON-RPC client (`scripts/lib/cm_client.py`) and the mapping orchestrator (`vault_writer --mode map-cm-clients`) — Task 3 (Glen running the mapping pass on Coolify) is auto-approved and DEFERRED per Glen's 2026-05-02 override; the code surface is complete and Glen will populate `cm_client_id` after Phase 11 ships.**

## Performance

- **Duration:** ~5 min (including TDD red/green for both tasks)
- **Started:** 2026-05-02T13:41:03Z
- **Completed:** 2026-05-02T13:46:11Z
- **Tasks:** 2 of 3 fully executed (Task 3 deferred per AUTO_MODE override)
- **Tests:** 31 (Phase 10 baseline) → 45 (after Task 1) → 49 (after Task 2). All pass.
- **Files created:** 2 — `scripts/lib/cm_client.py`, `scripts/tests/test_cm_client.py`
- **Files modified:** 2 — `scripts/lib/vault_writer.py`, `scripts/tests/test_vault_writer.py`

## Accomplishments

### Task 1 — `scripts/lib/cm_client.py` (TDD)

- `_cm_post(method, params, api_key)` — single network seam. Builds JSON-RPC 2.0 envelope, wraps high-level tool calls in `tools/call` (`{name, arguments}`) unless `method == "tools/list"`, sends `Authorization: Bearer ...` header, parses 401/429/200-with-error/200-success uniformly. On 429: parses `Retry-After` header and raises `CmRateLimitError(retry_after_seconds)`.
- `call_with_retry(method, params, api_key)` — D-A3 retry loop. 3 retries with 1s/5s/30s; on `CmRateLimitError`, sleeps `retry_after_seconds` first then continues; raises last error after exhaustion (caller falls back to cache).
- `load_cache` / `write_cache` / `gc_cache_orphans` / `_empty_cache` — D-F1 cache I/O. Atomic whole-file write via `vault_writer._atomic_write` (canonical helper, no re-implementation). Tolerates missing files, malformed JSON, and missing sub-keys without raising.
- `cm_summary_to_frontmatter_extra(summary)` — D-B1 / D-B2 / D-B-MOD-REVISED / D-C2-REVISED adapter. Empty scalars → `""`, empty arrays → `[]`, `deployed_modules = sorted({c["name"] for c in activeContracts})`, `sites = []` always.
- `search_clients_for_domain(domain, api_key)` — domain-stem query + website-substring match for the mapping pass. Falls back to first match if no website substring-match.
- 14 new tests across 4 classes (TestCmClient, TestCallWithRetry, TestCmCache, TestCmSummaryAdapter) — RED first (commit `be4cbc0`), GREEN after (commit `4ec3d2f`).

### Task 2 — `vault_writer.py --mode map-cm-clients` (TDD)

- `run_map_cm_clients(data_root, dry_run, feed_path)` — idempotent D-G1 mapping pass. Reads each record from `data/config/clients.jsonl`; if `cm_client_id` is already set, increments `unchanged` and continues. Otherwise calls `search_clients_for_domain`. On `CmTransportError` / `CmRpcError` / `cm_id is None`: appends a `system`/`warning`/`manual` feed entry and continues to the next record. Returns `{queried, mapped, unchanged, failed}` stats. Dry-run path prints `[dry-run] would search...` and writes nothing.
- argparse `--mode` choices extended with `"map-cm-clients"`.
- `main()` dispatch chain extended with the `elif args.mode == "map-cm-clients"` branch.
- `__all__` extended with `"run_map_cm_clients"`.
- **Lazy import:** `from . import cm_client as _cm` lives INSIDE `run_map_cm_clients`, NOT at vault_writer module top. Verified: `import scripts.lib.vault_writer` does NOT load `scripts.lib.cm_client` (T-11-02-08 mitigation; Mac daemon's `--mode project-to-icloud` path stays CM-free).
- 4 new tests in `TestRunMapCmClients` class — RED first (commit `dab3f54`), GREEN after (commit `609d24e`).

### Task 3 — DEFERRED PER GLEN OVERRIDE 2026-05-02

Auto-approved per AUTO_MODE chain flag and Glen's explicit "don't stop! I'll add keys later" directive. Original task type was `checkpoint:human-verify`; converted to auto-approval to land the code surface non-stop. Glen will perform the human-only steps AFTER Phase 11 ships:

1. Mint a CM API key at https://contracts.agend.info/settings/mcp (UI workflow, plaintext shown once).
2. Inject `CONTRACT_MANAGER_API_KEY` into Coolify's environment configuration for the agend-ops service.
3. SSH to Coolify (`ssh root@103.249.238.17`, `cd /opt/agend-ops`) and run `python3 -m scripts.lib.vault_writer --mode map-cm-clients --data-root data`.
4. Commit the populated `data/config/clients.jsonl` and run `bash scripts/push-and-sync.sh`.

The verify-gate command `grep -c '"cm_client_id"' data/config/clients.jsonl` returns 0 today — that is EXPECTED and acceptable under the deferral. No manual `cm_client_id` injection was attempted, because the value must come from a real CM `search_clients` response (which requires the real API key).

## Task Commits

| Task        | Phase | Commit    | Type    |
| ----------- | ----- | --------- | ------- |
| Task 1 — cm_client tests (failing) | RED   | `be4cbc0` | test    |
| Task 1 — cm_client implementation  | GREEN | `4ec3d2f` | feat    |
| Task 2 — TestRunMapCmClients (failing) | RED | `dab3f54` | test |
| Task 2 — run_map_cm_clients implementation | GREEN | `609d24e` | feat |

REFACTOR phase: skipped for both tasks — code is minimal, single-responsibility, and mirrors the plan verbatim. Adding cleanup churn would only obscure intent.

## Files Created/Modified

- **`scripts/lib/cm_client.py`** (NEW, 229 lines) — JSON-RPC client, retry loop, cache I/O + GC, summary adapter, mapping helper, three exception classes. Module-top imports: stdlib only (`json`, `time`, `urllib.error`, `urllib.request`, `pathlib`) plus `_atomic_write` and `now_iso_with_offset` re-exports from `vault_writer`.
- **`scripts/tests/test_cm_client.py`** (NEW, 199 lines) — 4 test classes, 14 tests covering envelope shape, retry timing, cache I/O, GC, and adapter behavior. All mocks at the seam (`scripts.lib.cm_client.urllib.request.urlopen` for envelope tests; `scripts.lib.cm_client._cm_post` for retry tests).
- **`scripts/lib/vault_writer.py`** (MODIFIED, +103 / -2 lines) — Added `run_map_cm_clients` function (after `run_incremental`, before the projection-mode section header) with lazy `from . import cm_client`. Extended argparse `--mode` choices and `main()` dispatch chain. Extended `__all__`.
- **`scripts/tests/test_vault_writer.py`** (MODIFIED, +92 lines) — Appended `TestRunMapCmClients` class with 4 tests (mapped / idempotent / per-client failure / dry-run). All mocks at `scripts.lib.cm_client.search_clients_for_domain`.

## Decisions Made

- **Lazy-import inside `run_map_cm_clients` instead of module-top.** Plan section "Notes on the implementation choices" recommends lazy import explicitly, but the original action prose used `from .cm_client import ... INSIDE the function`. I went with `from . import cm_client as _cm; search_clients_for_domain = _cm.search_clients_for_domain` — same lazy-load semantics, but the test mock at `scripts.lib.cm_client.search_clients_for_domain` resolves via attribute lookup at call time (not at import time), which is what the test expects. A `from .cm_client import search_clients_for_domain` would have bound the function ref at import time and broken the mock pattern.
- **Test header lookup uses `headers[k.lower()]`.** The plan's `request_obj.headers['Authorization']` would fail because urllib.request.Request normalises header keys internally (the actual key in `req.headers` is `Authorization` but the lookup is case-sensitive against the original storage). Using `{k.lower(): v for k, v in request_obj.headers.items()}` plus a `headers["authorization"]` lookup is robust to either capitalisation. Verified via the passing test.
- **Adapter `cm_summary_to_frontmatter_extra` returns plain `dict[str, ...]` with key order: deployed_modules, contract_start, contract_end, primary_contact, sites.** Same key set as Plan 01's `render_frontmatter` `cm_extra` consumer. Plan 03 (frontmatter populator) can pass this dict straight through without re-mapping.
- **`run_map_cm_clients` writes `level: "warning"` not `level: "info"` for "no CM match" cases** — matches Plan 01's enum extension intent. A "no match" is a data-quality flag Glen needs to see; demoting it to `info` would bury it in the dashboard.

## Deviations from Plan

**Two minor deviations (Rule 1 / Rule 3 — both auto-fixable):**

1. **[Rule 3 — Blocking issue] Lazy-import idiom changed from `from .cm_client import` to `from . import cm_client as _cm`.** The plan's literal action used `from .cm_client import search_clients_for_domain, CmTransportError, CmRpcError`. This works at runtime, but the test mock uses `mock.patch("scripts.lib.cm_client.search_clients_for_domain")`, which patches the attribute on the `cm_client` module. Using `from .cm_client import search_clients_for_domain` would bind the symbol at function-import time (the first call), and subsequent test mocks would not affect the bound reference inside `run_map_cm_clients`. Switched to `from . import cm_client as _cm` so the symbol is resolved fresh on every call via `_cm.search_clients_for_domain`. Result: tests pass; the lazy-import discipline (T-11-02-08) is preserved (cm_client is still NOT imported at vault_writer module top).

2. **[Rule 1 — Test correctness] TestCmClient header assertion changed from `request_obj.headers["Authorization"]` to a lowercased lookup.** urllib.request.Request stores headers via internal normalisation; the case-sensitive direct-key lookup is fragile across Python versions. Switched to `{k.lower(): v for k, v in request_obj.headers.items()}["authorization"]`. Same assertion intent, robust to header-capitalisation behavior.

Both deviations were tracked, applied, verified by re-running the test suite (49/49 passing), and disclosed here. No CLAUDE.md rules violated. No deletion of unrelated files. No additional files modified beyond `files_modified`.

## Issues Encountered

- **None blocking.** TDD RED gates produced clean failure signals (`ModuleNotFoundError` and `ImportError`); GREEN gates flipped both clean. Self-check below confirms all expected file-and-commit artifacts.
- **AUTO_MODE handling:** the prompt explicitly directed Task 3 to be auto-approved. The verify gate's `grep -c '"cm_client_id"' data/config/clients.jsonl` returns 0 (expected per Glen 2026-05-02 override). I did NOT manually edit `data/config/clients.jsonl` to fake a `cm_client_id` — those values must come from a real CM `search_clients` response, which requires the real API key, and Glen will perform that step on Coolify.

## TDD Gate Compliance

Both tasks honored RED → GREEN → (no REFACTOR needed) discipline:

**Task 1:**
- **RED:** `be4cbc0` — 14 tests fail with `ModuleNotFoundError: No module named 'scripts.lib.cm_client'`
- **GREEN:** `4ec3d2f` — All 14 tests pass; full suite 45/45.

**Task 2:**
- **RED:** `dab3f54` — 4 tests fail with `ImportError: cannot import name 'run_map_cm_clients' from 'scripts.lib.vault_writer'`
- **GREEN:** `609d24e` — All 4 tests pass; full suite 49/49.

**REFACTOR:** Skipped for both. The code mirrors the plan verbatim and is single-responsibility; refactoring would introduce churn without improving readability.

## Threat Model Compliance

- **T-11-02-01 (API key leakage in feed.jsonl):** ✅ Verified `grep -E "Bearer|cm_live_" data/feed.jsonl` returns no matches. `_cm_post` raises `CmTransportError(f"HTTP {e.code}: {e.reason}")` and `CmRpcError(f"{err.get('code')}: {err.get('message')}")` — neither echoes the Bearer header or API key. The `details.error` block in warning entries records `str(e)` only.
- **T-11-02-04 (DoS via hot-loop on rate limit):** ✅ `call_with_retry` honours `Retry-After` once, then falls into the regular 1s/5s/30s loop. After exhaustion, `run_map_cm_clients`'s per-client `try/except` continues to the next domain — no infinite loop. Mapping pass on 3 records well under any rate limit.
- **T-11-02-05 (clients.jsonl partial-write corruption):** ✅ `_atomic_write` (vault_writer.py:296-322) used for the whole-file rewrite; tempfile + os.replace + fsync(file) + fsync(dir) ensures crash-safe rollover.
- **T-11-02-08 (Mac daemon accidentally invokes CM):** ✅ Verified via `python3 -c 'import scripts.lib.vault_writer; assert "scripts.lib.cm_client" not in sys.modules'` — passes. `cm_client` is NOT loaded by importing `vault_writer`. Lazy-import inside `run_map_cm_clients` keeps Mac-side `--mode project-to-icloud` path CM-free.
- **T-11-02-02 / T-11-02-03 / T-11-02-06 / T-11-02-07:** Inherit from plan posture (cache fallback-only; cache is gitignored by Plan 01; CM is Glen's own server; mapping idempotency).

No new threat surface introduced beyond the threat register. No `## Threat Flags` section needed.

## User Setup Required

**For Glen (post-Phase 11 ship):**

1. **Mint CM API key** at https://contracts.agend.info/settings/mcp.
   - Service: `mcp`
   - Format: `cm_live_<48_hex>`
   - Save plaintext immediately (shown once; bcrypt-hashed server-side).
2. **Inject into Coolify env** for the agend-ops service:
   - Coolify dashboard → service → Environment Variables
   - `CONTRACT_MANAGER_API_KEY=<the_minted_key>`
   - Restart the service so the new env propagates.
3. **Run the mapping pass on Coolify:**
   ```bash
   ssh root@103.249.238.17
   cd /opt/agend-ops
   python3 -m scripts.lib.vault_writer --mode map-cm-clients --data-root data
   ```
4. **Verify and commit:**
   ```bash
   cat data/config/clients.jsonl
   git add data/config/clients.jsonl
   git commit -m "feat(11): populate cm_client_id via CM mapping pass"
   bash scripts/push-and-sync.sh
   ```
5. **For any failed domain:** Check `data/feed.jsonl` for `level: "warning"` entries with `summary: "map-cm-clients: failed for <domain>"` or `"no CM match for <domain>"`. Plan 03/04 will surface these in the CM-TODOS section.

## Next Phase Readiness

- **Plan 03 (CM frontmatter merge)** can call `cm_summary_to_frontmatter_extra(summary)` and pass the resulting dict directly to `render_frontmatter(client, ts, cm_extra={...})`. The 5-key shape matches Plan 01's accepted kwargs.
- **Plan 03/04 cache writers** can call `load_cache(Path("data/.cm-cache.json"))` (returns skeleton on missing/corrupt) → mutate → `write_cache(...)` (atomic). The cache is already gitignored by Plan 01.
- **Plan 04 fallback path** can call `call_with_retry("get_client_summary", {"clientId": cm_id}, api_key)`. On exhaustion, catch `CmTransportError` / `CmRpcError` / `CmRateLimitError` and read from cache.
- **Glen's manual mapping pass** (Task 3 deferred work) is the only remaining gate before Plan 03+ can read populated `cm_client_id` from `data/config/clients.jsonl` in production. Until then, Plan 03+ test fixtures should mock `cm_client_id` rather than read from the real file.

## Self-Check: PASSED

**Files claimed to be created/modified — all FOUND in commits:**

- `scripts/lib/cm_client.py` — FOUND (commit 4ec3d2f)
- `scripts/tests/test_cm_client.py` — FOUND (commit be4cbc0)
- `scripts/lib/vault_writer.py` — FOUND (commit 609d24e)
- `scripts/tests/test_vault_writer.py` — FOUND (commit dab3f54)

**Commits claimed to exist — all FOUND in git log:**

- `be4cbc0` (test: RED for cm_client) — FOUND
- `4ec3d2f` (feat: GREEN for cm_client) — FOUND
- `dab3f54` (test: RED for run_map_cm_clients) — FOUND
- `609d24e` (feat: GREEN for run_map_cm_clients) — FOUND

**Verification commands — all pass:**

- `python3 -m unittest discover scripts/tests` → 49 tests, OK
- `python3 -c 'from scripts.lib.cm_client import _cm_post, call_with_retry, cm_summary_to_frontmatter_extra, search_clients_for_domain, CmTransportError'` → exit 0
- `python3 -m scripts.lib.vault_writer --help | grep -F map-cm-clients` → matches one line
- `grep -c '"map-cm-clients"' scripts/lib/vault_writer.py` → 2 (argparse + dispatch)
- `grep -c "def run_map_cm_clients" scripts/lib/vault_writer.py` → 1
- `grep -c "run_map_cm_clients" scripts/lib/vault_writer.py` → 3 (definition + dispatch + __all__)
- `python3 -c 'import scripts.lib.vault_writer; assert "scripts.lib.cm_client" not in sys.modules'` → exit 0 (T-11-02-08 mitigation holds)
- `git status --porcelain` (before SUMMARY commit) → empty (no uncommitted leftovers in code paths)

**Verify-gate (per Task 3 plan spec):** `grep -c '"cm_client_id"' data/config/clients.jsonl` → 0. EXPECTED per Glen 2026-05-02 override (Task 3 deferred). NOT a self-check failure.

---
*Phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr*
*Completed: 2026-05-02*
