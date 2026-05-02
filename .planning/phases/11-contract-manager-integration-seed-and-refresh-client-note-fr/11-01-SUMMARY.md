---
phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr
plan: 01
subsystem: infra
tags: [contract-manager, vault-writer, schema, bootstrap, gitignore, env-validation, ruamel-yaml]

# Dependency graph
requires:
  - phase: 10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli
    provides: render_frontmatter (Phase 10 D-09 v1 4-key signature), feed-entry.json schema, sync-obsidian.sh wrapper, .gitignore conventions
provides:
  - schemas/feed-entry.json level enum extended with "warning" (4 values total)
  - data/.cm-cache.json gitignored (ready for Plan 03/04 cache writes)
  - scripts/sync-obsidian.sh fails fast on missing CONTRACT_MANAGER_API_KEY (Coolify-only fail-fast gate)
  - render_frontmatter accepts optional cm_extra and cm_stale_since kwargs (additive, backwards compatible)
affects: [11-02, 11-03, 11-04, future cm-cache writers, future warning-level emitters]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "${VAR:?msg} bash idiom for env var validation with no value leakage (T-11-01-01)"
    - "Additive Phase-N kwargs with default None — preserves Phase 10 byte-identical output for D-14/D-16 idempotency"
    - "Per-host runtime state in data/ goes to .gitignore (mirrors scripts/.vault-sync.lock pattern)"

key-files:
  created: []
  modified:
    - schemas/feed-entry.json
    - .gitignore
    - scripts/sync-obsidian.sh
    - scripts/lib/vault_writer.py
    - scripts/tests/test_vault_writer.py

key-decisions:
  - "Enum order ['critical', 'warning', 'info', 'debug'] (severity-descending) per 11-PATTERNS.md canonical sequence"
  - "Env-validation block placed AFTER flock guard but BEFORE REPO_ROOT — Mac never runs the script (Pitfall 1) so this only fires on Coolify; placed before no-op-delta gate so we fail fast without spending cycles checking deltas"
  - "Frontmatter key order chosen as Phase-10 4 keys + (contract_start, contract_end, primary_contact, deployed_modules, sites) + cm_data_stale_since — chronological grouping per RESEARCH.md lines 396-399"
  - "cm_stale_since check uses truthy `if cm_stale_since:` (not `is not None`) so empty strings also omit the key — defensive against future callers"

patterns-established:
  - "Phase 11 additive kwargs pattern: optional kwarg=None + body conditional `if kwarg is not None:` — extend without breaking 2-arg callers; mirror for future renderers (render_sites, render_usage, render_cm_todos)"
  - "Wave 0 bootstrap discipline: schema/config/signature edits land BEFORE any code path consumes them, so later waves only encounter green ground"

requirements-completed: [INTL-01, CM-WAVE0]

# Metrics
duration: 3min
completed: 2026-05-02
---

# Phase 11 Plan 01: Wave 0 Bootstrap Summary

**Wave 0 preconditions landed: feed schema accepts "warning" level, CM cache gitignored, sync wrapper fails loudly without API key, and render_frontmatter grew two optional kwargs (cm_extra, cm_stale_since) with byte-identical Phase 10 output for legacy callers.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-02T13:35:19Z
- **Completed:** 2026-05-02T13:37:52Z
- **Tasks:** 3 (1 TDD)
- **Files modified:** 5 (4 production + 1 test)

## Accomplishments

- `schemas/feed-entry.json` `level` enum now includes `"warning"` alongside `critical`/`info`/`debug` — D-A3-REVISED satisfied; future code can emit warning-level entries without schema rejection.
- `.gitignore` now excludes `data/.cm-cache.json` — D-F1 satisfied; Plan 02/03/04 cache writers will not accidentally commit per-host runtime state.
- `scripts/sync-obsidian.sh` aborts with `bash: CONTRACT_MANAGER_API_KEY: CONTRACT_MANAGER_API_KEY env var required (set on Coolify; not on Mac)` if the key is unset OR empty — D-A2 satisfied; Coolify rotation is now a one-liner (edit env, restart) per CONTEXT line 115.
- `render_frontmatter` accepts `cm_extra: dict | None = None` and `cm_stale_since: str | None = None` — Plan 03 can feed CM data without touching the function signature again. Existing 2-arg callers produce byte-identical Phase 10 output (D-14/D-16 idempotency preserved).
- Test suite grew from 25 → 31 tests; full suite green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend feed-entry.json enum + .gitignore** — `0ae7405` (feat)
2. **Task 2: Add CONTRACT_MANAGER_API_KEY env validation** — `40319dd` (feat)
3. **Task 3 (RED): Add failing render_frontmatter tests** — `7518c7b` (test) — TDD RED gate
4. **Task 3 (GREEN): Extend render_frontmatter signature** — `e23b424` (feat) — TDD GREEN gate

REFACTOR phase: not needed (additive 3-line param block + 7-line conditional is clean as-is).

## Files Created/Modified

- `schemas/feed-entry.json` — `level` enum extended from 3 to 4 values; no other property changed.
- `.gitignore` — Added one comment + one entry (`data/.cm-cache.json`) at the end of the file, mirroring the existing `scripts/.vault-sync.lock` runtime-state pattern.
- `scripts/sync-obsidian.sh` — Inserted a 6-line block (1 separator comment + 4-line explanatory comment + 1 `${VAR:?msg}` validation line) AFTER the flock portability guard and BEFORE `REPO_ROOT=`.
- `scripts/lib/vault_writer.py` — Replaced the 11-line `render_frontmatter` definition with a 30-line version that accepts two optional kwargs (`cm_extra`, `cm_stale_since`); imports unchanged (StringIO and `_yaml_instance` already in scope).
- `scripts/tests/test_vault_writer.py` — Appended `TestRenderFrontmatterPhase11` (6 tests) at the bottom of the file, before `if __name__ == "__main__":`.

## Decisions Made

- **Enum order chosen `["critical", "warning", "info", "debug"]`** — matches 11-PATTERNS.md line 552 canonical sequence (severity-descending). JSON Schema does not require ordered enums, but the canonical order keeps cross-file diffs reviewable.
- **Truthy check `if cm_stale_since:` instead of `is not None`** — defensive against a future caller that passes an empty string by mistake; matches the spirit of "stamp a TIMESTAMP, never a placeholder" from D-A3-REVISED.
- **Empty-array sentinel test (`assertNotIn("null", out.lower())`)** uses `lower()` to also catch ruamel.yaml's `Null` capitalization variant — covers the full output space without enumerating ruamel quirks.
- **`render_frontmatter` body order** — contracts (start, end) before contact (primary_contact) before infra (deployed_modules, sites) — chronological/causal grouping that matches how Glen reads a client note: when does the contract run, who's the contact, what's deployed.

## Deviations from Plan

None — plan executed exactly as written. Each task's `<action>` block was followed verbatim. Auto-fix rules (Rules 1-3) had no triggers: no bugs surfaced, no critical functionality was missing, no blocking issues encountered. Rule 4 (architectural) had no triggers either — every change was within the four files declared in `files_modified`.

## Issues Encountered

- **Mac flock unavailable** — On the Mac executing this plan, `command -v flock` returns nothing, so `bash scripts/sync-obsidian.sh --dry-run` exits at the portability guard before reaching the new env validation. This is expected per Pitfall 1 (Mac never runs this wrapper). The `${VAR:?msg}` idiom was verified in isolation via `bash -c` invocations: unset → fails, empty → fails, non-empty → passes. On Coolify (Linux container with util-linux flock) the guard will pass and the env check will fire as designed.
- **Pre-existing TDD `red-gate` test passes inadvertently** — `test_render_frontmatter_no_cm_extra_unchanged` is the backwards-compat sanity check; it passes in the RED phase because the Phase 10 4-key prefix is already byte-identical. This is documented in the test docstring and is the intended outcome (additive change must not break legacy callers). The other 5 RED tests failed with `TypeError: render_frontmatter() got an unexpected keyword argument 'cm_extra'`, satisfying the RED gate.

## TDD Gate Compliance

- **RED:** `7518c7b` (test commit) — 5 of 6 new tests fail with `TypeError` for unknown kwargs; 1 backwards-compat test passes by design.
- **GREEN:** `e23b424` (feat commit) — all 6 new tests pass; full suite (31 tests) green.
- **REFACTOR:** Skipped (no refactor needed; code is minimal and readable).

## User Setup Required

None — no external service configuration required for Wave 0. (Coolify will need `CONTRACT_MANAGER_API_KEY` set in its env injection panel before Plan 02 runs, but that is documented in 11-CONTEXT.md and does not affect Plan 01.)

## Next Phase Readiness

- Plan 02 (CM client wrapper) can now emit `level: "warning"` entries to `data/feed.jsonl` without schema validators rejecting them.
- Plan 03 (frontmatter merge) can call `render_frontmatter(client, ts, cm_extra={...}, cm_stale_since="...")` without touching the signature.
- Plan 04 (cache fallback) can write to `data/.cm-cache.json` without polluting git history.
- Coolify deployment must inject `CONTRACT_MANAGER_API_KEY` before any Wave 1 sync run; otherwise `scripts/sync-obsidian.sh` will exit non-zero with a clear stderr message.

## Self-Check: PASSED

Files claimed to be modified:
- `schemas/feed-entry.json` — FOUND (commit 0ae7405)
- `.gitignore` — FOUND (commit 0ae7405)
- `scripts/sync-obsidian.sh` — FOUND (commit 40319dd)
- `scripts/lib/vault_writer.py` — FOUND (commit e23b424)
- `scripts/tests/test_vault_writer.py` — FOUND (commit 7518c7b)

Commits claimed to exist:
- `0ae7405` (feat: schema + gitignore) — FOUND
- `40319dd` (feat: env validation) — FOUND
- `7518c7b` (test: RED) — FOUND
- `e23b424` (feat: GREEN) — FOUND

Verification commands:
- `python3 -m unittest discover scripts/tests` → 31 tests pass
- `python3 -c 'import json; assert "warning" in json.load(open("schemas/feed-entry.json"))["properties"]["level"]["enum"]'` → exit 0
- `git check-ignore data/.cm-cache.json` (after `touch`) → prints `data/.cm-cache.json`
- `bash -n scripts/sync-obsidian.sh` → exit 0
- `grep -c "cm_extra" scripts/lib/vault_writer.py` → 8 (≥ 6)
- `git status --porcelain` → empty (no uncommitted leftovers)

---
*Phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr*
*Completed: 2026-05-02*
