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


if __name__ == "__main__":
    unittest.main()
