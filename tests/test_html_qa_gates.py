from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "skill" / "taohtml" / "scripts" / "check_html_deck.py"
FIXTURES = ROOT / "tests" / "fixtures" / "qa-gates"
VIEWPORTS = ((1366, 768), (1600, 900), (1920, 1080))


class HtmlQAGateTests(unittest.TestCase):
    def run_fixture(
        self, fixture: str, width: int, height: int
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "qa"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(CHECKER),
                    str(FIXTURES / fixture),
                    str(output),
                    "--width",
                    str(width),
                    "--height",
                    str(height),
                    "--max-pages",
                    "1",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            report = json.loads((output / "qa-report.json").read_text(encoding="utf-8"))
        return completed, report

    def test_presentation_without_controlled_steps_fails_all_viewports(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                completed, report = self.run_fixture(
                    "presentation-zero-steps.html", width, height
                )
                self.assertEqual(completed.returncode, 1)
                self.assertIn(
                    "Presentation mode has zero controlled presentation steps",
                    completed.stdout,
                )
                contract = report["controlled_step_contract"]
                self.assertEqual(contract["contract"], "fragment-v1")
                self.assertEqual(contract["controlled_steps"], 0)

    def test_reading_without_steps_and_valid_presentation_pass(self) -> None:
        for fixture in ("reading-no-steps.html", "presentation-valid.html"):
            for width, height in VIEWPORTS:
                with self.subTest(fixture=fixture, viewport=(width, height)):
                    completed, report = self.run_fixture(fixture, width, height)
                    self.assertEqual(completed.returncode, 0, completed.stdout)
                    self.assertEqual(report["pages"][0]["text_collisions"], [])
                    self.assertTrue(report["pages"][0]["canvas_coverage"]["valid"])

    def test_active_slide_underfill_fails_actual_canvas_geometry(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                completed, report = self.run_fixture(
                    "canvas-underfill.html", width, height
                )
                self.assertEqual(completed.returncode, 1)
                self.assertIn(
                    "active slide does not cover the deck canvas", completed.stdout
                )
                coverage = report["pages"][0]["canvas_coverage"]
                self.assertFalse(coverage["valid"])
                self.assertLess(coverage["coverage"]["height_ratio"], 0.7)

    def test_slight_and_major_svg_text_collisions_fail_with_local_evidence(self) -> None:
        for fixture in ("svg-slight-overlap.html", "svg-major-overlap.html"):
            for width, height in VIEWPORTS:
                with self.subTest(fixture=fixture, viewport=(width, height)):
                    completed, report = self.run_fixture(fixture, width, height)
                    self.assertEqual(completed.returncode, 1)
                    self.assertIn("Page 1 state", completed.stdout)
                    self.assertIn("text collision between", completed.stdout)
                    self.assertIn("overlap=", completed.stdout)
                    collisions = report["pages"][0]["text_collisions"]
                    self.assertTrue(collisions)
                    collision = collisions[0]
                    self.assertEqual(collision["first"]["kind"], "svg-text")
                    self.assertEqual(collision["second"]["kind"], "svg-text")
                    self.assertTrue(collision["first"]["selector"])
                    self.assertTrue(collision["second"]["selector"])
                    self.assertGreater(collision["overlap"]["x"], 0)
                    self.assertGreater(collision["overlap"]["y"], 0)
                    if fixture == "svg-slight-overlap.html":
                        self.assertLess(collision["overlap"]["y"], 1)
                    else:
                        self.assertGreater(collision["overlap"]["y"], 20)

    def test_compact_svg_labels_pass_all_viewports(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                completed, report = self.run_fixture(
                    "svg-tight-valid.html", width, height
                )
                self.assertEqual(completed.returncode, 0, completed.stdout)
                self.assertEqual(report["pages"][0]["text_collisions"], [])

    def test_collision_is_checked_after_each_controlled_reveal_state(self) -> None:
        completed, report = self.run_fixture(
            "presentation-state-collision.html", 1600, 900
        )
        self.assertEqual(completed.returncode, 1)
        states = report["pages"][0]["text_collision_states"]
        self.assertEqual(states[0]["state"], "presentation-initial")
        self.assertEqual(states[0]["collisions"], [])
        self.assertEqual(states[1]["state"], "presentation-step-1")
        self.assertTrue(states[1]["collisions"])
        self.assertIn("state presentation-step-1", completed.stdout)

    def test_html_text_collision_uses_the_same_leaf_text_mechanism(self) -> None:
        completed, report = self.run_fixture("html-label-overlap.html", 1600, 900)
        self.assertEqual(completed.returncode, 1)
        collision = report["pages"][0]["text_collisions"][0]
        self.assertEqual(collision["first"]["kind"], "html")
        self.assertEqual(collision["second"]["kind"], "html")
        self.assertIn("text collision between", completed.stdout)

    def test_multiline_cjk_collision_inside_one_owner_fails_all_viewports(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                completed, report = self.run_fixture(
                    "html-multiline-cjk-overlap.html", width, height
                )
                self.assertEqual(completed.returncode, 1)
                self.assertIn("multiline text collision inside", completed.stdout)
                collisions = report["pages"][0]["intra_element_text_collisions"]
                self.assertTrue(collisions)
                self.assertEqual(collisions[0]["collision_scope"], "same-owner-lines")
                self.assertEqual(collisions[0]["first"]["selector"], collisions[0]["second"]["selector"])
                self.assertGreater(collisions[0]["overlap"]["y"], 0)
                self.assertIn(collisions[0], report["pages"][0]["text_collisions"])

    def test_multiline_cjk_with_safe_line_height_passes_all_viewports(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                completed, report = self.run_fixture(
                    "html-multiline-cjk-valid.html", width, height
                )
                self.assertEqual(completed.returncode, 0, completed.stdout)
                self.assertEqual(
                    report["pages"][0]["intra_element_text_collisions"], []
                )
                self.assertEqual(report["pages"][0]["text_collisions"], [])

    def test_static_normal_flow_font_metrics_pass_with_auditable_exclusion(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                completed, report = self.run_fixture(
                    "html-block-flow-tight-valid.html", width, height
                )
                self.assertEqual(completed.returncode, 0, completed.stdout)
                page = report["pages"][0]
                self.assertEqual(page["text_collisions"], [])
                exclusions = page["normal_flow_text_metric_exclusions"]
                self.assertTrue(exclusions)
                self.assertIn("font metrics", exclusions[0]["reason"])
                self.assertGreater(exclusions[0]["layout_clearance"]["y"], 0)
                self.assertEqual(exclusions[0]["metric_overlap_limit"], 1.25)
                self.assertLessEqual(
                    exclusions[0]["metric_overlap_depth"],
                    exclusions[0]["metric_overlap_limit"],
                )

    def test_independently_transformed_html_overlap_still_fails(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                completed, report = self.run_fixture(
                    "html-transform-overlap.html", width, height
                )
                self.assertEqual(completed.returncode, 1)
                collisions = report["pages"][0]["text_collisions"]
                self.assertTrue(collisions)
                self.assertEqual(collisions[0]["first"]["kind"], "html")
                self.assertEqual(collisions[0]["second"]["kind"], "html")
                self.assertIn("text collision between", completed.stdout)

    def test_parent_child_text_flow_is_not_double_counted(self) -> None:
        completed, report = self.run_fixture(
            "html-parent-child-flow.html", 1600, 900
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(report["pages"][0]["text_collisions"], [])

    def test_local_reasoned_opt_out_is_auditable(self) -> None:
        completed, report = self.run_fixture("html-label-opt-out.html", 1600, 900)
        self.assertEqual(completed.returncode, 0, completed.stdout)
        page = report["pages"][0]
        self.assertEqual(page["text_collisions"], [])
        self.assertEqual(len(page["text_collision_opt_outs"]), 1)
        self.assertEqual(
            page["text_collision_opt_outs"][0]["reason"],
            "intentional local watermark",
        )

    def test_empty_opt_out_reason_fails_closed(self) -> None:
        completed, report = self.run_fixture(
            "html-label-empty-opt-out.html", 1600, 900
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("opt-out requires a local reason", completed.stdout)
        self.assertEqual(
            len(report["pages"][0]["invalid_text_collision_opt_outs"]), 1
        )


if __name__ == "__main__":
    unittest.main()
