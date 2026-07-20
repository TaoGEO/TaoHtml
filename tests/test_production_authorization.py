from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = (
    ROOT / "skill" / "taohtml" / "scripts" / "check_production_authorization.py"
)


def load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "taohtml_production_authorization", CHECKER_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECKER = load_checker()


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


def confirmed(root: Path, filename: str, content: str) -> dict[str, str | None]:
    path = root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return gate(
        "confirmed",
        filename,
        sha256(path),
        f"conversation-ref-for-{path.stem}",
    )


def brief_gate(
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


def profile_use(
    status: str,
    artifact_path: str | None = None,
    artifact_sha256: str | None = None,
) -> dict[str, str | None]:
    return {
        "status": status,
        "artifact_path": artifact_path,
        "artifact_sha256": artifact_sha256,
    }


def selection(
    status: str,
    value_key: str,
    value: str | None = None,
    decision_ref: str | None = None,
) -> dict[str, str | None]:
    return {
        value_key: value,
        "selection_status": status,
        "decision_ref": decision_ref,
    }


DEFAULT_BUILT_IN_THEME = selection(
    "user_selected",
    "theme_id",
    "rigorous-consulting-report",
    "conversation://current/theme-selection",
)
DEFAULT_MOTION_DENSITY = selection(
    "user_selected",
    "density",
    "moderate",
    "conversation://current/motion-selection",
)


def confirmed_brief(
    root: Path,
    filename: str,
    content: str,
    *,
    built_in_theme: dict[str, str | None] | None = None,
    motion_density: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    path = root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return brief_gate(
        "confirmed",
        filename,
        sha256(path),
        f"conversation-ref-for-{path.stem}",
        CHECKER.design_decisions_sha256(
            built_in_theme or DEFAULT_BUILT_IN_THEME,
            motion_density or DEFAULT_MOTION_DENSITY,
        ),
    )


def state(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.3",
        "task_id": "synthetic-current-task",
        "route": "idea_only",
        "visual_route": "built_in",
        "material_summary": gate("not_required"),
        "reference_vi": gate("not_required"),
        "profile_use": profile_use("not_required"),
        "project_theme_compiled": False,
        "built_in_theme": dict(DEFAULT_BUILT_IN_THEME),
        "motion_density": dict(DEFAULT_MOTION_DENSITY),
        "design_brief": brief_gate("pending", "gates/design-brief.md"),
    }
    payload.update(overrides)
    if "built_in_theme" not in overrides and payload["visual_route"] != "built_in":
        payload["built_in_theme"] = selection("not_required", "theme_id")
    return payload


def legacy_state(version: str = "1.2", **overrides: object) -> dict[str, object]:
    payload = state()
    payload["schema_version"] = version
    payload.pop("built_in_theme")
    payload.pop("motion_density")
    if version == "1.1":
        payload.pop("profile_use")
    payload.update(overrides)
    return payload


class ProductionAuthorizationTests(unittest.TestCase):
    def evaluate(
        self, payload: dict[str, object], artifact_root: Path
    ) -> dict[str, object]:
        return CHECKER.evaluate_state(
            CHECKER.validate_state(payload, artifact_root)
        )

    def test_word_pdf_pending_summary_allows_only_summary_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.evaluate(
                state(
                    route="word_pdf",
                    visual_route="unresolved",
                    material_summary=gate("pending", "gates/material-summary.md"),
                ),
                Path(temp_dir),
            )
        self.assertFalse(result["authorized_for_formal_html"])
        self.assertEqual(result["blocking_gates"][0], "material_summary_confirmation")
        self.assertIn("material-summary-preview", result["allowed_actions"])
        self.assertNotIn("formal-html", result["allowed_actions"])

    def test_static_reference_pending_vi_allows_only_vi_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = self.evaluate(
                state(
                    route="word_pdf",
                    visual_route="static_reference",
                    material_summary=confirmed(
                        root, "gates/material-summary.md", "# Current summary\n"
                    ),
                    reference_vi=gate("pending", "gates/reference-vi.html"),
                ),
                root,
            )
        self.assertEqual(result["blocking_gates"], ["reference_vi_confirmation"])
        self.assertIn("reference-vi-preview", result["allowed_actions"])
        self.assertNotIn("design-brief-preview", result["allowed_actions"])
        self.assertNotIn("formal-html", result["allowed_actions"])

    def test_existing_deck_requires_current_material_summary_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.evaluate(
                state(
                    route="existing_ppt_html",
                    material_summary=gate("pending", "gates/deck-summary.md"),
                ),
                Path(temp_dir),
            )
        self.assertEqual(result["blocking_gates"], ["material_summary_confirmation"])
        self.assertEqual(result["allowed_actions"], ["material-summary-preview", "status"])

    def test_confirmed_vi_requires_project_theme_before_brief(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = self.evaluate(
                state(
                    visual_route="static_reference",
                    reference_vi=confirmed(
                        root, "gates/reference-vi.html", "<!doctype html><p>VI board</p>"
                    ),
                ),
                root,
            )
        self.assertEqual(result["blocking_gates"], ["project_theme_compilation"])
        self.assertEqual(result["allowed_actions"], ["project-theme-compile", "status"])

    def test_unconfirmed_brief_allows_brief_not_formal_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.evaluate(state(), Path(temp_dir))
        self.assertEqual(result["blocking_gates"], ["design_brief_confirmation"])
        self.assertIn("design-brief-preview", result["allowed_actions"])
        self.assertNotIn("formal-html", result["allowed_actions"])

    def test_profile_reuse_pending_allows_only_current_binding_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = state(
                visual_route="profile_reuse",
                profile_use=profile_use("pending", "gates/profile-use.json"),
            )
            result = self.evaluate(payload, Path(temp_dir))
        self.assertEqual(result["blocking_gates"], ["profile_use_binding"])
        self.assertEqual(result["allowed_actions"], ["profile-use-bind", "status"])
        self.assertNotIn("design-brief-preview", result["allowed_actions"])
        self.assertNotIn("formal-html", result["allowed_actions"])

    def test_six_ordinary_clarifications_still_stop_at_design_selection(self) -> None:
        scenario = {
            "ordinary_clarifications_used": 6,
            "production_state": state(
                built_in_theme=selection("pending", "theme_id"),
                motion_density=selection("pending", "density"),
            ),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.evaluate(scenario["production_state"], Path(temp_dir))
        self.assertEqual(scenario["ordinary_clarifications_used"], 6)
        self.assertEqual(
            result["blocking_gates"],
            ["built_in_theme_selection", "motion_density_selection"],
        )
        self.assertIn("built-in-theme-selection", result["allowed_actions"])
        self.assertIn("motion-density-selection", result["allowed_actions"])
        self.assertNotIn("design-brief-preview", result["allowed_actions"])
        self.assertNotIn("formal-html", result["allowed_actions"])

    def test_explicit_theme_and_motion_choices_open_the_brief_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            validated = CHECKER.validate_state(state(), root)
            result = CHECKER.evaluate_state(validated)
        self.assertEqual(
            validated["built_in_theme"],
            {
                "theme_id": "rigorous-consulting-report",
                "selection_status": "user_selected",
                "decision_ref": "conversation://current/theme-selection",
            },
        )
        self.assertEqual(validated["motion_density"]["density"], "moderate")
        self.assertEqual(result["blocking_gates"], ["design_brief_confirmation"])
        self.assertIn("design-brief-preview", result["allowed_actions"])

    def test_explicit_delegation_records_auditable_decisions(self) -> None:
        payload = state(
            built_in_theme=selection(
                "delegated_to_taohtml",
                "theme_id",
                "corporate-annual-report",
                "conversation://current/theme-delegation",
            ),
            motion_density=selection(
                "delegated_to_taohtml",
                "density",
                "minimal",
                "conversation://current/motion-delegation",
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.evaluate(payload, Path(temp_dir))
        decisions = {item["gate"]: item for item in result["verified_design_decisions"]}
        self.assertEqual(decisions["built_in_theme"]["value"], "corporate-annual-report")
        self.assertEqual(
            decisions["built_in_theme"]["selection_status"],
            "delegated_to_taohtml",
        )
        self.assertEqual(
            decisions["built_in_theme"]["decision_ref"],
            "conversation://current/theme-delegation",
        )
        self.assertEqual(decisions["motion_density"]["value"], "minimal")
        self.assertIn("design-brief-preview", result["allowed_actions"])

    def test_missing_theme_decision_blocks_brief_and_formal_html(self) -> None:
        payload = state(built_in_theme=selection("pending", "theme_id"))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = self.evaluate(payload, root)
            premature = confirmed_brief(
                root, "gates/design-brief.md", "# Premature brief\n"
            )
            with self.assertRaisesRegex(ValueError, "applicable upstream gates"):
                CHECKER.validate_state(state(built_in_theme=selection("pending", "theme_id"), design_brief=premature), root)
        self.assertEqual(result["blocking_gates"], ["built_in_theme_selection"])
        self.assertEqual(result["allowed_actions"], ["built-in-theme-selection", "status"])
        self.assertNotIn("formal-html", result["allowed_actions"])

    def test_missing_motion_decision_blocks_brief_and_formal_html(self) -> None:
        payload = state(motion_density=selection("pending", "density"))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = self.evaluate(payload, root)
            premature = confirmed_brief(
                root, "gates/design-brief.md", "# Premature brief\n"
            )
            with self.assertRaisesRegex(ValueError, "applicable upstream gates"):
                CHECKER.validate_state(state(motion_density=selection("pending", "density"), design_brief=premature), root)
        self.assertEqual(result["blocking_gates"], ["motion_density_selection"])
        self.assertEqual(result["allowed_actions"], ["motion-density-selection", "status"])
        self.assertNotIn("formal-html", result["allowed_actions"])

    def test_static_reference_and_profile_reuse_do_not_require_built_in_theme(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_result = self.evaluate(
                state(
                    visual_route="static_reference",
                    reference_vi=confirmed(
                        root, "gates/reference-vi.html", "<!doctype html><p>VI</p>"
                    ),
                    project_theme_compiled=True,
                ),
                root,
            )
            profile_result = self.evaluate(
                state(
                    visual_route="profile_reuse",
                    profile_use=profile_use("pending", "gates/profile-use.json"),
                ),
                root,
            )
        self.assertNotIn("built_in_theme_selection", static_result["blocking_gates"])
        self.assertIn("design-brief-preview", static_result["allowed_actions"])
        self.assertNotIn("built_in_theme_selection", profile_result["blocking_gates"])
        self.assertEqual(profile_result["blocking_gates"], ["profile_use_binding"])

    def test_legacy_built_in_state_is_migrated_to_blocked_and_reconfirm_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old_brief = confirmed(root, "gates/design-brief.md", "# Legacy brief\n")
            for version in ("1.1", "1.2"):
                with self.subTest(version=version):
                    validated = CHECKER.validate_state(
                        legacy_state(version, design_brief=old_brief),
                        root,
                    )
                    result = CHECKER.evaluate_state(validated)
                    self.assertTrue(result["migration"]["required"])
                    self.assertEqual(
                        result["migration"]["source_schema_version"], version
                    )
                    self.assertTrue(
                        result["migration"]["brief_reconfirmation_required"]
                    )
                    self.assertEqual(validated["design_brief"]["status"], "pending")
                    self.assertEqual(
                        result["blocking_gates"],
                        ["built_in_theme_selection", "motion_density_selection"],
                    )
                    self.assertFalse(result["authorized_for_formal_html"])
                    self.assertNotIn("formal-html", result["allowed_actions"])

    def test_current_file_hash_match_authorizes_and_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            brief = confirmed_brief(
                root, "gates/design-brief.md", "# Approved brief\n"
            )
            result = self.evaluate(state(design_brief=brief), root)
        self.assertTrue(result["authorized_for_formal_html"])
        self.assertEqual(
            result["verified_artifacts"],
            [
                {
                    "gate": "design_brief",
                    "artifact_path": "gates/design-brief.md",
                    "artifact_sha256": brief["artifact_sha256"],
                }
            ],
        )
        for action in ("formal-html", "browser-qa", "deliver-formal-html"):
            self.assertIn(action, result["allowed_actions"])

    def test_confirmed_brief_fails_closed_after_built_in_theme_decision_changes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            brief = confirmed_brief(
                root, "gates/design-brief.md", "# Theme-bound brief\n"
            )
            original = state(design_brief=brief)
            self.assertTrue(self.evaluate(original, root)["authorized_for_formal_html"])
            variants = (
                selection(
                    "user_selected",
                    "theme_id",
                    "corporate-annual-report",
                    "conversation://current/theme-selection",
                ),
                selection(
                    "delegated_to_taohtml",
                    "theme_id",
                    "rigorous-consulting-report",
                    "conversation://current/theme-selection",
                ),
                selection(
                    "user_selected",
                    "theme_id",
                    "rigorous-consulting-report",
                    "conversation://current/reconfirmed-theme",
                ),
            )
            for changed_theme in variants:
                with self.subTest(changed_theme=changed_theme):
                    with self.assertRaisesRegex(
                        ValueError, "does not match the current built-in theme"
                    ):
                        CHECKER.validate_state(
                            state(
                                built_in_theme=changed_theme,
                                design_brief=brief,
                            ),
                            root,
                        )

            state_path = root / "authorization.json"
            state_path.write_text(
                json.dumps(
                    state(
                        built_in_theme=variants[0],
                        design_brief=brief,
                    )
                ),
                encoding="utf-8",
            )
            denied = subprocess.run(
                [
                    sys.executable,
                    str(CHECKER_PATH),
                    "--state",
                    str(state_path),
                    "--artifact-root",
                    str(root),
                    "--action",
                    "formal-html",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(denied.returncode, 2)
        self.assertEqual(json.loads(denied.stdout)["status"], "invalid")

    def test_confirmed_static_reference_brief_fails_after_motion_decision_changes(
        self,
    ) -> None:
        built_in_not_required = selection("not_required", "theme_id")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reference_vi = confirmed(
                root,
                "gates/reference-vi.html",
                "<!doctype html><p>Current VI</p>",
            )
            brief = confirmed_brief(
                root,
                "gates/design-brief.md",
                "# Static-reference motion-bound brief\n",
                built_in_theme=built_in_not_required,
                motion_density=DEFAULT_MOTION_DENSITY,
            )
            original = state(
                visual_route="static_reference",
                reference_vi=reference_vi,
                project_theme_compiled=True,
                built_in_theme=built_in_not_required,
                design_brief=brief,
            )
            self.assertTrue(self.evaluate(original, root)["authorized_for_formal_html"])
            variants = (
                selection(
                    "user_selected",
                    "density",
                    "rich",
                    "conversation://current/motion-selection",
                ),
                selection(
                    "delegated_to_taohtml",
                    "density",
                    "moderate",
                    "conversation://current/motion-selection",
                ),
                selection(
                    "user_selected",
                    "density",
                    "moderate",
                    "conversation://current/reconfirmed-motion",
                ),
            )
            for changed_motion in variants:
                with self.subTest(changed_motion=changed_motion):
                    with self.assertRaisesRegex(
                        ValueError, "does not match the current built-in theme"
                    ):
                        CHECKER.validate_state(
                            state(
                                visual_route="static_reference",
                                reference_vi=reference_vi,
                                project_theme_compiled=True,
                                built_in_theme=built_in_not_required,
                                motion_density=changed_motion,
                                design_brief=brief,
                            ),
                            root,
                        )

    def test_pending_brief_cannot_carry_a_design_decision_binding(self) -> None:
        payload = state()
        payload["design_brief"] = brief_gate(
            "pending",
            "gates/design-brief.md",
            design_decisions_sha256=CHECKER.design_decisions_sha256(
                DEFAULT_BUILT_IN_THEME,
                DEFAULT_MOTION_DENSITY,
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(
                ValueError, "pending state cannot contain design_decisions_sha256"
            ):
                CHECKER.validate_state(payload, Path(temp_dir))

    def test_current_v13_confirmed_brief_without_decision_binding_fails_closed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old_shape = confirmed(
                root,
                "gates/design-brief.md",
                "# Unbound v1.3 brief\n",
            )
            with self.assertRaisesRegex(
                ValueError, "missing=design_decisions_sha256"
            ):
                CHECKER.validate_state(state(design_brief=old_shape), root)

    def test_confirmation_is_invalid_after_bound_file_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            brief = confirmed_brief(
                root, "gates/design-brief.md", "# Approved brief\n"
            )
            (root / "gates" / "design-brief.md").write_text(
                "# Changed after approval\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "does not match the current file"):
                CHECKER.validate_state(state(design_brief=brief), root)

    def test_confirmed_artifact_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            brief = brief_gate(
                "confirmed",
                "gates/missing-brief.md",
                "0" * 64,
                "conversation-ref-for-missing-brief",
                CHECKER.design_decisions_sha256(
                    DEFAULT_BUILT_IN_THEME, DEFAULT_MOTION_DENSITY
                ),
            )
            with self.assertRaisesRegex(ValueError, "does not exist"):
                CHECKER.validate_state(state(design_brief=brief), root)

    def test_confirmed_artifact_path_cannot_escape_task_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "task"
            root.mkdir()
            outside = Path(temp_dir) / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            brief = brief_gate(
                "confirmed",
                "../outside.md",
                sha256(outside),
                "conversation-ref-for-outside",
                CHECKER.design_decisions_sha256(
                    DEFAULT_BUILT_IN_THEME, DEFAULT_MOTION_DENSITY
                ),
            )
            with self.assertRaisesRegex(ValueError, "safe task-local relative path"):
                CHECKER.validate_state(state(design_brief=brief), root)

    def test_symlink_cannot_escape_task_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "task"
            root.mkdir()
            outside = Path(temp_dir) / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            try:
                (root / "linked.md").symlink_to(outside)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlink creation is unavailable on this runner: {exc}")
            brief = brief_gate(
                "confirmed",
                "linked.md",
                sha256(outside),
                "conversation-ref-for-linked",
                CHECKER.design_decisions_sha256(
                    DEFAULT_BUILT_IN_THEME, DEFAULT_MOTION_DENSITY
                ),
            )
            with self.assertRaisesRegex(ValueError, "must not .*symlink"):
                CHECKER.validate_state(state(design_brief=brief), root)

    def test_symlinked_parent_is_rejected_even_when_target_stays_inside_task_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "task"
            real = root / "real"
            real.mkdir(parents=True)
            brief_path = real / "brief.md"
            brief_path.write_text("inside", encoding="utf-8")
            try:
                (root / "linked").symlink_to(real, target_is_directory=True)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlink creation is unavailable on this runner: {exc}")
            brief = brief_gate(
                "confirmed",
                "linked/brief.md",
                sha256(brief_path),
                "conversation-ref-for-linked-parent",
                CHECKER.design_decisions_sha256(
                    DEFAULT_BUILT_IN_THEME, DEFAULT_MOTION_DENSITY
                ),
            )
            with self.assertRaisesRegex(ValueError, "must not use symlinks"):
                CHECKER.validate_state(state(design_brief=brief), root)

    def test_impossible_confirmation_order_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            brief = confirmed_brief(
                root, "gates/design-brief.md", "# Premature brief\n"
            )
            with self.assertRaisesRegex(ValueError, "design brief cannot be confirmed"):
                CHECKER.validate_state(
                    state(
                        route="word_pdf",
                        visual_route="unresolved",
                        material_summary=gate("pending", "gates/material-summary.md"),
                        design_brief=brief,
                    ),
                    root,
                )

    def test_cli_exposes_digest_for_pending_brief_and_reuses_it_for_confirmation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_path = root / "authorization.json"
            state_path.write_text(json.dumps(state()), encoding="utf-8")
            command = [
                sys.executable,
                str(CHECKER_PATH),
                "--state",
                str(state_path),
                "--artifact-root",
                str(root),
            ]
            preview = subprocess.run(
                [*command, "--action", "design-brief-preview"],
                check=False,
                capture_output=True,
                text=True,
            )
            preview_result = json.loads(preview.stdout)
            current_digest = preview_result["current_design_decisions_sha256"]
            brief_path = root / "gates/design-brief.md"
            brief_path.parent.mkdir(parents=True, exist_ok=True)
            brief_path.write_text("# CLI-bound brief\n", encoding="utf-8")
            confirmed_state = state(
                design_brief=brief_gate(
                    "confirmed",
                    "gates/design-brief.md",
                    sha256(brief_path),
                    "conversation://current/brief-confirmation",
                    current_digest,
                )
            )
            state_path.write_text(json.dumps(confirmed_state), encoding="utf-8")
            allowed = subprocess.run(
                [*command, "--action", "formal-html"],
                check=False,
                capture_output=True,
                text=True,
            )
            changed_state = {
                **confirmed_state,
                "motion_density": selection(
                    "user_selected",
                    "density",
                    "rich",
                    "conversation://current/motion-selection",
                ),
            }
            state_path.write_text(json.dumps(changed_state), encoding="utf-8")
            stale = subprocess.run(
                [*command, "--action", "formal-html"],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(preview.returncode, 0)
        self.assertTrue(preview_result["requested_action"]["allowed"])
        self.assertRegex(current_digest, r"^[0-9a-f]{64}$")
        self.assertEqual(
            current_digest,
            CHECKER.design_decisions_sha256(
                DEFAULT_BUILT_IN_THEME,
                DEFAULT_MOTION_DENSITY,
            ),
        )
        self.assertEqual(allowed.returncode, 0)
        self.assertTrue(json.loads(allowed.stdout)["requested_action"]["allowed"])
        self.assertEqual(stale.returncode, 2)
        self.assertIn(
            "does not match the current built-in theme",
            json.loads(stale.stdout)["error"],
        )

    def test_cli_denies_then_allows_only_current_bound_brief(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_path = root / "authorization.json"
            state_path.write_text(json.dumps(state()), encoding="utf-8")
            command = [
                sys.executable,
                str(CHECKER_PATH),
                "--state",
                str(state_path),
                "--artifact-root",
                str(root),
                "--action",
                "formal-html",
            ]
            denied = subprocess.run(command, check=False, capture_output=True, text=True)
            state_path.write_text(
                json.dumps(
                    state(
                        design_brief=confirmed_brief(
                            root, "gates/design-brief.md", "# Current brief\n"
                        )
                    )
                ),
                encoding="utf-8",
            )
            allowed = subprocess.run(command, check=False, capture_output=True, text=True)
            (root / "gates" / "design-brief.md").write_text(
                "# Stale confirmation\n", encoding="utf-8"
            )
            invalid = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(denied.returncode, 1)
        self.assertFalse(json.loads(denied.stdout)["requested_action"]["allowed"])
        self.assertEqual(allowed.returncode, 0)
        self.assertTrue(json.loads(allowed.stdout)["requested_action"]["allowed"])
        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(json.loads(invalid.stdout)["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
