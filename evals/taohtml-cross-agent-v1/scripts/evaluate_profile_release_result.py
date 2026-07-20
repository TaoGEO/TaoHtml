#!/usr/bin/env python3
"""Evaluate one returned Workflow Profile release run in four strict layers."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from blackbox_contract import (
    ContractError,
    directory_tree_sha256,
    file_hashes,
    load_json,
    normalize_returned_root,
    parse_utc,
    resolve_regular_file,
    safe_relative_path,
    safe_extract_zip,
    sha256_file,
    tree_sha256,
    utc_now,
    write_json,
)
from profile_release_contract import (
    EVIDENCE_CONTRACT_VERSION,
    FORBIDDEN_DIRECT_ROUTE_OUTPUTS,
    RECEIPT_VERSION,
    REQUIRED_OUTPUTS,
    RESULT_CONTRACT_VERSION,
    RUN_CONTRACT_VERSION,
    answer_sha256,
    assert_controller_owned_path,
    evaluate_blackbox_flow,
    layer_status,
    overall_status,
    release_toolchain_sha256,
    result_hmac_sha256,
    scenario_by_id,
    validate_external_review,
    validate_submission,
)


HANDOFF_VALIDATOR = (
    Path(__file__).resolve().parents[3]
    / "skill"
    / "taohtml"
    / "scripts"
    / "validate_project_handoff.py"
)


def _required_output_paths(output_root: Path) -> tuple[dict[str, Path], list[str]]:
    paths: dict[str, Path] = {}
    issues: list[str] = []
    for relative in REQUIRED_OUTPUTS:
        try:
            paths[relative] = resolve_regular_file(
                output_root, relative, f"required output {relative}"
            )
        except ContractError as exc:
            issues.append(str(exc))
    return paths, issues


def _validate_evidence_identity(
    evidence: dict[str, Any],
    *,
    receipt: dict[str, Any],
    paths: dict[str, Path],
) -> list[str]:
    issues: list[str] = []
    required_keys = {
        "evidence_contract_version",
        "run_id",
        "nonce",
        "scenario_id",
        "routing",
        "questions",
        "known_choices_reused",
        "design_brief",
        "production_authorization",
        "evidence_boundaries",
        "production",
    }
    if set(evidence) != required_keys:
        return ["profile-evidence fields drifted"]
    expected_identity = {
        "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
        "run_id": receipt["run_id"],
        "nonce": receipt["nonce"],
        "scenario_id": receipt["scenario_id"],
    }
    for key, expected in expected_identity.items():
        if evidence.get(key) != expected:
            issues.append(f"profile-evidence {key} mismatch")

    brief = evidence.get("design_brief")
    if not isinstance(brief, dict):
        issues.append("design_brief evidence must be an object")
    else:
        if brief.get("path") != "design-brief.md":
            issues.append("design brief path mismatch")
        if paths.get("design-brief.md") and brief.get("sha256") != sha256_file(paths["design-brief.md"]):
            issues.append("design brief hash mismatch")
        try:
            parse_utc(brief.get("confirmed_at"), "design brief confirmed_at")
        except ContractError as exc:
            issues.append(str(exc))

    authorization = evidence.get("production_authorization")
    if not isinstance(authorization, dict):
        issues.append("production_authorization evidence must be an object")
    else:
        if authorization.get("path") != "production-authorization.json":
            issues.append("Production Authorization path mismatch")
        if paths.get("production-authorization.json") and authorization.get("sha256") != sha256_file(paths["production-authorization.json"]):
            issues.append("Production Authorization hash mismatch")
        if authorization.get("target_html_path") != "build/index.html":
            issues.append("Production Authorization target HTML path mismatch")
        if paths.get("build/index.html") and authorization.get("target_html_sha256") != sha256_file(paths["build/index.html"]):
            issues.append("Production Authorization target HTML hash mismatch")
        try:
            parse_utc(authorization.get("authorized_at"), "Production Authorization authorized_at")
        except ContractError as exc:
            issues.append(str(exc))

    production = evidence.get("production")
    if not isinstance(production, dict):
        issues.append("production evidence must be an object")
    else:
        if production.get("handoff_path") != "project-handoff.json":
            issues.append("Handoff path mismatch")
        if paths.get("project-handoff.json") and production.get("handoff_sha256") != sha256_file(paths["project-handoff.json"]):
            issues.append("Handoff hash mismatch")
    return issues


def _validate_authorization(
    authorization: dict[str, Any],
    *,
    brief_sha256: str,
    html_sha256: str,
) -> list[str]:
    issues: list[str] = []
    if authorization.get("record_type") != "production_authorization":
        issues.append("Production Authorization record_type mismatch")
    if authorization.get("status") != "authorized":
        issues.append("Production Authorization is not authorized")
    if authorization.get("design_brief_sha256") != brief_sha256:
        issues.append("Production Authorization is not bound to the current brief")
    if authorization.get("target_artifact_sha256") != html_sha256:
        issues.append("Production Authorization is not bound to the current HTML")
    actions = authorization.get("authorized_actions")
    if not isinstance(actions, list) or not {
        "formal-html",
        "browser-qa",
        "deliver-formal-html",
    }.issubset(actions):
        issues.append("Production Authorization actions are incomplete")
    return issues


def _handoff_check(
    handoff_path: Path, output_root: Path
) -> tuple[dict[str, Any] | None, list[str]]:
    completed = subprocess.run(
        [
            sys.executable,
            str(HANDOFF_VALIDATOR),
            "--handoff",
            str(handoff_path),
            "--artifact-root",
            str(output_root),
            "--require",
            "delivery_ready",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None, ["Project Handoff validator did not return JSON"]
    issues: list[str] = []
    readiness = result.get("readiness")
    if not isinstance(readiness, dict) or not all(
        readiness.get(key) is True
        for key in (
            "schema_valid",
            "bindings_valid",
            "continuation_ready",
            "delivery_ready",
        )
    ):
        issues.append("Project Handoff four-layer readiness is incomplete or false")
    if result.get("qa_execution_claim") != "not_executed_by_validator":
        issues.append("Project Handoff validator QA execution boundary drifted")
    try:
        handoff = load_json(handoff_path)
        if handoff.get("schema_version") != "1.1":
            issues.append("Direct HTML release Handoff must use schema version 1.1")
        if handoff.get("current_build", "missing") is not None:
            issues.append(
                "Direct HTML release Handoff must keep current_build null instead of "
                "manufacturing a Report IR/Compiler binding"
            )
    except ContractError as exc:
        issues.append(str(exc))
    if completed.returncode != 0 and not issues:
        issues.append("Project Handoff validator returned a non-zero status")
    return result, issues


def _evidence_text_issues(
    scenario: dict[str, Any], *, brief_text: str, html_text: str, handoff_text: str
) -> list[str]:
    issues: list[str] = []
    combined = "\n".join((brief_text, html_text, handoff_text))
    for expectation in scenario["evidence_expectations"]:
        for term in expectation["required_terms"]:
            if term not in combined:
                issues.append(f"required evidence-boundary wording is missing: {term}")
        for term in expectation["forbidden_terms"]:
            if term in combined:
                issues.append(f"forbidden overclaim is present: {term}")
    return issues


def _load_optional_review(path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if path is None:
        return None, None
    resolved = path.resolve()
    return load_json(resolved), sha256_file(resolved)


def evaluate_returned_root(
    *,
    receipt_path: Path,
    returned_root: Path,
    returned_kind: str,
    returned_sha256: str,
    browser_review_path: Path | None,
    human_review_path: Path | None,
) -> dict[str, Any]:
    receipt = load_json(receipt_path)
    if receipt.get("receipt_version") != RECEIPT_VERSION:
        raise ContractError("Profile release receipt version mismatch")
    scenario = scenario_by_id(receipt.get("scenario_id", ""))
    static_issues: list[str] = []
    if receipt.get("controller_answer_sha256") != answer_sha256(scenario):
        static_issues.append("controller answer key changed after run preparation")
    if receipt.get("release_toolchain_sha256") != release_toolchain_sha256():
        static_issues.append("release acceptance toolchain changed after run preparation")

    run_path = resolve_regular_file(returned_root, "run.json", "returned run manifest")
    run = load_json(run_path)
    expected_run_fields = {
        "run_contract_version": RUN_CONTRACT_VERSION,
        "run_id": receipt["run_id"],
        "nonce": receipt["nonce"],
        "scenario_id": receipt["scenario_id"],
        "runner_label": receipt["runner_label"],
        "created_at": receipt["created_at"],
        "output_directory": receipt["output_directory"],
        "required_outputs": receipt["required_outputs"],
        "input_tree_sha256": receipt["input_tree_sha256"],
    }
    for key, expected in expected_run_fields.items():
        if run.get(key) != expected:
            static_issues.append(f"returned run manifest {key} mismatch")
    if sha256_file(run_path) != receipt["run_manifest_sha256"]:
        static_issues.append("returned run manifest hash mismatch")
    try:
        current_inputs = file_hashes(returned_root, receipt["input_files"].keys())
        if current_inputs != receipt["input_files"]:
            static_issues.append("participant input files changed")
        if tree_sha256(current_inputs) != receipt["input_tree_sha256"]:
            static_issues.append("participant input tree hash mismatch")
    except ContractError as exc:
        static_issues.append(str(exc))

    output_relative = receipt["output_directory"]
    output_path = safe_relative_path(output_relative, "receipt output_directory")
    output_root = returned_root.joinpath(*output_path.parts)
    if not output_root.is_dir() or output_root.is_symlink():
        raise ContractError("unique Profile release output directory is missing")
    submission_parent = output_root.parent
    sibling_outputs = [path for path in submission_parent.iterdir() if path.is_dir()]
    if sibling_outputs != [output_root]:
        static_issues.append("returned package contains multiple submission directories")
    paths, required_issues = _required_output_paths(output_root)
    static_issues.extend(required_issues)
    for forbidden in FORBIDDEN_DIRECT_ROUTE_OUTPUTS:
        if output_root.joinpath(*Path(forbidden).parts).exists():
            static_issues.append(f"Direct HTML release run contains forbidden pilot output: {forbidden}")

    evidence: dict[str, Any] = {}
    brief_text = ""
    html_text = ""
    handoff_text = ""
    handoff_result: dict[str, Any] | None = None
    participant_claim = "unknown"
    if not required_issues:
        submission = load_json(paths["submission.json"])
        participant_claim = submission.get("participant_claimed_status", "unknown")
        static_issues.extend(
            validate_submission(
                output_root,
                submission,
                run_id=receipt["run_id"],
                nonce=receipt["nonce"],
                scenario_id=receipt["scenario_id"],
            )
        )
        evidence = load_json(paths["profile-evidence.json"])
        static_issues.extend(
            _validate_evidence_identity(evidence, receipt=receipt, paths=paths)
        )
        brief_sha = sha256_file(paths["design-brief.md"])
        html_sha = sha256_file(paths["build/index.html"])
        authorization = load_json(paths["production-authorization.json"])
        static_issues.extend(
            _validate_authorization(
                authorization, brief_sha256=brief_sha, html_sha256=html_sha
            )
        )
        handoff_result, handoff_issues = _handoff_check(
            paths["project-handoff.json"], output_root
        )
        static_issues.extend(handoff_issues)
        brief_text = paths["design-brief.md"].read_text(encoding="utf-8")
        html_text = paths["build/index.html"].read_text(encoding="utf-8")
        handoff_text = paths["handoff.md"].read_text(encoding="utf-8")
        static_issues.extend(
            _evidence_text_issues(
                scenario,
                brief_text=brief_text,
                html_text=html_text,
                handoff_text=handoff_text,
            )
        )

    flow_issues = (
        evaluate_blackbox_flow(evidence, scenario, brief_text=brief_text)
        if evidence
        else ["profile-evidence.json is unavailable"]
    )
    html_sha256 = (
        sha256_file(paths["build/index.html"])
        if "build/index.html" in paths
        else "0" * 64
    )
    browser_review, browser_review_sha = _load_optional_review(browser_review_path)
    human_review, human_review_sha = _load_optional_review(human_review_path)
    browser_status, browser_issues, browser_record = validate_external_review(
        browser_review,
        kind="browser",
        scenario=scenario,
        run_id=receipt["run_id"],
        html_sha256=html_sha256,
    )
    human_status, human_issues, human_record = validate_external_review(
        human_review,
        kind="human",
        scenario=scenario,
        run_id=receipt["run_id"],
        html_sha256=html_sha256,
    )
    layers = {
        "contract_static": {
            "status": layer_status(static_issues),
            "issues": static_issues,
            "handoff_validator": handoff_result,
        },
        "blackbox_flow": {
            "status": layer_status(flow_issues),
            "issues": flow_issues,
        },
        "html_browser_qa": {
            "status": browser_status,
            "issues": browser_issues,
            "review": browser_record,
        },
        "human_visual_review": {
            "status": human_status,
            "issues": human_issues,
            "review": human_record,
        },
    }
    result = {
        "result_contract_version": RESULT_CONTRACT_VERSION,
        "evaluated_at": utc_now(),
        "run": {
            "run_id": receipt["run_id"],
            "nonce": receipt["nonce"],
            "scenario_id": receipt["scenario_id"],
            "runner_label": receipt["runner_label"],
            "source_commit": receipt["source_commit"],
            "primary_profile_id": scenario["primary_profile"]["profile_id"],
            "html_sha256": html_sha256,
        },
        "layers": layers,
        "overall_status": overall_status(layers),
        "claims": {
            "participant_claimed_status": participant_claim,
            "participant_status_used_for_pass": False,
            "contract_or_flow_pass_implies_browser_pass": False,
            "automatic_pass_implies_human_pass": False,
            "report_ir_or_compiler_formally_available": False,
        },
        "provenance": {
            "controller_receipt_sha256": sha256_file(receipt_path),
            "controller_answer_sha256": receipt["controller_answer_sha256"],
            "participant_zip_sha256": receipt["participant_zip_sha256"],
            "returned_artifact": {
                "kind": returned_kind,
                "sha256": returned_sha256,
            },
            "release_toolchain_sha256": receipt["release_toolchain_sha256"],
            "browser_review_sha256": browser_review_sha,
            "human_review_sha256": human_review_sha,
            "result_hmac_sha256": "",
        },
    }
    result["provenance"]["result_hmac_sha256"] = result_hmac_sha256(
        result, receipt["result_hmac_key"]
    )
    return result


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Workflow Profile release acceptance result",
        "",
        f"- Scenario: `{result['run']['scenario_id']}`",
        f"- Primary Profile: `{result['run']['primary_profile_id']}`",
        f"- Overall: **{result['overall_status']}**",
        "",
        "| Layer | Status |",
        "|---|---|",
    ]
    for name, layer in result["layers"].items():
        lines.append(f"| `{name}` | {layer['status']} |")
    lines.extend(
        [
            "",
            "Contract/static, black-box flow, and browser PASS never imply human visual PASS.",
            "A missing browser or human result keeps the row PENDING; any failed layer makes it FAIL.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--returned", type=Path, required=True)
    parser.add_argument("--browser-review", type=Path)
    parser.add_argument("--human-review", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt_path = args.receipt.resolve()
        returned = args.returned.resolve()
        if args.output.exists():
            raise ContractError(f"result output already exists: {args.output}")
        with tempfile.TemporaryDirectory(prefix="taohtml-profile-release-") as raw:
            if returned.is_file():
                root = safe_extract_zip(returned, Path(raw) / "returned")
                kind = "zip"
                returned_sha = sha256_file(returned)
            elif returned.is_dir():
                root = normalize_returned_root(returned)
                kind = "directory_tree"
                returned_sha = directory_tree_sha256(root)
            else:
                raise ContractError("returned artifact must be a ZIP or directory")
            assert_controller_owned_path(
                receipt_path, root, "controller receipt"
            )
            assert_controller_owned_path(
                args.output, root, "controller result"
            )
            if args.output.resolve().parent != receipt_path.parent:
                raise ContractError(
                    "controller result must be written beside its receipt.json"
                )
            if args.browser_review:
                assert_controller_owned_path(
                    args.browser_review, root, "browser review"
                )
            if args.human_review:
                assert_controller_owned_path(
                    args.human_review, root, "human review"
                )
            result = evaluate_returned_root(
                receipt_path=receipt_path,
                returned_root=root,
                returned_kind=kind,
                returned_sha256=returned_sha,
                browser_review_path=args.browser_review,
                human_review_path=args.human_review,
            )
        write_json(args.output, result)
        args.output.with_suffix(".md").write_text(
            render_markdown(result), encoding="utf-8"
        )
    except (ContractError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"PROFILE_RELEASE_EVALUATION_FAILED {exc}", file=sys.stderr)
        return 2
    print(
        f"PROFILE_RELEASE_RESULT {result['overall_status']} "
        f"scenario={result['run']['scenario_id']} output={args.output}"
    )
    return 0 if result["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
