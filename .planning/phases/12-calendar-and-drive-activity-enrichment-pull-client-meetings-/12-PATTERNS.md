# Phase 12: Calendar + Drive Activity Enrichment — Pattern Map

**Mapped:** 2026-05-03
**Files analyzed:** 7 (2 NEW, 4 MODIFIED, 1 READ-ONLY config)
**Analogs found:** 7 / 7 (all have strong Phase 11 analogs)

This phase is "mostly gluing existing patterns" (RESEARCH.md line 350). Every new file has an exact-match analog in Phase 11. The planner's job is to copy each pattern verbatim, swap names (`cm_*` → `workspace_*` / `cal_*` / `drive_*`), and keep architectural surprise to zero.

---

## File Classification

| File | New/Modified | Role | Data Flow | Closest Analog | Match Quality |
|------|--------------|------|-----------|----------------|---------------|
| `scripts/lib/workspace_client.py` | NEW | service (HTTP client) | request-response (HTTPS GET) | `scripts/lib/cm_client.py` | exact (different transport: GET vs JSON-RPC POST) |
| `scripts/tests/test_workspace_client.py` | NEW | test | request-response | `scripts/tests/test_cm_client.py` | exact |
| `scripts/lib/vault_writer.py` | MODIFIED | service (orchestrator) | batch transform | (self — Phase 11 extension points) | exact (additive) |
| `scripts/tests/test_vault_writer.py` | MODIFIED | test | batch transform | (self — Phase 11 test classes) | exact (additive) |
| `scripts/sync-obsidian.sh` | MODIFIED | config (env validation) | request-response | `scripts/sync-obsidian.sh` lines 29-33 | exact (additive sibling check) |
| `.gitignore` | MODIFIED | config | N/A | `.gitignore` line 33-34 | exact (one-line additive) |
| `data/config/clients.jsonl` | READ-ONLY | config (data) | N/A | (read by `load_clients`) | n/a — Phase 12 reads `aliases[]` only |

**Routing scope:** `workspace_client.py` and `_fetch_external_data_for_run` are Coolify-only (Pitfall 1 inheritance). Mac daemon (`run_projection`) MUST NOT import either.

---

## Pattern Assignments

### 1. `scripts/lib/workspace_client.py` (NEW)

**Role:** Single-network-seam HTTP client for Google Calendar v3 + Drive v3 REST APIs. Mirrors `cm_client.py` shape exactly; swaps JSON-RPC POST envelope for plain GET with query-string params.

**Analog:** `scripts/lib/cm_client.py` (read in full, 230 lines)

**Point-by-point mapping:**

| `cm_client.py` | `workspace_client.py` | Notes |
|----------------|------------------------|-------|
| Module docstring (lines 1-11) | Same shape, different transport | Already drafted in RESEARCH.md lines 451-460 |
| `import json/time/urllib` (lines 12-16) | Same | Add `urllib.parse` for `urlencode` |
| `from .vault_writer import _atomic_write, now_iso_with_offset` (line 20) | Same | DON'T HAND-ROLL — reuse atomic write |
| `CM_ENDPOINT = "https://contracts.agend.info/api/mcp"` (line 24) | `CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"` + `DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"` | Two bases — OR a single `GOOGLE_API_BASE = "https://www.googleapis.com"` (planner choice) |
| `RETRY_DELAYS = (1, 5, 30)` (line 25) | Same constant, same values | D-A3 inheritance |
| `TIMEOUT_S = 15` (line 26) | Same | |
| `CACHE_SCHEMA_VERSION = 1` (line 27) | Same | Per-tool caches each get their own schema version namespace |
| `class CmTransportError(Exception)` (line 32) | `class WorkspaceTransportError(Exception)` | Same docstring shape |
| `class CmRpcError(Exception)` (line 36) | `class WorkspaceRpcError(Exception)` | Google returns `{error: {code, message}}` JSON envelope |
| `class CmRateLimitError(CmTransportError)` (lines 40-45) | `class WorkspaceRateLimitError(WorkspaceTransportError)` | Same `retry_after_seconds` attr |
| (none) | `class WorkspaceAuthExpiredError(WorkspaceTransportError)` | NEW — 401 triggers OAuth refresh + retry once. Not present in CM (CM uses long-lived API keys). |

**Imports + constants pattern** (cm_client.py lines 1-27 — copy this header verbatim, swap names):

```python
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

# Reuse vault_writer's atomic-write helper (Don't Hand-Roll line 261-264).
from .vault_writer import _atomic_write, now_iso_with_offset  # noqa: F401
```

**Single network seam pattern** (cm_client.py lines 50-111 — `_cm_post`; copy and adapt):

```python
# cm_client.py lines 50-96 — POST + JSON-RPC envelope path:
def _cm_post(method: str, params: dict, api_key: str) -> dict:
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": rpc_method, "params": rpc_params,
    }).encode("utf-8")
    req = urllib.request.Request(
        CM_ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            try:
                retry_after = int(e.headers.get("Retry-After", "30"))
            except (ValueError, TypeError):
                retry_after = 30
            raise CmRateLimitError(retry_after) from e
        raise CmTransportError(f"HTTP {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise CmTransportError(f"network: {e.reason}") from e
```

Adapt to `_workspace_get(api_path, params, access_token) -> dict`:
- METHOD: `"GET"` (no body)
- URL: `f"https://www.googleapis.com/{api_path}"` + `?` + `urllib.parse.urlencode(params)`
- HEADERS: only `Authorization: Bearer {access_token}` (no Content-Type for GET)
- 401 path NEW: catch `e.code == 401` → `raise WorkspaceAuthExpiredError(...) from e` (caller refreshes + retries once)
- Response parse: returns the full JSON dict directly (no `result.structuredContent` unwrap — Google APIs return flat JSON)
- Error envelope: Google returns `{"error": {"code": 400, "message": "..."}}` → check `if "error" in payload: raise WorkspaceRpcError(...)` (mirrors cm_client.py lines 98-100)

**Retry wrapper pattern** (cm_client.py lines 116-131 — copy verbatim, swap exception names):

```python
# cm_client.py lines 116-131 — copy exactly:
def call_with_retry(method: str, params: dict, api_key: str) -> dict:
    """D-A3 retry loop. Caller falls back to cache on final raise."""
    last_err: Exception | None = None
    delays = (0,) + RETRY_DELAYS
    for delay in delays:
        if delay:
            time.sleep(delay)
        try:
            return _cm_post(method, params, api_key)
        except CmRateLimitError as e:
            time.sleep(e.retry_after_seconds)
            last_err = e
        except (CmTransportError, CmRpcError) as e:
            last_err = e
    assert last_err is not None
    raise last_err
```

For Phase 12, add ONE additional `except WorkspaceAuthExpiredError` clause that calls `_refresh_token_if_needed()` once and retries inline (don't bake refresh into the retry loop — keep refresh orthogonal). RESEARCH.md lines 425-426 prescribes the shape.

**Cache I/O pattern** (cm_client.py lines 136-176 — copy `_empty_cache`/`load_cache`/`write_cache`/`gc_cache_orphans` verbatim):

```python
# cm_client.py lines 136-176 — these four functions copy 1:1 to workspace_client.py
# with no behavioural change. The cache dict shape is identical.
def _empty_cache() -> dict:
    return {"schema_version": CACHE_SCHEMA_VERSION, "global": {}, "by_client": {}}

def load_cache(cache_path: Path) -> dict:
    if not cache_path.exists():
        return _empty_cache()
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or data.get("schema_version") != CACHE_SCHEMA_VERSION:
            return _empty_cache()
        data.setdefault("global", {})
        data.setdefault("by_client", {})
        return data
    except (OSError, json.JSONDecodeError):
        return _empty_cache()

def write_cache(cache_path: Path, cache: dict) -> None:
    content = json.dumps(cache, indent=2, sort_keys=True) + "\n"
    _atomic_write(cache_path, content)

def gc_cache_orphans(cache: dict, known_domains: set) -> dict:
    by_client = cache.get("by_client", {})
    orphans = [d for d in by_client.keys() if d not in known_domains]
    for d in orphans:
        del by_client[d]
    return cache
```

**Two cache files, not one:** Per RESEARCH.md Q6 (line 706-708), maintain SEPARATED `.cal-cache.json` + `.drive-cache.json`. Either: (a) two pairs of `load_cal_cache`/`load_drive_cache` thin wrappers that call the shared `load_cache(path)`, or (b) the orchestrator passes the explicit cache_path to a single `load_cache`. Option (b) is cleaner (no duplicated code).

**Adapter pattern (Calendar)** (cm_client.py lines 181-206 — `cm_summary_to_frontmatter_extra` shape; adapt for Calendar):

The CM analog returns a flat dict for frontmatter consumption. For Phase 12 Calendar, the analog is `format_calendar_event_for_log(event, primary_email)` — applies D-D1+D-D2 privacy filters, returns either a normalized event dict OR `None` (filtered out).

```python
# Source pattern: RESEARCH.md lines 559-590 — privacy filter chain
GLEN_INTERNAL_DOMAINS = frozenset({"iugo.com.au"})

def format_calendar_event_for_log(event: dict, primary_email: str) -> dict | None:
    """Apply D-D1, D-D2, return None if filtered. Mirrors cm_summary_to_frontmatter_extra
    pattern: takes raw API response, returns vault_writer-friendly dict (or None)."""
    attendees = event.get("attendees", [])
    if len(attendees) > 25:
        return None  # D-D2
    if event.get("visibility") == "private":
        return None  # D-D1 part 1
    external = [a for a in attendees
                if not _is_internal(a.get("email", ""), primary_email)]
    if not external:
        return None  # D-D1 part 2
    return {
        "id": event["id"],          # Pitfall 4: stable dedup key
        "summary": event.get("summary") or "(no title)",
        "start_dt": event["start"].get("dateTime") or event["start"].get("date"),
        "attendees": attendees,     # full list — _cal_meeting_event_tuple counts
        "html_link": event.get("htmlLink", ""),
    }
```

**Adapter pattern (Drive):** `format_drive_file_for_log(file, client_aliases)` — applies D-D3 (trashed/draft/restricted), returns dict OR `None`. Same shape as Calendar adapter.

**Endpoint allowlist pattern (NEW for Phase 12 — no exact analog in cm_client.py):**

CM has only ONE endpoint (`CM_ENDPOINT`). Workspace has multiple endpoints under `googleapis.com`, with the trust-boundary risk of accidental write paths (`permissions.update`, `share_drive_file` were the hardened MCP's removed surfaces). Per CONTEXT.md D-X1 line 46-47, define a strict allowlist constant:

```python
# Phase 12 NEW — module-level constant near other constants (after line 27 in cm_client.py shape)
WORKSPACE_ALLOWED_ENDPOINTS = frozenset({
    "calendar/v3/calendars/primary/events",
    "drive/v3/files",
    # Note: drive/v3/files/{id} matched via prefix check below
})
WORKSPACE_ALLOWED_ENDPOINT_PREFIXES = ("drive/v3/files/",)  # for /{id} variants

def _check_endpoint_allowed(api_path: str) -> None:
    """Trust boundary: workspace_client.py is read-only by construction.
    Any endpoint outside this allowlist is a bug, not a feature."""
    if api_path in WORKSPACE_ALLOWED_ENDPOINTS:
        return
    if any(api_path.startswith(p) for p in WORKSPACE_ALLOWED_ENDPOINT_PREFIXES):
        return
    raise WorkspaceTransportError(
        f"endpoint not in allowlist: {api_path!r} — see workspace_client.py "
        f"WORKSPACE_ALLOWED_ENDPOINTS"
    )
```

Call `_check_endpoint_allowed(api_path)` as the first line of `_workspace_get`, before the URL construction. The grep-lint test (see test patterns below) verifies the constant is the source of truth.

**OAuth token loader pattern (NEW for Phase 12 — no analog):**

CM uses long-lived API keys via env var. Workspace uses OAuth refresh tokens stored at `~/.google_workspace_mcp/credentials/` (per RESEARCH.md A2 line 645). New helper `_load_workspace_credentials()`:
- Read JSON from `${GOOGLE_MCP_CREDENTIALS_DIR:-~/.google_workspace_mcp/credentials}/<email>.json` (or whatever shape research-Q3 resolves to — Plan 01 verifies via source-read of `auth/credential_store.py` per A2).
- If `expires_at < now + 60s`: call `_refresh_workspace_token(refresh_token)` (POST to `https://oauth2.googleapis.com/token` per RESEARCH.md line 425).
- Return `access_token: str`.
- Raise `WorkspaceTransportError("credentials missing at <path>")` on absence.

Call this once at the top of `_fetch_external_data_for_run`'s lazy-import block, BEFORE the first `call_with_retry`.

**`__all__` export pattern** (cm_client.py has no explicit `__all__`; vault_writer.py at line 1791-1811 does):

For `workspace_client.py`, follow Phase 11 idiom (no explicit `__all__` — module-level names are imported by name in lazy-import block). The vault_writer.py `__all__` MUST be extended (see modified file section below).

---

### 2. `scripts/tests/test_workspace_client.py` (NEW)

**Role:** Mock-based unit tests for the HTTP seam, retry wrapper, cache I/O, adapters, and endpoint allowlist.

**Analog:** `scripts/tests/test_cm_client.py` (read in full, 199 lines)

**Test class structure** (1:1 mirror of test_cm_client.py):

| `test_cm_client.py` class | `test_workspace_client.py` class | Lines to mirror |
|--------------------------|----------------------------------|-----------------|
| `TestCmClient` (lines 12-82) | `TestWorkspaceClient` | The `_mock_response` helper (lines 18-27), envelope test (lines 29-49), error test (lines 51-59), 401 test (NEW for Phase 12 — auth-expired), 429 test (lines 72-82) |
| `TestCallWithRetry` (lines 85-118) | `TestWorkspaceCallWithRetry` | Same three tests: succeeds-first-try, retries-3-then-raises, rate-limit-uses-retry-after |
| `TestCmCache` (lines 121-163) | `TestWorkspaceCache` | All 4 tests: missing-returns-skeleton, corrupt-returns-skeleton, write-roundtrip, gc-orphans |
| `TestCmSummaryAdapter` (lines 166-199) | `TestCalendarEventAdapter` + `TestDriveFileAdapter` | Two adapter test classes — Calendar tests D-D1/D-D2 filters; Drive tests D-D3 filter |
| (none) | **`TestWorkspaceClientEndpointAllowlist`** | NEW — Phase 12 specific. See pattern below. |

**Mock-response helper pattern** (test_cm_client.py lines 18-27 — copy verbatim, no changes needed):

```python
def _mock_response(self, payload: dict, status: int = 200,
                   headers: dict | None = None):
    """Build a context-manager-compatible mock response."""
    m = MagicMock()
    m.read.return_value = json.dumps(payload).encode("utf-8")
    m.__enter__ = lambda self_: m
    m.__exit__ = lambda self_, *args: False
    m.status = status
    m.headers = headers or {}
    return m
```

**Mock-urlopen test pattern** (test_cm_client.py lines 29-49 — adapt URL/header assertions for GET):

```python
@patch("scripts.lib.workspace_client.urllib.request.urlopen")
def test_get_builds_correct_url_and_headers(self, mock_urlopen):
    from scripts.lib.workspace_client import _workspace_get
    mock_urlopen.return_value = self._mock_response({"items": [{"id": "evt1"}]})
    result = _workspace_get(
        "calendar/v3/calendars/primary/events",
        {"timeMin": "2026-02-02T00:00:00Z", "maxResults": 250},
        "test_token",
    )
    self.assertEqual(result, {"items": [{"id": "evt1"}]})
    request_obj = mock_urlopen.call_args[0][0]
    self.assertIn("calendar/v3/calendars/primary/events", request_obj.full_url)
    self.assertIn("timeMin=", request_obj.full_url)
    self.assertEqual(request_obj.get_method(), "GET")
    headers = {k.lower(): v for k, v in request_obj.headers.items()}
    self.assertEqual(headers["authorization"], "Bearer test_token")
```

**429 retry test pattern** (test_cm_client.py lines 72-82 — copy verbatim, swap class names):

The `urllib.error.HTTPError(url="x", code=429, msg="...", hdrs={"Retry-After": "60"}, fp=None)` idiom transfers identically.

**Endpoint-allowlist grep-lint test (TestWorkspaceClientEndpointAllowlist) — no exact analog, use this shape:**

There is NO existing grep-lint pattern in the codebase. The closest precedent is the subprocess-based `TestProjectionDoesNotImportCm` (test_vault_writer.py lines 957-983) which uses a subprocess + module-cache assertion. For endpoint allowlisting, a simpler in-process test suffices — read the source file, grep for any `urlopen` call OR any string containing `googleapis.com/`, ensure each falls under the allowlist:

```python
class TestWorkspaceClientEndpointAllowlist(unittest.TestCase):
    """Trust-boundary verification: workspace_client.py only calls Google API
    endpoints in WORKSPACE_ALLOWED_ENDPOINTS. CI catches accidental write paths
    (permissions.update, share_drive_file, etc.) before ship.

    Strategy: load the module's allowlist, walk every string literal in the
    source file, ensure every string starting with 'calendar/' or 'drive/' is
    in the allowlist (or its prefix set).
    """
    def test_only_allowlisted_endpoints_referenced(self):
        import re
        from scripts.lib import workspace_client
        from scripts.lib.workspace_client import (
            WORKSPACE_ALLOWED_ENDPOINTS, WORKSPACE_ALLOWED_ENDPOINT_PREFIXES,
        )
        source = Path(workspace_client.__file__).read_text(encoding="utf-8")
        # Match string-literal endpoint paths under googleapis.com (e.g.
        # "calendar/v3/...", "drive/v3/files", 'drive/v3/files/{id}').
        endpoint_pattern = re.compile(
            r'["\']((?:calendar|drive)/v3/[^"\']+)["\']'
        )
        found = set(endpoint_pattern.findall(source))
        for path in found:
            allowed = path in WORKSPACE_ALLOWED_ENDPOINTS or any(
                path.startswith(p) for p in WORKSPACE_ALLOWED_ENDPOINT_PREFIXES
            )
            self.assertTrue(
                allowed,
                f"endpoint {path!r} found in workspace_client.py but not in "
                f"WORKSPACE_ALLOWED_ENDPOINTS — add it explicitly or remove the call",
            )

    def test_no_write_verb_method_calls_present(self):
        """Defensive: scan for any method override that isn't GET. workspace_client
        is read-only by construction; POST/PUT/PATCH/DELETE indicate a bug."""
        from scripts.lib import workspace_client
        source = Path(workspace_client.__file__).read_text(encoding="utf-8")
        # Allow the literal "GET" string only; flag any other HTTP verb usage.
        for verb in ("POST", "PUT", "PATCH", "DELETE"):
            # Ignore comment lines and docstring mentions
            for line in source.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"'):
                    continue
                self.assertNotIn(
                    f'method="{verb}"', line,
                    f"workspace_client.py contains method={verb!r} on line "
                    f"{line!r} — this module is read-only by construction",
                )
```

This is a NEW test pattern but follows the same self-documenting style as `TestProjectionDoesNotImportCm` (use the production module's own constants as the source of truth so the test stays in sync).

---

### 3. `scripts/lib/vault_writer.py` (MODIFIED)

**Role:** Orchestrator extension — add Calendar + Drive event flow alongside CM.

**Analog:** Self — Phase 11 added `_fetch_cm_data_for_run` and 4 helpers; Phase 12 mirrors the same shape additively.

**Modification 1: `EMOJI_BY_KIND` extension** — line 49

**Current source** (line 49):
```python
EMOJI_BY_KIND = {"triage": "📧", "task": "✅", "invoice": "💰", "contract": "📄"}
```

**Phase 12 change** (additive — extend the dict, do not reorder existing keys):
```python
EMOJI_BY_KIND = {
    "triage":   "📧",  # Phase 2
    "task":     "✅",  # Phase 3
    "invoice":  "💰",  # Phase 7
    "contract": "📄",  # Phase 11 (RESERVED — do not reuse for Drive docs per D-C3)
    "meeting":  "📅",  # Phase 12 — Calendar events
    "doc":      "📝",  # Phase 12 — Drive files
}
```

**Verification anchor:** `grep "📄" vault-build/Clients/*.md | grep -v "Contract"` returns no matches (CONTEXT.md verification anchor 4).

**Modification 2: New helpers — Calendar + Drive event-tuple builders + filename matcher**

Insert AFTER `_cm_invoice_event_tuple` (vault_writer.py line 590), BEFORE `# Section renderers` header (line 592). Mirror the source-order convention established in Phase 11 Plan 04 (`_normalize_invoice_number` → `_clientid_to_slug` → `_cm_contract_event_tuple` → `_cm_invoice_event_tuple`).

**Pattern source — `_cm_contract_event_tuple` (lines 549-571):**
```python
def _cm_contract_event_tuple(contract: dict, local_tz_offset: str = "+10:30") -> tuple:
    """Build a D-E1 contract event tuple. kind="contract" → 📄 emoji via EMOJI_BY_KIND."""
    ts = f"{contract.get('endDate', '1970-01-01')}T00:00:00{local_tz_offset}"
    name = contract.get("name") or "(unnamed contract)"
    client_display = contract.get("client") or "(unknown client)"
    days = contract.get("daysUntilExpiry")
    if days is not None:
        summary = f"Contract renewal due — {client_display} ({name}, {days}d to expiry)"
    else:
        summary = f"Contract renewal due — {client_display} ({name})"
    cm_id = contract.get("id")
    if cm_id is not None:
        detail = (
            f"source: contract-manager · "
            f"[Open in CM](https://contracts.agend.info/contracts/{cm_id})"
        )
    else:
        detail = "source: contract-manager"
    return (ts, "contract", summary, detail, None)
```

**Phase 12 — `_cal_meeting_event_tuple`:**
```python
def _cal_meeting_event_tuple(event: dict, local_tz_offset: str = "+10:30") -> tuple:
    """Build a D-C1 calendar meeting event tuple. kind="meeting" → 📅 emoji.

    Source: Calendar v3 events.list response (post-format_calendar_event_for_log).
    Returns: (ts_iso, "meeting", summary, detail, gmail_thread_id_or_none).

    Pitfall 4 inheritance: event["id"] is the stable dedup key (NOT title/date).
    """
    # event["start_dt"] is RFC3339 ISO from format_calendar_event_for_log.
    # Fall back to local_tz_offset if no TZ offset present (date-only events).
    raw_start = event.get("start_dt") or "1970-01-01T00:00:00"
    if "T" not in raw_start:
        raw_start = f"{raw_start}T00:00:00{local_tz_offset}"
    elif raw_start.endswith("Z"):
        # RFC3339 with Z suffix → Python datetime needs +00:00 form
        raw_start = raw_start[:-1] + "+00:00"
    ts = raw_start
    title = event.get("summary") or "(no title)"
    n_attendees = len(event.get("attendees") or [])
    summary = f"{title} — {n_attendees} attendees"
    html_link = event.get("html_link") or ""
    if html_link:
        detail = f"[Open in Calendar]({html_link})"
    else:
        detail = None
    return (ts, "meeting", summary, detail, None)
```

**Phase 12 — `_drive_doc_event_tuple`:**
```python
def _drive_doc_event_tuple(file: dict, local_tz_offset: str = "+10:30") -> tuple:
    """Build a D-C2 drive document event tuple. kind="doc" → 📝 emoji.

    Source: Drive v3 files.list response (post-format_drive_file_for_log).
    Returns: (ts_iso, "doc", summary, detail, gmail_thread_id_or_none).
    """
    raw_modified = file.get("modifiedTime") or "1970-01-01T00:00:00Z"
    if raw_modified.endswith("Z"):
        ts = raw_modified[:-1] + "+00:00"
    else:
        ts = raw_modified
    name = file.get("name") or "(unnamed file)"
    modifier = file.get("lastModifyingUser") or {}
    modifier_name = (
        modifier.get("displayName")
        or (modifier.get("emailAddress") or "").split("@", 1)[0]
        or "unknown"
    )
    summary = f"{name} — modified by {modifier_name}"
    web_link = file.get("webViewLink") or ""
    if web_link:
        detail = f"[Open in Drive]({web_link})"
    else:
        detail = None
    return (ts, "doc", summary, detail, None)
```

**Phase 12 — `_match_drive_filename_to_client` (filename matching with stop-list + longest-match):**

CONTEXT.md D-A4-REVISED prescribes case-insensitive substring + word-boundary + stop-list + longest-alias-wins. The closest analog in the codebase is `_clientid_to_slug` (vault_writer.py lines 536-546) for the reverse-lookup pattern, AND `safe_slugify` (lines 88-95) for the fallback chain. Combine the two patterns:

```python
# Phase 12 — Drive filename matching helpers (D-A4-REVISED)
# Stop-list: ambiguous tokens that match Glen's brand/personal references
# rather than client names. Filename matches against these are silently ignored
# (one info-level feed entry per sync summarizes the count per D-A4-REVISED).
_DRIVE_FILENAME_STOP_LIST = frozenset({"agend", "iugo", "glen", "rosie"})

# Word-boundary delimiters per D-A4-REVISED: '_', '-', '.', ' ', or string start/end.
# Compiled once at module level for performance.
_DRIVE_FILENAME_DELIM_RE = re.compile(r"(?:^|[_\-. ])")
_DRIVE_FILENAME_DELIM_AFTER_RE = re.compile(r"(?:[_\-. ]|$)")


def _match_drive_filename_to_client(filename: str,
                                     clients: dict[str, dict]) -> str | None:
    """Match a Drive filename to a client domain by alias substring + stop-list.

    D-A4-REVISED rules:
      1. Case-insensitive substring match against `client_domain` (without TLD)
         OR any entry in `aliases[]`.
      2. Stop-list: filenames that ONLY match _DRIVE_FILENAME_STOP_LIST tokens
         return None (caller increments stop-list counter for feed summary).
      3. Word-boundary discipline: match must occur at a delimiter (_, -, ., space)
         or string start/end. Prevents 'STAV' from matching 'staffing.docx'.
      4. Longest alias wins (mirrors _clientid_to_slug's longest-match precedence).
      5. Multi-client match → first alias in left-to-right alphabetical order
         (mirrors D-A2 first-match-wins).

    Returns the matched client_domain (key into `clients` dict), or None for
    no-match / stop-list-only matches.
    """
    name_lower = filename.lower()

    # Build (alias_lower, client_domain) candidate list — include both
    # the domain stem (without TLD) and every alias.
    candidates: list[tuple[str, str]] = []
    for domain, info in clients.items():
        # Domain stem without TLD: 'propertycouncil.com.au' -> 'propertycouncil'
        stem = domain.split(".")[0].lower()
        candidates.append((stem, domain))
        for alias in (info.get("aliases") or []):
            if alias:
                candidates.append((alias.lower(), domain))

    # Stop-list match check (informational only — track for feed summary).
    stop_match = any(
        _has_word_boundary_match(name_lower, token)
        for token in _DRIVE_FILENAME_STOP_LIST
    )

    # Find all candidates that match at a word boundary.
    matches: list[tuple[str, str]] = []
    for token, domain in candidates:
        if _has_word_boundary_match(name_lower, token):
            matches.append((token, domain))

    if not matches:
        return None  # caller checks stop_match for the silent-ignore counter

    # Longest-alias wins (D-A4-REVISED). Tie-break: alphabetical (D-A4 multi-match).
    matches.sort(key=lambda m: (-len(m[0]), m[0]))
    return matches[0][1]


def _has_word_boundary_match(haystack: str, needle: str) -> bool:
    """Return True if needle appears in haystack at a word boundary (D-A4-REVISED).

    Boundaries: '_', '-', '.', ' ', or string start/end.
    """
    if not needle or not haystack:
        return False
    # Build a regex: needle preceded by start-or-delimiter AND followed by
    # end-or-delimiter. Escape needle to handle any regex metacharacters in aliases.
    pattern = rf"(?:^|[_\-. ]){re.escape(needle)}(?:[_\-. ]|$)"
    return re.search(pattern, haystack) is not None
```

**Stop-list constant placement:** put `_DRIVE_FILENAME_STOP_LIST` near the top of the module's constants block (after line 60's `_PRIORITY_BUCKET_NAMES` — it's the closest sibling pattern: a frozenset of stop-tokens used by a routing helper).

**Modification 3: `_gather_events` extension** — line 864

**Current source** (lines 864-950) — already extended in Phase 11 with `cm_expiring`/`cm_invoices` kwargs. Phase 12 follows the SAME ADDITIVE pattern: add `cal_events=None` + `drive_files=None` kwargs.

**Phase 11 source pattern** (lines 910-948 — Phase 11 contract events + CM invoices block):

```python
# --- Phase 11: contract events (D-E1) ---
if cm_expiring is not None:
    for contract in cm_expiring.get("contracts", []) or []:
        cm_client_id = contract.get("clientId")
        slug = _clientid_to_slug(cm_client_id, clients)
        evt = _cm_contract_event_tuple(contract)
        if slug == "_Unknown":
            unknown_pairs.append((evt, {
                "client_name": contract.get("client", ""),
                "client_domain": "",
            }))
        else:
            events_by_slug[slug].append(evt)

# --- Phase 11: CM-tracked invoices (D-D2 + Pitfall 4) ---
local_invoice_numbers: set[str] = set()
for rec in stream_ndjson(data_root / "invoices" / "active.jsonl"):
    n = _normalize_invoice_number(rec.get("invoice_number"))
    if n:
        local_invoice_numbers.add(n)

if cm_invoices is not None:
    for inv in cm_invoices.get("invoices", []) or []:
        cm_num = _normalize_invoice_number(inv.get("invoiceNumber"))
        if cm_num and cm_num in local_invoice_numbers:
            continue
        cm_client_id = inv.get("clientId")
        slug = _clientid_to_slug(cm_client_id, clients)
        evt = _cm_invoice_event_tuple(inv)
        if slug == "_Unknown":
            unknown_pairs.append((evt, {...}))
        else:
            events_by_slug[slug].append(evt)
```

**Phase 12 mirror — Calendar block** (insert after line 923 — immediately following the contract events block):

```python
# --- Phase 12: calendar meeting events (D-A2 + D-C1) ---
seen_event_ids: set[str] = set()  # Pitfall 4 dedup by Google event.id
if cal_events is not None:
    for raw_event in cal_events.get("items", []) or []:
        # Privacy filter already applied in workspace_client.format_calendar_event_for_log
        # (the orchestrator passes pre-filtered events). Defensive re-check is fine but
        # not required — keep this loop trivial.
        event_id = raw_event.get("id")
        if event_id and event_id in seen_event_ids:
            continue
        if event_id:
            seen_event_ids.add(event_id)
        # D-A2: strict attendee email domain match (first-match-wins, alphabetical).
        slug = _route_calendar_event_to_slug(raw_event, clients)
        evt = _cal_meeting_event_tuple(raw_event)
        if slug == "_Unknown":
            unknown_pairs.append((evt, {
                "client_name": "",
                "client_domain": "",
                "from": (raw_event.get("attendees") or [{}])[0].get("email", ""),
            }))
        else:
            events_by_slug[slug].append(evt)
```

**Phase 12 mirror — Drive block** (insert after Calendar block):

```python
# --- Phase 12: drive document events (D-A4-REVISED + D-C2) ---
seen_file_ids: set[str] = set()
stop_list_skipped = 0
if drive_files is not None:
    for raw_file in drive_files.get("files", []) or []:
        file_id = raw_file.get("id")
        if file_id and file_id in seen_file_ids:
            continue
        if file_id:
            seen_file_ids.add(file_id)
        # D-A4-REVISED: filename-based matching with stop-list + longest-alias.
        domain = _match_drive_filename_to_client(
            raw_file.get("name", ""), clients
        )
        if domain is None:
            # Either no-match or stop-list-only match — silently skip.
            # (Caller emits one info-level feed entry per sync with the count.)
            stop_list_skipped += 1
            continue
        slug = clients[domain]["slug"]
        evt = _drive_doc_event_tuple(raw_file)
        events_by_slug[slug].append(evt)
```

**`_route_calendar_event_to_slug` helper** (NEW, near `_route_to_slug` at line 452):

```python
def _route_calendar_event_to_slug(event: dict, clients: dict[str, dict]) -> str:
    """D-A2: route a calendar event to a client slug via attendee email domain.

    Match rule: at least one attendee's email host matches a `client_domain` OR
    appears in that client's `aliases[]`. Multi-client matches resolve to the
    first match in alphabetical client_domain order (D-A2 first-match-wins).

    Returns the client slug, or '_Unknown' on no match (D-04 routing rule preserved).
    """
    attendees = event.get("attendees") or []
    matched_domains: set[str] = set()
    for attendee in attendees:
        email = (attendee.get("email") or "").lower()
        if "@" not in email:
            continue
        host = email.split("@", 1)[1]
        # Direct domain match
        if host in clients:
            matched_domains.add(host)
            continue
        # Alias match: scan all clients for an alias that equals the host
        for domain, info in clients.items():
            aliases_lower = {a.lower() for a in (info.get("aliases") or [])}
            if host in aliases_lower:
                matched_domains.add(domain)
                break
    if not matched_domains:
        return "_Unknown"
    # First-match-wins by alphabetical client_domain order (deterministic)
    chosen = sorted(matched_domains)[0]
    return clients[chosen]["slug"]
```

Note: `load_clients` (lines 356-411) currently does NOT carry `aliases` through into the per-domain dict (lines 387-394). **Phase 12 must extend `load_clients` to carry `aliases`** the same way Phase 11 extended it to carry `cm_client_id` (lines 383-393). Single-line additive change in two places.

**Modification 4: Rename `_fetch_cm_data_for_run` → `_fetch_external_data_for_run`** (with backward-compat alias)

Per RESEARCH.md A9 (line 652): the existing `__all__` exports `_fetch_cm_data_for_run` and tests import this exact symbol. **Recommendation: keep `_fetch_cm_data_for_run` as a thin alias that calls the renamed function** so existing 17 tests pass without modification.

**Source pattern** (vault_writer.py lines 1165-1354 — read in full for orchestration shape).

**Phase 11 orchestration skeleton** (the parts the planner extends):

```python
# vault_writer.py line 1165 — function signature
def _fetch_cm_data_for_run(data_root, clients, feed_path) -> dict:

# Lines 1197-1206 — graceful-skip gate
api_key = os.environ.get("CONTRACT_MANAGER_API_KEY", "")
has_mapped_clients = any(c.get("cm_client_id") is not None for c in clients.values())
if not api_key or not has_mapped_clients:
    return {
        "global_expiring": None, "global_invoices": None,
        "by_domain": {d: {"frontmatter_extra": None, "sla_status": None,
                          "stale_since": None}
                      for d in clients.keys()},
    }

# Lines 1210-1214 — lazy import
from .cm_client import (
    call_with_retry, load_cache, write_cache, gc_cache_orphans,
    cm_summary_to_frontmatter_extra, search_clients_for_domain,
    CmTransportError, CmRpcError,
)

# Lines 1238-1260 — per-tool try/except + cache fallback (THE pattern to mirror)
try:
    exp_result = call_with_retry("list_contracts_expiring", {"days": 90}, api_key)
    cache["global"]["expiring_contracts"] = {
        "fetched_at": now_ts, "lookahead_days": 90, "result": exp_result,
    }
    out["global_expiring"] = exp_result
except (CmTransportError, CmRpcError) as e:
    _warn(f"CM stale (list_contracts_expiring): {type(e).__name__}",
          {"tool": "list_contracts_expiring", "error": str(e)})
    cached = cache.get("global", {}).get("expiring_contracts", {}).get("result")
    out["global_expiring"] = cached  # may be None if no cache
```

**Phase 12 extension shape** (the orchestration is "try CM first, then Cal, then Drive, all with shared retry+cache+warning + per-client try/except isolation"):

```python
def _fetch_external_data_for_run(data_root, clients, feed_path) -> dict:
    """Phase 12 extension of _fetch_cm_data_for_run.

    Returns the SAME shape as Phase 11's _fetch_cm_data_for_run, plus:
        - "global_calendar": dict | None (events.list response, post-filter)
        - "global_drive": dict | None (files.list response, post-filter, per-client routed)

    Three external-data fetches in sequence: CM (Phase 11), Calendar, Drive.
    Each independently retries + falls back to its own cache + emits its own
    warning feed entry. Per-tool failures are isolated; one source down does
    not block the other two.
    """
    # ... Phase 11 CM block stays as-is (lines 1197-1354) ...

    # --- Phase 12: Calendar fetch (NEW) ---
    cal_cache_path = data_root / ".cal-cache.json"
    cal_cache = load_cache(cal_cache_path)  # workspace_client's load_cache
    try:
        access_token = _load_workspace_credentials()  # raises on missing creds
    except WorkspaceTransportError as e:
        # Credentials missing → skip Workspace entirely, log one warning, continue.
        _warn(f"Workspace creds missing: {e}",
              {"tool": "workspace.credentials", "error": str(e)})
        out["global_calendar"] = None
        out["global_drive"] = None
        # Skip to cache write at end (CM already fetched above).
        try:
            write_cache(cache_path, cache)  # CM cache, not Workspace
        except Exception:
            pass
        return out

    # Calendar block — mirrors lines 1238-1260 verbatim, swap names:
    now = datetime.now().astimezone()
    time_min = (now - timedelta(days=90)).isoformat(timespec="seconds")
    time_max = (now + timedelta(days=30)).isoformat(timespec="seconds")
    try:
        cal_result = call_with_retry(
            "calendar/v3/calendars/primary/events",
            {
                "timeMin": time_min, "timeMax": time_max,
                "maxResults": 250, "singleEvents": "true", "orderBy": "startTime",
                "fields": "items(id,summary,start,end,attendees,visibility,htmlLink),nextPageToken",
            },
            access_token,
        )
        # Apply privacy filters AFTER fetch, BEFORE caching (so cache contains pre-filter
        # data — privacy filter is part of the adapter, not the wire format).
        primary_email = os.environ.get("GOOGLE_PRIMARY_EMAIL", "glen@iugo.com.au")
        filtered_items = []
        for raw in cal_result.get("items", []) or []:
            f = format_calendar_event_for_log(raw, primary_email)
            if f is not None:
                filtered_items.append(f)
        filtered_result = {"items": filtered_items}
        cal_cache["global"]["calendar_events"] = {
            "fetched_at": now_ts, "result": filtered_result,
        }
        out["global_calendar"] = filtered_result
    except (WorkspaceTransportError, WorkspaceRpcError) as e:
        _warn(f"Workspace stale (calendar/events): {type(e).__name__}",
              {"tool": "calendar.events", "error": str(e)})
        cached = cal_cache.get("global", {}).get("calendar_events", {}).get("result")
        out["global_calendar"] = cached  # may be None if no cache

    # --- Phase 12: Drive fetch (NEW) ---
    # Per D-A3-REVISED: recursive walk My Drive root, _DRIVE_MAX_DEPTH=3,
    # filter by D-D3 (trashed/draft/restricted), match filenames against client aliases.
    drive_cache_path = data_root / ".drive-cache.json"
    drive_cache = load_cache(drive_cache_path)
    try:
        drive_result = _walk_drive_for_clients(access_token, clients, max_depth=3)
        drive_cache["global"]["drive_files"] = {
            "fetched_at": now_ts, "result": drive_result,
        }
        out["global_drive"] = drive_result
    except (WorkspaceTransportError, WorkspaceRpcError) as e:
        _warn(f"Workspace stale (drive/files): {type(e).__name__}",
              {"tool": "drive.files", "error": str(e)})
        cached = drive_cache.get("global", {}).get("drive_files", {}).get("result")
        out["global_drive"] = cached

    # Persist all three caches (best-effort; failure here doesn't fail the sync).
    for path, c in ((cache_path, cache),
                    (cal_cache_path, cal_cache),
                    (drive_cache_path, drive_cache)):
        try:
            write_cache(path, c)
        except Exception as e:
            _warn(f"Cache write failed: {type(e).__name__}",
                  {"path": str(path), "error": str(e)})

    return out


# Backward-compat alias — keeps Phase 11's 17 mocked tests passing without modification.
_fetch_cm_data_for_run = _fetch_external_data_for_run
```

**Lazy import block** — extend Phase 11's import (lines 1210-1214) with the workspace_client names:

```python
# Phase 11 + Phase 12 lazy imports (single block, inside _fetch_external_data_for_run)
from .cm_client import (
    call_with_retry as cm_call_with_retry,  # rename to avoid shadowing
    load_cache as cm_load_cache,
    write_cache as cm_write_cache,
    gc_cache_orphans, cm_summary_to_frontmatter_extra,
    search_clients_for_domain,
    CmTransportError, CmRpcError,
)
from .workspace_client import (
    call_with_retry, load_cache, write_cache,
    format_calendar_event_for_log, format_drive_file_for_log,
    _load_workspace_credentials, _walk_drive_for_clients,
    WorkspaceTransportError, WorkspaceRpcError,
)
```

**ALTERNATIVE (cleaner — recommended):** keep CM and Workspace name spaces separate via module aliases:
```python
from . import cm_client as _cm
from . import workspace_client as _ws
```
This mirrors `run_map_cm_clients`'s `from . import cm_client as _cm` idiom (vault_writer.py line 1084) and avoids collision on `call_with_retry`/`load_cache`/`write_cache` which exist in BOTH modules. Planner picks one and stays consistent.

**Modification 5: `run_backfill` threading** — line 953-1049

**Current source** (line 997-1003 — single fetch + thread):
```python
cm_data = _fetch_cm_data_for_run(data_root, clients, feed_path)

events_by_slug, unknown_pairs = _gather_events(
    data_root, clients,
    cm_expiring=cm_data["global_expiring"],
    cm_invoices=cm_data["global_invoices"],
)
```

**Phase 12 change** (additive — same call site, two more kwargs):
```python
external_data = _fetch_external_data_for_run(data_root, clients, feed_path)

events_by_slug, unknown_pairs = _gather_events(
    data_root, clients,
    cm_expiring=external_data["global_expiring"],
    cm_invoices=external_data["global_invoices"],
    cal_events=external_data["global_calendar"],   # Phase 12 NEW
    drive_files=external_data["global_drive"],     # Phase 12 NEW
)
```

The `bucket = cm_data["by_domain"].get(domain, {})` access on lines 1015-1018 stays unchanged (Phase 12 doesn't add per-domain buckets — Calendar/Drive are routed inside `_gather_events` rather than per-client).

**Modification 6: `__all__` extension** — lines 1791-1811

**Current source** (lines 1804-1809):
```python
# Phase 11 helpers
"_normalize_invoice_number", "_clientid_to_slug",
"_cm_contract_event_tuple", "_cm_invoice_event_tuple",
"_fetch_cm_data_for_run",
```

**Phase 12 additions** (additive — append after Phase 11 helpers):
```python
# Phase 12 helpers
"_cal_meeting_event_tuple", "_drive_doc_event_tuple",
"_match_drive_filename_to_client", "_has_word_boundary_match",
"_route_calendar_event_to_slug",
"_fetch_external_data_for_run",  # the renamed sibling
"_DRIVE_FILENAME_STOP_LIST",
```

**Modification 7: `run_projection` docstring INVARIANT block extension** — line 1551

**Current source** (lines 1551-1556):
```python
INVARIANT (Phase 11 Pitfall 1 — T-11-04-01): This function MUST NOT import or
call cm_client. The Mac daemon runs `--mode project-to-icloud` and has no CM
API key. Any future contributor adding a CM call here breaks the design and
produces URLError noise on Mac sync logs. Negative test:
TestProjectionDoesNotImportCm spawns a fresh Python subprocess and asserts
`scripts.lib.cm_client` is NOT in `sys.modules` after run_projection returns.
```

**Phase 12 extension** (additive sentence in the same INVARIANT block):
```python
INVARIANT (Phase 11 Pitfall 1 — T-11-04-01, extended Phase 12 — T-12-01):
This function MUST NOT import or call cm_client OR workspace_client. The Mac
daemon runs `--mode project-to-icloud` and has neither a CM API key nor a
Workspace OAuth blob. Any future contributor adding either call here breaks
the design and produces URLError / FileNotFoundError noise on Mac sync logs.
Negative tests: TestProjectionDoesNotImportCm AND TestProjectionDoesNotImportWorkspace
each spawn a fresh Python subprocess and assert the respective module is NOT
in `sys.modules` after run_projection returns.
```

---

### 4. `scripts/tests/test_vault_writer.py` (MODIFIED)

**Role:** Test extension — six new test classes for Phase 12 (mirrors Phase 11 Plan 04's six new classes).

**Analog:** Self — Phase 11 added 6 test classes after `TestUsageSection`; Phase 12 adds 6 more after Phase 11's last class (`TestJitMapping`, line 1153).

**Phase 11 test class layout** (test_vault_writer.py — lines listed):
- `TestGatherEventsCmIntegration` (line 798) — 6 tests for `_gather_events` extension
- `TestContractMerge` (line 934) — 2 tests for event-tuple shape
- `TestProjectionDoesNotImportCm` (line 957) — 1 subprocess-based negative test
- `TestCacheFallbackEnd2End` (line 985) — 2 tests for cache fallback + stale_since stamping
- `TestBackfillIdempotentPhase11` (line 1088) — 1 test for D-14/D-16 idempotency under Phase 11
- `TestJitMapping` (line 1153) — 3 tests for D-G1 JIT fallback paths

**Phase 12 test class layout** (insert after `TestJitMapping`, line 1308):

| Phase 11 class | Phase 12 mirror | Test count |
|----------------|-----------------|------------|
| `TestGatherEventsCmIntegration` | `TestGatherEventsCalendarIntegration` | 4 (route by attendee, dedup by event ID per Pitfall 4, multi-client first-match-wins, no-cal-kwargs Phase 11 backwards compat) |
| `TestGatherEventsCmIntegration` | `TestGatherEventsDriveIntegration` | 5 (filename match, stop-list ignored, longest-alias-wins, word-boundary discipline, no-drive-kwargs backwards compat) |
| `TestContractMerge` | `TestActivityLogMergePhase12` | 4 (render_log_line accepts kind="meeting" + kind="doc", _cal_meeting_event_tuple shape, _drive_doc_event_tuple shape) |
| (NEW — privacy filters) | `TestPrivacyFilters` | 5 (D-D1 visibility=private, D-D1 no-external-attendees, D-D2 >25 attendees, D-D3 trashed, D-D3 .gdraft) |
| `TestProjectionDoesNotImportCm` | `TestProjectionDoesNotImportWorkspace` | 1 subprocess test |
| `TestCacheFallbackEnd2End` | `TestWorkspaceCacheFallbackEnd2End` | 2 (cal cache fallback, drive cache fallback) |
| `TestBackfillIdempotentPhase11` | `TestBackfillIdempotentPhase12` | 1 (mocked Cal+Drive responses → byte-identical across runs) |

**TestProjectionDoesNotImportWorkspace pattern** (test_vault_writer.py lines 957-983 — copy verbatim, change `cm_client` → `workspace_client`):

**Source pattern:**
```python
class TestProjectionDoesNotImportCm(unittest.TestCase):
    def test_projection_does_not_import_cm_client(self):
        with tempfile.TemporaryDirectory() as build, tempfile.TemporaryDirectory() as icloud:
            (Path(build) / "Clients").mkdir()
            code = (
                "import sys; "
                "from scripts.lib.vault_writer import run_projection; "
                f"run_projection(__import__('pathlib').Path({build!r}), "
                f"__import__('pathlib').Path({icloud!r}), dry_run=True); "
                "print('CMCLIENT_LOADED' if 'scripts.lib.cm_client' in sys.modules "
                "else 'CMCLIENT_NOT_LOADED')"
            )
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, cwd=os.getcwd(),
            )
            self.assertEqual(result.returncode, 0,
                             f"subprocess failed: {result.stderr}")
            self.assertIn("CMCLIENT_NOT_LOADED", result.stdout)
```

**Phase 12 mirror — same shape, two assertions:**
```python
class TestProjectionDoesNotImportWorkspace(unittest.TestCase):
    """Pitfall 1 inheritance (T-12-01): Mac daemon's run_projection MUST NOT
    pull workspace_client into sys.modules. Subprocess-based for the same
    reason as TestProjectionDoesNotImportCm — in-process tests would see
    workspace_client from earlier test classes that DO import it.
    """
    def test_projection_does_not_import_workspace_client(self):
        with tempfile.TemporaryDirectory() as build, tempfile.TemporaryDirectory() as icloud:
            (Path(build) / "Clients").mkdir()
            code = (
                "import sys; "
                "from scripts.lib.vault_writer import run_projection; "
                f"run_projection(__import__('pathlib').Path({build!r}), "
                f"__import__('pathlib').Path({icloud!r}), dry_run=True); "
                "print('WS_LOADED' if 'scripts.lib.workspace_client' in sys.modules "
                "else 'WS_NOT_LOADED'); "
                "print('CM_LOADED' if 'scripts.lib.cm_client' in sys.modules "
                "else 'CM_NOT_LOADED')"
            )
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, cwd=os.getcwd(),
            )
            self.assertEqual(result.returncode, 0,
                             f"subprocess failed: {result.stderr}")
            self.assertIn("WS_NOT_LOADED", result.stdout)
            self.assertIn("CM_NOT_LOADED", result.stdout)  # Phase 11 inheritance
```

**TestWorkspaceCacheFallbackEnd2End pattern** (test_vault_writer.py lines 985-1086 — `TestCacheFallbackEnd2End` is the analog):

Read lines 988-1015 (`_setup` + `_cached_summary` helpers) — copy and adapt:
- `_setup`: write a `clients.jsonl` with `aliases` (Phase 12 needs them for filename matching)
- `_cached_calendar()`: build a Calendar API response shape with one event
- `_cached_drive()`: build a Drive API response shape with one file

Read lines 1037-1042 (the patching idiom):
```python
with mock.patch.dict(os.environ, {"CONTRACT_MANAGER_API_KEY": "k"}), \
     mock.patch("scripts.lib.cm_client._cm_post",
                side_effect=CmTransportError("down")), \
     mock.patch("scripts.lib.cm_client.time.sleep"):
    from scripts.lib.vault_writer import run_backfill
    stats = run_backfill(data_root, Path(build), feed_path=feed_path)
```

Phase 12 mirror — patch `scripts.lib.workspace_client._workspace_get` (the network seam):
```python
with mock.patch.dict(os.environ, {
        "CONTRACT_MANAGER_API_KEY": "k",
        "GOOGLE_PRIMARY_EMAIL": "glen@iugo.com.au",
     }), \
     mock.patch("scripts.lib.workspace_client._workspace_get",
                side_effect=WorkspaceTransportError("down")), \
     mock.patch("scripts.lib.workspace_client._load_workspace_credentials",
                return_value="fake_token"), \
     mock.patch("scripts.lib.workspace_client.time.sleep"), \
     mock.patch("scripts.lib.cm_client._cm_post",
                side_effect=lambda *a, **k: {"contracts": []}):  # CM returns empty fast
    from scripts.lib.vault_writer import run_backfill
    stats = run_backfill(data_root, Path(build), feed_path=feed_path)
```

**TestBackfillIdempotentPhase12 — `_snapshot` extension:**

Read test_vault_writer.py lines 1142-1150 (`_snapshot` helper):
```python
def _snapshot(self, build_root: Path) -> dict:
    out = {}
    for md in sorted((build_root / "Clients").glob("*.md")):
        lines = md.read_text(encoding="utf-8").splitlines()
        filtered = [ln for ln in lines
                    if not ln.startswith("last_synced:")
                    and not ln.startswith("cm_data_stale_since:")]
        out[md.name] = "\n".join(filtered)
    return out
```

Phase 12 extension — also strip `workspace_data_stale_since:` (per RESEARCH.md Pattern 4 line 327 recommendation: introduce a new key rather than broaden `cm_data_stale_since`):
```python
def _snapshot(self, build_root: Path) -> dict:
    out = {}
    for md in sorted((build_root / "Clients").glob("*.md")):
        lines = md.read_text(encoding="utf-8").splitlines()
        filtered = [ln for ln in lines
                    if not ln.startswith("last_synced:")
                    and not ln.startswith("cm_data_stale_since:")
                    and not ln.startswith("workspace_data_stale_since:")]
        out[md.name] = "\n".join(filtered)
    return out
```

**ALSO update `TestBackfillIdempotent._snapshot_managed`** (line 220) — same one-line addition. Phase 11's `TestBackfillIdempotent` will start failing under Phase 12 if `workspace_data_stale_since` ever leaks into its fixture; the additive filter line keeps Phase 10 backwards compat.

---

### 5. `scripts/sync-obsidian.sh` (MODIFIED)

**Role:** Coolify entry-point — extend env validation for Workspace OAuth.

**Analog:** `scripts/sync-obsidian.sh` lines 29-33 (Phase 11's `CONTRACT_MANAGER_API_KEY` validation).

**Source pattern** (lines 29-33):
```bash
# ----- Phase 11: CM MCP API key validation -----
# CONTRACT_MANAGER_API_KEY is required for CM JSON-RPC calls (D-A2). The Mac daemon
# does NOT run this wrapper (Pitfall 1: Mac never calls CM by design), so this validation
# only fires on Coolify. The ${VAR:?msg} idiom aborts with the msg if VAR is unset OR empty.
: "${CONTRACT_MANAGER_API_KEY:?CONTRACT_MANAGER_API_KEY env var required (set on Coolify; not on Mac)}"
```

**Phase 12 extension** (additive — insert immediately after Phase 11's block):
```bash
# ----- Phase 12: Workspace OAuth credentials validation -----
# GOOGLE_MCP_CREDENTIALS_DIR points at the directory containing OAuth token blobs
# minted by hardened-workspace MCP (default: ~/.google_workspace_mcp/credentials).
# Phase 12 reads these directly to call Google Calendar v3 + Drive v3 (D-X1).
# Like CM, this only fires on Coolify (Mac daemon does NOT run sync-obsidian.sh).
# RESEARCH.md A2 + Q3 confirm Coolify must have this directory populated.
: "${GOOGLE_MCP_CREDENTIALS_DIR:=$HOME/.google_workspace_mcp/credentials}"
if [ ! -d "$GOOGLE_MCP_CREDENTIALS_DIR" ]; then
  echo "scripts/sync-obsidian.sh: GOOGLE_MCP_CREDENTIALS_DIR not found at $GOOGLE_MCP_CREDENTIALS_DIR" >&2
  echo "Expected directory containing OAuth token blob (set by hardened-workspace MCP)." >&2
  echo "On Coolify: copy from Mac via rclone OR mint fresh OAuth via auth flow." >&2
  exit 1
fi
```

**Note on default:** the `${VAR:=default}` idiom (assignment) gives a stable default; the `${VAR:?msg}` idiom (Phase 11 form) requires the var be explicitly set. Phase 12 uses the assignment form because there IS a sensible default path; Phase 11 had no sensible default for an API key. Both idioms are correct for their use cases.

**`GOOGLE_PRIMARY_EMAIL` env var:** the calendar privacy filter (D-D1) needs Glen's primary email to detect "no external attendees". Add a third validation line (or default to `glen@iugo.com.au` since RESEARCH.md confirms it):
```bash
: "${GOOGLE_PRIMARY_EMAIL:=glen@iugo.com.au}"
```
This stays in the wrapper rather than hardcoded in `workspace_client.py` because Glen's email is operational config, not code.

---

### 6. `.gitignore` (MODIFIED)

**Role:** Exclude per-tool runtime caches from git (mirror Phase 11's pattern verbatim).

**Analog:** `.gitignore` line 33-34 (Phase 11's CM cache rule).

**Source pattern** (lines 33-34):
```
# Phase 11: Contract Manager response cache (per-host runtime state, fallback only — D-F1)
data/.cm-cache.json
```

**Phase 12 extension** (additive — append at end of file):
```
# Phase 12: Workspace API response caches (per-host runtime state, fallback only — D-A3 + D-F1 mirror)
data/.cal-cache.json
data/.drive-cache.json
```

**Verification:** `git check-ignore data/.cal-cache.json && git check-ignore data/.drive-cache.json` returns both paths (CONTEXT.md verification anchor 6).

---

### 7. `data/config/clients.jsonl` (READ-ONLY)

**Role:** Reference data — Phase 12 reads `aliases[]` array per client; does NOT write.

**Sample row** (from `head -1 data/config/clients.jsonl`):
```json
{"domain": "propertycouncil.com.au", "name": "Property Council Australia", "aliases": ["pca"], "contact": "Craig Horton", "cm_client_id": 18}
```

**Phase 12 reads:**
- `domain` — used as canonical client_domain
- `aliases[]` — used by both `_route_calendar_event_to_slug` (Calendar attendee match) AND `_match_drive_filename_to_client` (Drive filename match)
- `name` — used for filename match against the domain stem (already supported via `domain.split(".")[0]`)

**Phase 12 does NOT write.** No JIT-mapping equivalent for Workspace (unlike Phase 11's D-G1 which mints `cm_client_id` on-demand). RESEARCH.md confirms Workspace uses domain stems + aliases — no external ID to mint.

**`load_clients` extension required** (vault_writer.py lines 379-394):

The current implementation drops `aliases` on the floor:
```python
# Lines 379-384 — raw_entries DOES NOT capture aliases
raw_entries.append({
    "name": name,
    "domain": domain,
    "status": rec.get("status", "active"),
    "cm_client_id": rec.get("cm_client_id"),
})

# Lines 387-394 — per-domain output dict DOES NOT carry aliases
out[r["domain"]] = {
    "slug": safe_slugify(r["name"], r["domain"]),
    "client_name": r["name"],
    "domain": r["domain"],
    "status": r["status"],
    "cm_client_id": r.get("cm_client_id"),
}
```

**Phase 12 change** (additive — single `aliases` field):
```python
raw_entries.append({
    "name": name,
    "domain": domain,
    "status": rec.get("status", "active"),
    "cm_client_id": rec.get("cm_client_id"),
    "aliases": rec.get("aliases") or [],  # Phase 12 NEW
})

out[r["domain"]] = {
    "slug": safe_slugify(r["name"], r["domain"]),
    "client_name": r["name"],
    "domain": r["domain"],
    "status": r["status"],
    "cm_client_id": r.get("cm_client_id"),
    "aliases": r.get("aliases") or [],  # Phase 12 NEW
}
```

This is the single Phase 11 pattern (lines 383-393) extended by one field, identical idiom. No tests of `load_clients` shape change are needed beyond verifying that `aliases` is reachable from a downstream caller (covered by `TestGatherEventsDriveIntegration` and `TestGatherEventsCalendarIntegration`).

---

## Shared Patterns

These cross-cutting patterns apply to multiple Phase 12 files; the planner extracts each into the right Plan.

### Shared Pattern 1: Lazy Import Discipline (Pitfall 1 inheritance)

**Source:** `scripts/lib/vault_writer.py` lines 1208-1214 (Phase 11 lazy import) AND lines 1551-1556 (run_projection INVARIANT docstring).

**Apply to:** All Phase 12 imports of `workspace_client`.

```python
# CORRECT (inside _fetch_external_data_for_run body):
from .workspace_client import (
    call_with_retry, load_cache, write_cache,
    format_calendar_event_for_log, format_drive_file_for_log,
    _load_workspace_credentials,
    WorkspaceTransportError, WorkspaceRpcError,
)

# WRONG (module top of vault_writer.py):
from .workspace_client import call_with_retry  # breaks Pitfall 1
```

**Verification:**
- `grep -E "^from .workspace_client" scripts/lib/vault_writer.py` returns 0 matches
- `TestProjectionDoesNotImportWorkspace` subprocess test passes

---

### Shared Pattern 2: Per-Tool Try/Except + Cache Fallback + Warning Feed Entry

**Source:** `scripts/lib/vault_writer.py` lines 1238-1260 (Phase 11 list_contracts_expiring block) — read this block as the canonical shape.

**Apply to:** Every external-data fetch in `_fetch_external_data_for_run` — Phase 11 has 4 (2 global + 2 per-client); Phase 12 adds at minimum 2 more (calendar global + drive global).

**Pattern shape:**
```python
try:
    result = call_with_retry(<tool_path>, <params>, <auth>)
    cache["<scope>"]["<tool_key>"] = {"fetched_at": now_ts, "result": result}
    out["<output_key>"] = result
except (<TransportError>, <RpcError>) as e:
    _warn(f"<system> stale (<tool_key>): {type(e).__name__}",
          {"tool": "<tool_key>", "error": str(e)})
    cached = cache.get("<scope>", {}).get("<tool_key>", {}).get("result")
    out["<output_key>"] = cached  # may be None if no cache
```

**Three failure modes per D-A3:**
1. Live succeeds → cache write + `out` populated, no warning
2. Live fails, cache hit → `out` populated from cache + warning emitted + stale_since stamped
3. Live fails, cache miss → `out["<output_key>"] = None` + warning emitted + downstream renders "unavailable" placeholder

---

### Shared Pattern 3: Atomic Whole-File Write

**Source:** `scripts/lib/vault_writer.py` lines 325-351 (`_atomic_write` — tempfile + os.replace + dir-fsync).

**Apply to:** All cache writes in `workspace_client.py`. Reuse via `from .vault_writer import _atomic_write` (Phase 11 cm_client.py line 20 — `noqa: F401`).

**Anti-pattern to avoid:** Hand-rolling tempfile + rename in `workspace_client.py`. RESEARCH.md line 346 explicitly calls this out as a Don't-Hand-Roll.

---

### Shared Pattern 4: Subprocess-Based Negative Test for Module Cache

**Source:** `scripts/tests/test_vault_writer.py` lines 957-983 (`TestProjectionDoesNotImportCm`).

**Apply to:** `TestProjectionDoesNotImportWorkspace` (Phase 12 mirror).

**Why subprocess and not in-process:** an in-process test would see `workspace_client` in `sys.modules` from earlier test classes that DID import it (e.g., `TestPrivacyFilters`, `TestWorkspaceCacheFallbackEnd2End`). Subprocess starts with a clean module cache so the assertion is meaningful. SUMMARY 11-04 line 158 explains this in detail.

---

### Shared Pattern 5: Mock Response for `urllib.request.urlopen`

**Source:** `scripts/tests/test_cm_client.py` lines 18-27 (`_mock_response` helper).

**Apply to:** `test_workspace_client.py` `TestWorkspaceClient`. Copy verbatim — no changes.

The pattern works for Calendar v3 + Drive v3 + OAuth refresh equally well because all three return JSON via `urlopen`.

---

### Shared Pattern 6: Mock at the Network Seam, Never at urllib

**Source:** Both `test_cm_client.py` and `test_vault_writer.py` Phase 11 test classes:
- `test_cm_client.py` patches `scripts.lib.cm_client.urllib.request.urlopen` (only because that file IS the seam)
- `test_vault_writer.py` patches `scripts.lib.cm_client._cm_post` (the higher-level seam, because vault_writer never touches urllib directly)

**Apply to:** Phase 12 follows the same hierarchy:
- `test_workspace_client.py` patches `scripts.lib.workspace_client.urllib.request.urlopen`
- `test_vault_writer.py` patches `scripts.lib.workspace_client._workspace_get` (the seam vault_writer indirectly calls)

This keeps the test pyramid clean: low-level tests verify the wire format, high-level tests verify orchestration without re-testing the wire.

---

### Shared Pattern 7: Snapshot-Strip for Idempotency Tests

**Source:** `scripts/tests/test_vault_writer.py` lines 220-235 (`TestBackfillIdempotent._snapshot_managed`) AND lines 1142-1150 (`TestBackfillIdempotentPhase11._snapshot`).

**Apply to:** `TestBackfillIdempotentPhase12._snapshot` AND extend the Phase 10/11 helpers with the new staleness key.

**Pattern:** filter out per-run trust signals before byte-comparing two consecutive runs.

```python
filtered = [ln for ln in lines
            if not ln.startswith("last_synced:")
            and not ln.startswith("cm_data_stale_since:")
            and not ln.startswith("workspace_data_stale_since:")]  # Phase 12 NEW
```

**Why three classes get the same one-line edit:** D-14/D-16 idempotency contract is "managed-section content modulo per-run trust signals". Each phase that adds a new trust signal extends the strip filter. Three places, three identical lines.

---

### Shared Pattern 8: Hardcoded Constant + Word-Boundary Regex (Phase 12 NEW)

**Source:** `scripts/lib/vault_writer.py` line 60 (`_PRIORITY_BUCKET_NAMES = frozenset({...})`) — closest sibling pattern: a frozenset of stop-tokens used by a routing helper (`render_unknown_note` lines 831-835 uses it for "leaked priority groups" detection).

**Apply to:** `_DRIVE_FILENAME_STOP_LIST` (D-A4-REVISED stop-list) AND `GLEN_INTERNAL_DOMAINS` (D-D1 internal-domain detection).

**Pattern shape:**
```python
# Module-level frozenset constant
_DRIVE_FILENAME_STOP_LIST = frozenset({"agend", "iugo", "glen", "rosie"})

# Word-boundary regex — compile once at module level
_DRIVE_FILENAME_DELIM_RE = re.compile(r"(?:^|[_\-. ])")

# Helper that combines them
def _has_word_boundary_match(haystack: str, needle: str) -> bool:
    if not needle or not haystack:
        return False
    pattern = rf"(?:^|[_\-. ]){re.escape(needle)}(?:[_\-. ]|$)"
    return re.search(pattern, haystack) is not None
```

**Test pattern:** unit-test `_has_word_boundary_match` with three positive cases (start, middle-with-delims, end) and three negative cases (no-delim-before, no-delim-after, both). Mirrors Phase 10's `TestSlugify` style (test_vault_writer.py lines 15-44).

---

### Shared Pattern 9: Longest-Match Precedence (Phase 12 inherits from Phase 11 idiom)

**Source pattern context:** `_clientid_to_slug` (vault_writer.py lines 536-546) is a reverse-lookup with a single-match contract; it doesn't show longest-match precedence directly. But CONTEXT.md D-A4-REVISED references "Mirrors `_clientid_to_slug` longest-match logic from Phase 11" — this is a slight misattribution. The actual longest-match pattern is more akin to **dictionary trie matching with deterministic tie-break**. There is no exact analog in the codebase for "longest substring of N candidates wins"; Phase 12 is the first place this pattern appears.

**Apply to:** `_match_drive_filename_to_client` (the only site that needs longest-match).

**Pattern shape** (sort by negative length, then alphabetical for tie-break):
```python
matches.sort(key=lambda m: (-len(m[0]), m[0]))
return matches[0][1]
```

**Test pattern:** include a fixture where two aliases would both match (`PCA` + `PCNZ` against `PCNZ-Doc.docx`); assert `PCNZ` wins (longer). Then a fixture with two equal-length aliases; assert alphabetical tie-break.

---

## No Analog Found

| File / Pattern | Reason | Recommendation |
|----------------|--------|----------------|
| OAuth token refresh helper (`_refresh_workspace_token`) | CM uses long-lived API keys; no OAuth flow exists in the codebase | Implement per RESEARCH.md line 425-426: 30-line urllib POST to `oauth2.googleapis.com/token`. Cite Google's official quickstart in the docstring. |
| Recursive Drive walker (`_walk_drive_for_clients`) | Drive's recursive query semantics are unique to v3 API; nothing in the codebase walks a remote tree | Implement per RESEARCH.md line 343 (Don't-Hand-Roll): single `q="parents in [...]"` query per folder, NOT a Python recursive walker. Bound by `_DRIVE_MAX_DEPTH = 3` per CONTEXT.md D-A3-REVISED. |
| Endpoint allowlist grep-lint test | No prior grep-lint test exists in the test suite | Use the shape proposed in §2 above (read source file, regex-find endpoint paths, assert subset of allowlist constant). The test reads the production constant as source-of-truth — same self-documenting style as `TestProjectionDoesNotImportCm`. |

---

## Metadata

**Analog search scope:**
- `/Users/glenr/work/todo-list/scripts/lib/` (vault_writer.py, cm_client.py — full read)
- `/Users/glenr/work/todo-list/scripts/tests/` (test_vault_writer.py, test_cm_client.py — targeted reads)
- `/Users/glenr/work/todo-list/scripts/sync-obsidian.sh` — full read
- `/Users/glenr/work/todo-list/.gitignore` — full read
- `/Users/glenr/work/todo-list/.planning/phases/11-*/11-04-SUMMARY.md` — full read
- `/Users/glenr/work/todo-list/.planning/phases/12-*/12-CONTEXT.md` — full read
- `/Users/glenr/work/todo-list/.planning/phases/12-*/12-RESEARCH.md` — targeted reads (lines 1-50, 240-410, 450-710)

**Files scanned:** 8 source files + 3 planning docs

**Pattern extraction date:** 2026-05-03

**Phase 11 quality bar reference:** SUMMARY 11-04 (commit `e2c56cb`) — 17 mocked tests, 7-min duration, 4 commits (TDD RED → GREEN per task). Phase 12 should match this discipline: lazy imports verified by subprocess test, per-tool try/except + cache fallback, snapshot-strip idempotency, single-network-seam test mocking.
