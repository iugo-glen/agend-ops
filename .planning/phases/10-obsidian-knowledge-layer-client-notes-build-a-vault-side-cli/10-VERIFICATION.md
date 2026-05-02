---
phase: 10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli
verified: 2026-05-01T00:00:00+09:30
status: passed
score: 16/16 must-haves verified
overrides_applied: 0
---

# Phase 10: Obsidian Knowledge Layer — Client Notes — Verification Report

**Phase Goal:** Build a vault-side CLI that turns Agend Ops's NDJSON activity feed into client-keyed Obsidian notes (`vault-build/Clients/<slug>.md`), then projects them into the iCloud canonical Obsidian vault on a Mac Studio so Glen can read/edit them on iPhone. Honors INTL-01 (context accumulation — client history, past decisions stored in structured files).

**Verified:** 2026-05-01
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                                  | Status      | Evidence                                                                                                                                                                              |
| -- | ---------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | vault-build/Clients/*.md generated from NDJSON (4 files exist on disk)                                                 | VERIFIED    | `vault-build/Clients/` contains `_Unknown.md` (13K), `association-for-tertiary-education-management.md`, `occupational-therapy-australia.md`, `property-council-australia.md` (2.4K) plus `.gitkeep` |
| 2  | NDJSON ingestion from data/triage/, data/tasks/, data/invoices/, data/todos/ (62 events routed)                        | VERIFIED    | `_gather_events()` at vault_writer.py:645 streams all four sources; live dry-run reports `events_routed: 62` matching SUMMARY claim                                                   |
| 3  | Marker-aware atomic splice with D-08a ABORT semantics (replace_managed_section + MarkerError)                          | VERIFIED    | `replace_managed_section()` at vault_writer.py:99-149 raises `MarkerError` on missing/duplicate/out-of-order markers; tests `TestMarkerError` (5 cases) all pass                       |
| 4  | Slug + collision suffix per Pattern 5 (slugify, slug_with_domain, safe_slugify)                                        | VERIFIED    | All three exported at vault_writer.py:70-94 with NFKD normalization; tests `TestSlugify` (6 cases incl. NFKD ASCII fold) all pass; runtime spot-check: `slugify('Property Council Australia') == 'property-council-australia'` |
| 5  | ruamel.yaml frontmatter round-trip per D-09 (4 keys: domain, client_name, status, last_synced)                         | VERIFIED    | `render_frontmatter()` at vault_writer.py:553-563 emits exactly the 4 D-09 v1 keys; live note inspection (property-council-australia.md lines 1-5) shows all 4 keys present              |
| 6  | D-10 triage filter (priority urgent/needs-response OR action_items)                                                    | VERIFIED    | `d10_triage_filter()` at vault_writer.py:404-412 implements the rule exactly; observable in association-for-tertiary-education-management.md (only `informational` triage with action_items survives) |
| 7  | D-11 unconditional task/invoice logging                                                                                | VERIFIED    | `_gather_events()` lines 669-677 streams tasks + invoices without filter; observable in `_Unknown.md` Group: AVA showing both completed and pending task records                       |
| 8  | D-12 line shape (### [YYYY-MM-DD HH:MM] {emoji} {summary})                                                             | VERIFIED    | `render_log_line()` at vault_writer.py:200-219 produces exact shape; live note shows `### [2026-03-23 01:11] 📧 Re: Agend x PCA...`; `EMOJI_BY_KIND = {'triage': '📧', 'task': '✅', 'invoice': '💰'}` confirmed at runtime |
| 9  | D-15a stub note for empty clients                                                                                      | VERIFIED    | `_NOTE_TEMPLATE` (lines 243-266) ALWAYS produces stub shape (Overview placeholder + empty `_(none)_` Open Items + Activity Log + Decisions stub); backfill loop at line 722 iterates ALL clients regardless of event count |
| 10 | D-14/D-16 idempotent regenerate-from-full (proven twice in Plan 02 + e2e tested in Wave 5)                            | VERIFIED    | Test `TestBackfillIdempotent.test_two_runs_identical_managed_content` PASSES; commit 453941d shows e2e re-run produced **only `last_synced` deltas** in 4/4 files (4 insertions, 4 deletions, 1 line each) |
| 11 | --feed-path threading per Issue 1 (production data/feed.jsonl never polluted by tests)                                 | VERIFIED    | `--feed-path` argparse arg at vault_writer.py:1131-1140; resolved at CLI boundary line 1145; `TestMain.test_main_failure_path_writes_critical_feed_to_temp` PASSES (subprocess test against `/nonexistent` --data-root, asserts critical entry lands ONLY in temp feed) |
| 12 | Slash commands wired (/sync-obsidian + hook in /triage-inbox, /task, /invoice)                                         | VERIFIED    | `.claude/commands/sync-obsidian.md` exists (3.8K); all 3 hook commands grep `bash scripts/sync-obsidian.sh --incremental \|\| true`; `git add` lines extended to include `vault-build/` in all 3 |
| 13 | Linux flock wrapper (scripts/sync-obsidian.sh) with no-op-delta gate, clock-skew cap, ruamel quote-strip                | VERIFIED    | Wrapper at scripts/sync-obsidian.sh:22-27 contains `command -v flock` portability guard; lines 56-109 implement no-op-delta guard; line 96-99 caps `LAST_SYNCED_EPOCH > CURRENT_EPOCH` (clock-skew defense H2); line 82 strips both `'` and `"` quotes (H3); flock acquired with 30s timeout at line 113 |
| 14 | Mac Studio LaunchAgent (com.agend.vault-sync.plist + fswatch wrapper + idempotent installer)                          | VERIFIED    | `mac/com.agend.vault-sync.plist` (KeepAlive=true, RunAtLoad=true, no WatchPaths); `mac/vault-sync-watcher.sh` (fswatch --latency 2 + xargs); `mac/install-daemon.sh` is idempotent (steps gated on existence checks); Glen's commit d3e24d2 from `glenr@GlensMacStudio.localdomain` proves install ran successfully on real hardware |
| 15 | project-to-icloud mode with brctl placeholder retries, dry-run safety, source/target marker symmetry                  | VERIFIED    | `run_projection()` at vault_writer.py:913+; `_handle_icloud_placeholder()` at line 815 (3 retries × 2s); Issue 5 strict dry-run gating verified by `TestProjection.test_dry_run_does_not_invoke_brctl` (mocks subprocess.run, asserts `brctl` never invoked); Issue 4 source-marker symmetry by `_extract_managed_section` raising MarkerError + `TestProjection.test_corrupt_source_marker_aborts_with_critical_feed` PASSES |
| 16 | End-to-end iPhone verification confirmed by user                                                                       | VERIFIED    | User statement: "so far it's working - I did the initial backfill and e2e testing on the iphone, so I think it's all up to date." Evidence on disk: commits d3e24d2 (installer fix from Mac Studio), d0990d9 (operator README beefed up after real install experience), 453941d (round-trip e2e test backfill showing only `last_synced` deltas) |

**Score:** 16/16 truths verified

### Required Artifacts

| Artifact                                                          | Expected                                                                  | Status   | Details                                                                                              |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------- |
| `vault-build/Clients/.gitkeep`                                    | Empty marker file                                                         | VERIFIED | 0B file present                                                                                      |
| `.gitignore` (D-17a `.obsidian/` exclude)                         | Excludes Obsidian workspace                                               | VERIFIED | Line shows `.obsidian/` after `# D-17a:` comment                                                     |
| `scripts/tests/__init__.py` + `scripts/tests/test_vault_writer.py` | Failing test scaffold → green                                             | VERIFIED | 25 tests pass (`Ran 25 tests in 0.127s OK`)                                                          |
| `scripts/requirements.txt` (`ruamel.yaml>=0.18,<0.19`)            | Pinned dependency                                                         | VERIFIED | Line 4 `ruamel.yaml>=0.18,<0.19`                                                                     |
| `scripts/lib/__init__.py` + `scripts/lib/vault_writer.py`         | Sync engine (~1200 lines, 19 exports)                                     | VERIFIED | 47.1K module exporting MarkerError, slugify, slug_with_domain, safe_slugify, replace_managed_section, render_log_line, run_backfill, run_incremental, run_projection, main, etc. |
| `scripts/sync-obsidian.sh`                                        | Linux flock wrapper with no-op guard + portability abort                  | VERIFIED | 5.9K, contains `flock`, `command -v flock`, no-op-delta guard, clock-skew cap, quote-strip          |
| `.claude/commands/sync-obsidian.md`                               | Slash command exposing /sync-obsidian                                     | VERIFIED | 3.8K with `--backfill`/`--incremental`/`--dry-run` mode detection                                    |
| `.claude/commands/triage-inbox.md` (modified)                     | Hook + `git add ... vault-build/`                                         | VERIFIED | Step 6 sync hook at line 164; `git add ... vault-build/` at line 178                                |
| `.claude/commands/task.md` (modified)                             | Hook + `git add ... vault-build/`                                         | VERIFIED | Hook at line 181; `git add ... vault-build/` at line 198                                             |
| `.claude/commands/invoice.md` (modified)                          | Hook + `git add ... vault-build/`                                         | VERIFIED | Hook at line 518; `git add ... vault-build/` at line 531                                             |
| `scripts/push-and-sync.sh` (annotation)                           | Comment confirming vault-build/ rides existing rail                       | VERIFIED | Line 6: `# Note: vault-build/ rides this rail per D-02 — slash commands commit vault-build/ before invoking this script.` |
| `mac/com.agend.vault-sync.plist`                                  | KeepAlive=true, RunAtLoad=true, no WatchPaths                             | VERIFIED | Confirmed; ProgramArguments points to `vault-sync-watcher.sh`                                        |
| `mac/vault-sync-watcher.sh`                                       | fswatch --latency 2 + xargs invoking vault_writer                          | VERIFIED | Confirmed; uses `.venv/bin/python3` (Glen's d3e24d2 fix)                                            |
| `mac/install-daemon.sh`                                           | Idempotent installer                                                      | VERIFIED | Steps gated on `command -v fswatch`, `[ -d .venv ]`, `cmp -s plist`; ends with `launchctl unload-then-load` |
| `mac/README.md`                                                   | Operator setup + troubleshooting + iCloud Optimize warning + Mac wrapper warning | VERIFIED | 10.3K including 4-step Complete Setup Checklist, iCloud Optimize Mac Storage warning (Pitfall 2), explicit "Do NOT call scripts/sync-obsidian.sh on Mac" header (Issue 7) |
| `vault-build/Clients/property-council-australia.md`              | Backfilled note with marker pairs                                         | VERIFIED | 2.4K, 4 marker references (1× OPEN-ITEMS-START/END pair, 1× ACTIVITY-LOG-START/END pair), 7 activity entries with 📧 emoji |
| `vault-build/Clients/_Unknown.md`                                  | Fallback note with grouped unmatched records                              | VERIFIED | 13K, 22 group buckets per Pattern 8 including the `needs-response` priority-bucket leak labeled with the data-quality flag |

### Key Link Verification

| From                                                  | To                                                                          | Via                                                              | Status | Details                                                                                                          |
| ----------------------------------------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------- |
| `scripts/lib/vault_writer.py`                         | `data/config/clients.jsonl`                                                 | `load_clients()` JSON-line parser                                | WIRED  | Function at line 327 reads `<data_root>/config/clients.jsonl`, builds slug map with collision detection         |
| `scripts/lib/vault_writer.py`                         | `data/triage/`, `data/tasks/active.jsonl`, `data/invoices/active.jsonl`     | `_gather_events()` NDJSON streaming                              | WIRED  | Lines 654-677; observable: 62 events routed against real data                                                    |
| `scripts/lib/vault_writer.py`                         | `<feed_path>` (default `<data_root>/feed.jsonl`)                            | `--feed-path` argparse + `append_feed_entry()`                   | WIRED  | Threaded through `run_backfill`, `run_incremental`, `run_projection`; default resolved at CLI boundary line 1145 |
| `scripts/lib/vault_writer.py`                         | `vault-build/Clients/*.md`                                                  | `_atomic_write()` tempfile + os.replace + fsync(file+dir)        | WIRED  | Lines 296-322; observable: 4 client notes on disk match expected scaffold                                        |
| `scripts/sync-obsidian.sh`                            | `scripts/lib/vault_writer.py`                                               | `exec /usr/bin/env python3 -m scripts.lib.vault_writer`          | WIRED  | Line 120 (after flock acquire and no-op-delta gate)                                                              |
| `.claude/commands/triage-inbox.md`                    | `scripts/sync-obsidian.sh`                                                  | Step 6 — bash invocation BEFORE dashboard rebuild commit         | WIRED  | Line 167 (`\|\| true` defensive)                                                                                  |
| `.claude/commands/task.md`                            | `scripts/sync-obsidian.sh`                                                  | Post-Execution sync step                                         | WIRED  | Line 181                                                                                                         |
| `.claude/commands/invoice.md`                         | `scripts/sync-obsidian.sh`                                                  | Post-Mutation sync step                                          | WIRED  | Line 518                                                                                                         |
| `mac/com.agend.vault-sync.plist`                      | `mac/vault-sync-watcher.sh`                                                 | ProgramArguments string array                                    | WIRED  | Plist line 10 → `/Users/glenr/work/agend-ops/mac/vault-sync-watcher.sh` (Mac Studio canonical clone path)        |
| `mac/vault-sync-watcher.sh`                           | `scripts/lib/vault_writer.py`                                               | `fswatch \| xargs python3 -m scripts.lib.vault_writer --mode project-to-icloud` | WIRED  | Lines 17-21; uses `.venv/bin/python3` (Glen's installer fix)                                                     |
| `scripts/lib/vault_writer.py` (--mode project-to-icloud) | `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AgendOps/Clients/` | atomic temp+rename writes via `replace_managed_section`          | WIRED  | argparse default at line 1121-1126; verified by `TestProjection.test_first_time_creates_new_file` PASS         |
| `scripts/lib/vault_writer.py` (projection abort path) | `<feed_path>` threaded via `--feed-path`                                    | `handle_marker_error_for_feed` + `append_feed_entry`             | WIRED  | Verified by `TestProjection.test_corrupt_source_marker_aborts_with_critical_feed` and `test_existing_target_marker_error_aborts` PASS |

### Data-Flow Trace (Level 4)

| Artifact                                          | Data Variable                          | Source                                            | Produces Real Data | Status   |
| ------------------------------------------------- | -------------------------------------- | ------------------------------------------------- | ------------------ | -------- |
| `vault-build/Clients/property-council-australia.md` | activity_log content                   | `_gather_events()` → `data/triage/*.jsonl`        | YES                | FLOWING  |
| `vault-build/Clients/_Unknown.md`                  | grouped activity_log + Pattern 8 buckets | `_gather_events()` unknown_pairs (62 events total) | YES (53 in _Unknown alone) | FLOWING  |
| `vault-build/Clients/*.md` frontmatter            | last_synced timestamp                  | `now_iso_with_offset()`                           | YES (real ISO 8601) | FLOWING  |

### Behavioral Spot-Checks

| Behavior                                           | Command                                                                                        | Result                                          | Status |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------- | ------ |
| Test suite passes (all 25 tests)                   | `python3 -m unittest discover scripts/tests`                                                   | `Ran 25 tests in 0.127s OK`                     | PASS   |
| Module exports expected symbols                    | `from scripts.lib.vault_writer import ...`                                                     | EMOJI_BY_KIND, MANAGED_SECTIONS, slugify all importable; `slugify('Property Council Australia') == 'property-council-australia'` | PASS   |
| Real-data dry-run produces expected stats          | `python3 -m scripts.lib.vault_writer --mode incremental --dry-run --data-root data --build-root /tmp/dry-run-test` | `vault_writer incremental complete: {'clients_written': 0, 'events_routed': 62}` | PASS   |
| Marker pair count is exactly 1+1 per file          | `grep -c "OPEN-ITEMS-START\|OPEN-ITEMS-END\|ACTIVITY-LOG-START\|ACTIVITY-LOG-END"` × 4 files   | All 4 files show exactly 4 marker references    | PASS   |
| Idempotency contract holds against real data       | `git show 453941d --stat` (e2e backfill commit)                                                | 4 files changed, 4 insertions(+), 4 deletions(-) — only `last_synced` lines differ | PASS   |
| Three post-review fixes present in code            | `git log --oneline 940456d 2961290 a903bc0`                                                    | All 3 commits exist with content matching descriptions; `fcntl.flock` present at vault_writer.py:787 | PASS   |
| Mac installer fix present                          | `git log --oneline d3e24d2 d0990d9`                                                            | Both commits exist; mac/install-daemon.sh creates `.venv`; mac/README.md is 10.3K with full operator guide | PASS   |

### Requirements Coverage

| Requirement | Source Plan          | Description                                                                                            | Status    | Evidence                                                                                                                      |
| ----------- | -------------------- | ------------------------------------------------------------------------------------------------------ | --------- | ----------------------------------------------------------------------------------------------------------------------------- |
| INTL-01     | All 5 plans (10-01..10-05) | Context accumulation — client history, past decisions stored in structured files (Phase 10 foundation, Phase 11 extends) | SATISFIED | Per-client `vault-build/Clients/<slug>.md` notes accumulate triage/task/invoice history with timestamped Activity Log + Open Items + Glen-owned Decisions section. 4 clients × full history → 62 routed events; iPhone-readable via iCloud Obsidian. Phase 11 will extend with Contract Manager data. |

No orphaned requirements detected. INTL-01 is the only requirement mapped to Phase 10 (Phase 11 extends).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `scripts/lib/vault_writer.py` | 757 | `TODO(future): per-client touched-set optimization` | Info | Documented v1 simplification per Pattern 3; explicitly stated in plan that incremental == backfill in v1. Not a stub. |
| `scripts/lib/vault_writer.py` | 815, 826, 940, etc. | `placeholder` references | Info | All references are to iCloud `.icloud` placeholder files (Apple's eviction mechanism), not stub placeholders. Legitimate domain term. |

No blockers. No warnings. No stub patterns hiding incomplete implementations.

### Human Verification Required

None — Glen has already executed the human-verify checkpoint on real hardware.

**Evidence of human verification:**
1. **Mac Studio install:** Commit `d3e24d2` authored by `Glen Rosie <glenr@GlensMacStudio.localdomain>` proves the installer ran on the actual Mac Studio (not the dev machine) and Glen iterated on it (added Python venv handling).
2. **Operator documentation:** Commit `d0990d9` extends mac/README.md from a basic guide to a 10.3K comprehensive setup guide — this kind of detail only emerges from real installation experience.
3. **Round-trip e2e:** Commit `453941d` (`data: e2e test backfill`, authored from Mac Studio) shows the full data path executed end-to-end and the diff is **only `last_synced` deltas in 4/4 files** — proving the engine is deterministic AND the round-trip works (Mac → vault_writer → vault-build → git push).
4. **User statement:** "so far it's working - I did the initial backfill and e2e testing on the iphone, so I think it's all up to date."

### Test Suite Files

- `scripts/tests/__init__.py` (package marker)
- `scripts/tests/test_vault_writer.py` (25 tests across 7 test classes: TestSlugify, TestReplaceManagedSection, TestMarkerError, TestRenderLogLine, TestBackfillIdempotent, TestMain, TestProjection)
- All 25 tests pass: `Ran 25 tests in 0.127s OK`
- Includes the post-review regression test `TestProjection.test_second_projection_preserves_user_content` (commit a903bc0) — pins the highest-impact data-loss invariant (Glen's user-edited Overview/Decisions survive future projections)

### Gaps Summary

**No gaps.** All 16 must-haves verified, all 17 artifacts present, all 12 key links wired, all 25 unit tests pass, all 7 behavioral spot-checks pass, INTL-01 satisfied, and Glen has confirmed end-to-end functionality on real hardware (Mac Studio install + iPhone Obsidian visibility + round-trip e2e backfill commit). The three post-review fixes (940456d serialization, 2961290 per-file isolation + WARN, a903bc0 regression test) are all present in the code and increase coverage.

**Note on STATE.md / ROADMAP.md status markers:** STATE.md shows `stopped_at: Phase 10 context gathered` and ROADMAP.md still has Plan 10-05 unchecked. These are orchestrator-owned files updated AFTER verification passes — not a verification gap. Per Plan 10-05 SUMMARY ("STATE/ROADMAP/REQUIREMENTS untouched: orchestrator owns these per the parallel_execution rules"), this is the expected state at verification time.

---

_Verified: 2026-05-01_
_Verifier: Claude (gsd-verifier)_
