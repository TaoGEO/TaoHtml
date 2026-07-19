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

from tests.test_report_ir_v1 import WORKFLOW_PROFILE_IDS, bound_ir, valid_ir


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skill" / "taohtml"
VALIDATOR_PATH = SKILL_DIR / "scripts" / "validate_project_handoff.py"
SCHEMA_PATH = SKILL_DIR / "references" / "project-handoff.schema.json"
REFERENCE_PATH = SKILL_DIR / "references" / "project-handoff-schema.md"
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "project-handoff"


def load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "taohtml_project_handoff_validator", VALIDATOR_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator()


def load_compiler() -> ModuleType:
    path = SKILL_DIR / "scripts" / "compile_report_ir.py"
    spec = importlib.util.spec_from_file_location("taohtml_report_ir_compiler", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER = load_compiler()


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def refresh_manifest_hash(payload: dict[str, object], root: Path) -> None:
    payload["current_build"]["build_manifest_ref"]["sha256"] = sha256(  # type: ignore[index]
        root / "build" / "build-manifest.json"
    )


def artifact(payload: dict[str, object], artifact_id: str) -> dict[str, object]:
    return next(
        item
        for item in payload["artifacts"]  # type: ignore[index]
        if item["artifact_id"] == artifact_id
    )


def qa_record(payload: dict[str, object], check_type: str) -> dict[str, object]:
    return next(
        item
        for item in payload["qa_records"]  # type: ignore[index]
        if item["check_type"] == check_type
    )


def meaning_changing_ready_payload() -> dict[str, object]:
    payload = load_fixture("meaning-preserving-ready.json")
    payload["task"] = {
        "task_intent": "continue_existing",
        "content_route": "existing_ppt_html",
        "change_class": "meaning_changing",
        "requested_delta": {
            "summary": "Rebuild one affected conclusion from the inspected source.",
            "affected_source_refs": ["source-primary"],
            "affected_decision_ids": ["decision-core-conclusion"],
            "preserves_meaning": False,
            "interpretation_basis": "source_reinspection",
            "confirmation_ref": None,
        },
    }
    payload["source_ledger"].append(  # type: ignore[union-attr]
        {
            "source_id": "source-primary",
            "identity": {
                "kind": "portable_path",
                "value": "materials/source.txt",
                "sha256": sha256(FIXTURE_ROOT / "materials" / "source.txt"),
            },
            "source_binding": "task_instruction_explicit",
            "source_role": "original_customer_material",
            "availability_status": "workspace_readable",
            "evidence_verification": "unverified",
            "inspection": {
                "coverage": "complete",
                "observed_at": "2026-07-17T12:00:00Z",
                "observation_basis": "The exact affected source was reinspected.",
            },
            "supports": [
                {"claim_id": "claim-rebuilt", "support_kind": "source_fact"}
            ],
            "limits": ["The source remains independently unverified."],
        }
    )
    payload["decisions"]["still_valid"].append(  # type: ignore[index,union-attr]
        {
            "decision_id": "decision-core-conclusion",
            "category": "core_conclusion",
            "value": "The affected conclusion is rebuilt in the complete current brief.",
            "basis_source_refs": ["source-primary"],
        }
    )
    design_brief = payload["confirmations"]["design_brief"]  # type: ignore[index]
    design_brief["scope"] = "current_snapshot"
    authorization_hash = sha256(FIXTURE_ROOT / "artifacts" / "authorization.json")
    payload["artifacts"].append(  # type: ignore[union-attr]
        {
            "artifact_id": "production-authorization-record",
            "kind": "authorization_record",
            "role": "gate_record",
            "availability_status": "workspace_readable",
            "locator": {
                "kind": "portable_path",
                "value": "artifacts/authorization.json",
            },
            "sha256": authorization_hash,
            "baseline_identity": None,
            "versions": {
                "runtime_version": None,
                "editor_version": None,
                "theme_version": None,
                "compiler_version": None,
            },
            "report_ir_ref": None,
        }
    )
    payload["confirmations"]["production_authorization"] = {  # type: ignore[index]
        "status": "authorized",
        "scope": "current_snapshot",
        "record_artifact_ref": "production-authorization-record",
        "record_sha256": authorization_hash,
        "target_artifact_ref": "current-html",
        "target_artifact_sha256": artifact(payload, "current-html")["sha256"],
        "design_brief_sha256": design_brief["artifact_sha256"],
        "authorized_actions": [
            "formal-html",
            "browser-qa",
            "deliver-formal-html",
        ],
    }
    return payload


def new_build_ready_payload() -> dict[str, object]:
    payload = meaning_changing_ready_payload()
    payload["task"] = {
        "task_intent": "new_build",
        "content_route": "existing_ppt_html",
        "change_class": "not_applicable",
        "requested_delta": {
            "summary": "Build the current report from the confirmed brief.",
            "affected_source_refs": [],
            "affected_decision_ids": [],
            "preserves_meaning": None,
            "interpretation_basis": "not_applicable",
            "confirmation_ref": None,
        },
    }
    return payload


def project_theme_ready_payload() -> dict[str, object]:
    payload = meaning_changing_ready_payload()
    theme_hash = sha256(FIXTURE_ROOT / "artifacts" / "project-theme.json")
    vi_hash = sha256(FIXTURE_ROOT / "artifacts" / "vi-board.md")
    payload["artifacts"].extend(  # type: ignore[union-attr]
        [
            {
                "artifact_id": "project-theme-current",
                "kind": "project_theme",
                "role": "supporting",
                "availability_status": "workspace_readable",
                "locator": {
                    "kind": "portable_path",
                    "value": "artifacts/project-theme.json",
                },
                "sha256": theme_hash,
                "baseline_identity": None,
                "versions": {
                    "runtime_version": None,
                    "editor_version": None,
                    "theme_version": "project-theme-v1",
                    "compiler_version": None,
                },
                "report_ir_ref": None,
            },
            {
                "artifact_id": "vi-current",
                "kind": "vi_board",
                "role": "gate_record",
                "availability_status": "workspace_readable",
                "locator": {
                    "kind": "portable_path",
                    "value": "artifacts/vi-board.md",
                },
                "sha256": vi_hash,
                "baseline_identity": None,
                "versions": {
                    "runtime_version": None,
                    "editor_version": None,
                    "theme_version": None,
                    "compiler_version": None,
                },
                "report_ir_ref": None,
            },
        ]
    )
    payload["design_binding"] = {
        "kind": "project_theme",
        "built_in_theme": None,
        "project_theme": {
            "artifact_ref": "project-theme-current",
            "theme_version": "project-theme-v1",
            "theme_sha256": theme_hash,
        },
        "enterprise_profile": None,
    }
    payload["confirmations"]["vi"] = {  # type: ignore[index]
        "status": "confirmed",
        "scope": "current_snapshot",
        "artifact_ref": "vi-current",
        "artifact_sha256": vi_hash,
        "confirmation_ref": "conversation://current/vi-confirmation",
    }
    artifact(payload, "current-html")["versions"][  # type: ignore[index]
        "theme_version"
    ] = "project-theme-v1"
    return payload


def compiled_handoff_payload(
    root: Path,
    primary_profile_id: str | None,
) -> tuple[dict[str, object], dict[str, object]]:
    shutil.copytree(FIXTURE_ROOT, root, dirs_exist_ok=True)
    source_bytes = b"segment,value\nenterprise,28\nother,7\n"
    source_path = root / "materials" / "growth.csv"
    source_path.write_bytes(source_bytes)
    ir = valid_ir(hashlib.sha256(source_bytes).hexdigest())
    if primary_profile_id is not None:
        ir = bound_ir(ir, primary_profile_id)
    manifest = COMPILER.compile_ir(
        ir,
        root,
        root / "build",
        report_ir_ref="report.ir.json",
    )

    payload = load_fixture("meaning-preserving-ready.json")
    payload["schema_version"] = "1.1"
    current = artifact(payload, "current-html")
    current["locator"] = {
        "kind": "portable_path",
        "value": "build/index.html",
    }
    current["sha256"] = manifest["outputs"]["html"]["sha256"]  # type: ignore[index]
    current["versions"]["compiler_version"] = manifest["compiler_version"]  # type: ignore[index]
    current["report_ir_ref"] = {
        "ref": {
            "kind": "portable_path",
            "value": "build/report.ir.normalized.json",
        },
        "sha256": manifest["outputs"]["normalized_ir"]["sha256"],  # type: ignore[index]
    }
    current_source = next(
        item
        for item in payload["source_ledger"]  # type: ignore[index]
        if item["source_role"] == "current_artifact"
    )
    current_source["identity"]["value"] = "build/index.html"
    current_source["identity"]["sha256"] = current["sha256"]
    for record in payload["qa_records"]:  # type: ignore[index]
        record["status"] = "not_run"
        record["artifact_sha256"] = current["sha256"]
        record["record_artifact_ref"] = None
        record["record_sha256"] = None
    workflow_profile = manifest["workflow_profile"]
    payload["current_build"] = {
        "artifact_ref": current["artifact_id"],
        "build_manifest_ref": {
            "ref": {
                "kind": "portable_path",
                "value": "build/build-manifest.json",
            },
            "sha256": sha256(root / "build" / "build-manifest.json"),
        },
        "workflow_profile": {
            "binding_state": workflow_profile["binding_state"],
            "primary_profile_id": workflow_profile["primary_profile_id"],
            "definition_version": workflow_profile["definition_version"],
            "binding_sha256": workflow_profile["binding_sha256"],
        },
    }
    return payload, manifest


class ProjectHandoffValidatorTests(unittest.TestCase):
    def evaluate(
        self,
        payload: dict[str, object],
        artifact_root: Path = FIXTURE_ROOT,
    ) -> dict[str, object]:
        return VALIDATOR.evaluate_handoff(payload, artifact_root)

    def test_read_only_missing_source_is_valid_but_never_deliverable(self) -> None:
        result = self.evaluate(load_fixture("review-only-missing-source.json"))
        self.assertEqual(
            result["readiness"],
            {
                "schema_valid": True,
                "bindings_valid": True,
                "continuation_ready": True,
                "delivery_ready": False,
            },
        )
        self.assertIn(
            "review_only snapshots never claim delivery readiness",
            result["blocking_reasons"]["delivery_ready"],
        )

    def test_meaning_preserving_exact_baseline_and_current_qa_are_ready(self) -> None:
        result = self.evaluate(load_fixture("meaning-preserving-ready.json"))
        self.assertTrue(all(result["readiness"].values()))
        self.assertEqual(result["qa_execution_claim"], "not_executed_by_validator")
        self.assertFalse(result["audit_metadata_used_for_readiness"])

    def test_meaning_preserving_baseline_hash_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "handoff"
            shutil.copytree(FIXTURE_ROOT, root)
            (root / "artifacts" / "baseline.html").write_text(
                "changed after handoff\n", encoding="utf-8"
            )
            payload = json.loads(
                (root / "meaning-preserving-ready.json").read_text(encoding="utf-8")
            )
            result = self.evaluate(payload, root)
        self.assertTrue(result["readiness"]["schema_valid"])
        self.assertFalse(result["readiness"]["bindings_valid"])
        self.assertFalse(result["readiness"]["continuation_ready"])
        self.assertTrue(
            any(
                "baseline-html" in reason and "hash drift" in reason
                for reason in result["blocking_reasons"]["bindings_valid"]
            )
        )

    def test_meaning_changing_needs_current_brief_and_authorization(self) -> None:
        result = self.evaluate(load_fixture("meaning-changing-missing-gates.json"))
        self.assertTrue(result["readiness"]["schema_valid"])
        self.assertTrue(result["readiness"]["bindings_valid"])
        self.assertFalse(result["readiness"]["continuation_ready"])
        self.assertFalse(result["readiness"]["delivery_ready"])
        blockers = result["blocking_reasons"]["continuation_ready"]
        self.assertIn(
            "complete current design brief is not locally hash-verified", blockers
        )
        self.assertIn("current formal production authorization is missing", blockers)

    def test_meaning_changing_can_reach_delivery_after_independent_current_gates(self) -> None:
        result = self.evaluate(meaning_changing_ready_payload())
        self.assertTrue(all(result["readiness"].values()))

    def test_current_authorization_cannot_target_the_delivered_baseline(self) -> None:
        for label, factory in (
            ("meaning-changing", meaning_changing_ready_payload),
            ("new-build", new_build_ready_payload),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir) / "handoff"
                shutil.copytree(FIXTURE_ROOT, root)
                payload = factory()
                baseline_hash = artifact(payload, "baseline-html")["sha256"]
                authorization = payload["confirmations"]["production_authorization"]  # type: ignore[index]
                authorization["target_artifact_ref"] = "baseline-html"
                authorization["target_artifact_sha256"] = baseline_hash
                structured = {
                    "schema_version": "1.0",
                    "record_type": "production_authorization",
                    "status": "authorized",
                    "target_artifact_ref": "baseline-html",
                    "target_artifact_sha256": baseline_hash,
                    "design_brief_sha256": authorization["design_brief_sha256"],
                    "authorized_actions": authorization["authorized_actions"],
                }
                record_path = root / "artifacts" / "authorization-baseline.json"
                record_path.write_text(
                    json.dumps(structured, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                record_hash = sha256(record_path)
                record_artifact = artifact(payload, "production-authorization-record")
                record_artifact["locator"]["value"] = "artifacts/authorization-baseline.json"  # type: ignore[index]
                record_artifact["sha256"] = record_hash
                authorization["record_sha256"] = record_hash
                result = self.evaluate(payload, root)
            self.assertTrue(result["readiness"]["schema_valid"])
            self.assertFalse(result["readiness"]["bindings_valid"])
            self.assertFalse(result["readiness"]["continuation_ready"])
            self.assertFalse(result["readiness"]["delivery_ready"])
            self.assertIn(
                "current production authorization must bind the exact current artifact id and hash",
                result["blocking_reasons"]["bindings_valid"],
            )

    def test_current_authorization_requires_each_formal_action_boundary(self) -> None:
        cases = (
            (
                "formal-html",
                ["browser-qa", "deliver-formal-html"],
                False,
            ),
            (
                "browser-qa",
                ["formal-html", "deliver-formal-html"],
                True,
            ),
            (
                "deliver-formal-html",
                ["formal-html", "browser-qa"],
                True,
            ),
        )
        for task_label, factory in (
            ("meaning-changing", meaning_changing_ready_payload),
            ("new-build", new_build_ready_payload),
        ):
            for missing_action, actions, continuation_expected in cases:
                with (
                    self.subTest(task=task_label, missing=missing_action),
                    tempfile.TemporaryDirectory() as temp_dir,
                ):
                    root = Path(temp_dir) / "handoff"
                    shutil.copytree(FIXTURE_ROOT, root)
                    payload = factory()
                    authorization = payload["confirmations"][  # type: ignore[index]
                        "production_authorization"
                    ]
                    authorization["authorized_actions"] = actions
                    structured = json.loads(
                        (root / "artifacts" / "authorization.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    structured["authorized_actions"] = actions
                    record_path = root / "artifacts" / f"authorization-without-{missing_action}.json"
                    record_path.write_text(
                        json.dumps(structured, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    record_hash = sha256(record_path)
                    record_artifact = artifact(
                        payload, "production-authorization-record"
                    )
                    record_artifact["locator"][  # type: ignore[index]
                        "value"
                    ] = f"artifacts/{record_path.name}"
                    record_artifact["sha256"] = record_hash
                    authorization["record_sha256"] = record_hash
                    result = self.evaluate(payload, root)
                self.assertTrue(result["readiness"]["schema_valid"])
                self.assertTrue(result["readiness"]["bindings_valid"])
                self.assertEqual(
                    result["readiness"]["continuation_ready"],
                    continuation_expected,
                )
                self.assertFalse(result["readiness"]["delivery_ready"])
                if missing_action == "formal-html":
                    self.assertIn(
                        "current production authorization does not permit formal-html",
                        result["blocking_reasons"]["continuation_ready"],
                    )
                self.assertIn(
                    "current production authorization does not permit QA and delivery",
                    result["blocking_reasons"]["delivery_ready"],
                )

    def test_primary_current_and_baseline_roles_require_html_report_artifacts(self) -> None:
        for artifact_id in ("current-html", "baseline-html"):
            with self.subTest(artifact_id=artifact_id):
                payload = load_fixture("meaning-preserving-ready.json")
                artifact(payload, artifact_id)["kind"] = "qa_record"
                result = self.evaluate(payload)
                self.assertTrue(result["readiness"]["schema_valid"])
                self.assertFalse(result["readiness"]["bindings_valid"])
                self.assertFalse(result["readiness"]["continuation_ready"])
                self.assertFalse(result["readiness"]["delivery_ready"])
                self.assertTrue(
                    any(
                        artifact_id in reason
                        and "primary HTML report artifact" in reason
                        for reason in result["blocking_reasons"]["bindings_valid"]
                    )
                )

    def test_current_brief_must_be_locally_hash_current_for_production_paths(self) -> None:
        for label, factory in (
            ("meaning-changing", meaning_changing_ready_payload),
            ("new-build", new_build_ready_payload),
        ):
            with self.subTest(label=label):
                payload = factory()
                brief_artifact = artifact(payload, "design-brief")
                brief_artifact["availability_status"] = "platform_visible_not_retrieved"
                brief_artifact["locator"] = {
                    "kind": "stable_locator",
                    "value": "artifact://design-brief/current",
                }
                result = self.evaluate(payload)
                self.assertTrue(result["readiness"]["bindings_valid"])
                self.assertFalse(result["readiness"]["continuation_ready"])
                self.assertFalse(result["readiness"]["delivery_ready"])
                self.assertNotIn(
                    "artifacts/design-brief.md", result["verified_local_files"]
                )
                self.assertTrue(
                    any(
                        "design brief" in reason and "locally hash-verified" in reason
                        for reason in result["blocking_reasons"]["continuation_ready"]
                    )
                )

    def test_project_theme_vi_confirmation_must_bind_local_current_vi(self) -> None:
        payload = project_theme_ready_payload()
        vi_artifact = artifact(payload, "vi-current")
        vi_artifact["availability_status"] = "platform_visible_not_retrieved"
        vi_artifact["locator"] = {
            "kind": "stable_locator",
            "value": "artifact://vi/current",
        }
        result = self.evaluate(payload)
        self.assertTrue(result["readiness"]["bindings_valid"])
        self.assertFalse(result["readiness"]["continuation_ready"])
        self.assertFalse(result["readiness"]["delivery_ready"])
        self.assertTrue(
            any(
                "VI confirmation" in reason and "locally hash-verified" in reason
                for reason in result["blocking_reasons"]["continuation_ready"]
            )
        )

    def test_project_theme_version_must_match_current_primary_html(self) -> None:
        matching = project_theme_ready_payload()
        matching_result = self.evaluate(matching)
        self.assertTrue(all(matching_result["readiness"].values()))

        drifted = project_theme_ready_payload()
        artifact(drifted, "current-html")["versions"][  # type: ignore[index]
            "theme_version"
        ] = "different-theme-version"
        drifted_result = self.evaluate(drifted)
        self.assertTrue(drifted_result["readiness"]["schema_valid"])
        self.assertFalse(drifted_result["readiness"]["bindings_valid"])
        self.assertFalse(drifted_result["readiness"]["continuation_ready"])
        self.assertFalse(drifted_result["readiness"]["delivery_ready"])
        self.assertIn(
            "current artifact theme_version does not match the project-theme binding",
            drifted_result["blocking_reasons"]["bindings_valid"],
        )

    def test_source_reinspection_requires_every_affected_source(self) -> None:
        payload = meaning_changing_ready_payload()
        second = copy.deepcopy(payload["source_ledger"][-1])  # type: ignore[index]
        second["source_id"] = "source-not-inspected"
        second["availability_status"] = "handoff_record_only"
        second["inspection"] = {
            "coverage": "not_retrieved",
            "observed_at": None,
            "observation_basis": "Only a prior handoff record is available.",
        }
        payload["source_ledger"].append(second)  # type: ignore[union-attr]
        payload["task"]["requested_delta"]["affected_source_refs"].append(  # type: ignore[index]
            "source-not-inspected"
        )
        result = self.evaluate(payload)
        self.assertTrue(result["readiness"]["bindings_valid"])
        self.assertFalse(result["readiness"]["continuation_ready"])
        self.assertIn(
            "affected source is not inspectable primary/external evidence: source-not-inspected",
            result["blocking_reasons"]["continuation_ready"],
        )

    def test_decision_only_meaning_change_uses_exact_confirmation_without_fake_source(self) -> None:
        payload = meaning_changing_ready_payload()
        delta = payload["task"]["requested_delta"]  # type: ignore[index]
        delta["affected_source_refs"] = []
        delta["interpretation_basis"] = "explicit_user_confirmation"
        delta["confirmation_ref"] = "conversation://exact/structure-change-confirmation"
        result = self.evaluate(payload)
        self.assertTrue(all(result["readiness"].values()))

    def test_enterprise_profile_binding_is_structured_and_matches_handoff(self) -> None:
        def bound_payload(root: Path) -> dict[str, object]:
            payload = load_fixture("meaning-preserving-ready.json")
            binding_path = root / "artifacts" / "profile-use.json"
            payload["design_binding"] = {
                "kind": "enterprise_profile",
                "built_in_theme": None,
                "project_theme": None,
                "enterprise_profile": {
                    "profile_ref": {
                        "kind": "portable_path",
                        "value": "artifacts/profile-use.json",
                    },
                    "profile_id": "portable-profile",
                    "profile_version": 3,
                    "theme_fingerprint": "d" * 64,
                    "binding_sha256": sha256(binding_path),
                },
            }
            return payload

        valid = bound_payload(FIXTURE_ROOT)
        self.assertTrue(all(self.evaluate(valid)["readiness"].values()))

        for label in (
            "random-json",
            "profile-id-drift",
            "version-drift",
            "theme-fingerprint-drift",
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir) / "handoff"
                shutil.copytree(FIXTURE_ROOT, root)
                payload = bound_payload(root)
                if label == "random-json":
                    path = root / "artifacts" / "random-profile.json"
                    path.write_text('{"profile_id": "portable-profile"}\n', encoding="utf-8")
                else:
                    record = json.loads(
                        (root / "artifacts" / "profile-use.json").read_text(encoding="utf-8")
                    )
                    if label == "profile-id-drift":
                        record["profile_id"] = "different-profile"
                        record["theme_home_path"] = (
                            "profiles/different-profile/versions/v3/assets/project-theme"
                        )
                    elif label == "version-drift":
                        record["version"] = 4
                        record["active_version_at_bind"] = 4
                        record["theme_home_path"] = (
                            "profiles/portable-profile/versions/v4/assets/project-theme"
                        )
                    else:
                        record["theme_fingerprint"] = "9" * 64
                    path = root / "artifacts" / f"profile-use-{label}.json"
                    path.write_text(
                        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                enterprise = payload["design_binding"]["enterprise_profile"]  # type: ignore[index]
                enterprise["profile_ref"]["value"] = f"artifacts/{path.name}"
                enterprise["binding_sha256"] = sha256(path)
                result = self.evaluate(payload, root)
            self.assertTrue(result["readiness"]["schema_valid"])
            self.assertFalse(result["readiness"]["bindings_valid"])
            self.assertFalse(result["readiness"]["continuation_ready"])
            self.assertFalse(result["readiness"]["delivery_ready"])

    def test_cli_rejects_duplicate_keys_and_non_finite_numbers(self) -> None:
        original = (FIXTURE_ROOT / "meaning-preserving-ready.json").read_text(
            encoding="utf-8"
        )
        cases = {
            "duplicate": original.replace(
                '  "schema_version": "1.0",',
                '  "schema_version": "1.0",\n  "schema_version": "1.0",',
                1,
            ),
            "NaN": original.replace("\"amount\": 1.25", "\"amount\": NaN", 1),
            "Infinity": original.replace(
                "\"amount\": 1.25", "\"amount\": Infinity", 1
            ),
        }
        for label, text in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                handoff = Path(temp_dir) / "handoff.json"
                handoff.write_text(text, encoding="utf-8")
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(VALIDATOR_PATH),
                        "--handoff",
                        str(handoff),
                        "--artifact-root",
                        str(FIXTURE_ROOT),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                result = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(result["readiness"]["schema_valid"])
            self.assertTrue(result["blocking_reasons"]["schema_valid"])

    def test_secondary_summary_cannot_masquerade_as_original_evidence(self) -> None:
        result = self.evaluate(load_fixture("invalid-secondary-substitution.json"))
        self.assertTrue(result["readiness"]["schema_valid"])
        self.assertFalse(result["readiness"]["bindings_valid"])
        self.assertTrue(
            any(
                "secondary_handoff_summary cannot claim source_fact" in reason
                for reason in result["blocking_reasons"]["bindings_valid"]
            )
        )

    def test_inspected_external_source_may_remain_unverified(self) -> None:
        payload = load_fixture("review-only-missing-source.json")
        payload["source_ledger"] = [
            {
                "source_id": "source-external-unverified",
                "identity": {
                    "kind": "stable_external_locator",
                    "value": "https://example.invalid/evidence-record",
                    "sha256": None,
                },
                "source_binding": "agent_retrieved_external",
                "source_role": "external_public_evidence",
                "availability_status": "external_retrieved_inspected",
                "evidence_verification": "unverified",
                "inspection": {
                    "coverage": "complete",
                    "observed_at": "2026-07-17T11:00:00Z",
                    "observation_basis": "The exact retrieved representation was inspected.",
                },
                "supports": [
                    {"claim_id": "claim-candidate", "support_kind": "source_fact"}
                ],
                "limits": [
                    "Inspection establishes access, not whether the candidate claim is true."
                ],
            }
        ]
        result = self.evaluate(payload)
        self.assertTrue(result["readiness"]["schema_valid"])
        self.assertTrue(result["readiness"]["bindings_valid"])
        self.assertTrue(result["readiness"]["continuation_ready"])

    def test_path_escape_is_rejected_by_the_schema(self) -> None:
        payload = load_fixture("meaning-preserving-ready.json")
        artifact(payload, "current-html")["locator"]["value"] = "../current.html"  # type: ignore[index]
        result = self.evaluate(payload)
        self.assertFalse(result["readiness"]["schema_valid"])
        self.assertFalse(result["readiness"]["bindings_valid"])

    def test_local_absolute_path_is_allowed_only_as_environment_observation(self) -> None:
        observed = self.evaluate(load_fixture("meaning-preserving-ready.json"))
        self.assertTrue(observed["readiness"]["bindings_valid"])

        payload = load_fixture("review-only-missing-source.json")
        payload["source_ledger"][0]["identity"]["value"] = "/local/source.txt"  # type: ignore[index]
        result = self.evaluate(payload)
        self.assertTrue(result["readiness"]["schema_valid"])
        self.assertFalse(result["readiness"]["bindings_valid"])
        self.assertTrue(
            any(
                "cannot use a local absolute path as identity" in reason
                for reason in result["blocking_reasons"]["bindings_valid"]
            )
        )

    def test_symlink_is_rejected_even_when_it_points_inside_the_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "handoff"
            shutil.copytree(FIXTURE_ROOT, root)
            try:
                (root / "artifacts" / "linked-baseline.html").symlink_to(
                    root / "artifacts" / "baseline.html"
                )
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            payload = json.loads(
                (root / "meaning-preserving-ready.json").read_text(encoding="utf-8")
            )
            artifact(payload, "baseline-html")["locator"][
                "value"
            ] = "artifacts/linked-baseline.html"  # type: ignore[index]
            result = self.evaluate(payload, root)
        self.assertTrue(result["readiness"]["schema_valid"])
        self.assertFalse(result["readiness"]["bindings_valid"])
        self.assertTrue(
            any(
                "baseline-html" in reason and "symlinks" in reason
                for reason in result["blocking_reasons"]["bindings_valid"]
            )
        )

    def test_unknown_enum_version_and_extra_field_fail_schema(self) -> None:
        cases: list[tuple[str, dict[str, object]]] = []
        unknown_enum = load_fixture("review-only-missing-source.json")
        unknown_enum["task"]["task_intent"] = "session_resume"  # type: ignore[index]
        cases.append(("unknown enum", unknown_enum))
        unknown_version = load_fixture("review-only-missing-source.json")
        unknown_version["schema_version"] = "9.9"
        cases.append(("unknown version", unknown_version))
        extra_field = load_fixture("review-only-missing-source.json")
        extra_field["company_name"] = "must not be accepted"
        cases.append(("additional field", extra_field))

        for label, payload in cases:
            with self.subTest(label=label):
                result = self.evaluate(payload)
                self.assertFalse(result["readiness"]["schema_valid"])
                self.assertFalse(result["readiness"]["bindings_valid"])

    def test_platform_model_and_cost_do_not_change_readiness(self) -> None:
        original = load_fixture("meaning-preserving-ready.json")
        changed = copy.deepcopy(original)
        changed["audit_metadata"] = {
            "platform": "a-different-audit-platform",
            "model": "a-different-audit-model",
            "cost": {
                "amount": 999.0,
                "currency": "ALT",
                "source": "a different audit source",
            },
            "notes": ["Changed only optional audit and cost metadata."],
        }
        original_result = self.evaluate(original)
        changed_result = self.evaluate(changed)
        self.assertEqual(original_result["readiness"], changed_result["readiness"])
        self.assertEqual(
            original_result["blocking_reasons"], changed_result["blocking_reasons"]
        )
        self.assertNotEqual(
            original_result["handoff_sha256"], changed_result["handoff_sha256"]
        )

    def test_qa_record_bound_to_baseline_does_not_ready_current_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "handoff"
            shutil.copytree(FIXTURE_ROOT, root)
            payload = json.loads(
                (root / "meaning-preserving-ready.json").read_text(encoding="utf-8")
            )
            baseline_hash = artifact(payload, "baseline-html")["sha256"]
            structured = {
                "schema_version": "1.0",
                "record_id": "qa-browser-current",
                "check_type": "browser_qa",
                "status": "passed",
                "artifact_ref": "baseline-html",
                "artifact_sha256": baseline_hash,
                "executed_at": "2026-07-17T12:00:00Z",
                "tool": "taohtml-check-html-deck",
            }
            record_path = root / "records" / "browser-baseline.json"
            record_path.write_text(
                json.dumps(structured, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            record_hash = sha256(record_path)
            record_artifact = artifact(payload, "qa-browser-record")
            record_artifact["locator"]["value"] = "records/browser-baseline.json"  # type: ignore[index]
            record_artifact["sha256"] = record_hash
            record = qa_record(payload, "browser_qa")
            record["artifact_ref"] = "baseline-html"
            record["artifact_sha256"] = baseline_hash
            record["record_sha256"] = record_hash
            result = self.evaluate(payload, root)
        self.assertTrue(result["readiness"]["bindings_valid"])
        self.assertTrue(result["readiness"]["continuation_ready"])
        self.assertFalse(result["readiness"]["delivery_ready"])
        self.assertIn(
            "current artifact lacks passed bound browser_qa record",
            result["blocking_reasons"]["delivery_ready"],
        )

    def test_handoff_v1_0_fixtures_remain_valid_without_profile_inference(self) -> None:
        for fixture in (
            "meaning-preserving-ready.json",
            "review-only-missing-source.json",
            "meaning-changing-missing-gates.json",
        ):
            with self.subTest(fixture=fixture):
                payload = load_fixture(fixture)
                result = self.evaluate(payload)
                self.assertTrue(result["readiness"]["schema_valid"])
                self.assertTrue(result["readiness"]["bindings_valid"])
                self.assertNotIn("current_build", payload)

    def test_handoff_v1_1_direct_html_uses_null_current_build(self) -> None:
        payload = load_fixture("meaning-preserving-ready.json")
        payload["schema_version"] = "1.1"
        payload["current_build"] = None
        result = self.evaluate(payload)
        self.assertTrue(all(result["readiness"].values()))

    def test_handoff_version_conditions_are_explicit_and_fail_closed(self) -> None:
        v1 = load_fixture("meaning-preserving-ready.json")
        v1["current_build"] = None
        self.assertFalse(self.evaluate(v1)["readiness"]["schema_valid"])

        v1_1 = load_fixture("meaning-preserving-ready.json")
        v1_1["schema_version"] = "1.1"
        self.assertFalse(self.evaluate(v1_1)["readiness"]["schema_valid"])

    def test_legacy_unbound_report_ir_build_is_verified_without_profile_inference(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload, _ = compiled_handoff_payload(root, None)
            result = self.evaluate(payload, root)
        self.assertTrue(result["readiness"]["schema_valid"])
        self.assertTrue(result["readiness"]["bindings_valid"])
        self.assertTrue(result["readiness"]["continuation_ready"])
        self.assertFalse(result["readiness"]["delivery_ready"])
        self.assertEqual(
            payload["current_build"]["workflow_profile"],  # type: ignore[index]
            {
                "binding_state": "legacy_unbound",
                "primary_profile_id": None,
                "definition_version": None,
                "binding_sha256": None,
            },
        )

    def test_all_nine_workflow_profiles_bind_the_same_handoff_contract(self) -> None:
        for profile_id in WORKFLOW_PROFILE_IDS:
            with self.subTest(profile_id=profile_id), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                payload, _ = compiled_handoff_payload(root, profile_id)
                result = self.evaluate(payload, root)
                self.assertTrue(result["readiness"]["schema_valid"])
                self.assertTrue(
                    result["readiness"]["bindings_valid"],
                    result["blocking_reasons"]["bindings_valid"],
                )
                self.assertTrue(result["readiness"]["continuation_ready"])
                self.assertFalse(result["readiness"]["delivery_ready"])
                self.assertEqual(
                    payload["current_build"]["workflow_profile"][  # type: ignore[index]
                        "primary_profile_id"
                    ],
                    profile_id,
                )

    def test_handoff_profile_id_version_and_binding_hash_drift_fail_closed(self) -> None:
        mutations = {
            "primary_profile_id": "formal-submission-writing",
            "definition_version": "9.9",
            "binding_sha256": "f" * 64,
        }
        for field, value in mutations.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                payload, _ = compiled_handoff_payload(
                    root, "research-analysis-argumentation"
                )
                payload["current_build"]["workflow_profile"][field] = value  # type: ignore[index]
                result = self.evaluate(payload, root)
                self.assertTrue(result["readiness"]["schema_valid"])
                self.assertFalse(result["readiness"]["bindings_valid"])

    def test_manifest_file_and_internal_build_identity_drift_fail_closed(self) -> None:
        mutations = (
            ("html_hash", lambda item: item["outputs"]["html"].__setitem__("sha256", "a" * 64)),
            ("ir_hash", lambda item: item["outputs"]["normalized_ir"].__setitem__("sha256", "b" * 64)),
            ("compiler", lambda item: item.__setitem__("compiler_version", "other-compiler")),
            (
                "profile_id",
                lambda item: item["workflow_profile"].__setitem__(
                    "primary_profile_id", "formal-submission-writing"
                ),
            ),
            (
                "profile_version",
                lambda item: item["workflow_profile"].__setitem__(
                    "definition_version", "9.9"
                ),
            ),
            (
                "profile_binding_hash",
                lambda item: item["workflow_profile"].__setitem__(
                    "binding_sha256", "f" * 64
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                payload, _ = compiled_handoff_payload(
                    root, "research-analysis-argumentation"
                )
                manifest_path = root / "build" / "build-manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                mutate(manifest)
                write_json(manifest_path, manifest)
                refresh_manifest_hash(payload, root)
                result = self.evaluate(payload, root)
                self.assertTrue(result["readiness"]["schema_valid"])
                self.assertFalse(result["readiness"]["bindings_valid"])

        for relative_path in (
            "build/index.html",
            "build/report.ir.normalized.json",
            "build/build-manifest.json",
        ):
            with self.subTest(file_drift=relative_path), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                payload, _ = compiled_handoff_payload(
                    root, "research-analysis-argumentation"
                )
                with (root / relative_path).open("ab") as handle:
                    handle.write(b" ")
                result = self.evaluate(payload, root)
                self.assertFalse(result["readiness"]["bindings_valid"])
                self.assertTrue(
                    any(
                        "hash drift" in issue
                        for issue in result["blocking_reasons"]["bindings_valid"]
                    )
                )

    def test_handoff_and_manifest_cannot_point_to_another_ir_or_html(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload, _ = compiled_handoff_payload(
                root, "research-analysis-argumentation"
            )
            other_ir = root / "build" / "other.ir.normalized.json"
            other_ir.write_bytes((root / "build" / "report.ir.normalized.json").read_bytes())
            current = artifact(payload, "current-html")
            current["report_ir_ref"]["ref"]["value"] = "build/other.ir.normalized.json"  # type: ignore[index]
            current["report_ir_ref"]["sha256"] = sha256(other_ir)  # type: ignore[index]
            result = self.evaluate(payload, root)
        self.assertFalse(result["readiness"]["bindings_valid"])

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload, _ = compiled_handoff_payload(
                root, "research-analysis-argumentation"
            )
            manifest_path = root / "build" / "build-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["outputs"]["html"]["ref"] = "other.html"
            write_json(manifest_path, manifest)
            refresh_manifest_hash(payload, root)
            result = self.evaluate(payload, root)
        self.assertFalse(result["readiness"]["bindings_valid"])

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload, _ = compiled_handoff_payload(
                root, "research-analysis-argumentation"
            )
            manifest_path = root / "build" / "build-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["outputs"]["normalized_ir"]["ref"] = "other.ir.json"
            write_json(manifest_path, manifest)
            refresh_manifest_hash(payload, root)
            result = self.evaluate(payload, root)
        self.assertFalse(result["readiness"]["bindings_valid"])

    def test_enterprise_and_workflow_profiles_use_independent_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload, _ = compiled_handoff_payload(
                root, "research-analysis-argumentation"
            )
            payload["design_binding"] = {
                "kind": "enterprise_profile",
                "built_in_theme": None,
                "project_theme": None,
                "enterprise_profile": {
                    "profile_ref": {
                        "kind": "portable_path",
                        "value": "artifacts/profile-use.json",
                    },
                    "profile_id": "portable-profile",
                    "profile_version": 3,
                    "theme_fingerprint": "d" * 64,
                    "binding_sha256": sha256(root / "artifacts" / "profile-use.json"),
                },
            }
            result = self.evaluate(payload, root)
        self.assertTrue(
            result["readiness"]["bindings_valid"],
            result["blocking_reasons"]["bindings_valid"],
        )
        self.assertEqual(
            payload["current_build"]["workflow_profile"]["primary_profile_id"],  # type: ignore[index]
            "research-analysis-argumentation",
        )

    def test_current_build_portability_states_cannot_fake_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload, _ = compiled_handoff_payload(
                root, "research-analysis-argumentation"
            )
            payload["current_build"]["build_manifest_ref"]["ref"] = {  # type: ignore[index]
                "kind": "stable_locator",
                "value": "artifact://build-manifest/current",
            }
            result = self.evaluate(payload, root)
        self.assertTrue(result["readiness"]["bindings_valid"])
        self.assertFalse(result["readiness"]["continuation_ready"])
        self.assertFalse(result["readiness"]["delivery_ready"])

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload, _ = compiled_handoff_payload(
                root, "research-analysis-argumentation"
            )
            (root / "build" / "build-manifest.json").unlink()
            result = self.evaluate(payload, root)
        self.assertFalse(result["readiness"]["bindings_valid"])

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload, _ = compiled_handoff_payload(
                root, "research-analysis-argumentation"
            )
            artifact(payload, "current-html")["availability_status"] = "handoff_record_only"
            result = self.evaluate(payload, root)
        self.assertTrue(result["readiness"]["bindings_valid"])
        self.assertFalse(result["readiness"]["continuation_ready"])

    def test_profile_binding_does_not_execute_qa_or_grant_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload, _ = compiled_handoff_payload(
                root, "research-analysis-argumentation"
            )
            result = self.evaluate(payload, root)
        self.assertEqual(result["qa_execution_claim"], "not_executed_by_validator")
        self.assertTrue(result["readiness"]["continuation_ready"])
        self.assertFalse(result["readiness"]["delivery_ready"])

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload, _ = compiled_handoff_payload(
                root, "research-analysis-argumentation"
            )
            payload["task"] = {
                "task_intent": "new_build",
                "content_route": "existing_ppt_html",
                "change_class": "not_applicable",
                "requested_delta": {
                    "summary": "Build after independent gates are satisfied.",
                    "affected_source_refs": [],
                    "affected_decision_ids": [],
                    "preserves_meaning": None,
                    "interpretation_basis": "not_applicable",
                    "confirmation_ref": None,
                },
            }
            result = self.evaluate(payload, root)
        self.assertTrue(result["readiness"]["bindings_valid"])
        self.assertFalse(result["readiness"]["continuation_ready"])
        self.assertTrue(
            any(
                "production authorization" in reason
                for reason in result["blocking_reasons"]["continuation_ready"]
            )
        )

    def test_cli_exit_codes_follow_the_requested_layer(self) -> None:
        ready = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR_PATH),
                "--handoff",
                str(FIXTURE_ROOT / "meaning-preserving-ready.json"),
                "--artifact-root",
                str(FIXTURE_ROOT),
                "--require",
                "delivery_ready",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        review = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR_PATH),
                "--handoff",
                str(FIXTURE_ROOT / "review-only-missing-source.json"),
                "--artifact-root",
                str(FIXTURE_ROOT),
                "--require",
                "delivery_ready",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(ready.returncode, 0, ready.stdout + ready.stderr)
        self.assertEqual(review.returncode, 1, review.stdout + review.stderr)
        self.assertTrue(json.loads(ready.stdout)["readiness"]["delivery_ready"])
        self.assertFalse(json.loads(review.stdout)["readiness"]["delivery_ready"])

    def test_schema_reference_and_skill_route_are_present(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["properties"]["schema_version"],
            {"enum": ["1.0", "1.1"]},
        )
        self.assertEqual(schema["$id"], "urn:taohtml:project-handoff:1.1")
        self.assertIn("current_build", schema["properties"])
        self.assertFalse(schema["additionalProperties"])
        self.assertTrue(REFERENCE_PATH.is_file())
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        handoff = (SKILL_DIR / "references" / "project-handoff.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("references/project-handoff-schema.md", skill)
        self.assertIn("scripts/validate_project_handoff.py", skill)
        self.assertIn("project-handoff.schema.json", handoff)
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("tests/fixtures/project-handoff/** text eol=lf", attributes)


if __name__ == "__main__":
    unittest.main()
