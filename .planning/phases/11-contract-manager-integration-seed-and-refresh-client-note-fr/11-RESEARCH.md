# Phase 11: Contract Manager Integration - Research

**Researched:** 2026-05-02
**Domain:** Outbound HTTP/JSON-RPC integration into Phase 10's vault-writer pipeline
**Confidence:** HIGH on transport, auth, tool shapes, integration mechanics; MEDIUM on Sites/Usage rendering (CM has the data but does NOT expose it via MCP — see Critical Findings)

## Summary

Phase 11 wires the Contract Manager MCP at `https://contracts.agend.info/api/mcp` into the existing `scripts/lib/vault_writer.py` Phase 10 engine. The transport is well-understood JSON-RPC 2.0 over HTTPS POST with `Authorization: Bearer cm_live_...` auth — the auth and dispatch code is fully readable in `~/work/contract-manager/src/app/api/mcp/route.ts`. The CM rate limit is **60 requests/minute per API key** (verified at `constants.ts:316-319`); Phase 11's ~30 requests per backfill is comfortably under the limit but still budget-aware. CM returns standard `Retry-After` headers on 429.

**Three findings reshape the planner's task list:**

1. **CM does NOT expose `sites[]` or `deployed_modules` via MCP.** Both the `Site` and `Product`/`ContractItem` tables exist in the Prisma schema (`prisma/schema.prisma:179, 408-426, 227-257`), but `get_client_summary` (the only client-detail tool) returns only profile + financial summary + `contacts` + `activeContracts` (with id/name/contractNumber/type/dates/totalValue/mrr) + `recentInvoices` + `openProposals`. There is **no array of sites and no array of deployed module names** in any of the 15 MCP tool responses. The planner must either: (a) treat `deployed_modules` as derivable from `activeContracts[].name` + the `contractItems` already needed for MRR (would require a CM tool extension), (b) source `deployed_modules` from `activeContracts[].type` (limited fidelity), or (c) **defer Sites and `deployed_modules` until a CM-side tool is added** and ship Phase 11 without them. This is a CONTEXT-vs-reality gap that needs Glen's call before planning proceeds. `[VERIFIED: source code at ~/work/contract-manager/src/lib/mcp/tools/lookups.ts and prisma/schema.prisma]`

2. **The feed-entry schema does NOT have a `warning` level** — only `["critical", "info", "debug"]` per `schemas/feed-entry.json:24-28`. CONTEXT.md D-A3 calls for a `system`/`warning` entry on CM staleness. The planner has two clean options: (a) extend the schema to add `"warning"` (small, additive, JSON Schema is enum-only here), or (b) use `system`/`info` with a marker in the summary like `"CM stale (fallback to cache)"` so dashboards can filter. I recommend (a) — it is one schema line and surfaces correctly in any future dashboard severity filter. `[VERIFIED: schemas/feed-entry.json:24]`

3. **`get_client_summary` requires a numeric `clientId`** (`z.number().int().positive()`), not a domain. The deferred idea in CONTEXT.md (one-time `search_clients` mapping pass that caches `cm_client_id` in `clients.jsonl`) is therefore not optional — it is the **only** way to call CM's frontmatter source tool. The mapping pass should be a Phase 11 Wave 0 task; it is small (~3 calls today) but mandatory. `[VERIFIED: ~/work/contract-manager/src/lib/mcp/tools/lookups.ts:79-80]`

**Primary recommendation:** Use **stdlib `urllib.request` with a small JSON-RPC wrapper** in a new `scripts/lib/cm_client.py` module. Reasons: (a) Phase 10 added only one Python dep (`ruamel.yaml`) — adding `requests` widens the deploy surface for both Coolify and Mac; (b) JSON-RPC 2.0 is a thin protocol, the wrapper is ~50 lines; (c) urllib gives explicit control over the retry+backoff sequence (1s/5s/30s per D-A3) without inheriting urllib3's `Retry` object semantics that would obscure CM's exact failure shapes; (d) urllib3 `Retry` does not idiomatically distinguish "retry on 5xx" from "respect Retry-After on 429" in the way D-A3 implies. Hand-roll the loop, keep it visible.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| MCP HTTP transport (POST + JSON-RPC) | scripts/lib/cm_client.py (new module) | — | Isolates the network IO from vault_writer; mockable in tests |
| Per-tool args/response shapes | scripts/lib/cm_client.py | — | Single place that knows CM's wire shapes; vault_writer imports typed helpers |
| Cache file (read fallback + atomic write) | scripts/lib/cm_client.py | data/.cm-cache.json | Cache is integration-domain state, not vault-domain; co-locate with HTTP code |
| Frontmatter extension (5 new keys) | scripts/lib/vault_writer.py:render_frontmatter | scripts/lib/cm_client.py | render_frontmatter stays in vault_writer (Phase 10 owns frontmatter shape); receives a CM data dict from the client module |
| Sites + Usage section rendering | scripts/lib/vault_writer.py (new render_sites, render_usage) | — | Sections are vault-domain output; mirror the existing render_open_items / render_activity_log pattern |
| CM-TODOS section (managed) | scripts/lib/vault_writer.py (new render_cm_todos) | — | Same pattern as Sites/Usage |
| Contract event Activity Log entries | scripts/lib/vault_writer.py:_gather_events | scripts/lib/cm_client.py | Mirrors how triage/task/invoice events are gathered today; CM contracts are a fourth event source |
| CM-tracked invoice merge | scripts/lib/vault_writer.py:_gather_events | scripts/lib/cm_client.py | Same as contract events; dedup against local active.jsonl by invoice_number |
| Cache concurrency (flock) | scripts/lib/cm_client.py | scripts/sync-obsidian.sh (already holds flock for the whole sync run) | Cache writes happen inside the existing flock window — no second lock needed |
| API key env var injection | scripts/sync-obsidian.sh | Coolify env config | Wrapper sets `CONTRACT_MANAGER_API_KEY` from env before exec'ing python |
| Mac-side projection | scripts/lib/vault_writer.py:run_projection (UNCHANGED) | — | Mac daemon does NOT call CM; only projects vault-build/ to iCloud |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `urllib.request` | 3.11+ (Coolify Python; verified by `.venv` reference in mac/install-daemon.sh) | HTTPS POST for JSON-RPC | Zero new deps. Phase 10 set the precedent: `ruamel.yaml` was added; nothing else. SSL via `ssl.create_default_context()` is sufficient for HTTPS to a public-cert CM endpoint. `[VERIFIED: scripts/requirements.txt only contains ruamel.yaml]` |
| Python stdlib `json` | 3.11+ | JSON-RPC envelope serialization | Already used throughout vault_writer for NDJSON. |
| Python stdlib `time` | 3.11+ | sleep() between retries | D-A3 timing: 1s / 5s / 30s. |
| ruamel.yaml | >=0.18,<0.19 (already pinned) | Frontmatter round-trip | Phase 10 dep; new CM keys ride the same render_frontmatter path. |

### Supporting (existing, no new install)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `unittest` | 3.11+ | Test framework | All Phase 11 test classes extend this. |
| Python stdlib `unittest.mock` | 3.11+ | Mock the HTTP call | Patch `cm_client._cm_post` (single seam, see test strategy). |
| Python stdlib `tempfile` + `os.replace` | 3.11+ | Atomic cache write | Mirror Phase 10's `_atomic_write` pattern; `data/.cm-cache.json` is small enough to rewrite whole-file every time. |
| Python stdlib `fcntl` | 3.11+ | Cache lock (if needed) | Already imported in vault_writer.py:29. Sync runs are already serialized by `scripts/.vault-sync.lock` (flock in `sync-obsidian.sh`), so a second lock is redundant on Coolify. Mac daemon does not call CM. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib urllib | `requests` (with `urllib3.util.Retry`) | Cleaner API, but adds a dep + transitive deps (urllib3, charset-normalizer, idna, certifi). For ~50 lines of code that runs once per sync, the dep cost is not justified. `[CITED: https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/]` |
| stdlib urllib | `httpx` | Modern async support, but Phase 11 is sync-only (one sync run per `/sync-obsidian` invocation, called from a bash script). Async is overkill. `[CITED: https://scrapeops.io/python-web-scraping-playbook/python-httpx-retry-failed-requests/]` |
| Hand-rolled retry loop | `tenacity` or `backoff` libs | These libs offer decorators with rich retry semantics, but D-A3 specifies exact timing (1s/5s/30s) with custom 429-vs-5xx-vs-network branching. Hand-rolling is shorter and clearer than configuring tenacity. `[CITED: https://pypi.org/project/backoff/]` |
| Single JSON file at `data/.cm-cache.json` | SQLite cache | JSON is git-diffable (even though gitignored, dev debug is easier) and the data volume (~3 clients × small response) is trivial. SQLite would be overkill. |

**Installation:** No new dependencies. `scripts/requirements.txt` unchanged.

**Version verification:** Python stdlib `urllib.request` ships with Python 3.x; `.venv` already in use on Mac per `mac/install-daemon.sh`. No registry check required.

## Architecture Patterns

### System Architecture Diagram

```
                      ┌─────────────────────────────────────────────┐
                      │  /sync-obsidian (bash wrapper)              │
                      │  - flock advisory lock                      │
                      │  - exports CONTRACT_MANAGER_API_KEY         │
                      │  - exec python -m scripts.lib.vault_writer  │
                      └────────────────┬────────────────────────────┘
                                       │
                                       ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │  scripts/lib/vault_writer.py (Phase 10 engine, EXTENDED)        │
   │                                                                  │
   │   1. load_clients(data_root)         ◄─── data/config/clients.jsonl
   │                                            (extended: cm_client_id)
   │                                                                  │
   │   2. cm = CmClient(api_key, cache_path)                          │
   │      - per-client: get_client_summary(cm_client_id)              │
   │      - global:    list_contracts_expiring(days)                  │
   │      - global:    list_overdue_invoices()                        │
   │      - per-client: get_utilization_summary, get_capacity_summary │
   │                                                                  │
   │           cm_client.py ─── HTTPS POST ───► contracts.agend.info  │
   │           ▲                                                       │
   │           └──── on retry exhaustion: read data/.cm-cache.json    │
   │                                                                  │
   │   3. _gather_events()                                            │
   │      • triage/task/invoice (Phase 10, unchanged)                 │
   │      • + contract events from cm.contracts_expiring             │
   │      • + cm-tracked invoices, deduped by invoice_number          │
   │                                                                  │
   │   4. render_frontmatter()    ── Phase 10's 4 keys                │
   │                              + CM 5: deployed_modules,           │
   │                                contract_start, contract_end,     │
   │                                primary_contact, sites[]          │
   │                              + cm_data_stale_since (cache mode)  │
   │                                                                  │
   │   5. render_cm_todos() ──► CM-TODOS managed section              │
   │   6. render_sites()    ──► Sites managed section                 │
   │   7. render_usage()    ──► Usage managed section                 │
   │   8. render_activity_log() ── Phase 10 + 📄 contract events      │
   │                                                                  │
   │   9. _atomic_write() per client → vault-build/Clients/<slug>.md  │
   └─────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                           git commit + push-and-sync.sh
                                       │
                                       ▼
                          Mac Studio LaunchAgent (UNCHANGED)
                          fswatch → run_projection() → iCloud vault
```

### Recommended Project Structure
```
scripts/
├── lib/
│   ├── vault_writer.py        # Phase 10; extended with CM-aware renders
│   ├── cm_client.py           # NEW — JSON-RPC client + cache
│   └── __init__.py
└── tests/
    ├── test_vault_writer.py   # Phase 10; new test classes added
    └── test_cm_client.py      # NEW — unit tests for the JSON-RPC client
data/
├── config/clients.jsonl       # Phase 10; extended with optional cm_client_id field
├── .cm-cache.json             # NEW (gitignored)
└── feed.jsonl                 # Phase 10; CM warnings join the existing entries
```

### Pattern 1: JSON-RPC Wrapper (stdlib urllib)
**What:** Single function that takes (method, params) and returns either result dict or raises a typed exception.
**When to use:** Every CM tool call.
**Example:**
```python
# scripts/lib/cm_client.py
import json
import time
import urllib.request
import urllib.error

class CmTransportError(Exception):
    """Network failure or non-2xx HTTP status."""
class CmRpcError(Exception):
    """JSON-RPC error envelope: {code: int, message: str}"""
class CmRateLimitError(CmTransportError):
    """429 response; carries retry_after_seconds."""

CM_ENDPOINT = "https://contracts.agend.info/api/mcp"
RETRY_DELAYS = (1, 5, 30)  # D-A3
TIMEOUT_S = 15

def _cm_post(method: str, params: dict, api_key: str) -> dict:
    """Single JSON-RPC call. Raises on transport or RPC error.
    Caller is responsible for retry — keep retry policy out of this seam
    so tests can mock _cm_post once and exercise the retry loop separately.
    """
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
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
            retry_after = int(e.headers.get("Retry-After", "30"))
            raise CmRateLimitError(retry_after) from e
        raise CmTransportError(f"HTTP {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise CmTransportError(f"network: {e.reason}") from e

    if "error" in payload:
        raise CmRpcError(f"{payload['error']['code']}: {payload['error']['message']}")
    return payload["result"]

def call_with_retry(method: str, params: dict, api_key: str, *, on_warn=None) -> dict:
    """D-A3: 3 retries with 1/5/30s backoff. Respect Retry-After on 429."""
    last_err = None
    for delay in (0,) + RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            return _cm_post(method, params, api_key)
        except CmRateLimitError as e:
            time.sleep(int(str(e)) or delay)
            last_err = e
        except (CmTransportError, CmRpcError) as e:
            last_err = e
    raise last_err  # caller falls back to cache
```

### Pattern 2: tools/call wire format
**What:** CM tools are invoked via JSON-RPC method `tools/call` with `{name, arguments}` params. The result is wrapped in `{content: [{type:"text", text:"..."}], structuredContent: {...}, isError: false}`.
**When to use:** Every Phase 11 CM read.
**Example:**
```python
# Wire body for get_client_summary(clientId=42):
{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
 "params": {"name": "get_client_summary", "arguments": {"clientId": 42}}}

# Response shape (always):
{"jsonrpc": "2.0", "id": 1, "result": {
    "content": [{"type": "text", "text": "<json-stringified result>"}],
    "structuredContent": {...the actual typed result, prefer this...},
    "isError": false
}}
```
Reach for `result["structuredContent"]` — it is the parsed, decimal-safe version (`server.ts:217-222`). `result["content"][0].text` is a duplicate JSON string; ignore unless `structuredContent` is missing. `[VERIFIED: ~/work/contract-manager/src/lib/mcp/server.ts:186-222]`

### Pattern 3: Atomic cache write (mirror Phase 10's `_atomic_write`)
```python
def _write_cache(cache_path: Path, cache: dict) -> None:
    """Whole-file rewrite via tempfile + os.replace + fsync."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=cache_path.parent,
                                prefix=f".{cache_path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, cache_path)
    except Exception:
        if os.path.exists(tmp): os.unlink(tmp)
        raise
```

### Anti-Patterns to Avoid
- **Calling `tools/list` on every sync run.** Tool definitions are static — call it once during the one-time mapping pass for sanity, then never again. Each call burns a rate-limit slot.
- **Treating `structuredContent` as optional.** It is always present on success per `server.ts:191-195`. If absent, that's a CM bug — surface it as a critical, not a fallback to text parsing.
- **Mutating `.cm-cache.json` in place.** A partial write during a CM-down + power-outage sequence yields corrupt JSON, which then fails to load on the next run *with* CM still down — double-fault. Atomic temp+rename is mandatory.
- **Adding `requests` "to be safe."** The dep widens the Mac Studio install (already on Glen's nerves per `mac/README.md` polish history) and is unnecessary for this volume.
- **Storing the API key in `data/`.** `data/` is git-tracked; the key must come from the environment only. `scripts/sync-obsidian.sh` should validate `${CONTRACT_MANAGER_API_KEY:?missing}` before exec'ing python.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TLS / cert validation | A custom SSL context | Python stdlib `ssl.create_default_context()` (used by urllib by default) | Cert chains, OCSP, hostname verification — solved problem. |
| JSON-RPC 2.0 envelope | Bespoke serializer | `json.dumps({"jsonrpc": "2.0", "id": 1, "method": ..., "params": ...})` | The protocol is 4 keys; the value is in not over-engineering. CM does not expose batch-id semantics that need anything more. |
| Atomic file write | Best-effort `os.rename` | Phase 10's `_atomic_write` (already in vault_writer.py:296) | Already includes fsync(file) + fsync(dir) for iCloud-safety. Reuse via direct call or copy-paste; do NOT rewrite a worse version. |
| ISO-8601 timestamp w/ offset | f-string formatting | `now_iso_with_offset()` (vault_writer.py:154) | Already used for `last_synced` and feed entries. `cm_data_stale_since` should reuse it. |
| Frontmatter extension | A new YAML library | Pass an extended dict into existing `render_frontmatter` (vault_writer.py:553) | One source of truth for frontmatter shape. Phase 10's render uses ruamel.yaml dump on a dict — extending is purely additive. |

## Runtime State Inventory

> Phase 11 is mostly an *additive* phase, not a rename/refactor. But it does introduce one piece of runtime state and one schema extension. Recording explicitly to avoid leaking surprises into execution.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | (1) `data/.cm-cache.json` — NEW per-host runtime cache, gitignored. (2) `data/config/clients.jsonl` — extended schema (optional `cm_client_id` field). | (1) None — file is created on first cache-write. (2) Code edit: `load_clients` tolerates missing key (already does — `rec.get(...)`). One-time data migration: run mapping pass to populate `cm_client_id` for the 3 known domains. |
| Live service config | (1) Coolify env var `CONTRACT_MANAGER_API_KEY` — set via Coolify UI, NOT in git. (2) CM-side API key entry in `app/settings/mcp` UI — Glen mints + revokes. | (1) Manual config step (documented in plan). (2) Manual key mint by Glen before first sync run. |
| OS-registered state | None — no Windows scheduler, no launchd registration, no pm2. The Mac LaunchAgent (Phase 10 `com.agend.vault-sync.plist`) does NOT call CM and is unchanged. | None — verified by `mac/com.agend.vault-sync.plist` ProgramArguments pointing only to vault-sync-watcher.sh which calls vault_writer with `--mode project-to-icloud` (no CM dep). |
| Secrets/env vars | `CONTRACT_MANAGER_API_KEY` — new env var. Set on Coolify only. Mac Studio does NOT need it (Mac runs project-to-icloud mode which does not call CM). | (1) Add validation in `scripts/sync-obsidian.sh` (`${CONTRACT_MANAGER_API_KEY:?missing}`). (2) Document on Coolify. (3) Document NON-requirement on Mac. |
| Build artifacts | None — no compiled binary, no egg-info, no Docker image carrying this string. | None. |

**Nothing in OS-registered state or build artifacts.** The integration is purely additive Python code + one env var + one cache file + one schema extension. `[VERIFIED: grep across mac/ and scripts/ for any old CM-related state]`

## Common Pitfalls

### Pitfall 1: Mac daemon accidentally invokes CM
**What goes wrong:** A future contributor adds a CM call to `run_projection()` thinking "all sync paths should refresh frontmatter."
**Why it happens:** The `_update_frontmatter_last_synced` step at vault_writer.py:1078 looks like a natural place to also refresh `cm_data_stale_since` — it's not.
**How to avoid:** Phase 11 must keep CM access **strictly inside `run_backfill` / `run_incremental`**. Add a docstring to `run_projection` that says "MUST NOT call CM — Mac daemon has no API key by design."
**Warning signs:** Mac Studio sync logs show `urllib.error.URLError`. Mac never had `CONTRACT_MANAGER_API_KEY` set, and that's the design.

### Pitfall 2: Partial CM data corrupting frontmatter on parse
**What goes wrong:** CM returns `get_client_summary` with `endDate: null` — Python parses it as `None`, ruamel.yaml dumps it as `~` or `null`, DataView fails the date filter.
**Why it happens:** Phase 10 frontmatter is hand-typed strings; Phase 11 ingests typed JSON.
**How to avoid:** Coerce CM responses through a small adapter before passing to `render_frontmatter`. Per D-B1 (empty scalar → `""`) and D-B2 (empty array → `[]`), the adapter does the empty-handling explicitly. Never hand the raw CM dict to YAML dump.
**Warning signs:** Test failure on `test_yaml_round_trip_with_null_contract_end`.

### Pitfall 3: Cache file silently grows unbounded
**What goes wrong:** Each sync stamps a new entry under `cm-cache.json` keyed by domain. If a client is removed from `clients.jsonl`, its cache entry persists forever.
**Why it happens:** No GC pass over the cache.
**How to avoid:** On every cache write, intersect the cache key set with `clients.keys()` from the current load and drop orphans. Cheap, idempotent, prevents cache rot.
**Warning signs:** Cache file size grows every month even though client count is stable.

### Pitfall 4: Invoice dedup case-fold defeats real differences
**What goes wrong:** Two distinct invoices `INV-0042` (local) and `inv-0042` (CM) are NOT the same — but case-fold dedup merges them.
**Why it happens:** D-D2 specifies case-fold default, but CM's invoice_number comes from Xero where casing is preserved.
**How to avoid:** Case-fold + trim only — do NOT strip prefixes or normalize separators. If casing matters in production, the bug surfaces as "I see two of the same invoice" — visible, fixable. If two genuinely different invoices were merged, the bug is invisible — much worse. Choose visible failure mode.
**Warning signs:** `_Unknown.md` shows duplicate invoice entries that differ only in casing. Then we know the dedup needs tightening, not loosening.

### Pitfall 5: Rate limit triggers on `tools/list` poll
**What goes wrong:** Plan author adds a "verify CM tools haven't changed" step that calls `tools/list` per sync. Combined with 6+ tool calls per sync per client, hits rate limit by client #4.
**Why it happens:** `tools/list` looks free. It's not.
**How to avoid:** `tools/list` is for the one-time mapping pass only. Do NOT poll it per sync.
**Warning signs:** Sync logs show 429s with `Retry-After: 60`.

### Pitfall 6: ISO-8601 dates from CM are date-only, frontmatter expects datetime-with-offset
**What goes wrong:** `get_client_summary` returns `startDate: "2026-03-15"` (date.format `'yyyy-MM-dd'` per `lookups.ts:135`). `last_synced` in Phase 10 frontmatter is `"2026-05-02T10:30:00+10:30"` (datetime-with-offset).
**Why it happens:** They're different temporal types. CM contract dates are calendar dates; `last_synced` is an instant.
**How to avoid:** Document this explicitly: `contract_start` and `contract_end` are date-only YYYY-MM-DD strings — DataView treats them correctly. `cm_data_stale_since` is datetime-with-offset (mirrors `last_synced` shape via `now_iso_with_offset()`).
**Warning signs:** YAML round-trip emits `2026-03-15 00:00:00` instead of the expected `'2026-03-15'`.

## Code Examples

Verified patterns from official sources:

### CM tools/call request (verified shape)
```python
# Source: ~/work/contract-manager/src/app/api/mcp/route.ts (POST handler)
# and ~/work/contract-manager/src/lib/mcp/server.ts (tools/call dispatch).
import json, urllib.request

def call_tool(name: str, args: dict, api_key: str) -> dict:
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": args},
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://contracts.agend.info/api/mcp",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",  # OR "X-API-Key": api_key
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["result"]["structuredContent"]
```

### Adapter: CM `get_client_summary` → frontmatter dict
```python
# Source: response shape from ~/work/contract-manager/src/lib/mcp/tools/lookups.ts:180-218
def cm_summary_to_frontmatter_extra(summary: dict) -> dict:
    """Map CM get_client_summary structuredContent to Phase 11 frontmatter extras.

    D-B1: scalar empty → ""; D-B2: array empty → [].
    """
    contracts = summary.get("activeContracts") or []
    contacts = summary.get("contacts") or []

    # contract_start: earliest start across active contracts; contract_end: latest end
    starts = [c["startDate"] for c in contracts if c.get("startDate")]
    ends   = [c["endDate"]   for c in contracts if c.get("endDate")]
    contract_start = min(starts) if starts else ""
    contract_end   = max(ends)   if ends   else ""

    # primary_contact: first contact (CM returns top-5 ordered by id ASC)
    primary_contact = contacts[0]["name"] if contacts else ""

    # deployed_modules: contract names; FIDELITY GAP — see Critical Findings
    deployed_modules = sorted({c["name"] for c in contracts}) if contracts else []

    return {
        "deployed_modules": deployed_modules,
        "contract_start": contract_start,
        "contract_end": contract_end,
        "primary_contact": primary_contact,
        "sites": [],  # NOT EXPOSED VIA MCP — see Critical Findings
    }
```

### Render order for extended frontmatter (D-09 + 5 new keys)
```python
# Update render_frontmatter at vault_writer.py:553 — keep Phase 10 keys first, append CM
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
        fm["sites"]            = cm_extra.get("sites", [])
    if cm_stale_since:
        fm["cm_data_stale_since"] = cm_stale_since  # only present in cache-fallback mode
    buf = StringIO()
    _yaml_instance().dump(fm, buf)
    return f"---\n{buf.getvalue()}---\n"
```

### Marker pairs for new managed sections (D-08/D-08a inheritance)
```
<!-- DO NOT EDIT BETWEEN MARKERS — managed by /sync-obsidian -->
<!-- CM-TODOS-START -->
## TODO: Missing CM Data
- `contract_start` — set in [Contract Manager](https://contracts.agend.info/clients/<id>)
- `primary_contact` — set in Contract Manager
<!-- CM-TODOS-END -->

<!-- DO NOT EDIT BETWEEN MARKERS — managed by /sync-obsidian -->
<!-- SITES-START -->
## Sites
- **prod.example.com** (Live) — modules: AMS Core, Events
- **staging.example.com** (Staging) — modules: AMS Core
<!-- SITES-END -->

<!-- DO NOT EDIT BETWEEN MARKERS — managed by /sync-obsidian -->
<!-- USAGE-START -->
## Usage
- **This month:** 12.5 hrs billed of 20.0 contracted (62%)
- **YTD:** 87.0 hrs billed
- **Upcoming committed:** 8.0 hrs (next 4 weeks)
<!-- USAGE-END -->
```
Add to `MANAGED_SECTIONS` at vault_writer.py:52: `("OPEN-ITEMS", "ACTIVITY-LOG", "CM-TODOS", "SITES", "USAGE")`. The marker discipline (D-08/D-08a) carries forward by construction — `replace_managed_section` is section-name-agnostic.

### CM-tracked invoice → activity log entry
```python
# Source: ~/work/contract-manager/src/lib/mcp/tools/financial.ts:195-213 (list_overdue_invoices result)
def cm_invoice_to_event_tuple(inv: dict, client_domain: str) -> tuple:
    """Build the (ts, kind, summary, detail, gmail_thread_id) tuple for D-12 line shape.

    Detail block prefixes 'source: contract-manager' per D-D2.
    """
    # Use issueDate as the event ts; YYYY-MM-DD → assume midnight in local-ish offset
    ts = f"{inv['issueDate']}T00:00:00+10:30"  # adjust to local TZ utility
    summary = f"{inv['invoiceNumber']} overdue ({inv['daysPastDue']}d) — ${inv['amount']}"
    detail = f"source: contract-manager · severity: {inv['severity']}"
    return (ts, "invoice", summary, detail, None)  # 💰 emoji unchanged
```

### Contract event → activity log entry (NEW emoji 📄)
```python
# Add to EMOJI_BY_KIND at vault_writer.py:49
EMOJI_BY_KIND = {"triage": "📧", "task": "✅", "invoice": "💰", "contract": "📄"}

# Source: ~/work/contract-manager/src/lib/mcp/tools/operations.ts:50-62 (list_contracts_expiring result)
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

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@modelcontextprotocol/server-github` npm | github/github-mcp-server remote HTTP | 2025-04 (per CLAUDE.md) | Sets ecosystem precedent that "remote HTTP MCP endpoints" are the canonical integration shape — Phase 11 follows this with CM. |
| `requests` for short-lived HTTP scripts | stdlib urllib for low-volume integrations | Stable for years | No version churn; reasonable Python 3.10+ choice. |
| Polling cron for inbound updates | CM webhook (deferred) | Future | Phase 11 is pull-on-sync. CM webhook → real-time push is a future enhancement once webhook infra exists in CM. |

**Deprecated/outdated (none for this phase):** No deprecation traps — all chosen primitives (urllib, json, ruamel.yaml) are current and stable.

## CM Tool Contract Reference (the planner needs this exactly)

All five tools we depend on, with exact arg + structuredContent shapes copied from the source. `[VERIFIED: ~/work/contract-manager/src/lib/mcp/tools/]`

### `search_clients` (one-time mapping pass only)
**File:** `src/lib/mcp/tools/lookups.ts:17-74`
**Args:** `{query: string (min 1), limit?: int (1..50, default 20)}`
**Returns (`structuredContent`):**
```jsonc
{
  "total": int,
  "clients": [
    {"id": int, "name": string, "email": string|null, "phone": string|null,
     "website": string|null, "activeContracts": int, "contactCount": int}
  ]
}
```
**Phase 11 use:** Per-domain query (e.g., `"propertycouncil"`), pick first match where `website` matches the domain in `clients.jsonl`. Cache the resolved `id` as `cm_client_id`. Run **once** during mapping pass.

### `get_client_summary` (per sync run, per client)
**File:** `src/lib/mcp/tools/lookups.ts:82-219`
**Args:** `{clientId: int (positive)}`
**Returns (`structuredContent`):**
```jsonc
{
  "client": {"id": int, "name": string, "email": string|null,
             "phone": string|null, "website": string|null},
  "financial": {"totalMRR": int, "totalARR": int,
                "activeContracts": int, "currency": "AUD"},
  "contacts": [{"id": int, "name": string, "email": string|null,
                "phone": string|null, "role": string|null}],   // ≤5
  "activeContracts": [{
    "id": int, "name": string, "contractNumber": string|null,
    "type": string,                      // ContractType enum
    "startDate": "YYYY-MM-DD",           // ALWAYS present (contract requires startDate)
    "endDate": "YYYY-MM-DD" | null,
    "totalValue": number|null,
    "mrr": int                           // computed sum of contractItems
  }],
  "recentInvoices": [...],               // ≤10, NOT what we use for invoice merge — see list_overdue_invoices
  "openProposals": [...]                 // ≤10
}
```
**Phase 11 use:** Source for `contract_start`, `contract_end`, `primary_contact`. **Source for `deployed_modules`** if we accept "contract name as module name" (FIDELITY GAP — see Critical Findings). **Cannot source `sites[]`** — not present.
**Errors:** Throws `"Client not found: <id>"` when clientId is invalid. Per `server.ts:158-162`, this becomes a `tools/call` result with `isError: true` (not a JSON-RPC error). Treat as cache fallback trigger.

### `list_contracts_expiring` (per sync run, global)
**File:** `src/lib/mcp/tools/operations.ts:21-72`
**Args:** `{days?: int (1..365, default 30)}`
**Returns (`structuredContent`):**
```jsonc
{
  "lookaheadDays": int,
  "total": int,
  "contracts": [{
    "id": int, "name": string, "contractNumber": string|null,
    "client": string,        // client name
    "clientId": int,         // ◄── join key for routing to slug
    "endDate": "YYYY-MM-DD",
    "daysUntilExpiry": int,
    "totalValue": number|null,
    "renewalType": string|null,
    "renewalScore": number|null,
    "renewalRisk": string|null,
    "recommendations": string[]
  }]
}
```
**Phase 11 use:** Per-event Activity Log entry (📄 emoji, D-E1). Route by `clientId` → mapped back to `client_domain` → slug. Recommend running with `days: 90` for a useful glance horizon.

### `get_capacity_summary` (per sync run, GLOBAL — not per-client)
**File:** `src/lib/mcp/tools/operations.ts:161-198`
**Args:** `{weeks?: int (1..12, default 8)}`
**Returns:** Team-wide capacity forecast. **No client filter exists.** Phase 11's "Usage section per client" needs to slice this somehow — but the data is per-person, not per-client. **This tool is the wrong fit for D-C3.** See Open Questions.

### `get_utilization_summary` (per sync run, GLOBAL — not per-client)
**File:** `src/lib/mcp/tools/operations.ts:207-256`
**Args:** `{year?: int, month?: int}`
**Returns:** Per-person billable hours for a month. **No client filter.** Same fit issue as `get_capacity_summary`.

### `list_overdue_invoices` (per sync run, global)
**File:** `src/lib/mcp/tools/financial.ts:167-248`
**Args:** `{}` (none)
**Returns (`structuredContent`):**
```jsonc
{
  "summary": {"total": int, "totalAmount": int, "currency": "AUD",
              "criticalCount": int, "warningCount": int,
              "aging": {"0-30": int, "31-60": int, "61-90": int, "90+": int}},
  "invoices": [{
    "id": int,
    "invoiceNumber": string,         // ◄── dedup key vs local active.jsonl `invoice_number`
    "amount": number,
    "issueDate": "YYYY-MM-DD",
    "dueDate": "YYYY-MM-DD",
    "daysPastDue": int,
    "severity": "info" | "warning" | "critical",
    "client": string,
    "clientId": int,                 // ◄── join key for routing
    "contract": string,
    "contractId": int
  }]
}
```
**Phase 11 use:** Activity Log per-invoice entries. Dedup vs local `data/invoices/active.jsonl`'s `invoice_number` field (case-fold + trim, per D-D2 + Pitfall 4 above).

## Auth + Key Lifecycle

`[VERIFIED: ~/work/contract-manager/src/app/api/mcp/route.ts:42-83 + src/lib/api-key-auth.ts:20-58]`

| Property | Value |
|----------|-------|
| Format | `cm_live_<48 hex chars>` |
| Generation | Glen mints in CM dashboard at `/settings/mcp`. Backend: `generateApiKey(userId, name, expiresInDays?, service='mcp')`. |
| Scope | Must be minted with `service: 'mcp'`. The auth check is `verifyApiKeyFull(apiKey, 'mcp')` — a `'external'`-scoped key is rejected. |
| Header support | Both `Authorization: Bearer cm_live_...` AND `X-API-Key: cm_live_...`. Phase 11 uses `Authorization: Bearer ...` for HTTP convention. |
| Hashing | bcrypt(10) on the server side. Plain key is shown to Glen exactly once at mint. |
| Expiry | Optional. If no `expiresInDays` was set at mint → never expires. |
| Rate limit | 60 req/min per `apiKeyId` (`mcp:apikey:${apiKeyId}` rate-limit identifier). Phase 11 budget: 5 tools × 3 clients = 15 calls per backfill. Comfortable. |
| 429 response | HTTP 429, body is JSON-RPC error envelope, headers include `Retry-After: <seconds>` and `X-RateLimit-Reset: <epoch>`. |
| Audit | Every call generates an `AuditLog` entry on CM side with method names. |

**Failure response shapes (the planner must distinguish):**
- **401, no body header:** Missing key entirely. RPC code -32600 (INVALID_REQUEST). Treat as fatal misconfiguration; do NOT retry.
- **401, "Invalid, expired, or wrong-scope":** Key was revoked, expired, or wrong scope. RPC code -32600. Treat as fatal; do NOT retry; log critical (the cache fallback won't help — Glen needs to mint a new key).
- **429, JSON-RPC error envelope, code -32603 INTERNAL_ERROR, message "Rate limit exceeded":** Headers carry `Retry-After`. Sleep that long, retry once. After single retry, fall back to cache.
- **400 PARSE_ERROR:** Body wasn't JSON. Phase 11 always sends JSON; if this happens it's our bug, log critical.
- **5xx or network error:** Retry per D-A3 (1s/5s/30s), then fall back to cache.
- **200 with `error` envelope (per-tool failure inside `tools/call`):** e.g., `"Client not found"`. Treat as data error for the affected entity only — NOT a transport failure. Stamp `cm_data_stale_since` on that one note's frontmatter, don't retry.

`[VERIFIED: route.ts:60-101, api-utils.ts:454-468]`

## Cache File Shape + Concurrency

### Schema (D-F1)
```jsonc
// data/.cm-cache.json
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
      "utilization_summary": {"fetched_at": "...", "result": {...}}
    }
  }
}
```
**Why this shape:** Global tools (expiring contracts, overdue invoices) are queried once per sync — keep them in `global`. Per-client tools live under `by_client[domain]`. Domain (not slug, not cm_client_id) is the dictionary key because the rest of vault_writer's data flow is keyed by domain via `clients.jsonl`.

### Concurrency
**Recommendation: NO second lock.** The wrapper already holds `scripts/.vault-sync.lock` (flock with 30s timeout, see `sync-obsidian.sh:111-115`) for the duration of the python invocation. CM reads + cache writes happen entirely inside that window. A second lock would be redundant and risk lock-order deadlocks if Phase 12 ever wants to share state.

**One subtle case:** the Mac Studio runs `vault_writer --mode project-to-icloud` *without* the bash wrapper's flock (Mac uses its own `_acquire_projection_lock` at vault_writer.py:777). Mac never calls CM (by design — see Pitfall 1), so no cache contention. **Verify this with a unit test:** `test_run_projection_does_not_open_cache_file`.

### Corruption tolerance
The cache is fallback-only (D-A1: cache is never the read path on success). If `data/.cm-cache.json` is corrupt or missing:
1. Live CM call attempt (always first).
2. On retry exhaustion, attempt cache load.
3. If cache load fails (FileNotFoundError, JSONDecodeError), DO NOT crash. Log a `system`/`info` entry: `"CM unreachable AND cache unreadable — using last-frozen note state"`, continue with no-CM-data fields blanked.
4. The next successful CM call replaces the corrupt cache via atomic write.

This double-fault tolerance is essential because the alternative is "CM down + cache corrupted = entire sync aborts = all unrelated triage/task/invoice events lost." That violates D-A3's "never block the entire vault on CM downtime."

## Test Scaffolding

### Mock seam: `_cm_post`
The single network function in `cm_client.py` is `_cm_post(method, params, api_key)`. Patch THAT in tests, not `urllib.request.urlopen`. Reasons:
- Single test seam, well-defined input/output.
- Tests don't have to construct `http.client.HTTPResponse` mocks (annoying).
- Lets us exercise the retry + cache fallback logic above the seam without faking network primitives.

```python
# scripts/tests/test_cm_client.py
from unittest.mock import patch
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

### New test classes (Phase 11 adds 6+; orchestrator targets ≥6 per CONTEXT)

| Class | Purpose | Mocks |
|-------|---------|-------|
| `TestCmClient` | JSON-RPC envelope shape, header injection, error parsing | `urllib.request.urlopen` |
| `TestCallWithRetry` | D-A3 retry timing, 429 Retry-After honoring | `_cm_post`, `time.sleep` |
| `TestCmCacheFallback` | Atomic write, corruption tolerance, GC of orphan keys | filesystem only (real tempdir) |
| `TestContractMerge` | get_client_summary → frontmatter dict, render_frontmatter extension | `_cm_post` |
| `TestCmTodosSection` | Missing-fields detection, marker discipline (inherits D-08a) | `_cm_post` |
| `TestSitesSection` | Empty CM → `_(no sites recorded in CM)_` placeholder; D-08a marker discipline | `_cm_post` |
| `TestUsageSection` | Aggregation logic, formatting | `_cm_post` |
| `TestInvoiceMerge` | Dedup against active.jsonl by invoice_number with case-fold | `_cm_post` |

### Existing fixtures to reuse (do NOT re-create)
- `TestBackfillIdempotent._snapshot_managed` (test_vault_writer.py:219) — snapshots `.md` content excluding `last_synced`. Phase 11 should also snapshot excluding `cm_data_stale_since` for the same reason.
- `tempfile.TemporaryDirectory` for `data_dir` + `build_dir` + `feed_dir` — see TestProjection. Phase 11 adds a 4th tempdir for `cache_dir` or just uses one within `data_dir`.

## Validation Architecture (integration-only — Nyquist disabled in config)

`workflow.nyquist_validation` is `false` in `.planning/config.json`, so the standard requirements-to-tests mapping table is omitted. However, the integration boundary is high-risk enough that some executable validation is still warranted in the plan:

### Recommended integration validations (not formal Nyquist; standard pytest)
1. **Mock contract test for the JSON-RPC client:** Given a frozen CM response payload, assert our parser produces the expected frontmatter dict + section markdown. Catches regressions when Glen edits CM tool shapes on the other side.
2. **Schema-shape test on cached responses:** When loading `data/.cm-cache.json`, validate the per-tool shape (could use jsonschema lib, or manual asserts). Avoids "old cache from before a CM tool change crashes today's render."
3. **Idempotency replay against frozen mock data:** Two consecutive `run_backfill` runs with the same mocked CM response produce byte-identical managed sections (modulo `last_synced` AND `cm_data_stale_since`). This test extends Phase 10's `TestBackfillIdempotent`.
4. **Cache-fallback round-trip:** Force `_cm_post` to raise `CmTransportError`. After retry exhaustion, the run uses the cached value AND stamps `cm_data_stale_since` in frontmatter. Then a subsequent run with `_cm_post` succeeding clears `cm_data_stale_since`.

### Sampling
- **Per task commit:** `python3 -m unittest discover scripts/tests` (matches Phase 10 ergonomics; existing 25 tests pass in 0.127s — Phase 11's additions should keep total under 1s).
- **Per phase merge:** Same — there is no separate full-suite vs quick-suite split today, and Phase 11 doesn't justify creating one.

## Project Constraints (from CLAUDE.md)

The planner MUST honor these — verbatim from `/Users/glenr/work/todo-list/CLAUDE.md`:

- **MCP server discipline:** Use ONLY the `hardened-workspace` MCP server for Gmail/Drive access. Phase 11 introduces a NEW MCP integration (Contract Manager) — but it is read-only, owned by Glen, on his own infrastructure (`contracts.agend.info`). It does NOT replace or compete with hardened-workspace. Document in the plan that the CM MCP is separate from the Gmail MCP.
- **Data ownership:** Local git repo as source of truth. CONTEXT.md D-A1 deliberately bends this — CM is the source of truth for 5 frontmatter fields. The cache (D-A3) is fallback-only. The plan must make this explicit, including the gitignore for `.cm-cache.json`.
- **Privacy:** Email content and business data must not leak to third-party services beyond Claude's own infrastructure. CM is Glen's own server, not a third-party — constraint preserved.
- **GSD workflow:** Phase 11 must go through `/gsd:execute-phase`. Already in flight per the orchestrator that spawned this researcher.
- **Server sync:** After committing data changes, run `bash scripts/push-and-sync.sh`. Phase 11 commits will include `data/config/clients.jsonl` (cm_client_id mapping) and possibly `vault-build/` regeneration; this rail is unchanged.
- **NDJSON conventions:** Activity feed in `data/feed.jsonl`, ISO 8601 with offset, types/levels/triggers per `schemas/feed-entry.json`. Phase 11 uses `system`/`info` (or new `warning` if schema is extended) for CM staleness.
- **Atomic writes:** Already a Phase 10 pattern; Phase 11 reuses `_atomic_write` for the cache file.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `deployed_modules` derived from `activeContracts[].name` is acceptable fidelity for v1 | Code Examples > cm_summary_to_frontmatter_extra | If Glen wants per-product (Product table) not per-contract names, Sites/Usage rendering needs CM tool extension before Phase 11 ships. |
| A2 | `primary_contact` = first item in CM `contacts[]` (which is ordered by `id ASC`, top 5) | Code Examples > cm_summary_to_frontmatter_extra | If Glen has multiple contacts and wants role-based selection (e.g., "billing" vs "primary"), this picks the wrong one. CM contact has a `role` field — could filter on that, but requires Glen's preference. |
| A3 | CM uses local-Adelaide TZ implicitly for date fields like `endDate: "2026-06-15"` | Code Examples > cm_contract_expiry_to_event_tuple | If CM stores in UTC but renders as date-only, the activity log entry could appear off by 1 day. Mitigation: render as `[YYYY-MM-DD]` (day-only) for contract events instead of `[YYYY-MM-DD HH:MM]`. |
| A4 | `data/invoices/active.jsonl` is currently empty (`0B`), so dedup logic is untested against real data | Pitfall 4 + Code Examples | Untested code path. Plan must include an integration test with synthetic local + CM invoice records. `[VERIFIED: stat shows 0B file]` |
| A5 | The `system`/`info` feed level is acceptable for CM staleness if `warning` cannot be added to the schema in this phase | Critical Findings (#2) | If `info` is too low and Glen misses the signal, dashboards may not surface it. Recommend: extend schema to add `"warning"` — small, safe change. |
| A6 | One `tools/list` call during the one-time mapping pass is acceptable | Pitfall 5 | Trivial cost; included for completeness as plan documentation. |
| A7 | Coolify can be configured to inject `CONTRACT_MANAGER_API_KEY` as an env var visible to bash subshells | Standard Stack > Stack Patterns | Standard Coolify behavior; if env injection requires a service restart, the plan should document that. |
| A8 | The `get_utilization_summary` and `get_capacity_summary` tools are global (no client filter), so D-C3's "consultant utilization for THIS client" cannot be sourced from them as-is | CM Tool Contract Reference | If Glen confirms global-team utilization is acceptable as a per-client section, fine. If he wants client-scoped utilization, CM needs a tool addition first. **This is a Critical Finding — see Open Questions.** |

## Open Questions (RESOLVED 2026-05-02)

These needed resolution before the planner wrote plans. All five were resolved during the post-research CONTEXT.md refinement session and confirmed by Plan 02 Task 3's checkpoint. Each question is annotated below with the resolving decision.

1. **Sites and `deployed_modules` source — CM cannot supply them today.**
   - What we know: Prisma `Site` and `Product` tables exist; MCP does not expose them.
   - What's unclear: Does Glen want Phase 11 to ship without Sites + with `deployed_modules` derived from contract names (limited fidelity)? Or extend CM's MCP first to add `list_sites_for_client(clientId)` and `list_deployed_products_for_client(clientId)`?
   - Recommendation: **Defer Sites until CM exposes a tool for it. Use `activeContracts[].name` for `deployed_modules` v1 with a note in the rendered section that says "(derived from contract names; will refine when CM exposes per-product detail)".** This keeps Phase 11 shippable. Glen can add CM tools in a Phase 11.x or Phase 12.
   - **RESOLVED:** see CONTEXT.md D-C2-REVISED (Sites section deferred; `sites: []` always) + D-B-MOD-REVISED (`deployed_modules` derived from `activeContracts[].name`).

2. **D-C3 Usage section — `get_utilization_summary` and `get_capacity_summary` are GLOBAL not per-client.**
   - What we know: Both tools return team-wide data, not client-filtered. `get_sla_status` is the closest to per-client (per-project + classifies by client) but isn't listed in CONTEXT.md.
   - What's unclear: Should each client note's Usage section show team-wide aggregates (i.e., the same numbers for all 3 clients)? Or should we use `get_sla_status` to scope by project per-client? Or defer Usage to Phase 11.x?
   - Recommendation: **Use `get_sla_status` (which CM already exposes) for the per-client Usage section.** Its `projects[]` array has `clientName` for grouping, and renders fields close to CONTEXT.md D-C3 ("hours billed this month, % of budget"). Add this to CONTEXT.md tool list before planning. If Glen still wants `get_utilization_summary` data, render it once in a global "Team utilization" stub on `_Unknown.md` or a future portfolio dashboard.
   - **RESOLVED:** see CONTEXT.md D-C3-REVISED (Usage section uses `get_sla_status` per-client; `get_utilization_summary` / `get_capacity_summary` rejected because team-wide).

3. **`warning` level on feed-entry schema — extend or substitute?**
   - What we know: Schema currently allows only `["critical", "info", "debug"]`. CONTEXT.md D-A3 says CM staleness is `warning`.
   - What's unclear: Does the planner have authority to extend the schema, or is this a separate task that needs Glen's blessing?
   - Recommendation: Treat as a Wave 0 task. One JSON line edit, no breaking change. Plan should sequence schema-extend BEFORE the first CM warning emission.
   - **RESOLVED:** see CONTEXT.md D-A3-REVISED (`warning` level added to `schemas/feed-entry.json` as Wave 0 task; additive enum change).

4. **API key bootstrap timing.**
   - What we know: Glen mints in CM dashboard, sets in Coolify env.
   - What's unclear: When does this happen relative to plan execution? If the plan implements + tests against a key that doesn't yet exist, every integration test fails.
   - Recommendation: Plan structure as Wave 0 = "Glen mints key, sets on Coolify, confirms via curl"; Waves 1+ = code. The mock-based tests run regardless of key presence.
   - **RESOLVED:** see Plan 02 Task 3 checkpoint (Glen mints CM key at `/settings/mcp`, injects via Coolify env, runs `--mode map-cm-clients`, commits `clients.jsonl`). Mock-based unit tests run regardless of key presence.

5. **Mapping pass execution mode.**
   - What we know: `search_clients` returns ID for a name query; cache `cm_client_id` in `clients.jsonl`.
   - What's unclear: Where does this run — a one-shot script, a `vault_writer --mode map-cm-clients` mode, or inline as part of first sync?
   - Recommendation: New mode `vault_writer --mode map-cm-clients` (idempotent — re-runs are safe and update IDs if CM IDs ever change). Run manually by Glen once. Subsequent syncs skip the mapping (cm_client_id already populated). If a client is added to `clients.jsonl` and lacks `cm_client_id`, sync runs `search_clients` for that one new client only.
   - **RESOLVED:** see CONTEXT.md D-G1 (mandatory `vault_writer --mode map-cm-clients` Wave 0 mapping pass; idempotent; new `clients.jsonl` records without `cm_client_id` trigger a single `search_clients` JIT mapping on next sync).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ stdlib `urllib`, `json`, `time`, `tempfile`, `fcntl` | cm_client.py | ✓ | 3.x (verified by Phase 10 in production) | — |
| ruamel.yaml >=0.18,<0.19 | render_frontmatter (Phase 10 dep) | ✓ | 0.18.x | — |
| `flock` (Linux) | scripts/sync-obsidian.sh wrapper | ✓ on Coolify | util-linux | Mac uses direct python invocation per `sync-obsidian.sh:14-18` |
| `fswatch` (macOS) | Mac LaunchAgent | ✓ on Mac Studio | per `mac/install-daemon.sh` | — |
| `CONTRACT_MANAGER_API_KEY` env var | cm_client.py | ✗ on Coolify (not yet set) | — | **No fallback — blocking dep.** Must be set before first CM-aware sync run. Test environment: use a fixture key in tests; production: Glen mints + sets via Coolify UI. |
| Network egress to `contracts.agend.info` from Coolify | cm_client.py | Assumed ✓ (CM is on Glen's infra; Coolify presumably has standard outbound) | — | If blocked: cache fallback degrades to "first-time-ever sync produces empty CM fields." |
| Network egress NOT required from Mac Studio to CM | run_projection (UNCHANGED) | n/a | — | By design Mac never calls CM. |

**Missing dependencies with no fallback:**
- `CONTRACT_MANAGER_API_KEY` — Glen mints + Coolify-injects before first sync.

**Missing dependencies with fallback:**
- None for v1.

## Critical Findings (read first)

The planner MUST decide on each of these BEFORE writing plans:

1. **Sites are not in CM MCP** (Open Question 1). Recommend deferring `sites[]` frontmatter and Sites section until CM exposes them. Phase 11 ships with empty `sites: []` always. Cleanup: re-flag in CONTEXT.md or update Decisions.

2. **`deployed_modules` is derived, not authoritative** (Open Question 1, Assumption A1). Per-contract name is the best we can do today — coarser than per-Product. Acceptable for v1 IF Glen agrees.

3. **D-C3 Usage section needs `get_sla_status`, not `get_utilization_summary` or `get_capacity_summary`** (Open Question 2, Assumption A8). The two tools listed in CONTEXT.md are global. The right tool exists but isn't named. Update CONTEXT.md tool list before planning.

4. **Feed-entry schema lacks `warning` level** (Open Question 3, Critical Finding #2). Plan should extend the schema as a Wave 0 task. Substitution to `info` is acceptable but lower-fidelity.

5. **`cm_client_id` mapping pass is mandatory, not deferred** (Critical Finding #3). `get_client_summary` requires numeric ID. Plan must ship the mapping mode and run it before first frontmatter populate.

## Sources

### Primary (HIGH confidence — verified via direct source code reading)
- `~/work/contract-manager/src/app/api/mcp/route.ts` — auth, dispatch, rate limit
- `~/work/contract-manager/src/lib/mcp/server.ts` — tools/call dispatch, structuredContent shape
- `~/work/contract-manager/src/lib/mcp/types.ts` — JsonRpcRequest/Response/ErrorCode contracts
- `~/work/contract-manager/src/lib/mcp/tools/index.ts` — full tool registry (15 tools)
- `~/work/contract-manager/src/lib/mcp/tools/lookups.ts` — search_clients, get_client_summary
- `~/work/contract-manager/src/lib/mcp/tools/operations.ts` — list_contracts_expiring, get_capacity_summary, get_utilization_summary, get_sla_status
- `~/work/contract-manager/src/lib/mcp/tools/financial.ts` — list_overdue_invoices
- `~/work/contract-manager/src/lib/api-key-auth.ts` — generateApiKey format
- `~/work/contract-manager/src/lib/api-utils.ts` — getRateLimitHeaders (Retry-After format)
- `~/work/contract-manager/src/lib/config/constants.ts:316-319` — RATE_LIMITS.EXTERNAL_API
- `~/work/contract-manager/prisma/schema.prisma` — Site model, Product model (NOT exposed via MCP)
- `scripts/lib/vault_writer.py` — Phase 10 sync engine (the extension target)
- `scripts/sync-obsidian.sh` — Linux flock wrapper
- `scripts/tests/test_vault_writer.py` — Phase 10 test patterns (extension reference)
- `schemas/feed-entry.json` — confirms `warning` level missing
- `data/config/clients.jsonl` — current 3-client registry, no cm_client_id field
- `.planning/phases/10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli/10-CONTEXT.md` — D-04..D-18 carry-forward decisions
- `.planning/phases/10-obsidian-knowledge-layer-client-notes-build-a-vault-side-cli/10-VERIFICATION.md` — Phase 10 must-haves all verified
- `.planning/phases/11-contract-manager-integration-seed-and-refresh-client-note-fr/11-CONTEXT.md` — D-A1..D-F1
- `.planning/REQUIREMENTS.md` — INTL-01 mapping
- `.planning/PROJECT.md` — core value, ownership, privacy constraints
- `CLAUDE.md` — project guardrails (hardened MCP discipline, data ownership)

### Secondary (MEDIUM confidence — official docs of broadly used libraries)
- [Python urllib.request docs](https://docs.python.org/3/library/urllib.request.html) — verified default ssl context behavior — used implicitly via stdlib choice rationale
- [JSON-RPC 2.0 specification](https://www.jsonrpc.org/specification) — envelope shape, batch semantics — sanity-checked against CM types.ts:24-55

### Tertiary (LOW confidence — corroborating, not load-bearing)
- [findwork.dev: Advanced usage of Python requests](https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/) — informed the urllib-vs-requests tradeoff write-up
- [scrapeops.io: Python HTTPX retry](https://scrapeops.io/python-web-scraping-playbook/python-httpx-retry-failed-requests/) — confirms httpx is async-first; sync-only Phase 11 doesn't benefit
- [pypi.org: backoff library](https://pypi.org/project/backoff/) — confirms decorator pattern is overkill for D-A3's hand-tuned timing

## Metadata

**Confidence breakdown:**
- Standard stack (urllib): HIGH — Phase 10 precedent + zero-dep philosophy
- Architecture (cm_client.py separate module): HIGH — clean test seam, mirrors vault_writer's responsibility split
- Auth + rate limits: HIGH — verified line-by-line in CM source
- CM tool contracts: HIGH — copied directly from TypeScript handler signatures
- Sites/Usage feasibility: MEDIUM — flagged as Critical Findings; depends on Glen's call on tool extension vs deferral
- Feed-entry schema: HIGH — schema file directly verified; `warning` is genuinely absent
- Cache concurrency strategy: HIGH — flock window already exists, no new locking needed
- Test scaffolding: HIGH — mirrors Phase 10's test patterns; mock seam is well-defined
- Invoice dedup field names: HIGH — verified `invoice_number` in both schemas

**Research date:** 2026-05-02
**Valid until:** 2026-06-01 (30 days for the broadly stable urllib/JSON-RPC parts; CM tool shapes valid until Glen ships a CM-side change — re-verify by reading the same TypeScript files)
