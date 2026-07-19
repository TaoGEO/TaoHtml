#!/usr/bin/env python3
"""Fail-closed controller acceptance for one returned black-box participant run."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from blackbox_contract import (
    ANSWER_ROOT,
    RECEIPT_VERSION,
    REQUIRED_OUTPUTS,
    RESULT_CONTRACT_VERSION,
    RUN_CONTRACT_VERSION,
    SHA256,
    SUBMISSION_CONTRACT_VERSION,
    ContractError,
    acceptance_toolchain_sha256,
    assert_no_answer_leakage,
    directory_tree_sha256,
    evaluate_assertions,
    file_hashes,
    load_answer_key,
    load_json,
    normalize_returned_root,
    parse_utc,
    resolve_regular_file,
    safe_extract_zip,
    safe_relative_path,
    sha256_file,
    result_hmac_sha256,
    tree_sha256,
    utc_now,
    write_json,
)


def _production_modules() -> tuple[Any, Any, Any]:
    from blackbox_contract import REPOSITORY_ROOT

    scripts = REPOSITORY_ROOT / "skill" / "taohtml" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import compile_report_ir
    import report_ir_core
    import validate_project_handoff

    return report_ir_core, compile_report_ir, validate_project_handoff


def _run(command: list[str], cwd: Path) -> dict[str, Any]:
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
        "status": "PASS" if completed.returncode == 0 else "FAIL",
    }


def _all_pass(records: list[dict[str, Any]]) -> bool:
    return bool(records) and all(record.get("status") == "PASS" for record in records)


def _check(check_id: str, passed: bool, evidence: Any, *, status: str | None = None) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": status or ("PASS" if passed else "FAIL"),
        "evidence": evidence,
    }


def _normalize_usage(value: object, label: str, fields: tuple[str, ...]) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    if not isinstance(value, dict):
        return {"availability": "unknown", **{field: None for field in fields}}, [
            f"{label} must be an object"
        ]
    availability = value.get("availability")
    normalized = copy.deepcopy(value)
    if availability not in {"exact", "unknown"}:
        issues.append(f"{label}.availability must be exact or unknown")
    for field in fields:
        item = value.get(field)
        if item is not None and (
            not isinstance(item, (int, float)) or isinstance(item, bool) or item < 0
        ):
            issues.append(f"{label}.{field} must be null or a non-negative number")
    if availability == "unknown" and any(value.get(field) is not None for field in fields):
        issues.append(f"unknown {label} cannot contain estimated numbers")
    if availability == "exact" and not any(value.get(field) is not None for field in fields):
        issues.append(f"exact {label} requires a numeric value")
    return normalized, issues


def validate_audit(value: object) -> tuple[dict[str, Any], list[str]]:
    fallback = {
        "platform": "unknown",
        "agent": "unknown",
        "model": "unknown",
        "started_at": None,
        "ended_at": None,
        "tokens": {
            "availability": "unknown",
            "source": "unknown",
            "input": None,
            "output": None,
            "cache": None,
            "total": None,
        },
        "points": {
            "availability": "unknown",
            "source": "unknown",
            "value": None,
            "balance_before": None,
            "balance_after": None,
        },
    }
    if not isinstance(value, dict):
        return fallback, ["audit must be an object"]
    issues: list[str] = []
    normalized = copy.deepcopy(fallback)
    for field in ("platform", "agent", "model"):
        item = value.get(field)
        if not isinstance(item, str) or not item.strip():
            issues.append(f"audit.{field} must be a non-empty string")
        else:
            normalized[field] = item
    normalized["started_at"] = value.get("started_at")
    normalized["ended_at"] = value.get("ended_at")
    try:
        started = parse_utc(value.get("started_at"), "audit.started_at")
        ended = parse_utc(value.get("ended_at"), "audit.ended_at")
        if ended < started:
            issues.append("audit.ended_at cannot precede started_at")
    except ContractError as exc:
        issues.append(str(exc))
    tokens, token_issues = _normalize_usage(
        value.get("tokens"), "audit.tokens", ("input", "output", "cache", "total")
    )
    points, point_issues = _normalize_usage(
        value.get("points"),
        "audit.points",
        ("value", "balance_before", "balance_after"),
    )
    if isinstance(tokens, dict):
        token_source = tokens.get("source")
        if token_source not in {"platform_task_usage", "manual", "unknown"}:
            token_issues.append("audit.tokens.source is unsupported")
        if tokens.get("availability") == "unknown" and token_source != "unknown":
            token_issues.append("unknown audit.tokens must use source=unknown")
        if tokens.get("availability") == "exact" and token_source == "unknown":
            token_issues.append("exact audit.tokens requires a concrete source")
    if isinstance(points, dict):
        source = points.get("source")
        if source not in {"platform_task_usage", "balance_delta", "manual", "unknown"}:
            point_issues.append("audit.points.source is unsupported")
        if points.get("availability") == "unknown" and source != "unknown":
            point_issues.append("unknown audit.points must use source=unknown")
        if points.get("availability") == "exact" and source == "unknown":
            point_issues.append("exact audit.points requires a concrete source")
        before = points.get("balance_before")
        after = points.get("balance_after")
        if source == "balance_delta":
            if before is None or after is None or points.get("value") is None:
                point_issues.append(
                    "balance_delta audit.points requires value, balance_before, and balance_after"
                )
            elif before - after != points.get("value"):
                point_issues.append("balance_delta audit.points value does not match balances")
        elif before is not None or after is not None:
            point_issues.append(
                "non-balance_delta audit.points cannot claim balance measurements"
            )
    normalized["tokens"] = tokens
    normalized["points"] = points
    issues.extend(token_issues)
    issues.extend(point_issues)
    return normalized, issues


def verify_returned_package(
    receipt: dict[str, Any], returned_root: Path
) -> tuple[Path, dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    assert_no_answer_leakage(
        returned_root, exclude_prefixes=(receipt["output_directory"],)
    )
    run_path = resolve_regular_file(returned_root, "run.json", "returned run manifest")
    run_manifest = load_json(run_path)
    checks.append(
        _check(
            "run_manifest_hash",
            sha256_file(run_path) == receipt["run_manifest_sha256"],
            {"expected": receipt["run_manifest_sha256"], "actual": sha256_file(run_path)},
        )
    )
    identity_fields = (
        "run_id",
        "nonce",
        "scenario_id",
        "target_platform",
        "created_at",
        "output_directory",
        "input_tree_sha256",
    )
    identity_mismatches = {
        field: {"receipt": receipt.get(field), "returned": run_manifest.get(field)}
        for field in identity_fields
        if receipt.get(field) != run_manifest.get(field)
    }
    checks.append(_check("run_identity", not identity_mismatches, identity_mismatches))
    checks.append(
        _check(
            "run_contract_version",
            run_manifest.get("run_contract_version") == RUN_CONTRACT_VERSION,
            run_manifest.get("run_contract_version"),
        )
    )
    expected_input_hashes = receipt.get("input_files")
    if not isinstance(expected_input_hashes, dict):
        raise ContractError("controller receipt input_files is invalid")
    actual_input_hashes: dict[str, str] = {}
    input_issues: list[str] = []
    for value, expected_hash in sorted(expected_input_hashes.items()):
        try:
            actual_hash = sha256_file(resolve_regular_file(returned_root, value, f"returned input {value}"))
            actual_input_hashes[value] = actual_hash
            if actual_hash != expected_hash:
                input_issues.append(f"input hash mismatch: {value}")
        except ContractError as exc:
            input_issues.append(str(exc))
    actual_tree = tree_sha256(actual_input_hashes)
    if actual_tree != receipt["input_tree_sha256"]:
        input_issues.append("input tree hash mismatch")
    checks.append(
        _check(
            "immutable_inputs",
            not input_issues,
            {"issues": input_issues, "actual_tree_sha256": actual_tree},
        )
    )

    output_relative = receipt["output_directory"]
    output_path = returned_root.joinpath(*safe_relative_path(output_relative, "output_directory").parts)
    allowed_files = set(receipt["participant_contents"])
    unexpected: list[str] = []
    for path in sorted(returned_root.rglob("*")):
        if path.is_symlink():
            unexpected.append(f"symlink: {path.relative_to(returned_root).as_posix()}")
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(returned_root).as_posix()
        if relative in allowed_files:
            continue
        try:
            path.relative_to(output_path)
        except ValueError:
            unexpected.append(relative)
    extra_submission_dirs: list[str] = []
    submission_root = returned_root / "submission"
    if submission_root.exists():
        for child in submission_root.iterdir():
            if child != output_path:
                extra_submission_dirs.append(child.name)
    checks.append(
        _check(
            "fresh_single_output_directory",
            output_path.is_dir() and not unexpected and not extra_submission_dirs,
            {
                "output_directory": output_relative,
                "exists": output_path.is_dir(),
                "unexpected_files": unexpected,
                "extra_submission_entries": extra_submission_dirs,
            },
        )
    )
    missing_outputs = [
        value for value in receipt["required_outputs"] if not (output_path / value).is_file()
    ]
    checks.append(_check("required_outputs", not missing_outputs, {"missing": missing_outputs}))
    if missing_outputs:
        return output_path, run_manifest, {}, checks

    submission = load_json(output_path / "submission.json")
    top_level_required = {
        "submission_contract_version",
        "run_id",
        "nonce",
        "scenario_id",
        "input_tree_sha256",
        "audit",
        "isolation_attestation",
        "artifacts",
    }
    shape_ok = set(submission) == top_level_required
    checks.append(_check("submission_shape", shape_ok, sorted(submission)))
    submission_mismatches = {
        field: {"expected": receipt[field], "actual": submission.get(field)}
        for field in ("run_id", "nonce", "scenario_id", "input_tree_sha256")
        if submission.get(field) != receipt[field]
    }
    if submission.get("submission_contract_version") != SUBMISSION_CONTRACT_VERSION:
        submission_mismatches["submission_contract_version"] = {
            "expected": SUBMISSION_CONTRACT_VERSION,
            "actual": submission.get("submission_contract_version"),
        }
    checks.append(_check("submission_identity", not submission_mismatches, submission_mismatches))
    attestation = submission.get("isolation_attestation")
    required_attestation = {
        "package_root_only": True,
        "installed_taohtml_only_external_input": True,
        "no_prior_artifacts_used": True,
    }
    checks.append(_check("pollution_attestation", attestation == required_attestation, attestation))

    artifacts = submission.get("artifacts")
    artifact_issues: list[str] = []
    if not isinstance(artifacts, dict):
        artifact_issues.append("submission artifacts must be an object")
        artifacts = {}
    actual_output_files = {
        path.relative_to(output_path).as_posix()
        for path in output_path.rglob("*")
        if path.is_file() and path.name != "submission.json"
    }
    if set(artifacts) != actual_output_files:
        artifact_issues.append("submission artifact inventory does not match output files")
    for value, declared_hash in sorted(artifacts.items()):
        if not isinstance(declared_hash, str) or not SHA256.fullmatch(declared_hash):
            artifact_issues.append(f"invalid declared artifact hash: {value}")
            continue
        try:
            actual_hash = sha256_file(resolve_regular_file(output_path, value, f"submission artifact {value}"))
        except ContractError as exc:
            artifact_issues.append(str(exc))
            continue
        if actual_hash != declared_hash:
            artifact_issues.append(f"artifact hash mismatch: {value}")
    checks.append(_check("submission_artifact_hashes", not artifact_issues, artifact_issues))
    return output_path, run_manifest, submission, checks


def _brief_handoff_binding(handoff: dict[str, Any], brief_hash: str) -> dict[str, Any]:
    evidence: dict[str, Any] = {"issues": []}
    try:
        confirmation = handoff["confirmations"]["design_brief"]
        artifact_ref = confirmation["artifact_ref"]
        artifacts = handoff["artifacts"]
        artifact = next(item for item in artifacts if item["artifact_id"] == artifact_ref)
        evidence.update(
            {
                "confirmation_status": confirmation.get("status"),
                "confirmation_scope": confirmation.get("scope"),
                "artifact_ref": artifact_ref,
                "artifact_locator": artifact.get("locator", {}).get("value"),
                "artifact_sha256": artifact.get("sha256"),
            }
        )
        if confirmation.get("status") != "confirmed":
            evidence["issues"].append("handoff design brief is not confirmed")
        if confirmation.get("scope") != "current_snapshot":
            evidence["issues"].append("handoff design brief is not current_snapshot")
        if confirmation.get("artifact_sha256") != brief_hash or artifact.get("sha256") != brief_hash:
            evidence["issues"].append("handoff design brief hash does not match current brief")
        if artifact.get("locator", {}).get("value") != "design-brief.md":
            evidence["issues"].append("handoff design brief locator must be design-brief.md")
    except (KeyError, StopIteration, TypeError) as exc:
        evidence["issues"].append(f"handoff design brief binding is incomplete: {exc}")
    return evidence


def _evaluate_technical(
    output_root: Path,
    answer_key: dict[str, Any],
    qa_output_dir: Path,
    *,
    skip_browser: bool,
) -> tuple[dict[str, Any], bool]:
    report_ir_core, compiler, handoff_validator = _production_modules()
    checks: dict[str, Any] = {}
    required_paths = {
        value: resolve_regular_file(output_root, value, f"required output {value}")
        for value in REQUIRED_OUTPUTS
        if value != "submission.json"
    }
    brief_text = required_paths["design-brief.md"].read_text(encoding="utf-8")
    brief_hash = sha256_file(required_paths["design-brief.md"])
    ir = load_json(required_paths["report-ir.json"])
    manifest = load_json(required_paths["build/build-manifest.json"])
    handoff_bytes = required_paths["project-handoff.json"].read_bytes()
    handoff = load_json(required_paths["project-handoff.json"])

    profile = answer_key["expected_profile"]
    brief_profile_checks = [
        {
            "id": "profile_id_in_brief",
            "status": "PASS" if profile["primary_profile_id"] in brief_text else "FAIL",
            "evidence": profile["primary_profile_id"],
        },
        {
            "id": "customer_profile_name_in_brief",
            "status": "PASS" if profile["customer_facing_name"] in brief_text else "FAIL",
            "evidence": profile["customer_facing_name"],
        },
        {
            "id": "definition_version_in_brief",
            "status": "PASS" if profile["definition_version"] in brief_text else "FAIL",
            "evidence": profile["definition_version"],
        },
    ]
    checks["profile_routing"] = {
        "status": "PASS" if _all_pass(brief_profile_checks) else "FAIL",
        "expected": profile,
        "brief_checks": brief_profile_checks,
    }

    try:
        ir_validation = report_ir_core.validate_ir(ir, output_root)
        ir_public = {key: value for key, value in ir_validation.items() if key != "normalized_ir"}
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        ir_validation = {
            "schema_valid": False,
            "references_valid": False,
            "semantics_valid": False,
            "compiler_ready": False,
            "issues": {"exception": [str(exc)]},
            "workflow_profile": {"binding_state": "invalid"},
        }
        ir_public = ir_validation
    ir_assertions = evaluate_assertions(ir, answer_key["hard_assertions"]["report_ir"])
    ir_layers = {
        key: bool(ir_validation.get(key))
        for key in ("schema_valid", "references_valid", "semantics_valid", "compiler_ready")
    }
    ir_pass = all(ir_layers.values()) and _all_pass(ir_assertions)
    checks["report_ir"] = {
        "status": "PASS" if ir_pass else "FAIL",
        "layers": ir_layers,
        "qa_execution_claim": ir_validation.get("qa_execution_claim"),
        "hard_assertions": ir_assertions,
        "validator_result": ir_public,
    }

    traceability = ir.get("traceability") if isinstance(ir.get("traceability"), dict) else {}
    ir_brief_evidence = {
        "ref": traceability.get("design_brief_ref"),
        "declared_sha256": traceability.get("design_brief_sha256"),
        "confirmation": traceability.get("design_brief_confirmation"),
        "actual_sha256": brief_hash,
        "issues": [],
    }
    if traceability.get("design_brief_ref") != "design-brief.md":
        ir_brief_evidence["issues"].append("Report IR brief ref must be design-brief.md")
    if traceability.get("design_brief_sha256") != brief_hash:
        ir_brief_evidence["issues"].append("Report IR brief hash is absent or stale")
    if traceability.get("design_brief_confirmation") != "confirmed":
        ir_brief_evidence["issues"].append("Report IR brief confirmation is not confirmed")
    handoff_brief_evidence = _brief_handoff_binding(handoff, brief_hash)
    brief_pass = not ir_brief_evidence["issues"] and not handoff_brief_evidence["issues"]
    checks["design_brief_binding"] = {
        "status": "PASS" if brief_pass else "FAIL",
        "report_ir": ir_brief_evidence,
        "project_handoff": handoff_brief_evidence,
    }

    manifest_assertions = evaluate_assertions(
        manifest, answer_key["hard_assertions"]["build_manifest"]
    )
    manifest_issues: list[str] = []
    if manifest.get("qa_execution_claim") != "not_executed_by_compiler":
        manifest_issues.append("compiler must not claim it executed QA")
    expected_output_refs = {
        "html": "index.html",
        "source_map": "source-map.json",
        "normalized_ir": "report.ir.normalized.json",
    }
    outputs = manifest.get("outputs") if isinstance(manifest.get("outputs"), dict) else {}
    for key, relative in expected_output_refs.items():
        record = outputs.get(key) if isinstance(outputs, dict) else None
        file_path = output_root / "build" / relative
        if not isinstance(record, dict) or record.get("ref") != relative:
            manifest_issues.append(f"manifest outputs.{key}.ref mismatch")
        elif record.get("sha256") != sha256_file(file_path):
            manifest_issues.append(f"manifest outputs.{key}.sha256 mismatch")
    if manifest.get("report_ir", {}).get("ref") != "report-ir.json":
        manifest_issues.append("manifest report_ir.ref must be report-ir.json")
    recompile_evidence: dict[str, Any] = {"files": {}, "issues": []}
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            recompile = Path(temp_dir) / "build"
            theme_binding = ir.get("build_binding", {}).get("theme", {})
            project_theme_dir = (
                output_root / "project-theme"
                if theme_binding.get("kind") == "project_theme"
                else None
            )
            compiled_manifest = compiler.compile_ir(
                ir,
                output_root,
                recompile,
                report_ir_ref="report-ir.json",
                project_theme_dir=project_theme_dir,
            )
            for relative in (
                "index.html",
                "source-map.json",
                "report.ir.normalized.json",
                "build-manifest.json",
            ):
                returned_hash = sha256_file(output_root / "build" / relative)
                recompiled_hash = sha256_file(recompile / relative)
                matches = returned_hash == recompiled_hash
                recompile_evidence["files"][relative] = {
                    "status": "PASS" if matches else "FAIL",
                    "returned_sha256": returned_hash,
                    "recompiled_sha256": recompiled_hash,
                }
                if not matches:
                    recompile_evidence["issues"].append(
                        f"returned {relative} differs from current deterministic compiler"
                    )
            if compiled_manifest.get("workflow_profile") != manifest.get("workflow_profile"):
                recompile_evidence["issues"].append("recompiled Profile binding differs")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        recompile_evidence["issues"].append(f"controller recompile failed: {exc}")
    manifest_pass = (
        not manifest_issues
        and not recompile_evidence["issues"]
        and _all_pass(manifest_assertions)
    )
    checks["compiler_manifest_html"] = {
        "status": "PASS" if manifest_pass else "FAIL",
        "issues": manifest_issues,
        "hard_assertions": manifest_assertions,
        "controller_recompile": recompile_evidence,
        "compiler_qa_execution_claim": manifest.get("qa_execution_claim"),
    }

    handoff_assertions = evaluate_assertions(
        handoff, answer_key["hard_assertions"]["project_handoff"]
    )
    try:
        handoff_result = handoff_validator.evaluate_handoff(
            handoff, output_root, handoff_bytes=handoff_bytes
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        handoff_result = {
            "readiness": {
                "schema_valid": False,
                "bindings_valid": False,
                "continuation_ready": False,
                "delivery_ready": False,
            },
            "blocking_reasons": {"exception": [str(exc)]},
            "qa_execution_claim": "not_executed_by_validator",
        }
    readiness = handoff_result.get("readiness", {})
    handoff_pass = (
        isinstance(readiness, dict)
        and all(readiness.get(key) is True for key in (
            "schema_valid",
            "bindings_valid",
            "continuation_ready",
            "delivery_ready",
        ))
        and handoff_result.get("qa_execution_claim") == "not_executed_by_validator"
        and _all_pass(handoff_assertions)
    )
    checks["project_handoff"] = {
        "status": "PASS" if handoff_pass else "FAIL",
        "readiness": readiness,
        "qa_execution_claim": handoff_result.get("qa_execution_claim"),
        "hard_assertions": handoff_assertions,
        "validator_result": handoff_result,
    }

    returned_records = {
        "source": "project-handoff validator",
        "execution_claim": handoff_result.get("qa_execution_claim"),
        "records": [
            {
                "record_id": record.get("record_id"),
                "check_type": record.get("check_type"),
                "status": record.get("status"),
                "record_artifact_ref": record.get("record_artifact_ref"),
            }
            for record in handoff.get("qa_records", [])
            if isinstance(record, dict)
        ],
        "meaning": "existing structured records were validated; they were not executed by the handoff validator",
    }
    from blackbox_contract import REPOSITORY_ROOT

    skill_scripts = REPOSITORY_ROOT / "skill" / "taohtml" / "scripts"
    asset_run = _run(
        [
            sys.executable,
            str(skill_scripts / "check_assets.py"),
            str(output_root / "build" / "index.html"),
            "--strict-offline",
        ],
        output_root,
    )
    if skip_browser:
        browser_run = {
            "command": None,
            "returncode": None,
            "output": "browser QA explicitly skipped by controller",
            "status": "NOT_RUN",
        }
    else:
        if qa_output_dir.exists():
            raise ContractError(f"controller QA output already exists: {qa_output_dir}")
        browser_run = _run(
            [
                sys.executable,
                str(skill_scripts / "check_html_deck.py"),
                str(output_root / "build" / "index.html"),
                str(qa_output_dir),
                "--width",
                "1600",
                "--height",
                "900",
            ],
            output_root,
        )
    controller_execution = {
        "asset_qa": asset_run,
        "browser_runtime_editor_qa": browser_run,
        "traceability_verification": {
            "status": "PASS"
            if ir_pass and brief_pass and manifest_pass and handoff_pass
            else "FAIL",
            "source": "accept_run.py current evaluation",
        },
        "delivery_integrity": {
            "status": "PASS" if manifest_pass and handoff_pass else "FAIL",
            "source": "accept_run.py current hash and binding evaluation",
        },
        "meaning": "these checks were executed by the controller for this acceptance run",
    }
    controller_qa_pass = all(
        record["status"] == "PASS"
        for record in (
            asset_run,
            browser_run,
            controller_execution["traceability_verification"],
            controller_execution["delivery_integrity"],
        )
    )
    checks["qa_boundary"] = {
        "status": "PASS" if controller_qa_pass else "FAIL",
        "returned_record_validation": returned_records,
        "controller_execution": controller_execution,
    }

    technical_pass = all(
        checks[key]["status"] == "PASS"
        for key in (
            "profile_routing",
            "design_brief_binding",
            "report_ir",
            "compiler_manifest_html",
            "project_handoff",
            "qa_boundary",
        )
    )
    return checks, technical_pass


def load_human_review(
    path: Path | None,
    answer_key: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    dimensions = answer_key["human_review_dimensions"]
    if path is None:
        return {
            "status": "PENDING",
            "dimensions": {
                dimension: {"status": "PENDING", "note": "尚未人工验收"}
                for dimension in dimensions
            },
            "source": None,
        }
    value = load_json(path)
    required = {
        "review_version",
        "scenario_id",
        "run_id",
        "status",
        "dimensions",
        "reviewer",
        "reviewed_at",
    }
    issues: list[str] = []
    if set(value) != required or value.get("review_version") != "1.0":
        issues.append("human review fields drifted")
    if value.get("scenario_id") != answer_key["scenario_id"] or value.get("run_id") != run_id:
        issues.append("human review run identity mismatch")
    raw_dimensions = value.get("dimensions")
    if not isinstance(raw_dimensions, dict) or set(raw_dimensions) != set(dimensions):
        issues.append("human review dimensions mismatch")
    else:
        for name, record in raw_dimensions.items():
            if (
                not isinstance(record, dict)
                or set(record) != {"status", "note"}
                or record.get("status") not in {"PASS", "FAIL"}
                or not isinstance(record.get("note"), str)
                or not record["note"].strip()
            ):
                issues.append(f"invalid human review dimension: {name}")
    try:
        parse_utc(value.get("reviewed_at"), "human_review.reviewed_at")
    except ContractError as exc:
        issues.append(str(exc))
    if value.get("status") not in {"PASS", "FAIL"}:
        issues.append("human review status must be PASS or FAIL")
    if isinstance(raw_dimensions, dict):
        all_dimension_pass = all(
            isinstance(record, dict) and record.get("status") == "PASS"
            for record in raw_dimensions.values()
        )
        if (value.get("status") == "PASS") != all_dimension_pass:
            issues.append("human review overall status contradicts dimensions")
    if issues:
        return {
            "status": "INVALID",
            "dimensions": raw_dimensions if isinstance(raw_dimensions, dict) else {},
            "source": str(path),
            "issues": issues,
        }
    return {**value, "source": str(path)}


def _markdown(result: dict[str, Any]) -> str:
    lines = [
        "# TaoHtml 跨 Agent 黑盒验收表",
        "",
        f"- run_id：`{result['run']['run_id']}`",
        f"- scenario：`{result['run']['scenario_id']}`",
        f"- target platform：`{result['run']['target_platform']}`",
        f"- 自动结论：`{result['automatic_status']}`",
        f"- 人工结论：`{result['human_review']['status']}`",
        f"- 最终结论：`{result['overall_status']}`",
        "",
        "| 自动检查 | 结论 |",
        "|---|---|",
    ]
    for name, record in result["checks"].items():
        lines.append(f"| `{name}` | {record['status']} |")
    lines.extend(
        [
            "",
            "## 人工验收（不会由自动检查代填）",
            "",
            "| 维度 | 结论 | 说明 |",
            "|---|---|---|",
        ]
    )
    for name, record in result["human_review"]["dimensions"].items():
        note = str(record.get("note", "")).replace("|", "\\|")
        lines.append(f"| `{name}` | {record.get('status', 'PENDING')} | {note} |")
    lines.extend(
        [
            "",
            "> 视觉审美、正式阅读体验、实际演讲效果和企业模板保真必须由人实际查看；自动 PASS 不代表这些维度已通过。",
            "",
        ]
    )
    return "\n".join(lines)


def accept(
    receipt_path: Path,
    returned_path: Path,
    result_path: Path,
    *,
    human_review_path: Path | None = None,
    skip_browser: bool = False,
) -> dict[str, Any]:
    if result_path.exists():
        raise ContractError(f"result output already exists: {result_path}")
    markdown_path = result_path.with_suffix(".md")
    if markdown_path.exists():
        raise ContractError(f"acceptance table already exists: {markdown_path}")
    if result_path.parent.resolve() != receipt_path.parent.resolve():
        raise ContractError(
            "result output must share the controller receipt directory for matrix provenance"
        )
    if returned_path.is_dir():
        returned_resolved = returned_path.resolve()
        for path, label in (
            (result_path, "result output"),
            (receipt_path, "controller receipt"),
            (human_review_path, "human review"),
        ):
            if path is None:
                continue
            try:
                path.resolve().relative_to(returned_resolved)
            except ValueError:
                continue
            raise ContractError(f"{label} must remain outside the returned participant root")
    receipt = load_json(receipt_path)
    if receipt.get("receipt_version") != RECEIPT_VERSION:
        raise ContractError("controller receipt version is unsupported")
    current_toolchain_sha256 = acceptance_toolchain_sha256()
    if receipt.get("acceptance_toolchain_sha256") != current_toolchain_sha256:
        raise ContractError(
            "acceptance toolchain drifted after run preparation; prepare a fresh run"
        )
    answer_key = load_answer_key(receipt["scenario_id"])
    key_path = ANSWER_ROOT / f"{receipt['scenario_id']}.json"
    if sha256_file(key_path) != receipt.get("answer_key_sha256"):
        raise ContractError("controller answer key hash drifted after run preparation")

    with tempfile.TemporaryDirectory() as temp_dir:
        if returned_path.is_file():
            returned_artifact = {
                "kind": "zip",
                "sha256": sha256_file(returned_path),
            }
            returned_root = safe_extract_zip(returned_path, Path(temp_dir) / "returned")
        elif returned_path.is_dir():
            returned_root = normalize_returned_root(returned_path.resolve())
            returned_artifact = {
                "kind": "directory_tree",
                "sha256": directory_tree_sha256(returned_root),
            }
        else:
            raise ContractError(f"returned path does not exist: {returned_path}")
        try:
            output_root, run_manifest, submission, integrity_checks = verify_returned_package(
                receipt, returned_root
            )
        except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
            output_root = returned_root / receipt["output_directory"]
            run_manifest = {}
            submission = {}
            integrity_checks = [_check("returned_package_integrity", False, str(exc))]
        integrity_pass = _all_pass(integrity_checks)
        audit, audit_issues = validate_audit(submission.get("audit"))
        checks: dict[str, Any] = {
            "participant_integrity": {
                "status": "PASS" if integrity_pass else "FAIL",
                "checks": integrity_checks,
            }
        }
        technical_pass = False
        if integrity_pass:
            qa_output_dir = result_path.parent / f"{result_path.stem}-qa"
            try:
                technical_checks, technical_pass = _evaluate_technical(
                    output_root,
                    answer_key,
                    qa_output_dir,
                    skip_browser=skip_browser,
                )
                checks.update(technical_checks)
            except (ContractError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                checks["technical_evaluation"] = _check(
                    "technical_evaluation", False, f"fail-closed exception: {exc}"
                )
                technical_pass = False
        automatic_pass = integrity_pass and technical_pass

    human_review = load_human_review(
        human_review_path, answer_key, receipt["run_id"]
    )
    if not automatic_pass:
        overall_status = "FAIL"
    elif human_review["status"] == "PASS":
        overall_status = "PASS"
    elif human_review["status"] in {"FAIL", "INVALID"}:
        overall_status = "FAIL"
    else:
        overall_status = "AWAITING_HUMAN"
    result = {
        "result_contract_version": RESULT_CONTRACT_VERSION,
        "evaluated_at": utc_now(),
        "run": {
            "run_id": receipt["run_id"],
            "nonce": receipt["nonce"],
            "scenario_id": receipt["scenario_id"],
            "target_platform": receipt["target_platform"],
            "created_at": receipt["created_at"],
            "source_commit": receipt["source_commit"],
            "input_tree_sha256": receipt["input_tree_sha256"],
        },
        "audit": {
            **audit,
            "validation_issues": audit_issues,
            "used_for_automatic_pass": False,
        },
        "automatic_status": "PASS" if automatic_pass else "FAIL",
        "human_review": human_review,
        "overall_status": overall_status,
        "checks": checks,
        "claims": {
            "model_evaluator_used": False,
            "network_used": False,
            "workbuddy_run_executed_by_this_script": False,
            "visual_aesthetics_automatically_passed": False,
            "actual_presentation_effect_automatically_passed": False,
        },
        "provenance": {
            "controller_receipt_sha256": sha256_file(receipt_path),
            "run_manifest_sha256": receipt["run_manifest_sha256"],
            "answer_key_sha256": receipt["answer_key_sha256"],
            "participant_zip_sha256": receipt["participant_zip_sha256"],
            "returned_artifact": returned_artifact,
            "acceptance_toolchain_sha256": current_toolchain_sha256,
        },
    }
    result["provenance"]["result_hmac_sha256"] = result_hmac_sha256(
        result, receipt["matrix_hmac_key"]
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(result_path, result)
    markdown_path.write_text(_markdown(result), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--returned", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--human-review", type=Path)
    parser.add_argument(
        "--skip-browser",
        action="store_true",
        help="Development only: records browser QA as NOT_RUN and cannot PASS.",
    )
    args = parser.parse_args()
    try:
        result = accept(
            args.receipt.resolve(),
            args.returned.resolve(),
            args.output.resolve(),
            human_review_path=(
                args.human_review.resolve() if args.human_review is not None else None
            ),
            skip_browser=args.skip_browser,
        )
    except (ContractError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ACCEPT_FAILED {exc}", file=sys.stderr)
        return 1
    print(
        "ACCEPT_RESULT "
        f"automatic={result['automatic_status']} "
        f"human={result['human_review']['status']} "
        f"overall={result['overall_status']}"
    )
    print(f"MACHINE_RESULT {args.output.resolve()}")
    print(f"HUMAN_TABLE {args.output.resolve().with_suffix('.md')}")
    return 0 if result["automatic_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
