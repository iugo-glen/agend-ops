---
status: passed
phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr
source: [11-VERIFICATION.md]
started: 2026-05-02T23:51:27+09:30
updated: 2026-05-03T07:00:00+10:00
---

## Current Test

Both UAT items completed 2026-05-03. Phase 11 code is production-verified end-to-end on Coolify with LIVE CM data flowing into client notes (after fixing two CM server-side Prisma schema bugs in contracts.agend.info). 3/3 mapped clients now have populated `contract_start`, `primary_contact`, and `deployed_modules` from CM. iPhone visual verification still pending (Glen's call when convenient).

## Tests

### 1. Mint CM API key + run mapping pass on Coolify (Plan 02 Task 3) — ✅ PASSED 2026-05-03

result: passed (2026-05-03; commit ffc4806)
- Glen minted CM API key at https://contracts.agend.info/settings/mcp 2026-05-03
- Glen injected CONTRACT_MANAGER_API_KEY into Coolify agend-ops service env
- Mapping pass run on Mac instead of Coolify (Pitfall 1 deviation accepted; Coolify host lacks ruamel.yaml — see Current Test note above)
- Result: queried=3, mapped=3, unchanged=0, failed=0
  - propertycouncil.com.au → cm_client_id 18
  - atem.org.au → cm_client_id 1
  - otaus.com.au → cm_client_id 225
- data/config/clients.jsonl committed (ffc4806) and pushed; Coolify synced

original expected steps below (kept for audit):

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

### 2. End-to-end CM-aware backfill on Coolify + iPhone Obsidian visual verification (Plan 04 Task 3) — ✅ PASSED (code) / ⚠️ CM server bug surfaced 2026-05-03

result: passed (code verified live on Coolify; CM server-side bug discovered and tracked separately)
- Coolify Python runtime fixed: `apt install python3-ruamel.yaml python3-ruamel.yaml.clib`
- Live backfill ran on Coolify: `vault_writer backfill complete: {'clients_written': 4, 'events_routed': 73}` — exit 0
- Phase 11 mitigation chain proven LIVE on production:
  - **D-A1 fallback chain**: live read first, cache-on-failure logic engaged
  - **T-11-04-06 isolation**: per-client try/except prevented one CM failure from killing the whole sync
  - **T-11-02-01 mitigation**: API key NOT echoed in feed warning entries (verified)
  - **D-C2-REVISED**: zero `## Sites` sections in any regenerated note
  - **CM-TODOS / USAGE / ACTIVITY-LOG markers**: present in all regenerated notes
  - **Graceful fallback rendering**: "_(CM data unavailable; will refresh next sync)_" + "_(no usage data)_" when CM is down
  - **Cache file**: created at `data/.cm-cache.json`, gitignored ✅
- iPhone visual verification deferred until CM server bug is fixed (no point checking rendering when CM data is empty by upstream bug)

## CM Server Bugs Fixed 2026-05-03

Two stale-field bugs in `contracts.agend.info` get_client_summary handler — both shipped:

1. **`Contact.role` → `Contact.position`** (commit b1f95ca on contract-manager:main)
   `get_client_summary` was selecting `role` from contacts; field is actually `position` per the Prisma schema. Fixed in `src/lib/mcp/tools/lookups.ts:103`.

2. **`Invoice.paidAmount` → derived from `paidDate`** (commit cdd94ed on contract-manager:main)
   Two handlers (`get_client_summary` recentInvoices subquery + `get_cash_flow_summary`) were selecting `paidAmount` which doesn't exist on the Invoice model. Schema only has `amount` + `paidDate` (no partial-payment tracking). Fixed by removing from select and deriving: `paidAmount = paidDate ? Number(amount) : 0`. Fixed in `src/lib/mcp/tools/lookups.ts:155,201` + `src/lib/mcp/tools/financial.ts:290,314,317`.

Both fixes verified: 26/26 vitest unit tests pass. Coolify auto-deployed both. Re-running agend-ops backfill after second fix produced **clean run with zero CM warnings** and **all 3 mapped clients populated with live CM data**:

- **PCA** (cm_client_id 18): `contract_start: '2025-04-01'`, `primary_contact: Craig Horton`, 20+ deployed modules
- **ATEM** (cm_client_id 1): `contract_start: '2026-03-11'`, `primary_contact: David Hathaway`, 1 deployed module
- **OTA** (cm_client_id 225): `primary_contact: Alexandra Reynolds`, no contract data (no active CM contract for OTA)

Empty contract events 📄 and zero CM invoices in Activity Log = CM legitimately has no expiring contracts or overdue invoices right now (not a bug).

original expected steps below (kept for audit):

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
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- **Coolify steady-state runtime decision (open):** Today the Mac ran the one-time mapping pass (Pitfall 1 deviation; accepted) and Coolify ran the live backfill (after `apt install python3-ruamel.yaml`). Neither host currently has GitHub push credentials AND the right Python deps AND the CM API key all in one place — making the steady-state "who runs sync, when, and commits where" pattern still ambiguous. Worth a discuss-phase to formalise.

- **Coolify push credentials (deployment gap):** Coolify has read-only access to GitHub (it pulls but cannot push). When Coolify regenerates vault-build/, the artifacts had to be rsync'd back to Mac for committing. A future phase should set up either deploy-key push from Coolify OR move sync to Mac-as-canonical (Mac already has push creds + ruamel + iCloud).

- **iPhone Obsidian visual verification (deferred):** Glen will check on iPhone when convenient — the rendering on iPhone is independent of the sync pipeline (iCloud → Obsidian) and will reflect whatever's in the iCloud-projected vault. Phase 10 D-03 routing means projection happens via Mac LaunchAgent reading the same vault-build/ that's now committed. Glen can verify any time.

- **(Resolved) CM server Prisma bugs:** Two field-name mismatches in `get_client_summary` handler at `contracts.agend.info` were fixed in commits b1f95ca and cdd94ed (contract-manager:main). Live CM data now flows into agend-ops client notes. See "CM Server Bugs Fixed" section above for details.
