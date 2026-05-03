---
status: partial
phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings-
source: [12-VERIFICATION.md]
started: 2026-05-03T12:05:22+09:30
updated: 2026-05-03T12:05:22+09:30
---

## Current Test

Glen pausing 2026-05-03 — return to item 1 (OAuth provisioning on Coolify) when ready. Item 1's architectural finding has been documented in revised step 1 below: the original "scp credentials from Mac" plan does NOT work because Mac uses Keychain. Coolify needs fresh OAuth minted there directly. ~30 min of work the next time Glen sits down with this. Phase 12 code is shipped and correct on master + Coolify HEAD.

## Tests

### 1. Provision OAuth on Coolify (one-time prerequisite — REVISED 2026-05-03)

**IMPORTANT FINDING during attempted provisioning 2026-05-03:** The original plan to "scp `~/.google_workspace_mcp/credentials/` from Mac to Coolify" does NOT work. The hardened-workspace MCP on macOS stores credentials in **macOS Keychain**, not in JSON files (per `auth/credential_store.py` docstring). The directory exists but is empty by design. There's no file to copy.

**Actual steps required:**

```bash
# 1. SSH to Coolify host
ssh root@103.249.238.17

# 2. Clone hardened-workspace-mcp on Coolify (mirrors Mac install)
mkdir -p /opt && cd /opt
git clone https://github.com/c0webster/hardened-google-workspace-mcp.git
cd hardened-google-workspace-mcp
uv sync   # uv is already installed on Coolify (we used it for graphify)

# 3. Set the credentials dir BEFORE running OAuth — forces JSON-file storage
#    instead of Linux SecretService (which workspace_client.py CAN'T read)
export GOOGLE_MCP_CREDENTIALS_DIR=/root/.google_workspace_mcp/credentials
mkdir -p "${GOOGLE_MCP_CREDENTIALS_DIR}"

# 4. Set the OAuth client credentials (copy values from your Mac's
#    ~/.claude.json hardened-workspace `env` block)
export GOOGLE_OAUTH_CLIENT_ID=804182813448-j6sf95h1fc9s1lqtbh08a47s6dlvhg2r.apps.googleusercontent.com
export GOOGLE_OAUTH_CLIENT_SECRET=<copy from ~/.claude.json on Mac — DO NOT paste here>

# 5. Run the MCP OAuth flow — this opens a browser-based consent. Coolify is
#    headless, so the MCP will print a URL you open IN YOUR BROWSER on Mac,
#    you consent as glen@iugo.com.au, then paste the redirect URL back to the
#    Coolify shell. Specific command depends on the MCP's auth helper —
#    typical pattern:
uv run python -m main --auth glen@iugo.com.au
# or
uv run python scripts/auth_helper.py glen@iugo.com.au
# (check the repo's README on Coolify for the exact entry point)

# 6. Verify JSON files now exist
ls -la "${GOOGLE_MCP_CREDENTIALS_DIR}"
# Expected: glen@iugo.com.au.json with refresh_token + access_token

# 7. Persist the env var for future shell sessions on Coolify (so cron / manual
#    runs both see it). Append to /etc/environment or root's .bashrc:
echo 'GOOGLE_MCP_CREDENTIALS_DIR=/root/.google_workspace_mcp/credentials' >> /etc/environment
# (also set CONTRACT_MANAGER_API_KEY here if not already — Phase 11 prereq)
```

result: [pending — start here]

### 2. Coolify backfill smoke test (sync runs end-to-end with workspace_client live)

expected:
After step 1 above is complete, in the same SSH session OR after `source /etc/environment`:
   ```bash
   ssh root@103.249.238.17
   cd /opt/agend-ops
   echo "${GOOGLE_MCP_CREDENTIALS_DIR}"  # confirm set
   ls -la "${GOOGLE_MCP_CREDENTIALS_DIR}"  # confirm OAuth blob present
   bash scripts/sync-obsidian.sh --backfill
   ```
3. Expected output: `vault_writer backfill complete: {'clients_written': N, 'events_routed': M}` where M is materially higher than Phase 11's baseline (73 events). Calendar events from rolling 90d + Drive top-20-per-client should add roughly 100-300 new events depending on activity.
4. Verify NEW cache files exist + are gitignored:
   ```bash
   ls -la data/.cal-cache.json data/.drive-cache.json
   command git check-ignore data/.cal-cache.json data/.drive-cache.json
   command git status  # neither should appear
   ```
5. Tail feed for warning entries from this run:
   ```bash
   command tail -20 data/feed.jsonl | command grep -E "Workspace stale|workspace_client|cal-cache|drive-cache"
   ```
   Zero warning entries on a successful run; some warnings are fine (cache fallback fired due to transient API blip).

result: [pending]

### 2. iPhone Obsidian visual verification (D-C1 + D-C2 line shapes render correctly)

expected:
1. Open Obsidian on iPhone (vault is in iCloud per Phase 10 D-03; projection happens via Mac Studio LaunchAgent or manual `project-to-icloud` from MacBook).
2. Open one client note that has both calendar and drive activity (e.g., Property Council Australia or AHRI). Verify Activity Log section contains:
   - **Calendar entries** in `### [YYYY-MM-DD HH:MM] 📅 {title} — {N} attendees` shape with `> [Open in Calendar](htmlLink)` underneath
   - **Drive entries** in `### [YYYY-MM-DD HH:MM] 📝 {filename} — modified by {modifier}` shape with `> [Open in Drive](webViewLink)` underneath
   - **Existing emojis still present**: 📧 (email triage), 📄 (CM contract), 💰 (invoice), ✅ (task)
3. Run anchor check on Mac:
   ```bash
   command grep "📄" vault-build/Clients/*.md | command grep -v "Contract" | head -3
   ```
   Expected: empty result. Confirms 📄 stays contract-only (D-C3 invariant) — no Drive doc accidentally rendered with the contract emoji.
4. Frontmatter check:
   ```bash
   command grep "^workspace_data_stale_since:" vault-build/Clients/*.md | head -3
   ```
   On a successful sync this should be empty (no clients have stale Workspace data). After a forced cache-fallback test (item 4 below), expect this to appear on affected notes.
5. Open one client's CM-TODOS section — make sure no regression from Phase 11 (e.g., `_(no missing CM data)_` for clients with full CM data, or specific TODO bullets for clients missing CM fields).

result: [pending]

### 3. Cache files materialize on Coolify and stay out of git

expected:
1. After item 1's backfill completes:
   ```bash
   ls -la /opt/agend-ops/data/.cal-cache.json
   ls -la /opt/agend-ops/data/.drive-cache.json
   command git -C /opt/agend-ops check-ignore data/.cal-cache.json data/.drive-cache.json
   command git -C /opt/agend-ops status  # neither should appear in untracked
   ```
2. Inspect cache content shape (via `python3 -c 'import json; d = json.load(open("data/.cal-cache.json")); print(sorted(d.keys()))'`):
   - cal-cache.json: top-level keys include `events_by_window` (or similar) + `cached_at` timestamp
   - drive-cache.json: top-level keys include `files_by_client` (or similar) + `cached_at` timestamp
3. Confirm `git log --diff-filter=A --name-only -- data/.cal-cache.json data/.drive-cache.json` returns NO commits (file was never accidentally committed).

result: [pending]

### 4. Negative-path cache fallback (optional resilience test)

expected:
1. Backup the OAuth blob: `cp -r "${GOOGLE_MCP_CREDENTIALS_DIR}" "${GOOGLE_MCP_CREDENTIALS_DIR}.bak"`
2. Corrupt or remove the credentials file:
   ```bash
   echo "broken" > "${GOOGLE_MCP_CREDENTIALS_DIR}/credentials.json"  # or whatever the OAuth file is named
   ```
3. Re-run `bash scripts/sync-obsidian.sh --backfill`. Expected behavior:
   - Sync STILL completes successfully (does NOT crash) — per-tool try/except + cache fallback chain holds
   - 4 warning-level entries appear in `data/feed.jsonl` (one per cal/drive call per client batch — exact count depends on retry exhaustion)
   - Affected client notes get `workspace_data_stale_since: <ts>` stamped in frontmatter
   - Activity Log shows the LAST KNOWN cached cal/drive content
   - No `level: critical` entries from this run
4. Restore credentials: `mv "${GOOGLE_MCP_CREDENTIALS_DIR}.bak" "${GOOGLE_MCP_CREDENTIALS_DIR}"` and re-run backfill. Expected: `workspace_data_stale_since` is CLEARED from frontmatter on the next successful read.

result: [pending] (optional — skip if items 1-3 pass cleanly)

## Summary

total: 4 (3 required + 1 optional)
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

(None at the code+test layer — verifier scored 23/23 must-haves verified. The 4 items above are LIVE infrastructure verifications that require Coolify execution with real OAuth credentials. Same deferred-verification pattern Phase 11 used for its Tasks 02-03 and 04-03.)

**Coolify OAuth credentials availability** (research Q3 follow-up — REVISED 2026-05-03): Phase 12 unconditionally validates `GOOGLE_MCP_CREDENTIALS_DIR` on Coolify (per Plan 12-01). If the env var is unset OR the path doesn't exist, sync-obsidian.sh fails fast at line 42. The original plan to scp credentials from Mac is INVALID — Mac stores them in Keychain (no files), so Glen must mint fresh OAuth on Coolify directly. See revised step 1 above.

**Phase 12.1 candidate (architectural follow-up):** The Phase 12 RESEARCH.md and CONTEXT.md (D-X1) assumed OAuth credentials would be portable JSON files. In reality, hardened-workspace-mcp uses platform-native credential stores by default (macOS Keychain on Mac, SecretService on Linux). For workspace_client.py to work on Coolify, `GOOGLE_MCP_CREDENTIALS_DIR` must be set BEFORE the OAuth flow so the MCP falls back to LocalDirectoryCredentialStore. Worth a follow-up phase that either:
(a) makes workspace_client.py able to read directly from system Keychain/SecretService (not just JSON files), OR
(b) bakes the "set GOOGLE_MCP_CREDENTIALS_DIR before auth" requirement into the install docs more prominently.
