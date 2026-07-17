#!/usr/bin/env python3
"""Build a deterministic Skill Hub package with separate overview and Agent rules."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_SOURCE = ROOT / "skill" / "taohtml"
README = ROOT / "README.md"
SLUG = "taohtml"
DISPLAY_NAME = "TaoHtml"
TAGS = ("HTML演示", "PPT转换", "报告设计", "视觉系统", "企业模板保真")
CATEGORY = "content-creation"
HOMEPAGE = "https://github.com/TaoGEO/TaoHtml"
AGENT_WORKFLOW_REFERENCE = Path("references/agent-workflow.md")


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def canonical_execution_body() -> str:
    text = (SKILL_SOURCE / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("canonical SKILL.md must start with YAML frontmatter")
    marker = text.find("\n---\n", 4)
    if marker < 0:
        raise ValueError("canonical SKILL.md frontmatter is not closed")
    return text[marker + len("\n---\n") :]


def readme_intro_copy() -> tuple[str, str]:
    text = README.read_text(encoding="utf-8")
    if not text.startswith("# TaoHtml\n") or "\n## 核心能力\n" not in text:
        raise ValueError("README.md must start with TaoHtml customer introduction")
    intro = text.split("\n## 核心能力\n", 1)[0].splitlines()[1:]
    paragraphs = [
        paragraph.strip()
        for paragraph in "\n".join(intro).split("\n\n")
        if paragraph.strip()
        and not paragraph.startswith("> English brief:")
        and not paragraph.startswith("当前版本：")
    ]
    if len(paragraphs) < 4:
        raise ValueError("README.md must contain four Chinese introduction paragraphs")
    plain = [re.sub(r"[`*_]", "", paragraph) for paragraph in paragraphs[:4]]
    return plain[0], "".join(plain)


def html_table_to_markdown(match: re.Match[str]) -> str:
    items: list[str] = []
    for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", match.group(0), re.DOTALL):
        cell = re.sub(
            r"<a\b[^>]*>\s*<img\b[^>]*>\s*</a>", "", cell, flags=re.DOTALL
        )
        strong = re.search(r"<strong>(.*?)</strong>", cell, re.DOTALL)
        if strong is None:
            continue
        title = html.unescape(re.sub(r"<[^>]+>", "", strong.group(1))).strip()
        detail = cell[strong.end() :]
        detail = re.sub(r"<br\s*/?>", " ", detail, flags=re.IGNORECASE)
        detail = html.unescape(re.sub(r"<[^>]+>", " ", detail))
        detail = re.sub(r"\s+", " ", detail).strip()
        if title and detail:
            items.append(f"- **{title}**：{detail}")
    if not items:
        raise ValueError("README HTML table must contain text-only customer copy")
    return "\n".join(items)


def absolute_repository_links(text: str, version: str) -> str:
    def replace(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2)
        if re.match(r"(?:https?://|mailto:|#)", target):
            return match.group(0)
        path, separator, fragment = target.partition("#")
        view = "tree" if path in {"skill/taohtml"} else "blob"
        absolute = f"{HOMEPAGE}/{view}/v{version}/{path}"
        if separator:
            absolute += f"#{fragment}"
        return f"[{label}]({absolute})"

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace, text)


def apply_text_only_channel_copy(text: str, version: str) -> str:
    replacements = {
        (
            "四套系统的对比使用完全相同的合成内容，各展示 5 页、共 20 页，便于直接比较完整的版式语言，"
            "而不是被选题差异干扰；即使不查看下方总览图，也可以通过表格了解各自的画面特征。"
        ): (
            "四套系统的对比使用完全相同的合成内容，各展示 5 页、共 20 页，便于直接比较完整的版式语言，"
            "而不是被选题差异干扰；以下表格直接说明各自的画面特征。"
        ),
        (
            "这两条路线共享“静态参考 → VI 设计标准图 → 当前版本确认 → 项目专用主题”的确认链，但保真目标不同。"
            "下方全部使用仓库自制、无真实品牌的合成样例。"
        ): (
            "这两条路线共享“静态参考 → VI 设计标准图 → 当前版本确认 → 项目专用主题”的确认链，但保真目标不同。"
            "以下说明基于仓库自制、无真实品牌的合成样例。"
        ),
        (
            "企业模板保真只承诺截图中可见的像素与页面角色，不宣称恢复原始 PPT 母版、矢量 Logo、字体源文件、"
            "截图外资产或动效。可查看仓库中的[完整五页 HTML 样例]"
            "(examples/corporate-template-fidelity/corporate-fidelity-sample.html)和[高清 VI 标准图]"
            "(examples/corporate-template-fidelity/reference-vi-board.png)。"
        ): (
            "企业模板保真只承诺截图中可见的像素与页面角色，不宣称恢复原始 PPT 母版、矢量 Logo、字体源文件、"
            "截图外资产或动效。可前往[GitHub README 的“使用客户参考图”章节]"
            f"({HOMEPAGE}/blob/v{version}/README.md#使用客户参考图)查看完整五页 HTML 样例与 VI 标准图。"
        ),
    }
    for source, replacement in replacements.items():
        if source not in text:
            raise ValueError(f"README.md text-only channel source copy drifted: {source[:32]}")
        text = text.replace(source, replacement, 1)
    return text


def readme_customer_overview(version: str) -> str:
    text = README.read_text(encoding="utf-8")
    if not text.startswith("# TaoHtml\n"):
        raise ValueError("README.md must start with '# TaoHtml'")
    for heading in (
        "## 核心能力",
        "## 四套内置视觉系统",
        "## 使用客户参考图",
        "## 安装入口",
        "## 版本更新",
        "## 作者与合作",
    ):
        if f"\n{heading}\n" not in text:
            raise ValueError(f"README.md is missing required customer heading: {heading}")

    text = apply_text_only_channel_copy(text, version)
    text = re.sub(r"(?m)^> English brief:.*\n?", "", text)
    text = re.sub(r"(?s)<table>.*?</table>", html_table_to_markdown, text)
    text = re.sub(
        r"(?m)^[ \t]*<a\b[^>]*>\s*<img\b[^>]*>\s*</a>[ \t]*$\n?",
        "",
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+\.(?:png|jpe?g|webp|gif|svg)(?:#[^)]*)?)\)",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )
    text = absolute_repository_links(text, version)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    lowered = text.lower()
    if any(marker in lowered for marker in ("<img", "docs/assets/readme/", ".png)")):
        raise ValueError("Skill Hub overview must not contain README image references")
    return text


def skillhub_body(version: str) -> str:
    return readme_customer_overview(version)


def skillhub_frontmatter(version: str) -> str:
    summary, description = readme_intro_copy()
    return "\n".join(
        (
            "---",
            f"name: {yaml_string(SLUG)}",
            f"slug: {yaml_string(SLUG)}",
            f"version: {yaml_string(version)}",
            f"displayName: {yaml_string(DISPLAY_NAME)}",
            f"summary: {yaml_string(summary)}",
            f"description: {yaml_string(description)}",
            f"tags: {json.dumps(TAGS, ensure_ascii=False)}",
            f"category: {yaml_string(CATEGORY)}",
            f"license: {yaml_string('MIT')}",
            f"homepage: {yaml_string(HOMEPAGE)}",
            "---",
            "",
        )
    )


def build_directory(output_dir: Path, version: str) -> None:
    shutil.copytree(
        SKILL_SOURCE,
        output_dir,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    (output_dir / AGENT_WORKFLOW_REFERENCE).write_text(
        canonical_execution_body(),
        encoding="utf-8",
    )
    (output_dir / "SKILL.md").write_text(
        skillhub_frontmatter(version) + skillhub_body(version),
        encoding="utf-8",
    )


def package(output_zip: Path, version: str) -> None:
    output_zip = output_zip.resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="taohtml-skillhub-") as temp_dir:
        package_root = Path(temp_dir) / SLUG
        build_directory(package_root, version)
        with zipfile.ZipFile(
            output_zip, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for path in sorted(package_root.rglob("*")):
                if not path.is_file():
                    continue
                relative = path.relative_to(package_root).as_posix()
                info = zipfile.ZipInfo(relative)
                info.date_time = (1980, 1, 1, 0, 0, 0)
                info.create_system = 3
                mode = (
                    0o755
                    if relative
                    in {"scripts/preflight.py", "scripts/profile_store.py"}
                    else 0o644
                )
                info.external_attr = mode << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
    print(f"Packaged TaoHtml Skill Hub {version}: {output_zip}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Package the canonical TaoHtml skill for Skill Hub."
    )
    parser.add_argument("output_zip", type=Path)
    parser.add_argument(
        "--version",
        default=(ROOT / "VERSION").read_text(encoding="utf-8").strip(),
    )
    args = parser.parse_args()
    if args.output_zip.suffix.lower() != ".zip":
        parser.error("output path must end in .zip")
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        parser.error("version must use MAJOR.MINOR.PATCH")
    package(args.output_zip, args.version)


if __name__ == "__main__":
    main()
