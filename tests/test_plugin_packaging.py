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
GITHUB_REPOSITORY = "https://github.com/TaoGEO/TaoHtml"


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
                self.assertEqual(claude_manifest["version"], version)
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

    def test_claude_remote_marketplace_installs_the_repository_plugin(self) -> None:
        claude_manifest = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        claude_marketplace = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(claude_manifest["skills"], "./skill/")
        self.assertNotIn("version", claude_manifest)
        self.assertEqual(claude_manifest["repository"], GITHUB_REPOSITORY)

        claude_entry = claude_marketplace["plugins"][0]
        self.assertEqual(claude_entry["name"], "taohtml")
        self.assertEqual(claude_entry["source"], "./")
        self.assertFalse(
            (ROOT / ".agents" / "plugins" / "marketplace.json").exists(),
            "Do not claim a Codex remote marketplace without a validator-compatible skills/ layout",
        )
        self.assertFalse(
            (ROOT / ".codex-plugin" / "plugin.json").exists(),
            "Do not expose an invalid Codex repository plugin root",
        )

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("claude plugin marketplace add TaoGEO/TaoHtml", readme)
        self.assertNotIn("codex plugin marketplace add TaoGEO/TaoHtml", readme)

    def test_readme_separates_safe_first_install_and_replacement_update(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("$HOME/.agents/skills/taohtml", readme)
        self.assertIn("首次安装", readme)
        self.assertIn("原始 Skill：更新", readme)
        self.assertIn('mv "$target" "$backup"', readme)
        self.assertIn("Move-Item -LiteralPath $target -Destination $backup", readme)
        self.assertNotIn(
            "cp -R ./skill/taohtml ~/.codex/skills/taohtml",
            readme,
        )
        self.assertNotIn(
            "Copy-Item -Recurse -Force .\\skill\\taohtml $env:USERPROFILE\\.codex\\skills\\taohtml",
            readme,
        )
        self.assertIn("离线 / 手动备选", readme)


if __name__ == "__main__":
    unittest.main()
