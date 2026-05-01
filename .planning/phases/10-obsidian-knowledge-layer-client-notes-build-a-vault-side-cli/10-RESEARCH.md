# Phase 10: Obsidian Knowledge Layer — Client Notes - Research

**Researched:** 2026-05-01
**Domain:** Markdown vault projection from NDJSON history; macOS background daemon; iCloud-mediated mobile sync
**Confidence:** HIGH (decisions are locked; research fills in HOW, not WHAT)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Vault location & sync (3-tier model)**
- **D-01:** iCloud Obsidian vault is canonical at `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AgendOps`. Single source of truth Glen sees on Mac and iPhone. User-owned content (Overview, Decisions) lives here exclusively.
- **D-02:** Coolify writes server-side proposals to `vault-build/Clients/*.md` in the repo. Transport layer, not a vault. `scripts/push-and-sync.sh` propagates `vault-build/` from Coolify to the always-on Mac Studio via git.
- **D-03:** Mac Studio launchd daemon watches `vault-build/` for incoming git pulls and applies managed-section updates to the iCloud canonical vault. User-owned sections preserved by construction (daemon writes only between markers). Direction: one-way `vault-build/` → iCloud. No merge-back, no concurrent-write risk on the Mac side.

**Client matching**
- **D-04:** Canonical key = `client_domain` resolved against `data/config/clients.jsonl`. `client_name` is display-only.
- **D-05:** A record routes to `_Unknown.md` if `client_domain` is null/empty OR doesn't exactly match a `domain` in `clients.jsonl`. Backfill never silently drops events.
- **D-06:** One note per canonical client. Filename = `{slug-of-display-name}.md` in `Clients/`. Slug deterministic; collisions resolved by appending domain suffix.
- **D-06a:** `_Unknown.md` is a single fallback note grouping unmatched records. Surfaces data-quality misfires intentionally.

**Note structure**
- **D-07:** Fixed section order: (1) YAML frontmatter [v1: `domain`, `client_name`, `status`, `last_synced`]; (2) Overview (Glen-owned); (3) Open Items (managed, reconstructed); (4) Activity Log (managed, append-only); (5) Decisions (Glen-owned stub for v1).
- **D-08:** Section boundaries demarcated by HTML comment markers (`<!-- ACTIVITY-LOG-START -->` / `<!-- ACTIVITY-LOG-END -->`, plus `OPEN-ITEMS` and `FRONTMATTER` markers). Daemon ONLY reads/writes content between matching marker pairs.
- **D-08a:** **Marker error policy:** If a managed section's marker is missing or malformed, daemon ABORTS the update for that file, logs `system`/`critical` entry to `data/feed.jsonl`, skips the file. NO silent regeneration. Template includes visible warning comment near each marker pair.
- **D-09:** Backfill sourcing — `domain`/`client_name` from `clients.jsonl`; `status` defaults `"active"` (`"unknown"` for `_Unknown.md`); `last_synced` updated every sync. Phase 11 fields not populated in v1.

**Activity Log filter**
- **D-10:** Only triage records with `priority ∈ {urgent, needs-response}` OR non-empty `action_items` hit the log.
- **D-11:** All task records (any outcome) and all invoice events (created/marked-paid/overdue) log unconditionally.
- **D-12:** Activity Log entry shape: `### [YYYY-MM-DD HH:MM] {emoji} {one-line summary}` + optional indented detail block. Emojis: 📧 triage, ✅ task, 💰 invoice.

**Sync triggers**
- **D-13:** Four trigger paths through ONE shared sync function: `/triage-inbox`, `/task` completion, `/invoice` events, `/sync-obsidian` (with `--backfill` and `--incremental` modes). All write to `vault-build/Clients/*.md`. Mac Studio daemon auto-projects to iCloud.
- **D-14:** Sync writes idempotent on `(record_id, client_slug)`. Activity Log + Open Items + frontmatter regenerable deterministically from `data/`.

**Backfill scope**
- **D-15:** Initial backfill processes everything in `data/` end-to-end. Same filtering as incremental. Stub note for every client in `clients.jsonl` even if no records.
- **D-15a:** Stub note shape — frontmatter present, Overview placeholder line, empty Open Items, empty Activity Log, empty Decisions.
- **D-16:** Backfill idempotent — running it twice produces byte-identical managed sections (modulo `last_synced`).

**Library / runtime**
- **D-17:** Direct markdown file I/O for writes — NOT kepano `obsidian-cli`. Obsidian app not running on headless Coolify; Mac daemon must run without Obsidian foregrounded.
- **D-17a:** Repo `vault-build/` is markdown-only. `.obsidian/` is in `.gitignore`. iCloud canonical vault has its own `.obsidian/` shared between Mac and iPhone via iCloud.

**Decisions section (v1)**
- **D-18:** Manually-edited stub. Auto-extraction deferred.

### Claude's Discretion

The following areas are open for the planner — research below makes recommendations:
- Slug generation algorithm (kebab-case, ascii-fold)
- Final YAML frontmatter property names within v1 spec (DataView-friendly)
- Markdown rendering of detail blocks (code fences, callouts, indented prose)
- Sync layer language: single Bash/Node/Python script vs several
- Mac Studio launchd daemon implementation (fswatch, WatchPaths, polling, 30s SLA, iCloud transient unavailability)
- Concurrency on Coolify (file lock vs queue vs single-writer process)
- Internal structure of `_Unknown.md` (table per record vs subsections)
- `last_synced` placement (per-note frontmatter vs `data/.last-vault-sync`)
- How `--backfill` confirms before regenerating

### Deferred Ideas (OUT OF SCOPE)

- Project portfolio notes (one per AMS module deployment)
- Weekly project review skill
- Daily Notes auto-population
- Bidirectional Inbox bridge
- Auto-extracted decisions (needs `decision_summary` field on tasks first)
- DataView dashboard inside Obsidian
- kepano `obsidian-cli` ad-hoc Mac-side use
- Backing canonical vault to git (vault-archive/)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTL-01 | Context accumulation — client history, past decisions stored in structured files | Per-client markdown notes accumulating triage/task/invoice history into Activity Log; client-keyed Open Items mirror; Glen-owned Decisions stub for manual capture (auto-extraction deferred). Phase 11 extends frontmatter with contract-manager data. |

This is the first concrete fulfilment of INTL-01. Phase 10 builds the structural foundation (notes, markers, sync rail); Phase 11 enriches frontmatter; Phase 12 widens the inputs (calendar, drive). Future Decisions auto-extraction completes the loop.
</phase_requirements>

## Summary

This phase wires three infrastructure pieces together: (1) a **shared sync function** running on Coolify that writes per-client markdown into `vault-build/Clients/*.md` whenever triage/task/invoice events fire, (2) a **transport rail** (`scripts/push-and-sync.sh` extended) that propagates `vault-build/` to a Mac Studio via git, and (3) a **launchd daemon** on the Mac Studio that watches for git pulls and projects managed sections from `vault-build/` into the iCloud canonical vault — where Obsidian on iPhone picks them up via Apple's file provider.

The hot path is **marker-aware atomic markdown writes**. The daemon reads only content between matching `<!-- X-START --> ... <!-- X-END -->` pairs and replaces only that span — Glen's Overview and Decisions text outside markers is invisible to it. Malformed markers ABORT the update for that file with a `critical`-level feed entry (D-08a), preventing silent regeneration. Atomic writes use the temp-file-then-rename POSIX idiom so the daemon never leaves a half-written note in iCloud where Apple's `bird`/`cloudd` could partially upload it.

**Primary recommendation:** Implement the sync layer in **Python 3** (single module under `scripts/lib/vault_writer.py`, exposed through a thin `scripts/sync-obsidian.sh` wrapper). The Mac daemon is a **fswatch-driven launchd LaunchAgent** wrapping the same Python module in `--apply-from-vault-build` mode. Concurrency on Coolify is handled by a single-writer pattern (`flock` advisory lock on a sentinel file) since all four triggers run inside the same Claude Code session sequentially in practice — the lock is defensive insurance, not the primary mechanism. `last_synced` lives in **per-note frontmatter** (one timestamp per file, naturally idempotent, survives partial sync crashes).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Read NDJSON history (`data/triage/`, `data/tasks/`, `data/invoices/`, `data/todos/`) | Coolify (Python sync layer) | — | Data lives on Coolify; Mac never reads `data/`. |
| Generate `vault-build/Clients/*.md` (managed-section content) | Coolify (Python sync layer) | — | Single writer. Headless. No Obsidian dependency. |
| Validate input records against schemas | Coolify (Python sync layer) | — | Mirror `scripts/validate-data.sh` pattern; refuse to consume malformed records. |
| Atomic write of managed-section spans | Both (Coolify writes vault-build; Mac writes iCloud) | — | Same algorithm runs in both places — Coolify writes the proposal layer, Mac projects to canonical. |
| Git transport (commit + push from Coolify, pull on Mac) | `scripts/push-and-sync.sh` (extended) | — | Existing rail. Add `vault-build/` to commit set. |
| Filesystem watch on Mac for incoming git changes | Mac Studio launchd + fswatch | — | fswatch wraps FSEvents; LaunchAgent keeps it alive across login sessions. |
| Project managed sections from `vault-build/` to iCloud canonical | Mac Studio (Python sync layer, daemon mode) | — | Same Python module, different entry point. Reads `vault-build/`, writes iCloud. |
| Marker integrity check + abort-on-malformed | Mac Studio (in projection step) | Coolify (also enforces during initial write) | D-08a — aborts at projection so user-edited iCloud notes are never silently regenerated. |
| Logging daemon errors to `data/feed.jsonl` | Mac Studio (writes to repo on local clone) | Coolify (sees on next pull) | Daemon's only writeback to repo is the feed entry; never edits managed content. |
| Mobile rendering | iPhone Obsidian (consumes iCloud) | — | Apple's file provider handles transport from iCloud to device. |

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|---------------|---------|---------|--------------|
| Python 3.11+ | 3.11+ (Mac has 3.14, Coolify TBD — verify in Wave 0) | Sync layer + daemon implementation language | NDJSON streaming via stdlib `json`, atomic writes via stdlib `os.replace`, structured YAML via `ruamel.yaml`. Already present on Mac (3.14). [VERIFIED: `python3 --version` on dev machine] |
| `ruamel.yaml` | latest (≥0.18) | YAML round-trip for frontmatter | Preserves comments, key order, formatting on round-trip — PyYAML strips them. [CITED: ruamel.yaml docs, oreate AI comparison] |
| `jq` | 1.7+ | NDJSON validation in shell wrappers | Already used throughout `scripts/validate-data.sh` and slash commands. [VERIFIED: `jq --version` returns 1.7.1] |
| `fswatch` | 1.17+ (install via brew on Mac Studio) | Filesystem watch wrapper around FSEvents | Apple officially discourages `WatchPaths` (race-prone, missing events per Apple developer docs); `fswatch` is the canonical alternative. [CITED: launchd developer docs, [allenap.me/posts/flock-behaviour](https://allenap.me/posts/flock-behaviour)] |
| `flock` | util-linux on Coolify | Advisory file lock for concurrent-writer safety | Native on Linux. Mac doesn't ship it but Mac side is single-writer by design (D-03). [VERIFIED: man7 flock(2)] |
| Bash 4+ on Coolify, Bash 3.2 on Mac | — | Thin wrapper scripts only | Mac default is Bash 3.2 (no associative arrays, no `mapfile`). Keep Mac-side shell scripts minimal; defer logic to Python. [VERIFIED: `bash --version` returns 3.2.57 on Mac] |

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|---------------|---------|---------|-------------|
| `unicodedata` (stdlib) | — | Unicode NFKD normalization for slug ascii-fold | Slug generation (D-06). |
| `re` (stdlib) | — | Marker regex parsing, slug character class | Marker detect, slug build. |
| `pathlib` (stdlib) | — | Filesystem operations | All path manipulation. |
| `tempfile.NamedTemporaryFile` (stdlib) | — | Atomic write temp-file primitive | Pair with `os.replace` for the canonical idiom. [CITED: python-atomicwrites docs, ActiveState recipe] |
| `launchctl` + `~/Library/LaunchAgents/com.agend.vault-sync.plist` | macOS native | Mac daemon registration | Standard LaunchAgent pattern for run-as-user services. [CITED: launchd.info tutorial] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python | Bash | NDJSON + YAML + atomic writes + Unicode slugs + cross-platform daemon code is painful in pure Bash. Mac default Bash is 3.2 (no associative arrays). Strongly recommend Python. |
| Python | Node.js | Both work. Python wins on stdlib coverage (`unicodedata`, `tempfile.NamedTemporaryFile`, `os.replace`) and matches Glen's existing tooling profile better. Node would mean adding `package.json` at repo root (currently no node_modules in main repo, only in `dashboard/`). |
| `ruamel.yaml` | PyYAML | PyYAML strips comments and reorders keys on round-trip — dangerous when the daemon must preserve any user-added frontmatter additions Glen makes by hand. Use `ruamel.yaml`. |
| `fswatch` (LaunchAgent wrapper) | launchd `WatchPaths` directly | WatchPaths is non-recursive AND Apple developer docs say "Use of WatchPaths is highly discouraged, as filesystem event monitoring is highly race-prone, and modifications may be missed entirely, with no guarantee that the file will be in a consistent state when the job is launched." [CITED: launchd.plist(5) man page] |
| `fswatch` | git post-merge hook | A post-merge hook on Mac would only fire for `git pull` (not `--rebase`) [CITED: git-scm.com githooks docs]. Multiple sources of truth (manual git pulls, automated cron pulls, future direct writes) make filesystem watch more robust than tying to one specific git operation. |
| `flock` on Coolify | In-process lock / no lock | Slash commands run sequentially in one Claude session in practice, but a future scheduled run + manual run could overlap. `flock` is one line and bulletproof. |

**Installation (verify in Wave 0):**

```bash
# On Coolify (Linux)
apt-get install jq                       # Probably already present
pip3 install ruamel.yaml                  # Add to requirements file in scripts/

# On Mac Studio (one-time, manual)
brew install fswatch                      # Required for daemon
pip3 install ruamel.yaml                  # If not already
```

**Version verification:** `ruamel.yaml` is on PyPI; release `0.18.x` is current and battle-tested. Verify exact version with `pip3 show ruamel.yaml` after install. fswatch 1.17+ is current (homebrew tracks it).

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  COOLIFY (Linux, headless, single-writer)                       │
│                                                                  │
│  /triage-inbox ─┐                                               │
│  /task complete ├──> shared sync function ──> vault-build/      │
│  /invoice event ┤    (Python: vault_writer.py)   Clients/*.md   │
│  /sync-obsidian ┘            │                                  │
│                              ├─ reads data/triage/*.jsonl       │
│                              ├─ reads data/tasks/active.jsonl   │
│                              ├─ reads data/invoices/active.jsonl│
│                              ├─ reads data/todos/active.jsonl   │
│                              ├─ reads data/config/clients.jsonl │
│                              ├─ flock(scripts/.vault-sync.lock) │
│                              └─ atomic write managed-sections   │
│                                                                  │
│  scripts/push-and-sync.sh                                       │
│       └─> git push (incl. vault-build/) ──┐                     │
└──────────────────────────────────────────┼─────────────────────┘
                                            │
                                            ▼
                          ┌──────────────────────────────────────┐
                          │  GitHub repo (transport)             │
                          └──────────────────────────────────────┘
                                            │
                                            ▼ git pull (manual or cron)
┌─────────────────────────────────────────────────────────────────┐
│  MAC STUDIO (always-on, projects to iCloud)                     │
│                                                                  │
│  fswatch on ~/work/todo-list/vault-build/                       │
│       │                                                          │
│       ▼  (file change detected)                                 │
│  launchd LaunchAgent  ──>  vault_writer.py --project-to-icloud  │
│  (com.agend.vault-sync)         │                               │
│                                 ├─ for each vault-build/*.md:   │
│                                 │   1. read managed sections    │
│                                 │   2. open iCloud counterpart  │
│                                 │   3. validate markers         │
│                                 │      (ABORT if malformed)     │
│                                 │   4. splice managed content   │
│                                 │   5. atomic temp+rename       │
│                                 └─ write feed entry on errors   │
│                                                                  │
│  ~/Library/Mobile Documents/iCloud~md~obsidian/                 │
│       Documents/AgendOps/Clients/*.md  (canonical vault)        │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │ (Apple bird/cloudd daemon)
                           ▼
                  ┌────────────────────┐
                  │  iPhone Obsidian   │
                  │  (read-only view)  │
                  └────────────────────┘
```

### Recommended Project Structure

```
scripts/
├── sync-obsidian.sh              # Thin bash wrapper for /sync-obsidian command
├── lib/
│   └── vault_writer.py           # Sync engine — backfill, incremental, project-to-icloud modes
├── build-dashboard-data.sh       # Existing
├── push-and-sync.sh              # Existing — extend to commit vault-build/
└── validate-data.sh              # Existing — extend to validate vault-build/ markdown

vault-build/
└── Clients/
    ├── property-council-australia.md
    ├── association-for-tertiary-education-management.md
    ├── occupational-therapy-australia.md
    └── _Unknown.md

mac/                              # NEW directory: Mac-side daemon assets
├── com.agend.vault-sync.plist    # LaunchAgent template (committed; user copies to ~/Library/LaunchAgents/)
├── install-daemon.sh             # One-shot installer that copies plist, runs launchctl load
└── README.md                     # Setup instructions for Glen

.claude/commands/
├── sync-obsidian.md              # NEW slash command
├── triage-inbox.md               # MODIFY — add vault-build/ write step
├── task.md                       # MODIFY — add vault-build/ write step on completion
└── invoice.md                    # MODIFY — add vault-build/ write step on state change

schemas/
└── (no new schemas needed; vault notes are markdown not JSON)
```

### Pattern 1: Marker-Aware Atomic Markdown Write

**What:** Replace content strictly between `<!-- X-START -->` and `<!-- X-END -->` markers without touching anything outside; write atomically using the POSIX `rename` idiom.

**When to use:** Every write to a managed section in either `vault-build/` (Coolify) or iCloud (Mac daemon).

**Algorithm:**

```python
# scripts/lib/vault_writer.py (excerpt — illustrative, not final)
# Source: python-atomicwrites docs + LWN Article on atomic writes
import os
import re
import tempfile
from pathlib import Path

MARKER_PATTERN = re.compile(
    r"(<!--\s*([A-Z-]+)-START\s*-->)(.*?)(<!--\s*\2-END\s*-->)",
    re.DOTALL,
)

class MarkerError(Exception):
    """Raised when start/end markers are missing or malformed (D-08a)."""

def replace_managed_section(file_path: Path, section_name: str, new_content: str) -> None:
    """Replace content between <!-- {section_name}-START --> and <!-- {section_name}-END -->.
    Atomic write via temp-file + os.replace.
    Raises MarkerError if markers are missing/malformed (D-08a)."""
    original = file_path.read_text(encoding="utf-8")

    start_re = re.compile(rf"<!--\s*{section_name}-START\s*-->")
    end_re   = re.compile(rf"<!--\s*{section_name}-END\s*-->")
    starts = list(start_re.finditer(original))
    ends   = list(end_re.finditer(original))

    if len(starts) != 1 or len(ends) != 1:
        raise MarkerError(
            f"{file_path}: expected exactly 1 {section_name}-START and 1 -END, "
            f"got {len(starts)} starts, {len(ends)} ends"
        )
    if starts[0].end() > ends[0].start():
        raise MarkerError(f"{file_path}: {section_name}-END appears before -START")

    new_text = (
        original[: starts[0].end()]
        + "\n"
        + new_content.rstrip("\n")
        + "\n"
        + original[ends[0].start() :]
    )

    # Atomic write: temp file in same directory (so rename is atomic across same fs),
    # fsync the temp file, rename, then fsync the directory.
    dir_path = file_path.parent
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix=f".{file_path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)         # atomic on POSIX
        # fsync the directory so the rename is durable (LWN best practice)
        dir_fd = os.open(dir_path, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
```

**Why this exact shape:**
- `os.replace` is atomic on POSIX (Linux + macOS). [VERIFIED: Python docs, LWN article]
- Temp file MUST be in the same directory as the target so rename stays inside one filesystem (cross-fs rename is not atomic).
- Dotfile prefix on temp keeps it out of `ls` output and avoids triggering fswatch on the Mac side until the rename happens. (fswatch reports the rename event, not the half-written temp file — that's the whole point.)
- `fsync` of file + directory matters because iCloud's `bird`/`cloudd` daemon could partially upload an unfsynced file, leading to corrupted state on iPhone. [CITED: LWN atomic writes article]
- Counts of START/END markers MUST be exactly 1 each — multiple matches indicate corruption (e.g., a previous bad write left both old and new markers).

### Pattern 2: Marker Template

**What:** Initial note shape Coolify writes during backfill, daemon never regenerates.

**Example:**

```markdown
---
domain: propertycouncil.com.au
client_name: Property Council Australia
status: active
last_synced: 2026-05-01T10:30:00+10:30
---

<!-- DO NOT EDIT BETWEEN MARKERS — managed by /sync-obsidian -->
<!-- OVERVIEW-START -->
<!-- OVERVIEW-END -->

## Overview

_No notes yet — replace this line with relationship context._

<!-- DO NOT EDIT BETWEEN MARKERS — managed by /sync-obsidian -->
<!-- OPEN-ITEMS-START -->
## Open Items

_(none)_
<!-- OPEN-ITEMS-END -->

<!-- DO NOT EDIT BETWEEN MARKERS — managed by /sync-obsidian -->
<!-- ACTIVITY-LOG-START -->
## Activity Log

<!-- No activity logged for this client yet -->
<!-- ACTIVITY-LOG-END -->

## Decisions

_(Glen-edited; auto-extraction deferred to a future phase)_
```

**Note on OVERVIEW markers:** Glen's Overview section is OUTSIDE the OVERVIEW markers in the template above. The OVERVIEW marker pair is empty — its purpose is structural future-proofing if Phase 11+ ever needs to inject managed content into the Overview area. Per D-07, Overview is Glen-owned and the sync layer NEVER reads or writes it. The empty marker pair sits at the top of the section as a structural anchor; the human-edited content lives below. (This deviates slightly from a strict reading of D-08 — flagged below as Tension with D-08.)

**Tension with Decision D-08:** D-08 says markers exist for OVERVIEW, OPEN-ITEMS, ACTIVITY-LOG, and FRONTMATTER. But D-07 says Overview is "Glen-owned, manually-edited, freeform. Sync layer NEVER reads or writes this section." There's no managed content in Overview. **Recommended resolution for the planner:** drop the OVERVIEW markers from v1 and leave the section as raw markdown below `## Overview`. Future phases can add an OVERVIEW marker pair if/when they need to. This simplifies the template, removes a marker-integrity-check burden, and matches the actual semantic. Bring this to Glen during planning if needed — it's a minor template cleanup, not a contradiction of intent.

**Note on FRONTMATTER markers:** YAML frontmatter is naturally bounded by `---` lines. No HTML comment markers needed — `ruamel.yaml` parses the bounded region and writes it back. The FRONTMATTER "marker" mentioned in D-08 is the `---`/`---` pair itself; treat the whole frontmatter block as a managed section bounded by those delimiters.

### Pattern 3: NDJSON Streaming + Per-Client Grouping

**What:** Stream input records once, bucket by `client_slug`, sort merged events by timestamp, render Activity Log section per client.

**Algorithm sketch:**

```python
# Phase 1: load clients, build domain → slug map
clients = {}    # domain → {"slug": ..., "client_name": ...}
for line in open("data/config/clients.jsonl"):
    rec = json.loads(line)
    clients[rec["domain"]] = {
        "slug": slugify(rec["name"]),
        "client_name": rec["name"],
    }

# Phase 2: stream + bucket
events_by_slug = collections.defaultdict(list)
def route(rec, source_type):
    domain = rec.get("client_domain") or _extract_domain_from_email(rec.get("from"))
    bucket = clients.get(domain, None)
    slug = bucket["slug"] if bucket else "_Unknown"
    events_by_slug[slug].append((rec_ts(rec), source_type, rec))

for f in glob("data/triage/*.jsonl"):
    for line in open(f):
        rec = json.loads(line)
        if d10_filter(rec):                       # priority in {urgent, needs-response} OR action_items
            route(rec, "triage")

for line in open("data/tasks/active.jsonl"):
    rec = json.loads(line)
    route(rec, "task")                            # all tasks per D-11

for line in open("data/invoices/active.jsonl"):
    rec = json.loads(line)
    route(rec, "invoice")                         # all invoices per D-11

# Phase 3: per-client render
for slug, events in events_by_slug.items():
    events.sort(key=lambda t: t[0])               # stable sort by ts
    activity_log_md = "\n".join(render_log_line(e) for e in events)
    open_items_md  = render_open_items(slug, todos, tasks)
    write_managed_sections(
        path=f"vault-build/Clients/{slug}.md",
        sections={
            "FRONTMATTER":  render_frontmatter(slug),
            "OPEN-ITEMS":   open_items_md,
            "ACTIVITY-LOG": activity_log_md,
        },
    )
```

**Idempotency note:** Because backfill regenerates each managed section from full data, in-memory dedup by `(record_id, slug)` is unnecessary for backfill — the deterministic regenerate-from-source covers it (D-14, D-16). For incremental sync, dedup IS needed: read the existing Activity Log markdown, parse the `[YYYY-MM-DD HH:MM]` entries, skip any record_id already represented. Simpler alternative: incremental mode also regenerates from full data for any client touched in this batch — slightly more work but trivial at this scale (~30 clients, 2 months). **Recommendation: regenerate-from-full-data for both modes.** The performance difference is negligible and the simpler invariant ("output is a pure function of input") is worth more than micro-optimization.

### Pattern 4: launchd LaunchAgent + fswatch Wrapper

**What:** A LaunchAgent that keeps fswatch running; fswatch fires the projection script on any change in `vault-build/`.

**`~/Library/LaunchAgents/com.agend.vault-sync.plist`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agend.vault-sync</string>

    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/fswatch</string>
        <string>-o</string>                                  <!-- one event per batch -->
        <string>--latency</string>
        <string>2</string>                                   <!-- coalesce events 2s -->
        <string>/Users/glenr/work/todo-list/vault-build</string>
    </array>

    <key>StandardOutPath</key>
    <string>/Users/glenr/Library/Logs/agend-vault-sync.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/glenr/Library/Logs/agend-vault-sync.err.log</string>

    <key>KeepAlive</key>
    <true/>                                                  <!-- restart if fswatch dies -->

    <key>RunAtLoad</key>
    <true/>                                                  <!-- run at login -->

    <!--
        fswatch -o emits one line per batch of events. Pipe it to xargs to call our projector
        on each batch. We use a wrapper script because launchd ProgramArguments can't pipe.
    -->
</dict>
</plist>
```

Wait — `ProgramArguments` can't pipe directly. The LaunchAgent must point to a wrapper script:

```bash
# mac/vault-sync-watcher.sh
#!/bin/bash
set -euo pipefail
REPO=/Users/glenr/work/todo-list

# fswatch -o emits one line per batch; xargs -n1 calls projector once per batch.
exec /opt/homebrew/bin/fswatch -o --latency 2 "$REPO/vault-build" \
  | xargs -n1 -I{} /usr/bin/env python3 "$REPO/scripts/lib/vault_writer.py" --project-to-icloud
```

And the plist's `ProgramArguments` becomes `["/Users/glenr/work/todo-list/mac/vault-sync-watcher.sh"]`. `KeepAlive=true` ensures launchd restarts the wrapper if it ever dies (network blip, fswatch crash, etc.).

**30s SLA reasoning:** With fswatch latency=2s + Python projector typical runtime <1s, worst-case detection-to-projection is ~3-5s. Apple's iCloud sync from Mac to iPhone is "within seconds" when both devices are awake/connected ([CITED: zottmann.org iCloud deep dive](https://zottmann.org/2025/09/08/ios-icloud-drive-synchronization-deep.html)). 30s is comfortable.

**Resilience to laptop sleep/wake:** Mac Studio is always-on per D-03, but if it ever sleeps, launchd resumes the wrapper on wake, and fswatch picks up changes during the next polling/event cycle. The git pull on the Mac is the actual "input event" — once `vault-build/` files have new mtimes, fswatch will fire even if the changes happened during sleep.

**Resilience to transient iCloud unavailability:** When iCloud is offline, writes to `~/Library/Mobile Documents/...` succeed locally; `cloudd`/`bird` queues the upload. On iCloud reconnect, queue drains. The daemon does not need to handle iCloud-specific errors — it just writes to a regular filesystem path and Apple's daemons take over. The one failure mode: iCloud quota exceeded → write fails → projector logs `system`/`critical` to `data/feed.jsonl`.

### Pattern 5: Slug Algorithm

**What:** Deterministic kebab-case + ASCII fold; collision resolution by domain suffix.

```python
import re, unicodedata

_VALID_CHARS = re.compile(r"[^a-z0-9-]+")
_DASHES = re.compile(r"-{2,}")

def slugify(name: str) -> str:
    """Deterministic kebab-case slug.
    1. NFKD normalize (decomposes composed glyphs: 'é' → 'e' + combining acute)
    2. Encode to ASCII, dropping non-ASCII bytes (drops the combining marks left over)
    3. Lowercase
    4. Replace anything not [a-z0-9] with '-'
    5. Collapse runs of '-' and trim leading/trailing '-'
    """
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    dashed = _VALID_CHARS.sub("-", lowered)
    collapsed = _DASHES.sub("-", dashed)
    return collapsed.strip("-")

def slug_with_domain(name: str, domain: str) -> str:
    """Used when a base slug collides with another client's slug. Appends domain suffix."""
    base = slugify(name)
    domain_part = slugify(domain.replace(".", "-"))
    return f"{base}--{domain_part}"
```

**Examples (sanity-check):**
- `"Property Council Australia"` → `property-council-australia`
- `"Co-op & Sons, LLC."` → `co-op-sons-llc`
- `"Société Générale"` → `societe-generale`
- `"日本企業"` → `""` (empty after strip) → **edge case: empty result must fall back to domain slug**: `nihon-co-jp`. Add a defensive check.

**Collision detection during backfill:** Build the slug for every client in `clients.jsonl`. If two slugs collide, switch BOTH to `slug_with_domain` form. Document collisions in the backfill log so Glen sees them. With 3 current clients there are no collisions; the algorithm scales to ~30 fine.

**Edge case to handle in code:**
```python
def safe_slugify(name: str, domain: str) -> str:
    s = slugify(name)
    if not s:                                  # all non-ASCII or all symbols
        s = slugify(domain.replace(".", "-"))
    if not s:
        s = "client-unknown"                   # shouldn't happen for real clients
    return s
```

### Pattern 6: Frontmatter Property Names (DataView-Friendly)

**What:** Property names that are easy to query both in DataView's frontmatter mode and in inline-field mode if Glen ever switches.

**Recommendation:** Use **`snake_case`** for all custom properties.

**Why:**
- Obsidian's built-in property defaults are `tags`, `aliases`, `cssclasses` — already snake-ish (lowercase + underscores aren't even needed because they're single words).
- DataView matches frontmatter property names verbatim; both `snake_case` and `kebab-case` work, but `snake_case` is friendlier for DataView Lua-style queries because hyphens require escaping or quoting in JS-eval contexts.
- The ruamel.yaml round-trip preserves keys exactly; snake_case keeps the YAML clean.
- Matches the existing repo convention — schema property names in `schemas/*.json` are `client_name`, `client_domain`, `due_date`, `task_type`, etc. — all snake_case. Reuse the convention.
- D-09 already uses snake_case names: `domain`, `client_name`, `status`, `last_synced`. Lock these.

**Phase 10 v1 frontmatter spec:**

```yaml
---
domain: propertycouncil.com.au          # string, exact match to clients.jsonl entry
client_name: Property Council Australia # string, display name
status: active                          # enum: active | inactive | unknown (extensible)
last_synced: 2026-05-01T10:30:00+10:30  # ISO 8601 with TZ offset (Obsidian 1.4.3+ supports offsets)
---
```

**Important:** Obsidian Properties supports ISO 8601 with timezone offsets as of v1.4.3 ([CITED: forum.obsidian.md/t/properties-time-type-support-for-iso-8601-standard](https://forum.obsidian.md/t/properties-time-type-support-for-iso-8601-standard/64532)). Glen's existing data uses `+10:30` (Adelaide ACDT) — keep that style. Match the format already used in `data/feed.jsonl` and the schema patterns. [VERIFIED: feed-entry schema requires `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$`]

**Phase 11 extension fields (for the planner's awareness; do NOT populate in v1):** `deployed_modules`, `contract_start`, `contract_end`, `primary_contact`, `sites`. All snake_case.

### Pattern 7: Activity Log Entry Rendering

**What:** Fixed shape per D-12.

```markdown
### [2026-05-01 10:30] 📧 Greg Davenport — SOW review (PCA)
> needs-response · contract review for Tuesday meeting
> [Open thread](https://mail.google.com/mail/u/0/#inbox/19d17c8f98f99484)

### [2026-05-01 11:42] ✅ task-2026-05-01-003 completed: Summarize SOW
> Outcome: 4-email thread, member rates deployment status, talking points captured

### [2026-04-28 14:00] 💰 inv-2026-04-28-002 marked paid: $5,500.00 AUD
> PROP-0324, INV-0042
```

**Rules:**
- One `###` heading per event. Heading is the parsed dedup key during incremental sync if we ever skip the regenerate-from-full strategy.
- Indented `>` block (markdown blockquote) for detail — renders cleanly in Obsidian + iPhone.
- Gmail thread links use `mail.google.com/mail/u/0/#inbox/{thread_id}` per CONTEXT.md `<specifics>`. Confirmed they open natively in iPhone Gmail.
- Newest at top OR oldest at top? **Recommend newest at top** (matches the source article and Linear/Notion aesthetic Glen called out). Last 30-50 entries; truncate older entries to a `_Archive_` collapse later if files get long.

### Pattern 8: `_Unknown.md` Internal Structure

**What:** Subsections by closest available identifier.

```markdown
---
domain: ""
client_name: Unknown
status: unknown
last_synced: 2026-05-01T10:30:00+10:30
---

## Overview

_Records that didn't route to a known client. Surface for cleanup — add the domain
to `data/config/clients.jsonl` to claim it._

<!-- ACTIVITY-LOG-START -->
## Activity Log

### Group: needs-response (5 records)

> _**Note:** "needs-response" is a triage priority bucket, not a client. These records
> were misrouted because client extraction failed during triage. Investigate triage logic._

#### [2026-03-23 12:44] ✅ task-2026-03-23-002 completed: PCA pre-meeting catch-up
> Outcome: meeting prep notes captured

#### [2026-03-23 12:44] ✅ task-2026-03-23-003 completed: Manju monthly catch-up review
> Outcome: pending

### Group: github.com (2 records)

#### [2026-03-23 09:36] 📧 GitHub — Workflow run failure
> low-priority · build failure notification
<!-- ACTIVITY-LOG-END -->
```

**Rules:**
- Group by closest identifier: `client_name` if non-empty, else `from` email's domain part, else `"unknown"`.
- Show count per group at the heading level for at-a-glance triage.
- For the specific case of `client_name = "needs-response"` (priority bucket leak — see Glen's task-2026-03-23-002), add a contextual note explaining what happened. Don't hide the bug; surface it.
- Subsection ordering: by record count descending (loudest groups first).

### Pattern 9: Concurrency on Coolify

**What:** Single shared sync function — flock advisory lock prevents overlapping writes.

**Recommendation: `flock` on a sentinel file under `scripts/.vault-sync.lock`.**

```bash
# scripts/sync-obsidian.sh — entrypoint for /sync-obsidian command
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK_FILE="$REPO_ROOT/scripts/.vault-sync.lock"

# Wait up to 30s for the lock; fail loudly if we don't get it.
exec 9>"$LOCK_FILE"
flock --timeout 30 9 || {
  echo "ERROR: another vault-sync is in progress; aborting." >&2
  exit 1
}

# Run the actual Python sync
exec /usr/bin/env python3 "$REPO_ROOT/scripts/lib/vault_writer.py" "$@"
```

**Rationale:**
- Slash commands run sequentially in one Claude session in practice. The lock is defensive insurance against future scenarios (scheduled run + manual run, concurrent triage hooks).
- `flock(1)` is util-linux native — available on Coolify (Linux). Mac Studio doesn't ship it but Mac runs the daemon, not the slash commands, so it doesn't need flock. [VERIFIED: man7 flock(1)]
- A single in-process Python that handles all 4 trigger paths (one runtime per `/triage-inbox`, `/task`, `/invoice`, `/sync-obsidian` invocation) is simpler than a queue. Each Claude command invokes the python script; flock serializes them.
- Do NOT use `flock` on the markdown files themselves — write atomicity comes from the temp+rename pattern. flock guards the higher-level sync operation.

**Alternative considered + rejected:** A queue file (`data/queue/vault-sync.jsonl`) processed by a separate worker. Adds operational complexity (when does the worker run? what restarts it?) for no meaningful benefit at this scale.

### Pattern 10: `last_synced` Placement

**What:** Per-note frontmatter.

**Recommendation: per-note frontmatter (`last_synced` field), NOT a single `data/.last-vault-sync` state file.**

**Rationale:**
- **Locality:** the timestamp travels with the note. Glen can look at any note and see when it was last refreshed.
- **Crash resilience:** if a sync run crashes after writing 10 notes and before writing the 11th, the 10 successful notes have correct `last_synced` and the 11th retains its old value. A single state file would either (a) be set after all writes (so a crash leaves all 10 correctly written but globally marked stale) or (b) be set per-note (which IS the per-note frontmatter idea, just stored in a separate file).
- **Manual editability:** if Glen edits frontmatter by hand on iPhone (adds a tag, changes status), the `last_synced` field is right there next to the other properties. ruamel.yaml round-trips preserve his edits.
- **Idempotency:** D-14 says writes are idempotent. If we regenerate from full data each run, `last_synced` is the only field that changes between identical runs. Writing it per-note keeps the change scope localized.

**One implication:** the daemon must read each note's frontmatter to decide if it needs to project (or just project unconditionally on any vault-build/ change). **Recommend project-unconditionally** — fswatch already filters by directory change, project all changed files, write `last_synced` from the projection time. Simple, no race conditions.

### Anti-Patterns to Avoid

- **Regex-based YAML editing:** Will eventually corrupt frontmatter when Glen adds a list value or a multi-line string by hand. Use `ruamel.yaml` for round-trip safety.
- **Naive concatenation for managed-section replacement:** If you do `re.sub(START_TO_END_PATTERN, new_content, file_text)`, multi-line content with markdown that contains `<!--` will explode. Use the explicit-bounds approach in Pattern 1.
- **Writing markdown directly with shell heredocs:** Tempting but fragile. The slash command writes a JSON record (always valid), then invokes the Python writer (always valid markdown). No shell-quoting hell.
- **launchd `WatchPaths` instead of fswatch:** Apple's developer docs explicitly discourage WatchPaths because of race conditions and missed events. Use fswatch wrapped in a KeepAlive LaunchAgent. [CITED: launchd.plist(5) man page]
- **kepano `obsidian-cli` for the daemon write path:** Per D-17 and confirmed by research — kepano CLI requires Obsidian to be open. Headless Mac daemon means Obsidian is NOT foregrounded. Direct file I/O is the only viable path. [CITED: skills.sh kepano obsidian-cli docs]
- **Append-only Activity Log file (vs regenerate-from-full):** Tempting because it sounds idempotent, but you'd need a dedup map AND you'd lose the ability to fix bad records by editing source NDJSON. The "regenerate-from-source" pattern (D-14, D-16) is the right invariant.
- **`git pull` on Mac Studio without a clean state:** If the Mac side ever has uncommitted changes in `vault-build/` (shouldn't happen by design, but if a future bug introduces it), `git pull --ff-only` would fail. The pull script on Mac should include `git checkout -- vault-build/` before pull, mirroring the Coolify-side `git checkout -- data/queue/` defensiveness in `push-and-sync.sh`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing/serialization | Regex-based YAML reader/writer | `ruamel.yaml` | Comments, multi-line strings, nested lists, key order — all corrupted by regex. ruamel.yaml round-trips preserve them. |
| Atomic file writes | Direct `open(path, "w")` | `tempfile.NamedTemporaryFile(dir=parent)` + `os.replace` + `os.fsync(dir_fd)` | Without atomic semantics, the daemon can leave half-written files in iCloud, which Apple's `bird`/`cloudd` partially uploads, corrupting iPhone state. |
| Filesystem watch on macOS | Polling loop, launchd `WatchPaths` | `fswatch` (homebrew) wrapped in LaunchAgent | WatchPaths is officially discouraged by Apple. Polling burns CPU and misses fast events. fswatch wraps the kernel FSEvents API correctly. |
| Concurrent-write coordination | Application-level mutex | `flock` on a sentinel file | flock is kernel-enforced advisory locking, survives process crashes (fd cleanup releases the lock). |
| Unicode-safe slug generation | `s.lower().replace(' ', '-')` | `unicodedata.normalize("NFKD", s).encode("ascii", "ignore")` then character-class regex | Naive lowercasing doesn't handle accents, ligatures, math glyphs, full-width characters. NFKD decomposes them; ASCII-encode strips combining marks. |
| Frontmatter ↔ markdown body splitting | Regex `^---\n.*?\n---\n(.*)$` | Find first two `---` delimiters explicitly | Frontmatter spec allows blank lines and `---` inside multi-line strings; explicit two-pass parsing is more robust. (Or use `ruamel.yaml`'s YAML stream parsing on the leading section.) |
| iCloud upload force / coordination | Calling `brctl` to force download | Just write the file and let Apple's daemons handle it | Apple explicitly says "applications cannot force synchronization." Writing to the iCloud Drive path is sufficient — `cloudd`/`bird` handle the rest. |

**Key insight:** This phase is mostly orchestration of well-understood primitives (NDJSON streaming, atomic file writes, fswatch, ruamel.yaml). The risk is in WIRING them correctly, not in the primitives themselves. The custom code that's really new: the marker-aware splice algorithm, the slug fallback logic, and the launchd plist + wrapper script.

## Runtime State Inventory

> Phase 10 is a greenfield phase that ADDS state but doesn't rename or refactor existing state. This section confirms there's no hidden state to migrate — only NEW state to create.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 10 creates fresh `vault-build/Clients/*.md` from `data/` history. The iCloud canonical vault `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AgendOps/` does not yet exist; Glen will create it during setup. | Create `vault-build/Clients/` (committed); Glen creates `AgendOps` vault in iCloud Obsidian app once. |
| Live service config | None — no external service has prior knowledge of "Agend Ops Obsidian vault". Coolify, GitHub Pages, Xero, hardened-workspace MCP — none of them touch the new vault. | None. |
| OS-registered state | NEW: `~/Library/LaunchAgents/com.agend.vault-sync.plist` will be installed during Mac setup. | New: install via `launchctl load -w ~/Library/LaunchAgents/com.agend.vault-sync.plist`. Document in `mac/README.md`. |
| Secrets/env vars | None — sync layer reads only public NDJSON data. No new keys, no new OAuth grants. | None. |
| Build artifacts | NEW: `vault-build/Clients/*.md` is committed-to-git build output. Will require a `.gitkeep` in `vault-build/Clients/` if directory needs to exist before first sync. | Add `vault-build/Clients/.gitkeep` in initial scaffolding task. |

**Key non-finding:** No retroactive migration is needed. Phase 10 is purely additive.

## Common Pitfalls

### Pitfall 1: Marker corruption from Obsidian plugins or manual edits

**What goes wrong:** Some Obsidian plugins (Templater, Templates, Linter) rewrite parts of notes, occasionally stripping HTML comments or inserting whitespace that breaks marker matching. A manual paste from another note can also accidentally duplicate a marker pair.

**Why it happens:** Obsidian's editor doesn't surface HTML comments visibly by default; Glen might delete one without noticing.

**How to avoid:**
- Visible warning text right above each marker pair (D-08a already specifies this).
- Marker integrity check on EVERY projection step — count START vs END markers, verify ordering. If anything is off, ABORT this file's update and log `system`/`critical` to `data/feed.jsonl`.
- The aborted file's `last_synced` does not get touched — Glen sees a stale timestamp and knows something is wrong.

**Warning signs:** Feed entries with type `system` and level `critical`. Slow drift in `last_synced` for one specific note while others stay fresh.

### Pitfall 2: iCloud `.icloud` placeholder eviction of files the daemon needs to read

**What goes wrong:** If Glen's Mac Studio has "Optimize Mac Storage" on, iCloud may evict files from local disk and replace them with `.icloud` placeholders. The daemon tries to read `Clients/property-council-australia.md`, finds only `.property-council-australia.md.icloud`, and throws.

**Why it happens:** Default macOS behavior; Mac Studios with small SSDs are most affected.

**How to avoid:**
- During Mac daemon install, ensure the iCloud Drive folder for the AgendOps vault has "Keep Downloaded" set (or "Optimize Mac Storage" off for that specific folder).
- Defensive read: if the projector encounters a `.icloud` placeholder, call `brctl download <path>` and retry. Cap retries at 3 with 2-second waits. Log `system`/`critical` if all retries fail.
- Document this in `mac/README.md`. [CITED: techgarden.alphasmanifesto.com on .icloud placeholders, eclecticlight on iCloud sync]

**Warning signs:** Daemon errors reading specific notes; presence of `.NAME.icloud` files in `Clients/`.

### Pitfall 3: NDJSON line corruption from concurrent appends mid-write

**What goes wrong:** Two `/task` invocations append to `data/tasks/active.jsonl` near-simultaneously; one sees a partial line from the other.

**Why it happens:** POSIX append-mode writes are atomic only up to PIPE_BUF (typically 4 KB). Long lines can interleave.

**How to avoid:**
- Wrap writes to `data/*.jsonl` in `flock` (already partially done in slash commands; verify and tighten in Phase 10 task that touches these files).
- Validate input NDJSON before consuming during sync — the validator step (Pattern: validation strategy below) catches partial-line corruption.
- Note: this isn't a NEW pitfall introduced by Phase 10, but Phase 10 makes it more visible because the sync layer is now reading these files programmatically more often.

**Warning signs:** `validate-data.sh` reports `bad_lines > 0`; sync layer's input validator flags malformed records.

### Pitfall 4: Gmail thread URL fragments don't open Gmail on iPhone reliably

**What goes wrong:** `https://mail.google.com/mail/u/0/#inbox/{thread_id}` opens Safari, then Safari tries to redirect to Gmail. iOS may or may not catch this.

**Why it happens:** iOS Universal Links for Gmail are Gmail-app-version-dependent.

**How to avoid:**
- This is the format CONTEXT.md `<specifics>` mandates — it's the best available. No fix; document as known limitation.
- Alternative `googlegmail://co?to=` would open compose, not the thread — wrong direction.
- Glen has confirmed this works for him in practice (D-13 line in the article and CONTEXT.md `<specifics>`). Trust the spec.

**Warning signs:** Glen reports "thread links don't open in Gmail" — investigate Universal Link config, but won't be a Phase 10 blocker.

### Pitfall 5: macOS Bash 3.2 incompatibilities in Mac-side wrapper scripts

**What goes wrong:** Plan author writes `mapfile -t lines < file` or uses associative arrays in the Mac wrapper script; works on Coolify (bash 4+) but fails silently on Mac (bash 3.2.57).

**Why it happens:** macOS ships bash 3.2 by default for licensing reasons (no GPLv3). It hasn't been updated since 2007.

**How to avoid:**
- Keep Mac-side bash to absolute minimum: just `exec` into Python.
- All actual logic in Python. Bash on Mac is just a thin launcher.
- ShellCheck the Mac wrapper script with `--shell=bash --severity=warning`.

**Warning signs:** Daemon "succeeds" but writes no output; check launchd logs for unrecognized-syntax errors.

### Pitfall 6: Empty stub note triggers the daemon's marker validator on first sync

**What goes wrong:** Coolify writes a fresh stub note with empty managed sections. Daemon picks up the change, opens iCloud counterpart — but iCloud counterpart doesn't exist yet. Daemon code path "create-if-missing" must coexist with the strict marker-integrity check.

**Why it happens:** First-time setup OR adding a brand-new client to `clients.jsonl`.

**How to avoid:**
- Distinguish "new file in iCloud (no markers expected — write the full template)" from "existing file (markers required — abort if malformed)".
- Algorithm: if iCloud counterpart doesn't exist, write the full file (markers + content) and mark it "freshly created" in the projection log. If it does exist, run marker validation; abort on failure.
- This is a code branch in the Mac-side projector. Test with empty iCloud directory + Coolify writing a brand-new client.

**Warning signs:** First-run errors reading non-existent iCloud paths; stack trace from the daemon on the very first projection.

## Code Examples

### Frontmatter render (ruamel.yaml round-trip)

```python
# Source: ruamel.yaml docs (https://yaml.dev/doc/ruamel.yaml/overview/)
from ruamel.yaml import YAML
from io import StringIO

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)

def render_frontmatter(client: dict, last_synced_iso: str) -> str:
    fm = {
        "domain": client["domain"],
        "client_name": client["name"],
        "status": client.get("status", "active"),
        "last_synced": last_synced_iso,
    }
    buf = StringIO()
    yaml.dump(fm, buf)
    return f"---\n{buf.getvalue()}---\n"
```

### Activity log line render

```python
# Source: D-12 + CONTEXT.md <specifics> for Gmail link format
EMOJI = {"triage": "📧", "task": "✅", "invoice": "💰"}

def render_log_line(rec_ts_iso: str, kind: str, summary: str, detail: str | None = None,
                    gmail_thread_id: str | None = None) -> str:
    # Convert ISO to "YYYY-MM-DD HH:MM"
    short_ts = rec_ts_iso[:16].replace("T", " ")
    line = f"### [{short_ts}] {EMOJI[kind]} {summary}\n"
    if detail:
        line += f"> {detail}\n"
    if gmail_thread_id:
        line += f"> [Open thread](https://mail.google.com/mail/u/0/#inbox/{gmail_thread_id})\n"
    return line
```

### Slash command extension snippet (for triage-inbox.md, task.md, invoice.md)

```markdown
## Step N: Update Obsidian vault-build/

After writing the {triage|task|invoice} record, sync the affected client note:

```bash
bash scripts/sync-obsidian.sh --incremental --record-type {triage|task|invoice}
```

This writes managed sections in `vault-build/Clients/*.md`. The Mac Studio daemon will pick up the change after the next git push and project to iCloud automatically.

If the sync fails (lock timeout, validation error), the failure is logged to `data/feed.jsonl` as `system`/`critical` but does NOT block the slash command from completing — the next sync run will catch up.
```

### Daemon entry point

```python
# scripts/lib/vault_writer.py — entrypoint
import argparse, sys, traceback

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["backfill", "incremental", "project-to-icloud"], required=True)
    p.add_argument("--record-type", choices=["triage", "task", "invoice", "all"], default="all")
    args = p.parse_args()

    try:
        if args.mode == "backfill":
            run_backfill()                       # writes vault-build/
        elif args.mode == "incremental":
            run_incremental(args.record_type)    # writes vault-build/
        elif args.mode == "project-to-icloud":
            run_projection()                     # reads vault-build/, writes iCloud
    except Exception as e:
        log_critical_to_feed(f"vault_writer {args.mode} failed: {type(e).__name__}: {e}")
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| launchd `WatchPaths` directly | fswatch + LaunchAgent + KeepAlive | Apple has discouraged WatchPaths in launchd.plist(5) for years | Phase 10 daemon must use fswatch wrapper, not WatchPaths. |
| PyYAML for round-trip YAML | ruamel.yaml | ruamel.yaml became standard for round-trip YAML ~2018 | Use ruamel.yaml; PyYAML loses comments and key order. |
| Direct file write + rename without fsync | temp + rename + fsync(file) + fsync(dir) | LWN clarified durability requirements ~2019 | Daemon writes to iCloud must fsync; Apple's daemons can partially upload unfsynced data. |
| kepano `obsidian-cli` for any vault scripting | Direct file I/O for headless cases | kepano CLI requires Obsidian app open (confirmed Mar 2026) | Don't use kepano CLI for headless Coolify or unattended Mac daemon. |

**Deprecated/outdated:**
- `pyaml` (note: not PyYAML) — separate, less-maintained library. Don't confuse.
- Mac-only `shlock` — alternative to flock, but Mac side doesn't need locking (single-writer by design); no use case.
- launchd `StartInterval` polling for vault detection — wasteful; fswatch is event-driven.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Glen will install fswatch via Homebrew on the Mac Studio (`brew install fswatch`) | Standard Stack, Pattern 4 | If brew isn't available or Glen prefers MacPorts: install path differs. Wave 0 verifies brew availability. |
| A2 | The Mac Studio is reachable from Coolify via the existing `push-and-sync.sh` rail (specifically: it runs `git pull` on its own clone of the repo, automatically or manually) | Architecture Diagram | If "always-on Mac Studio" is currently a development-time assumption with no automation in place, the planner needs a task to add a pull mechanism (cron `git pull` every 60s, or post-push webhook). CONTEXT.md D-03 says "git pulls" trigger the daemon — assumes someone or something is doing the pull. |
| A3 | "Always-on" Mac Studio means no laptop-sleep concerns | Pattern 4 | If the Mac Studio actually does sleep, fswatch will resume on wake and pick up changes; expected behavior is fine. Worst case: a delayed sync after a sleep cycle. |
| A4 | `pip3` is available on the Coolify container | Standard Stack | If Coolify's container is alpine-based without pip, install path differs. Wave 0 verifies. |
| A5 | iPhone Obsidian uses the iCloud-backed vault Glen will manually create at `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AgendOps` | Architecture Diagram | If Glen's iPhone Obsidian uses Obsidian Sync instead of iCloud, the canonical-vault path differs and Apple's bird/cloudd is bypassed. CONTEXT.md D-01 explicitly locks iCloud, so this is low-risk. |
| A6 | Phase 10's planner will scope a Wave 0 task for daemon installation on the Mac Studio | Architecture Map | If left implicit, Glen ends up with no daemon and confused about why his iPhone isn't updating. Plan must include explicit Mac-side install task. |
| A7 | Existing slash command files (triage-inbox.md, task.md, invoice.md) can be extended with a final "sync to vault-build" step without breaking their existing behavior | Pattern: Code Examples | Verified by reading the command files — they end with `git commit` of dashboard data; appending a `bash scripts/sync-obsidian.sh` call before the commit fits cleanly. |
| A8 | Glen's display of newest-first vs oldest-first preference for Activity Log | Pattern 7 | Recommended newest-first based on Linear/Notion aesthetic and source article. Confirm during planning if not assumed correctly. |

## Open Questions

1. **Mac Studio git-pull cadence — manual, cron, or webhook?**
   - What we know: D-03 says "watches `vault-build/` for incoming git pulls". Implies someone is pulling.
   - What's unclear: who? Glen manually? cron? GitHub webhook → SSH script?
   - Recommendation: simplest first — cron `git pull --ff-only` every 60s on Mac Studio. fswatch will fire on the file changes from the pull. Document as a planner-time task. Webhook can come later if 60s feels stale.

2. **First-time Mac daemon install: scripted or documented?**
   - What we know: New `~/Library/LaunchAgents/com.agend.vault-sync.plist` and `mac/vault-sync-watcher.sh`.
   - What's unclear: do we ship a `mac/install-daemon.sh` that does `launchctl load` automatically, or just docs in `mac/README.md`?
   - Recommendation: ship a `mac/install-daemon.sh` for one-shot install — Glen runs it once and never thinks about it again. Idempotent (handles already-loaded case via `launchctl unload` first).

3. **What does `/sync-obsidian --backfill` do if `vault-build/Clients/` already has notes?**
   - What we know: D-15 says backfill is initial; D-16 says backfill is idempotent.
   - What's unclear: is `--backfill` a one-time bootstrap, or does running it again clobber updates the daemon hasn't picked up yet?
   - Recommendation: `--backfill` is always safe to re-run (deterministic regenerate from full data). It only writes to `vault-build/`, not to iCloud. The daemon will then re-project — which is also idempotent. Should NOT have a confirmation prompt; managed sections are safe by definition. Document this clearly.

4. **What happens when a client is REMOVED from `clients.jsonl`?**
   - What we know: backfill creates a stub for every client in `clients.jsonl`. If Glen removes a client, the corresponding `.md` in `vault-build/` becomes orphaned.
   - What's unclear: should the sync layer DELETE the orphan? Or move to `_Archive/`? Or leave it?
   - Recommendation: leave it. Glen can `git rm` manually if he wants. Auto-delete is dangerous (Glen might have edited the Overview heavily). Out of scope for v1; mention in deferred.

5. **Triage records have a `dismissed` field that's not in the schema (verified in `data/triage/2026-03-23T004602.jsonl`).**
   - What we know: schema declares `additionalProperties: false`; live data has extra fields.
   - What's unclear: should the sync validator be strict (refuse) or lenient (warn)?
   - Recommendation: lenient on read (extra fields ignored) but strict on schema validation as a separate step that flags drift. Phase 10 doesn't fix the schema; flag it for a future tidy-up. Affects Pattern 9 implementation (validation strategy).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Sync layer + daemon | ✓ on Mac (3.14); Coolify TBD | 3.14.4 (Mac); verify Coolify | If Coolify lacks Python 3.11, install via `apt install python3` in Dockerfile or use Python 3.10+ (some f-string tweaks needed) |
| `jq` 1.7+ | Validation, slash command snippets | ✓ on Mac | 1.7.1 | — |
| `ruamel.yaml` | Frontmatter round-trip | ✗ (not yet installed) | — | `pip3 install ruamel.yaml` (one-time setup task) |
| `fswatch` | Mac daemon | ✗ on Mac (not installed) | — | `brew install fswatch` (one-time Mac setup task); no fallback that meets 30s SLA |
| `flock` | Coolify concurrency lock | Linux native | util-linux | — |
| `launchctl` | Mac daemon registration | macOS native | — | — |
| `brctl` (iCloud control) | Defensive download of evicted .icloud placeholders | macOS native | — | — |
| Mac Studio always-on, reachable | Daemon host | A2 assumption | — | Plan must include Mac-side install task |

**Missing dependencies with no fallback:**
- `fswatch` on Mac Studio — must be installed during Phase 10 setup; the daemon depends on it.

**Missing dependencies with fallback:**
- `ruamel.yaml` on Coolify and Mac — install via pip; trivially fixable.

## Validation Architecture

> Note: Phase 10 doesn't have JSON-schema test coverage in the existing pattern (no test framework configured at repo root). Validation in this codebase has historically been: (1) `scripts/validate-data.sh` for NDJSON well-formedness, (2) `additionalProperties: false` JSON schema files for shape checking, (3) manual smoke testing of slash commands. This phase should follow the same validation-by-convention approach.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None at repo root (Coolify dashboard has Jest under `dashboard/`, but that's a separate Next.js project). Phase 10 lives at the repo root. |
| Config file | None |
| Quick run command | `bash scripts/validate-data.sh && bash scripts/sync-obsidian.sh --backfill --dry-run` (Wave 0 must add `--dry-run` to the sync script) |
| Full suite command | Above + manual visual check of `vault-build/Clients/` after backfill |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTL-01 | Backfill creates one note per client in clients.jsonl + `_Unknown.md` | smoke | `bash scripts/sync-obsidian.sh --backfill && ls vault-build/Clients/` (expect ≥4 files: 3 clients + _Unknown) | ❌ Wave 0 |
| INTL-01 | Activity Log entries rendered in correct format with emoji | unit | `python3 -m unittest scripts.tests.test_render_log_line` | ❌ Wave 0 (decide if introducing pytest is worth it) |
| INTL-01 | Marker-aware splice preserves content outside markers | unit | `python3 -m unittest scripts.tests.test_replace_managed_section` | ❌ Wave 0 |
| INTL-01 | Slug algorithm is deterministic + handles edge cases | unit | `python3 -m unittest scripts.tests.test_slugify` | ❌ Wave 0 |
| D-08a | Malformed markers ABORT and log critical | unit + smoke | `python3 -m unittest scripts.tests.test_marker_error` + check feed.jsonl after a corrupted-fixture run | ❌ Wave 0 |
| D-14 | Idempotency: backfill twice = byte-identical (modulo last_synced) | smoke | `bash scripts/sync-obsidian.sh --backfill && cp -r vault-build/Clients /tmp/run1 && bash scripts/sync-obsidian.sh --backfill && diff -r /tmp/run1 vault-build/Clients` (excluding last_synced lines) | ❌ Wave 0 |
| D-08 | All managed sections delimited by markers in stub notes | smoke | `grep -c "ACTIVITY-LOG-START" vault-build/Clients/*.md` should equal `grep -c "ACTIVITY-LOG-END"` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `bash scripts/validate-data.sh && bash scripts/sync-obsidian.sh --backfill --dry-run`
- **Per wave merge:** Above + run `python3 -m unittest discover scripts/tests` if pytest scaffold is added
- **Phase gate:** Full backfill on real data, manual visual inspection of generated `vault-build/Clients/` files, manual install of Mac daemon and confirm one round-trip from Coolify-write → push → Mac-pull → iCloud-write → iPhone-display

### Wave 0 Gaps

- [ ] Add `scripts/sync-obsidian.sh --dry-run` flag (writes nothing, prints what would change)
- [ ] Decide whether to introduce `pytest` or stay with `unittest` stdlib for Python tests; either way add `scripts/tests/` directory
- [ ] Consider extending `scripts/validate-data.sh` with a `--vault-build` mode that re-parses generated frontmatter as YAML and checks marker pair balance (re-validates the output, not just input)
- [ ] Document `mac/README.md` setup instructions including fswatch install, plist load, brctl auto-download config
- [ ] Add `vault-build/Clients/.gitkeep` so the directory exists in fresh clones before first sync

## Project Constraints (from CLAUDE.md)

These directives must be honored by the planner:

- **Data ownership:** All data lives in local git repo (`vault-build/` IS in repo, as committed transport). iCloud canonical vault is NOT in repo (Apple-managed; user-owned content). [Aligned with D-01, D-02, D-17a.]
- **Privacy:** Email content and business data must not leak to third-party services. Sync layer reads only local `data/` NDJSON and writes only to local files. No external API calls. [Aligned.]
- **NDJSON conventions:** Append-only, one JSON object per line, ISO 8601 with TZ offset. Sync layer reads NDJSON, never writes it. [Aligned.]
- **Schemas:** All NDJSON record shapes are in `schemas/*.json`. Sync layer must validate against these before consuming. [Aligned via Wave 0 validation step.]
- **MCP usage:** Use ONLY `hardened-workspace` for Gmail/Drive. Phase 10 doesn't touch Gmail or Drive directly — it reads triage records that hardened-workspace previously populated. [Aligned by not introducing new MCP dependencies.]
- **Server sync:** After committing data changes, run `bash scripts/push-and-sync.sh` instead of raw `git push` to push AND sync the Coolify server. **Phase 10 must extend `push-and-sync.sh` to ensure `vault-build/` is included in pushed changes.** [Action item for the planner.]
- **GSD workflow:** All file edits go through GSD commands. [Standard practice; planner-aware.]
- **Atomic git commit per logical operation:** One commit per sync run; vault-build/ commit message format `data: sync vault-build after {trigger}`. [Aligned with existing repo conventions.]
- **`triage-inbox.md`, `task.md`, `invoice.md` already commit dashboard data after their writes:** Phase 10 inserts the vault-build/ sync step BEFORE the commit, so vault-build files are included in the same commit. [Verified by reading the existing slash command files.]

## Sources

### Primary (HIGH confidence)
- [Apple launchd developer documentation — Creating Launch Daemons and Agents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html) — LaunchAgent plist semantics, KeepAlive, RunAtLoad
- [launchd.plist(5) man page](https://keith.github.io/xcode-man-pages/launchd.plist.5.html) — explicit "WatchPaths is highly discouraged" guidance
- [git-scm.com githooks docs](https://git-scm.com/docs/githooks) — post-merge hook behavior, --rebase caveat
- [Python `os.replace` and `tempfile` stdlib](https://docs.python.org/3/library/os.html#os.replace) — atomic rename POSIX guarantee
- [LWN.net atomic writes article](https://lwn.net/Articles/789600/) — fsync directory rationale
- [Obsidian forum: ISO 8601 with timezone offset support in v1.4.3](https://forum.obsidian.md/t/properties-time-type-support-for-iso-8601-standard/64532) — confirmed Obsidian Properties accepts `+10:30` offsets
- [ruamel.yaml official docs](https://yaml.dev/doc/ruamel.yaml/overview/) — round-trip preservation
- Direct repo inspection: `schemas/*.json`, `scripts/{build-dashboard-data,push-and-sync,validate-data}.sh`, `.claude/commands/{triage-inbox,task,invoice}.md`, `data/config/clients.jsonl`, sample triage/task/invoice/feed records

### Secondary (MEDIUM confidence)
- [zottmann.org iCloud Drive Sync Deep Dive (Sept 2025)](https://zottmann.org/2025/09/08/ios-icloud-drive-synchronization-deep.html) — foreground-vs-background latency, no-force-sync API
- [techgarden.alphasmanifesto.com — Manually downloading or evicting iCloud files](https://techgarden.alphasmanifesto.com/mac/Manually-downloading-or-evicting-iCloud-files) — `brctl download`, `.icloud` placeholders
- [Eclectic Light: How to fix problems with iCloud and iCloud Drive](https://eclecticlight.co/2023/07/24/how-to-fix-problems-with-icloud-and-icloud-drive/) — daemon coordination, troubleshooting
- [allenap.me on flock(2) macOS vs Linux](https://allenap.me/posts/flock-behaviour) — portability differences (Mac-side single-writer design avoids these)
- [launchd.info tutorial](https://www.launchd.info/) — common patterns, gotchas
- [kepano/obsidian-skills GitHub](https://github.com/kepano/obsidian-skills) — confirms obsidian-cli requires Obsidian open (D-17 rationale)
- [oreate AI: ruamel.yaml vs PyYAML comparison](https://www.oreateai.com/blog/choosing-between-ruamelyaml-and-pyyaml-a-comprehensive-comparison/2ca85e856751622588a46a00a9a8e664) — round-trip semantics
- [mandalivia.com: Weekly project review with Claude Code and Obsidian CLI](https://www.mandalivia.com/obsidian/weekly-project-review-with-claude-code-and-obsidian-cli/) — log convention adapted for D-12

### Tertiary (LOW confidence — flagged)
- macOS bash 3.2.57 limitations — based on local `bash --version` and known macOS-shipped-bash history. Worth verifying with planner if any Mac-side bash logic seems tricky.
- Specifics of Coolify container's Python availability and version — Wave 0 must verify.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every component directly verified or sourced from primary docs
- Architecture (3-tier transport): HIGH — D-01..D-03 lock the model; research fills implementation only
- Marker-aware atomic writes: HIGH — primitives (POSIX rename, fsync, mkstemp) are stdlib; algorithm is straightforward
- launchd + fswatch daemon: MEDIUM — fswatch is established but the install/configure path on a specific Mac Studio has device-specific risk (homebrew availability, iCloud Optimize-Mac-Storage setting)
- Slug algorithm: HIGH — Unicode NFKD + ASCII-encode is well-known
- Frontmatter conventions: HIGH — Obsidian Properties + DataView both accept snake_case ISO 8601 with TZ offsets
- Pitfalls: HIGH for code-side pitfalls (markers, atomic writes); MEDIUM for iCloud-specific edge cases (placeholder eviction, cloudd timing)

**Research date:** 2026-05-01
**Valid until:** 2026-06-01 (most components stable; check fswatch and ruamel.yaml versions before install)

## RESEARCH COMPLETE

**Phase:** 10 - Obsidian Knowledge Layer (Client Notes)
**Confidence:** HIGH

### Key Findings

- **Sync layer language: Python 3.11+** (single module under `scripts/lib/vault_writer.py` with thin Bash wrappers). Stdlib coverage is decisive — `os.replace`, `tempfile`, `unicodedata`, `pathlib` cover every primitive needed.
- **Mac daemon: fswatch + LaunchAgent + KeepAlive**, NOT launchd `WatchPaths` (Apple explicitly discourages it). 30s SLA achievable with `fswatch --latency 2` and the existing iCloud-to-iPhone path.
- **`last_synced` lives in per-note frontmatter**, not a global state file — better crash resilience, locality, and survives the regenerate-from-full sync invariant.
- **Concurrency on Coolify: `flock` advisory lock on a sentinel file** under `scripts/.vault-sync.lock`. Defensive insurance; in-Claude-session sequencing covers most cases.
- **Slug algorithm: NFKD + ASCII-encode + character-class regex**, with empty-result fallback to domain-derived slug. Collisions resolved by `slug--domain-slug` form.
- **Marker integrity check is the daemon's most important safety property** — exactly-1 START + exactly-1 END counts; mismatch ABORTS and logs `system`/`critical` per D-08a.
- **kepano `obsidian-cli` is not viable** for either Coolify (headless) or Mac daemon (unattended) — confirmed via research that it requires Obsidian app to be open.
- **OVERVIEW marker pair tension with D-08:** Overview is Glen-owned per D-07 (sync NEVER reads/writes), so empty OVERVIEW markers add code-burden without value. **Recommend dropping OVERVIEW markers from v1; planner can flag during /gsd-plan-phase.**

### File Created

`/Users/glenr/work/todo-list/.planning/phases/10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli/10-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Every component directly verified or sourced from primary docs |
| Architecture (3-tier transport) | HIGH | D-01..D-03 lock the model; research only fills implementation |
| Marker-aware atomic writes | HIGH | POSIX primitives + clear algorithm |
| launchd + fswatch daemon | MEDIUM | Tooling well-known; Mac Studio device-specific install path has minor risk (brew, iCloud storage settings) |
| Slug algorithm | HIGH | Unicode NFKD is the canonical pattern |
| Frontmatter conventions | HIGH | Obsidian + DataView agree on snake_case ISO 8601 |
| Pitfalls | HIGH (code) / MEDIUM (iCloud edges) | Code-level pitfalls well-understood; iCloud quirks have residual unknowns |

### Open Questions for the Planner

1. **Mac Studio git-pull cadence** — manual, cron, or webhook? Recommendation: cron `git pull --ff-only` every 60s.
2. **Mac daemon install ergonomics** — ship `mac/install-daemon.sh` for one-shot install? Recommendation: yes.
3. **OVERVIEW marker pair** — drop from v1? (See Tension with D-08 in Pattern 2.) Recommendation: drop.
4. **Triage `dismissed` field schema drift** — strict or lenient validation? Recommendation: lenient on read, flag for separate cleanup phase.
5. **Orphan note handling when client removed from clients.jsonl** — auto-delete or leave? Recommendation: leave; manual `git rm`.

### Ready for Planning

Research complete. Planner can now create PLAN.md files. Recommended wave structure:
- **Wave 0:** Dependencies (pip install ruamel.yaml on Coolify, brew install fswatch on Mac), `vault-build/Clients/.gitkeep`, dry-run flag, test scaffold
- **Wave 1:** Sync layer core — `scripts/lib/vault_writer.py` with backfill mode, slugify, marker splice, atomic write
- **Wave 2:** Coolify integration — slash command extensions (triage-inbox.md, task.md, invoice.md), `scripts/sync-obsidian.sh` wrapper with flock, `push-and-sync.sh` extension
- **Wave 3:** Mac daemon — `mac/com.agend.vault-sync.plist`, `mac/vault-sync-watcher.sh`, `mac/install-daemon.sh`, `mac/README.md`, projection mode in vault_writer.py
- **Wave 4:** Backfill execution + verification — run `--backfill`, manual install daemon, end-to-end smoke test (Coolify write → push → Mac pull → iCloud project → iPhone display)
