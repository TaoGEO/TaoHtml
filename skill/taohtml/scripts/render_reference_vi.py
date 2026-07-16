#!/usr/bin/env python3
"""Render a validated single-static-reference VI contract to HTML and PNG."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from project_theme_layout import (
    EXECUTABLE_LAYOUT_OPTIONS_WITH_UNKNOWN,
    resolve_layout_items,
)


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = SKILL_ROOT / "assets" / "reference-vi-board" / "template.html"
SCHEMA_VERSION = "1.2"
LEGACY_SCHEMA_VERSION = "1.1"
BOARD_SIZE = (3200, 2400)
EXPORT_VIEWPORT = (1600, 1200)
STATUSES = {"observed", "extension", "unknown"}
STATUS_LABELS = {
    "observed": "直接观察",
    "extension": "报告适配建议",
    "unknown": "参考中无法判断",
}
BASE_TOP_LEVEL_KEYS = {
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
CORPORATE_TOP_LEVEL_KEYS = BASE_TOP_LEVEL_KEYS | {
    "reference_mode",
    "source_image",
    "locked_regions",
    "editable_regions",
    "extension_pages",
    "limitations",
}
REFERENCE_MODES = {"reconstruct", "corporate_fidelity"}
LOCKED_REGION_FIELDS = {"id", "type", "bbox", "status", "basis", "extraction"}
EDITABLE_REGION_FIELDS = {"id", "bbox", "allowed_content", "basis"}
EXTENSION_PAGE_FIELDS = {"role", "status", "basis"}
LIMITATION_FIELDS = {"item", "status", "basis"}
SOURCE_IMAGE_FIELDS = {"sha256", "width", "height"}
LOCKED_REGION_TYPES = {"logo", "header", "footer", "brand_bar", "decoration"}
PAGE_ROLES = {"cover", "content", "process", "data", "closing"}
EXTENSION_PAGE_ROLES = {"cover", "section", "data"}
REGION_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CORPORATE_MIN_SOURCE_SIZE = (960, 540)
CORPORATE_MIN_CROP_SIZE = (24, 24)
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
EXECUTABLE_LAYOUT_OPTIONS = EXECUTABLE_LAYOUT_OPTIONS_WITH_UNKNOWN
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
    resolve_layout_items(normalized)
    return normalized


def _validate_bbox(raw: object, path: str) -> list[float]:
    if (
        not isinstance(raw, list)
        or len(raw) != 4
        or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in raw)
    ):
        raise ValueError(f"{path} must be [x, y, width, height] with four numbers.")
    bbox = [float(value) for value in raw]
    if any(not math.isfinite(value) for value in bbox):
        raise ValueError(f"{path} values must be finite.")
    x, y, width, height = bbox
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError(f"{path} must use non-negative x/y and positive width/height.")
    if x > 1 or y > 1 or width > 1 or height > 1 or x + width > 1 or y + height > 1:
        raise ValueError(f"{path} must stay inside normalized coordinates 0..1.")
    return bbox


def _bbox_overlap(first: list[float], second: list[float]) -> bool:
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    return min(ax + aw, bx + bw) > max(ax, bx) and min(ay + ah, by + bh) > max(ay, by)


def _validate_source_image(raw: object) -> dict[str, object]:
    source = _require_exact_keys(raw, SOURCE_IMAGE_FIELDS, "source_image")
    digest = source["sha256"]
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise ValueError("source_image.sha256 must be a lowercase SHA-256 digest.")
    dimensions: dict[str, int] = {}
    for field in ("width", "height"):
        value = source[field]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"source_image.{field} must be a positive integer.")
        dimensions[field] = value
    return {"sha256": digest, **dimensions}


def _validate_locked_regions(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list) or not 1 <= len(raw) <= 12:
        raise ValueError("locked_regions must contain between 1 and 12 fixed elements.")
    normalized: list[dict[str, object]] = []
    ids: set[str] = set()
    for index, value in enumerate(raw):
        path = f"locked_regions[{index}]"
        item = _require_exact_keys(value, LOCKED_REGION_FIELDS, path)
        region_id = _require_text(item["id"], "id", path)
        if not REGION_ID.fullmatch(region_id) or region_id in ids:
            raise ValueError(f"{path}.id must be a unique lowercase hyphenated id.")
        ids.add(region_id)
        region_type = _require_text(item["type"], "type", path)
        if region_type not in LOCKED_REGION_TYPES:
            raise ValueError(
                f"{path}.type must be one of: {', '.join(sorted(LOCKED_REGION_TYPES))}."
            )
        status = _require_text(item["status"], "status", path)
        if status != "observed":
            raise ValueError(f"{path}.status must be observed for a locked visible element.")
        extraction = _require_text(item["extraction"], "extraction", path)
        if extraction != "crop":
            raise ValueError(
                f"{path}.extraction must be crop; fixed brand elements are never model-redrawn."
            )
        normalized.append(
            {
                "id": region_id,
                "type": region_type,
                "bbox": _validate_bbox(item["bbox"], f"{path}.bbox"),
                "status": status,
                "basis": _require_text(item["basis"], "basis", path),
                "extraction": extraction,
            }
        )
    return normalized


def _validate_editable_regions(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list) or len(raw) != 1:
        raise ValueError(
            "editable_regions must contain exactly one safe content region in corporate_fidelity v1."
        )
    item = _require_exact_keys(raw[0], EDITABLE_REGION_FIELDS, "editable_regions[0]")
    region_id = _require_text(item["id"], "id", "editable_regions[0]")
    if not REGION_ID.fullmatch(region_id):
        raise ValueError("editable_regions[0].id must be a lowercase hyphenated id.")
    roles = item["allowed_content"]
    if (
        not isinstance(roles, list)
        or not roles
        or any(not isinstance(role, str) or role not in PAGE_ROLES for role in roles)
        or len(set(roles)) != len(roles)
    ):
        raise ValueError(
            "editable_regions[0].allowed_content must be a unique non-empty list of supported page roles."
        )
    if set(roles) != PAGE_ROLES:
        raise ValueError(
            "editable_regions[0].allowed_content must allow cover, content, process, data, and closing for the five-page shell."
        )
    return [
        {
            "id": region_id,
            "bbox": _validate_bbox(item["bbox"], "editable_regions[0].bbox"),
            "allowed_content": list(roles),
            "basis": _require_text(item["basis"], "basis", "editable_regions[0]"),
        }
    ]


def _validate_extension_pages(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list) or not 2 <= len(raw) <= 3:
        raise ValueError("extension_pages must contain two or three proposed corporate page roles.")
    normalized: list[dict[str, str]] = []
    roles: set[str] = set()
    for index, value in enumerate(raw):
        path = f"extension_pages[{index}]"
        item = _require_exact_keys(value, EXTENSION_PAGE_FIELDS, path)
        role = _require_text(item["role"], "role", path)
        if role not in EXTENSION_PAGE_ROLES or role in roles:
            raise ValueError(f"{path}.role must be a unique cover, section, or data role.")
        roles.add(role)
        status = _require_text(item["status"], "status", path)
        if status != "extension":
            raise ValueError(
                f"{path}.status must be extension; page types not visible in the screenshot cannot be observed."
            )
        normalized.append(
            {
                "role": role,
                "status": status,
                "basis": _require_text(item["basis"], "basis", path),
            }
        )
    return normalized


def _validate_limitations(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list) or not 1 <= len(raw) <= 6:
        raise ValueError("limitations must contain between one and six explicit unknowns or limits.")
    normalized: list[dict[str, str]] = []
    for index, value in enumerate(raw):
        path = f"limitations[{index}]"
        item = _require_exact_keys(value, LIMITATION_FIELDS, path)
        status = _require_text(item["status"], "status", path)
        if status != "unknown":
            raise ValueError(f"{path}.status must be unknown.")
        normalized.append(
            {
                "item": _require_text(item["item"], "item", path),
                "status": status,
                "basis": _require_text(item["basis"], "basis", path),
            }
        )
    return normalized


def validate_contract(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("contract must be an object.")
    schema_version = raw.get("schema_version")
    if schema_version == LEGACY_SCHEMA_VERSION:
        contract = _require_exact_keys(raw, BASE_TOP_LEVEL_KEYS, "contract")
    elif schema_version == SCHEMA_VERSION:
        contract = _require_exact_keys(raw, CORPORATE_TOP_LEVEL_KEYS, "contract")
    else:
        raise ValueError(
            f"schema_version must be {LEGACY_SCHEMA_VERSION} or {SCHEMA_VERSION}."
        )

    board = _require_exact_keys(
        contract["board"], {"title", "subtitle", "reference_label"}, "board"
    )
    normalized: dict[str, Any] = {
        "schema_version": schema_version,
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

    if schema_version == LEGACY_SCHEMA_VERSION:
        return normalized

    mode = contract["reference_mode"]
    if mode not in REFERENCE_MODES:
        raise ValueError(
            f"reference_mode must be one of: {', '.join(sorted(REFERENCE_MODES))}."
        )
    normalized["reference_mode"] = mode
    normalized["source_image"] = _validate_source_image(contract["source_image"])
    if mode == "reconstruct":
        for field in ("locked_regions", "editable_regions", "extension_pages", "limitations"):
            if contract[field] != []:
                raise ValueError(f"{field} must be empty when reference_mode is reconstruct.")
            normalized[field] = []
        return normalized

    normalized["locked_regions"] = _validate_locked_regions(contract["locked_regions"])
    normalized["editable_regions"] = _validate_editable_regions(contract["editable_regions"])
    normalized["extension_pages"] = _validate_extension_pages(contract["extension_pages"])
    normalized["limitations"] = _validate_limitations(contract["limitations"])
    editable = normalized["editable_regions"][0]
    for locked in normalized["locked_regions"]:
        if _bbox_overlap(locked["bbox"], editable["bbox"]):
            raise ValueError(
                f"locked_regions.{locked['id']} overlaps editable_regions.{editable['id']}; "
                "fixed corporate elements and report content must not conflict."
            )
    extension_roles = {item["role"] for item in normalized["extension_pages"]}
    mini_to_extension_role = {"cover": "cover", "content": "section", "data": "data"}
    for item in normalized["mini_pages"]:
        role = mini_to_extension_role[item["kind"]]
        if role in extension_roles and item["status"] != "extension":
            raise ValueError(
                f"corporate_fidelity mini page {item['kind']} is unseen and must be extension."
            )
        if role not in extension_roles and item["status"] != "observed":
            raise ValueError(
                f"corporate_fidelity mini page {item['kind']} must be observed or listed in extension_pages."
            )
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


def source_image_binding(source_image: Path) -> dict[str, object]:
    try:
        path = source_image.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"Source image does not exist: {source_image}") from exc
    if path.suffix.lower() not in RASTER_MIME_TYPES:
        raise ValueError(
            "corporate_fidelity requires exactly one raster PNG, JPEG, or WebP screenshot."
        )
    source_data_uri(path)
    try:
        from PIL import Image

        with Image.open(path) as image:
            width, height = image.size
    except (ImportError, OSError, ValueError) as exc:
        raise ValueError(f"Corporate source image is not readable: {path}") from exc
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "width": width,
        "height": height,
    }


def validate_source_binding(contract: dict[str, Any], source_image: Path) -> dict[str, object]:
    if contract.get("schema_version") == LEGACY_SCHEMA_VERSION:
        source_data_uri(source_image)
        return {}
    actual = source_image_binding(source_image)
    declared = contract["source_image"]
    if actual != declared:
        raise ValueError(
            "source_image sha256 or dimensions do not match the current screenshot."
        )
    if contract.get("reference_mode") == "corporate_fidelity":
        minimum_width, minimum_height = CORPORATE_MIN_SOURCE_SIZE
        if actual["width"] < minimum_width or actual["height"] < minimum_height:
            raise ValueError(
                "Corporate screenshot resolution is too low for reliable fixed-element extraction; "
                f"need at least {minimum_width}x{minimum_height}, got {actual['width']}x{actual['height']}."
            )
    return actual


def _pixel_bbox(bbox: list[float], width: int, height: int) -> list[int]:
    x, y, region_width, region_height = bbox
    left = math.floor(round(x * width, 10))
    top = math.floor(round(y * height, 10))
    right = math.ceil(round((x + region_width) * width, 10))
    bottom = math.ceil(round((y + region_height) * height, 10))
    return [left, top, right, bottom]


def extract_locked_regions(
    contract: dict[str, Any], source_image: Path
) -> list[dict[str, object]]:
    if contract.get("reference_mode") != "corporate_fidelity":
        return []
    binding = validate_source_binding(contract, source_image)
    try:
        from PIL import Image

        with Image.open(source_image) as image:
            source = image.convert("RGBA")
            extracted: list[dict[str, object]] = []
            for region in contract["locked_regions"]:
                pixel_bbox = _pixel_bbox(
                    region["bbox"], int(binding["width"]), int(binding["height"])
                )
                crop_width = pixel_bbox[2] - pixel_bbox[0]
                crop_height = pixel_bbox[3] - pixel_bbox[1]
                minimum_width, minimum_height = CORPORATE_MIN_CROP_SIZE
                if crop_width < minimum_width or crop_height < minimum_height:
                    raise ValueError(
                        f"Locked region {region['id']} is only {crop_width}x{crop_height}px; "
                        "request a clearer screenshot or an independent logo instead of redrawing it."
                    )
                crop = source.crop(tuple(pixel_bbox))
                buffer = io.BytesIO()
                crop.save(buffer, format="PNG", optimize=False, compress_level=9)
                payload = buffer.getvalue()
                extracted.append(
                    {
                        **region,
                        "pixel_bbox": pixel_bbox,
                        "width": crop_width,
                        "height": crop_height,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "data_uri": "data:image/png;base64,"
                        + base64.b64encode(payload).decode("ascii"),
                    }
                )
    except (ImportError, OSError, ValueError) as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"Corporate fixed-element extraction failed: {source_image}") from exc
    return extracted


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


def _bbox_style(bbox: list[float]) -> str:
    x, y, width, height = bbox
    return (
        f"left:{x * 100:.6f}%;top:{y * 100:.6f}%;"
        f"width:{width * 100:.6f}%;height:{height * 100:.6f}%"
    )


def _render_reference_image(
    contract: dict[str, Any], source_uri: str, reference_alt: str
) -> str:
    if contract.get("reference_mode") != "corporate_fidelity":
        return f'<img src="{_e(source_uri)}" alt="{reference_alt}">'
    overlays = "".join(
        f'<span class="reference-overlay locked-overlay" style="{_bbox_style(item["bbox"])}" '
        f'data-locked-region="{_e(item["id"])}">{_e(item["id"])}</span>'
        for item in contract["locked_regions"]
    )
    overlays += "".join(
        f'<span class="reference-overlay editable-overlay" style="{_bbox_style(item["bbox"])}" '
        f'data-editable-region="{_e(item["id"])}">SAFE</span>'
        for item in contract["editable_regions"]
    )
    width = contract["source_image"]["width"]
    height = contract["source_image"]["height"]
    return (
        f'<div class="reference-image-stack" style="aspect-ratio:{width}/{height}">'
        f'<img src="{_e(source_uri)}" alt="{reference_alt}">{overlays}</div>'
    )


def _render_locked_region_items(items: list[dict[str, object]]) -> str:
    labels = {
        "logo": "Logo",
        "header": "页眉",
        "footer": "页脚",
        "brand_bar": "品牌条",
        "decoration": "固定装饰",
    }
    return "".join(
        '<article class="component locked-item" data-fixed-element="true">'
        f'{_status(item)}<h3>{_e(labels[item["type"]])} · {_e(item["id"])}</h3>'
        f'<p>{_e(item["basis"])}</p><code>{_e(json.dumps(item["bbox"]))}</code>'
        "</article>"
        for item in items
    )


def _render_crop_previews(items: list[dict[str, object]]) -> str:
    return "".join(
        '<article class="crop-preview">'
        f'<img src="{_e(item["data_uri"])}" alt="{_e(item["id"])} 固定元素裁切">'
        f'<strong>{_e(item["id"])}</strong><span>{item["width"]}×{item["height"]} px</span>'
        f'<code>{_e(item["sha256"][:12])}…</code></article>'
        for item in items
    )


def _render_editable_preview(contract: dict[str, Any]) -> str:
    if contract.get("reference_mode") != "corporate_fidelity":
        return '<span class="generic-safe-label">SAFE<br>AREA</span>'
    locked = "".join(
        f'<span class="safe-locked" style="{_bbox_style(item["bbox"])}"></span>'
        for item in contract["locked_regions"]
    )
    editable = contract["editable_regions"][0]
    return (
        f'{locked}<span class="safe-editable" style="{_bbox_style(editable["bbox"])}">'
        f'{_e(editable["id"])}<small>仅此区域可排版与动效</small></span>'
    )


def _render_editable_items(contract: dict[str, Any]) -> str:
    if contract.get("reference_mode") != "corporate_fidelity":
        return "".join(
            _info_item(item, "label", "value") for item in contract["layout"]
        )
    return "".join(
        '<article class="info-item">'
        f'<div class="info-head"><strong>{_e(item["id"])}</strong>'
        '<span class="status status-extension">可编辑安全区</span></div>'
        f'<p class="info-value">{_e(" / ".join(item["allowed_content"]))}</p>'
        f'<p class="item-basis">{_e(item["basis"])}</p></article>'
        for item in contract["editable_regions"]
    )


def _render_limitations(contract: dict[str, Any]) -> str:
    if contract.get("reference_mode") != "corporate_fidelity":
        return ""
    return (
        '<div class="limitations-group"><h3>未知项 / 限制</h3>'
        + "".join(
            '<article class="info-item">'
            f'<div class="info-head"><strong>{_e(item["item"])}</strong>{_status(item)}</div>'
            f'{_basis(item)}</article>'
            for item in contract["limitations"]
        )
        + "</div>"
    )


def _render_mini_pages(
    items: Iterable[dict[str, str]],
    contract: dict[str, Any] | None = None,
    extracted_regions: list[dict[str, object]] | None = None,
) -> str:
    by_kind = {item["kind"]: item for item in items}
    cards: list[str] = []
    corporate = bool(contract and contract.get("reference_mode") == "corporate_fidelity")
    shell = ""
    editable = ""
    if corporate and extracted_regions:
        shell = "".join(
            f'<img class="mini-fixed-region" src="{_e(region["data_uri"])}" '
            f'alt="" style="{_bbox_style(region["bbox"])}">'
            for region in extracted_regions
        )
        editable_region = contract["editable_regions"][0]
        editable = (
            f'<span class="mini-editable-region" style="{_bbox_style(editable_region["bbox"])}"></span>'
        )
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
        if corporate:
            canvas = canvas.replace('class="mini-canvas"', 'class="mini-canvas corporate-mini-canvas"', 1)
            canvas = canvas.replace('>', f'>{shell}{editable}', 1)
        cards.append(
            f'<article class="mini-page-card mini-{kind}">{canvas}'
            f'<div class="mini-copy">{_status(item)}<h3>{_e(item["title"])}</h3>'
            f'<p>{_e(item["description"])}</p>{_basis(item)}</div></article>'
        )
    return "".join(cards)


def render_html(
    contract: dict[str, Any],
    source_uri: str,
    extracted_regions: list[dict[str, object]] | None = None,
) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    corporate = contract.get("reference_mode") == "corporate_fidelity"
    if corporate and extracted_regions is None:
        raise ValueError(
            "corporate_fidelity VI rendering requires deterministic locked-region crops."
        )
    extracted_regions = extracted_regions or []
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
    if corporate:
        imagery_body = (
            '<div class="crop-preview-grid">'
            + _render_crop_previews(extracted_regions)
            + "</div>"
        )
        component_items = _render_locked_region_items(contract["locked_regions"])
        reference_caption = "企业模板保真｜红框为固定元素，绿框为可编辑安全区"
        components_title = "固定企业元素清单"
        footer_note = "截图中可见效果保真｜固定层无动效｜未见页面只作延展建议"
        reference_mode = "corporate_fidelity"
    else:
        imagery_body = (
            f'<div class="crop-demo"><img src="{_e(source_uri)}" '
            f'alt="{reference_alt}的裁切示意"></div><div class="stack">'
            + "".join(
                _info_item(item, "label", "description")
                for item in contract["imagery"]
            )
            + "</div>"
        )
        component_items = _render_components(contract["components"])
        reference_caption = "单张静态参考｜提取设计语言并允许重新构图"
        components_title = "卡片 · 面板 · 标签 · 边框"
        footer_note = "三类边界已显式标注｜结构字段可机器校验｜缺失类别保持未知"
        reference_mode = contract.get("reference_mode", "reconstruct")
    replacements = {
        "DOCUMENT_TITLE": _e(contract["board"]["title"]),
        "BOARD_TITLE": _e(contract["board"]["title"]),
        "BOARD_SUBTITLE": _e(contract["board"]["subtitle"]),
        "BOARD_STYLE": _e(board_style),
        "REFERENCE_IMAGE": _render_reference_image(contract, source_uri, reference_alt),
        "REFERENCE_LABEL": reference_alt,
        "REFERENCE_CAPTION": reference_caption,
        "REFERENCE_MODE": reference_mode,
        "PALETTE_ITEMS": _render_palette(contract["palette"]),
        "TYPOGRAPHY_ITEMS": _render_typography(contract["typography"]),
        "EDITABLE_REGION_PREVIEW": _render_editable_preview(contract),
        "LAYOUT_ITEMS": _render_editable_items(contract),
        "COMPONENTS_PANEL_TITLE": components_title,
        "COMPONENT_ITEMS": component_items,
        "IMAGERY_BODY": imagery_body,
        "EVIDENCE_ITEMS": "".join(
            _info_item(item, "label", "description")
            for item in contract["evidence_language"]
        ),
        "EVIDENCE_SAMPLE": _render_evidence_sample(contract["evidence_language"]),
        "GUARDRAIL_GROUPS": _render_guardrails(contract["guardrails"]),
        "LIMITATION_ITEMS": _render_limitations(contract),
        "MINI_PAGE_ITEMS": _render_mini_pages(
            contract["mini_pages"], contract, extracted_regions
        ),
        "EXECUTABLE_LAYOUT_ITEMS": _render_executable_layout(
            contract["executable_layout"]
        ),
        "SCHEMA_VERSION": contract["schema_version"],
        "SCHEMA_VERSION_LABEL": contract["schema_version"],
        "FOOTER_NOTE": footer_note,
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
    validate_source_binding(normalized, source_image)
    extracted_regions = extract_locked_regions(normalized, source_image)
    output_base = output_base.expanduser().resolve()
    if output_base.suffix:
        raise ValueError("--output must be a base path without a file extension.")
    output_base.parent.mkdir(parents=True, exist_ok=True)
    html_path = output_base.with_suffix(".html")
    png_path = output_base.with_suffix(".png")
    html_path.write_text(
        render_html(normalized, source_uri, extracted_regions), encoding="utf-8"
    )
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
