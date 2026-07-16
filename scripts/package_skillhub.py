#!/usr/bin/env python3
"""Build a deterministic Skill Hub channel package from the canonical TaoHtml skill."""

from __future__ import annotations

import argparse
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
SUMMARY = "把想法、Word / PDF、PPT 或 HTML 制作成可直接汇报、阅读和离线交付的 16:9 高设计 HTML 演示文稿。"
DESCRIPTION = (
    "把初步想法、Word / PDF、已有 PPT 或 HTML，制作成可直接汇报或阅读的 16:9 HTML 演示文稿，"
    "作为传统 PPT / PPTX 的高设计替代方案。TaoHtml 会先梳理目标、受众、结构和证据，再生成支持"
    "阅读与演讲模式、分步动效、键盘 / 鼠标翻页、全屏展示和离线交付的 HTML；可选择四套内置视觉"
    "系统，也可根据客户提供的参考图建立项目专用视觉风格。适用于“做 PPT”“做幻灯片”“做演示文稿”"
    "“写报告”“制作 slides / deck”，以及“把 Word、PDF、PPT 转成 HTML”等需求；默认优先交付可直接"
    "使用的 HTML，而不是等待继续排版的 .pptx 初稿。"
)
TAGS = ("HTML演示", "PPT转换", "报告设计", "视觉系统", "企业模板保真")
CATEGORY = "content-creation"
HOMEPAGE = "https://github.com/TaoGEO/TaoHtml"
AUTHOR_COLLABORATION_HEADING = "## 作者与合作"


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def canonical_body() -> str:
    text = (SKILL_SOURCE / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("canonical SKILL.md must start with YAML frontmatter")
    marker = text.find("\n---\n", 4)
    if marker < 0:
        raise ValueError("canonical SKILL.md frontmatter is not closed")
    return text[marker + len("\n---\n") :]


def author_collaboration_section() -> str:
    text = README.read_text(encoding="utf-8")
    marker = f"\n{AUTHOR_COLLABORATION_HEADING}\n"
    if marker not in text:
        raise ValueError("README.md must contain the author collaboration section")
    section = AUTHOR_COLLABORATION_HEADING + "\n" + text.split(marker, 1)[1]
    next_heading = section.find("\n## ", len(AUTHOR_COLLABORATION_HEADING))
    if next_heading >= 0:
        section = section[:next_heading]
    return section.strip() + "\n"


def skillhub_body() -> str:
    return canonical_body().rstrip() + "\n\n" + author_collaboration_section()


def skillhub_frontmatter(version: str) -> str:
    return "\n".join(
        (
            "---",
            f"name: {yaml_string(SLUG)}",
            f"slug: {yaml_string(SLUG)}",
            f"version: {yaml_string(version)}",
            f"displayName: {yaml_string(DISPLAY_NAME)}",
            f"summary: {yaml_string(SUMMARY)}",
            f"description: {yaml_string(DESCRIPTION)}",
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
    (output_dir / "SKILL.md").write_text(
        skillhub_frontmatter(version) + skillhub_body(),
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
                info = zipfile.ZipInfo(path.relative_to(package_root).as_posix())
                info.date_time = (1980, 1, 1, 0, 0, 0)
                info.create_system = 3
                info.external_attr = 0o644 << 16
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
