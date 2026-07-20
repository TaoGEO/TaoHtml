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
    resolve_regular_file,
    safe_extract_zip,
    safe_relative_path,
    sha256_file,
    tree_sha256,
    utc_now,
    write_json,
)
from profile_release_contract import (
    FORBIDDEN_DIRECT_ROUTE_OUTPUTS,
    PRODUCTION_ACTIONS,
    PRODUCTION_CHECK_RECORD_VERSION,
    RECEIPT_VERSION,
    REQUIRED_OUTPUTS,
    RESULT_CONTRACT_VERSION,
    RUN_CONTRACT_VERSION,
    answer_sha256,
    assert_controller_owned_path,
    overall_status,
    release_toolchain_sha256,
    result_hmac_sha256,
    scenario_by_id,
    validate_brief_decisions,
    validate_controller_trace,
    validate_external_review,
    validate_participant_evidence,
    validate_submission,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HANDOFF_VALIDATOR = (
    REPOSITORY_ROOT / "skill" / "taohtml" / "scripts" / "validate_project_handoff.py"
)
PRODUCTION_CHECKER = (
    REPOSITORY_ROOT
    / "skill"
    / "taohtml"
    / "scripts"
    / "check_production_authorization.py"
)
PRODUCTION_CHECKER_REF = "skill/taohtml/scripts/check_production_authorization.py"


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


def _run_production_checker(
    output_root: Path, state_path: Path, action: str
) -> tuple[int, dict[str, Any] | None, list[str]]:
    completed = subprocess.run(
        [
            sys.executable,
            str(PRODUCTION_CHECKER),
            "--state",
            str(state_path),
            "--artifact-root",
            str(output_root),
            "--action",
            action,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return completed.returncode, None, [
            f"Production Authorization checker did not return JSON for {action}"
        ]
    if not isinstance(result, dict):
        return completed.returncode, None, [
            f"Production Authorization checker returned a non-object for {action}"
        ]
    return completed.returncode, result, []


def _validate_current_production_state(
    output_root: Path, state_path: Path, brief_path: Path
) -> list[str]:
    issues: list[str] = []
    try:
        state = load_json(state_path)
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        return [f"current production-state is invalid: {exc}"]
    if state.get("schema_version") != "1.3":
        issues.append("current production-state must use schema version 1.3")
    brief_gate = state.get("design_brief")
    if not isinstance(brief_gate, dict):
        issues.append("current production-state design_brief gate is missing")
    else:
        if brief_gate.get("status") != "confirmed":
            issues.append("current production-state design brief is not confirmed")
        if brief_gate.get("artifact_path") != "design-brief.md":
            issues.append("current production-state does not bind design-brief.md")
        if brief_gate.get("artifact_sha256") != sha256_file(brief_path):
            issues.append("current production-state does not bind the current design brief")
        if not isinstance(brief_gate.get("design_decisions_sha256"), str):
            issues.append("current production-state lacks design_decisions_sha256")
    exit_code, result, checker_issues = _run_production_checker(
        output_root, state_path, "deliver-formal-html"
    )
    issues.extend(checker_issues)
    if (
        exit_code != 0
        or not result
        or result.get("requested_action")
        != {"name": "deliver-formal-html", "allowed": True}
    ):
        issues.append(
            "current production-state/checker does not authorize deliver-formal-html"
        )
    return issues


def _validate_production_check_records(
    production_checks_root: Path,
    *,
    receipt: dict[str, Any],
    output_root: Path,
    state_path: Path,
    brief_path: Path,
    html_path: Path,
    browser_review_path: Path | None,
) -> tuple[list[str], dict[str, Any]]:
    issues: list[str] = []
    current_state_sha = sha256_file(state_path)
    current_brief_sha = sha256_file(brief_path)
    current_html_sha = sha256_file(html_path)
    checker_sha = sha256_file(PRODUCTION_CHECKER)
    records: dict[str, Any] = {}
    expected_files = {f"{action}.json" for action in PRODUCTION_ACTIONS}
    actual_files = {
        path.name for path in production_checks_root.iterdir() if path.is_file()
    }
    if actual_files != expected_files:
        issues.append("controller production checks are missing or contain extras")
    for action in PRODUCTION_ACTIONS:
        try:
            path = resolve_regular_file(
                production_checks_root, f"{action}.json", "production check record"
            )
            record = load_json(path)
        except (ContractError, OSError, json.JSONDecodeError) as exc:
            issues.append(f"cannot read controller {action} record: {exc}")
            continue
        records[action] = record
        expected_keys = {
            "record_contract_version",
            "run_id",
            "scenario_id",
            "action",
            "checker_path",
            "checker_sha256",
            "production_state_path",
            "production_state_sha256",
            "design_brief_path",
            "design_brief_sha256",
            "html_observation",
            "browser_review_observation",
            "process_exit_code",
            "checker_result",
            "stderr",
        }
        if set(record) != expected_keys:
            issues.append(f"controller {action} record fields drifted")
        for key, expected in {
            "record_contract_version": PRODUCTION_CHECK_RECORD_VERSION,
            "run_id": receipt["run_id"],
            "scenario_id": receipt["scenario_id"],
            "action": action,
            "checker_path": PRODUCTION_CHECKER_REF,
            "checker_sha256": checker_sha,
            "production_state_path": "gates/production-state.json",
            "production_state_sha256": current_state_sha,
            "design_brief_path": "design-brief.md",
            "design_brief_sha256": current_brief_sha,
            "process_exit_code": 0,
        }.items():
            if record.get(key) != expected:
                issues.append(f"controller {action} record {key} mismatch")
        expected_html = {
            "path": "build/index.html",
            "state": "absent" if action == "formal-html" else "present",
            "sha256": None if action == "formal-html" else current_html_sha,
        }
        if record.get("html_observation") != expected_html:
            issues.append(f"controller {action} record HTML observation mismatch")
        if action == "deliver-formal-html":
            if browser_review_path is None:
                expected_browser_review = None
            else:
                expected_browser_review = {
                    "path": "browser-review.json",
                    "sha256": sha256_file(browser_review_path),
                    "html_sha256": current_html_sha,
                    "status": "PASS",
                }
            if record.get("browser_review_observation") != expected_browser_review:
                issues.append(
                    "controller deliver-formal-html record does not follow current browser QA"
                )
        elif record.get("browser_review_observation") is not None:
            issues.append(f"controller {action} record has a premature browser observation")
        exit_code, current_result, checker_issues = _run_production_checker(
            output_root, state_path, action
        )
        issues.extend(checker_issues)
        if exit_code != 0:
            issues.append(f"current checker rejects {action}")
        if record.get("checker_result") != current_result:
            issues.append(f"controller {action} record is not the current checker result")
        if not isinstance(current_result, dict) or current_result.get("requested_action") != {
            "name": action,
            "allowed": True,
        }:
            issues.append(f"controller {action} record does not prove an allowed action")
    return issues, records


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


def _load_optional_record(path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
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
    conversation_trace_path: Path | None,
    production_checks_root: Path | None,
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
        "case_id": receipt["case_id"],
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

    output_path = safe_relative_path(
        receipt["output_directory"], "receipt output_directory"
    )
    output_root = returned_root.joinpath(*output_path.parts)
    if not output_root.is_dir() or output_root.is_symlink():
        raise ContractError("unique Profile release output directory is missing")
    sibling_outputs = [path for path in output_root.parent.iterdir() if path.is_dir()]
    if sibling_outputs != [output_root]:
        static_issues.append("returned package contains multiple submission directories")
    paths, required_issues = _required_output_paths(output_root)
    static_issues.extend(required_issues)
    for forbidden in FORBIDDEN_DIRECT_ROUTE_OUTPUTS:
        if output_root.joinpath(*Path(forbidden).parts).exists():
            static_issues.append(
                f"Direct HTML release run contains forbidden or obsolete output: {forbidden}"
            )

    participant_claim = "unknown"
    handoff_result: dict[str, Any] | None = None
    brief_text = ""
    html_text = ""
    handoff_text = ""
    if not required_issues:
        submission = load_json(paths["submission.json"])
        participant_claim = submission.get("participant_claimed_status", "unknown")
        static_issues.extend(
            validate_submission(
                output_root,
                submission,
                run_id=receipt["run_id"],
                nonce=receipt["nonce"],
                case_id=receipt["case_id"],
            )
        )
        brief_text = paths["design-brief.md"].read_text(encoding="utf-8")
        html_text = paths["build/index.html"].read_text(encoding="utf-8")
        handoff_text = paths["handoff.md"].read_text(encoding="utf-8")
        static_issues.extend(validate_brief_decisions(brief_text, scenario))
        evidence = load_json(paths["profile-evidence.json"])
        static_issues.extend(
            validate_participant_evidence(
                evidence,
                scenario,
                run_id=receipt["run_id"],
                nonce=receipt["nonce"],
                case_id=receipt["case_id"],
                brief_sha256=sha256_file(paths["design-brief.md"]),
                handoff_sha256=sha256_file(paths["project-handoff.json"]),
            )
        )
        static_issues.extend(
            _validate_current_production_state(
                output_root,
                paths["gates/production-state.json"],
                paths["design-brief.md"],
            )
        )
        handoff_result, handoff_issues = _handoff_check(
            paths["project-handoff.json"], output_root
        )
        static_issues.extend(handoff_issues)
        static_issues.extend(
            _evidence_text_issues(
                scenario,
                brief_text=brief_text,
                html_text=html_text,
                handoff_text=handoff_text,
            )
        )

    html_sha256 = (
        sha256_file(paths["build/index.html"])
        if "build/index.html" in paths
        else "0" * 64
    )
    browser_review, browser_review_sha = _load_optional_record(browser_review_path)
    human_review, human_review_sha = _load_optional_record(human_review_path)
    browser_status, browser_issues, browser_record = validate_external_review(
        browser_review,
        kind="browser",
        scenario=scenario,
        run_id=receipt["run_id"],
        html_sha256=html_sha256,
        review_root=browser_review_path.parent if browser_review_path else None,
    )
    human_status, human_issues, human_record = validate_external_review(
        human_review,
        kind="human",
        scenario=scenario,
        run_id=receipt["run_id"],
        html_sha256=html_sha256,
    )

    flow_issues: list[str] = []
    flow_pending: list[str] = []
    trace: dict[str, Any] | None = None
    trace_sha: str | None = None
    if conversation_trace_path is None:
        flow_pending.append("controller/platform conversation trace is missing")
    elif "design-brief.md" not in paths:
        flow_issues.append("current design brief is unavailable for trace binding")
    else:
        trace, trace_sha = _load_optional_record(conversation_trace_path)
        flow_issues.extend(
            validate_controller_trace(
                trace,
                scenario,
                run_id=receipt["run_id"],
                brief_sha256=sha256_file(paths["design-brief.md"]),
            )
        )
    production_records: dict[str, Any] | None = None
    production_checks_sha: str | None = None
    if production_checks_root is None:
        flow_pending.append("controller Production Authorization checker records are missing")
    elif not all(
        key in paths
        for key in (
            "gates/production-state.json",
            "design-brief.md",
            "build/index.html",
        )
    ):
        flow_issues.append("current artifacts are unavailable for production-check binding")
    else:
        flow_issues_from_records, production_records = _validate_production_check_records(
            production_checks_root,
            receipt=receipt,
            output_root=output_root,
            state_path=paths["gates/production-state.json"],
            brief_path=paths["design-brief.md"],
            html_path=paths["build/index.html"],
            browser_review_path=browser_review_path,
        )
        flow_issues.extend(flow_issues_from_records)
        production_checks_sha = tree_sha256(file_hashes(production_checks_root))
    if browser_review is None:
        flow_pending.append("controller browser QA record is missing from the shared-gate trace")
    elif browser_status == "FAIL":
        flow_issues.append("controller browser QA gate failed")
    blackbox_status = (
        "FAIL" if flow_issues else "PENDING" if flow_pending else "PASS"
    )

    layers = {
        "contract_static": {
            "status": "FAIL" if static_issues else "PASS",
            "issues": static_issues,
            "handoff_validator": handoff_result,
        },
        "blackbox_flow": {
            "status": blackbox_status,
            "issues": [*flow_issues, *flow_pending],
            "controller_evidence": {
                "trace": trace,
                "production_checks": production_records,
            },
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
            "conversation_trace_sha256": trace_sha,
            "production_checks_sha256": production_checks_sha,
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
            "Missing controller trace, checker records, browser QA, or human review remains PENDING.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--returned", type=Path, required=True)
    parser.add_argument("--conversation-trace", type=Path)
    parser.add_argument("--production-checks", type=Path)
    parser.add_argument("--browser-review", type=Path)
    parser.add_argument("--human-review", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt_path = args.receipt.resolve()
        returned = args.returned.resolve()
        controller_root = receipt_path.parent
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
            assert_controller_owned_path(receipt_path, root, "controller receipt")
            assert_controller_owned_path(args.output, root, "controller result")
            if args.output.resolve().parent != controller_root:
                raise ContractError("controller result must be written beside receipt.json")
            optional_paths = (
                (args.conversation_trace, controller_root / "conversation-trace.json", "conversation trace"),
                (args.production_checks, controller_root / "production-checks", "production checks"),
                (args.browser_review, controller_root / "browser-review.json", "browser review"),
                (args.human_review, controller_root / "human-review.json", "human review"),
            )
            for supplied, expected, label in optional_paths:
                if supplied:
                    assert_controller_owned_path(supplied, root, label)
                    if supplied.resolve() != expected:
                        raise ContractError(f"{label} must use the controller-owned canonical path")
            result = evaluate_returned_root(
                receipt_path=receipt_path,
                returned_root=root,
                returned_kind=kind,
                returned_sha256=returned_sha,
                conversation_trace_path=(
                    args.conversation_trace.resolve() if args.conversation_trace else None
                ),
                production_checks_root=(
                    args.production_checks.resolve() if args.production_checks else None
                ),
                browser_review_path=(
                    args.browser_review.resolve() if args.browser_review else None
                ),
                human_review_path=(
                    args.human_review.resolve() if args.human_review else None
                ),
            )
        write_json(args.output, result)
        args.output.with_suffix(".md").write_text(render_markdown(result), encoding="utf-8")
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
