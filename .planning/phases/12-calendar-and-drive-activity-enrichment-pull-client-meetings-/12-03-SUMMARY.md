---
phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings
plan: 03
subsystem: vault-writer
tags: [phase-12, vault-writer, gather-events, filename-matching, tdd, rendering, routing]

# Dependency graph
requires:
  - phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings
    plan: 01
    provides: EMOJI_BY_KIND meeting→📅 + doc→📝 (consumed by event-tuple builders), load_clients aliases plumbing (consumed by _match_drive_filename_to_client), render_log_line accepts new kinds
  - phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings
    plan: 02
    provides: scripts/lib/workspace_client.py adapter shapes (format_calendar_event_for_log + format_drive_file_for_log) — Wave 4 will call these and pipe their output into _gather_events kwargs added by this plan
provides:
  - scripts/lib/vault_writer.py new module constant _DRIVE_FILENAME_STOP_LIST = frozenset({"agend","iugo","glen","rosie"}) — Wave 4 orchestrator consumes for stop-list-only count summary
  - scripts/lib/vault_writer.py 5 new helpers: _has_word_boundary_match (D-A4-REVISED rule 3 regex), _match_drive_filename_to_client (D-A4-REVISED rules 1-5), _route_calendar_event_to_slug (D-A2 attendee-domain routing), _cal_meeting_event_tuple (D-C1 line shape), _drive_doc_event_tuple (D-C2 line shape)
  - scripts/lib/vault_writer.py _gather_events extended with cal_events + drive_files kwargs (additive — Phase 11 callers unaffected); calendar branch dedups by event ID + routes via D-A2 + falls back to _Unknown.md; drive branch dedups by file ID + routes via D-A4-REVISED + applies D-B2 top-20-per-client cap + silently drops no-match files
affects: [12-04 _fetch_external_data_for_run will pipe workspace_client adapter outputs into _gather_events via the kwargs landed here]

# Tech tracking
tech-stack:
  added: []  # zero new third-party deps; preserves Phase 10/11 zero-extra-dep precedent
  patterns:
    - "Phase 11 cm_expiring/cm_invoices kwarg-extension pattern mirrored 1:1 for cal_events/drive_files — additive Optional[dict]=None default; per-source dedup set; Pitfall 4 dedup by stable upstream ID; sibling block placement after the existing Phase 11 cm_invoices branch"
    - "Pure routing helpers (_match_drive_filename_to_client, _route_calendar_event_to_slug) — caller is responsible for stop-list bookkeeping and feed-entry emission; matchers stay pure so they can be unit-tested without orchestration concerns. Phase 12 first establishes this separation; future client-routing modules (Slack, Linear) follow."
    - "D-A4-REVISED word-boundary regex idiom: rf\"(?:^|[_\\-. ]){re.escape(needle)}(?:[_\\-. ]|$)\" — single source of truth for word-boundary discipline. re.escape() is the T-12-03-06 mitigation against alias-as-regex-injection."
    - "D-B2 per-client cap pattern — drive_buckets defaultdict per slug, then events_by_slug[slug].extend(evts[:20]). The walker upstream sorts by modifiedTime desc; here we just slice. Decoupling collection from cap (vs interleaved) keeps the dedup logic simple and the cap explicit."
    - "Sort key tuple (-len(needle), needle, domain) for D-A4-REVISED rule 4+5 — longest needle wins; alphabetical tie-break on (needle, domain). Three-level deterministic sort means routing is reproducible across runs (T-12-03-07 idempotency mitigation)."

key-files:
  created: []
  modified:
    - scripts/lib/vault_writer.py
    - scripts/tests/test_vault_writer.py

key-decisions:
  - "Module constant _DRIVE_FILENAME_STOP_LIST placed AFTER _PRIORITY_BUCKET_NAMES in the constants block (line ~70) — sibling pattern: a frozenset used by a routing helper. Matches PATTERNS.md guidance and Phase 10's _PRIORITY_BUCKET_NAMES placement convention."
  - "_has_word_boundary_match + _match_drive_filename_to_client + _route_calendar_event_to_slug placed AFTER _clientid_to_slug (line ~559) and BEFORE _cm_contract_event_tuple — under a new section header `# Phase 12 routing helpers (D-A2 + D-A4-REVISED)`. Bottom-up order: word-boundary helper → filename matcher (uses it) → calendar router (sibling logic)."
  - "_cal_meeting_event_tuple + _drive_doc_event_tuple placed AFTER _cm_invoice_event_tuple (line ~703) and BEFORE `# Section renderers` — under a new section header `# Phase 12 event-tuple builders (D-C1 calendar + D-C2 drive)`. Co-located with their Phase 11 sibling _cm_*_event_tuple builders for diff hygiene."
  - "Drive no-match → silent drop (NOT _Unknown.md routing) — this is the D-A4-REVISED-mandated divergence from Phase 10/11/12-cal routing. Calendar attendees give clear 'this should belong to a client even if unmapped' signal (CM JIT-mapping precedent); Drive filenames without an alias hit are routinely Glen's personal/internal files. Comment in production code calls this out."
  - "Drive cap implementation: collect into drive_buckets defaultdict, THEN events_by_slug[slug].extend(evts[:20]) — vs interleaved cap-as-you-go. Cleaner separation: dedup loop runs once per file; cap loop runs once per slug; no per-iteration len() check. Matches the plan's exact spec."
  - "Test fixture for word-boundary metachar-escape verification revised — the plan's specified haystack `report.+.docx` does not satisfy the word-boundary regex for needle `.+` (the `.` at position 6 is not preceded by a delimiter). Updated to `report .+ stuff` which has space-delimited word boundaries on both sides; added complement test `test_unescaped_regex_would_not_match_literal_token` to prove re.escape is what's preventing raw-regex interpretation. Documented as Rule 1 deviation."

patterns-established:
  - "Phase 12 D-A4-REVISED filename matching is the first place 'longest substring of N candidates wins with deterministic tie-break' appears in the codebase. Pattern: collect (needle, owning_domain) candidates → filter through word-boundary check → sort by (-len, needle, domain) → return matches[0][1]. Future routers needing N-way alias arbitration follow this template."
  - "Pitfall 4 per-source dedup-set pattern (Phase 11 inherited, Phase 12 extended): each upstream source gets its own seen_*_ids set inside _gather_events (cm_invoices: invoice_number; Phase 12 cal_events: event ID; Phase 12 drive_files: file ID). Sets live in the function's local scope so they reset per call; Pitfall 4 mitigation is structural (dedup happens BEFORE routing, so a malicious upstream sending the same ID with different bodies cannot inflate the bucket)."
  - "Adapter-to-kwarg pipeline: workspace_client adapters return None on filter MATCH and dict on PASS; _gather_events then dedups + routes the post-filter dicts via plan-12-03 helpers. The kwargs accept {\"items\": [...]} for cal and {\"files\": [...]} for drive — matches the Phase 11 cm_expiring={\"contracts\":[...]} / cm_invoices={\"invoices\":[...]} envelope shape so Wave 4 just flows the workspace_client return values straight in."

requirements-completed:
  - INTL-01-CAL  # routing + event-tuple shape for Calendar entries (Wave 4 pipes in workspace_client.list_events output)
  - INTL-01-DRIVE  # routing + event-tuple shape for Drive entries (Wave 4 pipes in workspace_client._walk_drive_for_clients output)

# Metrics
duration: ~8min
completed: 2026-05-03
---

# Phase 12 Plan 03: vault_writer Routing + Event-Tuple Surface Summary

**Routing + rendering surface for Calendar/Drive landed: `_match_drive_filename_to_client` (D-A4-REVISED case-insensitive substring + word boundary + longest-alias-wins + alphabetical tie-break + stop-list constant), `_route_calendar_event_to_slug` (D-A2 attendee-domain routing with first-match-wins), `_cal_meeting_event_tuple` (D-C1 line shape), `_drive_doc_event_tuple` (D-C2 line shape with displayName/email-local-part/unknown fallback chain), and `_gather_events` extended with `cal_events`/`drive_files` kwargs that dedup by stable upstream ID (Pitfall 4) and apply D-B2 per-client top-20 cap. No live HTTP — Wave 4 will pipe `workspace_client` adapter outputs into the kwargs landed here.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-03T02:01:18Z
- **Completed:** 2026-05-03T02:09:00Z
- **Tasks:** 2 (both TDD: RED → GREEN per task)
- **Files modified:** 2 (1 production + 1 test)
- **Tests:** 135 → 190 (+55 across 7 new test classes)

## Accomplishments

- **D-A4-REVISED Drive filename matching** — `_match_drive_filename_to_client(filename, clients)` implements all 5 rules of D-A4-REVISED in a pure routing helper:
  1. Case-insensitive substring match against `client_domain` stem (TLD stripped) OR `aliases[]` entries.
  2. Word-boundary discipline via `_has_word_boundary_match` — a regex with delimiter alternation `(?:^|[_\-. ]){re.escape(needle)}(?:[_\-. ]|$)`. Critical: `STAV` MUST NOT match `staffing.docx` (test `test_word_boundary_excludes_substring`).
  3. Longest needle wins (e.g. `PCNZ` beats `PC` on the same filename).
  4. Alphabetical tie-break on equal-length aliases (e.g. two clients sharing alias `XYZ` → `alpha.org` wins over `beta.org`).
  5. The matcher returns the matched `client_domain` or `None` — no stop-list bookkeeping in the matcher (caller responsibility per D-A4-REVISED last paragraph).
- **D-A2 Calendar routing** — `_route_calendar_event_to_slug(event, clients)` implements attendee-email-domain matching with case-insensitive host comparison, alias-equality fallback (NOT substring; substring is Drive-only), and alphabetical first-match-wins for multi-client meetings. Returns `_Unknown` on no match (D-04 routing rule preserved).
- **Stop-list constant** — `_DRIVE_FILENAME_STOP_LIST = frozenset({"agend", "iugo", "glen", "rosie"})` — Glen's brand/personal references that are NOT clients. Constant is exposed via `__all__` for Wave 4's stop-list-only count summary feed entry.
- **D-C1 calendar line shape** — `_cal_meeting_event_tuple(event)` produces `(ts, "meeting", "{title} — {N} attendees", "[Open in Calendar]({htmlLink})", None)`. Handles three start-time formats: RFC3339 with offset (passthrough), RFC3339 with `Z` suffix (normalised to `+00:00`), date-only (appended with midnight + local TZ). Falls back to `(no title)` placeholder when summary is None/empty.
- **D-C2 drive line shape** — `_drive_doc_event_tuple(file)` produces `(ts, "doc", "{filename} — modified by {modifier_name}", "[Open in Drive]({webViewLink})", None)`. Modifier-name fallback chain: `displayName` → email local part (split on `@`, take left) → `"unknown"`. Falls back to `(unnamed file)` placeholder when name is None/empty.
- **`_gather_events` extension** — signature gains two additive kwargs (`cal_events: dict | None = None`, `drive_files: dict | None = None`); two new branches placed AFTER the Phase 11 `cm_invoices` block and BEFORE the return:
  - **Calendar branch**: per-event dedup set keyed off Google's stable `event["id"]` (Pitfall 4 — title/date can change without rotating the ID), routing via `_route_calendar_event_to_slug`, `_Unknown` events appended to `unknown_pairs` with `from = first_attendee.email` (mirrors Phase 10 D-04 routing posture).
  - **Drive branch**: per-file dedup set keyed off `file["id"]`, routing via `_match_drive_filename_to_client`, no-match files SILENTLY DROPPED (NOT routed to `_Unknown.md` — D-A4-REVISED divergence from Phase 10/11/Calendar; Drive lacks the attendee-driven "this should belong to a client even if unmapped" signal). D-B2 top-20-per-client cap applied via `events_by_slug[slug].extend(drive_buckets[slug][:20])` after collection completes.
- **Pitfall 1 invariant preserved** — `vault_writer.py` top-level still has NO `from .workspace_client import ...` line. Wave 4 will introduce the lazy import inside `_fetch_external_data_for_run` so Mac-side `run_projection` can never accidentally instantiate `workspace_client`.
- **Phase 11 backwards compatibility** — `test_no_cal_kwargs_unchanged_phase11_behaviour` and `test_no_drive_kwargs_unchanged_phase11_behaviour` confirm that `_gather_events(data_root, clients)` (Phase 11 calling convention) and `_gather_events(data_root, clients, cal_events=None, drive_files=None)` (Phase 12 explicit-None calling convention) produce identical `events_by_slug` dicts.

## Task Commits

Each task was executed TDD (RED → GREEN) with `--no-verify` (worktree parallel execution).

1. **Task 1 RED — `faf3f0d`** — `test(12-03): RED tests for filename matching + calendar routing helpers`
   - `TestHasWordBoundaryMatch` (10 tests), `TestFilenameMatchingPhase12` (12 tests), `TestCalendarRoutingPhase12` (8 tests) — 30 tests fail RED with `ImportError`.
2. **Task 1 GREEN — `c5de4e8`** — `feat(12-03): GREEN — filename matching + calendar routing helpers`
   - `_DRIVE_FILENAME_STOP_LIST` constant + 3 helpers + `__all__` export.
   - 31 tests pass (the GREEN run revealed a test-fixture bug → fixed inline; see Deviations); full suite: 135 → 166.
3. **Task 2 RED — `d089043`** — `test(12-03): RED tests for event-tuple builders + _gather_events extension`
   - `TestCalEventTuplePhase12` (6 tests), `TestDriveEventTuplePhase12` (7 tests), `TestGatherEventsCalendarIntegration` (5 tests), `TestGatherEventsDriveIntegration` (6 tests) — 24 tests fail RED with `ImportError` (tuple helpers absent) and `TypeError` (`cal_events` / `drive_files` kwargs unknown).
4. **Task 2 GREEN — `fdc44d0`** — `feat(12-03): GREEN — event-tuple builders + _gather_events extension`
   - 2 new tuple builders + `_gather_events` signature/docstring/branch extension + `__all__` export.
   - 24 tests pass; full suite: 166 → 190.

REFACTOR commits not required for either task — production implementations are minimal additive helpers that passed verification on first GREEN run.

## TDD Gate Compliance

All two tasks completed RED → GREEN cycles. Gate sequence verified in git log:

| Task | RED commit | GREEN commit | Tests added | Status |
|------|-----------|-------------|-------------|--------|
| 1    | `faf3f0d` | `c5de4e8`   | 31          | PASS   |
| 2    | `d089043` | `fdc44d0`   | 24          | PASS   |

No REFACTOR commits required.

## Verification Results

```
$ python3 -m unittest discover scripts/tests
Ran 190 tests in 0.202s
OK
```

Per-class breakdown (Phase 12-03 only):

| Test Class                              | Tests |
|-----------------------------------------|-------|
| `TestHasWordBoundaryMatch`              | 10    |
| `TestFilenameMatchingPhase12`           | 12    |
| `TestCalendarRoutingPhase12`            |  8    |
| `TestCalEventTuplePhase12`              |  6    |
| `TestDriveEventTuplePhase12`            |  7    |
| `TestGatherEventsCalendarIntegration`   |  5    |
| `TestGatherEventsDriveIntegration`      |  6    |
| **Total NEW**                           | **54**|

Plus +1 complement test (`test_unescaped_regex_would_not_match_literal_token`) added during GREEN to formalise the negative half of the re.escape verification (see Deviations); 55 net new tests over the 135-test starting baseline → 190 total.

Acceptance-criteria spot-checks:

- All required new symbols importable: `_match_drive_filename_to_client`, `_has_word_boundary_match`, `_route_calendar_event_to_slug`, `_cal_meeting_event_tuple`, `_drive_doc_event_tuple`, `_DRIVE_FILENAME_STOP_LIST` — confirmed via inline `python3 -c '...'`.
- `_DRIVE_FILENAME_STOP_LIST == frozenset({"agend", "iugo", "glen", "rosie"})` — confirmed.
- `_gather_events` signature gains `cal_events` and `drive_files` kwargs with default `None`: `inspect.signature(_gather_events).parameters` returns `['data_root', 'clients', 'cm_expiring', 'cm_invoices', 'cal_events', 'drive_files']`.
- `grep -E "^from .workspace_client|^import .*workspace_client" scripts/lib/vault_writer.py` returns nothing — Pitfall 1 invariant preserved.
- `git diff 68df53e..HEAD --name-only` returns exactly `scripts/lib/vault_writer.py` and `scripts/tests/test_vault_writer.py` — no scope leak.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug in test fixture] `test_regex_metacharacters_escaped` haystack revised**

- **Found during:** Task 1 GREEN verification run (1/31 tests failed)
- **Issue:** The plan-specified test was `_has_word_boundary_match("report.+.docx", ".+") → True`. With the regex spec `(?:^|[_\-. ]){re.escape(needle)}(?:[_\-. ]|$)`, the `.+` literal at positions 6-7 of `report.+.docx` does not satisfy the word-boundary requirement: position 5 (immediately before `.+`) is `t` (alphanumeric, NOT a delimiter), so the regex fails to match. The intent of the test was to verify `re.escape(needle)` is applied (preventing raw-regex interpretation of metachars).
- **Fix:** Changed haystack to `"report .+ stuff"` — spaces flank the literal `.+` token, satisfying both delimiter requirements. Added a complement test `test_unescaped_regex_would_not_match_literal_token` that asserts `_has_word_boundary_match("no literal here", ".+")` is False — proving the function is searching for the literal `.+` token (not raw regex `.+` which would always match any non-empty haystack). Together the two tests bracket the re.escape behaviour: positive-find on a haystack containing the literal, negative-find on a haystack that does not.
- **Files modified:** `scripts/tests/test_vault_writer.py`
- **Commit:** `c5de4e8` (Task 1 GREEN — folded into the same commit since the test fixture and the production code ship together)

This is the only deviation from plan. The production code matches the spec verbatim; the deviation is a test-fixture correction that strengthens (rather than weakens) the test surface.

### Notes (non-deviations)

- **Phase 11 backwards-compat tests pre-pass after Task 2 GREEN.** `test_no_cal_kwargs_unchanged_phase11_behaviour` and `test_no_drive_kwargs_unchanged_phase11_behaviour` are forward-looking guards — they fail RED with `TypeError` because the kwargs don't exist yet, then pass GREEN once added. The plan explicitly anticipated this pattern.

- **Test count: +55 new tests vs plan's "54 new tests" target.** The +1 is the `test_unescaped_regex_would_not_match_literal_token` complement test added during deviation Rule 1 fix. The plan's count was advisory; the +1 is a strict-improvement on test surface (no behaviour weakened).

## Authentication Gates

None — this plan is pure routing/render surface with synthetic test fixtures. No live HTTP, no OAuth, no MCP calls. The auth surface lives in Wave 1 (`workspace_client`, already shipped) and Wave 4 (`_fetch_external_data_for_run`, future). Glen does not need to provide any credentials for this plan.

## Threat Flags

No new security surface beyond what was anticipated in the plan's `<threat_model>` section. All 9 threats (T-12-03-01 through T-12-03-09) have their mitigations realized in code as specified:

| Threat | Mitigation Realized |
|--------|---------------------|
| T-12-03-01 (Calendar event-ID dedup) | `seen_event_ids` keyed off `event["id"]`; test `test_dedup_by_event_id_not_title` pins the invariant. |
| T-12-03-02 (Drive file-ID dedup) | `seen_file_ids` keyed off `file["id"]`; test `test_dedup_by_file_id` pins. |
| T-12-03-03 (Calendar markdown injection in title) | Accepted per D-D4 (vault is Glen-only). Title flows verbatim into `f"{title} — {n} attendees"`. |
| T-12-03-04 (Drive filename markdown injection) | Accepted per D-D4 (same posture). |
| T-12-03-05 (Filename match leaks alias↔domain) | Drive branch silently drops no-match files (does NOT route to `_Unknown.md`). Calendar branch routes per D-04 with first-attendee email — same posture as Phase 10. |
| T-12-03-06 (Aliases as regex injection) | `re.escape(needle)` in `_has_word_boundary_match`; test `test_regex_metacharacters_escaped` + `test_unescaped_regex_would_not_match_literal_token` enforce. |
| T-12-03-07 (Idempotency drift in routing) | Three-level deterministic sort `(-len, needle, domain)` for D-A4; alphabetical sort for D-A2; tests `test_alphabetical_first_match_wins_multi_client` + `test_alphabetical_tie_break_on_equal_length` pin both. |
| T-12-03-08 (Stop-list-only silent drops without log) | Accepted — audit trail lives in Wave 4 orchestrator (Plan 12-04) per separation-of-concerns; matcher stays pure. |
| T-12-03-09 (`_DRIVE_FILENAME_STOP_LIST` unbounded growth) | Accepted — frozen module-level constant, only Glen-edited; code review + positive PCA tests catch any accidental client-name addition. |

## Patterns Established for Future Phases

- **N-way alias arbitration with deterministic tie-break**: Phase 12 D-A4-REVISED is the first place "longest substring of N candidates wins, alphabetical tie-break" appears in the codebase. Future routers (Slack username → client, Linear team → client, etc.) needing similar arbitration should follow the `(-len, needle, domain)` sort-key template.
- **Pure routing helpers + caller-owned bookkeeping**: `_match_drive_filename_to_client` returns `None` on no-match without distinguishing stop-list-only matches. The Wave 4 orchestrator owns the stop-list count summary (one info-level feed entry per sync). This separation lets the matcher stay pure (unit-testable without orchestration mocks) and keeps audit-trail concerns out of the routing layer.
- **Adapter-to-kwarg pipeline shape**: Phase 11 established `cm_expiring={"contracts": [...]}` / `cm_invoices={"invoices": [...]}` envelope shapes for `_gather_events`. Phase 12 extended with `cal_events={"items": [...]}` / `drive_files={"files": [...]}` — same pattern, matches the workspace_client adapter return values directly so Wave 4 just flows through. Future external-data sources (Slack threads? Linear issues?) should adopt the same envelope-with-singular-array-key convention.

## Self-Check: PASSED

Files claimed to be modified:
- `scripts/lib/vault_writer.py` — FOUND (modified in commits c5de4e8 + fdc44d0)
- `scripts/tests/test_vault_writer.py` — FOUND (modified in commits faf3f0d + c5de4e8 + d089043)

Commits claimed to exist:
- `faf3f0d` (Task 1 RED) — FOUND in git log
- `c5de4e8` (Task 1 GREEN) — FOUND in git log
- `d089043` (Task 2 RED) — FOUND in git log
- `fdc44d0` (Task 2 GREEN) — FOUND in git log

Verification commands run:
- `python3 -m unittest discover scripts/tests` → 190 tests pass (135 baseline + 55 new)
- `python3 -c 'from scripts.lib.vault_writer import _match_drive_filename_to_client, _has_word_boundary_match, _route_calendar_event_to_slug, _cal_meeting_event_tuple, _drive_doc_event_tuple, _DRIVE_FILENAME_STOP_LIST'` → exit 0
- `python3 -c 'from scripts.lib.vault_writer import _DRIVE_FILENAME_STOP_LIST; assert _DRIVE_FILENAME_STOP_LIST == frozenset({"agend", "iugo", "glen", "rosie"})'` → exit 0
- `python3 -c 'import inspect; from scripts.lib.vault_writer import _gather_events; sig = inspect.signature(_gather_events); assert sig.parameters["cal_events"].default is None; assert sig.parameters["drive_files"].default is None'` → exit 0
- `grep -c "def _match_drive_filename_to_client\|def _has_word_boundary_match\|def _route_calendar_event_to_slug" scripts/lib/vault_writer.py` → 3
- `grep -c "def _cal_meeting_event_tuple\|def _drive_doc_event_tuple\|def _gather_events" scripts/lib/vault_writer.py` → 3
- `grep -c "_DRIVE_FILENAME_STOP_LIST" scripts/lib/vault_writer.py` → 2 (definition + `__all__`)
- `grep -c "cal_events" scripts/lib/vault_writer.py` → 4 (signature + body + docstring + comment)
- `grep -c "drive_files" scripts/lib/vault_writer.py` → 4
- `grep -E "^from .workspace_client|^import .*workspace_client" scripts/lib/vault_writer.py` → empty (exit 1) — Pitfall 1 invariant preserved
- `git diff 68df53e..HEAD --name-only` → `scripts/lib/vault_writer.py`, `scripts/tests/test_vault_writer.py` (no scope leak)

## Next Phase Readiness

- **Wave 4 (Plan 12-04, `_fetch_external_data_for_run`)** can pipe `workspace_client._workspace_get(...)` + `_walk_drive_for_clients(...)` adapter outputs straight into `_gather_events(... cal_events=..., drive_files=...)` — the kwargs accept `{"items": [...]}` for cal and `{"files": [...]}` for drive, matching the Wave 2 adapter envelope shape.
- **Lazy-import discipline (Pitfall 1)**: Wave 4 will add `from .workspace_client import ...` ONLY inside `_fetch_external_data_for_run` (not at module top). Plan 12-03 left the top-level import surface untouched; the negative test `TestProjectionDoesNotImportWorkspace` (to be added in Wave 4) will pin the discipline.
- **Stop-list audit trail (deferred to Wave 4)**: the Wave 4 orchestrator computes the stop-list-only count by re-running `_match_drive_filename_to_client` against each filename and incrementing a counter when the matcher returns None AND any token in `_DRIVE_FILENAME_STOP_LIST` matches via `_has_word_boundary_match`. One info-level feed entry per sync summarises (e.g., `"Phase 12 Drive: 7 stop-list-only filenames silently skipped"`). The plumbing for this is fully in place (matcher + stop-list both exposed in `__all__`); Wave 4 just wires the counter.
- **Phase 11 callers unaffected**: `run_backfill` calls `_gather_events(data_root, clients, cm_expiring=..., cm_invoices=...)` — this still works; `cal_events` and `drive_files` default to None, so the new branches are no-ops for any caller that doesn't pass them. Backwards-compat tests prove this.

---
*Phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings*
*Completed: 2026-05-03*
