#!/usr/bin/env python3
"""Validate one Report IR v0 research fixture and compile it through TaoHtml.

This is deliberately a narrow research adapter, not the production Report IR
Schema or Compiler. It supports one five-page semantic profile so the team can
measure deterministic compilation, theme switching, patch locality, and QA.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT_FIELDS = {
    "report_ir_version",
    "report",
    "projection",
    "sources",
    "claims",
    "evidence",
    "evidence_links",
    "blocks",
    "pages",
    "traceability",
}
BLOCK_KINDS = {
    "kicker",
    "headline",
    "body_text",
    "label",
    "claim",
    "metric",
    "table_cell",
}
EXPECTED_FORMS = ("poster", "comparison", "process", "data", "closing")
FORBIDDEN_KEY_RE = re.compile(r"(?:^|_)(?:html|css|javascript|script|style)(?:_|$)", re.I)
FORBIDDEN_VALUE_RE = re.compile(
    r"<\s*(?:script|style|iframe)\b|javascript\s*:|\bon[a-z]+\s*=",
    re.I,
)
REPORT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,127}$")
CONTENT_STATUSES = {"verified", "illustrative", "unverified"}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def compiler_dependency_hashes(skill_root: Path) -> dict[str, str]:
    """Return the exact code and runtime bytes that determine compilation.

    The adapter path alone is not an identity. A model could otherwise replace
    the compiler or renderer and still write a plausible manifest that names
    the original path. These hashes let the controller prove which immutable
    compiler stack produced a build.
    """

    renderer = skill_root / "scripts" / "render_visual_system.py"
    theme_runtime = skill_root / "scripts" / "theme_runtime.py"
    shell_root = skill_root / "assets" / "html-deck-template"
    return {
        "adapter_sha256": sha256_file(Path(__file__).resolve()),
        "renderer_sha256": sha256_file(renderer),
        "theme_runtime_sha256": sha256_file(theme_runtime),
        "runtime_shell_sha256": sha256_file(shell_root / "index.html"),
        "editor_css_sha256": sha256_file(
            shell_root / "assets" / "runtime" / "taohtml-editor.css"
        ),
        "editor_js_sha256": sha256_file(
            shell_root / "assets" / "runtime" / "taohtml-editor.js"
        ),
    }


def portable_workspace_path(path: Path, workspace_root: Path) -> str:
    """Use POSIX workspace-relative paths when an artifact belongs to the run."""

    resolved = path.resolve()
    try:
        return resolved.relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def write_utf8_lf(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    path.write_bytes(normalized.encode("utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def require_fields(value: dict[str, Any], required: set[str], label: str) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise ValueError(f"{label}: missing fields: {', '.join(missing)}")


def reject_executable_content(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}: object key must be a string")
            if FORBIDDEN_KEY_RE.search(key):
                raise ValueError(f"{path}.{key}: executable presentation fields are forbidden")
            reject_executable_content(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_executable_content(child, f"{path}[{index}]")
    elif isinstance(value, str) and FORBIDDEN_VALUE_RE.search(value):
        raise ValueError(f"{path}: executable markup is forbidden")


def validate_entity_array(
    values: Any,
    label: str,
    required: set[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{label}: must be a non-empty array")
    registry: dict[str, dict[str, Any]] = {}
    result: list[dict[str, Any]] = []
    for index, item in enumerate(values):
        if not isinstance(item, dict):
            raise ValueError(f"{label}[{index}]: must be an object")
        require_fields(item, required, f"{label}[{index}]")
        entity_id = item["id"]
        if not isinstance(entity_id, str) or not entity_id:
            raise ValueError(f"{label}[{index}].id: must be a non-empty string")
        if entity_id in registry:
            raise ValueError(f"{label}: duplicate id: {entity_id}")
        registry[entity_id] = item
        result.append(item)
    return result, registry


def derive_visual_source_kind(
    source: dict[str, Any],
    linked_evidence: list[dict[str, Any]],
) -> str:
    """Map semantic verification state to the renderer's two safe labels.

    Local byte integrity is not evidence verification. A visual can be labeled
    verified only when both the selected Source and every Evidence record that
    uses it explicitly declare verified content. Missing or mixed evidence is
    conservatively rendered as illustrative.
    """

    source_status = source.get("content_status")
    if source_status not in CONTENT_STATUSES:
        raise ValueError(
            f"source.{source.get('id', '<unknown>')}.content_status: "
            f"unsupported status {source_status!r}"
        )
    evidence_statuses = [item.get("content_status") for item in linked_evidence]
    invalid = sorted(
        {status for status in evidence_statuses if status not in CONTENT_STATUSES},
        key=lambda value: repr(value),
    )
    if invalid:
        raise ValueError(f"visual evidence has unsupported content_status values: {invalid}")
    if source_status != "verified" or not evidence_statuses:
        return "illustrative"
    if any(status != "verified" for status in evidence_statuses):
        return "illustrative"
    return "verified"


def validate_ir(ir: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    unknown = sorted(set(ir) - ROOT_FIELDS)
    missing = sorted(ROOT_FIELDS - set(ir))
    if unknown or missing:
        raise ValueError(f"root fields mismatch; missing={missing}, unknown={unknown}")
    if ir["report_ir_version"] != "research-v0":
        raise ValueError("report_ir_version must be research-v0")
    reject_executable_content(ir)

    report = ir["report"]
    projection = ir["projection"]
    blocks = ir["blocks"]
    traceability = ir["traceability"]
    if not isinstance(report, dict) or not isinstance(projection, dict):
        raise ValueError("report and projection must be objects")
    if not isinstance(traceability, dict):
        raise ValueError("traceability must be an object")
    require_fields(
        traceability,
        {"pending_verification_required"},
        "traceability",
    )
    if not isinstance(traceability["pending_verification_required"], bool):
        raise ValueError("traceability.pending_verification_required must be a boolean")
    require_fields(
        report,
        {
            "id",
            "title",
            "objective",
            "audience",
            "archetype",
            "evidence_rigor",
            "visual_source_ref",
            "document_title_ref",
            "footer_ref",
        },
        "report",
    )
    if not isinstance(report["id"], str) or not REPORT_ID_RE.fullmatch(report["id"]):
        raise ValueError("report.id must be a stable ASCII identifier")
    require_fields(
        projection,
        {
            "id",
            "delivery_mode",
            "information_density",
            "motion_density",
            "interaction_level",
            "page_order",
        },
        "projection",
    )
    if projection["delivery_mode"] != "presentation":
        raise ValueError("research adapter requires delivery_mode=presentation")

    if not isinstance(blocks, dict) or not blocks:
        raise ValueError("blocks must be a non-empty object")
    for block_id, block in blocks.items():
        if not isinstance(block_id, str) or not block_id:
            raise ValueError("block id must be a non-empty string")
        if not isinstance(block, dict):
            raise ValueError(f"blocks.{block_id}: must be an object")
        if set(block) != {"kind", "content"}:
            raise ValueError(f"blocks.{block_id}: only kind and content are allowed")
        if block["kind"] not in BLOCK_KINDS:
            raise ValueError(f"blocks.{block_id}.kind: unsupported kind {block['kind']!r}")
        if not isinstance(block["content"], str) or not block["content"].strip():
            raise ValueError(f"blocks.{block_id}.content: must be non-empty text")

    sources, source_by_id = validate_entity_array(
        ir["sources"],
        "sources",
        {"id", "locator", "sha256", "source_role", "content_status", "limitation"},
    )
    _, claim_by_id = validate_entity_array(
        ir["claims"],
        "claims",
        {"id", "kind", "statement", "status"},
    )
    evidence, evidence_by_id = validate_entity_array(
        ir["evidence"],
        "evidence",
        {"id", "source_refs", "kind", "content_status", "scope"},
    )
    for source in sources:
        if source["content_status"] not in CONTENT_STATUSES:
            raise ValueError(
                f"source.{source['id']}.content_status: unsupported status "
                f"{source['content_status']!r}"
            )
        if source["source_role"] == "synthetic_fixture" and source["content_status"] != "illustrative":
            raise ValueError(
                f"source.{source['id']}: synthetic_fixture must remain illustrative"
            )
    for item in evidence:
        if item["content_status"] not in CONTENT_STATUSES:
            raise ValueError(
                f"evidence.{item['id']}.content_status: unsupported status "
                f"{item['content_status']!r}"
            )
        if str(item["kind"]).startswith("synthetic_") and item["content_status"] != "illustrative":
            raise ValueError(
                f"evidence.{item['id']}: synthetic evidence must remain illustrative"
            )
    links = ir["evidence_links"]
    if not isinstance(links, list) or not links:
        raise ValueError("evidence_links must be a non-empty array")
    for index, link in enumerate(links):
        if not isinstance(link, dict):
            raise ValueError(f"evidence_links[{index}] must be an object")
        require_fields(link, {"claim_ref", "evidence_ref", "relation"}, f"evidence_links[{index}]")
        if link["claim_ref"] not in claim_by_id:
            raise ValueError(f"evidence_links[{index}]: unknown claim {link['claim_ref']}")
        if link["evidence_ref"] not in evidence_by_id:
            raise ValueError(f"evidence_links[{index}]: unknown evidence {link['evidence_ref']}")

    for item in evidence:
        refs = item["source_refs"]
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"evidence.{item['id']}: source_refs must be non-empty")
        for ref in refs:
            if ref not in source_by_id:
                raise ValueError(f"evidence.{item['id']}: unknown source {ref}")

    resolved_sources: dict[str, Path] = {}
    for source in sources:
        locator = source["locator"]
        if not isinstance(locator, str) or not locator or Path(locator).is_absolute():
            raise ValueError(f"source.{source['id']}: locator must be a relative path")
        path = (workspace_root / locator).resolve()
        try:
            path.relative_to(workspace_root.resolve())
        except ValueError as exc:
            raise ValueError(f"source.{source['id']}: locator escapes workspace") from exc
        if not path.is_file():
            raise ValueError(f"source.{source['id']}: file not found: {locator}")
        actual = sha256_file(path)
        if actual != source["sha256"]:
            raise ValueError(
                f"source.{source['id']}: sha256 mismatch; expected {source['sha256']}, got {actual}"
            )
        resolved_sources[source["id"]] = path

    pages, page_by_id = validate_entity_array(
        ir["pages"],
        "pages",
        {"id", "role", "form", "task", "claim_refs", "evidence_refs", "slots"},
    )
    page_order = projection["page_order"]
    if not isinstance(page_order, list) or len(page_order) != 5:
        raise ValueError("projection.page_order must contain exactly five page ids")
    if len(set(page_order)) != len(page_order):
        raise ValueError("projection.page_order contains duplicate page ids")
    if set(page_order) != set(page_by_id):
        raise ValueError("projection.page_order must reference every page exactly once")
    ordered_pages = [page_by_id[page_id] for page_id in page_order]
    forms = tuple(page["form"] for page in ordered_pages)
    if forms != EXPECTED_FORMS:
        raise ValueError(f"page forms must be {EXPECTED_FORMS}, got {forms}")

    for page in pages:
        if not isinstance(page["slots"], dict):
            raise ValueError(f"page.{page['id']}.slots must be an object")
        for claim_ref in page["claim_refs"]:
            if claim_ref not in claim_by_id:
                raise ValueError(f"page.{page['id']}: unknown claim {claim_ref}")
        for evidence_ref in page["evidence_refs"]:
            if evidence_ref not in evidence_by_id:
                raise ValueError(f"page.{page['id']}: unknown evidence {evidence_ref}")

    visual_source_ref = report["visual_source_ref"]
    if visual_source_ref not in resolved_sources:
        raise ValueError(f"report.visual_source_ref: unknown source {visual_source_ref}")
    visual_source_record = source_by_id[visual_source_ref]
    visual_evidence = [
        item for item in evidence if visual_source_ref in item["source_refs"]
    ]
    visual_source_kind = derive_visual_source_kind(
        visual_source_record,
        visual_evidence,
    )
    for ref_name in ("document_title_ref", "footer_ref"):
        if report[ref_name] not in blocks:
            raise ValueError(f"report.{ref_name}: unknown block {report[ref_name]}")

    return {
        "blocks": blocks,
        "pages": ordered_pages,
        "visual_source": resolved_sources[visual_source_ref],
        "visual_source_ref": visual_source_ref,
        "visual_source_record": visual_source_record,
        "visual_evidence": visual_evidence,
        "visual_source_kind": visual_source_kind,
        "claim_count": len(claim_by_id),
        "evidence_count": len(evidence_by_id),
        "source_count": len(source_by_id),
    }


def block_text(blocks: dict[str, dict[str, str]], ref: Any, label: str) -> str:
    if not isinstance(ref, str) or ref not in blocks:
        raise ValueError(f"{label}: unknown block reference {ref!r}")
    return blocks[ref]["content"]


def item_values(
    blocks: dict[str, dict[str, str]],
    items: Any,
    expected_count: int,
    keys: tuple[str, ...],
    label: str,
) -> list[dict[str, str]]:
    if not isinstance(items, list) or len(items) != expected_count:
        raise ValueError(f"{label}: expected {expected_count} items")
    result = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != set(keys):
            raise ValueError(f"{label}[{index}]: expected keys {keys}")
        result.append(
            {key: block_text(blocks, item[key], f"{label}[{index}].{key}") for key in keys}
        )
    return result


def build_content_map(ir: dict[str, Any], validated: dict[str, Any]) -> dict[str, str]:
    blocks = validated["blocks"]
    poster, comparison, process, data, closing = validated["pages"]
    report = ir["report"]

    def scalar(page: dict[str, Any], key: str) -> str:
        return block_text(blocks, page["slots"].get(key), f"page.{page['id']}.slots.{key}")

    comparison_items = item_values(
        blocks, comparison["slots"].get("items"), 3, ("label", "title", "body"), "comparison.items"
    )
    process_items = item_values(
        blocks, process["slots"].get("items"), 4, ("num", "title", "body"), "process.items"
    )
    metrics = item_values(
        blocks, data["slots"].get("metrics"), 3, ("value", "label"), "data.metrics"
    )
    closing_items = item_values(
        blocks, closing["slots"].get("items"), 3, ("num", "title", "body"), "closing.items"
    )

    headers = data["slots"].get("table_headers")
    rows = data["slots"].get("table_rows")
    if not isinstance(headers, list) or len(headers) != 3:
        raise ValueError("data.table_headers: expected three block references")
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError("data.table_rows: expected three rows")
    header_values = [block_text(blocks, ref, "data.table_headers") for ref in headers]
    row_values: list[list[str]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError(f"data.table_rows[{index}]: expected three block references")
        row_values.append([block_text(blocks, ref, f"data.table_rows[{index}]") for ref in row])

    content: dict[str, str] = {
        "DOCUMENT_TITLE": block_text(blocks, report["document_title_ref"], "report.document_title_ref"),
        "FOOTER": block_text(blocks, report["footer_ref"], "report.footer_ref"),
        "S1_KICKER": scalar(poster, "kicker"),
        "S1_TITLE_A": scalar(poster, "title_a"),
        "S1_TITLE_B": scalar(poster, "title_b"),
        "S1_LEDE": scalar(poster, "lede"),
        "S1_LABEL": scalar(poster, "label"),
        "S1_CLAIM": scalar(poster, "claim"),
        "S2_KICKER": scalar(comparison, "kicker"),
        "S2_TITLE": scalar(comparison, "title"),
        "S2_LEDE": scalar(comparison, "lede"),
        "S3_KICKER": scalar(process, "kicker"),
        "S3_TITLE": scalar(process, "title"),
        "S3_LEDE": scalar(process, "lede"),
        "S4_KICKER": scalar(data, "kicker"),
        "S4_TITLE": scalar(data, "title"),
        "S4_LEDE": scalar(data, "lede"),
        "S4_SOURCE": scalar(data, "source_label"),
        "S5_KICKER": scalar(closing, "kicker"),
        "S5_TITLE": scalar(closing, "title"),
        "S5_LEDE": scalar(closing, "lede"),
        "S5_LABEL": scalar(closing, "label"),
        "S5_CLAIM": scalar(closing, "claim"),
    }
    for index, item in enumerate(comparison_items, start=1):
        content[f"S2_{index}_LABEL"] = item["label"]
        content[f"S2_{index}_TITLE"] = item["title"]
        content[f"S2_{index}_BODY"] = item["body"]
    for index, item in enumerate(process_items, start=1):
        content[f"S3_{index}_NUM"] = item["num"]
        content[f"S3_{index}_TITLE"] = item["title"]
        content[f"S3_{index}_BODY"] = item["body"]
    for index, item in enumerate(metrics, start=1):
        content[f"S4_M{index}_VALUE"] = item["value"]
        content[f"S4_M{index}_LABEL"] = item["label"]
    for index, value in enumerate(header_values, start=1):
        content[f"S4_TABLE_H{index}"] = value
    for row_index, row in enumerate(row_values, start=1):
        for column_index, value in enumerate(row, start=1):
            content[f"S4_R{row_index}_C{column_index}"] = value
    for index, item in enumerate(closing_items, start=1):
        content[f"S5_{index}_NUM"] = item["num"]
        content[f"S5_{index}_TITLE"] = item["title"]
        content[f"S5_{index}_BODY"] = item["body"]
    return content


def load_renderer(skill_root: Path) -> ModuleType:
    path = skill_root / "scripts" / "render_visual_system.py"
    if not path.is_file():
        raise ValueError(f"renderer not found: {path}")
    module_name = f"report_ir_v0_renderer_{sha256_bytes(str(path.resolve()).encode('utf-8'))[:12]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        raise ValueError(f"cannot load renderer: {path}")
    module = importlib.util.module_from_spec(spec)
    # render_visual_system imports theme_runtime by its short module name. Tests
    # and controller jobs can compile multiple isolated workspaces in one Python
    # process; retaining a prior workspace's module would silently bind the new
    # compiler run to deleted or wrong theme files.
    previous_theme_runtime = sys.modules.pop("theme_runtime", None)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop("theme_runtime", None)
        if previous_theme_runtime is not None:
            sys.modules["theme_runtime"] = previous_theme_runtime
    return module


def bind_benchmark_case(output: Path, report_id: str) -> None:
    """Bind generated bytes to the current semantic case without visible copy."""

    source = output.read_text(encoding="utf-8")
    marker = '<main class="deck"'
    if source.count(marker) != 1:
        raise ValueError("compiled HTML must contain exactly one main.deck root")
    replacement = f'{marker} data-benchmark-case="{html.escape(report_id, quote=True)}"'
    write_utf8_lf(output, source.replace(marker, replacement, 1))


def compile_ir(
    ir_path: Path,
    workspace_root: Path,
    skill_root: Path,
    theme: str,
    output: Path,
    manifest_path: Path,
    content_map_path: Path | None = None,
) -> dict[str, Any]:
    ir = load_json(ir_path)
    validated = validate_ir(ir, workspace_root)
    content = build_content_map(ir, validated)
    renderer = load_renderer(skill_root)
    if theme not in renderer.THEME_IDS:
        raise ValueError(f"unsupported built-in theme: {theme}")
    source_uri, source_kind = renderer.resolve_source(
        validated["visual_source"],
        validated["visual_source_kind"],
    )
    renderer._render_bundle(
        content,
        renderer.load_built_in_theme(theme),
        output,
        source_uri,
        source_kind,
        target_mode="presentation",
    )
    bind_benchmark_case(output, ir["report"]["id"])
    if content_map_path is not None:
        write_utf8_lf(
            content_map_path,
            json.dumps(content, ensure_ascii=False, indent=2) + "\n",
        )

    theme_root = skill_root / "assets" / "visual-systems" / theme
    input_hashes = {
        "report_ir_sha256": sha256_file(ir_path),
        "content_fingerprint": sha256_bytes(canonical_bytes(content)),
        "source_sha256": sha256_file(validated["visual_source"]),
        "theme_json_sha256": sha256_file(theme_root / "theme.json"),
        "theme_css_sha256": sha256_file(theme_root / "theme.css"),
        "templates_sha256": sha256_file(theme_root / "templates.html"),
    }
    compiler_hashes = compiler_dependency_hashes(skill_root)
    manifest = {
        "manifest_version": "research-v0",
        "compiler": {
            "id": "report-ir-v0-five-page-adapter",
            "sha256": compiler_hashes["adapter_sha256"],
            "model_calls": 0,
            "production_ready": False,
        },
        "compiler_dependencies": compiler_hashes,
        "artifact_status": "preview_unverified",
        "formal_delivery_ready": False,
        "qa_requirements": {
            "browser_qa": "required_for_formal_delivery",
            "status": "not_run_by_compiler",
        },
        "report_id": ir["report"]["id"],
        "projection_id": ir["projection"]["id"],
        "theme_id": theme,
        "page_order": ir["projection"]["page_order"],
        "entity_counts": {
            "pages": len(validated["pages"]),
            "blocks": len(validated["blocks"]),
            "claims": validated["claim_count"],
            "evidence": validated["evidence_count"],
            "sources": validated["source_count"],
        },
        "input_hashes": input_hashes,
        "output": {
            "path": portable_workspace_path(output, workspace_root),
            "sha256": sha256_file(output),
        },
        "evidence_boundary": {
            "asset_grounding": "verified_local_bytes",
            "visual_source_ref": validated["visual_source_ref"],
            "source_role": validated["visual_source_record"]["source_role"],
            "source_content_status": validated["visual_source_record"]["content_status"],
            "linked_evidence_content_statuses": sorted(
                {item["content_status"] for item in validated["visual_evidence"]}
            ),
            "renderer_source_kind": source_kind,
            "real_world_status": source_kind,
            "pending_verification_required": bool(
                ir["traceability"].get("pending_verification_required")
            ),
        },
    }
    write_utf8_lf(
        manifest_path,
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--skill-root", type=Path, required=True)
    parser.add_argument("--theme", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--content-map-output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        ir_path = args.ir.resolve()
        workspace_root = args.workspace_root.resolve()
        skill_root = args.skill_root.resolve()
        ir = load_json(ir_path)
        validated = validate_ir(ir, workspace_root)
        build_content_map(ir, validated)
        if args.validate_only:
            print(f"IR_VALID {ir_path}")
            return 0
        if args.output is None or args.manifest is None:
            parser.error("--output and --manifest are required unless --validate-only is used")
        manifest = compile_ir(
            ir_path,
            workspace_root,
            skill_root,
            args.theme,
            args.output.resolve(),
            args.manifest.resolve(),
            args.content_map_output.resolve() if args.content_map_output else None,
        )
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"IR_COMPILE_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"IR_COMPILE_OK {args.output.resolve()}")
    print(f"MANIFEST {args.manifest.resolve()}")
    print(f"OUTPUT_SHA256 {manifest['output']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
