---
phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings
plan: 01
subsystem: infra
tags: [phase-12, workspace, calendar, drive, bootstrap, emoji, cache, env-validation, gitignore]

# Dependency graph
requires:
  - phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr
    provides: scripts/sync-obsidian.sh CONTRACT_MANAGER_API_KEY validation pattern, .gitignore Phase-11 cache exclusion pattern, EMOJI_BY_KIND with contract→📄, load_clients with cm_client_id plumbing
provides:
  - .gitignore excludes data/.cal-cache.json AND data/.drive-cache.json (ready for Wave 1 workspace_client.write_cache + Wave 3 _fetch_external_data_for_run cache writes)
  - scripts/sync-obsidian.sh fails fast on missing GOOGLE_MCP_CREDENTIALS_DIR (sibling to CONTRACT_MANAGER_API_KEY check; Coolify-only fail-fast gate)
  - scripts/lib/vault_writer.py EMOJI_BY_KIND now has six entries (meeting→📅, doc→📝 added; 📄 still contract-only per D-C3)
  - scripts/lib/vault_writer.py render_log_line accepts kind="meeting" and kind="doc" without raising ValueError (downstream Wave 2/3 renderers depend on this)
  - scripts/lib/vault_writer.py load_clients carries aliases[] through into the per-domain info dict (defaults to [] for missing/null fields; per-call list copy)
affects: [12-02, 12-03, 12-04, future workspace_client cache writers, future Calendar/Drive renderers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "${VAR:?msg} bash idiom — reused unchanged from Phase 11 for sibling Workspace OAuth credentials path validation (T-12-01-01 mitigation)"
    - "Additive Phase-N kwargs + dict-extension pattern — EMOJI_BY_KIND grew from 4 to 6 entries; load_clients dict literal grew by one key, mirroring Phase 11's cm_client_id plumbing"
    - "Defensive list normalization: list(rec.get(\"aliases\") or []) — converts None and missing-key cases to [] AND copies the list per call so downstream mutation cannot leak back (T-12-01-05 mitigation)"

key-files:
  created: []
  modified:
    - .gitignore
    - scripts/sync-obsidian.sh
    - scripts/lib/vault_writer.py
    - scripts/tests/test_vault_writer.py

key-decisions:
  - "Cache exclusion block placed at the END of .gitignore (after Phase 11's data/.cm-cache.json) — keeps phase-of-introduction comments chronologically grouped; mirrors Phase 11 SUMMARY's placement decision"
  - "GOOGLE_MCP_CREDENTIALS_DIR validation placed IMMEDIATELY AFTER CONTRACT_MANAGER_API_KEY check and BEFORE REPO_ROOT — both env validations fire before any cycle is spent on the no-op-delta gate or flock acquisition; mirrors Phase 11 placement"
  - "EMOJI_BY_KIND rewritten as multi-line dict with phase-of-introduction comments — readability + diff hygiene (single key change is now one line; previous one-liner would have shown the whole dict); 📄 explicitly marked RESERVED per D-C3"
  - "load_clients aliases plumbing follows Phase 11 cm_client_id pattern verbatim (additive key in both raw_entries and per-domain dict; defensive default in get) — minimal diff surface, easy to verify"
  - "Test classes appended AFTER TestJitMapping (the existing last class) and BEFORE if __name__ == \"__main__\" — same placement Phase 11 used for TestRenderFrontmatterPhase11"

patterns-established:
  - "Phase-12 Wave 0 mirror discipline: when Phase 11 already established a precondition pattern (gitignore line, env validation, signature/dict extension), Phase 12 reuses the exact placement + idiom; no re-debate"
  - "Defensive list-copy normalization pattern for user-controlled config arrays — `list(rec.get(\"key\") or [])` is the canonical seam at clients.jsonl ingestion; T-12-01-05 (regex injection) is downstream-mitigated via re.escape() in Wave 2's matcher"
  - "TDD RED gate where a subset of tests pre-pass by design (additive change preserves prior behaviour) is acceptable so long as the discriminating tests fail; documented in the test commit message"

requirements-completed: [INTL-01-CAL, INTL-01-DRIVE, INTL-01-WORKSPACE-CACHE, INTL-01-PROJECTION-ISOLATION]

# Metrics
duration: 3min
completed: 2026-05-03
---

# Phase 12 Plan 01: Wave 0 Bootstrap Summary

**Wave 0 preconditions landed: cal/drive cache files gitignored, sync wrapper fails loudly without Workspace OAuth dir, EMOJI_BY_KIND extended with meeting/doc kinds (📄 stays contract-only), and load_clients carries aliases through into the per-domain dict for Wave 2's filename matcher.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-03T01:42:04Z
- **Completed:** 2026-05-03T01:45:05Z
- **Tasks:** 2 (1 auto, 1 TDD)
- **Files modified:** 4 (3 production + 1 test)
- **Tests:** 74 → 85 (+11 new Phase 12 Wave 0 tests; full suite green)

## Accomplishments

- `.gitignore` now excludes `data/.cal-cache.json` AND `data/.drive-cache.json` — Wave 1 workspace_client and Wave 3 `_fetch_external_data_for_run` cache writers will not accidentally commit per-host runtime state. Phase 11's `data/.cm-cache.json` line preserved.
- `scripts/sync-obsidian.sh` now aborts with `bash: GOOGLE_MCP_CREDENTIALS_DIR: GOOGLE_MCP_CREDENTIALS_DIR env var required (path to OAuth credentials dir; set on Coolify; not on Mac)` if the dir is unset OR empty — D-X1 architectural decision satisfied; OAuth blob discovery now has a single fail-fast gate. Phase 11's CONTRACT_MANAGER_API_KEY check still intact.
- `EMOJI_BY_KIND` extended from 4 to 6 entries: `meeting`→📅 and `doc`→📝 added; Phase 2/3/7/11 entries preserved with phase-of-introduction comments. D-C3 invariant verified: 📄 maps to exactly one kind (`contract`).
- `render_log_line` now accepts `kind="meeting"` and `kind="doc"` without raising `ValueError` — Wave 2/3 renderers (📅 calendar entries + 📝 drive entries) can use the existing seam without modification. Docstring updated to list all six kinds.
- `load_clients` now carries `aliases[]` through both assembly points (raw_entries dict + per-domain info dict), with `list(rec.get("aliases") or [])` for defensive None/missing-key normalization and per-call list copy. Wave 2's D-A4-REVISED filename matcher can now iterate `info["aliases"]` without re-parsing clients.jsonl.
- All 34 real clients in `data/config/clients.jsonl` now expose their `aliases` field through `load_clients` (verified via `python3 -c '... assert all("aliases" in v for v in c.values())'`).

## Task Commits

Each task was committed atomically with `--no-verify` (worktree parallel execution):

1. **Task 1: gitignore cache exclusion + sync-obsidian.sh env validation** — `73e1d77` (feat)
2. **Task 2 (RED): failing tests for emoji extension + aliases plumbing** — `ab07496` (test) — TDD RED gate
3. **Task 2 (GREEN): EMOJI_BY_KIND extension + load_clients aliases plumbing** — `6718bfb` (feat) — TDD GREEN gate

REFACTOR phase: not needed (additive 8-line dict-extend + 2-line dict-key extend + docstring is already clean).

## Files Created/Modified

- `.gitignore` (commit 73e1d77) — Appended one comment header + two exclusion lines (`data/.cal-cache.json`, `data/.drive-cache.json`) at the end of the file, mirroring the existing Phase 11 `data/.cm-cache.json` block.
- `scripts/sync-obsidian.sh` (commit 73e1d77) — Inserted an 8-line block (1 separator comment + 6-line explanatory comment + 1 `${VAR:?msg}` validation line) IMMEDIATELY AFTER the existing `CONTRACT_MANAGER_API_KEY:?` check and BEFORE `REPO_ROOT=`. No existing line modified.
- `scripts/lib/vault_writer.py` (commit 6718bfb) — Replaced the 1-line `EMOJI_BY_KIND` dict with an 8-line multi-line version with phase-of-introduction comments; updated `render_log_line` docstring to list all six kinds; added one key (`aliases`) to both `load_clients` assembly points (raw_entries dict literal at line 379-385 + per-domain info dict at line 387-395); extended `load_clients` docstring with the new field.
- `scripts/tests/test_vault_writer.py` (commit ab07496) — Appended `TestEmojiByKindPhase12` (6 tests) and `TestLoadClientsAliasesPhase12` (5 tests) at the bottom of the file, before `if __name__ == "__main__":`. Imports unchanged (json, tempfile, unittest, Path already in scope).

## Decisions Made

- **Multi-line `EMOJI_BY_KIND` dict with phase-of-introduction comments** — The Phase 10 dict was a one-liner. Rewriting it as 6 lines with `# Phase N` annotations provides three benefits: (1) future single-key additions are one-line diffs, (2) the `# RESERVED` comment on `contract → 📄` is co-located with the value (preventing accidental remapping), (3) D-C3's "📄 stays contract-only" invariant is documented at the source (not just the test).
- **`list(rec.get("aliases") or [])` defensive idiom** — Three behaviours in one expression: (1) missing key → `[]` (Python `dict.get` returns None; `None or []` evaluates to `[]`), (2) explicit JSON `null` → `[]` (same logic), (3) per-call list copy (so downstream mutation of `clients[domain]["aliases"]` cannot leak back into `raw_entries` state). Verified by `test_load_clients_aliases_is_a_copy_not_a_reference`.
- **Test class placement after `TestJitMapping` (existing last class)** — Mirrors Phase 11's placement of `TestRenderFrontmatterPhase11` after the previous last class. Keeps the file chronologically grouped by phase, easy to scan.
- **Skipped REFACTOR phase** — Two-line dict-extend in `load_clients` + 8-line dict-extend of `EMOJI_BY_KIND` + docstring updates are already minimal. No simplification opportunity exists without sacrificing readability (e.g., conditional aliases population would be more lines, not fewer).

## Deviations from Plan

None — plan executed exactly as written. Each task's `<action>` block was followed verbatim. Auto-fix rules (Rules 1-3) had no triggers: no bugs surfaced, no critical functionality was missing, no blocking issues encountered. Rule 4 (architectural) had no triggers either — every change was within the four files declared in `files_modified`.

## Issues Encountered

- **Mac flock unavailable** — On the Mac executing this plan, `command -v flock` returns nothing, so `bash scripts/sync-obsidian.sh --dry-run` exits at the portability guard (line 22-27) before reaching the new env validation. Same constraint as Phase 11. Mitigation: verified the `${VAR:?msg}` idiom in isolation via Bash heredocs (unset → exit 1 with stderr `bash: line 1: GOOGLE_MCP_CREDENTIALS_DIR: GOOGLE_MCP_CREDENTIALS_DIR env var required (...)`; empty → exit 1; set → exit 0). On Coolify (Linux container with util-linux flock), the guard will pass and the env check will fire as designed.
- **Pre-passing RED tests by design** — 3 of the 11 new tests passed in the RED phase: `test_emoji_by_kind_preserves_phase_10_11_kinds` (Phase 10/11 entries already present pre-edit), `test_emoji_by_kind_contract_emoji_stays_contract_only` (📄 already maps only to `contract` pre-edit because `meeting`/`doc` keys not yet registered), and `test_render_log_line_rejects_unknown_kind` (validation gate already intact). The 8 discriminating tests failed as expected. This is the documented behaviour for additive-change TDD where the RED gate proves "the new behaviour does not exist yet" via discriminating tests, while the legacy-preservation tests serve as belt-and-braces sanity checks. Mirrors Phase 11's `test_render_frontmatter_no_cm_extra_unchanged` precedent.

## TDD Gate Compliance

- **RED:** `ab07496` (test commit) — 8 of 11 new tests fail with `KeyError: 'aliases'` (5 alias tests) and `AssertionError: None != '📅'` / `None != '📝'` (3 emoji tests). The other 3 tests pre-pass by design (legacy-preservation belts-and-braces).
- **GREEN:** `6718bfb` (feat commit) — All 11 new tests pass; full suite (85 tests) green.
- **REFACTOR:** Skipped (no refactor needed; production code is minimal additive plumbing).

## User Setup Required

None — no external service configuration required for Wave 0. Coolify deployment will need `GOOGLE_MCP_CREDENTIALS_DIR` set in its env injection panel before Wave 1 (workspace_client.py) runs, but that is documented in 12-CONTEXT.md (D-X1) and does not affect Wave 0.

## Next Phase Readiness

- **Wave 1 (workspace_client.py)** can now write to `data/.cal-cache.json` AND `data/.drive-cache.json` without polluting git history; can rely on `GOOGLE_MCP_CREDENTIALS_DIR` being non-empty by the time `_workspace_get` runs (sync-obsidian.sh fails earlier).
- **Wave 2 (vault_writer rendering surface)** can call `render_log_line(kind="meeting", ...)` and `render_log_line(kind="doc", ...)` without ValueError; D-A4-REVISED filename matcher can iterate `client_info["aliases"]` directly (already populated by `load_clients`).
- **Wave 3 (`_fetch_external_data_for_run` rename + Calendar/Drive integration)** inherits the cache fallback location + the Pitfall 1 invariant (Mac never imports workspace_client; verified by `grep -E "^from .workspace_client" scripts/lib/vault_writer.py` returning nothing).
- **Coolify deployment must inject `GOOGLE_MCP_CREDENTIALS_DIR`** before any Wave 1+ sync run; otherwise `scripts/sync-obsidian.sh` will exit non-zero with a clear stderr message naming the env var (no value leak).

## Self-Check: PASSED

Files claimed to be modified:
- `.gitignore` — FOUND (commit 73e1d77)
- `scripts/sync-obsidian.sh` — FOUND (commit 73e1d77)
- `scripts/lib/vault_writer.py` — FOUND (commit 6718bfb)
- `scripts/tests/test_vault_writer.py` — FOUND (commit ab07496)

Commits claimed to exist:
- `73e1d77` (feat: gitignore + env validation) — FOUND
- `ab07496` (test: RED) — FOUND
- `6718bfb` (feat: GREEN) — FOUND

Verification commands:
- `python3 -m unittest discover scripts/tests` → 85 tests pass (74 baseline + 11 new)
- `grep -Fxq 'data/.cal-cache.json' .gitignore` → exit 0
- `grep -Fxq 'data/.drive-cache.json' .gitignore` → exit 0
- `grep -Fxq 'data/.cm-cache.json' .gitignore` → exit 0 (Phase 11 line preserved)
- `git check-ignore data/.cal-cache.json` (after `touch`) → prints `data/.cal-cache.json`
- `git check-ignore data/.drive-cache.json` (after `touch`) → prints `data/.drive-cache.json`
- `bash -n scripts/sync-obsidian.sh` → exit 0
- `grep -c 'GOOGLE_MCP_CREDENTIALS_DIR:?' scripts/sync-obsidian.sh` → 1
- `grep -c 'CONTRACT_MANAGER_API_KEY:?' scripts/sync-obsidian.sh` → 1 (Phase 11 validation intact)
- `python3 -c 'from scripts.lib.vault_writer import EMOJI_BY_KIND; assert EMOJI_BY_KIND["meeting"] == "📅" and EMOJI_BY_KIND["doc"] == "📝" and EMOJI_BY_KIND["contract"] == "📄" and len(EMOJI_BY_KIND) == 6'` → exit 0
- `grep -c '"meeting":' scripts/lib/vault_writer.py` → 1
- `grep -c '"doc":' scripts/lib/vault_writer.py` → 1
- `grep -c '"contract":' scripts/lib/vault_writer.py` → 1
- `grep -c "aliases" scripts/lib/vault_writer.py` → 3 (raw_entries assembly + per-domain dict + docstring)
- `grep -E "^from .workspace_client|^import .*workspace_client" scripts/lib/vault_writer.py` → empty (no premature import; Pitfall 1 preserved)
- `python3 -c 'from scripts.lib.vault_writer import load_clients; from pathlib import Path; c=load_clients(Path("data")); assert all("aliases" in v for v in c.values())'` → exit 0 (all 34 real clients carry aliases)
- `git diff --name-only 828cbd9..HEAD` → exactly the four files in `files_modified` (no scope leak)

---
*Phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings*
*Completed: 2026-05-03*
