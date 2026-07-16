#!/usr/bin/env python3
"""Compile a confirmed static-reference VI handoff into a project theme."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import render_reference_vi


SCHEMA_VERSION = "1.0"
TOP_LEVEL_KEYS = {
    "schema_version",
    "project",
    "confirmation",
    "inputs",
    "target_mode",
    "customer_corrections",
}
OUTPUT_FILES = {"theme.json", "theme.css", "templates.html", "provenance.json"}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
NUMBER_PX = re.compile(r"(?P<value>\d{1,3})(?:\s*[–—-]\s*\d{1,3})?\s*px", re.IGNORECASE)
PERCENT = re.compile(r"(?P<value>\d{1,2})\s*%")


def _exact_object(raw: object, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object.")
    actual = set(raw)
    if actual != keys:
        missing = ", ".join(sorted(keys - actual)) or "none"
        extra = ", ".join(sorted(actual - keys)) or "none"
        raise ValueError(f"{label} keys mismatch; missing: {missing}; extra: {extra}.")
    return raw


def _text(value: object, label: str, maximum: int = 120) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    normalized = value.strip()
    if len(normalized) > maximum:
        raise ValueError(f"{label} exceeds {maximum} characters.")
    return normalized


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_input(root: Path, value: object, label: str) -> Path:
    relative = Path(_text(value, label, 240))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label} must be a safe path relative to the handoff file.")
    try:
        resolved = (root / relative).resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"{label} does not exist: {relative}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes the handoff directory: {relative}") from exc
    if not resolved.is_file():
        raise ValueError(f"{label} is not a file: {relative}")
    return resolved


def load_handoff(path: Path) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    try:
        handoff_path = path.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"Handoff request does not exist: {path}") from exc
    if not handoff_path.is_file():
        raise ValueError(f"Handoff request is not a file: {handoff_path}")
    try:
        raw = json.loads(handoff_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Handoff request is not valid JSON: {exc}") from exc
    request = _exact_object(raw, TOP_LEVEL_KEYS, "handoff")
    if request["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"handoff.schema_version must be {SCHEMA_VERSION}.")

    project = _exact_object(request["project"], {"id", "display_name"}, "handoff.project")
    project_id = _text(project["id"], "handoff.project.id", 48)
    if not SLUG.fullmatch(project_id):
        raise ValueError("handoff.project.id must be a lowercase hyphenated slug.")
    display_name = _text(project["display_name"], "handoff.project.display_name", 80)

    confirmation = _exact_object(
        request["confirmation"],
        {"status", "phrase", "vi_contract_sha256", "reference_image_sha256"},
        "handoff.confirmation",
    )
    if confirmation["status"] != "confirmed" or confirmation["phrase"] != "确认 VI":
        raise ValueError('VI is not confirmed; status must be "confirmed" and phrase must be "确认 VI".')
    for field in ("vi_contract_sha256", "reference_image_sha256"):
        if not isinstance(confirmation[field], str) or not SHA256.fullmatch(confirmation[field]):
            raise ValueError(f"handoff.confirmation.{field} must be a lowercase SHA-256 digest.")

    inputs = _exact_object(
        request["inputs"], {"vi_contract", "reference_image"}, "handoff.inputs"
    )
    root = handoff_path.parent.resolve()
    vi_path = _safe_input(root, inputs["vi_contract"], "handoff.inputs.vi_contract")
    reference_path = _safe_input(root, inputs["reference_image"], "handoff.inputs.reference_image")
    if _sha256(vi_path) != confirmation["vi_contract_sha256"]:
        raise ValueError("Confirmed VI contract hash does not match the current file.")
    if _sha256(reference_path) != confirmation["reference_image_sha256"]:
        raise ValueError("Confirmed reference image hash does not match the current file.")

    target_mode = request["target_mode"]
    if target_mode not in {"reading", "presentation"}:
        raise ValueError("handoff.target_mode must be reading or presentation.")
    corrections = request["customer_corrections"]
    if not isinstance(corrections, list) or len(corrections) > 20:
        raise ValueError("handoff.customer_corrections must be a list of at most 20 strings.")
    normalized_corrections = [
        _text(value, f"handoff.customer_corrections[{index}]", 180)
        for index, value in enumerate(corrections)
    ]

    contract = render_reference_vi.load_contract(vi_path)
    render_reference_vi.source_data_uri(reference_path)
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "project": {"id": project_id, "display_name": display_name},
        "confirmation": dict(confirmation),
        "inputs": {
            "vi_contract": vi_path.name,
            "reference_image": reference_path.name,
        },
        "target_mode": target_mode,
        "customer_corrections": normalized_corrections,
    }
    return normalized, contract, vi_path, reference_path


def _luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _palette_token(
    items: list[dict[str, str]],
    token: str,
    keywords: tuple[str, ...],
    fallback: str,
    used: set[int],
    *,
    prefer_dark: bool = False,
    prefer_light: bool = False,
) -> tuple[str, dict[str, str]]:
    candidates = [
        (index, item)
        for index, item in enumerate(items)
        if item["status"] != "unknown" and HEX.fullmatch(item["value"])
    ]
    matches = [
        (index, item)
        for index, item in candidates
        if any(keyword in f"{item['name']} {item['role']}" for keyword in keywords)
    ]
    available = [(index, item) for index, item in (matches or candidates) if index not in used]
    if available:
        if prefer_dark:
            index, item = min(available, key=lambda entry: _luminance(entry[1]["value"]))
        elif prefer_light:
            index, item = max(available, key=lambda entry: _luminance(entry[1]["value"]))
        else:
            index, item = available[0]
        used.add(index)
        return item["value"].upper(), {
            "status": item["status"],
            "source": f"palette[{index}]",
            "basis": item["basis"],
        }
    return fallback, {
        "status": "fallback",
        "source": "compiler-neutral-default",
        "basis": f"VI did not provide a usable {token} color; neutral reversible fallback.",
    }


def _first_item(
    items: list[dict[str, str]], predicate: Callable[[dict[str, str]], bool]
) -> tuple[int, dict[str, str]] | None:
    return next(
        ((index, item) for index, item in enumerate(items) if item["status"] != "unknown" and predicate(item)),
        None,
    )


def _size_token(
    items: list[dict[str, str]],
    levels: tuple[str, ...],
    fallback: int,
    token: str,
) -> tuple[str, dict[str, str]]:
    result = _first_item(items, lambda item: item["level"].upper() in levels)
    if result:
        index, item = result
        match = NUMBER_PX.search(item["spec"])
        if match:
            value = int(match.group("value"))
            return f"{value}px", {
                "status": item["status"],
                "source": f"typography[{index}]",
                "basis": item["basis"],
            }
    return f"{fallback}px", {
        "status": "fallback",
        "source": "compiler-neutral-default",
        "basis": f"VI did not provide a parseable {token} size; neutral reversible fallback.",
    }


def _spacing_token(contract: dict[str, Any]) -> tuple[str, dict[str, str]]:
    result = _first_item(
        contract["layout"],
        lambda item: any(word in item["label"] for word in ("间距", "留白", "外边距")),
    )
    if result:
        index, item = result
        px = NUMBER_PX.search(item["value"])
        if px:
            return f"{int(px.group('value'))}px", {
                "status": item["status"],
                "source": f"layout[{index}]",
                "basis": item["basis"],
            }
        percent = PERCENT.search(item["value"])
        if percent:
            computed = round(1600 * int(percent.group("value")) / 100)
            return f"{computed}px", {
                "status": item["status"],
                "source": f"layout[{index}]",
                "basis": f"{item['basis']}；按 1600px 画布确定性换算。",
            }
    return "64px", {
        "status": "fallback",
        "source": "compiler-neutral-default",
        "basis": "VI did not provide parseable canvas spacing; neutral reversible fallback.",
    }


def _boundary_records(contract: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for section in render_reference_vi.SECTION_LIMITS:
        for index, item in enumerate(contract[section]):
            status = item["status"]
            records.append(
                {
                    "path": f"{section}[{index}]",
                    "status": status,
                    "basis": item["basis"],
                    "compiled": status != "unknown",
                    "rule": "unknown is retained as uncompiled boundary" if status == "unknown" else "eligible for deterministic theme compilation",
                }
            )
    return records


def _compile_tokens(contract: dict[str, Any]) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    used: set[int] = set()
    colors: dict[str, str] = {}
    sources: dict[str, dict[str, str]] = {}
    color_specs = (
        ("canvas", ("画布", "底色", "纸张", "背景"), "#F4F2E9", False, True),
        ("ink", ("墨", "标题", "边框", "结构线", "正文"), "#17191A", True, False),
        ("signal", ("强调", "结论", "主要数据", "主色", "砖红"), "#B94B3F", False, False),
        ("accent", ("次级", "章节", "标签", "金", "黄"), "#C8A64B", False, False),
        ("panel", ("面板", "反白", "深", "图片"), "#233C37", True, False),
    )
    for token, keywords, fallback, dark, light in color_specs:
        colors[token], sources[f"colors.{token}"] = _palette_token(
            contract["palette"], token, keywords, fallback, used, prefer_dark=dark, prefer_light=light
        )
    colors["paper"] = colors["canvas"]
    sources["colors.paper"] = {
        **sources["colors.canvas"],
        "basis": f"{sources['colors.canvas']['basis']}；v1 复用为卡片纸色。",
    }

    display, display_source = _size_token(contract["typography"], ("H1",), 72, "display")
    heading, heading_source = _size_token(contract["typography"], ("H2", "H3"), 36, "heading")
    body, body_source = _size_token(contract["typography"], ("BODY", "P"), 20, "body")
    canvas_x, spacing_source = _spacing_token(contract)
    tokens = {
        **colors,
        "display_size": display,
        "heading_size": heading,
        "body_size": body,
        "caption_size": "13px",
        "canvas_x": canvas_x,
        "canvas_y": "46px",
        "gap": "22px",
    }
    sources.update(
        {
            "type.display_size": display_source,
            "type.heading_size": heading_source,
            "type.body_size": body_source,
            "type.caption_size": {
                "status": "fallback",
                "source": "compiler-neutral-default",
                "basis": "VI hierarchy does not require an exact caption size; neutral reversible fallback.",
            },
            "spacing.canvas_x": spacing_source,
            "spacing.canvas_y": {
                "status": "fallback",
                "source": "compiler-neutral-default",
                "basis": "Vertical safe area is a reversible runtime-fit fallback.",
            },
            "spacing.gap": {
                "status": "extension",
                "source": "layout rhythm",
                "basis": "Compile the VI module rhythm into a consistent report grid gap.",
            },
        }
    )
    return tokens, sources


def _css(theme_id: str, tokens: dict[str, str], contract: dict[str, Any]) -> str:
    component_text = " ".join(
        item["description"] for item in contract["components"] if item["status"] != "unknown"
    )
    hard_edges = any(word in component_text for word in ("直角", "无圆角", "硬边", "粗黑边"))
    radius = "0" if hard_edges else "4px"
    border_width = "3px" if any(word in component_text for word in ("粗", "硬边")) else "1px"
    image_text = " ".join(
        item["description"] for item in contract["imagery"] if item["status"] != "unknown"
    )
    image_filter = "grayscale(1) contrast(1.14)" if "去色" in image_text else "saturate(.82) contrast(1.04)"
    selector = f'.deck[data-theme="{theme_id}"]'
    return f"""{selector} {{
  --pt-canvas: {tokens['canvas']};
  --pt-ink: {tokens['ink']};
  --pt-signal: {tokens['signal']};
  --pt-accent: {tokens['accent']};
  --pt-panel: {tokens['panel']};
  --pt-paper: {tokens['paper']};
  --pt-display: {tokens['display_size']};
  --pt-heading: {tokens['heading_size']};
  --pt-body: {tokens['body_size']};
  --pt-caption: {tokens['caption_size']};
  --pt-canvas-x: {tokens['canvas_x']};
  --pt-canvas-y: {tokens['canvas_y']};
  --pt-gap: {tokens['gap']};
  --pt-border: {border_width} solid var(--pt-ink);
  --pt-radius: {radius};
  color: var(--pt-ink);
  background: var(--pt-canvas);
  font-family: Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
}}

{selector} .slide {{ padding: var(--pt-canvas-y) var(--pt-canvas-x) 56px; color: var(--pt-ink); background: var(--pt-canvas); }}
{selector} .slide::before {{ display: none; }}
{selector} h1, {selector} h2, {selector} h3, {selector} p {{ margin-top: 0; }}
{selector} .fragment {{ transform: translateY(14px); transition: opacity .42s cubic-bezier(.2,.8,.2,1), transform .42s cubic-bezier(.2,.8,.2,1); }}
{selector} .fragment.visible, {selector}[data-mode="reading"] .fragment {{ transform: none; }}
.pt-kicker {{ display: inline-flex; padding: 7px 11px; color: var(--pt-ink); background: var(--pt-accent); border: var(--pt-border); font-size: var(--pt-caption); font-weight: 900; letter-spacing: .08em; }}
.pt-title {{ margin: 18px 0 12px; max-width: 1260px; font-size: var(--pt-heading); line-height: 1.02; font-weight: 950; }}
.pt-lede {{ max-width: 1040px; font-size: var(--pt-body); line-height: 1.42; }}
.pt-footer {{ position: absolute; left: var(--pt-canvas-x); right: var(--pt-canvas-x); bottom: 28px; padding-top: 10px; border-top: 2px solid var(--pt-ink); font-size: var(--pt-caption); font-weight: 800; }}
.pt-cover-grid {{ display: grid; grid-template-columns: 7fr 5fr; gap: 38px; height: 100%; align-items: center; }}
.pt-cover h1 {{ margin: 22px 0 18px; font-size: var(--pt-display); line-height: .98; font-weight: 950; letter-spacing: -.035em; }}
.pt-cover-art {{ position: relative; height: 510px; overflow: hidden; background: var(--pt-panel); border: var(--pt-border); }}
.pt-cover-art::before {{ content: ""; position: absolute; width: 78%; height: 38%; left: -8%; top: 18%; background: var(--pt-signal); clip-path: polygon(0 72%, 20% 38%, 42% 62%, 65% 5%, 100% 54%, 100% 100%, 0 100%); }}
.pt-cover-art::after {{ content: ""; position: absolute; width: 170px; height: 170px; right: 11%; top: 10%; border-radius: 50%; background: var(--pt-accent); }}
.pt-claim {{ position: absolute; left: 28px; right: 28px; bottom: 28px; padding: 20px 22px; color: var(--pt-canvas); background: var(--pt-ink); border-left: 10px solid var(--pt-signal); font-size: 21px; line-height: 1.32; font-weight: 800; }}
.pt-card-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--pt-gap); margin-top: 38px; }}
.pt-card {{ min-height: 300px; padding: 25px; background: var(--pt-paper); border: var(--pt-border); border-radius: var(--pt-radius); }}
.pt-card:nth-child(2) {{ transform: translateY(22px); }}
.pt-card h3 {{ margin: 18px 0 12px; font-size: 31px; line-height: 1.05; }}
.pt-card p {{ font-size: 18px; line-height: 1.45; }}
.pt-label {{ display: inline-flex; padding: 6px 9px; background: var(--pt-accent); border: 2px solid var(--pt-ink); font-size: 12px; font-weight: 900; }}
.pt-rail {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; margin-top: 46px; border: var(--pt-border); }}
.pt-step {{ min-height: 320px; padding: 26px; background: var(--pt-paper); border-right: var(--pt-border); }}
.pt-step:last-child {{ border-right: 0; }}
.pt-step strong {{ display: block; color: var(--pt-signal); font-size: 62px; line-height: 1; font-weight: 950; }}
.pt-step h3 {{ margin: 22px 0 12px; font-size: 28px; }}
.pt-step p {{ font-size: 17px; line-height: 1.42; }}
.pt-evidence-grid {{ display: grid; grid-template-columns: 5fr 7fr; gap: var(--pt-gap); margin-top: 28px; }}
.pt-source-frame {{ height: 430px; margin: 0; overflow: hidden; background: var(--pt-panel); border: var(--pt-border); }}
.pt-source-frame img {{ width: 100%; height: 100%; object-fit: cover; filter: {image_filter}; }}
.pt-data-panel {{ padding: 24px; color: var(--pt-canvas); background: var(--pt-panel); border: var(--pt-border); }}
.pt-bars {{ display: grid; grid-template-columns: repeat(3, 1fr); align-items: end; gap: 20px; height: 210px; padding: 22px 18px 0; border-bottom: 2px solid var(--pt-canvas); }}
.pt-bar {{ display: grid; align-content: end; min-height: 40%; padding: 16px 10px; color: var(--pt-ink); background: var(--pt-signal); font-weight: 900; text-align: center; }}
.pt-bar:nth-child(2) {{ min-height: 68%; background: var(--pt-accent); }} .pt-bar:nth-child(3) {{ min-height: 88%; background: var(--pt-canvas); }}
.pt-bar strong {{ display: block; font-size: 38px; }} .pt-bar span {{ font-size: 12px; }}
.pt-table {{ width: 100%; margin-top: 18px; border-collapse: collapse; font-size: 14px; }}
.pt-table th, .pt-table td {{ padding: 9px 10px; border-bottom: 1px solid color-mix(in srgb, var(--pt-canvas), transparent 60%); text-align: left; }}
.pt-actions {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--pt-gap); margin-top: 38px; }}
.pt-action {{ min-height: 265px; padding: 24px; background: var(--pt-paper); border: var(--pt-border); }}
.pt-action strong {{ color: var(--pt-signal); font-size: 54px; line-height: 1; }} .pt-action h3 {{ margin: 20px 0 12px; font-size: 27px; }}
.pt-final {{ margin-top: 30px; padding: 20px 24px; color: var(--pt-canvas); background: var(--pt-ink); border-left: 12px solid var(--pt-signal); font-size: 24px; font-weight: 900; }}
{selector} .source-btn {{ top: 48px; right: var(--pt-canvas-x); background: var(--pt-ink); color: var(--pt-canvas); border-radius: 0; }}
"""


def _templates() -> str:
    return """<section class="slide active pt-cover" data-title="核心命题" data-layout="reference-hero-cover">
  <div class="pt-cover-grid"><div><div class="pt-kicker">{{S1_KICKER}}</div><h1>{{S1_TITLE_A}}<br>{{S1_TITLE_B}}</h1><p class="pt-lede">{{S1_LEDE}}</p></div>
  <div class="pt-cover-art" role="img" aria-label="项目主题几何主视觉"><aside class="pt-claim fragment" data-step="1"><span class="pt-label">{{S1_LABEL}}</span><p>{{S1_CLAIM}}</p></aside></div></div><div class="pt-footer">{{FOOTER}}</div>
</section>

<section class="slide" data-title="内容诊断" data-layout="asymmetric-evidence-cards">
  <div class="pt-kicker">{{S2_KICKER}}</div><h2 class="pt-title">{{S2_TITLE}}</h2><p class="pt-lede">{{S2_LEDE}}</p><div class="pt-card-grid">
    <article class="pt-card fragment" data-step="1"><span class="pt-label">{{S2_1_LABEL}}</span><h3>{{S2_1_TITLE}}</h3><p>{{S2_1_BODY}}</p></article>
    <article class="pt-card fragment" data-step="2"><span class="pt-label">{{S2_2_LABEL}}</span><h3>{{S2_2_TITLE}}</h3><p>{{S2_2_BODY}}</p></article>
    <article class="pt-card fragment" data-step="3"><span class="pt-label">{{S2_3_LABEL}}</span><h3>{{S2_3_TITLE}}</h3><p>{{S2_3_BODY}}</p></article>
  </div><div class="pt-footer">{{FOOTER}}</div>
</section>

<section class="slide" data-title="内容机制" data-layout="hard-rule-process-rail">
  <div class="pt-kicker">{{S3_KICKER}}</div><h2 class="pt-title">{{S3_TITLE}}</h2><p class="pt-lede">{{S3_LEDE}}</p><div class="pt-rail">
    <article class="pt-step fragment" data-step="1"><strong>{{S3_1_NUM}}</strong><h3>{{S3_1_TITLE}}</h3><p>{{S3_1_BODY}}</p></article>
    <article class="pt-step fragment" data-step="2"><strong>{{S3_2_NUM}}</strong><h3>{{S3_2_TITLE}}</h3><p>{{S3_2_BODY}}</p></article>
    <article class="pt-step fragment" data-step="3"><strong>{{S3_3_NUM}}</strong><h3>{{S3_3_TITLE}}</h3><p>{{S3_3_BODY}}</p></article>
    <article class="pt-step fragment" data-step="4"><strong>{{S3_4_NUM}}</strong><h3>{{S3_4_TITLE}}</h3><p>{{S3_4_BODY}}</p></article>
  </div><div class="pt-footer">{{FOOTER}}</div>
</section>

<section class="slide" data-title="证据与数据" data-layout="source-and-direct-bars">
  <button class="source-btn" data-source="{{SOURCE_URI}}" data-source-kind="{{SOURCE_KIND}}" data-source-label="{{SOURCE_LABEL}}">{{S4_SOURCE}}</button>
  <div class="pt-kicker">{{S4_KICKER}}</div><h2 class="pt-title">{{S4_TITLE}}</h2><p class="pt-lede">{{S4_LEDE}}</p><div class="pt-evidence-grid">
    <figure class="pt-source-frame fragment" data-step="1"><img src="{{SOURCE_URI}}" alt="{{SOURCE_LABEL}}"></figure><div class="pt-data-panel">
      <div class="pt-bars fragment" data-step="2"><div class="pt-bar"><strong>{{S4_M1_VALUE}}</strong><span>{{S4_M1_LABEL}}</span></div><div class="pt-bar"><strong>{{S4_M2_VALUE}}</strong><span>{{S4_M2_LABEL}}</span></div><div class="pt-bar"><strong>{{S4_M3_VALUE}}</strong><span>{{S4_M3_LABEL}}</span></div></div>
      <table class="pt-table fragment" data-step="3"><thead><tr><th>{{S4_TABLE_H1}}</th><th>{{S4_TABLE_H2}}</th><th>{{S4_TABLE_H3}}</th></tr></thead><tbody><tr><td>{{S4_R1_C1}}</td><td>{{S4_R1_C2}}</td><td>{{S4_R1_C3}}</td></tr><tr><td>{{S4_R2_C1}}</td><td>{{S4_R2_C2}}</td><td>{{S4_R2_C3}}</td></tr><tr><td>{{S4_R3_C1}}</td><td>{{S4_R3_C2}}</td><td>{{S4_R3_C3}}</td></tr></tbody></table>
    </div></div><div class="pt-footer">{{FOOTER}}</div>
</section>

<section class="slide" data-title="行动收束" data-layout="project-action-wall">
  <div class="pt-kicker">{{S5_KICKER}}</div><h2 class="pt-title">{{S5_TITLE}}</h2><p class="pt-lede">{{S5_LEDE}}</p><div class="pt-actions">
    <article class="pt-action fragment" data-step="1"><strong>{{S5_1_NUM}}</strong><h3>{{S5_1_TITLE}}</h3><p>{{S5_1_BODY}}</p></article>
    <article class="pt-action fragment" data-step="2"><strong>{{S5_2_NUM}}</strong><h3>{{S5_2_TITLE}}</h3><p>{{S5_2_BODY}}</p></article>
    <article class="pt-action fragment" data-step="3"><strong>{{S5_3_NUM}}</strong><h3>{{S5_3_TITLE}}</h3><p>{{S5_3_BODY}}</p></article>
  </div><div class="pt-final fragment" data-step="4"><span class="pt-label">{{S5_LABEL}}</span> {{S5_CLAIM}}</div><div class="pt-footer">{{FOOTER}}</div>
</section>"""


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def compile_theme(request_path: Path, output_theme: Path) -> Path:
    request, contract, vi_path, reference_path = load_handoff(request_path)
    theme_id = f"project-{request['project']['id']}"
    tokens, token_sources = _compile_tokens(contract)
    boundaries = _boundary_records(contract)
    counts = {
        status: sum(record["status"] == status for record in boundaries)
        for status in ("observed", "extension", "unknown")
    }
    preserve = [
        item["description"]
        for item in contract["guardrails"]
        if item["mode"] == "preserve" and item["status"] != "unknown"
    ]
    forbidden = [
        item["description"]
        for item in contract["guardrails"]
        if item["mode"] == "avoid" and item["status"] != "unknown"
    ]
    evidence = next(
        (item for item in contract["evidence_language"] if item["status"] == "observed"),
        None,
    )
    evidence_rule = (
        evidence["description"]
        if evidence
        else "Neutral labeled metrics and table fallback; no reference-observed chart grammar."
    )
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "project",
        "id": theme_id,
        "display_name": request["project"]["display_name"],
        "description": "由已确认单张静态参考 VI 合同编译的当前项目专用主题",
        "project": {
            "id": request["project"]["id"],
            "target_mode": request["target_mode"],
            "global_built_in": False,
        },
        "files": {
            "tokens": "theme.css",
            "templates": "templates.html",
            "provenance": "provenance.json",
        },
        "identity": {
            "composition": "Confirmed VI grid compiled into a 7:5 hero, asymmetric three-card content page, hard-rule process rail, source-plus-data page, and action wall.",
            "hierarchy": "Conclusion-first display heading, compact section label, bounded body copy, and direct evidence values.",
            "image_treatment": "; ".join(
                item["description"] for item in contract["imagery"] if item["status"] != "unknown"
            )
            or "Neutral cover crop fallback; not a reference observation.",
            "module_language": "; ".join(
                item["description"] for item in contract["components"] if item["status"] != "unknown"
            ),
            "chart_evidence": evidence_rule,
            "motion": "TaoHtml Runtime reveal syntax; not observed or inferred from the static reference.",
        },
        "tokens": tokens,
        "token_sources": token_sources,
        "canvas": {
            "aspect_ratio": "16:9",
            "grid": next(
                (item["value"] for item in contract["layout"] if item["status"] != "unknown" and "网格" in item["label"]),
                "neutral 12-column fallback",
            ),
            "safe_area": f"{tokens['canvas_x']} horizontal; {tokens['canvas_y']} vertical",
        },
        "layout_variants": [
            {"id": "reference-hero-cover", "role": "cover"},
            {"id": "asymmetric-evidence-cards", "role": "content"},
            {"id": "hard-rule-process-rail", "role": "content"},
            {"id": "source-and-direct-bars", "role": "evidence-data"},
            {"id": "project-action-wall", "role": "closing"},
        ],
        "components": {
            "card": "Hard-bounded evidence card with label, conclusion, and concise body.",
            "panel": "Dark inverse evidence panel with direct labels.",
            "label": "Compact solid section tag with no provenance implication.",
            "border": "Structural rule derived from confirmed component language.",
            "image": "Embedded local source, hard crop, and explicit verified/illustrative label from the renderer.",
            "chart": evidence_rule,
        },
        "preserve": preserve,
        "forbidden": forbidden,
        "motion": {
            "observed_from_reference": False,
            "source": "TaoHtml shared Runtime and report-task reveal decisions",
            "enter": "generic opacity plus 14px upward reveal over 420ms",
            "stagger": "existing fragment and data-step syntax",
            "disabled": ["reference-inferred timing", "reference-inferred transitions", "cross-page morph"],
        },
        "compilation": {
            "confirmation": "确认 VI",
            "vi_contract_sha256": request["confirmation"]["vi_contract_sha256"],
            "reference_image_sha256": request["confirmation"]["reference_image_sha256"],
            "boundary_summary": counts,
            "customer_corrections": request["customer_corrections"],
        },
        "template_contract": {
            "placeholder_format": "{{UPPER_SNAKE_CASE}}",
            "minimum_slides": 5,
            "required_markers": ["data-layout", "fragment", "data-step"],
        },
    }
    fallback_records = [
        {"token": token, **record}
        for token, record in token_sources.items()
        if record["status"] == "fallback"
    ]
    provenance = {
        "schema_version": SCHEMA_VERSION,
        "theme_id": theme_id,
        "confirmed_inputs": {
            "vi_contract": vi_path.name,
            "vi_contract_sha256": _sha256(vi_path),
            "reference_image": reference_path.name,
            "reference_image_sha256": _sha256(reference_path),
            "confirmation_status": request["confirmation"]["status"],
            "confirmation_phrase": request["confirmation"]["phrase"],
            "target_mode": request["target_mode"],
            "customer_corrections": request["customer_corrections"],
        },
        "boundary_policy": {
            "observed": "eligible for direct deterministic compilation",
            "extension": "eligible only as a labeled report adaptation",
            "unknown": "retained but never compiled as observed",
            "fallback": "neutral reversible compiler default, never reference evidence",
        },
        "boundary_records": boundaries,
        "fallback_records": fallback_records,
        "motion_boundary": manifest["motion"],
    }
    css = _css(theme_id, tokens, contract).strip() + "\n"
    templates = _templates().strip() + "\n"
    for text, label in ((css, "theme.css"), (templates, "templates.html")):
        if re.search(r"(?:https?:)?//|@import\b", text, re.IGNORECASE):
            raise ValueError(f"Compiled {label} contains a remote asset reference.")

    supplied_output = output_theme.expanduser()
    if supplied_output.is_symlink():
        raise ValueError(f"Output theme directory must not be a symlink: {supplied_output}")
    output = supplied_output.resolve()
    if output.exists() and not output.is_dir():
        raise ValueError(f"Output theme path is not a directory: {output}")
    if output.exists():
        actual = {entry.name for entry in output.iterdir()}
        extra = actual - OUTPUT_FILES
        if extra:
            raise ValueError(f"Output theme directory contains unexpected files: {', '.join(sorted(extra))}")
        if any(entry.is_symlink() or not entry.is_file() for entry in output.iterdir()):
            raise ValueError(f"Output theme directory must contain regular files only: {output}")
    output.mkdir(parents=True, exist_ok=True)
    payloads = {
        "theme.json": _json_text(manifest),
        "theme.css": css,
        "templates.html": templates,
        "provenance.json": _json_text(provenance),
    }
    for filename, payload in payloads.items():
        target = output / filename
        target.write_text(payload, encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile a machine-confirmed single-reference VI handoff into a deterministic project theme."
    )
    parser.add_argument("--request", type=Path, required=True, help="Confirmed VI handoff JSON.")
    parser.add_argument("--output-theme", type=Path, required=True, help="Project theme output directory.")
    args = parser.parse_args()
    try:
        output = compile_theme(args.request, args.output_theme)
    except (OSError, ValueError) as exc:
        print(f"PROJECT_THEME_COMPILE_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"PROJECT_THEME_COMPILE_OK {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
