"""Phase 11 — Contract Manager MCP client unit tests.

Run: python3 -m unittest discover scripts/tests
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestCmClient(unittest.TestCase):
    """JSON-RPC envelope shape, header injection, error parsing.

    Mocks urllib.request.urlopen because we are testing the seam itself.
    """

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

    @patch("scripts.lib.cm_client.urllib.request.urlopen")
    def test_post_builds_correct_envelope(self, mock_urlopen):
        from scripts.lib.cm_client import _cm_post
        mock_urlopen.return_value = self._mock_response({
            "jsonrpc": "2.0", "id": 1,
            "result": {"content": [{"type": "text", "text": "{}"}],
                       "structuredContent": {"client": {"id": 42}},
                       "isError": False},
        })
        result = _cm_post("get_client_summary", {"clientId": 42}, "test_key")
        self.assertEqual(result, {"client": {"id": 42}})
        # Verify request shape
        request_obj = mock_urlopen.call_args[0][0]
        body = json.loads(request_obj.data.decode("utf-8"))
        self.assertEqual(body["jsonrpc"], "2.0")
        self.assertEqual(body["method"], "tools/call")
        self.assertEqual(body["params"]["name"], "get_client_summary")
        self.assertEqual(body["params"]["arguments"], {"clientId": 42})
        # Verify Authorization header (urllib lower-cases header names internally)
        headers = {k.lower(): v for k, v in request_obj.headers.items()}
        self.assertEqual(headers["authorization"], "Bearer test_key")

    @patch("scripts.lib.cm_client.urllib.request.urlopen")
    def test_post_raises_on_jsonrpc_error(self, mock_urlopen):
        from scripts.lib.cm_client import _cm_post, CmRpcError
        mock_urlopen.return_value = self._mock_response({
            "jsonrpc": "2.0", "id": 1,
            "error": {"code": -32600, "message": "Invalid"},
        })
        with self.assertRaises(CmRpcError):
            _cm_post("get_client_summary", {"clientId": 42}, "test_key")

    @patch("scripts.lib.cm_client.urllib.request.urlopen")
    def test_post_raises_on_iserror_true(self, mock_urlopen):
        from scripts.lib.cm_client import _cm_post, CmRpcError
        mock_urlopen.return_value = self._mock_response({
            "jsonrpc": "2.0", "id": 1,
            "result": {"content": [{"type": "text", "text": "Client not found"}],
                       "isError": True},
        })
        with self.assertRaises(CmRpcError):
            _cm_post("get_client_summary", {"clientId": 999}, "test_key")

    @patch("scripts.lib.cm_client.urllib.request.urlopen")
    def test_post_raises_rate_limit_on_429(self, mock_urlopen):
        import urllib.error
        from scripts.lib.cm_client import _cm_post, CmRateLimitError
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="x", code=429, msg="Too Many Requests",
            hdrs={"Retry-After": "60"}, fp=None,
        )
        with self.assertRaises(CmRateLimitError) as ctx:
            _cm_post("get_client_summary", {"clientId": 42}, "test_key")
        self.assertEqual(ctx.exception.retry_after_seconds, 60)


class TestCallWithRetry(unittest.TestCase):
    """D-A3: 3 retries with 1s/5s/30s; honour Retry-After once."""

    @patch("scripts.lib.cm_client._cm_post")
    def test_succeeds_on_first_try(self, mock_post):
        from scripts.lib.cm_client import call_with_retry
        mock_post.return_value = {"client": {"id": 42}}
        result = call_with_retry("get_client_summary", {"clientId": 42}, "key")
        self.assertEqual(result["client"]["id"], 42)
        self.assertEqual(mock_post.call_count, 1)

    @patch("scripts.lib.cm_client._cm_post")
    @patch("scripts.lib.cm_client.time.sleep")
    def test_retries_three_times_then_raises(self, mock_sleep, mock_post):
        from scripts.lib.cm_client import call_with_retry, CmTransportError
        mock_post.side_effect = CmTransportError("boom")
        with self.assertRaises(CmTransportError):
            call_with_retry("x", {}, "key")
        self.assertEqual(mock_post.call_count, 4)  # initial + 3 retries
        # Verify the 1s/5s/30s delays were used (sleep called with these values)
        sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
        self.assertIn(1, sleep_args)
        self.assertIn(5, sleep_args)
        self.assertIn(30, sleep_args)

    @patch("scripts.lib.cm_client._cm_post")
    @patch("scripts.lib.cm_client.time.sleep")
    def test_rate_limit_uses_retry_after(self, mock_sleep, mock_post):
        from scripts.lib.cm_client import call_with_retry, CmRateLimitError
        mock_post.side_effect = [CmRateLimitError(60), {"ok": True}]
        result = call_with_retry("x", {}, "key")
        self.assertEqual(result, {"ok": True})
        sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
        self.assertIn(60, sleep_args)


class TestCmCache(unittest.TestCase):
    """Atomic write, corruption tolerance, GC of orphan keys."""

    def test_load_cache_missing_returns_skeleton(self):
        from scripts.lib.cm_client import load_cache, CACHE_SCHEMA_VERSION
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "missing.json"
            cache = load_cache(path)
            self.assertEqual(cache["schema_version"], CACHE_SCHEMA_VERSION)
            self.assertEqual(cache["global"], {})
            self.assertEqual(cache["by_client"], {})

    def test_load_cache_corrupt_returns_skeleton(self):
        from scripts.lib.cm_client import load_cache
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "corrupt.json"
            path.write_text("not json {{{", encoding="utf-8")
            cache = load_cache(path)
            self.assertEqual(cache["by_client"], {})

    def test_write_then_load_roundtrip(self):
        from scripts.lib.cm_client import write_cache, load_cache
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "cache.json"
            cache = {"schema_version": 1, "global": {"x": 1}, "by_client": {"example.com": {"y": 2}}}
            write_cache(path, cache)
            loaded = load_cache(path)
            self.assertEqual(loaded["global"], {"x": 1})
            self.assertEqual(loaded["by_client"]["example.com"], {"y": 2})

    def test_gc_orphans_drops_unknown_domains(self):
        from scripts.lib.cm_client import gc_cache_orphans
        cache = {
            "schema_version": 1,
            "global": {},
            "by_client": {
                "active.com": {"x": 1},
                "removed.com": {"y": 2},
            },
        }
        gc_cache_orphans(cache, {"active.com"})
        self.assertIn("active.com", cache["by_client"])
        self.assertNotIn("removed.com", cache["by_client"])


class TestCmSummaryAdapter(unittest.TestCase):
    """D-B1, D-B2, D-B-MOD-REVISED, D-C2-REVISED."""

    def test_empty_summary_yields_empty_strings_and_lists(self):
        from scripts.lib.cm_client import cm_summary_to_frontmatter_extra
        out = cm_summary_to_frontmatter_extra({})
        self.assertEqual(out["contract_start"], "")
        self.assertEqual(out["contract_end"], "")
        self.assertEqual(out["primary_contact"], "")
        self.assertEqual(out["deployed_modules"], [])
        self.assertEqual(out["sites"], [])

    def test_populated_contracts_yield_min_max_dates(self):
        from scripts.lib.cm_client import cm_summary_to_frontmatter_extra
        summary = {
            "activeContracts": [
                {"name": "AMS Core", "startDate": "2026-01-01", "endDate": "2027-01-01"},
                {"name": "Events", "startDate": "2025-06-01", "endDate": "2026-12-31"},
                {"name": "AMS Core", "startDate": "2026-03-01", "endDate": "2027-06-01"},
            ],
            "contacts": [{"name": "Alice", "email": "a@x.com"}],
        }
        out = cm_summary_to_frontmatter_extra(summary)
        self.assertEqual(out["contract_start"], "2025-06-01")  # min
        self.assertEqual(out["contract_end"], "2027-06-01")  # max
        self.assertEqual(out["primary_contact"], "Alice")
        self.assertEqual(out["deployed_modules"], ["AMS Core", "Events"])  # sorted unique

    def test_sites_always_empty_per_d_c2_revised(self):
        from scripts.lib.cm_client import cm_summary_to_frontmatter_extra
        # Even if CM returned sites somehow, our adapter ignores and emits []
        summary = {"activeContracts": [], "contacts": []}
        out = cm_summary_to_frontmatter_extra(summary)
        self.assertEqual(out["sites"], [])
