from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skill" / "taohtml"
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
INTAKE = (SKILL_DIR / "references" / "intake-workflow.md").read_text(encoding="utf-8")
BRIEF = (SKILL_DIR / "references" / "design-brief-template.md").read_text(
    encoding="utf-8"
)
PLAYBOOK = (SKILL_DIR / "references" / "process-playbook.md").read_text(
    encoding="utf-8"
)
MATERIAL = (SKILL_DIR / "references" / "material-understanding.md").read_text(
    encoding="utf-8"
)
ENVIRONMENT = (SKILL_DIR / "references" / "environment-preflight.md").read_text(
    encoding="utf-8"
)
AUTHORIZATION = (
    SKILL_DIR / "references" / "production-authorization.md"
).read_text(encoding="utf-8")
HANDOFF = (SKILL_DIR / "references" / "project-handoff.md").read_text(
    encoding="utf-8"
)
RUNTIME = (SKILL_DIR / "references" / "runtime-contract.md").read_text(
    encoding="utf-8"
)
PROFILE = (SKILL_DIR / "references" / "profile-memory.md").read_text(
    encoding="utf-8"
)
PUBLIC_WORKFLOW = (ROOT / "docs" / "workflow.md").read_text(encoding="utf-8")


def contract_table(text: str, heading: str) -> dict[str, dict[str, str]]:
    section = text.split(f"### {heading}", 1)[1]
    lines = section.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith("|"))
    table_lines = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        table_lines.append(line)

    def cells(line: str) -> list[str]:
        return [cell.strip().strip("`") for cell in line.strip("|").split("|")]

    headers = cells(table_lines[0])
    rows: dict[str, dict[str, str]] = {}
    for line in table_lines[2:]:
        values = cells(line)
        row = dict(zip(headers, values, strict=True))
        rows[values[0]] = row
    return rows


class IntakeContractTests(unittest.TestCase):
    def test_fresh_placeholder_cannot_bind_stale_workspace_prompt(self) -> None:
        combined = SKILL + INTAKE
        intake_flat = " ".join(INTAKE.split())
        self.assertIn(
            "Start every new build or meaning-changing continuation that will create or revise\nHTML with a route handshake",
            SKILL,
        )
        self.assertIn("bypasses this handshake", SKILL)
        self.assertNotIn(
            "Start every invocation that will create or revise HTML with a route handshake",
            SKILL,
        )
        self.assertIn("do not scan the workspace for a presumed input", SKILL)
        self.assertIn("`input/prompt.md`", INTAKE)
        self.assertIn("is never a binding", intake_flat)
        self.assertIn("do not scan for candidates at all", INTAKE)
        self.assertIn("show exactly one route choice", INTAKE)
        self.assertIn("Do not inspect the workspace", combined)

    def test_project_intent_overlay_does_not_add_a_fourth_content_route(self) -> None:
        entry_routes = SKILL.split("## Entry Routes", 1)[1].split(
            "## Project Handoff Overlay", 1
        )[0]
        self.assertEqual(
            re.findall(r"^\d+\. \*\*", entry_routes, flags=re.MULTILINE),
            ["1. **", "2. **", "3. **"],
        )
        for intent in ("new_build", "review_only", "continue_existing"):
            self.assertIn(intent, HANDOFF)
        self.assertIn("it is not a fourth content entry", HANDOFF.replace("\n", " "))
        self.assertIn("does not add a fourth content entry", SKILL.replace("\n", " "))
        self.assertIn("references/project-handoff.md", SKILL)

    def test_read_only_handoff_is_zero_question_and_non_producing(self) -> None:
        self.assertIn("Default a `review_only` handoff to **0 clarification questions**", HANDOFF)
        self.assertIn("without turning the read-only response into a question", HANDOFF)
        self.assertIn("Do not restart the full route interview", HANDOFF)
        self.assertIn("or create/modify\nHTML", HANDOFF)
        self.assertIn("does not ask an entry-route question", SKILL)
        self.assertIn("默认 0 个澄清问题", PUBLIC_WORKFLOW)
        self.assertIn("不生成材料理解摘要、设计简报或 HTML", PUBLIC_WORKFLOW)

    def test_handoff_source_roles_and_availability_are_explicit(self) -> None:
        for role in (
            "original_customer_material",
            "external_public_evidence",
            "secondary_handoff_summary",
            "current_artifact",
            "visual_reference",
            "agent_generated_material",
            "described_unavailable_material",
        ):
            self.assertIn(role, HANDOFF)
            self.assertIn(role, MATERIAL)
            self.assertIn(role, BRIEF)
        for status in (
            "workspace_readable",
            "external_retrieved_inspected",
            "platform_visible_not_retrieved",
            "handoff_record_only",
            "confirmed_missing",
            "not_yet_verified",
        ):
            self.assertIn(status, HANDOFF)
            self.assertIn(status, MATERIAL)
            self.assertIn(status, BRIEF)
        self.assertIn("does not replace the original material", HANDOFF)
        self.assertIn("not where its claims came from", HANDOFF)

    def test_retrieved_public_evidence_has_real_provenance_semantics(self) -> None:
        matrix = contract_table(HANDOFF, "Evidence Provenance Matrix")
        verified = matrix["agent_retrieved_public_source_verified"]
        self.assertEqual(verified["source_binding"], "agent_retrieved_external")
        self.assertEqual(verified["source_role"], "external_public_evidence")
        self.assertEqual(
            verified["availability_status"], "external_retrieved_inspected"
        )
        self.assertEqual(verified["evidence_verification"], "verified")
        self.assertNotIn(
            verified["source_role"],
            {"original_customer_material", "agent_generated_material"},
        )
        self.assertNotEqual(verified["availability_status"], "workspace_readable")

        unverified = matrix["agent_retrieved_public_source_unverified"]
        self.assertEqual(unverified["source_role"], verified["source_role"])
        self.assertEqual(
            unverified["availability_status"], verified["availability_status"]
        )
        self.assertEqual(unverified["evidence_verification"], "unverified")
        self.assertIn("外部公开证据", PUBLIC_WORKFLOW)
        self.assertIn("agent_retrieved_external", PUBLIC_WORKFLOW)

    def test_handoff_candidate_discovery_stays_source_bound_and_narrow(self) -> None:
        intake_flat = " ".join(INTAKE.split())
        self.assertIn(
            "Apply the existing local/upload source-binding rules without exception",
            HANDOFF,
        )
        self.assertIn("Candidate discovery is disabled by default", HANDOFF)
        self.assertIn("explicitly asks the Agent to find the source", HANDOFF)
        self.assertIn("must not read candidate content or auto-bind", HANDOFF)
        self.assertIn("Do not recursively scan a home directory", HANDOFF)
        self.assertIn("Do not recursively scan a home directory", intake_flat)
        self.assertIn("does not prove that the material was\ncleaned", HANDOFF)
        self.assertIn("without converting it to `confirmed_missing`", HANDOFF)

    def test_continuation_uses_delta_intake_and_protects_meaning(self) -> None:
        self.assertIn("Perform delta intake", HANDOFF)
        self.assertIn("ask only that\nsingle largest gap", HANDOFF)
        self.assertIn("do not replay the full interview", SKILL)
        for safe_change in (
            "layout, spacing, typography, color",
            "Runtime-compatible navigation, technical, portability",
            "local wording improvements",
        ):
            self.assertIn(safe_change, HANDOFF)
        for protected_change in (
            "real data, quotations, citations, source attribution",
            "which evidence supports which claim",
            "a core viewpoint, main conclusion, scope promise",
        ):
            self.assertIn(protected_change, HANDOFF)
        self.assertIn("Restore the original source or obtain explicit user confirmation", HANDOFF)
        self.assertIn("Do not turn every unavailable original into a\nblock", HANDOFF)
        self.assertIn("delivery-time `《待核实内容清单》`", HANDOFF)
        self.assertIn("display and confirm the complete current brief", HANDOFF)
        self.assertIn("current-task contract in\n`production-authorization.md`", HANDOFF)

    def test_continuation_matrix_skips_brief_only_for_local_semantic_noop(self) -> None:
        matrix = contract_table(HANDOFF, "Continuation Decision Matrix")
        local = matrix["meaning_preserving_local"]
        self.assertEqual(local["intake"], "do_not_rerun")
        self.assertEqual(local["material_summary"], "do_not_rebuild")
        self.assertEqual(local["design_brief"], "no_reconfirmation")
        self.assertEqual(
            local["required_current_validation"], "exact_artifact_qa_and_delivery"
        )

        meaning_change = matrix["meaning_changing"]
        self.assertEqual(meaning_change["intake"], "delta_only")
        self.assertEqual(meaning_change["material_summary"], "rebuild_affected")
        self.assertEqual(
            meaning_change["design_brief"], "confirm_complete_current_brief"
        )
        self.assertEqual(
            meaning_change["required_current_validation"],
            "authorization_qa_and_delivery",
        )
        self.assertNotEqual(local["design_brief"], meaning_change["design_brief"])
        self.assertIn("不重跑 intake、材料摘要或设计简报确认", PUBLIC_WORKFLOW)

    def test_handoff_readiness_and_operation_claims_require_current_evidence(self) -> None:
        for marker in (
            "**found**",
            "**can be previewed**",
            "**ready**",
            "**formally deliverable**",
            "strict offline asset QA",
            "browser preflight/HTML QA",
            "current_artifact_tested",
            "current_runtime_contract",
        ):
            self.assertIn(marker, HANDOFF)
        self.assertIn("Do not repeat an untested control description", HANDOFF)
        self.assertIn("current HTML tested in browser QA", SKILL)
        self.assertIn("不能说“已就绪”“QA 已通过”或“可正式交付”", PUBLIC_WORKFLOW)

    def test_handoff_overlay_preserves_runtime_and_profile_boundaries(self) -> None:
        self.assertIn("does not add Runtime capabilities", HANDOFF)
        self.assertIn("create a new\ncorporate Profile data category", HANDOFF)
        self.assertIn("profile isolation and validation", HANDOFF)
        self.assertIn("Do not promise dual-screen presenter view", RUNTIME)
        self.assertIn("Never store report prose, project goals, audience, evidence", PROFILE)
        self.assertIn("six-\nquestion limits", HANDOFF)

    def test_handoff_contract_is_not_tied_to_one_filename_path_or_company(self) -> None:
        self.assertNotRegex(HANDOFF, r"[A-Za-z]:\\\\")
        self.assertIn("Do not use filenames", HANDOFF)
        self.assertIn("operating-system paths", HANDOFF)
        self.assertIn("company names, or a fixed keyword list", HANDOFF)

    def test_recent_agent_options_can_bind_a_compact_answer(self) -> None:
        self.assertIn("latest_options = decision id", INTAKE)
        self.assertIn("most recent active option record in this same conversation", INTAKE)
        self.assertIn("Consume the record after one answer", INTAKE)
        self.assertIn("the same compact text attached to a fresh invocation", INTAKE)
        self.assertIn("cannot", INTAKE)

    def test_user_explicit_input_prompt_path_is_eligible_and_recorded(self) -> None:
        intake_flat = " ".join(INTAKE.split())
        self.assertIn("current_upload_or_user_explicit", INTAKE)
        self.assertIn("task_instruction_explicit", INTAKE)
        self.assertIn("candidate_confirmed", INTAKE)
        self.assertIn(
            "source identity/path | source_binding | source role | availability status",
            INTAKE,
        )
        self.assertIn("conventional filename such as `input/prompt.md`", intake_flat)
        self.assertIn("the user uploads it now and it is available", INTAKE)
        self.assertIn("provides one resolvable exact file path", INTAKE)
        self.assertIn("source_binding", MATERIAL)
        self.assertIn("source_binding", BRIEF)
        self.assertIn("must never be relabeled as a creative supplement", INTAKE)

    def test_startup_uses_semantic_state_not_an_invalid_token_list(self) -> None:
        self.assertIn("not from a blacklist", INTAKE)
        self.assertIn("enumeration of tokens", INTAKE)
        self.assertIn("generalize across languages, punctuation, emoji, and platform UI", INTAKE)
        self.assertIn("section numbering", INTAKE)

    def test_preflight_is_capability_scoped_and_fail_fast(self) -> None:
        self.assertIn("smallest profile needed", ENVIRONMENT)
        self.assertIn("blocked by Pillow, Playwright, or Chromium", ENVIRONMENT)
        self.assertIn("before opening or extracting a PDF", SKILL)
        self.assertIn("before opening or analyzing any reference image", SKILL)
        self.assertIn("minimal `profile-reuse` environment profile", SKILL)
        self.assertIn("no Playwright or Chromium", ENVIRONMENT)
        self.assertIn("run the `browser` profile before browser QA", SKILL)
        self.assertIn("Do not offer “manual corporate fidelity.”", ENVIRONMENT)
        self.assertIn("Do not call `reconstruct`", ENVIRONMENT)
        self.assertIn("technical", ENVIRONMENT)
        self.assertIn("downgrade because it requires the same", ENVIRONMENT)

    def test_formal_html_uses_current_state_and_allowed_action_matrix(self) -> None:
        self.assertIn("Allowed-Action Matrix", AUTHORIZATION)
        self.assertIn("current-invocation-id", AUTHORIZATION)
        self.assertIn('"schema_version": "1.3"', AUTHORIZATION)
        self.assertIn("--action built-in-theme-selection", AUTHORIZATION)
        self.assertIn("--action motion-density-selection", AUTHORIZATION)
        self.assertIn("current_design_decisions_sha256", AUTHORIZATION)
        self.assertIn("--action design-brief-preview", AUTHORIZATION)
        self.assertIn("--action formal-html", AUTHORIZATION)
        self.assertIn("--action deliver-formal-html", AUTHORIZATION)
        self.assertIn("not formal report HTML", AUTHORIZATION)
        self.assertIn(
            "scripts/check_production_authorization.py --artifact-root <current-task-root> --action formal-html",
            SKILL,
        )
        self.assertIn("never use a fixed authorization phrase", INTAKE)
        for marker in (
            "artifact_path",
            "artifact_sha256",
            "confirmation_ref",
            "decision_ref",
            "design_decisions_sha256",
            "does not access or independently",
        ):
            self.assertIn(marker, AUTHORIZATION)
        self.assertIn("fail-closed migration", AUTHORIZATION)
        self.assertIn("migration.required: true", AUTHORIZATION)

    def test_clear_idea_can_stop_with_zero_questions(self) -> None:
        self.assertIn("Allow **0 clarification questions**", INTAKE)
        self.assertIn(
            "proceed directly to the independent design-choice gate with zero clarification questions",
            INTAKE,
        )
        self.assertIn("Do not impose this gate on an idea-only input", INTAKE)

    def test_file_source_gate_precedes_every_startup_or_read_action(self) -> None:
        self.assertLess(
            INTAKE.index("| S0 Route handshake |"),
            INTAKE.index("| S0B File source acquisition/binding |"),
        )
        self.assertLess(
            INTAKE.index("| S0B File source acquisition/binding |"),
            INTAKE.index("| S0A Startup completion |"),
        )
        self.assertIn("`route_selected` and `source_bound` are independent facts", INTAKE)
        self.assertIn("including with a compact `2` or `3`", INTAKE)

    def test_word_pdf_without_source_only_requests_source_and_stops(self) -> None:
        case = contract_table(INTAKE, "Source Acquisition Decision Table")[
            "word_pdf_missing"
        ]
        self.assertEqual(case["allowed_actions"], "request_source,stop")
        self.assertEqual(case["next_state"], "S0B")
        self.assertEqual(
            set(case["forbidden_actions"].split(",")),
            {
                "use_mode_question",
                "length_question",
                "audience_question",
                "filesystem_search",
                "candidate_discovery",
                "source_read",
            },
        )

    def test_existing_ppt_html_without_source_only_requests_source_and_stops(
        self,
    ) -> None:
        case = contract_table(INTAKE, "Source Acquisition Decision Table")[
            "existing_ppt_html_missing"
        ]
        self.assertEqual(case["allowed_actions"], "request_source,stop")
        self.assertEqual(case["next_state"], "S0B")
        self.assertIn("filesystem_search", case["forbidden_actions"].split(","))
        self.assertIn("candidate_discovery", case["forbidden_actions"].split(","))
        self.assertIn("source_read", case["forbidden_actions"].split(","))

    def test_current_upload_binds_once_without_reasking(self) -> None:
        case = contract_table(INTAKE, "Source Acquisition Decision Table")[
            "current_upload"
        ]
        self.assertEqual(case["allowed_actions"], "bind_exact_source,continue")
        self.assertEqual(case["next_state"], "S0A")
        self.assertIn("request_source", case["forbidden_actions"].split(","))

    def test_explicit_path_uses_only_that_path(self) -> None:
        case = contract_table(INTAKE, "Source Acquisition Decision Table")[
            "explicit_path"
        ]
        self.assertEqual(case["allowed_actions"], "bind_exact_path,continue")
        self.assertEqual(case["next_state"], "S0A")
        self.assertEqual(
            set(case["forbidden_actions"].split(",")),
            {"request_source", "parent_search", "sibling_search", "broad_search"},
        )

    def test_explicit_narrow_directory_search_is_metadata_only_until_confirmation(
        self,
    ) -> None:
        cases = contract_table(INTAKE, "Source Acquisition Decision Table")
        discovery = cases["authorized_directory_discovery"]
        self.assertEqual(
            discovery["discovery_authorization"], "explicit_narrow_directory"
        )
        self.assertEqual(
            discovery["allowed_actions"], "metadata_discovery,show_exact_paths,stop"
        )
        for action in ("content_read", "extract", "summarize", "auto_bind"):
            self.assertIn(action, discovery["forbidden_actions"].split(","))
        self.assertEqual(discovery["next_state"], "S0B")

        confirmed = cases["confirmed_candidate"]
        self.assertEqual(
            confirmed["allowed_actions"], "bind_confirmed_candidate,continue"
        )
        self.assertEqual(confirmed["next_state"], "S0A")

    def test_workspace_and_history_files_never_auto_bind(self) -> None:
        case = contract_table(INTAKE, "Source Acquisition Decision Table")[
            "workspace_or_history_residue"
        ]
        self.assertEqual(case["allowed_actions"], "request_source,stop")
        self.assertEqual(case["discovery_authorization"], "absent")
        self.assertEqual(case["next_state"], "S0B")
        self.assertIn("auto_bind", case["forbidden_actions"].split(","))
        self.assertIn("filesystem_search", case["forbidden_actions"].split(","))

    def test_task_instruction_source_can_bind_without_search(self) -> None:
        case = contract_table(INTAKE, "Source Acquisition Decision Table")[
            "task_instruction_source"
        ]
        self.assertEqual(case["allowed_actions"], "bind_exact_source,continue")
        self.assertEqual(case["next_state"], "S0A")
        self.assertIn("candidate_discovery", case["forbidden_actions"].split(","))

    def test_idea_only_bypasses_file_source_acquisition_unchanged(self) -> None:
        case = contract_table(INTAKE, "Source Acquisition Decision Table")[
            "idea_only_topic"
        ]
        self.assertEqual(case["source_status"], "not_applicable")
        self.assertEqual(case["allowed_actions"], "continue_startup")
        self.assertEqual(case["next_state"], "S0A")
        self.assertIn("Do not apply it to `idea_only`", INTAKE)

    def test_public_entry_copy_exposes_upload_or_path_stop_gate(self) -> None:
        self.assertIn("Word / PDF：选择后请上传源文件", PUBLIC_WORKFLOW)
        self.assertIn("已有 PPT / HTML：选择后请上传现有文件", PUBLIC_WORKFLOW)
        self.assertIn("“已选入口”不等于“已绑定来源”", PUBLIC_WORKFLOW)
        self.assertIn(
            "必须只请求上传文件或提供可解析的完整路径",
            PUBLIC_WORKFLOW,
        )
        self.assertIn("候选发现默认禁止", PUBLIC_WORKFLOW)

    def test_ordinary_intake_targets_three_to_five_questions(self) -> None:
        self.assertIn("Treat **3-5 clarification questions** as the ordinary target", INTAKE)
        self.assertIn("Ask only the largest current gap", INTAKE)
        self.assertIn("not a four-question form", INTAKE)

    def test_six_is_a_hard_cap_but_brief_confirmation_is_separate(self) -> None:
        self.assertIn(
            "Enforce **6 clarification questions** as a hard maximum, including for the most complex idea-only intake",
            INTAKE,
        )
        self.assertIn("Do not ask a seventh", INTAKE)
        self.assertIn("do not count toward this budget", INTAKE)
        self.assertIn("start a new intake cycle with fresh counters", INTAKE)

    def test_known_route_mode_audience_goal_length_and_action_path_are_not_reasked(
        self,
    ) -> None:
        self.assertIn(
            "Treat a stated route, use mode, audience, desired outcome, content length, real action path, or hard presentation duration as `known`",
            INTAKE,
        )
        self.assertIn("do not ask for or confirm the same information again", INTAKE)

    def test_known_presentation_mode_is_not_reasked(self) -> None:
        self.assertIn(
            "If presentation mode is already known, do not ask the user to select the use mode again",
            INTAKE,
        )

    def test_missing_length_offers_three_levels_and_dynamic_page_estimate(self) -> None:
        self.assertIn(
            "ask one question that offers **concise / standard / detailed**",
            INTAKE,
        )
        self.assertIn(
            "Estimate the page count dynamically from the actual material",
            INTAKE,
        )
        self.assertIn(
            "Never assign or present a fixed page range by length label alone",
            INTAKE,
        )
        self.assertIn("do not infer a default length without explicit delegation", INTAKE)
        self.assertNotRegex(INTAKE, r"\b\d+\s*[-–]\s*\d+\s+pages\b")

    def test_presentation_duration_is_not_a_default_startup_condition(self) -> None:
        self.assertIn(
            "Presentation duration is an optional delivery constraint, not a startup choice or a design-ready prerequisite",
            INTAKE,
        )
        self.assertIn("do not ask for a duration by default", INTAKE)
        self.assertIn("do not block progress when no duration was given", INTAKE)

    def test_user_provided_hard_duration_is_used_without_reasking(self) -> None:
        self.assertIn("If the user provides a hard duration", INTAKE)
        self.assertIn("use it to constrain scope, pacing, and content density", INTAKE)
        self.assertIn(
            "do not ask the user to repeat or confirm that duration",
            INTAKE,
        )
        self.assertIn("A hard duration does not replace the content-length choice", INTAKE)

    def test_same_gap_is_asked_at_most_twice(self) -> None:
        self.assertIn("same key gap at most **twice**", INTAKE)
        self.assertIn("On the second attempt", INTAKE)
        self.assertIn("a concrete example or 2-3 real options", INTAKE)

    def test_three_rounds_without_information_gain_stop_questions(self) -> None:
        self.assertIn(
            "three consecutive rounds without actionable new information", INTAKE
        )
        self.assertIn("Stop ordinary clarification immediately", INTAKE)
        self.assertIn("infer all remaining ordinary low-risk gaps", INTAKE)

    def test_ordinary_missing_content_is_completed_and_handed_off(self) -> None:
        self.assertIn("Ordinary information gaps do not automatically create a block", INTAKE)
        self.assertIn("creative-supplement ledger", INTAKE)
        self.assertIn("《待核实内容清单》", PLAYBOOK)
        for field in ("页面/内容", "补充类型", "来源状态", "建议动作"):
            self.assertIn(field, PLAYBOOK)

    def test_minimum_hard_boundary_gap_blocks_brief_and_production(self) -> None:
        self.assertIn("do not generate a Report Design Brief", INTAKE)
        self.assertIn("do not begin production", INTAKE)
        self.assertIn("minimum hard boundaries", INTAKE)
        self.assertIn("never invent a real customer or company identity", INTAKE)
        self.assertIn("legal, medical, financial, safety", INTAKE)
        for heading in (
            "## 当前已知",
            "## 未决缺口",
            "## 为什么不能推断",
            "## 最小补充材料",
            "## 恢复条件",
        ):
            self.assertIn(heading, INTAKE)
        self.assertIn("use the blocked-intake output instead of this template", BRIEF)

    def test_conversion_goal_requires_a_real_action_path_before_brief(self) -> None:
        self.assertIn("A conversion objective is not design-ready", INTAKE)
        self.assertIn("real action path remains missing", INTAKE)
        self.assertIn("do not generate a Report Design Brief or begin production", INTAKE)

    def test_verified_source_action_path_is_reused_without_reasking(self) -> None:
        self.assertIn(
            "Do not ask for an action path already supported by the source or project context",
            INTAKE,
        )
        self.assertIn("record the value, source, and verification result", INTAKE)

    def test_non_conversion_reports_do_not_require_an_action_path(self) -> None:
        self.assertIn(
            "Do not ask for an action path when the report is explanatory, educational, or internal",
            INTAKE,
        )

    def test_action_channels_cannot_be_invented(self) -> None:
        self.assertIn(
            "Never invent a URL, QR code, contact detail, price, command, or product entry",
            INTAKE,
        )
        self.assertIn("Never synthesize a placeholder channel", PLAYBOOK)

    def test_brief_and_delivery_trace_the_executable_action_path(self) -> None:
        for field in (
            "期望行动",
            "真实执行路径",
            "渠道来源与验证状态",
            "最终页面展示方式",
        ):
            self.assertIn(field, BRIEF)
        self.assertIn("executable-action traceability", PLAYBOOK)
        self.assertIn(
            "visible, usable, and aligned with the confirmed objective", PLAYBOOK
        )

    def test_skill_asks_one_design_decision_per_round_and_has_no_dbs_dependency(
        self,
    ) -> None:
        self.assertIn("identify use mode and content length one decision at a time", SKILL)
        self.assertIn("Ask one decision question per round", SKILL)
        self.assertIn("Do not bundle independent startup choices", SKILL)
        self.assertNotIn("compact startup", (SKILL + INTAKE).lower())
        self.assertNotIn("bundled startup", (SKILL + INTAKE).lower())
        self.assertNotIn("DBS", SKILL + INTAKE + BRIEF)

    def test_design_ready_state_stops_questions_before_the_cap(self) -> None:
        self.assertIn(
            "Stop ordinary clarification immediately when the design-ready gate passes",
            INTAKE,
        )
        self.assertIn("never continue asking to approach a target or maximum", INTAKE)
        self.assertIn(
            "Stop ordinary clarification as soon as these conditions are met", INTAKE
        )

    def test_visual_and_motion_choices_are_outside_the_six_question_budget(self) -> None:
        for marker in (
            "Built-in theme selection, motion-density selection",
            "cannot be skipped by the six-question maximum",
            "never selects either value",
            "without either, stop at this gate",
            "minimal | moderate | rich",
            "少量 / 适中 / 丰富",
        ):
            self.assertIn(marker, INTAKE)
        self.assertIn(
            "remain required after six ordinary questions", SKILL
        )
        self.assertNotIn(
            "If the project reaches the maximum or the three-no-gain stop before a low-risk visual choice is selected",
            INTAKE,
        )

    def test_verification_handoff_does_not_expand_the_question_budget(self) -> None:
        self.assertIn("Enforce **6 clarification questions**", INTAKE)
        self.assertIn("must not trigger this block", INTAKE)
        self.assertIn("continue instead of repeatedly interrupting the user", INTAKE)

    def test_reference_dual_mode_is_one_budgeted_non_repeating_choice(self) -> None:
        for marker in (
            "参考风格重构",
            "企业模板保真",
            "reference_mode",
            "count this as one ordinary clarification question",
            "never repeat it after the answer is known",
        ):
            self.assertIn(marker, INTAKE)
        self.assertIn("If the user already says", SKILL)
        self.assertIn("do not ask again", SKILL)
        self.assertIn(
            "The one-time reference-mode choice is a clarification question",
            SKILL,
        )

    def test_design_brief_records_corporate_fidelity_boundaries(self) -> None:
        for marker in (
            "参考图模式",
            "保真边界",
            "锁定企业元素",
            "可编辑安全区",
            "参考事实边界",
            "延展页面与限制",
            "原始 PPT 母版",
            "矢量 Logo",
        ):
            self.assertIn(marker, BRIEF)


if __name__ == "__main__":
    unittest.main()
