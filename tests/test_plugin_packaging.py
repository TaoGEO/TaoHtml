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
EXPECTED_CUSTOMER_OPENING = (
    "把已有的 Word、PDF 或 PPT，直接制作成可在浏览器中汇报、带分步动效、支持全屏展示与离线交付的 16:9 HTML 演示文稿。"
    "它不只是转换文件格式，还会重新设计页面、视觉层级和讲解节奏，让成品可以直接用于项目汇报、客户提案、产品路演或培训。",
    "如果你准备写报告、做汇报或制作提案，但目前只有一个主题、还没有完整思路，TaoHtml 也可以通过少量关键问题，"
    "帮助你梳理目标、受众、核心观点、证据和报告结构，再完成内容与演示设计。",
    "如果你有喜欢的 PPT、网页或图片风格，可以把参考图发给 TaoHtml。它会拆解配色、字体层级、构图、组件和品牌元素，"
    "先生成一张 VI 设计标准图供你确认，再按照这套标准制作完整报告。企业模板还可以保留 Logo、页眉、页脚等固定品牌元素。",
    "如果你没有明确的参考风格，可以直接选择四套内置视觉系统：黑白荧光卡片、严谨咨询报告、稳重企业年报、杂志图文拼贴，"
    "由 TaoHtml 根据报告内容完成重构与设计。",
)

sys.path.insert(0, str(ROOT))
from scripts import package_skillhub as skillhub_packager


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
                for relative in (
                    "requirements.txt",
                    "scripts/preflight.py",
                    "scripts/profile_store.py",
                    "scripts/check_production_authorization.py",
                    "references/profile-memory.md",
                    "references/production-authorization.md",
                ):
                    bundled = (
                        f"{ARCHIVE_ROOT}/plugins/taohtml/skills/taohtml/{relative}"
                    )
                    self.assertIn(bundled, names)
                    self.assertEqual(
                        archive.read(bundled),
                        (ROOT / "skill" / "taohtml" / relative).read_bytes(),
                    )
                preflight_info = archive.getinfo(
                    f"{ARCHIVE_ROOT}/plugins/taohtml/skills/taohtml/scripts/preflight.py"
                )
                self.assertEqual((preflight_info.external_attr >> 16) & 0o777, 0o755)
                profile_store_info = archive.getinfo(
                    f"{ARCHIVE_ROOT}/plugins/taohtml/skills/taohtml/scripts/profile_store.py"
                )
                self.assertEqual(
                    (profile_store_info.external_attr >> 16) & 0o777,
                    0o755,
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
        self.assertIn("taohtml-marketplace-v0.3.2.zip", readme)
        for version in ("v0.3.2", "v0.3.1", "v0.3.0", "v0.2.0", "v0.1.0"):
            self.assertIn(version, readme)
        self.assertIn("CHANGELOG.md#032---2026-07-16", readme)
        self.assertIn("CHANGELOG.md#031---2026-07-16", readme)
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

    def test_builds_skillhub_channel_package_with_separate_overview_and_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
            output = Path(temp_dir) / f"taohtml-skillhub-v{version}.zip"
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
                self.assertIn("references/agent-workflow.md", names)
                self.assertIn("requirements.txt", names)
                self.assertIn("scripts/preflight.py", names)
                self.assertIn("scripts/profile_store.py", names)
                self.assertIn("scripts/check_production_authorization.py", names)
                self.assertIn("references/profile-memory.md", names)
                self.assertIn("references/production-authorization.md", names)
                self.assertEqual(
                    archive.read("requirements.txt"),
                    (ROOT / "skill" / "taohtml" / "requirements.txt").read_bytes(),
                )
                self.assertEqual(
                    archive.read("scripts/preflight.py"),
                    (ROOT / "skill" / "taohtml" / "scripts" / "preflight.py").read_bytes(),
                )
                self.assertEqual(
                    (archive.getinfo("scripts/preflight.py").external_attr >> 16) & 0o777,
                    0o755,
                )
                self.assertEqual(
                    (archive.getinfo("scripts/profile_store.py").external_attr >> 16)
                    & 0o777,
                    0o755,
                )
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
                self.assertEqual(metadata["version"], version)
                self.assertEqual(metadata["displayName"], "TaoHtml")
                self.assertEqual(metadata["category"], "content-creation")
                self.assertEqual(
                    metadata["tags"],
                    ["HTML演示", "PPT转换", "报告设计", "视觉系统", "企业模板保真"],
                )
                self.assertIn("16:9", metadata["summary"])
                self.assertIn("四套内置视觉系统", metadata["description"])
                self.assertIn("把参考图发给 TaoHtml", metadata["description"])
                self.assertIn("VI 设计标准图供你确认", metadata["description"])
                self.assertNotIn("CSS scroll-snap", metadata["description"])
                expected_summary, expected_description = (
                    skillhub_packager.readme_intro_copy()
                )
                self.assertEqual(metadata["summary"], expected_summary)
                self.assertEqual(metadata["description"], expected_description)
                self.assertEqual(metadata["summary"], EXPECTED_CUSTOMER_OPENING[0])
                self.assertEqual(
                    metadata["description"], "".join(EXPECTED_CUSTOMER_OPENING)
                )

                canonical_text = (
                    ROOT / "skill" / "taohtml" / "SKILL.md"
                ).read_text(encoding="utf-8")
                canonical_body = canonical_text.split("\n---\n", 1)[1]
                self.assertEqual(
                    archive.read("references/agent-workflow.md").decode("utf-8"),
                    canonical_body,
                )
                self.assertEqual(
                    generated_body,
                    skillhub_packager.skillhub_body(version),
                )
                self.assertEqual(
                    skillhub_packager.skillhub_body(version),
                    skillhub_packager.readme_customer_overview(version),
                )
                self.assertNotEqual(generated_body, canonical_body)
                self.assertIn("## Explicit Invocation", canonical_body)
                self.assertNotIn("Explicit Invocation", generated_body)
                self.assertTrue(
                    generated_body.startswith(
                        "# TaoHtml\n\n" + "\n\n".join(EXPECTED_CUSTOMER_OPENING)
                    )
                )
                before_installation = generated_body.split("\n## 安装入口\n", 1)[0]
                self.assertNotIn("agent-workflow.md", before_installation)
                self.assertNotIn("Agent 执行要求（安装后）", generated_body)
                self.assertIn(
                    "Agent 都必须先完整读取同一渠道包内的 `references/agent-workflow.md`",
                    generated_body,
                )
                self.assertIn("用户无需手动打开或加载这些文件", generated_body)
                self.assertIn("均从技能根目录解析", generated_body)

                readme = (ROOT / "README.md").read_text(encoding="utf-8")
                for heading in (
                    "## 核心能力",
                    "## 四套内置视觉系统",
                    "## 使用客户参考图",
                    "## 安装入口",
                    "## 版本更新",
                    "## 作者与合作",
                ):
                    self.assertIn(heading, generated_body)
                for key_copy in (
                    *EXPECTED_CUSTOMER_OPENING,
                    "黑白荧光卡片",
                    "严谨咨询报告",
                    "稳重企业年报",
                    "杂志图文拼贴",
                    "接受 1 张静态参考图，提取可观察的颜色、字体层级、构图、组件和证据语言",
                    "接受同一模板族 1–3 张静态截图，锁定截图中可见的 Logo、页眉、页脚、品牌条和固定装饰",
                    "TaoHtml 由 Tao 发起",
                    "微信：`taomir`",
                ):
                    self.assertIn(key_copy, readme)
                    self.assertIn(key_copy, generated_body)
                self.assertNotRegex(
                    generated_body,
                    r"(?i)<img|!\[[^\]]*\]\(|\.(?:png|jpe?g|webp|gif|svg)\)",
                )
                self.assertNotIn("docs/assets/readme/", generated_body)
                self.assertNotIn("即使不查看下方总览图", generated_body)
                self.assertIn("以下表格直接说明各自的画面特征", generated_body)
                self.assertNotIn("下方全部使用", generated_body)
                self.assertIn("以下说明基于仓库自制、无真实品牌的合成样例", generated_body)
                self.assertNotIn("和高清 VI 标准图", generated_body)
                self.assertIn(
                    f"[GitHub README 的“使用客户参考图”章节]({GITHUB_REPOSITORY}/blob/v{version}/README.md#使用客户参考图)",
                    generated_body,
                )
                self.assertNotIn("## 作者与合作", canonical_text)
                self.assertNotIn("taomir", canonical_text)
                self.assertNotIn("taomir", metadata["summary"])
                self.assertNotIn("taomir", metadata["description"])
                self.assertNotIn(
                    "taomir",
                    (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
                )

    def test_public_channel_descriptions_share_the_current_positioning(self) -> None:
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
        self.assertIn("windows-smoke:", workflow)
        self.assertIn("runs-on: windows-latest", workflow)
        self.assertIn("--profile static-reference", workflow)
        self.assertIn("--profile profile-reuse", workflow)
        self.assertIn("render_reference_vi.py", workflow)
        self.assertIn("compile_project_theme.py", workflow)


if __name__ == "__main__":
    unittest.main()
