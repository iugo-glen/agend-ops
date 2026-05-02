---
status: partial
phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr
source: [11-VERIFICATION.md]
started: 2026-05-02T23:51:27+09:30
updated: 2026-05-02T23:51:27+09:30
---

## Current Test

[awaiting human testing — Glen will perform after Phase 11 ships per "don't stop! I'll add keys later" override 2026-05-02]

## Tests

### 1. Mint CM API key + run mapping pass on Coolify (Plan 02 Task 3)

expected:
1. Mint a CM API key at `https://contracts.agend.info/settings/mcp` (UI shows plaintext exactly once; bcrypt-hashed server-side; format `cm_live_<48_hex>`).
2. Inject into Coolify env vars for the `agend-ops` service: `CONTRACT_MANAGER_API_KEY=cm_live_...` (Coolify dashboard → service → Environment Variables).
3. SSH to Coolify and run the mapping pass:
   ```bash
   ssh root@103.249.238.17
   cd /opt/agend-ops
   python3 -m scripts.lib.vault_writer --mode map-cm-clients --data-root data
   ```
4. Expected output: `vault_writer map-cm-clients complete: {'queried': 3, 'mapped': N, 'unchanged': 0, 'failed': M}` where N + M = 3.
5. Verify `data/config/clients.jsonl` now contains `"cm_client_id": <int>` on each successful record.
6. Verify any failed records have a corresponding `"level": "warning"` entry in `data/feed.jsonl`.
7. Commit `data/config/clients.jsonl` and run `bash scripts/push-and-sync.sh`.
8. Optional: confirm `data/.cm-cache.json` does NOT exist after this mode (cache populates during sync, not mapping).

result: [pending]

### 2. End-to-end CM-aware backfill on Coolify + iPhone Obsidian visual verification (Plan 04 Task 3)

expected:
1. SSH to Coolify and confirm `CONTRACT_MANAGER_API_KEY` is exported (`echo "${CONTRACT_MANAGER_API_KEY:0:8}..."` shows prefix only).
2. Run a CM-aware backfill: `bash scripts/sync-obsidian.sh --backfill`. Expect output containing `vault_writer backfill complete: {'clients_written': N, 'events_routed': M}`.
3. Inspect one client note: `cat vault-build/Clients/<slug>.md`. Verify:
   - Frontmatter contains `domain`, `client_name`, `status`, `last_synced` (Phase 10) PLUS `contract_start`, `contract_end`, `primary_contact`, `deployed_modules`, `sites: []` (Phase 11; populated where CM has data).
   - `## TODO: Missing CM Data` section between `## Overview` and `## Open Items`. Body shows `_(no missing CM data)_` if all 4 monitored fields populated, otherwise bullets like `- contract_start — set in Contract Manager (...)`.
   - `## Usage` section between `## Open Items` and `## Activity Log`. Body either lists project utilization bullets or `_(no usage data)_`.
   - Activity Log includes contract events rendered as `### [YYYY-MM-DD HH:MM] 📄 Contract renewal due — ...` and any CM-tracked invoices not present locally.
   - There is NO `## Sites` section anywhere in the file (D-C2-REVISED).
4. Confirm cache file exists and is gitignored: `ls -la data/.cm-cache.json` (file present), `git check-ignore data/.cm-cache.json` (returns the path), `git status` (file does NOT appear in untracked list).
5. Tail feed for warning entries: `grep '"level": "warning"' data/feed.jsonl | tail -5`. Zero is fine; some is fine. Key: no `critical` entries from this run.
6. Optional resilience test: temporarily set `CONTRACT_MANAGER_API_KEY="cm_live_invalid"` and re-run the backfill. Expect a warning entry per affected client AND `cm_data_stale_since` stamped on the regenerated notes (cache hit if cache exists). Restore the real key after.
7. Commit + push regenerated `vault-build/Clients/*.md` and `data/feed.jsonl` if they changed: `git add vault-build data/feed.jsonl && git commit -m "data(11): live CM-aware backfill" && bash scripts/push-and-sync.sh`. Confirm `data/.cm-cache.json` does NOT appear (gitignored).
8. Open Obsidian on iPhone (vault is in iCloud per Phase 10 D-03). Open one client note. Verify:
   - Frontmatter readable at the top (Obsidian renders as a property table).
   - CM-TODOS section is collapsed-by-default-readable (per D-08 marker discipline).
   - Usage section shows hours/budget where SLA data exists.
   - Activity Log items render with the new 📄 emoji on contract events.
   - Glen-owned sections (Overview, Decisions) preserved unchanged.

result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

(None — both items are deferred-by-design per Glen 2026-05-02 AUTO_MODE override. Code paths are proven by 17 mocked-CM unit tests across 6 integration test classes; the deferred items are LIVE infrastructure verifications that require the real CM API key Glen mints in step 1.)
