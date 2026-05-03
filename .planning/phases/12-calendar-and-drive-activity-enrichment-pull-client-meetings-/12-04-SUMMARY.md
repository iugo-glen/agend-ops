---
phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings
plan: 04
subsystem: vault-writer
tags: [phase-12, vault-writer, workspace, orchestration, cache-fallback, idempotency, pitfall-1, integration, oauth, ship-ready]

# Dependency graph
requires:
  - phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings
    plan: 01
    provides: GOOGLE_MCP_CREDENTIALS_DIR env validation in sync-obsidian.sh; .gitignore entries for data/.cal-cache.json + data/.drive-cache.json; load_clients aliases plumbing; EMOJI_BY_KIND meeting/doc kinds
  - phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings
    plan: 02
    provides: scripts/lib/workspace_client.py (call_with_retry, load_cache, write_cache, format_calendar_event_for_log, _load_workspace_credentials, _walk_drive_for_clients, WorkspaceTransportError/RpcError/AuthExpiredError); endpoint allowlist; OAuth refresh-on-expiry
  - phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings
    plan: 03
    provides: _gather_events extension with cal_events + drive_files kwargs; _match_drive_filename_to_client + _has_word_boundary_match + _DRIVE_FILENAME_STOP_LIST; _route_calendar_event_to_slug; _cal_meeting_event_tuple + _drive_doc_event_tuple
  - phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr
    plan: 04
    provides: _fetch_cm_data_for_run (rename target); cm_data_stale_since stamping pattern; TestProjectionDoesNotImportCm subprocess-based negative test (model for Phase 12 mirror); per-tool try/except CM cache fallback shape; D-A3 retry+cache+warning verbatim model
provides:
  - scripts/lib/vault_writer.py _fetch_external_data_for_run (orchestrates CM + Calendar + Drive in one pass; per-tool try/except + cache fallback + workspace_data_stale_since stamping + 401 refresh-on-call + stop-list-only counter)
  - scripts/lib/vault_writer.py _fetch_cm_data_for_run backward-compat alias preserving Phase 11's 17 mocked tests with zero modification (`_fetch_cm_data_for_run = _fetch_external_data_for_run`)
  - scripts/lib/vault_writer.py render_frontmatter accepts additive workspace_stale_since kwarg (renders workspace_data_stale_since YAML key when set; no-op when None — Phase 10/11 callers unaffected)
  - scripts/lib/vault_writer.py run_backfill threads cal_events + drive_files through _gather_events; threads workspace_stale_since through render_frontmatter
  - scripts/lib/vault_writer.py run_projection INVARIANT block extended for T-12-04-01 (workspace_client added to the Pitfall 1 ban list alongside cm_client)
  - scripts/tests/test_vault_writer.py 4 new test classes: TestStopListSilentSkipCounter (2 tests), TestWorkspaceCacheFallbackEnd2End (3 tests), TestBackfillIdempotentPhase12 (1 test), TestProjectionDoesNotImportWorkspace (1 test)
  - scripts/tests/test_vault_writer.py extended _snapshot helpers in TestBackfillIdempotent + TestBackfillIdempotentPhase11 (additive workspace_data_stale_since strip — Phase 10/11 idempotency still green under Phase 12)
  - Phase 12 SHIP-READY status: after this plan lands, `bash scripts/sync-obsidian.sh --backfill` on Coolify produces vault notes with 📅 meeting + 📝 doc lines alongside Phase 2/3/7/11 entries
affects: [phase-12-ship (Glen runs sync-obsidian.sh on Coolify), future client-routing modules (Slack/Linear) inheriting the per-source dedup-set + lazy-import + cache-fallback pattern, future Mac-side parity if ever needed]

# Tech tracking
tech-stack:
  added: []  # zero new third-party deps; preserves Phase 10/11/12-02/03 zero-extra-dep precedent
  patterns:
    - "Function-rename + backward-compat alias pattern: `_fetch_cm_data_for_run = _fetch_external_data_for_run` at module bottom preserves Phase 11's 17 mocked tests verbatim while extending the function's responsibility. Mirrors how Python stdlib evolves names without breaking imports (e.g., asyncio.async → asyncio.ensure_future)."
    - "Restructured early-return: Phase 11's `if not api_key: return early_dict` shape is kept for the CM portion (gracefully skip with warning when env unset), but Phase 12 inverts the structure so the WORKSPACE block runs INDEPENDENTLY of CM status. Both paths produce a complete `out` dict with all 11 keys."
    - "Per-tool isolated try/except + cache-fallback (Phase 11 D-A3 inheritance, extended to 3 tools): each of CM (Phase 11) + Calendar (Phase 12) + Drive (Phase 12) gets its own try/except wrapping its call_with_retry / walker. One tool down does not block the other two; per-tool cache files mean a poisoned drive-cache cannot affect calendar fallback."
    - "OAuth refresh-on-401 nested try/except: outer try catches transport/RPC errors → cache fallback; inner try catches WorkspaceAuthExpiredError → refresh + retry once; if refresh itself raises WorkspaceTransportError, the outer catch fires and falls back to cache. Two-level structure keeps the happy path linear."
    - "workspace_stale_since via min(stale_candidates): older of (cal_stale_at, drive_stale_at) becomes the surfaced timestamp. Both fresh → None; one stale → that timestamp; both stale → older. Single rendered frontmatter key reflects the SOURCE OF TRUTH staleness."
    - "Subprocess-based negative test for Pitfall 1 inheritance: a single subprocess runs `run_projection(...)` AND prints both 'WS_NOT_LOADED' AND 'CM_NOT_LOADED' to stdout. The test asserts BOTH appear — pinning T-12-04-01 (Phase 12) AND T-11-04-01 (Phase 11 inheritance) in one regression-resistant check."
    - "Stop-list-only counter as caller responsibility (Plan 12-03's pure-router design): the matcher returns None for both stop-list-only AND no-match cases. The orchestrator re-runs `_match_drive_filename_to_client` on each adapted file and increments the counter when matcher returns None AND any stop-list token has a word-boundary match. Audit trail lives at the orchestration layer, matcher stays pure for unit-testability."

key-files:
  created: []
  modified:
    - scripts/lib/vault_writer.py
    - scripts/tests/test_vault_writer.py

key-decisions:
  - "Function rename via backward-compat alias (NOT shim wrapper) — `_fetch_cm_data_for_run = _fetch_external_data_for_run` at module bottom is a plain attribute alias. Both names resolve to the same function object (`is` comparison is True). Phase 11's 17 mocked tests that import `_fetch_cm_data_for_run` continue to pass without modification because they're invoking the SAME function — just under the legacy name. This is structurally cleaner than a shim wrapper that would cost an extra stack frame and make tracebacks confusing."
  - "Restructured CM early-return: instead of the original `if not api_key: return X`, the new structure initializes `out` up front with ALL 11 keys (Phase 11's 3 + Phase 12's 4 NEW + the by_domain dict pre-populated with empty buckets), then `if api_key and has_mapped_clients:` gates ONLY the CM fetch logic. The Workspace block runs UNCONDITIONALLY (gated separately by `GOOGLE_MCP_CREDENTIALS_DIR`). This means a fresh install with no CM key still gets Calendar + Drive data; a Coolify deployment with no Workspace creds still gets CM data; both env vars unset → still returns a complete dict, just with all values None or 0."
  - "Hoisted `_warn` closure above the CM gate — Phase 11's `_warn` lived inside the `if api_key:` branch, so the CM-skip path couldn't emit warnings. Phase 12 needs `_warn` accessible from BOTH the CM block AND the new Workspace block, so it's hoisted to immediately after the `out` initialization. The hoist is structurally additive: Phase 11 callers see no behaviour change because the CM block is unchanged below it."
  - "Per-tool cache files (data/.cal-cache.json + data/.drive-cache.json) — RESEARCH Q6 verdict: separate files per tool, mirroring Phase 11's data/.cm-cache.json. Rationale: corruption isolation (a poisoned drive-cache.json doesn't break Calendar fallback), atomic write granularity (each cache rewrites independently), and gitignore additions are explicit (Plan 12-01 added both lines). Phase 12's caches use the same `{schema_version, global, by_client}` shape as Phase 11; the load_cache/write_cache helpers in workspace_client.py implement it 1:1 with cm_client.py."
  - "workspace_stale_since rendered AFTER cm_data_stale_since — when both stale-since fields are present (rare but possible: CM down + Workspace down in the same run), the frontmatter renders `cm_data_stale_since:` first then `workspace_data_stale_since:` because ruamel.yaml preserves dict insertion order and the conditional branch in render_frontmatter writes them in that order. Tested explicitly in TestWorkspaceCacheFallbackEnd2End by asserting both keys appear in the rendered text and `stale_ts` matches the cached fetched_at."
  - "Subprocess test asserts BOTH 'WS_NOT_LOADED' AND 'CM_NOT_LOADED' in one run — the subprocess imports `run_projection` from vault_writer, calls it with `dry_run=True`, then prints two strings. The test asserts both strings appear. Single subprocess execution catches BOTH Phase 12 T-12-04-01 (workspace_client never enters sys.modules) AND Phase 11 T-11-04-01 (cm_client never enters sys.modules). Cheaper than two separate subprocesses + structurally proves the invariants are truly orthogonal (one regression doesn't mask the other)."
  - "Snapshot helper extension (additive): both `TestBackfillIdempotent._snapshot_managed` and `TestBackfillIdempotentPhase11._snapshot` had their filter chains extended with `not ln.startswith('workspace_data_stale_since:')`. Under Phase 10/11 fixtures the new clause is a no-op (those tests don't trigger Workspace fallback), so Phase 10/11 idempotency tests stay green. Under Phase 12 fixtures (TestBackfillIdempotentPhase12 + TestWorkspaceCacheFallbackEnd2End) the clause is necessary — without it, byte-equality across two runs would fail when workspace_data_stale_since is stamped."

patterns-established:
  - "Phase-12 closing wave shape: previous waves (12-01 bootstrap, 12-02 client module, 12-03 routing surface) culminate in Wave 4 — the orchestrator that wires them together. Wave 4 is small (~370 net lines added; mostly inside one function) but high-leverage: it's the ONLY place all three Phase 12 sub-systems converge. Future phases should follow the same shape (bootstrap → client → render → orchestrator) when integrating multi-component external systems."
  - "Backward-compat alias for function rename — preserves test surface verbatim while letting the new name carry an extended docstring + signature semantics. Future renames in the codebase (e.g., when Phase 13 might rename _fetch_external_data_for_run again to absorb a Slack/Linear source) should use this idiom rather than shim wrappers."
  - "Subprocess-based Pitfall 1 negative test, ONE subprocess pins MULTIPLE invariants — Phase 11's `TestProjectionDoesNotImportCm` ran one subprocess to check one invariant. Phase 12's `TestProjectionDoesNotImportWorkspace` runs one subprocess to check TWO invariants (cm_client AND workspace_client). Future regressions in either fail the same test. Pattern scales: a future Phase that adds a third lazy-imported helper (Slack? Linear?) appends a third `print()` to the subprocess code + a third assertion to the test."
  - "Mock at scripts.lib.workspace_client.<symbol> — even though _fetch_external_data_for_run does `from .workspace_client import call_with_retry as ws_call_with_retry`, the lazy import re-runs each call. Each function entry, the import retrieves the (potentially patched) attribute on the workspace_client module. Tests that mock `scripts.lib.workspace_client.call_with_retry` therefore see their mocks honoured. Pattern verified by all 5 new tests in this plan working with this mocking shape."

requirements-completed:
  - INTL-01-CAL  # Calendar live read + cache fallback + workspace_data_stale_since stamping + privacy-filter pipeline (D-D1+D-D2 from Plan 12-02; routing from Plan 12-03; orchestration here)
  - INTL-01-DRIVE  # Drive live read + cache fallback + workspace_data_stale_since stamping + privacy-filter pipeline (D-D3 from Plan 12-02; routing from Plan 12-03; orchestration + stop-list audit trail here)
  - INTL-01-PRIVACY  # Privacy filters wired in via workspace_client adapters; orchestrator never bypasses them; D-D4 vault-is-Glen-only acceptance applied
  - INTL-01-WORKSPACE-CACHE  # Per-tool .cal-cache.json + .drive-cache.json end-to-end: load on entry, write on exit, cache-on-failure populates `out`; gitignored per Plan 12-01
  - INTL-01-PROJECTION-ISOLATION  # T-12-04-01 enforced: subprocess test verifies workspace_client NOT in sys.modules after run_projection; Pitfall 1 inheritance from Phase 11 verified in same subprocess

# Metrics
duration: ~7min
completed: 2026-05-03
---

# Phase 12 Plan 04: Wave 4 Orchestrator + Final Integration Summary

**Final wave landed: `_fetch_external_data_for_run` orchestrates CM (Phase 11) + Calendar + Drive (Phase 12) in one pass, with per-tool try/except + cache fallback + workspace_data_stale_since stamping + 401 refresh-on-call + stop-list-only counter. `run_backfill` threads cal+drive through `_gather_events`. `render_frontmatter` accepts the additive `workspace_stale_since` kwarg. Subprocess-based negative test pins T-12-04-01 (Mac daemon never imports workspace_client) AND verifies T-11-04-01 inheritance (cm_client also never imported) in one execution. Phase 12 is now SHIPPABLE.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-05-03T02:14:57Z
- **Completed:** 2026-05-03T02:21:55Z
- **Tasks:** 2 (both TDD: RED → GREEN)
- **Files modified:** 2 (1 production + 1 test)
- **Tests:** 190 → 197 (+7 new tests across 4 new test classes; 2 existing snapshot helpers extended additively)
- **Lines changed:** scripts/lib/vault_writer.py +384 / -169 (net +215; mostly the renamed function with restructured early-return + Calendar/Drive blocks); scripts/tests/test_vault_writer.py +418 / -5

## Accomplishments

- **`_fetch_cm_data_for_run` renamed to `_fetch_external_data_for_run`** with a one-line backward-compat alias at module bottom (`_fetch_cm_data_for_run = _fetch_external_data_for_run`). Both names resolve to the same function object (`assert _fetch_cm_data_for_run is _fetch_external_data_for_run`); Phase 11's 17 mocked tests continue to pass without modification.
- **Restructured early-return** — Phase 11's original `if not api_key: return early_dict` shape would have only produced 3 of the 7 keys Phase 12 needs. The new shape initializes `out` with ALL 11 keys up front, then gates ONLY the CM fetch logic behind `if api_key and has_mapped_clients:`. The Workspace block runs INDEPENDENTLY (gated separately by `GOOGLE_MCP_CREDENTIALS_DIR`). Result: a fresh install with no CM key still gets Calendar+Drive; a Coolify deployment with no Workspace creds still gets CM; both unset → all 11 keys present with sensible None/0 values.
- **`_warn` closure hoisted above the CM gate** — needed because Phase 12's Workspace block also emits warnings (e.g., "Workspace credentials path unset"). Hoisted to immediately after the `out` initialization so both CM and Workspace blocks share the same closure. Structurally additive — Phase 11 callers see no behaviour change.
- **Calendar fetch block** — 90d window (`now - 90d` to `now + 30d` per D-B1), `singleEvents=true` for recurrence expansion, explicit `fields=...` clause requesting `visibility` + `attendees` (D-D1+D-A2 routing prerequisites), per-event filtering via `format_calendar_event_for_log` BEFORE caching (post-filter cache shape; D-D1+D-D2 cannot be bypassed by a future caller misreading the cache), cache fallback on `WorkspaceTransportError`/`WorkspaceRpcError`, OAuth 401 → ONE refresh + retry via nested try/except.
- **Drive fetch block** — single-call against `_walk_drive_for_clients(access_token)` (the walker already applies D-D3 + D-A3-REVISED scope), cache fallback + 401 refresh-on-call mirroring Calendar's shape.
- **`workspace_stale_since` stamping** — `min(cal_stale_at, drive_stale_at)` from per-source `cached_block.fetched_at` when EITHER fell back; None on full freshness. Surfaced via additive `workspace_stale_since` kwarg on `render_frontmatter`, which renders `workspace_data_stale_since: <iso>` in the frontmatter dict (after `cm_data_stale_since` if both present; ruamel.yaml preserves insertion order).
- **Stop-list-only counter** — D-A4-REVISED summary feed entry. Post-fetch walk over `out["global_drive"]["files"]`; for each file where `_match_drive_filename_to_client` returns None AND any token in `_DRIVE_FILENAME_STOP_LIST` matches via `_has_word_boundary_match` → increment `drive_stop_list_skipped`. ONE info-level feed entry per sync (NOT per-file) when count > 0; no entry when count is 0. Audit trail lives at the orchestration layer; the matcher stays pure (Plan 12-03 design preserved).
- **Per-tool cache persistence at function exit** — both `data/.cal-cache.json` and `data/.drive-cache.json` written via `workspace_client.write_cache` (atomic temp+rename; gitignored per Plan 12-01). Best-effort: cache write failure emits a warning but does not fail the sync.
- **`run_backfill` threading** — three changes: (1) `external_data = _fetch_external_data_for_run(...)` replaces the old CM-only call, (2) `_gather_events(...)` now receives `cal_events=external_data.get("global_calendar"), drive_files=external_data.get("global_drive")`, (3) `render_frontmatter(...)` now receives `workspace_stale_since=external_data.get("workspace_stale_since")`. Per-domain bucket access unchanged from Phase 11 (Phase 12 doesn't add per-domain buckets — Calendar/Drive route inside `_gather_events`).
- **`run_projection` INVARIANT block extended for T-12-04-01** — explicitly bans both `cm_client` AND `workspace_client` imports. Names `TestProjectionDoesNotImportCm` AND `TestProjectionDoesNotImportWorkspace` as the negative tests.
- **`__all__` extension** — `_fetch_external_data_for_run` added (Phase 12 renamed orchestrator); `_fetch_cm_data_for_run` kept as the backward-compat alias name. Both importable; both `is` the same function object.
- **Lazy import discipline preserved** — `from .workspace_client import (...)` lives ONLY inside `_fetch_external_data_for_run`. `grep -E "^from .workspace_client|^import .*workspace_client" scripts/lib/vault_writer.py` returns empty. The lazy import block uses `as` aliases (`call_with_retry as ws_call_with_retry`, `load_cache as ws_load_cache`, etc.) to avoid name collision with the existing `from .cm_client import call_with_retry, load_cache, ...` lazy block.

## Task Commits

Each task was executed TDD (RED + GREEN) with `--no-verify` (worktree parallel execution).

1. **Task 1 RED — `06af8dd`** — `test(12-04): RED — TestStopListSilentSkipCounter for _fetch_external_data_for_run`
   - Two new tests: `test_orchestrator_counts_stop_list_skips` (5 files, 2 stop-list-only → count=2 + ONE info feed entry) and `test_orchestrator_no_stop_list_entry_when_zero_skips` (all files real-client → no entry). Both fail RED with `ImportError: cannot import name '_fetch_external_data_for_run' from 'scripts.lib.vault_writer'`.
2. **Task 1 GREEN — `44b75dc`** — `feat(12-04): GREEN — _fetch_external_data_for_run + Calendar/Drive fetch + cache fallback`
   - Renames `_fetch_cm_data_for_run` → `_fetch_external_data_for_run`; restructures early-return; hoists `_warn`; adds Workspace gate + Calendar block + Drive block + workspace_stale_since stamping + stop-list counter + cache writes; updates `render_frontmatter` signature; threads in `run_backfill`; updates `run_projection` INVARIANT block; extends `__all__`. The 2 RED tests pass; full suite goes from 190 → 192.
3. **Task 2 GREEN — `a0820c1`** — `test(12-04): GREEN — Workspace cache fallback + Phase 12 idempotency + Pitfall 1 inheritance`
   - Three new test classes: `TestWorkspaceCacheFallbackEnd2End` (3 tests), `TestBackfillIdempotentPhase12` (1 test), `TestProjectionDoesNotImportWorkspace` (1 test). Plus extends `TestBackfillIdempotent._snapshot_managed` and `TestBackfillIdempotentPhase11._snapshot` to also strip `workspace_data_stale_since:` (additive — Phase 10/11 idempotency tests stay green). All 5 new tests pass on first run; full suite 192 → 197.

## TDD Gate Compliance

Two tasks completed RED → GREEN cycles. Gate sequence verified in git log:

| Task | RED commit | GREEN commit | Tests added | Status |
|------|-----------|-------------|-------------|--------|
| 1    | `06af8dd` | `44b75dc`   | 2           | PASS   |
| 2    | (combined RED+GREEN — see Notes) | `a0820c1`   | 5           | PASS   |

**Note on Task 2 RED+GREEN combined:** the plan permitted the three test classes in Task 2 to be appended after Task 1's deliverables landed (per the plan's `<action>` block: "tests should mostly GREEN against Task 1's deliverables, with the exception of the snapshot extension..."). The snapshot extensions to TestBackfillIdempotent + TestBackfillIdempotentPhase11 are forward-compat (additive filter clauses with no fixture trigger in those classes), so they don't constitute a discriminating RED. The 3 NEW Workspace-cache-fallback tests + 1 Phase 12 idempotency test + 1 subprocess Pitfall-1 test all pass on first GREEN run because Task 1's `_fetch_external_data_for_run` already correctly emits the workspace_data_stale_since stamp + warning feed entry + cache-on-success behaviours.

REFACTOR commits not required — production code shipped clean on first GREEN of each task.

## Verification Results

```
$ python3 -m unittest discover scripts/tests
Ran 197 tests in 0.284s
OK
```

Per-class breakdown (Phase 12-04 only):

| Test Class                              | Tests |
|-----------------------------------------|-------|
| `TestStopListSilentSkipCounter`         | 2     |
| `TestWorkspaceCacheFallbackEnd2End`     | 3     |
| `TestBackfillIdempotentPhase12`         | 1     |
| `TestProjectionDoesNotImportWorkspace`  | 1     |
| **Total NEW**                           | **7** |

Plus 2 existing snapshot helpers extended (not new tests, but additive filter clauses):

| Existing Class                          | Snapshot helper | Phase 12 extension          |
|-----------------------------------------|-----------------|-----------------------------|
| `TestBackfillIdempotent`                | `_snapshot_managed` | strip `workspace_data_stale_since:` |
| `TestBackfillIdempotentPhase11`         | `_snapshot`     | strip `workspace_data_stale_since:` |

**Acceptance-criteria spot-checks:**

- `python3 -c 'from scripts.lib.vault_writer import _fetch_cm_data_for_run, _fetch_external_data_for_run; assert _fetch_cm_data_for_run is _fetch_external_data_for_run'` → exit 0 (backward-compat alias preserves Phase 11 tests).
- `grep -c "def _fetch_external_data_for_run" scripts/lib/vault_writer.py` → 1.
- `grep -c "_fetch_cm_data_for_run = _fetch_external_data_for_run" scripts/lib/vault_writer.py` → 1.
- `grep -c "from .workspace_client import" scripts/lib/vault_writer.py` → 1 (the lazy import inside the orchestrator).
- `grep -E "^from .workspace_client|^import .*workspace_client" scripts/lib/vault_writer.py` → empty (no top-level import; Pitfall 1 invariant preserved).
- `grep -c "workspace_data_stale_since" scripts/lib/vault_writer.py` → 3 (frontmatter dict key + docstring mentions).
- `grep -c "T-12-04-01" scripts/lib/vault_writer.py` → 2 (run_projection INVARIANT block + lazy-import block comment).
- `grep -c "workspace_data_stale_since" scripts/tests/test_vault_writer.py` → 10 (assertions + 3 snapshot-strip clauses).
- `grep -c "TestProjectionDoesNotImportWorkspace" scripts/tests/test_vault_writer.py` → 1.
- Smoke test: `CONTRACT_MANAGER_API_KEY= GOOGLE_MCP_CREDENTIALS_DIR= python3 -c '...'` → returns `{global_calendar: None, global_drive: None, drive_stop_list_skipped: 0, ...}` (graceful skip with all 11 keys present).
- `git diff 660e575..HEAD --name-only` → exactly `scripts/lib/vault_writer.py` and `scripts/tests/test_vault_writer.py` (no scope leak).

## Deviations from Plan

### Auto-fixed Issues

None — the plan was executed exactly as written. Each task's `<action>` block was followed verbatim. Auto-fix rules (Rules 1–4) had no triggers: no bugs surfaced, no critical functionality was missing, no blocking issues encountered, no architectural decisions needed.

### Notes (non-deviations)

**1. Restructured early-return shape compared to Phase 11.** The plan's `<action>` Step 1 instructed "RENAME `_fetch_cm_data_for_run` to `_fetch_external_data_for_run`. Add a one-line backward-compat alias at module-bottom..." and Step 2 instructed "INSIDE the renamed function, ADD Calendar + Drive fetch blocks. The structure follows Phase 11's pattern exactly: ... NEW: graceful-skip gate for Workspace data...". Phase 11's existing function had an `if not api_key: return early_dict` early-return on line 1449. Adding the Calendar+Drive blocks AFTER the early-return would mean those blocks are unreachable when CM is gracefully skipped (a common Coolify scenario when CONTRACT_MANAGER_API_KEY is unset). The orchestrator must run Workspace INDEPENDENTLY of CM status. Solution: the early-return was restructured into an `if api_key and has_mapped_clients:` block that wraps ONLY the CM fetch logic, with Workspace block running unconditionally below. The `out` dict is initialized up front with ALL 11 keys so both CM-skip and CM-active paths produce a complete structure. The `_warn` closure was hoisted above the CM gate so Workspace can emit warnings too. Net result: behaviour-preserving for Phase 11 (the CM-skip path still returns the same structure Phase 11 returned, just augmented with Phase 12 keys initialized to None/0); behaviour-extending for Phase 12 (Workspace runs even when CM is skipped). This is structurally cleaner than placing the Workspace block AFTER the early-return because that would have required duplicating the Workspace block in TWO branches (early-return path AND main path) or wrapping the entire function body in a try/finally. The plan's Step 2 framing ("INSIDE the renamed function, ADD Calendar + Drive fetch blocks") is honoured — they are inside the function, just after a hoisted `out`/`_warn` and gated by their own env-var check rather than placed after a CM-only early-return. No deviation in observable behaviour or test surface.

**2. Task 2 had no discriminating RED commit.** The plan permitted this: "TDD ordering: append the three test classes RED first (they reference modules that exist but the orchestration code paths under test were just landed in Task 1; tests should mostly GREEN against Task 1's deliverables...". The 3 Workspace-cache-fallback tests + 1 Phase 12 idempotency test + 1 subprocess Pitfall-1 test all passed on first run because Task 1's `_fetch_external_data_for_run` already correctly emits the workspace_data_stale_since stamp + warning feed entry + cache-on-success behaviours. The snapshot-helper extensions to TestBackfillIdempotent + TestBackfillIdempotentPhase11 are forward-compat (additive filter clauses with no fixture that triggers Workspace fallback in those classes), so those tests stay green with or without the extension. Combined the test additions + snapshot extensions into one commit. This is the documented behaviour for additive-change TDD where the GREEN gate proves "the new behaviour exists and works"; no discriminating RED is necessary because Task 1 was the discriminating change.

## Authentication Gates

None during this plan's execution — all OAuth flow is exercised through unit tests with mocked `_load_workspace_credentials`, `call_with_retry`, and `_walk_drive_for_clients`. Live OAuth blob mint happens off the executor critical path (Glen's hardened-workspace MCP setup + Coolify env injection — both deferred to ship-checklist post-12-04).

The Phase 12 ship checklist (per plan output): Glen will ship Phase 12 by:
1. SSH to Coolify (`ssh root@103.249.238.17`); confirm `GOOGLE_MCP_CREDENTIALS_DIR` is exported and the OAuth blob is at `${GOOGLE_MCP_CREDENTIALS_DIR}/glen@iugo.com.au.json`.
2. Run `bash scripts/sync-obsidian.sh --backfill`. Expect output `vault_writer backfill complete: {'clients_written': N, 'events_routed': M}` with M materially higher than the Phase 11 baseline.
3. Inspect a regenerated client note (e.g. `cat vault-build/Clients/property-council-australia.md`); verify Activity Log has 📅 lines (recent meetings within 90d) AND 📝 lines (recently-modified Drive docs).
4. `grep "📄" vault-build/Clients/*.md | grep -v "Contract"` returns no matches (D-C3 verification anchor).
5. Confirm `data/.cal-cache.json` and `data/.drive-cache.json` exist on Coolify AND are NOT in `git status` (gitignored per Plan 12-01).
6. Optional: temporarily clear `GOOGLE_MCP_CREDENTIALS_DIR`, re-run backfill — expect ONE warning feed entry per fetch attempt + `workspace_data_stale_since` stamps + cache-sourced data; restore env var afterwards.
7. Commit + push regenerated `vault-build/Clients/*.md` and `data/feed.jsonl` via `bash scripts/push-and-sync.sh`.
8. Open Obsidian on iPhone. Confirm: 📅 meeting and 📝 doc emoji render correctly alongside existing 📧✅💰📄; Glen-owned Overview/Decisions sections preserved; CM-TODOS + Usage sections (Phase 11) intact.

## Threat Flags

No new security surface beyond what was anticipated in the plan's `<threat_model>` section. All 12 threats (T-12-04-01 through T-12-04-12) have their mitigations realized in code as specified:

| Threat | Mitigation Realized |
|--------|---------------------|
| T-12-04-01 (Mac daemon imports workspace_client — Pitfall 1 inheritance) | workspace_client imported LAZILY inside `_fetch_external_data_for_run` only. run_projection (Mac mode) does not call `_fetch_external_data_for_run`. `TestProjectionDoesNotImportWorkspace` subprocess test verifies BOTH `scripts.lib.workspace_client` AND `scripts.lib.cm_client` NOT in sys.modules after run_projection. |
| T-12-04-02 (cal/drive cache poisoning) | Both caches gitignored (Plan 12-01); fallback-only (live calls always tried first); per-tool isolation (corrupt cal cache doesn't poison drive fallback); adapter extracts only typed fields; single-tenant Coolify host. |
| T-12-04-03 (OAuth token leakage via warning feed entries) | `_warn` records `details: {"error": str(e)}` where `e.args` contain only sanitized strings ("HTTP 401: Unauthorized", "credentials refresh failed: ..."). Bearer header NEVER leaks because `WorkspaceTransportError.args` carries only the formatted exception message from workspace_client.py (verified Plan 12-02). |
| T-12-04-04 (Calendar event title prompt-injection in markdown render) | Title flows verbatim into `f"{title} — {N} attendees"` via `_cal_meeting_event_tuple` (Plan 12-03). htmlLink hardcoded to Google's own URL. D-D4 acceptance: vault is Glen-only; impact is "broken-looking link" not exfil. |
| T-12-04-05 (invoice/contract dedup keys collide with Calendar/Drive event IDs) | Calendar event IDs are opaque Google strings; invoice IDs are local NDJSON-row IDs; namespaces don't share. Pitfall 4's case-fold-only invoice dedup unaffected. Plan 12-03's per-source `seen_event_ids` + `seen_file_ids` are local-scope sets in `_gather_events`. |
| T-12-04-06 (Workspace rate limit DoS) | call_with_retry honours Retry-After (Plan 12-02); Phase 12 issues at most 1 Calendar + 1 Drive call per sync = 2 calls/sync, far below Calendar's 500/100s/user limit; cache fallback covers exhaustion; per-tool try/except in orchestrator ensures one tool's rate-limit doesn't kill the other. |
| T-12-04-07 (workspace_data_stale_since timestamp leaks last-fresh info) | Accepted — same posture as Phase 11 T-11-04-07 for cm_data_stale_since. Acceptable signal in Glen-only vault (D-D4). |
| T-12-04-08 (Idempotency drift between Phase 12 runs) | `_gather_events` Phase 12 extension is deterministic (event/file ID dedup; alphabetical first-match-wins routing; D-B2 top-20 cap on pre-sorted input). `_snapshot_managed` strips `workspace_data_stale_since:`. `TestBackfillIdempotentPhase12.test_two_runs_byte_identical_with_workspace_data` pins the invariant. |
| T-12-04-09 (concurrent vault_writer + stalled OAuth refresh corrupts credentials) | Accepted — flock in sync-obsidian.sh serialises sync runs (Phase 11 T-11-04-09 inheritance); `_atomic_write` (temp+rename) for credentials rewrite ensures no partial blob visible. |
| T-12-04-10 (lazy import block leaks workspace_client membership via grep) | Accepted — `grep -c "from .workspace_client" scripts/lib/vault_writer.py` returns 1 (the documented lazy-import inside the orchestrator). Public-by-construction. The SECRECY constraint is "Mac daemon doesn't EXECUTE the import path" which the subprocess test verifies. |
| T-12-04-11 (OAuth refresh during backfill against DNS-poisoned oauth2.googleapis.com) | TLS via urllib.request.urlopen validates Google's certificate chain by default. Defense-in-depth: refresh failure raises WorkspaceTransportError → cache fallback + warning feed entry. |
| T-12-04-12 (workspace_stale_since cache poisoning injects malicious YAML) | `workspace_stale_since` rendered via ruamel.yaml scalar — special chars are quoted/escaped, not interpreted as YAML structure. Same posture as Phase 11's `cm_data_stale_since`. |

Defense-in-depth chain (the renderer is the FINAL transform of untrusted Workspace bytes into vault notes):
1. workspace_client._workspace_get JSON-decodes the response (no eval).
2. Privacy filters (D-D1/D-D2/D-D3) drop high-risk events/files BEFORE returning to vault_writer.
3. Adapters extract only typed fields (no `**event` spread).
4. Routing helpers in Plan 12-03 use deterministic alphabetical first-match-wins (no LLM-driven inference).
5. Event-tuple builders in Plan 12-03 interpolate verbatim into D-12 line shapes (no template-string exec).
6. Renderers (existing render_log_line, Phase 10) generate plain markdown.
7. Obsidian renders as markdown (no script exec). The vault is Glen-only (D-D4); the only failure mode of an injected title is "broken-looking link", not exfil.

## Patterns Established for Future Phases

- **Function-rename + backward-compat alias**: when a function's responsibility expands beyond its name's scope, rename + leave an alias. Future renames of `_fetch_external_data_for_run` (e.g., to absorb a Slack source in Phase 13) should follow the same idiom.
- **Restructured early-return for multi-source orchestrators**: Phase 11's `if not api_key: return early_dict` pattern works for single-source fetches but breaks down when N independent sources need to run unconditionally. Initialize `out` with all keys up front, gate per-source logic with per-source env-var checks, run each source independently.
- **Subprocess-based negative test for Pitfall 1, MULTIPLE invariants in ONE subprocess**: Phase 11's TestProjectionDoesNotImportCm pinned one invariant. Phase 12's TestProjectionDoesNotImportWorkspace pins TWO (workspace_client AND cm_client) in one subprocess. Future regressions in either fail the same test. Pattern scales to N invariants by adding more `print()` lines + assertions.
- **Per-tool cache files (data/.cm-cache.json + data/.cal-cache.json + data/.drive-cache.json)**: each external source gets its own cache file so corruption is isolated. Same JSON shape (`{schema_version, global, by_client}`) so the load_cache/write_cache helpers can be 1:1 across modules. Future external sources (Slack? Linear?) follow the same pattern.

## Self-Check: PASSED

Files claimed to be modified:
- `scripts/lib/vault_writer.py` — FOUND (modified in commit 44b75dc)
- `scripts/tests/test_vault_writer.py` — FOUND (modified in commits 06af8dd + a0820c1)

Commits claimed to exist:
- `06af8dd` (Task 1 RED) — FOUND in git log
- `44b75dc` (Task 1 GREEN) — FOUND in git log
- `a0820c1` (Task 2 GREEN — combined snapshot extension + 3 new test classes) — FOUND in git log

Verification commands:
- `python3 -m unittest discover scripts/tests` → 197 tests pass (190 baseline + 7 new)
- `python3 -c 'from scripts.lib.vault_writer import _fetch_cm_data_for_run, _fetch_external_data_for_run; assert _fetch_cm_data_for_run is _fetch_external_data_for_run; print("OK")'` → exit 0 ("OK")
- `grep -c "def _fetch_external_data_for_run" scripts/lib/vault_writer.py` → 1
- `grep -c "_fetch_cm_data_for_run = _fetch_external_data_for_run" scripts/lib/vault_writer.py` → 1
- `grep -E "^from .workspace_client|^import .*workspace_client" scripts/lib/vault_writer.py` → empty (Pitfall 1 invariant)
- `grep -c "from .workspace_client import" scripts/lib/vault_writer.py` → 1 (lazy import inside orchestrator)
- `grep -c "workspace_data_stale_since" scripts/lib/vault_writer.py` → 3
- `grep -c "T-12-04-01" scripts/lib/vault_writer.py` → 2
- `grep -c "workspace_data_stale_since" scripts/tests/test_vault_writer.py` → 10
- `grep -c "TestProjectionDoesNotImportWorkspace" scripts/tests/test_vault_writer.py` → 1
- Smoke test (graceful skip): exits 0 with all 11 keys present in `_fetch_external_data_for_run` output.
- `git diff 660e575..HEAD --name-only` → exactly `scripts/lib/vault_writer.py` + `scripts/tests/test_vault_writer.py` (no scope leak)

## Next Phase Readiness

- **Phase 12 SHIP-READY**: with this plan landed, all four verification anchors from CONTEXT.md (lines 224-233) are satisfied at the test/structural level. The remaining ship steps are deferred-verification on Coolify (per Authentication Gates section above).
- **Phase 13 (TBD)**: future external sources (Slack, Linear, etc.) should follow the patterns established here — own client module under `scripts/lib/`, own cache file under `data/`, lazy import inside `_fetch_external_data_for_run` (or its successor), subprocess negative test for Pitfall 1 inheritance.
- **No pending blockers from this plan** — all 7 new tests pass; Phase 10/11/12-01/02/03 tests stay green; backward-compat alias preserves the 17 Phase 11 mocked tests verbatim; Pitfall 1 invariant verified via subprocess for both cm_client and workspace_client.

---
*Phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings*
*Completed: 2026-05-03*
