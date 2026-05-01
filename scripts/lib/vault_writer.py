"""Phase 10 Obsidian vault sync engine.

Single-module sync layer for `vault-build/Clients/<slug>.md`. Owns:

- NDJSON ingestion from `data/triage/`, `data/tasks/`, `data/invoices/`, `data/todos/`
- Per-client routing via canonical `client_domain` against `data/config/clients.jsonl` (D-04, D-05)
- Slug generation with NFKD normalization + ASCII fold + collision suffix (D-06, Pattern 5)
- ruamel.yaml round-trip frontmatter (D-09, Pattern 6) with snake_case ISO-8601-with-offset
- Marker-aware atomic markdown splice with D-08a ABORT semantics (Pattern 1)
- D-10 triage filter (priority urgent/needs-response OR non-empty action_items)
- D-11 unconditional task/invoice logging
- D-12 activity-log line shape: `### [YYYY-MM-DD HH:MM] {emoji} {summary}`
- D-15a stub note shape for clients with zero records
- D-14/D-16 idempotency: regenerate-from-full produces byte-identical managed sections
- `--feed-path` argparse arg threading the system/critical feed-entry destination through
  every code path; tests pass a temp path so production `data/feed.jsonl` is never polluted
  (Issue 1 + Issue 6).

Modes (CLI):
    backfill     - rebuild every note from full data/ history
    incremental  - per Pattern 3 simplification, also regenerates from full data in v1

References: see .planning/phases/10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli/
10-CONTEXT.md (D-XX decisions), 10-RESEARCH.md (Patterns 1, 3, 5, 6, 7, 8), schemas/feed-entry.json.
"""

import argparse
import collections
import json
import os
import re
import sys
import tempfile
import traceback
import unicodedata
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Iterator

from ruamel.yaml import YAML


# Constants ---------------------------------------------------------------

EMOJI_BY_KIND = {"triage": "📧", "task": "✅", "invoice": "💰"}
GMAIL_THREAD_URL = "https://mail.google.com/mail/u/0/#inbox/{thread_id}"
# OVERVIEW marker pair dropped per researcher recommendation; D-08 keeps OPEN-ITEMS + ACTIVITY-LOG.
MANAGED_SECTIONS = ("OPEN-ITEMS", "ACTIVITY-LOG")
TS_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
_VALID_CHARS_RE = re.compile(r"[^a-z0-9-]+")
_DASH_RUN_RE = re.compile(r"-{2,}")

# Triage priority bucket names that occasionally leak into `client_name` upstream;
# Pattern 8 / D-06a uses these to annotate the _Unknown.md groups for cleanup.
_PRIORITY_BUCKET_NAMES = frozenset({"urgent", "needs-response", "informational", "low-priority"})


# Errors ------------------------------------------------------------------

class MarkerError(Exception):
    """Raised when section markers are missing/duplicated/malformed (D-08a)."""


# Slug helpers (Pattern 5) ------------------------------------------------

def slugify(name: str) -> str:
    """NFKD-normalize, ASCII-fold, lowercase, collapse non-[a-z0-9] to '-', trim dashes."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    dashed = _VALID_CHARS_RE.sub("-", lowered)
    collapsed = _DASH_RUN_RE.sub("-", dashed)
    return collapsed.strip("-")


def slug_with_domain(name: str, domain: str) -> str:
    """Collision-resistant variant: `{name-slug}--{domain-slug}`."""
    base = slugify(name)
    domain_part = slugify(domain.replace(".", "-"))
    return f"{base}--{domain_part}"


def safe_slugify(name: str, domain: str) -> str:
    """Slugify name; fall back to domain; finally to 'client-unknown'. Never returns ''."""
    s = slugify(name)
    if not s:
        s = slugify(domain.replace(".", "-"))
    if not s:
        s = "client-unknown"
    return s


# Marker-aware atomic write (Pattern 1) -----------------------------------

def replace_managed_section(file_path: Path, section_name: str, new_content: str) -> None:
    """Splice `new_content` between `<!-- {section_name}-START -->` and `-END` markers.

    Atomic via tempfile + os.replace + fsync(file) + fsync(dir). Raises MarkerError per D-08a
    when markers are missing, duplicated, or out of order. Preserves all bytes outside the
    marker pair.
    """
    original = file_path.read_text(encoding="utf-8")

    start_re = re.compile(rf"<!--\s*{re.escape(section_name)}-START\s*-->")
    end_re = re.compile(rf"<!--\s*{re.escape(section_name)}-END\s*-->")
    starts = list(start_re.finditer(original))
    ends = list(end_re.finditer(original))

    if len(starts) != 1 or len(ends) != 1:
        raise MarkerError(
            f"{file_path}: expected exactly 1 {section_name}-START and 1 {section_name}-END, "
            f"got {len(starts)} starts, {len(ends)} ends"
        )
    if starts[0].end() > ends[0].start():
        raise MarkerError(f"{file_path}: {section_name}-END appears before -START")

    new_text = (
        original[: starts[0].end()]
        + "\n"
        + new_content.rstrip("\n")
        + "\n"
        + original[ends[0].start():]
    )

    dir_path = file_path.parent
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix=f".{file_path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
        # fsync the containing directory so iCloud/cloudd cannot upload a partial state.
        dir_fd = os.open(dir_path, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


# Feed-entry helpers (D-08a + Issue 1 + Issue 6) --------------------------

def now_iso_with_offset() -> str:
    """ISO 8601 with timezone offset matching `feed-entry.json` regex.

    `datetime.now().astimezone()` resolves the local TZ; `isoformat(timespec='seconds')`
    drops microseconds and emits the `±HH:MM` offset suffix that the schema requires.
    """
    return datetime.now().astimezone().isoformat(timespec="seconds")


def handle_marker_error_for_feed(*, file_path: Path, section: str, reason: str) -> dict:
    """Build the system/critical feed entry for a marker-integrity ABORT.

    Returns a dict matching `schemas/feed-entry.json` (additionalProperties: false on the
    top level). Caller appends via `append_feed_entry` so writing is testable separately.
    """
    summary = f"vault-sync marker error: {file_path.name} ({section})"
    if len(summary) > 200:
        summary = summary[:197] + "..."
    return {
        "ts": now_iso_with_offset(),
        "type": "system",
        "summary": summary,
        "level": "critical",
        "trigger": "hook",
        "details": {
            "file": str(file_path),
            "section": section,
            "reason": reason,
        },
    }


def append_feed_entry(entry: dict, *, feed_path: Path) -> None:
    """Append a single NDJSON feed entry to `feed_path`.

    Open in 'a' mode so the single-line write is atomic up to PIPE_BUF (RESEARCH Pitfall 3).
    Creates parent directories if missing — the threaded `--feed-path` may live anywhere
    (production: `<data_root>/feed.jsonl`; tests: temp dir).
    """
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    with open(feed_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# Activity-log line rendering (D-12) --------------------------------------

def render_log_line(*, rec_ts_iso: str, kind: str, summary: str,
                    detail: str | None = None, gmail_thread_id: str | None = None) -> str:
    """D-12 line shape:

        ### [YYYY-MM-DD HH:MM] {emoji} {summary}
        > {detail}                          (only if detail given)
        > [Open thread]({gmail-url})        (only if gmail_thread_id given)

    Emojis per kind: triage→📧, task→✅, invoice→💰 (EMOJI_BY_KIND).
    """
    if kind not in EMOJI_BY_KIND:
        raise ValueError(f"unknown kind: {kind!r} (expected one of {list(EMOJI_BY_KIND)})")
    # "2026-05-01T10:30:00+10:30" → "2026-05-01 10:30"
    short_ts = rec_ts_iso[:16].replace("T", " ")
    line = f"### [{short_ts}] {EMOJI_BY_KIND[kind]} {summary}\n"
    if detail:
        line += f"> {detail}\n"
    if gmail_thread_id:
        line += f"> [Open thread]({GMAIL_THREAD_URL.format(thread_id=gmail_thread_id)})\n"
    return line


# YAML helper --------------------------------------------------------------

def _yaml_instance() -> YAML:
    """Centralized ruamel.yaml configuration so frontmatter render stays consistent.

    `preserve_quotes=True` keeps strings exactly as written by Glen; default block-style
    flow (one key per line) is what DataView parses cleanly per Pattern 6.
    """
    y = YAML()
    y.preserve_quotes = True
    y.indent(mapping=2, sequence=4, offset=2)
    return y


# =========================================================================
# Task 2: backfill / incremental orchestrators + CLI (--feed-path threading)
# =========================================================================


# Note template (Pattern 2; OVERVIEW marker pair dropped per researcher recommendation) -----

_NOTE_TEMPLATE = """\
{frontmatter}
## Overview

_No notes yet — replace this line with relationship context._

<!-- DO NOT EDIT BETWEEN MARKERS — managed by /sync-obsidian -->
<!-- OPEN-ITEMS-START -->
## Open Items

{open_items}
<!-- OPEN-ITEMS-END -->

<!-- DO NOT EDIT BETWEEN MARKERS — managed by /sync-obsidian -->
<!-- ACTIVITY-LOG-START -->
## Activity Log

{activity_log}
<!-- ACTIVITY-LOG-END -->

## Decisions

_(Glen-edited; auto-extraction deferred to a future phase)_
"""

_UNKNOWN_TEMPLATE = """\
{frontmatter}
## Overview

_Auto-generated bucket of unmatched records. Surfaced for cleanup per D-06a._

<!-- DO NOT EDIT BETWEEN MARKERS — managed by /sync-obsidian -->
<!-- OPEN-ITEMS-START -->
## Open Items

_(none)_
<!-- OPEN-ITEMS-END -->

<!-- DO NOT EDIT BETWEEN MARKERS — managed by /sync-obsidian -->
<!-- ACTIVITY-LOG-START -->
## Activity Log

{activity_log}
<!-- ACTIVITY-LOG-END -->

## Decisions

_(Glen-edited; auto-extraction deferred to a future phase)_
"""


# Atomic full-file write helper (Pattern 1 sibling for whole-file recreate path) ---

def _atomic_write(file_path: Path, content: str) -> None:
    """Write `content` to `file_path` via tempfile + os.replace + fsync(file+dir).

    Sibling of `replace_managed_section` for the from-scratch recreate path.
    Used during regenerate-from-full backfill where the whole file is rewritten.
    """
    dir_path = file_path.parent
    dir_path.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix=f".{file_path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
        dir_fd = os.open(dir_path, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


# Client registry loader (D-04, D-06) -------------------------------------

def load_clients(data_root: Path) -> dict[str, dict]:
    """Read `<data_root>/config/clients.jsonl` → dict mapping `domain` to client info.

    Each value: `{"slug": str, "client_name": str, "domain": str, "status": "active"}`.

    Slug computed via `safe_slugify(name, domain)`. If two clients map to the same slug,
    BOTH are switched to the `slug_with_domain` collision-resistant form (Pattern 5)
    and a stderr message is emitted. Missing/empty clients.jsonl returns `{}`.
    """
    clients_path = data_root / "config" / "clients.jsonl"
    out: dict[str, dict] = {}
    if not clients_path.exists():
        print(f"[load_clients] WARN: {clients_path} not found", file=sys.stderr)
        return out

    raw_entries: list[dict] = []
    for rec in stream_ndjson(clients_path):
        # Tolerate both `name` and `client_name` keys; clients.jsonl currently uses `name`.
        name = rec.get("name") or rec.get("client_name") or ""
        domain = rec.get("domain") or ""
        if not domain:
            print(f"[load_clients] WARN: skipping entry without domain: {rec!r}", file=sys.stderr)
            continue
        raw_entries.append({"name": name, "domain": domain, "status": rec.get("status", "active")})

    # First pass: assign safe slug per client.
    for r in raw_entries:
        out[r["domain"]] = {
            "slug": safe_slugify(r["name"], r["domain"]),
            "client_name": r["name"],
            "domain": r["domain"],
            "status": r["status"],
        }

    # Collision detection: any slug owned by ≥2 domains is rewritten to slug_with_domain
    # for ALL of its owners (Pattern 5).
    by_slug: dict[str, list[str]] = collections.defaultdict(list)
    for domain, info in out.items():
        by_slug[info["slug"]].append(domain)
    for slug, owners in by_slug.items():
        if len(owners) > 1:
            print(
                f"[load_clients] slug collision on {slug!r}: {owners} — switching all "
                f"to slug_with_domain form",
                file=sys.stderr,
            )
            for d in owners:
                out[d]["slug"] = slug_with_domain(out[d]["client_name"], d)

    return out


# NDJSON streaming (Pattern 3 + repo convention) --------------------------

def stream_ndjson(path: Path) -> Iterator[dict]:
    """Yield JSON-decoded lines from `path`; lenient on blank/bad lines.

    Skips empty lines silently; logs malformed lines to stderr but continues —
    the regenerate-from-full backfill must not abort on a single corrupt record
    (T-10-06 mitigation).
    """
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[stream_ndjson] WARN: {path}:{lineno} skip malformed: {e}",
                      file=sys.stderr)


# D-10 triage filter ------------------------------------------------------

def d10_triage_filter(rec: dict) -> bool:
    """Per D-10: only triage records with priority urgent/needs-response OR non-empty
    action_items hit the Activity Log. Informational/low-priority/admin emails stay in
    `data/triage/` but don't pollute notes.
    """
    if rec.get("priority") in {"urgent", "needs-response"}:
        return True
    items = rec.get("action_items") or []
    return isinstance(items, list) and len(items) > 0


# Routing (D-04, D-05) ----------------------------------------------------

def _route_to_slug(rec: dict, clients: dict[str, dict]) -> str:
    """Return the client slug for a record; `_Unknown` when no exact domain match.

    Per D-05, only `client_domain` (or `domain`) is used for routing — `client_name`
    is display-only and would otherwise leak the priority-bucket-name bug into notes.
    """
    domain = rec.get("client_domain") or rec.get("domain") or ""
    if domain and domain in clients:
        return clients[domain]["slug"]
    return "_Unknown"


# Event extraction --------------------------------------------------------

def _event_tuple(rec: dict, kind: str) -> tuple:
    """Build `(ts, kind, summary, detail, gmail_thread_id)` for the Activity Log.

    `ts` falls back through `ts` → `received` → `created_at` → `completed_at`. Records
    missing all four are tagged with epoch-zero so they sort to the bottom rather than
    crashing the renderer.
    """
    ts = (
        rec.get("ts")
        or rec.get("received")
        or rec.get("created_at")
        or rec.get("completed_at")
        or "1970-01-01T00:00:00+00:00"
    )

    if kind == "triage":
        summary = rec.get("subject") or rec.get("summary") or "(no subject)"
        detail_bits = []
        priority = rec.get("priority")
        if priority:
            detail_bits.append(priority)
        action_type = rec.get("action_type")
        if action_type and action_type != "none":
            detail_bits.append(action_type)
        items = rec.get("action_items") or []
        if items:
            first = items[0]
            detail_bits.append(first if len(first) <= 80 else first[:77] + "...")
        detail = " · ".join(detail_bits) if detail_bits else None
        gmail_thread_id = rec.get("thread_id")
        return (ts, kind, summary, detail, gmail_thread_id)

    if kind == "task":
        rec_id = rec.get("id", "task-?")
        status = rec.get("status", "?")
        desc = rec.get("description") or ""
        summary = f"{rec_id} {status}"
        if desc:
            summary += f" — {desc if len(desc) <= 80 else desc[:77] + '...'}"
        outcome = rec.get("outcome")
        detail = outcome if outcome else None
        return (ts, kind, summary, detail, None)

    if kind == "invoice":
        rec_id = rec.get("id", "inv-?")
        status = rec.get("status", "?")
        amount = rec.get("amount")
        summary = f"{rec_id} {status}"
        if amount is not None:
            summary += f" (${amount})"
        detail = rec.get("description") or rec.get("note") or None
        return (ts, kind, summary, detail, None)

    # Unknown kind — render as best we can.
    summary = str(rec.get("id") or rec.get("summary") or rec)[:80]
    return (ts, kind, summary, None, None)


# Section renderers -------------------------------------------------------

def render_open_items(slug: str, todos: list, tasks: list, clients: dict[str, dict]) -> str:
    """Markdown bullet list of open todos + open tasks routed to this client.

    Routing uses `_route_to_slug` so the same D-05 exact-domain rule applies.
    Empty result → `_(none)_` so the section is never visually blank.
    """
    bullets: list[str] = []

    for todo in todos:
        if _route_to_slug(todo, clients) != slug:
            continue
        status = (todo.get("status") or "").lower()
        if status in {"done", "completed", "closed"}:
            continue
        text = todo.get("text") or todo.get("description") or todo.get("title") or "(unlabeled todo)"
        todo_id = todo.get("id", "")
        if todo_id:
            bullets.append(f"- [ ] {text} (`{todo_id}`)")
        else:
            bullets.append(f"- [ ] {text}")

    for task in tasks:
        if _route_to_slug(task, clients) != slug:
            continue
        status = (task.get("status") or "").lower()
        if status in {"completed", "done", "closed", "cancelled"}:
            continue
        desc = task.get("description") or "(unlabeled task)"
        task_id = task.get("id", "")
        if task_id:
            bullets.append(f"- [ ] {desc} (`{task_id}`)")
        else:
            bullets.append(f"- [ ] {desc}")

    if not bullets:
        return "_(none)_"
    return "\n".join(bullets)


def render_activity_log(events: list) -> str:
    """Render newest-first activity log via `render_log_line`.

    Each event tuple: `(ts_iso, kind, summary, detail_or_none, gmail_thread_id_or_none)`.
    Empty events list → fallback comment so the section reads cleanly.
    """
    if not events:
        return "<!-- No activity logged for this client yet -->"
    # Sort by ts ASC then reverse → newest first; stable so equal ts preserve insertion order.
    sorted_events = sorted(events, key=lambda e: e[0])
    sorted_events.reverse()
    lines = []
    for ts_iso, kind, summary, detail, gmail_thread_id in sorted_events:
        lines.append(render_log_line(
            rec_ts_iso=ts_iso,
            kind=kind,
            summary=summary,
            detail=detail,
            gmail_thread_id=gmail_thread_id,
        ))
    return "\n".join(lines).rstrip("\n")


def render_frontmatter(client: dict, last_synced_iso: str) -> str:
    """ruamel.yaml round-tripped frontmatter (D-09 v1: 4 fields, snake_case)."""
    fm = {
        "domain": client["domain"],
        "client_name": client["client_name"],
        "status": client.get("status", "active"),
        "last_synced": last_synced_iso,
    }
    buf = StringIO()
    _yaml_instance().dump(fm, buf)
    return f"---\n{buf.getvalue()}---\n"


def build_note_initial_markdown(client: dict, fm_str: str, open_items: str,
                                activity_log: str) -> str:
    """Assemble the full note from the Pattern 2 marker template.

    Used on every backfill run since vault-build/ is regenerated from full data
    (D-02 transport rail; user-owned-section preservation is a Plan 04 concern).
    """
    return _NOTE_TEMPLATE.format(
        frontmatter=fm_str.rstrip("\n"),
        open_items=open_items,
        activity_log=activity_log,
    )


def render_unknown_note(unmatched_events: list, last_synced_iso: str) -> str:
    """Pattern 8: group unmatched events by closest available identifier.

    Preference order per group label:
      1. `client_name` if present AND not a triage priority bucket name
         ("needs-response" etc. — these are the documented data-quality leak)
      2. email-domain part of `from`
      3. `"no-identifier"`
    """
    fm_str = render_frontmatter(
        {"domain": "", "client_name": "Unknown", "status": "unknown"},
        last_synced_iso,
    )

    if not unmatched_events:
        return _UNKNOWN_TEMPLATE.format(
            frontmatter=fm_str.rstrip("\n"),
            activity_log="<!-- No unmatched records — this is the expected steady state -->",
        )

    # `unmatched_events` here is a list of (event_tuple, source_record) pairs so we can
    # pull labels from the original record. Backwards compatible: if it's just tuples,
    # synthesize a label from "no-identifier".
    groups: dict[str, list] = collections.defaultdict(list)
    leaked_priority_groups: set[str] = set()
    for item in unmatched_events:
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], dict):
            event_tuple, src = item
        else:
            event_tuple, src = item, {}

        client_name = src.get("client_name") or ""
        if client_name and client_name not in _PRIORITY_BUCKET_NAMES:
            label = client_name
        elif client_name in _PRIORITY_BUCKET_NAMES:
            label = client_name
            leaked_priority_groups.add(label)
        else:
            from_addr = src.get("from") or ""
            if "@" in from_addr:
                label = from_addr.split("@", 1)[1].strip().lower() or "no-identifier"
            else:
                label = "no-identifier"
        groups[label].append(event_tuple)

    body_parts: list[str] = []
    for label in sorted(groups):
        events = groups[label]
        body_parts.append(f"### Group: {label} ({len(events)} records)")
        if label in leaked_priority_groups:
            body_parts.append(
                f"> **Data-quality flag:** `{label}` is a triage priority bucket name that "
                f"leaked into `client_name` upstream. Glen, please clean these records."
            )
        body_parts.append(render_activity_log(events))
        body_parts.append("")  # blank line between groups

    return _UNKNOWN_TEMPLATE.format(
        frontmatter=fm_str.rstrip("\n"),
        activity_log="\n".join(body_parts).rstrip("\n"),
    )


# Backfill / incremental orchestrators (D-13, D-14, D-15, D-15a, D-16) ----

def _gather_events(data_root: Path, clients: dict[str, dict]) -> tuple[dict, list]:
    """Stream all data sources → bucket events by client slug.

    Returns `(events_by_slug, unknown_pairs)` where `unknown_pairs` is a list of
    `(event_tuple, source_record)` for the _Unknown.md grouping pass.
    """
    events_by_slug: dict[str, list] = collections.defaultdict(list)
    unknown_pairs: list = []

    # Triage: D-10 filter
    triage_dir = data_root / "triage"
    if triage_dir.exists():
        for triage_file in sorted(triage_dir.glob("*.jsonl")):
            for rec in stream_ndjson(triage_file):
                if not d10_triage_filter(rec):
                    continue
                slug = _route_to_slug(rec, clients)
                evt = _event_tuple(rec, "triage")
                if slug == "_Unknown":
                    unknown_pairs.append((evt, rec))
                else:
                    events_by_slug[slug].append(evt)

    # Tasks/invoices: D-11 unconditional
    for kind, rel_path in (("task", Path("tasks") / "active.jsonl"),
                            ("invoice", Path("invoices") / "active.jsonl")):
        for rec in stream_ndjson(data_root / rel_path):
            slug = _route_to_slug(rec, clients)
            evt = _event_tuple(rec, kind)
            if slug == "_Unknown":
                unknown_pairs.append((evt, rec))
            else:
                events_by_slug[slug].append(evt)

    return events_by_slug, unknown_pairs


def run_backfill(data_root: Path, build_root: Path, dry_run: bool = False,
                 feed_path: Path | None = None) -> dict:
    """Regenerate every client note from full `data/` history (D-15, D-16).

    Args:
        data_root: directory containing `config/clients.jsonl`, `triage/`, `tasks/`, etc.
        build_root: target root; notes land at `<build_root>/Clients/<slug>.md`.
        dry_run: if True, print `[dry-run] would write …` and write nothing.
        feed_path: where critical feed entries land on failure. Default: `<data_root>/feed.jsonl`.
            Tests override to a temp path so production audit trail is never polluted (Issue 1).

    Returns: `{"clients_written": int, "events_routed": int}`.

    Idempotent (D-14, D-16): two consecutive runs produce byte-identical managed sections
    excluding the `last_synced` frontmatter line.
    """
    last_synced = now_iso_with_offset()
    if feed_path is None:
        feed_path = data_root / "feed.jsonl"

    # Hard precondition: data_root must exist. Missing config/clients.jsonl is
    # tolerable (load_clients warns + returns {}), but a non-existent data_root
    # is a configuration error that must surface as a failure-path feed entry
    # (Issue 1 — TestMain.test_main_failure_path_writes_critical_feed_to_temp).
    if not data_root.exists():
        raise FileNotFoundError(
            f"data_root does not exist: {data_root}"
        )

    clients = load_clients(data_root)
    todos = list(stream_ndjson(data_root / "todos" / "active.jsonl"))
    tasks = list(stream_ndjson(data_root / "tasks" / "active.jsonl"))
    events_by_slug, unknown_pairs = _gather_events(data_root, clients)

    output_dir = build_root / "Clients"
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    # Stub note for every client even with no records (D-15a)
    for domain, client in clients.items():
        slug = client["slug"]
        events = events_by_slug.get(slug, [])
        fm = render_frontmatter(client, last_synced)
        oi = render_open_items(slug, todos, tasks, clients)
        al = render_activity_log(events)
        path = output_dir / f"{slug}.md"
        if dry_run:
            print(f"[dry-run] would write {path}")
            continue
        content = build_note_initial_markdown(client, fm, oi, al)
        _atomic_write(path, content)
        written.append(path)

    # Always create _Unknown.md per D-15a — the empty-state stub still serves as
    # the documented "no leaks today" signal Glen reads on iPhone.
    unknown_path = output_dir / "_Unknown.md"
    unknown_content = render_unknown_note(unknown_pairs, last_synced)
    if dry_run:
        print(f"[dry-run] would write {unknown_path}")
    else:
        _atomic_write(unknown_path, unknown_content)
        written.append(unknown_path)

    events_routed = sum(len(v) for v in events_by_slug.values()) + len(unknown_pairs)
    return {"clients_written": len(written), "events_routed": events_routed}


def run_incremental(data_root: Path, build_root: Path, record_type: str = "all",
                    dry_run: bool = False, feed_path: Path | None = None) -> dict:
    """Per Pattern 3 simplification, v1 incremental ALSO regenerates from full data.

    Functionally equivalent to `run_backfill`; `record_type` accepted for CLI parity
    but unused in v1. `feed_path` semantics same as `run_backfill`.

    TODO(future): per-client touched-set optimization once volume warrants it.
    """
    return run_backfill(data_root, build_root, dry_run=dry_run, feed_path=feed_path)


# CLI entry point (Issue 1 + Issue 6 — --feed-path threading) -------------

def main() -> None:
    """argparse CLI — `--feed-path` threaded through every code path that may write
    a critical feed entry.

    Failure-path invariant: any uncaught exception in run_backfill / run_incremental
    is caught here and converted to a system/critical feed entry written to the
    threaded `--feed-path`, then the process exits 1. The default `feed_path` is
    resolved at the CLI boundary so library calls and the failure-path handler
    share the exact same value (no accidental hardcode of `data/feed.jsonl`).
    """
    p = argparse.ArgumentParser(prog="vault_writer")
    p.add_argument("--mode", choices=["backfill", "incremental"], required=True)
    p.add_argument("--data-root", default=Path("data"), type=Path)
    p.add_argument("--build-root", default=Path("vault-build"), type=Path)
    p.add_argument("--record-type", choices=["triage", "task", "invoice", "all"], default="all")
    p.add_argument("--record-id", default=None)  # accepted for hook parity; unused in v1
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--feed-path",
        type=Path,
        default=None,
        help=(
            "NDJSON feed-entry destination for system/critical entries. "
            "Default: <data_root>/feed.jsonl. Tests pass a temp path so the "
            "production audit trail is never polluted (Issue 1 + Issue 6)."
        ),
    )
    args = p.parse_args()

    # Resolve feed_path default ONCE at CLI boundary so library calls and the
    # failure-path handler share the same value.
    feed_path = args.feed_path if args.feed_path is not None else (args.data_root / "feed.jsonl")

    try:
        if args.mode == "backfill":
            stats = run_backfill(args.data_root, args.build_root,
                                 dry_run=args.dry_run, feed_path=feed_path)
        else:
            stats = run_incremental(args.data_root, args.build_root,
                                    record_type=args.record_type,
                                    dry_run=args.dry_run, feed_path=feed_path)
        print(f"vault_writer {args.mode} complete: {stats}")
    except Exception as e:
        entry = {
            "ts": now_iso_with_offset(),
            "type": "system",
            "summary": f"vault_writer {args.mode} failed: {type(e).__name__}",
            "level": "critical",
            "trigger": "hook",
            "details": {
                "mode": args.mode,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc()[-1000:],
            },
        }
        try:
            # CRITICAL: write to the threaded feed_path, NEVER hardcode data/feed.jsonl.
            # This protects Glen's production audit trail when tests run main() against
            # /nonexistent --data-root paths (Issue 1).
            append_feed_entry(entry, feed_path=feed_path)
        except Exception:
            pass  # don't recurse if logging itself fails
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


__all__ = [
    "MarkerError",
    "slugify", "slug_with_domain", "safe_slugify",
    "replace_managed_section",
    "handle_marker_error_for_feed", "append_feed_entry", "now_iso_with_offset",
    "render_log_line",
    "EMOJI_BY_KIND", "MANAGED_SECTIONS", "TS_PATTERN",
    "load_clients", "stream_ndjson", "d10_triage_filter",
    "render_open_items", "render_activity_log", "render_frontmatter",
    "render_unknown_note", "build_note_initial_markdown",
    "run_backfill", "run_incremental", "main",
]


if __name__ == "__main__":
    main()
