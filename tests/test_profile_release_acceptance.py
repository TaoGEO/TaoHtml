from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "evals" / "taohtml-cross-agent-v1"
SCRIPTS = EVAL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import evaluate_profile_release_matrix as matrix_evaluator  # noqa: E402
import evaluate_profile_release_result as result_evaluator  # noqa: E402
import profile_release_contract as contract  # noqa: E402
from prepare_profile_release_run import prepare  # noqa: E402


def brief_text(scenario: dict[str, object]) -> str:
    labels = scenario["required_brief_decisions"]
    profile = scenario["primary_profile"]
    identity = (
        f"primary_profile = {profile['profile_id']} | "
        f"{profile['customer_facing_name']} | {profile['definition_version']}"
    )
    return "## 场景特有决策\n\n" + identity + "\n" + "\n".join(
        f"- {label}: 已记录" for label in labels
    )


def valid_evidence(scenario: dict[str, object]) -> dict[str, object]:
    routing_spec = scenario["routing"]
    profile = scenario["primary_profile"]
    ambiguous = routing_spec["mode"] == "ambiguous"
    return {
        "evidence_contract_version": contract.EVIDENCE_CONTRACT_VERSION,
        "run_id": "profile-test-run",
        "nonce": "0" * 32,
        "scenario_id": scenario["scenario_id"],
        "routing": {
            "mode": routing_spec["mode"],
            "profile_id": profile["profile_id"],
            "customer_facing_name": profile["customer_facing_name"],
            "definition_version": profile["definition_version"],
            "selection_basis": routing_spec["selection_basis"],
            "catalog_shown": list(contract.PROFILE_NAMES) if ambiguous else [],
            "user_answer": routing_spec["expected_user_answer"] if ambiguous else None,
        },
        "questions": (
            [{"topic": "business_goal", "text": "这份成品最主要要完成哪一种业务目标？"}]
            if ambiguous
            else []
        ),
        "known_choices_reused": scenario["known_choices"],
        "design_brief": {
            "path": "design-brief.md",
            "sha256": "1" * 64,
            "confirmation_ref": "conversation://brief/confirmed",
            "confirmed_at": "2026-07-20T01:00:00Z",
            "scenario_decisions": scenario["required_brief_decisions"],
        },
        "production_authorization": {
            "path": "production-authorization.json",
            "sha256": "2" * 64,
            "authorization_ref": "conversation://production/authorized",
            "authorized_at": "2026-07-20T01:01:00Z",
            "target_html_path": "build/index.html",
            "target_html_sha256": "3" * 64,
        },
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
            "gate_sequence": list(contract.SHARED_GATE_SEQUENCE),
            "handoff_path": "project-handoff.json",
            "handoff_sha256": "4" * 64,
        },
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
        self.assertEqual(len({item["scenario_id"] for item in scenarios}), 9)
        self.assertEqual(len({item["request_ref"] for item in scenarios}), 9)
        self.assertEqual(len({item["audit"]["customer_goal"] for item in scenarios}), 9)
        self.assertEqual(
            len({item["audit"]["critical_judgment"] for item in scenarios}), 9
        )
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
        requests = [contract.scenario_request_path(item).read_bytes() for item in scenarios]
        self.assertEqual(len({hashlib.sha256(value).hexdigest() for value in requests}), 9)
        for raw in requests:
            text = raw.decode("utf-8")
            for customer_marker in ("TaoGEO", "WorkBuddy", "OpenAI", "某某公司"):
                self.assertNotIn(customer_marker, text)
        with self.assertRaises(contract.ContractError):
            contract.scenario_by_id([])  # type: ignore[arg-type]

    def test_every_scenario_audits_required_release_dimensions(self) -> None:
        for scenario in self.matrix["scenarios"]:
            audit = scenario["audit"]
            self.assertTrue(audit["customer_goal"])
            self.assertTrue(audit["critical_judgment"])
            self.assertTrue(audit["design_ready_increment"])
            self.assertTrue(audit["evidence_boundary"])
            self.assertTrue(audit["delivery_status"])
            self.assertTrue(audit["qa_focus"])
            self.assertEqual(set(scenario["known_choices"]), contract.KNOWN_CHOICE_KEYS)
            self.assertTrue(scenario["required_brief_decisions"])
            self.assertTrue(scenario["evidence_expectations"])
            self.assertTrue(scenario["human_review_dimensions"])
            definition = (
                ROOT
                / "skill"
                / "taohtml"
                / "references"
                / f"workflow-profile-{scenario['primary_profile']['profile_id']}.md"
            ).read_text(encoding="utf-8")
            increment = definition.split("### 设计简报增量", 1)[1].split("\n## ", 1)[0]
            defined_labels = set(
                re.findall(r"^- `([^`]+)`:", increment, flags=re.MULTILINE)
            )
            self.assertTrue(
                set(scenario["required_brief_decisions"]).issubset(defined_labels),
                scenario["scenario_id"],
            )

    def test_all_participant_packages_are_answer_free_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first_raw, tempfile.TemporaryDirectory() as second_raw:
            first_root = Path(first_raw)
            second_root = Path(second_raw)
            for index, scenario in enumerate(self.matrix["scenarios"]):
                identity = {
                    "run_id": f"profile-case-{index:02d}",
                    "nonce": f"{index:032x}",
                    "created_at": "2026-07-20T02:00:00Z",
                }
                first = prepare(scenario["scenario_id"], first_root, **identity)
                second = prepare(scenario["scenario_id"], second_root, **identity)
                self.assertEqual(
                    hashlib.sha256(first["archive"].read_bytes()).hexdigest(),
                    hashlib.sha256(second["archive"].read_bytes()).hexdigest(),
                )
                receipt = json.loads(first["receipt"].read_text(encoding="utf-8"))
                with zipfile.ZipFile(first["archive"]) as archive:
                    names = archive.namelist()
                    self.assertNotIn("controller/receipt.json", names)
                    package_text = "\n".join(
                        archive.read(name).decode("utf-8", errors="ignore") for name in names
                    )
                self.assertNotIn(receipt["result_hmac_key"], package_text)
                self.assertNotIn(
                    scenario["primary_profile"]["profile_id"], package_text
                )
                self.assertNotIn(
                    scenario["primary_profile"]["customer_facing_name"], package_text
                )
                self.assertFalse(receipt["controller_answer_embedded"])
                self.assertFalse(receipt["expected_profile_embedded"])

    def test_clear_routes_reuse_known_choices_and_skip_catalog(self) -> None:
        for scenario in self.matrix["scenarios"]:
            if scenario["routing"]["mode"] != "clear":
                continue
            evidence = valid_evidence(scenario)
            self.assertEqual(
                contract.evaluate_blackbox_flow(
                    evidence, scenario, brief_text=brief_text(scenario)
                ),
                [],
            )

    def test_ambiguous_route_requires_all_nine_and_one_business_question(self) -> None:
        scenario = next(
            item for item in self.matrix["scenarios"] if item["routing"]["mode"] == "ambiguous"
        )
        evidence = valid_evidence(scenario)
        self.assertEqual(
            contract.evaluate_blackbox_flow(
                evidence, scenario, brief_text=brief_text(scenario)
            ),
            [],
        )
        missing_catalog = copy.deepcopy(evidence)
        missing_catalog["routing"]["catalog_shown"] = list(contract.PROFILE_NAMES[:-1])
        issues = contract.evaluate_blackbox_flow(
            missing_catalog, scenario, brief_text=brief_text(scenario)
        )
        self.assertTrue(any("complete nine-name catalog" in item for item in issues))
        duplicate_goal = copy.deepcopy(evidence)
        duplicate_goal["questions"].append(
            {"topic": "business_goal", "text": "再确认一次业务目标？"}
        )
        issues = contract.evaluate_blackbox_flow(
            duplicate_goal, scenario, brief_text=brief_text(scenario)
        )
        self.assertTrue(any("exactly one business-goal" in item for item in issues))

    def test_flow_fails_on_repeated_known_choice_or_missing_brief_decision(self) -> None:
        scenario = self.matrix["scenarios"][0]
        evidence = valid_evidence(scenario)
        evidence["questions"] = [
            {"topic": "use_mode", "text": "你要阅读还是演示？"}
        ]
        evidence["design_brief"]["scenario_decisions"] = scenario[
            "required_brief_decisions"
        ][:-1]
        issues = contract.evaluate_blackbox_flow(
            evidence, scenario, brief_text=brief_text(scenario)
        )
        self.assertTrue(any("known choices were asked again" in item for item in issues))
        self.assertTrue(any("scenario-specific decisions" in item for item in issues))

    def test_flow_fails_when_brief_and_authorization_are_conflated(self) -> None:
        scenario = self.matrix["scenarios"][0]
        evidence = valid_evidence(scenario)
        evidence["production_authorization"]["authorization_ref"] = evidence[
            "design_brief"
        ]["confirmation_ref"]
        evidence["production_authorization"]["authorized_at"] = evidence[
            "design_brief"
        ]["confirmed_at"]
        issues = contract.evaluate_blackbox_flow(
            evidence, scenario, brief_text=brief_text(scenario)
        )
        self.assertTrue(any("not independent" in item for item in issues))
        self.assertTrue(any("does not follow" in item for item in issues))

    def test_missing_browser_or_human_result_is_fail_closed(self) -> None:
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
        layers = {
            "contract_static": {"status": "PASS"},
            "blackbox_flow": {"status": "PASS"},
            "html_browser_qa": {"status": browser_status},
            "human_visual_review": {"status": human_status},
        }
        participant_claimed_status = "PASS"
        self.assertEqual(participant_claimed_status, "PASS")
        self.assertEqual(browser_status, "PENDING")
        self.assertEqual(human_status, "PENDING")
        self.assertEqual(contract.overall_status(layers), "PENDING")

    def test_participant_pass_cannot_promote_a_real_row_without_external_layers(self) -> None:
        scenario = self.matrix["scenarios"][0]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            prepared = prepare(
                scenario["scenario_id"],
                root,
                run_id="profile-real-row",
                nonce="9" * 32,
                created_at="2026-07-20T03:00:00Z",
            )
            participant_root = prepared["participant_tree"]
            receipt = json.loads(prepared["receipt"].read_text(encoding="utf-8"))
            output = participant_root / receipt["output_directory"]
            (output / "build").mkdir(parents=True)

            brief = brief_text(scenario) + "\n签批权限待确认\n"
            (output / "design-brief.md").write_text(brief, encoding="utf-8")
            (output / "build" / "index.html").write_text(
                "<!doctype html><html><body>签批权限待确认</body></html>",
                encoding="utf-8",
            )
            (output / "project-handoff.json").write_text("{}\n", encoding="utf-8")
            (output / "handoff.md").write_text("签批权限待确认\n", encoding="utf-8")
            brief_sha = hashlib.sha256(
                (output / "design-brief.md").read_bytes()
            ).hexdigest()
            html_sha = hashlib.sha256(
                (output / "build" / "index.html").read_bytes()
            ).hexdigest()
            authorization = {
                "schema_version": "1.0",
                "record_type": "production_authorization",
                "status": "authorized",
                "target_artifact_ref": "current-html",
                "target_artifact_sha256": html_sha,
                "design_brief_sha256": brief_sha,
                "authorized_actions": [
                    "formal-html",
                    "browser-qa",
                    "deliver-formal-html",
                ],
            }
            (output / "production-authorization.json").write_text(
                json.dumps(authorization, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            evidence = valid_evidence(scenario)
            evidence["run_id"] = receipt["run_id"]
            evidence["nonce"] = receipt["nonce"]
            evidence["design_brief"]["sha256"] = brief_sha
            evidence["production_authorization"]["sha256"] = hashlib.sha256(
                (output / "production-authorization.json").read_bytes()
            ).hexdigest()
            evidence["production_authorization"]["target_html_sha256"] = html_sha
            evidence["production"]["handoff_sha256"] = hashlib.sha256(
                (output / "project-handoff.json").read_bytes()
            ).hexdigest()
            (output / "profile-evidence.json").write_text(
                json.dumps(evidence, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            artifacts = {
                path.relative_to(output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in output.rglob("*")
                if path.is_file()
            }
            submission = {
                "submission_contract_version": contract.SUBMISSION_CONTRACT_VERSION,
                "run_id": receipt["run_id"],
                "nonce": receipt["nonce"],
                "scenario_id": receipt["scenario_id"],
                "participant_claimed_status": "PASS",
                "artifacts": artifacts,
            }
            (output / "submission.json").write_text(
                json.dumps(submission, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            handoff_validation = {
                "readiness": {
                    "schema_valid": True,
                    "bindings_valid": True,
                    "continuation_ready": True,
                    "delivery_ready": True,
                },
                "qa_execution_claim": "not_executed_by_validator",
            }
            with mock.patch.object(
                result_evaluator,
                "_handoff_check",
                return_value=(handoff_validation, []),
            ):
                result = result_evaluator.evaluate_returned_root(
                    receipt_path=prepared["receipt"],
                    returned_root=participant_root,
                    returned_kind="directory_tree",
                    returned_sha256="e" * 64,
                    browser_review_path=None,
                    human_review_path=None,
                )
            self.assertEqual(result["layers"]["contract_static"]["status"], "PASS")
            self.assertEqual(result["layers"]["blackbox_flow"]["status"], "PASS")
            self.assertEqual(result["layers"]["html_browser_qa"]["status"], "PENDING")
            self.assertEqual(result["layers"]["human_visual_review"]["status"], "PENDING")
            self.assertEqual(result["claims"]["participant_claimed_status"], "PASS")
            self.assertFalse(result["claims"]["participant_status_used_for_pass"])
            self.assertEqual(result["overall_status"], "PENDING")
            schema = json.loads(contract.RESULT_SCHEMA_PATH.read_text(encoding="utf-8"))
            self.assertEqual(
                result["result_contract_version"],
                schema["properties"]["result_contract_version"]["const"],
            )
            self.assertEqual(set(result), set(schema["required"]))
            result_path = prepared["receipt"].parent / "result.json"
            result_path.write_text(
                json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            _, issues = matrix_evaluator._verify_result(result_path)
            self.assertEqual(issues, [])

            forged = copy.deepcopy(result)
            forged["overall_status"] = "PASS"
            forged["provenance"]["result_hmac_sha256"] = contract.result_hmac_sha256(
                forged, receipt["result_hmac_key"]
            )
            forged_path = prepared["receipt"].parent / "forged.json"
            forged_path.write_text(
                json.dumps(forged, ensure_ascii=False) + "\n", encoding="utf-8"
            )
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
            handoff_path.write_text(
                json.dumps(handoff, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            result, issues = result_evaluator._handoff_check(
                handoff_path, artifact_root
            )
        self.assertEqual(issues, [])
        self.assertIsNotNone(result)
        self.assertTrue(all(result["readiness"].values()))

    def test_external_review_cannot_pass_with_wrong_html_or_missing_dimensions(self) -> None:
        scenario = self.matrix["scenarios"][0]
        browser = {
            "review_contract_version": "taohtml-profile-release-browser-review-1",
            "scenario_id": scenario["scenario_id"],
            "run_id": "profile-test-run",
            "html_sha256": "b" * 64,
            "status": "PASS",
            "tool": "taohtml-check-html-deck",
            "qa_report_sha256": "c" * 64,
            "screenshots_sha256": {"page-01.png": "d" * 64},
        }
        status, issues, _ = contract.validate_external_review(
            browser,
            kind="browser",
            scenario=scenario,
            run_id="profile-test-run",
            html_sha256="a" * 64,
        )
        self.assertEqual(status, "FAIL")
        self.assertTrue(any("current HTML" in item for item in issues))

        human = {
            "review_contract_version": "taohtml-profile-release-human-review-1",
            "scenario_id": scenario["scenario_id"],
            "run_id": "profile-test-run",
            "html_sha256": "a" * 64,
            "status": "PASS",
            "dimensions": {},
        }
        status, issues, _ = contract.validate_external_review(
            human,
            kind="human",
            scenario=scenario,
            run_id="profile-test-run",
            html_sha256="a" * 64,
        )
        self.assertEqual(status, "FAIL")
        self.assertTrue(any("dimensions" in item for item in issues))

    def test_complete_external_browser_and_human_records_can_pass_their_own_layers(self) -> None:
        scenario = self.matrix["scenarios"][0]
        html_sha = "a" * 64
        browser = {
            "review_contract_version": "taohtml-profile-release-browser-review-1",
            "scenario_id": scenario["scenario_id"],
            "run_id": "profile-test-run",
            "html_sha256": html_sha,
            "status": "PASS",
            "tool": "taohtml-check-html-deck",
            "executed_at": "2026-07-20T04:00:00Z",
            "process_exit_code": 0,
            "qa_stdout_marker": "HTML_DECK_QA_OK",
            "qa_report_sha256": "b" * 64,
            "screenshots_sha256": {"page-01.png": "c" * 64},
        }
        status, issues, _ = contract.validate_external_review(
            browser,
            kind="browser",
            scenario=scenario,
            run_id="profile-test-run",
            html_sha256=html_sha,
        )
        self.assertEqual((status, issues), ("PASS", []))

        human = {
            "review_contract_version": "taohtml-profile-release-human-review-1",
            "scenario_id": scenario["scenario_id"],
            "run_id": "profile-test-run",
            "html_sha256": html_sha,
            "status": "PASS",
            "reviewer": "release reviewer",
            "reviewed_at": "2026-07-20T04:10:00Z",
            "dimensions": {
                name: {"status": "PASS", "note": f"checked {name}"}
                for name in scenario["human_review_dimensions"]
            },
        }
        status, issues, _ = contract.validate_external_review(
            human,
            kind="human",
            scenario=scenario,
            run_id="profile-test-run",
            html_sha256=html_sha,
        )
        self.assertEqual((status, issues), ("PASS", []))

    def test_result_hmac_detects_a_forged_pass(self) -> None:
        key = "ab" * 32
        result = {
            "overall_status": "PENDING",
            "provenance": {"result_hmac_sha256": ""},
        }
        result["provenance"]["result_hmac_sha256"] = contract.result_hmac_sha256(
            result, key
        )
        forged = copy.deepcopy(result)
        forged["overall_status"] = "PASS"
        self.assertNotEqual(
            forged["provenance"]["result_hmac_sha256"],
            contract.result_hmac_sha256(forged, key),
        )

    def test_controller_receipt_reviews_and_result_cannot_live_in_participant_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            participant = Path(raw) / "participant"
            participant.mkdir()
            with self.assertRaises(contract.ContractError):
                contract.assert_controller_owned_path(
                    participant / "controller" / "result.json",
                    participant,
                    "controller result",
                )
            contract.assert_controller_owned_path(
                Path(raw) / "controller" / "result.json",
                participant,
                "controller result",
            )

    def test_empty_matrix_is_pending_not_pass(self) -> None:
        result = matrix_evaluator.evaluate_matrix([])
        self.assertEqual(result["status"], "PENDING")
        self.assertFalse(result["claims"]["all_profiles_executed"])
        self.assertFalse(result["claims"]["all_browser_qa_passed"])
        self.assertFalse(result["claims"]["all_human_visual_reviews_passed"])

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
        for packaging_script in (
            ROOT / "scripts" / "package_skillhub.py",
            ROOT / "scripts" / "package_plugin_marketplace.py",
        ):
            text = packaging_script.read_text(encoding="utf-8")
            self.assertIn("shutil.copytree(", text)
            self.assertIn("SKILL_SOURCE", text)


if __name__ == "__main__":
    unittest.main()
