#!/usr/bin/env python3
"""Fail-closed primitives for the nine-Profile release acceptance matrix."""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any, Iterable

from blackbox_contract import (
    ContractError,
    canonical_json_bytes,
    file_hashes,
    load_json,
    parse_utc,
    resolve_regular_file,
    safe_identifier,
    safe_relative_path,
    sha256_file,
    tree_sha256,
)


EVAL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = EVAL_ROOT.parents[1]
PARTICIPANT_ROOT = EVAL_ROOT / "participant" / "profile-release-scenarios"
CONTROLLER_ROOT = EVAL_ROOT / "controller"
MATRIX_PATH = CONTROLLER_ROOT / "profile-release-matrix.json"
RESULT_SCHEMA_PATH = EVAL_ROOT / "schemas" / "profile-release-result.schema.json"

RUN_CONTRACT_VERSION = "taohtml-profile-release-run-1"
RECEIPT_VERSION = "taohtml-profile-release-receipt-1"
SUBMISSION_CONTRACT_VERSION = "taohtml-profile-release-submission-1"
EVIDENCE_CONTRACT_VERSION = "taohtml-profile-release-evidence-1"
RESULT_CONTRACT_VERSION = "taohtml-profile-release-result-1"
MATRIX_RESULT_CONTRACT_VERSION = "taohtml-profile-release-matrix-result-1"

PROFILE_IDS = (
    "formal-submission-writing",
    "research-analysis-argumentation",
    "periodic-operations-reporting",
    "proposal-planning-decision",
    "live-presentation-persuasion",
    "teaching-training-knowledge-transfer",
    "project-lifecycle-reporting",
    "brand-communication-editorial-publishing",
    "rule-response-application-defense",
)

PROFILE_NAMES = (
    "规范报送与正式写作",
    "研究分析与专业论证",
    "周期经营与数据汇报",
    "方案策划与决策提案",
    "现场演讲与说服表达",
    "教学培训与知识传递",
    "项目全过程汇报",
    "品牌传播与编辑出版",
    "规则响应、申报与答辩",
)

KNOWN_CHOICE_KEYS = {
    "input_entry_route",
    "use_mode",
    "content_length",
    "visual_binding",
    "motion_density",
}
SHARED_GATE_SEQUENCE = (
    "profile_routing",
    "design_brief_confirmation",
    "production_authorization",
    "direct_html",
    "runtime_qa",
    "browser_qa",
    "handoff",
)
REQUIRED_OUTPUTS = (
    "design-brief.md",
    "production-authorization.json",
    "build/index.html",
    "project-handoff.json",
    "handoff.md",
    "profile-evidence.json",
    "submission.json",
)
FORBIDDEN_DIRECT_ROUTE_OUTPUTS = {
    "report-ir.json",
    "build/build-manifest.json",
    "build/source-map.json",
    "build/report.ir.normalized.json",
}
TOOLCHAIN_FILES = (
    "PROFILE_RELEASE_ACCEPTANCE.md",
    "controller/profile-release-matrix.json",
    "schemas/profile-release-result.schema.json",
    "scripts/evaluate_profile_release_matrix.py",
    "scripts/evaluate_profile_release_result.py",
    "scripts/prepare_profile_release_run.py",
    "scripts/profile_release_contract.py",
    "scripts/run_profile_release_browser_qa.py",
)
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _require_exact_keys(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise ContractError(f"{label} fields drifted: {actual}")
    return value


def load_release_matrix() -> dict[str, Any]:
    matrix = load_json(MATRIX_PATH)
    _require_exact_keys(
        matrix,
        {
            "matrix_contract_version",
            "release_target",
            "status",
            "expected_run_count",
            "layers",
            "pass_policy",
            "compiler_report_ir_boundary",
            "scenarios",
        },
        "release matrix",
    )
    if matrix["matrix_contract_version"] != "taohtml-profile-release-matrix-1":
        raise ContractError("release matrix contract version drifted")
    if matrix["release_target"] != "v0.5.0-candidate":
        raise ContractError("release target drifted")
    if matrix["status"] != "DEFINED_PENDING_REAL_RUNS":
        raise ContractError("release matrix must remain pending until real runs exist")
    if matrix["expected_run_count"] != 9:
        raise ContractError("release matrix must require exactly nine runs")
    if matrix["layers"] != [
        "contract_static",
        "blackbox_flow",
        "html_browser_qa",
        "human_visual_review",
    ]:
        raise ContractError("release acceptance layers drifted")

    scenarios = matrix["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) != 9:
        raise ContractError("release matrix must contain exactly nine scenarios")
    scenario_ids: list[str] = []
    profile_ids: list[str] = []
    request_refs: list[str] = []
    for scenario in scenarios:
        _validate_scenario(scenario)
        scenario_ids.append(scenario["scenario_id"])
        profile_ids.append(scenario["primary_profile"]["profile_id"])
        request_refs.append(scenario["request_ref"])
    if len(set(scenario_ids)) != 9:
        raise ContractError("release scenario ids must be unique")
    if len(set(request_refs)) != 9:
        raise ContractError("release request fixtures must be unique")
    if tuple(profile_ids) != PROFILE_IDS:
        raise ContractError("release matrix must cover each stable Profile exactly once")
    if sum(item["routing"]["mode"] == "ambiguous" for item in scenarios) != 1:
        raise ContractError("release matrix must contain exactly one genuine ambiguity case")
    return matrix


def _validate_scenario(scenario: object) -> None:
    value = _require_exact_keys(
        scenario,
        {
            "scenario_id",
            "request_ref",
            "primary_profile",
            "routing",
            "audit",
            "known_choices",
            "required_brief_decisions",
            "evidence_expectations",
            "human_review_dimensions",
            "leakage_markers",
        },
        "release scenario",
    )
    safe_identifier(value["scenario_id"], "scenario_id")
    safe_relative_path(value["request_ref"], "request_ref")
    profile = _require_exact_keys(
        value["primary_profile"],
        {"profile_id", "customer_facing_name", "definition_version"},
        "primary profile",
    )
    if profile["profile_id"] not in PROFILE_IDS or profile["definition_version"] != "2.0":
        raise ContractError("scenario primary Profile identity is invalid")
    expected_name = PROFILE_NAMES[PROFILE_IDS.index(profile["profile_id"])]
    if profile["customer_facing_name"] != expected_name:
        raise ContractError("scenario customer-facing Profile name drifted")
    routing = _require_exact_keys(
        value["routing"],
        {"mode", "selection_basis", "expected_user_answer"},
        "routing",
    )
    if routing["mode"] not in {"clear", "ambiguous"}:
        raise ContractError("routing mode must be clear or ambiguous")
    if routing["mode"] == "clear" and routing["expected_user_answer"] is not None:
        raise ContractError("clear routing cannot carry a controller answer")
    if routing["mode"] == "ambiguous" and not routing["expected_user_answer"]:
        raise ContractError("ambiguous routing requires a controller-held user answer")
    _require_exact_keys(
        value["audit"],
        {
            "customer_goal",
            "critical_judgment",
            "design_ready_increment",
            "evidence_boundary",
            "delivery_status",
            "qa_focus",
        },
        "scenario audit",
    )
    if any(
        not value["audit"].get(field)
        for field in (
            "customer_goal",
            "critical_judgment",
            "design_ready_increment",
            "evidence_boundary",
            "delivery_status",
            "qa_focus",
        )
    ):
        raise ContractError("scenario audit contains an empty dimension")
    if set(value["known_choices"]) != KNOWN_CHOICE_KEYS:
        raise ContractError("known-choice coverage drifted")
    if any(not isinstance(item, str) or not item for item in value["known_choices"].values()):
        raise ContractError("known choices must be non-empty strings")
    for field in (
        "required_brief_decisions",
        "evidence_expectations",
        "human_review_dimensions",
        "leakage_markers",
    ):
        if not isinstance(value[field], list) or not value[field]:
            raise ContractError(f"{field} must be a non-empty array")
    if len(set(value["required_brief_decisions"])) != len(value["required_brief_decisions"]):
        raise ContractError("required brief decisions must be unique")
    if len(set(value["human_review_dimensions"])) != len(value["human_review_dimensions"]):
        raise ContractError("human review dimensions must be unique")
    for expectation in value["evidence_expectations"]:
        _require_exact_keys(
            expectation,
            {"boundary_id", "required_status", "required_terms", "forbidden_terms"},
            "evidence expectation",
        )
        if not expectation["boundary_id"] or not expectation["required_status"]:
            raise ContractError("evidence expectation identity/status is empty")
        if not isinstance(expectation["required_terms"], list) or not expectation["required_terms"]:
            raise ContractError("evidence expectation requires public boundary wording")
        if not isinstance(expectation["forbidden_terms"], list) or not expectation["forbidden_terms"]:
            raise ContractError("evidence expectation requires forbidden overclaim wording")


def scenario_by_id(scenario_id: str) -> dict[str, Any]:
    if not isinstance(scenario_id, str):
        raise ContractError("scenario_id must be a string")
    safe_identifier(scenario_id, "scenario_id")
    for scenario in load_release_matrix()["scenarios"]:
        if scenario["scenario_id"] == scenario_id:
            return scenario
    raise ContractError(f"unknown Profile release scenario: {scenario_id}")


def scenario_request_path(scenario: dict[str, Any]) -> Path:
    return resolve_regular_file(EVAL_ROOT, scenario["request_ref"], "scenario request")


def release_toolchain_hashes() -> dict[str, str]:
    return {
        relative: sha256_file(
            resolve_regular_file(EVAL_ROOT, relative, "release toolchain file")
        )
        for relative in TOOLCHAIN_FILES
    }


def release_toolchain_sha256() -> str:
    return tree_sha256(release_toolchain_hashes())


def answer_sha256(scenario: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(scenario)).hexdigest()


def answer_leakage_markers(scenario: dict[str, Any]) -> set[str]:
    profile = scenario["primary_profile"]
    markers = {
        profile["profile_id"],
        profile["customer_facing_name"],
        *scenario["leakage_markers"],
        *scenario["required_brief_decisions"],
    }
    return {marker.casefold() for marker in markers if marker}


def assert_answer_free_package(root: Path, scenario: dict[str, Any]) -> None:
    markers = answer_leakage_markers(scenario)
    forbidden_components = {"controller", "answer", "answer-key", "rubric", "score"}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ContractError(f"participant package cannot contain symlinks: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(Path(component).stem.casefold() in forbidden_components for component in relative.parts):
            raise ContractError(f"controller-only filename leaked into package: {relative}")
        text = path.read_bytes().decode("utf-8", errors="ignore").casefold()
        leaked = sorted(marker for marker in markers if marker in text)
        if leaked:
            raise ContractError(
                f"controller answer marker leaked into participant file {relative}: {leaked}"
            )


def assert_controller_owned_path(path: Path, participant_root: Path, label: str) -> None:
    candidate = path.resolve()
    root = participant_root.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return
    raise ContractError(f"{label} must remain outside the participant package")


def validate_submission(
    output_root: Path,
    submission: dict[str, Any],
    *,
    run_id: str,
    nonce: str,
    scenario_id: str,
) -> list[str]:
    issues: list[str] = []
    expected_keys = {
        "submission_contract_version",
        "run_id",
        "nonce",
        "scenario_id",
        "participant_claimed_status",
        "artifacts",
    }
    if not isinstance(submission, dict) or set(submission) != expected_keys:
        return ["submission fields drifted"]
    expected_identity = {
        "submission_contract_version": SUBMISSION_CONTRACT_VERSION,
        "run_id": run_id,
        "nonce": nonce,
        "scenario_id": scenario_id,
    }
    for key, expected in expected_identity.items():
        if submission.get(key) != expected:
            issues.append(f"submission {key} mismatch")
    if submission.get("participant_claimed_status") not in {"PASS", "FAIL", "PENDING"}:
        issues.append("participant_claimed_status is invalid")
    artifacts = submission.get("artifacts")
    if not isinstance(artifacts, dict):
        issues.append("submission artifacts must be an object")
        return issues
    actual_paths = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file() and path.name != "submission.json"
    }
    if set(artifacts) != actual_paths:
        issues.append("submission artifact inventory is incomplete or contains extras")
        return issues
    for relative, expected_hash in artifacts.items():
        try:
            path = resolve_regular_file(output_root, relative, "submission artifact")
        except ContractError as exc:
            issues.append(str(exc))
            continue
        if not isinstance(expected_hash, str) or not SHA256.fullmatch(expected_hash):
            issues.append(f"submission artifact hash is invalid: {relative}")
        elif sha256_file(path) != expected_hash:
            issues.append(f"submission artifact hash mismatch: {relative}")
    return issues


def evaluate_blackbox_flow(
    evidence: dict[str, Any],
    scenario: dict[str, Any],
    *,
    brief_text: str,
) -> list[str]:
    issues: list[str] = []
    routing = evidence.get("routing")
    if not isinstance(routing, dict):
        return ["routing evidence must be an object"]
    expected_profile = scenario["primary_profile"]
    for key in ("profile_id", "customer_facing_name", "definition_version"):
        if routing.get(key) != expected_profile[key]:
            issues.append(f"primary Profile {key} mismatch")
    if routing.get("mode") != scenario["routing"]["mode"]:
        issues.append("routing mode mismatch")
    if not isinstance(routing.get("selection_basis"), str) or not routing["selection_basis"].strip():
        issues.append("semantic selection basis is missing")

    questions = evidence.get("questions")
    if not isinstance(questions, list):
        issues.append("questions must be an array")
        questions = []
    question_topics: list[str] = []
    for question in questions:
        if not isinstance(question, dict) or set(question) != {"topic", "text"}:
            issues.append("question evidence fields drifted")
            continue
        topic = question.get("topic")
        if not isinstance(topic, str) or not isinstance(question.get("text"), str):
            issues.append("question topic/text is invalid")
            continue
        question_topics.append(topic)
    repeated = sorted(KNOWN_CHOICE_KEYS.intersection(question_topics))
    if repeated:
        issues.append(f"known choices were asked again: {repeated}")
    if len(question_topics) != len(set(question_topics)):
        issues.append("a question topic was repeated")

    catalog = routing.get("catalog_shown")
    user_answer = routing.get("user_answer")
    if scenario["routing"]["mode"] == "clear":
        if catalog not in (None, []):
            issues.append("clear routing displayed the Profile catalog")
        if "business_goal" in question_topics:
            issues.append("clear routing asked an unnecessary business-goal question")
        if user_answer is not None:
            issues.append("clear routing fabricated an ambiguity answer")
    else:
        if catalog != list(PROFILE_NAMES):
            issues.append("ambiguous routing did not display the complete nine-name catalog")
        if question_topics.count("business_goal") != 1:
            issues.append("ambiguous routing must ask exactly one business-goal question")
        if user_answer != scenario["routing"]["expected_user_answer"]:
            issues.append("ambiguous routing answer does not match the controller-held reply")

    if evidence.get("known_choices_reused") != scenario["known_choices"]:
        issues.append("known entrance/mode/length/visual/motion choices were not reused exactly")

    brief = evidence.get("design_brief")
    if not isinstance(brief, dict):
        issues.append("design brief evidence must be an object")
    else:
        decisions = brief.get("scenario_decisions")
        if decisions != scenario["required_brief_decisions"]:
            issues.append("scenario-specific decisions are incomplete, reordered, or duplicated")
        if "## 场景特有决策" not in brief_text:
            issues.append("the one Report Design Brief lacks 场景特有决策")
        for label in scenario["required_brief_decisions"]:
            if label not in brief_text:
                issues.append(f"Report Design Brief is missing scenario decision: {label}")
        expected_profile = scenario["primary_profile"]
        for value, label in (
            (expected_profile["profile_id"], "stable Profile id"),
            (expected_profile["customer_facing_name"], "customer-facing Profile name"),
            (expected_profile["definition_version"], "Profile definition version"),
        ):
            if value not in brief_text:
                issues.append(f"Report Design Brief is missing {label}")

    authorization = evidence.get("production_authorization")
    if not isinstance(authorization, dict) or not isinstance(brief, dict):
        issues.append("brief/Production Authorization separation cannot be verified")
    else:
        brief_ref = brief.get("confirmation_ref")
        auth_ref = authorization.get("authorization_ref")
        if not brief_ref or not auth_ref or brief_ref == auth_ref:
            issues.append("brief confirmation and Production Authorization are not independent")
        try:
            brief_time = parse_utc(brief.get("confirmed_at"), "brief confirmed_at")
            authorization_time = parse_utc(
                authorization.get("authorized_at"), "Production Authorization authorized_at"
            )
            if brief_time >= authorization_time:
                issues.append("Production Authorization does not follow brief confirmation")
        except ContractError as exc:
            issues.append(str(exc))

    boundaries = evidence.get("evidence_boundaries")
    if not isinstance(boundaries, list):
        issues.append("evidence boundaries must be an array")
    else:
        if any(
            not isinstance(item, dict) or set(item) != {"boundary_id", "status"}
            for item in boundaries
        ):
            issues.append("evidence boundary fields drifted")
        boundary_ids = [
            item.get("boundary_id") for item in boundaries if isinstance(item, dict)
        ]
        if len(boundary_ids) != len(set(boundary_ids)):
            issues.append("an evidence boundary was duplicated")
        actual = {
            item.get("boundary_id"): item.get("status")
            for item in boundaries
            if isinstance(item, dict)
        }
        expected = {
            item["boundary_id"]: item["required_status"]
            for item in scenario["evidence_expectations"]
        }
        if actual != expected:
            issues.append("Profile evidence boundary status is incomplete or overstated")

    production = evidence.get("production")
    if not isinstance(production, dict):
        issues.append("production evidence must be an object")
    else:
        if production.get("route") != "direct_html":
            issues.append("release scenario bypassed the Direct HTML default")
        if production.get("runtime_contract") != "taohtml-runtime-1":
            issues.append("release scenario did not preserve the current Runtime contract")
        if production.get("gate_sequence") != list(SHARED_GATE_SEQUENCE):
            issues.append("shared Profile/brief/authorization/Runtime/browser/Handoff gates were bypassed")
    return issues


def layer_status(issues: Iterable[str]) -> str:
    return "FAIL" if list(issues) else "PASS"


def overall_status(layers: dict[str, dict[str, Any]]) -> str:
    statuses = [layers[name]["status"] for name in (
        "contract_static",
        "blackbox_flow",
        "html_browser_qa",
        "human_visual_review",
    )]
    if "FAIL" in statuses:
        return "FAIL"
    if "PENDING" in statuses:
        return "PENDING"
    return "PASS"


def validate_external_review(
    review: dict[str, Any] | None,
    *,
    kind: str,
    scenario: dict[str, Any],
    run_id: str,
    html_sha256: str,
) -> tuple[str, list[str], dict[str, Any] | None]:
    if review is None:
        return "PENDING", [f"{kind} result is missing"], None
    issues: list[str] = []
    expected_contract = (
        "taohtml-profile-release-browser-review-1"
        if kind == "browser"
        else "taohtml-profile-release-human-review-1"
    )
    if review.get("review_contract_version") != expected_contract:
        issues.append(f"{kind} review contract version mismatch")
    if review.get("scenario_id") != scenario["scenario_id"]:
        issues.append(f"{kind} review scenario mismatch")
    if review.get("run_id") != run_id:
        issues.append(f"{kind} review run mismatch")
    if review.get("html_sha256") != html_sha256:
        issues.append(f"{kind} review is not bound to the current HTML")
    if review.get("status") not in {"PASS", "FAIL"}:
        issues.append(f"{kind} review status must be PASS or FAIL")
    if kind == "browser":
        if review.get("tool") != "taohtml-check-html-deck":
            issues.append("browser review tool identity mismatch")
        if review.get("process_exit_code") != 0:
            issues.append("browser QA process did not exit successfully")
        if review.get("qa_stdout_marker") != "HTML_DECK_QA_OK":
            issues.append("browser QA success marker is missing")
        try:
            parse_utc(review.get("executed_at"), "browser review executed_at")
        except ContractError as exc:
            issues.append(str(exc))
        report_sha = review.get("qa_report_sha256")
        screenshots = review.get("screenshots_sha256")
        if not isinstance(report_sha, str) or not SHA256.fullmatch(report_sha):
            issues.append("browser review QA report hash is invalid")
        if (
            not isinstance(screenshots, dict)
            or not screenshots
            or any(
                not isinstance(path, str)
                or not path
                or not isinstance(digest, str)
                or not SHA256.fullmatch(digest)
                for path, digest in screenshots.items()
            )
        ):
            issues.append("browser review lacks QA report or screenshot hashes")
    else:
        if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
            issues.append("human reviewer identity is missing")
        try:
            parse_utc(review.get("reviewed_at"), "human review reviewed_at")
        except ContractError as exc:
            issues.append(str(exc))
        dimensions = review.get("dimensions")
        expected_dimensions = scenario["human_review_dimensions"]
        if not isinstance(dimensions, dict) or set(dimensions) != set(expected_dimensions):
            issues.append("human review dimensions are incomplete or contain extras")
        elif any(
            not isinstance(dimensions[name], dict)
            or dimensions[name].get("status") != "PASS"
            or not dimensions[name].get("note")
            for name in expected_dimensions
        ):
            issues.append("human review has a non-PASS or unreasoned dimension")
    if issues or review.get("status") == "FAIL":
        if review.get("status") == "FAIL" and not issues:
            issues.append(f"{kind} reviewer reported FAIL")
        return "FAIL", issues, review
    return "PASS", [], review


def result_hmac_payload(result: dict[str, Any]) -> bytes:
    authenticated = copy.deepcopy(result)
    provenance = authenticated.get("provenance")
    if not isinstance(provenance, dict):
        raise ContractError("result provenance must be an object")
    provenance.pop("result_hmac_sha256", None)
    return canonical_json_bytes(authenticated)


def result_hmac_sha256(result: dict[str, Any], hexadecimal_key: str) -> str:
    if not isinstance(hexadecimal_key, str) or not re.fullmatch(r"[a-f0-9]{64}", hexadecimal_key):
        raise ContractError("controller result HMAC key is invalid")
    return hmac.new(
        bytes.fromhex(hexadecimal_key), result_hmac_payload(result), hashlib.sha256
    ).hexdigest()


def output_tree_sha256(output_root: Path) -> str:
    return tree_sha256(file_hashes(output_root))
