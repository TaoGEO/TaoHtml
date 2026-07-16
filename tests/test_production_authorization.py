from __future__ import annotations

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


def gate(
    status: str,
    artifact_id: str | None = None,
    confirmation_ref: str | None = None,
) -> dict[str, str | None]:
    return {
        "status": status,
        "artifact_id": artifact_id,
        "confirmation_ref": confirmation_ref,
    }


def state(**overrides) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "task_id": "synthetic-current-task",
        "route": "idea_only",
        "visual_route": "built_in",
        "material_summary": gate("not_required"),
        "reference_vi": gate("not_required"),
        "project_theme_compiled": False,
        "design_brief": gate("pending"),
    }
    payload.update(overrides)
    return payload


class ProductionAuthorizationTests(unittest.TestCase):
    def evaluate(self, payload: dict[str, object]) -> dict[str, object]:
        return CHECKER.evaluate_state(CHECKER.validate_state(payload))

    def test_word_pdf_pending_summary_allows_only_summary_preview(self) -> None:
        result = self.evaluate(
            state(
                route="word_pdf",
                visual_route="unresolved",
                material_summary=gate("pending", "summary-draft"),
            )
        )
        self.assertFalse(result["authorized_for_formal_html"])
        self.assertEqual(
            result["blocking_gates"][0], "material_summary_confirmation"
        )
        self.assertIn("material-summary-preview", result["allowed_actions"])
        self.assertNotIn("formal-html", result["allowed_actions"])

    def test_static_reference_pending_vi_allows_only_vi_preview(self) -> None:
        result = self.evaluate(
            state(
                route="word_pdf",
                visual_route="static_reference",
                material_summary=gate(
                    "confirmed", "summary-v2", "current-turn-summary-confirmation"
                ),
                reference_vi=gate("pending", "vi-board-draft"),
            )
        )
        self.assertEqual(result["blocking_gates"], ["reference_vi_confirmation"])
        self.assertIn("reference-vi-preview", result["allowed_actions"])
        self.assertNotIn("design-brief-preview", result["allowed_actions"])
        self.assertNotIn("formal-html", result["allowed_actions"])

    def test_existing_deck_requires_current_material_summary_confirmation(self) -> None:
        result = self.evaluate(
            state(
                route="existing_ppt_html",
                material_summary=gate("pending", "deck-summary-draft"),
            )
        )
        self.assertEqual(result["blocking_gates"], ["material_summary_confirmation"])
        self.assertEqual(
            result["allowed_actions"], ["material-summary-preview", "status"]
        )
        self.assertNotIn("formal-html", result["allowed_actions"])

    def test_confirmed_vi_requires_project_theme_before_brief(self) -> None:
        result = self.evaluate(
            state(
                visual_route="static_reference",
                reference_vi=gate(
                    "confirmed", "vi-board-v3", "current-turn-vi-confirmation"
                ),
            )
        )
        self.assertEqual(result["blocking_gates"], ["project_theme_compilation"])
        self.assertEqual(
            result["allowed_actions"], ["project-theme-compile", "status"]
        )

    def test_unconfirmed_brief_allows_brief_not_formal_html(self) -> None:
        result = self.evaluate(state(design_brief=gate("pending", "brief-v1")))
        self.assertEqual(result["blocking_gates"], ["design_brief_confirmation"])
        self.assertIn("design-brief-preview", result["allowed_actions"])
        self.assertNotIn("formal-html", result["allowed_actions"])

    def test_all_current_gates_authorize_formal_html_qa_and_delivery(self) -> None:
        result = self.evaluate(
            state(
                design_brief=gate(
                    "confirmed", "brief-v2", "current-turn-brief-confirmation"
                )
            )
        )
        self.assertTrue(result["authorized_for_formal_html"])
        for action in ("formal-html", "browser-qa", "deliver-formal-html"):
            self.assertIn(action, result["allowed_actions"])

    def test_impossible_confirmation_order_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "design brief cannot be confirmed"):
            CHECKER.validate_state(
                state(
                    route="word_pdf",
                    visual_route="unresolved",
                    material_summary=gate("pending", "summary-v1"),
                    design_brief=gate(
                        "confirmed", "brief-v1", "stale-confirmation-reference"
                    ),
                )
            )

    def test_cli_denies_formal_html_until_current_brief_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "authorization.json"
            state_path.write_text(json.dumps(state()), encoding="utf-8")
            denied = subprocess.run(
                [
                    sys.executable,
                    str(CHECKER_PATH),
                    "--state",
                    str(state_path),
                    "--action",
                    "formal-html",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            state_path.write_text(
                json.dumps(
                    state(
                        design_brief=gate(
                            "confirmed",
                            "brief-current",
                            "current-turn-brief-confirmation",
                        )
                    )
                ),
                encoding="utf-8",
            )
            allowed = subprocess.run(
                [
                    sys.executable,
                    str(CHECKER_PATH),
                    "--state",
                    str(state_path),
                    "--action",
                    "formal-html",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(denied.returncode, 1)
        self.assertFalse(json.loads(denied.stdout)["requested_action"]["allowed"])
        self.assertEqual(allowed.returncode, 0)
        self.assertTrue(json.loads(allowed.stdout)["requested_action"]["allowed"])


if __name__ == "__main__":
    unittest.main()
