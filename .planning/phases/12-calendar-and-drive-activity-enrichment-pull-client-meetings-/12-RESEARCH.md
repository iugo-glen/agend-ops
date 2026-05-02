# Phase 12: Calendar + Drive Activity Enrichment - Research

**Researched:** 2026-05-03
**Domain:** Google Workspace ingestion (Calendar + Drive) into Phase 10/11 vault-writer pipeline
**Confidence:** HIGH on integration architecture; HIGH on hardened-workspace tool shapes (source-verified); BLOCKED on Drive root inspection (cannot run MCP from researcher subagent — Glen-action required)

## Summary

Phase 12 extends the per-client Obsidian client notes (Phase 10 transport rail + Phase 11 frontmatter/managed-section discipline) with **calendar meetings** and **Drive document activity**, both appended to the existing Activity Log managed section. The 14 locked decisions (D-A1..D-D4) leave a small, additive surface: two new `EMOJI_BY_KIND` entries (📅, 📝), no new managed sections, no frontmatter additions, two new cache files paralleling Phase 11's `data/.cm-cache.json`.

**The single largest finding from this research re-shapes the wave structure**: the hardened-workspace MCP is a **local stdio MCP process**, not a remote JSON-RPC HTTP endpoint. It is **not reachable from `urllib.request`** the way Phase 11's `cm_client.py` reaches `https://contracts.agend.info/api/mcp`. Furthermore, every read tool in the hardened MCP (`get_events`, `list_drive_items`, `search_drive_files`) returns **formatted text strings, not structured JSON**. This invalidates the most natural Phase 11 analog (a `workspace_client.py` that mirrors `cm_client.py`'s urllib seam) and forces an architectural choice the planner MUST make explicit in Plan 01.

Two architectural options resolve the blocker. The strongly recommended option (Option A) skips the MCP entirely on the Coolify backend and calls **Google's REST APIs directly** via `google-api-python-client`, reusing the OAuth token blob already minted by hardened-workspace at `~/.google_workspace_mcp/credentials/`. This preserves single-network-seam discipline (one new `workspace_client.py`), preserves the per-tool retry+cache+warning shape from Phase 11, and lets Phase 12's tests mock the API client the same way `test_cm_client.py` mocks urllib. **Option B** (have Claude orchestrate the MCP calls inside `/sync-obsidian` and snapshot results to `data/.cal-cache.json` + `data/.drive-cache.json` for `vault_writer.py` to consume read-only) violates the CLAUDE.md "vault sync is a single Coolify cron-like operation" assumption Phase 10/11 was built around — it forces sync to run inside an interactive Claude session, which Coolify cannot do. Recommendation: **Option A** with explicit security review of the OAuth credential reuse boundary.

**Primary recommendation:** Build a single `scripts/lib/workspace_client.py` (mirroring `cm_client.py`'s structure: HTTPS seam, retry wrapper, cache I/O, response adapters) that uses `google-api-python-client` against the user's OAuth token blob. Extend `vault_writer._fetch_cm_data_for_run` into a `_fetch_external_data_for_run` that orchestrates CM + Calendar + Drive in one pass with shared retry+cache+warning semantics. Two new `EMOJI_BY_KIND` entries, two new event-tuple builders, two new merge points in `_gather_events`. No new managed sections. No frontmatter changes. Roughly 4 plans across 4 waves, mirroring Phase 11's velocity.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Source scope + matching (Area 1):**
- **D-A1: Calendar source — primary calendar only.** Pull events from `glen@iugo.com.au`'s primary Google Calendar. No additional calendars.
- **D-A2: Calendar matching rule — strict attendee email domain match.** A calendar event is assigned to a client if and only if at least one attendee's email host matches a `client_domain` or alias in `data/config/clients.jsonl`. No fuzzy title matching. Multi-client meeting policy: first-matching-client wins (alphabetical client_domain order); emit a `system`/`info` feed entry per occurrence.
- **D-A3: Drive scope — research-time inspection.** Researcher MUST inspect Glen's Drive via `mcp__hardened-workspace__list_drive_items` at root and propose `DRIVE_CLIENTS_ROOT`. Likely: `/My Drive/Clients/` or `/Shared drives/Agend Clients/`. **STATUS: BLOCKED — see Open Questions Q1.**
- **D-A4: Drive matching rule — folder hierarchy is canonical.** Each immediate subfolder under `DRIVE_CLIENTS_ROOT` represents one client. Subfolder name → matched against `client_domain` or aliases (case-insensitive substring with longest-match preference, mirrors `_clientid_to_slug`). Files at the root (not in any subfolder) are silently ignored, with one info-level feed entry per sync summarizing the count.

**Time window + freshness (Area 2):**
- **D-B1: Calendar window — rolling 90 days.** `now - 90 days` ≤ `start.dateTime` ≤ `now + 30 days`. Hardcoded constants in vault_writer config.
- **D-B2: Drive window — top 20 by modifiedTime, no time bound.** Per client subfolder, recursive listing bounded by `_DRIVE_MAX_DEPTH = 3`, sort by `modifiedTime` desc, take 20.
- **D-B3: Cadence — every sync run, like Phase 11.** Calendar + Drive reads happen on every `sync-obsidian.sh --backfill` invocation, alongside the existing CM read.

**Activity Log shape + frontmatter (Area 3):**
- **D-C1: Calendar entry format.** `### [YYYY-MM-DD HH:MM] 📅 {event_title} — {N} attendees` followed by `> [Open in Calendar]({htmlLink})`. Title verbatim. Time local-Adelaide via `now_iso_with_offset()`.
- **D-C2: Drive entry format.** `### [YYYY-MM-DD HH:MM] 📝 {filename} — modified by {modifier_name}` followed by `> [Open in Drive]({webViewLink})`. `modifier_name` from `lastModifyingUser.displayName` (or email-local-part fallback).
- **D-C3: EMOJI_BY_KIND extension.** Add `"meeting": "📅"`, `"doc": "📝"`. 📄 stays contract-only.
- **D-C4: No new frontmatter keys.** Phase 12 writes ONLY to the Activity Log managed section.

**Privacy filters + redaction (Area 4):**
- **D-D1: Personal-event filter — visibility OR no-external-attendees.** Skip if `visibility == "private"` OR every attendee is internal. **WARNING: hardened MCP does not surface visibility — see Open Question Q4 + Pitfall 3.**
- **D-D2: Mass-attendee filter — skip events with `len(event.attendees) > 25`.**
- **D-D3: Drive content filter — Trash + private/draft.** Skip `trashed: true`, `name` ending `.gdraft` or containing `[DRAFT]`, restricted-shared-with-Glen documents.
- **D-D4: Vault leak posture — vault is Glen-only.** No redaction logic.

### Claude's Discretion

- Exact retry timings (D-A3 of Phase 11 specified 1s/5s/30s; Phase 12 should mirror)
- Cache file shape — single unified `data/.workspace-cache.json` vs separated `data/.cal-cache.json` + `data/.drive-cache.json` (researcher recommendation: SEPARATED — see Architecture Patterns)
- Whether `workspace_client.py` is one module or split into `cal_client.py` + `drive_client.py` (researcher recommendation: SINGLE module — see Architecture Patterns)
- HTTP client library choice for direct Google API calls (`google-api-python-client` vs raw `urllib` against `googleapis.com`)
- Whether the MCP-vs-direct-API architectural choice escalates back to Glen as a discuss-phase follow-up or is decided by the planner
- Phase 11 D-G1 JIT-mapping analog for "new client appears in attendee email but isn't in clients.jsonl yet" — recommendation: write `_Unknown.md` entry, do NOT auto-create clients.jsonl rows from Workspace data (different trust boundary than CM JIT)
- Recursive-walk strategy for Drive (single recursive query with `mimeType != folder` vs explicit per-level `list_drive_items` calls — researcher recommendation: API-side recursive query with `parents in [...]` to minimize round-trips)
- Frontmatter render order — D-C4 forbids new keys, so unchanged

### Deferred Ideas (OUT OF SCOPE)

- **Calendar/Drive frontmatter keys** (`last_meeting_at`, `recent_doc_count`, `activity_counts`): rejected per D-C4. Revisit if/when Glen wants Obsidian DataView dashboards.
- **Multi-client meeting fan-out**: planner default is first-match-wins per D-A2; upgrade to fan-out if proven needed.
- **Cross-client correlation** (Drive doc references suggest a client overlap): out of scope.
- **Calendar/Drive write-back**: out of scope. Vault is read-only consumer.
- **Drive content extraction / summarization**: out of scope. Phase 12 links only.
- **Per-client calendar overrides** (assign meetings from external consultant emails): handled today via `clients.jsonl aliases[]`.
- **Client-shareable note export** (sanitized PDF/MD): out of scope; future phase with its own redaction contract.

## Phase Requirements

The phase description references "TBD (extends INTL-01)" and asks the researcher to propose specific requirement IDs. Recommended:

| ID | Description | Research Support |
|----|-------------|------------------|
| INTL-01-CAL | Calendar meetings matched by attendee email domain appear in per-client Activity Log within rolling 90-day window with 📅 emoji, attendee count, and Open-in-Calendar link, deduped by event ID | D-A1, D-A2, D-B1, D-C1, D-C3; Architecture Pattern 1; Common Pitfalls 1 + 4 |
| INTL-01-DRIVE | Drive documents in the per-client subfolder (under `DRIVE_CLIENTS_ROOT`) appear in per-client Activity Log, top 20 by `modifiedTime` desc, with 📝 emoji, modifier name, and Open-in-Drive link, deduped by file ID | D-A3, D-A4, D-B2, D-C2, D-C3; Architecture Pattern 1; Pitfall 4 |
| INTL-01-PRIVACY | Personal events (no external attendees), mass events (>25 attendees), trashed/draft Drive files, and restricted-shared docs are filtered out before reaching the Activity Log; one info-level summary feed entry per sync explains skip counts | D-D1, D-D2, D-D3; Common Pitfall 3 |
| INTL-01-WORKSPACE-CACHE | Calendar + Drive reads use retry+cache fallback (3 retries 1s/5s/30s → cache → warning feed); cache files gitignored; `cm_data_stale_since`-equivalent staleness signal stamped on affected notes | Phase 11 D-A3 pattern; Architecture Pattern 2 |
| INTL-01-PROJECTION-ISOLATION | Mac daemon's `run_projection` does NOT import `workspace_client` (extends Phase 11 Pitfall 1 / T-11-04-01); subprocess-based negative test enforces the invariant | Common Pitfall 1 |

These IDs propagate cleanly to the planner's per-plan `requirements-completed:` frontmatter and to verifier acceptance criteria.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Calendar event fetch (HTTP/API call) | Coolify Linux container (`scripts/lib/workspace_client.py`) | — | Coolify is the only host that runs `sync-obsidian.sh --backfill`. Mac daemon runs `run_projection` ONLY (Phase 11 Pitfall 1 inheritance). Like `cm_client.py`, this is a per-process external-data fetcher. |
| Drive folder/file fetch (HTTP/API call) | Coolify Linux container (`scripts/lib/workspace_client.py`) | — | Same rationale as Calendar. |
| Cache fallback I/O | Coolify (writes `data/.cal-cache.json` + `data/.drive-cache.json`) | — | Per-host runtime state, not a vault artifact. Gitignored. Mac daemon never reads or writes these. |
| Attendee → client domain match | Coolify (`vault_writer._gather_events` extension) | — | Pure-Python routing logic; same trust boundary as Phase 11 `_clientid_to_slug`. |
| Drive subfolder → client slug match | Coolify (`vault_writer._gather_events` extension) | — | Same as above; longest-substring match against `clients.jsonl`. |
| Privacy filters (D-D1/D-D2/D-D3) | Coolify (filter functions called inside `workspace_client.py` adapter, BEFORE returning to vault_writer) | — | Centralizes filter logic; vault_writer sees only post-filter event/file lists. Mirrors `cm_summary_to_frontmatter_extra` adapter pattern. |
| Activity Log render | Coolify (`vault_writer.render_activity_log` UNCHANGED; new event tuples flow through `render_log_line`) | Mac daemon projects via `run_projection` | The 📅 and 📝 lines are produced on Coolify in `vault-build/Clients/*.md`; the Mac daemon splices them through to iCloud unchanged. |
| Frontmatter render | Coolify (`vault_writer.render_frontmatter` UNCHANGED) | Mac daemon (preserves user-added fields via ruamel.yaml round-trip) | D-C4 forbids new keys; render path is byte-identical to Phase 11. |
| Sync orchestration | Coolify shell (`scripts/sync-obsidian.sh`) | — | Wrapper acquires flock, sets env, exec's `python3 -m scripts.lib.vault_writer`. Phase 12 may need to add `GOOGLE_MCP_CREDENTIALS_DIR` validation alongside `CONTRACT_MANAGER_API_KEY` per D-A2 of Phase 11 — see Open Question Q3. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-api-python-client` | >=2.150 | Direct Google Calendar / Drive REST API access | [VERIFIED: hardened-workspace MCP source uses this — `service.events().list(...)`, `service.files().list(...)`] Standard Google client library; same package the hardened MCP uses internally. Reusing it directly skips the formatted-text-output handicap. |
| `google-auth` | >=2.30 | Loads OAuth credentials.json + token.json blob already minted by hardened MCP | [VERIFIED: hardened-workspace's `auth/google_auth.py:55` references `Credentials` from `google.oauth2.credentials`] Same package; same token format; we read the already-existing OAuth blob, never mint our own. |
| `google-auth-oauthlib` | >=1.2 | Token refresh on expiry | [CITED: Google's official Python quickstart guides] Standard pairing with `google-api-python-client` for refresh flow. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `urllib.request` | stdlib | Token refresh fallback if google-auth unavailable | [VERIFIED: cm_client.py uses urllib stdlib successfully — Phase 11 zero-extra-dep precedent] If the planner picks "raw urllib against googleapis.com" instead of `google-api-python-client` (lower-dep option), urllib is sufficient. |
| `ruamel.yaml` | >=0.18,<0.19 | Frontmatter round-trip (UNCHANGED from Phase 10/11) | Already pinned in `scripts/requirements.txt`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct Google API (Option A — recommended) | hardened-workspace MCP via Claude orchestration (Option B) | Option B keeps the security-hardening boundary intact (no broad-scope OAuth tokens used by sync code) but forces sync to run inside an interactive Claude session — Coolify can't do that. Option A reuses the same OAuth blob the hardened MCP holds, so the credential surface is the same; the differentiation is that Phase 12's Python code can issue tools the hardened MCP **deliberately removed** (e.g., `permissions.update`, `share_drive_file`). Mitigation: keep Phase 12's Google client read-only; document the trust boundary explicitly. |
| `google-api-python-client` | Raw `urllib.request` against `https://www.googleapis.com/calendar/v3/calendars/primary/events` and `https://www.googleapis.com/drive/v3/files` with manual OAuth Bearer header | Raw urllib avoids adding 3 deps to `requirements.txt`. The Google Python client adds ~25 transitive deps. **Recommendation: raw urllib for Phase 12 to preserve Phase 10/11 zero-extra-dep precedent.** Calendar v3 and Drive v3 are both stable JSON REST APIs; we don't benefit from the client library's pagination helpers because we're explicit about page size anyway. |
| Per-tool cache files (`.cal-cache.json` + `.drive-cache.json`) | Single unified `.workspace-cache.json` | Per-tool gives the same shape as Phase 11 `.cm-cache.json`, makes diagnostics easier (`cat data/.cal-cache.json | jq '.global'`), and isolates corruption (a corrupt cal cache doesn't taint drive). Single file is one fewer path to gitignore but reduces clarity. **Recommendation: per-tool. See research question Q6.** |
| Single `workspace_client.py` module | Split `cal_client.py` + `drive_client.py` | Single module mirrors Phase 11's `cm_client.py` shape, avoids duplicating the auth/cache/retry plumbing twice. Calendar and Drive share the same OAuth scope set, the same credential file, the same retry semantics. **Recommendation: single module.** |

**Installation:**
```bash
# If raw-urllib path (recommended for stack consistency):
# No new dependencies — urllib is stdlib

# If google-api-python-client path:
# (would need scripts/requirements.txt update + Coolify rebuild)
pip install google-api-python-client>=2.150 google-auth>=2.30 google-auth-oauthlib>=1.2
```

**Version verification:** `google-api-python-client` 2.150+ is the latest 2.x as of the hardened-workspace MCP's `pyproject.toml`. [ASSUMED] — researcher could not run `pip index versions` to confirm currency in this session. Planner should run `pip index versions google-api-python-client` before adding to requirements.

## Architecture Patterns

### System Architecture Diagram

```
                                    ┌─────────────────────────────────┐
                                    │  Glen runs:                     │
                                    │  bash scripts/sync-obsidian.sh  │
                                    │           --backfill            │
                                    │  on Coolify (103.249.238.17)    │
                                    └─────────────┬───────────────────┘
                                                  │
                       ┌──────────────────────────┴───────────────────┐
                       │ scripts/sync-obsidian.sh                     │
                       │ - validates CONTRACT_MANAGER_API_KEY         │
                       │ - validates GOOGLE_MCP_CREDENTIALS_DIR (NEW) │
                       │ - acquires flock                             │
                       │ - exec python3 -m scripts.lib.vault_writer   │
                       └──────────────────────────┬───────────────────┘
                                                  │
                       ┌──────────────────────────▼───────────────────┐
                       │ vault_writer.run_backfill()                  │
                       │  ↓                                           │
                       │ _fetch_external_data_for_run() (RENAMED      │
                       │   from _fetch_cm_data_for_run; same shape)   │
                       │  ├── CM block (Phase 11 — UNCHANGED)         │
                       │  ├── Calendar block (NEW)                    │
                       │  └── Drive block (NEW)                       │
                       └──────────────────────────┬───────────────────┘
                                                  │
                ┌─────────────────────────────────┼──────────────────────────────────┐
                │                                 │                                  │
     ┌──────────▼─────────┐         ┌─────────────▼─────────┐         ┌──────────────▼─────────┐
     │ scripts/lib/       │         │ scripts/lib/          │         │ scripts/lib/           │
     │   cm_client.py     │         │   workspace_client.py │         │   vault_writer.py      │
     │ (Phase 11)         │         │ (NEW — Phase 12)      │         │   (UNCHANGED orchestr) │
     │                    │         │                       │         │                        │
     │ HTTPS POST →       │         │ HTTPS GET (urllib) →  │         │ _gather_events()       │
     │   contracts.agend  │         │   googleapis.com/     │         │   merges 5 sources:    │
     │   .info/api/mcp    │         │     calendar/v3       │         │   triage, task, inv,   │
     │                    │         │     drive/v3          │         │   contract, meeting,   │
     │ Bearer auth        │         │                       │         │   doc                  │
     │ JSON-RPC envelope  │         │ OAuth Bearer (token   │         │                        │
     │ structuredContent  │         │   from ~/.google_     │         │ render_log_line()      │
     │                    │         │   workspace_mcp/      │         │   uses EMOJI_BY_KIND   │
     │ retry+cache        │         │   credentials/)       │         │   (📅, 📝 added)       │
     │ (.cm-cache.json)   │         │                       │         │                        │
     │                    │         │ retry+cache           │         │ Output:                │
     │ SAME PATTERN       │         │ (.cal-cache.json,     │         │   vault-build/         │
     │ AS PHASE 12        │         │  .drive-cache.json)   │         │     Clients/*.md       │
     └────────────────────┘         └───────────────────────┘         └────────────┬───────────┘
                                                                                   │
                                                                                   │ git push (push-and-sync.sh)
                                                                                   ▼
                                                                       ┌────────────────────────┐
                                                                       │ Mac Studio (always-on) │
                                                                       │ launchd + fswatch      │
                                                                       │ → run_projection() in  │
                                                                       │   vault_writer.py      │
                                                                       │ → splices managed      │
                                                                       │   sections into        │
                                                                       │   ~/Library/.../iCloud │
                                                                       │     /Obsidian/AgendOps │
                                                                       │                        │
                                                                       │ INVARIANT: Mac NEVER   │
                                                                       │ imports cm_client OR   │
                                                                       │ workspace_client       │
                                                                       │ (Pitfall 1 extended)   │
                                                                       └────────────────────────┘
                                                                                   │
                                                                                   ▼
                                                                       ┌────────────────────────┐
                                                                       │ iPhone Obsidian (live) │
                                                                       │ Glen taps a client →   │
                                                                       │ sees Activity Log with │
                                                                       │ 📅 meetings + 📝 docs  │
                                                                       │ alongside existing     │
                                                                       │ 📧✅💰📄 entries       │
                                                                       └────────────────────────┘
```

### Component Responsibilities

| Component | File:Line (existing) or NEW | Responsibility |
|-----------|----------------------------|----------------|
| Sync wrapper | `scripts/sync-obsidian.sh:1-130` (extend) | Add `: "${GOOGLE_MCP_CREDENTIALS_DIR:?...}"` validation alongside Phase 11's CM key check (line 33) |
| Sync engine entry | `scripts/lib/vault_writer.py:1702` (`main()`) | UNCHANGED. The new env var is consumed inside `_fetch_external_data_for_run`, not parsed at CLI. |
| External-data orchestrator | `scripts/lib/vault_writer.py:1165` (`_fetch_cm_data_for_run`) → rename + extend OR keep CM-only and add a second sibling | Single point where all live external reads happen with retry+cache+warning. **Recommendation: rename to `_fetch_external_data_for_run` and extend** (additive: same return shape with two new keys `cal_data` and `drive_data`). Tests for Phase 11 still mock the CM-specific path. |
| Workspace HTTP seam | `scripts/lib/workspace_client.py` (NEW) | Mirrors `cm_client.py:1-229` shape: `_workspace_get` (single network seam), `call_with_retry`, cache I/O (`load_cache`, `write_cache`, `gc_cache_orphans`), response adapters (`format_calendar_event_for_log`, `format_drive_file_for_log`). Errors: `WorkspaceTransportError`, `WorkspaceRpcError` (mirror CM error class hierarchy). |
| Event tuple builders | `scripts/lib/vault_writer.py` (NEW helpers, near lines 549-589 where Phase 11 placed `_cm_contract_event_tuple`) | `_cal_meeting_event_tuple(event, attendee_clients)`, `_drive_doc_event_tuple(file)`. Returns the same 5-tuple shape used everywhere: `(ts_iso, kind, summary, detail, gmail_thread_id_or_none)`. `gmail_thread_id` is None for both new kinds. |
| Routing helpers | `scripts/lib/vault_writer.py` (NEW) | `_attendee_emails_to_slug(attendees, clients)` — D-A2 strict-domain match, returns first match (alphabetical) or `"_Unknown"`. `_drive_folder_to_slug(folder_name, clients)` — D-A4 case-insensitive longest-substring, mirrors `_clientid_to_slug:1536`. |
| Privacy filter | `scripts/lib/workspace_client.py` (NEW, inside the response adapter) | Three-stage filter: (1) D-D1 — events without external attendees skipped, (2) D-D2 — events with >25 attendees skipped, (3) D-D3 — Drive files with `name.endswith('.gdraft')` or `'[DRAFT]' in name` skipped. Per-skip counters returned alongside event/file lists. |
| `_gather_events` extension | `scripts/lib/vault_writer.py:864-950` (extend) | Add `cal_data=None, drive_data=None` kwargs (same additive shape Phase 11 used for `cm_expiring`, `cm_invoices`). Phase 11 callers stay byte-identical. |
| `EMOJI_BY_KIND` extension | `scripts/lib/vault_writer.py:49` (extend) | `{"triage": "📧", "task": "✅", "invoice": "💰", "contract": "📄", "meeting": "📅", "doc": "📝"}`. **Single-line edit; preserves Phase 11 four kinds in original order.** |
| Test scaffolding | `scripts/tests/test_vault_writer.py:445+` (extend); `scripts/tests/test_workspace_client.py` (NEW) | Mirror Phase 11: `TestCalendarFetch`, `TestDriveFetch`, `TestPrivacyFilters`, `TestActivityLogMergePhase12`, `TestProjectionDoesNotImportWorkspace` (subprocess), `TestWorkspaceCacheFallbackEnd2End`, `TestBackfillIdempotentPhase12`. |

### Recommended Project Structure
```
scripts/
├── lib/
│   ├── vault_writer.py        # Phase 10/11/12 orchestrator (extend in place)
│   ├── cm_client.py           # Phase 11 (UNCHANGED)
│   └── workspace_client.py    # Phase 12 NEW — mirrors cm_client.py shape
├── tests/
│   ├── test_vault_writer.py   # Extend with Phase 12 test classes
│   ├── test_cm_client.py      # Phase 11 (UNCHANGED)
│   └── test_workspace_client.py  # Phase 12 NEW — mocks urllib.request.urlopen
├── sync-obsidian.sh           # Extend with GOOGLE_MCP_CREDENTIALS_DIR validation
└── requirements.txt           # Phase 12 may need google-api-python-client OR stay urllib-only
data/
├── .cm-cache.json             # Phase 11 (gitignored)
├── .cal-cache.json            # Phase 12 NEW (gitignored — extend .gitignore)
└── .drive-cache.json          # Phase 12 NEW (gitignored)
```

### Pattern 1: Single-Network-Seam (mirrored from Phase 11 `cm_client.py`)
**What:** All external HTTP calls go through one function (`_workspace_get`); tests mock that function, never `urllib.request.urlopen` directly.
**When to use:** Always — Phase 11 established this and Phase 12 must mirror to keep test patterns consistent.
**Example:**
```python
# Source: scripts/lib/cm_client.py:50-111 — Phase 11 verified pattern

def _workspace_get(api_path: str, params: dict, access_token: str) -> dict:
    """Single network seam for Calendar v3 + Drive v3.

    Test seam: tests patch `scripts.lib.workspace_client._workspace_get`,
    NEVER `urllib.request.urlopen`. Mirrors cm_client.py:50-111.
    """
    url = f"https://www.googleapis.com/{api_path}"
    if params:
        from urllib.parse import urlencode
        url += "?" + urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry_after = int(e.headers.get("Retry-After", "30"))
            raise WorkspaceRateLimitError(retry_after) from e
        raise WorkspaceTransportError(f"HTTP {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise WorkspaceTransportError(f"network: {e.reason}") from e
```
[CITED: Phase 11 cm_client.py — same shape, exhaustively proven via 17 mocked tests in commit `1b1e904`]

### Pattern 2: Retry + Cache Fallback + Warning Feed (mirrored from Phase 11 D-A3)
**What:** Wrap each tool in try/except. On exhaustion (3 retries), read from per-tool cache file. On cache miss, leave bucket empty + emit `level: warning` feed entry. Stamp staleness timestamp on first fallback.
**When to use:** Always for external data Phase 12 reads. Inherited verbatim from Phase 11; Phase 12 just adds two more buckets to the same `_fetch_*_data_for_run` shape.
**Example:**
```python
# Source: scripts/lib/vault_writer.py:1238-1260 — Phase 11 verified pattern
# Adapted for Calendar:

try:
    cal_result = call_with_retry(
        "calendar/v3/calendars/primary/events",
        {"timeMin": ninety_days_ago, "timeMax": thirty_days_ahead, "maxResults": 250},
        access_token,
    )
    cache["global"]["calendar_events"] = {
        "fetched_at": now_ts, "lookback_days": 90, "result": cal_result,
    }
    out["global_calendar"] = cal_result
except (WorkspaceTransportError, WorkspaceRpcError) as e:
    _warn(f"Workspace stale (calendar/events): {type(e).__name__}",
          {"tool": "calendar.events", "error": str(e)})
    cached = cache.get("global", {}).get("calendar_events", {}).get("result")
    out["global_calendar"] = cached  # may be None if no cache
```

### Pattern 3: Lazy Import Discipline (mirrored from Phase 11 Pitfall 1)
**What:** `workspace_client` is imported INSIDE `_fetch_external_data_for_run`, never at module top. Mac daemon's `run_projection` (which never calls this helper) keeps `workspace_client` out of `sys.modules`.
**When to use:** Always for any module touching external networks that the Mac daemon must not pull in.
**Example:**
```python
# Source: scripts/lib/vault_writer.py:1208-1214 — Phase 11 verified pattern

def _fetch_external_data_for_run(data_root, clients, feed_path) -> dict:
    # Graceful skip checks first (no imports happen)
    if not _should_fetch_workspace_data():
        return _empty_workspace_buckets(clients)

    # Lazy import — keeps Mac daemon clean
    from .workspace_client import (
        call_with_retry, load_cache, write_cache, gc_cache_orphans,
        format_calendar_event_for_log, format_drive_file_for_log,
        WorkspaceTransportError, WorkspaceRpcError,
    )
    # ... rest of function
```

### Pattern 4: Snapshot-Strip Idempotency (mirrored from Phase 11 D-14/D-16)
**What:** Two consecutive backfills with frozen mocked responses produce byte-identical managed-section content modulo per-run trust signals (`last_synced`, `cm_data_stale_since`, and Phase 12's new `workspace_data_stale_since` if applicable).
**When to use:** D-14/D-16 verification anchor 5 mandates this for Phase 12.
**Example:** Extend `TestBackfillIdempotent._snapshot_managed` to also strip a `workspace_data_stale_since:` line if Phase 12 introduces one. **Recommendation: do NOT introduce a new staleness key; reuse `cm_data_stale_since` as a generic external-data staleness signal, OR rename it now to `external_data_stale_since`** — but that's a frontmatter rename which is a Phase 12 scope expansion. Safer: introduce `workspace_data_stale_since` and update the snapshot helper.

### Anti-Patterns to Avoid
- **Hand-rolling Drive recursive walk inside vault_writer.py.** Drive API supports recursive listing via `parents in [...]` queries; making N round-trips per client (~34 × ~3 levels = ~100 calls) is wasteful. **Use a single query per client subfolder with `q="'<folder_id>' in parents and trashed=false and mimeType != 'application/vnd.google-apps.folder'", orderBy="modifiedTime desc", pageSize=20`**.
- **Calling MCP tools from the planner-recommended `workspace_client.py`.** The hardened-workspace MCP is stdio-only; Python can't reach it via urllib. Either (a) call Google APIs directly with the same OAuth blob (recommended), or (b) escalate the architectural choice back to Glen.
- **Importing `workspace_client` at module top of `vault_writer.py`.** Breaks Pitfall 1 inheritance. Mac daemon would pull network-touching code into `sys.modules` even when it never calls it.
- **Sharing the cache across phases (single `data/.workspace-cache.json`).** Mixes CM cache schema (different from Calendar/Drive cache schema) with Workspace cache; one corruption taints both. **Per-tool cache files.**
- **Adding `last_meeting_at` / `recent_doc_count` frontmatter keys.** D-C4 forbids this; the planner must not "improve" the spec.
- **Reusing 📄 for Drive docs.** D-C3 reserves 📄 for contracts; verifier anchor 4 explicitly checks for leakage.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth Bearer token refresh | Custom refresh logic from `refresh_token` | `google-auth`'s `Credentials.refresh(Request())` OR (if staying urllib-only) `urllib.request.urlopen` POST to `https://oauth2.googleapis.com/token` | Refresh logic involves clock skew tolerance, timeout retries, and edge cases around expired-but-valid refresh tokens. Google's library handles them; urllib path is a documented 30-line snippet from Google's official quickstart. |
| RFC3339 timestamp formatting for `timeMin`/`timeMax` | Custom strftime patterns | `datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')` (already used in `gcalendar/calendar_tools.py:391-392`) | The Calendar API rejects timestamps without TZ; rejects ones with non-Z suffix in some endpoints. The Z-suffix idiom is documented and tested. |
| Drive folder hierarchy traversal | Recursive Python walker that issues N `list_drive_items` calls | Single API call per client subfolder using `q="'<folder_id>' in parents and trashed=false"` with `orderBy="modifiedTime desc", pageSize=20` | One round-trip per client = 34 calls/backfill. The recursive walker would be ~100+ calls. The query language already supports the recursion. |
| Pagination across `nextPageToken` | Manual loop reconstruction | Phase 11 D-B2 caps at 20 — single page suffices for both Calendar (90d × 5/day = 450 events fits in `maxResults=250` × 2 pages) and Drive (top-20 fits in one page). **No pagination needed if you respect D-B1/D-B2.** | Pagination introduces edge cases (tokens that expire, tokens that reorder); not needed at our volume. |
| Filename hashing for cache keys | Custom hash | `data/.cal-cache.json` keyed by `client_domain` (mirroring `data/.cm-cache.json:by_client`) | Phase 11 already proved this shape works. Use it verbatim. |
| Atomic JSON write | New tempfile+rename code | `vault_writer._atomic_write` already exists at `scripts/lib/vault_writer.py:325-351` and is reused by `cm_client.py:164` | The dir-fsync + tempfile pattern is hard to get right; reuse it via the same import idiom `from .vault_writer import _atomic_write`. |
| Email domain extraction | Custom regex | `attendee_email.split("@", 1)[1].strip().lower()` — same idiom Phase 10 uses at `vault_writer.py:837-839` for `_Unknown.md` grouping | Already battle-tested in production for ~2 months of triage data. |
| Modifier display name fallback | Custom fallback chain | `lastModifyingUser.get("displayName") or lastModifyingUser.get("emailAddress", "").split("@", 1)[0] or "unknown"` | Same one-liner pattern Phase 10 uses for `from` field fallback. |

**Key insight:** Phase 12's "build" is mostly **gluing existing patterns**. The only new code that's genuinely original is the privacy-filter logic in `workspace_client.py` (D-D1/D-D2/D-D3) and the OAuth token-loading helper. Both are <50 lines.

## Runtime State Inventory

This is an additive feature phase, NOT a rename/refactor. The Runtime State Inventory section is technically optional. However, two stored-state items DO need explicit handling:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 12 produces no persistent records in `data/` beyond two new gitignored cache files | Plan adds `.cal-cache.json` + `.drive-cache.json` to `.gitignore` (Wave 0 task) |
| Live service config | hardened-workspace MCP credentials live at `~/.google_workspace_mcp/credentials/` (NOT in git) on Glen's Mac AND must exist at the same path on Coolify for Phase 12's direct-API approach to work | Glen-action: copy Mac credentials to Coolify OR mint fresh OAuth on Coolify |
| OS-registered state | None — no Windows tasks, no launchd plists, no systemd units introduced by Phase 12 | None |
| Secrets/env vars | NEW: `GOOGLE_MCP_CREDENTIALS_DIR` env var (or implicit default `~/.google_workspace_mcp/credentials`); `CONTRACT_MANAGER_API_KEY` (Phase 11 — UNCHANGED) | sync-obsidian.sh validation extension; Coolify env var injection |
| Build artifacts / installed packages | If google-api-python-client path chosen, `pip install` adds ~25 transitive deps to Coolify Python env. If urllib-only path chosen (recommended), zero new packages | Update `scripts/requirements.txt` only if going non-stdlib |

## Common Pitfalls

### Pitfall 1: Mac daemon imports `workspace_client` (extends Phase 11 Pitfall 1)
**What goes wrong:** Phase 11's T-11-04-01 invariant (Mac never imports `cm_client`) extends to Phase 12 verbatim — Mac never imports `workspace_client`. If a future contributor adds a top-of-module `from .workspace_client import ...` to `vault_writer.py`, the Mac daemon's `run_projection` will pull HTTP code, OAuth credentials, and network paths into `sys.modules`, producing log noise and (worse) attempting actual API calls if env vars happen to be present.
**Why it happens:** Two new modules (`workspace_client.py`) tempts a contributor to "tidy up" the lazy-import block in `_fetch_external_data_for_run` by hoisting it.
**How to avoid:** Subprocess-based negative test analogous to `TestProjectionDoesNotImportCm`. Test class `TestProjectionDoesNotImportWorkspace` spawns a fresh Python and asserts `scripts.lib.workspace_client not in sys.modules` after `run_projection()` returns. Verified in subprocess (not in-process — see Pitfall 1 reasoning in Phase 11 SUMMARY commit `1b1e904`).
**Warning signs:** `grep "^from .workspace_client" scripts/lib/vault_writer.py` returns more than 0. Mac daemon log shows URLError or FileNotFoundError for OAuth token files. Consult Phase 11 commit `1b1e904` test_projection_does_not_import_cm pattern.

### Pitfall 2: hardened-workspace MCP returns formatted text, not JSON
**What goes wrong:** A contributor sees `mcp__hardened-workspace__get_events` listed in CONTEXT.md `<canonical_refs>` and assumes Phase 12's Python code can call it directly. The MCP is **stdio-only** (uvx-spawned local subprocess), and even if the planner stands up an HTTP shim, **the response is formatted text strings**, not JSON. Parsing that text from Python would be:
- Brittle (the format changes whenever the MCP author tweaks logging)
- Unable to access fields the MCP doesn't expose (`visibility`, `lastModifyingUser`, `permissions.role`)
- Slower (round-trip text → regex → fields)

**Why it happens:** CONTEXT.md says "uses the existing hardened-workspace MCP" — verbatim true at the system level (vault data ultimately reflects the same Workspace state) but misleading at the implementation level.

**How to avoid:**
- Plan 01 EXPLICITLY chooses the Coolify-side fetch path (recommended: direct Google REST API + OAuth blob reuse).
- All Phase 12 fetch tests mock `urllib.request.urlopen` (not MCP).
- The `<canonical_refs>` reference to MCP tools is informational ("equivalent functionality is exposed by these MCP tools for Glen's interactive use"), NOT a code dependency.

**Warning signs:**
- A test imports `from mcp_*` or attempts `subprocess.run(["uv", "run", ...])` from inside vault_writer code.
- A discussion of "how to parse this MCP text output" appears in any plan.
- The planner's `<action>` block specifies a regex against `f'- "{summary}" (Starts: ...)'` patterns.

[VERIFIED: source-read of `/Users/glenr/hardened-google-workspace-mcp/gcalendar/calendar_tools.py:514-531` and `gdrive/drive_tools.py:107-115`]

### Pitfall 3: `event.visibility` not exposed by hardened MCP — D-D1 first clause unenforceable as written
**What goes wrong:** D-D1 specifies "Skip events where `visibility == 'private'` OR no external attendees." The `visibility` field is part of the Google Calendar API event resource, BUT the hardened-workspace MCP's `get_events` tool **never includes it in the formatted output** (only `summary`, `start`/`end`, `description` (in detailed mode), `location`, `attendees`, `id`, `htmlLink`). Phase 12's Python sync code that goes direct-to-API DOES get `visibility` back as a field on `events.list` results.
**Why it happens:** D-D1 was written assuming MCP-mediated access; the field truly exists in the underlying Google API but is filtered out by the MCP's text formatter.
**How to avoid:**
- If Phase 12 uses Option A (direct Google API), include `visibility` in the explicit `fields=...` query parameter (e.g., `fields=items(id,summary,start,end,attendees,visibility,htmlLink)`). D-D1 is fully enforceable.
- If Phase 12 uses Option B (MCP via Claude), D-D1's first clause is **unenforceable** and must be reformulated to attendee-only.
- Either way, the planner must verify against a real `events.list` call early (see Open Question Q4).

**Warning signs:** Test fixtures for D-D1 only construct `attendees: []` events; no test fixture sets `visibility: "private"`. If you see this in test scaffolding, the visibility branch is dead code.

### Pitfall 4: Event ID dedup is exact-match-only (analog of Phase 11 Pitfall 4)
**What goes wrong:** A calendar event scheduled across 3 client domains (`a@pca.com`, `b@iugo.com.au`, `c@otaus.com.au` attendees) would, under D-A2's first-match-wins rule, route to one client (say PCA). On the next sync, the same event ID appears again — but if Glen edited the event title or description, the `_event_tuple`'s `summary` field changes. Phase 11's invoice dedup uses `_normalize_invoice_number` (case-fold + trim only). Phase 12's calendar event dedup must use the **Google `event.id` field as the dedup key** — exact equality, no normalization.
**Why it happens:** Tempting to dedup by `(date, title)` because the title is human-readable. But Google rotates IDs only on event RECREATE; edits keep the same ID. Title-based dedup would lose the entire idempotency contract.
**How to avoid:**
- `_cal_meeting_event_tuple` carries `event["id"]` as a stable key.
- `_gather_events` Phase 12 extension dedups by event ID across runs (same shape as Phase 11's `_normalize_invoice_number` but no normalization — IDs are opaque strings).
- Pin this in a test analogous to `test_gather_events_dedup_does_not_strip_prefixes`: `test_calendar_dedup_uses_event_id_only_not_title`.

**Warning signs:** A dedup call references `event["summary"].lower().strip()`. Always wrong for calendar events.

### Pitfall 5: `_DRIVE_MAX_DEPTH = 3` recursive walk fan-out
**What goes wrong:** D-A4 promises subfolder-canonical matching but doesn't restrict depth, so `_DRIVE_MAX_DEPTH = 3` (per CONTEXT.md `<domain>` block) is the implicit cap. A naive recursive walker that issues one `list_drive_items` per folder per level fans out to ~100+ API calls per backfill (34 clients × 3 levels). At Drive's 1000-req/100s/user limit ([CITED: developers.google.com/drive/api/guides/limits]), this is fine — but it's wasteful, slow, and hits cache-hot edge cases.
**Why it happens:** Drive doesn't expose a "list everything under this folder recursively" tool natively in `list_drive_items`; you have to either iterate or use a depth-walking query.
**How to avoid:** Use `q="'<client_folder_id>' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed=false"` per client folder. **One call per client.** This skips the recursion entirely by treating "everything inside (and inside subfolders)" as not the use case — D-B2 says top-20 by `modifiedTime`, which the Drive API natively supports via `orderBy="modifiedTime desc"` + `pageSize=20`. **The planner should challenge whether `_DRIVE_MAX_DEPTH = 3` is even needed**: if the client subfolder has nested folders (e.g., `Clients/PCA/Contracts/`, `Clients/PCA/Designs/`), the immediate-children-only listing misses everything. **Recommendation: clarify with Glen during planning whether nested Drive structure is in-scope.** [ASSUMED] — researcher does not know the actual Drive structure.

**Warning signs:**
- A plan's verification step grep counts `list_drive_items` calls and expects > 34.
- Tests fixture nested folders 3+ deep with files at every level.

### Pitfall 6: OAuth token expiry mid-backfill
**What goes wrong:** Glen's OAuth access token (1-hour validity) expires partway through a long backfill. First half of clients get current data; second half get 401 Unauthorized → cache fallback → spurious "stale" warnings.
**Why it happens:** Backfill is a single long-running operation; doesn't natively refresh.
**How to avoid:**
- `workspace_client.call_with_retry`'s 429-handling pattern is reusable: catch 401, refresh token via `urllib` POST to `https://oauth2.googleapis.com/token`, retry once.
- Token refresh BEFORE first call (zero-cost): always call `_refresh_token_if_needed()` at the top of `_fetch_external_data_for_run`'s lazy-import block. If `expires_at < now + 60s`, refresh.
- Test fixture: `test_token_refresh_on_401`.

**Warning signs:** A plan ships without any 401 handling. A backfill runs successfully on Glen's freshly-minted token but fails on Glen's hour-old token.

[CITED: Google's OAuth 2.0 token refresh docs at `https://developers.google.com/identity/protocols/oauth2`]

### Pitfall 7: First-match-wins routing is non-deterministic across clients.jsonl edits
**What goes wrong:** D-A2 says "first matching client wins, alphabetical client_domain order." Glen edits `clients.jsonl` to insert a new row near the top (alphabetically) → suddenly an event that previously routed to ATEM now routes to ACA → Activity Log on ATEM loses an entry, ACA gains one. The diff in `vault-build/Clients/*.md` makes this look like an idempotency violation.
**Why it happens:** "Alphabetical" is determined by current-time `clients.jsonl` content, not event-time content.
**How to avoid:**
- Document the rule in `_attendee_emails_to_slug` docstring: "Re-routing on `clients.jsonl` edit is INTENDED; idempotency holds modulo client registry mutations."
- Test: `test_routing_is_alphabetical_first_match_wins`. Verify on a fixture with two clients matching the same attendee; assert deterministic slug.
- Glen-facing log: emit `system`/`info` feed entry per multi-match meeting so Glen can audit retroactively.

**Warning signs:** `TestBackfillIdempotentPhase12` fails after `clients.jsonl` is reordered. Symptom is correct; the test should NOT be relaxed — the snapshot helper should NOT strip `clients.jsonl` ordering effects.

## Code Examples

### Example 1: Workspace client module skeleton (mirrors cm_client.py)

```python
# Source: scripts/lib/cm_client.py:1-50 (verified pattern from commit 1b1e904)
# Adapted for Calendar/Drive

"""Phase 12 — Google Workspace (Calendar + Drive) REST client.

Single-purpose: invoke Calendar v3 + Drive v3 REST APIs at googleapis.com via
HTTPS GET, with retry+cache-fallback per Phase 11 D-A3 pattern.

Test seam: `_workspace_get` is the only function that touches the network. Tests
patch `_workspace_get`, NOT `urllib.request.urlopen`. See test_workspace_client.py.

Cache shape: per-tool — data/.cal-cache.json + data/.drive-cache.json (D-F1 mirror).
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .vault_writer import _atomic_write, now_iso_with_offset  # noqa: F401

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
RETRY_DELAYS = (1, 5, 30)
TIMEOUT_S = 15
CACHE_SCHEMA_VERSION = 1


class WorkspaceTransportError(Exception):
    """Network failure or non-2xx HTTP status (other than 401, 429)."""


class WorkspaceRpcError(Exception):
    """Google API error response (e.g., {error: {code: 400, message: "..."}})."""


class WorkspaceRateLimitError(WorkspaceTransportError):
    def __init__(self, retry_after_seconds: int):
        super().__init__(f"rate-limited; retry after {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds


class WorkspaceAuthExpiredError(WorkspaceTransportError):
    """401 — caller should refresh token and retry once."""
```

### Example 2: Calendar event fetch (using direct Google API)

```python
# Source: gcalendar/calendar_tools.py:413-427 (verified params from MCP source)

def list_calendar_events(time_min: str, time_max: str,
                          access_token: str,
                          max_results: int = 250) -> dict:
    """Fetch events from primary calendar in the [time_min, time_max] window.

    Args:
        time_min: RFC3339 timestamp ('2026-02-02T00:00:00Z')
        time_max: RFC3339 timestamp ('2026-06-02T00:00:00Z')
        access_token: OAuth Bearer token from ~/.google_workspace_mcp/credentials/

    Returns:
        Google Calendar API response: {"items": [...], "nextPageToken": ...}
    """
    params = {
        "timeMin": time_min,
        "timeMax": time_max,
        "maxResults": max_results,
        "singleEvents": "true",
        "orderBy": "startTime",
        # Explicit fields list — get visibility (D-D1), attendees (D-A2), id (Pitfall 4)
        "fields": "items(id,summary,start,end,attendees,visibility,htmlLink),nextPageToken",
    }
    return _workspace_get("calendar/v3/calendars/primary/events", params, access_token)
```

### Example 3: Drive folder children fetch

```python
# Source: gdrive/drive_helpers.py:198-204 (verified default fields)
# Adapted to add lastModifyingUser + trashed (NOT in default fields)

def list_drive_folder_children(folder_id: str, access_token: str,
                                page_size: int = 20) -> dict:
    """Fetch top-N children of a Drive folder by modifiedTime desc, including the
    file fields D-C2 needs that the hardened MCP DOESN'T return by default."""
    q = (
        f"'{folder_id}' in parents "
        f"and trashed=false "
        f"and mimeType != 'application/vnd.google-apps.folder'"
    )
    params = {
        "q": q,
        "pageSize": page_size,
        "orderBy": "modifiedTime desc",
        # CRITICAL: explicit fields, including lastModifyingUser (NOT in MCP default)
        "fields": "files(id,name,mimeType,modifiedTime,webViewLink,lastModifyingUser),nextPageToken",
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true",
    }
    return _workspace_get("drive/v3/files", params, access_token)
```

### Example 4: Privacy filter chain

```python
# D-D1, D-D2 implementation in workspace_client.py adapter

GLEN_INTERNAL_DOMAINS = frozenset({"iugo.com.au"})

def filter_event_for_log(event: dict, primary_email: str) -> dict | None:
    """Apply D-D1, D-D2 to a raw Calendar event. Returns None if filtered out."""
    attendees = event.get("attendees", [])

    # D-D2: mass-attendee filter
    if len(attendees) > 25:
        return None

    # D-D1 part 1: visibility (only enforceable via direct Google API)
    if event.get("visibility") == "private":
        return None

    # D-D1 part 2: no-external-attendees filter
    external_attendees = [
        a for a in attendees
        if not _is_internal(a.get("email", ""), primary_email)
    ]
    if not external_attendees:
        return None

    return event


def _is_internal(email: str, primary_email: str) -> bool:
    """Internal: Glen's primary email OR @iugo.com.au domain."""
    if not email:
        return True  # missing email is treated as internal (defensive)
    if email.lower() == primary_email.lower():
        return True
    domain = email.split("@", 1)[1].lower() if "@" in email else ""
    return domain in GLEN_INTERNAL_DOMAINS
```

### Example 5: Subprocess Pitfall 1 negative test

```python
# Source: scripts/tests/test_vault_writer.py — TestProjectionDoesNotImportCm
# Adapted for Phase 12 — same shape, different module name

class TestProjectionDoesNotImportWorkspace(unittest.TestCase):
    """Pitfall 1 (extends T-11-04-01): Mac daemon's run_projection MUST NOT pull
    workspace_client into sys.modules.

    Subprocess-based: an in-process test would see workspace_client from earlier
    test classes that DO import it (TestWorkspaceCacheFallbackEnd2End,
    TestCalendarFetch). The subprocess starts fresh.
    """
    def test_projection_does_not_import_workspace_client(self):
        import subprocess, tempfile, os
        b = tempfile.mkdtemp()
        i = tempfile.mkdtemp()
        os.makedirs(b + "/Clients")
        result = subprocess.run([
            "python3", "-c", f"""
import sys
from scripts.lib.vault_writer import run_projection
from pathlib import Path
run_projection(Path({b!r}), Path({i!r}), dry_run=True)
assert "scripts.lib.workspace_client" not in sys.modules, \\
    "Mac daemon must not import workspace_client (Phase 12 Pitfall 1)"
assert "scripts.lib.cm_client" not in sys.modules, \\
    "Pitfall 1 inheritance: Mac daemon must also not import cm_client"
"""
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0,
                         f"stderr: {result.stderr}\nstdout: {result.stdout}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-source data clients (`triage_loader.py`, `task_loader.py`, etc.) | Single seam per external source (Phase 11 `cm_client.py`) | Phase 11 (May 2026) | Phase 12 inherits the single-seam pattern. Don't split into `cal_client.py` + `drive_client.py`. |
| Synchronous full-file regenerate on every sync | Same; cache layer added for failure-mode resilience (Phase 11 D-A3) | Phase 11 | Phase 12 reuses retry+cache wrapper verbatim. |
| Frontmatter as the only Activity-Log signal carrier | Activity Log entries with kind-specific emoji + detail blocks (Phase 10 D-12 + Phase 11 EMOJI_BY_KIND) | Phase 11 | Phase 12 just extends EMOJI_BY_KIND with two new kinds. No structural change. |
| `cm_data_stale_since` as the only staleness signal | TBD — Phase 12 either reuses the key (semantic broadening) or adds `workspace_data_stale_since` | Phase 12 (this phase) | Researcher recommends: **add `workspace_data_stale_since`**; broader-key rename is a scope expansion. |

**Deprecated/outdated:**
- Reading hardened-workspace MCP from Python via subprocess + stdio: never standard, never recommended; Phase 11 didn't do it for CM either.
- Treating `mcp__hardened-workspace__get_events` formatted-text output as parseable: see Pitfall 2.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `google-api-python-client` 2.150 is current | Standard Stack | Planner may pin a stale version; recommend `pip index versions google-api-python-client` at planning time |
| A2 | OAuth refresh token in `~/.google_workspace_mcp/credentials/` is the **same** OAuth blob the hardened-workspace MCP uses (i.e., reusable by Phase 12 Python code) | Architecture Patterns, Don't Hand-Roll | If the format differs (e.g., MCP stores tokens in encrypted format, or the file shape is `oauth-state.json` vs `token.json`), Phase 12 needs a separate refresh flow. Verify by reading `auth/credential_store.py` early in Plan 01. |
| A3 | Coolify Linux container has, or can have, `~/.google_workspace_mcp/credentials/` populated with the same OAuth blob Glen uses on his Mac | Runtime State Inventory | If Coolify can't host OAuth tokens, Option A is unavailable and Phase 12 must escalate to Glen for a re-discuss. |
| A4 | `event.visibility` is exposed by the Calendar API `events.list` endpoint when explicitly requested via `fields=...` | Pitfall 3 | If Google's API also strips it (unlikely — verified in [CITED: developers.google.com/calendar/api/v3/reference/events]), D-D1 first clause is unenforceable. |
| A5 | `lastModifyingUser` is exposed by the Drive API `files.list` endpoint when requested via `fields=files(lastModifyingUser)` | Code Examples #3 | If Google requires per-file `files.get` for this field, the per-client cost goes from 1 call to 21 calls (1 list + 20 gets). Probably the latter for some Workspace tiers. **Verify in Plan 01.** |
| A6 | Glen's Drive has a recognizable `Clients/` (or similar) folder hierarchy; `DRIVE_CLIENTS_ROOT` proposal is achievable | Open Question Q1 | If Drive root has no client structure, Phase 12 cannot ship without Glen migrating content. The planner must treat this as a blocking pre-condition. |
| A7 | First-match-wins multi-client routing (D-A2) yields acceptable Activity Log signal in practice | Pitfall 7 | If multiple Workspace activities span clients (which is likely for a 30-client AMS shop), Glen may want fan-out behavior. The discuss-phase deferred this to planner default; planner may want to escalate. |
| A8 | RAID/Drive concept of nested subfolders within a client folder is **not** in scope; one folder = one client; no `Clients/PCA/Contracts/` substructure expected | Pitfall 5 | If Glen organizes per-client docs into `Clients/PCA/Contracts/`, `Clients/PCA/Invoices/`, the recursive walk depth matters. **Open Question Q1** should clarify this when Glen inspects the Drive root. |
| A9 | Phase 11's `_fetch_cm_data_for_run` rename to `_fetch_external_data_for_run` does not break the existing 17 mocked tests | Architecture Pattern | Verified by inspection: the existing `__all__` exports `_fetch_cm_data_for_run`; tests import this exact symbol. **Recommendation: add `_fetch_external_data_for_run` as a new name; keep `_fetch_cm_data_for_run` as an alias for backward compat.** |

## Open Questions

These are the seven research questions from CONTEXT.md, with answers + recommendations:

### Q1. Drive structure inspection — **BLOCKED on Glen action**

**What we know:** Glen's Drive root structure is unknown to this researcher session. The hardened-workspace MCP `list_drive_items` tool would return formatted text (per Pitfall 2) when Glen runs it interactively in his Mac Claude Code session. The researcher subagent cannot invoke MCP tools directly.

**What's unclear:** Whether `Clients/` exists at My Drive root, vs `Shared drives/Agend Clients/`, vs nested under another path. Whether each client subfolder has nested structure (`PCA/Contracts/`, `PCA/Designs/`) or is flat.

**Recommendation:** Glen runs the following in his Mac Claude Code session BEFORE the planner starts Plan 01:

```
/mcp call hardened-workspace list_drive_items folder_id="root"
/mcp call hardened-workspace list_drive_items folder_id="<id_of_Clients_folder>"
```

The planner blocks on this Glen-action and writes the resulting `DRIVE_CLIENTS_ROOT` constant into Plan 01. If no obvious folder exists, the phase blocks on Glen migrating content first — this is in CONTEXT.md as the explicit pre-condition.

**Fallback if blocked indefinitely:** Phase 12 could ship Calendar-only (skip Drive entirely) as a 12.1 sub-phase, with a Phase 12.2 for Drive once the folder hierarchy is known.

### Q2. Hardened-workspace MCP `get_events` API shape

**Answer (HIGH confidence):**
- **Date range parameters:** `time_min` and `time_max` (snake_case in MCP), translated to `timeMin`/`timeMax` (camelCase) in the underlying Calendar API call. Format is **RFC3339**: e.g., `'2026-02-02T00:00:00Z'` or `'2026-02-02'` (date-only). [VERIFIED: `gcalendar/calendar_tools.py:361-362, 415`]
- **Pagination:** The MCP wraps the underlying `events.list` call without exposing `pageToken`. `max_results` is capped at the MCP-level `25` default, with no documented upper bound. **For Phase 12's direct-API path, pagination uses `pageToken` from the response's `nextPageToken` field**; we set `maxResults=250` and accept that 90 days × ~5 events/day = ~450 events fits in 2 pages. [CITED: Calendar v3 docs at `https://developers.google.com/calendar/api/v3/reference/events/list`]
- **Attendee response shape:** `[{email, responseStatus, optional, organizer, displayName?}]`. The MCP truncates this to `email: responseStatus` text; the underlying API exposes the full dict. [VERIFIED: `gcalendar/calendar_tools.py:175-211`]

### Q3. Hardened-workspace MCP rate limits

**Answer (HIGH confidence):**
- **Calendar v3 quota:** 1,000,000 queries per day per project, 500 queries per 100 seconds per user. [CITED: `https://developers.google.com/calendar/api/guides/quota`]
- **Drive v3 quota:** 1,000,000,000 queries per day per project, 1,000 queries per 100 seconds per user. [CITED: `https://developers.google.com/drive/api/guides/limits`]
- **Phase 12 budget:** 90 days × 1 calendar = 1 call. Drive: 34 clients × 1 call (folder list with `pageSize=20`) = 34 calls. **Total: 35 calls per backfill.** Far below limits.
- **Recommendation:** No batching needed. Single sequential calls per client, with `Retry-After` honor on 429. Rate limit handling reuses Phase 11 `CmRateLimitError` shape (rename to `WorkspaceRateLimitError`).

### Q4. `event.visibility` field availability

**Answer (HIGH confidence with caveat):**
- **Underlying Calendar v3 API:** `visibility` field is part of the event resource, with values `default`, `public`, `private`, `confidential`. [VERIFIED: `gcalendar/calendar_tools.py:144` enum + Google docs]
- **hardened-workspace MCP:** The formatted text output of `get_events` does **NOT** include `visibility` in the rendered event line (verified by reading the formatter at `gcalendar/calendar_tools.py:514-531`). It exists only in `create_event`/`modify_event` as an input parameter.
- **Implication for D-D1:** D-D1's first clause (`visibility == "private"`) is enforceable only if Phase 12 goes direct-API (Option A). If Phase 12 uses the MCP via Claude (Option B), only the second clause (no-external-attendees) is enforceable — this is a **strict reduction in privacy filtering** and Glen should be informed during planning.
- **Recommendation:** Plan with Option A. Make `fields=items(...,visibility,...)` explicit in the `events.list` call.

### Q5. `lastModifyingUser` availability on Drive list response

**Answer (HIGH confidence):**
- **Default `files.list` fields:** `id, name, mimeType, webViewLink, iconLink, modifiedTime, size` — does **NOT** include `lastModifyingUser`. [VERIFIED: `drive_helpers.py:201`]
- **Adding `lastModifyingUser`:** Append `lastModifyingUser` to the explicit `fields=files(...)` parameter. The underlying Drive v3 API supports this on the list endpoint. [CITED: `https://developers.google.com/drive/api/v3/reference/files/list`]
- **No additional API call needed.** Phase 12 does NOT need per-file `files.get` calls. (This was the most expensive worry from CONTEXT.md Q5.)
- **Recommendation:** Set `fields=files(id,name,mimeType,modifiedTime,webViewLink,lastModifyingUser),nextPageToken` in the Drive list call. Single round-trip per client folder.

### Q6. Cache file naming — separated vs unified

**Recommendation: SEPARATED — `data/.cal-cache.json` + `data/.drive-cache.json`.**

| Aspect | Separated (recommended) | Unified |
|--------|-------------------------|---------|
| Mirror Phase 11 pattern | ✓ Identical to `data/.cm-cache.json` shape | ✗ Diverges; future phase 13 might be confused |
| Diagnostics | ✓ `cat data/.cal-cache.json \| jq '.global'` is targeted | ✗ Need `jq '.calendar.global'` |
| Corruption isolation | ✓ Corrupt cal cache doesn't kill Drive fallback | ✗ Single corruption kills both |
| Atomicity | ✓ Each tempfile-rename is independent | ✓ Single rename (slightly faster) |
| `.gitignore` lines | 2 | 1 |
| Schema version evolution | ✓ Per-tool bumps don't affect each other | ✗ Schema bump invalidates both |
| Test fixtures | ✓ Tests can mock cal cache without seeding drive | ✗ Tests must seed both even when only one is exercised |

**Trade-off:** One extra `.gitignore` entry. Worth it.

### Q7. Cross-phase test interaction — `TestProjectionDoesNotImportWorkspace` is reusable

**Answer (HIGH confidence):**
- The Phase 11 `TestProjectionDoesNotImportCm` pattern (subprocess + assertion that `scripts.lib.cm_client not in sys.modules`) is fully reusable. Copy the test class verbatim, change `cm_client` → `workspace_client` and the test name. The subprocess invocation is necessary because in-process tests would see `workspace_client` already imported from earlier `TestCalendarFetch` / `TestDriveFetch` tests.
- **Recommendation:** Add this test in Wave 0 alongside the empty-`workspace_client.py` stub, so the invariant is enforced from day one (TDD RED → ImportError on missing module → GREEN once stub exists).

## Suggested Wave Structure

Phase 11 had 4 plans across 4 waves; Phase 12 fits the same shape. **Recommended structure:**

| Wave | Plan | Title | Tasks |
|------|------|-------|-------|
| 0 | 12-01 | Wave 0 — Cache plumbing + workspace_client stub | (1) Extend `.gitignore` with `data/.cal-cache.json` + `data/.drive-cache.json`. (2) Create empty `scripts/lib/workspace_client.py` stub with `WorkspaceTransportError`/`WorkspaceRpcError`/`WorkspaceRateLimitError` classes + `_workspace_get` skeleton (raises NotImplementedError). (3) Glen-action checkpoint: confirm `DRIVE_CLIENTS_ROOT` from Q1 inspection. (4) Add `EMOJI_BY_KIND["meeting"] = "📅"` and `EMOJI_BY_KIND["doc"] = "📝"`. (5) Wire `TestProjectionDoesNotImportWorkspace` (will pass immediately on stub). |
| 1 | 12-02 | Wave 1 — `workspace_client.py` + RED tests | TDD: RED test for `_workspace_get` (urllib mock), `call_with_retry`, `load_cache` / `write_cache` / `gc_cache_orphans`, `format_calendar_event_for_log`, `format_drive_file_for_log`, OAuth token loader from `~/.google_workspace_mcp/credentials/`. GREEN: implement each (mostly copy-paste from `cm_client.py`, swap JSON-RPC envelope for plain GET). |
| 2 | 12-03 | Wave 2 — `_gather_events` extension + event tuple builders | (TDD) Add `_cal_meeting_event_tuple`, `_drive_doc_event_tuple`, `_attendee_emails_to_slug`, `_drive_folder_to_slug`. Extend `_gather_events` with `cal_data=None, drive_data=None` kwargs. Add tests `TestGatherEventsCalIntegration`, `TestGatherEventsDriveIntegration`, `TestPrivacyFilters`. |
| 3 | 12-04 | Wave 3 — `_fetch_external_data_for_run` extension + idempotency tests | (TDD) Rename Phase 11's `_fetch_cm_data_for_run` to `_fetch_external_data_for_run` (keeping a backward-compat alias). Add Calendar + Drive blocks alongside CM. `run_backfill` threads cal + drive data into `_gather_events`. Add `TestWorkspaceCacheFallbackEnd2End`, `TestBackfillIdempotentPhase12` (extends snapshot-strip with `workspace_data_stale_since`). Final integration test: full backfill against frozen mocked Calendar + Drive responses produces byte-identical output across two runs. |

**Optional Wave 4 (12-05):** Glen-action verification on Coolify — same shape as Phase 11's deferred Task 3. SSH to Coolify, run `bash scripts/sync-obsidian.sh --backfill`, inspect a regenerated note for 📅 + 📝 entries, push, verify on iPhone Obsidian. Auto-approve per AUTO_MODE if Glen prefers.

**Why 4 plans, not 3 or 5:**
- 3 plans would force Wave 0 setup + Wave 1 client to share a plan, breaking the Phase 11 RED→GREEN per-plan rhythm.
- 5+ plans would split `_fetch_external_data_for_run` across multiple plans, fracturing the cache-fallback semantics that must be tested as one unit.

## Test Surface

**Mirror Phase 11 test classes verbatim.** Phase 11 has these existing test classes (74 tests total in `test_vault_writer.py` + 11 in `test_cm_client.py`):

| Phase 11 Class | Phase 12 Analog | Mocking Strategy |
|----------------|-----------------|------------------|
| `TestCmClient` (in `test_cm_client.py`) | `TestWorkspaceClient` (in `test_workspace_client.py`, NEW) | Mock `urllib.request.urlopen`; verify Bearer header, RFC3339 formatting, query-string encoding |
| `TestRunMapCmClients` | `TestRunWorkspaceTokenRefresh` | Mock `urllib.request.urlopen` for token refresh endpoint; verify atomic write of refreshed token blob |
| `TestRenderFrontmatterPhase11` | None — D-C4 forbids new frontmatter | n/a |
| `TestCmTodosSection` | None — D-C4 forbids new managed sections | n/a |
| `TestUsageSection` | None — same as above | n/a |
| `TestGatherEventsCmIntegration` | `TestGatherEventsCalIntegration` + `TestGatherEventsDriveIntegration` | Mock `_workspace_get` to return canned `events.list` / `files.list` JSON; verify routing, dedup by event ID / file ID, multi-client first-match-wins |
| `TestContractMerge` | `TestMeetingMerge` + `TestDocMerge` | Verify `render_log_line(kind="meeting")` produces 📅 with the D-C1 line shape; same for "doc" + 📝 |
| `TestProjectionDoesNotImportCm` | `TestProjectionDoesNotImportWorkspace` (subprocess) | Verbatim copy with module name swap |
| `TestCacheFallbackEnd2End` | `TestWorkspaceCacheFallbackEnd2End` | Mock `_workspace_get` to raise `WorkspaceTransportError`; assert cache hit + `workspace_data_stale_since` stamped + warning feed entry written |
| `TestBackfillIdempotentPhase11` | `TestBackfillIdempotentPhase12` | Extend `_snapshot_managed` to also strip `workspace_data_stale_since:` lines |
| `TestJitMapping` | None — Phase 12 should NOT auto-create clients.jsonl rows from Workspace data (different trust boundary) | n/a |

**New test classes specific to Phase 12 (no Phase 11 analog):**

| New Class | Purpose | Mocking Strategy |
|-----------|---------|------------------|
| `TestPrivacyFilters` | D-D1 / D-D2 / D-D3 enforcement | Construct event/file dict fixtures; assert filter chain returns None on personal/mass/trash |
| `TestAttendeeRouting` | D-A2 strict-domain matching + first-match-wins multi-client | Construct fixtures with attendees spanning multiple client domains in `clients.jsonl`; assert deterministic alphabetical first-match |
| `TestDriveFolderRouting` | D-A4 case-insensitive longest-substring matching | Construct fixtures where folder name matches multiple aliases of different clients; assert longest-substring wins |
| `TestOAuthTokenLoader` | Reads `~/.google_workspace_mcp/credentials/` token blob | Mock filesystem; verify expiry-check + refresh trigger |
| `TestNonExternalEventsSkipped` | Pinning the no-external-attendees rule end-to-end | One event with all-internal attendees, one with one external; assert only the latter routes |
| `TestEventIdDedupNotTitleDedup` | Pitfall 4 invariant | Two events with same ID, different titles; assert only one routes |

**Total Phase 12 tests added:** ~25-30 test methods. Phase 11 added 17 (74 → 91 will be the post-Phase-12 baseline).

**Wave 0 gaps:** None — `scripts/tests/test_vault_writer.py` and `scripts/tests/test_cm_client.py` already exist; `scripts/tests/test_workspace_client.py` is the only new file. No framework install needed (unittest is stdlib).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` (Python stdlib) — same as Phase 10/11 |
| Config file | none (Python stdlib `unittest.TestLoader.discover`) |
| Quick run command | `python3 -m unittest scripts.tests.test_workspace_client -v` |
| Full suite command | `python3 -m unittest discover scripts/tests` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTL-01-CAL | 📅 calendar entries appear in Activity Log within 90-day window with correct shape | unit | `python3 -m unittest scripts.tests.test_vault_writer.TestGatherEventsCalIntegration -v` | ❌ Wave 2 |
| INTL-01-CAL | First-match-wins multi-client routing is deterministic | unit | `python3 -m unittest scripts.tests.test_vault_writer.TestAttendeeRouting -v` | ❌ Wave 2 |
| INTL-01-DRIVE | 📝 Drive entries appear, top-20 by modifiedTime, with modifier name | unit | `python3 -m unittest scripts.tests.test_vault_writer.TestGatherEventsDriveIntegration -v` | ❌ Wave 2 |
| INTL-01-DRIVE | Drive folder→slug routing uses longest-substring | unit | `python3 -m unittest scripts.tests.test_vault_writer.TestDriveFolderRouting -v` | ❌ Wave 2 |
| INTL-01-PRIVACY | All three filter clauses (D-D1/D-D2/D-D3) work | unit | `python3 -m unittest scripts.tests.test_vault_writer.TestPrivacyFilters -v` | ❌ Wave 2 |
| INTL-01-WORKSPACE-CACHE | Retry + cache fallback + warning emission | integration | `python3 -m unittest scripts.tests.test_vault_writer.TestWorkspaceCacheFallbackEnd2End -v` | ❌ Wave 3 |
| INTL-01-PROJECTION-ISOLATION | Mac daemon never imports workspace_client | unit (subprocess) | `python3 -m unittest scripts.tests.test_vault_writer.TestProjectionDoesNotImportWorkspace -v` | ❌ Wave 0 |
| Verification anchor 5 (D-14/D-16) | Two backfills byte-identical | integration | `python3 -m unittest scripts.tests.test_vault_writer.TestBackfillIdempotentPhase12 -v` | ❌ Wave 3 |
| Verification anchor 6 (cache gitignored) | `data/.cal-cache.json` and `data/.drive-cache.json` are gitignored | smoke | `git check-ignore data/.cal-cache.json data/.drive-cache.json` | ❌ Wave 0 |
| Verification anchor 4 (📄 contract-only) | No Drive entries leak into 📄 | smoke | `grep "📄" vault-build/Clients/*.md \| grep -v "Contract"` returns empty | manual at Wave 4 |

### Sampling Rate
- **Per task commit:** Quick run on the test class affected by the task (`python3 -m unittest scripts.tests.test_vault_writer.TestX -v`).
- **Per wave merge:** Full suite (`python3 -m unittest discover scripts/tests`).
- **Phase gate:** Full suite green + Glen's iPhone visual verification (deferrable per AUTO_MODE per Phase 11 precedent).

### Wave 0 Gaps
- [ ] `scripts/lib/workspace_client.py` — empty stub with error classes (created in 12-01)
- [ ] `scripts/tests/test_workspace_client.py` — new file (created in 12-02)
- [ ] `.gitignore` — add 2 lines for cache files (Wave 0 task in 12-01)
- [ ] `EMOJI_BY_KIND` dict — extended with 2 entries (Wave 0 task in 12-01)
- [ ] `TestProjectionDoesNotImportWorkspace` — RED test in 12-01, becomes GREEN immediately on stub creation
- Framework install: none — unittest is stdlib

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | OAuth 2.0 token refresh via `oauth2.googleapis.com/token`; tokens loaded from `~/.google_workspace_mcp/credentials/` (existing trust boundary) — Phase 12 introduces NO new auth surface |
| V3 Session Management | n/a | No user sessions; backend-only |
| V4 Access Control | yes | Phase 12 reads Glen's primary calendar + Drive — same scope hardened-workspace MCP already has. **Important:** Phase 12 Python code COULD call `permissions.update`, `share_drive_file`, etc. (the hardened MCP removed these). Mitigation: keep `workspace_client.py` strictly read-only; whitelist the 2-3 endpoints used (`calendar/v3/calendars/primary/events`, `drive/v3/files`). |
| V5 Input Validation | yes | Calendar `summary` (event title) and Drive `name` (filename) are user-controlled and rendered into markdown. Risk: title contains `]` or `)` character that breaks the `[Open]({url})` link syntax. Standard control: render via `_event_tuple` which already does length truncation + `· `-joining; do not pass title verbatim into markdown without escape. |
| V6 Cryptography | yes (transitive) | TLS via `urllib.request.urlopen` (default cert validation); OAuth tokens at rest are owned by Google (file permissions = user-mode 0600 on Coolify). **Never hand-roll crypto.** |

### Known Threat Patterns for Phase 12 stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Calendar event title → markdown injection (e.g., title contains `[evil](http://attacker.com/steal)`) | Tampering / Information Disclosure | D-D4 says vault is Glen-only, so the threat reduces to "Glen taps a link he didn't expect." Standard control: render with markdown-escape (escape `]`, `(`, `)`) OR truncate to N chars. Use the same idiom Phase 10 uses for `subject` in triage events (`vault_writer.py:482`). |
| Drive filename → markdown injection | Tampering | Same as above — escape on render. |
| Attendee email → social-engineering Glen via fake `@iugo.com.au` lookalikes | Spoofing | Out of scope for Phase 12; Glen relies on Google's own anti-spoofing on the inbound side. |
| Attendee email → DoS via 1000-attendee event | DoS | D-D2 caps at 25 attendees; defended. |
| OAuth token leakage via warning feed entries | Information Disclosure | Phase 11 T-11-04-03 mitigation reused: `_warn` records only `details: {"error": str(e)}`; never includes the Bearer header. Verified by inspection of cm_client errors; same approach for workspace_client. |
| Cache poisoning to inject false events | Tampering | `data/.cal-cache.json` and `data/.drive-cache.json` are gitignored, fallback-only (live call always tries first), and contain typed fields filtered by adapters. Same shape as Phase 11 T-11-04-02. |
| Token refresh failure → indefinite stale data | DoS | Cache fallback + `workspace_data_stale_since` in frontmatter is the visible signal Glen sees. Documented warning; not a critical escalation. |
| Phase 12 Python code accidentally calling `share_drive_file` or `permissions.update` | Tampering / Privilege Escalation | Code review: `workspace_client.py` whitelists the 2-3 endpoints. CI lint: `grep -E "(permissions|sharing|share_)" scripts/lib/workspace_client.py` should return 0. |

## Sources

### Primary (HIGH confidence)
- **`/Users/glenr/work/todo-list/scripts/lib/cm_client.py`** — Phase 11 verified pattern (urllib JSON-RPC seam, retry+cache+adapters)
- **`/Users/glenr/work/todo-list/scripts/lib/vault_writer.py`** — Phase 10/11 production code; lines verified by direct read (not inference)
- **`/Users/glenr/work/todo-list/.planning/phases/11-contract-manager-integration-seed-and-refresh-client-note-fr/11-04-SUMMARY.md`** — Phase 11 final state with all threat mitigations applied
- **`/Users/glenr/hardened-google-workspace-mcp/gcalendar/calendar_tools.py`** — hardened MCP source for `list_calendars`, `get_events`; lines 304-534 verify response shape (formatted text, no `visibility`)
- **`/Users/glenr/hardened-google-workspace-mcp/gdrive/drive_tools.py`** — hardened MCP source for `search_drive_files`, `list_drive_items`; lines 386-443 verify response shape and that `lastModifyingUser` is NOT in default fields
- **`/Users/glenr/hardened-google-workspace-mcp/gdrive/drive_helpers.py:198-204`** — verifies the default `fields=` parameter in Drive listing
- **`/Users/glenr/hardened-google-workspace-mcp/auth/google_auth.py:40-55`** — verifies OAuth credentials live at `~/.google_workspace_mcp/credentials/`
- **`/Users/glenr/hardened-google-workspace-mcp/SECURITY.md:29-95`** — verifies which tools were removed from the hardened fork (relevant to Pitfall 2)
- **`/Users/glenr/work/todo-list/CLAUDE.md`** — confirms `mcp__hardened-workspace__*`-only rule
- **`/Users/glenr/work/todo-list/data/config/clients.jsonl`** — 34 clients, all with `cm_client_id` populated post-Phase 11

### Secondary (MEDIUM confidence — Google API references)
- [Calendar v3 events.list reference](https://developers.google.com/calendar/api/v3/reference/events/list) — confirms `timeMin/timeMax` semantics, `pageToken`, `fields` parameter
- [Drive v3 files.list reference](https://developers.google.com/drive/api/v3/reference/files/list) — confirms `q`, `orderBy`, `fields` parameters, `lastModifyingUser` field availability
- [Calendar API quota](https://developers.google.com/calendar/api/guides/quota) — 500 queries / 100 sec / user
- [Drive API limits](https://developers.google.com/drive/api/guides/limits) — 1000 queries / 100 sec / user
- [OAuth 2.0 refresh](https://developers.google.com/identity/protocols/oauth2) — token refresh flow

### Tertiary (LOW confidence — needs validation)
- A1, A4, A5 (assumption that `visibility` and `lastModifyingUser` are returnable via explicit `fields=` query) — needs confirmation via real API call before Plan 02 ships. Recommended: Plan 01 includes a one-time `curl` smoke test against Glen's actual calendar to confirm `visibility` is non-null on at least one private event.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `google-api-python-client` and urllib pinned by source-read of hardened MCP's pyproject.toml
- Architecture: HIGH — direct mirror of Phase 11 pattern, exhaustively proven
- Pitfalls: HIGH — Pitfall 2 is THE critical finding, source-verified by reading MCP code
- Open Questions: Q1 BLOCKED on Glen action; Q2-Q7 answered with HIGH confidence

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (30 days for stable infrastructure; the Google APIs are stable, the hardened MCP is at a recent commit, Phase 11 has stabilized)

---
*Phase: 12-calendar-and-drive-activity-enrichment-pull-client-meetings-*
*Researched: 2026-05-03*
