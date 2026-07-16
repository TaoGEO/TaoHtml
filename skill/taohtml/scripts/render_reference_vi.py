#!/usr/bin/env python3
"""Render a validated single-static-reference VI contract to HTML and PNG."""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = SKILL_ROOT / "assets" / "reference-vi-board" / "template.html"
SCHEMA_VERSION = "1.1"
BOARD_SIZE = (3200, 2400)
EXPORT_VIEWPORT = (1600, 1200)
STATUSES = {"observed", "extension", "unknown"}
STATUS_LABELS = {
    "observed": "直接观察",
    "extension": "报告适配建议",
    "unknown": "参考中无法判断",
}
TOP_LEVEL_KEYS = {
    "schema_version",
    "board",
    "palette",
    "typography",
    "layout",
    "components",
    "imagery",
    "evidence_language",
    "mini_pages",
    "guardrails",
    "executable_layout",
}
SECTION_LIMITS = {
    "palette": (1, 6),
    "typography": (2, 4),
    "layout": (2, 4),
    "components": (2, 4),
    "imagery": (1, 3),
    "evidence_language": (1, 3),
    "mini_pages": (3, 3),
    "guardrails": (2, 6),
}
ITEM_FIELDS = {
    "palette": {"name", "value", "role", "status", "basis"},
    "typography": {"level", "sample", "spec", "status", "basis"},
    "layout": {"label", "value", "status", "basis"},
    "components": {"name", "description", "status", "basis"},
    "imagery": {"label", "description", "status", "basis"},
    "evidence_language": {"label", "description", "sample", "status", "basis"},
    "mini_pages": {"kind", "title", "description", "status", "basis"},
    "guardrails": {"mode", "title", "description", "status", "basis"},
}
EXECUTABLE_LAYOUT_ITEM_FIELDS = {"value", "status", "basis"}
EXECUTABLE_LAYOUT_OPTIONS = {
    "page_axis": {"row", "column", "unknown"},
    "alignment": {"start", "center", "end", "unknown"},
    "cover_structure": {"split", "single-column", "unknown"},
    "cover_split": {"7:5", "5:7", "1:1", "none", "unknown"},
    "content_structure": {"card-grid", "stack", "single-focus", "unknown"},
    "content_columns": {"1", "2", "3", "unknown"},
    "image_placement": {"left", "right", "top", "bottom", "background", "inline", "unknown"},
    "image_aspect_ratio": {"16:9", "4:3", "3:2", "1:1", "3:4", "unknown"},
    "image_fit": {"cover", "contain", "unknown"},
    "image_treatment": {"natural", "muted", "monochrome", "high-contrast", "unknown"},
    "data_structure": {"source-chart-split", "chart-focus", "table-focus", "metrics-grid", "unknown"},
    "data_columns": {"1", "2", "3", "unknown"},
    "module_organization": {"hard-grid", "soft-stack", "open-field", "unknown"},
    "density": {"low", "medium", "high", "unknown"},
    "visual_focus": {"headline-and-image", "headline-only", "image-first", "data-first", "balanced", "unknown"},
}
EXECUTABLE_LAYOUT_LABELS = {
    "page_axis": "页面主轴",
    "alignment": "主要对齐",
    "cover_structure": "封面结构",
    "cover_split": "封面分栏",
    "content_structure": "内容组织",
    "content_columns": "内容列数",
    "image_placement": "图片位置",
    "image_aspect_ratio": "图片比例",
    "image_fit": "图片适配",
    "image_treatment": "图片处理",
    "data_structure": "数据页结构",
    "data_columns": "数据列数",
    "module_organization": "模块组织",
    "density": "信息密度",
    "visual_focus": "视觉焦点",
}
FIELD_LENGTHS = {
    "title": 48,
    "subtitle": 80,
    "reference_label": 48,
    "name": 28,
    "value": 32,
    "role": 44,
    "level": 12,
    "sample": 42,
    "spec": 60,
    "label": 28,
    "description": 88,
    "basis": 88,
    "kind": 12,
    "mode": 12,
    "status": 12,
}
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
UNKNOWN_COLOR_VALUE = "unknown"
FORBIDDEN_ANALYSIS = re.compile(
    r"(?:连续状态|逐步变化|关键帧|时间线|时序|缓动|动态|动效|动画|转场|运动)"
    r"|\b(?:motions?|movements?|animat(?:e|es|ed|ing|ion|ions)|transitions?|timelines?|"
    r"timing|sequences?|sequential(?:ly)?|easing|keyframes?|morph(?:s|ed|ing)?)\b",
    re.IGNORECASE,
)
NEGATION_BEFORE = re.compile(
    r"(?:未见|未展示|未出现|不含|不包含|不涉及|不支持|不分析|不检查|不推断|不输出|"
    r"不判断|无法判断|不能判断|不可判断)"
    r"|(?:不|未|禁止|不得|不要|不可|无需)(?:从|由|基于|在|把)?"
    r"[^，,。；;！？!?\n]{0,24}(?:推断|分析|检查|输出|判断|展示|出现|包含|涉及|支持|"
    r"建立|定义|写入|加入|描述|写成|作为|使用|采用)"
    r"|\b(?:unsupported|not supported|absent|not inferred|cannot infer)\b"
    r"|\b(?:cannot|can't|do not|don't|must not|should not|never)\b"
    r"[^,.;!?\n]{0,32}\b(?:infer|analy[sz]e|inspect|check|output|establish|define|observe|"
    r"determine|support|include|describe|write|use|apply|add)\b",
    re.IGNORECASE,
)
DIRECT_NEGATION_BEFORE = re.compile(
    r"(?:没有|无|非)|\b(?:no|not|without)\b", re.IGNORECASE
)
NEGATED_LIST_FILLER = re.compile(
    r"(?:任何|明确的|可识别的|可判断的|可推断的|可确认的|规则|语法|描述|信息|证据|"
    r"分析|推断|状态|行为|内容|设计|线索|的|、|，|,|/|和|与|或|及|以及)"
    r"|\b(?:any|a|an|or|and|nor|rules?|cues?|descriptions?|inferences?|analysis|"
    r"information|evidence|behaviou?r|states?|design)\b|[\s:/-]+",
    re.IGNORECASE,
)
NEGATION_AFTER = re.compile(
    r"^(?:(?:规则|语法|信息|行为|线索|设计|状态)?(?:在参考(?:图|中)?|由单帧)?)?"
    r"(?:未展示|未出现|无法判断|不能判断|不可判断|未知|不支持|不分析|不推断|不输出)"
    r"|^(?:\s+(?:rules?|cues?|behaviou?r|states?|design))?\s*"
    r"(?:is|are|was|were)?\s*(?:not shown|cannot be inferred|can not be inferred|"
    r"is unknown|are unknown|is unsupported|are unsupported)\b",
    re.IGNORECASE,
)
STRONG_CLAUSE_BREAK = re.compile(r"[。；;！？!?\n]")
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


def _require_exact_keys(value: object, expected: set[str], path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object.")
    actual = set(value)
    if actual != expected:
        missing = ", ".join(sorted(expected - actual)) or "none"
        extra = ", ".join(sorted(actual - expected)) or "none"
        raise ValueError(f"{path} keys mismatch; missing: {missing}; extra: {extra}.")
    return value


def _require_text(value: object, field: str, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}.{field} must be a non-empty string.")
    text = value.strip()
    limit = FIELD_LENGTHS.get(field, 88)
    if len(text) > limit:
        raise ValueError(f"{path}.{field} exceeds {limit} characters.")
    if _contains_dynamic_rule(text):
        raise ValueError(
            f"{path}.{field} contains unsupported dynamic-analysis wording for a single static reference."
        )
    return text


def _contains_dynamic_rule(text: str) -> bool:
    """Return whether text asserts a dynamic rule instead of denying that inference."""
    for match in FORBIDDEN_ANALYSIS.finditer(text):
        before = text[: match.start()]
        after = text[match.end() :]
        clause_start = max(
            (separator.end() for separator in STRONG_CLAUSE_BREAK.finditer(before)),
            default=0,
        )
        clause_prefix = before[clause_start:]
        negated = False
        for pattern in (NEGATION_BEFORE, DIRECT_NEGATION_BEFORE):
            negations = list(pattern.finditer(clause_prefix))
            if not negations:
                continue
            governed_text = clause_prefix[negations[-1].end() :]
            simplified = FORBIDDEN_ANALYSIS.sub(" ", governed_text)
            simplified = NEGATED_LIST_FILLER.sub(" ", simplified)
            if len(governed_text) <= 64 and not simplified.strip():
                negated = True
                break
        if negated:
            continue
        if NEGATION_AFTER.search(after[:64]):
            continue
        return True
    return False


def _validate_item(section: str, raw: object, index: int) -> dict[str, str]:
    path = f"{section}[{index}]"
    item = _require_exact_keys(raw, ITEM_FIELDS[section], path)
    normalized = {
        field: _require_text(item[field], field, path) for field in ITEM_FIELDS[section]
    }
    if normalized["status"] not in STATUSES:
        raise ValueError(
            f"{path}.status must be one of: {', '.join(sorted(STATUSES))}."
        )
    if section == "palette":
        if normalized["status"] == "unknown":
            if normalized["value"] != UNKNOWN_COLOR_VALUE:
                raise ValueError(
                    f"{path}.value must be '{UNKNOWN_COLOR_VALUE}' when the color is unknown; "
                    "a real hex value would fabricate a color fact."
                )
        elif not HEX_COLOR.fullmatch(normalized["value"]):
            raise ValueError(
                f"{path}.value must be a six-digit hex color such as #112233 "
                "when status is observed or extension."
            )
    if section == "mini_pages" and normalized["kind"] not in {"cover", "content", "data"}:
        raise ValueError(f"{path}.kind must be cover, content, or data.")
    if section == "guardrails" and normalized["mode"] not in {"preserve", "avoid"}:
        raise ValueError(f"{path}.mode must be preserve or avoid.")
    if section == "evidence_language":
        samples = {"bar", "line", "table", "metric", "citation", "none"}
        if normalized["sample"] not in samples:
            raise ValueError(
                f"{path}.sample must be one of: {', '.join(sorted(samples))}."
            )
        if normalized["status"] == "observed" and normalized["sample"] == "none":
            raise ValueError(f"{path} cannot mark an absent evidence sample as observed.")
        if normalized["status"] == "unknown" and normalized["sample"] != "none":
            raise ValueError(f"{path} must use sample 'none' when evidence is unknown.")
    return normalized


def _validate_executable_layout(raw: object) -> dict[str, dict[str, str]]:
    layout = _require_exact_keys(raw, set(EXECUTABLE_LAYOUT_OPTIONS), "executable_layout")
    normalized: dict[str, dict[str, str]] = {}
    for field, options in EXECUTABLE_LAYOUT_OPTIONS.items():
        path = f"executable_layout.{field}"
        item = _require_exact_keys(layout[field], EXECUTABLE_LAYOUT_ITEM_FIELDS, path)
        value = _require_text(item["value"], "value", path)
        status = _require_text(item["status"], "status", path)
        basis = _require_text(item["basis"], "basis", path)
        if status not in STATUSES:
            raise ValueError(f"{path}.status must be one of: {', '.join(sorted(STATUSES))}.")
        if value not in options:
            raise ValueError(f"{path}.value must be one of: {', '.join(sorted(options))}.")
        if status == "unknown" and value != "unknown":
            raise ValueError(f"{path}.value must be 'unknown' when status is unknown.")
        if status != "unknown" and value == "unknown":
            raise ValueError(f"{path}.value cannot be 'unknown' when status is {status}.")
        normalized[field] = {"value": value, "status": status, "basis": basis}
    cover = normalized["cover_structure"]["value"]
    split = normalized["cover_split"]["value"]
    if cover == "single-column" and split not in {"none", "unknown"}:
        raise ValueError("executable_layout.cover_split must be none for a single-column cover.")
    if cover == "split" and split == "none":
        raise ValueError("executable_layout.cover_split cannot be none for a split cover.")
    return normalized


def validate_contract(raw: object) -> dict[str, Any]:
    contract = _require_exact_keys(raw, TOP_LEVEL_KEYS, "contract")
    if contract["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}.")

    board = _require_exact_keys(
        contract["board"], {"title", "subtitle", "reference_label"}, "board"
    )
    normalized: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "board": {
            field: _require_text(board[field], field, "board")
            for field in ("title", "subtitle", "reference_label")
        },
    }

    normalized["executable_layout"] = _validate_executable_layout(
        contract["executable_layout"]
    )

    statuses: set[str] = {
        item["status"] for item in normalized["executable_layout"].values()
    }
    for section, (minimum, maximum) in SECTION_LIMITS.items():
        raw_items = contract[section]
        if not isinstance(raw_items, list):
            raise ValueError(f"{section} must be a list.")
        if not minimum <= len(raw_items) <= maximum:
            raise ValueError(
                f"{section} must contain between {minimum} and {maximum} items."
            )
        items = [_validate_item(section, item, index) for index, item in enumerate(raw_items)]
        statuses.update(item["status"] for item in items)
        normalized[section] = items

    mini_kinds = [item["kind"] for item in normalized["mini_pages"]]
    if set(mini_kinds) != {"cover", "content", "data"} or len(set(mini_kinds)) != 3:
        raise ValueError("mini_pages must contain exactly one cover, one content, and one data item.")
    guardrail_modes = {item["mode"] for item in normalized["guardrails"]}
    if guardrail_modes != {"preserve", "avoid"}:
        raise ValueError("guardrails must include at least one preserve and one avoid item.")
    if statuses != STATUSES:
        missing = ", ".join(sorted(STATUSES - statuses))
        raise ValueError(f"The contract must expose all three boundary statuses; missing: {missing}.")
    return normalized


def load_contract(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError(f"VI data must be UTF-8 JSON: {path}") from exc
    except OSError as exc:
        raise ValueError(f"VI data is not readable: {path}") from exc
    return validate_contract(raw)


def source_data_uri(source_image: Path) -> str:
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
            raise ValueError(
                f"Source image is not a readable {suffix[1:].upper()} file: {path}"
            ) from exc
        expected_format, mime_type = RASTER_MIME_TYPES[suffix]
        if actual_format != expected_format:
            raise ValueError(
                f"Source image extension and content disagree: expected {expected_format}, "
                f"found {actual_format or 'unknown'}."
            )

    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _e(value: str) -> str:
    return html.escape(value, quote=True)


def _status(item: dict[str, str]) -> str:
    status = item["status"]
    return f'<span class="status status-{status}">{STATUS_LABELS[status]}</span>'


def _basis(item: dict[str, str]) -> str:
    return f'<p class="item-basis">{_e(item["basis"])}</p>'


def _info_item(item: dict[str, str], heading: str, value: str) -> str:
    return (
        '<article class="info-item">'
        f'<div class="info-head"><strong>{_e(item[heading])}</strong>{_status(item)}</div>'
        f'<p class="info-value">{_e(item[value])}</p>{_basis(item)}'
        "</article>"
    )


def _render_palette(items: Iterable[dict[str, str]]) -> str:
    swatches: list[str] = []
    for item in items:
        if item["status"] == "unknown":
            color_sample = (
                '<div class="swatch-color swatch-color-unknown" '
                'aria-label="参考中无法判断颜色"></div>'
            )
            value_label = "未识别色值"
            article_class = "swatch swatch-unknown"
        else:
            color_sample = (
                f'<div class="swatch-color" style="background:{_e(item["value"])}"></div>'
            )
            value_label = item["value"].upper()
            article_class = "swatch"
        swatches.append(
            f'<article class="{article_class}">{color_sample}'
            f'<div><h3>{_e(item["name"])}</h3><code>{_e(value_label)}</code>'
            f'<p>{_e(item["role"])}</p>{_status(item)}{_basis(item)}</div>'
            "</article>"
        )
    return "".join(swatches)


def _render_typography(items: Iterable[dict[str, str]]) -> str:
    return "".join(
        '<article class="type-row">'
        f'<div class="type-level">{_e(item["level"])}</div>'
        f'<div class="type-sample">{_e(item["sample"])}</div>'
        f'<div class="type-spec">{_status(item)}<p>{_e(item["spec"])}</p>{_basis(item)}</div>'
        "</article>"
        for item in items
    )


def _render_components(items: Iterable[dict[str, str]]) -> str:
    return "".join(
        '<article class="component">'
        f'{_status(item)}<h3>{_e(item["name"])}</h3><p>{_e(item["description"])}</p>{_basis(item)}'
        "</article>"
        for item in items
    )


def _render_executable_layout(items: dict[str, dict[str, str]]) -> str:
    return "".join(
        '<article class="grammar-item">'
        f'<div class="grammar-head"><strong>{_e(EXECUTABLE_LAYOUT_LABELS[field])}</strong>'
        f'{_status(item)}</div><code>{_e(item["value"])}</code>{_basis(item)}</article>'
        for field, item in items.items()
    )


def _render_guardrails(items: Iterable[dict[str, str]]) -> str:
    groups: list[str] = []
    for mode, label in (("preserve", "保留项"), ("avoid", "禁用项")):
        body = "".join(
            '<article class="info-item">'
            f'<div class="info-head"><strong>{_e(item["title"])}</strong>{_status(item)}</div>'
            f'<p class="info-value">{_e(item["description"])}</p>{_basis(item)}'
            "</article>"
            for item in items
            if item["mode"] == mode
        )
        groups.append(f'<div class="guardrail-group {mode}"><h3>{label}</h3>{body}</div>')
    return "".join(groups)


def _render_evidence_sample(items: Iterable[dict[str, str]]) -> str:
    observed = next((item for item in items if item["status"] == "observed"), None)
    if observed is None:
        return (
            '<div class="evidence-sample evidence-empty" role="note">'
            "<strong>参考中未出现</strong><span>保持未知，不补画证据语法</span></div>"
        )
    sample = observed["sample"]
    if sample == "bar":
        body = "<i></i><i></i><i></i>"
    elif sample == "line":
        body = (
            '<svg viewBox="0 0 180 180" role="img" aria-label="折线语言示意">'
            '<polyline points="12,148 64,104 110,121 168,42" fill="none" '
            'stroke="currentColor" stroke-width="12"/></svg>'
        )
    elif sample == "table":
        body = "".join("<i></i>" for _ in range(9))
    elif sample == "metric":
        body = "<strong>42</strong><span>直接数值</span>"
    else:
        body = "<i></i><i></i><i></i><i></i>"
    return (
        f'<div class="evidence-sample evidence-{sample}" '
        f'aria-label="{_e(observed["label"])}示意">{body}</div>'
    )


def _render_mini_pages(items: Iterable[dict[str, str]]) -> str:
    by_kind = {item["kind"]: item for item in items}
    cards: list[str] = []
    for kind in ("cover", "content", "data"):
        item = by_kind[kind]
        if kind == "cover":
            canvas = (
                '<div class="mini-canvas"><div class="mini-title">'
                f'{_e(item["title"])}</div><div class="mini-rule"></div></div>'
            )
        elif kind == "content":
            canvas = '<div class="mini-canvas"><div></div><div></div></div>'
        else:
            canvas = '<div class="mini-canvas"><i></i><i></i><i></i></div>'
        cards.append(
            f'<article class="mini-page-card mini-{kind}">{canvas}'
            f'<div class="mini-copy">{_status(item)}<h3>{_e(item["title"])}</h3>'
            f'<p>{_e(item["description"])}</p>{_basis(item)}</div></article>'
        )
    return "".join(cards)


def render_html(contract: dict[str, Any], source_uri: str) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    colors = [
        item["value"]
        for item in contract["palette"]
        if item["status"] != "unknown"
    ]
    if colors:
        colors = [colors[index % len(colors)] for index in range(4)]
    else:
        colors = [
            "var(--board-ink)",
            "var(--unknown-soft)",
            "var(--unknown)",
            "var(--board-paper)",
        ]
    board_style = ";".join(
        f"--sample-{index}:{color}" for index, color in enumerate(colors, start=1)
    )
    reference_alt = _e(contract["board"]["reference_label"])
    replacements = {
        "DOCUMENT_TITLE": _e(contract["board"]["title"]),
        "BOARD_TITLE": _e(contract["board"]["title"]),
        "BOARD_SUBTITLE": _e(contract["board"]["subtitle"]),
        "BOARD_STYLE": _e(board_style),
        "REFERENCE_IMAGE": f'<img src="{_e(source_uri)}" alt="{reference_alt}">',
        "CROP_IMAGE": f'<img src="{_e(source_uri)}" alt="{reference_alt}的裁切示意">',
        "REFERENCE_LABEL": reference_alt,
        "PALETTE_ITEMS": _render_palette(contract["palette"]),
        "TYPOGRAPHY_ITEMS": _render_typography(contract["typography"]),
        "LAYOUT_ITEMS": "".join(
            _info_item(item, "label", "value") for item in contract["layout"]
        ),
        "COMPONENT_ITEMS": _render_components(contract["components"]),
        "IMAGERY_ITEMS": "".join(
            _info_item(item, "label", "description") for item in contract["imagery"]
        ),
        "EVIDENCE_ITEMS": "".join(
            _info_item(item, "label", "description")
            for item in contract["evidence_language"]
        ),
        "EVIDENCE_SAMPLE": _render_evidence_sample(contract["evidence_language"]),
        "GUARDRAIL_GROUPS": _render_guardrails(contract["guardrails"]),
        "MINI_PAGE_ITEMS": _render_mini_pages(contract["mini_pages"]),
        "EXECUTABLE_LAYOUT_ITEMS": _render_executable_layout(
            contract["executable_layout"]
        ),
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "SCHEMA_VERSION_LABEL": SCHEMA_VERSION,
    }
    rendered = template
    for marker, value in replacements.items():
        token = "{{" + marker + "}}"
        if rendered.count(token) != 1:
            raise ValueError(f"Template marker must appear exactly once: {token}")
        rendered = rendered.replace(token, value)
    unresolved = re.findall(r"\{\{[A-Z][A-Z0-9_]*\}\}", rendered)
    if unresolved:
        raise ValueError(f"Unresolved template markers remain: {', '.join(unresolved)}")
    return rendered


def export_png(html_path: Path, png_path: Path) -> Path:
    try:
        from PIL import Image
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ValueError(
            "PNG export requires Pillow and Playwright from the project requirements."
        ) from exc

    width, height = EXPORT_VIEWPORT
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=["--disable-gpu"])
            page = browser.new_page(
                viewport={"width": width, "height": height}, device_scale_factor=2
            )
            page.goto(html_path.as_uri(), wait_until="load")
            page.add_style_tag(
                content="""
                    html, body {
                      width: 1600px !important;
                      min-width: 1600px !important;
                      height: 1200px !important;
                      min-height: 1200px !important;
                    }
                    #vi-board {
                      transform: scale(.5);
                      transform-origin: top left;
                    }
                """
            )
            page.evaluate("document.fonts.ready")
            page.evaluate(
                "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
            )
            page.wait_for_timeout(200)
            board = page.locator("#vi-board")
            bounds = board.bounding_box()
            if bounds is None:
                raise ValueError("Rendered VI board is not visible in the browser.")
            actual = (round(bounds["width"]), round(bounds["height"]))
            if actual != EXPORT_VIEWPORT:
                raise ValueError(
                    f"Rendered VI board size mismatch: expected {EXPORT_VIEWPORT}, found {actual}."
                )
            overflowing = page.locator(".panel").evaluate_all(
                """nodes => nodes
                    .filter(node => node.scrollWidth > node.clientWidth || node.scrollHeight > node.clientHeight)
                    .map(node => node.querySelector('h2')?.textContent || 'unnamed panel')"""
            )
            if overflowing:
                raise ValueError(
                    "Rendered VI board has clipped panels: " + ", ".join(overflowing)
                )
            board.screenshot(path=str(png_path))
            browser.close()
    except PlaywrightError as exc:
        png_path.unlink(missing_ok=True)
        raise ValueError(
            "Chromium PNG export failed. Install the project browser with "
            "`python -m playwright install chromium`."
        ) from exc

    try:
        with Image.open(png_path) as image:
            image.verify()
    except OSError as exc:
        png_path.unlink(missing_ok=True)
        raise ValueError(f"PNG verification failed: {png_path}") from exc
    with Image.open(png_path) as image:
        actual_format, actual_size = image.format, image.size
    if actual_format != "PNG" or actual_size != BOARD_SIZE:
        png_path.unlink(missing_ok=True)
        raise ValueError(
            f"PNG verification failed: expected PNG {BOARD_SIZE}, "
            f"found {actual_format} {actual_size}."
        )
    return png_path


def render_board(
    contract: dict[str, Any], source_image: Path, output_base: Path
) -> tuple[Path, Path]:
    normalized = validate_contract(contract)
    source_uri = source_data_uri(source_image)
    output_base = output_base.expanduser().resolve()
    if output_base.suffix:
        raise ValueError("--output must be a base path without a file extension.")
    output_base.parent.mkdir(parents=True, exist_ok=True)
    html_path = output_base.with_suffix(".html")
    png_path = output_base.with_suffix(".png")
    html_path.write_text(render_html(normalized, source_uri), encoding="utf-8")
    png_path.unlink(missing_ok=True)
    export_png(html_path, png_path)
    return html_path, png_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a single-static-reference VI contract to deterministic HTML and a 3200x2400 PNG."
    )
    parser.add_argument("--data", type=Path, required=True, help="UTF-8 VI contract JSON.")
    parser.add_argument(
        "--source-image",
        type=Path,
        required=True,
        help="Verified local PNG, JPEG, WebP, or safe offline SVG reference.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output base path without extension; .html and .png are created.",
    )
    args = parser.parse_args()

    try:
        contract = load_contract(args.data.resolve())
        html_path, png_path = render_board(contract, args.source_image, args.output)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"REFERENCE_VI_RENDER_FAILED: {exc}", file=sys.stderr)
        return 1

    print(f"REFERENCE_VI_HTML_OK {html_path}")
    print(f"REFERENCE_VI_PNG_OK {png_path} {BOARD_SIZE[0]}x{BOARD_SIZE[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
