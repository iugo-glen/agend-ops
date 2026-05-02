---
phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr
plan: 03
subsystem: vault-writer
tags: [contract-manager, vault-writer, sections, rendering, phase-11]

# Dependency graph
requires:
  - plan: 01
    provides: render_frontmatter accepts cm_extra/cm_stale_since, schemas/feed-entry.json level enum extended with "warning"
  - plan: 02
    provides: cm_summary_to_frontmatter_extra (cm_extra source), call_with_retry("get_sla_status", ...) (sla_result source)
provides:
  - "EMOJI_BY_KIND extended with \"contract\": \"📄\""
  - "MANAGED_SECTIONS = (\"CM-TODOS\", \"OPEN-ITEMS\", \"USAGE\", \"ACTIVITY-LOG\") — Sites OMITTED"
  - "_NOTE_TEMPLATE and _UNKNOWN_TEMPLATE include CM-TODOS and USAGE marker pairs in display order"
  - "build_note_initial_markdown(client, fm_str, open_items, activity_log, cm_todos=…, usage=…) — additive kwargs with placeholder defaults"
  - "render_cm_todos(cm_extra) — D-B3 renderer, three output shapes"
  - "render_usage(sla_result, client_name) — D-C3-REVISED renderer with case-insensitive substring filter"
affects: [11-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Three-state empty-section pattern: explicit None-vs-empty-data distinction (`_(CM data unavailable; will refresh next sync)_` vs `_(no missing CM data)_` vs bullet list) — caller-side cache-fallback semantics surface to the user"
    - "Fixed-tuple monitored_keys idiom for idempotency: tuple-of-tuples (not dict) so iteration order is deterministic across Python versions; mirrors Phase 10's frontmatter key ordering discipline"
    - "Defensive number formatter (`_fmt`) inside render_usage: tolerates None, normalises floats with no fractional part to int strings, falls through to str() for everything else — keeps Glen's vault diffs stable when CM swaps int↔float types"

key-files:
  created: []
  modified:
    - scripts/lib/vault_writer.py
    - scripts/tests/test_vault_writer.py

key-decisions:
  - "monitored_keys uses tuple-of-tuples (`((\"contract_start\", \"Contract start date\"), …)`), NOT a dict — guarantees stable iteration order across runs for D-14/D-16 idempotency"
  - "render_cm_todos signals cache-fallback explicitly: `cm_extra=None` → \"CM data unavailable; will refresh next sync\"; populated-but-empty-fields → bullet list; all-populated → \"no missing CM data\". Three distinct shapes mean Glen sees different signals for different failure modes"
  - "render_usage filter is case-insensitive substring match (`name_lower in clientName.lower()`), NOT equality — defensive against minor mismatches like \"Property Council\" vs \"property council australia\""
  - "_UNKNOWN_TEMPLATE uses placeholder bodies (`_(no missing CM data)_`, `_(no usage data)_`) for the CM-TODOS and USAGE sections — _Unknown.md groups unmatched records, has no client_name to filter against, and never has CM data; the marker pairs still must exist so projection's MANAGED_SECTIONS iteration finds them"
  - "TestProjection fixture extended with new managed sections (Rule 3) — `MANAGED_SECTIONS` is now iterated by run_projection over 4 names; the existing test fixture only had OPEN-ITEMS + ACTIVITY-LOG markers, so adding CM-TODOS and USAGE markers to the fixture is required (NOT a flaky test, this is correctness)"

patterns-established:
  - "Phase 11 renderer signature convention: `render_<section>(<source_dict_or_None>, [<filter_arg>]) -> str`. Always accepts None for the cache-fallback path, returns a sentinel string. Plan 04 should mirror this for any new renderers (e.g. site-section if added later)."
  - "Managed section addition checklist (for future Phase 11.x adding e.g. Sites):\n    1. Append name to MANAGED_SECTIONS tuple in display order\n    2. Add marker pair to _NOTE_TEMPLATE AND _UNKNOWN_TEMPLATE in matching order\n    3. Add format key to build_note_initial_markdown signature with safe default\n    4. Implement render_<section>() following the three-state pattern\n    5. Add to __all__\n    6. Update test fixtures that include managed-section markers (TestProjection)"

requirements-completed: [INTL-01, CM-FRONTMATTER, CM-SECTIONS]
# These match the plan frontmatter requirements list. CM-FRONTMATTER and CM-SECTIONS
# are now structurally complete (templates + renderers); CM-WAVE0 was completed in
# Plan 01. INTL-01 is partially advanced — the rendering surface for CM data is in
# place but Plan 04 must still wire the data through run_backfill.

# Metrics
duration: 6min
completed: 2026-05-02
---

# Phase 11 Plan 03: Managed-Section Rendering Surface Summary

**Wave 3 lands the contract emoji, the CM-TODOS and USAGE managed sections (Sites OMITTED per D-C2-REVISED), and the two renderers — all isolated from CM HTTP. Plan 04 will feed real CM data through these renderers via `_gather_events` extension and run_backfill integration.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-02 (worktree wave 3 spawn)
- **Tasks:** 2 (1 non-TDD constants/templates extension, 1 TDD renderer pair)
- **Tests:** 49 (Phase 10 + 11-01 + 11-02 baseline) → 59 (after Task 2 GREEN). All pass.
- **Files modified:** 2 — `scripts/lib/vault_writer.py`, `scripts/tests/test_vault_writer.py`

## Accomplishments

### Task 1 — constants + templates extension (commit `0dd194e`)

- `EMOJI_BY_KIND` now contains `"contract": "📄"` alongside triage/task/invoice (D-E1). `render_log_line` (lines 200-219) checks `if kind not in EMOJI_BY_KIND:` and accepts the new kind without further changes — Plan 04 can emit `kind="contract"` events through the Activity Log unchanged.
- `MANAGED_SECTIONS` extended from 2 to 4 names — `("CM-TODOS", "OPEN-ITEMS", "USAGE", "ACTIVITY-LOG")` — in display order so projection's iteration matches the on-disk section order. **Sites is OMITTED** (D-C2-REVISED): no SITES marker pair anywhere in the codebase.
- `_NOTE_TEMPLATE` adds two new marker pairs: `<!-- CM-TODOS-START --> ... <!-- CM-TODOS-END -->` between Overview and Open Items, and `<!-- USAGE-START --> ... <!-- USAGE-END -->` between Open Items and Activity Log. The template now has 4 marker pairs, 2 new format keys (`{cm_todos}`, `{usage}`).
- `_UNKNOWN_TEMPLATE` mirrors the change but with hard-coded placeholder bodies (`_(no missing CM data)_`, `_(no usage data)_`) — `_Unknown.md` groups unmatched records and has no client to filter against.
- `build_note_initial_markdown` gains optional kwargs `cm_todos=…` and `usage=…` with safe placeholder defaults so any pre-Phase-11 4-arg caller continues to produce a valid note. Test verified: `build_note_initial_markdown(client, fm_str, open_items, activity_log)` works without modification, produces a note with placeholder bodies in the new sections.
- `TestProjection.test_second_projection_preserves_user_content` fixture extended (Rule 3 deviation — see below) — both source and target templates now carry CM-TODOS and USAGE markers so the projection iteration succeeds.

### Task 2 — render_cm_todos + render_usage with TDD discipline (commits `8504015` RED → `9c2f381` GREEN)

- `render_cm_todos(cm_extra: dict | None) -> str`:
  - `None` → `_(CM data unavailable; will refresh next sync)_` (cache-fallback signal)
  - All 4 monitored keys (contract_start, contract_end, primary_contact, deployed_modules) populated → `_(no missing CM data)_`
  - Any monitored key empty (empty string, empty list, or None) → bullet list with explanatory text and link to https://contracts.agend.info/
  - **`sites` is NOT iterated** (D-C2-REVISED steady state) — verified by `test_sites_is_not_a_missing_condition`.
- `render_usage(sla_result: dict | None, client_name: str) -> str`:
  - `None` or empty `projects[]` or no client match → `_(no usage data)_`
  - Per-project bullet shape: `- **{projectName}** — {hoursLogged} hrs of {hoursBudgeted} ({percentConsumed}%) [{status}]`
  - Filter is case-insensitive substring match on `clientName` → `Property Council` matches `property council australia`.
  - Defensive number formatter normalises `12.0` → `"12"`, leaves `12.5` as-is, returns `"?"` for missing values.
- Both functions exported via `__all__` (alphabetical-proximate to existing render_*).
- 10 new tests pass: 5 for `TestCmTodosSection` + 5 for `TestUsageSection`. Full suite 59/59 green.

## Task Commits

| Task | Phase | Commit | Type |
| ---- | ----- | ------ | ---- |
| Task 1 — constants + templates extension | n/a (non-TDD) | `0dd194e` | feat |
| Task 2 — failing render_cm_todos / render_usage tests | RED | `8504015` | test |
| Task 2 — render_cm_todos / render_usage implementation | GREEN | `9c2f381` | feat |

REFACTOR phase: skipped. Both renderers are minimal, single-responsibility, and follow the plan's spec verbatim. The `_fmt` helper is local to `render_usage` (not exported) and there is no shared structure between the two renderers worth extracting yet.

## Files Created/Modified

- **`scripts/lib/vault_writer.py`** (MODIFIED, +99 lines / -7 lines)
  - Line 49: `EMOJI_BY_KIND` dict extended with one key.
  - Line 51-53: `MANAGED_SECTIONS` tuple extended from 2 to 4 names; comment updated to reflect Phase 11 D-B3/D-C1/D-C3-REVISED.
  - Lines 243-275: `_NOTE_TEMPLATE` literal — 14 lines added (CM-TODOS marker pair + USAGE marker pair, each with header, format-key body, and end marker).
  - Lines 277-313: `_UNKNOWN_TEMPLATE` literal — 14 lines added (same marker pairs but with hard-coded placeholder bodies).
  - Lines 558-647: two new render functions inserted between `render_open_items` and `render_activity_log`. Source order verified: open_items (520) → cm_todos (561) → usage (599) → activity_log (650).
  - Lines 711-722: `build_note_initial_markdown` signature extended with `cm_todos: str = "_(no missing CM data)_"` and `usage: str = "_(no usage data)_"`. Body adds two `.format()` keys.
  - `__all__` (line 1439): adds `"render_cm_todos", "render_usage",` line.
- **`scripts/tests/test_vault_writer.py`** (MODIFIED, +118 lines / -4 lines)
  - Lines 411-456: `test_second_projection_preserves_user_content` fixture extended with CM-TODOS and USAGE markers in both source and target; new assertions verify the new managed sections splice through.
  - Lines 671-779: two new test classes appended (`TestCmTodosSection` with 5 tests, `TestUsageSection` with 5 tests).

## Decisions Made

- **`monitored_keys` is a tuple-of-tuples, not a dict.** This guarantees stable iteration order across Python versions (dicts have insertion-ordered iteration since 3.7 but the tuple form is a stronger contract). Two consecutive `render_cm_todos` calls with the same input produce byte-identical output — the D-14/D-16 idempotency promise extends to the new section.
- **Three-state output pattern, not two.** Distinguishing `None` (CM unreachable) from "all populated" (no work for Glen) from "some empty" (Glen has work) gives Glen three different signals on the dashboard. A binary "data or no data" pattern would conflate cache-fallback with empty-CM-record, hiding a real failure mode.
- **`render_usage` filter is case-insensitive substring, not equality.** CM is Glen's own server, but client-name spelling drift between CM and `data/config/clients.jsonl` is a real risk (e.g. "Property Council" vs "Property Council Australia"). Substring match handles both directions; case-insensitive handles capitalisation drift. The cost (false positives matching unrelated clients with overlapping names) is bounded — Glen has ~30 clients and would notice immediately.
- **`render_usage`'s defensive `_fmt` helper.** CM's get_sla_status documentation says fields are numbers, but Glen has been bitten by API drift before. `_fmt` collapses `12.0 → "12"` and `12.5 → "12.5"` and `None → "?"` — keeps the rendered bullet stable when CM swaps int↔float types. Without `_fmt`, every CM serialisation change would produce a noisy diff in Glen's vault.
- **`_UNKNOWN_TEMPLATE` uses literal placeholder bodies, not template format keys.** `_Unknown.md` is a synthetic note for unmatched records; it has no client to filter against and never has CM data. Hard-coding `_(no missing CM data)_` / `_(no usage data)_` matches the same strings that `render_cm_todos` / `render_usage` return for their respective empty cases — Glen sees identical text whether viewing a real client or _Unknown.md.
- **Test fixture update for `TestProjection.test_second_projection_preserves_user_content`.** This was the ONE existing test that broke when MANAGED_SECTIONS grew. The other 4 projection tests assert "skipped_marker_error >= 1" or "subprocess.run not called" — those still pass under the new marker requirements (just for a slightly different reason; the abort fires on the missing CM-TODOS marker instead of the originally-targeted broken section). Only the success-path test (`projected == 1`) needed the fixture extension.

## Deviations from Plan

**One Rule 3 (blocking issue) deviation, auto-applied:**

**1. [Rule 3 — Blocking issue] TestProjection fixture needed CM-TODOS / USAGE markers**
- **Found during:** Task 1 verification — running the full test suite after the constants/templates change surfaced a single test failure: `test_second_projection_preserves_user_content` reported `stats["projected"] == 0` instead of `1`.
- **Issue:** `run_projection`'s "existing target" path iterates `MANAGED_SECTIONS` and aborts on any source/target file lacking the markers. The plan's Task 1 changed `MANAGED_SECTIONS` from `("OPEN-ITEMS", "ACTIVITY-LOG")` to `("CM-TODOS", "OPEN-ITEMS", "USAGE", "ACTIVITY-LOG")`, but the existing test fixture only included markers for OPEN-ITEMS and ACTIVITY-LOG. The first iteration (CM-TODOS) couldn't find markers in the source, so the projection aborted and incremented `skipped_marker_error` instead of `projected`.
- **Fix:** Extended both source and target fixtures in `test_second_projection_preserves_user_content` to include CM-TODOS and USAGE marker pairs alongside the existing OPEN-ITEMS and ACTIVITY-LOG pairs. Strengthened the test assertions to also verify the new managed sections splice through (added `assertIn("UPDATED-CM-TODOS", after)`, `assertIn("UPDATED-USAGE", after)`, and corresponding `assertNotIn` checks for the old content).
- **Files modified:** `scripts/tests/test_vault_writer.py` (lines ~411-456).
- **Commit:** `0dd194e` (bundled with Task 1 — the production change forced the fixture update; isolating them into separate commits would have left the suite red between commits, which is worse for bisect).
- **Why this is Rule 3 not Rule 1:** the production code change is correct (the projection MUST iterate all managed sections to remain idempotent). The test fixture was correct for the Phase 10 contract; it became incorrect when Plan 11-03 widened the contract. This is the canonical "fix tests to match the new contract" case, not a bug.

**No other deviations.** Rule 1 (bugs), Rule 2 (missing critical functionality), and Rule 4 (architectural) had no triggers. Each task's `<action>` block was followed verbatim. No stubs introduced (the "TODO: Missing CM Data" header in the templates is the section TITLE, not a code stub).

## Issues Encountered

- **None blocking.** The Rule 3 deviation above was caught immediately by the post-Task-1 full-suite verification, fixed within the same commit, and re-verified before proceeding to Task 2's RED phase.
- **AUTO_MODE handling:** Plan 11-03 has no checkpoints (`autonomous: true` in frontmatter). AUTO_MODE was a no-op for this plan — there were no human-verify or decision gates to auto-approve.

## TDD Gate Compliance

- **Task 1 (non-TDD by plan spec):** No RED gate required. Verified by post-edit acceptance criteria (constants/templates produce expected output).
- **Task 2 (TDD by plan spec):**
  - **RED:** `8504015` — all 10 new tests fail with `ImportError: cannot import name 'render_cm_todos' / 'render_usage'`. Clean RED gate.
  - **GREEN:** `9c2f381` — all 10 new tests pass; full suite 59/59.
  - **REFACTOR:** Skipped. Both renderers are ~30 lines each, single-responsibility, no shared structure to extract. Adding refactor churn would obscure intent.

## Threat Model Compliance

- **T-11-03-01 (marker discipline failure):** ✅ All 4 marker pairs present in both `_NOTE_TEMPLATE` and `_UNKNOWN_TEMPLATE`. `MANAGED_SECTIONS` is the canonical list iterated by `replace_managed_section` and `run_projection`. The D-08a ABORT semantics fire identically for any of the 4 sections.
- **T-11-03-02 (prompt injection via project names):** ✅ `render_usage` interpolates `proj.get("projectName")` into the bullet `- **{name}** — N hrs of M (P%)`. The double-asterisk wrapping constrains the literal name's position; even a malicious name like `[click](http://evil)` renders as a literal markdown link in Glen's vault — safe.
- **T-11-03-03 (prompt injection via contract names in CM-TODOS):** ✅ Bullets interpolate the literal key name (e.g. `contract_start`), NOT a CM-controlled value. The hyperlink target is hard-coded `https://contracts.agend.info/`. No CM data flows into the URL or link target.
- **T-11-03-04 (Sites field accidentally rendered):** ✅ Verified by `test_sites_is_not_a_missing_condition` — `render_cm_todos` does NOT iterate `sites`. The frontmatter still includes `sites: []` (Plan 01) for forward-compat with future DataView queries, but no managed section renders it.
- **T-11-03-05 (idempotency drift):** ✅ `monitored_keys` is a fixed tuple-of-tuples (not a dict that could permute insertion order). `render_usage` iterates `matched` projects in CM's response order. Two consecutive runs with the same input produce byte-identical output. Plan 04's `TestBackfillIdempotent` will extend `_snapshot_managed` to confirm.
- **T-11-03-06 (placeholder string drift):** ✅ All three "empty" outputs are pinned by tests with exact-string assertions: `_(no missing CM data)_`, `_(CM data unavailable; will refresh next sync)_`, `_(no usage data)_`. Any future drift fails the test loudly.
- **T-11-03-07 (UI confusion):** ✅ Inherits Phase 10 emoji palette; the contract emoji (📄) is distinct from invoice (💰), task (✅), and triage (📧). Plan 04 will add the source-tag (`> source: contract-manager`) per D-D2.

No new threat surface introduced. No `## Threat Flags` section needed.

## User Setup Required

None for Plan 11-03 specifically. The renderers don't make any HTTP calls and don't need any external configuration. The deferred CM API key + Coolify env injection from Plan 11-02's Task 3 is still needed before Plan 11-04 wires the renderers to live data — but that is a Plan 11-04 prerequisite, not a Plan 11-03 prerequisite.

## Next Phase Readiness

- **Plan 11-04 (`_gather_events` extension + run_backfill CM integration)** can now call:
  - `render_cm_todos(cm_extra)` — with `cm_extra` from `cm_summary_to_frontmatter_extra(...)` (Plan 02), or `None` if cache fallback exhausted.
  - `render_usage(sla_result, client["client_name"])` — with `sla_result` from `cm_client.call_with_retry("get_sla_status", {"clientId": cm_id, "asOfDate": today})`, or `None` if cache fallback exhausted.
  - `build_note_initial_markdown(client, fm_str, open_items, activity_log, cm_todos=…, usage=…)` — both new kwargs accept the renderer outputs directly.
- **Plan 11-04 idempotency tests** must extend `TestBackfillIdempotent._snapshot_managed` to capture the 4-section state (CM-TODOS + OPEN-ITEMS + USAGE + ACTIVITY-LOG) instead of the 2-section Phase 10 state. The test pattern stays the same — just iterate over `MANAGED_SECTIONS` directly so future additions don't require test edits.
- **Activity Log will accept `kind="contract"`** events automatically. Plan 11-04's `_gather_events` extension can emit contract-renewal entries with the new emoji without any further `render_log_line` changes.

## Self-Check: PASSED

**Files claimed to be modified — all FOUND in commits:**

- `scripts/lib/vault_writer.py` — FOUND (commits `0dd194e`, `9c2f381`)
- `scripts/tests/test_vault_writer.py` — FOUND (commits `0dd194e`, `8504015`)

**Commits claimed to exist — all FOUND in git log:**

- `0dd194e` (feat: constants + templates) — FOUND
- `8504015` (test: RED for renderers) — FOUND
- `9c2f381` (feat: GREEN for renderers) — FOUND

**Verification commands — all pass:**

- `python3 -m unittest discover scripts/tests` → 59 tests, OK
- `python3 -c 'from scripts.lib.vault_writer import EMOJI_BY_KIND, MANAGED_SECTIONS, render_cm_todos, render_usage'` → exit 0
- `python3 -c 'from scripts.lib.vault_writer import EMOJI_BY_KIND; assert EMOJI_BY_KIND["contract"] == "📄"'` → exit 0
- `python3 -c 'from scripts.lib.vault_writer import MANAGED_SECTIONS; assert MANAGED_SECTIONS == ("CM-TODOS", "OPEN-ITEMS", "USAGE", "ACTIVITY-LOG")'` → exit 0
- `grep -v '^#' scripts/lib/vault_writer.py | grep -c "CM-TODOS-START"` → 2 (≥ 2 — `_NOTE_TEMPLATE` + `_UNKNOWN_TEMPLATE`)
- `grep -v '^#' scripts/lib/vault_writer.py | grep -c "USAGE-START"` → 2 (≥ 2)
- `grep -v '^#' scripts/lib/vault_writer.py | grep -c "SITES-START"` → 0 (D-C2-REVISED holds)
- `grep -c "def render_cm_todos" scripts/lib/vault_writer.py` → 1
- `grep -c "def render_usage" scripts/lib/vault_writer.py` → 1
- `grep -v '^#' scripts/lib/vault_writer.py | grep -c "render_sites"` → 0 (no Sites renderer anywhere)
- `awk '/^def render_open_items/{a=NR} /^def render_cm_todos/{b=NR} /^def render_usage/{c=NR} /^def render_activity_log/{d=NR} END{exit !(a<b && b<c && c<d)}' scripts/lib/vault_writer.py` → exit 0 (source order: 520 → 561 → 599 → 650)
- `python3 -c 'from scripts.lib.vault_writer import build_note_initial_markdown; out = build_note_initial_markdown({"domain":"x.com","client_name":"X"}, "---\nx: y\n---\n", "_(none)_", "<!-- empty -->"); assert "CM-TODOS-START" in out; assert "USAGE-START" in out; assert "SITES" not in out'` → exit 0 (default kwargs work — backwards compat)
- `git status --porcelain` (non-config files only) → empty after Task commits

---
*Phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr*
*Completed: 2026-05-02*
