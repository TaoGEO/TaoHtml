from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image
import yaml


ROOT = Path(__file__).resolve().parents[1]
PACKAGER = ROOT / "scripts" / "package_plugin_marketplace.py"
SKILLHUB_PACKAGER = ROOT / "scripts" / "package_skillhub.py"
ARCHIVE_ROOT = "taohtml-marketplace"
GITHUB_REPOSITORY = "https://github.com/TaoGEO/TaoHtml"


class PluginPackagingTests(unittest.TestCase):
    def test_builds_one_cross_client_bundle_from_the_canonical_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "taohtml-marketplace.zip"
            repeated_output = Path(temp_dir) / "taohtml-marketplace-repeated.zip"
            subprocess.run(
                [sys.executable, str(PACKAGER), str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [sys.executable, str(PACKAGER), str(repeated_output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(output.read_bytes(), repeated_output.read_bytes())

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

    def test_readme_exposes_safe_installation_and_version_entries(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("$HOME/.agents/skills/taohtml", readme)
        self.assertIn('test ! -e "$target"', readme)
        self.assertNotIn(
            "cp -R ./skill/taohtml ~/.codex/skills/taohtml",
            readme,
        )
        self.assertNotIn(
            "Copy-Item -Recurse -Force .\\skill\\taohtml $env:USERPROFILE\\.codex\\skills\\taohtml",
            readme,
        )
        self.assertIn("taohtml-marketplace-v0.3.0.zip", readme)
        for version in ("v0.3.0", "v0.2.0", "v0.1.0"):
            self.assertIn(version, readme)
        self.assertIn("CHANGELOG.md#030---2026-07-16", readme)
        self.assertIn("CHANGELOG.md#020---2026-07-15", readme)
        self.assertIn("CHANGELOG.md#010---2026-07-13", readme)
        image_paths = set(
            re.findall(
                r'(?:src|href)="(docs/assets/readme/v0\.3\.0/[^"]+\.png)"',
                readme,
            )
        )
        self.assertEqual(
            image_paths,
            {
                "docs/assets/readme/v0.3.0/built-in-visual-systems.png",
                "docs/assets/readme/v0.3.0/reference-style-reconstruction.png",
                "docs/assets/readme/v0.3.0/corporate-template-fidelity.png",
            },
        )
        for image_path in image_paths:
            self.assertTrue((ROOT / image_path).is_file(), image_path)
        asset_dir = ROOT / "docs" / "assets" / "readme" / "v0.3.0"
        self.assertEqual(
            {path.name for path in asset_dir.glob("*.png")},
            {Path(image_path).name for image_path in image_paths},
        )
        overview = asset_dir / "built-in-visual-systems.png"
        self.assertEqual(
            hashlib.sha256(overview.read_bytes()).hexdigest(),
            "87ad99a01382611a23c88e6c7172013b9e6b77bd759216e804380cf841ec6c8e",
        )
        with Image.open(overview) as image:
            self.assertEqual(image.size, (1708, 914))

    def test_builds_skillhub_channel_package_from_the_canonical_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "taohtml-skillhub-v0.3.0.zip"
            repeated_output = Path(temp_dir) / "taohtml-skillhub-repeated.zip"
            subprocess.run(
                [
                    sys.executable,
                    str(SKILLHUB_PACKAGER),
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [sys.executable, str(SKILLHUB_PACKAGER), str(repeated_output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(output.read_bytes(), repeated_output.read_bytes())

            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                self.assertIn("SKILL.md", names)
                self.assertEqual(
                    [name for name in names if name.endswith("SKILL.md")],
                    ["SKILL.md"],
                )
                self.assertFalse(
                    any(name.startswith("docs/assets/readme/") for name in names)
                )

                skill_text = archive.read("SKILL.md").decode("utf-8")
                _, frontmatter_text, generated_body = skill_text.split("---\n", 2)
                metadata = yaml.safe_load(frontmatter_text)
                self.assertEqual(metadata["name"], "taohtml")
                self.assertEqual(metadata["slug"], "taohtml")
                self.assertEqual(
                    metadata["version"],
                    (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
                )
                self.assertEqual(metadata["displayName"], "TaoHtml")
                self.assertEqual(metadata["category"], "content-creation")
                self.assertEqual(
                    metadata["tags"],
                    ["HTML演示", "PPT转换", "报告设计", "视觉系统", "企业模板保真"],
                )
                self.assertIn("16:9", metadata["summary"])
                self.assertIn("四套内置视觉系统", metadata["description"])
                self.assertIn("参考图建立项目专用视觉风格", metadata["description"])
                self.assertNotIn("CSS scroll-snap", metadata["description"])

                canonical_text = (
                    ROOT / "skill" / "taohtml" / "SKILL.md"
                ).read_text(encoding="utf-8")
                canonical_body = canonical_text.split("\n---\n", 1)[1]
                self.assertEqual(generated_body, canonical_body)

    def test_public_channel_descriptions_share_the_v030_positioning(self) -> None:
        canonical = (ROOT / "skill" / "taohtml" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        agent_metadata = (
            ROOT / "skill" / "taohtml" / "agents" / "openai.yaml"
        ).read_text(encoding="utf-8")
        claude_manifest = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        claude_marketplace = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("16:9 offline HTML", canonical)
        self.assertIn("four built-in visual systems", canonical)
        self.assertIn("reference-based project theme", canonical)
        self.assertIn("16:9 offline HTML", agent_metadata)
        self.assertIn("16:9 offline HTML", claude_manifest["description"])
        self.assertEqual(
            claude_manifest["description"],
            claude_marketplace["plugins"][0]["description"],
        )
        self.assertIn(
            "built-in or reference-based visual systems",
            claude_manifest["description"],
        )
        self.assertNotIn("CSS scroll-snap", canonical)
        self.assertIn("allow_implicit_invocation: false", agent_metadata)

    def test_v030_changelog_accounts_for_every_merged_pr(self) -> None:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        release_section = changelog.split("## [0.3.0]", 1)[1].split(
            "## [0.2.0]", 1
        )[0]
        for pull_request in range(3, 11):
            self.assertIn(
                f"https://github.com/TaoGEO/TaoHtml/pull/{pull_request}",
                release_section,
            )

    def test_ci_packages_both_distribution_channels(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "quality.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("scripts/package_plugin_marketplace.py", workflow)
        self.assertIn("scripts/package_skillhub.py", workflow)


if __name__ == "__main__":
    unittest.main()
