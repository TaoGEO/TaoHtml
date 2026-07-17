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


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        self.assertEqual(schema["properties"]["schema_version"], {"const": "1.0"})
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
