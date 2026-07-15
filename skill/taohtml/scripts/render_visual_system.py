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
SOURCE_KINDS = ("verified", "illustrative")
ILLUSTRATIVE_MARKER = re.compile(
    r"示意|模拟|待核实|illustrative|simulation|pending verification", re.IGNORECASE
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


def local_image_data_uri(source_image: Path) -> str:
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


def illustrative_placeholder_data_uri() -> str:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760">
<rect width="1200" height="760" fill="#f3f1e9"/><rect x="70" y="70" width="1060" height="620" rx="28" fill="#fff" stroke="#17202a" stroke-width="3" stroke-dasharray="12 12"/>
<path d="M150 560L350 390L520 470L760 245L1045 420" fill="none" stroke="#17202a" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="350" cy="390" r="24" fill="#d7ff3f" stroke="#17202a" stroke-width="8"/><circle cx="760" cy="245" r="24" fill="#ff7a33" stroke="#17202a" stroke-width="8"/>
<text x="150" y="175" font-family="Arial,sans-serif" font-size="42" font-weight="700" fill="#17202a">示意内容 · 待核实</text>
<text x="150" y="225" font-family="Arial,sans-serif" font-size="24" fill="#53606d">No verified source image was supplied.</text>
</svg>"""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def resolve_source(
    source_image: Path | None,
    source_kind: str | None,
) -> tuple[str, str]:
    """Validate and embed a source image without inferring verified provenance.

    A caller must explicitly pass ``verified`` after grounding the local file in
    confirmed source material. Omitting ``source_kind`` is always fail-safe and
    illustrative, whether or not a local image is supplied.
    """
    resolved_kind = source_kind or "illustrative"
    if resolved_kind not in SOURCE_KINDS:
        raise ValueError(f"Unknown source kind: {resolved_kind}")
    if resolved_kind == "verified" and source_image is None:
        raise ValueError(
            "Verified local evidence requires --source-image with a readable PNG, JPEG, WebP, or SVG file."
        )
    source_uri = (
        local_image_data_uri(source_image)
        if source_image is not None
        else illustrative_placeholder_data_uri()
    )
    return source_uri, resolved_kind


def render_sections(
    template: str,
    content: dict[str, str],
    source_uri: str,
    source_kind: str,
) -> str:
    values = {key: html.escape(value, quote=True) for key, value in content.items()}
    if source_kind == "illustrative":
        source_text = content.get("S4_SOURCE", "")
        if not ILLUSTRATIVE_MARKER.search(source_text):
            source_text = f"示意 / 待核实 · {source_text or '生成视觉'}"
        values["S4_SOURCE"] = html.escape(source_text, quote=True)
        source_label = "示意内容图片（待核实）"
    else:
        source_label = "来源证据图片（已核实）"
    values["SOURCE_URI"] = html.escape(source_uri, quote=True)
    values["SOURCE_LABEL"] = html.escape(source_label, quote=True)
    values["SOURCE_KIND"] = source_kind
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


def _render_theme(
    content: dict[str, str],
    theme_id: str,
    output: Path,
    source_uri: str,
    source_kind: str,
) -> Path:
    manifest = load_manifest(theme_id)
    theme_dir = SYSTEMS_ROOT / theme_id
    css = (theme_dir / "theme.css").read_text(encoding="utf-8").strip()
    sections = render_sections(
        (theme_dir / "templates.html").read_text(encoding="utf-8"),
        content,
        source_uri,
        source_kind,
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
    source_kind: str | None = None,
) -> Path:
    """Render one theme; an omitted source kind always means illustrative."""
    source_uri, resolved_kind = resolve_source(source_image, source_kind)
    return _render_theme(content, theme_id, output, source_uri, resolved_kind)


def render_all(
    content: dict[str, str],
    output_root: Path,
    source_image: Path | None = None,
    source_kind: str | None = None,
) -> list[Path]:
    """Render every theme; verified provenance must be explicitly declared."""
    source_uri, resolved_kind = resolve_source(source_image, source_kind)
    return [
        _render_theme(
            content,
            theme_id,
            output_root / theme_id / "index.html",
            source_uri,
            resolved_kind,
        )
        for theme_id in THEME_IDS
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render content through TaoHtml's built-in visual systems with verified or illustrative local visuals."
    )
    parser.add_argument("--content", type=Path, required=True, help="Flat JSON content object.")
    parser.add_argument(
        "--source-image",
        type=Path,
        help="Local PNG, JPEG, WebP, or SVG image to validate and embed. Omit for an automatically labeled illustrative placeholder.",
    )
    parser.add_argument(
        "--source-kind",
        choices=SOURCE_KINDS,
        help="Use verified only for grounded source material; illustrative is labeled next to the visual. Defaults to illustrative even when --source-image is supplied.",
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
                    args.source_kind,
                )
            ]
        else:
            if args.output_root is None:
                parser.error("--output-root is required with --all")
            outputs = render_all(
                content,
                args.output_root.resolve(),
                args.source_image,
                args.source_kind,
            )
    except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as exc:
        print(f"RENDER_FAILED: {exc}", file=sys.stderr)
        return 1

    for output in outputs:
        print(f"RENDER_OK {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
