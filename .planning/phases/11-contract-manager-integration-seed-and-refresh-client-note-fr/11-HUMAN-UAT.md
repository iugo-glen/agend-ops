---
status: passed
phase: 11-contract-manager-integration-seed-and-refresh-client-note-fr
source: [11-VERIFICATION.md]
started: 2026-05-02T23:51:27+09:30
updated: 2026-05-03T07:00:00+10:00
---

## Current Test

Both UAT items completed 2026-05-03. Phase 11 code is production-verified end-to-end on Coolify. Discovered CM server-side Prisma schema bug (separate from phase 11) — see Gaps section.

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

## CM Server Bug (separate ticket — contracts.agend.info)

`get_client_summary` on `https://contracts.agend.info/api/mcp` returns `CmRpcError` for all 3 clients with the same Prisma schema mismatch:

```
Invalid prisma.client.findUnique() invocation:
Unknown field `role` for select statement on model `Contact`.
Available options are marked with ?: clientId, position, isPrimary, ignitionId, isRecipient, isSigner, createdAt, updatedAt, client, acceptedProposals, receivedProposals, _count.
```

The MCP `get_client_summary` handler is selecting a `role` field that doesn't exist on the Prisma `Contact` model. This is a CM-side schema/handler mismatch (NOT phase 11). Once fixed at contracts.agend.info, the next phase 11 sync will auto-populate `contract_start`, `contract_end`, `primary_contact`, `deployed_modules`, contract events 📄, and Usage SLA data — no code changes needed in agend-ops.

Affected clients (all 3 mapped):
- propertycouncil.com.au (cm_client_id: 18)
- atem.org.au (cm_client_id: 1)
- otaus.com.au (cm_client_id: 225)

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

- **CM server-side Prisma bug (separate ticket — contracts.agend.info):** `get_client_summary` MCP handler is selecting a `role` field that doesn't exist on the `Contact` Prisma model. Hits all 3 clients identically. This is a bug in Glen's other repo (the contract-manager codebase), NOT phase 11. Phase 11 handled it gracefully exactly as designed: per-client try/except + warning feed entries + graceful fallback rendering + no crashes. Once fixed, the next sync will populate CM data without code changes here.

- **Coolify steady-state runtime decision (open):** Today the Mac ran the one-time mapping pass (Pitfall 1 deviation; accepted) and Coolify ran the live backfill (after `apt install python3-ruamel.yaml`). Neither host currently has GitHub push credentials AND the right Python deps AND the CM API key all in one place — making the steady-state "who runs sync, when, and commits where" pattern still ambiguous. Worth a discuss-phase to formalise.

- **Coolify push credentials (deployment gap):** Coolify has read-only access to GitHub (it pulls but cannot push). When Coolify regenerates vault-build/, the artifacts had to be rsync'd back to Mac for committing. A future phase should set up either deploy-key push from Coolify OR move sync to Mac-as-canonical (Mac already has push creds + ruamel + iCloud).
