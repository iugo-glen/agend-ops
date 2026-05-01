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

### Vault location & sync (canonical model: iCloud, repo as transport)
- **D-01:** **iCloud Obsidian vault is canonical.** Path: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AgendOps`. This is the single source of truth Glen sees on Mac and iPhone. All user-owned content (Overview, Decisions sections) lives here exclusively.
- **D-02:** **Coolify writes server-side proposals to `vault-build/Clients/*.md` in the repo.** This is a transport layer, not a vault. `scripts/push-and-sync.sh` propagates `vault-build/` from Coolify to the always-on Mac Studio via git. The Coolify server has zero awareness of the iCloud canonical vault — it only emits proposals.
- **D-03:** **An always-on Mac Studio runs a launchd daemon that watches `vault-build/`** for incoming git pulls and applies managed-section updates to the iCloud canonical vault. User-owned sections (Overview, Decisions) in iCloud are preserved by construction — the daemon never reads them and writes only to managed sections delimited by HTML comment markers (D-08). Direction is one-way: `vault-build/` → iCloud. There is no merge-back. There is no concurrent-write risk. Mac Studio's "always-on" property eliminates the manual-trigger UX gap; scheduled Coolify triage runs reach Glen's iPhone within seconds of the daemon detecting the git pull.

### Client matching
- **D-04:** Canonical key = `client_domain`, resolved against `data/config/clients.jsonl`. `client_name` is display-only and never used for routing.
- **D-05:** **Detection rule (deterministic):** A record routes to `_Unknown.md` if `client_domain` is null/empty OR `client_domain` does not exactly match a `domain` field in `clients.jsonl`. The `client_name` field is ignored for routing — this filters out the entire bug class where priority bucket names like `"needs-response"` leak into `client_name`. Backfill never silently drops events.
- **D-06:** One note per canonical client. Filename = `{slug-of-display-name}.md` written to the iCloud vault's `Clients/` directory and to `vault-build/Clients/` in the repo (managed sections only). Slug rules deterministic; collisions (rare given ~30 clients) resolved by appending the domain suffix.
- **D-06a:** `_Unknown.md` is a single fallback note containing all unmatched records grouped by the closest available identifier (`client_name` if present, `from` email domain otherwise). Surfaces data-quality misfires for Glen's manual cleanup; it's a feature of the design, not a fallback to be hidden.

### Note structure (per-client)
- **D-07:** Each note has a fixed section order:
  1. **YAML frontmatter** (Phase 10 v1 fields): `domain`, `client_name`, `status`, `last_synced`. Phase 11 (Contract Manager) extends with `deployed_modules`, `contract_start`, `contract_end`, `primary_contact`, `sites[]`. Phase 10's planner does NOT need to populate the Phase 11 fields.
  2. **Overview** — Glen-owned, manually-edited, freeform. Sync layer NEVER reads or writes this section.
  3. **Open Items** — reconstructed (not appended) on each sync from active tasks + active todos referencing the client. Managed section.
  4. **Activity Log** — append-only dated entries from triage / tasks / invoices. Managed section.
  5. **Decisions** — Glen-owned, manually-edited stub for v1 (auto-extraction deferred to a future phase).
- **D-08:** Section boundaries demarcated by HTML comment markers (`<!-- ACTIVITY-LOG-START -->` / `<!-- ACTIVITY-LOG-END -->`, plus `OPEN-ITEMS` and `FRONTMATTER` markers). The Mac-side daemon (D-03) ONLY reads/writes content between matching marker pairs in managed sections. Content outside markers is invisible to the daemon.
- **D-08a:** **Marker error policy.** If a managed section's start or end marker is missing or malformed (plugin rewrite, accidental edit), the daemon ABORTS the update for that file, logs an error to `data/feed.jsonl` with type `system` and level `critical`, and skips the file. No silent regeneration. The note template includes a visible warning comment near each marker pair: `<!-- DO NOT EDIT BETWEEN MARKERS — managed by /sync-obsidian -->`.
- **D-09:** **Backfill sourcing for Phase 10 v1 frontmatter:**
  - `domain` ← `clients.jsonl` (entry's `domain` field)
  - `client_name` ← `clients.jsonl` (entry's `client_name`)
  - `status` ← default `"active"` for every client in `clients.jsonl`; `"unknown"` for `_Unknown.md`. Glen edits this manually thereafter; sync never overwrites once the note exists.
  - `last_synced` ← timestamp of the most recent sync run, written every time.
  Phase 11 will source `deployed_modules`, `contract_start/end`, `primary_contact`, `sites[]` from the Contract Manager MCP. Until Phase 11 ships, those fields do NOT appear in frontmatter (Phase 10 keeps the spec lean rather than populating empty placeholders).

### Activity Log filter
- **D-10:** Only triage records with `priority ∈ {urgent, needs-response}` OR non-empty `action_items` hit the Activity Log. Informational/low-priority/admin emails stay in `data/triage/` but don't pollute the note.
- **D-11:** All task records that resolve to a known client log to the Activity Log (regardless of outcome). All invoice events (created/marked-paid/overdue-detected) log unconditionally.
- **D-12:** Activity Log entries follow a fixed shape: `### [YYYY-MM-DD HH:MM] {type-emoji} {one-line summary}` followed by an optional indented detail block. Type emojis: 📧 triage, ✅ task, 💰 invoice. (Adapted from the source article's GTD log convention.)

### Sync triggers
- **D-13:** Four trigger paths, all routed through a shared sync function so behaviour is identical. All write to `vault-build/Clients/*.md` in the repo (the transport layer per D-02). The Mac Studio launchd daemon (D-03) auto-projects to the iCloud canonical vault — Glen does NOT need to run `/sync-obsidian` manually for routine updates.
  1. `/triage-inbox` — after writing the triage record, append matching entries to `vault-build/Clients/*.md`
  2. `/task` completion — after marking task completed, append outcome to the client's `vault-build/` file
  3. `/invoice` create / mark-paid / overdue-detection — append state-change to the client's `vault-build/` file
  4. `/sync-obsidian` — standalone command. Two modes: `--backfill` (rebuild every managed section from scratch using full `data/` history) and `--incremental` (append since last_synced timestamp). Idempotent. Run manually for first-time backfill or after data corrections; the daemon handles routine projection automatically.
- **D-14:** Sync writes are idempotent on `(record_id, client_slug)`. Re-running incremental sync does not duplicate entries. Activity Log + Open Items + frontmatter can be regenerated deterministically from `data/` for any client at any time.

### Backfill scope
- **D-15:** Initial backfill processes everything in `data/` end-to-end (~2 months, manageable volume). Applies the same filtering rules as incremental sync. Produces seeded notes for every canonical client; clients with no records still get a stub note so the vault is complete from day one.
- **D-15a:** **Stub note shape** (clients in `clients.jsonl` with no records in `data/`):
  - Frontmatter: `domain`, `client_name` from `clients.jsonl`; `status: "active"`; `last_synced: <timestamp>`
  - Overview section: empty markers + a single placeholder line `_No notes yet — replace this line with relationship context._`
  - Open Items: empty managed section
  - Activity Log: empty managed section with a comment `<!-- No activity logged for this client yet -->`
  - Decisions: empty managed-by-Glen section
- **D-16:** Backfill is idempotent: running it twice on the same data set produces byte-identical managed sections (modulo `last_synced`).

### Library / runtime choice
- **D-17:** Use direct markdown file I/O for writes — NOT kepano's `obsidian-cli`. Reason: writes happen on the headless Coolify server (Obsidian app not running) and the Mac Studio daemon needs to run reliably without the Obsidian app being foregrounded. Direct file I/O removes the runtime dependency. The article's grep/awk bulk-read pattern also fits — orders of magnitude faster than per-property CLI calls.
- **D-17a:** **Repo `vault-build/` is markdown-only — no `.obsidian/` config directory.** The iCloud canonical vault has its own `.obsidian/` (workspace, plugins, themes) that lives only in iCloud and is owned by Obsidian itself. Mac and iPhone share that config natively via iCloud. Putting `.obsidian/` in git would create churn (workspace state changes constantly) and force config drift between devices. `.obsidian/` is in `.gitignore` for the repo.

### Decisions section (v1)
- **D-18:** Decisions section is a manually-edited stub for v1. Glen writes them by hand. Auto-extraction from task outcomes is deferred — the signal we'd need (a `decision_summary` field on task records) doesn't exist yet, and adding it now expands scope.

### Claude's Discretion
- Exact slug generation algorithm (kebab-case, ascii-fold, etc.)
- Final YAML frontmatter property names within the v1 spec (must be DataView-friendly for future use)
- Markdown rendering of detail blocks (code fences, callouts, indented prose)
- Whether the sync layer (server-side `vault-build/` writer) is a single Node/Python/Bash script or several
- Mac Studio launchd daemon implementation details (fswatch, launchd `WatchPaths`, polling interval if any). Specification: must trigger within 30s of a git pull, must be resilient to transient iCloud unavailability.
- Concurrency handling if a triage hook and a task hook fire simultaneously on Coolify (file lock vs queue vs single-writer process)
- Internal structure of `_Unknown.md` (table per record vs subsections)
- Whether `last_synced` is per-note frontmatter or a single `data/.last-vault-sync` state file
- How `/sync-obsidian --backfill` confirms with the user before regenerating managed sections (managed sections are safe to overwrite by definition; user-owned sections are not in scope of overwrite)

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
- `vault-build/Clients/*.md` — NEW directory inside repo (committed) — server-side proposal layer, NOT a real Obsidian vault
- `vault-build/Clients/_Unknown.md` — fallback bucket for unmatched records
- `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AgendOps/Clients/*.md` — iCloud canonical vault (NOT in repo, owned by Obsidian)
- Mac Studio launchd daemon — NEW: watches `vault-build/`, projects managed-section updates to iCloud canonical
- `.claude/commands/triage-inbox.md` — append `vault-build/` write step
- `.claude/commands/task.md` — append `vault-build/` write step on completion
- `.claude/commands/invoice.md` — append `vault-build/` write step on state change
- `.claude/commands/sync-obsidian.md` — NEW command file (manual/scheduled trigger; daemon handles routine projection)
- `data/.last-vault-sync` (or per-note frontmatter) — state file tracking last_synced timestamp
- `.gitignore` — exclude `.obsidian/` (D-17a)

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
- **DataView dashboard inside Obsidian** (future phase, not yet queued) — `vault/Dashboard.md` querying frontmatter across all client notes (overdue invoices, stale clients, modules deployed by status). Earliest fit is post-Phase 11 once Contract Manager fields are populated. Add via `/gsd-add-backlog` if desired before then.
- **Obsidian CLI (kepano) ad-hoc Mac-side use** — D-17 already locks the write path to direct file I/O for reliability reasons. The kepano CLI remains available for one-off Mac-side queries, mobile shortcuts, plugin development workflows that don't touch the data pipeline.
- **Backing the canonical vault to git** — currently the iCloud vault is canonical and lives only in iCloud (Apple-managed backup). If Glen later wants explicit git history of his Overview/Decisions content, add a Mac-side daemon mode that periodically exports user-owned sections back to a `vault-archive/` git directory.

</deferred>

---

*Phase: 10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli*
*Context gathered: 2026-05-01*
