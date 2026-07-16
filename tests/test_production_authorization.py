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


def state(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.1",
        "task_id": "synthetic-current-task",
        "route": "idea_only",
        "visual_route": "built_in",
        "material_summary": gate("not_required"),
        "reference_vi": gate("not_required"),
        "project_theme_compiled": False,
        "design_brief": gate("pending", "gates/design-brief.md"),
    }
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

    def test_current_file_hash_match_authorizes_and_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            brief = confirmed(root, "gates/design-brief.md", "# Approved brief\n")
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

    def test_confirmation_is_invalid_after_bound_file_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            brief = confirmed(root, "gates/design-brief.md", "# Approved brief\n")
            (root / "gates" / "design-brief.md").write_text(
                "# Changed after approval\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "does not match the current file"):
                CHECKER.validate_state(state(design_brief=brief), root)

    def test_confirmed_artifact_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            brief = gate(
                "confirmed",
                "gates/missing-brief.md",
                "0" * 64,
                "conversation-ref-for-missing-brief",
            )
            with self.assertRaisesRegex(ValueError, "does not exist"):
                CHECKER.validate_state(state(design_brief=brief), root)

    def test_confirmed_artifact_path_cannot_escape_task_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "task"
            root.mkdir()
            outside = Path(temp_dir) / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            brief = gate(
                "confirmed",
                "../outside.md",
                sha256(outside),
                "conversation-ref-for-outside",
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
            brief = gate(
                "confirmed",
                "linked.md",
                sha256(outside),
                "conversation-ref-for-linked",
            )
            with self.assertRaisesRegex(ValueError, "escapes the task artifact root"):
                CHECKER.validate_state(state(design_brief=brief), root)

    def test_impossible_confirmation_order_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            brief = confirmed(root, "gates/design-brief.md", "# Premature brief\n")
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
                        design_brief=confirmed(
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
