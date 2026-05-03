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
import time
import urllib.error
import urllib.parse
import urllib.request
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
