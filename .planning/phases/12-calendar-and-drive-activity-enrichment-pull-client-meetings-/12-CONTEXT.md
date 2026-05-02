# Phase 12: Calendar + Drive Activity Enrichment - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Enrich the per-client Obsidian notes (built in Phase 10, frontmatter-extended in Phase 11) with **calendar meetings** and **Drive document activity** by pulling from Glen's Google Workspace via the existing `hardened-workspace` MCP (already authorized; no new MCP registrations). Both signals append to the **Activity Log** managed section using the established Phase 10 D-12 line shape and Phase 11 emoji discipline. No new managed body sections; no new frontmatter keys.

**In scope:**
- Live MCP read every `sync-obsidian.sh --backfill` run for both Calendar and Drive (mirrors Phase 11 D-A1 pattern)
- Calendar: pull Glen's primary calendar only, rolling 90-day window (now-90d to now+30d)
- Drive: scope inspected at research-time (Drive structure unknown today); per-client folder hierarchy is canonical match rule; top 20 docs by `modifiedTime` desc per client
- Two new EMOJI_BY_KIND entries: `meeting → 📅`, `doc → 📝` (📄 reserved for Phase 11 contracts)
- Calendar entries appended to Activity Log: `### [YYYY-MM-DD HH:MM] 📅 {title} — {N} attendees | [Open](url)`
- Drive entries appended to Activity Log: `### [YYYY-MM-DD HH:MM] 📝 {filename} — modified by {modifier} | [Open](url)`
- Privacy filters: skip events with `visibility: private` OR no external attendees; skip events with >25 attendees; skip Trash + private/draft Drive files
- Cache fallback at `data/.cal-cache.json` and `data/.drive-cache.json` (gitignored, mirrors Phase 11 cache pattern)
- Per-client try/except + warning feed entries on hardened-workspace MCP failure
- Inherits Phase 10 D-14/D-16 byte-identical regenerate-from-full guarantee

**Out of scope (deferred to later phases — see Deferred Ideas):**
- Frontmatter additions like `last_meeting_at`, `recent_doc_count` — kept Activity-Log-only per D-C4
- Client-shareable note export / vault sharing externally — separate phase if ever requested (per D-D4)
- Mass-attendee event detail (full attendee list rendering) — count only per D-C1
- Drive content extraction / summarization (we link, we don't summarize)
- Calendar/Drive write-back (vault is read-only consumer of Workspace data)
- Cross-client meeting fan-out (one meeting → multiple notes) — deferred to planner (D-A2 default: first matching client wins, log a system/info entry on multi-match)

</domain>

<locked_from_prior_phases>
## Inherited (no re-decision needed)

These are SET by Phase 10 and Phase 11. The planner MUST honor them; the discusser MUST NOT re-litigate them.

- **Phase 10 D-12 line shape**: `### [YYYY-MM-DD HH:MM] {emoji} {summary}\n> {detail}` — calendar and drive entries follow this exactly.
- **Phase 10 D-08/D-08a marker discipline**: `<!-- ACTIVITY-LOG-START -->` / `<!-- ACTIVITY-LOG-END -->` markers must be present and singular; malformed → ABORT + `level: critical` feed entry.
- **Phase 10 D-14/D-16 idempotency**: regenerate-from-full produces byte-identical content modulo `last_synced` (and Phase 11's `cm_data_stale_since`). Phase 12 MUST preserve this — calendar/drive event/doc IDs become the dedup keys.
- **Phase 10 MANAGED_SECTIONS order**: `("CM-TODOS", "OPEN-ITEMS", "USAGE", "ACTIVITY-LOG")` — Phase 12 does NOT add new sections.
- **Phase 11 EMOJI_BY_KIND**: `{"triage": "📧", "task": "✅", "invoice": "💰", "contract": "📄"}` — Phase 12 extends with `"meeting": "📅"` and `"doc": "📝"`. 📄 stays contract-only.
- **Phase 11 retry+cache fallback pattern**: 3 retries (1s/5s/30s backoff) → on exhaustion fall back to per-tool cache file → stamp staleness flag → append `level: warning` feed entry → continue sync. Phase 12 reuses this exact pattern for calendar + drive failures.
- **Phase 11 Pitfall 1 (Mac never imports cm_client)**: similar discipline — Mac's `run_projection` MUST NOT import any new hardened-workspace fetch helper. Phase 12 fetch helpers belong in `run_backfill` (Coolify-only) via lazy import. Negative test required.
- **CLAUDE.md MCP rule**: `mcp__hardened-workspace__*` ONLY. No `claude.ai Gmail` or `claude.ai Google Calendar`. Phase 12 verifier MUST grep enforce.

</locked_from_prior_phases>

<decisions>
## Implementation Decisions

### Source scope + matching (Area 1)

- **D-A1: Calendar source — primary calendar only.** Pull events from Glen's primary Google Calendar (the calendar associated with `glen@iugo.com.au`). No additional calendars (no team/shared, no subscribed). Cleanest signal; matches the Phase 2 pattern of trusting Glen's primary inbox/calendar as the canonical work surface. If Glen later wants a second calendar (e.g., a future "Agend Team" calendar), that's a config extension, not a re-discussion — add a `data/config/calendars.jsonl` mirror of clients.jsonl.

- **D-A2: Calendar matching rule — strict attendee email domain match.** A calendar event is assigned to a client if AND ONLY IF at least one attendee's email host (the `@host` portion) matches a `client_domain` in `data/config/clients.jsonl` OR any of that client's `aliases[]`. No fuzzy title matching. No fallback. Mirrors the Phase 2 email triage rule exactly. **Multi-client meeting policy (planner decision):** if attendees span multiple clients, default to first-matching-client wins (using the alphabetical client_domain order for determinism); emit a `system`/`info` feed entry per occurrence so Glen can audit. The planner may upgrade this to a multi-client fan-out if it proves needed in practice.

- **D-A3: Drive scope — research-time inspection.** Drive's actual top-level structure is unknown to this CONTEXT writer. The gsd-phase-researcher MUST inspect Glen's Drive (via `mcp__hardened-workspace__list_drive_items` at the root) and propose the canonical Clients folder path during research. Likely candidates: `/My Drive/Clients/`, `/Shared drives/Agend Clients/`. The planner produces a `DRIVE_CLIENTS_ROOT` constant from the researcher's findings. If no obvious folder exists, the researcher flags this as a blocking pre-condition (Glen creates `Clients/` and migrates content first) — Phase 12 cannot ship without a known path.

- **D-A4: Drive matching rule — folder hierarchy is canonical.** Once `DRIVE_CLIENTS_ROOT` is established, each immediate subfolder under it represents one client. Subfolder name → matched against client_domain or aliases (case-insensitive substring with longest-match preference, mirrors `_clientid_to_slug` from Phase 11). No filename-based matching. No sharing-list-based matching. Docs at the root of `DRIVE_CLIENTS_ROOT` (not in any subfolder) → silently ignored, with one info-level feed entry per sync summarizing how many were skipped.

### Time window + freshness (Area 2)

- **D-B1: Calendar window — rolling 90 days.** Pull events with `start.dateTime` between `now - 90 days` and `now + 30 days`. The forward window catches upcoming meetings (so glanceable on phone — "what's coming up with this client this month"). The backward window matches Glen's cognitive horizon for client history. Hardcoded constants in vault_writer config; no per-client override needed.

- **D-B2: Drive window — top 20 by modifiedTime, no time bound.** Per client subfolder, list every file (recursively, but bounded by `_DRIVE_MAX_DEPTH` = 3 to prevent runaway), sort by `modifiedTime` desc, take the first 20. No "must be modified within N days" filter — if a client folder has a contract from 2024 sitting there, it still appears as long as it's in the top 20 by recency. The 20-cap keeps Activity Log sections phone-readable.

- **D-B3: Cadence — every sync run, like Phase 11.** Calendar + Drive reads happen on every `sync-obsidian.sh --backfill` invocation, alongside the existing Phase 11 CM read. All three (CM, Cal, Drive) share the retry+cache+warning pattern from D-A3 of Phase 11 (now generalized). No separate cron, no daily-only cadence. Phone-glanceable means current-state-on-every-sync, not "current as of yesterday's batch".

### Activity Log shape + frontmatter (Area 3)

- **D-C1: Calendar entry format.** ```
### [YYYY-MM-DD HH:MM] 📅 {event_title} — {N} attendees
> [Open in Calendar]({htmlLink})
```
  Title is verbatim from Calendar API `summary` field (no truncation; Obsidian wraps). Attendee count is `len(event.attendees)` including organizer. `htmlLink` is the Google-provided URL. Time is local-Adelaide via the existing `now_iso_with_offset()` helper (consistent with Phase 10).

- **D-C2: Drive entry format.** ```
### [YYYY-MM-DD HH:MM] 📝 {filename} — modified by {modifier_name}
> [Open in Drive]({webViewLink})
```
  Filename is verbatim. `modifier_name` is `lastModifyingUser.displayName` (or `email_local_part` fallback if displayName missing). `webViewLink` is the Google-provided URL.

- **D-C3: EMOJI_BY_KIND extension.** Add two entries:
  ```python
  EMOJI_BY_KIND = {
      "triage":   "📧",  # Phase 2
      "task":     "✅",  # Phase 3
      "invoice":  "💰",  # Phase 7
      "contract": "📄",  # Phase 11
      "meeting":  "📅",  # Phase 12 (new)
      "doc":      "📝",  # Phase 12 (new)
  }
  ```
  📄 is RESERVED for contracts. The planner MUST NOT reuse it for Drive docs even though it semantically suggests "document" — the Phase 11 contract → 📄 mapping is locked.

- **D-C4: No new frontmatter keys.** Phase 12 writes ONLY to the Activity Log managed section. No `last_meeting_at`, no `recent_doc_count`, no `activity_counts` dict. Rationale: keeps frontmatter focused on stable client metadata (Phase 10/11 keys); avoids D-14/D-16 idempotency churn from continuously-updating timestamp fields. If DataView-driven dashboards later need these, that's a separate phase that owns the frontmatter migration as its own contract.

### Privacy filters + redaction (Area 4)

- **D-D1: Personal-event filter — visibility OR no-external-attendees.** Skip a calendar event if EITHER:
  1. Event's `visibility` field equals `"private"` (Google's explicit private-flag), OR
  2. Every attendee's email host is `iugo.com.au` (Glen's company) OR is Glen's own primary email — i.e., no external participants.
  Catches: personal events Glen marked private (gym, doctor, school runs); internal-only Iugo standup/sync meetings (which usually aren't client-relevant). Does NOT skip just because Glen is the only confirmed attendee — events with non-responding external attendees are kept (those are sales/discovery calls).

- **D-D2: Mass-attendee filter — skip events with >25 attendees.** A calendar event with `len(event.attendees) > 25` is filtered out. Catches AGMs, conferences, big webinars (e.g., "AHRI Convention 2026 — 1,200 attendees"). Threshold of 25 keeps legitimate workshops + training sessions in scope. This filter is composable with D-D1 (an event matching either rule is filtered).

- **D-D3: Drive content filter — Trash + private/draft.** Skip a Drive file if ANY of:
  - `trashed: true` (Google's deleted-but-not-purged flag)
  - `name` ends with `.gdraft` (Google Doc draft format) OR contains `[DRAFT]` token
  - `permissions.role` for everyone-except-owner is `"reader"` or restricted AND Glen is not the owner (i.e., a doc someone shared TO Glen with read-only restricted access — likely confidential).
  Each skip increments a per-sync counter; one info-level feed entry per sync summarizes ("Phase 12 Drive: 3 trashed, 1 draft, 0 restricted skipped for client X").

- **D-D4: Vault leak posture — vault is Glen-only.** No redaction logic needed. The Obsidian vault lives on iCloud (Glen-only), in the agend-ops GitHub repo (Glen-only access), and on the Coolify server (Glen-only). It is NOT a client-shareable artifact. Internal pricing, strategy notes, internal meeting titles all stay verbatim. If a future phase (e.g., "Phase 13: Client-Shareable Note Export") ever needs redaction logic, that phase owns the redaction contract — Phase 12 ships without it.

</decisions>

<deferred_ideas>
## Deferred Ideas (captured for backlog or future phases)

- **Calendar/Drive frontmatter keys** (`last_meeting_at`, `recent_doc_count`, `activity_counts: {meetings_90d, docs}`): rejected per D-C4 to keep frontmatter idempotency clean. Revisit if/when Glen wants Obsidian DataView dashboards across clients.
- **Multi-client meeting fan-out** (one meeting on multiple client notes when attendees span clients): planner default is first-match-wins per D-A2; upgrade to fan-out if Glen finds the first-match rule loses signal. Each fan-out triples Activity Log writes for that event.
- **Cross-client correlation** (e.g., "this PCA contract appeared on a Drive doc named ATEM-comparison.docx — flag overlap?"): out of scope for Phase 12; might fit a future "Phase 14: Portfolio Dashboard" or 999.1 graphify integration.
- **Calendar/Drive write-back**: out of scope. Vault is read-only consumer of Workspace data; Workspace stays canonical.
- **Drive content extraction / summarization** (Claude reads doc bodies and summarizes into the note): out of scope. Phase 12 links only. Could be a future "Phase 15: Doc Summary Pipeline" if proven valuable.
- **Per-client calendar overrides** (e.g., assign meetings from `consultant@external.io` to ATEM via aliases): handled today via clients.jsonl `aliases[]`, no new mechanism needed.
- **Client-shareable note export** (a future `--mode export-client-share` that strips internal data and produces a sanitized PDF/MD per client): out of scope; would be its own phase with its own redaction contract.

</deferred_ideas>

<canonical_refs>
## Canonical References

The planner and researcher MUST read these.

### Roadmap + planning
- `.planning/ROADMAP.md` § Phase 12 — phase goal + dependency on Phase 10/11
- `.planning/PROJECT.md` § Constraints — privacy, data ownership, hardened MCP rule
- `.planning/REQUIREMENTS.md` § INTL-01 — context accumulation requirement Phase 12 extends

### Phase 10 (vault foundations)
- `.planning/phases/10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli/10-CONTEXT.md` — D-08 marker discipline, D-12 line shape, D-14/D-16 idempotency, D-13 single-writer flock
- `.planning/phases/10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli/10-04-SUMMARY.md` (and earlier plans) — final decisions actually shipped
- `scripts/sync-obsidian.sh` — wrapper Phase 12 hooks into
- `scripts/lib/vault_writer.py` § `_gather_events`, `render_log_line`, `EMOJI_BY_KIND`, `MANAGED_SECTIONS`, `_atomic_write` — all extension points

### Phase 11 (CM integration — closest analog pattern)
- `.planning/phases/11-contract-manager-integration-seed-and-refresh-client-note-fr/11-CONTEXT.md` — D-A1 live read, D-A3 retry+cache fallback, D-G1 JIT mapping (analogous pattern for new clients found in Calendar/Drive but not in clients.jsonl)
- `.planning/phases/11-contract-manager-integration-seed-and-refresh-client-note-fr/11-04-SUMMARY.md` — `_fetch_cm_data_for_run`, `cm_data_stale_since` stamping, Pitfall 1 enforcement
- `scripts/lib/cm_client.py` — single-network-seam pattern Phase 12's `cal_client.py` and `drive_client.py` (or unified `workspace_client.py`) MUST mirror
- `scripts/tests/test_vault_writer.py` § `TestProjectionDoesNotImportCm` — Phase 12 needs the analogous negative test

### Hardened workspace MCP
- `CLAUDE.md` § "MCP Server Usage" — `mcp__hardened-workspace__*` only; never `claude.ai Gmail/Calendar`
- `mcp__hardened-workspace__list_calendars` — discovery
- `mcp__hardened-workspace__get_events` — primary read for Phase 12 calendar
- `mcp__hardened-workspace__search_drive_files` — Phase 12 drive discovery
- `mcp__hardened-workspace__list_drive_items` — folder structure walk for D-A3 research
- `mcp__hardened-workspace__get_drive_file_content` — NOT used in Phase 12 (we link, don't extract)

### Schemas
- `schemas/feed-entry.json` — `level: warning` already added in Phase 11 Plan 01; reused for Phase 12 stale-data warnings; no schema change required
- `schemas/client-config-entry.json` (if exists, else implicit in clients.jsonl shape) — Phase 12 does not modify

</canonical_refs>

<research_questions>
## Research Questions for gsd-phase-researcher

The researcher MUST resolve these before the planner runs:

1. **Drive structure** (blocks D-A3): What's at the root of Glen's Drive? Is there an existing `Clients/` folder, or do we need to migrate? Use `list_drive_items` at root, walk down 2 levels, propose `DRIVE_CLIENTS_ROOT`.
2. **Hardened-workspace MCP `get_events` API shape**: confirm date range parameter format (RFC3339? unix epoch? `timeMin`/`timeMax`?), pagination cursor semantics, attendee response shape (does it include `responseStatus`? `email`? `displayName`?).
3. **Hardened-workspace MCP rate limits**: 90 days × ~5 events/day = ~450 events per backfill from `get_events`. Plus per-client Drive reads ≈ 34 clients × ~20 docs = 680 doc metadata calls. Are rate limits a concern? What's the recommended pagination/batch strategy?
4. **`event.visibility` field availability**: confirm Google Calendar API exposes `visibility: "private"` via the hardened-workspace `get_events` response. If not, D-D1's first clause needs reformulation.
5. **`lastModifyingUser` availability on Drive files**: confirm it's in the standard `mcp__hardened-workspace__list_drive_items` response. If not, may need a per-file `get_file_metadata` call (cost increase).
6. **Cache file naming**: `data/.cal-cache.json` and `data/.drive-cache.json` (Phase 11 pattern) vs unified `data/.workspace-cache.json` (single seam). Researcher trade-off recommendation.
7. **Cross-phase test interaction**: Phase 11's `TestProjectionDoesNotImportCm` checks `cm_client` not in sys.modules. Phase 12 needs an analogous test for the new workspace client(s). Confirm test pattern reusable.

</research_questions>

<verification_anchors>
## Phase Verification Anchors (for goal-backward verifier)

Phase 12 is "shipped" when:

1. `bash scripts/sync-obsidian.sh --backfill` on Coolify completes with exit 0 AND produces `clients_written: N, events_routed: M` where M increased materially (calendar + drive entries now flow into Activity Log).
2. At least one regenerated client note has Activity Log entries with both 📅 (calendar) and 📝 (drive) line shapes per D-C1/D-C2.
3. `python3 -m unittest discover scripts/tests` passes (existing 74 + new tests for `TestCalendarFetch`, `TestDriveFetch`, `TestPrivacyFilters`, `TestActivityLogMerge`, `TestProjectionDoesNotImportWorkspace`).
4. `grep "📄" vault-build/Clients/*.md | grep -v "Contract"` returns no matches — i.e., 📄 is contract-only (no Drive entries leaked into 📄).
5. D-14/D-16 idempotency holds: two consecutive backfills with mocked frozen Workspace data produce byte-identical content (modulo `last_synced`).
6. `data/.cal-cache.json` and `data/.drive-cache.json` exist after first run AND are gitignored (extending Phase 11's `.gitignore` rule).
7. Glen visually confirms on iPhone: a recent meeting from this week renders correctly with 📅, attendee count, and Open link; a recently-modified Drive doc renders with 📝, modifier name, and Open link.

</verification_anchors>
