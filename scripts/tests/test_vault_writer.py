"""Phase 10 — Obsidian sync layer unit tests.

These tests are RED until Plan 02 implements scripts/lib/vault_writer.py.
Run: python3 -m unittest discover scripts/tests
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestSlugify(unittest.TestCase):
    """D-06: deterministic slug; collision suffix; empty fallback. Pattern 5."""

    def test_basic_kebab_case(self):
        from scripts.lib.vault_writer import slugify
        self.assertEqual(slugify("Property Council Australia"), "property-council-australia")

    def test_punctuation_collapsed(self):
        from scripts.lib.vault_writer import slugify
        self.assertEqual(slugify("Co-op & Sons, LLC."), "co-op-sons-llc")

    def test_nfkd_ascii_fold(self):
        from scripts.lib.vault_writer import slugify
        self.assertEqual(slugify("Société Générale"), "societe-generale")

    def test_all_non_ascii_returns_empty(self):
        from scripts.lib.vault_writer import slugify
        # Pure non-ASCII glyphs strip to empty after NFKD + ASCII encode.
        self.assertEqual(slugify("日本企業"), "")

    def test_safe_slugify_falls_back_to_domain(self):
        from scripts.lib.vault_writer import safe_slugify
        self.assertEqual(safe_slugify("日本企業", "nihon.co.jp"), "nihon-co-jp")

    def test_collision_form(self):
        from scripts.lib.vault_writer import slug_with_domain
        self.assertEqual(
            slug_with_domain("Acme Corp", "acme.com"),
            "acme-corp--acme-com",
        )


class TestReplaceManagedSection(unittest.TestCase):
    """D-08: marker-bounded splice preserves outside content. Pattern 1."""

    def _make_note(self, body: str) -> Path:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        tmp.write(body)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return Path(tmp.name)

    def test_replaces_only_inside_markers(self):
        from scripts.lib.vault_writer import replace_managed_section
        path = self._make_note(
            "# Title\n\nGlen wrote this overview.\n\n"
            "<!-- ACTIVITY-LOG-START -->\nold content\n<!-- ACTIVITY-LOG-END -->\n\n"
            "## Decisions\n\nGlen wrote decisions.\n"
        )
        replace_managed_section(path, "ACTIVITY-LOG", "new entry")
        after = path.read_text(encoding="utf-8")
        self.assertIn("Glen wrote this overview.", after)
        self.assertIn("Glen wrote decisions.", after)
        self.assertIn("new entry", after)
        self.assertNotIn("old content", after)

    def test_atomic_write_no_partial_state(self):
        """Pattern 1: temp+rename means target file is either old or new, never partial."""
        from scripts.lib.vault_writer import replace_managed_section
        path = self._make_note(
            "<!-- ACTIVITY-LOG-START -->\nold\n<!-- ACTIVITY-LOG-END -->\n"
        )
        replace_managed_section(path, "ACTIVITY-LOG", "fresh")
        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("fresh", content)
        self.assertNotIn("old", content)


class TestMarkerError(unittest.TestCase):
    """D-08a: missing/duplicate/malformed markers ABORT update."""

    def _make_note(self, body: str) -> Path:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        tmp.write(body)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return Path(tmp.name)

    def test_missing_start_marker_raises(self):
        from scripts.lib.vault_writer import replace_managed_section, MarkerError
        path = self._make_note("body without markers\n")
        with self.assertRaises(MarkerError):
            replace_managed_section(path, "ACTIVITY-LOG", "x")

    def test_missing_end_marker_raises(self):
        from scripts.lib.vault_writer import replace_managed_section, MarkerError
        path = self._make_note("<!-- ACTIVITY-LOG-START -->\nx\n")
        with self.assertRaises(MarkerError):
            replace_managed_section(path, "ACTIVITY-LOG", "x")

    def test_duplicate_start_raises(self):
        from scripts.lib.vault_writer import replace_managed_section, MarkerError
        path = self._make_note(
            "<!-- ACTIVITY-LOG-START -->\nx\n<!-- ACTIVITY-LOG-START -->\n"
            "y\n<!-- ACTIVITY-LOG-END -->\n"
        )
        with self.assertRaises(MarkerError):
            replace_managed_section(path, "ACTIVITY-LOG", "z")

    def test_end_before_start_raises(self):
        from scripts.lib.vault_writer import replace_managed_section, MarkerError
        path = self._make_note(
            "<!-- ACTIVITY-LOG-END -->\nx\n<!-- ACTIVITY-LOG-START -->\n"
        )
        with self.assertRaises(MarkerError):
            replace_managed_section(path, "ACTIVITY-LOG", "y")

    def test_marker_error_logs_critical_feed_entry(self):
        """D-08a: ABORT path writes a system/critical entry to data/feed.jsonl."""
        from scripts.lib.vault_writer import handle_marker_error_for_feed
        entry = handle_marker_error_for_feed(
            file_path=Path("vault-build/Clients/_test_.md"),
            section="ACTIVITY-LOG",
            reason="expected exactly 1 ACTIVITY-LOG-END marker, got 0",
        )
        self.assertEqual(entry["type"], "system")
        self.assertEqual(entry["level"], "critical")
        self.assertEqual(entry["trigger"], "hook")
        self.assertIn("ACTIVITY-LOG", entry["summary"])
        self.assertIn("file", entry["details"])


class TestRenderLogLine(unittest.TestCase):
    """D-12: ### [YYYY-MM-DD HH:MM] {emoji} {summary}; emojis per kind."""

    def test_triage_uses_email_emoji(self):
        from scripts.lib.vault_writer import render_log_line
        line = render_log_line(
            rec_ts_iso="2026-05-01T10:30:00+10:30",
            kind="triage",
            summary="Greg Davenport — SOW review",
        )
        self.assertTrue(line.startswith("### [2026-05-01 10:30] 📧 Greg Davenport — SOW review"))

    def test_task_uses_check_emoji(self):
        from scripts.lib.vault_writer import render_log_line
        line = render_log_line(
            rec_ts_iso="2026-05-01T11:42:00+10:30",
            kind="task",
            summary="task-2026-05-01-003 completed",
        )
        self.assertIn("✅", line)
        self.assertIn("[2026-05-01 11:42]", line)

    def test_invoice_uses_money_emoji(self):
        from scripts.lib.vault_writer import render_log_line
        line = render_log_line(
            rec_ts_iso="2026-04-28T14:00:00+10:30",
            kind="invoice",
            summary="inv-2026-04-28-002 marked paid",
        )
        self.assertIn("💰", line)

    def test_optional_detail_block(self):
        from scripts.lib.vault_writer import render_log_line
        line = render_log_line(
            rec_ts_iso="2026-05-01T10:30:00+10:30",
            kind="triage",
            summary="x",
            detail="needs-response · contract review",
        )
        self.assertIn("> needs-response · contract review", line)

    def test_optional_gmail_thread_link(self):
        from scripts.lib.vault_writer import render_log_line
        line = render_log_line(
            rec_ts_iso="2026-05-01T10:30:00+10:30",
            kind="triage",
            summary="x",
            gmail_thread_id="19d17c8f98f99484",
        )
        self.assertIn(
            "https://mail.google.com/mail/u/0/#inbox/19d17c8f98f99484",
            line,
        )


class TestBackfillIdempotent(unittest.TestCase):
    """D-14, D-16: regenerate-from-full produces byte-identical managed sections (modulo last_synced)."""

    def test_two_runs_identical_managed_content(self):
        """Plan 02's run_backfill must produce byte-identical managed-section content twice in a row.
        Excludes the last_synced frontmatter line which always changes.
        """
        from scripts.lib.vault_writer import run_backfill
        with tempfile.TemporaryDirectory() as build_dir, tempfile.TemporaryDirectory() as data_dir:
            # Minimal data fixture: one client, no records → stub note path (D-15a).
            config_dir = Path(data_dir) / "config"
            config_dir.mkdir()
            (config_dir / "clients.jsonl").write_text(
                '{"domain": "example.com", "name": "Example", "aliases": [], "contact": "Test"}\n',
                encoding="utf-8",
            )
            # Empty triage/tasks/invoices/todos directories.
            for sub in ("triage", "tasks", "invoices", "todos"):
                (Path(data_dir) / sub).mkdir()

            # Run backfill twice
            run_backfill(data_root=Path(data_dir), build_root=Path(build_dir))
            first = self._snapshot_managed(Path(build_dir))
            run_backfill(data_root=Path(data_dir), build_root=Path(build_dir))
            second = self._snapshot_managed(Path(build_dir))
            self.assertEqual(first, second)

    def _snapshot_managed(self, build_root: Path) -> dict:
        """Read each .md and strip last_synced line for comparison."""
        out = {}
        for md in sorted((build_root / "Clients").glob("*.md")):
            lines = md.read_text(encoding="utf-8").splitlines()
            # Drop any line beginning with 'last_synced:' inside frontmatter
            filtered = [ln for ln in lines if not ln.startswith("last_synced:")]
            out[md.name] = "\n".join(filtered)
        return out


class TestMain(unittest.TestCase):
    """Issue 1 audit-trail isolation — main() failure-path MUST NOT pollute production data/feed.jsonl."""

    def test_main_failure_path_writes_critical_feed_to_temp(self):
        """Failure-path test: invoke main() with a bogus --data-root so backfill raises;
        the resulting critical feed entry MUST land in a TEMP --feed-path, NEVER in
        the production data/feed.jsonl. This protects D-08a feed-entry trust per
        CLAUDE.md single-writer / Glen-owned audit-trail constraint.

        Plan 02 Task 2 activates this test by:
          1. Adding `--feed-path` to main()'s argparse (default: <repo_root>/data/feed.jsonl).
          2. Threading feed_path through run_backfill / run_incremental.
          3. Removing the @unittest.skip decorator above.
        """
        with tempfile.TemporaryDirectory() as build_dir, \
             tempfile.TemporaryDirectory() as data_dir, \
             tempfile.TemporaryDirectory() as feed_dir:
            feed_path = Path(feed_dir) / "data" / "feed.jsonl"
            feed_path.parent.mkdir(parents=True, exist_ok=True)
            # Run main() via subprocess to fully exercise argparse + exit-code path.
            # Use a non-existent --data-root so backfill explodes inside main()'s try/except.
            proc = subprocess.run(
                [
                    sys.executable, "-m", "scripts.lib.vault_writer",
                    "--mode", "backfill",
                    "--data-root", "/nonexistent-issue1-isolation",
                    "--build-root", str(build_dir),
                    "--feed-path", str(feed_path),
                ],
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).resolve().parents[2]),  # repo root
            )
            # Failure expected (exit 1)
            self.assertNotEqual(proc.returncode, 0,
                f"expected non-zero exit; stdout={proc.stdout!r} stderr={proc.stderr!r}")
            # Critical feed entry MUST be in the temp --feed-path
            self.assertTrue(feed_path.exists(),
                f"expected feed entry at {feed_path}; stderr={proc.stderr!r}")
            contents = feed_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertGreaterEqual(len(contents), 1)
            import json as _json
            entry = _json.loads(contents[-1])
            self.assertEqual(entry["type"], "system")
            self.assertEqual(entry["level"], "critical")


class TestProjection(unittest.TestCase):
    """Plan 04: D-03 projection from vault-build/ to iCloud canonical vault.

    Covers:
    - Pitfall 6 first-time create
    - D-08a target-side marker abort
    - Issue 4 source-side marker abort (parity with target-side)
    - Issue 5 strict dry-run (no brctl invocation)
    """

    def test_first_time_creates_new_file(self):
        """Pitfall 6: first projection of a new client — write full template, skip marker check."""
        from scripts.lib.vault_writer import run_projection
        with tempfile.TemporaryDirectory() as build, \
             tempfile.TemporaryDirectory() as icloud, \
             tempfile.TemporaryDirectory() as feed_dir:
            source_dir = Path(build) / "Clients"
            source_dir.mkdir()
            source = source_dir / "test-client.md"
            source.write_text(
                "---\ndomain: test.example\nclient_name: Test\nstatus: active\n"
                "last_synced: 2026-05-01T10:30:00+10:30\n---\n\n"
                "## Overview\n\n_x_\n\n"
                "<!-- OPEN-ITEMS-START -->\n## Open Items\n\n_(none)_\n<!-- OPEN-ITEMS-END -->\n\n"
                "<!-- ACTIVITY-LOG-START -->\n## Activity Log\n\n_x_\n<!-- ACTIVITY-LOG-END -->\n\n"
                "## Decisions\n\n_x_\n",
                encoding="utf-8",
            )
            feed_path = Path(feed_dir) / "feed.jsonl"
            stats = run_projection(Path(build), Path(icloud),
                                   dry_run=False, feed_path=feed_path)
            self.assertEqual(stats["created_new"], 1)
            self.assertTrue((Path(icloud) / "Clients" / "test-client.md").exists())

    def test_existing_target_marker_error_aborts(self):
        """D-08a: malformed markers in iCloud target ABORT and log critical, no overwrite."""
        from scripts.lib.vault_writer import run_projection
        with tempfile.TemporaryDirectory() as build, \
             tempfile.TemporaryDirectory() as icloud, \
             tempfile.TemporaryDirectory() as feed_dir:
            # Set up build/Clients/foo.md with valid markers
            source_dir = Path(build) / "Clients"
            source_dir.mkdir(parents=True)
            source = source_dir / "foo.md"
            source.write_text(
                "<!-- ACTIVITY-LOG-START -->\nnew-content\n<!-- ACTIVITY-LOG-END -->\n"
                "<!-- OPEN-ITEMS-START -->\nopen\n<!-- OPEN-ITEMS-END -->\n",
                encoding="utf-8",
            )
            # Set up iCloud/Clients/foo.md with MISSING ACTIVITY-LOG-END (corrupt)
            target_dir = Path(icloud) / "Clients"
            target_dir.mkdir(parents=True)
            target = target_dir / "foo.md"
            target.write_text(
                "## Overview\nuser content\n\n"
                "<!-- OPEN-ITEMS-START -->\nold-open\n<!-- OPEN-ITEMS-END -->\n"
                "<!-- ACTIVITY-LOG-START -->\nold\n",  # missing END
                encoding="utf-8",
            )

            feed_path = Path(feed_dir) / "feed.jsonl"
            stats = run_projection(Path(build), Path(icloud),
                                   dry_run=False, feed_path=feed_path)
            self.assertGreaterEqual(stats["skipped_marker_error"], 1)
            # Verify user content was preserved (NOT overwritten)
            self.assertIn("user content", target.read_text(encoding="utf-8"))
            # Verify a critical feed entry was written to the temp feed_path
            self.assertTrue(feed_path.exists())

    def test_corrupt_source_marker_aborts_with_critical_feed(self):
        """Issue 4: source-side marker corruption is treated with the same severity as
        target-side. A malformed <!-- ACTIVITY-LOG-START --> block in
        vault-build/Clients/foo.md must abort that file's projection and write a
        critical feed entry to the threaded feed_path.
        """
        import json as _json
        from scripts.lib.vault_writer import run_projection
        with tempfile.TemporaryDirectory() as build, \
             tempfile.TemporaryDirectory() as icloud, \
             tempfile.TemporaryDirectory() as feed_dir:
            source_dir = Path(build) / "Clients"
            source_dir.mkdir(parents=True)
            source = source_dir / "foo.md"
            # SOURCE corrupted: TWO ACTIVITY-LOG-START markers and ONE END.
            source.write_text(
                "<!-- ACTIVITY-LOG-START -->\nfirst\n<!-- ACTIVITY-LOG-START -->\n"
                "second\n<!-- ACTIVITY-LOG-END -->\n"
                "<!-- OPEN-ITEMS-START -->\nopen\n<!-- OPEN-ITEMS-END -->\n",
                encoding="utf-8",
            )
            # iCloud target exists with valid markers (so source is the broken side)
            target_dir = Path(icloud) / "Clients"
            target_dir.mkdir(parents=True)
            target = target_dir / "foo.md"
            target.write_text(
                "<!-- OPEN-ITEMS-START -->\nold-open\n<!-- OPEN-ITEMS-END -->\n"
                "<!-- ACTIVITY-LOG-START -->\nold\n<!-- ACTIVITY-LOG-END -->\n",
                encoding="utf-8",
            )
            feed_path = Path(feed_dir) / "feed.jsonl"
            stats = run_projection(Path(build), Path(icloud),
                                   dry_run=False, feed_path=feed_path)
            # File aborted — counted under skipped_marker_error
            self.assertGreaterEqual(stats["skipped_marker_error"], 1)
            # Critical feed entry written to the temp feed_path
            self.assertTrue(feed_path.exists())
            lines = feed_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertGreaterEqual(len(lines), 1)
            entry = _json.loads(lines[-1])
            self.assertEqual(entry["type"], "system")
            self.assertEqual(entry["level"], "critical")
            # Source path appears in the entry (not target)
            self.assertIn("foo.md", entry["details"]["file"])

    def test_second_projection_preserves_user_content(self):
        """Regression (post-review fix): Glen's user-edited Overview and Decisions
        in the iCloud target MUST survive a subsequent projection from vault-build/.
        Only the managed sections (OPEN-ITEMS, ACTIVITY-LOG) should change.

        Without this test, a future refactor of run_projection that accidentally
        rewrites the whole file (e.g. always taking the source-as-truth path
        instead of just splicing managed sections) would silently destroy Glen's
        notes — the highest-impact data-loss risk in Phase 10.
        """
        from scripts.lib.vault_writer import run_projection
        with tempfile.TemporaryDirectory() as build, \
             tempfile.TemporaryDirectory() as icloud, \
             tempfile.TemporaryDirectory() as feed_dir:
            # vault-build source: regenerated-from-full template content
            source_dir = Path(build) / "Clients"
            source_dir.mkdir()
            source = source_dir / "test-client.md"
            source.write_text(
                "---\ndomain: test.example\nclient_name: Test\nstatus: active\n"
                "last_synced: 2026-05-01T10:30:00+10:30\n---\n\n"
                "## Overview\n\n_template Overview placeholder_\n\n"
                "<!-- OPEN-ITEMS-START -->\nUPDATED-OPEN-ITEMS\n<!-- OPEN-ITEMS-END -->\n\n"
                "<!-- ACTIVITY-LOG-START -->\nUPDATED-ACTIVITY-LOG\n<!-- ACTIVITY-LOG-END -->\n\n"
                "## Decisions\n\n_template Decisions placeholder_\n",
                encoding="utf-8",
            )
            # iCloud target: Glen has heavily edited Overview and Decisions on iPhone
            target_dir = Path(icloud) / "Clients"
            target_dir.mkdir()
            target = target_dir / "test-client.md"
            target.write_text(
                "---\ndomain: test.example\nclient_name: Test\nstatus: active\n"
                "last_synced: 2026-04-30T10:30:00+10:30\n"
                "glen_added_field: my-custom-value\n---\n\n"
                "## Overview\n\n"
                "GLEN-CUSTOM-OVERVIEW: annual contract renewed Mar 2026, "
                "primary contact Sarah K., billing on net-30.\n\n"
                "<!-- OPEN-ITEMS-START -->\nold-open-items-content\n<!-- OPEN-ITEMS-END -->\n\n"
                "<!-- ACTIVITY-LOG-START -->\nold-activity-log-content\n<!-- ACTIVITY-LOG-END -->\n\n"
                "## Decisions\n\n"
                "GLEN-CUSTOM-DECISION: moved to monthly invoicing 2026-04 per Sarah's request.\n",
                encoding="utf-8",
            )
            feed_path = Path(feed_dir) / "feed.jsonl"
            stats = run_projection(Path(build), Path(icloud),
                                   dry_run=False, feed_path=feed_path)
            self.assertEqual(stats["projected"], 1)
            self.assertEqual(stats["created_new"], 0)
            self.assertEqual(stats["skipped_marker_error"], 0)

            after = target.read_text(encoding="utf-8")
            # Glen's user-edited Overview and Decisions MUST be preserved verbatim
            self.assertIn("GLEN-CUSTOM-OVERVIEW", after)
            self.assertIn("annual contract renewed Mar 2026", after)
            self.assertIn("primary contact Sarah K.", after)
            self.assertIn("GLEN-CUSTOM-DECISION", after)
            self.assertIn("moved to monthly invoicing 2026-04", after)
            # Glen's custom frontmatter field MUST survive ruamel round-trip
            self.assertIn("glen_added_field: my-custom-value", after)
            # Managed sections MUST be replaced with source content
            self.assertIn("UPDATED-OPEN-ITEMS", after)
            self.assertIn("UPDATED-ACTIVITY-LOG", after)
            self.assertNotIn("old-open-items-content", after)
            self.assertNotIn("old-activity-log-content", after)
            # The template-only Overview text from source MUST NOT have been written to target
            self.assertNotIn("_template Overview placeholder_", after)
            self.assertNotIn("_template Decisions placeholder_", after)

    def test_dry_run_does_not_invoke_brctl(self):
        """Issue 5: dry_run is STRICTLY read-only — no brctl subprocess invocations."""
        from unittest import mock
        from scripts.lib.vault_writer import run_projection
        with tempfile.TemporaryDirectory() as build, \
             tempfile.TemporaryDirectory() as icloud, \
             tempfile.TemporaryDirectory() as feed_dir:
            source_dir = Path(build) / "Clients"
            source_dir.mkdir(parents=True)
            source = source_dir / "foo.md"
            source.write_text(
                "<!-- OPEN-ITEMS-START -->\nopen\n<!-- OPEN-ITEMS-END -->\n"
                "<!-- ACTIVITY-LOG-START -->\nnew\n<!-- ACTIVITY-LOG-END -->\n",
                encoding="utf-8",
            )
            # Create an .icloud placeholder in icloud/Clients to simulate
            # iCloud Optimize-Mac-Storage. Without dry_run, run_projection would
            # invoke brctl. With dry_run, it MUST NOT.
            target_dir = Path(icloud) / "Clients"
            target_dir.mkdir(parents=True)
            placeholder = target_dir / ".foo.md.icloud"
            placeholder.write_text("", encoding="utf-8")

            feed_path = Path(feed_dir) / "feed.jsonl"

            # Patch subprocess.run inside the vault_writer module so we can assert
            # it is never called during a dry-run projection.
            with mock.patch("scripts.lib.vault_writer.subprocess.run") as mock_run:
                run_projection(Path(build), Path(icloud),
                               dry_run=True, feed_path=feed_path)
                # Issue 5: brctl MUST NOT have been invoked.
                for call in mock_run.call_args_list:
                    # call.args[0] is the argv list passed to subprocess.run.
                    argv = call.args[0] if call.args else []
                    self.assertFalse(
                        argv and argv[0] == "brctl",
                        f"brctl invoked under dry_run: {argv}",
                    )


class TestRenderFrontmatterPhase11(unittest.TestCase):
    """Phase 11: render_frontmatter extension with cm_extra + cm_stale_since kwargs.

    Backwards compatibility (Phase 10 callers passing only client + last_synced) MUST
    produce byte-identical output to the Phase 10 implementation. The new kwargs
    default to None and are purely additive.
    """

    def _client(self):
        return {"domain": "example.com", "client_name": "Example", "status": "active"}

    def test_render_frontmatter_no_cm_extra_unchanged(self):
        from scripts.lib.vault_writer import render_frontmatter
        out = render_frontmatter(self._client(), "2026-05-02T10:30:00+10:30")
        # Phase 10 four keys present
        self.assertIn("domain: example.com", out)
        self.assertIn("client_name: Example", out)
        self.assertIn("status: active", out)
        self.assertIn("last_synced:", out)
        # No CM keys
        self.assertNotIn("deployed_modules", out)
        self.assertNotIn("contract_start", out)
        self.assertNotIn("sites", out)
        self.assertNotIn("cm_data_stale_since", out)

    def test_render_frontmatter_with_cm_extra_appends_five_keys(self):
        from scripts.lib.vault_writer import render_frontmatter
        cm_extra = {
            "deployed_modules": ["AMS Core"],
            "contract_start": "2026-01-01",
            "contract_end": "2027-01-01",
            "primary_contact": "Alice",
            "sites": [],
        }
        out = render_frontmatter(self._client(), "2026-05-02T10:30:00+10:30",
                                 cm_extra=cm_extra)
        for key in ("contract_start", "contract_end", "primary_contact",
                    "deployed_modules", "sites"):
            self.assertIn(key, out)
        # Phase 10 keys still come first (sanity check on ordering)
        self.assertLess(out.index("last_synced"), out.index("contract_start"))

    def test_render_frontmatter_with_cm_stale_since_appended_last(self):
        from scripts.lib.vault_writer import render_frontmatter
        out = render_frontmatter(self._client(), "2026-05-02T10:30:00+10:30",
                                 cm_extra={}, cm_stale_since="2026-05-01T12:00:00+10:30")
        self.assertIn("cm_data_stale_since", out)
        self.assertIn("2026-05-01T12:00:00+10:30", out)

    def test_render_frontmatter_empty_scalars_render_as_empty_strings(self):
        from scripts.lib.vault_writer import render_frontmatter
        cm_extra = {
            "deployed_modules": [],
            "contract_start": "",
            "contract_end": "",
            "primary_contact": "",
            "sites": [],
        }
        out = render_frontmatter(self._client(), "2026-05-02T10:30:00+10:30",
                                 cm_extra=cm_extra)
        # D-B1: empty scalar → ''. ruamel.yaml may emit "''" or '""' for empty string.
        # The crucial invariant is: NO 'null' or '~' tokens for these fields.
        for key in ("contract_start", "contract_end", "primary_contact"):
            self.assertIn(f"{key}:", out)
        # D-B2: empty array → [] (or block style with no children).
        self.assertNotIn("null", out.lower())
        self.assertNotIn(": ~", out)

    def test_render_frontmatter_omits_cm_keys_when_extra_is_none(self):
        from scripts.lib.vault_writer import render_frontmatter
        out = render_frontmatter(self._client(), "2026-05-02T10:30:00+10:30",
                                 cm_extra=None)
        self.assertNotIn("deployed_modules", out)
        self.assertNotIn("sites", out)

    def test_render_frontmatter_omits_cm_stale_since_when_none(self):
        from scripts.lib.vault_writer import render_frontmatter
        out = render_frontmatter(self._client(), "2026-05-02T10:30:00+10:30",
                                 cm_stale_since=None)
        self.assertNotIn("cm_data_stale_since", out)


if __name__ == "__main__":
    unittest.main()
