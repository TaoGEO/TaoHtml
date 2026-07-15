from __future__ import annotations

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
                "duration",
            }.issubset(run_required)
        )
        human_required = set(schema["$defs"]["human_review"]["required"])
        self.assertIn("manual_revision_count", human_required)
        self.assertIn("reference_floor", human_required)
        self.assertIn("failure_samples", schema["properties"])

        metadata = json.loads(
            (BENCHMARK / "schemas" / "run-metadata.example.json").read_text(encoding="utf-8")
        )
        human_review = json.loads(
            (BENCHMARK / "schemas" / "human-review.example.json").read_text(encoding="utf-8")
        )
        JUDGE.validate_metadata(metadata, metadata["scenario_id"])
        JUDGE.validate_human_review(human_review)


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
            self.assertFalse(any("controller" in path for path in relative_files))
            self.assertFalse(any(path.endswith(".json") for path in relative_files))

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
            self.make_result("one", 2, 0, comparable=True, score=4, revisions=1),
            self.make_result("two", 6, 2, comparable=True, score=2, revisions=3),
            self.make_result("three", 4, 0, comparable=False, score=None, revisions=None),
        ]
        report = AGGREGATE.aggregate(results)
        overall = report["overall"]
        self.assertEqual(overall["run_count"], 3)
        self.assertEqual(overall["comparable_run_count"], 2)
        self.assertEqual(overall["success_rate"], 0.5)
        self.assertEqual(overall["hard_failure_count"]["total"], 2)
        self.assertEqual(overall["question_count"]["median"], 4)
        self.assertEqual(overall["question_count"]["range"], [2, 6])
        self.assertEqual(overall["human_dimensions"]["story_progression"]["median"], 3)
        self.assertEqual(overall["manual_revision_count"]["median"], 2)
        self.assertEqual(overall["reference_floor_distribution"], {"unavailable": 3})
        self.assertEqual(len(report["groups"]), 1)

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
