#!/usr/bin/env python3
"""Render content through one built-in visual system and the shared runtime shell."""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SYSTEMS_ROOT = SKILL_ROOT / "assets" / "visual-systems"
SHELL_PATH = SKILL_ROOT / "assets" / "html-deck-template" / "index.html"
THEME_IDS = (
    "black-white-fluorescent-cards",
    "rigorous-consulting-report",
    "corporate-annual-report",
    "editorial-collage",
)
START_MARKER = "    <!-- TAOHTML_SLIDES_START -->"
END_MARKER = "    <!-- TAOHTML_SLIDES_END -->"
PLACEHOLDER = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


def load_content(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        raise ValueError("Content must be a non-empty JSON object.")
    invalid = sorted(key for key, value in raw.items() if not isinstance(key, str) or not isinstance(value, str))
    if invalid:
        raise ValueError(f"Every content field must be a string: {', '.join(invalid)}")
    return raw


def load_manifest(theme_id: str) -> dict[str, object]:
    if theme_id not in THEME_IDS:
        raise ValueError(f"Unknown theme: {theme_id}")
    manifest_path = SYSTEMS_ROOT / theme_id / "theme.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("id") != theme_id:
        raise ValueError(f"Theme manifest id mismatch: {manifest_path}")
    return manifest


def source_data_uri() -> str:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760">
<rect width="1200" height="760" fill="#f6f3e8"/><rect x="64" y="56" width="1072" height="648" rx="24" fill="#ffffff" stroke="#17202a" stroke-width="3"/>
<text x="112" y="132" font-family="Arial,sans-serif" font-size="30" font-weight="700" fill="#17202a">固定内容样张 · 合成证据记录</text>
<text x="112" y="184" font-family="Arial,sans-serif" font-size="20" fill="#53606d">用于比较四套视觉系统，不代表真实客户数据</text>
<line x1="112" y1="226" x2="1088" y2="226" stroke="#c7ced6" stroke-width="2"/>
<text x="112" y="294" font-family="Arial,sans-serif" font-size="22" font-weight="700" fill="#17202a">证据条目</text>
<text x="112" y="344" font-family="Arial,sans-serif" font-size="20" fill="#17202a">案例归档：12 个项目，统一字段后可检索</text>
<text x="112" y="390" font-family="Arial,sans-serif" font-size="20" fill="#17202a">引用准备：8 个案例完成来源与结论绑定</text>
<text x="112" y="436" font-family="Arial,sans-serif" font-size="20" fill="#17202a">销售复用：6 个案例进入提案与复盘场景</text>
<rect x="112" y="500" width="976" height="112" rx="12" fill="#17202a"/>
<text x="152" y="550" font-family="Arial,sans-serif" font-size="18" fill="#b9c2cc">结论</text>
<text x="152" y="586" font-family="Arial,sans-serif" font-size="24" font-weight="700" fill="#ffffff">证据必须同时保留来源、语境、结论与可复用入口。</text>
</svg>"""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def render_sections(template: str, content: dict[str, str]) -> str:
    values = {key: html.escape(value, quote=True) for key, value in content.items()}
    values["SOURCE_URI"] = source_data_uri()
    required = set(PLACEHOLDER.findall(template))
    missing = sorted(required - values.keys())
    if missing:
        raise ValueError(f"Missing content fields: {', '.join(missing)}")
    rendered = PLACEHOLDER.sub(lambda match: values[match.group(1)], template)
    if PLACEHOLDER.search(rendered):
        raise ValueError("Unresolved visual-system placeholder remains.")
    if rendered.count('<section class="slide') < 5:
        raise ValueError("A visual system must render at least five slides.")
    return rendered.strip()


def render_theme(content: dict[str, str], theme_id: str, output: Path) -> Path:
    manifest = load_manifest(theme_id)
    theme_dir = SYSTEMS_ROOT / theme_id
    css = (theme_dir / "theme.css").read_text(encoding="utf-8").strip()
    sections = render_sections(
        (theme_dir / "templates.html").read_text(encoding="utf-8"), content
    )
    if "</style>" in css.lower():
        raise ValueError(f"Theme CSS contains a closing style tag: {theme_id}")

    shell = SHELL_PATH.read_text(encoding="utf-8")
    if shell.count(START_MARKER) != 1 or shell.count(END_MARKER) != 1:
        raise ValueError("Runtime shell is missing unique slide markers.")
    prefix, remainder = shell.split(START_MARKER, 1)
    _, suffix = remainder.split(END_MARKER, 1)
    rendered = f"{prefix}{START_MARKER}\n{sections}\n{END_MARKER}{suffix}"

    theme_style = (
        f'  <style id="taohtml-visual-system" data-theme-id="{theme_id}">\n'
        f"{css}\n"
        "  </style>\n"
    )
    rendered = rendered.replace("</head>", f"{theme_style}</head>", 1)
    rendered = rendered.replace('<html lang="en">', '<html lang="zh-CN">', 1)
    rendered = re.sub(
        r"<title>.*?</title>",
        f"<title>{html.escape(content.get('DOCUMENT_TITLE', 'TaoHtml'), quote=False)}</title>",
        rendered,
        count=1,
        flags=re.DOTALL,
    )
    display_name = html.escape(str(manifest["display_name"]), quote=True)
    rendered = rendered.replace(
        '<main class="deck" id="deck">',
        f'<main class="deck" id="deck" data-theme="{theme_id}" data-theme-name="{display_name}">',
        1,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    return output


def render_all(content: dict[str, str], output_root: Path) -> list[Path]:
    return [
        render_theme(content, theme_id, output_root / theme_id / "index.html")
        for theme_id in THEME_IDS
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render deterministic content through TaoHtml's built-in visual systems."
    )
    parser.add_argument("--content", type=Path, required=True, help="Flat JSON content object.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--theme", choices=THEME_IDS)
    mode.add_argument("--all", action="store_true")
    parser.add_argument("--output", type=Path, help="Output HTML for --theme.")
    parser.add_argument("--output-root", type=Path, help="Output directory for --all.")
    args = parser.parse_args()

    try:
        content = load_content(args.content.resolve())
        if args.theme:
            if args.output is None:
                parser.error("--output is required with --theme")
            outputs = [render_theme(content, args.theme, args.output.resolve())]
        else:
            if args.output_root is None:
                parser.error("--output-root is required with --all")
            outputs = render_all(content, args.output_root.resolve())
    except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as exc:
        print(f"RENDER_FAILED: {exc}", file=sys.stderr)
        return 1

    for output in outputs:
        print(f"RENDER_OK {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
