#!/usr/bin/env python3
"""Evaluate the authenticated nine-row Workflow Profile release matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from blackbox_contract import ContractError, load_json, sha256_file, utc_now, write_json
from profile_release_contract import (
    MATRIX_RESULT_CONTRACT_VERSION,
    PROFILE_IDS,
    RECEIPT_VERSION,
    RESULT_CONTRACT_VERSION,
    answer_sha256,
    load_release_matrix,
    overall_status,
    release_toolchain_sha256,
    result_hmac_sha256,
    scenario_by_id,
)


LAYER_NAMES = (
    "contract_static",
    "blackbox_flow",
    "html_browser_qa",
    "human_visual_review",
)


def _verify_result(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    issues: list[str] = []
    try:
        result = load_json(path)
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        return None, [f"cannot read result {path}: {exc}"]
    if result.get("result_contract_version") != RESULT_CONTRACT_VERSION:
        issues.append(f"result contract version mismatch: {path}")
    run = result.get("run")
    if not isinstance(run, dict):
        return result, [*issues, f"result run is missing: {path}"]
    for field in (
        "run_id",
        "nonce",
        "scenario_id",
        "runner_label",
        "source_commit",
        "primary_profile_id",
        "html_sha256",
    ):
        if not isinstance(run.get(field), str) or not run[field]:
            issues.append(f"result run {field} is invalid: {path}")
    try:
        scenario = scenario_by_id(run.get("scenario_id", ""))
    except ContractError as exc:
        return result, [*issues, str(exc)]
    if run.get("primary_profile_id") != scenario["primary_profile"]["profile_id"]:
        issues.append(f"result primary Profile mismatch: {path}")
    layers = result.get("layers")
    if not isinstance(layers, dict) or set(layers) != set(LAYER_NAMES):
        issues.append(f"result four-layer evidence is incomplete: {path}")
    elif any(
        not isinstance(layers[name], dict)
        or layers[name].get("status") not in {"PASS", "FAIL", "PENDING"}
        for name in LAYER_NAMES
    ):
        issues.append(f"result contains an invalid layer: {path}")
    else:
        derived_status = overall_status(layers)
        if result.get("overall_status") != derived_status:
            issues.append(
                f"result overall status contradicts its four layers: {path}"
            )
    claims = result.get("claims")
    if not isinstance(claims, dict) or claims.get("participant_status_used_for_pass") is not False:
        issues.append(f"participant PASS boundary is missing: {path}")
    if isinstance(claims, dict) and (
        claims.get("contract_or_flow_pass_implies_browser_pass") is not False
        or claims.get("automatic_pass_implies_human_pass") is not False
        or claims.get("report_ir_or_compiler_formally_available") is not False
    ):
        issues.append(f"release capability/layer claim is overstated: {path}")

    receipt_path = path.parent / "receipt.json"
    try:
        receipt = load_json(receipt_path)
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        return result, [*issues, f"receipt is missing for {path}: {exc}"]
    if receipt.get("receipt_version") != RECEIPT_VERSION:
        issues.append(f"receipt version mismatch: {receipt_path}")
    if (
        receipt.get("run_id") != run.get("run_id")
        or receipt.get("nonce") != run.get("nonce")
        or receipt.get("scenario_id") != run.get("scenario_id")
    ):
        issues.append(f"result/receipt identity mismatch: {path}")
    if receipt.get("controller_answer_sha256") != answer_sha256(scenario):
        issues.append(f"controller answer drifted: {path}")
    if receipt.get("release_toolchain_sha256") != release_toolchain_sha256():
        issues.append(f"release toolchain drifted: {path}")
    provenance = result.get("provenance")
    if not isinstance(provenance, dict):
        issues.append(f"result provenance is missing: {path}")
    else:
        if provenance.get("controller_receipt_sha256") != sha256_file(receipt_path):
            issues.append(f"result is not bound to its receipt: {path}")
        try:
            expected_hmac = result_hmac_sha256(
                result, receipt.get("result_hmac_key", "")
            )
        except ContractError as exc:
            issues.append(f"result HMAC cannot be verified: {path}: {exc}")
        else:
            if provenance.get("result_hmac_sha256") != expected_hmac:
                issues.append(f"result HMAC is invalid: {path}")
    return result, issues


def evaluate_matrix(result_paths: list[Path]) -> dict[str, Any]:
    matrix = load_release_matrix()
    issues: list[str] = []
    rows: list[dict[str, Any]] = []
    if len(result_paths) != matrix["expected_run_count"]:
        issues.append(
            f"expected exactly {matrix['expected_run_count']} results; received {len(result_paths)}"
        )
    seen_scenarios: set[str] = set()
    seen_profiles: set[str] = set()
    seen_runs: set[str] = set()
    seen_nonces: set[str] = set()
    invalid = False
    for path in result_paths:
        result, result_issues = _verify_result(path.resolve())
        issues.extend(result_issues)
        invalid = invalid or bool(result_issues)
        if result is None or not isinstance(result.get("run"), dict):
            continue
        run = result["run"]
        scenario_id = run.get("scenario_id")
        profile_id = run.get("primary_profile_id")
        run_id = run.get("run_id")
        nonce = run.get("nonce")
        for value, seen, label in (
            (scenario_id, seen_scenarios, "scenario"),
            (profile_id, seen_profiles, "Profile"),
            (run_id, seen_runs, "run"),
            (nonce, seen_nonces, "nonce"),
        ):
            if not isinstance(value, str):
                issues.append(f"invalid {label} identity type: {type(value).__name__}")
                invalid = True
                continue
            if value in seen:
                issues.append(f"duplicate {label} identity: {value}")
                invalid = True
            seen.add(value)
        rows.append(
            {
                "scenario_id": scenario_id,
                "primary_profile_id": profile_id,
                "run_id": run_id,
                "overall_status": result.get("overall_status"),
                "layers": {
                    name: result.get("layers", {}).get(name, {}).get("status", "INVALID")
                    for name in LAYER_NAMES
                },
                "result_sha256": sha256_file(path.resolve()),
            }
        )

    expected_scenarios = {item["scenario_id"] for item in matrix["scenarios"]}
    if seen_scenarios != expected_scenarios:
        issues.append("scenario coverage is not exactly the declared nine")
    if seen_profiles != set(PROFILE_IDS):
        issues.append("primary Profile coverage is not exactly the declared nine")
    row_statuses = [row["overall_status"] for row in rows]
    if invalid:
        status = "FAIL"
    elif len(rows) != 9 or any(item == "PENDING" for item in row_statuses):
        status = "PENDING"
    elif any(item != "PASS" for item in row_statuses):
        status = "FAIL"
    else:
        status = "PASS"
    return {
        "matrix_result_contract_version": MATRIX_RESULT_CONTRACT_VERSION,
        "evaluated_at": utc_now(),
        "release_target": matrix["release_target"],
        "status": status,
        "expected_run_count": 9,
        "received_run_count": len(rows),
        "rows": sorted(rows, key=lambda item: str(item["scenario_id"])),
        "issues": issues,
        "claims": {
            "all_profiles_executed": seen_profiles == set(PROFILE_IDS) and len(rows) == 9,
            "all_contract_static_passed": len(rows) == 9 and all(row["layers"]["contract_static"] == "PASS" for row in rows),
            "all_blackbox_flows_passed": len(rows) == 9 and all(row["layers"]["blackbox_flow"] == "PASS" for row in rows),
            "all_browser_qa_passed": len(rows) == 9 and all(row["layers"]["html_browser_qa"] == "PASS" for row in rows),
            "all_human_visual_reviews_passed": len(rows) == 9 and all(row["layers"]["human_visual_review"] == "PASS" for row in rows),
            "report_ir_or_compiler_formally_available": False,
        },
        "release_toolchain_sha256": release_toolchain_sha256(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, nargs="*")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ContractError(f"matrix output already exists: {args.output}")
        result = evaluate_matrix(args.results)
        write_json(args.output, result)
    except (ContractError, OSError, ValueError) as exc:
        print(f"PROFILE_RELEASE_MATRIX_FAILED {exc}", file=sys.stderr)
        return 2
    print(f"PROFILE_RELEASE_MATRIX {result['status']} output={args.output}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
