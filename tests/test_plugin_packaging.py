from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGER = ROOT / "scripts" / "package_plugin_marketplace.py"
ARCHIVE_ROOT = "taohtml-marketplace"


class PluginPackagingTests(unittest.TestCase):
    def test_builds_one_cross_client_bundle_from_the_canonical_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "taohtml-marketplace.zip"
            subprocess.run(
                [sys.executable, str(PACKAGER), str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                skill_path = (
                    f"{ARCHIVE_ROOT}/plugins/taohtml/skills/taohtml/SKILL.md"
                )
                codex_manifest_path = (
                    f"{ARCHIVE_ROOT}/plugins/taohtml/.codex-plugin/plugin.json"
                )
                claude_manifest_path = (
                    f"{ARCHIVE_ROOT}/plugins/taohtml/.claude-plugin/plugin.json"
                )
                self.assertIn(skill_path, names)
                self.assertIn(
                    f"{ARCHIVE_ROOT}/.agents/plugins/marketplace.json", names
                )
                self.assertIn(
                    f"{ARCHIVE_ROOT}/.claude-plugin/marketplace.json", names
                )
                self.assertEqual(
                    archive.read(skill_path),
                    (ROOT / "skill" / "taohtml" / "SKILL.md").read_bytes(),
                )

                codex_manifest = json.loads(archive.read(codex_manifest_path))
                claude_manifest = json.loads(archive.read(claude_manifest_path))
                version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
                for key in (
                    "name",
                    "version",
                    "description",
                    "author",
                    "homepage",
                    "repository",
                    "license",
                    "keywords",
                    "skills",
                ):
                    self.assertEqual(codex_manifest[key], claude_manifest[key])
                self.assertEqual(codex_manifest["skills"], "./skills/")
                self.assertEqual(codex_manifest["version"], version)
                self.assertIn("interface", codex_manifest)
                self.assertNotIn("interface", claude_manifest)

                bundled_skills = [
                    name for name in names if name.endswith("/SKILL.md")
                ]
                self.assertEqual(bundled_skills, [skill_path])
                self.assertFalse(
                    any("agent-method-report" in name for name in names)
                )

    def test_repository_keeps_only_one_taohtml_skill_source(self) -> None:
        tracked_skills = subprocess.run(
            ["git", "ls-files", "*SKILL.md"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertEqual(tracked_skills, ["skill/taohtml/SKILL.md"])


if __name__ == "__main__":
    unittest.main()
