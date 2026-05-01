---
phase: 10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli
plan: 02
subsystem: backend
tags: [python, vault-writer, ruamel-yaml, ndjson, atomic-write, marker-splice, idempotency, tdd-green, obsidian, sync-engine]

# Dependency graph
requires:
  - phase: 10
    plan: 01
    provides: scripts/tests/test_vault_writer.py RED scaffold (20 tests; 19 active + 1 SKIPPED) locking the symbol surface; scripts/lib/__init__.py + scripts/tests/__init__.py packages; ruamel.yaml>=0.18,<0.19 declared in scripts/requirements.txt; vault-build/Clients/.gitkeep so the directory exists in fresh clones
provides:
  - scripts/lib/vault_writer.py — single-module sync engine exporting 18 symbols (slugify family, replace_managed_section + MarkerError, render_log_line, run_backfill, run_incremental, main, plus helpers — see Symbol Exports section below)
  - vault-build/Clients/{property-council-australia,association-for-tertiary-education-management,occupational-therapy-australia}.md + _Unknown.md — first real backfill output committed to repo (D-02 transport rail; 62 events routed)
  - --feed-path argparse arg threaded through every code path that may write a system/critical feed entry, default <data_root>/feed.jsonl resolved at the CLI boundary so failure-path handler and library calls share the value (Issue 1 + Issue 6)
  - TestMain.test_main_failure_path_writes_critical_feed_to_temp activated (skip decorator removed) — 20/20 tests now green; production data/feed.jsonl audit trail proven untouched after running the failure-path test
affects: [10-03-PLAN, 10-04-PLAN, 10-05-PLAN]

# Tech tracking
tech-stack:
  added:
    - "ruamel.yaml 0.18.x (installed via pip3 install --break-system-packages from scripts/requirements.txt)"
  patterns:
    - "Pattern 1: marker-aware atomic markdown splice — tempfile.mkstemp + os.replace + os.fsync(file) + os.fsync(dir) so iCloud's bird/cloudd cannot upload a partial state"
    - "Pattern 1 sibling: _atomic_write for the whole-file recreate path used by regenerate-from-full backfill"
    - "Pattern 3: NDJSON streaming + per-client bucketing via _gather_events; lenient on blank/bad lines (T-10-06 mitigation)"
    - "Pattern 5: NFKD-normalized ASCII-folded slug with collision-resistant slug_with_domain fallback in load_clients()"
    - "Pattern 6: ruamel.yaml round-trip frontmatter render (4 D-09 v1 fields snake_case; ISO 8601 with TZ offset matching schemas/feed-entry.json regex)"
    - "Pattern 7: render_log_line ### [YYYY-MM-DD HH:MM] {emoji} {summary} with optional > detail and > [Open thread](gmail-url)"
    - "Pattern 8: render_unknown_note groups by client_name (or email-domain) with explicit data-quality-flag annotation when client_name is a triage priority bucket like \"needs-response\""
    - "Issue 1 + Issue 6 isolation pattern: --feed-path argparse arg threaded through main → run_backfill → run_incremental → append_feed_entry, default resolved ONCE at the CLI boundary so library callers and the failure-path handler share the same value"
    - "Failure-path-must-fire pattern: run_backfill raises FileNotFoundError when data_root is missing so the documented critical-feed-entry contract actually executes (Issue 1 invariant)"

key-files:
  created:
    - scripts/lib/vault_writer.py (842 lines, single-module sync engine — Plan 10-04 will extend with --mode project-to-icloud using the same --feed-path threading pattern)
    - vault-build/Clients/property-council-australia.md (2.4K, 7 activity log entries)
    - vault-build/Clients/association-for-tertiary-education-management.md (782B, no records yet — D-15a stub)
    - vault-build/Clients/occupational-therapy-australia.md (835B, no records yet — D-15a stub)
    - vault-build/Clients/_Unknown.md (13K, 5 group buckets including the priority-bucket leak annotation for "needs-response")
  modified:
    - scripts/tests/test_vault_writer.py (1 line — removed @unittest.skip decorator on TestMain.test_main_failure_path_writes_critical_feed_to_temp; the test body was already written by Plan 01)

key-decisions:
  - "OVERVIEW marker pair dropped per researcher recommendation (10-RESEARCH §Pattern 2) — Overview is Glen-owned freeform and adding empty markers around a single-line stub creates no value while inviting marker-corruption Rule-2 fixes"
  - "_atomic_write is a sibling of replace_managed_section, NOT a refactor of it — backfill regenerates whole files (D-14, D-16); marker splice only matters for Plan 04's iCloud projection where user-owned Overview/Decisions live"
  - "run_backfill raises FileNotFoundError on missing data_root — without this, the documented Issue 1 failure-path test would have green-passed by silently writing 4 stub-only notes (1 client_unknown stub + _Unknown.md) instead of raising; this is a Rule-1 fix per the deviation rules"
  - "_Unknown.md grouping accepts BOTH (event_tuple, source_record) pairs AND bare event_tuples for backward compatibility — only the pair form can attach the data-quality-flag annotation when client_name leaks a priority bucket name"
  - "Lenient stream_ndjson (warns to stderr, continues processing) — matches RESEARCH.md Pitfall 3 + the repo's validate-data.sh stance; a single corrupt line cannot abort an entire backfill of 62 events"
  - "ruamel.yaml installed via pip3 install --break-system-packages because the macOS Python 3.14 environment is PEP-668-marked external — documented for Plan 10-03 which will provide a setup script"

patterns-established:
  - "Module-level __all__ updated incrementally per plan task — Task 1 listed 12 exports, Task 2 added run_backfill / run_incremental / main / load_clients / stream_ndjson / d10_triage_filter / render_open_items / render_activity_log / render_frontmatter / render_unknown_note / build_note_initial_markdown for a final 18-symbol surface"
  - "Pattern 7 line rendering composes with Pattern 8 _Unknown.md grouping — render_unknown_note calls render_activity_log per-group, demonstrating that the line-rendering primitive composes upward without modification"

requirements-completed: [INTL-01]

threat-mitigations-applied:
  - "T-10-04 (tampering on managed-section write): replace_managed_section AND _atomic_write both use tempfile.mkstemp + os.fsync(file) + os.replace + os.fsync(dir) — verified by TestReplaceManagedSection.test_atomic_write_no_partial_state and TestBackfillIdempotent.test_two_runs_identical_managed_content"
  - "T-10-05 (information disclosure via _Unknown.md): accepted by design — _Unknown.md surfaces data-quality misfires per D-06a; the 'needs-response' priority bucket leak annotation is the documented feature, not a bug"
  - "T-10-06 (DOS via malformed NDJSON line): stream_ndjson catches json.JSONDecodeError per-line, warns to stderr, continues — backfill of 62 valid events tolerated coexisting with the dismissed-field schema drift in data/triage/2026-03-23T095320.jsonl"
  - "T-10-07 (path traversal via slug): safe_slugify outputs only [a-z0-9-]; output_dir / f'{slug}.md' construction prevents user-controlled path prefix"
  - "T-10-08 (repudiation via swallowed sync failure): main() except branch ALWAYS writes a system/critical feed entry to the threaded feed_path before sys.exit(1) — verified by TestMain.test_main_failure_path_writes_critical_feed_to_temp which runs main against /nonexistent-issue1-isolation"
  - "T-10-08a (test invocations polluting production data/feed.jsonl): --feed-path argparse arg threaded through every code path; default resolved at CLI boundary; verified end-to-end by TestMain assertion on temp feed_path PLUS git hash-object diff before/after the test = identical (production audit trail untouched)"
  - "T-10-09 (feed entry forged from external input): accepted — summary capped at 200 chars per schemas/feed-entry.json, repo is single-user private, exception messages are bounded by traceback.format_exc()[-1000:]"

# Metrics
duration: 5min
completed: 2026-05-01
---

# Phase 10 Plan 02: Vault Writer Sync Engine Summary

**Implemented `scripts/lib/vault_writer.py` (842 lines, 18 symbols) — the load-bearing sync engine for Phase 10 — turning Plan 01's 19 RED tests + 1 SKIPPED placeholder fully GREEN (20/20), running a real backfill against `data/` that routes 62 events into 4 markdown notes, and proving via subprocess test that the `--feed-path` argparse threading keeps the production `data/feed.jsonl` audit trail untouched when failure paths fire (Issue 1).**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-01T08:49:03Z
- **Completed:** 2026-05-01T08:54:03Z
- **Tasks:** 2 (both auto+tdd, both passed verification with one Rule-1 deviation in Task 2)
- **Files created:** 5 (scripts/lib/vault_writer.py + 4 vault-build/Clients/*.md)
- **Files modified:** 1 (scripts/tests/test_vault_writer.py — removed @unittest.skip)

## Symbol Exports

Final `__all__` surface (18 symbols, up from 12 after Task 1):

```python
__all__ = [
    "MarkerError",
    "slugify", "slug_with_domain", "safe_slugify",
    "replace_managed_section",
    "handle_marker_error_for_feed", "append_feed_entry", "now_iso_with_offset",
    "render_log_line",
    "EMOJI_BY_KIND", "MANAGED_SECTIONS", "TS_PATTERN",
    "load_clients", "stream_ndjson", "d10_triage_filter",
    "render_open_items", "render_activity_log", "render_frontmatter",
    "render_unknown_note", "build_note_initial_markdown",
    "run_backfill", "run_incremental", "main",
]
```

Key signatures (Issue 1 / Issue 6 — `feed_path` threaded everywhere it can be needed):

```python
def run_backfill(data_root: Path, build_root: Path, dry_run: bool = False,
                 feed_path: Path | None = None) -> dict
def run_incremental(data_root: Path, build_root: Path, record_type: str = "all",
                    dry_run: bool = False, feed_path: Path | None = None) -> dict
def main() -> None  # argparse: --mode {backfill,incremental} --data-root --build-root
                    #          --record-type {triage,task,invoice,all} --record-id
                    #          --dry-run --feed-path
def append_feed_entry(entry: dict, *, feed_path: Path) -> None
```

## Test Counts (RED → GREEN)

| Test class | Methods | After Task 1 | After Task 2 |
|------------|---------|--------------|--------------|
| TestSlugify | 6 | 6 ✅ | 6 ✅ |
| TestReplaceManagedSection | 2 | 2 ✅ | 2 ✅ |
| TestMarkerError | 5 | 5 ✅ | 5 ✅ |
| TestRenderLogLine | 5 | 5 ✅ | 5 ✅ |
| TestBackfillIdempotent | 1 | RED (no run_backfill yet) | 1 ✅ |
| TestMain | 1 | SKIPPED | 1 ✅ (skip removed + activated) |
| **Total** | **20** | **18 / 20** | **20 / 20** |

```text
$ python3 -m unittest discover scripts/tests
....................
----------------------------------------------------------------------
Ran 20 tests in 0.098s
OK
```

## Sample Backfill Output

```text
$ python3 -m scripts.lib.vault_writer --mode backfill --data-root data --build-root vault-build
vault_writer backfill complete: {'clients_written': 4, 'events_routed': 62}

$ ls vault-build/Clients/
_Unknown.md
association-for-tertiary-education-management.md
occupational-therapy-australia.md
property-council-australia.md

$ wc -l vault-build/Clients/*.md
   286  _Unknown.md
    23  association-for-tertiary-education-management.md
    23  occupational-therapy-australia.md
    51  property-council-australia.md
```

Sample frontmatter (Pattern 6 round-tripped via ruamel.yaml — D-09 v1 four fields, snake_case, ISO 8601 with TZ offset matching `schemas/feed-entry.json` regex):

```yaml
---
domain: propertycouncil.com.au
client_name: Property Council Australia
status: active
last_synced: '2026-05-01T18:22:56+09:30'
---
```

Sample activity log line (Pattern 7 / D-12):

```markdown
### [2026-03-23 01:11] 📧 Re: Agend x PCA Shopping Centre Online - SOW Review & Finalisation Meeting
> urgent · contract · Review PCA updated SOW with comments before Tuesday meeting
> [Open thread](https://mail.google.com/mail/u/0/#inbox/19d17c8e63ca79c1)
```

## Idempotency Verification (D-14, D-16)

```text
$ python3 -m scripts.lib.vault_writer --mode backfill && cp -r vault-build/Clients /tmp/run1-$$
$ python3 -m scripts.lib.vault_writer --mode backfill
$ diff -ru --ignore-matching-lines='^last_synced:' /tmp/run1-$$ vault-build/Clients
$ echo "diff exit: $?"
diff exit: 0
```

Two consecutive backfills produce byte-identical managed sections excluding the `last_synced:` line. Confirmed via test (`TestBackfillIdempotent.test_two_runs_identical_managed_content`) and via real-data run.

## Issue 1 Isolation Confirmation

**Production `data/feed.jsonl` is provably untouched** when the failure-path test runs:

```text
$ git hash-object data/feed.jsonl  # before
8741905a3cbe72642fb91e4e4db1908c8057a1f0
$ python3 -m unittest scripts.tests.test_vault_writer.TestMain -v
test_main_failure_path_writes_critical_feed_to_temp ... ok
Ran 1 test in 0.070s
OK
$ git hash-object data/feed.jsonl  # after
8741905a3cbe72642fb91e4e4db1908c8057a1f0
$ git diff --stat data/feed.jsonl
(empty)
```

The TestMain test invokes `main()` via subprocess with `--data-root /nonexistent-issue1-isolation` and `--feed-path <tempdir>/data/feed.jsonl`. The non-existent data-root makes `run_backfill` raise `FileNotFoundError`; main()'s except branch builds the system/critical feed entry and writes it to the **threaded** `--feed-path` (the temp dir), not to `data/feed.jsonl`. Production audit trail integrity verified end-to-end.

## Task Commits

Each task committed atomically:

1. **Task 1: vault_writer library functions (slug, marker, render)** — `7374169` (feat)
   - 18 of 20 tests green (TestSlugify ×6, TestReplaceManagedSection ×2, TestMarkerError ×5, TestRenderLogLine ×5)
   - 12 symbols exported in initial `__all__`

2. **Task 2: backfill/incremental + --feed-path threading + activate TestMain** — `b19f083` (feat)
   - All 20 tests green; TestMain skip decorator removed
   - 6 additional symbols added (run_backfill, run_incremental, main, plus 8 helper renderers/loaders)
   - 4 vault-build/Clients/*.md files generated and committed (D-02 transport rail)

## Files Created/Modified

- **`scripts/lib/vault_writer.py`** (NEW, 842 lines) — single-module sync engine. Two-section structure: Task 1 implementations (lines 1-241: imports, constants, MarkerError, slug family, replace_managed_section, feed-entry helpers, render_log_line, _yaml_instance) followed by Task 2 extensions (lines 243-842: note templates, _atomic_write, load_clients, stream_ndjson, d10_triage_filter, _route_to_slug, _event_tuple, render_open_items, render_activity_log, render_frontmatter, build_note_initial_markdown, render_unknown_note, _gather_events, run_backfill, run_incremental, main, final __all__).
- **`scripts/tests/test_vault_writer.py`** (MODIFIED, -1 line) — removed `@unittest.skip("Activated in Plan 02 Task 2 once main() supports --feed-path argparse")` decorator on `TestMain.test_main_failure_path_writes_critical_feed_to_temp`. The test body was already in place from Plan 01.
- **`vault-build/Clients/property-council-australia.md`** (NEW, 2.4K) — 7 triage activity log entries spanning 2026-03-22 to 2026-03-23, all `urgent` or `needs-response` per D-10 filter; routed via D-04 exact `client_domain` match against `propertycouncil.com.au`.
- **`vault-build/Clients/association-for-tertiary-education-management.md`** (NEW, 782B) — D-15a stub note (no records currently route to ATEM via exact domain match — the one informational triage about ATEM has `priority: informational` so it's filtered out by D-10).
- **`vault-build/Clients/occupational-therapy-australia.md`** (NEW, 835B) — D-15a stub note.
- **`vault-build/Clients/_Unknown.md`** (NEW, 13K) — 5 group buckets surfaced for cleanup per D-06a, including the documented `needs-response` priority-bucket leak annotation (`task-2026-03-23-002` and `-003` have `client_name: "needs-response"` from upstream triage misfires).

## Decisions Made

- **Drop OVERVIEW marker pair (researcher recommendation honored)** — the Overview section is Glen-owned freeform; adding empty markers around the single-line stub creates corruption-error surface without value.
- **`_atomic_write` is a sibling of `replace_managed_section`, not a refactor** — backfill regenerates whole files (D-14, D-16); marker splice only matters for Plan 04's iCloud projection where user-owned Overview/Decisions live.
- **`run_backfill` raises `FileNotFoundError` on missing `data_root`** — necessary so the documented Issue 1 failure-path test exercises the critical-feed-entry contract; without this, the test would have green-passed by silently writing stub-only notes against the empty universe.
- **`_Unknown.md` grouping accepts both `(event_tuple, source_record)` pairs and bare tuples** — backward compatible; only the pair form can attach the data-quality-flag annotation when `client_name` leaks a priority bucket name.
- **Lenient `stream_ndjson` (warn + continue, never abort)** — matches RESEARCH.md Pitfall 3 + the repo's `validate-data.sh` stance; a single corrupt line cannot abort an entire backfill.
- **Install ruamel.yaml via `pip3 install --break-system-packages`** — macOS Python 3.14 environment is PEP-668-marked external; documented here for Plan 10-03 which will provide a setup script.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `run_backfill` returned success against a non-existent `data_root` instead of raising**

- **Found during:** Task 2, when running `TestMain.test_main_failure_path_writes_critical_feed_to_temp`
- **Issue:** The test invokes `main` via subprocess with `--data-root /nonexistent-issue1-isolation` expecting backfill to raise so main()'s except branch fires and writes a critical feed entry to the threaded `--feed-path`. My initial `run_backfill` was too lenient: `load_clients` returns `{}` on missing `clients.jsonl`, the various NDJSON streams are empty, and the backfill silently succeeds writing only `_Unknown.md`. Test failed: `expected non-zero exit; stdout="vault_writer backfill complete: {'clients_written': 1, 'events_routed': 0}"`.
- **Fix:** Added a hard precondition at the top of `run_backfill`: `if not data_root.exists(): raise FileNotFoundError(...)`. Missing `config/clients.jsonl` is still tolerable (load_clients warns + returns `{}` — useful for fresh-checkout sanity); but a missing `data_root` is a configuration error that must surface as a failure-path feed entry per the Issue 1 invariant.
- **Files modified:** `scripts/lib/vault_writer.py` (5 lines added inside `run_backfill`)
- **Commit:** `b19f083`

No other deviations — both tasks otherwise executed exactly as the plan specified.

## Authentication Gates

None encountered — vault_writer.py is a pure local file-I/O module with no network or auth surface.

## Issues Encountered

- **rtk grep wrapper does not pass through `-F`, `-B`, `-c`, `-n`, `-E` flags** (environmental, not project): verified all such acceptance criteria via Python one-liners instead. Underlying file content meets every criterion.
- **ruamel.yaml not installed by default**: macOS Python 3.14 is PEP-668-marked external. Installed via `pip3 install --break-system-packages 'ruamel.yaml>=0.18,<0.19'`. Plan 10-03 will own a real setup script that handles both Coolify (Linux) and Mac Studio (macOS) install paths cleanly.

## Threat Model Compliance

All 7 documented threats addressed (see frontmatter `threat-mitigations-applied` for the full table). T-10-04 (atomic write tampering), T-10-08 (repudiation via swallowed failure), and T-10-08a (test pollution of production feed) are the load-bearing mitigations and are all verified by automated tests (`TestReplaceManagedSection.test_atomic_write_no_partial_state`, `TestBackfillIdempotent`, and `TestMain.test_main_failure_path_writes_critical_feed_to_temp` respectively).

No new threat surface introduced beyond what the plan's `<threat_model>` documents — no network endpoints, no auth paths, no schema changes at trust boundaries. The vault-build/Clients/ writes are local file-I/O within an already-trusted directory tree. No `Threat Flags` section needed.

## TDD Gate Compliance

This plan is the GREEN half of the cross-plan TDD pair started by Plan 01:

- **RED gate** (Plan 01): `47b8f7f` — `test(10-01): scaffold scripts/tests/test_vault_writer.py with 19 RED tests + 1 SKIPPED placeholder`
- **GREEN gate** (this plan, Task 1): `7374169` — `feat(10-02): implement vault_writer library functions (slug, marker, render)` — turns 18 of 20 tests green
- **GREEN gate completion** (this plan, Task 2): `b19f083` — `feat(10-02): backfill/incremental + --feed-path threading + activate TestMain` — turns the remaining 2 tests green (TestBackfillIdempotent + TestMain) for full 20/20

No REFACTOR gate required — the implementation is straight-through and matches the plan's <action> blocks. Final test suite is 20/20 OK.

## Known Stubs

None. Every function is implemented and exercised by tests or by the real backfill against `data/`. The Decisions section in every generated note is a Glen-owned manual stub by design (D-18) and is documented as such — not a code stub.

## Verification Results

```text
$ python3 -m unittest discover scripts/tests 2>&1 | tail -3
Ran 20 tests in 0.098s
OK

$ python3 -m scripts.lib.vault_writer --mode backfill --data-root data --build-root vault-build 2>&1 | tail -1
vault_writer backfill complete: {'clients_written': 4, 'events_routed': 62}

$ ls vault-build/Clients/
_Unknown.md
association-for-tertiary-education-management.md
occupational-therapy-australia.md
property-council-australia.md

$ for f in vault-build/Clients/*.md; do
>   [ "$(grep -c 'ACTIVITY-LOG-START' "$f")" = "1" ] && [ "$(grep -c 'ACTIVITY-LOG-END' "$f")" = "1" ] || echo "BAD: $f"
> done
(no output — all marker pairs intact)

$ python3 -m scripts.lib.vault_writer --mode backfill --dry-run 2>&1 | tail -1
vault_writer backfill complete: {'clients_written': 0, 'events_routed': 62}
$ git status --short vault-build/  # dry-run leaves no changes
(no output)

$ # Issue 1 isolation
$ git hash-object data/feed.jsonl     # before
8741905a3cbe72642fb91e4e4db1908c8057a1f0
$ python3 -m unittest scripts.tests.test_vault_writer.TestMain -v 2>&1 | tail -3
Ran 1 test in 0.070s
OK
$ git hash-object data/feed.jsonl     # after
8741905a3cbe72642fb91e4e4db1908c8057a1f0
$ git diff --stat data/feed.jsonl     # empty (production audit trail untouched)
(no output)
```

## Note for Plan 04 (Projection Mode)

The projection mode (`--mode project-to-icloud`) is intentionally NOT implemented in this plan. Plan 04 will extend `scripts/lib/vault_writer.py` (same single-module structure, do not split) by adding:

1. **A new `run_projection(vault_build_root, icloud_root, dry_run, feed_path)` function** — reads `vault-build/Clients/*.md` and applies their managed-section content to the iCloud canonical vault via `replace_managed_section` (preserving Glen's user-owned Overview + Decisions sections).
2. **A new `--mode project-to-icloud` choice in main()'s argparse**, plus a `--icloud-root` arg.
3. **Reuse the SAME `--feed-path` default-resolution pattern** that this plan established. Specifically: do NOT recompute `feed_path` inside `run_projection` — let the value flow in from `main()` exactly the way `run_backfill` and `run_incremental` already accept it. This is the Issue 1 + Issue 6 invariant; tests must be able to thread a temp `--feed-path` so production `data/feed.jsonl` is never polluted by projection-mode failure-path tests either.
4. **Use `replace_managed_section` (NOT `_atomic_write`)** — projection mode mutates an existing user-owned file; the marker-bounded splice + D-08a ABORT semantics are exactly what protects Glen's Overview and Decisions content.

The MarkerError → critical-feed-entry path is already wired (`handle_marker_error_for_feed` + `append_feed_entry`); Plan 04's projection failure handler should call them directly with the threaded `feed_path`.

## Self-Check: PASSED

Files created (verified to exist):

- `scripts/lib/vault_writer.py` — FOUND (842 lines)
- `scripts/tests/test_vault_writer.py` — FOUND (modified — skip decorator removed)
- `vault-build/Clients/property-council-australia.md` — FOUND
- `vault-build/Clients/association-for-tertiary-education-management.md` — FOUND
- `vault-build/Clients/occupational-therapy-australia.md` — FOUND
- `vault-build/Clients/_Unknown.md` — FOUND

Commits verified to exist in git log:

- `7374169` (Task 1: library functions) — FOUND
- `b19f083` (Task 2: backfill + --feed-path + TestMain activation) — FOUND

Final test run: `Ran 20 tests in 0.098s — OK`

---
*Phase: 10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli*
*Completed: 2026-05-01*
