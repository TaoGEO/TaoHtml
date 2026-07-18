from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "report-ir-v0"


def load_script(name: str) -> ModuleType:
    path = EVAL / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"report_ir_v0_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREPARE = load_script("prepare_run")
ADAPTER = load_script("report_ir_adapter")
JUDGE = load_script("judge_run")
PACKAGER = load_script("package_result")
COMPARE = load_script("compare_runs")


class ReportIrV0PreparationTests(unittest.TestCase):
    def test_direct_and_ir_workspaces_are_controller_free_and_route_specific(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            direct = PREPARE.prepare("direct", Path(temp) / "direct")
            ir = PREPARE.prepare("ir", Path(temp) / "ir")

            direct_files = {
                str(path.relative_to(direct)) for path in direct.rglob("*") if path.is_file()
            }
            ir_files = {str(path.relative_to(ir)) for path in ir.rglob("*") if path.is_file()}

            self.assertNotIn("input/report-ir-contract.md", direct_files)
            self.assertEqual(
                {path for path in direct_files if path.startswith("tools/")},
                {"tools/package_result.py"},
            )
            self.assertIn("input/report-ir-contract.md", ir_files)
            self.assertIn("tools/report_ir_adapter.py", ir_files)
            self.assertIn("tools/package_result.py", ir_files)
            self.assertFalse(any("controller" in path for path in direct_files | ir_files))
            self.assertFalse(any("reference-ir" in path for path in direct_files | ir_files))

            direct_metadata = json.loads((direct / "run-metadata.json").read_text())
            ir_metadata = json.loads((ir / "run-metadata.json").read_text())
            self.assertEqual(direct_metadata["route"], "direct")
            self.assertEqual(ir_metadata["route"], "ir")
            self.assertEqual(direct_metadata["model"], "auto")
            self.assertEqual(direct_metadata["case_id"], "case-a")
            self.assertEqual(direct_metadata["pair_id"], "local-pair")
            self.assertTrue((direct / "input" / "case-spec.json").is_file())

    def test_case_rotation_changes_content_and_binds_one_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            direct = PREPARE.prepare(
                "direct",
                root / "direct",
                case_id="case-b",
                pair_id="pair-b-01",
            )
            ir = PREPARE.prepare(
                "ir",
                root / "ir",
                case_id="case-b",
                pair_id="pair-b-01",
            )
            direct_spec = (direct / "input" / "case-spec.json").read_bytes()
            ir_spec = (ir / "input" / "case-spec.json").read_bytes()
            self.assertEqual(direct_spec, ir_spec)
            self.assertIn("访谈不少，决策依据依然断层", (direct / "input" / "design-brief.md").read_text())
            self.assertNotIn("证据先行", (direct / "input" / "design-brief.md").read_text())
            direct_manifest = json.loads((direct / "workspace-manifest.json").read_text())
            ir_manifest = json.loads((ir / "workspace-manifest.json").read_text())
            self.assertEqual(direct_manifest["case_spec_sha256"], ir_manifest["case_spec_sha256"])
            self.assertEqual(direct_manifest["pair_id"], "pair-b-01")
            self.assertEqual(ir_manifest["expected_report_id"], "report_customer_insight_loop_b")
            self.assertIn(
                'data-benchmark-case="report_customer_insight_loop_b"',
                (direct / "input" / "prompt.md").read_text(),
            )
            self.assertNotIn("{{", (direct / "input" / "prompt.md").read_text())

    def test_controller_receipt_is_external_and_detects_input_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = PREPARE.prepare("ir", root / "workspace")
            receipt = PREPARE.write_controller_receipt(
                "ir",
                workspace,
                root / "controller" / "ir-receipt.json",
            )
            self.assertFalse((workspace / "ir-receipt.json").exists())
            evidence = JUDGE.verify_integrity_receipt(workspace, receipt, "ir")
            self.assertGreater(evidence["immutable_file_count"], 10)

            adapter = workspace / "tools" / "report_ir_adapter.py"
            adapter.write_text(adapter.read_text(encoding="utf-8") + "\n# modified\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "immutable executor input mismatch"):
                JUDGE.verify_integrity_receipt(workspace, receipt, "ir")


class ReportIrV0AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = json.loads(
            (EVAL / "controller" / "reference-ir.json").read_text(encoding="utf-8")
        )

    def test_reference_ir_validates_and_compiles_without_model_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = PREPARE.prepare("ir", Path(temp) / "workspace")
            ir_path = workspace / "report-ir.json"
            ir_path.write_text(json.dumps(self.reference, ensure_ascii=False), encoding="utf-8")
            output = workspace / "deliverable" / "index.html"
            manifest_path = workspace / "deliverable" / "build-manifest.json"
            manifest = ADAPTER.compile_ir(
                ir_path,
                workspace,
                workspace / "skill" / "taohtml",
                "rigorous-consulting-report",
                output,
                manifest_path,
            )
            self.assertTrue(output.is_file())
            self.assertEqual(manifest["compiler"]["model_calls"], 0)
            self.assertEqual(manifest["entity_counts"]["pages"], 5)
            self.assertEqual(manifest["artifact_status"], "preview_unverified")
            self.assertFalse(manifest["formal_delivery_ready"])
            self.assertEqual(
                manifest["compiler"]["sha256"],
                ADAPTER.sha256_file(EVAL / "scripts" / "report_ir_adapter.py"),
            )
            self.assertEqual(
                manifest["compiler_dependencies"],
                ADAPTER.compiler_dependency_hashes(workspace / "skill" / "taohtml"),
            )
            self.assertEqual(
                manifest["qa_requirements"]["browser_qa"],
                "required_for_formal_delivery",
            )
            self.assertEqual(manifest["output"]["path"], "deliverable/index.html")
            output_text = output.read_text(encoding="utf-8")
            self.assertIn(
                'data-benchmark-case="report_case_evidence_system"',
                output_text,
            )
            self.assertIn('data-source-kind="illustrative"', output_text)
            self.assertIn('data-source-label="示意内容图片（待核实）"', output_text)
            self.assertNotIn('data-source-kind="verified"', output_text)
            self.assertEqual(
                manifest["evidence_boundary"]["renderer_source_kind"],
                "illustrative",
            )
            self.assertEqual(
                manifest["evidence_boundary"]["real_world_status"],
                "illustrative",
            )
            deck = JUDGE.DeckParser()
            deck.feed(output_text)
            evidence = JUDGE.validate_ir_source_binding(self.reference, manifest, deck)
            self.assertEqual(evidence["expected_source_kind"], "illustrative")

    def test_verified_visual_requires_verified_source_and_all_linked_evidence(self) -> None:
        source = {
            "id": "source_public",
            "source_role": "external_public_evidence",
            "content_status": "verified",
        }
        verified = [{"id": "evidence_verified", "content_status": "verified"}]
        illustrative = [{"id": "evidence_fixture", "content_status": "illustrative"}]
        self.assertEqual(ADAPTER.derive_visual_source_kind(source, verified), "verified")
        self.assertEqual(
            ADAPTER.derive_visual_source_kind(source, illustrative),
            "illustrative",
        )
        self.assertEqual(ADAPTER.derive_visual_source_kind(source, []), "illustrative")
        unverified_source = {**source, "content_status": "unverified"}
        self.assertEqual(
            ADAPTER.derive_visual_source_kind(unverified_source, verified),
            "illustrative",
        )

    def test_unknown_or_contradictory_source_status_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = PREPARE.prepare("ir", Path(temp) / "workspace")
            unknown = copy.deepcopy(self.reference)
            unknown["sources"][0]["content_status"] = "trusted"
            with self.assertRaisesRegex(ValueError, "unsupported status"):
                ADAPTER.validate_ir(unknown, workspace)

            contradictory = copy.deepcopy(self.reference)
            contradictory["sources"][0]["content_status"] = "verified"
            with self.assertRaisesRegex(ValueError, "synthetic_fixture must remain illustrative"):
                ADAPTER.validate_ir(contradictory, workspace)

    def test_judge_rejects_html_source_status_that_disagrees_with_ir(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = PREPARE.prepare("ir", Path(temp) / "workspace")
            ir_path = workspace / "report-ir.json"
            ir_path.write_text(json.dumps(self.reference, ensure_ascii=False), encoding="utf-8")
            output = workspace / "deliverable" / "index.html"
            manifest_path = workspace / "deliverable" / "build-manifest.json"
            manifest = ADAPTER.compile_ir(
                ir_path,
                workspace,
                workspace / "skill" / "taohtml",
                "rigorous-consulting-report",
                output,
                manifest_path,
            )
            forged_html = output.read_text(encoding="utf-8").replace(
                'data-source-kind="illustrative"',
                'data-source-kind="verified"',
            ).replace(
                'data-source-label="示意内容图片（待核实）"',
                'data-source-label="来源证据图片（已核实）"',
            )
            deck = JUDGE.DeckParser()
            deck.feed(forged_html)
            with self.assertRaisesRegex(ValueError, "compiled HTML source kind mismatch"):
                JUDGE.validate_ir_source_binding(self.reference, manifest, deck)

    def test_generated_research_files_use_lf_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "nested" / "result.txt"
            ADAPTER.write_utf8_lf(path, "first\r\nsecond\rthird\n")
            self.assertEqual(path.read_bytes(), b"first\nsecond\nthird\n")

    def test_unknown_reference_and_executable_payload_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = PREPARE.prepare("ir", Path(temp) / "workspace")

            unknown = copy.deepcopy(self.reference)
            unknown["pages"][0]["claim_refs"] = ["claim_missing"]
            with self.assertRaisesRegex(ValueError, "unknown claim"):
                ADAPTER.validate_ir(unknown, workspace)

            executable = copy.deepcopy(self.reference)
            executable["blocks"]["block_cover_title_a"]["content"] = "<script>alert(1)</script>"
            with self.assertRaisesRegex(ValueError, "executable markup"):
                ADAPTER.validate_ir(executable, workspace)

    def test_traceability_requires_explicit_pending_verification_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = PREPARE.prepare("ir", Path(temp) / "workspace")
            missing = copy.deepcopy(self.reference)
            missing["traceability"].pop("pending_verification_required")
            with self.assertRaisesRegex(ValueError, "pending_verification_required"):
                ADAPTER.validate_ir(missing, workspace)

    def test_result_packager_rejects_forged_manifest_and_keeps_complete_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = PREPARE.prepare("ir", root / "workspace")
            ir_path = workspace / "report-ir.json"
            ir_path.write_text(json.dumps(self.reference, ensure_ascii=False), encoding="utf-8")
            output = workspace / "deliverable" / "index.html"
            manifest_path = workspace / "deliverable" / "build-manifest.json"
            ADAPTER.compile_ir(
                ir_path,
                workspace,
                workspace / "skill" / "taohtml",
                "black-white-fluorescent-cards",
                output,
                manifest_path,
            )
            (workspace / "deliverable" / "handoff.md").write_text(
                "# 预览构建\n\n## 待核实内容清单\n",
                encoding="utf-8",
            )
            archive_name = json.loads(
                (workspace / "workspace-manifest.json").read_text(encoding="utf-8")
            )["expected_result_archive"]
            archive = PACKAGER.package("ir", workspace, root / archive_name)
            with zipfile.ZipFile(archive) as bundle:
                names = set(bundle.namelist())
            self.assertIn("report-ir.json", names)
            self.assertIn("deliverable/build-manifest.json", names)
            self.assertIn("result-index.json", names)
            self.assertIn("tools/report_ir_adapter.py", names)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["compiler"]["sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "compiler.sha256"):
                PACKAGER.package("ir", workspace, root / archive_name)


class ReportIrV0MetadataTests(unittest.TestCase):
    def test_unavailable_usage_cannot_hide_estimates(self) -> None:
        metadata = json.loads(
            (EVAL / "executor" / "input" / "run-metadata-template.json").read_text()
        )
        metadata.update({"route": "direct", "client": "workbuddy", "model": "auto"})
        JUDGE.validate_metadata(metadata, "direct")

        metadata["token_usage"]["total_tokens"] = 100
        with self.assertRaisesRegex(ValueError, "cannot contain estimates"):
            JUDGE.validate_metadata(metadata, "direct")

    def test_exact_workbuddy_points_are_recorded_without_calling_them_tokens(self) -> None:
        direct = {
            "route": "direct",
            "status": "PASS",
            "case": {
                "case_id": "case-a",
                "pair_id": "pair-01",
                "expected_report_id": "report_case_evidence_system",
                "case_spec_sha256": "a" * 64,
            },
            "usage": {
                "recorded": {
                    "billing_usage": {
                        "availability": "exact",
                        "source": "WorkBuddy task UI",
                        "workbuddy_points": 211,
                    }
                }
            },
        }
        ir = copy.deepcopy(direct)
        ir["route"] = "ir"
        ir["usage"]["recorded"]["billing_usage"]["workbuddy_points"] = 19
        result = COMPARE.compare(direct, ir)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["workbuddy_points"]["difference"], 192)
        self.assertEqual(result["workbuddy_points"]["reduction_percent"], 91.0)
        self.assertIn("not model tokens", result["workbuddy_points"]["interpretation"])

    def test_comparison_rejects_cross_case_or_cross_pair_results(self) -> None:
        base = {
            "route": "direct",
            "status": "PASS",
            "case": {
                "case_id": "case-a",
                "pair_id": "pair-01",
                "expected_report_id": "report_case_evidence_system",
                "case_spec_sha256": "a" * 64,
            },
            "usage": {"recorded": {"billing_usage": {"availability": "unavailable"}}},
        }
        ir = copy.deepcopy(base)
        ir["route"] = "ir"
        ir["case"]["pair_id"] = "pair-02"
        result = COMPARE.compare(base, ir)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["pair_integrity"]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
