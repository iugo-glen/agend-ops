"""Phase 12 — workspace_client unit tests.

Mirrors test_cm_client.py 1:1; new test classes added for Phase 12-specific
surfaces (endpoint allowlist, OAuth token loader, privacy filters).

All tests mock urllib.request.urlopen for the seam-level class (TestWorkspaceClient)
and mock _workspace_get for higher-level classes (TestWorkspaceCallWithRetry, etc.).
"""
import json
import os
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


class TestWorkspaceCache(unittest.TestCase):
    """Phase 12: cache helpers — atomic write, corruption tolerance, GC."""

    def test_load_cache_missing_returns_skeleton(self):
        from scripts.lib.workspace_client import load_cache, CACHE_SCHEMA_VERSION
        with mock.patch("pathlib.Path.exists", return_value=False):
            cache = load_cache(Path("/nonexistent/cache.json"))
        self.assertEqual(cache["schema_version"], CACHE_SCHEMA_VERSION)
        self.assertEqual(cache["global"], {})
        self.assertEqual(cache["by_client"], {})

    def test_load_cache_corrupt_returns_skeleton(self):
        from scripts.lib.workspace_client import load_cache
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{not valid json")
            corrupt_path = Path(f.name)
        try:
            cache = load_cache(corrupt_path)
            self.assertEqual(cache["global"], {})
            self.assertEqual(cache["by_client"], {})
        finally:
            corrupt_path.unlink()

    def test_load_cache_schema_mismatch_returns_skeleton(self):
        from scripts.lib.workspace_client import load_cache
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"schema_version": 999, "global": {"k": "v"}}, f)
            mismatch_path = Path(f.name)
        try:
            cache = load_cache(mismatch_path)
            self.assertEqual(cache["global"], {})  # reset to skeleton
        finally:
            mismatch_path.unlink()

    def test_write_cache_atomic_roundtrip(self):
        from scripts.lib.workspace_client import (
            write_cache, load_cache, CACHE_SCHEMA_VERSION,
        )
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            cache_path = Path(d) / "cache.json"
            cache = {
                "schema_version": CACHE_SCHEMA_VERSION,
                "global": {"calendar_events": {"fetched_at": "2026-05-02T10:00", "result": {"items": []}}},
                "by_client": {},
            }
            write_cache(cache_path, cache)
            self.assertTrue(cache_path.exists())
            roundtrip = load_cache(cache_path)
            self.assertEqual(roundtrip, cache)

    def test_gc_cache_orphans_drops_unknown_domains(self):
        from scripts.lib.workspace_client import gc_cache_orphans, CACHE_SCHEMA_VERSION
        cache = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "global": {},
            "by_client": {
                "current.com": {"x": 1},
                "removed.com": {"x": 2},
                "alsoremoved.com": {"x": 3},
            },
        }
        result = gc_cache_orphans(cache, {"current.com"})
        self.assertEqual(set(result["by_client"].keys()), {"current.com"})

    def test_load_cache_defensive_setdefault_for_missing_subkeys(self):
        """Cache file with schema_version=1 but missing 'global' or 'by_client' keys."""
        from scripts.lib.workspace_client import load_cache, CACHE_SCHEMA_VERSION
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"schema_version": CACHE_SCHEMA_VERSION}, f)  # no sub-keys
            partial_path = Path(f.name)
        try:
            cache = load_cache(partial_path)
            self.assertEqual(cache["global"], {})
            self.assertEqual(cache["by_client"], {})
        finally:
            partial_path.unlink()


class TestIsInternalHelper(unittest.TestCase):
    """D-D1 part 2 — _is_internal classification."""

    def test_iugo_domain_is_internal(self):
        from scripts.lib.workspace_client import _is_internal
        self.assertTrue(_is_internal("anyone@iugo.com.au", "glen@iugo.com.au"))

    def test_primary_email_is_internal_case_insensitive(self):
        from scripts.lib.workspace_client import _is_internal
        self.assertTrue(_is_internal("GLEN@iugo.com.au", "glen@iugo.com.au"))

    def test_external_domain_is_external(self):
        from scripts.lib.workspace_client import _is_internal
        self.assertFalse(_is_internal("alex@otaus.com.au", "glen@iugo.com.au"))

    def test_empty_email_treated_as_internal(self):
        from scripts.lib.workspace_client import _is_internal
        self.assertTrue(_is_internal("", "glen@iugo.com.au"))

    def test_no_at_sign_treated_as_internal(self):
        from scripts.lib.workspace_client import _is_internal
        self.assertTrue(_is_internal("malformed_no_at_sign", "glen@iugo.com.au"))


class TestCalendarEventAdapter(unittest.TestCase):
    """Phase 12 D-D1 + D-D2 — format_calendar_event_for_log."""

    def _event(self, **overrides) -> dict:
        e = {
            "id": "evt-001",
            "summary": "Sync with PCA",
            "start": {"dateTime": "2026-05-15T10:00:00+10:30"},
            "end": {"dateTime": "2026-05-15T11:00:00+10:30"},
            "attendees": [
                {"email": "glen@iugo.com.au"},
                {"email": "craig@propertycouncil.com.au"},
            ],
            "htmlLink": "https://calendar.google.com/event?eid=xyz",
            "visibility": "default",
        }
        e.update(overrides)
        return e

    def test_passes_event_with_external_attendee(self):
        from scripts.lib.workspace_client import format_calendar_event_for_log
        result = format_calendar_event_for_log(self._event(), "glen@iugo.com.au")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "evt-001")
        self.assertEqual(result["summary"], "Sync with PCA")
        self.assertEqual(result["html_link"], "https://calendar.google.com/event?eid=xyz")

    def test_filters_private_visibility(self):
        from scripts.lib.workspace_client import format_calendar_event_for_log
        result = format_calendar_event_for_log(
            self._event(visibility="private"), "glen@iugo.com.au")
        self.assertIsNone(result)

    def test_filters_no_external_attendees(self):
        from scripts.lib.workspace_client import format_calendar_event_for_log
        all_internal = self._event(attendees=[
            {"email": "glen@iugo.com.au"},
            {"email": "anyone@iugo.com.au"},
        ])
        result = format_calendar_event_for_log(all_internal, "glen@iugo.com.au")
        self.assertIsNone(result)

    def test_filters_mass_attendees(self):
        """D-D2: 26 attendees → filtered."""
        from scripts.lib.workspace_client import format_calendar_event_for_log
        many = self._event(attendees=[
            {"email": f"u{i}@external.com"} for i in range(26)
        ])
        result = format_calendar_event_for_log(many, "glen@iugo.com.au")
        self.assertIsNone(result)

    def test_filters_25_attendees_passes(self):
        """D-D2 boundary: exactly 25 → passes."""
        from scripts.lib.workspace_client import format_calendar_event_for_log
        exactly_25 = self._event(attendees=[
            {"email": f"u{i}@external.com"} for i in range(25)
        ])
        result = format_calendar_event_for_log(exactly_25, "glen@iugo.com.au")
        self.assertIsNotNone(result)

    def test_passes_with_one_external(self):
        """D-D1 boundary: 24 internal + 1 external → passes."""
        from scripts.lib.workspace_client import format_calendar_event_for_log
        mostly_internal = self._event(attendees=[
            {"email": f"u{i}@iugo.com.au"} for i in range(24)
        ] + [{"email": "external@otaus.com.au"}])
        result = format_calendar_event_for_log(mostly_internal, "glen@iugo.com.au")
        self.assertIsNotNone(result)

    def test_handles_missing_summary(self):
        from scripts.lib.workspace_client import format_calendar_event_for_log
        no_title = self._event(summary=None)
        result = format_calendar_event_for_log(no_title, "glen@iugo.com.au")
        self.assertEqual(result["summary"], "(no title)")

    def test_handles_date_only_start(self):
        from scripts.lib.workspace_client import format_calendar_event_for_log
        date_only = self._event(start={"date": "2026-05-15"})
        result = format_calendar_event_for_log(date_only, "glen@iugo.com.au")
        self.assertEqual(result["start_dt"], "2026-05-15")

    def test_carries_id_for_dedup(self):
        """Pitfall 4: event ID is the stable dedup key in _gather_events (Wave 2)."""
        from scripts.lib.workspace_client import format_calendar_event_for_log
        result = format_calendar_event_for_log(
            self._event(id="stable-google-event-id-xyz"), "glen@iugo.com.au")
        self.assertEqual(result["id"], "stable-google-event-id-xyz")


class TestDriveFileAdapter(unittest.TestCase):
    """Phase 12 D-D3 — format_drive_file_for_log."""

    def _file(self, **overrides) -> dict:
        f = {
            "id": "file-001",
            "name": "Proposal-PCA-v3.docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "modifiedTime": "2026-05-01T14:00:00Z",
            "webViewLink": "https://docs.google.com/document/d/xyz/edit",
            "lastModifyingUser": {"displayName": "Glen Rosie",
                                  "emailAddress": "glen@iugo.com.au"},
            "trashed": False,
            "parents": ["root"],
        }
        f.update(overrides)
        return f

    def test_passes_normal_file(self):
        from scripts.lib.workspace_client import format_drive_file_for_log
        result = format_drive_file_for_log(self._file())
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "file-001")
        self.assertEqual(result["name"], "Proposal-PCA-v3.docx")
        self.assertEqual(result["last_modifying_user"]["displayName"], "Glen Rosie")

    def test_filters_trashed(self):
        from scripts.lib.workspace_client import format_drive_file_for_log
        result = format_drive_file_for_log(self._file(trashed=True))
        self.assertIsNone(result)

    def test_filters_gdraft_extension(self):
        from scripts.lib.workspace_client import format_drive_file_for_log
        result = format_drive_file_for_log(self._file(name="Notes.gdraft"))
        self.assertIsNone(result)

    def test_filters_draft_token_in_name(self):
        """D-D3 case-sensitive — exact match for `[DRAFT]` token."""
        from scripts.lib.workspace_client import format_drive_file_for_log
        result = format_drive_file_for_log(self._file(name="My [DRAFT] document.docx"))
        self.assertIsNone(result)

    def test_passes_lowercase_draft_in_name(self):
        """D-D3 is case-sensitive: lowercase `[draft]` is NOT filtered."""
        from scripts.lib.workspace_client import format_drive_file_for_log
        result = format_drive_file_for_log(self._file(name="my [draft] doc.docx"))
        self.assertIsNotNone(result)

    def test_handles_missing_last_modifying_user(self):
        from scripts.lib.workspace_client import format_drive_file_for_log
        result = format_drive_file_for_log(self._file(lastModifyingUser=None))
        self.assertEqual(result["last_modifying_user"], {})

    def test_carries_id_for_dedup(self):
        from scripts.lib.workspace_client import format_drive_file_for_log
        result = format_drive_file_for_log(self._file(id="stable-drive-file-id-xyz"))
        self.assertEqual(result["id"], "stable-drive-file-id-xyz")


class TestOAuthTokenLoader(unittest.TestCase):
    """Phase 12: OAuth blob read + refresh flow."""

    def _write_creds(self, dir_path: Path, email: str, expiry_iso: str,
                      token: str = "stored_access") -> Path:
        path = dir_path / f"{email}.json"
        path.write_text(json.dumps({
            "token": token,
            "refresh_token": "rt_xxx",
            "client_id": "cid",
            "client_secret": "csec",
            "expiry": expiry_iso,
        }), encoding="utf-8")
        return path

    @patch("scripts.lib.workspace_client.urllib.request.urlopen")
    def test_load_credentials_returns_existing_token_when_not_expiring(self, mock_urlopen):
        from scripts.lib.workspace_client import _load_workspace_credentials
        from datetime import datetime, timezone, timedelta
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            far_future = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            self._write_creds(Path(d), "glen@iugo.com.au", far_future, token="fresh_token")
            with mock.patch.dict(os.environ, {"GOOGLE_MCP_CREDENTIALS_DIR": d,
                                              "GOOGLE_PRIMARY_EMAIL": "glen@iugo.com.au"}):
                token = _load_workspace_credentials()
            self.assertEqual(token, "fresh_token")
            mock_urlopen.assert_not_called()

    @patch("scripts.lib.workspace_client.urllib.request.urlopen")
    def test_load_credentials_refreshes_when_expiring_soon(self, mock_urlopen):
        from scripts.lib.workspace_client import _load_workspace_credentials
        from datetime import datetime, timezone, timedelta
        import tempfile
        # Mock refresh response
        m = MagicMock()
        m.read.return_value = json.dumps({
            "access_token": "REFRESHED_ACCESS",
            "expires_in": 3600,
            "scope": "x", "token_type": "Bearer",
        }).encode("utf-8")
        m.__enter__ = lambda self_: m
        m.__exit__ = lambda self_, *args: False
        mock_urlopen.return_value = m
        with tempfile.TemporaryDirectory() as d:
            soon = (datetime.now(timezone.utc) + timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
            self._write_creds(Path(d), "glen@iugo.com.au", soon, token="OLD_ACCESS")
            with mock.patch.dict(os.environ, {"GOOGLE_MCP_CREDENTIALS_DIR": d,
                                              "GOOGLE_PRIMARY_EMAIL": "glen@iugo.com.au"}):
                token = _load_workspace_credentials()
            self.assertEqual(token, "REFRESHED_ACCESS")
            mock_urlopen.assert_called_once()
            # Verify the request was POSTed to the OAuth endpoint
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.get_method(), "POST")
            self.assertIn("oauth2.googleapis.com/token", req.full_url)

    def test_load_credentials_raises_on_missing_file(self):
        from scripts.lib.workspace_client import (
            _load_workspace_credentials, WorkspaceTransportError,
        )
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(os.environ, {"GOOGLE_MCP_CREDENTIALS_DIR": d,
                                              "GOOGLE_PRIMARY_EMAIL": "missing@example.com"}):
                with self.assertRaises(WorkspaceTransportError) as ctx:
                    _load_workspace_credentials()
                self.assertIn("credentials missing", str(ctx.exception))

    @patch("scripts.lib.workspace_client.urllib.request.urlopen")
    def test_load_credentials_raises_on_refresh_failure(self, mock_urlopen):
        from scripts.lib.workspace_client import (
            _load_workspace_credentials, WorkspaceTransportError,
        )
        from datetime import datetime, timezone, timedelta
        import tempfile
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="x", code=400, msg="invalid_grant", hdrs={}, fp=None,
        )
        with tempfile.TemporaryDirectory() as d:
            soon = (datetime.now(timezone.utc) + timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
            self._write_creds(Path(d), "glen@iugo.com.au", soon)
            with mock.patch.dict(os.environ, {"GOOGLE_MCP_CREDENTIALS_DIR": d,
                                              "GOOGLE_PRIMARY_EMAIL": "glen@iugo.com.au"}):
                with self.assertRaises(WorkspaceTransportError) as ctx:
                    _load_workspace_credentials()
                self.assertIn("credentials refresh failed", str(ctx.exception))


class TestDriveWalker(unittest.TestCase):
    """Phase 12 D-A3-REVISED: _walk_drive_for_clients single-call list with D-D3 filter applied."""

    @patch("scripts.lib.workspace_client._workspace_get")
    def test_walk_drive_returns_filtered_files(self, mock_get):
        from scripts.lib.workspace_client import _walk_drive_for_clients
        mock_get.return_value = {
            "files": [
                {"id": "f1", "name": "Proposal.docx", "mimeType": "application/x",
                 "modifiedTime": "2026-05-01T10:00:00Z",
                 "webViewLink": "https://docs.google.com/d/f1",
                 "lastModifyingUser": {"displayName": "Glen"},
                 "trashed": False, "parents": ["root"]},
                {"id": "f2", "name": "Notes.gdraft", "mimeType": "application/x",
                 "modifiedTime": "2026-05-02T10:00:00Z", "webViewLink": "x",
                 "lastModifyingUser": {}, "trashed": False, "parents": ["root"]},
                {"id": "f3", "name": "Deleted.docx", "mimeType": "application/x",
                 "modifiedTime": "2026-05-03T10:00:00Z", "webViewLink": "x",
                 "lastModifyingUser": {}, "trashed": True, "parents": ["root"]},
            ]
        }
        result = _walk_drive_for_clients("test_token")
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(result["files"][0]["id"], "f1")
        self.assertEqual(result["files"][0]["name"], "Proposal.docx")

    @patch("scripts.lib.workspace_client._workspace_get")
    def test_walk_drive_passes_required_fields_query_param(self, mock_get):
        from scripts.lib.workspace_client import _walk_drive_for_clients
        mock_get.return_value = {"files": []}
        _walk_drive_for_clients("test_token")
        # Verify the params dict passed to _workspace_get
        api_path, params, token = mock_get.call_args[0]
        self.assertEqual(api_path, "drive/v3/files")
        self.assertIn("lastModifyingUser", params["fields"])
        self.assertEqual(params["orderBy"], "modifiedTime desc")
        self.assertIn("trashed=false", params["q"])
        self.assertIn("application/vnd.google-apps.folder", params["q"])

    @patch("scripts.lib.workspace_client._workspace_get")
    def test_walk_drive_handles_empty_response(self, mock_get):
        from scripts.lib.workspace_client import _walk_drive_for_clients
        mock_get.return_value = {"files": []}
        result = _walk_drive_for_clients("test_token")
        self.assertEqual(result, {"files": []})


class TestWorkspaceClientEndpointAllowlist(unittest.TestCase):
    """Trust-boundary verification (D-X1): workspace_client.py only references
    allowlisted Google API endpoints. CI catches accidental write paths
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
        """Defensive: scan for any HTTP verb that isn't GET. workspace_client
        is read-only by construction.

        Carve-out: the OAuth POST in `_refresh_workspace_token` to
        oauth2.googleapis.com/token is the SOLE write call. The line is marked
        with `# OAUTH-POST:` to make it greppable; this test skips that line.
        """
        from scripts.lib import workspace_client
        source = Path(workspace_client.__file__).read_text(encoding="utf-8")
        for verb in ("POST", "PUT", "PATCH", "DELETE"):
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                if "OAUTH-POST:" in line:
                    continue  # documented carve-out
                self.assertNotIn(
                    f'method="{verb}"', line,
                    f"workspace_client.py:{i}: found method={verb!r} on line "
                    f"{line.strip()!r} — this module is read-only by construction; "
                    f"add an OAUTH-POST: comment marker if this is a documented carve-out",
                )


if __name__ == "__main__":
    unittest.main()
