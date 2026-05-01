---
description: Sync Obsidian vault-build/ from data/ NDJSON history (--backfill or --incremental)
allowed-tools: "Read, Bash(bash scripts/*), Bash(jq *), Bash(date *), Bash(git *), Bash(ls *), Bash(wc *)"
---

# /sync-obsidian — Sync Obsidian vault-build/

Per Phase 10 D-13 (4): standalone manual + scheduled trigger for vault sync. The Mac Studio launchd daemon (Plan 04) handles routine projection automatically; this command is for first-time backfill or after data corrections.

## Mode Detection

- **If $ARGUMENTS contains "--backfill"** -> rebuild every managed section from full history (D-15)
- **If $ARGUMENTS contains "--incremental"** (or empty) -> append since last_synced per note (subject to wrapper-level no-op-delta guard — silently exits 0 if no NDJSON changes have happened since the previous sync)
- **If $ARGUMENTS contains "--dry-run"** -> print changes without writing (Wave 0 gap closure; bypasses the no-op guard so previews are always observable)

## Steps

### Step 1: Run the sync wrapper

```bash
bash scripts/sync-obsidian.sh $ARGUMENTS
```

The wrapper (a) verifies it's running on a flock-capable host (Linux/Coolify only), (b) for `--incremental` mode, short-circuits silently if no NDJSON deltas have occurred since the last sync, (c) acquires a flock on `scripts/.vault-sync.lock` (30s timeout), and (d) invokes `python3 -m scripts.lib.vault_writer` with the matched mode. On uncaught exception, vault_writer's main() writes a `system`/`critical` entry to `data/feed.jsonl` before exiting non-zero.

### Step 2: Report what changed

```bash
git status --short vault-build/
```

Show the user a count of modified/created files. If `--dry-run`, no changes are expected and the user is told nothing to commit. If the wrapper short-circuited on no-op (no NDJSON deltas), `git status --short vault-build/` will be empty — that's the expected outcome.

### Step 3: Stage and commit (skip if --dry-run or no-op)

For non-dry-run modes with actual changes, stage and commit per the repo's `data: sync vault-build after {trigger}` convention (RESEARCH.md line 1012):

```bash
git add vault-build/ data/feed.jsonl
git commit -m "data: sync vault-build after /sync-obsidian"
```

If `git commit` fails because nothing changed (idempotent re-run OR wrapper short-circuited on no-op), continue without error — print "vault-build/ already up to date."

### Step 4: Push (per CLAUDE.md project convention)

Use `bash scripts/push-and-sync.sh` (NOT raw git push) so the Coolify server pulls the change and the Mac Studio daemon can pick it up:

```bash
bash scripts/push-and-sync.sh
```

### Step 5: Report summary

Display:
- Mode invoked
- Number of vault-build/Clients/*.md files modified or created (or "no-op — already up to date" when the wrapper short-circuited)
- Whether the push succeeded
- Note for first-time setup: if this is the first backfill, instruct Glen to install the Mac Studio daemon per `mac/README.md` (Plan 04 deliverable) so the iCloud projection runs automatically. After install, the Mac daemon will project these files into the iCloud canonical vault.

## Notes for Operators

- `--backfill` is always safe to re-run AND ALWAYS runs (the no-op guard is bypassed for backfill, so re-syncs from full history are unconditional). Per D-14/D-16 it produces byte-identical managed sections each time (modulo `last_synced`). The daemon's projection step is also idempotent. There is NO confirmation prompt — managed sections are safe to overwrite by definition.
- `--incremental` is the default; the slash commands `/triage-inbox`, `/task`, `/invoice` all invoke this wrapper internally with `--incremental`. Read-only invocations (e.g. `/task list`) silently no-op via the wrapper's delta guard.
- When in doubt, run `--backfill --dry-run` first to preview the regenerated content before committing.
