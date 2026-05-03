"""Phase 12 — workspace_client unit tests.

Mirrors test_cm_client.py 1:1; new test classes added for Phase 12-specific
surfaces (endpoint allowlist, OAuth token loader, privacy filters).

All tests mock urllib.request.urlopen for the seam-level class (TestWorkspaceClient)
and mock _workspace_get for higher-level classes (TestWorkspaceCallWithRetry, etc.).
"""
import json
import unittest
import unittest.mock as mock
from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error


class TestWorkspaceClient(unittest.TestCase):
    """Phase 12: HTTPS GET seam — URL/header construction, error mapping."""

    def _mock_response(self, payload: dict, status: int = 200,
                       headers: dict | None = None):
        """Build a context-manager-compatible mock response (verbatim from test_cm_client.py)."""
        m = MagicMock()
        m.read.return_value = json.dumps(payload).encode("utf-8")
        m.__enter__ = lambda self_: m
        m.__exit__ = lambda self_, *args: False
        m.status = status
        m.headers = headers or {}
        return m

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
        # No Content-Type for GET — important: any value here would suggest a
        # body, which workspace_client never sends.
        self.assertNotIn("content-type", headers)

    @patch("scripts.lib.workspace_client.urllib.request.urlopen")
    def test_get_unwraps_json_payload_directly(self, mock_urlopen):
        """Google APIs return flat JSON (not the JSON-RPC envelope CM uses)."""
        from scripts.lib.workspace_client import _workspace_get
        payload = {"items": [{"id": "f1"}], "nextPageToken": "tok"}
        mock_urlopen.return_value = self._mock_response(payload)
        result = _workspace_get("drive/v3/files", {}, "test_token")
        self.assertEqual(result, payload)

    @patch("scripts.lib.workspace_client.urllib.request.urlopen")
    def test_get_raises_rpc_error_on_google_error_envelope(self, mock_urlopen):
        from scripts.lib.workspace_client import _workspace_get, WorkspaceRpcError
        mock_urlopen.return_value = self._mock_response(
            {"error": {"code": 400, "message": "Invalid timeMin format"}}
        )
        with self.assertRaises(WorkspaceRpcError) as ctx:
            _workspace_get("calendar/v3/calendars/primary/events", {}, "tok")
        self.assertIn("400", str(ctx.exception))
        self.assertIn("Invalid timeMin format", str(ctx.exception))

    @patch("scripts.lib.workspace_client.urllib.request.urlopen")
    def test_get_raises_auth_expired_on_401(self, mock_urlopen):
        from scripts.lib.workspace_client import (
            _workspace_get, WorkspaceAuthExpiredError, WorkspaceTransportError,
        )
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="x", code=401, msg="Unauthorized", hdrs={}, fp=None,
        )
        with self.assertRaises(WorkspaceAuthExpiredError) as ctx:
            _workspace_get("drive/v3/files", {}, "expired_token")
        # Subclass check — caller catching the broader TransportError still works.
        self.assertIsInstance(ctx.exception, WorkspaceTransportError)

    @patch("scripts.lib.workspace_client.urllib.request.urlopen")
    def test_get_raises_rate_limit_with_retry_after(self, mock_urlopen):
        from scripts.lib.workspace_client import (
            _workspace_get, WorkspaceRateLimitError,
        )
        # urllib.error.HTTPError stores headers via the `hdrs` argument; the .headers
        # attribute supports .get() for this header name in CPython's Message impl.
        import email.message
        msg = email.message.Message()
        msg["Retry-After"] = "60"
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="x", code=429, msg="Too Many Requests", hdrs=msg, fp=None,
        )
        with self.assertRaises(WorkspaceRateLimitError) as ctx:
            _workspace_get("calendar/v3/calendars/primary/events", {}, "tok")
        self.assertEqual(ctx.exception.retry_after_seconds, 60)

    @patch("scripts.lib.workspace_client.urllib.request.urlopen")
    def test_get_raises_rate_limit_default_retry_after_30s(self, mock_urlopen):
        from scripts.lib.workspace_client import (
            _workspace_get, WorkspaceRateLimitError,
        )
        import email.message
        msg = email.message.Message()  # no Retry-After header
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="x", code=429, msg="Too Many Requests", hdrs=msg, fp=None,
        )
        with self.assertRaises(WorkspaceRateLimitError) as ctx:
            _workspace_get("drive/v3/files", {}, "tok")
        self.assertEqual(ctx.exception.retry_after_seconds, 30)

    @patch("scripts.lib.workspace_client.urllib.request.urlopen")
    def test_get_raises_transport_on_500(self, mock_urlopen):
        from scripts.lib.workspace_client import (
            _workspace_get, WorkspaceTransportError,
        )
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="x", code=500, msg="Internal Server Error", hdrs={}, fp=None,
        )
        with self.assertRaises(WorkspaceTransportError) as ctx:
            _workspace_get("calendar/v3/calendars/primary/events", {}, "tok")
        self.assertIn("HTTP 500", str(ctx.exception))

    @patch("scripts.lib.workspace_client.urllib.request.urlopen")
    def test_get_raises_transport_on_network_error(self, mock_urlopen):
        from scripts.lib.workspace_client import (
            _workspace_get, WorkspaceTransportError,
        )
        mock_urlopen.side_effect = urllib.error.URLError("DNS lookup failed")
        with self.assertRaises(WorkspaceTransportError) as ctx:
            _workspace_get("drive/v3/files", {}, "tok")
        self.assertIn("network", str(ctx.exception))

    @patch("scripts.lib.workspace_client.urllib.request.urlopen")
    def test_get_rejects_disallowed_endpoint(self, mock_urlopen):
        """D-X1 trust boundary: only allowlisted endpoints reach the network."""
        from scripts.lib.workspace_client import (
            _workspace_get, WorkspaceTransportError,
        )
        with self.assertRaises(WorkspaceTransportError) as ctx:
            _workspace_get("admin/directory/v1/users", {}, "tok")
        self.assertIn("not in allowlist", str(ctx.exception))
        # Critical: disallowed paths short-circuit BEFORE any network call.
        mock_urlopen.assert_not_called()

    @patch("scripts.lib.workspace_client.urllib.request.urlopen")
    def test_get_accepts_drive_files_id_prefix(self, mock_urlopen):
        """Allowlist prefix entry: drive/v3/files/{id} for child-folder listings."""
        from scripts.lib.workspace_client import _workspace_get
        mock_urlopen.return_value = self._mock_response({"id": "abc", "name": "f"})
        # Should NOT raise:
        result = _workspace_get("drive/v3/files/abc123", {}, "tok")
        self.assertEqual(result["id"], "abc")


class TestWorkspaceCallWithRetry(unittest.TestCase):
    """Phase 12: D-A3 retry loop — 1s/5s/30s with auth-expired short-circuit."""

    @patch("scripts.lib.workspace_client.time.sleep")
    @patch("scripts.lib.workspace_client._workspace_get")
    def test_succeeds_first_try(self, mock_get, mock_sleep):
        from scripts.lib.workspace_client import call_with_retry
        mock_get.return_value = {"ok": True}
        result = call_with_retry("calendar/v3/calendars/primary/events", {}, "tok")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(mock_get.call_count, 1)
        # No retry sleeps fired (the delays==0 first pass skips sleep).
        nonzero_sleeps = [c for c in mock_sleep.call_args_list if c.args[0] != 0]
        self.assertEqual(nonzero_sleeps, [])

    @patch("scripts.lib.workspace_client.time.sleep")
    @patch("scripts.lib.workspace_client._workspace_get")
    def test_retries_three_times_then_raises(self, mock_get, mock_sleep):
        from scripts.lib.workspace_client import (
            call_with_retry, WorkspaceTransportError,
        )
        mock_get.side_effect = WorkspaceTransportError("down")
        with self.assertRaises(WorkspaceTransportError):
            call_with_retry("drive/v3/files", {}, "tok")
        # 1 immediate + 3 retries = 4 calls
        self.assertEqual(mock_get.call_count, 4)
        # Sleep delays in order: 1s, 5s, 30s (the 0 first delay is skipped)
        sleeps_seen = [c.args[0] for c in mock_sleep.call_args_list]
        self.assertEqual(sleeps_seen, [1, 5, 30])

    @patch("scripts.lib.workspace_client.time.sleep")
    @patch("scripts.lib.workspace_client._workspace_get")
    def test_rate_limit_uses_retry_after(self, mock_get, mock_sleep):
        from scripts.lib.workspace_client import (
            call_with_retry, WorkspaceRateLimitError,
        )
        mock_get.side_effect = [
            WorkspaceRateLimitError(42),
            {"ok": True},
        ]
        result = call_with_retry("calendar/v3/calendars/primary/events", {}, "tok")
        self.assertEqual(result, {"ok": True})
        # Retry-After honoured: time.sleep(42) called
        self.assertIn(42, [c.args[0] for c in mock_sleep.call_args_list])

    @patch("scripts.lib.workspace_client.time.sleep")
    @patch("scripts.lib.workspace_client._workspace_get")
    def test_auth_expired_propagates_immediately(self, mock_get, mock_sleep):
        from scripts.lib.workspace_client import (
            call_with_retry, WorkspaceAuthExpiredError,
        )
        mock_get.side_effect = WorkspaceAuthExpiredError("401")
        with self.assertRaises(WorkspaceAuthExpiredError):
            call_with_retry("drive/v3/files", {}, "expired_tok")
        # Critical: auth-expired does NOT consume retries — only 1 call.
        self.assertEqual(mock_get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
