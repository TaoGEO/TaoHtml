from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

import fitz


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "evals" / "taohtml-quality-v1"


def load_script(name: str) -> ModuleType:
    path = BENCHMARK / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"taohtml_eval_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREPARE = load_script("prepare_run")
JUDGE = load_script("judge_run")
AGGREGATE = load_script("aggregate_results")


class QualityBenchmarkDefinitionTests(unittest.TestCase):
    def test_three_scenarios_have_executor_and_controller_halves(self) -> None:
        expected = {
            "idea-live-conversion",
            "pdf-evidence-report",
            "existing-html-upgrade",
        }
        controller_files = {
            path.stem for path in (BENCHMARK / "controller" / "scenarios").glob("*.json")
        }
        executor_dirs = {
            path.name
            for path in (BENCHMARK / "executor" / "scenarios").iterdir()
            if path.is_dir()
        }
        self.assertEqual(controller_files, expected)
        self.assertEqual(executor_dirs, expected)

        for scenario_id in expected:
            scenario = JUDGE.load_scenario(scenario_id)
            self.assertEqual(scenario["id"], scenario_id)
            self.assertTrue(scenario["follow_up_answers"])
            self.assertTrue(scenario["forbidden_behaviors"])
            self.assertIn("entrypoint", scenario["expected_delivery"])
            self.assertTrue(
                (BENCHMARK / "executor" / "scenarios" / scenario_id / "prompt.md").is_file()
            )

    def test_executor_prompts_explicitly_bind_prepared_inputs(self) -> None:
        prompts = {
            scenario_id: (
                BENCHMARK / "executor" / "scenarios" / scenario_id / "prompt.md"
            ).read_text(encoding="utf-8")
            for scenario_id in (
                "idea-live-conversion",
                "pdf-evidence-report",
                "existing-html-upgrade",
            )
        }
        for prompt in prompts.values():
            self.assertIn("`input/prompt.md`", prompt)
        self.assertIn("明确将", prompts["idea-live-conversion"])
        self.assertIn("没有其他报告材料", prompts["idea-live-conversion"])
        self.assertIn(
            "explicitly binds `input/prompt.md` as the current task instruction",
            prompts["pdf-evidence-report"],
        )
        self.assertIn(
            "`input/materials/orbit-pilot-review.pdf` as the source material",
            prompts["pdf-evidence-report"],
        )
        self.assertIn(
            "`input/materials/legacy-deck.html` as the source material",
            prompts["existing-html-upgrade"],
        )

    def test_result_schema_records_required_comparison_fields(self) -> None:
        schema = json.loads(
            (BENCHMARK / "schemas" / "run-result.schema.json").read_text(encoding="utf-8")
        )
        run_required = set(schema["properties"]["run"]["required"])
        self.assertTrue(
            {
                "client",
                "agent",
                "model",
                "skill",
                "question_count",
                "token_usage",
                "billing_usage",
                "duration",
            }.issubset(run_required)
        )
        human_required = set(schema["$defs"]["human_review"]["required"])
        self.assertIn("manual_revision_count", human_required)
        self.assertIn("reference_floor", human_required)
        self.assertIn("failure_samples", schema["properties"])
        self.assertIn(
            "conditional",
            schema["properties"]["objective"]["properties"]["status"]["enum"],
        )
        check_statuses = schema["properties"]["objective"]["properties"]["checks"][
            "items"
        ]["properties"]["status"]["enum"]
        self.assertIn("warning", check_statuses)

        metadata = json.loads(
            (BENCHMARK / "schemas" / "run-metadata.example.json").read_text(encoding="utf-8")
        )
        human_review = json.loads(
            (BENCHMARK / "schemas" / "human-review.example.json").read_text(encoding="utf-8")
        )
        JUDGE.validate_metadata(metadata, metadata["scenario_id"])
        JUDGE.validate_human_review(human_review)

    def test_usage_metadata_accepts_only_exact_platform_values(self) -> None:
        metadata = json.loads(
            (BENCHMARK / "schemas" / "run-metadata.example.json").read_text(encoding="utf-8")
        )
        exact = copy.deepcopy(metadata)
        exact["token_usage"] = {
            "availability": "exact",
            "source": "platform_task_usage",
            "input_tokens": 120,
            "output_tokens": 80,
            "cache_tokens": None,
            "total_tokens": 200,
        }
        exact["billing_usage"] = {
            "availability": "exact",
            "source": "balance_delta",
            "workbuddy_points": 7,
            "balance_before": 100,
            "balance_after": 93,
        }
        JUDGE.validate_metadata(exact, exact["scenario_id"])

        partial_exact_tokens = copy.deepcopy(exact)
        partial_exact_tokens["token_usage"]["output_tokens"] = None
        partial_exact_tokens["token_usage"]["total_tokens"] = None
        JUDGE.validate_metadata(partial_exact_tokens, partial_exact_tokens["scenario_id"])

        unavailable_with_estimate = copy.deepcopy(metadata)
        unavailable_with_estimate["billing_usage"]["workbuddy_points"] = 5
        with self.assertRaisesRegex(ValueError, "unavailable billing_usage"):
            JUDGE.validate_metadata(
                unavailable_with_estimate,
                unavailable_with_estimate["scenario_id"],
            )

        unavailable_tokens_with_estimate = copy.deepcopy(metadata)
        unavailable_tokens_with_estimate["token_usage"]["total_tokens"] = 200
        with self.assertRaisesRegex(ValueError, "unavailable token_usage"):
            JUDGE.validate_metadata(
                unavailable_tokens_with_estimate,
                unavailable_tokens_with_estimate["scenario_id"],
            )

        mismatched_delta = copy.deepcopy(exact)
        mismatched_delta["billing_usage"]["workbuddy_points"] = 8
        with self.assertRaisesRegex(ValueError, "exactly equal"):
            JUDGE.validate_metadata(mismatched_delta, mismatched_delta["scenario_id"])

    def test_workbuddy_reassessment_preserves_artifact_pass_and_conditional_workflow(
        self,
    ) -> None:
        reassessment = json.loads(
            (
                BENCHMARK
                / "controller"
                / "reassessments"
                / "workbuddy-idea-live-conversion-20260715.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(reassessment["artifact_status"], "pass")
        self.assertEqual(reassessment["workflow_status"], "conditional")
        self.assertIn("sealed WorkBuddy RAR remains unchanged", reassessment["source_record_policy"])
        self.assertIn("5 分钟", reassessment["observed_creative_supplements"])


class PrepareRunTests(unittest.TestCase):
    def test_prepared_idea_workspace_has_no_controller_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = PREPARE.prepare_workspace(
                "idea-live-conversion", Path(temp_dir) / "workspace"
            )
            relative_files = {
                str(path.relative_to(workspace)) for path in workspace.rglob("*") if path.is_file()
            }
            self.assertIn("input/prompt.md", relative_files)
            self.assertIn("skill/taohtml/SKILL.md", relative_files)
            prepared_prompt = (workspace / "input" / "prompt.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("明确将 `input/prompt.md` 绑定为当前任务说明", prepared_prompt)
            self.assertIn("没有其他报告材料", prepared_prompt)
            self.assertFalse(any("controller" in path for path in relative_files))
            json_files = {path for path in relative_files if path.endswith(".json")}
            self.assertEqual(
                json_files,
                {
                    f"skill/taohtml/assets/visual-systems/{theme_id}/theme.json"
                    for theme_id in (
                        "black-white-fluorescent-cards",
                        "rigorous-consulting-report",
                        "corporate-annual-report",
                        "editorial-collage",
                    )
                }
                | {"skill/taohtml/references/project-handoff.schema.json"},
            )

    def test_pdf_is_generated_as_small_three_page_material(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = PREPARE.prepare_workspace(
                "pdf-evidence-report", Path(temp_dir) / "workspace"
            )
            pdf = workspace / "input" / "materials" / "orbit-pilot-review.pdf"
            source = workspace / "input" / "materials" / "orbit-pilot-review.source.txt"
            self.assertTrue(pdf.is_file())
            self.assertFalse(source.exists())
            self.assertLess(pdf.stat().st_size, 200_000)
            with fitz.open(pdf) as document:
                self.assertEqual(document.page_count, 3)
                text = "\n".join(page.get_text() for page in document)
            self.assertIn("128 service deliveries", text)
            self.assertIn("78 percent", text)


class DeterministicJudgeTests(unittest.TestCase):
    @staticmethod
    def idea_semantic_checks(
        handoff_text: str | None,
        *,
        question_count: int = 6,
        extra_html: str = "",
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        scenario = JUDGE.load_scenario("idea-live-conversion")
        target = scenario["content_checks"]["allowed_action_targets"][0]
        html_text = f"""
        <main class="deck" data-mode="presentation">
          <section class="slide">
            <p>先把案例变成可调用证据，再谈扩大获客。</p>
            <p>案例散落，这是一个示意场景。</p>
            <p>整理过程预计 5 分钟完成。</p>
            {extra_html}
          </section>
          <section class="slide"><a href="{target}">{target}</a></section>
        </main>
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            html = Path(temp_dir) / "index.html"
            html.write_text(html_text, encoding="utf-8")
            _, content_checks = JUDGE.inspect_content(html, scenario)
        fact_check = next(
            check
            for check in content_checks
            if check["id"] == "content.source-bounded-facts"
        )
        question_check = JUDGE.make_check(
            "intake.question-cap",
            "intake",
            "pass" if question_count <= 6 else "fail",
            "Question cap.",
            {"actual": question_count, "maximum": 6},
            scope="workflow",
        )
        checks = [question_check, *content_checks]
        checks.extend(
            JUDGE.inspect_verification_handoff(
                handoff_text,
                scenario,
                fact_check["evidence"]["unexpected"],
            )
        )
        return JUDGE.classify_checks(checks), checks

    @staticmethod
    def complete_handoff() -> str:
        return """## 《待核实内容清单》

| 页面/内容 | 补充类型 | 来源状态 | 建议动作 |
|---|---|---|---|
| 第 1 页“5 分钟” | 推演数字 | TaoHtml 创作性补全，尚待客户核实 | 确认、修改、删除或让 TaoHtml 替换 |
"""

    def test_missing_entrypoint_is_a_comparable_hard_failure(self) -> None:
        metadata = json.loads(
            (BENCHMARK / "schemas" / "run-metadata.example.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            result = JUDGE.judge(
                "idea-live-conversion",
                workspace,
                metadata,
                None,
                skip_browser=False,
            )
        self.assertEqual(result["objective"]["status"], "fail")
        self.assertTrue(result["comparison"]["comparable"])
        self.assertFalse(result["comparison"]["benchmark_success"])

    def test_content_locked_html_compares_exact_slide_copy(self) -> None:
        scenario = JUDGE.load_scenario("existing-html-upgrade")
        slides = scenario["content_checks"]["exact_slide_text"]
        html_text = (
            '<main class="deck" data-mode="presentation">'
            + "".join(f'<section class="slide"><p>{text}</p></section>' for text in slides)
            + "</main>"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            html = Path(temp_dir) / "index.html"
            html.write_text(html_text, encoding="utf-8")
            _, checks = JUDGE.inspect_content(html, scenario)
        statuses = {check["id"]: check["status"] for check in checks}
        self.assertEqual(statuses["content.exact-page-copy"], "pass")
        self.assertEqual(statuses["delivery.slide-count"], "pass")
        self.assertEqual(statuses["content.action-targets"], "pass")

    def test_numeric_fact_and_action_allowlists_catch_inventions(self) -> None:
        scenario = JUDGE.load_scenario("pdf-evidence-report")
        required = " ".join(
            group["any"][0] for group in scenario["content_checks"]["required_text_groups"]
        )
        html_text = f"""
        <main class="deck" data-mode="reading">
          <section class="slide">
            <p>{required}</p>
            <p>99 percent</p>
            <a href="https://example.com/invented">Continue</a>
            <button class="source-btn" data-source="assets/source.png">Source</button>
          </section>
          <section class="slide"><p>Evidence</p></section>
        </main>
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            html = Path(temp_dir) / "index.html"
            html.write_text(html_text, encoding="utf-8")
            _, checks = JUDGE.inspect_content(html, scenario)
        statuses = {check["id"]: check["status"] for check in checks}
        self.assertEqual(statuses["content.core-viewpoints"], "pass")
        self.assertEqual(statuses["content.source-bounded-facts"], "fail")
        self.assertEqual(statuses["content.action-targets"], "fail")

    def test_composite_label_and_visible_action_preserve_valid_output(self) -> None:
        scenario = JUDGE.load_scenario("idea-live-conversion")
        target = scenario["content_checks"]["allowed_action_targets"][0]
        html_text = f"""
        <main class="deck" data-mode="presentation">
          <section class="slide">
            <p>先把案例变成可调用证据，再谈扩大获客。</p>
            <p>案例散落，这是一个合成示例。</p>
          </section>
          <section class="slide">
            <a href="{target}">{target}</a>
          </section>
        </main>
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            html = Path(temp_dir) / "index.html"
            html.write_text(html_text, encoding="utf-8")
            _, checks = JUDGE.inspect_content(html, scenario)
        statuses = {check["id"]: check["status"] for check in checks}
        self.assertEqual(statuses["content.core-viewpoints"], "pass")
        self.assertEqual(statuses["content.action-targets"], "pass")

    def test_a_idea_only_output_with_complete_handoff_is_pass(self) -> None:
        classification, checks = self.idea_semantic_checks(self.complete_handoff())
        statuses = {check["id"]: check["status"] for check in checks}
        self.assertEqual(statuses["content.source-bounded-facts"], "pass")
        self.assertEqual(statuses["delivery.verification-handoff"], "pass")
        self.assertEqual(statuses["handoff.creative-fact-coverage"], "pass")
        self.assertEqual(classification["artifact_status"], "pass")
        self.assertEqual(classification["status"], "pass")

    def test_b_usable_output_without_handoff_is_conditional(self) -> None:
        classification, checks = self.idea_semantic_checks(None)
        statuses = {check["id"]: check["status"] for check in checks}
        self.assertEqual(statuses["delivery.verification-handoff"], "warning")
        self.assertEqual(classification["artifact_status"], "pass")
        self.assertEqual(classification["status"], "conditional")

    def test_c_invented_real_source_or_unverified_high_risk_fact_is_fail(self) -> None:
        for forbidden in (
            "真实客户星河咨询 CEO 李明表示",
            "来源：《2026 独立顾问转化率白皮书》",
            "财务建议：每位顾问应投入全部储蓄",
        ):
            with self.subTest(forbidden=forbidden):
                classification, checks = self.idea_semantic_checks(
                    self.complete_handoff(),
                    extra_html=f"<p>{forbidden}</p>",
                )
                statuses = {check["id"]: check["status"] for check in checks}
                self.assertEqual(statuses["content.forbidden-claims"], "fail")
                self.assertEqual(classification["artifact_status"], "fail")
                self.assertEqual(classification["status"], "fail")

    def test_d_confirmed_source_data_is_not_creative_supplement(self) -> None:
        scenario = JUDGE.load_scenario("pdf-evidence-report")
        handoff = """## Pending Verification List

| Page/content | Supplement type | Source status | Suggested action |
|---|---|---|---|
| Page 2, 78 percent | Creative supplement | Pending verification | Confirm or replace |
"""
        checks = JUDGE.inspect_verification_handoff(handoff, scenario, [])
        statuses = {check["id"]: check["status"] for check in checks}
        self.assertEqual(statuses["handoff.protected-source-classification"], "fail")
        self.assertEqual(JUDGE.classify_checks(checks)["status"], "fail")

    def test_source_only_report_can_explicitly_declare_no_creative_supplements(
        self,
    ) -> None:
        scenario = JUDGE.load_scenario("pdf-evidence-report")
        handoff = """## 《待核实内容清单》

无；本报告未新增待客户核实的事实性内容
"""
        checks = JUDGE.inspect_verification_handoff(handoff, scenario, [])
        statuses = {check["id"]: check["status"] for check in checks}
        self.assertEqual(statuses["delivery.verification-handoff"], "pass")
        self.assertEqual(statuses["handoff.creative-fact-coverage"], "pass")
        self.assertEqual(JUDGE.classify_checks(checks)["status"], "pass")

    def test_idea_only_semantic_claims_cannot_pass_with_empty_handoff(self) -> None:
        scenario = JUDGE.load_scenario("idea-live-conversion")
        target = scenario["content_checks"]["allowed_action_targets"][0]
        html_text = f"""
        <main class="deck" data-mode="presentation">
          <section class="slide">
            <p>先把案例变成可调用证据，再谈扩大获客。</p>
            <p>案例散落，这是一个示意场景。</p>
            <p>我们已经处理几十个项目、几百段对话，每个线索都能高效转化。</p>
          </section>
          <section class="slide"><a href="{target}">{target}</a></section>
        </main>
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            html = Path(temp_dir) / "index.html"
            html.write_text(html_text, encoding="utf-8")
            _, content_checks = JUDGE.inspect_content(html, scenario)
        fact_check = next(
            check
            for check in content_checks
            if check["id"] == "content.source-bounded-facts"
        )
        self.assertEqual(fact_check["evidence"]["unexpected"], [])

        handoff = """## 《待核实内容清单》

无；本报告未新增待客户核实的事实性内容
"""
        checks = [
            *content_checks,
            *JUDGE.inspect_verification_handoff(handoff, scenario, []),
        ]
        statuses = {check["id"]: check["status"] for check in checks}
        self.assertEqual(statuses["delivery.verification-handoff"], "warning")
        self.assertEqual(statuses["handoff.creative-fact-coverage"], "warning")
        self.assertEqual(JUDGE.classify_checks(checks)["status"], "conditional")

    def test_e_handoff_does_not_expand_six_question_cap(self) -> None:
        at_cap, _ = self.idea_semantic_checks(self.complete_handoff(), question_count=6)
        over_cap, checks = self.idea_semantic_checks(
            self.complete_handoff(), question_count=7
        )
        self.assertEqual(at_cap["status"], "pass")
        self.assertEqual(over_cap["status"], "fail")
        question_check = next(check for check in checks if check["id"] == "intake.question-cap")
        self.assertEqual(question_check["evidence"]["actual"], 7)


class AggregateResultsTests(unittest.TestCase):
    @staticmethod
    def make_result(
        run_id: str,
        questions: int,
        hard_failures: int,
        *,
        comparable: bool,
        score: int | None,
        revisions: int | None,
        total_tokens: int | None = None,
        workbuddy_points: float | None = None,
        points_source: str = "platform_task_usage",
        balance_before: float | None = None,
        balance_after: float | None = None,
    ) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "run": {
                "id": run_id,
                "scenario_id": "idea-live-conversion",
                "client": "Codex",
                "agent": "Agent A",
                "model": "Model A",
                "skill": {"version": "0.2.0", "commit": "abc1234"},
                "question_count": questions,
                "token_usage": {
                    "availability": "exact" if total_tokens is not None else "unavailable",
                    "source": "platform_task_usage" if total_tokens is not None else "unavailable",
                    "input_tokens": None,
                    "output_tokens": None,
                    "cache_tokens": None,
                    "total_tokens": total_tokens,
                },
                "billing_usage": {
                    "availability": "exact" if workbuddy_points is not None else "unavailable",
                    "source": points_source if workbuddy_points is not None else "unavailable",
                    "workbuddy_points": workbuddy_points,
                    "balance_before": balance_before,
                    "balance_after": balance_after,
                },
            },
            "objective": {"hard_failure_count": hard_failures},
            "human": {
                "dimensions": {"story_progression": {"score": score, "note": ""}},
                "manual_revision_count": revisions,
                "reference_floor": {"status": "unavailable", "note": ""},
            },
            "failure_samples": [],
            "comparison": {
                "comparable": comparable,
                "benchmark_success": comparable and hard_failures == 0,
            },
        }

    def test_aggregate_reports_success_hard_failures_ranges_and_revisions(self) -> None:
        results = [
            self.make_result(
                "one", 2, 0, comparable=True, score=4, revisions=1, total_tokens=100
            ),
            self.make_result(
                "two",
                6,
                2,
                comparable=True,
                score=2,
                revisions=3,
                workbuddy_points=12.5,
            ),
            self.make_result(
                "three",
                4,
                0,
                comparable=False,
                score=None,
                revisions=None,
                total_tokens=200,
                workbuddy_points=7,
                points_source="balance_delta",
                balance_before=100,
                balance_after=93,
            ),
        ]
        report = AGGREGATE.aggregate(results)
        overall = report["overall"]
        self.assertEqual(overall["run_count"], 3)
        self.assertEqual(overall["comparable_run_count"], 2)
        self.assertEqual(overall["success_rate"], 0.5)
        self.assertEqual(overall["hard_failure_count"]["total"], 2)
        self.assertEqual(overall["question_count"]["median"], 4)
        self.assertEqual(overall["question_count"]["range"], [2, 6])
        self.assertEqual(
            overall["usage_availability"]["tokens"],
            {"exact_count": 2, "unavailable_count": 1, "availability_rate": 0.6667},
        )
        self.assertEqual(
            overall["usage_availability"]["workbuddy_points"],
            {"exact_count": 2, "unavailable_count": 1, "availability_rate": 0.6667},
        )
        self.assertEqual(overall["total_tokens"]["median"], 150)
        self.assertEqual(overall["total_tokens"]["range"], [100, 200])
        self.assertEqual(overall["workbuddy_points"]["median"], 9.75)
        self.assertEqual(overall["workbuddy_points"]["range"], [7, 12.5])
        self.assertEqual(overall["human_dimensions"]["story_progression"]["median"], 3)
        self.assertEqual(overall["manual_revision_count"]["median"], 2)
        self.assertEqual(overall["reference_floor_distribution"], {"unavailable": 3})
        self.assertEqual(len(report["groups"]), 1)
        markdown = AGGREGATE.render_markdown(report)
        self.assertIn("Token availability: 66.7% (2/3)", markdown)
        self.assertIn("WorkBuddy points availability: 66.7% (2/3)", markdown)

    def test_result_validation_requires_explicit_usage_availability(self) -> None:
        result = self.make_result(
            "one", 2, 0, comparable=True, score=4, revisions=1
        )
        del result["run"]["billing_usage"]
        with self.assertRaisesRegex(ValueError, "billing_usage"):
            AGGREGATE.validate_result(result, Path("result.json"))

    def test_aggregate_separates_artifact_usable_from_conditional_workflow(self) -> None:
        passed = self.make_result(
            "pass", 3, 0, comparable=True, score=4, revisions=0
        )
        passed["objective"].update(
            {"status": "pass", "artifact_status": "pass", "warning_count": 0}
        )
        passed["comparison"].update(
            {"workflow_status": "pass", "artifact_usable": True}
        )
        conditional = self.make_result(
            "conditional", 4, 0, comparable=True, score=4, revisions=0
        )
        conditional["objective"].update(
            {
                "status": "conditional",
                "artifact_status": "pass",
                "warning_count": 1,
            }
        )
        conditional["comparison"].update(
            {
                "workflow_status": "conditional",
                "artifact_usable": True,
                "benchmark_success": False,
            }
        )
        overall = AGGREGATE.aggregate([passed, conditional])["overall"]
        self.assertEqual(overall["success_rate"], 0.5)
        self.assertEqual(overall["conditional_rate"], 0.5)
        self.assertEqual(overall["artifact_usable_rate"], 1.0)
        self.assertEqual(
            overall["workflow_status_distribution"],
            {"pass": 1, "conditional": 1},
        )

    def test_directory_discovery_ignores_metadata_and_human_review_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "run").mkdir()
            for name in ("result.json", "run-metadata.json", "human-review.json"):
                (root / "run" / name).write_text("{}", encoding="utf-8")
            self.assertEqual(
                AGGREGATE.discover([root]),
                [root / "run" / "result.json"],
            )


if __name__ == "__main__":
    unittest.main()
