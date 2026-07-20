from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "evals" / "taohtml-cross-agent-v1"
SCRIPTS = EVAL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import evaluate_profile_release_matrix as matrix_evaluator  # noqa: E402
import evaluate_profile_release_result as result_evaluator  # noqa: E402
import profile_release_contract as contract  # noqa: E402
import record_profile_release_production_check as production_recorder  # noqa: E402
import run_profile_release_browser_qa as browser_runner  # noqa: E402
from prepare_profile_release_run import prepare  # noqa: E402


def load_production_checker() -> object:
    path = ROOT / "skill" / "taohtml" / "scripts" / "check_production_authorization.py"
    spec = importlib.util.spec_from_file_location("profile_release_auth", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRODUCTION_CHECKER = load_production_checker()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def png_bytes(width: int, height: int) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    row = b"\x00" + b"\xff\xff\xff" * width
    return signature + chunk(b"IHDR", header) + chunk(
        b"IDAT", zlib.compress(row * height, 9)
    ) + chunk(b"IEND", b"")


def brief_text(scenario: dict[str, object], *, placeholder: bool = False) -> str:
    profile = scenario["primary_profile"]
    checks = scenario["brief_content_checks"]
    fact_markers = checks["fact_markers"]
    status_markers = checks["status_markers"]
    lines = [
        "# Report Design Brief",
        "",
        (
            f"primary_profile = {profile['profile_id']} | "
            f"{profile['customer_facing_name']} | {profile['definition_version']}"
        ),
        "",
        "## 场景特有决策",
        "",
    ]
    for index, label in enumerate(scenario["required_brief_decisions"]):
        fact = fact_markers[index % len(fact_markers)]
        status = status_markers[index % len(status_markers)]
        value = "已记录" if placeholder else f"采用与{fact}相符的可审计处理方案"
        lines.extend(
            [
                f"### {label}",
                "",
                f"- 实际决策：{value}",
                f"- 事实依据：当前用户事实明确提到{fact}，据此限定本项处理",
                f"- 状态边界：本项按{status}状态表达，不扩张为更强结论",
                "",
            ]
        )
    lines.extend(
        term
        for expectation in scenario["evidence_expectations"]
        for term in expectation["required_terms"]
    )
    return "\n".join(lines) + "\n"


def production_state(scenario: dict[str, object], brief_sha: str) -> dict[str, object]:
    theme = {
        "theme_id": scenario["known_choices"]["visual_binding"],
        "selection_status": "user_selected",
        "decision_ref": "conversation://current/theme-selection",
    }
    motion = {
        "density": scenario["known_choices"]["motion_density"],
        "selection_status": "user_selected",
        "decision_ref": "conversation://current/motion-selection",
    }
    return {
        "schema_version": "1.3",
        "task_id": f"profile-release-{scenario['scenario_id']}",
        "route": "idea_only",
        "visual_route": "built_in",
        "material_summary": {
            "status": "not_required",
            "artifact_path": None,
            "artifact_sha256": None,
            "confirmation_ref": None,
        },
        "reference_vi": {
            "status": "not_required",
            "artifact_path": None,
            "artifact_sha256": None,
            "confirmation_ref": None,
        },
        "profile_use": {
            "status": "not_required",
            "artifact_path": None,
            "artifact_sha256": None,
        },
        "project_theme_compiled": False,
        "built_in_theme": theme,
        "motion_density": motion,
        "design_brief": {
            "status": "confirmed",
            "artifact_path": "design-brief.md",
            "artifact_sha256": brief_sha,
            "confirmation_ref": "conversation://current/brief-confirmed",
            "design_decisions_sha256": PRODUCTION_CHECKER.design_decisions_sha256(
                theme, motion
            ),
        },
    }


def participant_evidence(
    scenario: dict[str, object], *, run_id: str, nonce: str, case_id: str, brief_sha: str,
    handoff_sha: str,
) -> dict[str, object]:
    return {
        "evidence_contract_version": contract.EVIDENCE_CONTRACT_VERSION,
        "run_id": run_id,
        "nonce": nonce,
        "case_id": case_id,
        "selected_profile": scenario["primary_profile"],
        "selection_basis": "根据主要业务结果、受众使用方式与证据约束选择唯一主路径",
        "design_brief": {"path": "design-brief.md", "sha256": brief_sha},
        "evidence_boundaries": [
            {
                "boundary_id": item["boundary_id"],
                "status": item["required_status"],
            }
            for item in scenario["evidence_expectations"]
        ],
        "production": {
            "route": "direct_html",
            "runtime_contract": "taohtml-runtime-1",
            "handoff_path": "project-handoff.json",
            "handoff_sha256": handoff_sha,
        },
    }


def controller_trace(
    scenario: dict[str, object], *, run_id: str, brief_sha: str
) -> dict[str, object]:
    profile = scenario["primary_profile"]
    ambiguous = scenario["routing"]["mode"] == "ambiguous"
    turns = [{"turn_id": "u-request", "role": "user", "text": "请按当前请求继续完成这份离线材料。"}]
    questions: list[dict[str, str]] = []
    if ambiguous:
        catalog_text = "；".join(contract.PROFILE_NAMES)
        turns.append(
            {
                "turn_id": "a-catalog",
                "role": "assistant",
                "text": f"可选业务目标：{catalog_text}。这份成品最主要要完成哪一种业务目标？",
            }
        )
        turns.append(
            {
                "turn_id": "u-answer",
                "role": "user",
                "text": scenario["routing"]["expected_user_answer"],
            }
        )
        questions = [{"turn_id": "a-catalog", "topic": "business_goal"}]
    turns.extend(
        [
            {
                "turn_id": "a-profile",
                "role": "assistant",
                "text": f"已选择 primary Profile：{profile['customer_facing_name']}，并继续形成简报。",
            },
            {
                "turn_id": "a-brief",
                "role": "assistant",
                "text": f"请确认当前完整设计简报，SHA-256 为 {brief_sha}。",
            },
            {
                "turn_id": "u-confirm",
                "role": "user",
                "text": "确认这份当前完整设计简报，可以进入独立授权检查。",
            },
            {
                "turn_id": "a-html",
                "role": "assistant",
                "text": "formal-html checker 已允许，现已保存第一份 Direct HTML。",
            },
            {
                "turn_id": "a-runtime",
                "role": "assistant",
                "text": "已执行当前 TaoHtml Runtime 的交互与阅读状态检查。",
            },
            {
                "turn_id": "a-handoff",
                "role": "assistant",
                "text": "deliver-formal-html checker 已允许，现已形成便携 Handoff。",
            },
        ]
    )
    return {
        "trace_contract_version": contract.TRACE_CONTRACT_VERSION,
        "run_id": run_id,
        "scenario_id": scenario["scenario_id"],
        "source": {
            "kind": "platform_turn_export",
            "locator": "codex://thread/profile-release-test/turns",
        },
        "turns": turns,
        "observations": {
            "routing": {
                "mode": scenario["routing"]["mode"],
                **profile,
                "selection_basis": scenario["routing"]["selection_basis"],
                "selection_turn_id": "a-profile",
                "catalog_turn_id": "a-catalog" if ambiguous else None,
                "user_answer_turn_id": "u-answer" if ambiguous else None,
            },
            "questions": questions,
            "known_choices_reused": scenario["known_choices"],
            "design_brief_confirmation": {
                "presented_turn_id": "a-brief",
                "confirmation_turn_id": "u-confirm",
                "artifact_path": "design-brief.md",
                "artifact_sha256": brief_sha,
            },
        },
        "timeline": [
            {"event": "profile_routing", "turn_id": "a-profile", "record_path": None},
            {"event": "design_brief_confirmation", "turn_id": "u-confirm", "record_path": None},
            {"event": "production_authorization_formal-html", "turn_id": None, "record_path": "production-checks/formal-html.json"},
            {"event": "direct_html", "turn_id": "a-html", "record_path": None},
            {"event": "runtime_qa", "turn_id": "a-runtime", "record_path": None},
            {"event": "production_authorization_browser-qa", "turn_id": None, "record_path": "production-checks/browser-qa.json"},
            {"event": "browser_qa", "turn_id": None, "record_path": "browser-review.json"},
            {"event": "production_authorization_deliver-formal-html", "turn_id": None, "record_path": "production-checks/deliver-formal-html.json"},
            {"event": "handoff", "turn_id": "a-handoff", "record_path": None},
        ],
    }


def create_browser_review(
    controller_root: Path,
    scenario: dict[str, object],
    *,
    run_id: str,
    html_sha: str,
) -> Path:
    viewport_records: list[dict[str, object]] = []
    for width, height in contract.REQUIRED_VIEWPORTS:
        viewport_id = f"{width}x{height}"
        viewport_root = controller_root / "browser-qa" / viewport_id
        report_path = viewport_root / "qa-report.json"
        screenshot_path = viewport_root / "page-01.png"
        write_json(
            report_path,
            {
                "url": "file:///controller-return/build/index.html",
                "viewport": {"width": width, "height": height},
                "pages": [{"page": 1}],
            },
        )
        screenshot_path.write_bytes(png_bytes(width, height))
        viewport_records.append(
            {
                "viewport_id": viewport_id,
                "width": width,
                "height": height,
                "html_sha256": html_sha,
                "process_exit_code": 0,
                "qa_stdout_marker": "HTML_DECK_QA_OK",
                "report_path": report_path.relative_to(controller_root).as_posix(),
                "report_sha256": sha256(report_path),
                "screenshots_sha256": {
                    screenshot_path.relative_to(controller_root).as_posix(): sha256(
                        screenshot_path
                    )
                },
            }
        )
    review_path = controller_root / "browser-review.json"
    write_json(
        review_path,
        {
            "review_contract_version": contract.BROWSER_REVIEW_CONTRACT_VERSION,
            "scenario_id": scenario["scenario_id"],
            "run_id": run_id,
            "html_sha256": html_sha,
            "status": "PASS",
            "tool": "taohtml-check-html-deck",
            "executed_at": "2026-07-21T04:00:00Z",
            "viewports": viewport_records,
        },
    )
    return review_path


def create_human_review(
    controller_root: Path,
    scenario: dict[str, object],
    *,
    run_id: str,
    html_sha: str,
) -> Path:
    path = controller_root / "human-review.json"
    write_json(
        path,
        {
            "review_contract_version": "taohtml-profile-release-human-review-1",
            "scenario_id": scenario["scenario_id"],
            "run_id": run_id,
            "html_sha256": html_sha,
            "status": "PASS",
            "reviewer": "independent release reviewer",
            "reviewed_at": "2026-07-21T04:10:00Z",
            "dimensions": {
                name: {"status": "PASS", "note": f"checked {name} against current HTML"}
                for name in scenario["human_review_dimensions"]
            },
        },
    )
    return path


def build_returned_run(root: Path, scenario: dict[str, object]) -> dict[str, Path]:
    prepared = prepare(
        scenario["scenario_id"],
        root,
        run_id="profile-real-row",
        nonce="9" * 32,
        created_at="2026-07-21T03:00:00Z",
    )
    participant_root = prepared["participant_tree"]
    controller_root = prepared["receipt"].parent
    receipt = json.loads(prepared["receipt"].read_text(encoding="utf-8"))
    output = participant_root / receipt["output_directory"]
    (output / "gates").mkdir(parents=True)
    (output / "build").mkdir()
    brief = brief_text(scenario)
    (output / "design-brief.md").write_text(brief, encoding="utf-8")
    write_json(output / "gates" / "production-state.json", production_state(scenario, sha256(output / "design-brief.md")))

    formal = production_recorder.capture_production_check(
        receipt_path=prepared["receipt"], returned_root=participant_root, action="formal-html"
    )
    write_json(controller_root / "production-checks" / "formal-html.json", formal)

    required_term = scenario["evidence_expectations"][0]["required_terms"][0]
    (output / "build" / "index.html").write_text(
        f"<!doctype html><html><body>{required_term}</body></html>", encoding="utf-8"
    )
    browser_record = production_recorder.capture_production_check(
        receipt_path=prepared["receipt"], returned_root=participant_root, action="browser-qa"
    )
    write_json(controller_root / "production-checks" / "browser-qa.json", browser_record)

    browser_review = create_browser_review(
        controller_root,
        scenario,
        run_id=receipt["run_id"],
        html_sha=sha256(output / "build" / "index.html"),
    )
    delivery_record = production_recorder.capture_production_check(
        receipt_path=prepared["receipt"],
        returned_root=participant_root,
        action="deliver-formal-html",
    )
    write_json(
        controller_root / "production-checks" / "deliver-formal-html.json",
        delivery_record,
    )

    (output / "project-handoff.json").write_text("{}\n", encoding="utf-8")
    (output / "handoff.md").write_text(required_term + "\n", encoding="utf-8")
    evidence = participant_evidence(
        scenario,
        run_id=receipt["run_id"],
        nonce=receipt["nonce"],
        case_id=receipt["case_id"],
        brief_sha=sha256(output / "design-brief.md"),
        handoff_sha=sha256(output / "project-handoff.json"),
    )
    write_json(output / "profile-evidence.json", evidence)
    artifacts = {
        path.relative_to(output).as_posix(): sha256(path)
        for path in output.rglob("*")
        if path.is_file()
    }
    write_json(
        output / "submission.json",
        {
            "submission_contract_version": contract.SUBMISSION_CONTRACT_VERSION,
            "run_id": receipt["run_id"],
            "nonce": receipt["nonce"],
            "case_id": receipt["case_id"],
            "participant_claimed_status": "PASS",
            "artifacts": artifacts,
        },
    )
    write_json(
        controller_root / "conversation-trace.json",
        controller_trace(
            scenario, run_id=receipt["run_id"], brief_sha=sha256(output / "design-brief.md")
        ),
    )
    human_review = create_human_review(
        controller_root,
        scenario,
        run_id=receipt["run_id"],
        html_sha=sha256(output / "build" / "index.html"),
    )
    return {
        **prepared,
        "output": output,
        "controller_root": controller_root,
        "trace": controller_root / "conversation-trace.json",
        "production_checks": controller_root / "production-checks",
        "browser_review": browser_review,
        "human_review": human_review,
    }


HANDOFF_VALIDATION = {
    "readiness": {
        "schema_valid": True,
        "bindings_valid": True,
        "continuation_ready": True,
        "delivery_ready": True,
    },
    "qa_execution_claim": "not_executed_by_validator",
}


class ProfileReleaseAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = contract.load_release_matrix()

    def test_matrix_has_exactly_nine_unique_generic_scenarios(self) -> None:
        scenarios = self.matrix["scenarios"]
        self.assertEqual(len(scenarios), 9)
        self.assertEqual(
            tuple(item["primary_profile"]["profile_id"] for item in scenarios),
            contract.PROFILE_IDS,
        )
        for selector in (
            lambda item: item["scenario_id"],
            lambda item: item["request_ref"],
            lambda item: item["audit"]["customer_goal"],
            lambda item: item["audit"]["critical_judgment"],
        ):
            self.assertEqual(len({selector(item) for item in scenarios}), 9)
        self.assertEqual(
            len(
                {
                    expectation["boundary_id"]
                    for item in scenarios
                    for expectation in item["evidence_expectations"]
                }
            ),
            9,
        )
        self.assertEqual(
            sum(item["routing"]["mode"] == "ambiguous" for item in scenarios), 1
        )

    def test_every_scenario_audits_profile_contract_and_content_checks(self) -> None:
        for scenario in self.matrix["scenarios"]:
            self.assertEqual(set(scenario["known_choices"]), contract.KNOWN_CHOICE_KEYS)
            self.assertTrue(scenario["brief_content_checks"]["fact_markers"])
            self.assertTrue(scenario["brief_content_checks"]["status_markers"])
            definition = (
                ROOT
                / "skill"
                / "taohtml"
                / "references"
                / f"workflow-profile-{scenario['primary_profile']['profile_id']}.md"
            ).read_text(encoding="utf-8")
            increment = definition.split("### 设计简报增量", 1)[1].split("\n## ", 1)[0]
            labels = set(re.findall(r"^- `([^`]+)`:", increment, flags=re.MULTILINE))
            self.assertTrue(set(scenario["required_brief_decisions"]).issubset(labels))

    def test_all_participant_packages_are_answer_free_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first_raw, tempfile.TemporaryDirectory() as second_raw:
            for index, scenario in enumerate(self.matrix["scenarios"]):
                identity = {
                    "run_id": f"profile-case-{index:02d}",
                    "nonce": f"{index:032x}",
                    "created_at": "2026-07-21T02:00:00Z",
                }
                first = prepare(scenario["scenario_id"], Path(first_raw), **identity)
                second = prepare(scenario["scenario_id"], Path(second_raw), **identity)
                self.assertEqual(sha256(first["archive"]), sha256(second["archive"]))
                receipt = json.loads(first["receipt"].read_text(encoding="utf-8"))
                with zipfile.ZipFile(first["archive"]) as archive:
                    package_text = "\n".join(
                        archive.read(name).decode("utf-8", errors="ignore")
                        for name in archive.namelist()
                    ).casefold()
                self.assertNotIn(receipt["result_hmac_key"], package_text)
                for marker in contract.answer_leakage_markers(scenario):
                    self.assertNotIn(marker, package_text, (scenario["scenario_id"], marker))
                self.assertFalse(receipt["controller_answer_embedded"])
                self.assertFalse(receipt["expected_profile_embedded"])

    def test_placeholder_brief_labels_do_not_pass_semantic_check(self) -> None:
        scenario = self.matrix["scenarios"][0]
        issues = contract.validate_brief_decisions(
            brief_text(scenario, placeholder=True), scenario
        )
        self.assertTrue(any("placeholder-only" in item for item in issues))
        self.assertEqual(
            contract.validate_brief_decisions(brief_text(scenario), scenario), []
        )

    def test_controller_trace_proves_clear_and_ambiguous_routing(self) -> None:
        for scenario in self.matrix["scenarios"]:
            brief_sha = "a" * 64
            trace = controller_trace(scenario, run_id="profile-test-run", brief_sha=brief_sha)
            self.assertEqual(
                contract.validate_controller_trace(
                    trace, scenario, run_id="profile-test-run", brief_sha256=brief_sha
                ),
                [],
            )

    def test_forged_participant_evidence_cannot_replace_controller_trace(self) -> None:
        scenario = self.matrix["scenarios"][0]
        with tempfile.TemporaryDirectory() as raw:
            built = build_returned_run(Path(raw), scenario)
            with mock.patch.object(
                result_evaluator, "_handoff_check", return_value=(HANDOFF_VALIDATION, [])
            ):
                result = result_evaluator.evaluate_returned_root(
                    receipt_path=built["receipt"],
                    returned_root=built["participant_tree"],
                    returned_kind="directory_tree",
                    returned_sha256="e" * 64,
                    conversation_trace_path=None,
                    production_checks_root=built["production_checks"],
                    browser_review_path=built["browser_review"],
                    human_review_path=built["human_review"],
                )
        self.assertEqual(result["layers"]["contract_static"]["status"], "PASS")
        self.assertEqual(result["layers"]["blackbox_flow"]["status"], "PENDING")
        self.assertTrue(
            any("conversation trace is missing" in item for item in result["layers"]["blackbox_flow"]["issues"])
        )

    def test_trace_rejects_repeated_known_choice_and_missing_catalog(self) -> None:
        clear = self.matrix["scenarios"][0]
        clear_trace = controller_trace(clear, run_id="profile-test-run", brief_sha="a" * 64)
        clear_trace["observations"]["questions"] = [
            {"turn_id": "a-profile", "topic": "use_mode"}
        ]
        issues = contract.validate_controller_trace(
            clear_trace, clear, run_id="profile-test-run", brief_sha256="a" * 64
        )
        self.assertTrue(any("known choices were asked again" in item for item in issues))

        ambiguous = next(
            item for item in self.matrix["scenarios"] if item["routing"]["mode"] == "ambiguous"
        )
        trace = controller_trace(ambiguous, run_id="profile-test-run", brief_sha="a" * 64)
        trace["turns"][1]["text"] = "只展示了一个目标。这份成品主要要做什么？"
        issues = contract.validate_controller_trace(
            trace, ambiguous, run_id="profile-test-run", brief_sha256="a" * 64
        )
        self.assertTrue(any("all nine Profiles" in item for item in issues))

    def test_real_production_state_fixture_runs_all_three_current_checker_actions(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "profile-release-production-state"
        with tempfile.TemporaryDirectory() as raw:
            artifact_root = Path(raw) / "artifact"
            shutil.copytree(fixture, artifact_root)
            state = artifact_root / "gates" / "production-state.json"
            checker = ROOT / "skill" / "taohtml" / "scripts" / "check_production_authorization.py"
            for action in contract.PRODUCTION_ACTIONS:
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(checker),
                        "--state",
                        str(state),
                        "--artifact-root",
                        str(artifact_root),
                        "--action",
                        action,
                    ],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, (action, completed.stdout))
                result = json.loads(completed.stdout)
                self.assertEqual(
                    result["requested_action"], {"name": action, "allowed": True}
                )

    def test_production_records_enforce_pre_and_post_html_observations(self) -> None:
        scenario = self.matrix["scenarios"][0]
        with tempfile.TemporaryDirectory() as raw:
            built = build_returned_run(Path(raw), scenario)
            records = {
                action: json.loads(
                    (built["production_checks"] / f"{action}.json").read_text(encoding="utf-8")
                )
                for action in contract.PRODUCTION_ACTIONS
            }
            self.assertEqual(records["formal-html"]["html_observation"]["state"], "absent")
            self.assertIsNone(records["formal-html"]["html_observation"]["sha256"])
            for action in ("browser-qa", "deliver-formal-html"):
                self.assertEqual(records[action]["html_observation"]["state"], "present")
                self.assertEqual(
                    records[action]["html_observation"]["sha256"],
                    sha256(built["output"] / "build" / "index.html"),
                )
            with self.assertRaises(contract.ContractError):
                production_recorder.capture_production_check(
                    receipt_path=built["receipt"],
                    returned_root=built["participant_tree"],
                    action="formal-html",
                )
            with self.assertRaises(contract.ContractError):
                production_recorder.capture_production_check(
                    receipt_path=built["receipt"],
                    returned_root=built["participant_tree"],
                    action="browser-qa",
                )
            saved_review = built["controller_root"] / "browser-review.saved.json"
            built["browser_review"].rename(saved_review)
            with self.assertRaises(contract.ContractError):
                production_recorder.capture_production_check(
                    receipt_path=built["receipt"],
                    returned_root=built["participant_tree"],
                    action="deliver-formal-html",
                )

    def test_obsolete_self_authored_authorization_cannot_pass(self) -> None:
        scenario = self.matrix["scenarios"][0]
        with tempfile.TemporaryDirectory() as raw:
            built = build_returned_run(Path(raw), scenario)
            obsolete = built["output"] / "production-authorization.json"
            write_json(
                obsolete,
                {
                    "status": "authorized",
                    "target_artifact_sha256": sha256(built["output"] / "build" / "index.html"),
                },
            )
            submission = json.loads(
                (built["output"] / "submission.json").read_text(encoding="utf-8")
            )
            submission["artifacts"]["production-authorization.json"] = sha256(obsolete)
            write_json(built["output"] / "submission.json", submission)
            with mock.patch.object(
                result_evaluator, "_handoff_check", return_value=(HANDOFF_VALIDATION, [])
            ):
                result = result_evaluator.evaluate_returned_root(
                    receipt_path=built["receipt"],
                    returned_root=built["participant_tree"],
                    returned_kind="directory_tree",
                    returned_sha256="e" * 64,
                    conversation_trace_path=built["trace"],
                    production_checks_root=built["production_checks"],
                    browser_review_path=built["browser_review"],
                    human_review_path=built["human_review"],
                )
        self.assertEqual(result["layers"]["contract_static"]["status"], "FAIL")
        self.assertTrue(
            any("production-authorization.json" in item for item in result["layers"]["contract_static"]["issues"])
        )

    def test_fake_browser_hash_and_missing_viewport_fail_closed(self) -> None:
        scenario = self.matrix["scenarios"][0]
        with tempfile.TemporaryDirectory() as raw:
            controller_root = Path(raw)
            review_path = create_browser_review(
                controller_root,
                scenario,
                run_id="profile-test-run",
                html_sha="a" * 64,
            )
            review = json.loads(review_path.read_text(encoding="utf-8"))
            forged = copy.deepcopy(review)
            forged["viewports"][0]["report_sha256"] = "b" * 64
            status, issues, _ = contract.validate_external_review(
                forged,
                kind="browser",
                scenario=scenario,
                run_id="profile-test-run",
                html_sha256="a" * 64,
                review_root=controller_root,
            )
            self.assertEqual(status, "FAIL")
            self.assertTrue(any("report hash mismatch" in item for item in issues))

            missing = copy.deepcopy(review)
            missing["viewports"].pop()
            status, issues, _ = contract.validate_external_review(
                missing,
                kind="browser",
                scenario=scenario,
                run_id="profile-test-run",
                html_sha256="a" * 64,
                review_root=controller_root,
            )
            self.assertEqual(status, "FAIL")
            self.assertTrue(any("three required viewports" in item for item in issues))

    def test_browser_review_rehashes_actual_three_viewport_artifacts(self) -> None:
        scenario = self.matrix["scenarios"][0]
        with tempfile.TemporaryDirectory() as raw:
            controller_root = Path(raw)
            review_path = create_browser_review(
                controller_root,
                scenario,
                run_id="profile-test-run",
                html_sha="a" * 64,
            )
            review = json.loads(review_path.read_text(encoding="utf-8"))
            status, issues, _ = contract.validate_external_review(
                review,
                kind="browser",
                scenario=scenario,
                run_id="profile-test-run",
                html_sha256="a" * 64,
                review_root=controller_root,
            )
        self.assertEqual((status, issues), ("PASS", []))

    def test_browser_runner_invokes_all_three_viewports(self) -> None:
        scenario = self.matrix["scenarios"][0]
        with tempfile.TemporaryDirectory() as raw:
            built = build_returned_run(Path(raw), scenario)
            calls: list[tuple[int, int]] = []

            def fake_qa(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                viewport_root = Path(command[3])
                width = int(command[5])
                height = int(command[7])
                calls.append((width, height))
                write_json(
                    viewport_root / "qa-report.json",
                    {
                        "url": (built["output"] / "build" / "index.html").as_uri(),
                        "viewport": {"width": width, "height": height},
                        "pages": [{"page": 1}],
                    },
                )
                (viewport_root / "page-01.png").write_bytes(png_bytes(width, height))
                return subprocess.CompletedProcess(
                    command, 0, stdout="HTML_DECK_QA_OK\n", stderr=""
                )

            with mock.patch.object(browser_runner.subprocess, "run", side_effect=fake_qa):
                review = browser_runner.run_browser_qa(
                    receipt_path=built["receipt"],
                    returned_root=built["participant_tree"],
                    output_dir=built["controller_root"] / "runner-browser-qa",
                    production_check_path=(
                        built["production_checks"] / "browser-qa.json"
                    ),
                )
            status, issues, _ = contract.validate_external_review(
                review,
                kind="browser",
                scenario=scenario,
                run_id="profile-real-row",
                html_sha256=sha256(built["output"] / "build" / "index.html"),
                review_root=built["controller_root"],
            )
        self.assertEqual(calls, list(contract.REQUIRED_VIEWPORTS))
        self.assertEqual((status, issues), ("PASS", []))

    def test_missing_controller_or_human_layers_remain_pending(self) -> None:
        scenario = self.matrix["scenarios"][0]
        browser_status, _, _ = contract.validate_external_review(
            None,
            kind="browser",
            scenario=scenario,
            run_id="profile-test-run",
            html_sha256="a" * 64,
        )
        human_status, _, _ = contract.validate_external_review(
            None,
            kind="human",
            scenario=scenario,
            run_id="profile-test-run",
            html_sha256="a" * 64,
        )
        self.assertEqual((browser_status, human_status), ("PENDING", "PENDING"))
        layers = {
            "contract_static": {"status": "PASS"},
            "blackbox_flow": {"status": "PENDING"},
            "html_browser_qa": {"status": browser_status},
            "human_visual_review": {"status": human_status},
        }
        self.assertEqual(contract.overall_status(layers), "PENDING")

    def test_one_fully_bound_row_can_pass_each_independent_layer(self) -> None:
        scenario = self.matrix["scenarios"][0]
        with tempfile.TemporaryDirectory() as raw:
            built = build_returned_run(Path(raw), scenario)
            with mock.patch.object(
                result_evaluator, "_handoff_check", return_value=(HANDOFF_VALIDATION, [])
            ):
                result = result_evaluator.evaluate_returned_root(
                    receipt_path=built["receipt"],
                    returned_root=built["participant_tree"],
                    returned_kind="directory_tree",
                    returned_sha256="e" * 64,
                    conversation_trace_path=built["trace"],
                    production_checks_root=built["production_checks"],
                    browser_review_path=built["browser_review"],
                    human_review_path=built["human_review"],
                )
        self.assertEqual(
            {name: layer["status"] for name, layer in result["layers"].items()},
            {
                "contract_static": "PASS",
                "blackbox_flow": "PASS",
                "html_browser_qa": "PASS",
                "human_visual_review": "PASS",
            },
        )
        self.assertEqual(result["overall_status"], "PASS")
        self.assertFalse(result["claims"]["participant_status_used_for_pass"])
        schema = json.loads(contract.RESULT_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            result["result_contract_version"],
            schema["properties"]["result_contract_version"]["const"],
        )
        self.assertEqual(set(result), set(schema["required"]))

    def test_result_hmac_and_matrix_reject_forged_overall_pass(self) -> None:
        key = "ab" * 32
        result = {"overall_status": "PENDING", "provenance": {"result_hmac_sha256": ""}}
        result["provenance"]["result_hmac_sha256"] = contract.result_hmac_sha256(result, key)
        forged = copy.deepcopy(result)
        forged["overall_status"] = "PASS"
        self.assertNotEqual(
            forged["provenance"]["result_hmac_sha256"],
            contract.result_hmac_sha256(forged, key),
        )
        self.assertEqual(matrix_evaluator.evaluate_matrix([])["status"], "PENDING")

        scenario = self.matrix["scenarios"][0]
        with tempfile.TemporaryDirectory() as raw:
            built = build_returned_run(Path(raw), scenario)
            receipt = json.loads(built["receipt"].read_text(encoding="utf-8"))
            with mock.patch.object(
                result_evaluator, "_handoff_check", return_value=(HANDOFF_VALIDATION, [])
            ):
                pending = result_evaluator.evaluate_returned_root(
                    receipt_path=built["receipt"],
                    returned_root=built["participant_tree"],
                    returned_kind="directory_tree",
                    returned_sha256="e" * 64,
                    conversation_trace_path=built["trace"],
                    production_checks_root=built["production_checks"],
                    browser_review_path=built["browser_review"],
                    human_review_path=None,
                )
            self.assertEqual(pending["overall_status"], "PENDING")
            forged_result = copy.deepcopy(pending)
            forged_result["overall_status"] = "PASS"
            forged_result["provenance"]["result_hmac_sha256"] = (
                contract.result_hmac_sha256(
                    forged_result, receipt["result_hmac_key"]
                )
            )
            forged_path = built["controller_root"] / "forged-result.json"
            write_json(forged_path, forged_result)
            _, issues = matrix_evaluator._verify_result(forged_path)
        self.assertTrue(any("contradicts its four layers" in item for item in issues))

    def test_direct_html_release_accepts_null_current_build_handoff(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "project-handoff"
        with tempfile.TemporaryDirectory() as raw:
            artifact_root = Path(raw) / "handoff"
            shutil.copytree(fixture_root, artifact_root)
            handoff_path = artifact_root / "meaning-preserving-ready.json"
            handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
            handoff["schema_version"] = "1.1"
            handoff["current_build"] = None
            write_json(handoff_path, handoff)
            result, issues = result_evaluator._handoff_check(handoff_path, artifact_root)
        self.assertEqual(issues, [])
        self.assertIsNotNone(result)
        self.assertTrue(all(result["readiness"].values()))

    def test_controller_evidence_cannot_live_in_participant_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            participant = Path(raw) / "participant"
            participant.mkdir()
            for relative in (
                "conversation-trace.json",
                "production-checks/formal-html.json",
                "browser-review.json",
            ):
                with self.assertRaises(contract.ContractError):
                    contract.assert_controller_owned_path(
                        participant / relative, participant, "controller evidence"
                    )

    def test_report_ir_and_compiler_are_packaged_but_experimental(self) -> None:
        boundary = self.matrix["compiler_report_ir_boundary"]
        self.assertEqual(boundary["v0_5_0_status"], "experimental_pilot_only")
        self.assertEqual(boundary["default_production_route"], "direct_html")
        self.assertFalse(boundary["package_presence_means_formal_general_availability"])
        self.assertEqual(
            set(boundary["unsupported_in_v0_5_0"]),
            {
                "advanced_composition_graph",
                "non_monotonic_runtime_state",
                "incremental_compilation",
            },
        )
        for relative in boundary["release_packages_include"]:
            self.assertTrue((ROOT / "skill" / "taohtml" / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
