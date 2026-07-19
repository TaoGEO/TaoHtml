from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "evals" / "taohtml-cross-agent-v1"
SCRIPT_ROOT = EVAL_ROOT / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import accept_run as ACCEPT  # noqa: E402
import blackbox_contract as CONTRACT  # noqa: E402
import evaluate_matrix as MATRIX  # noqa: E402
import prepare_run as PREPARE  # noqa: E402

from tests.test_project_handoff_validator import (  # noqa: E402
    VALIDATOR as HANDOFF_VALIDATOR,
    compiled_handoff_payload,
    load_fixture,
)
from tests.test_report_ir_v1 import bound_ir, valid_ir  # noqa: E402


FIXED_CREATED_AT = "2026-07-19T08:00:00Z"
FIXED_NONCE = "0123456789abcdef0123456789abcdef"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_stub_submission(prepared: dict[str, Path | str]) -> Path:
    tree = Path(prepared["participant_tree"])
    receipt = CONTRACT.load_json(Path(prepared["receipt"]))
    output = tree / receipt["output_directory"]
    (output / "build").mkdir(parents=True)
    key = CONTRACT.load_answer_key(receipt["scenario_id"])
    profile = key["expected_profile"]
    (output / "design-brief.md").write_text(
        "\n".join(
            [
                "# 报告设计简报",
                profile["customer_facing_name"],
                profile["primary_profile_id"],
                profile["definition_version"],
            ]
        ),
        encoding="utf-8",
    )
    write_json(output / "report-ir.json", {})
    (output / "build" / "index.html").write_text(
        "<!doctype html><html><body>direct-only stub</body></html>\n",
        encoding="utf-8",
    )
    write_json(output / "build" / "build-manifest.json", {})
    write_json(output / "build" / "source-map.json", {})
    write_json(output / "build" / "report.ir.normalized.json", {})
    write_json(output / "project-handoff.json", {})
    (output / "handoff.md").write_text("stub handoff\n", encoding="utf-8")
    artifact_hashes = {
        path.relative_to(output).as_posix(): CONTRACT.sha256_file(path)
        for path in output.rglob("*")
        if path.is_file()
    }
    write_json(
        output / "submission.json",
        {
            "submission_contract_version": CONTRACT.SUBMISSION_CONTRACT_VERSION,
            "run_id": receipt["run_id"],
            "nonce": receipt["nonce"],
            "scenario_id": receipt["scenario_id"],
            "input_tree_sha256": receipt["input_tree_sha256"],
            "audit": {
                "platform": "workbuddy",
                "agent": "workbuddy",
                "model": "unknown",
                "started_at": "2026-07-19T08:01:00Z",
                "ended_at": "2026-07-19T08:02:00Z",
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
            },
            "isolation_attestation": {
                "package_root_only": True,
                "installed_taohtml_only_external_input": True,
                "no_prior_artifacts_used": True,
            },
            "artifacts": artifact_hashes,
        },
    )
    return output


def prepare_fixed(root: Path, scenario: str = "idea-change-pitch") -> dict[str, Path | str]:
    return PREPARE.prepare(
        scenario,
        "workbuddy",
        root,
        run_id=f"{scenario}-run",
        nonce=FIXED_NONCE,
        created_at=FIXED_CREATED_AT,
    )


class CrossAgentPackageTests(unittest.TestCase):
    def test_three_scenarios_are_generic_and_answer_free(self) -> None:
        scenario_ids = {
            path.parent.name
            for path in (EVAL_ROOT / "participant" / "scenarios").glob("*/scenario.json")
        }
        self.assertEqual(
            scenario_ids,
            {"idea-change-pitch", "research-reading-brief", "corporate-ops-rebuild"},
        )
        markers = {item.casefold() for item in CONTRACT.leakage_markers()}
        for scenario_id in scenario_ids:
            request = (
                EVAL_ROOT
                / "participant"
                / "scenarios"
                / scenario_id
                / "request.md"
            ).read_text(encoding="utf-8").casefold()
            self.assertFalse(markers.intersection(marker for marker in markers if marker in request))
            self.assertNotIn("primary_profile_id", request)
            self.assertNotIn("report_ir_version", request)

    def test_participant_zip_contains_only_inputs_and_run_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prepared = prepare_fixed(Path(temp_dir) / "runs")
            archive = Path(prepared["archive"])
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
                self.assertEqual(
                    names, ["RUN_INSTRUCTIONS.md", "request.md", "run.json"]
                )
                combined = b"\n".join(bundle.read(name) for name in names)
            self.assertNotIn(b"controller", b"\n".join(name.encode() for name in names))
            self.assertNotIn(b"live-presentation-persuasion", combined)
            self.assertNotIn(b"control-key", combined)

    def test_material_builders_produce_real_portable_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "runs"
            research = PREPARE.prepare(
                "research-reading-brief",
                "workbuddy",
                root,
                run_id="research-format-run",
                nonce=FIXED_NONCE,
                created_at=FIXED_CREATED_AT,
            )
            tree = Path(research["participant_tree"])
            self.assertTrue((tree / "materials" / "field-study.pdf").read_bytes().startswith(b"%PDF-1.4"))
            with zipfile.ZipFile(tree / "materials" / "interview-notes.docx") as document:
                self.assertIn("word/document.xml", document.namelist())
            corporate = PREPARE.prepare(
                "corporate-ops-rebuild",
                "codex",
                root,
                run_id="corporate-format-run",
                nonce="1123456789abcdef0123456789abcdef",
                created_at=FIXED_CREATED_AT,
            )
            image = Path(corporate["participant_tree"]) / "materials" / "template-screenshot.png"
            self.assertEqual(CONTRACT.png_dimensions(image), (1600, 900))

    def test_same_explicit_identity_produces_identical_zip_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            first = prepare_fixed(base / "first")
            second = prepare_fixed(base / "second")
            self.assertEqual(
                CONTRACT.sha256_file(Path(first["archive"])),
                CONTRACT.sha256_file(Path(second["archive"])),
            )

    def test_default_runs_get_distinct_run_id_and_nonce(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "runs"
            first = PREPARE.prepare("idea-change-pitch", "codex", root)
            second = PREPARE.prepare("idea-change-pitch", "codex", root)
            self.assertNotEqual(first["run_id"], second["run_id"])
            self.assertNotEqual(first["nonce"], second["nonce"])

    def test_existing_run_directory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "runs"
            prepare_fixed(root)
            with self.assertRaisesRegex(CONTRACT.ContractError, "already exists"):
                prepare_fixed(root)

    def test_answer_marker_injection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prepared = prepare_fixed(Path(temp_dir) / "runs")
            tree = Path(prepared["participant_tree"])
            with (tree / "request.md").open("a", encoding="utf-8") as handle:
                handle.write("\nlive-presentation-persuasion\n")
            with self.assertRaisesRegex(CONTRACT.ContractError, "answer marker leaked"):
                CONTRACT.assert_no_answer_leakage(tree)

    def test_controller_answer_key_is_physically_outside_participant_source(self) -> None:
        participant = (EVAL_ROOT / "participant").resolve()
        controller = (EVAL_ROOT / "controller").resolve()
        self.assertNotEqual(participant, controller)
        with self.assertRaises(ValueError):
            controller.relative_to(participant)
        participant_files = {path.name.casefold() for path in participant.rglob("*") if path.is_file()}
        self.assertFalse({"human_review.md", "matrix.json"} & participant_files)


class CrossAgentIntegrityTests(unittest.TestCase):
    def test_returned_input_hash_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prepared = prepare_fixed(Path(temp_dir) / "runs")
            tree = Path(prepared["participant_tree"])
            (tree / "request.md").write_text("benign but changed\n", encoding="utf-8")
            receipt = CONTRACT.load_json(Path(prepared["receipt"]))
            _, _, _, checks = ACCEPT.verify_returned_package(receipt, tree)
            immutable = next(record for record in checks if record["id"] == "immutable_inputs")
            self.assertEqual(immutable["status"], "FAIL")

    def test_run_id_or_nonce_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prepared = prepare_fixed(Path(temp_dir) / "runs")
            tree = Path(prepared["participant_tree"])
            run = CONTRACT.load_json(tree / "run.json")
            run["nonce"] = "f" * 32
            write_json(tree / "run.json", run)
            receipt = CONTRACT.load_json(Path(prepared["receipt"]))
            _, _, _, checks = ACCEPT.verify_returned_package(receipt, tree)
            identity = next(record for record in checks if record["id"] == "run_identity")
            manifest_hash = next(record for record in checks if record["id"] == "run_manifest_hash")
            self.assertEqual(identity["status"], "FAIL")
            self.assertEqual(manifest_hash["status"], "FAIL")

    def test_extra_old_submission_directory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prepared = prepare_fixed(Path(temp_dir) / "runs")
            tree = Path(prepared["participant_tree"])
            build_stub_submission(prepared)
            (tree / "submission" / "old-run").mkdir()
            (tree / "submission" / "old-run" / "index.html").write_text(
                "old\n", encoding="utf-8"
            )
            receipt = CONTRACT.load_json(Path(prepared["receipt"]))
            _, _, _, checks = ACCEPT.verify_returned_package(receipt, tree)
            fresh = next(
                record for record in checks if record["id"] == "fresh_single_output_directory"
            )
            self.assertEqual(fresh["status"], "FAIL")
            self.assertIn("old-run", fresh["evidence"]["extra_submission_entries"])

    def test_submission_artifact_hash_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prepared = prepare_fixed(Path(temp_dir) / "runs")
            output = build_stub_submission(prepared)
            (output / "handoff.md").write_text("changed after submission\n", encoding="utf-8")
            receipt = CONTRACT.load_json(Path(prepared["receipt"]))
            _, _, _, checks = ACCEPT.verify_returned_package(
                receipt, Path(prepared["participant_tree"])
            )
            hashes = next(record for record in checks if record["id"] == "submission_artifact_hashes")
            self.assertEqual(hashes["status"], "FAIL")

    def test_controller_result_cannot_be_written_inside_participant_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prepared = prepare_fixed(Path(temp_dir) / "runs")
            build_stub_submission(prepared)
            participant = Path(prepared["participant_tree"])
            with self.assertRaisesRegex(CONTRACT.ContractError, "must remain outside"):
                ACCEPT.accept(
                    Path(prepared["receipt"]),
                    participant,
                    participant / "controller-result.json",
                    skip_browser=True,
                )


class CrossAgentEvaluationBoundaryTests(unittest.TestCase):
    def test_direct_only_stub_cannot_pass_required_ir_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prepared = prepare_fixed(Path(temp_dir) / "runs")
            build_stub_submission(prepared)
            result = ACCEPT.accept(
                Path(prepared["receipt"]),
                Path(prepared["participant_tree"]),
                Path(temp_dir) / "result.json",
                skip_browser=True,
            )
            self.assertEqual(result["checks"]["participant_integrity"]["status"], "PASS")
            self.assertEqual(result["checks"]["report_ir"]["status"], "FAIL")
            self.assertEqual(result["automatic_status"], "FAIL")
            self.assertFalse(result["claims"]["workbuddy_run_executed_by_this_script"])

    def test_legacy_ir_may_validate_but_fails_profile_bound_blackbox_assertions(self) -> None:
        source = b"segment,value\nenterprise,28\nother,7\n"
        legacy = valid_ir(hashlib.sha256(source).hexdigest())
        key = CONTRACT.load_answer_key("research-reading-brief")
        assertions = CONTRACT.evaluate_assertions(
            legacy, key["hard_assertions"]["report_ir"]
        )
        self.assertTrue(any(record["path"] == "report_ir_version" and record["status"] == "FAIL" for record in assertions))
        self.assertTrue(any(record["path"] == "workflow_profile.primary_profile_id" and record["status"] == "FAIL" for record in assertions))

    def test_bound_ir_reports_four_independent_layers(self) -> None:
        source = b"segment,value\nenterprise,28\nother,7\n"
        candidate = bound_ir(
            valid_ir(hashlib.sha256(source).hexdigest()),
            "research-analysis-argumentation",
        )
        report_ir_core, _, _ = ACCEPT._production_modules()
        result = report_ir_core.validate_ir(candidate)
        self.assertEqual(
            {key: result[key] for key in (
                "schema_valid",
                "references_valid",
                "semantics_valid",
                "compiler_ready",
            )},
            {
                "schema_valid": True,
                "references_valid": True,
                "semantics_valid": True,
                "compiler_ready": True,
            },
        )
        self.assertEqual(result["qa_execution_claim"], "not_executed_by_validator")

    def test_controller_browser_skip_is_not_qa_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prepared = prepare_fixed(Path(temp_dir) / "runs")
            build_stub_submission(prepared)
            result = ACCEPT.accept(
                Path(prepared["receipt"]),
                Path(prepared["participant_tree"]),
                Path(temp_dir) / "result.json",
                skip_browser=True,
            )
            qa = result["checks"]["qa_boundary"]
            self.assertEqual(qa["status"], "FAIL")
            self.assertEqual(
                qa["controller_execution"]["browser_runtime_editor_qa"]["status"],
                "NOT_RUN",
            )

    def test_handoff_record_validation_does_not_execute_qa(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "handoff"
            payload, _ = compiled_handoff_payload(
                root, "research-analysis-argumentation"
            )
            result = HANDOFF_VALIDATOR.evaluate_handoff(payload, root)
            self.assertTrue(result["readiness"]["schema_valid"])
            self.assertTrue(result["readiness"]["bindings_valid"])
            self.assertFalse(result["readiness"]["delivery_ready"])
            self.assertEqual(result["qa_execution_claim"], "not_executed_by_validator")

    def test_direct_handoff_current_build_null_cannot_satisfy_ir_assertion(self) -> None:
        payload = load_fixture("meaning-preserving-ready.json")
        payload["schema_version"] = "1.1"
        payload["current_build"] = None
        result = HANDOFF_VALIDATOR.evaluate_handoff(payload, CONTRACT.REPOSITORY_ROOT / "tests" / "fixtures" / "project-handoff")
        self.assertTrue(result["readiness"]["schema_valid"])
        assertions = CONTRACT.evaluate_assertions(
            payload,
            CONTRACT.load_answer_key("research-reading-brief")["hard_assertions"]["project_handoff"],
        )
        self.assertTrue(any(record["path"].startswith("current_build") and record["status"] == "FAIL" for record in assertions))

    def test_audit_usage_unknown_is_not_estimated_and_does_not_affect_pass(self) -> None:
        audit, issues = ACCEPT.validate_audit(
            {
                "platform": "workbuddy",
                "agent": "workbuddy",
                "model": "unknown",
                "started_at": "2026-07-19T08:00:00Z",
                "ended_at": "2026-07-19T08:01:00Z",
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
        )
        self.assertEqual(issues, [])
        self.assertEqual(audit["tokens"]["availability"], "unknown")

    def test_balance_delta_points_must_match_exact_platform_balances(self) -> None:
        _, issues = ACCEPT.validate_audit(
            {
                "platform": "workbuddy",
                "agent": "workbuddy",
                "model": "unknown",
                "started_at": "2026-07-19T08:00:00Z",
                "ended_at": "2026-07-19T08:01:00Z",
                "tokens": {
                    "availability": "unknown",
                    "source": "unknown",
                    "input": None,
                    "output": None,
                    "cache": None,
                    "total": None,
                },
                "points": {
                    "availability": "exact",
                    "source": "balance_delta",
                    "value": 8,
                    "balance_before": 100,
                    "balance_after": 95,
                },
            }
        )
        self.assertIn("balance_delta audit.points value does not match balances", issues)


class CrossAgentMatrixTests(unittest.TestCase):
    def _result(self, scenario: str, platform: str, human: str = "PASS") -> dict:
        return {
            "result_contract_version": CONTRACT.RESULT_CONTRACT_VERSION,
            "run": {
                "scenario_id": scenario,
                "target_platform": platform,
                "run_id": f"{scenario}-{platform}",
            },
            "automatic_status": "PASS",
            "human_review": {"status": human},
        }

    def test_full_matrix_stays_disabled_when_results_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_json(
                root / "one-result.json",
                self._result("idea-change-pitch", "codex"),
            )
            result = MATRIX.evaluate([root / "one-result.json"])
            self.assertEqual(result["smoke_status"], "NOT_PASSED")
            self.assertFalse(result["full_matrix"]["enabled"])
            self.assertFalse(result["workbuddy_results_synthesized"])
            self.assertEqual(
                len([row for row in result["smoke_rows"] if row["status"] == "MISSING"]),
                5,
            )

    def test_full_matrix_enables_only_after_all_six_automatic_and_human_pass(self) -> None:
        matrix = CONTRACT.load_json(EVAL_ROOT / "controller" / "matrix.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            paths: list[Path] = []
            for scenario in matrix["smoke"]["scenarios"]:
                for platform in matrix["platforms"]:
                    path = Path(temp_dir) / f"{scenario}-{platform}-result.json"
                    write_json(path, self._result(scenario, platform))
                    paths.append(path)
            passed = MATRIX.evaluate(paths)
            self.assertEqual(passed["smoke_status"], "PASS")
            self.assertTrue(passed["full_matrix"]["enabled"])
            self.assertEqual(passed["full_matrix"]["expected_run_count"], 18)
            pending_path = paths[0]
            write_json(
                pending_path,
                self._result("idea-change-pitch", "codex", human="PENDING"),
            )
            pending = MATRIX.evaluate(paths)
            self.assertFalse(pending["full_matrix"]["enabled"])


if __name__ == "__main__":
    unittest.main()
