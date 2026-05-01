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


__all__ = [
    "MarkerError",
    "slugify", "slug_with_domain", "safe_slugify",
    "replace_managed_section",
    "handle_marker_error_for_feed", "append_feed_entry", "now_iso_with_offset",
    "render_log_line",
    "EMOJI_BY_KIND", "MANAGED_SECTIONS", "TS_PATTERN",
    # run_backfill, run_incremental, main — added in Task 2
]
