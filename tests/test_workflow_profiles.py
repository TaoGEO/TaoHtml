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
    "research-analysis-argumentation": "2.0",
    "periodic-operations-reporting": "2.0",
    "proposal-planning-decision": "2.0",
    "live-presentation-persuasion": "2.0",
    "teaching-training-knowledge-transfer": "2.0",
    "project-lifecycle-reporting": "2.0",
    "brand-communication-editorial-publishing": "2.0",
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
        self.assertIn("adds no IR questionnaire", CONTRACT)
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
        self.assertIn("displayed to the customer as 少量 / 适中 / 丰富", CONTRACT)
        self.assertIn(
            "the customer must select it or explicitly delegate the choice", CONTRACT
        )
        self.assertIn(
            "never turn\na Profile's `motion_density` recommendation into a selected value",
            CONTRACT,
        )

        for _, name, definition_ref in EXPECTED_PROFILES:
            text = definition_text(definition_ref)
            evidence = re.search(r"^- `evidence_rigor`: `([^`]+)`$", text, re.MULTILINE)
            information = re.search(
                r"^- `information_density`: `([^`]+)`$", text, re.MULTILINE
            )
            motion = re.search(
                r"^- `motion_density`: `([^`]+)` recommendation only; "
                r"require customer selection or explicit delegation$",
                text,
                re.MULTILINE,
            )
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
        self.assertIn("明确确认只绑定此版本的完整设计简报", BRIEF)
        self.assertIn("当前内置主题/不适用状态与动效决定", BRIEF)
        self.assertIn("任一设计决定变更后都必须更新并重新确认", BRIEF)
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
        self.assertIn("Profile selection itself never activates Report IR", CONTRACT)
        self.assertIn("Direct HTML from the\n  default production path", CONTRACT)
        self.assertIn("one generic top-level `workflow_profile` binding", CONTRACT)
        self.assertIn("Report IR `1.0` remains legacy unbound", CONTRACT)
        self.assertIn("does not replace\n  the Report Design Brief", CONTRACT)
        self.assertIn("Profile-triggered Compiler branch", CONTRACT)
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

    def test_engineering_nodes_implement_exactly_nine_detailed_golden_paths(self) -> None:
        self.assertEqual(
            set(DETAILED_PROFILES),
            {
                "formal-submission-writing",
                "research-analysis-argumentation",
                "periodic-operations-reporting",
                "proposal-planning-decision",
                "live-presentation-persuasion",
                "teaching-training-knowledge-transfer",
                "project-lifecycle-reporting",
                "brand-communication-editorial-publishing",
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

        self.assertEqual(len(EXPECTED_PROFILES) - len(DETAILED_PROFILES), 0)
        self.assertIn("all nine Profiles are\n  detailed/implemented Golden Paths", CONTRACT)
        self.assertIn("zero current Profiles remain foundation\n  definitions", CONTRACT)
        self.assertIn("A foundation definition remains usable", CONTRACT)

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

    def test_research_golden_path_routes_by_real_question_and_deliverable(self) -> None:
        text = definition_text(
            "references/workflow-profile-research-analysis-argumentation.md"
        )
        flat = " ".join(text.split())
        for marker in (
            "main job is to answer a substantive question",
            "test or bound a hypothesis",
            "explain a mechanism",
            "form a professional conclusion",
            "Many citations, professional tone, data charts",
            "use `proposal-planning-decision`",
            "use `rule-response-application-defense`",
            "use `periodic-operations-reporting`",
            "read independently or presented under the already confirmed `use_mode`",
            "methods actually used",
            "Claim–Evidence–Source relationships",
            "Its delivery class must remain honest",
            "no required chapter count, page count, thesis format, or journal structure",
        ):
            self.assertIn(marker, flat)

        for field in (
            "`研究问题与决策语境`",
            "`范围与术语口径`",
            "`方法与已检查材料`",
            "`核心 Claim–Evidence 状态`",
            "`替代解释/冲突`",
            "`目标结论强度`",
            "`关键局限/缺口`",
            "`交付边界`",
        ):
            self.assertIn(field, text)

    def test_research_method_evidence_causality_and_provisional_boundaries(self) -> None:
        text = definition_text(
            "references/workflow-profile-research-analysis-argumentation.md"
        )
        required = text.split("## 所需信息", 1)[1].split(
            "## design-ready 条件", 1
        )[0]
        design_ready = text.split("## design-ready 条件", 1)[1].split(
            "## 叙事任务", 1
        )[0]
        evidence = text.split("## 证据规则", 1)[1].split(
            "## 横向参数默认值", 1
        )[0]
        qa = text.split("## QA 验收", 1)[1].split(
            "## 能力叠加与冲突处理", 1
        )[0]

        required_flat = " ".join(required.split())
        for marker in (
            "methods actually used and their execution status",
            "methods only planned, proposed, described by a source, or not completed",
            "File availability, a method section, or an earlier summary does not prove method completion",
            "观察/事实 (observation / fact)",
            "推论 (inference)",
            "假设 (hypothesis)",
            "推演/模拟 (projection / simulation)",
            "建议 (recommendation)",
            "未决冲突 (unresolved conflict)",
            "one largest still-missing item",
            "Critical facts, source identity, method completion, sample, data, calculations",
        ):
            self.assertIn(marker, required_flat)

        design_ready_flat = " ".join(design_ready.split())
        for marker in (
            "method execution, evidence, and claim-fit reach the claimed strength",
            "do not pretend verification is complete",
            "explicitly accepts an exploratory/preliminary scope",
            "must remain visible in the brief, every conclusion-bearing page, delivery wording, and Handoff",
            "must not be packaged as a validated final study",
        ):
            self.assertIn(marker, design_ready_flat)

        evidence_flat = " ".join(evidence.split())
        for marker in (
            "File existence is not fact verification",
            "a secondary summary is not automatically original evidence",
            "source credibility is not proof that the source fits the current Claim",
            "supporting evidence together with limitations, counterevidence, and alternative explanations",
            "supports, limits, refutes, or supplies background",
            "Correlation or timing alone cannot be upgraded to proved causation",
            "Never invent data, samples, interviews, surveys, experiments",
        ):
            self.assertIn(marker, evidence_flat)

        qa_flat = " ".join(qa.split())
        for marker in (
            "`question-to-conclusion`",
            "`method-to-result`",
            "`Claim–Evidence–Source`",
            "correlation, mechanism evidence, and causal conclusions remain distinct",
            "counterevidence, alternative explanations, conflicts",
            "conclusion strength never exceeds the completed method, evidence, or claim-fit",
            "exploratory/preliminary results remain non-final",
            "no file's existence, polished citation, or secondary summary is treated as proof",
        ):
            self.assertIn(marker, qa_flat)

    def test_periodic_operations_routes_by_operating_cadence_and_management_need(self) -> None:
        text = definition_text(
            "references/workflow-profile-periodic-operations-reporting.md"
        )
        flat = " ".join(text.split())
        for marker in (
            "weekly, monthly, quarterly, annual, or other real operating cadence",
            "presence of KPIs, dates, charts, or an “annual report” label does not by itself",
            "Use `brand-communication-editorial-publishing`",
            "Use `project-lifecycle-reporting`",
            "Use `proposal-planning-decision`",
            "what happened in the current period",
            "which drivers are directly supported",
            "which decisions and next actions are required, who owns them",
            "no required chapter count, page count, KPI-card count, dashboard shape",
        ):
            self.assertIn(marker, flat)

        for field in (
            "`经营周期与 cutoff`",
            "`管理问题`",
            "`指标与口径`",
            "`比较基准`",
            "`数据完整性与修订`",
            "`关键差异/驱动`",
            "`风险机会`",
            "`决策/行动/owner`",
            "`关键限制`",
            "`交付边界`",
        ):
            self.assertIn(field, text)

    def test_periodic_metric_comparison_driver_and_data_gap_boundaries(self) -> None:
        text = definition_text(
            "references/workflow-profile-periodic-operations-reporting.md"
        )
        required = text.split("## 所需信息", 1)[1].split(
            "## design-ready 条件", 1
        )[0]
        design_ready = text.split("## design-ready 条件", 1)[1].split(
            "## 叙事任务", 1
        )[0]
        evidence = text.split("## 证据规则", 1)[1].split(
            "## 横向参数默认值", 1
        )[0]
        qa = text.split("## QA 验收", 1)[1].split(
            "## 能力叠加与冲突处理", 1
        )[0]

        required_flat = " ".join(required.split())
        for marker in (
            "reporting period, reporting cutoff, and timezone",
            "whether data is frozen, final, provisional, still updating, restated",
            "exact definition, unit/currency, numerator and denominator",
            "source identity/version, cutoff, aggregation level and method, and revision status",
            "`actual`",
            "`target / budget`",
            "`forecast`",
            "`projection / simulation`",
            "`restated / revised data`",
            "`unknown | withheld | pending`",
            "recalculate on a common basis, provide an honest bridge, or label the comparison `not comparable`",
            "`数据直接支持的 driver`",
            "`基于材料的解释`",
            "`待验证 hypothesis`",
            "one largest still-missing data item",
            "explicitly accepts a `preliminary / data-gap review`",
            "Do not invent performance, targets, budgets, causes, risks, owners, actions",
        ):
            self.assertIn(marker, required_flat)

        design_ready_flat = " ".join(design_ready.split())
        for marker in (
            "definition, unit/currency, numerator/denominator",
            "selected for the real management question without cherry-picking",
            "recalculated, bridged, or labeled not comparable",
            "Supported metrics may remain visible while affected conclusions are withheld or pending",
            "must not be packaged as a complete formal period review",
        ):
            self.assertIn(marker, design_ready_flat)

        evidence_flat = " ".join(evidence.split())
        for marker in (
            "Do not mix total and component, growth rate and percentage-point change",
            "actual, target/budget, forecast, projection/simulation, restated/revised data",
            "Correlation and timing do not automatically prove causation",
            "not to maximize a favorable narrative",
            "Never turn a plan or ongoing action into completed work or verified effect",
            "Do not leave an old chart beside a newly restated figure",
        ):
            self.assertIn(marker, evidence_flat)

        qa_flat = " ".join(qa.split())
        for marker in (
            "`metric math`",
            "numerator/denominator, unit/currency, aggregation, time interval, cutoff",
            "year-over-year/period-over-period, percentage/percentage point",
            "data source/version, cutoff, revision/restatement",
            "comparisons preserve definition, scope, currency, time window, denominator",
            "driver language matches evidence strength",
            "never used silently for a formal conclusion",
            "preliminary/data-gap results remain explicitly non-final",
        ):
            self.assertIn(marker, qa_flat)

    def test_teaching_routes_by_learning_transfer_and_records_brief_increment(self) -> None:
        text = definition_text(
            "references/workflow-profile-teaching-training-knowledge-transfer.md"
        )
        flat = " ".join(text.split())
        for marker in (
            "main job is to help a defined learner group",
            "acquire, understand, retain, practice, or apply specific knowledge",
            "“Make a training PPT”",
            "presence of an instructor",
            "does not by itself establish this Profile",
            "use `live-presentation-persuasion` or `brand-communication-editorial-publishing`",
            "use `research-analysis-argumentation`",
            "read or presented under the already confirmed `use_mode`",
            "does not by itself prove that any learner has attended, mastered, passed",
            "no required course length, chapter count, page count, exercise count",
        ):
            self.assertIn(marker, flat)

        for field in (
            "`学习者与已有基础`",
            "`目标能力/可观察表现`",
            "`先备知识与范围边界`",
            "`学习进阶/概念依赖`",
            "`关键示例、误解与失败模式`",
            "`练习/回顾与反馈方式`",
            "`授课/自学环境及讲师支持`",
            "`完成/评价边界`",
            "`关键风险与交付边界`",
        ):
            self.assertIn(field, text)

    def test_teaching_design_golden_path_evidence_and_qa_are_separate(self) -> None:
        text = definition_text(
            "references/workflow-profile-teaching-training-knowledge-transfer.md"
        )
        required = text.split("## 所需信息", 1)[1].split(
            "## design-ready 条件", 1
        )[0]
        design_ready = text.split("## design-ready 条件", 1)[1].split(
            "## 叙事任务", 1
        )[0]
        golden_path = text.split("### Golden Path", 1)[1].split(
            "### 页面任务与学习表达", 1
        )[0]
        evidence = text.split("## 证据规则", 1)[1].split(
            "## 横向参数默认值", 1
        )[0]
        qa = text.split("## QA 验收", 1)[1].split(
            "## 能力叠加与冲突处理", 1
        )[0]

        required_flat = " ".join(required.split())
        for marker in (
            "learner group and relevant differences",
            "existing baseline, prerequisite knowledge",
            "target capability and observable performance",
            "having seen or heard something, understanding it, being able to explain it",
            "concept, rule, procedure, or skill dependencies",
            "correct examples, worked examples, counterexamples, failure modes",
            "high-risk knowledge, operational steps, safety/compliance points",
            "Do not ask for mode, duration, instructor support, practice, or assessment by default",
            "one largest still-missing item",
            "Never creatively complete a real rule, factual teaching claim",
        ):
            self.assertIn(marker, required_flat)

        design_ready_flat = " ".join(design_ready.split())
        for marker in (
            "learner group, existing baseline, prerequisite knowledge",
            "concept/procedure dependencies, progression logic",
            "source identity, checked scope, and actual strength",
            "practice or review need, instructions, expected response, answer/feedback behavior",
            "does not mean a learner has completed or mastered it",
            "disclosure cannot turn invented knowledge into instruction",
        ):
            self.assertIn(marker, design_ready_flat)

        golden_path_flat = " ".join(golden_path.split())
        for marker in (
            "Audit knowledge and dependencies",
            "Derive the learning progression",
            "activating prior knowledge or establishing meaning",
            "stepwise demonstration or worked example",
            "learner practice, judgment, or review",
            "misconception correction",
            "Align examples, practice, and feedback",
            "Do not assign a unique model answer to an open question",
            "Do not implement automatic scoring, learner state, completion tracking, certificates, an LMS, or a quiz engine",
        ):
            self.assertIn(marker, golden_path_flat)

        evidence_flat = " ".join(evidence.split())
        for marker in (
            "Bind target knowledge, factual rules, operational procedures",
            "Keep source fact, interpretation, editorial simplification, illustrative situation",
            "Never invent knowledge, a source, quotation, customer, learner record",
            "Practice instructions, answer, feedback, explanation, and review must not contradict",
            "For an open question, state the evaluation lens",
        ):
            self.assertIn(marker, evidence_flat)

        qa_flat = " ".join(qa.split())
        for marker in (
            "`objective-content-example-practice-review alignment`",
            "learner baseline, prerequisite order, concept/procedure dependency",
            "worked examples, counterexamples, failure modes, fictional situations",
            "practice instruction, prompt, expected response, answer, feedback",
            "reading mode exposes every necessary final state",
            "no learner attendance, completion, score, pass, mastery, certification, or effect is claimed",
        ):
            self.assertIn(marker, qa_flat)

    def test_project_routes_by_specific_governance_and_records_brief_increment(self) -> None:
        text = definition_text(
            "references/workflow-profile-project-lifecycle-reporting.md"
        )
        flat = " ".join(text.split())
        for marker in (
            "govern one specific project",
            "objective, scope, baseline, phase, progress, changes, risks, decisions, results, or closeout state",
            "A project name, timeline, milestone list",
            "does not by itself establish this Profile",
            "Use `periodic-operations-reporting`",
            "Use `proposal-planning-decision`",
            "Use `rule-response-application-defense`",
            "adapted to the project's actual phase",
            "delivered, accepted, and closed states kept distinct",
            "no required project method, phase count, chapter count, page count",
        ):
            self.assertIn(marker, flat)

        for field in (
            "`项目目标、sponsor/受众与治理目的`",
            "`baseline/范围版本`",
            "`当前阶段与 reporting cutoff`",
            "`里程碑/交付物及状态证据`",
            "`变化/偏差与影响`",
            "`issue/risk/dependency`",
            "`所需决策、行动与 owner`",
            "`验收/收尾条件、未结义务`",
            "`关键缺口与状态结论`",
            "`交付边界`",
        ):
            self.assertIn(field, text)

    def test_project_design_golden_path_evidence_and_qa_are_separate(self) -> None:
        text = definition_text(
            "references/workflow-profile-project-lifecycle-reporting.md"
        )
        required = text.split("## 所需信息", 1)[1].split(
            "## design-ready 条件", 1
        )[0]
        design_ready = text.split("## design-ready 条件", 1)[1].split(
            "## 叙事任务", 1
        )[0]
        golden_path = text.split("### Golden Path", 1)[1].split(
            "### 页面任务与项目治理表达", 1
        )[0]
        evidence = text.split("## 证据规则", 1)[1].split(
            "## 横向参数默认值", 1
        )[0]
        qa = text.split("## QA 验收", 1)[1].split(
            "## 能力叠加与冲突处理", 1
        )[0]

        required_flat = " ".join(required.split())
        for marker in (
            "scope baseline, baseline version/date",
            "current phase and the evidence that establishes it",
            "reporting cutoff and applicable timezone",
            "`planned`",
            "`in progress`",
            "`blocked`",
            "`delivered`",
            "`accepted`",
            "`closed`",
            "Project Handoff is a continuation and transition index, not external project acceptance evidence",
            "`baseline`, `current`, and `forecast`",
            "`proposed change`",
            "`approved change`",
            "`implemented change`",
            "`issue`, `risk`, `dependency`, `decision`, and `action`",
            "`progress / closeout-readiness draft`",
        ):
            self.assertIn(marker, required_flat)

        design_ready_flat = " ".join(design_ready.split())
        for marker in (
            "scope baseline, version/date",
            "baseline/current/forecast distinctions",
            "proposed/approved/implemented changes",
            "issues, risks, dependencies, decisions, and actions classified honestly",
            "only when delivery, acceptance, remaining obligations, and closure conditions are evidenced",
            "must not be packaged as accepted or closed",
        ):
            self.assertIn(marker, design_ready_flat)

        golden_path_flat = " ".join(golden_path.split())
        for marker in (
            "Reconstruct the evidence-backed state",
            "Keep file existence, delivered, accepted, and closed distinct",
            "Separate time and change layers",
            "Reconcile governance categories",
            "Choose the honest project branch",
            "At closeout, emphasize delivery, acceptance, unresolved obligations",
            "A deliverable's existence does not establish acceptance, benefit, or impact",
        ):
            self.assertIn(marker, golden_path_flat)

        evidence_flat = " ".join(evidence.split())
        for marker in (
            "Bind every material baseline, phase, milestone, deliverable, date, completion percentage",
            "Project Handoff does not equal stakeholder acceptance",
            "Keep planned, in progress, blocked, delivered, accepted, and closed distinct",
            "Classify issue, risk, dependency, decision, and action honestly",
            "Do not invent milestones, dates, percentages, status, owners, approvals, results, benefits, acceptance, or closure",
        ):
            self.assertIn(marker, evidence_flat)

        qa_flat = " ".join(qa.split())
        for marker in (
            "`baseline/current/forecast`",
            "milestone/deliverable identity, planned and actual dates, state, owner, completion percentage",
            "proposed, approved, or implemented",
            "issues, risks, dependencies, decisions, and actions are classified distinctly",
            "neither file existence nor Project Handoff is used as acceptance",
            "remains unaccepted and unclosed throughout",
        ):
            self.assertIn(marker, qa_flat)

    def test_brand_routes_by_external_communication_and_records_brief_increment(self) -> None:
        text = definition_text(
            "references/workflow-profile-brand-communication-editorial-publishing.md"
        )
        flat = " ".join(text.split())
        for marker in (
            "communicate a brand, idea, product launch, event/project story, or editorial subject",
            "external or broad audience",
            "A desire for a beautiful page, brand colors, a Logo",
            "does not by itself establish this Profile",
            "Use `live-presentation-persuasion`",
            "Use `formal-submission-writing` or `rule-response-application-defense`",
            "Use `teaching-training-knowledge-transfer`",
            "high-quality offline editorial HTML artifact or presentation-ready brand deck",
            "TaoHtml delivery does not mean the artifact has been hosted, published, distributed",
            "no required campaign structure, chapter count, page count, magazine layout",
        ):
            self.assertIn(marker, flat)

        for field in (
            "`外部受众与传播/出版场景`",
            "`核心传播目标、central message 与 story angle`",
            "`品牌/主体身份、语气与视觉边界`",
            "`approved/source-backed/unverified claims`",
            "`素材来源、权利与真实资产保护`",
            "`引用/证言状态`",
            "`CTA/action path`",
            "`公开/内部使用边界、分发限制`",
            "`关键缺口、风险与交付边界`",
        ):
            self.assertIn(field, text)

    def test_brand_design_golden_path_evidence_and_qa_are_separate(self) -> None:
        text = definition_text(
            "references/workflow-profile-brand-communication-editorial-publishing.md"
        )
        required = text.split("## 所需信息", 1)[1].split(
            "## design-ready 条件", 1
        )[0]
        design_ready = text.split("## design-ready 条件", 1)[1].split(
            "## 叙事任务", 1
        )[0]
        golden_path = text.split("### Golden Path", 1)[1].split(
            "### 页面任务与传播表达", 1
        )[0]
        evidence = text.split("## 证据规则", 1)[1].split(
            "## 横向参数默认值", 1
        )[0]
        qa = text.split("## QA 验收", 1)[1].split(
            "## 能力叠加与冲突处理", 1
        )[0]

        required_flat = " ".join(required.split())
        for marker in (
            "central message, story angle",
            "brand, entity, product, project, or event identity",
            "`approved claim`",
            "`source-backed fact`",
            "`interpretation / editorial framing`",
            "`projection`",
            "`illustrative content`",
            "`unverified claim`",
            "Access to an image does not equal permission to use it",
            "Do not replace or materially alter a real Logo, screenshot, photograph",
            "Bind a quotation or testimonial to its exact original text",
            "Add a CTA or conversion path only when",
            "Call the artifact `public / publication-ready` only when",
            "`internal review / editorial draft`",
        ):
            self.assertIn(marker, required_flat)

        design_ready_flat = " ".join(design_ready.split())
        for marker in (
            "brand/entity/product/project identity, naming, tone, validated visual binding",
            "every key approved/source-backed/unverified claim",
            "usage-rights or permission boundary",
            "exact quotation/testimonial text, identity, permission/public status",
            "exact verified real action path only when",
            "must not be packaged as public or publication-ready",
        ):
            self.assertIn(marker, design_ready_flat)

        golden_path_flat = " ".join(golden_path.split())
        for marker in (
            "Audit claims before amplification",
            "Audit assets and rights",
            "Protect real Logos, screenshots, photographs",
            "Verify quotations and optional action",
            "without forcing a sales CTA",
            "Choose the honest publication branch",
            "earning attention",
            "building credibility through proof, story, and identity",
            "does not automatically create a magazine style",
        ):
            self.assertIn(marker, golden_path_flat)

        evidence_flat = " ".join(evidence.split())
        for marker in (
            "Bind every material brand/entity/product/project identity, key claim",
            "Keep approved claim, source-backed fact, editorial interpretation",
            "Record asset provenance separately from usage rights",
            "Accessibility, download, or public visibility does not equal permission",
            "Never replace, redraw, or factually alter a real Logo",
            "Bind quotations and testimonials to exact text",
            "preserve the exact verified link, decoded QR value, email, phone number",
        ):
            self.assertIn(marker, evidence_flat)

        qa_flat = " ".join(qa.split())
        for marker in (
            "brand/entity/product/project identity, naming, Logo, brand bar, header/footer",
            "every key claim, quotation, testimonial, customer, case, data point, award, ranking",
            "each asset records provenance, inspection coverage, usage/permission status",
            "quotation/testimonial text, identity, permission/public state",
            "every applicable CTA/action path has matching visible text, link or decoded QR",
            "has no forced sales CTA",
            "remains not for publication or external use throughout",
            "without claiming hosting, publication, distribution, tracking, analytics, or conversion",
        ):
            self.assertIn(marker, qa_flat)

    def test_final_golden_paths_keep_shared_gates_direct_html_and_no_new_systems(self) -> None:
        for profile_id, forbidden_systems in (
            (
                "teaching-training-knowledge-transfer",
                ("LMS", "quiz engine", "automatic scoring", "learner state"),
            ),
            (
                "project-lifecycle-reporting",
                ("project database", "live timeline", "Gantt engine", "automatic refresh"),
            ),
            (
                "brand-communication-editorial-publishing",
                ("CMS", "public website", "hosting", "tracking", "analytics"),
            ),
        ):
            definition_ref = next(
                ref for current_id, _, ref in EXPECTED_PROFILES if current_id == profile_id
            )
            text = definition_text(definition_ref)
            flat = " ".join(text.split())
            for marker in (
                "one existing Report Design Brief",
                "do not create a second brief",
                "Profile-specific confirmation round",
                "Profile selection, complete-brief confirmation, and current-file Production Authorization remain three independent facts",
                "Direct HTML remains the default",
                "IR engineering route is independently authorized",
                "Do not add",
                "Report IR Schema",
                "Profile-triggered IR path",
                "Compiler branch",
                "first runnable direct-HTML artifact",
            ):
                self.assertIn(marker, flat, profile_id)
            for forbidden_system in forbidden_systems:
                self.assertIn(forbidden_system, flat, profile_id)

    def test_new_golden_paths_keep_one_brief_direct_html_and_engineering_boundaries(self) -> None:
        for profile_id, forbidden_runtime in (
            ("research-analysis-argumentation", "citation engine"),
            ("periodic-operations-reporting", "data connector"),
        ):
            definition_ref = next(
                ref for current_id, _, ref in EXPECTED_PROFILES if current_id == profile_id
            )
            text = definition_text(definition_ref)
            flat = " ".join(text.split())
            for marker in (
                "one existing Report Design Brief",
                "do not create a second brief",
                "Profile-specific confirmation round",
                "Profile selection, complete-brief confirmation, and current-file Production Authorization remain three independent facts",
                "Direct HTML remains the default",
                "IR engineering route is independently authorized",
                "Do not add",
                "Report IR Schema",
                "Profile-triggered IR path",
                "Compiler branch",
            ):
                self.assertIn(marker, flat, profile_id)
            self.assertIn(forbidden_runtime, flat, profile_id)

        operations = definition_text(
            "references/workflow-profile-periodic-operations-reporting.md"
        )
        operations_flat = " ".join(operations.split())
        for forbidden_extension in (
            "real-time dashboard",
            "data connector",
            "automatic refresh",
            "online analysis system",
            "new chart component",
        ):
            self.assertIn(forbidden_extension, operations_flat)

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
        self.assertIn("workflow_profile", schema_properties)
        binding = REPORT_IR_SCHEMA["$defs"]["workflow_profile_binding"]
        self.assertFalse(binding["additionalProperties"])
        self.assertEqual(
            set(binding["required"]),
            {
                "primary_profile_id",
                "definition_version",
                "selection_basis",
                "capability_overlays",
            },
        )
        self.assertNotIn("profile_ref", binding["properties"])
        for forbidden_property in (
            "decision_score",
            "audience_movement",
            "formal_recipient",
            "mandatory_section",
            "rule_requirement",
            "compliance_status",
            "score_weight",
            "learner_state",
            "quiz_score",
            "project_status",
            "acceptance_status",
            "publication_ready",
            "asset_rights",
            "conversion_tracking",
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
