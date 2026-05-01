# Phase 10: Obsidian Knowledge Layer — Client Notes - Context

**Gathered:** 2026-05-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Per-client markdown knowledge base inside an Obsidian vault. Each ~30 client gets one durable note that accumulates context (status, deployed modules, contacts, contract dates, decisions, recent activity) sourced from existing `data/` NDJSON records. Backfill once from history; subsequent triage, task, and invoice events auto-append.

**In scope:**
- Client notes only (one per canonical client domain)
- Vault location, structure, and templates
- Backfill from existing `data/triage/`, `data/tasks/`, `data/invoices/`
- Sync hooks into `/triage-inbox`, `/task` completion, `/invoice` events
- Standalone `/sync-obsidian` command for manual + scheduled runs
- Mobile-readable on iPhone Obsidian via iCloud Drive

**Out of scope (deferred to later phases — see Deferred Ideas):**
- Project portfolio notes (one per AMS deployment) and weekly project review
- Daily Notes auto-population
- Bidirectional Inbox bridge (mobile capture → todos/active.jsonl)
- Auto-extraction of decisions from task outcomes
- Cross-vault search or DataView dashboards

</domain>

<decisions>
## Implementation Decisions

### Vault location & sync
- **D-01:** Vault lives at `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AgendOps`. iCloud Drive provides Mac ↔ iPhone sync via Obsidian's native iCloud support.
- **D-02:** Coolify server at 103.249.238.17 (`/opt/agend-ops`) does NOT have iCloud access. Server-side writes go to a `vault/` directory inside the repo; existing `scripts/push-and-sync.sh` already syncs server↔Mac via git. A Mac-side post-pull hook (or running `/sync-obsidian` on Mac) projects from `vault/` into the iCloud-Obsidian vault. Single direction: data → Obsidian. Glen never edits inside `vault/`.
- **D-03:** The repo's `vault/` subfolder is the working canonical (committed to git). The iCloud Obsidian vault is a synchronised projection. This keeps the data model auditable and avoids dual-write conflicts between server triage runs and Glen's manual edits on iPhone. Glen-edited sections (Overview, Decisions) are still safe because they live only in the iCloud projection until explicitly merged back.

### Client matching
- **D-04:** Canonical key = `client_domain`, resolved against `data/config/clients.jsonl`. `client_name` is display-only.
- **D-05:** Records without a resolvable `client_domain` (or with junk values like `client_name = "needs-response"`) are routed to a single `vault/Clients/_Unknown.md` note for manual review. Backfill never silently drops events.
- **D-06:** One note per canonical client. Filename = `{slug-of-display-name}.md`. Slug rules deterministic; collisions (rare given ~30 clients) resolved by appending the domain suffix.

### Note structure (per-client)
- **D-07:** Each note has a fixed section order:
  1. **YAML frontmatter** — `status`, `domain`, `deployed_modules`, `contract_start`, `contract_end`, `primary_contact`, `last_synced`
  2. **Overview** — Glen-owned, manually-edited, freeform. Sync layer NEVER overwrites.
  3. **Open Items** — reconstructed (not appended) on each sync from active tasks + active todos referencing the client.
  4. **Activity Log** — append-only dated entries from triage / tasks / invoices.
  5. **Decisions** — Glen-owned, manually-edited stub for v1 (auto-extraction deferred).
- **D-08:** Section boundaries demarcated by HTML comment markers (`<!-- ACTIVITY-LOG-START -->` / `<!-- ACTIVITY-LOG-END -->`, etc.) so the sync script can update managed sections without touching freeform sections.
- **D-09:** Frontmatter `last_synced` is updated every sync. Other properties (`status`, `deployed_modules`, etc.) are seeded by backfill from clients.jsonl + observed records but never auto-overwritten — Glen owns them after creation.

### Activity Log filter
- **D-10:** Only triage records with `priority ∈ {urgent, needs-response}` OR non-empty `action_items` hit the Activity Log. Informational/low-priority/admin emails stay in `data/triage/` but don't pollute the note.
- **D-11:** All task records that resolve to a known client log to the Activity Log (regardless of outcome). All invoice events (created/marked-paid/overdue-detected) log unconditionally.
- **D-12:** Activity Log entries follow a fixed shape: `### [YYYY-MM-DD HH:MM] {type-emoji} {one-line summary}` followed by an optional indented detail block. Type emojis: 📧 triage, ✅ task, 💰 invoice. (Adapted from the source article's GTD log convention.)

### Sync triggers
- **D-13:** Four trigger paths, all routed through a shared sync function so behaviour is identical:
  1. `/triage-inbox` — after writing the triage record, append matching entries to client notes
  2. `/task` completion — after marking task completed, append outcome to its client's note
  3. `/invoice` create / mark-paid / overdue-detection — append state-change to client's note
  4. `/sync-obsidian` — standalone command. Two modes: `--backfill` (rebuild Activity Log from scratch using full `data/` history) and `--incremental` (append since last_synced timestamp). Idempotent.
- **D-14:** Sync writes are idempotent on `(record_id, client_slug)`. Re-running incremental sync does not duplicate entries. The Activity Log section can be regenerated deterministically from `data/`.

### Backfill scope
- **D-15:** Initial backfill processes everything in `data/` end-to-end (~2 months, manageable volume). Applies the same filtering rules as incremental sync. Produces seeded notes for every canonical client; clients with no records get a stub note from `clients.jsonl` so the vault is complete from day one.
- **D-16:** Backfill is idempotent: running it twice on the same data set produces byte-identical notes (modulo `last_synced`).

### Library / runtime choice
- **D-17:** Use direct markdown file I/O for writes — NOT kepano's `obsidian-cli`. Reason: writes happen on the headless Coolify server (Obsidian app not running) and during scheduled runs. Direct file I/O removes the runtime dependency. The article's grep/awk bulk-read pattern also fits — orders of magnitude faster than per-property CLI calls. The kepano skill remains available for ad-hoc Mac-side workflows in future phases.

### Decisions section (v1)
- **D-18:** Decisions section is a manually-edited stub for v1. Glen writes them by hand. Auto-extraction from task outcomes is deferred — the signal we'd need (a `decision_summary` field on task records) doesn't exist yet, and adding it now expands scope.

### Claude's Discretion
- Exact slug generation algorithm (kebab-case, ascii-fold, etc.)
- Final YAML frontmatter property names (must be DataView-friendly for future use)
- Markdown rendering of detail blocks (code fences, callouts, indented prose)
- Whether the sync layer is a single Node/Python/Bash script or several
- Mac-side iCloud sync mechanism (fswatch watcher, git post-merge hook, or manual command)
- Concurrency handling if a triage hook and a task hook fire simultaneously (file lock vs queue)
- Internal structure of `_Unknown.md` (table per record vs subsections)
- Whether `last_synced` is per-note frontmatter or a single `data/.last-vault-sync` state file
- How `/sync-obsidian --backfill` confirms with the user before overwriting an existing Activity Log

</decisions>

<specifics>
## Specific Ideas

- The article's `### [YYYY-MM-DD]` log heading convention is the model — proven, parseable, future-friendly for Obsidian CLI integrations
- Linear/Notion aesthetic in note structure: clean frontmatter, scannable log, generous whitespace
- "Mission control per client" — when Glen taps a client note on his phone, he should see status (frontmatter), what's open right now (Open Items), and what just happened (recent Activity Log)
- Frontmatter property names should be DataView-queryable (`overdue_invoices`, `stale_since`) for a future Phase that builds an in-vault portfolio dashboard
- Don't fight Obsidian's UX: links to Gmail threads should use `mail.google.com/mail/u/0/#inbox/{thread_id}` so they open the email natively in iPhone Gmail
- The `_Unknown.md` bucket is intentionally a feature, not a bug — it surfaces triage extraction misfires (like the `client_name = "needs-response"` case found during discovery) for cleanup

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Core value, constraints (data ownership, privacy, mobile)
- `.planning/REQUIREMENTS.md` §Future Requirements / Intelligence — INTL-01 (Context accumulation) is the requirement Phase 10 fulfils. Update mapping during planning.
- `.planning/STATE.md` — Prior phase decisions and accumulated context

### Prior phase context (carry-forward decisions)
- `.planning/phases/08-interactive-dashboard/08-CONTEXT.md` D-02 — Claude as single writer pattern
- `.planning/phases/08-interactive-dashboard/08-CONTEXT.md` D-05 — Direct disk read pattern
- `.planning/phases/06-daily-task-management/06-CONTEXT.md` — Todo schema and integration model

### Data contracts (read before generating notes)
- `schemas/triage-record.json` — has `client_name`, `client_domain`, `priority`, `action_items` — drives D-10 filter
- `schemas/task-record.json` — has `client_name`, `outcome`, `task_type`, `output_dir`
- `schemas/invoice-record.json` — has client info + status transitions
- `schemas/feed-entry.json` — log format for the system's own activity feed (do not duplicate)
- `schemas/todo-record.json` — for Open Items mirror
- `data/config/clients.jsonl` — canonical client registry, source of truth for D-04 / D-06

### Existing infrastructure (reuse, don't reinvent)
- `scripts/build-dashboard-data.sh` — pattern for compiling NDJSON into derived artifacts
- `scripts/push-and-sync.sh` — Mac↔Coolify sync mechanism (must integrate with, not bypass)
- `scripts/validate-data.sh` — schema validation pattern; vault writes should validate input records before consuming them
- `.claude/commands/triage-inbox.md` — hook target for D-13 (1)
- `.claude/commands/task.md` — hook target for D-13 (2)
- `.claude/commands/invoice.md` — hook target for D-13 (3)

### External references (Obsidian ecosystem)
- https://github.com/kepano/obsidian-skills — kepano's official Obsidian Agent Skills (reference patterns for note structure even though we're not using the CLI for writes)
- https://www.mandalivia.com/obsidian/weekly-project-review-with-claude-code-and-obsidian-cli/ — source article. Adapt its log convention and bulk-read pattern; defer its triage workflow to a later phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `data/config/clients.jsonl` — already maps domain to canonical client. Authoritative for D-04. Drives the universe of notes to create during backfill (every entry gets a stub).
- Existing `client_name` + `client_domain` fields in triage / task / invoice records — backfill iterates without schema changes
- `scripts/validate-data.sh` jq-based validator — same pattern works for vault note validation
- NDJSON streaming via `jq -c` — reading triage records line-by-line is the right backfill primitive
- HTML comment markers as section delimiters — battle-tested pattern (used in many static site generators)

### Established Patterns
- Append-only files with monotonic timestamps (NDJSON) — Activity Log section mirrors this exactly
- Atomic git commit per logical operation — vault writes follow same pattern (one commit per sync run)
- Schema validation before write — proposed for vault writes too
- Coolify ↔ Mac via push-and-sync.sh — the `vault/` directory rides this rail; iCloud projection is Mac-side only

### Integration Points
- `vault/Clients/*.md` — new directory inside repo (committed)
- `vault/Clients/_Unknown.md` — fallback bucket for unmatched records
- `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AgendOps/` — Mac-side projection (NOT in repo)
- `.claude/commands/triage-inbox.md` — append vault sync step
- `.claude/commands/task.md` — append vault sync step on completion
- `.claude/commands/invoice.md` — append vault sync step on state change
- `.claude/commands/sync-obsidian.md` — NEW command file
- `data/.last-vault-sync` (or per-note frontmatter) — state file tracking last_synced timestamp

### Data quality concerns
- `task-2026-03-23-002` has `client_name: "needs-response"` (priority bucket leaked into the field). Symptom that triage's client extraction occasionally misfires. Phase 10 should NOT paper over this — the `_Unknown.md` bucket exposes it for cleanup.

</code_context>

<deferred>
## Deferred Ideas

- **Project portfolio notes** — one note per AMS module deployment with `status`/`area`/`review-cycle` frontmatter. Direct port of the source article's pattern. Future phase.
- **Weekly project review skill** — gather → present → triage → wrap workflow from the article. Builds on project notes (above).
- **Daily Notes auto-population** — append daily briefing + triage summary into `vault/Daily/YYYY-MM-DD.md`. Future phase.
- **Bidirectional Inbox bridge** — Obsidian mobile capture → `vault/Inbox/*.md` → cron pulls into `data/todos/active.jsonl`. Future phase.
- **Auto-extracted decisions** — task-executor adds optional `decision_summary` field; sync layer routes flagged tasks to the Decisions section. Future phase. v1 keeps Decisions manual-only.
- **DataView dashboard inside Obsidian** — `vault/Dashboard.md` querying frontmatter across all client notes (overdue invoices, stale clients, modules deployed by status). Add once frontmatter property design has stabilised.
- **Obsidian CLI integration** — kepano's CLI for ad-hoc Mac-side queries, mobile shortcuts, plugin development. Useful as a discoverability tool but not core to the data flow.
- **Vault git history independent of repo** — currently vault rides the repo's git. If vault grows large or needs separate access controls, fork to its own repo with Obsidian Sync.

</deferred>

---

*Phase: 10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli*
*Context gathered: 2026-05-01*
