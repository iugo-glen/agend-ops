# Phase 11: Contract Manager Integration — Pattern Map

**Mapped:** 2026-05-02
**Files analyzed:** 9 (3 NEW, 6 EXTENDED)
**Analogs found:** 8 / 9 (cm_client.py is genuinely new; nearest precedents are vault_writer.py atomic-write + retry idioms)

## Source Artifacts Read

- `.planning/phases/11-contract-manager-integration-seed-and-refresh-client-note-fr/11-CONTEXT.md` (D-A1..D-F1 + Post-Research Refinements D-C2-REVISED, D-C3-REVISED, D-B-MOD-REVISED, D-A3-REVISED, D-G1)
- `.planning/phases/11-contract-manager-integration-seed-and-refresh-client-note-fr/11-RESEARCH.md` (Architectural Responsibility Map, Pattern 1/2/3 examples, Test Scaffolding, CM Tool Contract Reference)
- `scripts/lib/vault_writer.py` (1201 lines — Phase 10 engine)
- `scripts/tests/test_vault_writer.py` (501 lines — 25 existing tests across 7 test classes)
- `scripts/sync-obsidian.sh` (125 lines — Linux flock wrapper)
- `schemas/feed-entry.json` (47 lines — current `level` enum lacks `warning`)
- `data/config/clients.jsonl` (3 client records, no `cm_client_id` field today)
- `.gitignore` (current entries — pattern target for `data/.cm-cache.json`)
- `scripts/requirements.txt` (only `ruamel.yaml>=0.18,<0.19`)

## File Classification

| Phase 11 File | Status | Role | Data Flow | Closest Analog | Match Quality |
|---------------|--------|------|-----------|----------------|---------------|
| `scripts/lib/cm_client.py` | NEW | service / network-client | request-response (HTTP JSON-RPC) + cache fallback | `scripts/lib/vault_writer.py` (atomic-write idiom) | partial — no existing HTTP client; reuse atomic-write + ISO-ts patterns |
| `scripts/tests/test_cm_client.py` | NEW | test | unit (mock seam) | `scripts/tests/test_vault_writer.py` (TestProjection mock pattern at L460-497) | exact — same `unittest` + `mock.patch` style |
| `data/.cm-cache.json` | NEW (runtime) | data / cache file | file-I/O (atomic whole-file rewrite) | vault_writer `_atomic_write` (vault_writer.py:296-322) | exact — copy idiom verbatim |
| `scripts/lib/vault_writer.py` | EXTENDED | service / orchestrator | request-response + file-I/O | self (Phase 10 — extending in place) | n/a |
| `scripts/sync-obsidian.sh` | EXTENDED | wrapper / config | shell preflight | self (existing portability guard L21-27) | exact — same `command -v` / `>&2` idiom |
| `scripts/tests/test_vault_writer.py` | EXTENDED | test | unit | self (TestBackfillIdempotent L192-227, TestProjection L277-497) | exact |
| `data/config/clients.jsonl` | EXTENDED (data) | config | file-I/O (one-time mapping) | self (current 3-line schema) | exact — additive `cm_client_id` field |
| `schemas/feed-entry.json` | EXTENDED | schema | enum extension | self (existing `level` enum L24-28) | exact — additive enum entry |
| `.gitignore` | EXTENDED | config | text | self (existing `scripts/.vault-sync.lock` entry L29-30) | exact — same runtime-state-not-tracked rationale |

## Pattern Assignments

### `scripts/lib/cm_client.py` (NEW — service, request-response + cache fallback)

**Analog:** `scripts/lib/vault_writer.py` (no existing HTTP client; reuse Phase 10 idioms for atomic-write, ISO-ts, error class shape)

**RESEARCH-supplied patterns to copy verbatim:** RESEARCH.md Pattern 1 (lines 142-210), Pattern 2 (lines 213-228), Pattern 3 (lines 230-246), and Code Examples sections "CM tools/call request" (322-346) and "Adapter: CM get_client_summary" (349-378).

**Imports pattern** (mirror vault_writer.py:27-44 — stdlib-only):

```python
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
```

**Custom exception class shape** (mirror vault_writer.py:64-65 `MarkerError`):

```python
# vault_writer.py:64-65 precedent — small, named, single-responsibility
class MarkerError(Exception):
    """Raised when section markers are missing/duplicated/malformed (D-08a)."""
```

For Phase 11, define three error classes per RESEARCH.md Pattern 1 lines 150-155:
```python
class CmTransportError(Exception):
    """Network failure or non-2xx HTTP status."""
class CmRpcError(Exception):
    """JSON-RPC error envelope: {code: int, message: str}"""
class CmRateLimitError(CmTransportError):
    """429 response; carries retry_after_seconds."""
```

**Atomic cache write** (copy verbatim from vault_writer.py:296-322 `_atomic_write`):

```python
# vault_writer.py:296-322 — copy this idiom for _write_cache(path, dict)
def _atomic_write(file_path: Path, content: str) -> None:
    """Write `content` to `file_path` via tempfile + os.replace + fsync(file+dir)."""
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
```

For `cm_client.py`, the cache writer wraps this with `json.dumps(cache, indent=2, sort_keys=True)` per RESEARCH.md Pattern 3 (lines 232-246). **Do not rewrite a worse atomic-write — call the same idiom.** RESEARCH.md "Don't Hand-Roll" table line 261 explicitly says: "Already includes fsync(file) + fsync(dir) for iCloud-safety. Reuse via direct call or copy-paste; do NOT rewrite a worse version."

**ISO timestamp helper** (reuse vault_writer.py:154-160 `now_iso_with_offset`):

```python
# vault_writer.py:154-160 — reuse for cm-cache `fetched_at` and `cm_data_stale_since`
def now_iso_with_offset() -> str:
    """ISO 8601 with timezone offset matching `feed-entry.json` regex.
    `datetime.now().astimezone()` resolves the local TZ; `isoformat(timespec='seconds')`
    drops microseconds and emits the `±HH:MM` offset suffix that the schema requires.
    """
    return datetime.now().astimezone().isoformat(timespec="seconds")
```

**Action for planner:** Either `from .vault_writer import now_iso_with_offset` (cleaner) OR copy-paste. RESEARCH.md "Don't Hand-Roll" (L262) explicitly forbids re-rolling this.

**Core JSON-RPC pattern** — RESEARCH.md Pattern 1 (lines 161-209) is the canonical template. Key seam per RESEARCH.md "Test Scaffolding > Mock seam: `_cm_post`" (lines 655-660): **the single network function `_cm_post(method, params, api_key)` is the test seam — do NOT inline `urllib.request.urlopen` in `call_with_retry`. Tests patch `_cm_post`, not urlopen.**

**Retry policy + 429 handling** — RESEARCH.md Pattern 1 lines 196-209 supplemented by "Auth + Key Lifecycle > Failure response shapes" (lines 600-609):
- 401 (missing/invalid key) → fatal, do NOT retry, log critical
- 429 → respect `Retry-After` header, single retry, then fall back to cache
- 5xx / network → 1s/5s/30s backoff (D-A3), then fall back to cache
- 200 with `isError:true` envelope → data error for that one entity, stamp `cm_data_stale_since` on that note's frontmatter only

**Adapter pattern (CM response → frontmatter dict)** — RESEARCH.md Code Examples lines 349-378. **Critical refinement per CONTEXT D-B-MOD-REVISED (L90):** `deployed_modules = sorted({c["name"] for c in activeContracts})`. Sites is always `[]` per D-C2-REVISED.

---

### `scripts/tests/test_cm_client.py` (NEW — test, unit with mock seam)

**Analog:** `scripts/tests/test_vault_writer.py` (TestProjection mock pattern at lines 460-497 — `unittest.mock.patch`)

**Imports pattern** (mirror test_vault_writer.py:1-12):

```python
"""Phase 11 — Contract Manager MCP client unit tests.
Run: python3 -m unittest discover scripts/tests
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
```

**Mock-patch idiom** — copy from test_vault_writer.py:487-497 (TestProjection.test_dry_run_does_not_invoke_brctl):

```python
# test_vault_writer.py:487-497 — patch a module-level symbol with mock.patch
with mock.patch("scripts.lib.vault_writer.subprocess.run") as mock_run:
    run_projection(Path(build), Path(icloud),
                   dry_run=True, feed_path=feed_path)
    for call in mock_run.call_args_list:
        argv = call.args[0] if call.args else []
        self.assertFalse(
            argv and argv[0] == "brctl",
            f"brctl invoked under dry_run: {argv}",
        )
```

For cm_client tests, patch `scripts.lib.cm_client._cm_post` per RESEARCH.md lines 663-679:

```python
# RESEARCH.md "Test Scaffolding" lines 663-679 — copy-paste skeleton
class TestCallWithRetry(unittest.TestCase):
    @patch("scripts.lib.cm_client._cm_post")
    def test_succeeds_on_first_try(self, mock_post):
        mock_post.return_value = {"client": {"id": 42}}
        result = call_with_retry("get_client_summary", {"clientId": 42}, "key")
        self.assertEqual(result["client"]["id"], 42)
        self.assertEqual(mock_post.call_count, 1)

    @patch("scripts.lib.cm_client._cm_post")
    @patch("scripts.lib.cm_client.time.sleep")  # avoid real 36s sleep in tests
    def test_retries_three_times_then_raises(self, mock_sleep, mock_post):
        mock_post.side_effect = CmTransportError("oops")
        with self.assertRaises(CmTransportError):
            call_with_retry("x", {}, "key")
        self.assertEqual(mock_post.call_count, 4)  # initial + 3 retries
```

**Test classes to add** (per RESEARCH.md table at lines 681-692):
- `TestCmClient` — JSON-RPC envelope, header injection, error parsing (mocks `urllib.request.urlopen`)
- `TestCallWithRetry` — D-A3 retry timing, 429 Retry-After (mocks `_cm_post`, `time.sleep`)
- `TestCmCacheFallback` — atomic write, corruption tolerance, GC of orphan keys (real tempdir)

---

### `data/.cm-cache.json` (NEW — runtime cache file, gitignored)

**Analog:** vault_writer `_atomic_write` target idiom (vault_writer.py:296-322).

**Schema** — per CONTEXT D-F1 + RESEARCH.md "Cache File Shape + Concurrency" (lines 612-636):

```jsonc
{
  "schema_version": 1,
  "global": {
    "expiring_contracts": {
      "fetched_at": "2026-05-02T10:30:00+10:30",
      "lookahead_days": 90,
      "result": { /* structuredContent of list_contracts_expiring */ }
    },
    "overdue_invoices": {
      "fetched_at": "2026-05-02T10:30:00+10:30",
      "result": { /* structuredContent of list_overdue_invoices */ }
    }
  },
  "by_client": {
    "propertycouncil.com.au": {
      "client_summary": {"fetched_at": "...", "result": {...}},
      "sla_status": {"fetched_at": "...", "result": {...}}
    }
  }
}
```

**Note on `sla_status`** — D-C3-REVISED (CONTEXT L89) replaces `utilization_summary`/`capacity_summary` with `get_sla_status`. The cache shape above reflects that correction; planner should NOT cache utilization/capacity.

**Concurrency** — RESEARCH.md "Concurrency" (lines 639-642): NO second lock. The wrapper already holds `scripts/.vault-sync.lock` (sync-obsidian.sh:111-115) for the duration of the python invocation. The Mac daemon never calls CM by design (Pitfall 1 at RESEARCH lines 281-285).

**Corruption tolerance** — RESEARCH.md lines 644-651: cache is fallback-only; `FileNotFoundError` / `JSONDecodeError` on load → log `system`/`info` "CM unreachable AND cache unreadable", continue with blanked CM fields, never crash the sync.

---

### `scripts/lib/vault_writer.py` (EXTENDED — service / orchestrator)

**Analog:** self — Phase 10 idioms.

#### Extension 1: `EMOJI_BY_KIND` add 📄 (vault_writer.py:49)

**Current** (line 49):
```python
EMOJI_BY_KIND = {"triage": "📧", "task": "✅", "invoice": "💰"}
```

**Phase 11** (per CONTEXT D-E1 + RESEARCH lines 451):
```python
EMOJI_BY_KIND = {"triage": "📧", "task": "✅", "invoice": "💰", "contract": "📄"}
```

**Pattern:** This is a single-line dict-extend. The downstream `render_log_line` (vault_writer.py:200-219) checks `if kind not in EMOJI_BY_KIND:` and accepts any registered kind — no other change needed for `kind="contract"`.

#### Extension 2: `MANAGED_SECTIONS` tuple (vault_writer.py:52)

**Current**:
```python
MANAGED_SECTIONS = ("OPEN-ITEMS", "ACTIVITY-LOG")
```

**Phase 11** (per CONTEXT D-B3 + D-C1 + D-C3-REVISED — Sites DEFERRED per D-C2-REVISED):
```python
MANAGED_SECTIONS = ("CM-TODOS", "OPEN-ITEMS", "USAGE", "ACTIVITY-LOG")
```

**IMPORTANT — Sites is OMITTED.** Per CONTEXT D-C2-REVISED (line 88): "Phase 11 ships with frontmatter `sites: []` always, and **no Sites managed section is rendered** — neither the marker pair nor the placeholder body."

The marker discipline (D-08/D-08a) carries forward by construction — `replace_managed_section` is section-name-agnostic per RESEARCH line 431.

#### Extension 3: `render_frontmatter` (vault_writer.py:553-563)

**Current** (lines 553-563):
```python
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
```

**Phase 11** — extend per RESEARCH.md "Render order for extended frontmatter" lines 381-405:

```python
def render_frontmatter(client: dict, last_synced_iso: str,
                       cm_extra: dict | None = None,
                       cm_stale_since: str | None = None) -> str:
    fm = {
        # Phase 10 v1 keys — UNCHANGED ORDER
        "domain": client["domain"],
        "client_name": client["client_name"],
        "status": client.get("status", "active"),
        "last_synced": last_synced_iso,
    }
    if cm_extra is not None:
        # Phase 11 keys: chronological grouping (contracts → contact → infra)
        fm["contract_start"]   = cm_extra.get("contract_start", "")
        fm["contract_end"]     = cm_extra.get("contract_end", "")
        fm["primary_contact"]  = cm_extra.get("primary_contact", "")
        fm["deployed_modules"] = cm_extra.get("deployed_modules", [])
        fm["sites"]            = cm_extra.get("sites", [])  # always [] per D-C2-REVISED
    if cm_stale_since:
        fm["cm_data_stale_since"] = cm_stale_since
    buf = StringIO()
    _yaml_instance().dump(fm, buf)
    return f"---\n{buf.getvalue()}---\n"
```

**D-B1 / D-B2 contract:** scalar empty → `""`, array empty → `[]`. The adapter (RESEARCH lines 351-378) does the empty-handling BEFORE handing the dict to `render_frontmatter`.

#### Extension 4: New `render_cm_todos`, `render_usage` (NO render_sites per D-C2-REVISED)

**Pattern source:** mirror `render_open_items` (vault_writer.py:491-527) and `render_activity_log` (vault_writer.py:530-550):

```python
# vault_writer.py:491-527 (render_open_items) — patterns to copy:
# 1. Build bullets list
# 2. If empty, return `_(none)_` placeholder (line 526)
# 3. Return "\n".join(bullets) (line 527)
def render_open_items(slug: str, todos: list, tasks: list, clients: dict[str, dict]) -> str:
    bullets: list[str] = []
    # ... iterate, filter, append ...
    if not bullets:
        return "_(none)_"
    return "\n".join(bullets)
```

For `render_cm_todos(cm_extra: dict | None) -> str`:
- Iterate the 4 keys (`contract_start`, `contract_end`, `primary_contact`, `deployed_modules` — NOT `sites` since per D-C2-REVISED `sites: []` is the steady state, not a "missing" condition)
- Empty-detection: scalar `""` or list `[]` → bullet
- Empty result → `_(no missing CM data)_` placeholder (mirrors `_(none)_` idiom from L526)
- When CM is unreachable AND cache is empty: render `_(CM data unavailable; will refresh next sync)_`

For `render_usage(cm_sla: dict | None) -> str`:
- Per D-C3-REVISED (CONTEXT L89): use `get_sla_status` `projects[]` array filtered by `clientName`
- Empty → `_(no usage data)_`

#### Extension 5: `_gather_events` (vault_writer.py:645-679)

**Current** (lines 645-679 — three event sources: triage, task, invoice).

**Phase 11** — add fourth and fifth sources per CONTEXT D-D2 + D-E1:

**(a) Contract events** from `cm.list_contracts_expiring(days=90)` per RESEARCH lines 449-466:
```python
# RESEARCH lines 449-466 — copy verbatim
def cm_contract_expiry_to_event_tuple(contract: dict) -> tuple:
    """Per D-E1 line shape with 📄 emoji."""
    ts = f"{contract['endDate']}T00:00:00+10:30"
    summary = (
        f"Contract renewal due — {contract['client']} "
        f"({contract['name']}, {contract['daysUntilExpiry']}d to expiry)"
    )
    cm_id = contract["id"]
    detail = (
        f"source: contract-manager · "
        f"[Open in CM](https://contracts.agend.info/contracts/{cm_id})"
    )
    return (ts, "contract", summary, detail, None)
```

**(b) CM-tracked invoices** from `cm.list_overdue_invoices()` per RESEARCH lines 433-446. **D-D2 dedup against local invoices** by `invoice_number` (case-fold + trim only, per Pitfall 4 at RESEARCH lines 299-303 — do NOT strip prefixes/separators).

**Routing:** CM contracts and CM invoices both have `clientId` (numeric CM ID); reverse-map via the inverse of D-G1's `cm_client_id` → domain → slug lookup. Records that don't reverse-map go to `_Unknown.md` (D-04 routing rule preserved).

#### Extension 6: New `--mode map-cm-clients` (per CONTEXT D-G1, RESEARCH Open Question 5 lines 762-765)

**Analog:** existing CLI mode dispatch at vault_writer.py:1110-1160 (argparse `choices` list at L1114).

**Current** (line 1113):
```python
p.add_argument(
    "--mode",
    choices=["backfill", "incremental", "project-to-icloud"],
    required=True,
)
```

**Phase 11**:
```python
p.add_argument(
    "--mode",
    choices=["backfill", "incremental", "project-to-icloud", "map-cm-clients"],
    required=True,
)
```

**Implementation pattern** — mirror `run_projection` shape (vault_writer.py:913-965) for the new `run_map_cm_clients(data_root, feed_path)`:
1. Load `clients.jsonl` via `stream_ndjson` (vault_writer.py:381-399)
2. For each record without `cm_client_id`, call `cm.search_clients(query=domain)`
3. Pick first match; write back via atomic-rewrite of `clients.jsonl` (use `_atomic_write` at vault_writer.py:296)
4. Idempotent: re-runs are safe; updates IDs if CM IDs change

#### Extension 7: Per-file try/except for CM fetch failures (mirror vault_writer.py:1077-1092)

**Source pattern** (vault_writer.py:1073-1092 — `_update_frontmatter_last_synced` failure handling):

```python
# vault_writer.py:1073-1092 — copy this idiom for CM fetch failures
if not dry_run:
    try:
        _update_frontmatter_last_synced(target, last_synced)
    except Exception as e:
        append_feed_entry(
            handle_marker_error_for_feed(
                file_path=target,
                section="<frontmatter>",
                reason=f"frontmatter update failed: {type(e).__name__}: {e}",
            ),
            feed_path=feed_path,
        )
        print(
            f"WARN: frontmatter update failed for {target} "
            f"({type(e).__name__}: {e}); managed-section splice already succeeded",
            file=sys.stderr,
        )
```

**Phase 11 application:** wrap each per-client `cm.get_client_summary(cm_client_id)` call in `try/except (CmTransportError, CmRpcError)`. On exhaustion → load from cache, stamp `cm_data_stale_since`, append `system`/`warning` feed entry, **continue with next client** — never abort entire backfill.

#### Extension 8: Critical guard — `run_projection` MUST NOT call CM (RESEARCH Pitfall 1, lines 281-285)

**Pattern:** Add a docstring assertion + a unit test `test_run_projection_does_not_open_cache_file` (RESEARCH line 642). Mac daemon design invariant.

---

### `scripts/sync-obsidian.sh` (EXTENDED — wrapper / config)

**Analog:** self — existing portability guard L21-27.

**Current** (lines 21-27):
```bash
# ----- Issue 7: portability guard -----
if ! command -v flock >/dev/null 2>&1; then
  echo "scripts/sync-obsidian.sh requires util-linux's flock (Coolify/Linux only)." >&2
  echo "On Mac, invoke vault_writer directly: python3 -m scripts.lib.vault_writer --mode <mode>" >&2
  echo "See mac/README.md for the canonical macOS instructions." >&2
  exit 1
fi
```

**Phase 11 add** (per CONTEXT D-A2, RESEARCH "Anti-Patterns to Avoid" line 253: `${CONTRACT_MANAGER_API_KEY:?missing}`):

```bash
# Phase 11: CONTRACT_MANAGER_API_KEY required for CM MCP calls.
# Validation idiom: ${VAR:?msg} aborts with the msg if VAR is unset/empty.
: "${CONTRACT_MANAGER_API_KEY:?CONTRACT_MANAGER_API_KEY env var required (set on Coolify; not on Mac)}"
```

**Place this AFTER the flock portability guard (after line 27) and BEFORE the no-op-delta gate (before line 50)** — because Mac daemon doesn't run sync-obsidian.sh anyway (it invokes vault_writer.py directly per L14-18 docstring), so this validation only fires on Coolify.

---

### `scripts/tests/test_vault_writer.py` (EXTENDED — test)

**Analog:** self — existing TestBackfill / TestProjection test-class structure.

**Existing test classes** (test_vault_writer.py):
- `TestSlugify` (L14-43)
- `TestReplaceManagedSection` (L46-80)
- `TestMarkerError` (L83-134)
- `TestRenderLogLine` (L137-189)
- `TestBackfillIdempotent` (L192-227) — **`_snapshot_managed` helper at L219-227 is the key reusable fixture**
- `TestMain` (L230-274)
- `TestProjection` (L277-497)

**Snapshot helper to extend** (test_vault_writer.py:219-227):

```python
# test_vault_writer.py:219-227 — Phase 11 must extend this to ALSO strip cm_data_stale_since
def _snapshot_managed(self, build_root: Path) -> dict:
    """Read each .md and strip last_synced line for comparison."""
    out = {}
    for md in sorted((build_root / "Clients").glob("*.md")):
        lines = md.read_text(encoding="utf-8").splitlines()
        # Drop any line beginning with 'last_synced:' inside frontmatter
        filtered = [ln for ln in lines if not ln.startswith("last_synced:")]
        out[md.name] = "\n".join(filtered)
    return out
```

**Phase 11 extension** — add `cm_data_stale_since` to the strip list per RESEARCH.md "Existing fixtures to reuse" line 695: "Phase 11 should also snapshot excluding `cm_data_stale_since` for the same reason."

**Test classes to add** (per CONTEXT specifics + RESEARCH.md table at lines 681-692, with TestSitesSection OMITTED per D-C2-REVISED):

| Class | Purpose | Mocks | Analog |
|-------|---------|-------|--------|
| `TestContractMerge` | get_client_summary → frontmatter dict, render_frontmatter extension | `_cm_post` | mirrors TestRenderLogLine structure (L137-189) |
| `TestCmTodosSection` | Missing-fields detection, marker discipline (inherits D-08a), `_(no missing CM data)_` placeholder | `_cm_post` | mirrors TestReplaceManagedSection (L46-80) for marker handling |
| `TestUsageSection` | per-client SLA status filtering by `clientName`, formatting | `_cm_post` | mirrors test_replaces_only_inside_markers (L56-68) |
| `TestInvoiceMerge` | Dedup against `data/invoices/active.jsonl` by invoice_number with case-fold + trim only (Pitfall 4) | `_cm_post` | mirrors TestBackfillIdempotent fixture pattern (L192-227) |
| `TestCacheFallbackEnd2End` | Force `_cm_post` to raise → cache fallback → `cm_data_stale_since` stamped → next run with `_cm_post` succeeding clears it | `_cm_post`, real tempdir | mirrors TestProjection.test_existing_target_marker_error_aborts (L311-344) which similarly mocks an error path and asserts feed entry written |

**TestSitesSection is OMITTED** because Sites is deferred per D-C2-REVISED.

**Test fixture pattern to copy** (test_vault_writer.py:200-217 — TestBackfillIdempotent):

```python
# test_vault_writer.py:200-217 — copy this for each new test class needing a working data_root
with tempfile.TemporaryDirectory() as build_dir, tempfile.TemporaryDirectory() as data_dir:
    config_dir = Path(data_dir) / "config"
    config_dir.mkdir()
    (config_dir / "clients.jsonl").write_text(
        '{"domain": "example.com", "name": "Example", ...}\n',
        encoding="utf-8",
    )
    for sub in ("triage", "tasks", "invoices", "todos"):
        (Path(data_dir) / sub).mkdir()
    run_backfill(data_root=Path(data_dir), build_root=Path(build_dir))
```

For Phase 11 tests: extend the clients.jsonl fixture line to include `"cm_client_id": 42` and patch `cm_client._cm_post` to return a frozen `get_client_summary` payload.

---

### `data/config/clients.jsonl` (EXTENDED — config / one-time mapping data)

**Analog:** self — existing 3-line schema.

**Current**:
```jsonl
{"domain": "propertycouncil.com.au", "name": "Property Council Australia", "aliases": ["pca"], "contact": "Craig Horton"}
{"domain": "atem.org.au", "name": "Association for Tertiary Education Management", "aliases": ["ATEM"], "contact": "ML Huppatz"}
{"domain": "otaus.com.au", "name": "Occupational Therapy Australia", "aliases": ["OTA"], "contact": "Alex Reynolds"}
```

**Phase 11** — add optional `cm_client_id: int` field (populated by `--mode map-cm-clients` per D-G1):
```jsonl
{"domain": "propertycouncil.com.au", "name": "Property Council Australia", "aliases": ["pca"], "contact": "Craig Horton", "cm_client_id": 42}
```

**Backwards compatibility:** vault_writer.py:344-345 already uses `rec.get(...)` for tolerant reading. New field is `client.get("cm_client_id")` — `None` triggers a single just-in-time `search_clients` call for that one domain (per CONTEXT D-G1 last sentence).

**Atomic write idiom** — when `--mode map-cm-clients` writes back: collect all records → rewrite full file atomically via `_atomic_write` (vault_writer.py:296). Do NOT in-place edit (corrupts on power loss per RESEARCH Anti-Patterns line 251).

---

### `schemas/feed-entry.json` (EXTENDED — schema)

**Analog:** self — existing `level` enum at lines 24-28.

**Current** (lines 24-28):
```json
"level": {
  "type": "string",
  "enum": ["critical", "info", "debug"],
  "description": "Severity level for filtering"
},
```

**Phase 11** (per CONTEXT D-A3-REVISED line 91 — Wave 0 task, MUST land before any code emits a `warning`-level entry):
```json
"level": {
  "type": "string",
  "enum": ["critical", "warning", "info", "debug"],
  "description": "Severity level for filtering"
},
```

**Pattern:** Single-line additive enum extension. **Sequencing constraint per CONTEXT D-A3-REVISED:** schema edit MUST land in a Wave 0 commit before any code path emits a `warning`-level entry. Otherwise `validate-data.sh` (if it validates feed entries) breaks.

**Verification side-check:** RESEARCH lines 14-15 explicitly verified the schema is missing `warning`. The 3-tuple `["critical", "info", "debug"]` is on schemas/feed-entry.json line 26 (verified by direct read).

---

### `.gitignore` (EXTENDED — config)

**Analog:** self — existing `scripts/.vault-sync.lock` line 30.

**Current** (lines 28-30):
```
# Runtime lock files (created by flock in scripts/sync-obsidian.sh)
scripts/.vault-sync.lock
```

**Phase 11 add** (per CONTEXT D-F1, "Cache is per-host runtime state, like Coolify's PID files"):
```
# Phase 11: Contract Manager response cache (per-host runtime state, fallback only)
data/.cm-cache.json
```

**Pattern:** Same rationale as `.vault-sync.lock` — per-host runtime state, never canonical, never tracked. Group new entry under a clear comment explaining the "fallback only, not source of truth" semantics.

---

## Shared Patterns

### Cross-cutting Pattern A — Atomic Write
**Source:** `scripts/lib/vault_writer.py:296-322` (`_atomic_write`)
**Apply to:** cache file write, clients.jsonl rewrite (mapping mode), any Phase 11 file mutation
**Rule:** Never `os.rename` without `fsync(file)` + `fsync(dir)`; never in-place edit; tempfile prefix `f".{file_path.name}."` and suffix `.tmp` for predictable cleanup

```python
# vault_writer.py:296-322 — the canonical atomic-write idiom
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
```

### Cross-cutting Pattern B — Marker Discipline (D-08/D-08a)
**Source:** `scripts/lib/vault_writer.py:99-149` (`replace_managed_section`) + `vault_writer.py:791-812` (`_extract_managed_section`)
**Apply to:** ALL new managed sections (CM-TODOS, USAGE — Sites is omitted per D-C2-REVISED)
**Rule:** Section-name-agnostic — adding to MANAGED_SECTIONS tuple is sufficient; no per-section code needed because `replace_managed_section(file_path, section_name, new_content)` parameterizes on `section_name`.

```python
# vault_writer.py:113-119 — the marker invariant check
if len(starts) != 1 or len(ends) != 1:
    raise MarkerError(
        f"{file_path}: expected exactly 1 {section_name}-START and 1 {section_name}-END, "
        f"got {len(starts)} starts, {len(ends)} ends"
    )
if starts[0].end() > ends[0].start():
    raise MarkerError(f"{file_path}: {section_name}-END appears before -START")
```

**ABORT path** (vault_writer.py:1024-1042 — for source markers; vault_writer.py:1048-1066 — for target markers):
- Catch `MarkerError`
- Build feed entry via `handle_marker_error_for_feed` (vault_writer.py:163-183)
- Append via `append_feed_entry(entry, feed_path=feed_path)` (vault_writer.py:186-195)
- `print(...file=sys.stderr)` and `break` to skip remaining sections for this file
- **DO NOT update `last_synced`** on aborted files (vault_writer.py:1068-1071 — Pitfall 1)

### Cross-cutting Pattern C — `--feed-path` threading
**Source:** `scripts/lib/vault_writer.py:1131-1145` (CLI default resolution) + threading through `run_backfill`/`run_projection`
**Apply to:** all CM-warning emission paths
**Rule:** Per RESEARCH "Established Patterns" line 177 — extend this pattern to also cover CM warning paths. Tests pass a temp `feed_path` so production audit trail (`data/feed.jsonl`) is never polluted (Issue 1).

```python
# vault_writer.py:1143-1145 — resolve feed_path ONCE at CLI boundary
feed_path = args.feed_path if args.feed_path is not None else (args.data_root / "feed.jsonl")
```

```python
# vault_writer.py:186-195 — atomic NDJSON append (≤PIPE_BUF single line)
def append_feed_entry(entry: dict, *, feed_path: Path) -> None:
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    with open(feed_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

For Phase 11 CM `warning` entry shape:
```python
{
    "ts": now_iso_with_offset(),
    "type": "system",
    "summary": "CM stale (fallback to cache) — propertycouncil.com.au",
    "level": "warning",   # <-- requires schema extension first (Wave 0)
    "trigger": "hook",
    "details": {
        "domain": "propertycouncil.com.au",
        "cache_age_seconds": 86400,
        "last_error": "CmTransportError: ...",
    },
}
```

### Cross-cutting Pattern D — Per-file try/except (no cascading failure)
**Source:** `scripts/lib/vault_writer.py:1073-1092` (frontmatter update failure handling)
**Apply to:** CM fetch failures inside `run_backfill` per-client loop
**Rule:** A single client's CM failure must NOT halt the backfill. Wrap, log, fall back to cache, continue.

```python
# vault_writer.py:1073-1092 — copy this idiom for per-client CM fetches
try:
    _update_frontmatter_last_synced(target, last_synced)
except Exception as e:
    append_feed_entry(
        handle_marker_error_for_feed(
            file_path=target,
            section="<frontmatter>",
            reason=f"frontmatter update failed: {type(e).__name__}: {e}",
        ),
        feed_path=feed_path,
    )
    print(
        f"WARN: frontmatter update failed for {target} "
        f"({type(e).__name__}: {e}); managed-section splice already succeeded",
        file=sys.stderr,
    )
```

### Cross-cutting Pattern E — ISO timestamp helper
**Source:** `scripts/lib/vault_writer.py:154-160` (`now_iso_with_offset`)
**Apply to:** `cm_data_stale_since` frontmatter field, cache `fetched_at` field, all `warning` feed entries
**Rule:** RESEARCH "Don't Hand-Roll" line 262 — never re-roll. Either import or copy verbatim.

### Cross-cutting Pattern F — Concurrency (`_acquire_projection_lock` precedent)
**Source:** `scripts/lib/vault_writer.py:777-788` (`_acquire_projection_lock`)
**Apply to:** N/A for Phase 11 — RESEARCH lines 639-642 confirms NO second lock needed. The wrapper's `scripts/.vault-sync.lock` (sync-obsidian.sh:111-115) covers the entire CM read + cache write window. Mac daemon never calls CM by design.

```python
# vault_writer.py:777-788 — fcntl precedent for FUTURE phases needing daemon-side locks
def _acquire_projection_lock(dry_run: bool):
    if dry_run:
        return None
    _PROJECTION_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = open(_PROJECTION_LOCK_PATH, "w")
    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
    return lock_fd
```

**Reference only — Phase 11 does NOT add a new lock.** Cited so the planner can confirm "no new lock needed" with provenance.

---

## No Analog Found

| File | Role | Data Flow | Reason | Mitigation |
|------|------|-----------|--------|------------|
| `scripts/lib/cm_client.py` | service / network-client | request-response (HTTP JSON-RPC) + cache fallback | First outbound HTTP integration in this codebase. Phase 10 is filesystem-only. No prior `urllib.request` usage. | Use RESEARCH.md Pattern 1/2/3 (lines 142-246) as canonical templates. They are written specifically for Phase 11 and verified against `~/work/contract-manager` source. Reuse Phase 10 idioms for atomic-write, ISO-ts, error class shape, custom exception hierarchy. |

This is the only genuine analog gap. All other files reuse established Phase 10 patterns 1:1 with verified file:line citations.

---

## Phase 11 Wave 0 Sequencing Constraints (planner — please honor)

Per CONTEXT Post-Research Refinements + RESEARCH Open Questions, these tasks must land before any code path that depends on them:

1. **schemas/feed-entry.json** enum extension (`+"warning"`) — MUST land before any `warning`-level feed entry is emitted (D-A3-REVISED at CONTEXT L91)
2. **`scripts/lib/vault_writer.py --mode map-cm-clients`** — MUST land before first frontmatter populate (D-G1 at CONTEXT L92; RESEARCH Open Question 5 lines 762-765)
3. **`.gitignore` extension** — MUST land before any cache file is written, otherwise the cache could accidentally get committed
4. **`scripts/sync-obsidian.sh` env validation** — should land alongside `cm_client.py` so a missing `CONTRACT_MANAGER_API_KEY` fails loudly at the wrapper, not silently inside Python

---

## Metadata

**Analog search scope:**
- `scripts/lib/` (vault_writer.py — full file analyzed)
- `scripts/tests/` (test_vault_writer.py — full file analyzed)
- `scripts/` (sync-obsidian.sh, requirements.txt — full files analyzed)
- `schemas/` (feed-entry.json — full file analyzed)
- `data/config/` (clients.jsonl — full file analyzed)
- `.gitignore` — full file analyzed

**Files scanned:** 8 (all read in full; nothing >2000 lines so no targeted-section reads required)

**Key citations directory:**
- `vault_writer.py:49` → EMOJI_BY_KIND
- `vault_writer.py:52` → MANAGED_SECTIONS
- `vault_writer.py:99-149` → replace_managed_section
- `vault_writer.py:154-160` → now_iso_with_offset
- `vault_writer.py:163-183` → handle_marker_error_for_feed
- `vault_writer.py:186-195` → append_feed_entry
- `vault_writer.py:200-219` → render_log_line
- `vault_writer.py:296-322` → _atomic_write
- `vault_writer.py:381-399` → stream_ndjson
- `vault_writer.py:491-527` → render_open_items (template for render_cm_todos / render_usage)
- `vault_writer.py:530-550` → render_activity_log
- `vault_writer.py:553-563` → render_frontmatter (extension target)
- `vault_writer.py:645-679` → _gather_events (extension target)
- `vault_writer.py:777-788` → _acquire_projection_lock (reference only)
- `vault_writer.py:791-812` → _extract_managed_section
- `vault_writer.py:1073-1092` → per-file try/except idiom
- `vault_writer.py:1110-1183` → main() CLI argparse + failure-path
- `test_vault_writer.py:192-227` → TestBackfillIdempotent + _snapshot_managed
- `test_vault_writer.py:277-497` → TestProjection (mock pattern + temp-dir fixture)
- `test_vault_writer.py:460-497` → mock.patch idiom
- `sync-obsidian.sh:21-27` → portability-guard `command -v` idiom
- `sync-obsidian.sh:111-115` → flock acquisition (covers CM read window)
- `schemas/feed-entry.json:24-28` → level enum (extension target)
- `.gitignore:28-30` → runtime-lock-file precedent

**Pattern extraction date:** 2026-05-02
