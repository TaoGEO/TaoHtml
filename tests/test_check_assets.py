from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK_ASSETS = ROOT / "skill" / "taohtml" / "scripts" / "check_assets.py"
TEMPLATE = ROOT / "skill" / "taohtml" / "assets" / "html-deck-template" / "index.html"


def run_check(html: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK_ASSETS), str(html), *extra_args],
        check=False,
        capture_output=True,
        text=True,
    )


class CheckAssetsTests(unittest.TestCase):
    def test_bundled_template_is_portable(self) -> None:
        result = run_check(TEMPLATE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ASSET_CHECK_OK", result.stdout)

    def test_missing_data_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            html = Path(temp_dir) / "index.html"
            html.write_text('<button data-source="assets/missing.png">Source</button>', encoding="utf-8")
            result = run_check(html)

        self.assertEqual(result.returncode, 1)
        self.assertIn("MISSING_ASSETS", result.stdout)
        self.assertIn("assets/missing.png", result.stdout)

    def test_srcset_candidates_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "one.png").touch()
            html = root / "index.html"
            html.write_text('<img srcset="one.png 1x, two.png 2x">', encoding="utf-8")
            result = run_check(html)

        self.assertEqual(result.returncode, 1)
        self.assertIn("two.png", result.stdout)
        self.assertNotIn("  one.png\n", result.stdout)

    def test_remote_assets_are_reported_but_do_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            html = Path(temp_dir) / "index.html"
            html.write_text('<img src="https://example.com/evidence.png">', encoding="utf-8")
            result = run_check(html)

        self.assertEqual(result.returncode, 0)
        self.assertIn("REMOTE_ASSETS", result.stdout)

    def test_remote_assets_fail_in_strict_offline_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            html = Path(temp_dir) / "index.html"
            html.write_text('<img src="https://example.com/evidence.png">', encoding="utf-8")
            result = run_check(html, "--strict-offline")

        self.assertEqual(result.returncode, 1)
        self.assertIn("REMOTE_ASSETS", result.stdout)

    def test_external_hyperlinks_are_allowed_in_strict_offline_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            html = Path(temp_dir) / "index.html"
            html.write_text('<a href="https://example.com/source">Source</a>', encoding="utf-8")
            result = run_check(html, "--strict-offline")

        self.assertEqual(result.returncode, 0)
        self.assertIn("REMOTE_LINKS", result.stdout)
        self.assertIn("ASSET_CHECK_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
