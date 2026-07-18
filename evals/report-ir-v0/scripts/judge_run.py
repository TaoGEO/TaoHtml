#!/usr/bin/env python3
"""Judge one completed Report IR v0 direct or IR workspace.

The judge is controller-only. It is deliberately not copied into executor
packages, so the task cannot optimize against implementation details.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


CONTENT_STATUSES = {"verified", "illustrative", "unverified"}


class DeckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.slide_count = 0
        self.deck_mode: str | None = None
        self.benchmark_case: str | None = None
        self.text: list[str] = []
        self.source_bindings: list[dict[str, str]] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        classes = set(values.get("class", "").split())
        if tag in {"script", "style", "template"}:
            self.skip += 1
        if tag == "main" and "deck" in classes:
            self.deck_mode = values.get("data-mode") or None
            self.benchmark_case = values.get("data-benchmark-case") or None
        if tag == "section" and "slide" in classes:
            self.slide_count += 1
        if "source-btn" in classes or "data-source-kind" in values:
            self.source_bindings.append(
                {
                    "kind": values.get("data-source-kind", ""),
                    "label": values.get("data-source-label", ""),
                }
            )

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "template"}:
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data: str) -> None:
        if self.skip == 0 and data.strip():
            self.text.append(data.strip())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "output": completed.stdout,
    }


def make_check(check_id: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"id": check_id, "status": "PASS" if passed else "FAIL", "evidence": evidence}


def expected_ir_source_kind(ir: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Independently derive the safe renderer label from Report IR semantics."""

    report = ir.get("report")
    sources = ir.get("sources")
    evidence = ir.get("evidence")
    if not isinstance(report, dict) or not isinstance(sources, list) or not isinstance(evidence, list):
        raise ValueError("Report IR source binding structure is invalid")
    visual_source_ref = report.get("visual_source_ref")
    matching = [item for item in sources if isinstance(item, dict) and item.get("id") == visual_source_ref]
    if len(matching) != 1:
        raise ValueError("Report IR visual_source_ref must resolve exactly once")
    source = matching[0]
    source_status = source.get("content_status")
    if source_status not in CONTENT_STATUSES:
        raise ValueError(f"unsupported visual Source content_status: {source_status!r}")
    linked = [
        item
        for item in evidence
        if isinstance(item, dict)
        and isinstance(item.get("source_refs"), list)
        and visual_source_ref in item["source_refs"]
    ]
    evidence_statuses = [item.get("content_status") for item in linked]
    if any(status not in CONTENT_STATUSES for status in evidence_statuses):
        raise ValueError("unsupported linked Evidence content_status")
    is_verified = (
        source.get("source_role") != "synthetic_fixture"
        and source_status == "verified"
        and bool(evidence_statuses)
        and all(status == "verified" for status in evidence_statuses)
    )
    expected = "verified" if is_verified else "illustrative"
    return expected, {
        "visual_source_ref": visual_source_ref,
        "source_role": source.get("source_role"),
        "source_content_status": source_status,
        "linked_evidence_content_statuses": sorted(set(evidence_statuses)),
    }


def validate_ir_source_binding(
    ir: dict[str, Any],
    manifest: dict[str, Any],
    deck: DeckParser,
) -> dict[str, Any]:
    """Require IR, build manifest and rendered HTML to agree on provenance."""

    expected, semantic_evidence = expected_ir_source_kind(ir)
    boundary = manifest.get("evidence_boundary")
    if not isinstance(boundary, dict):
        raise ValueError("build manifest evidence_boundary must be an object")
    expected_boundary = {
        **semantic_evidence,
        "renderer_source_kind": expected,
        "real_world_status": expected,
    }
    mismatched_boundary = {
        key: {"expected": value, "actual": boundary.get(key)}
        for key, value in expected_boundary.items()
        if boundary.get(key) != value
    }
    if mismatched_boundary:
        raise ValueError(
            "build manifest evidence boundary mismatch: "
            + json.dumps(mismatched_boundary, ensure_ascii=False, sort_keys=True)
        )
    if not deck.source_bindings:
        raise ValueError("compiled HTML has no source binding")
    actual_kinds = sorted({item["kind"] for item in deck.source_bindings})
    if actual_kinds != [expected]:
        raise ValueError(
            f"compiled HTML source kind mismatch: expected {expected!r}, got {actual_kinds!r}"
        )
    labels = [item["label"] for item in deck.source_bindings]
    if expected == "illustrative":
        bad_labels = [label for label in labels if "待核实" not in label or "已核实" in label]
    else:
        bad_labels = [label for label in labels if "已核实" not in label or "待核实" in label]
    if bad_labels:
        raise ValueError(f"compiled HTML source labels contradict {expected}: {bad_labels!r}")
    return {
        **semantic_evidence,
        "expected_source_kind": expected,
        "html_source_binding_count": len(deck.source_bindings),
        "html_source_kinds": actual_kinds,
        "html_source_labels": labels,
    }


def load_case_spec(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("case spec must be an object")
    required = {
        "case_spec_version",
        "case_id",
        "expected_report_id",
        "slide_count",
        "required_text",
        "disclosure_text",
        "required_minimum_disclosures",
        "forbidden_text",
    }
    missing = sorted(required - set(value))
    if missing:
        raise ValueError(f"case spec missing fields: {', '.join(missing)}")
    if value["case_spec_version"] != "report-ir-v0-case-1":
        raise ValueError("unsupported case spec version")
    if not isinstance(value["slide_count"], int) or value["slide_count"] <= 0:
        raise ValueError("case spec slide_count must be positive")
    for field in ("required_text", "disclosure_text", "forbidden_text"):
        if not isinstance(value[field], list) or not all(
            isinstance(item, str) and item for item in value[field]
        ):
            raise ValueError(f"case spec {field} must contain non-empty strings")
    if not isinstance(value["required_minimum_disclosures"], int):
        raise ValueError("case spec disclosure minimum must be an integer")
    return value


def validate_usage_block(value: Any, label: str, numeric_fields: tuple[str, ...]) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    availability = value.get("availability")
    if availability not in {"exact", "unavailable"}:
        raise ValueError(f"{label}.availability must be exact or unavailable")
    if availability == "unavailable":
        populated = [field for field in numeric_fields if value.get(field) is not None]
        if populated:
            raise ValueError(f"unavailable {label} cannot contain estimates: {populated}")
    else:
        if value.get("source") in {None, "", "unavailable"}:
            raise ValueError(f"exact {label} requires a concrete source")
        populated = [field for field in numeric_fields if value.get(field) is not None]
        if not populated:
            raise ValueError(f"exact {label} requires at least one numeric value")
        invalid = [
            field
            for field in populated
            if not isinstance(value.get(field), (int, float))
            or isinstance(value.get(field), bool)
            or value.get(field) < 0
        ]
        if invalid:
            raise ValueError(f"exact {label} has invalid numeric values: {invalid}")


def validate_metadata(
    value: Any,
    route: str,
    case_id: str | None = None,
    pair_id: str | None = None,
) -> None:
    if not isinstance(value, dict):
        raise ValueError("run metadata must be an object")
    if value.get("route") != route:
        raise ValueError(f"metadata route mismatch: {value.get('route')!r}")
    if value.get("client") != "workbuddy" or value.get("model") != "auto":
        raise ValueError("WorkBuddy comparison must keep client=workbuddy and model=auto")
    if case_id is not None and value.get("case_id") != case_id:
        raise ValueError("run metadata case_id mismatch")
    if pair_id is not None and value.get("pair_id") != pair_id:
        raise ValueError("run metadata pair_id mismatch")
    validate_usage_block(
        value.get("token_usage"),
        "token_usage",
        ("input_tokens", "output_tokens", "cache_tokens", "total_tokens"),
    )
    validate_usage_block(
        value.get("billing_usage"),
        "billing_usage",
        ("workbuddy_points", "balance_before", "balance_after"),
    )


def verify_integrity_receipt(workspace: Path, receipt_path: Path, route: str) -> dict[str, Any]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        raise ValueError("controller receipt must be an object")
    if receipt.get("receipt_version") != "report-ir-v0-controller-receipt-1":
        raise ValueError("unsupported controller receipt version")
    if receipt.get("route") != route:
        raise ValueError("controller receipt route mismatch")
    manifest = json.loads((workspace / "workspace-manifest.json").read_text(encoding="utf-8"))
    if receipt.get("case_id") != manifest.get("case_id"):
        raise ValueError("controller receipt case_id mismatch")
    if receipt.get("pair_id") != manifest.get("pair_id"):
        raise ValueError("controller receipt pair_id mismatch")
    files = receipt.get("immutable_files")
    if not isinstance(files, dict) or not files:
        raise ValueError("controller receipt has no immutable file hashes")
    canonical = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    tree_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if tree_hash != receipt.get("immutable_tree_sha256"):
        raise ValueError("controller receipt tree hash is invalid")
    mismatches: list[dict[str, Any]] = []
    for relative, expected in sorted(files.items()):
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError("controller receipt contains an invalid file record")
        candidate = (workspace / relative).resolve()
        try:
            candidate.relative_to(workspace.resolve())
        except ValueError as exc:
            raise ValueError(f"receipt path escapes workspace: {relative}") from exc
        actual = sha256(candidate) if candidate.is_file() else None
        if actual != expected:
            mismatches.append({"path": relative, "expected": expected, "actual": actual})
    if mismatches:
        raise ValueError(f"immutable executor input mismatch: {json.dumps(mismatches, ensure_ascii=False)}")
    return {
        "receipt": str(receipt_path),
        "immutable_file_count": len(files),
        "immutable_tree_sha256": tree_hash,
        "case_id": receipt.get("case_id"),
        "pair_id": receipt.get("pair_id"),
        "case_spec_sha256": receipt.get("case_spec_sha256"),
    }


def compiler_dependency_hashes(skill_root: Path, adapter: Path) -> dict[str, str]:
    shell_root = skill_root / "assets" / "html-deck-template"
    return {
        "adapter_sha256": sha256(adapter),
        "renderer_sha256": sha256(skill_root / "scripts" / "render_visual_system.py"),
        "theme_runtime_sha256": sha256(skill_root / "scripts" / "theme_runtime.py"),
        "runtime_shell_sha256": sha256(shell_root / "index.html"),
        "editor_css_sha256": sha256(
            shell_root / "assets" / "runtime" / "taohtml-editor.css"
        ),
        "editor_js_sha256": sha256(
            shell_root / "assets" / "runtime" / "taohtml-editor.js"
        ),
    }


def validate_ir_manifest(
    manifest: Any,
    workspace: Path,
    ir: Path,
    html: Path,
    controller_adapter: Path,
) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise ValueError("build manifest must be an object")
    if manifest.get("manifest_version") != "research-v0":
        raise ValueError("build manifest version mismatch")
    if manifest.get("artifact_status") != "preview_unverified":
        raise ValueError("IR artifact must remain preview_unverified")
    if manifest.get("formal_delivery_ready") is not False:
        raise ValueError("IR manifest cannot mark formal delivery ready")
    compiler = manifest.get("compiler")
    if not isinstance(compiler, dict):
        raise ValueError("build manifest compiler must be an object")
    expected_dependencies = compiler_dependency_hashes(
        workspace / "skill" / "taohtml",
        controller_adapter,
    )
    if compiler.get("id") != "report-ir-v0-five-page-adapter":
        raise ValueError("build manifest compiler id mismatch")
    if compiler.get("sha256") != expected_dependencies["adapter_sha256"]:
        raise ValueError("build manifest compiler sha256 mismatch")
    if compiler.get("model_calls") != 0 or compiler.get("production_ready") is not False:
        raise ValueError("build manifest compiler boundary mismatch")
    if manifest.get("compiler_dependencies") != expected_dependencies:
        raise ValueError("build manifest compiler dependency hashes mismatch")
    input_hashes = manifest.get("input_hashes")
    if not isinstance(input_hashes, dict) or input_hashes.get("report_ir_sha256") != sha256(ir):
        raise ValueError("build manifest report IR hash mismatch")
    output = manifest.get("output")
    if not isinstance(output, dict) or output.get("sha256") != sha256(html):
        raise ValueError("build manifest output hash mismatch")
    qa = manifest.get("qa_requirements")
    if not isinstance(qa, dict) or qa.get("status") != "not_run_by_compiler":
        raise ValueError("build manifest QA boundary mismatch")
    return {
        "compiler_sha256": compiler["sha256"],
        "report_ir_sha256": input_hashes["report_ir_sha256"],
        "output_sha256": output["sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("route", choices=("direct", "ir"))
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    output = (args.output or workspace / "judge-result.json").resolve()
    html = workspace / "deliverable" / "index.html"
    handoff = workspace / "deliverable" / "handoff.md"
    metadata_path = workspace / "run-metadata.json"
    checks: list[dict[str, Any]] = []
    commands: dict[str, Any] = {}
    metadata: dict[str, Any] | None = None
    case_spec: dict[str, Any] | None = None
    workspace_manifest: dict[str, Any] | None = None
    browser_qa_dir = output.parent / f"{args.route}-browser-qa"

    try:
        workspace_manifest = json.loads(
            (workspace / "workspace-manifest.json").read_text(encoding="utf-8")
        )
        case_spec_path = workspace / workspace_manifest["case_spec"]
        case_spec = load_case_spec(case_spec_path)
        if workspace_manifest.get("case_id") != case_spec["case_id"]:
            raise ValueError("workspace manifest and case spec case_id mismatch")
        if workspace_manifest.get("expected_report_id") != case_spec["expected_report_id"]:
            raise ValueError("workspace manifest expected_report_id mismatch")
        if workspace_manifest.get("case_spec_sha256") != sha256(case_spec_path):
            raise ValueError("workspace manifest case spec hash mismatch")
        checks.append(
            make_check(
                "workflow.case_spec",
                True,
                {
                    "case_id": case_spec["case_id"],
                    "pair_id": workspace_manifest.get("pair_id"),
                    "sha256": sha256(case_spec_path),
                },
            )
        )
    except (FileNotFoundError, KeyError, json.JSONDecodeError, OSError, ValueError) as exc:
        checks.append(make_check("workflow.case_spec", False, str(exc)))

    try:
        integrity = verify_integrity_receipt(workspace, args.receipt.resolve(), args.route)
        checks.append(make_check("workflow.executor_integrity", True, integrity))
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        checks.append(make_check("workflow.executor_integrity", False, str(exc)))

    checks.append(make_check("delivery.html_exists", html.is_file(), str(html)))
    checks.append(make_check("delivery.handoff_exists", handoff.is_file(), str(handoff)))
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        validate_metadata(
            metadata,
            args.route,
            case_spec.get("case_id") if case_spec else None,
            workspace_manifest.get("pair_id") if workspace_manifest else None,
        )
        checks.append(make_check("workflow.metadata", True, str(metadata_path)))
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        checks.append(make_check("workflow.metadata", False, str(exc)))

    if html.is_file() and case_spec is not None:
        deck = DeckParser()
        deck.feed(html.read_text(encoding="utf-8", errors="replace"))
        visible_text = " ".join(deck.text)
        missing = [item for item in case_spec["required_text"] if item not in visible_text]
        disclosures = [item for item in case_spec["disclosure_text"] if item in visible_text]
        output_text = visible_text
        if handoff.is_file():
            output_text += " " + handoff.read_text(encoding="utf-8", errors="replace")
        ir_output = workspace / "report-ir.json"
        if ir_output.is_file():
            output_text += " " + ir_output.read_text(encoding="utf-8", errors="replace")
        forbidden_found = [item for item in case_spec["forbidden_text"] if item in output_text]
        checks.extend(
            (
                make_check(
                    "content.expected_pages",
                    deck.slide_count == case_spec["slide_count"],
                    {"expected": case_spec["slide_count"], "actual": deck.slide_count},
                ),
                make_check("content.fixed_copy", not missing, {"missing": missing}),
                make_check(
                    "content.synthetic_boundary",
                    len(disclosures) >= case_spec["required_minimum_disclosures"],
                    {
                        "found": disclosures,
                        "required_minimum": case_spec["required_minimum_disclosures"],
                    },
                ),
                make_check(
                    "content.case_identity",
                    deck.benchmark_case == case_spec["expected_report_id"],
                    {
                        "expected": case_spec["expected_report_id"],
                        "actual": deck.benchmark_case,
                    },
                ),
                make_check(
                    "content.no_cross_case_reuse",
                    not forbidden_found,
                    {"forbidden_found": forbidden_found},
                ),
            )
        )

        skill_root = workspace / "skill" / "taohtml"
        asset_checker = skill_root / "scripts" / "check_assets.py"
        browser_checker = skill_root / "scripts" / "check_html_deck.py"
        asset_record = run(
            [sys.executable, str(asset_checker), "--strict-offline", str(html)],
            workspace,
        )
        browser_record = run(
            [sys.executable, str(browser_checker), str(html), str(browser_qa_dir)],
            workspace,
        )
        commands["asset_qa"] = asset_record
        commands["browser_qa"] = browser_record
        browser_mode = None
        browser_report = browser_qa_dir / "qa-report.json"
        if browser_report.is_file():
            try:
                browser_data = json.loads(browser_report.read_text(encoding="utf-8"))
                browser_mode = browser_data.get("runtime_behavior", {}).get("before", {}).get("mode")
            except (json.JSONDecodeError, OSError, AttributeError):
                browser_mode = None
        checks.append(
            make_check(
                "runtime.presentation_mode",
                deck.deck_mode == "presentation" or browser_mode == "presentation",
                {"static": deck.deck_mode, "browser": browser_mode},
            )
        )
        checks.append(
            make_check("qa.strict_offline", asset_record["returncode"] == 0, asset_record["output"])
        )
        checks.append(
            make_check(
                "qa.browser",
                browser_record["returncode"] == 0,
                {
                    "output": browser_record["output"],
                    "report": str(browser_qa_dir / "qa-report.json"),
                },
            )
        )

    if handoff.is_file():
        handoff_text = handoff.read_text(encoding="utf-8", errors="replace")
        checks.append(
            make_check(
                "handoff.pending_verification_list",
                "待核实内容清单" in handoff_text,
                str(handoff),
            )
        )

    if args.route == "ir":
        ir = workspace / "report-ir.json"
        manifest = workspace / "deliverable" / "build-manifest.json"
        checks.append(make_check("ir.source_exists", ir.is_file(), str(ir)))
        checks.append(make_check("ir.manifest_exists", manifest.is_file(), str(manifest)))
        ir_data: dict[str, Any] | None = None
        if ir.is_file() and case_spec is not None:
            try:
                ir_data = json.loads(ir.read_text(encoding="utf-8"))
                actual_report_id = ir_data.get("report", {}).get("id")
                checks.append(
                    make_check(
                        "ir.case_identity",
                        actual_report_id == case_spec["expected_report_id"],
                        {
                            "expected": case_spec["expected_report_id"],
                            "actual": actual_report_id,
                        },
                    )
                )
            except (json.JSONDecodeError, OSError, AttributeError) as exc:
                checks.append(make_check("ir.case_identity", False, str(exc)))
        if ir.is_file() and manifest.is_file() and html.is_file():
            try:
                manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
                controller_adapter = Path(__file__).with_name("report_ir_adapter.py")
                manifest_evidence = validate_ir_manifest(
                    manifest_data,
                    workspace,
                    ir,
                    html,
                    controller_adapter,
                )
                checks.append(make_check("ir.manifest_integrity", True, manifest_evidence))
                if ir_data is None:
                    raise ValueError("Report IR could not be loaded for source status validation")
                try:
                    source_binding_evidence = validate_ir_source_binding(
                        ir_data,
                        manifest_data,
                        deck,
                    )
                    checks.append(
                        make_check(
                            "ir.source_status_consistency",
                            True,
                            source_binding_evidence,
                        )
                    )
                except ValueError as exc:
                    checks.append(
                        make_check("ir.source_status_consistency", False, str(exc))
                    )
                theme = manifest_data["theme_id"]
                with tempfile.TemporaryDirectory(prefix="report-ir-v0-judge-") as temp:
                    rebuilt = Path(temp) / "index.html"
                    rebuilt_manifest = Path(temp) / "build-manifest.json"
                    record = run(
                        [
                            sys.executable,
                            str(controller_adapter),
                            "--ir",
                            str(ir),
                            "--workspace-root",
                            str(workspace),
                            "--skill-root",
                            str(workspace / "skill" / "taohtml"),
                            "--theme",
                            theme,
                            "--output",
                            str(rebuilt),
                            "--manifest",
                            str(rebuilt_manifest),
                        ],
                        workspace,
                    )
                    commands["ir_recompile"] = record
                    exact = record["returncode"] == 0 and sha256(rebuilt) == sha256(html)
                    normalized_equal = False
                    if record["returncode"] == 0 and rebuilt.is_file():
                        original_bytes = html.read_bytes()
                        rebuilt_bytes = rebuilt.read_bytes()
                        normalized_equal = original_bytes.replace(b"\r\n", b"\n") == rebuilt_bytes.replace(
                            b"\r\n", b"\n"
                        )
                    checks.append(
                        make_check(
                            "ir.deterministic_recompile",
                            exact,
                            {
                                "original_sha256": sha256(html),
                                "rebuilt_sha256": sha256(rebuilt) if rebuilt.is_file() else None,
                                "equal_after_line_ending_normalization": normalized_equal,
                                "compiler_output": record["output"],
                            },
                        )
                    )
            except (KeyError, json.JSONDecodeError, OSError, ValueError) as exc:
                if not any(item["id"] == "ir.manifest_integrity" for item in checks):
                    checks.append(make_check("ir.manifest_integrity", False, str(exc)))
                if not any(item["id"] == "ir.source_status_consistency" for item in checks):
                    checks.append(make_check("ir.source_status_consistency", False, str(exc)))
                checks.append(make_check("ir.deterministic_recompile", False, str(exc)))

    status = "PASS" if checks and all(item["status"] == "PASS" for item in checks) else "FAIL"
    result = {
        "result_version": "report-ir-v0-workbuddy-judge-4",
        "route": args.route,
        "status": status,
        "case": {
            "case_id": case_spec.get("case_id") if case_spec else None,
            "pair_id": workspace_manifest.get("pair_id") if workspace_manifest else None,
            "expected_report_id": case_spec.get("expected_report_id") if case_spec else None,
            "case_spec_sha256": sha256(workspace / "input" / "case-spec.json")
            if (workspace / "input" / "case-spec.json").is_file()
            else None,
        },
        "checks": checks,
        "commands": commands,
        "usage": {
            "source": "run-metadata.json",
            "rule": "use exact platform values when exposed; otherwise unavailable; never estimate",
            "recorded": {
                "duration_seconds": metadata.get("duration_seconds"),
                "token_usage": metadata.get("token_usage"),
                "billing_usage": metadata.get("billing_usage"),
            }
            if metadata
            else None,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"JUDGE_{status} {output}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
