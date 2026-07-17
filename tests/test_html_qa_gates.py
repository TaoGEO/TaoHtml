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

    def test_vertical_and_horizontal_ancestor_clipping_fail_all_viewports(self) -> None:
        cases = (
            ("ancestor-vertical-clip.html", "bottom"),
            ("ancestor-horizontal-clip.html", "right"),
        )
        for fixture, direction in cases:
            for width, height in VIEWPORTS:
                with self.subTest(fixture=fixture, viewport=(width, height)):
                    completed, report = self.run_fixture(fixture, width, height)
                    self.assertEqual(completed.returncode, 1)
                    self.assertIn("readable content", completed.stdout)
                    self.assertIn("is clipped by ancestor", completed.stdout)
                    clipping = report["pages"][0]["ancestor_clipping"][0]
                    self.assertEqual(clipping["page"], 1)
                    self.assertEqual(clipping["state"], "reading-initial")
                    self.assertIn(direction, clipping["directions"])
                    self.assertGreater(clipping["clipped_pixels"][direction], 1)
                    self.assertTrue(clipping["content"]["selector"])
                    self.assertTrue(clipping["content"]["text"])
                    self.assertTrue(
                        clipping["clipping_ancestor"]["selector"]
                    )
                    self.assertIn(
                        clipping["clipping_ancestor"][f"overflow_{'x' if direction == 'right' else 'y'}"],
                        {"hidden", "clip", "auto", "scroll"},
                    )
                    self.assertTrue(clipping["content"]["rect"])
                    self.assertTrue(
                        clipping["clipping_ancestor"]["content_box"]
                    )

    def test_transformed_content_clipped_by_ancestor_fails(self) -> None:
        completed, report = self.run_fixture(
            "ancestor-transform-clip.html", 1600, 900
        )
        self.assertEqual(completed.returncode, 1)
        clipping = report["pages"][0]["ancestor_clipping"][0]
        self.assertIn("right", clipping["directions"])
        self.assertEqual(
            clipping["clipping_ancestor"]["overflow_x"], "clip"
        )
        self.assertIn("shifted-report-copy", clipping["content"]["selector"])
        self.assertIn("clip-window", clipping["clipping_ancestor"]["selector"])

    def test_tight_normal_flow_at_clip_boundary_passes_all_viewports(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                completed, report = self.run_fixture(
                    "ancestor-tight-valid.html", width, height
                )
                self.assertEqual(completed.returncode, 0, completed.stdout)
                page = report["pages"][0]
                self.assertEqual(page["ancestor_clipping"], [])
                state = page["ancestor_clipping_states"][0]
                self.assertGreater(state["candidate_count"], 0)
                self.assertGreater(state["clipping_ancestor_checks"], 0)

    def test_object_fit_crop_and_aria_hidden_fixed_decoration_do_not_report(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                completed, report = self.run_fixture(
                    "ancestor-noncontent-crop-valid.html", width, height
                )
                self.assertEqual(completed.returncode, 0, completed.stdout)
                page = report["pages"][0]
                self.assertEqual(page["ancestor_clipping"], [])
                state = page["ancestor_clipping_states"][0]
                self.assertEqual(state["candidate_count"], 1)

    def test_intermediate_reveal_ancestor_clipping_fails_even_when_final_state_fits(self) -> None:
        completed, report = self.run_fixture(
            "ancestor-reveal-intermediate-clip.html", 1600, 900
        )
        self.assertEqual(completed.returncode, 1)
        states = report["pages"][0]["ancestor_clipping_states"]
        self.assertEqual(
            [state["state"] for state in states],
            ["presentation-initial", "presentation-step-1", "presentation-step-2"],
        )
        self.assertEqual(states[0]["clips"], [])
        self.assertTrue(states[1]["clips"])
        self.assertEqual(states[2]["clips"], [])
        self.assertIn("state presentation-step-1", completed.stdout)
        performance = report["ancestor_clipping_performance"]
        self.assertEqual(performance["pages_checked"], 1)
        self.assertEqual(performance["states_checked"], 3)
        self.assertGreater(performance["candidate_evaluations"], 0)
        self.assertGreater(performance["clipping_ancestor_checks"], 0)
        self.assertGreaterEqual(performance["browser_evaluation_ms"], 0)

    def test_responsive_editable_region_still_honors_canonical_capacity(self) -> None:
        completed, report = self.run_fixture(
            "editable-capacity-responsive-fail.html", 1920, 1080
        )
        self.assertEqual(completed.returncode, 1)
        page = report["pages"][0]
        self.assertEqual(page["ancestor_clipping"], [])
        self.assertEqual(len(page["editable_region_capacity_failures"]), 1)
        failure = page["editable_region_capacity_failures"][0]
        self.assertEqual(failure["page"], 1)
        self.assertEqual(failure["state"], "reading-initial")
        self.assertEqual(failure["editable_region"]["id"], "generic-safe-area")
        self.assertIn("vertical", failure["axes"])
        self.assertIn("top", failure["directions"])
        self.assertIn("bottom", failure["directions"])
        self.assertGreater(failure["clipped_pixels"]["top"], 1)
        self.assertEqual(
            failure["probe_viewport"],
            {"width": 1600, "height": 900},
        )
        self.assertTrue(failure["clipped_content"]["samples"])
        self.assertIn("canonical 1600x900 editable-region capacity", completed.stdout)
        self.assertFalse(report["passed"])
        self.assertTrue(
            any("editable-region capacity" in item for item in report["failures"])
        )


if __name__ == "__main__":
    unittest.main()
