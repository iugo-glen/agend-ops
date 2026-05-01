# Phase 10: Obsidian Knowledge Layer — Client Notes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 10-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-01
**Phase:** 10-obsidian-knowledge-layer-client-notes
**Areas discussed:** Vault location, Client matching, Note structure, Sync triggers, Activity Log filter, Decisions section, Backfill scope

---

## Vault location & sync

| Option | Description | Selected |
|--------|-------------|----------|
| iCloud Drive folder | `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AgendOps`. Mac + iPhone Obsidian native sync. Coolify pushes via git or rclone. | ✓ |
| Inside the repo (vault/ subfolder) | Committed alongside `data/`. Simplest, no extra sync layer. Mobile via Obsidian Git plugin. | partial — vault/ subfolder is the working canonical, iCloud is the Mac-side projection |
| Separate git repo + Obsidian Sync | Paid service, cleanest separation. | |
| Syncthing peer-to-peer | Self-hosted P2P sync. | |

**User's choice:** iCloud Drive folder (Recommended).
**Notes:** Resolved via D-02/D-03 to combine the picked option with the runner-up — repo `vault/` is the canonical write target, iCloud Obsidian vault is a Mac-side projection. Coolify cannot reach iCloud directly, so a Mac-side sync step closes the loop.

---

## Client matching

| Option | Description | Selected |
|--------|-------------|----------|
| `clients.jsonl` domain as canonical key | Use `client_domain` lookup. `client_name` is display only. Unmatched records go to `_Unknown.md`. | ✓ |
| `client_name` as primary, fuzzy match | Trust name first, fuzzy-match into clients.jsonl. | |
| Both — domain when present, name when not | Hierarchical: domain wins, fall back to name. | |

**User's choice:** Domain as canonical key (Recommended).
**Notes:** Glen accepted the recommendation. The discovery surfaced a real data-quality bug (`client_name = "needs-response"` in `task-2026-03-23-002`) that the chosen approach handles cleanly via the Unknown bucket.

---

## Note structure (sections)

| Option | Description | Selected |
|--------|-------------|----------|
| YAML frontmatter + auto Activity Log (baseline) | Properties + append-only dated log of triage/tasks/invoices. | ✓ |
| Manually-edited Overview/Notes section | Glen-owned freeform. Sync layer never overwrites. | ✓ |
| Decisions section | Per-client decision log. Auto-append from flagged tasks, manual for now. | ✓ |
| Open items / next actions | GTD-style mirror of active tasks/todos referencing the client. Reconstructed each sync. | ✓ |

**User's choice:** All four (multiSelect).
**Notes:** Maximalist note shape — full per-client mission control. Section boundaries enforced via HTML comment markers (D-08) so managed sections (frontmatter, Activity Log, Open Items) can be regenerated without touching freeform sections (Overview, Decisions).

---

## Sync triggers

| Option | Description | Selected |
|--------|-------------|----------|
| Hook into `/triage-inbox` | Append matching client log entries after every triage run. | ✓ |
| Hook into `/task` completion | Log task outcome to its client's note. | ✓ |
| Hook into `/invoice` events | Log invoice state changes. | ✓ |
| Standalone `/sync-obsidian` command | Manual + scheduled. Backfill and incremental modes. | ✓ |

**User's choice:** All four (multiSelect).
**Notes:** All four routed through a shared sync function (D-13) so behaviour is identical regardless of trigger. Idempotency guarantees on `(record_id, client_slug)` (D-14) make re-runs safe.

---

## Activity Log filter

| Option | Description | Selected |
|--------|-------------|----------|
| Only urgent + needs-response + has action_items | Filter at emit. Quietest, most readable timeline. | ✓ |
| Everything except low-priority | More inclusive. Captures admin/notification emails. | |
| All triage records, period | Maximalist. Most complete, least readable. | |

**User's choice:** Urgent + needs-response + has action_items (Recommended).
**Notes:** Tasks and invoices always log unconditionally — this filter only governs the email noise.

---

## Decisions section (v1)

| Option | Description | Selected |
|--------|-------------|----------|
| Manual section, Glen writes by hand | Defer auto-extraction. Lean v1. | ✓ |
| Auto-extract from task outcomes flagged decision-worthy | Add `decision_summary` field to task-record. Scope expansion. | |
| Empty stub, defer entirely | Skip the section in v1. | |

**User's choice:** Manual for v1 (Recommended).
**Notes:** Auto-extraction deferred until task-executor produces reliable signal.

---

## Backfill scope

| Option | Description | Selected |
|--------|-------------|----------|
| Everything in `data/` | ~2 months of records. Manageable. Full client history from day one. | ✓ |
| Last 90 days only | Cap backfill — useful at scale, not now. | |
| Skip backfill — only future events | Notes start empty. Loses existing context. | |

**User's choice:** Everything in `data/` (Recommended).
**Notes:** ~2 months total volume; same outcome as the 90-day option. Idempotent backfill (D-16) means re-running is safe.

---

## Claude's Discretion

- Slug generation algorithm
- Final YAML frontmatter property names (DataView-friendly)
- Markdown rendering of detail blocks
- Whether the sync layer is one script or several
- Mac-side iCloud sync mechanism (fswatch / git hook / manual)
- Concurrency handling between simultaneous triage and task hooks
- Internal structure of `_Unknown.md`
- `last_synced` storage location (per-note frontmatter vs single state file)
- Backfill confirmation prompt for `/sync-obsidian --backfill` over an existing log
- Library / runtime — locked to direct file I/O via D-17 (NOT kepano's obsidian-cli) because writes happen on the headless Coolify server

---

## Deferred Ideas (recap)

- Project portfolio notes + weekly review skill (direct port of the source article)
- Daily Notes auto-population
- Bidirectional Inbox bridge (mobile capture → todos)
- Auto-extracted decisions from task outcomes
- DataView dashboard inside Obsidian
- Obsidian CLI integration for ad-hoc Mac-side workflows
- Vault as a separate git repo with Obsidian Sync

---

*Discussion logged: 2026-05-01*
