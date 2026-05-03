---
phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings
plan: 02
subsystem: workspace-client
tags: [phase-12, workspace, calendar, drive, mcp-client, tdd, retry, cache, oauth, allowlist, privacy-filter]

# Dependency graph
requires:
  - phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr
    provides: scripts/lib/cm_client.py shape (single seam + retry + cache + adapters), scripts/tests/test_cm_client.py mock-response idiom, vault_writer._atomic_write + now_iso_with_offset re-export pattern, RETRY_DELAYS=(1,5,30) D-A3 retry shape
  - phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings
    plan: 01
    provides: GOOGLE_MCP_CREDENTIALS_DIR env (consumed by _credentials_path), .gitignore data/.cal-cache.json + data/.drive-cache.json (consumed by write_cache callers in Wave 3)
provides:
  - scripts/lib/workspace_client.py — single-network-seam HTTP client for Google Calendar v3 + Drive v3 with retry+cache+OAuth+privacy-filter
  - 18 public/test-importable names: _workspace_get, call_with_retry, load_cache, write_cache, gc_cache_orphans, _empty_cache, format_calendar_event_for_log, format_drive_file_for_log, _is_internal, _load_workspace_credentials, _refresh_workspace_token, _credentials_path, _walk_drive_for_clients, _check_endpoint_allowed, WorkspaceTransportError, WorkspaceRpcError, WorkspaceRateLimitError, WorkspaceAuthExpiredError, WORKSPACE_ALLOWED_ENDPOINTS, WORKSPACE_ALLOWED_ENDPOINT_PREFIXES, RETRY_DELAYS, CACHE_SCHEMA_VERSION, OAUTH_TOKEN_REFRESH_URL, OAUTH_REFRESH_LEEWAY_S, GLEN_INTERNAL_DOMAINS
  - D-X1 trust boundary enforced by THREE independent layers (allowlist constant + runtime gate + CI grep-lint test)
  - D-D1/D-D2/D-D3 privacy filters applied INSIDE workspace_client adapters; vault_writer never sees pre-filter data
  - OAuth refresh-on-expiry flow with atomic credentials-blob rewrite (best-effort)
  - Single OAUTH-POST: write-verb carve-out documented and tested
affects: [12-03 _gather_events extension, 12-04 _fetch_external_data_for_run lazy-import block, future Mac-side parity (Wave 4 if shipped)]

# Tech tracking
tech-stack:
  added: []  # zero new third-party deps; preserves Phase 10/11 zero-extra-dep precedent
  patterns:
    - "Phase 11 cm_client.py shape mirrored 1:1 with three Phase-12-specific additions: strict endpoint allowlist (constant + runtime gate + CI grep-lint), OAuth token loader with automatic refresh on expiry, per-tool privacy-filter adapters (D-D1/D-D2/D-D3) applied INSIDE workspace_client before returning to vault_writer"
    - "OAUTH-POST: comment marker as a defence-in-depth carve-out — the SOLE non-GET method= line in the module is annotated so the grep-lint test can structurally distinguish the documented OAuth refresh from any future regression"
    - "Subclass exception hierarchy (WorkspaceAuthExpiredError ⊂ WorkspaceTransportError) lets retry callers catch the broader transport error generically while higher-level orchestration intercepts the specific 401 path for token refresh"
    - "Frozenset for endpoint allowlist + tuple for prefix matches — immutable by construction; cannot be mutated by attacker-controlled code at import time"
    - "Adapter functions returning None on filter MATCH and dict on PASS — caller pattern: `if (adapted := format_*(raw)) is not None: out.append(adapted)`. Preserves D-D1/D-D2/D-D3 invariant that vault_writer never sees pre-filter records"

key-files:
  created:
    - scripts/lib/workspace_client.py
    - scripts/tests/test_workspace_client.py
  modified: []

key-decisions:
  - "workspace_client.py mirrors cm_client.py 1:1 — same module structure (constants → exceptions → seam → retry → cache → adapters), same docstring style, same _atomic_write delegation pattern, same `(0,) + RETRY_DELAYS` retry-loop idiom. Phase 11 patterns are now established convention; deviating would cost review time without value."
  - "Endpoint allowlist enforced by THREE independent layers (constant + runtime gate + CI grep-lint with OAUTH-POST: carve-out marker) — defence in depth. T-12-02-03/04/11 mitigation chain is structurally redundant by design."
  - "WorkspaceAuthExpiredError as subclass of WorkspaceTransportError — `except WorkspaceTransportError` still catches 401 but `except WorkspaceAuthExpiredError` lets call_with_retry short-circuit retry consumption. Tested explicitly: retry consumed=0 on auth-expired path."
  - "OAuth refresh fires when expiry < now + 60s (OAUTH_REFRESH_LEEWAY_S) — RESEARCH Pitfall 6 mitigation. A long backfill that crosses the 1-hour OAuth boundary triggers a refresh on the next call, not after the call fails 401. The 60s window is generous enough to absorb network round-trips between the check and the API call."
  - "Drive walker ships as a single-call list against drive/v3/files (NOT recursive) — D-A3-REVISED scope (Glen's Drive root is flat, ~100 items). max_depth/page_size carry forward-compat semantics so a future Phase 12.x can introduce nested-folder walking without breaking the call signature. RESEARCH Anti-Patterns explicitly forbids hand-rolled recursive walks."
  - "Adapter functions filter BEFORE returning to caller (return None on MATCH) — vault_writer never sees pre-filter records, so D-D1/D-D2/D-D3 cannot be bypassed by a caller forgetting to filter. Phase 11 cm_summary_to_frontmatter_extra returns adapted dict unconditionally; Phase 12 inverts this because privacy filters are correctness-critical."
  - "_is_internal defaults empty/no-@ emails to internal (defensive: fail-closed against the no-external-attendee filter). A malformed attendee email shouldn't accidentally make a personal calendar event appear external."

patterns-established:
  - "Phase-12 single-seam mirror discipline: a new Wave 1 client module under scripts/lib/ replicates Phase 11 cm_client.py 1:1 with named additions for cross-module-specific concerns. Future client modules (Slack, Linear, etc.) follow the same template."
  - "TDD RED→GREEN→REFACTOR per task — RED commits fail with ImportError on absent symbol; GREEN commits pass all new tests AND existing tests; no REFACTOR commits required (fresh module written to spec)."
  - "Endpoint-allowlist defence-in-depth: any new HTTP client module shipping read-only by-construction MUST express the trust boundary as (a) immutable constant set, (b) runtime gate that raises before network call, (c) CI test that walks source for accidental regressions. The OAUTH-POST: marker is the canonical idiom for documented carve-outs."
  - "Adapter-with-filter return contract: per-tool response adapters return None on filter MATCH so callers cannot accidentally bypass privacy/safety filters by misreading the adapter signature. Phase 11's adapter (always-returns-dict) was acceptable for unfiltered CM responses; Phase 12 inverts this for privacy-critical surfaces."

requirements-completed:
  - INTL-01-CAL  # Workspace OAuth + endpoint allowlist + retry + cache scaffolding for Calendar v3 access
  - INTL-01-DRIVE  # Workspace OAuth + endpoint allowlist + retry + cache scaffolding for Drive v3 access
  - INTL-01-PRIVACY  # D-D1 (visibility OR no-external-attendees), D-D2 (>25 attendees), D-D3 (trashed/draft) filters applied at adapter boundary
  - INTL-01-WORKSPACE-CACHE  # load_cache/write_cache/gc_cache_orphans helpers (atomic, schema-versioned, corruption-tolerant) ready for per-tool cache files

# Metrics
duration: 8min
completed: 2026-05-03
---

# Phase 12 Plan 02: Workspace Client (Calendar + Drive REST seam) Summary

**Single-network-seam HTTP client built for Google Calendar v3 + Drive v3 — `scripts/lib/workspace_client.py` mirrors Phase 11 `cm_client.py` 1:1 with three Phase-12-specific additions: a strict endpoint allowlist enforced by constant + runtime gate + CI grep-lint test (D-X1 trust boundary), an OAuth token loader with automatic refresh on expiry (RESEARCH Pitfall 6), and per-tool privacy-filter adapters that apply D-D1/D-D2/D-D3 BEFORE returning to vault_writer.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-03T01:48:00Z
- **Completed:** 2026-05-03T01:56:17Z
- **Tasks:** 3 (all TDD: RED→GREEN per task)
- **Files created:** 2 (1 production, 1 test)
- **Tests:** 85 → 135 (+50 new tests across 7 new test classes)
- **Lines of code:** scripts/lib/workspace_client.py = 481 (with rich docstrings); scripts/tests/test_workspace_client.py = ~660

## Accomplishments

- **Single network seam** (`_workspace_get`): the ONE function in the module that touches the network. Tests at the seam level patch `urllib.request.urlopen`; tests at higher layers patch `_workspace_get`. Mirrors Phase 11 `_cm_post` test-isolation pattern verbatim.
- **D-X1 trust boundary enforced THREE ways**:
  1. `WORKSPACE_ALLOWED_ENDPOINTS = frozenset({"calendar/v3/calendars/primary/events", "drive/v3/files"})` + `WORKSPACE_ALLOWED_ENDPOINT_PREFIXES = ("drive/v3/files/",)` — intentionally narrow constant set.
  2. `_check_endpoint_allowed(api_path)` — runtime gate, FIRST line of `_workspace_get`. Disallowed paths short-circuit BEFORE any network call (test verifies `urlopen.assert_not_called()`).
  3. `TestWorkspaceClientEndpointAllowlist` — CI grep-lint walks every `["'](calendar|drive)/v3/...["']` string literal in the module source AND scans every non-comment line for `method="POST/PUT/PATCH/DELETE"` with the OAUTH-POST: carve-out marker excluded.
- **HTTP method hardcoded GET** — no POST/PUT/PATCH/DELETE codepath exists in the module except the lone documented OAuth refresh write to `oauth2.googleapis.com/token` (carve-out marker `# OAUTH-POST:` makes the line greppable; the carve-out is structurally distinct because the host is OUTSIDE the `googleapis.com/<api_path>` namespace).
- **Four exception classes**:
  - `WorkspaceTransportError` — network failure or non-2xx HTTP (other than 401, 429)
  - `WorkspaceRpcError` — Google API error envelope `{"error": {"code", "message"}}`
  - `WorkspaceRateLimitError(WorkspaceTransportError)` — 429; carries `retry_after_seconds`
  - `WorkspaceAuthExpiredError(WorkspaceTransportError)` — 401; caller refreshes OAuth and retries (NEW for Phase 12; no analog in cm_client because CM uses long-lived API keys)
- **D-A3 retry wrapper** (`call_with_retry`) — `(0,) + RETRY_DELAYS = (0, 1, 5, 30)` delay sequence; auth-expired propagates IMMEDIATELY (does not consume retries); rate-limit honours `Retry-After` once per call. Test enforces sleep-call sequence `[1, 5, 30]` and exactly 4 total `_workspace_get` calls on persistent failure.
- **Cache I/O** (`load_cache`, `write_cache`, `gc_cache_orphans`, `_empty_cache`) — byte-identical mirror of Phase 11 cm_client cache helpers. Atomic writes via `vault_writer._atomic_write` (single source of truth — same idiom used by all production state writes since Phase 10). Corruption tolerance: missing/corrupt JSON/schema-mismatch all return skeleton without raising. Defensive `setdefault("global", {})` and `setdefault("by_client", {})` for partial JSON.
- **Privacy filters at the adapter boundary**:
  - `format_calendar_event_for_log` applies **D-D2** (>25 attendees, cheapest check first), **D-D1 part 1** (visibility=private), **D-D1 part 2** (no external attendee). Returns adapter dict on PASS, `None` on filter MATCH. Carries event `id` for stable dedup downstream (Pitfall 4).
  - `format_drive_file_for_log` applies **D-D3** (trashed OR `.gdraft` extension OR case-sensitive `[DRAFT]` token). Returns adapter dict on PASS, `None` on MATCH. Carries file `id` for stable dedup. Lower-case `[draft]` is NOT filtered (D-D3 is case-sensitive per CONTEXT.md — `[DRAFT]` is Google's literal token).
- **`_is_internal` helper** — D-D1 part 2 attendee classification. Empty/no-@ emails default to internal (defensive — fail-closed against the no-external filter); primary-email match is case-insensitive; `iugo.com.au` host membership via `GLEN_INTERNAL_DOMAINS` frozenset.
- **OAuth token loader** (`_load_workspace_credentials`) — reads OAuth blob from `${GOOGLE_MCP_CREDENTIALS_DIR}/${GOOGLE_PRIMARY_EMAIL}.json` (env-var-overridable per Plan 12-01), normalises `Z` and `+00:00` expiry formats, refreshes if expiry < now + 60s (`OAUTH_REFRESH_LEEWAY_S`). On refresh, atomically rewrites the credentials blob with new access_token + new expiry so the next sync inherits the fresh token. Best-effort rewrite (OSError swallowed; in-memory token still works for the current sync).
- **OAuth refresh helper** (`_refresh_workspace_token`) — POSTs form-encoded body to `oauth2.googleapis.com/token`. The line carrying `method="POST"` has the `# OAUTH-POST:` carve-out marker. Maps HTTPError/URLError/decode/missing-fields all to `WorkspaceTransportError("credentials refresh failed: ...")`.
- **Drive walker** (`_walk_drive_for_clients`) — single-call list against `drive/v3/files` with the explicit `fields=files(id,name,mimeType,modifiedTime,webViewLink,lastModifyingUser,trashed,parents),nextPageToken` clause that surfaces `lastModifyingUser` (NOT in default response). q-clause excludes folders + trashed. orderBy=modifiedTime desc. supportsAllDrives=false (D-A3-REVISED My-Drive-only). Applies D-D3 via `format_drive_file_for_log`. `max_depth`/`page_size` carry forward-compat intent without current use.

## Task Commits

Each task was executed TDD (RED → GREEN) with `--no-verify` (worktree parallel execution).

1. **Task 1 RED — `fde6238`** — `test(12-02): RED tests for workspace_client transport seam, retry wrapper, endpoint allowlist`
   - `TestWorkspaceClient` (10 tests): URL/header construction, JSON unwrap (flat — not JSON-RPC), error mapping for 401/429 (Retry-After + 30s default)/500/network/Google-error-envelope, allowlist short-circuit, drive/v3/files/{id} prefix accept
   - `TestWorkspaceCallWithRetry` (4 tests): D-A3 1s/5s/30s sequence, auth-expired propagates without consuming retries, rate-limit honours Retry-After
2. **Task 1 GREEN — `71185a5`** — `feat(12-02): GREEN — workspace_client.py module with _workspace_get + call_with_retry + allowlist gate`
   - 14 tests pass; full suite: 85 → 99 (+14)
3. **Task 2 RED — `71e5113`** — `test(12-02): RED tests for cache I/O, _is_internal helper, calendar+drive adapters`
   - `TestWorkspaceCache` (6), `TestIsInternalHelper` (5), `TestCalendarEventAdapter` (9), `TestDriveFileAdapter` (7) — 27 tests fail with ImportError
4. **Task 2 GREEN — `6038964`** — `feat(12-02): GREEN — cache I/O + privacy-filter adapters (D-D1/D-D2/D-D3)`
   - 27 tests pass; full suite: 99 → 126 (+27)
5. **Task 3 RED — `241c960`** — `test(12-02): RED tests for OAuth token loader, Drive walker, endpoint allowlist grep-lint`
   - `TestOAuthTokenLoader` (4), `TestDriveWalker` (3), `TestWorkspaceClientEndpointAllowlist` (2) — 7 of 9 RED (the 2 allowlist tests pre-pass against the existing module, as documented in the commit; they will continue to pass once OAuth POST lands with the carve-out marker)
6. **Task 3 GREEN — `2dc4330`** — `feat(12-02): GREEN — OAuth token loader + refresh, Drive walker, endpoint allowlist source-of-truth`
   - 9 tests pass; full suite: 126 → 135 (+9; +50 over the 85-test starting baseline)

## TDD Gate Compliance

All three tasks completed RED → GREEN cycles. Gate sequence verified in git log:

| Task | RED commit | GREEN commit | Tests added | Status |
|------|-----------|-------------|-------------|--------|
| 1    | `fde6238` | `71185a5`   | 14          | PASS   |
| 2    | `71e5113` | `6038964`   | 27          | PASS   |
| 3    | `241c960` | `2dc4330`   |  9          | PASS   |

No REFACTOR commits required — all GREEN implementations passed verification on first run.

The Task 3 RED phase included two tests (`TestWorkspaceClientEndpointAllowlist::test_only_allowlisted_endpoints_referenced` and `::test_no_write_verb_method_calls_present`) that pre-pass against the existing module because no non-allowlisted paths or write-verbs are present yet. The plan explicitly calls this out as acceptable: those tests are forward-looking guards that will continue to pass after Task 3 GREEN adds the OAuth POST (with the OAUTH-POST: carve-out marker). The discriminating tests (the 7 OAuth + Drive walker tests) all failed RED as required.

## Verification Results

```
$ python3 -m unittest discover scripts/tests
Ran 135 tests in 0.184s
OK
```

Per-class breakdown (Phase 12-02 only):

| Test Class                           | Tests |
|--------------------------------------|-------|
| `TestWorkspaceClient`                | 10    |
| `TestWorkspaceCallWithRetry`         |  4    |
| `TestWorkspaceCache`                 |  6    |
| `TestIsInternalHelper`               |  5    |
| `TestCalendarEventAdapter`           |  9    |
| `TestDriveFileAdapter`               |  7    |
| `TestOAuthTokenLoader`               |  4    |
| `TestDriveWalker`                    |  3    |
| `TestWorkspaceClientEndpointAllowlist`|  2    |
| **Total**                            | **50**|

Acceptance-criteria spot-checks:

- All required public symbols importable: `_workspace_get`, `call_with_retry`, `load_cache`, `write_cache`, `gc_cache_orphans`, `format_calendar_event_for_log`, `format_drive_file_for_log`, `_load_workspace_credentials`, `_refresh_workspace_token`, `_walk_drive_for_clients`, `WorkspaceTransportError`, `WorkspaceRpcError`, `WorkspaceRateLimitError`, `WorkspaceAuthExpiredError`, `WORKSPACE_ALLOWED_ENDPOINTS`, `WORKSPACE_ALLOWED_ENDPOINT_PREFIXES`, `RETRY_DELAYS`, `CACHE_SCHEMA_VERSION` (18 names) — confirmed via inline `python3 -c '...'`.
- `WORKSPACE_ALLOWED_ENDPOINTS` has exactly 2 entries (`calendar/v3/calendars/primary/events`, `drive/v3/files`) — intentionally narrow.
- `RETRY_DELAYS == (1, 5, 30)` — D-A3 inheritance from Phase 11.
- Stdlib-only imports + the lazy `from .vault_writer import _atomic_write, now_iso_with_offset`: zero new third-party deps, preserving the Phase 10/11 zero-extra-dep precedent.
- `grep -E 'method="(POST|PUT|PATCH|DELETE)"' scripts/lib/workspace_client.py | grep -v "OAUTH-POST"` returns no lines — only the documented OAuth carve-out is present.
- `vault_writer.py` has NO top-level `from .workspace_client import ...` — Pitfall 1 invariant preserved (Wave 3 will add the lazy import inside `_fetch_external_data_for_run`).
- One `OAUTH-POST:` carve-out marker in the entire file — single documented write-verb exception.

## Deviations from Plan

### Auto-fixed Issues

None — the plan was executed exactly as written. Tests RED → GREEN per task; all acceptance criteria passed on first attempt; no Rule-1/2/3 fixes required.

### Notes (non-deviations)

**1. Module size: 481 lines vs plan's "250-310 range" target.** The plan's line-count guidance was advisory ("mirrors cm_client.py's 229 lines + Phase 12 additions for OAuth/walker/allowlist"). The actual size reflects:
- 4 vs Phase 11's 3 exception classes (+ WorkspaceAuthExpiredError)
- Endpoint allowlist constants + runtime gate (Phase 11 has neither)
- OAuth refresh helper + path helper + loader (3 functions, ~95 lines combined; Phase 11 has none — uses long-lived API keys)
- Two adapter functions vs one (+ `_is_internal` helper)
- Drive walker (Phase 11 has no walker — CM is per-client lookup, not directory listing)

Of the 481 lines, ~93 are blank/comment/docstring-quote-only and ~388 are code. The added functionality is justified by the spec; this is not bloat. The grep-lint test (`TestWorkspaceClientEndpointAllowlist`) catches accidental scope creep at the endpoint level, which is the correctness-relevant constraint.

**2. Allowlist tests pre-pass during Task 3 RED.** As documented in the Task 3 RED commit message, two of the nine RED tests (`test_only_allowlisted_endpoints_referenced` and `test_no_write_verb_method_calls_present`) pre-pass against the module-as-of-Task-2 because no non-allowlisted endpoints or write-verbs exist yet. The plan explicitly anticipated and accepted this pattern (12-02-PLAN.md "TDD ordering for this task: append tests RED first... 7 of 9 tests fail RED"). The discriminating 7 OAuth + Drive-walker tests failed RED as required.

## Authentication Gates

None required during this plan's execution — all OAuth flow is exercised through unit tests with mocked `urllib.request.urlopen`. Live OAuth blob mint happens off the executor critical path (in Glen's hardened-workspace MCP setup, separate from this plan's scope).

The `_load_workspace_credentials` function will surface real authentication gates at Wave 3 ship time (12-04) when `_fetch_external_data_for_run` calls it during a sync run. If the OAuth blob is missing or the refresh-token is revoked, the function raises `WorkspaceTransportError` with a `"credentials missing"` or `"credentials refresh failed:"` prefix — Wave 3's caller catches this and falls back to cache + emits a `level: warning` feed entry per the threat-model T-12-02-02 mitigation plan.

## Threat Flags

No new security surface beyond what was anticipated in the plan's `<threat_model>` section. All 11 threats (T-12-02-01 through T-12-02-11) have their mitigations realized in code as specified:

| Threat | Mitigation Realized |
|--------|---------------------|
| T-12-02-01 (token leakage via logs) | Exception messages format `"HTTP {code}: {reason}"`, `"network: {reason}"`, `"decode: {error}"`, `"credentials refresh failed: ..."` — none echo Bearer header or the token value. |
| T-12-02-02 (refresh failure → stale data) | `_load_workspace_credentials` raises `WorkspaceTransportError("credentials refresh failed: ...")` — Wave 3 catches and falls back to cache. |
| T-12-02-03 (allowlist bypass via interpolation) | `_check_endpoint_allowed` is FIRST line of `_workspace_get`; param typed `str`. Grep-lint walks string literals. |
| T-12-02-04 (write-verb regression) | `test_no_write_verb_method_calls_present` scans every line; OAUTH-POST: carve-out is the SOLE allowed exception. |
| T-12-02-05 (calendar title markdown injection) | Adapter returns summary verbatim; renderer-side escape deferred to Wave 2 (D-D4 vault-is-Glen-only acceptance). |
| T-12-02-06 (cache poisoning) | Cache gitignored (Plan 12-01); fallback-only; adapter extracts only typed fields; single-tenant Coolify host. |
| T-12-02-07 (refresh storm) | `OAUTH_REFRESH_LEEWAY_S=60` window; refresh failure raises immediately (no retry inside `_refresh_workspace_token`). |
| T-12-02-08 (rate limit DoS) | `call_with_retry` honours `Retry-After`; cache fallback covers exhaustion; ~2 calls/sync vs Calendar's 500/100s/user limit. |
| T-12-02-09 (path leakage in error) | Accepted — path is non-secret. |
| T-12-02-10 (atomic credentials race) | `_atomic_write` (temp+rename); flock in sync-obsidian.sh serialises sync runs. |
| T-12-02-11 (privilege escalation via permissions.update) | Three-layer allowlist defence (constant + gate + grep-lint). |

## Patterns Established for Future Phases

- **Read-only-by-construction HTTP client**: any future client module shipping with explicit endpoint constraints SHOULD follow the constant + runtime gate + CI grep-lint triad. The `OAUTH-POST:` marker is the canonical idiom for documented write-verb carve-outs.
- **Adapter-with-filter return contract**: per-tool response adapters that need to apply privacy/safety filters return `None` on filter MATCH so callers cannot accidentally bypass filtering. (Phase 11's adapter — `cm_summary_to_frontmatter_extra` — returns dict unconditionally because there's no privacy filter; Phase 12 inverts this where filters are correctness-critical.)
- **OAuth-blob reuse pattern**: env-var-driven path discovery (`GOOGLE_MCP_CREDENTIALS_DIR` / `GOOGLE_PRIMARY_EMAIL`) lets Phase-12 code reuse the OAuth blob originally minted by hardened-workspace MCP without inheriting its stdio transport. The trust-boundary mechanism shifts (direct REST API instead of MCP tool calls) but the ownership boundary stays the same (OAuth blob lives at the same path).
- **TDD per-task RED→GREEN cycle**: each task is one RED commit (failing tests) + one GREEN commit (implementation). No combined commits, no REFACTOR commits when GREEN passes first try. Six commits total for three tasks.

## Self-Check: PASSED

- File `scripts/lib/workspace_client.py` exists (verified)
- File `scripts/tests/test_workspace_client.py` exists (verified)
- Commit `fde6238` (Task 1 RED) exists in git log
- Commit `71185a5` (Task 1 GREEN) exists in git log
- Commit `71e5113` (Task 2 RED) exists in git log
- Commit `6038964` (Task 2 GREEN) exists in git log
- Commit `241c960` (Task 3 RED) exists in git log
- Commit `2dc4330` (Task 3 GREEN) exists in git log
- All 135 tests pass (`python3 -m unittest discover scripts/tests` exits 0)
- Module imports cleanly (`python3 -c 'from scripts.lib import workspace_client'`)
- vault_writer.py has NO top-level workspace_client import (Pitfall 1 invariant preserved)
- No file outside `files_modified` list was touched
