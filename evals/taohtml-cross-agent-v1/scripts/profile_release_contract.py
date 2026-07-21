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
    png_dimensions,
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

RUN_CONTRACT_VERSION = "taohtml-profile-release-run-2"
RECEIPT_VERSION = "taohtml-profile-release-receipt-2"
SUBMISSION_CONTRACT_VERSION = "taohtml-profile-release-submission-1"
EVIDENCE_CONTRACT_VERSION = "taohtml-profile-release-evidence-2"
TRACE_CONTRACT_VERSION = "taohtml-profile-release-controller-trace-1"
PRODUCTION_CHECK_RECORD_VERSION = "taohtml-profile-release-production-check-1"
BROWSER_REVIEW_CONTRACT_VERSION = "taohtml-profile-release-browser-review-2"
RESULT_CONTRACT_VERSION = "taohtml-profile-release-result-2"
MATRIX_RESULT_CONTRACT_VERSION = "taohtml-profile-release-matrix-result-2"

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
TRACE_TIMELINE = (
    "profile_routing",
    "design_brief_confirmation",
    "production_authorization_formal-html",
    "direct_html",
    "runtime_qa",
    "production_authorization_browser-qa",
    "browser_qa",
    "production_authorization_deliver-formal-html",
    "handoff",
)
PRODUCTION_ACTIONS = ("formal-html", "browser-qa", "deliver-formal-html")
REQUIRED_VIEWPORTS = ((1366, 768), (1600, 900), (1920, 1080))
REQUIRED_OUTPUTS = (
    "design-brief.md",
    "gates/production-state.json",
    "build/index.html",
    "project-handoff.json",
    "handoff.md",
    "profile-evidence.json",
    "submission.json",
)
FORBIDDEN_DIRECT_ROUTE_OUTPUTS = {
    "production-authorization.json",
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
    "scripts/record_profile_release_production_check.py",
    "scripts/run_profile_release_browser_qa.py",
)
SHA256 = re.compile(r"^[a-f0-9]{64}$")
PLACEHOLDERS = {
    "已记录",
    "见正文",
    "见上文",
    "同上",
    "待补充",
    "待定",
    "无",
    "不适用",
    "n/a",
    "na",
}


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
    if matrix["matrix_contract_version"] != "taohtml-profile-release-matrix-2":
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
    if len(set(scenario_ids)) != 9 or len(set(request_refs)) != 9:
        raise ContractError("release scenario ids and request fixtures must be unique")
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
            "brief_content_checks",
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
    if profile["customer_facing_name"] != PROFILE_NAMES[PROFILE_IDS.index(profile["profile_id"])]:
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
    audit = _require_exact_keys(
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
    if any(not audit.get(field) for field in audit):
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
    content_checks = value["brief_content_checks"]
    if not isinstance(content_checks, list) or not content_checks:
        raise ContractError("brief content checks must be a non-empty array")
    check_labels: list[str] = []
    check_signatures: list[tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = []
    for content_check in content_checks:
        check = _require_exact_keys(
            content_check,
            {"label", "decision_any_of", "fact_any_of", "status_any_of"},
            "brief content check",
        )
        if not isinstance(check["label"], str) or not check["label"]:
            raise ContractError("brief content check label must be a non-empty string")
        check_labels.append(check["label"])
        for field in ("decision_any_of", "fact_any_of", "status_any_of"):
            terms = check[field]
            if (
                not isinstance(terms, list)
                or not terms
                or any(not isinstance(term, str) or not term for term in terms)
                or len(terms) != len(set(terms))
            ):
                raise ContractError(
                    f"brief content check {check['label']}/{field} must contain unique non-empty terms"
                )
        check_signatures.append(
            (
                tuple(check["decision_any_of"]),
                tuple(check["fact_any_of"]),
                tuple(check["status_any_of"]),
            )
        )
    if check_labels != value["required_brief_decisions"]:
        raise ContractError(
            "brief content checks must bind every required brief decision once and in order"
        )
    if len(check_signatures) != len(set(check_signatures)):
        raise ContractError("brief content checks cannot reuse one rule set across decisions")
    for expectation in value["evidence_expectations"]:
        _require_exact_keys(
            expectation,
            {"boundary_id", "required_status", "required_terms", "forbidden_terms"},
            "evidence expectation",
        )
        if not expectation["boundary_id"] or not expectation["required_status"]:
            raise ContractError("evidence expectation identity/status is empty")
        if not expectation["required_terms"] or not expectation["forbidden_terms"]:
            raise ContractError("evidence expectation wording is incomplete")


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
        relative: sha256_file(resolve_regular_file(EVAL_ROOT, relative, "release toolchain file"))
        for relative in TOOLCHAIN_FILES
    }


def release_toolchain_sha256() -> str:
    return tree_sha256(release_toolchain_hashes())


def answer_sha256(scenario: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(scenario)).hexdigest()


def answer_leakage_markers(scenario: dict[str, Any]) -> set[str]:
    profile = scenario["primary_profile"]
    routing = scenario["routing"]
    audit = scenario["audit"]
    markers: set[str] = {
        scenario["scenario_id"],
        profile["profile_id"],
        profile["customer_facing_name"],
        routing["selection_basis"],
        *scenario["leakage_markers"],
        *scenario["required_brief_decisions"],
        audit["critical_judgment"],
        audit["evidence_boundary"],
        audit["delivery_status"],
        *audit["design_ready_increment"],
        *audit["qa_focus"],
    }
    if routing["expected_user_answer"]:
        markers.add(routing["expected_user_answer"])
    for expectation in scenario["evidence_expectations"]:
        markers.add(expectation["required_status"])
        markers.update(expectation["required_terms"])
        markers.update(expectation["forbidden_terms"])
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
        if any(Path(part).stem.casefold() in forbidden_components for part in relative.parts):
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
    case_id: str,
) -> list[str]:
    issues: list[str] = []
    expected_keys = {
        "submission_contract_version",
        "run_id",
        "nonce",
        "case_id",
        "participant_claimed_status",
        "artifacts",
    }
    if not isinstance(submission, dict) or set(submission) != expected_keys:
        return ["submission fields drifted"]
    expected_identity = {
        "submission_contract_version": SUBMISSION_CONTRACT_VERSION,
        "run_id": run_id,
        "nonce": nonce,
        "case_id": case_id,
    }
    for key, expected in expected_identity.items():
        if submission.get(key) != expected:
            issues.append(f"submission {key} mismatch")
    if submission.get("participant_claimed_status") not in {"PASS", "FAIL", "PENDING"}:
        issues.append("participant_claimed_status is invalid")
    artifacts = submission.get("artifacts")
    if not isinstance(artifacts, dict):
        return [*issues, "submission artifacts must be an object"]
    actual_paths = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file() and path.name != "submission.json"
    }
    if set(artifacts) != actual_paths:
        return [*issues, "submission artifact inventory is incomplete or contains extras"]
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


def _meaningful(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().strip("。；;：:").casefold()
    return len(normalized) >= 6 and normalized not in PLACEHOLDERS


def parse_brief_decisions(brief_text: str) -> dict[str, dict[str, str]]:
    decisions: dict[str, dict[str, str]] = {}
    section_match = re.search(
        r"^##\s+场景特有决策\s*$([\s\S]*?)(?=^##\s+|\Z)",
        brief_text,
        flags=re.MULTILINE,
    )
    if not section_match:
        return decisions
    section = section_match.group(1)
    blocks = list(re.finditer(r"^###\s+(.+?)\s*$", section, flags=re.MULTILINE))
    for index, match in enumerate(blocks):
        label = match.group(1).strip().strip("`")
        end = blocks[index + 1].start() if index + 1 < len(blocks) else len(section)
        body = section[match.end():end]
        fields: dict[str, str] = {}
        for field in ("实际决策", "事实依据", "状态边界"):
            found = re.search(
                rf"^-\s*{field}\s*[：:]\s*(.+?)\s*$",
                body,
                flags=re.MULTILINE,
            )
            if found:
                fields[field] = found.group(1).strip()
        decisions[label] = fields
    return decisions


def validate_brief_decisions(brief_text: str, scenario: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    decisions = parse_brief_decisions(brief_text)
    expected_labels = scenario["required_brief_decisions"]
    if list(decisions) != expected_labels:
        issues.append("scenario-specific brief decisions are missing, reordered, or duplicated")
    checks_by_label = {
        item["label"]: item for item in scenario["brief_content_checks"]
    }
    field_rules = (
        ("实际决策", "decision_any_of", "a decision semantic"),
        ("事实依据", "fact_any_of", "its related scenario fact"),
        ("状态边界", "status_any_of", "its related status boundary"),
    )
    for label in expected_labels:
        fields = decisions.get(label, {})
        check = checks_by_label[label]
        for field in ("实际决策", "事实依据", "状态边界"):
            if not _meaningful(fields.get(field)):
                issues.append(f"Report Design Brief {label}/{field} is empty or placeholder-only")
        for field, rule, description in field_rules:
            text = fields.get(field, "")
            if text and not any(term in text for term in check[rule]):
                issues.append(
                    f"Report Design Brief {label}/{field} is not linked to {description}"
                )
    for field in ("实际决策", "事实依据", "状态边界"):
        contents = [decisions.get(label, {}).get(field, "") for label in expected_labels]
        if len(contents) > 1 and all(contents) and len(set(contents)) == 1:
            issues.append(
                f"Report Design Brief reuses identical {field} content across every decision"
            )
    profile = scenario["primary_profile"]
    for value, label in (
        (profile["profile_id"], "stable Profile id"),
        (profile["customer_facing_name"], "customer-facing Profile name"),
        (profile["definition_version"], "Profile definition version"),
    ):
        if value not in brief_text:
            issues.append(f"Report Design Brief is missing {label}")
    return issues


def validate_participant_evidence(
    evidence: dict[str, Any],
    scenario: dict[str, Any],
    *,
    run_id: str,
    nonce: str,
    case_id: str,
    brief_sha256: str,
    handoff_sha256: str,
) -> list[str]:
    issues: list[str] = []
    expected_keys = {
        "evidence_contract_version",
        "run_id",
        "nonce",
        "case_id",
        "selected_profile",
        "selection_basis",
        "design_brief",
        "evidence_boundaries",
        "production",
    }
    if not isinstance(evidence, dict) or set(evidence) != expected_keys:
        return ["profile-evidence fields drifted"]
    for key, expected in {
        "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
        "run_id": run_id,
        "nonce": nonce,
        "case_id": case_id,
    }.items():
        if evidence.get(key) != expected:
            issues.append(f"profile-evidence {key} mismatch")
    if evidence.get("selected_profile") != scenario["primary_profile"]:
        issues.append("participant-reported primary Profile mismatch")
    if not _meaningful(evidence.get("selection_basis")):
        issues.append("participant selection basis is missing")
    brief = evidence.get("design_brief")
    if not isinstance(brief, dict) or set(brief) != {"path", "sha256"}:
        issues.append("participant design brief evidence fields drifted")
    elif brief != {"path": "design-brief.md", "sha256": brief_sha256}:
        issues.append("participant design brief evidence is not current")
    boundaries = evidence.get("evidence_boundaries")
    expected_boundaries = [
        {"boundary_id": item["boundary_id"], "status": item["required_status"]}
        for item in scenario["evidence_expectations"]
    ]
    if boundaries != expected_boundaries:
        issues.append("participant evidence boundary status is incomplete or overstated")
    production = evidence.get("production")
    expected_production = {
        "route": "direct_html",
        "runtime_contract": "taohtml-runtime-1",
        "handoff_path": "project-handoff.json",
        "handoff_sha256": handoff_sha256,
    }
    if production != expected_production:
        issues.append("participant production evidence does not match Direct HTML/Runtime/Handoff")
    return issues


def _trace_turn_map(trace: dict[str, Any], issues: list[str]) -> tuple[dict[str, dict[str, str]], dict[str, int]]:
    turns = trace.get("turns")
    if not isinstance(turns, list) or not turns:
        issues.append("controller trace turns are missing")
        return {}, {}
    result: dict[str, dict[str, str]] = {}
    indexes: dict[str, int] = {}
    for index, turn in enumerate(turns):
        if not isinstance(turn, dict) or set(turn) != {"turn_id", "role", "text"}:
            issues.append("controller trace turn fields drifted")
            continue
        turn_id = turn.get("turn_id")
        if not isinstance(turn_id, str) or not turn_id or turn_id in result:
            issues.append("controller trace turn ids are empty or duplicated")
            continue
        if turn.get("role") not in {"user", "assistant"} or not _meaningful(turn.get("text")):
            issues.append(f"controller trace turn is not auditable: {turn_id}")
        result[turn_id] = turn
        indexes[turn_id] = index
    return result, indexes


def validate_controller_trace(
    trace: dict[str, Any],
    scenario: dict[str, Any],
    *,
    run_id: str,
    brief_sha256: str,
) -> list[str]:
    issues: list[str] = []
    expected_keys = {
        "trace_contract_version",
        "run_id",
        "scenario_id",
        "source",
        "turns",
        "observations",
        "timeline",
    }
    if not isinstance(trace, dict) or set(trace) != expected_keys:
        return ["controller trace fields drifted"]
    if trace.get("trace_contract_version") != TRACE_CONTRACT_VERSION:
        issues.append("controller trace contract version mismatch")
    if trace.get("run_id") != run_id or trace.get("scenario_id") != scenario["scenario_id"]:
        issues.append("controller trace run/scenario mismatch")
    source = trace.get("source")
    if (
        not isinstance(source, dict)
        or set(source) != {"kind", "locator"}
        or source.get("kind") not in {"platform_turn_export", "controller_captured_trace"}
        or not _meaningful(source.get("locator"))
    ):
        issues.append("controller trace source is not auditable")
    turns, indexes = _trace_turn_map(trace, issues)
    observations = trace.get("observations")
    if not isinstance(observations, dict) or set(observations) != {
        "routing", "questions", "known_choices_reused", "design_brief_confirmation"
    }:
        return [*issues, "controller trace observations fields drifted"]
    routing = observations.get("routing")
    routing_keys = {
        "mode",
        "profile_id",
        "customer_facing_name",
        "definition_version",
        "selection_basis",
        "selection_turn_id",
        "catalog_turn_id",
        "user_answer_turn_id",
    }
    if not isinstance(routing, dict) or set(routing) != routing_keys:
        issues.append("controller routing observation fields drifted")
        routing = {}
    profile = scenario["primary_profile"]
    for key in ("profile_id", "customer_facing_name", "definition_version"):
        if routing.get(key) != profile[key]:
            issues.append(f"controller-observed primary Profile {key} mismatch")
    if routing.get("mode") != scenario["routing"]["mode"]:
        issues.append("controller-observed routing mode mismatch")
    if not _meaningful(routing.get("selection_basis")):
        issues.append("controller-observed semantic selection basis is missing")
    selection_turn = turns.get(routing.get("selection_turn_id"))
    if (
        not selection_turn
        or selection_turn.get("role") != "assistant"
        or profile["customer_facing_name"] not in selection_turn.get("text", "")
    ):
        issues.append("selected Profile is not present in the referenced assistant turn")

    questions = observations.get("questions")
    if not isinstance(questions, list):
        issues.append("controller-observed questions must be an array")
        questions = []
    topics: list[str] = []
    observed_question_turn_ids: list[object] = []
    for question in questions:
        if not isinstance(question, dict) or set(question) != {"turn_id", "topic"}:
            issues.append("controller-observed question fields drifted")
            continue
        observed_question_turn_ids.append(question.get("turn_id"))
        turn = turns.get(question.get("turn_id"))
        if (
            not turn
            or turn.get("role") != "assistant"
            or not any(mark in turn.get("text", "") for mark in ("?", "？"))
        ):
            issues.append("controller-observed question does not reference an actual assistant question")
        topics.append(question.get("topic"))
    actual_question_turn_ids = [
        turn_id
        for turn_id, turn in turns.items()
        if turn.get("role") == "assistant"
        and any(mark in turn.get("text", "") for mark in ("?", "？"))
    ]
    if observed_question_turn_ids != actual_question_turn_ids:
        issues.append(
            "controller-observed questions must reference every actual assistant question exactly once and in turn order"
        )
    repeated = sorted(KNOWN_CHOICE_KEYS.intersection(item for item in topics if isinstance(item, str)))
    if repeated:
        issues.append(f"known choices were asked again: {repeated}")
    if len(topics) != len(set(topics)):
        issues.append("a controller-observed question topic was repeated")
    if scenario["routing"]["mode"] == "clear":
        if questions:
            issues.append("clear routing asked an unnecessary question")
        if routing.get("catalog_turn_id") is not None or routing.get("user_answer_turn_id") is not None:
            issues.append("clear routing fabricated catalog or ambiguity-answer turns")
    else:
        if topics != ["business_goal"]:
            issues.append("ambiguous routing must ask exactly one business-goal question")
        catalog_turn = turns.get(routing.get("catalog_turn_id"))
        if (
            not catalog_turn
            or catalog_turn.get("role") != "assistant"
            or any(name not in catalog_turn.get("text", "") for name in PROFILE_NAMES)
        ):
            issues.append("ambiguous routing did not show all nine Profiles in the referenced turn")
        answer_turn = turns.get(routing.get("user_answer_turn_id"))
        expected_answer = scenario["routing"]["expected_user_answer"]
        if (
            not answer_turn
            or answer_turn.get("role") != "user"
            or expected_answer not in answer_turn.get("text", "")
        ):
            issues.append("ambiguous routing lacks the controller-held user answer turn")
    if observations.get("known_choices_reused") != scenario["known_choices"]:
        issues.append("controller trace does not prove exact reuse of the five known choices")

    confirmation = observations.get("design_brief_confirmation")
    if not isinstance(confirmation, dict) or set(confirmation) != {
        "presented_turn_id", "confirmation_turn_id", "artifact_path", "artifact_sha256"
    }:
        issues.append("design brief confirmation observation fields drifted")
        confirmation = {}
    presented = turns.get(confirmation.get("presented_turn_id"))
    confirmed = turns.get(confirmation.get("confirmation_turn_id"))
    if not presented or presented.get("role") != "assistant":
        issues.append("design brief was not presented in an actual assistant turn")
    if not confirmed or confirmed.get("role") != "user":
        issues.append("design brief lacks an actual user confirmation turn")
    if confirmation.get("artifact_path") != "design-brief.md" or confirmation.get("artifact_sha256") != brief_sha256:
        issues.append("design brief confirmation is not bound to the current brief")
    if presented and confirmed and indexes[presented["turn_id"]] >= indexes[confirmed["turn_id"]]:
        issues.append("design brief confirmation precedes its presentation")

    timeline = trace.get("timeline")
    if not isinstance(timeline, list) or len(timeline) != len(TRACE_TIMELINE):
        issues.append("controller trace shared-gate timeline is incomplete")
        timeline = []
    else:
        if [item.get("event") for item in timeline if isinstance(item, dict)] != list(TRACE_TIMELINE):
            issues.append("controller trace shared-gate timeline is reordered or bypassed")
        expected_records = {
            "production_authorization_formal-html": "production-checks/formal-html.json",
            "production_authorization_browser-qa": "production-checks/browser-qa.json",
            "browser_qa": "browser-review.json",
            "production_authorization_deliver-formal-html": "production-checks/deliver-formal-html.json",
        }
        for item in timeline:
            if not isinstance(item, dict) or set(item) != {"event", "turn_id", "record_path"}:
                issues.append("controller trace timeline event fields drifted")
                continue
            event = item.get("event")
            if event in expected_records:
                if item.get("turn_id") is not None or item.get("record_path") != expected_records[event]:
                    issues.append(f"controller trace {event} does not reference its controller record")
            else:
                turn = turns.get(item.get("turn_id"))
                if not turn or item.get("record_path") is not None:
                    issues.append(f"controller trace {event} does not reference an actual turn")
        timeline_turns = [
            indexes[item["turn_id"]]
            for item in timeline
            if isinstance(item, dict) and item.get("turn_id") in indexes
        ]
        if timeline_turns != sorted(timeline_turns) or len(timeline_turns) != 5:
            issues.append("controller trace message gates are not in actual turn order")
        if timeline and confirmation:
            if timeline[0].get("turn_id") != routing.get("selection_turn_id"):
                issues.append("timeline Profile routing does not match the routing observation")
            if timeline[1].get("turn_id") != confirmation.get("confirmation_turn_id"):
                issues.append("timeline brief confirmation does not match the confirmed turn")
    return issues


def _browser_review_issues(
    review: dict[str, Any],
    *,
    review_root: Path | None,
) -> list[str]:
    issues: list[str] = []
    if review_root is None:
        return ["browser review root is missing"]
    viewports = review.get("viewports")
    if not isinstance(viewports, list):
        return ["browser review viewports must be an array"]
    observed = [
        (item.get("width"), item.get("height"))
        for item in viewports
        if isinstance(item, dict)
    ]
    if observed != list(REQUIRED_VIEWPORTS):
        issues.append("browser review must contain exactly the three required viewports")
    for item in viewports:
        expected_keys = {
            "viewport_id",
            "width",
            "height",
            "html_sha256",
            "process_exit_code",
            "qa_stdout_marker",
            "report_path",
            "report_sha256",
            "screenshots_sha256",
        }
        if not isinstance(item, dict) or set(item) != expected_keys:
            issues.append("browser viewport record fields drifted")
            continue
        width, height = item.get("width"), item.get("height")
        viewport_id = f"{width}x{height}"
        if item.get("viewport_id") != viewport_id:
            issues.append(f"browser viewport id mismatch: {viewport_id}")
        if item.get("html_sha256") != review.get("html_sha256"):
            issues.append(f"browser viewport is not bound to the reviewed HTML: {viewport_id}")
        if item.get("process_exit_code") != 0 or item.get("qa_stdout_marker") != "HTML_DECK_QA_OK":
            issues.append(f"browser QA did not pass at {viewport_id}")
        try:
            report = resolve_regular_file(review_root, item.get("report_path"), "browser QA report")
        except (ContractError, TypeError) as exc:
            issues.append(str(exc))
            continue
        if item.get("report_sha256") != sha256_file(report):
            issues.append(f"browser QA report hash mismatch at {viewport_id}")
        report_json: dict[str, Any] | None = None
        report_pages: list[Any] = []
        try:
            report_json = load_json(report)
        except (ContractError, OSError, json.JSONDecodeError) as exc:
            issues.append(f"browser QA report is invalid at {viewport_id}: {exc}")
        else:
            if report_json.get("viewport") != {"width": width, "height": height}:
                issues.append(f"browser QA report viewport mismatch at {viewport_id}")
            if not isinstance(report_json.get("url"), str) or not report_json["url"].endswith("/build/index.html"):
                issues.append(f"browser QA report does not reference build/index.html at {viewport_id}")
            if not isinstance(report_json.get("pages"), list) or not report_json["pages"]:
                issues.append(f"browser QA report has no inspected pages at {viewport_id}")
            else:
                report_pages = report_json["pages"]
        screenshots = item.get("screenshots_sha256")
        if not isinstance(screenshots, dict) or not screenshots:
            issues.append(f"browser QA screenshots are missing at {viewport_id}")
            continue
        page_numbers = [
            page.get("page") if isinstance(page, dict) else None
            for page in report_pages
        ]
        expected_page_numbers = list(range(1, len(report_pages) + 1))
        if page_numbers != expected_page_numbers:
            issues.append(
                f"browser QA report pages must be unique and contiguous from 1 at {viewport_id}"
            )
        report_parent = Path(item["report_path"]).parent
        expected_screenshots = {
            (report_parent / f"page-{page_number:02d}.png").as_posix()
            for page_number in expected_page_numbers
        }
        report_screenshots: set[str] = set()
        for page, page_number in zip(report_pages, expected_page_numbers):
            screenshot_value = page.get("screenshot") if isinstance(page, dict) else None
            if (
                not isinstance(screenshot_value, str)
                or Path(screenshot_value).name != f"page-{page_number:02d}.png"
            ):
                issues.append(
                    f"browser QA report page screenshot binding mismatch at {viewport_id}: page {page_number}"
                )
                continue
            try:
                report_screenshot = Path(screenshot_value).resolve().relative_to(
                    review_root.resolve()
                )
            except (OSError, ValueError):
                issues.append(
                    f"browser QA report page screenshot escapes the controller root at {viewport_id}: page {page_number}"
                )
            else:
                report_screenshots.add(report_screenshot.as_posix())
        if set(screenshots) != expected_screenshots or set(screenshots) != report_screenshots:
            issues.append(
                f"browser QA screenshot set does not exactly cover report pages at {viewport_id}"
            )
        for relative, digest in screenshots.items():
            try:
                screenshot = resolve_regular_file(review_root, relative, "browser QA screenshot")
            except (ContractError, TypeError) as exc:
                issues.append(str(exc))
                continue
            if not isinstance(digest, str) or not SHA256.fullmatch(digest) or sha256_file(screenshot) != digest:
                issues.append(f"browser QA screenshot hash mismatch at {viewport_id}: {relative}")
                continue
            try:
                dimensions = png_dimensions(screenshot)
            except (ContractError, OSError) as exc:
                issues.append(f"browser QA screenshot is invalid at {viewport_id}: {exc}")
            else:
                if dimensions != (width, height):
                    issues.append(f"browser QA screenshot dimensions mismatch at {viewport_id}: {relative}")
    return issues


def validate_external_review(
    review: dict[str, Any] | None,
    *,
    kind: str,
    scenario: dict[str, Any],
    run_id: str,
    html_sha256: str,
    review_root: Path | None = None,
) -> tuple[str, list[str], dict[str, Any] | None]:
    if review is None:
        return "PENDING", [f"{kind} result is missing"], None
    issues: list[str] = []
    expected_contract = (
        BROWSER_REVIEW_CONTRACT_VERSION
        if kind == "browser"
        else "taohtml-profile-release-human-review-1"
    )
    if review.get("review_contract_version") != expected_contract:
        issues.append(f"{kind} review contract version mismatch")
    if review.get("scenario_id") != scenario["scenario_id"] or review.get("run_id") != run_id:
        issues.append(f"{kind} review run/scenario mismatch")
    if review.get("html_sha256") != html_sha256:
        issues.append(f"{kind} review is not bound to the current HTML")
    if review.get("status") not in {"PASS", "FAIL"}:
        issues.append(f"{kind} review status must be PASS or FAIL")
    if kind == "browser":
        expected_keys = {
            "review_contract_version",
            "scenario_id",
            "run_id",
            "html_sha256",
            "status",
            "tool",
            "executed_at",
            "viewports",
        }
        if set(review) != expected_keys:
            issues.append("browser review fields drifted")
        if review.get("tool") != "taohtml-check-html-deck":
            issues.append("browser review tool identity mismatch")
        try:
            parse_utc(review.get("executed_at"), "browser review executed_at")
        except ContractError as exc:
            issues.append(str(exc))
        issues.extend(_browser_review_issues(review, review_root=review_root))
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


def layer_status(issues: Iterable[str]) -> str:
    return "FAIL" if list(issues) else "PASS"


def overall_status(layers: dict[str, dict[str, Any]]) -> str:
    statuses = [
        layers[name]["status"]
        for name in (
            "contract_static",
            "blackbox_flow",
            "html_browser_qa",
            "human_visual_review",
        )
    ]
    if "FAIL" in statuses:
        return "FAIL"
    if "PENDING" in statuses:
        return "PENDING"
    return "PASS"


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
