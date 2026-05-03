---
phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings
verified: 2026-05-02T00:00:00Z
status: human_needed
score: 23/23 must-haves verified (code+test layer); 1 deferred ship-checklist item awaits Coolify execution
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run `bash scripts/sync-obsidian.sh --backfill` on Coolify with GOOGLE_MCP_CREDENTIALS_DIR exported and OAuth blob present at ${GOOGLE_MCP_CREDENTIALS_DIR}/glen@iugo.com.au.json"
    expected: "Output `vault_writer backfill complete: {clients_written: N, events_routed: M}` with M materially higher than the Phase 11 baseline; data/.cal-cache.json + data/.drive-cache.json materialize on-host (NOT in git status); regenerated client notes contain 📅 meeting + 📝 doc lines in Activity Log"
    why_human: "Live OAuth flow + Google API round trip cannot be exercised from a unit-test harness; requires Coolify host with credentials minted by hardened-workspace MCP — by-design deferred verification per Phase 11 precedent (Plan 12-04 SUMMARY 'Authentication Gates' section step list)"
  - test: "After backfill, open Obsidian on iPhone and inspect a regenerated client note (e.g. property-council-australia.md)"
    expected: "📅 lines render alongside existing 📧 ✅ 💰 📄 entries; 📝 lines render with 'modified by {name}' tail; htmlLink/webViewLink links resolve in Calendar/Drive; D-C3 anchor passes (`grep '📄' vault-build/Clients/*.md | grep -v 'Contract'` empty)"
    why_human: "Visual rendering on Obsidian iPhone client + emoji glyph correctness on the rendered surface — cannot be programmatically verified without a real device; visual regression check"
  - test: "Confirm `data/.cal-cache.json` and `data/.drive-cache.json` exist on Coolify after backfill AND do not appear in `git status`"
    expected: "Both files present on disk under the data/ directory with valid JSON `{schema_version, global, by_client}` shape; `git status` shows no new untracked files matching those names (gitignore exclusion working in production environment)"
    why_human: "Verifies the .gitignore lines actually take effect against real cache writes (not just the synthetic `touch` test executed during verification); requires production sync run"
  - test: "Optional negative-path test: temporarily clear GOOGLE_MCP_CREDENTIALS_DIR on Coolify and re-run backfill"
    expected: "ONE warning feed entry per fetch attempt; workspace_data_stale_since: timestamp appears in regenerated frontmatter; Activity Log contains cached entries (not empty); restore env var afterwards"
    why_human: "Live cache-fallback chain end-to-end requires running against a real Workspace failure case; unit-test mocks cannot exercise the actual filesystem + bash + Python boundaries simultaneously"
---

# Phase 12: Calendar + Drive Activity Enrichment Verification Report

**Phase Goal:** Enrich client notes with meetings (Google Calendar, matched by attendee email -> canonical `client_domain`) and documents (Google Drive, matched by filename substring per D-A4-REVISED) appended to the Activity Log section. Uses Google Calendar v3 + Drive v3 REST APIs directly via OAuth blob from hardened-workspace credentials per D-X1.

**Verified:** 2026-05-02
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (must_haves merged from all 4 plan frontmatters)

#### Plan 12-01 (Wave 0 Bootstrap)

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1.1 | `.gitignore` excludes `data/.cal-cache.json` AND `data/.drive-cache.json` BEFORE any cache write | VERIFIED | Lines 37-38 of `.gitignore` contain both paths; Phase 11 line 34 `data/.cm-cache.json` preserved; `git check-ignore data/.cal-cache.json data/.drive-cache.json` (after `touch`) returns both paths |
| 1.2 | `scripts/sync-obsidian.sh` fails loudly if `GOOGLE_MCP_CREDENTIALS_DIR` is unset on Coolify | VERIFIED | Line 42 of `scripts/sync-obsidian.sh` contains `: "${GOOGLE_MCP_CREDENTIALS_DIR:?GOOGLE_MCP_CREDENTIALS_DIR env var required ...}"`; placed AFTER existing `CONTRACT_MANAGER_API_KEY:?` (line 33) and BEFORE `REPO_ROOT=` (per plan placement) |
| 1.3 | `EMOJI_BY_KIND` extends with meeting→📅 and doc→📝 while preserving contract→📄 | VERIFIED | `python3 -c 'from scripts.lib.vault_writer import EMOJI_BY_KIND; print(EMOJI_BY_KIND)'` prints `{'triage': '📧', 'task': '✅', 'invoice': '💰', 'contract': '📄', 'meeting': '📅', 'doc': '📝'}`; D-C3 invariant preserved (📄 maps only to `contract`) |
| 1.4 | `load_clients` carries `aliases[]` through into the per-domain dict | VERIFIED | `vault_writer.py` lines 386-394 (raw_entries assembly + per-domain dict literal) include `"aliases": list(rec.get("aliases") or [])`; `TestLoadClientsAliasesPhase12` (5 tests) all pass |
| 1.5 | `render_log_line` accepts `kind="meeting"` and `kind="doc"` without ValueError | VERIFIED | `TestEmojiByKindPhase12.test_render_log_line_accepts_meeting_kind` and `test_render_log_line_accepts_doc_kind` pass; emit lines starting `### [...] 📅 ...` and `### [...] 📝 ...` respectively |

#### Plan 12-02 (Workspace Client)

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 2.1 | `scripts/lib/workspace_client.py` exists with single network seam, retry wrapper, atomic cache helpers, OAuth loader, response adapters, strict endpoint allowlist | VERIFIED | File exists at 19.3K; module-level `_workspace_get`, `call_with_retry`, `load_cache`, `write_cache`, `gc_cache_orphans`, `format_calendar_event_for_log`, `format_drive_file_for_log`, `_load_workspace_credentials`, `_walk_drive_for_clients`, `_check_endpoint_allowed` all importable |
| 2.2 | Five exception classes — WorkspaceTransportError, WorkspaceRpcError, WorkspaceRateLimitError(WorkspaceTransportError), WorkspaceAuthExpiredError(WorkspaceTransportError) — mirror cm_client hierarchy | VERIFIED | All four classes importable; `issubclass(WorkspaceAuthExpiredError, WorkspaceTransportError) == True`; verified via inline python check (Note: the must-have lists "Five" but only four are required per plan; spec count is correct in code) |
| 2.3 | Endpoint allowlist enforces D-X1 trust boundary (only `calendar/v3/calendars/primary/events`, `drive/v3/files`, and `drive/v3/files/{id}` reachable) | VERIFIED | `WORKSPACE_ALLOWED_ENDPOINTS = frozenset({'drive/v3/files', 'calendar/v3/calendars/primary/events'})`; `WORKSPACE_ALLOWED_ENDPOINT_PREFIXES = ('drive/v3/files/',)`; `_check_endpoint_allowed` is line 1 (line 125) of `_workspace_get`; raises before any urlopen call when path not in allowlist |
| 2.4 | OAuth token loader reads `~/.google_workspace_mcp/credentials/` (or `GOOGLE_MCP_CREDENTIALS_DIR`), refreshes via `oauth2.googleapis.com/token` if expiring, never logs token | VERIFIED | `_credentials_path` honours env var override; `_refresh_workspace_token` POSTs to `OAUTH_TOKEN_REFRESH_URL = "https://oauth2.googleapis.com/token"` form-encoded with `# OAUTH-POST:` carve-out marker; `OAUTH_REFRESH_LEEWAY_S = 60`; exception messages format as `"HTTP {code}: {reason}"` / `"network: {reason}"` / `"credentials refresh failed: ..."` — none echo Bearer header (T-12-02-01) |
| 2.5 | Privacy filter adapters apply D-D1 (visibility OR no-external-attendees), D-D2 (>25 attendees), D-D3 (trashed/draft Drive) BEFORE returning to vault_writer | VERIFIED | `format_calendar_event_for_log` lines 269-281: D-D2 first (cheapest), then D-D1 part 1 (`visibility=="private"`), then D-D1 part 2 (no external attendees via `_is_internal`); `format_drive_file_for_log` lines 301-307: D-D3 (trashed → None, .gdraft → None, `[DRAFT]` token → None — case-sensitive); both return None on filter MATCH |
| 2.6 | Endpoint allowlist source-grep test exists | VERIFIED | `TestWorkspaceClientEndpointAllowlist` in `test_workspace_client.py` lines 608-661 with two methods: `test_only_allowlisted_endpoints_referenced` (regex-walks every `calendar/v3/...|drive/v3/...` literal in module source) + `test_no_write_verb_method_calls_present` (scans for `method="POST/PUT/PATCH/DELETE"` with `OAUTH-POST:` carve-out); both pass in CI |

#### Plan 12-03 (Routing + Event-Tuple Surface)

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 3.1 | `_match_drive_filename_to_client` implements D-A4-REVISED (case-insensitive substring + word-boundary + longest-alias-wins + alphabetical tie-break + stop-list) | VERIFIED | `vault_writer.py` lines 589-626 implement all 5 rules; sort key `(-len(needle), needle, domain)` for longest-wins + alphabetical tie-break; stop-list constant at line 75 (`_DRIVE_FILENAME_STOP_LIST = frozenset({"agend", "iugo", "glen", "rosie"})`); `TestFilenameMatchingPhase12` (12 tests) + `TestHasWordBoundaryMatch` (10 tests) all pass |
| 3.2 | `_route_calendar_event_to_slug` implements D-A2 (strict attendee email domain match + first-match-wins by alphabetical client_domain order) | VERIFIED | `vault_writer.py` lines 629-660; case-insensitive host extraction + alias-equality fallback (NOT substring); `sorted(matched_domains)[0]` gives alphabetical first-match-wins; `TestCalendarRoutingPhase12` (8 tests) all pass |
| 3.3 | `_cal_meeting_event_tuple` produces D-C1 line shape `(ts, "meeting", "{title} — {N} attendees", "[Open in Calendar]({htmlLink})", None)` | VERIFIED | `vault_writer.py` lines 708-737; handles RFC3339-with-offset / Z-suffix / date-only formats; (no title) fallback for empty summary; `TestCalEventTuplePhase12` (6 tests) all pass |
| 3.4 | `_drive_doc_event_tuple` produces D-C2 line shape `(ts, "doc", "{filename} — modified by {modifier}", "[Open in Drive]({webViewLink})", None)` | VERIFIED | `vault_writer.py` lines 740-767; modifier fallback chain `displayName` → email local-part → `"unknown"`; (unnamed file) fallback for empty name; `TestDriveEventTuplePhase12` (7 tests) all pass |
| 3.5 | `_gather_events` accepts `cal_events=None` and `drive_files=None` kwargs (additive); Phase 11 callers behave identically | VERIFIED | `inspect.signature(_gather_events).parameters` returns `[data_root, clients, cm_expiring, cm_invoices, cal_events, drive_files]`; `TestGatherEventsCalendarIntegration` (5 tests) + `TestGatherEventsDriveIntegration` (6 tests) all pass; Phase 11 `TestGatherEventsCmIntegration` still passes (verified above) |
| 3.6 | Pitfall 4 inheritance — Calendar event ID is the stable dedup key (NOT title/date); Drive file ID likewise | VERIFIED | `seen_event_ids` and `seen_file_ids` per-source local sets in `_gather_events` (Plan 12-03 design); `TestGatherEventsCalendarIntegration::test_dedup_by_event_id_not_title` + `TestGatherEventsDriveIntegration::test_dedup_by_file_id` pin invariant |
| 3.7 | `render_log_line` renders kind="meeting" → 📅 line + kind="doc" → 📝 line correctly | VERIFIED | Direct test runs from Plan 12-01 confirm; D-C1 + D-C2 line shape end-to-end via `_cal_meeting_event_tuple` + `_drive_doc_event_tuple` calls into `render_log_line` |

#### Plan 12-04 (Orchestrator + Final Integration)

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 4.1 | `_fetch_cm_data_for_run` is renamed to `_fetch_external_data_for_run` with backward-compat alias preserving Phase 11's 17 mocked tests | VERIFIED | `vault_writer.py` line 1421 `def _fetch_external_data_for_run(...)`; line 1809 `_fetch_cm_data_for_run = _fetch_external_data_for_run`; inline `python3 -c 'assert _fetch_cm_data_for_run is _fetch_external_data_for_run'` passes; Phase 11 `TestGatherEventsCmIntegration`, `TestCacheFallbackEnd2End`, `TestBackfillIdempotentPhase11` all still pass |
| 4.2 | `_fetch_external_data_for_run` fetches CM (Phase 11) + Calendar (events.list) + Drive (files.list) in sequence with shared retry+cache+warning semantics; per-tool failures isolated | VERIFIED | Lines 1666-1758 implement Calendar block + Drive block with independent try/except wrapping `ws_call_with_retry` / `_walk_drive_for_clients`; restructured early-return (per Note 1 in 12-04 SUMMARY) ensures Workspace runs INDEPENDENTLY of CM status; lines 1760-1763 set `workspace_stale_since = min(stale_candidates)` |
| 4.3 | Per-tool cache fallback writes `data/.cal-cache.json` AND `data/.drive-cache.json`; each cache atomic-written via `vault_writer._atomic_write` | VERIFIED | Lines 1675-1678 + 1730-1733 load each cache; lines 1715-1718 + 1746-1749 write post-fetch cache entries; lines 1794-1802 persist via `ws_write_cache` (which delegates to `vault_writer._atomic_write`); both paths gitignored (Wave 0); `TestWorkspaceCacheFallbackEnd2End` (3 tests) all pass |
| 4.4 | On Calendar/Drive fetch exhaustion, frontmatter gains `workspace_data_stale_since` stamped from cached `fetched_at`; cleared on next successful fetch | VERIFIED | `render_frontmatter` line 959 emits `fm["workspace_data_stale_since"] = workspace_stale_since` when set; `TestWorkspaceCacheFallbackEnd2End::test_calendar_cache_fallback_stamps_workspace_stale_since` + `test_drive_cache_fallback_stamps_workspace_stale_since` + `test_workspace_cache_clears_stale_since_on_success` all pass |
| 4.5 | 401 mid-backfill triggers ONE OAuth token refresh + retry; refresh failure → cache fallback + level=warning feed entry | VERIFIED | Lines 1701-1707 (Calendar) + 1743-1745 (Drive) implement nested try/except: outer catches Transport/RpcError → cache fallback + `_warn`; inner catches `WorkspaceAuthExpiredError` → re-call `_load_workspace_credentials()` + retry once; if refresh fails, raises `WorkspaceTransportError` which falls through to outer catch |
| 4.6 | `run_backfill` threads cal_data + drive_data through `_gather_events` alongside cm_data (no behavioural change to Phase 11 paths) | VERIFIED | Lines 1254-1255 `_gather_events(... cal_events=external_data.get("global_calendar"), drive_files=external_data.get("global_drive"))`; line 1276 `render_frontmatter(... workspace_stale_since=external_data.get("workspace_stale_since"))`; Phase 11 idempotency test still passes (snapshot helpers extended additively per Plan 12-04 SUMMARY decision) |
| 4.7 | `TestProjectionDoesNotImportWorkspace` (subprocess) verifies Mac daemon's `run_projection` does NOT import `scripts.lib.workspace_client` (T-12-04-01) | VERIFIED | `test_vault_writer.py` lines 2478-2507; subprocess executes `run_projection` and asserts BOTH `WS_NOT_LOADED` AND `CM_NOT_LOADED` print to stdout; test passes (`Ran 1 test in 0.083s OK`); `grep -E "^from .workspace_client|^import .*workspace_client" scripts/lib/vault_writer.py` returns empty (lazy import only inside `_fetch_external_data_for_run` body, line 1642) |
| 4.8 | `TestBackfillIdempotentPhase12`: two backfills with frozen mocked Calendar+Drive responses produce byte-identical managed sections | VERIFIED | `test_vault_writer.py` line 2394; passes; `_snapshot_managed` extended with `not ln.startswith('workspace_data_stale_since:')` filter; Phase 10/11 idempotency tests still pass under the additive filter |
| 4.9 | Stop-list-only Drive matches counter reported in one info-level feed entry per sync | VERIFIED | Lines 1768-1792 implement post-fetch walk over `out["global_drive"]["files"]`; `_match_drive_filename_to_client` returning None + `_has_word_boundary_match(name_lower, tok)` for any stop-list token → increment `stop_skipped`; ONE info-level `append_feed_entry` when `stop_skipped > 0`; `TestStopListSilentSkipCounter` (2 tests) both pass |

**Score:** 23/23 truths verified at the code+test layer.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `.gitignore` | cal-cache + drive-cache exclusion | VERIFIED | Lines 37-38 contain both literal paths; Phase 11 cm-cache line 34 preserved; `git check-ignore` confirms exclusion |
| `scripts/sync-obsidian.sh` | GOOGLE_MCP_CREDENTIALS_DIR env validation | VERIFIED | Line 42 contains `: "${GOOGLE_MCP_CREDENTIALS_DIR:?...}"`; positioned after CONTRACT_MANAGER_API_KEY check, before REPO_ROOT (per plan placement) |
| `scripts/lib/vault_writer.py` (Wave 0) | EMOJI_BY_KIND extension; load_clients aliases plumbing | VERIFIED | EMOJI_BY_KIND has 6 entries; `aliases` key present in raw_entries (line 384) AND per-domain dict (line 392); docstring updated |
| `scripts/tests/test_vault_writer.py` (Wave 0) | TestEmojiByKindPhase12 + TestLoadClientsAliasesPhase12 | VERIFIED | Both classes present; 11 tests pass (6 emoji + 5 aliases) |
| `scripts/lib/workspace_client.py` | Single-network-seam HTTP client | VERIFIED | 19.3K file; all 18+ public symbols importable; mirrors cm_client.py 1:1 with allowlist+OAuth+adapter additions; CI grep-lint test enforces D-X1 |
| `scripts/tests/test_workspace_client.py` | 7 test classes including TestWorkspaceClientEndpointAllowlist | VERIFIED | 9 test classes total: TestWorkspaceClient (10), TestWorkspaceCallWithRetry (4), TestWorkspaceCache (6), TestIsInternalHelper (5), TestCalendarEventAdapter (9), TestDriveFileAdapter (7), TestOAuthTokenLoader (4), TestDriveWalker (3), TestWorkspaceClientEndpointAllowlist (2) — 50 tests total, all pass |
| `scripts/lib/vault_writer.py` (Wave 2) | _match_drive_filename_to_client, _has_word_boundary_match, _DRIVE_FILENAME_STOP_LIST, _route_calendar_event_to_slug, _cal_meeting_event_tuple, _drive_doc_event_tuple, _gather_events extended | VERIFIED | All 5 helpers + 1 extended function + 1 constant present at expected line ranges; signatures match plan spec; Pitfall 1 invariant (no top-level workspace_client import) preserved |
| `scripts/tests/test_vault_writer.py` (Wave 2) | TestFilenameMatchingPhase12, TestCalendarRoutingPhase12, TestCalEventTuplePhase12, TestDriveEventTuplePhase12, TestGatherEventsCalendarIntegration, TestGatherEventsDriveIntegration, TestHasWordBoundaryMatch | VERIFIED | All 7 classes present; 54 + 1 (deviation `test_unescaped_regex_would_not_match_literal_token`) = 55 tests pass |
| `scripts/lib/vault_writer.py` (Wave 4) | _fetch_external_data_for_run; render_frontmatter workspace_stale_since kwarg; run_backfill threads workspace data; lazy import block | VERIFIED | Function rename + alias + restructured early-return + Calendar/Drive blocks + workspace_stale_since stamping + stop-list counter all present; lazy import confined to function body (line 1642); `grep -E "^from .workspace_client" vault_writer.py` returns empty |
| `scripts/tests/test_vault_writer.py` (Wave 4) | TestWorkspaceCacheFallbackEnd2End, TestBackfillIdempotentPhase12, TestProjectionDoesNotImportWorkspace, TestStopListSilentSkipCounter | VERIFIED | All 4 classes present; 7 new tests pass; 2 existing snapshot helpers (`TestBackfillIdempotent._snapshot_managed`, `TestBackfillIdempotentPhase11._snapshot`) extended with `workspace_data_stale_since:` filter (Phase 10/11 idempotency still green) |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `.gitignore` literal lines | Wave 1 cache writers + Wave 4 _fetch_external_data_for_run | git check-ignore against actual paths | WIRED | `git check-ignore data/.cal-cache.json data/.drive-cache.json` returns both; Wave 4 writes via `ws_write_cache` (line 1797) |
| `scripts/sync-obsidian.sh` env validation | Coolify env injection for OAuth credentials | `${GOOGLE_MCP_CREDENTIALS_DIR:?...}` bash idiom | WIRED | Line 42 grepped; same idiom as Phase 11 sibling at line 33 |
| `EMOJI_BY_KIND` | `render_log_line` validation gate | `if kind not in EMOJI_BY_KIND: raise ValueError` | WIRED | `render_log_line` accepts both new kinds; tested via `TestEmojiByKindPhase12.test_render_log_line_accepts_meeting_kind` + `_doc_kind` |
| `load_clients` aliases | Wave 2 `_match_drive_filename_to_client` | `info["aliases"]` field iteration | WIRED | Line 612 `for alias in (info.get("aliases") or []):` reads the field that Wave 0 plumbed in |
| `call_with_retry` | `_workspace_get` | `_workspace_get(api_path, params, access_token)` invocation in retry loop | WIRED | Line 174 inside try/except for `(0,) + RETRY_DELAYS` loop |
| `_workspace_get` | `WORKSPACE_ALLOWED_ENDPOINTS` / `WORKSPACE_ALLOWED_ENDPOINT_PREFIXES` | `_check_endpoint_allowed(api_path)` first-line gate | WIRED | Line 125 IS the first executable statement in `_workspace_get`; raises before any urlopen call |
| `format_calendar_event_for_log` | D-D1 + D-D2 privacy filters | filter chain BEFORE adapter dict construction | WIRED | Lines 271-281 apply D-D2 then D-D1 part 1 then D-D1 part 2 BEFORE `return {...}` (line 284) |
| `write_cache` | `vault_writer._atomic_write` | import + delegated atomic temp+rename | WIRED | Line 41 imports `_atomic_write`; verified via inline import; cache test fixtures exercise the full path |
| `_gather_events cal_events` branch | `_route_calendar_event_to_slug` | per-event routing call | WIRED | Confirmed via `TestGatherEventsCalendarIntegration::test_routes_via_attendee_domain` |
| `_gather_events drive_files` branch | `_match_drive_filename_to_client` | per-file filename matching call | WIRED | Confirmed via `TestGatherEventsDriveIntegration::test_routes_via_filename_matching` |
| `_match_drive_filename_to_client` | `_has_word_boundary_match` | regex word-boundary check | WIRED | Line 618 `if _has_word_boundary_match(name_lower, needle):` |
| `_cal_meeting_event_tuple` | `EMOJI_BY_KIND['meeting']` | `kind="meeting"` in tuple → `render_log_line` dispatches via `EMOJI_BY_KIND` | WIRED | Tuple position 1 is literal `"meeting"` (line 737); `render_log_line` looks up via `EMOJI_BY_KIND[kind]` |
| `_fetch_external_data_for_run` | `scripts.lib.workspace_client` (ALL imports inside function) | lazy import block | WIRED | Line 1642 `from .workspace_client import (...)` is INSIDE the function body; module top has no `from .workspace_client` import (`grep -E "^from .workspace_client"` returns empty); subprocess test confirms `WS_NOT_LOADED` |
| `run_backfill` | `_gather_events` with cal_events + drive_files kwargs | `external_data['global_calendar']` + `external_data['global_drive']` thread | WIRED | Lines 1254-1255 |
| `render_frontmatter` | `workspace_data_stale_since` key | additive optional kwarg + frontmatter dict assignment | WIRED | Line 938 docstring + line 959 `fm["workspace_data_stale_since"] = workspace_stale_since` (when set) |
| `run_projection` | `scripts.lib.workspace_client` (MUST NOT be imported) | subprocess negative test | WIRED (negative invariant) | `TestProjectionDoesNotImportWorkspace` passes; INVARIANT block at line 2006 documents the constraint with explicit T-12-04-01 reference |

### Data-Flow Trace (Level 4)

This phase produces vault-side rendered output. The full live flow requires a Coolify execution (deferred to human verification). Mock-based unit tests verify the data-flow chain end-to-end:

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `_fetch_external_data_for_run` | `out["global_calendar"]` | `format_calendar_event_for_log` over `ws_call_with_retry("calendar/v3/calendars/primary/events", ...)` result | mocked: yes; live: deferred | FLOWING (test) — `TestWorkspaceCacheFallbackEnd2End` exercises end-to-end with mocked Workspace client |
| `_fetch_external_data_for_run` | `out["global_drive"]` | `_walk_drive_for_clients(access_token)` (which calls `_workspace_get("drive/v3/files", ...)`) | mocked: yes; live: deferred | FLOWING (test) |
| `_fetch_external_data_for_run` | `out["workspace_stale_since"]` | `min(cal_stale_at, drive_stale_at)` from cached `fetched_at` when EITHER fell back | yes | FLOWING |
| `_fetch_external_data_for_run` | `out["drive_stop_list_skipped"]` | counter of files where matcher returns None AND any stop-list token has word-boundary match | yes | FLOWING — `TestStopListSilentSkipCounter` validates both 0-skip and N-skip paths |
| `run_backfill` | per-client Activity Log entries | `_gather_events(... cal_events=external_data.get("global_calendar"), drive_files=external_data.get("global_drive"))` | yes | FLOWING — Phase 12 idempotency test renders byte-identical output across two runs |
| `render_frontmatter` | `workspace_data_stale_since` YAML key | `external_data.get("workspace_stale_since")` thread → kwarg | yes | FLOWING — `TestWorkspaceCacheFallbackEnd2End::test_calendar_cache_fallback_stamps_workspace_stale_since` confirms |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full unit test suite passes | `python3 -m unittest discover scripts/tests` | `Ran 197 tests in 0.319s OK` | PASS |
| EMOJI_BY_KIND has 6 entries with correct mappings | `python3 -c 'from scripts.lib.vault_writer import EMOJI_BY_KIND; print(EMOJI_BY_KIND)'` | `{'triage': '📧', 'task': '✅', 'invoice': '💰', 'contract': '📄', 'meeting': '📅', 'doc': '📝'}` | PASS |
| Stop-list constant equals expected frozenset | `python3 -c 'from scripts.lib.vault_writer import _DRIVE_FILENAME_STOP_LIST; print(_DRIVE_FILENAME_STOP_LIST)'` | `frozenset({'agend', 'iugo', 'rosie', 'glen'})` | PASS |
| Backward-compat alias is identity | `python3 -c '... assert _fetch_cm_data_for_run is _fetch_external_data_for_run'` | exit 0 | PASS |
| WORKSPACE_ALLOWED_ENDPOINTS narrow | `python3 -c '...print(WORKSPACE_ALLOWED_ENDPOINTS)'` | `frozenset({'drive/v3/files', 'calendar/v3/calendars/primary/events'})` | PASS |
| WorkspaceAuthExpiredError subclass of WorkspaceTransportError | `python3 -c 'print(issubclass(WorkspaceAuthExpiredError, WorkspaceTransportError))'` | `True` | PASS |
| .gitignore lines effective | `touch data/.cal-cache.json data/.drive-cache.json && git check-ignore data/.cal-cache.json data/.drive-cache.json` | both paths printed | PASS |
| TestWorkspaceClientEndpointAllowlist (CI grep-lint) | `python3 -m unittest scripts.tests.test_workspace_client.TestWorkspaceClientEndpointAllowlist` | `Ran 2 tests OK` | PASS |
| TestProjectionDoesNotImportWorkspace (subprocess Pitfall 1) | `python3 -m unittest scripts.tests.test_vault_writer.TestProjectionDoesNotImportWorkspace` | `Ran 1 test OK` | PASS |
| Phase 11 tests still green under rename+alias | `python3 -m unittest scripts.tests.test_vault_writer.TestGatherEventsCmIntegration scripts.tests.test_vault_writer.TestCacheFallbackEnd2End scripts.tests.test_vault_writer.TestBackfillIdempotentPhase11` | `Ran 9 tests OK` | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
| ----------- | -------------- | ----------- | ------ | -------- |
| INTL-01-CAL | 12-01, 12-02, 12-03, 12-04 | Calendar meetings matched by attendee email domain → per-client Activity Log with 📅 | SATISFIED | `format_calendar_event_for_log` (D-D1+D-D2 + adapter shape); `_route_calendar_event_to_slug` (D-A2); `_cal_meeting_event_tuple` (D-C1 line shape); 90-day window enforced in `_fetch_external_data_for_run` (lines 1667-1672 compute `time_min = now - 90d`, `time_max = now + 30d`); `singleEvents=true`; `fields=` explicit; cache fallback wired |
| INTL-01-DRIVE | 12-01, 12-02, 12-03, 12-04 | Drive documents per filename matching → per-client Activity Log with 📝 | SATISFIED | `format_drive_file_for_log` (D-D3 adapter); `_walk_drive_for_clients` (D-A3-REVISED scope); `_match_drive_filename_to_client` (D-A4-REVISED rules 1-5); `_drive_doc_event_tuple` (D-C2 line shape); stop-list constant + word-boundary regex with `re.escape`; cache fallback wired |
| INTL-01-PRIVACY | 12-02, 12-04 | Privacy filters (visibility:private OR no-external-attendees, >25 attendees, trashed/draft) | SATISFIED | All three filters implemented IN-ADAPTER (`format_calendar_event_for_log` + `format_drive_file_for_log`) BEFORE returning to `vault_writer`; orchestrator never sees pre-filter data; D-D3 case-sensitive `[DRAFT]` token enforced |
| INTL-01-WORKSPACE-CACHE | 12-01, 12-02, 12-04 | Calendar+Drive use retry+cache fallback (3 retries, 1/5/30 backoff); per-tool cache files | SATISFIED | `RETRY_DELAYS = (1, 5, 30)`; `(0,) + RETRY_DELAYS` retry loop in `call_with_retry`; per-tool cache files (`data/.cal-cache.json` + `data/.drive-cache.json`); both gitignored; atomic temp+rename via `_atomic_write`; `workspace_data_stale_since` stamping on fallback |
| INTL-01-PROJECTION-ISOLATION | 12-01, 12-04 | Mac daemon's run_projection does NOT import workspace_client | SATISFIED | Lazy import confined to `_fetch_external_data_for_run` body (line 1642); `grep -E "^from .workspace_client" scripts/lib/vault_writer.py` returns empty; `TestProjectionDoesNotImportWorkspace` subprocess test verifies `'scripts.lib.workspace_client' not in sys.modules` AFTER `run_projection` returns; `run_projection` INVARIANT block (line 2006) documents constraint with T-12-04-01 reference |

**Orphaned requirements check:** REQUIREMENTS.md lists exactly 5 INTL-01-* IDs mapped to Phase 12 (lines 96-100); all 5 are claimed by at least one Phase 12 plan. No orphans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none) | — | No TODO/FIXME/PLACEHOLDER comments in new code; no empty handlers; no console.log-only implementations; no hardcoded empty data flowing to render | n/a | n/a |

Anti-pattern scan over the four files modified across all 4 plans (`.gitignore`, `scripts/sync-obsidian.sh`, `scripts/lib/vault_writer.py`, `scripts/lib/workspace_client.py`, `scripts/tests/test_vault_writer.py`, `scripts/tests/test_workspace_client.py`) found no blocker patterns. The `(0,) + RETRY_DELAYS = (0, 1, 5, 30)` initial-tuple pattern in `call_with_retry` is intentional (D-A3 inheritance — first attempt is immediate). The `# OAUTH-POST:` carve-out marker in `workspace_client.py` line 340 is a documented exception covered by the grep-lint test.

### Human Verification Required

The phase is structurally complete (all code-and-tests deliverables landed, all 197 unit tests pass on master) but a final live ship-checklist requires Coolify execution + iPhone visual check. This is the deferred verification pattern explicitly documented in Plan 12-04 SUMMARY's "Authentication Gates" section, mirroring Phase 11's deferred Task 3 ship pattern.

#### 1. Coolify backfill smoke test

**Test:** SSH `ssh root@103.249.238.17`; export `GOOGLE_MCP_CREDENTIALS_DIR` pointing at the OAuth credentials directory; confirm `${GOOGLE_MCP_CREDENTIALS_DIR}/glen@iugo.com.au.json` exists; run `bash scripts/sync-obsidian.sh --backfill`.
**Expected:** Final stdout line `vault_writer backfill complete: {'clients_written': N, 'events_routed': M}` with M materially higher than the Phase 11 baseline (Phase 12 adds Calendar + Drive entries to existing CM/triage/tasks/invoices). No `bash: GOOGLE_MCP_CREDENTIALS_DIR: ... env var required` error in stderr.
**Why human:** Live OAuth flow + Google API round trip cannot be exercised in a unit-test harness. Requires real Workspace credentials minted by hardened-workspace MCP — by-design deferred per Plan 12-04 SUMMARY.

#### 2. Obsidian iPhone visual check

**Test:** After backfill + push, open Obsidian on iPhone. Open `vault-build/Clients/property-council-australia.md` (or any client with recent meetings/docs).
**Expected:** Activity Log section contains 📅 lines (recent meetings within 90d, alongside existing 📧✅💰📄 entries) AND 📝 lines (recently-modified Drive docs). Glen-owned Overview/Decisions sections preserved. CM-TODOS + Usage sections (Phase 11) intact. D-C3 anchor: `grep "📄" vault-build/Clients/*.md | grep -v "Contract"` returns no matches.
**Why human:** Visual rendering on Obsidian iPhone client + emoji glyph correctness on the rendered surface — cannot be programmatically verified without a real device.

#### 3. Cache files materialize on Coolify and stay out of git

**Test:** After backfill, `ls -la data/.cal-cache.json data/.drive-cache.json` on Coolify; `git status`.
**Expected:** Both files exist with valid JSON `{schema_version, global, by_client}` shape; `git status` shows neither (gitignored exclusion working in production).
**Why human:** Verifies the .gitignore lines actually take effect against real cache writes (not just the synthetic `touch` test executed during this verification); requires production sync run.

#### 4. Negative-path cache fallback (optional)

**Test:** Temporarily clear `GOOGLE_MCP_CREDENTIALS_DIR` on Coolify; re-run `bash scripts/sync-obsidian.sh --backfill`.
**Expected:** `bash` exits non-zero with stderr containing `GOOGLE_MCP_CREDENTIALS_DIR env var required` — the wrapper's fail-fast gate fires BEFORE any sync work. Restore env var afterwards. Alternatively (to test live cache fallback rather than wrapper), set `GOOGLE_MCP_CREDENTIALS_DIR=/nonexistent`: expect ONE warning feed entry per fetch attempt, `workspace_data_stale_since` stamp in regenerated frontmatter, Activity Log contains cached entries (not empty).
**Why human:** Live cache-fallback chain end-to-end requires running against a real Workspace failure case; unit-test mocks cannot exercise the actual filesystem + bash + Python boundaries simultaneously.

### Gaps Summary

No gaps in the code+test layer. All 23 must-haves are VERIFIED across the 4 plans. All 16 SUMMARY-claimed commits exist in git history. The full 197-test unit suite passes on master (74 baseline + 11 Wave 0 + 50 Wave 1 + 55 Wave 2 + 7 Wave 4 = 197 — count matches Plan 12-04 SUMMARY exactly).

The remaining work is the deferred ship-checklist (Coolify execution + iPhone visual verification) — by-design per Plan 12-04's "Authentication Gates" section and Phase 11's established deferred-verification precedent. Status set to `human_needed` rather than `passed` to surface this final ship-side validation step.

---

*Verified: 2026-05-02*
*Verifier: Claude (gsd-verifier)*
