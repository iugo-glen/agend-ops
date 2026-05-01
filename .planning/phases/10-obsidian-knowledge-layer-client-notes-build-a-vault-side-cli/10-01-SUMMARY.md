---
phase: 10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli
plan: 01
subsystem: infra
tags: [python, unittest, gitignore, gitkeep, ruamel-yaml, tdd-red, scaffold, obsidian]

# Dependency graph
requires:
  - phase: 09 (and earlier)
    provides: scripts/ directory exists; data/ NDJSON conventions established (data/triage/.gitkeep convention mirrored here)
provides:
  - vault-build/Clients/ committed via .gitkeep so D-02 transport rail directory exists in fresh clones
  - .gitignore extended with .obsidian/ (D-17a) — workspace state stays out, vault-build/ rides the rail
  - Python package layout (scripts/lib/, scripts/tests/) ready for Plan 02's import path scripts.lib.vault_writer
  - scripts/requirements.txt pinning ruamel.yaml>=0.18,<0.19 for round-trip YAML preservation
  - 6 TestCase RED scaffold (19 active + 1 SKIPPED placeholder) in scripts/tests/test_vault_writer.py — Plan 02's GREEN target
affects: [10-02-PLAN, 10-03-PLAN, 10-04-PLAN, 10-05-PLAN]

# Tech tracking
tech-stack:
  added: [ruamel.yaml (declared, not yet installed in any runtime), Python stdlib unittest as test runner]
  patterns:
    - "Python package layout: scripts/lib/ for production, scripts/tests/ for tests, both with __init__.py for unittest discovery"
    - "Empty-directory marker via .gitkeep mirrors data/triage/.gitkeep, data/config/.gitkeep convention"
    - ".gitignore section style: blank-line separator, # Section heading, optional descriptor, then patterns"
    - "Negative-space transport rail: .obsidian/ excluded but vault-build/ NOT excluded — committing the build output is intentional (D-02)"
    - "TDD RED-across-plans: Plan 01 ships failing tests, Plan 02 ships implementation that turns them green"

key-files:
  created:
    - vault-build/Clients/.gitkeep (zero bytes)
    - scripts/lib/__init__.py (zero bytes)
    - scripts/tests/__init__.py (zero bytes)
    - scripts/requirements.txt (4 lines: 3 comments + ruamel.yaml>=0.18,<0.19)
    - scripts/tests/test_vault_writer.py (279 lines, 6 TestCase classes, 19 active tests + 1 skipped)
  modified:
    - .gitignore (appended 4 lines: blank line + # comment header + descriptor + .obsidian/)

key-decisions:
  - "stdlib unittest, NOT pytest — keeps Phase 10 dependency surface minimal (no test framework install)"
  - "Pin ruamel.yaml>=0.18,<0.19 (range, not bare) — defense against malicious 1.0.0 PyPI uploads (T-10-02 mitigation)"
  - "TestMain.test_main_failure_path_writes_critical_feed_to_temp ships SKIPPED — placeholder activates in Plan 02 Task 2 once main() supports --feed-path; documents the audit-trail isolation contract without forcing this plan to also wire argparse"

patterns-established:
  - "Plan-pair RED/GREEN: Plan 01 commits failing scaffold + types in test names; Plan 02 implements production code against locked symbol surface (slugify, slug_with_domain, safe_slugify, replace_managed_section, MarkerError, handle_marker_error_for_feed, render_log_line, run_backfill)"
  - "Skipped-placeholder pattern: tests that need infrastructure not yet built ship with @unittest.skip(\"Activated in Plan XX Task YY once …\") — documents the contract today, activates atomically when prerequisites land"

requirements-completed: [INTL-01]

# Metrics
duration: 3min
completed: 2026-05-01
---

# Phase 10 Plan 01: Filesystem & Test Scaffold Summary

**Bootstrapped Phase 10's filesystem invariants — committed empty vault-build/Clients/, excluded .obsidian/ from git, and shipped a 6-class stdlib-unittest RED scaffold (19 active + 1 SKIPPED) that locks the 8 symbols Plan 02's vault_writer.py must export.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-01T08:41:37Z
- **Completed:** 2026-05-01T08:44:41Z
- **Tasks:** 2 (both auto, both passed verification on first run)
- **Files created:** 5
- **Files modified:** 1 (.gitignore)

## Accomplishments

- vault-build/Clients/.gitkeep committed (zero bytes, mirrors data/triage/.gitkeep) — D-02 transport rail directory now exists in fresh clones without requiring sync to run first.
- .gitignore section appended for .obsidian/ per D-17a (T-10-01 information-disclosure mitigation: Obsidian plugin/workspace state with potential plugin secrets, recent file paths, and cached queries cannot land in commits). vault-build/ deliberately NOT excluded so the transport rail commits.
- Python package layout (scripts/lib/__init__.py + scripts/tests/__init__.py) ready for `from scripts.lib.vault_writer import …` resolution under `python3 -m unittest discover scripts/tests`.
- scripts/requirements.txt pins ruamel.yaml in range form (>=0.18,<0.19) — T-10-02 tampering mitigation against malicious 1.0.0 PyPI uploads while still allowing 0.18.x patches.
- 6-class RED test scaffold with 20 total test methods (19 active failing on ModuleNotFoundError, 1 SKIPPED placeholder) — locks the API surface for Plan 02 (slugify, slug_with_domain, safe_slugify, replace_managed_section, MarkerError, handle_marker_error_for_feed, render_log_line, run_backfill).

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold vault-build/Clients/ + .gitignore + Python package layout** — `56fd10c` (chore)
2. **Task 2: Write failing test scaffold for vault_writer.py (RED stage)** — `47b8f7f` (test)

_Note: this plan is the RED half of a cross-plan TDD pair. Plan 02 ships the GREEN feat() commit that turns these 19 active tests green and removes the @unittest.skip from TestMain to bring the 20th test live._

## Files Created/Modified

- `vault-build/Clients/.gitkeep` — zero-byte directory marker so the D-02 transport rail directory is present in fresh clones before any sync runs.
- `scripts/lib/__init__.py` — Python package marker; required for `from scripts.lib.vault_writer import …` to resolve under unittest discovery.
- `scripts/tests/__init__.py` — Python package marker; required for `python3 -m unittest discover scripts/tests` to pick up tests.
- `scripts/requirements.txt` — 4-line manifest pinning `ruamel.yaml>=0.18,<0.19` (with install-target comments for Coolify and Mac Studio).
- `scripts/tests/test_vault_writer.py` — 279-line stdlib-unittest scaffold defining TestSlugify, TestReplaceManagedSection, TestMarkerError, TestRenderLogLine, TestBackfillIdempotent, TestMain (last one carries the SKIPPED placeholder).
- `.gitignore` — appended a 4-line section: blank separator + `# Obsidian vault config (lives in iCloud canonical vault, not in repo)` header + D-17a descriptor + `.obsidian/` pattern.

## Decisions Made

- **stdlib unittest over pytest** — followed plan + 10-PATTERNS.md guidance; keeps Phase 10 zero-install for tests, only ruamel.yaml is a runtime dep.
- **Pin range, not bare version, for ruamel.yaml** — `>=0.18,<0.19` rather than `ruamel.yaml` so a hostile 1.0.0 release cannot be silently installed (T-10-02 from plan threat model).
- **Activated TestMain placeholder via @unittest.skip with explicit Plan 02 Task 2 hand-off note** — instead of leaving the test out entirely, the skipped method documents the audit-trail isolation contract (Issue 1: failure-path critical feed entry MUST go to temp --feed-path, never production data/feed.jsonl) so Plan 02's planner cannot miss the requirement.

## Deviations from Plan

None — plan executed exactly as written. Both tasks' acceptance criteria passed on first verification run with no auto-fixes required.

## Issues Encountered

None. Two minor environmental notes (not issues with the plan or code):

- The `rtk grep` proxy in this environment doesn't pass through `-F`, `-B`, or `-c` reliably for some patterns; verified all such acceptance criteria with a one-liner Python script instead. Underlying file content meets every criterion.
- `git diff --diff-filter=D --name-only HEAD~1 HEAD` confirms zero unintended deletions across both commits.

## Threat Model Compliance

The plan's three documented threats are addressed:

| Threat ID | Disposition | Status in this plan |
|-----------|-------------|---------------------|
| T-10-01 (Information Disclosure via .obsidian/) | mitigate | DONE — `.obsidian/` line in .gitignore verified outside comments |
| T-10-02 (Tampering via unbounded ruamel.yaml dep) | mitigate | DONE — pin is `ruamel.yaml>=0.18,<0.19`, range form |
| T-10-03 (Test-scaffold drift) | accept | Acknowledged — Plan 02 may add tests; this plan locks 6 contracts |

No new threat surface introduced beyond what the plan's `<threat_model>` already documents — no network endpoints, no auth paths, no schema changes at trust boundaries. No `Threat Flags` section needed.

## TDD Gate Compliance

This plan ships only the RED gate (`test(...)` commit `47b8f7f`). The GREEN gate (`feat(...)`) is owned by Plan 02 by design — the plan frontmatter declares this is `type: execute` (not `type: tdd`), and the cross-plan RED→GREEN handoff is the documented Phase 10 wave structure. No GREEN commit is expected in this plan.

## Known Stubs

None. The TestMain placeholder is documented (skipped with explicit Plan 02 Task 2 activation note) — it's a declared interface contract for the next plan, not stubbed UI/data.

## Verification Results

```
$ ls -la vault-build/Clients/.gitkeep scripts/lib/__init__.py scripts/tests/__init__.py scripts/requirements.txt scripts/tests/test_vault_writer.py
-rw-r--r--  1 glenr  staff      0  vault-build/Clients/.gitkeep
-rw-r--r--  1 glenr  staff      0  scripts/lib/__init__.py
-rw-r--r--  1 glenr  staff      0  scripts/tests/__init__.py
-rw-r--r--  1 glenr  staff    208  scripts/requirements.txt
-rw-r--r--  1 glenr  staff  12212  scripts/tests/test_vault_writer.py

$ python3 -m unittest discover scripts/tests 2>&1 | tail -3
Ran 20 tests in 0.003s
FAILED (errors=19, skipped=1)

$ python3 -c "import scripts.lib; import scripts.tests; print('packages OK')"
packages OK
```

RED state confirmed: 19 ModuleNotFoundError errors citing `scripts.lib.vault_writer`, exactly the GREEN target Plan 02 will satisfy. The 1 skip is the TestMain placeholder.

## Next Plan Readiness

Plan 02 (`10-02-PLAN.md`) is unblocked:

- Test entry point established: `python3 -m unittest discover scripts/tests`
- Import path for production code locked: `scripts.lib.vault_writer`
- 8 symbols Plan 02 must export are now contractually documented in failing tests: `slugify`, `slug_with_domain`, `safe_slugify`, `replace_managed_section`, `MarkerError`, `handle_marker_error_for_feed`, `render_log_line`, `run_backfill`
- `--feed-path` argparse + feed_path threading requirement documented in TestMain skip docstring (Plan 02 Task 2 must add it AND remove the `@unittest.skip` decorator to bring the 20th test live)
- ruamel.yaml dependency declared (will be installed by Plan 02 or its install plan)
- vault-build/Clients/ directory exists and is committed — ready to receive generated `.md` notes

No blockers. No concerns.

## Self-Check: PASSED

All claimed artefacts verified to exist:

- vault-build/Clients/.gitkeep — FOUND
- scripts/lib/__init__.py — FOUND
- scripts/tests/__init__.py — FOUND
- scripts/requirements.txt — FOUND
- scripts/tests/test_vault_writer.py — FOUND
- .planning/phases/10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli/10-01-SUMMARY.md — FOUND
- .gitignore contains `.obsidian/` — FOUND

All claimed commits verified to exist in git log:

- 56fd10c (Task 1: scaffold) — FOUND
- 47b8f7f (Task 2: RED test scaffold) — FOUND

---
*Phase: 10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli*
*Completed: 2026-05-01*
