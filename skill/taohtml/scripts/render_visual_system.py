#!/usr/bin/env python3
"""Render content through one built-in visual system and the shared runtime shell."""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
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
RASTER_MIME_TYPES = {
    ".png": ("PNG", "image/png"),
    ".jpg": ("JPEG", "image/jpeg"),
    ".jpeg": ("JPEG", "image/jpeg"),
    ".webp": ("WEBP", "image/webp"),
}
SVG_EXTERNAL_REFERENCE = re.compile(
    rb"(?:href|xlink:href|src)\s*=\s*['\"]\s*(?!#|data:)[^'\"]+"
    rb"|url\(\s*['\"]?\s*(?!#|data:)[^)]+|@import\b",
    re.IGNORECASE,
)
SVG_ACTIVE_CONTENT = re.compile(
    rb"<\s*(?:script|foreignObject)\b|\son[a-z]+\s*=", re.IGNORECASE
)


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


def source_data_uri(source_image: Path | None) -> str:
    if source_image is None:
        raise ValueError(
            "Verified local evidence is required: pass --source-image with a readable PNG, JPEG, WebP, or SVG file."
        )
    try:
        path = source_image.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"Source image does not exist: {source_image}") from exc
    if not path.is_file():
        raise ValueError(f"Source image is not a file: {path}")

    suffix = path.suffix.lower()
    if suffix not in {*RASTER_MIME_TYPES, ".svg"}:
        raise ValueError(
            f"Unsupported source image type '{suffix or '<none>'}'; use PNG, JPEG, WebP, or SVG."
        )
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"Source image is not readable: {path}") from exc
    if not payload:
        raise ValueError(f"Source image is empty: {path}")

    if suffix == ".svg":
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise ValueError(f"Source SVG is not readable XML: {path}") from exc
        if root.tag.rsplit("}", 1)[-1].lower() != "svg":
            raise ValueError(f"Source SVG has no <svg> root: {path}")
        if SVG_EXTERNAL_REFERENCE.search(payload):
            raise ValueError(f"Source SVG contains a non-offline external reference: {path}")
        if SVG_ACTIVE_CONTENT.search(payload):
            raise ValueError(f"Source SVG contains active content: {path}")
        mime_type = "image/svg+xml"
    else:
        try:
            from PIL import Image

            with Image.open(path) as image:
                actual_format = image.format
                image.verify()
        except (ImportError, OSError, ValueError) as exc:
            raise ValueError(f"Source image is not a readable {suffix[1:].upper()} file: {path}") from exc
        expected_format, mime_type = RASTER_MIME_TYPES[suffix]
        if actual_format != expected_format:
            raise ValueError(
                f"Source image extension and content disagree: expected {expected_format}, found {actual_format or 'unknown'}."
            )

    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def render_sections(template: str, content: dict[str, str], source_uri: str) -> str:
    values = {key: html.escape(value, quote=True) for key, value in content.items()}
    values["SOURCE_URI"] = html.escape(source_uri, quote=True)
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


def _render_theme(content: dict[str, str], theme_id: str, output: Path, source_uri: str) -> Path:
    manifest = load_manifest(theme_id)
    theme_dir = SYSTEMS_ROOT / theme_id
    css = (theme_dir / "theme.css").read_text(encoding="utf-8").strip()
    sections = render_sections(
        (theme_dir / "templates.html").read_text(encoding="utf-8"), content, source_uri
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


def render_theme(
    content: dict[str, str],
    theme_id: str,
    output: Path,
    source_image: Path | None = None,
) -> Path:
    return _render_theme(content, theme_id, output, source_data_uri(source_image))


def render_all(
    content: dict[str, str],
    output_root: Path,
    source_image: Path | None = None,
) -> list[Path]:
    source_uri = source_data_uri(source_image)
    return [
        _render_theme(content, theme_id, output_root / theme_id / "index.html", source_uri)
        for theme_id in THEME_IDS
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render content and verified local evidence through TaoHtml's built-in visual systems."
    )
    parser.add_argument("--content", type=Path, required=True, help="Flat JSON content object.")
    parser.add_argument(
        "--source-image",
        type=Path,
        required=True,
        help="Verified local PNG, JPEG, WebP, or SVG evidence image to validate and embed for offline use.",
    )
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
            outputs = [
                render_theme(
                    content,
                    args.theme,
                    args.output.resolve(),
                    args.source_image,
                )
            ]
        else:
            if args.output_root is None:
                parser.error("--output-root is required with --all")
            outputs = render_all(content, args.output_root.resolve(), args.source_image)
    except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as exc:
        print(f"RENDER_FAILED: {exc}", file=sys.stderr)
        return 1

    for output in outputs:
        print(f"RENDER_OK {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
