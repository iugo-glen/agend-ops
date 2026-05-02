"""Phase 10 — Obsidian sync layer unit tests.

These tests are RED until Plan 02 implements scripts/lib/vault_writer.py.
Run: python3 -m unittest discover scripts/tests
"""
import json
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
        """Read each .md and strip last_synced + cm_data_stale_since lines for comparison.

        Phase 11 extension: also strip cm_data_stale_since since it is a
        cache-fallback signal that changes between runs depending on cache
        state (D-A3). The idempotency contract is "managed-section content
        is byte-identical modulo per-run trust signals".
        """
        out = {}
        for md in sorted((build_root / "Clients").glob("*.md")):
            lines = md.read_text(encoding="utf-8").splitlines()
            filtered = [ln for ln in lines
                        if not ln.startswith("last_synced:")
                        and not ln.startswith("cm_data_stale_since:")]
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
                "<!-- CM-TODOS-START -->\nUPDATED-CM-TODOS\n<!-- CM-TODOS-END -->\n\n"
                "<!-- OPEN-ITEMS-START -->\nUPDATED-OPEN-ITEMS\n<!-- OPEN-ITEMS-END -->\n\n"
                "<!-- USAGE-START -->\nUPDATED-USAGE\n<!-- USAGE-END -->\n\n"
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
                "<!-- CM-TODOS-START -->\nold-cm-todos-content\n<!-- CM-TODOS-END -->\n\n"
                "<!-- OPEN-ITEMS-START -->\nold-open-items-content\n<!-- OPEN-ITEMS-END -->\n\n"
                "<!-- USAGE-START -->\nold-usage-content\n<!-- USAGE-END -->\n\n"
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
            # Managed sections MUST be replaced with source content (all 4 per Phase 11 D-C1)
            self.assertIn("UPDATED-CM-TODOS", after)
            self.assertIn("UPDATED-OPEN-ITEMS", after)
            self.assertIn("UPDATED-USAGE", after)
            self.assertIn("UPDATED-ACTIVITY-LOG", after)
            self.assertNotIn("old-cm-todos-content", after)
            self.assertNotIn("old-open-items-content", after)
            self.assertNotIn("old-usage-content", after)
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


class TestRunMapCmClients(unittest.TestCase):
    """Phase 11 D-G1: idempotent mapping pass populates cm_client_id."""

    def _setup(self, d: Path) -> Path:
        config = d / "config"
        config.mkdir()
        (d / "feed.jsonl").touch()
        return config / "clients.jsonl"

    def test_map_cm_clients_writes_id_for_unmapped_domain(self):
        import unittest.mock as mock
        with tempfile.TemporaryDirectory() as d:
            data_root = Path(d)
            clients = self._setup(data_root)
            clients.write_text(
                '{"domain": "example.com", "name": "Ex"}\n',
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"CONTRACT_MANAGER_API_KEY": "test"}), \
                 mock.patch("scripts.lib.cm_client.search_clients_for_domain",
                            return_value=42):
                from scripts.lib.vault_writer import run_map_cm_clients
                stats = run_map_cm_clients(data_root, feed_path=data_root / "feed.jsonl")
            self.assertEqual(stats["mapped"], 1)
            written = clients.read_text(encoding="utf-8")
            self.assertIn('"cm_client_id": 42', written)
            self.assertIn('"domain": "example.com"', written)

    def test_map_cm_clients_idempotent_when_all_ids_present(self):
        import unittest.mock as mock
        with tempfile.TemporaryDirectory() as d:
            data_root = Path(d)
            clients = self._setup(data_root)
            clients.write_text(
                '{"domain": "ex.com", "name": "Ex", "cm_client_id": 5}\n',
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"CONTRACT_MANAGER_API_KEY": "test"}), \
                 mock.patch("scripts.lib.cm_client.search_clients_for_domain") as m_search:
                from scripts.lib.vault_writer import run_map_cm_clients
                stats = run_map_cm_clients(data_root, feed_path=data_root / "feed.jsonl")
            m_search.assert_not_called()
            self.assertEqual(stats["unchanged"], 1)
            self.assertEqual(stats["mapped"], 0)

    def test_map_cm_clients_continues_on_per_client_failure(self):
        import unittest.mock as mock
        from scripts.lib.cm_client import CmTransportError
        with tempfile.TemporaryDirectory() as d:
            data_root = Path(d)
            clients = self._setup(data_root)
            clients.write_text(
                '{"domain": "fail.com", "name": "F"}\n'
                '{"domain": "ok.com", "name": "O"}\n',
                encoding="utf-8",
            )
            def side(domain, _key):
                if domain == "fail.com":
                    raise CmTransportError("network down")
                return 7
            with mock.patch.dict(os.environ, {"CONTRACT_MANAGER_API_KEY": "test"}), \
                 mock.patch("scripts.lib.cm_client.search_clients_for_domain",
                            side_effect=side):
                from scripts.lib.vault_writer import run_map_cm_clients
                stats = run_map_cm_clients(data_root, feed_path=data_root / "feed.jsonl")
            self.assertEqual(stats["mapped"], 1)
            self.assertEqual(stats["failed"], 1)
            written = clients.read_text(encoding="utf-8")
            self.assertIn('"cm_client_id": 7', written)
            # The failed record stays without cm_client_id
            self.assertIn('"domain": "fail.com"', written)
            # Feed warning was emitted
            feed = (data_root / "feed.jsonl").read_text(encoding="utf-8")
            self.assertIn("map-cm-clients: failed for fail.com", feed)
            self.assertIn('"level": "warning"', feed)

    def test_map_cm_clients_dry_run_does_not_write(self):
        import unittest.mock as mock
        with tempfile.TemporaryDirectory() as d:
            data_root = Path(d)
            clients = self._setup(data_root)
            original = '{"domain": "example.com", "name": "Ex"}\n'
            clients.write_text(original, encoding="utf-8")
            with mock.patch.dict(os.environ, {"CONTRACT_MANAGER_API_KEY": "test"}), \
                 mock.patch("scripts.lib.cm_client.search_clients_for_domain"):
                from scripts.lib.vault_writer import run_map_cm_clients
                stats = run_map_cm_clients(data_root, dry_run=True,
                                           feed_path=data_root / "feed.jsonl")
            self.assertEqual(clients.read_text(encoding="utf-8"), original)
            self.assertEqual(stats["queried"], 1)


class TestCmTodosSection(unittest.TestCase):
    """Phase 11 D-B3: CM-TODOS managed section. Marker discipline inherits D-08a."""

    def test_renders_no_missing_placeholder_when_all_populated(self):
        from scripts.lib.vault_writer import render_cm_todos
        out = render_cm_todos({
            "deployed_modules": ["AMS Core"],
            "contract_start": "2026-01-01",
            "contract_end": "2027-01-01",
            "primary_contact": "Alice",
            "sites": [],
        })
        self.assertEqual(out, "_(no missing CM data)_")

    def test_renders_bullets_for_missing_scalars(self):
        from scripts.lib.vault_writer import render_cm_todos
        out = render_cm_todos({
            "deployed_modules": ["X"],
            "contract_start": "",
            "contract_end": "2027-01-01",
            "primary_contact": "",
            "sites": [],
        })
        self.assertIn("contract_start", out)
        self.assertIn("primary_contact", out)
        self.assertNotIn("contract_end", out)  # populated, should NOT appear
        self.assertNotIn("deployed_modules", out)  # populated, should NOT appear

    def test_renders_bullet_for_empty_deployed_modules(self):
        from scripts.lib.vault_writer import render_cm_todos
        out = render_cm_todos({
            "deployed_modules": [],
            "contract_start": "2026-01-01",
            "contract_end": "2027-01-01",
            "primary_contact": "Alice",
            "sites": [],
        })
        self.assertIn("deployed_modules", out)

    def test_renders_unavailable_placeholder_when_cm_extra_is_none(self):
        from scripts.lib.vault_writer import render_cm_todos
        out = render_cm_todos(None)
        self.assertEqual(out, "_(CM data unavailable; will refresh next sync)_")

    def test_sites_is_not_a_missing_condition(self):
        from scripts.lib.vault_writer import render_cm_todos
        # Sites is permanently [] per D-C2-REVISED — it should NEVER appear as a TODO bullet
        out = render_cm_todos({
            "deployed_modules": ["X"],
            "contract_start": "2026-01-01",
            "contract_end": "2027-01-01",
            "primary_contact": "Alice",
            "sites": [],
        })
        self.assertNotIn("sites", out.lower())
        self.assertEqual(out, "_(no missing CM data)_")


class TestUsageSection(unittest.TestCase):
    """Phase 11 D-C3-REVISED: Usage section sourced from get_sla_status."""

    def _sla(self, projects: list) -> dict:
        return {"asOfDate": "2026-05-02", "projects": projects}

    def test_no_usage_data_when_sla_none(self):
        from scripts.lib.vault_writer import render_usage
        self.assertEqual(render_usage(None, "Anyone"), "_(no usage data)_")

    def test_no_projects_returns_placeholder(self):
        from scripts.lib.vault_writer import render_usage
        self.assertEqual(render_usage(self._sla([]), "Anyone"), "_(no usage data)_")

    def test_filters_by_client_name(self):
        from scripts.lib.vault_writer import render_usage
        sla = self._sla([
            {"projectName": "Alpha", "clientName": "Other Client",
             "hoursLogged": 5, "hoursBudgeted": 10, "percentConsumed": 50},
            {"projectName": "Beta", "clientName": "Property Council",
             "hoursLogged": 12.5, "hoursBudgeted": 20, "percentConsumed": 62},
        ])
        out = render_usage(sla, "Property Council")
        self.assertIn("Beta", out)
        self.assertNotIn("Alpha", out)
        self.assertNotIn("Other Client", out)

    def test_renders_hours_and_percent(self):
        from scripts.lib.vault_writer import render_usage
        sla = self._sla([
            {"projectName": "Beta", "clientName": "Property Council",
             "hoursLogged": 12.5, "hoursBudgeted": 20, "percentConsumed": 62,
             "status": "on-track"},
        ])
        out = render_usage(sla, "Property Council")
        self.assertIn("12.5", out)
        self.assertIn("20", out)
        self.assertIn("62", out)
        self.assertIn("on-track", out)

    def test_filter_is_case_insensitive_substring(self):
        from scripts.lib.vault_writer import render_usage
        sla = self._sla([
            {"projectName": "PCA Project", "clientName": "property council australia",
             "hoursLogged": 1, "hoursBudgeted": 2, "percentConsumed": 50},
        ])
        out = render_usage(sla, "Property Council")
        self.assertIn("PCA Project", out)


class TestGatherEventsCmIntegration(unittest.TestCase):
    """Phase 11 _gather_events: CM contract events + CM invoice merge with dedup."""

    def _setup(self, d: Path) -> Path:
        config = d / "config"
        config.mkdir()
        (d / "triage").mkdir()
        (d / "tasks").mkdir()
        (d / "invoices").mkdir()
        (d / "todos").mkdir()
        (config / "clients.jsonl").write_text(
            '{"domain": "ex.com", "name": "Ex", "cm_client_id": 42}\n',
            encoding="utf-8",
        )
        (d / "tasks" / "active.jsonl").write_text("", encoding="utf-8")
        (d / "invoices" / "active.jsonl").write_text("", encoding="utf-8")
        return d

    def test_gather_events_includes_contract_events_when_cm_expiring_provided(self):
        from scripts.lib.vault_writer import _gather_events, load_clients
        with tempfile.TemporaryDirectory() as d:
            data_root = Path(self._setup(Path(d)))
            clients = load_clients(data_root)
            cm_expiring = {"contracts": [
                {"id": 7, "name": "MSA", "client": "Ex", "clientId": 42,
                 "endDate": "2026-06-15", "daysUntilExpiry": 30},
            ]}
            events_by_slug, _ = _gather_events(data_root, clients,
                                               cm_expiring=cm_expiring)
            slug = clients["ex.com"]["slug"]
            kinds = [e[1] for e in events_by_slug.get(slug, [])]
            self.assertIn("contract", kinds)

    def test_gather_events_unmapped_cm_clientid_routes_to_unknown(self):
        from scripts.lib.vault_writer import _gather_events, load_clients
        with tempfile.TemporaryDirectory() as d:
            data_root = Path(self._setup(Path(d)))
            clients = load_clients(data_root)
            cm_expiring = {"contracts": [
                {"id": 7, "name": "MSA", "client": "Stranger", "clientId": 999,
                 "endDate": "2026-06-15", "daysUntilExpiry": 30},
            ]}
            _, unknown_pairs = _gather_events(data_root, clients,
                                              cm_expiring=cm_expiring)
            kinds = [evt[1] for (evt, _src) in unknown_pairs]
            self.assertIn("contract", kinds)

    def test_gather_events_dedup_invoice_local_wins(self):
        from scripts.lib.vault_writer import _gather_events, load_clients
        with tempfile.TemporaryDirectory() as d:
            data_root = Path(self._setup(Path(d)))
            (data_root / "invoices" / "active.jsonl").write_text(
                '{"id":"inv-001","invoice_number":"INV-0042","client_domain":"ex.com",'
                '"status":"sent","amount":1000}\n',
                encoding="utf-8",
            )
            clients = load_clients(data_root)
            cm_invoices = {"invoices": [
                {"id": 11, "invoiceNumber": "INV-0042", "amount": 1000,
                 "issueDate": "2026-04-01", "dueDate": "2026-04-30",
                 "daysPastDue": 30, "severity": "warning",
                 "client": "Ex", "clientId": 42, "contract": "MSA", "contractId": 7},
            ]}
            events_by_slug, _ = _gather_events(data_root, clients,
                                               cm_invoices=cm_invoices)
            slug = clients["ex.com"]["slug"]
            invoice_summaries = [e[2] for e in events_by_slug.get(slug, [])
                                 if e[1] == "invoice"]
            # Only one invoice line — the local one (Phase 10 _event_tuple format)
            self.assertEqual(len(invoice_summaries), 1)
            # The CM-source-tag must NOT appear (local wins; no source label)
            invoice_details = [e[3] for e in events_by_slug.get(slug, [])
                               if e[1] == "invoice"]
            self.assertFalse(any(d and "contract-manager" in d for d in invoice_details))

    def test_gather_events_dedup_case_insensitive(self):
        from scripts.lib.vault_writer import _gather_events, load_clients
        with tempfile.TemporaryDirectory() as d:
            data_root = Path(self._setup(Path(d)))
            (data_root / "invoices" / "active.jsonl").write_text(
                '{"id":"inv-001","invoice_number":"INV-0042","client_domain":"ex.com",'
                '"status":"sent","amount":1000}\n',
                encoding="utf-8",
            )
            clients = load_clients(data_root)
            cm_invoices = {"invoices": [
                {"id": 11, "invoiceNumber": "inv-0042",  # lowercase variant
                 "amount": 1000, "issueDate": "2026-04-01", "dueDate": "2026-04-30",
                 "daysPastDue": 30, "severity": "warning",
                 "client": "Ex", "clientId": 42, "contract": "MSA", "contractId": 7},
            ]}
            events_by_slug, _ = _gather_events(data_root, clients,
                                               cm_invoices=cm_invoices)
            slug = clients["ex.com"]["slug"]
            inv_count = sum(1 for e in events_by_slug.get(slug, []) if e[1] == "invoice")
            self.assertEqual(inv_count, 1)  # case-fold dedup honoured

    def test_gather_events_dedup_does_not_strip_prefixes(self):
        from scripts.lib.vault_writer import _gather_events, load_clients
        with tempfile.TemporaryDirectory() as d:
            data_root = Path(self._setup(Path(d)))
            (data_root / "invoices" / "active.jsonl").write_text(
                '{"id":"inv-001","invoice_number":"INV-0042","client_domain":"ex.com",'
                '"status":"sent","amount":1000}\n',
                encoding="utf-8",
            )
            clients = load_clients(data_root)
            # Pitfall 4: stripping "INV-" prefix would conflate; we must NOT
            cm_invoices = {"invoices": [
                {"id": 11, "invoiceNumber": "0042",  # bare digits — different invoice
                 "amount": 999, "issueDate": "2026-04-01", "dueDate": "2026-04-30",
                 "daysPastDue": 30, "severity": "warning",
                 "client": "Ex", "clientId": 42, "contract": "MSA", "contractId": 7},
            ]}
            events_by_slug, _ = _gather_events(data_root, clients,
                                               cm_invoices=cm_invoices)
            slug = clients["ex.com"]["slug"]
            inv_count = sum(1 for e in events_by_slug.get(slug, []) if e[1] == "invoice")
            self.assertEqual(inv_count, 2)  # treated as DIFFERENT invoices

    def test_gather_events_no_cm_kwargs_unchanged_phase10_behaviour(self):
        from scripts.lib.vault_writer import _gather_events, load_clients
        with tempfile.TemporaryDirectory() as d:
            data_root = Path(self._setup(Path(d)))
            (data_root / "tasks" / "active.jsonl").write_text(
                '{"id":"task-1","status":"open","description":"do thing",'
                '"client_domain":"ex.com","ts":"2026-04-01T10:00:00+10:30"}\n',
                encoding="utf-8",
            )
            clients = load_clients(data_root)
            ev_p10, _ = _gather_events(data_root, clients)
            ev_p11, _ = _gather_events(data_root, clients,
                                       cm_expiring=None, cm_invoices=None)
            self.assertEqual(ev_p10, ev_p11)


class TestContractMerge(unittest.TestCase):
    """Phase 11 D-E1 + render_log_line accepts kind=contract."""

    def test_render_log_line_accepts_contract_kind(self):
        from scripts.lib.vault_writer import render_log_line
        out = render_log_line(rec_ts_iso="2026-06-15T00:00:00+10:30",
                              kind="contract", summary="x")
        self.assertTrue(out.startswith("### [2026-06-15 00:00] 📄 x"))

    def test_cm_contract_event_tuple_shape(self):
        from scripts.lib.vault_writer import _cm_contract_event_tuple
        ts, kind, summary, detail, ttid = _cm_contract_event_tuple({
            "id": 1, "name": "MSA", "client": "PCA", "clientId": 42,
            "endDate": "2026-06-15", "daysUntilExpiry": 30,
        })
        self.assertEqual(kind, "contract")
        self.assertIn("PCA", summary)
        self.assertIn("MSA", summary)
        self.assertIn("source: contract-manager", detail)
        self.assertIn("https://contracts.agend.info/contracts/1", detail)
        self.assertIsNone(ttid)


class TestProjectionDoesNotImportCm(unittest.TestCase):
    """Pitfall 1: Mac daemon's run_projection MUST NOT import scripts.lib.cm_client.

    Verified by spawning a fresh Python subprocess so module-cache state is clean
    (an in-process test could see cm_client in sys.modules from earlier test
    classes that did import it).
    """

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


class TestCacheFallbackEnd2End(unittest.TestCase):
    """Phase 11 D-A3 end-to-end: live failure → cache fallback → cm_data_stale_since stamp."""

    def _setup(self, d: Path):
        config = d / "config"
        config.mkdir()
        (d / "triage").mkdir()
        (d / "tasks").mkdir()
        (d / "invoices").mkdir()
        (d / "todos").mkdir()
        (config / "clients.jsonl").write_text(
            '{"domain":"ex.com","name":"Ex","cm_client_id":42}\n',
            encoding="utf-8",
        )
        (d / "tasks" / "active.jsonl").write_text("", encoding="utf-8")
        (d / "invoices" / "active.jsonl").write_text("", encoding="utf-8")
        return d, d / ".cm-cache.json"

    def _cached_summary(self):
        return {
            "client": {"id": 42, "name": "Ex"},
            "financial": {"totalMRR": 5000, "totalARR": 60000,
                          "activeContracts": 1, "currency": "AUD"},
            "contacts": [{"id": 1, "name": "Alice", "email": "a@ex.com"}],
            "activeContracts": [{
                "id": 7, "name": "AMS Core", "type": "MSA",
                "startDate": "2026-01-01", "endDate": "2027-01-01",
                "totalValue": 60000, "mrr": 5000,
            }],
            "recentInvoices": [], "openProposals": [],
        }

    def test_cache_fallback_stamps_stale_since_and_writes_warning(self):
        import unittest.mock as mock
        from scripts.lib.cm_client import CmTransportError
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as build:
            data_root, cache_path = self._setup(Path(d))
            stale_ts = "2026-04-01T10:00:00+10:30"
            cache = {
                "schema_version": 1,
                "global": {},
                "by_client": {
                    "ex.com": {
                        "client_summary": {"fetched_at": stale_ts,
                                           "result": self._cached_summary()},
                    }
                },
            }
            cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
            feed_path = data_root / "feed.jsonl"
            feed_path.touch()

            with mock.patch.dict(os.environ, {"CONTRACT_MANAGER_API_KEY": "k"}), \
                 mock.patch("scripts.lib.cm_client._cm_post",
                            side_effect=CmTransportError("down")), \
                 mock.patch("scripts.lib.cm_client.time.sleep"):
                from scripts.lib.vault_writer import run_backfill
                stats = run_backfill(data_root, Path(build), feed_path=feed_path)
            self.assertGreaterEqual(stats["clients_written"], 1)

            ex_md = list((Path(build) / "Clients").glob("*.md"))
            ex_text = next(p for p in ex_md
                           if "_Unknown" not in p.name).read_text(encoding="utf-8")
            self.assertIn("cm_data_stale_since", ex_text)
            self.assertIn(stale_ts, ex_text)
            # Cached frontmatter values surface (Alice → primary_contact, AMS Core → deployed_modules)
            self.assertIn("Alice", ex_text)
            self.assertIn("AMS Core", ex_text)
            # Warning feed entry written
            feed = feed_path.read_text(encoding="utf-8")
            self.assertIn('"level": "warning"', feed)

    def test_cache_clears_stale_since_when_cm_succeeds(self):
        import unittest.mock as mock
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as build:
            data_root, cache_path = self._setup(Path(d))
            feed_path = data_root / "feed.jsonl"
            feed_path.touch()
            fresh_summary = self._cached_summary()
            sla_response = {"asOfDate": "2026-05-02", "projects": []}

            def _fake_post(method, params, key):
                if method == "get_client_summary":
                    return fresh_summary
                if method == "list_contracts_expiring":
                    return {"contracts": []}
                if method == "list_overdue_invoices":
                    return {"invoices": []}
                if method == "get_sla_status":
                    return sla_response
                return {}

            with mock.patch.dict(os.environ, {"CONTRACT_MANAGER_API_KEY": "k"}), \
                 mock.patch("scripts.lib.cm_client._cm_post", side_effect=_fake_post):
                from scripts.lib.vault_writer import run_backfill
                run_backfill(data_root, Path(build), feed_path=feed_path)

            ex_md = list((Path(build) / "Clients").glob("*.md"))
            ex_text = next(p for p in ex_md
                           if "_Unknown" not in p.name).read_text(encoding="utf-8")
            self.assertNotIn("cm_data_stale_since", ex_text)


class TestBackfillIdempotentPhase11(unittest.TestCase):
    """D-14/D-16 idempotency under Phase 11 — two runs same CM responses → byte-identical
    managed sections.

    Strips both `last_synced:` and `cm_data_stale_since:` from the snapshot before
    comparison.
    """

    def test_two_runs_byte_identical_managed(self):
        import unittest.mock as mock
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as build:
            data_root = Path(d)
            (data_root / "config").mkdir()
            (data_root / "triage").mkdir()
            (data_root / "tasks").mkdir()
            (data_root / "invoices").mkdir()
            (data_root / "todos").mkdir()
            (data_root / "config" / "clients.jsonl").write_text(
                '{"domain":"ex.com","name":"Ex","cm_client_id":42}\n',
                encoding="utf-8",
            )
            (data_root / "tasks" / "active.jsonl").write_text("", encoding="utf-8")
            (data_root / "invoices" / "active.jsonl").write_text("", encoding="utf-8")
            feed = data_root / "feed.jsonl"
            feed.touch()

            fresh = {
                "client": {"id": 42, "name": "Ex"},
                "financial": {"totalMRR": 0, "totalARR": 0,
                              "activeContracts": 0, "currency": "AUD"},
                "contacts": [], "activeContracts": [],
                "recentInvoices": [], "openProposals": [],
            }

            def _fake_post(method, params, key):
                if method == "get_client_summary":
                    return fresh
                if method == "list_contracts_expiring":
                    return {"contracts": []}
                if method == "list_overdue_invoices":
                    return {"invoices": []}
                if method == "get_sla_status":
                    return {"projects": []}
                return {}

            with mock.patch.dict(os.environ, {"CONTRACT_MANAGER_API_KEY": "k"}), \
                 mock.patch("scripts.lib.cm_client._cm_post", side_effect=_fake_post):
                from scripts.lib.vault_writer import run_backfill
                run_backfill(data_root, Path(build), feed_path=feed)
                snap1 = self._snapshot(Path(build))
                run_backfill(data_root, Path(build), feed_path=feed)
                snap2 = self._snapshot(Path(build))
            self.assertEqual(snap1, snap2)

    def _snapshot(self, build_root: Path) -> dict:
        out = {}
        for md in sorted((build_root / "Clients").glob("*.md")):
            lines = md.read_text(encoding="utf-8").splitlines()
            filtered = [ln for ln in lines
                        if not ln.startswith("last_synced:")
                        and not ln.startswith("cm_data_stale_since:")]
            out[md.name] = "\n".join(filtered)
        return out


class TestJitMapping(unittest.TestCase):
    """D-G1 JIT fallback inside _fetch_cm_data_for_run.

    When clients.jsonl gains a new row without cm_client_id (e.g. Glen adds a
    new client between Phase 11 ship and the next --mode map-cm-clients run),
    the next sync issues ONE search_clients call for that domain. Three paths
    must be tested: success (id found, persisted, feed.info), no-match (warn,
    bucket empty, no mutation), and search failure (warn, bucket empty, no
    mutation). All three preserve idempotency — clients.jsonl persists the JIT
    result so the NEXT sync skips the JIT path entirely.

    Test seam: mock `scripts.lib.cm_client._cm_post` (the single network seam
    per RESEARCH §Test Scaffolding) so search_clients_for_domain is exercised
    end-to-end without touching the network.
    """

    def _setup(self, d: Path, *, with_cm_id: bool = False) -> Path:
        config = d / "config"
        config.mkdir()
        (d / "triage").mkdir()
        (d / "tasks").mkdir()
        (d / "invoices").mkdir()
        (d / "todos").mkdir()
        # Seed one mapped client (so has_mapped_clients gate trips and the
        # CM fetch loop actually runs) and one unmapped target client.
        line_mapped = '{"domain": "mapped.com", "name": "Mapped", "cm_client_id": 5}\n'
        if with_cm_id:
            line_target = '{"domain": "new.com", "name": "NewCo", "cm_client_id": 99}\n'
        else:
            line_target = '{"domain": "new.com", "name": "NewCo"}\n'
        (config / "clients.jsonl").write_text(line_mapped + line_target, encoding="utf-8")
        (d / "tasks" / "active.jsonl").write_text("", encoding="utf-8")
        (d / "invoices" / "active.jsonl").write_text("", encoding="utf-8")
        return d

    def _fake_post_factory(self, *, search_returns=None, search_raises=None,
                            summary_for_5=None, summary_for_jit=None):
        """Build a side_effect for cm_client._cm_post that handles every method
        run_backfill issues, with configurable behaviour for `search_clients`.
        """
        def _post(method, params, key):
            if method == "search_clients":
                if search_raises is not None:
                    raise search_raises
                return search_returns or {"clients": []}
            if method == "list_contracts_expiring":
                return {"contracts": []}
            if method == "list_overdue_invoices":
                return {"invoices": []}
            if method == "get_client_summary":
                cid = params.get("clientId")
                if cid == 5:
                    return summary_for_5 or {"client": {"id": 5, "name": "Mapped"},
                                              "financial": {}, "contacts": [],
                                              "activeContracts": [],
                                              "recentInvoices": [], "openProposals": []}
                return summary_for_jit or {"client": {"id": cid, "name": "NewCo"},
                                            "financial": {}, "contacts": [],
                                            "activeContracts": [],
                                            "recentInvoices": [], "openProposals": []}
            if method == "get_sla_status":
                return {"projects": []}
            return {}
        return _post

    def test_jit_maps_new_domain(self):
        """search_clients returns a website-substring match → cm_client_id is
        persisted to clients.jsonl, the info-level feed entry is written, and
        get_client_summary is called with the freshly-mapped id."""
        import unittest.mock as mock
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as build:
            data_root = Path(self._setup(Path(d)))
            feed = data_root / "feed.jsonl"
            feed.touch()
            search_payload = {"clients": [
                {"id": 77, "name": "NewCo Pty", "website": "https://new.com",
                 "email": None, "phone": None, "activeContracts": 1, "contactCount": 1},
            ]}
            calls: list = []
            def _trace_post(method, params, key):
                calls.append((method, params))
                fp = self._fake_post_factory(search_returns=search_payload)
                return fp(method, params, key)
            with mock.patch.dict(os.environ, {"CONTRACT_MANAGER_API_KEY": "k"}), \
                 mock.patch("scripts.lib.cm_client._cm_post", side_effect=_trace_post), \
                 mock.patch("scripts.lib.cm_client.time.sleep"):
                from scripts.lib.vault_writer import run_backfill
                run_backfill(data_root, Path(build), feed_path=feed)
            # 1. clients.jsonl now has the new id
            updated = (data_root / "config" / "clients.jsonl").read_text(encoding="utf-8")
            self.assertIn('"cm_client_id": 77', updated)
            self.assertIn('"domain": "new.com"', updated)
            # 2. feed has the info entry
            feed_text = feed.read_text(encoding="utf-8")
            self.assertIn('"level": "info"', feed_text)
            self.assertIn("JIT-mapped new.com", feed_text)
            self.assertIn("cm_client_id=77", feed_text)
            # 3. get_client_summary was called with id 77 (the JIT result)
            summary_calls = [(m, p) for (m, p) in calls if m == "get_client_summary"]
            self.assertTrue(any(p.get("clientId") == 77 for (_m, p) in summary_calls),
                            f"expected get_client_summary(clientId=77); calls: {summary_calls}")

    def test_jit_no_match_warns(self):
        """search_clients returns empty → warning feed entry, empty bucket, NO
        mutation of clients.jsonl. The unmapped record stays unmapped so the
        next sync re-attempts JIT (idempotent — eventually consistent)."""
        import unittest.mock as mock
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as build:
            data_root = Path(self._setup(Path(d)))
            feed = data_root / "feed.jsonl"
            feed.touch()
            with mock.patch.dict(os.environ, {"CONTRACT_MANAGER_API_KEY": "k"}), \
                 mock.patch("scripts.lib.cm_client._cm_post",
                            side_effect=self._fake_post_factory(search_returns={"clients": []})), \
                 mock.patch("scripts.lib.cm_client.time.sleep"):
                from scripts.lib.vault_writer import run_backfill
                run_backfill(data_root, Path(build), feed_path=feed)
            # clients.jsonl unchanged for new.com (still no cm_client_id)
            after = (data_root / "config" / "clients.jsonl").read_text(encoding="utf-8")
            self.assertNotIn('"cm_client_id": 77', after)
            new_lines = [ln for ln in after.splitlines() if '"domain": "new.com"' in ln]
            self.assertTrue(new_lines, "new.com record disappeared from clients.jsonl")
            self.assertNotIn("cm_client_id", new_lines[0])
            # Warning feed entry written
            feed_text = feed.read_text(encoding="utf-8")
            self.assertIn('"level": "warning"', feed_text)
            self.assertIn("JIT mapping failed for new.com", feed_text)

    def test_jit_search_fails_warns(self):
        """search_clients raises CmTransportError → warning feed entry, empty
        bucket, NO mutation of clients.jsonl. CM downtime degrades gracefully."""
        import unittest.mock as mock
        from scripts.lib.cm_client import CmTransportError
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as build:
            data_root = Path(self._setup(Path(d)))
            feed = data_root / "feed.jsonl"
            feed.touch()
            def _post(method, params, key):
                if method == "search_clients":
                    raise CmTransportError("network down")
                return self._fake_post_factory()(method, params, key)
            with mock.patch.dict(os.environ, {"CONTRACT_MANAGER_API_KEY": "k"}), \
                 mock.patch("scripts.lib.cm_client._cm_post", side_effect=_post), \
                 mock.patch("scripts.lib.cm_client.time.sleep"):
                from scripts.lib.vault_writer import run_backfill
                run_backfill(data_root, Path(build), feed_path=feed)
            after = (data_root / "config" / "clients.jsonl").read_text(encoding="utf-8")
            new_lines = [ln for ln in after.splitlines() if '"domain": "new.com"' in ln]
            self.assertTrue(new_lines)
            self.assertNotIn("cm_client_id", new_lines[0])
            feed_text = feed.read_text(encoding="utf-8")
            self.assertIn('"level": "warning"', feed_text)
            self.assertIn("JIT mapping failed for new.com", feed_text)
            self.assertIn("CmTransportError", feed_text)


if __name__ == "__main__":
    unittest.main()
