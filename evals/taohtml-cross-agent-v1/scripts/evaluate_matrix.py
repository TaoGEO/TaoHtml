#!/usr/bin/env python3
"""Verify authenticated acceptance results before opening the full matrix gate."""

from __future__ import annotations

import argparse
import hmac
import itertools
import json
import re
import sys
from pathlib import Path
from typing import Any

from blackbox_contract import (
    ANSWER_ROOT,
    CONTROLLER_ROOT,
    NONCE,
    RECEIPT_VERSION,
    RESULT_CONTRACT_VERSION,
    RESULT_PROVENANCE_KEYS,
    SAFE_ID,
    SHA256,
    ContractError,
    acceptance_toolchain_sha256,
    load_answer_key,
    load_json,
    parse_utc,
    result_hmac_sha256,
    sha256_file,
    utc_now,
    write_json,
)


RESULT_KEYS = {
    "result_contract_version",
    "evaluated_at",
    "run",
    "audit",
    "automatic_status",
    "human_review",
    "overall_status",
    "checks",
    "claims",
    "provenance",
}
RUN_KEYS = {
    "run_id",
    "nonce",
    "scenario_id",
    "target_platform",
    "created_at",
    "source_commit",
    "input_tree_sha256",
}
AUDIT_KEYS = {
    "platform",
    "agent",
    "model",
    "started_at",
    "ended_at",
    "tokens",
    "points",
    "validation_issues",
    "used_for_automatic_pass",
}
TOKEN_KEYS = {"availability", "source", "input", "output", "cache", "total"}
POINT_KEYS = {
    "availability",
    "source",
    "value",
    "balance_before",
    "balance_after",
}
CLAIMS = {
    "model_evaluator_used": False,
    "network_used": False,
    "workbuddy_run_executed_by_this_script": False,
    "visual_aesthetics_automatically_passed": False,
    "actual_presentation_effect_automatically_passed": False,
}
AUTOMATIC_CHECK_KEYS = {
    "participant_integrity",
    "profile_routing",
    "design_brief_binding",
    "report_ir",
    "compiler_manifest_html",
    "project_handoff",
    "qa_boundary",
}
INTEGRITY_CHECK_IDS = {
    "run_manifest_hash",
    "run_identity",
    "run_contract_version",
    "immutable_inputs",
    "fresh_single_output_directory",
    "required_outputs",
    "submission_shape",
    "submission_identity",
    "pollution_attestation",
    "submission_artifact_hashes",
}
READINESS_KEYS = {
    "schema_valid",
    "bindings_valid",
    "continuation_ready",
    "delivery_ready",
}
IR_LAYER_KEYS = {
    "schema_valid",
    "references_valid",
    "semantics_valid",
    "compiler_ready",
}
RECEIPT_KEYS = {
    "receipt_version",
    "run_id",
    "nonce",
    "scenario_id",
    "target_platform",
    "created_at",
    "output_directory",
    "required_outputs",
    "input_files",
    "input_tree_sha256",
    "run_manifest_sha256",
    "participant_zip_sha256",
    "answer_key_sha256",
    "acceptance_toolchain_sha256",
    "matrix_hmac_key",
    "source_commit",
    "participant_contents",
    "controller_answer_embedded",
    "expected_profile_embedded",
}


def result_paths(inputs: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for value in inputs:
        if value.is_dir():
            paths.extend(sorted(value.rglob("result.json")))
            paths.extend(sorted(value.rglob("*-result.json")))
        elif value.is_file():
            paths.append(value)
        else:
            raise ContractError(f"result input does not exist: {value}")
    unique: dict[Path, None] = {}
    for path in paths:
        unique[path.resolve()] = None
    return list(unique)


def _exact_keys(value: object, expected: set[str], label: str, issues: list[str]) -> bool:
    if not isinstance(value, dict):
        issues.append(f"{label} must be an object")
        return False
    actual = set(value)
    if actual != expected:
        issues.append(
            f"{label} fields drifted: missing={sorted(expected - actual)} extra={sorted(actual - expected)}"
        )
        return False
    return True


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _all_status_pass(records: object, label: str, issues: list[str]) -> bool:
    if not isinstance(records, list) or not records:
        issues.append(f"{label} must be a non-empty array")
        return False
    passed = True
    for index, record in enumerate(records):
        if not isinstance(record, dict) or record.get("status") != "PASS":
            issues.append(f"{label}[{index}] is not PASS")
            passed = False
    return passed


def _validate_hard_assertions(
    records: object,
    expected: object,
    label: str,
    issues: list[str],
) -> None:
    if not isinstance(records, list) or not isinstance(expected, list):
        issues.append(f"{label} hard assertions must be arrays")
        return
    if len(records) != len(expected):
        issues.append(f"{label} hard assertion count does not match the answer key")
        return
    for index, (record, assertion) in enumerate(zip(records, expected)):
        if (
            not isinstance(record, dict)
            or set(record) != {"path", "expected", "actual", "status", "error"}
            or not isinstance(assertion, dict)
            or set(assertion) != {"path", "equals"}
            or record.get("path") != assertion.get("path")
            or record.get("expected") != assertion.get("equals")
            or record.get("actual") != assertion.get("equals")
            or record.get("status") != "PASS"
            or record.get("error") is not None
        ):
            issues.append(f"{label} hard assertion[{index}] is not an exact answer-key PASS")


def _validate_human_pass(
    human: object,
    answer_key: dict[str, Any],
    run_id: str,
    issues: list[str],
) -> None:
    expected_keys = {
        "review_version",
        "scenario_id",
        "run_id",
        "status",
        "dimensions",
        "reviewer",
        "reviewed_at",
        "source",
    }
    if not _exact_keys(human, expected_keys, "human_review PASS record", issues):
        return
    assert isinstance(human, dict)
    if human["review_version"] != "1.0":
        issues.append("human_review.review_version is unsupported")
    if human["scenario_id"] != answer_key["scenario_id"] or human["run_id"] != run_id:
        issues.append("human_review identity does not match the accepted run")
    if human["status"] != "PASS":
        issues.append("human_review PASS validator received a non-PASS status")
    if not _nonempty_text(human["reviewer"]) or not _nonempty_text(human["source"]):
        issues.append("human_review reviewer and source must be recorded")
    try:
        parse_utc(human["reviewed_at"], "human_review.reviewed_at")
    except ContractError as exc:
        issues.append(str(exc))
    dimensions = human["dimensions"]
    expected_dimensions = set(answer_key["human_review_dimensions"])
    if not isinstance(dimensions, dict) or set(dimensions) != expected_dimensions:
        issues.append("human_review dimensions do not match the controller answer key")
        return
    for name, record in dimensions.items():
        if (
            not isinstance(record, dict)
            or set(record) != {"status", "note"}
            or record.get("status") != "PASS"
            or not _nonempty_text(record.get("note"))
        ):
            issues.append(f"human_review dimension is not a documented PASS: {name}")


def _validate_automatic_pass(
    checks: object,
    answer_key: dict[str, Any],
    issues: list[str],
) -> None:
    if not _exact_keys(checks, AUTOMATIC_CHECK_KEYS, "automatic checks", issues):
        return
    assert isinstance(checks, dict)
    for name, record in checks.items():
        if not isinstance(record, dict) or record.get("status") != "PASS":
            issues.append(f"automatic check is not PASS: {name}")

    integrity = checks["participant_integrity"]
    nested = integrity.get("checks") if isinstance(integrity, dict) else None
    if not isinstance(nested, list):
        issues.append("participant_integrity.checks must be an array")
    else:
        ids: set[str] = set()
        malformed_integrity = False
        for record in nested:
            if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                malformed_integrity = True
                continue
            ids.add(record["id"])
        if (
            malformed_integrity
            or ids != INTEGRITY_CHECK_IDS
            or len(nested) != len(INTEGRITY_CHECK_IDS)
        ):
            issues.append("participant integrity evidence is incomplete")
        _all_status_pass(nested, "participant_integrity.checks", issues)

    profile = checks["profile_routing"]
    if not isinstance(profile, dict):
        issues.append("profile_routing must be an object")
    else:
        if profile.get("expected") != answer_key["expected_profile"]:
            issues.append("profile_routing expected Profile does not match the answer key")
        brief_checks = profile.get("brief_checks")
        expected_brief_evidence = {
            "profile_id_in_brief": answer_key["expected_profile"]["primary_profile_id"],
            "customer_profile_name_in_brief": answer_key["expected_profile"]["customer_facing_name"],
            "definition_version_in_brief": answer_key["expected_profile"]["definition_version"],
        }
        if not isinstance(brief_checks, list) or len(brief_checks) != len(expected_brief_evidence):
            issues.append("profile_routing brief evidence is incomplete")
        else:
            actual_brief_evidence: dict[str, object] = {}
            for record in brief_checks:
                if (
                    not isinstance(record, dict)
                    or set(record) != {"id", "status", "evidence"}
                    or not isinstance(record.get("id"), str)
                    or record.get("status") != "PASS"
                ):
                    issues.append("profile_routing brief evidence record is malformed")
                    continue
                actual_brief_evidence[record["id"]] = record["evidence"]
            if actual_brief_evidence != expected_brief_evidence:
                issues.append("profile_routing brief evidence does not match the answer key")

    brief = checks["design_brief_binding"]
    if not isinstance(brief, dict):
        issues.append("design_brief_binding must be an object")
    else:
        for section in ("report_ir", "project_handoff"):
            record = brief.get(section)
            if not isinstance(record, dict) or record.get("issues") != []:
                issues.append(f"design brief {section} binding has unresolved issues")

    report_ir = checks["report_ir"]
    if not isinstance(report_ir, dict):
        issues.append("report_ir check must be an object")
    else:
        layers = report_ir.get("layers")
        if not isinstance(layers, dict) or set(layers) != IR_LAYER_KEYS or not all(
            layers.get(key) is True for key in IR_LAYER_KEYS
        ):
            issues.append("Report IR four-layer evidence is incomplete or false")
        if report_ir.get("qa_execution_claim") != "not_executed_by_validator":
            issues.append("Report IR validator QA execution boundary drifted")
        _validate_hard_assertions(
            report_ir.get("hard_assertions"),
            answer_key["hard_assertions"]["report_ir"],
            "report_ir",
            issues,
        )

    compiler = checks["compiler_manifest_html"]
    if not isinstance(compiler, dict):
        issues.append("compiler_manifest_html must be an object")
    else:
        if compiler.get("issues") != []:
            issues.append("compiler manifest reports unresolved issues")
        if compiler.get("compiler_qa_execution_claim") != "not_executed_by_compiler":
            issues.append("Compiler QA execution boundary drifted")
        _validate_hard_assertions(
            compiler.get("hard_assertions"),
            answer_key["hard_assertions"]["build_manifest"],
            "compiler",
            issues,
        )
        recompile = compiler.get("controller_recompile")
        if not isinstance(recompile, dict) or recompile.get("issues") != []:
            issues.append("controller recompile evidence is missing or failed")
        else:
            files = recompile.get("files")
            expected_files = {
                "index.html",
                "source-map.json",
                "report.ir.normalized.json",
                "build-manifest.json",
            }
            if not isinstance(files, dict) or set(files) != expected_files:
                issues.append("controller recompile file evidence is incomplete")
            elif any(
                not isinstance(record, dict)
                or set(record) != {"status", "returned_sha256", "recompiled_sha256"}
                or record.get("status") != "PASS"
                or not isinstance(record.get("returned_sha256"), str)
                or not SHA256.fullmatch(record["returned_sha256"])
                or record.get("returned_sha256") != record.get("recompiled_sha256")
                for record in files.values()
            ):
                issues.append("controller recompile contains a non-PASS file")

    handoff = checks["project_handoff"]
    if not isinstance(handoff, dict):
        issues.append("project_handoff check must be an object")
    else:
        readiness = handoff.get("readiness")
        if not isinstance(readiness, dict) or set(readiness) != READINESS_KEYS or not all(
            readiness.get(key) is True for key in READINESS_KEYS
        ):
            issues.append("Project Handoff four-layer readiness is incomplete or false")
        if handoff.get("qa_execution_claim") != "not_executed_by_validator":
            issues.append("Project Handoff QA execution boundary drifted")
        _validate_hard_assertions(
            handoff.get("hard_assertions"),
            answer_key["hard_assertions"]["project_handoff"],
            "handoff",
            issues,
        )

    qa = checks["qa_boundary"]
    if not isinstance(qa, dict):
        issues.append("qa_boundary must be an object")
    else:
        returned = qa.get("returned_record_validation")
        if (
            not isinstance(returned, dict)
            or returned.get("execution_claim") != "not_executed_by_validator"
        ):
            issues.append("returned QA record validation boundary is missing")
        else:
            records = returned.get("records")
            expected_types = {
                "asset_qa",
                "browser_qa",
                "runtime_editor_qa",
                "traceability",
                "delivery_verification",
            }
            actual_types: set[str] = set()
            malformed_record = False
            if isinstance(records, list):
                for record in records:
                    if not isinstance(record, dict) or not isinstance(
                        record.get("check_type"), str
                    ):
                        malformed_record = True
                        continue
                    actual_types.add(record["check_type"])
            if (
                not isinstance(records, list)
                or malformed_record
                or len(records) != len(expected_types)
                or actual_types != expected_types
            ):
                issues.append("returned QA records do not cover all delivery checks")
            elif any(
                record.get("status") != "passed"
                or not _nonempty_text(record.get("record_id"))
                or not _nonempty_text(record.get("record_artifact_ref"))
                for record in records
            ):
                issues.append("returned QA records contain an unpassed or unbound record")
        execution = qa.get("controller_execution")
        expected_execution = {
            "asset_qa",
            "browser_runtime_editor_qa",
            "traceability_verification",
            "delivery_integrity",
            "meaning",
        }
        if not isinstance(execution, dict) or set(execution) != expected_execution:
            issues.append("controller QA execution evidence is incomplete")
        else:
            for name in expected_execution - {"meaning"}:
                record = execution[name]
                if not isinstance(record, dict) or record.get("status") != "PASS":
                    issues.append(f"controller QA execution is not PASS: {name}")


def _validate_result_contract(
    result: object,
    receipt: object,
    answer_key: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not _exact_keys(result, RESULT_KEYS, "result", issues):
        return
    assert isinstance(result, dict)
    if result["result_contract_version"] != RESULT_CONTRACT_VERSION:
        issues.append("result_contract_version is unsupported")
    try:
        parse_utc(result["evaluated_at"], "result.evaluated_at")
    except ContractError as exc:
        issues.append(str(exc))
    if not _exact_keys(result["run"], RUN_KEYS, "result.run", issues):
        run: dict[str, Any] = {}
    else:
        run = result["run"]
        for field in ("run_id", "scenario_id"):
            if not isinstance(run.get(field), str) or not SAFE_ID.fullmatch(run[field]):
                issues.append(f"result.run.{field} is invalid")
        if not isinstance(run.get("nonce"), str) or not NONCE.fullmatch(run["nonce"]):
            issues.append("result.run.nonce is invalid")
        if run.get("target_platform") not in ("codex", "workbuddy"):
            issues.append("result.run.target_platform is invalid")
        if not _nonempty_text(run.get("source_commit")):
            issues.append("result.run.source_commit is invalid")
        if not isinstance(run.get("input_tree_sha256"), str) or not SHA256.fullmatch(
            run["input_tree_sha256"]
        ):
            issues.append("result.run.input_tree_sha256 is invalid")
        try:
            parse_utc(run.get("created_at"), "result.run.created_at")
        except ContractError as exc:
            issues.append(str(exc))
    if not _exact_keys(result["audit"], AUDIT_KEYS, "result.audit", issues):
        audit: dict[str, Any] = {}
    else:
        audit = result["audit"]
        if audit.get("used_for_automatic_pass") is not False:
            issues.append("audit metadata must not influence automatic PASS")
        if not isinstance(audit.get("validation_issues"), list):
            issues.append("audit.validation_issues must be an array")
        for field in ("platform", "agent", "model"):
            if not _nonempty_text(audit.get(field)):
                issues.append(f"audit.{field} must be recorded")
        _exact_keys(audit.get("tokens"), TOKEN_KEYS, "result.audit.tokens", issues)
        _exact_keys(audit.get("points"), POINT_KEYS, "result.audit.points", issues)
    if result["claims"] != CLAIMS:
        issues.append("result claims are incomplete or contradict the evaluator boundary")
    if result["automatic_status"] not in ("PASS", "FAIL"):
        issues.append("automatic_status is unsupported")
    human = result["human_review"]
    human_status = human.get("status") if isinstance(human, dict) else None
    if human_status not in ("PASS", "FAIL", "PENDING", "INVALID"):
        issues.append("human_review.status is unsupported")
    if result["overall_status"] not in ("PASS", "FAIL", "AWAITING_HUMAN"):
        issues.append("overall_status is unsupported")
    expected_overall = (
        "FAIL"
        if result["automatic_status"] == "FAIL"
        else (
            "PASS"
            if human_status == "PASS"
            else "FAIL"
            if human_status in ("FAIL", "INVALID")
            else "AWAITING_HUMAN"
        )
    )
    if result["overall_status"] != expected_overall:
        issues.append("automatic, human, and overall statuses contradict each other")
    if result["automatic_status"] == "PASS":
        if answer_key is None:
            issues.append("automatic PASS cannot be checked without the controller answer key")
        else:
            _validate_automatic_pass(result["checks"], answer_key, issues)
    elif not isinstance(result["checks"], dict) or not result["checks"]:
        issues.append("failed automatic result must still contain evaluator checks")
    if human_status == "PASS":
        if answer_key is None:
            issues.append("human PASS cannot be checked without the controller answer key")
        else:
            _validate_human_pass(human, answer_key, run.get("run_id"), issues)
    if result["overall_status"] == "PASS" and (
        result["automatic_status"] != "PASS" or human_status != "PASS"
    ):
        issues.append("overall PASS requires both automatic and human PASS")

    if not _exact_keys(receipt, RECEIPT_KEYS, "controller receipt", issues):
        return
    assert isinstance(receipt, dict)
    if receipt["receipt_version"] != RECEIPT_VERSION:
        issues.append("controller receipt version is unsupported")
    if not re.fullmatch(r"[a-f0-9]{64}", str(receipt["matrix_hmac_key"])):
        issues.append("controller receipt matrix HMAC key is invalid")
    if receipt["controller_answer_embedded"] is not False or receipt["expected_profile_embedded"] is not False:
        issues.append("controller receipt claims participant answer leakage")
    run_bindings = {
        "run_id": "run_id",
        "nonce": "nonce",
        "scenario_id": "scenario_id",
        "target_platform": "target_platform",
        "created_at": "created_at",
        "source_commit": "source_commit",
        "input_tree_sha256": "input_tree_sha256",
    }
    for result_field, receipt_field in run_bindings.items():
        if run.get(result_field) != receipt.get(receipt_field):
            issues.append(f"result.run.{result_field} does not match controller receipt")


def validate_result_artifact(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    issues: list[str] = []
    if path.is_symlink():
        return None, ["result path cannot be a symlink"]
    try:
        result = load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return None, [f"result JSON is invalid: {exc}"]
    receipt_path = path.with_name("receipt.json")
    if not receipt_path.is_file() or receipt_path.is_symlink():
        return result, ["authenticated result requires a non-symlink receipt.json beside it"]
    try:
        receipt = load_json(receipt_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return result, [f"controller receipt is invalid: {exc}"]

    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    scenario_id = run.get("scenario_id")
    answer_key: dict[str, Any] | None = None
    if isinstance(scenario_id, str):
        try:
            answer_key = load_answer_key(scenario_id)
        except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(f"controller answer key is unavailable: {exc}")
    else:
        issues.append("result scenario_id is missing")
    _validate_result_contract(result, receipt, answer_key, issues)

    provenance = result.get("provenance")
    if _exact_keys(provenance, RESULT_PROVENANCE_KEYS, "result.provenance", issues):
        assert isinstance(provenance, dict)
        if provenance["controller_receipt_sha256"] != sha256_file(receipt_path):
            issues.append("result does not bind the current controller receipt bytes")
        for result_field, receipt_field in (
            ("run_manifest_sha256", "run_manifest_sha256"),
            ("answer_key_sha256", "answer_key_sha256"),
            ("participant_zip_sha256", "participant_zip_sha256"),
            ("acceptance_toolchain_sha256", "acceptance_toolchain_sha256"),
        ):
            if provenance[result_field] != receipt.get(receipt_field):
                issues.append(f"result provenance {result_field} does not match receipt")
        returned = provenance["returned_artifact"]
        if (
            not isinstance(returned, dict)
            or set(returned) != {"kind", "sha256"}
            or returned.get("kind") not in ("zip", "directory_tree")
            or not isinstance(returned.get("sha256"), str)
            or not SHA256.fullmatch(returned["sha256"])
        ):
            issues.append("returned artifact provenance is invalid")
        current_toolchain = acceptance_toolchain_sha256()
        if receipt.get("acceptance_toolchain_sha256") != current_toolchain:
            issues.append("controller receipt acceptance toolchain has drifted")
        if provenance["acceptance_toolchain_sha256"] != current_toolchain:
            issues.append("result acceptance toolchain has drifted")
        if answer_key is not None:
            key_path = ANSWER_ROOT / f"{scenario_id}.json"
            if receipt.get("answer_key_sha256") != sha256_file(key_path):
                issues.append("controller answer key bytes drifted after acceptance")
        declared_hmac = provenance.get("result_hmac_sha256")
        if not isinstance(declared_hmac, str) or not SHA256.fullmatch(declared_hmac):
            issues.append("result HMAC is missing or invalid")
        else:
            try:
                expected_hmac = result_hmac_sha256(result, receipt["matrix_hmac_key"])
            except (KeyError, ContractError) as exc:
                issues.append(f"result HMAC cannot be verified: {exc}")
            else:
                if not hmac.compare_digest(declared_hmac, expected_hmac):
                    issues.append("result HMAC does not authenticate the acceptance payload")
    return result, issues


def evaluate(inputs: list[Path]) -> dict[str, Any]:
    matrix = load_json(CONTROLLER_ROOT / "matrix.json")
    expected_rows = {
        (scenario, platform)
        for scenario, platform in itertools.product(
            matrix["smoke"]["scenarios"], matrix["platforms"]
        )
    }
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    unexpected: list[dict[str, str]] = []
    duplicates: list[dict[str, str]] = []
    identity_conflicts: list[dict[str, str]] = []
    invalid_results: list[dict[str, Any]] = []
    seen_identities: dict[tuple[str, str], str] = {}
    for path in result_paths(inputs):
        result, issues = validate_result_artifact(path)
        if issues or result is None:
            invalid_results.append({"path": str(path), "issues": issues})
            continue
        run = result["run"]
        row = (run["scenario_id"], run["target_platform"])
        if row not in expected_rows:
            unexpected.append(
                {"scenario_id": row[0], "platform": row[1], "path": str(path)}
            )
            continue
        if row in rows:
            duplicates.append(
                {"scenario_id": row[0], "platform": row[1], "path": str(path)}
            )
            continue
        identity_values = {
            "run_id": run["run_id"],
            "nonce": run["nonce"],
            "participant_zip_sha256": result["provenance"]["participant_zip_sha256"],
        }
        conflicting = False
        for identity_kind, identity_value in identity_values.items():
            identity = (identity_kind, identity_value)
            if identity in seen_identities:
                identity_conflicts.append(
                    {
                        "identity": identity_kind,
                        "value": identity_value,
                        "first_path": seen_identities[identity],
                        "path": str(path),
                    }
                )
                conflicting = True
            else:
                seen_identities[identity] = str(path)
        if conflicting:
            continue
        rows[row] = result

    records: list[dict[str, Any]] = []
    for scenario, platform in sorted(expected_rows):
        result = rows.get((scenario, platform))
        if result is None:
            records.append(
                {
                    "scenario_id": scenario,
                    "platform": platform,
                    "status": "MISSING",
                    "automatic_status": None,
                    "human_status": None,
                    "overall_status": None,
                    "run_id": None,
                }
            )
            continue
        automatic = result["automatic_status"]
        human = result["human_review"]["status"]
        overall = result["overall_status"]
        passed = automatic == "PASS" and human == "PASS" and overall == "PASS"
        records.append(
            {
                "scenario_id": scenario,
                "platform": platform,
                "status": "PASS" if passed else "NOT_PASSED",
                "automatic_status": automatic,
                "human_status": human,
                "overall_status": overall,
                "run_id": result["run"]["run_id"],
            }
        )
    smoke_pass = (
        len(records) == matrix["smoke"]["expected_run_count"]
        and all(record["status"] == "PASS" for record in records)
        and not duplicates
        and not unexpected
        and not invalid_results
        and not identity_conflicts
    )
    return {
        "matrix_result_version": "taohtml-cross-agent-matrix-result-2",
        "evaluated_at": utc_now(),
        "smoke_status": "PASS" if smoke_pass else "NOT_PASSED",
        "smoke_rows": records,
        "duplicate_rows": duplicates,
        "identity_conflicts": identity_conflicts,
        "unexpected_rows": unexpected,
        "invalid_results": invalid_results,
        "full_matrix": {
            "enabled": smoke_pass,
            "reason": (
                "all six authenticated smoke results passed automatic and human acceptance"
                if smoke_pass
                else "full remains disabled until every authenticated smoke row passes"
            ),
            "expected_run_count": matrix["full"]["expected_run_count"],
            "profiles": matrix["full"]["profile_ids"],
            "platforms": matrix["platforms"],
            "scenario_fixtures_in_this_node": matrix["full"][
                "scenario_fixtures_in_this_node"
            ],
        },
        "workbuddy_results_synthesized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        print(f"MATRIX_FAILED output already exists: {args.output}", file=sys.stderr)
        return 1
    try:
        result = evaluate([path.resolve() for path in args.results])
        write_json(args.output.resolve(), result)
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"MATRIX_FAILED {exc}", file=sys.stderr)
        return 1
    print(
        f"MATRIX_RESULT smoke={result['smoke_status']} "
        f"full_enabled={str(result['full_matrix']['enabled']).lower()} "
        f"invalid_results={len(result['invalid_results'])}"
    )
    print(args.output.resolve())
    return 0 if result["full_matrix"]["enabled"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
