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

DETAILED_PROFILES = {
    "formal-submission-writing": "2.0",
    "proposal-planning-decision": "2.0",
    "live-presentation-persuasion": "2.0",
    "rule-response-application-defense": "2.0",
}

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
            expected_version = DETAILED_PROFILES.get(profile_id, "1.0")
            self.assertIn(f"Definition version: `{expected_version}`", text)
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
        self.assertNotIn("作为正式 HTML 制作授权", BRIEF)
        self.assertIn("明确确认只绑定此版本的完整设计简报与当前会话记录", BRIEF)
        self.assertIn(
            "允许进入独立的 current-file Production Authorization 检查", BRIEF
        )
        self.assertIn("设计简报确认不是正式 HTML 制作授权", BRIEF)
        self.assertIn(
            "只有该检查允许 `formal-html` 后，才能开始正式制作", BRIEF
        )

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
                " ".join(ir_boundary.split()),
                r"(?:IR (?:engineering )?route is independently authorized|independently authorized IR route)",
            )

    def test_engineering_nodes_implement_exactly_four_detailed_golden_paths(self) -> None:
        self.assertEqual(
            set(DETAILED_PROFILES),
            {
                "formal-submission-writing",
                "proposal-planning-decision",
                "live-presentation-persuasion",
                "rule-response-application-defense",
            },
        )
        for profile_id, expected_version in DETAILED_PROFILES.items():
            definition_ref = next(
                ref for current_id, _, ref in EXPECTED_PROFILES if current_id == profile_id
            )
            text = definition_text(definition_ref)
            identity = text.split("## 身份与版本", 1)[1].split(
                "## 适用目标", 1
            )[0]
            self.assertIn(f"Definition version: `{expected_version}`", identity)
            self.assertIn("Status: detailed/implemented Golden Path", identity)
            self.assertIn("### Golden Path", text)
            self.assertIn("### 设计简报增量", text)

        for profile_id, _, definition_ref in EXPECTED_PROFILES:
            if profile_id in DETAILED_PROFILES:
                continue
            identity = definition_text(definition_ref).split(
                "## 身份与版本", 1
            )[1].split("## 适用目标", 1)[0]
            self.assertIn("foundation definition", identity, profile_id)
            self.assertNotIn("Status: detailed/implemented Golden Path", identity)

        self.assertEqual(len(EXPECTED_PROFILES) - len(DETAILED_PROFILES), 5)
        self.assertIn("four detailed/implemented Golden Paths", CONTRACT)
        self.assertIn("the other\n  five Profiles remain foundation definitions", CONTRACT)

    def test_long_detailed_profiles_have_top_level_contents(self) -> None:
        for profile_id in DETAILED_PROFILES:
            definition_ref = next(
                ref for current_id, _, ref in EXPECTED_PROFILES if current_id == profile_id
            )
            text = definition_text(definition_ref)
            self.assertGreater(len(text.splitlines()), 100, profile_id)
            identity = text.split("## 身份与版本", 1)[1].split(
                "## 适用目标", 1
            )[0]
            self.assertIn("### 目录", identity, profile_id)
            self.assertEqual(
                len(re.findall(r"^- \[[^]]+\]\(#[^)]+\)$", identity, re.MULTILINE)),
                len(REQUIRED_SECTIONS) - 1,
                profile_id,
            )

    def test_detailed_profiles_reuse_shared_flow_and_on_demand_loading(self) -> None:
        router = SKILL.split("## Workflow Profile Routing", 1)[1].split(
            "## Project Handoff Overlay", 1
        )[0]
        self.assertIn("When the selected definition declares a detailed/implemented", router)
        self.assertIn("after loading that one\ndefinition", router)
        self.assertIn("never\nloads another Profile", router)
        for profile_id in DETAILED_PROFILES:
            definition_ref = next(
                ref for current_id, _, ref in EXPECTED_PROFILES if current_id == profile_id
            )
            text = definition_text(definition_ref)
            for shared_ref in (
                "intake-workflow.md",
                "design-brief-template.md",
                "production-authorization.md",
                "process-playbook.md",
                "runtime-contract.md",
                "project-handoff.md",
            ):
                self.assertIn(shared_ref, text, profile_id)
            self.assertIn("first runnable direct-HTML artifact", text, profile_id)
            self.assertIn("Profile-specific confirmation round", text, profile_id)

    def test_proposal_golden_path_covers_decision_integrity_and_delivery(self) -> None:
        text = definition_text(
            "references/workflow-profile-proposal-planning-decision.md"
        )
        for marker in (
            "who makes the decision",
            "why a decision is required now",
            "maintaining the status quo means",
            "客户提供的选项",
            "Agent 提议的候选方案",
            "已淘汰方案",
            "Do not invent weights",
            "never manufacture a full matrix",
            "facts, assumptions, and projections distinct",
            "Never change weights after seeing the result",
            "failure conditions",
            "residual risks",
            "resource/time boundary",
            "next decision",
            "only if the desired result requires an external",
        ):
            self.assertIn(marker, text)

        for field in (
            "`决策问题`",
            "`决策人及责任边界`",
            "`选项集合及来源状态`",
            "`评价标准`",
            "`关键取舍`",
            "`推荐依据`",
            "`实施责任`",
            "`风险与失效条件`",
        ):
            self.assertIn(field, text)

    def test_live_golden_path_covers_audience_motion_and_presenter_qa(self) -> None:
        text = definition_text(
            "references/workflow-profile-live-presentation-persuasion.md"
        )
        for marker in (
            "audience's current understanding",
            "the understanding, decision, or action",
            "presenter's relationship",
            "never ask for it by default",
            "Build the oral story spine",
            "make decisive evidence visible when",
            "complete reading final state",
            "Do not force a sales CTA",
            "Generate speaker-support content only when",
            "existing `fragment-v1` contract",
            "whole-page navigation",
            "per-page return-state",
            "target presentation viewports",
        ):
            self.assertIn(marker, text)

        for field in (
            "`受众当前状态`",
            "`目标移动`",
            "`核心主张`",
            "`决定性证据`",
            "`主要阻力`",
            "`故事脊柱`",
            "`现场约束`",
            "`动效/口播意图`",
            "`最终行动`",
        ):
            self.assertIn(field, text)

    def test_formal_submission_golden_path_covers_authority_and_consistency(self) -> None:
        text = definition_text(
            "references/workflow-profile-formal-submission-writing.md"
        )
        flat = " ".join(text.split())
        for marker in (
            "defined recipient or reporting body",
            "institutional purpose",
            "formal-use boundary",
            "A formal tone",
            "mandatory chapters, fields, statements",
            "agreed or customary structure",
            "authorship, responsibility, approval, sign-off",
            "confidentiality, classification, retention, and distribution restrictions only",
            "`权威要求`",
            "`客户材料`",
            "`外部证据`",
            "`Agent 补全`",
            "An ordinary reference",
            "Trace every actual mandatory item",
            "task/mandate, basis, facts, analysis, conclusion or",
            "Keep source facts, interpretation, and proposed or recommended",
            "Never use `创作性补全`",
            "`required-section completeness`",
            "delivery wording is accurate",
        ):
            self.assertIn(marker, flat)

        for field in (
            "`正式对象与目的`",
            "`必须覆盖项`",
            "`权威来源及版本`",
            "`术语与口径`",
            "`责任与签批边界`",
            "`格式/时间/保密约束`",
            "`关键缺口与风险`",
        ):
            self.assertIn(field, text)

    def test_rule_response_golden_path_covers_traceability_and_honest_gaps(self) -> None:
        text = definition_text(
            "references/workflow-profile-rule-response-application-defense.md"
        )
        flat = " ".join(text.split())
        for marker in (
            "Use as primary only when success is materially governed",
            "`文件存在` does not mean `规则已核验`",
            "`资格/一票否决项`",
            "`强制响应项`",
            "`评分项与权重`",
            "`加分项`",
            "`格式/篇幅/提交约束`",
            "`答辩要求`",
            "Do not invent a category",
            "original wording or accurate paraphrase plus rule locator",
            "supporting evidence and evidence locator",
            "`已满足`, `部分满足`",
            "possessing a document",
            "not a new TaoHtml Schema",
            "A missing mandatory proof is not an ordinary gap eligible for creative supplements",
            "`gap-analysis / preparation draft`",
            "not a compliant submit-ready final artifact",
            "reviewer can locate each applicable response and proof",
            "do not force a fixed outline, page count, matrix, or card layout",
            "Never invent a score, weight, qualification, certificate",
            "existing `fragment-v1`",
            "Do not promise dual-screen presenter view",
            "defense final pages, staged intermediate states",
        ):
            self.assertIn(marker, flat)

        for field in (
            "`规则身份与版本`",
            "`申报/评审目标`",
            "`资格与强制项`",
            "`评分与权重`",
            "`响应—证据状态`",
            "`格式/截止/答辩约束`",
            "`责任边界`",
            "`缺口/冲突与提交风险`",
        ):
            self.assertIn(field, text)

    def test_rule_response_submit_ready_requires_actual_submission_compatibility(self) -> None:
        text = definition_text(
            "references/workflow-profile-rule-response-application-defense.md"
        )
        design_ready = text.split("## design-ready 条件", 1)[1].split(
            "## 叙事任务", 1
        )[0]
        golden_path = text.split("### Golden Path", 1)[1].split(
            "### 页面任务与评审核验重点", 1
        )[0]
        evidence = text.split("## 证据规则", 1)[1].split(
            "## 横向参数默认值", 1
        )[0]
        qa = text.split("## QA 验收", 1)[1].split(
            "## 能力叠加与冲突处理", 1
        )[0]

        design_ready_flat = " ".join(design_ready.split())
        golden_path_flat = " ".join(golden_path.split())
        evidence_flat = " ".join(evidence.split())
        qa_flat = " ".join(qa.split())

        for marker in (
            "`actual deliverable format/channel compatibility`",
            "exact TaoHtml output format and package are accepted by the applicable submission channel",
            "deadline and every other mandatory submission constraint",
            "no missing mandatory proof or unsatisfied mandatory submission constraint",
        ):
            self.assertIn(marker, design_ready_flat)

        for marker in (
            "mandatory proof is sufficient",
            "actual TaoHtml deliverable format/package is accepted by the applicable submission channel",
            "deadline plus every other mandatory submission constraint is actually satisfied",
            "Disclosure records the failure; it does not satisfy the constraint or make the artifact submit-ready",
        ):
            self.assertIn(marker, golden_path_flat)

        self.assertIn(
            "A locally openable HTML or successful current-file Production Authorization does not prove channel acceptance",
            evidence_flat,
        )
        self.assertIn(
            "Disclosure of incompatibility records a gap; it never satisfies it",
            evidence_flat,
        )

        for marker in (
            "for a formal compliant or submit-ready result",
            "actual delivered format/package is accepted by the applicable submission channel",
            "none may pass merely by being disclosed",
            "disclosure does not make the artifact compliant or submit-ready",
            "the user has explicitly reclassified it as `gap-analysis / preparation draft`",
            "diagnostic draft may disclose the unsatisfied items",
        ):
            self.assertIn(marker, qa_flat)
        self.assertNotIn(
            "constraints are satisfied or disclosed with their submission impact",
            qa_flat,
        )

    def test_detailed_profiles_stay_inside_ir_runtime_and_layout_boundaries(self) -> None:
        schema_properties = REPORT_IR_SCHEMA["properties"]
        for forbidden_property in (
            "workflow_profile",
            "decision_score",
            "audience_movement",
            "formal_recipient",
            "mandatory_section",
            "rule_requirement",
            "compliance_status",
            "score_weight",
        ):
            self.assertNotIn(forbidden_property, schema_properties)

        for profile_id in DETAILED_PROFILES:
            definition_ref = next(
                ref for current_id, _, ref in EXPECTED_PROFILES if current_id == profile_id
            )
            text = definition_text(definition_ref)
            flat = " ".join(text.split())
            self.assertIn("Direct HTML remains the default", flat, profile_id)
            self.assertIn("independently authorized", flat, profile_id)
            self.assertIn("Do not add", flat, profile_id)
            self.assertIn("Report IR Schema", flat, profile_id)
            self.assertIn("Compiler branch", flat, profile_id)
            self.assertIn("cross-page morphing", flat, profile_id)
            self.assertIn("no required", flat, profile_id)
            self.assertIn("page count", flat, profile_id)

    def test_design_brief_uses_one_selected_profile_increment_only(self) -> None:
        self.assertIn("## 场景特有决策", BRIEF)
        self.assertIn("只写入当前主 Profile", BRIEF)
        self.assertIn("不展示未选 Profile 的字段", BRIEF)
        self.assertIn("not a second brief or confirmation round", BRIEF)
        for unselected_field in (
            "决策问题",
            "受众当前状态",
            "正式对象与目的",
            "规则身份与版本",
        ):
            self.assertNotIn(unselected_field, BRIEF)


if __name__ == "__main__":
    unittest.main()
