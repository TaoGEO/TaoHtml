from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

from tests.test_report_ir_v1 import bound_ir, valid_ir
from tests.test_project_handoff_validator import new_build_ready_payload


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skill" / "taohtml"
SCRIPT_PATH = SKILL_DIR / "scripts" / "orchestrate_report_ir_pilot.py"
REFERENCE_PATH = SKILL_DIR / "references" / "report-ir-pilot-workflow.md"
HANDOFF_FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "project-handoff"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "taohtml_report_ir_pilot_workflow", SCRIPT_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WORKFLOW = load_script()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate(
    status: str,
    artifact_path: str | None = None,
    artifact_sha256: str | None = None,
    confirmation_ref: str | None = None,
) -> dict[str, str | None]:
    return {
        "status": status,
        "artifact_path": artifact_path,
        "artifact_sha256": artifact_sha256,
        "confirmation_ref": confirmation_ref,
    }


def design_brief_gate(
    status: str,
    artifact_path: str | None = None,
    artifact_sha256: str | None = None,
    confirmation_ref: str | None = None,
    design_decisions_sha256: str | None = None,
) -> dict[str, str | None]:
    return {
        **gate(status, artifact_path, artifact_sha256, confirmation_ref),
        "design_decisions_sha256": design_decisions_sha256,
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


class ReportIrPilotWorkflowTests(unittest.TestCase):
    task_id = "pilot-task-one"

    def _project(
        self,
        root: Path,
        *,
        brief_confirmed: bool = True,
        legacy_ir: bool = False,
    ) -> None:
        materials = root / "materials"
        materials.mkdir(parents=True, exist_ok=True)
        source = materials / "growth.csv"
        source.write_bytes(b"segment,value\nenterprise,28\nother,7\n")

        brief = root / "brief" / "design-brief.md"
        brief.parent.mkdir(parents=True)
        brief.write_text("# Confirmed report design brief\n", encoding="utf-8")
        built_in_theme = {
            "theme_id": "rigorous-consulting-report",
            "selection_status": "user_selected",
            "decision_ref": "conversation://pilot/theme-selection",
        }
        motion_density = {
            "density": "moderate",
            "selection_status": "user_selected",
            "decision_ref": "conversation://pilot/motion-selection",
        }
        brief_gate = (
            design_brief_gate(
                "confirmed",
                "brief/design-brief.md",
                sha256(brief),
                "conversation://pilot/brief-confirmation",
                WORKFLOW.production_authorization.design_decisions_sha256(
                    built_in_theme,
                    motion_density,
                ),
            )
            if brief_confirmed
            else design_brief_gate("pending", "brief/design-brief.md")
        )
        state = {
            "schema_version": "1.3",
            "task_id": self.task_id,
            "route": "idea_only",
            "visual_route": "built_in",
            "material_summary": gate("not_required"),
            "reference_vi": gate("not_required"),
            "profile_use": {
                "status": "not_required",
                "artifact_path": None,
                "artifact_sha256": None,
            },
            "project_theme_compiled": False,
            "built_in_theme": built_in_theme,
            "motion_density": motion_density,
            "design_brief": brief_gate,
        }
        write_json(root / "gates" / "production-state.json", state)
        write_json(
            root / "gates" / "report-ir-pilot-authorization.json",
            {
                "schema_version": "1.0",
                "authorization_type": "report_ir_engineering_pilot",
                "status": "authorized",
                "scope": "project",
                "task_id": self.task_id,
                "route": "report_ir_pilot",
                "authorization_ref": "engineering://report-ir-pilot/task-one",
            },
        )
        ir = valid_ir(sha256(source))
        if not legacy_ir:
            ir = bound_ir(
                ir,
                "research-analysis-argumentation",
                selection_basis="已确认目标是形成证据、方法与推理可检查的专业结论。",
            )
        ir["traceability"]["design_brief_ref"] = "brief/design-brief.md"
        ir["traceability"]["design_brief_sha256"] = sha256(brief)
        write_json(root / "report-ir.json", ir)

    def _command(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--artifact-root",
                str(root),
                "--status-output",
                "records/report-ir-pilot-status.json",
                *extra,
            ],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )

    @staticmethod
    def _pilot_args() -> tuple[str, ...]:
        return (
            "--pilot-authorization",
            "gates/report-ir-pilot-authorization.json",
            "--production-state",
            "gates/production-state.json",
            "--report-ir",
            "report-ir.json",
            "--output-dir",
            "build",
        )

    def test_direct_route_is_default_and_does_not_create_or_read_ir(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            result = self._command(root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            status = json.loads(
                (root / "records" / "report-ir-pilot-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["route"], "direct_html")
            self.assertEqual(status["status"], "direct_html_unchanged")
            self.assertEqual(
                status["fallback_policy"], "ordinary_direct_html_route_unchanged"
            )
            self.assertEqual(status["report_ir_validation"]["status"], "not_executed")
            self.assertFalse((root / "build").exists())

    def test_pilot_only_inputs_without_authorization_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            result = self._command(root, "--report-ir", "report-ir.json")
            self.assertEqual(result.returncode, 1)
            status = json.loads(
                (root / "records" / "report-ir-pilot-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["route"], "direct_html")
            self.assertEqual(status["status"], "blocked")
            self.assertEqual(
                status["diagnostics"][0]["code"], "pilot_authorization_required"
            )
            self.assertFalse((root / "build").exists())

    def test_confirmed_brief_gate_blocks_pilot_before_validation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root, brief_confirmed=False)
            result = self._command(root, *self._pilot_args())
            self.assertEqual(result.returncode, 1)
            status = json.loads(
                (root / "records" / "report-ir-pilot-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["route"], "report_ir_pilot")
            self.assertEqual(status["status"], "blocked")
            self.assertEqual(
                status["diagnostics"][0]["code"], "formal_html_not_authorized"
            )
            self.assertEqual(
                status["fallback_policy"], "forbidden_after_pilot_selection"
            )
            self.assertEqual(status["report_ir_validation"]["status"], "not_executed")
            self.assertFalse((root / "build").exists())

    def test_authorized_pilot_compiles_and_records_not_executed_gates(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            result = self._command(root, *self._pilot_args())
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            status = json.loads(
                (root / "records" / "report-ir-pilot-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["status"], "compiled_pending_qa_handoff")
            self.assertTrue(status["production_authorization"]["allowed"])
            self.assertEqual(
                status["production_authorization"]["built_in_theme"]["theme_id"],
                "rigorous-consulting-report",
            )
            self.assertEqual(
                status["production_authorization"]["motion_density"]["density"],
                "moderate",
            )
            self.assertEqual(
                status["production_authorization"]["design_decisions_sha256"],
                WORKFLOW.production_authorization.design_decisions_sha256(
                    status["production_authorization"]["built_in_theme"],
                    status["production_authorization"]["motion_density"],
                ),
            )
            for field in (
                "schema_valid",
                "references_valid",
                "semantics_valid",
                "compiler_ready",
            ):
                self.assertTrue(status["report_ir_validation"][field], field)
            self.assertEqual(status["compiler"]["status"], "compiled")
            self.assertEqual(
                status["report_ir_validation"]["workflow_profile"]["binding_state"],
                "bound",
            )
            self.assertEqual(
                status["compiler"]["workflow_profile"]["primary_profile_id"],
                "research-analysis-argumentation",
            )
            self.assertEqual(
                status["compiler"]["compiler_invocation"],
                "local_compile_report_ir.compile_ir",
            )
            self.assertEqual(
                status["compiler"]["manifest_sha256"],
                sha256(root / "build" / "build-manifest.json"),
            )
            self.assertEqual(status["html_qa"]["status"], "not_executed")
            self.assertEqual(status["project_handoff"]["status"], "not_executed")
            self.assertEqual(
                status["html_qa"]["execution_claim"],
                "not_executed_by_orchestrator",
            )
            for name in (
                "index.html",
                "source-map.json",
                "report.ir.normalized.json",
                "build-manifest.json",
            ):
                self.assertTrue((root / "build" / name).is_file(), name)

    def test_authorized_legacy_v1_0_pilot_remains_compilable_without_inference(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root, legacy_ir=True)
            result = self._command(root, *self._pilot_args())
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            status = json.loads(
                (root / "records" / "report-ir-pilot-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["status"], "compiled_pending_qa_handoff")
            self.assertEqual(
                status["report_ir_validation"]["workflow_profile"]["binding_state"],
                "legacy_unbound",
            )
            self.assertIsNone(
                status["compiler"]["workflow_profile"]["primary_profile_id"]
            )

    def test_invalid_ir_stays_on_pilot_and_never_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            path = root / "report-ir.json"
            ir = json.loads(path.read_text(encoding="utf-8"))
            ir["traceability"]["design_brief_confirmation"] = (
                "reconfirmation_required"
            )
            write_json(path, ir)
            result = self._command(root, *self._pilot_args())
            self.assertEqual(result.returncode, 1)
            status = json.loads(
                (root / "records" / "report-ir-pilot-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["route"], "report_ir_pilot")
            self.assertEqual(status["status"], "blocked")
            self.assertEqual(
                status["fallback_policy"], "forbidden_after_pilot_selection"
            )
            self.assertEqual(
                status["diagnostics"][0]["stage"], "report_ir_validation"
            )
            self.assertFalse((root / "build").exists())

    def test_report_ir_must_bind_the_exact_current_brief_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            path = root / "report-ir.json"
            ir = json.loads(path.read_text(encoding="utf-8"))
            ir["traceability"]["design_brief_sha256"] = "0" * 64
            write_json(path, ir)
            result = self._command(root, *self._pilot_args())
            self.assertEqual(result.returncode, 1)
            status = json.loads(
                (root / "records" / "report-ir-pilot-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["route"], "report_ir_pilot")
            self.assertEqual(
                status["report_ir_validation"]["status"],
                "binding_or_input_invalid",
            )
            self.assertIn("brief hash", status["diagnostics"][0]["message"])
            self.assertFalse((root / "build").exists())

    def test_report_ir_must_match_authorized_built_in_theme(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            path = root / "report-ir.json"
            ir = json.loads(path.read_text(encoding="utf-8"))
            ir["build_binding"]["theme"]["ref"] = "corporate-annual-report"
            write_json(path, ir)
            result = self._command(root, *self._pilot_args())
            self.assertEqual(result.returncode, 1)
            status = json.loads(
                (root / "records" / "report-ir-pilot-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["diagnostics"][0]["code"], "report_ir_invalid")
            self.assertIn(
                "production-state decision", status["diagnostics"][0]["message"]
            )
            self.assertFalse((root / "build").exists())

    def test_report_ir_must_match_authorized_motion_density(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            path = root / "report-ir.json"
            ir = json.loads(path.read_text(encoding="utf-8"))
            ir["projection"]["motion_density"] = "rich"
            write_json(path, ir)
            result = self._command(root, *self._pilot_args())
            self.assertEqual(result.returncode, 1)
            status = json.loads(
                (root / "records" / "report-ir-pilot-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["diagnostics"][0]["code"], "report_ir_invalid")
            self.assertIn(
                "motion_density", status["diagnostics"][0]["message"]
            )
            self.assertFalse((root / "build").exists())

    def test_handoff_validator_failure_is_recorded_after_compile(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            write_json(root / "project-handoff.json", {})
            result = self._command(
                root, *self._pilot_args(), "--handoff", "project-handoff.json"
            )
            self.assertEqual(result.returncode, 1)
            status = json.loads(
                (root / "records" / "report-ir-pilot-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["compiler"]["status"], "compiled")
            self.assertFalse(status["project_handoff"]["readiness"]["schema_valid"])
            self.assertEqual(
                status["project_handoff"]["qa_execution_claim"],
                "not_executed_by_validator",
            )
            self.assertEqual(
                status["diagnostics"][0]["code"],
                "project_handoff_bindings_invalid",
            )
            self.assertEqual(
                status["fallback_policy"], "forbidden_after_pilot_selection"
            )

    def test_ready_handoff_binds_compiled_html_ir_and_current_brief(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            shutil.copytree(HANDOFF_FIXTURE_ROOT, root, dirs_exist_ok=True)
            self._project(root)
            first = self._command(root, *self._pilot_args())
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            manifest = json.loads(
                (root / "build" / "build-manifest.json").read_text(encoding="utf-8")
            )
            manifest_hash = sha256(root / "build" / "build-manifest.json")
            html_hash = manifest["outputs"]["html"]["sha256"]
            normalized_hash = manifest["outputs"]["normalized_ir"]["sha256"]
            brief_hash = sha256(root / "brief" / "design-brief.md")

            payload = new_build_ready_payload()
            payload["schema_version"] = "1.1"
            current = next(
                item
                for item in payload["artifacts"]
                if item["artifact_id"] == "current-html"
            )
            current["locator"] = {
                "kind": "portable_path",
                "value": "build/index.html",
            }
            current["sha256"] = html_hash
            current["versions"]["compiler_version"] = manifest["compiler_version"]
            current["report_ir_ref"] = {
                "ref": {
                    "kind": "portable_path",
                    "value": "build/report.ir.normalized.json",
                },
                "sha256": normalized_hash,
            }
            current_source = next(
                item
                for item in payload["source_ledger"]
                if item["source_role"] == "current_artifact"
            )
            current_source["identity"]["value"] = "build/index.html"
            current_source["identity"]["sha256"] = html_hash
            profile = manifest["workflow_profile"]
            payload["current_build"] = {
                "artifact_ref": "current-html",
                "build_manifest_ref": {
                    "ref": {
                        "kind": "portable_path",
                        "value": "build/build-manifest.json",
                    },
                    "sha256": manifest_hash,
                },
                "workflow_profile": {
                    "binding_state": profile["binding_state"],
                    "primary_profile_id": profile["primary_profile_id"],
                    "definition_version": profile["definition_version"],
                    "binding_sha256": profile["binding_sha256"],
                },
            }

            copied_brief = root / "artifacts" / "design-brief.md"
            copied_brief.write_bytes((root / "brief" / "design-brief.md").read_bytes())
            brief_artifact = next(
                item
                for item in payload["artifacts"]
                if item["artifact_id"] == "design-brief"
            )
            brief_artifact["sha256"] = brief_hash
            payload["confirmations"]["design_brief"]["artifact_sha256"] = brief_hash

            for qa in payload["qa_records"]:
                qa["artifact_sha256"] = html_hash
                record_artifact = next(
                    item
                    for item in payload["artifacts"]
                    if item["artifact_id"] == qa["record_artifact_ref"]
                )
                record_path = root / record_artifact["locator"]["value"]
                record = json.loads(record_path.read_text(encoding="utf-8"))
                record["artifact_sha256"] = html_hash
                write_json(record_path, record)
                record_hash = sha256(record_path)
                record_artifact["sha256"] = record_hash
                qa["record_sha256"] = record_hash

            authorization = payload["confirmations"]["production_authorization"]
            authorization["target_artifact_sha256"] = html_hash
            authorization["design_brief_sha256"] = brief_hash
            authorization_path = root / "artifacts" / "authorization.json"
            authorization_record = json.loads(
                authorization_path.read_text(encoding="utf-8")
            )
            authorization_record["target_artifact_sha256"] = html_hash
            authorization_record["design_brief_sha256"] = brief_hash
            write_json(authorization_path, authorization_record)
            authorization_hash = sha256(authorization_path)
            authorization["record_sha256"] = authorization_hash
            authorization_artifact = next(
                item
                for item in payload["artifacts"]
                if item["artifact_id"] == authorization["record_artifact_ref"]
            )
            authorization_artifact["sha256"] = authorization_hash

            write_json(root / "project-handoff.json", payload)
            result = self._command(
                root, *self._pilot_args(), "--handoff", "project-handoff.json"
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            status = json.loads(
                (root / "records" / "report-ir-pilot-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["status"], "delivery_ready_recorded")
            self.assertEqual(
                status["project_handoff"]["readiness"],
                {
                    "schema_valid": True,
                    "bindings_valid": True,
                    "continuation_ready": True,
                    "delivery_ready": True,
                },
            )
            self.assertTrue(status["project_handoff"]["pilot_build_binding_valid"])
            self.assertEqual(
                status["html_qa"]["execution_claim"],
                "not_executed_by_orchestrator",
            )
            self.assertEqual(
                status["project_handoff"]["qa_execution_claim"],
                "not_executed_by_validator",
            )

    def test_handoff_binding_requires_exact_html_and_normalized_ir(self) -> None:
        workflow_profile = {
            "binding_state": "bound",
            "primary_profile_id": "research-analysis-argumentation",
            "definition_version": "2.0",
            "binding_sha256": "c" * 64,
        }
        handoff = {
            "schema_version": "1.1",
            "confirmations": {
                "design_brief": {
                    "status": "confirmed",
                    "artifact_sha256": "d" * 64,
                }
            },
            "artifacts": [
                {
                    "artifact_id": "current-html",
                    "role": "current",
                    "locator": {"kind": "portable_path", "value": "build/index.html"},
                    "sha256": "a" * 64,
                    "versions": {"compiler_version": "0.1.0-dev"},
                    "report_ir_ref": {
                        "ref": {
                            "kind": "portable_path",
                            "value": "build/report.ir.normalized.json",
                        },
                        "sha256": "b" * 64,
                    },
                }
            ],
            "current_build": {
                "artifact_ref": "current-html",
                "build_manifest_ref": {
                    "ref": {
                        "kind": "portable_path",
                        "value": "build/build-manifest.json",
                    },
                    "sha256": "e" * 64,
                },
                "workflow_profile": workflow_profile,
            },
        }
        self.assertEqual(
            WORKFLOW._handoff_binding_issues(
                handoff,
                html_ref="build/index.html",
                html_sha256="a" * 64,
                normalized_ir_ref="build/report.ir.normalized.json",
                normalized_ir_sha256="b" * 64,
                manifest_ref="build/build-manifest.json",
                manifest_sha256="e" * 64,
                compiler_version="0.1.0-dev",
                workflow_profile={
                    **workflow_profile,
                    "binding_contract_version": "1.1",
                    "selection_basis": "confirmed basis",
                    "capability_overlays": [],
                },
                design_brief_sha256="d" * 64,
            ),
            [],
        )
        drifted = copy.deepcopy(handoff)
        drifted["artifacts"][0]["report_ir_ref"]["sha256"] = "c" * 64
        issues = WORKFLOW._handoff_binding_issues(
            drifted,
            html_ref="build/index.html",
            html_sha256="a" * 64,
            normalized_ir_ref="build/report.ir.normalized.json",
            normalized_ir_sha256="b" * 64,
            manifest_ref="build/build-manifest.json",
            manifest_sha256="e" * 64,
            compiler_version="0.1.0-dev",
            workflow_profile={
                **workflow_profile,
                "binding_contract_version": "1.1",
                "selection_basis": "confirmed basis",
                "capability_overlays": [],
            },
            design_brief_sha256="d" * 64,
        )
        self.assertIn("normalized Report IR", issues[0])

        legacy = copy.deepcopy(handoff)
        legacy["schema_version"] = "1.0"
        legacy.pop("current_build")
        issues = WORKFLOW._handoff_binding_issues(
            legacy,
            html_ref="build/index.html",
            html_sha256="a" * 64,
            normalized_ir_ref="build/report.ir.normalized.json",
            normalized_ir_sha256="b" * 64,
            manifest_ref="build/build-manifest.json",
            manifest_sha256="e" * 64,
            compiler_version="0.1.0-dev",
            workflow_profile={
                **workflow_profile,
                "binding_contract_version": "1.1",
                "selection_basis": "confirmed basis",
                "capability_overlays": [],
            },
            design_brief_sha256="d" * 64,
        )
        self.assertTrue(any("schema_version 1.1" in issue for issue in issues))
        self.assertTrue(any("current_build" in issue for issue in issues))

    def test_skill_routes_pilot_details_to_one_direct_reference(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        reference = REFERENCE_PATH.read_text(encoding="utf-8")
        self.assertIn("references/report-ir-pilot-workflow.md", skill)
        self.assertIn("不要询问“是否使用 IR”", reference)
        self.assertIn("禁止回退 direct HTML", reference)
        self.assertIn("客户未明确\n缩小范围时先完整展示四套", reference)
        self.assertIn("not_executed_by_orchestrator", reference)
        self.assertIn("not_executed_by_validator", reference)


if __name__ == "__main__":
    unittest.main()
