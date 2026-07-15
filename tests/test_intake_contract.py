from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skill" / "taohtml"
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
INTAKE = (SKILL_DIR / "references" / "intake-workflow.md").read_text(encoding="utf-8")
BRIEF = (SKILL_DIR / "references" / "design-brief-template.md").read_text(
    encoding="utf-8"
)


class IntakeContractTests(unittest.TestCase):
    def test_clear_idea_can_stop_with_zero_questions(self) -> None:
        self.assertIn("Allow **0 clarification questions**", INTAKE)
        self.assertIn("proceed directly to a brief with zero clarification questions", INTAKE)
        self.assertIn("Do not impose this gate on an idea-only input", INTAKE)

    def test_ordinary_intake_targets_three_to_five_questions(self) -> None:
        self.assertIn("Treat **3-5 clarification questions** as the ordinary target", INTAKE)
        self.assertIn("Ask only the largest current gap", INTAKE)
        self.assertIn("not a four-question form", INTAKE)

    def test_six_is_a_hard_cap_but_brief_confirmation_is_separate(self) -> None:
        self.assertIn("Enforce **6 clarification questions** as a hard maximum", INTAKE)
        self.assertIn("Do not ask a seventh", INTAKE)
        self.assertIn("does not count toward this budget", INTAKE)
        self.assertIn("start a new intake cycle with fresh counters", INTAKE)

    def test_same_gap_is_asked_at_most_twice(self) -> None:
        self.assertIn("same key gap at most **twice**", INTAKE)
        self.assertIn("On the second attempt", INTAKE)
        self.assertIn("a concrete example or 2-3 real options", INTAKE)

    def test_three_rounds_without_information_gain_stop_questions(self) -> None:
        self.assertIn(
            "three consecutive rounds without actionable new information", INTAKE
        )
        self.assertIn("Stop questioning immediately", INTAKE)
        self.assertIn("infer all remaining low-risk gaps", INTAKE)

    def test_high_risk_gap_blocks_brief_and_production(self) -> None:
        self.assertIn("do not generate a Report Design Brief", INTAKE)
        self.assertIn("do not begin production", INTAKE)
        for heading in (
            "## 当前已知",
            "## 未决缺口",
            "## 为什么不能推断",
            "## 最小补充材料",
            "## 恢复条件",
        ):
            self.assertIn(heading, INTAKE)
        self.assertIn("use the blocked-intake output instead of this template", BRIEF)

    def test_skill_keeps_compact_startup_and_has_no_dbs_dependency(self) -> None:
        self.assertIn("compress these startup choices into one short interaction", SKILL)
        self.assertIn("the compact startup choice is the explicit exception", SKILL)
        self.assertNotIn("DBS", SKILL + INTAKE + BRIEF)


if __name__ == "__main__":
    unittest.main()
