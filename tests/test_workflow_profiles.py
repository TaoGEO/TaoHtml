from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skill" / "taohtml"
REFERENCES = SKILL_DIR / "references"
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
CONTRACT = (REFERENCES / "workflow-profile-contract.md").read_text(
    encoding="utf-8"
)
CATALOG = (REFERENCES / "workflow-profiles.md").read_text(encoding="utf-8")
BRIEF = (REFERENCES / "design-brief-template.md").read_text(encoding="utf-8")
REPORT_IR_SCHEMA = json.loads(
    (REFERENCES / "report-ir-v1.schema.json").read_text(encoding="utf-8")
)

EXPECTED_PROFILES = (
    (
        "formal-submission-writing",
        "规范报送与正式写作",
        "references/workflow-profile-formal-submission-writing.md",
    ),
    (
        "research-analysis-argumentation",
        "研究分析与专业论证",
        "references/workflow-profile-research-analysis-argumentation.md",
    ),
    (
        "periodic-operations-reporting",
        "周期经营与数据汇报",
        "references/workflow-profile-periodic-operations-reporting.md",
    ),
    (
        "proposal-planning-decision",
        "方案策划与决策提案",
        "references/workflow-profile-proposal-planning-decision.md",
    ),
    (
        "live-presentation-persuasion",
        "现场演讲与说服表达",
        "references/workflow-profile-live-presentation-persuasion.md",
    ),
    (
        "teaching-training-knowledge-transfer",
        "教学培训与知识传递",
        "references/workflow-profile-teaching-training-knowledge-transfer.md",
    ),
    (
        "project-lifecycle-reporting",
        "项目全过程汇报",
        "references/workflow-profile-project-lifecycle-reporting.md",
    ),
    (
        "brand-communication-editorial-publishing",
        "品牌传播与编辑出版",
        "references/workflow-profile-brand-communication-editorial-publishing.md",
    ),
    (
        "rule-response-application-defense",
        "规则响应、申报与答辩",
        "references/workflow-profile-rule-response-application-defense.md",
    ),
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


def catalog_rows() -> list[tuple[str, str, str, str]]:
    rows = []
    for line in CATALOG.splitlines():
        match = re.match(
            r"^\| `(?P<profile_id>[^`]+)` \| (?P<name>[^|]+) \| "
            r"(?P<goal>[^|]+) \| `(?P<definition_ref>[^`]+)` \|$",
            line,
        )
        if match:
            rows.append(tuple(value.strip() for value in match.groups()))
    return rows


def definition_text(definition_ref: str) -> str:
    return (SKILL_DIR / definition_ref).read_text(encoding="utf-8")


class WorkflowProfileContractTests(unittest.TestCase):
    def test_catalog_is_lightweight_complete_and_stable(self) -> None:
        rows = catalog_rows()
        self.assertEqual(
            [(profile_id, name, definition_ref) for profile_id, name, _, definition_ref in rows],
            list(EXPECTED_PROFILES),
        )
        self.assertEqual(len({definition_ref for _, _, _, definition_ref in rows}), 9)
        self.assertTrue(all(goal for _, _, goal, _ in rows))
        self.assertLess(len(CATALOG.splitlines()), 50)
        self.assertNotIn("## Foundation Definitions", CATALOG)
        self.assertNotIn("Definition version", CATALOG)
        for heading in REQUIRED_SECTIONS:
            self.assertNotIn(f"## {heading}", CATALOG)

    def test_every_profile_has_one_unique_nonempty_direct_definition(self) -> None:
        expected_files = {definition_ref for _, _, definition_ref in EXPECTED_PROFILES}
        actual_profile_files = {
            f"references/{path.name}"
            for path in REFERENCES.glob("workflow-profile-*.md")
            if path.name != "workflow-profile-contract.md"
        }
        self.assertEqual(actual_profile_files, expected_files)

        for profile_id, name, definition_ref in EXPECTED_PROFILES:
            self.assertEqual(definition_ref.count("/"), 1)
            path = SKILL_DIR / definition_ref
            self.assertTrue(path.is_file(), definition_ref)
            text = definition_text(definition_ref)
            self.assertGreater(len(text.strip()), 1000, definition_ref)
            self.assertEqual(re.findall(r"^# (.+)$", text, re.MULTILINE), [name])
            self.assertIn(f"- `profile_id`: `{profile_id}`", text)
            self.assertIn("Definition version: `1.0`", text)
            self.assertEqual(
                re.findall(r"^## (.+)$", text, re.MULTILINE),
                list(REQUIRED_SECTIONS),
                name,
            )
            for parameter in HORIZONTAL_PARAMETERS:
                self.assertIn(f"`{parameter}`", text, f"{name}: {parameter}")
            self.assertIn(
                f"| `{profile_id}` | {name} | `{definition_ref}` |", CONTRACT
            )

    def test_each_required_definition_section_is_nonempty(self) -> None:
        for _, name, definition_ref in EXPECTED_PROFILES:
            text = definition_text(definition_ref)
            for index, heading in enumerate(REQUIRED_SECTIONS):
                start = text.index(f"## {heading}") + len(f"## {heading}")
                if index + 1 < len(REQUIRED_SECTIONS):
                    end = text.index(f"## {REQUIRED_SECTIONS[index + 1]}", start)
                else:
                    end = len(text)
                self.assertGreater(len(text[start:end].strip()), 20, f"{name}: {heading}")

    def test_skill_routes_clear_and_ambiguous_paths_progressively(self) -> None:
        router = SKILL.split("## Workflow Profile Routing", 1)[1].split(
            "## Project Handoff Overlay", 1
        )[0]
        flat = " ".join(router.split())
        self.assertIn("TaoHtml is one installed Skill", flat)
        self.assertIn("exactly one primary Profile", flat)
        self.assertIn("semantics of eligible inspected material", flat)
        self.assertIn("select it automatically", flat)
        self.assertIn("do not ask a Profile question or read/display the catalog", flat)
        self.assertIn("read only the selected `definition_ref`", flat)
        self.assertIn("do not load any other Profile definition", flat)
        self.assertIn("read `references/workflow-profiles.md`", flat)
        self.assertIn("display all nine exact customer-facing names and primary goals", flat)
        self.assertIn("do not load the other eight definitions", flat)
        self.assertIn("bounded overlays", flat)
        for _, name, _ in EXPECTED_PROFILES:
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

    def test_profile_enums_match_report_ir_without_aliases(self) -> None:
        evidence_enum = set(
            REPORT_IR_SCHEMA["$defs"]["report"]["properties"]["evidence_rigor"]["enum"]
        )
        information_enum = set(
            REPORT_IR_SCHEMA["$defs"]["projection"]["properties"]["information_density"]["enum"]
        )
        motion_enum = set(
            REPORT_IR_SCHEMA["$defs"]["projection"]["properties"]["motion_density"]["enum"]
        )
        self.assertEqual(evidence_enum, {"exploratory", "standard", "formal"})
        self.assertEqual(information_enum, {"low", "medium", "high"})
        self.assertEqual(motion_enum, {"minimal", "moderate", "rich"})
        self.assertIn("No Product-layer aliases are permitted", CONTRACT)

        for _, name, definition_ref in EXPECTED_PROFILES:
            text = definition_text(definition_ref)
            evidence = re.search(r"^- `evidence_rigor`: `([^`]+)`$", text, re.MULTILINE)
            information = re.search(
                r"^- `information_density`: `([^`]+)`$", text, re.MULTILINE
            )
            motion = re.search(r"^- `motion_density`: `([^`]+)`$", text, re.MULTILINE)
            self.assertIn(evidence.group(1), evidence_enum, name)
            self.assertIn(information.group(1), information_enum, name)
            self.assertIn(motion.group(1), motion_enum, name)
            use_mode_line = next(
                line for line in text.splitlines() if line.startswith("- `use_mode`:")
            )
            self.assertIn("only after explicit delegation", use_mode_line, name)

        self.assertIn("`content_length` is not a Profile default", CONTRACT)
        self.assertIn("explicit-delegation requirement", CONTRACT)
        self.assertIn("use-mode or content-length choice", SKILL)

    def test_design_brief_formally_records_profile_result_and_gate_boundaries(self) -> None:
        self.assertIn("## 主要工作场景", BRIEF)
        for field in (
            "主工作场景：九场景目录中的精确客户名称",
            "稳定 profile_id：",
            "definition version：",
            "语义选择依据：",
            "bounded capability overlays：无",
        ):
            self.assertIn(field, BRIEF)
        self.assertIn(
            "Profile selection, confirmation of the complete current Report Design Brief, and Production Authorization as three independent facts",
            BRIEF,
        )
        self.assertIn("meaning-changing continuation", BRIEF)
        self.assertIn("meaning-preserving local continuation", BRIEF)
        self.assertIn("Do not add a Profile-specific confirmation round", BRIEF)
        self.assertIn("Do not expose a Profile or IR questionnaire", BRIEF)

    def test_existing_entry_handoff_brief_and_authorization_gates_are_preserved(self) -> None:
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

    def test_profile_contract_does_not_activate_implementation_layers(self) -> None:
        self.assertIn("Do not add or change Report IR schema fields", CONTRACT)
        self.assertIn("Do not invoke the Report IR route merely because a Profile", CONTRACT)
        self.assertIn("must not copy their schemas, scripts,\nalgorithms", CONTRACT)
        for _, _, definition_ref in EXPECTED_PROFILES:
            text = definition_text(definition_ref)
            ir_boundary = text.split("## IR 映射边界", 1)[1].split(
                "## Runtime/主题使用", 1
            )[0]
            self.assertRegex(
                ir_boundary,
                r"(?:IR (?:engineering )?route is independently authorized|independently authorized IR route)",
            )

    def test_node_one_keeps_both_golden_paths_at_foundation_level(self) -> None:
        for profile_id in (
            "proposal-planning-decision",
            "live-presentation-persuasion",
        ):
            definition_ref = next(
                ref for current_id, _, ref in EXPECTED_PROFILES if current_id == profile_id
            )
            identity = definition_text(definition_ref).split("## 身份与版本", 1)[1].split(
                "## 适用目标", 1
            )[0]
            self.assertIn("foundation definition only", identity)
            self.assertIn("Golden Path detailed workflow", identity)
            self.assertIn("outside this engineering node", identity)


if __name__ == "__main__":
    unittest.main()
