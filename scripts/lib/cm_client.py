"""Phase 11 — Contract Manager MCP JSON-RPC client.

Single-purpose: invoke CM tools at https://contracts.agend.info/api/mcp via
JSON-RPC 2.0 over HTTPS POST, with retry+cache-fallback per D-A3. The HTTP
layer is isolated here so vault_writer.py imports a clean Python interface.

Test seam: `_cm_post` is the only function that touches the network. Tests
patch `_cm_post`, NOT `urllib.request.urlopen`. See test_cm_client.py.

Cache shape: D-F1 — single JSON file at data/.cm-cache.json, fallback only.
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

# Reuse vault_writer's atomic-write helper (Don't Hand-Roll line 261-264).
# `now_iso_with_offset` is re-exported here for callers that want a single import.
from .vault_writer import _atomic_write, now_iso_with_offset  # noqa: F401


# Module constants -------------------------------------------------------------
CM_ENDPOINT = "https://contracts.agend.info/api/mcp"
RETRY_DELAYS = (1, 5, 30)  # D-A3
TIMEOUT_S = 15
CACHE_SCHEMA_VERSION = 1


# Errors -----------------------------------------------------------------------

class CmTransportError(Exception):
    """Network failure or non-2xx HTTP status (other than 429)."""


class CmRpcError(Exception):
    """JSON-RPC `error` envelope: {code: int, message: str}."""


class CmRateLimitError(CmTransportError):
    """429 response. Carries `retry_after_seconds` parsed from Retry-After header."""

    def __init__(self, retry_after_seconds: int):
        super().__init__(f"rate-limited; retry after {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds


# Single network seam ----------------------------------------------------------

def _cm_post(method: str, params: dict, api_key: str) -> dict:
    """Single JSON-RPC call. Returns `result["structuredContent"]` on success.

    Wraps the params per CM's `tools/call` convention unless `method == "tools/list"`.
    Raises:
        CmRateLimitError on 429 (caller may retry once after retry_after_seconds)
        CmTransportError on 4xx/5xx/network error
        CmRpcError on JSON-RPC `error` envelope
        CmRpcError on tools/call returning isError:true
    """
    if method == "tools/list":
        rpc_method = "tools/list"
        rpc_params = params or {}
    else:
        rpc_method = "tools/call"
        rpc_params = {"name": method, "arguments": params}

    body = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": rpc_method,
        "params": rpc_params,
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
    except (json.JSONDecodeError, OSError) as e:
        raise CmTransportError(f"decode: {e}") from e

    if "error" in payload:
        err = payload["error"]
        raise CmRpcError(f"{err.get('code')}: {err.get('message')}")

    result = payload.get("result", {})
    # tools/call wraps results; tools/list returns directly under "result"
    if rpc_method == "tools/call":
        if result.get("isError"):
            raise CmRpcError(f"tool error: {result.get('content', [{}])[0].get('text', '')}")
        # RESEARCH line 226-228: prefer structuredContent
        if "structuredContent" not in result:
            raise CmRpcError("missing structuredContent in tools/call result")
        return result["structuredContent"]
    return result


# Retry wrapper (D-A3: 1s/5s/30s; respect Retry-After once) --------------------

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


# Cache I/O --------------------------------------------------------------------

def _empty_cache() -> dict:
    return {"schema_version": CACHE_SCHEMA_VERSION, "global": {}, "by_client": {}}


def load_cache(cache_path: Path) -> dict:
    """Return cache dict or a fresh skeleton on missing/corrupt cache.

    Per RESEARCH lines 644-651: cache is fallback-only. Never raise; the next
    successful CM call will replace the corrupt cache via atomic write.
    """
    if not cache_path.exists():
        return _empty_cache()
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or data.get("schema_version") != CACHE_SCHEMA_VERSION:
            return _empty_cache()
        # Defensive: ensure required sub-keys exist
        data.setdefault("global", {})
        data.setdefault("by_client", {})
        return data
    except (OSError, json.JSONDecodeError):
        return _empty_cache()


def write_cache(cache_path: Path, cache: dict) -> None:
    """Atomic whole-file rewrite via vault_writer._atomic_write."""
    content = json.dumps(cache, indent=2, sort_keys=True) + "\n"
    _atomic_write(cache_path, content)


def gc_cache_orphans(cache: dict, known_domains: set) -> dict:
    """Drop `by_client` entries whose key is not in known_domains. Pitfall 3.

    Returns the same dict (mutated in place) for caller chaining.
    """
    by_client = cache.get("by_client", {})
    orphans = [d for d in by_client.keys() if d not in known_domains]
    for d in orphans:
        del by_client[d]
    return cache


# Adapters: CM response → vault_writer-friendly dicts --------------------------

def cm_summary_to_frontmatter_extra(summary: dict) -> dict:
    """Map `get_client_summary` structuredContent to Phase 11 frontmatter extras.

    D-B1: scalar empty → "". D-B2: array empty → []. D-B-MOD-REVISED: deployed_modules
    derived from activeContracts[].name (limited fidelity acknowledged inline). D-C2-REVISED:
    sites is always [] — Sites section is deferred until CM exposes a tool for it.
    """
    contracts = summary.get("activeContracts") or []
    contacts = summary.get("contacts") or []

    starts = [c["startDate"] for c in contracts if c.get("startDate")]
    ends = [c["endDate"] for c in contracts if c.get("endDate")]
    contract_start = min(starts) if starts else ""
    contract_end = max(ends) if ends else ""

    primary_contact = contacts[0]["name"] if contacts and contacts[0].get("name") else ""

    deployed_modules = sorted({c["name"] for c in contracts if c.get("name")}) if contracts else []

    return {
        "deployed_modules": deployed_modules,
        "contract_start": contract_start,
        "contract_end": contract_end,
        "primary_contact": primary_contact,
        "sites": [],  # D-C2-REVISED — never populated in Phase 11
    }


# Mapping helper ---------------------------------------------------------------

def search_clients_for_domain(domain: str, api_key: str):
    """Call CM `search_clients` and return the int id whose `website` matches `domain`.

    The query uses the second-level domain stem (e.g. "propertycouncil" for
    "propertycouncil.com.au") because CM stores websites with assorted prefixes
    (`https://`, `www.`, etc.) and a substring match on website is more reliable
    than a name-based query. Returns None if no candidate matches.
    """
    stem = domain.split(".")[0]
    result = call_with_retry("search_clients", {"query": stem, "limit": 10}, api_key)
    for client in result.get("clients", []):
        website = (client.get("website") or "").lower()
        if domain.lower() in website:
            return int(client["id"])
    # Fallback: first match if domain didn't substring-match any website
    candidates = result.get("clients", [])
    if candidates:
        return int(candidates[0]["id"])
    return None
