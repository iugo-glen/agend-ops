"""Phase 12 — Google Workspace (Calendar + Drive) REST client.

Single-purpose: invoke Calendar v3 + Drive v3 REST APIs at googleapis.com via
HTTPS GET, with retry+cache-fallback per Phase 11 D-A3 pattern.

Test seam: `_workspace_get` is the only function that touches the network. Tests
patch `_workspace_get`, NOT `urllib.request.urlopen` (except TestWorkspaceClient
which DOES patch urlopen to verify the seam itself). See test_workspace_client.py.

Cache shape: per-tool — data/.cal-cache.json + data/.drive-cache.json (per
RESEARCH Q6; mirrors Phase 11 D-F1 cm-cache pattern).

Trust boundary (D-X1): this module makes Google API calls using the OAuth blob
originally minted by hardened-workspace MCP. The hardened MCP DELIBERATELY
removes write-capable tools (permissions.update, share_drive_file, etc.) for
prompt-injection defence. Direct-API access here re-enables those endpoints at
the SDK level, so we mitigate via:
  1. Strict endpoint allowlist (WORKSPACE_ALLOWED_ENDPOINTS) checked at
     _workspace_get's first line.
  2. HTTP method hardcoded to "GET" — no POST/PUT/PATCH/DELETE codepath exists.
  3. CI grep-lint test (TestWorkspaceClientEndpointAllowlist) catches accidental
     write paths before merge.

Mac daemon isolation (Pitfall 1 inheritance): this module is imported LAZILY
inside vault_writer._fetch_external_data_for_run (Wave 3). Module top of
vault_writer.py MUST NOT contain `from .workspace_client import ...`.
TestProjectionDoesNotImportWorkspace enforces in CI.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Reuse vault_writer's atomic-write helper (Don't Hand-Roll line 261-264 of 12-PATTERNS.md).
# now_iso_with_offset is imported here for cache-stamping in Wave 3 callers; pulling it via
# this seam keeps Phase 11/12 timestamp parity (single source of truth).
from .vault_writer import _atomic_write, now_iso_with_offset  # noqa: F401


# Module constants -------------------------------------------------------------

RETRY_DELAYS = (1, 5, 30)  # D-A3 inheritance — same shape as cm_client
TIMEOUT_S = 15
CACHE_SCHEMA_VERSION = 1
OAUTH_TOKEN_REFRESH_URL = "https://oauth2.googleapis.com/token"
OAUTH_REFRESH_LEEWAY_S = 60  # Pitfall 6: refresh if expiry < now + 60s

# D-X1 trust boundary: workspace_client.py is read-only by construction. Any
# endpoint outside this allowlist is a bug, not a feature. Adding an entry here
# is a CONSCIOUS scope expansion that requires updating the threat model.
WORKSPACE_ALLOWED_ENDPOINTS = frozenset({
    "calendar/v3/calendars/primary/events",
    "drive/v3/files",
})
WORKSPACE_ALLOWED_ENDPOINT_PREFIXES = ("drive/v3/files/",)  # for /{id} variants

# D-D1 internal-domain set — events with no attendees outside this set are
# treated as personal/internal and filtered out (see format_calendar_event_for_log).
GLEN_INTERNAL_DOMAINS = frozenset({"iugo.com.au"})


# Errors -----------------------------------------------------------------------

class WorkspaceTransportError(Exception):
    """Network failure or non-2xx HTTP status (other than 401, 429)."""


class WorkspaceRpcError(Exception):
    """Google API error envelope: {"error": {"code": int, "message": str}}."""


class WorkspaceRateLimitError(WorkspaceTransportError):
    """429 response. Carries `retry_after_seconds` parsed from Retry-After header."""

    def __init__(self, retry_after_seconds: int):
        super().__init__(f"rate-limited; retry after {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds


class WorkspaceAuthExpiredError(WorkspaceTransportError):
    """401 response. Caller refreshes OAuth token and retries once.

    No analog in cm_client (CM uses long-lived API keys). Per RESEARCH Pitfall 6:
    OAuth access tokens are 1-hour TTL; a long backfill can cross the boundary.
    """


# Endpoint allowlist gate ------------------------------------------------------

def _check_endpoint_allowed(api_path: str) -> None:
    """Trust boundary: workspace_client.py is read-only by construction (D-X1).

    Any endpoint outside this allowlist is a bug, not a feature. The grep-lint
    test TestWorkspaceClientEndpointAllowlist verifies allowlist completeness in CI.
    """
    if api_path in WORKSPACE_ALLOWED_ENDPOINTS:
        return
    if any(api_path.startswith(p) for p in WORKSPACE_ALLOWED_ENDPOINT_PREFIXES):
        return
    raise WorkspaceTransportError(
        f"endpoint not in allowlist: {api_path!r} — see workspace_client.py "
        f"WORKSPACE_ALLOWED_ENDPOINTS"
    )


# Single network seam ----------------------------------------------------------

def _workspace_get(api_path: str, params: dict, access_token: str) -> dict:
    """Single HTTPS GET call to googleapis.com. Returns the parsed JSON dict.

    Tests patch THIS function (not urllib.request.urlopen) — except
    TestWorkspaceClient which patches urlopen to verify the seam end-to-end.

    Raises:
        WorkspaceAuthExpiredError on 401 (caller refreshes token + retries once)
        WorkspaceRateLimitError on 429 (caller backs off retry_after seconds)
        WorkspaceTransportError on other 4xx/5xx, network error, decode error,
            or disallowed endpoint
        WorkspaceRpcError on Google API error envelope
    """
    _check_endpoint_allowed(api_path)

    url = f"https://www.googleapis.com/{api_path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise WorkspaceAuthExpiredError(f"HTTP 401: {e.reason}") from e
        if e.code == 429:
            try:
                retry_after = int(e.headers.get("Retry-After", "30"))
            except (ValueError, TypeError):
                retry_after = 30
            raise WorkspaceRateLimitError(retry_after) from e
        raise WorkspaceTransportError(f"HTTP {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise WorkspaceTransportError(f"network: {e.reason}") from e
    except (json.JSONDecodeError, OSError) as e:
        raise WorkspaceTransportError(f"decode: {e}") from e

    if isinstance(payload, dict) and "error" in payload:
        err = payload["error"] or {}
        raise WorkspaceRpcError(f"{err.get('code')}: {err.get('message')}")

    return payload


# Retry wrapper (D-A3: 1s/5s/30s; respect Retry-After once; auth-expired propagates) ---

def call_with_retry(api_path: str, params: dict, access_token: str) -> dict:
    """D-A3 retry loop. Caller falls back to cache on final raise.

    Auth-expired errors propagate immediately so the caller can refresh the
    OAuth token and retry once at a higher level (orchestration concern).
    """
    last_err: Exception | None = None
    delays = (0,) + RETRY_DELAYS
    for delay in delays:
        if delay:
            time.sleep(delay)
        try:
            return _workspace_get(api_path, params, access_token)
        except WorkspaceAuthExpiredError:
            # Don't consume a retry on auth — propagate so caller refreshes token.
            raise
        except WorkspaceRateLimitError as e:
            time.sleep(e.retry_after_seconds)
            last_err = e
        except (WorkspaceTransportError, WorkspaceRpcError) as e:
            last_err = e
    assert last_err is not None
    raise last_err


# Cache I/O --------------------------------------------------------------------

def _empty_cache() -> dict:
    return {"schema_version": CACHE_SCHEMA_VERSION, "global": {}, "by_client": {}}


def load_cache(cache_path: Path) -> dict:
    """Return cache dict or a fresh skeleton on missing/corrupt cache.

    Mirrors cm_client.load_cache exactly — fallback-only, never raises.
    """
    if not cache_path.exists():
        return _empty_cache()
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or data.get("schema_version") != CACHE_SCHEMA_VERSION:
            return _empty_cache()
        # Defensive: ensure required sub-keys exist (mirrors cm_client.load_cache)
        data.setdefault("global", {})
        data.setdefault("by_client", {})
        return data
    except (OSError, json.JSONDecodeError):
        return _empty_cache()


def write_cache(cache_path: Path, cache: dict) -> None:
    """Atomic whole-file write of the cache (temp+rename via vault_writer._atomic_write).

    Mirrors cm_client.write_cache exactly. The trailing newline matches the
    convention used by other JSON artifacts in the repo (feed.jsonl, etc.).
    """
    content = json.dumps(cache, indent=2, sort_keys=True) + "\n"
    _atomic_write(cache_path, content)


def gc_cache_orphans(cache: dict, known_domains: set) -> dict:
    """Drop `by_client` entries whose domain is not in `known_domains`.

    Mirrors cm_client.gc_cache_orphans. Mutates `cache` in place AND returns it
    (caller pattern: `cache = gc_cache_orphans(cache, known)`). For Phase 12,
    Calendar + Drive both use global-only caches (no `by_client` entries), but
    keeping the helper present means future per-client expansions follow the
    same shape.
    """
    by_client = cache.get("by_client", {})
    orphans = [d for d in by_client.keys() if d not in known_domains]
    for d in orphans:
        del by_client[d]
    return cache


# Privacy filter helpers -------------------------------------------------------

def _is_internal(email: str, primary_email: str) -> bool:
    """D-D1 part 2: classify an attendee email as internal vs external.

    Internal = empty/malformed email (defensive default), or matches primary_email,
    or has an @host in GLEN_INTERNAL_DOMAINS. External otherwise.
    """
    if not email:
        return True  # defensive: missing email treated as internal
    email = email.lower()
    if email == primary_email.lower():
        return True
    if "@" not in email:
        return True  # defensive: malformed email treated as internal
    host = email.split("@", 1)[1]
    return host in GLEN_INTERNAL_DOMAINS


# Calendar adapter — applies D-D1 + D-D2 ---------------------------------------

def format_calendar_event_for_log(event: dict, primary_email: str) -> dict | None:
    """Apply D-D1 (visibility OR no-external-attendees) + D-D2 (>25 attendees).

    Returns: adapted dict on PASS, None on filter MATCH.

    The adapter shape feeds Wave 2's `_cal_meeting_event_tuple` (vault_writer.py
    extension). Pitfall 4 inheritance: `id` is the stable dedup key; tests
    enforce the field is preserved.
    """
    attendees = event.get("attendees") or []

    # D-D2: mass-attendee filter (cheapest check first)
    if len(attendees) > 25:
        return None

    # D-D1 part 1: explicit visibility=private
    if event.get("visibility") == "private":
        return None

    # D-D1 part 2: no external attendees → personal/internal-only event
    if not any(not _is_internal(a.get("email", ""), primary_email) for a in attendees):
        return None

    start = event.get("start") or {}
    return {
        "id": event["id"],
        "summary": event.get("summary") or "(no title)",
        "start_dt": start.get("dateTime") or start.get("date") or "",
        "attendees": attendees,
        "html_link": event.get("htmlLink", ""),
        "visibility": event.get("visibility", ""),
    }


# Drive adapter — applies D-D3 -------------------------------------------------

def format_drive_file_for_log(file: dict) -> dict | None:
    """Apply D-D3 (trashed OR .gdraft OR [DRAFT] token).

    Returns: adapted dict on PASS, None on filter MATCH.
    """
    if file.get("trashed") is True:
        return None
    name = file.get("name") or ""
    if name.endswith(".gdraft"):
        return None
    if "[DRAFT]" in name:  # case-sensitive per CONTEXT.md D-D3
        return None
    return {
        "id": file["id"],
        "name": name,
        "mime_type": file.get("mimeType", ""),
        "modified_time": file.get("modifiedTime", ""),
        "web_view_link": file.get("webViewLink", ""),
        "last_modifying_user": file.get("lastModifyingUser") or {},
        "parents": file.get("parents") or [],
    }


# OAuth token loader -----------------------------------------------------------

def _refresh_workspace_token(client_id: str, client_secret: str,
                              refresh_token: str) -> tuple[str, str]:
    """POST to oauth2.googleapis.com/token; return (new_access_token, new_expiry_iso_z).

    This is the ONE place workspace_client makes a non-GET request. The OAuth
    refresh endpoint is OUTSIDE googleapis.com/<api_path> namespace (it lives at
    oauth2.googleapis.com), so it's a deliberate carve-out from the
    WORKSPACE_ALLOWED_ENDPOINTS allowlist (see test_no_write_verb_method_calls_present).
    """
    body = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode("utf-8")
    req = urllib.request.Request(
        OAUTH_TOKEN_REFRESH_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",  # OAUTH-POST: workspace_client write-verb exception (token refresh only — D-X1 carve-out)
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise WorkspaceTransportError(f"credentials refresh failed: HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise WorkspaceTransportError(f"credentials refresh failed: network: {e.reason}") from e
    except (json.JSONDecodeError, OSError) as e:
        raise WorkspaceTransportError(f"credentials refresh failed: decode: {e}") from e

    access = payload.get("access_token")
    expires_in = int(payload.get("expires_in") or 0)
    if not access or expires_in <= 0:
        raise WorkspaceTransportError(
            "credentials refresh failed: missing access_token/expires_in in response"
        )
    new_expiry = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    return access, new_expiry


def _credentials_path(primary_email: str | None = None) -> Path:
    """Compute the OAuth credentials file path for `primary_email`.

    Honours GOOGLE_MCP_CREDENTIALS_DIR env var (introduced in Plan 12-01) over
    the default ~/.google_workspace_mcp/credentials/ location.
    """
    creds_dir = os.environ.get("GOOGLE_MCP_CREDENTIALS_DIR") or str(
        Path.home() / ".google_workspace_mcp" / "credentials"
    )
    email = primary_email or os.environ.get("GOOGLE_PRIMARY_EMAIL", "glen@iugo.com.au")
    return Path(creds_dir) / f"{email}.json"


def _load_workspace_credentials(primary_email: str | None = None) -> str:
    """Read the OAuth blob, refresh if expiring soon, return access token.

    Refresh threshold: OAUTH_REFRESH_LEEWAY_S (60s) before the stored expiry.
    On refresh, atomically rewrites the credentials file with new access_token
    AND new expiry so the next sync round inherits the fresh token.

    Raises:
        WorkspaceTransportError if credentials file missing OR refresh fails.
    """
    path = _credentials_path(primary_email)
    if not path.exists():
        raise WorkspaceTransportError(f"credentials missing at {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            blob = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise WorkspaceTransportError(f"credentials read failed: {e}") from e

    expiry_str = blob.get("expiry") or ""
    # Normalise expiry to a UTC datetime. Accept both "...Z" and "...+00:00" forms.
    try:
        if expiry_str.endswith("Z"):
            expiry_dt = datetime.fromisoformat(expiry_str[:-1] + "+00:00")
        else:
            expiry_dt = datetime.fromisoformat(expiry_str)
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
    except ValueError:
        # Malformed expiry → force a refresh
        expiry_dt = datetime.now(timezone.utc)

    now_utc = datetime.now(timezone.utc)
    refresh_at = now_utc + timedelta(seconds=OAUTH_REFRESH_LEEWAY_S)

    if expiry_dt > refresh_at:
        access = blob.get("token")
        if not access:
            raise WorkspaceTransportError("credentials missing 'token' field")
        return access

    # Refresh
    client_id = blob.get("client_id") or ""
    client_secret = blob.get("client_secret") or ""
    refresh_tok = blob.get("refresh_token") or ""
    if not (client_id and client_secret and refresh_tok):
        raise WorkspaceTransportError(
            "credentials missing client_id/client_secret/refresh_token; cannot refresh"
        )
    new_access, new_expiry = _refresh_workspace_token(client_id, client_secret, refresh_tok)
    blob["token"] = new_access
    blob["expiry"] = new_expiry
    # Atomically rewrite (best-effort; if write fails, the old token still works
    # for this sync but the next sync will re-refresh).
    try:
        _atomic_write(path, json.dumps(blob, indent=2) + "\n")
    except OSError:
        pass  # see comment above
    return new_access


# Drive walker -----------------------------------------------------------------

def _walk_drive_for_clients(access_token: str, max_depth: int = 3,
                             page_size: int = 100) -> dict:
    """List Drive files in My Drive (D-A3-REVISED scope) with D-D3 filtering applied.

    Single API call against drive/v3/files (the q-clause already excludes folders
    and trashed; per RESEARCH.md Anti-Patterns: do not hand-roll recursive walk).
    Returns {"files": [<adapted file dict>, ...]} where adapter = format_drive_file_for_log.

    Args:
        access_token: OAuth Bearer token (from _load_workspace_credentials)
        max_depth: forward-compat parameter; currently unused (Drive root is flat
            per CONTEXT.md D-A3-REVISED). A future phase 12.x can introduce
            recursive walking without breaking the call signature.
        page_size: Drive `pageSize` (max 1000; 100 keeps payload manageable).

    Note on D-A3-REVISED scope: Glen's Drive is flat at the root (~100 items;
    no /Clients/ folder hierarchy). Per RESEARCH.md Anti-Patterns, a single
    list call with `q="trashed=false and mimeType != folder"` plus
    `orderBy="modifiedTime desc"` covers the entire surface in one round-trip
    at Phase 12 ship time.
    """
    params = {
        "q": "trashed=false and mimeType != 'application/vnd.google-apps.folder'",
        "pageSize": page_size,
        "orderBy": "modifiedTime desc",
        # Explicit fields: lastModifyingUser is NOT in the default response (per
        # RESEARCH.md A5/Q5 — verified via hardened-workspace MCP source-read).
        "fields": (
            "files(id,name,mimeType,modifiedTime,webViewLink,"
            "lastModifyingUser,trashed,parents),nextPageToken"
        ),
        "supportsAllDrives": "false",
        "includeItemsFromAllDrives": "false",
    }
    raw = _workspace_get("drive/v3/files", params, access_token)
    out_files = []
    for f in (raw.get("files") or []):
        adapted = format_drive_file_for_log(f)
        if adapted is not None:
            out_files.append(adapted)
    return {"files": out_files}
