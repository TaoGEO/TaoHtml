from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DECK = ROOT / "skill" / "taohtml" / "scripts" / "package_deck.py"


def load_package_deck() -> ModuleType:
    spec = importlib.util.spec_from_file_location("taohtml_package_deck", PACKAGE_DECK)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PACKAGE_DECK_MODULE = load_package_deck()


class PackageDeckTests(unittest.TestCase):
    def run_packager(self, deck: Path, archive: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PACKAGE_DECK), str(deck), str(archive)],
            check=False,
            capture_output=True,
            text=True,
        )

    def create_deck(self, root: Path) -> Path:
        deck = root / "example-deck"
        (deck / "assets").mkdir(parents=True)
        (deck / "index.html").write_text("<h1>Example</h1>", encoding="utf-8")
        return deck

    def create_symlink(
        self, link: Path, target: Path, *, target_is_directory: bool = False
    ) -> None:
        try:
            link.symlink_to(target, target_is_directory=target_is_directory)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")

    def assert_rejected(
        self, result: subprocess.CompletedProcess[str], archive: Path, *messages: str
    ) -> None:
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertFalse(archive.exists(), output)
        for message in messages:
            self.assertIn(message, output)

    def assert_no_temporary_archives(self, archive: Path) -> None:
        self.assertEqual(
            list(archive.parent.glob(f".{archive.name}.*.tmp")),
            [],
        )

    def test_packages_deck_with_relative_folder_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deck = self.create_deck(root)
            (deck / "assets" / "evidence.txt").write_text("proof", encoding="utf-8")
            archive = root / "dist" / "example-deck.zip"

            result = self.run_packager(deck, archive)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(
                    set(bundle.namelist()),
                    {"example-deck/index.html", "example-deck/assets/evidence.txt"},
                )
            self.assert_no_temporary_archives(archive)

    def test_rejects_symlink_to_file_outside_deck(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deck = self.create_deck(root)
            secret = root / "secret.txt"
            secret.write_text("outside", encoding="utf-8")
            link = deck / "assets" / "secret.txt"
            self.create_symlink(link, secret)
            archive = root / "dist" / "example-deck.zip"

            result = self.run_packager(deck, archive)

            self.assert_rejected(result, archive, str(link), "symbolic links")

    def test_rejects_symlink_to_file_inside_deck(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deck = self.create_deck(root)
            target = deck / "assets" / "original.txt"
            target.write_text("inside", encoding="utf-8")
            link = deck / "assets" / "duplicate.txt"
            self.create_symlink(link, target)
            archive = root / "dist" / "example-deck.zip"

            result = self.run_packager(deck, archive)

            self.assert_rejected(result, archive, str(link), "symbolic links")

    def test_rejects_symlink_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deck = self.create_deck(root)
            linked_target = root / "linked-assets"
            linked_target.mkdir()
            (linked_target / "outside.txt").write_text("outside", encoding="utf-8")
            link = deck / "linked-assets"
            self.create_symlink(link, linked_target, target_is_directory=True)
            archive = root / "dist" / "example-deck.zip"

            result = self.run_packager(deck, archive)

            self.assert_rejected(result, archive, str(link), "symbolic links")

    def test_rejects_nested_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deck = self.create_deck(root)
            nested = deck / "assets" / "one" / "two"
            nested.mkdir(parents=True)
            secret = root / "nested-secret.txt"
            secret.write_text("outside", encoding="utf-8")
            link = nested / "secret.txt"
            self.create_symlink(link, secret)
            archive = root / "dist" / "example-deck.zip"

            result = self.run_packager(deck, archive)

            self.assert_rejected(result, archive, str(link), "symbolic links")

    def test_rejects_symlink_as_deck_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deck = self.create_deck(root)
            linked_deck = root / "linked-deck"
            self.create_symlink(linked_deck, deck, target_is_directory=True)
            archive = root / "dist" / "example-deck.zip"

            result = self.run_packager(linked_deck, archive)

            self.assert_rejected(result, archive, str(linked_deck), "symbolic links")

    def test_rejects_output_archive_inside_deck(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deck = self.create_deck(root)
            archive = deck / "delivery.zip"

            result = self.run_packager(deck, archive)

            self.assert_rejected(result, archive, str(archive), "inside deck root")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO creation is unavailable")
    def test_rejects_special_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deck = self.create_deck(root)
            fifo = deck / "assets" / "events.pipe"
            os.mkfifo(fifo)
            archive = root / "dist" / "example-deck.zip"

            result = self.run_packager(deck, archive)

            self.assert_rejected(result, archive, str(fifo), "FIFO", "regular file")

    def test_reparse_point_is_link_like_without_path_is_junction(self) -> None:
        class LegacyPath:
            pass

        legacy_path = LegacyPath()
        entry_stat = SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_file_attributes=0x400,
        )
        self.assertFalse(hasattr(legacy_path, "is_junction"))

        with mock.patch.object(
            PACKAGE_DECK_MODULE.stat,
            "FILE_ATTRIBUTE_REPARSE_POINT",
            0x400,
            create=True,
        ):
            self.assertTrue(PACKAGE_DECK_MODULE._is_link_like(legacy_path, entry_stat))

    def test_write_failure_leaves_no_output_or_temporary_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deck = self.create_deck(root)
            archive = root / "dist" / "example-deck.zip"

            with mock.patch.object(
                PACKAGE_DECK_MODULE.zipfile.ZipFile,
                "write",
                side_effect=OSError("simulated write failure"),
            ):
                with self.assertRaisesRegex(OSError, "simulated write failure"):
                    PACKAGE_DECK_MODULE.package_deck(deck, archive)

            self.assertFalse(archive.exists())
            self.assert_no_temporary_archives(archive)

    def test_write_failure_preserves_existing_output_and_cleans_temporary_archive(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deck = self.create_deck(root)
            archive = root / "dist" / "example-deck.zip"
            archive.parent.mkdir(parents=True)
            with zipfile.ZipFile(archive, "w") as existing:
                existing.writestr("previous-delivery.txt", b"known-good")
            original = archive.read_bytes()

            with mock.patch.object(
                PACKAGE_DECK_MODULE.zipfile.ZipFile,
                "write",
                side_effect=OSError("simulated compression failure"),
            ):
                with self.assertRaisesRegex(OSError, "simulated compression failure"):
                    PACKAGE_DECK_MODULE.package_deck(deck, archive)

            self.assertEqual(archive.read_bytes(), original)
            self.assert_no_temporary_archives(archive)


if __name__ == "__main__":
    unittest.main()
