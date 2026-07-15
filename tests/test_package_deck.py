from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DECK = ROOT / "skill" / "taohtml" / "scripts" / "package_deck.py"


class PackageDeckTests(unittest.TestCase):
    def test_packages_deck_with_relative_folder_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deck = root / "example-deck"
            (deck / "assets").mkdir(parents=True)
            (deck / "index.html").write_text("<h1>Example</h1>", encoding="utf-8")
            (deck / "assets" / "evidence.txt").write_text("proof", encoding="utf-8")
            archive = root / "dist" / "example-deck.zip"

            result = subprocess.run(
                [sys.executable, str(PACKAGE_DECK), str(deck), str(archive)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(
                    set(bundle.namelist()),
                    {"example-deck/index.html", "example-deck/assets/evidence.txt"},
                )


if __name__ == "__main__":
    unittest.main()
