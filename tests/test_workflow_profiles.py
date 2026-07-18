from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skill" / "taohtml"
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
CONTRACT = (
    SKILL_DIR / "references" / "workflow-profile-contract.md"
).read_text(encoding="utf-8")
PROFILES = (SKILL_DIR / "references" / "workflow-profiles.md").read_text(
    encoding="utf-8"
)

EXPECTED_PROFILES = (
    ("formal-submission-writing", "规范报送与正式写作"),
    ("research-analysis-argumentation", "研究分析与专业论证"),
    ("periodic-operations-reporting", "周期经营与数据汇报"),
    ("proposal-planning-decision", "方案策划与决策提案"),
    ("live-presentation-persuasion", "现场演讲与说服表达"),
    ("teaching-training-knowledge-transfer", "教学培训与知识传递"),
    ("project-lifecycle-reporting", "项目全过程汇报"),
    ("brand-communication-editorial-publishing", "品牌传播与编辑出版"),
    ("rule-response-application-defense", "规则响应、申报与答辩"),
)

REQUIRED_SECTIONS = (
    "身份与版本",
    "适用目标",
    "排除范围",
    "成品",
    "所需信息",
    "design-ready 条件",
    "叙事任务",
    "证据规则",
    "横向参数默认值",
    "IR 映射边界",
    "Runtime/主题使用",
    "QA 验收",
    "能力叠加与冲突处理",
)

HORIZONTAL_PARAMETERS = (
    "input_entry_route",
    "use_mode",
    "visual_binding",
    "evidence_rigor",
    "information_density",
    "motion_density",
    "continuation_state",
)


def profile_sections() -> list[tuple[int, str, str]]:
    matches = list(re.finditer(r"^### (\d+)\. (.+)$", PROFILES, re.MULTILINE))
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(PROFILES)
        sections.append((int(match.group(1)), match.group(2), PROFILES[match.end() : end]))
    return sections


class WorkflowProfileContractTests(unittest.TestCase):
    def test_catalog_has_the_nine_stable_profiles_in_order(self) -> None:
        sections = profile_sections()
        self.assertEqual(
            [(number, name) for number, name, _ in sections],
            [(index, name) for index, (_, name) in enumerate(EXPECTED_PROFILES, 1)],
        )

        ids = []
        for (_, expected_name), (_, actual_name, body) in zip(
            EXPECTED_PROFILES, sections, strict=True
        ):
            self.assertEqual(actual_name, expected_name)
            match = re.search(r"^- `profile_id`: `([^`]+)`$", body, re.MULTILINE)
            self.assertIsNotNone(match, expected_name)
            ids.append(match.group(1))

        self.assertEqual(ids, [profile_id for profile_id, _ in EXPECTED_PROFILES])
        self.assertEqual(len(ids), len(set(ids)))

        for profile_id, name in EXPECTED_PROFILES:
            self.assertIn(f"| `{profile_id}` | {name} |", PROFILES)

    def test_every_profile_implements_the_uniform_foundation_contract(self) -> None:
        for _, name, body in profile_sections():
            headings = re.findall(r"^#### (.+)$", body, re.MULTILINE)
            self.assertEqual(headings, list(REQUIRED_SECTIONS), name)
            for parameter in HORIZONTAL_PARAMETERS:
                self.assertIn(f"`{parameter}`", body, f"{name}: {parameter}")

        for heading in REQUIRED_SECTIONS:
            self.assertIn(f"| {heading} |", CONTRACT)

    def test_skill_is_a_lightweight_semantic_router(self) -> None:
        router = SKILL.split("## Workflow Profile Routing", 1)[1].split(
            "## Project Handoff Overlay", 1
        )[0]
        router_flat = " ".join(router.split())
        self.assertIn("TaoHtml is one installed Skill", router_flat)
        self.assertIn("on-demand Workflow Profiles, not separate Skills", router_flat)
        self.assertIn("exactly one primary Profile", router_flat)
        self.assertIn("explicit business objective", router_flat)
        self.assertIn("semantics of eligible inspected material", router_flat)
        self.assertIn("select it automatically", router_flat)
        self.assertIn(
            "do not ask a Profile question or display the catalog", router_flat
        )
        self.assertIn("apply only the selected foundation definition", router_flat)
        self.assertIn("display all nine exact customer-facing names", router_flat)
        self.assertIn("ask one question", router_flat)
        self.assertIn("primary business goal", router_flat)
        self.assertIn("keyword blacklist", router_flat)
        self.assertIn("hard-coded numbers", router_flat)
        self.assertIn("fixed report-type mapping", router_flat)
        self.assertIn("bounded overlays", router_flat)
        self.assertIn("references/workflow-profile-contract.md", router_flat)
        self.assertIn("references/workflow-profiles.md", router_flat)

        for _, name in EXPECTED_PROFILES:
            self.assertNotIn(name, router)
        self.assertLess(len(SKILL.splitlines()), 500)

    def test_ambiguous_fallback_is_one_business_goal_question_not_ir_intake(self) -> None:
        self.assertIn("display all nine exact", CONTRACT)
        self.assertIn("ask exactly one routing question", CONTRACT)
        self.assertIn("which business goal", CONTRACT)
        self.assertIn("never a Profile id, Report IR field", CONTRACT)
        self.assertIn("does not create a\nnew intake cycle", CONTRACT)
        self.assertIn("Do not expose Report IR as a user choice", CONTRACT)
        self.assertIn("Do not ask the user to fill these as a Profile form", CONTRACT)

    def test_primary_profile_and_horizontal_parameters_are_independent(self) -> None:
        self.assertIn("exactly one primary Profile per project", CONTRACT)
        self.assertIn("never run two\n   complete Profile workflows in parallel", CONTRACT)
        self.assertIn("must remain separately recorded", CONTRACT)
        self.assertIn("primary_profile = profile_id", CONTRACT)
        self.assertIn("capability_overlays = bounded capability", CONTRACT)
        self.assertIn("must not import a second Profile's complete intake", CONTRACT)
        for parameter in HORIZONTAL_PARAMETERS:
            self.assertIn(f"| `{parameter}` |", CONTRACT)

    def test_existing_entry_handoff_brief_and_authorization_gates_are_preserved(
        self,
    ) -> None:
        entry_routes = SKILL.split("## Entry Routes", 1)[1].split(
            "## Workflow Profile Routing", 1
        )[0]
        self.assertEqual(
            re.findall(r"^\d+\. \*\*", entry_routes, re.MULTILINE),
            ["1. **", "2. **", "3. **"],
        )
        for marker in (
            "The three material entry routes",
            "Material Understanding\n  Summary confirmation gate",
            "Handoff overlay",
            "The complete current Report Design Brief",
            "Current-file Production Authorization",
            "Direct-HTML default production",
            "`《待核实内容清单》` delivery",
        ):
            self.assertIn(marker, CONTRACT)

    def test_profile_contract_does_not_copy_or_activate_implementation_layers(self) -> None:
        self.assertIn("Do not add or change Report IR schema fields", CONTRACT)
        self.assertIn("Do not invoke the Report IR route merely because a Profile", CONTRACT)
        self.assertIn("must not copy their schemas, scripts,\nalgorithms", CONTRACT)
        self.assertIn("it cannot authorize new motion engineering", CONTRACT)
        for _, _, body in profile_sections():
            ir_boundary = body.split("#### IR 映射边界", 1)[1].split(
                "#### Runtime/主题使用", 1
            )[0]
            self.assertRegex(
                ir_boundary,
                r"(?:IR (?:engineering )?route is independently authorized|independently authorized IR route)",
            )

    def test_node_one_keeps_both_golden_paths_at_foundation_level(self) -> None:
        bodies = {name: body for _, name, body in profile_sections()}
        for name in ("方案策划与决策提案", "现场演讲与说服表达"):
            identity = bodies[name].split("#### 身份与版本", 1)[1].split(
                "#### 适用目标", 1
            )[0]
            self.assertIn("foundation definition only", identity)
            self.assertIn("Golden Path detailed workflow", identity)
            self.assertIn("outside this engineering node", identity)


if __name__ == "__main__":
    unittest.main()
