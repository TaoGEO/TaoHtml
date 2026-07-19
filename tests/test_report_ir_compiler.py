from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

from tests.test_report_ir_v1 import bound_ir, valid_ir


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "taohtml" / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
THEME_IDS = (
    "black-white-fluorescent-cards",
    "rigorous-consulting-report",
    "corporate-annual-report",
    "editorial-collage",
)


def load_script(name: str) -> ModuleType:
    path = SCRIPT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"taohtml_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER = load_script("compile_report_ir")
PROJECT_THEME_COMPILER = load_script("compile_project_theme")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class ReportIrCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_bytes = b"segment,value\nenterprise,28\nother,7\n"
        self.ir = valid_ir(sha256(self.source_bytes))

    def _project(self, root: Path) -> None:
        materials = root / "materials"
        materials.mkdir(parents=True)
        (materials / "growth.csv").write_bytes(self.source_bytes)

    def test_compiles_variable_seven_page_report_into_runtime(self) -> None:
        self.ir["sources"][0].update(
            {
                "title": "客户增长数据",
                "publisher": "客户研究组",
                "published_date": "2026-07",
                "page_locator": "数据表 1",
            }
        )
        self.ir["pages"][1]["source_display"] = "footer"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            output = root / "build"
            manifest = COMPILER.compile_ir(self.ir, root, output)
            rendered = (output / "index.html").read_text(encoding="utf-8")
            source_map = json.loads((output / "source-map.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["counts"]["pages"], 7)
            self.assertEqual(manifest["compiler_version"], "0.2.0-dev")
            self.assertEqual(manifest["counts"]["output_pages"], 7)
            self.assertEqual(rendered.count('class="slide ri-page'), 7)
            self.assertIn('data-report-ir-version="1.0"', rendered)
            self.assertIn('data-ir-page-id="page-growth"', rendered)
            self.assertIn('data-ir-block-id="block-growth-chart"', rendered)
            self.assertIn('data-step="1"', rendered)
            self.assertIn('id="taohtml-speaker-notes"', rendered)
            self.assertIn("客户增长数据 · 客户研究组 · 2026-07 · 数据表 1", rendered)
            self.assertEqual(len(source_map["pages"]), 7)
            self.assertEqual(manifest["qa_execution_claim"], "not_executed_by_compiler")
            self.assertEqual(
                manifest["workflow_profile"]["binding_state"], "legacy_unbound"
            )
            self.assertIsNone(manifest["workflow_profile"]["primary_profile_id"])
            self.assertEqual(
                manifest["runtime"]["report_ir_patch_contract"],
                "embedded-html-v1",
            )
            self.assertNotIn(
                "runtime_editor_does_not_yet_export_a_report_ir_patch",
                manifest["open_boundaries"],
            )

    def test_compiler_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            first = root / "first"
            second = root / "second"
            first_manifest = COMPILER.compile_ir(self.ir, root, first)
            second_manifest = COMPILER.compile_ir(self.ir, root, second)
            for name in (
                "index.html",
                "source-map.json",
                "report.ir.normalized.json",
                "build-manifest.json",
            ):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            self.assertEqual(
                first_manifest["outputs"]["html"]["sha256"],
                second_manifest["outputs"]["html"]["sha256"],
            )

    def test_workflow_profile_binding_changes_identity_but_not_compiler_decisions(self) -> None:
        first_ir = bound_ir(
            self.ir,
            "research-analysis-argumentation",
            selection_basis="已确认目标是形成证据与推理可检查的专业结论。",
        )
        second_ir = bound_ir(
            self.ir,
            "proposal-planning-decision",
            selection_basis="已确认目标是支持管理层在真实选项之间作出决策。",
            capability_overlays=[
                {
                    "source_profile_id": "live-presentation-persuasion",
                    "bounded_capability": "现场讲解关键取舍",
                    "reason": "决策会在会议中现场说明。",
                    "affected_scope": "推荐与风险页",
                }
            ],
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            first_output = root / "first-profile"
            second_output = root / "second-profile"
            first_manifest = COMPILER.compile_ir(first_ir, root, first_output)
            second_manifest = COMPILER.compile_ir(second_ir, root, second_output)

            self.assertNotEqual(
                first_manifest["report_ir"]["normalized_sha256"],
                second_manifest["report_ir"]["normalized_sha256"],
            )
            self.assertNotEqual(
                first_manifest["workflow_profile"]["binding_sha256"],
                second_manifest["workflow_profile"]["binding_sha256"],
            )
            self.assertNotEqual(
                first_manifest["outputs"]["html"]["sha256"],
                second_manifest["outputs"]["html"]["sha256"],
            )
            self.assertEqual(
                first_manifest["report_ir"]["semantic_graph_sha256"],
                second_manifest["report_ir"]["semantic_graph_sha256"],
            )
            self.assertEqual(first_manifest["theme"], second_manifest["theme"])
            self.assertEqual(first_manifest["runtime"], second_manifest["runtime"])
            self.assertEqual(
                first_manifest["degradations"], second_manifest["degradations"]
            )
            first_html = (first_output / "index.html").read_text(encoding="utf-8")
            second_html = (second_output / "index.html").read_text(encoding="utf-8")
            first_pages = first_html.split(COMPILER.START_MARKER, 1)[1].split(
                COMPILER.END_MARKER, 1
            )[0]
            second_pages = second_html.split(COMPILER.START_MARKER, 1)[1].split(
                COMPILER.END_MARKER, 1
            )[0]
            self.assertEqual(first_pages, second_pages)
            first_source_map = json.loads(
                (first_output / "source-map.json").read_text(encoding="utf-8")
            )
            second_source_map = json.loads(
                (second_output / "source-map.json").read_text(encoding="utf-8")
            )
            self.assertEqual(first_source_map["pages"], second_source_map["pages"])
            self.assertIn('data-report-ir-version="1.1"', first_html)
            self.assertEqual(
                second_manifest["workflow_profile"]["capability_overlays"],
                second_ir["workflow_profile"]["capability_overlays"],
            )
            self.assertEqual(
                second_manifest["workflow_profile"],
                COMPILER.workflow_profile_record(second_ir),
            )

    def test_same_ir_semantics_compile_through_all_four_themes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            normalized_hashes: set[str] = set()
            semantic_hashes: set[str] = set()
            html_hashes: set[str] = set()
            for theme_id in THEME_IDS:
                candidate = copy.deepcopy(self.ir)
                candidate["build_binding"]["theme"]["ref"] = theme_id
                output = root / theme_id
                manifest = COMPILER.compile_ir(candidate, root, output)
                rendered = (output / "index.html").read_text(encoding="utf-8")
                normalized_hashes.add(manifest["report_ir"]["normalized_sha256"])
                semantic_hashes.add(manifest["report_ir"]["semantic_graph_sha256"])
                html_hashes.add(manifest["outputs"]["html"]["sha256"])
                self.assertIn(f'data-theme="{theme_id}"', rendered)
                self.assertEqual(manifest["counts"]["output_pages"], 7)
            self.assertEqual(len(normalized_hashes), 4)
            self.assertEqual(len(semantic_hashes), 1)
            self.assertEqual(len(html_hashes), 4)

    def test_v10_and_v11_share_computed_header_and_built_in_theme_styles(self) -> None:
        from playwright.sync_api import sync_playwright

        expected_accents = {
            "black-white-fluorescent-cards": "#d8ff19",
            "rigorous-consulting-report": "#2a7f82",
            "corporate-annual-report": "#b89a5b",
            "editorial-collage": "#f1c84b",
        }
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            outputs: dict[tuple[str, str], Path] = {}
            for theme_id in THEME_IDS:
                legacy = copy.deepcopy(self.ir)
                legacy["build_binding"]["theme"]["ref"] = theme_id
                current = bound_ir(
                    legacy,
                    "research-analysis-argumentation",
                    selection_basis="已确认目标是形成证据与推理可检查的专业结论。",
                )
                for version, candidate in (("1.0", legacy), ("1.1", current)):
                    output = root / f"{theme_id}-{version}"
                    COMPILER.compile_ir(candidate, root, output)
                    outputs[(theme_id, version)] = output / "index.html"

            snapshots: dict[tuple[str, str], dict[str, object]] = {}
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(args=["--disable-gpu"])
                page = browser.new_page(viewport={"width": 1600, "height": 900})
                for identity, html_path in outputs.items():
                    page.goto(html_path.resolve().as_uri(), wait_until="load")
                    snapshots[identity] = page.locator(".slide.active").evaluate(
                        """slide => {
                          const deckStyle = getComputedStyle(document.querySelector('.deck'));
                          const pick = selector => {
                            const style = getComputedStyle(slide.querySelector(selector));
                            return {
                              display: style.display,
                              fontSize: style.fontSize,
                              lineHeight: style.lineHeight,
                              marginTop: style.marginTop,
                              marginBottom: style.marginBottom,
                              maxWidth: style.maxWidth,
                            };
                          };
                          return {
                            accent: deckStyle.getPropertyValue('--ri-accent').trim(),
                            pagePadding: getComputedStyle(slide).padding,
                            kicker: pick('.ri-kicker'),
                            title: pick('.ri-title'),
                            task: pick('.ri-task'),
                          };
                        }"""
                    )
                browser.close()

            for theme_id, expected_accent in expected_accents.items():
                with self.subTest(theme=theme_id):
                    legacy = snapshots[(theme_id, "1.0")]
                    current = snapshots[(theme_id, "1.1")]
                    self.assertEqual(current, legacy)
                    self.assertEqual(current["accent"], expected_accent)
                    self.assertEqual(current["pagePadding"], "56px 68px 64px")
                    self.assertEqual(current["kicker"]["display"], "flex")
                    self.assertEqual(current["kicker"]["fontSize"], "14px")
                    self.assertEqual(current["title"]["fontSize"], "76px")
                    expected_line_height = (
                        "95.76px" if theme_id == "editorial-collage" else "89.68px"
                    )
                    self.assertEqual(current["title"]["lineHeight"], expected_line_height)
                    self.assertEqual(current["title"]["marginTop"], "0px")
                    self.assertEqual(current["task"]["fontSize"], "19.52px")
                    self.assertEqual(current["task"]["marginTop"], "16px")

    def test_cjk_single_two_and_three_line_titles_are_safe_across_themes_and_viewports(
        self,
    ) -> None:
        from playwright.sync_api import sync_playwright

        title_texts = {
            "block-cover-title": (
                "观察记录、访谈感受与预约事件链尚未对齐，"
                "当前证据不足以对释放规则作出因果归因"
            ),
            "block-growth-title": "共享会议室现有观察仍不足以支持释放规则因果归因",
            "block-method-title": "证据责任边界",
        }
        candidate = bound_ir(
            self.ir,
            "research-analysis-argumentation",
            selection_basis="已确认目标是形成证据与推理可检查的专业结论。",
        )
        for block in candidate["blocks"]:
            if block["id"] in title_texts:
                block["text"] = title_texts[block["id"]]
            if block["id"] == "block-method-process":
                block.clear()
                block.update(
                    {
                        "id": "block-method-process",
                        "kind": "metric",
                        "items": [
                            {
                                "id": "item-method-one",
                                "label": "North",
                                "value": "31 / 168 · 18.5% · 当前观察比例",
                            },
                            {
                                "id": "item-method-two",
                                "label": "South",
                                "value": "18 / 144 · 12.5% · 当前观察比例",
                            },
                            {
                                "id": "item-method-three",
                                "label": "合计",
                                "value": "49 / 312 · 15.7% · 当前观察比例",
                            },
                        ],
                    }
                )

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            outputs: dict[str, Path] = {}
            for theme_id in THEME_IDS:
                themed = copy.deepcopy(candidate)
                themed["build_binding"]["theme"]["ref"] = theme_id
                output = root / theme_id
                COMPILER.compile_ir(themed, root, output)
                outputs[theme_id] = output / "index.html"

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(args=["--disable-gpu"])
                saw_multiline_metric = False
                for width, height in ((1366, 768), (1600, 900), (1920, 1080)):
                    for theme_id, html_path in outputs.items():
                        with self.subTest(theme=theme_id, viewport=(width, height)):
                            page = browser.new_page(
                                viewport={"width": width, "height": height}
                            )
                            page.goto(html_path.resolve().as_uri(), wait_until="load")
                            measurements = [
                                page.evaluate(
                                    """index => {
                                      window.TaoHtmlRuntime.showPage(index);
                                      const slide = document.querySelectorAll('.slide')[index];
                                      const title = slide.querySelector('.ri-title');
                                      const task = slide.querySelector('.ri-task');
                                      const content = slide.querySelector('.ri-content');
                                      const titleRange = document.createRange();
                                      titleRange.selectNodeContents(title);
                                      const titleRects = [...titleRange.getClientRects()]
                                        .filter(rect => rect.width > 0 && rect.height > 0)
                                        .map(rect => ({
                                          top: rect.top,
                                          bottom: rect.bottom,
                                        }));
                                      const taskRange = document.createRange();
                                      taskRange.selectNodeContents(task);
                                      const taskRects = [...taskRange.getClientRects()]
                                        .filter(rect => rect.width > 0 && rect.height > 0);
                                      const slideRect = slide.getBoundingClientRect();
                                      const titleRect = title.getBoundingClientRect();
                                      const contentRect = content.getBoundingClientRect();
                                      const metricLineGaps = [...slide.querySelectorAll(
                                        '.ri-metric-value'
                                      )].flatMap(metric => {
                                        const range = document.createRange();
                                        range.selectNodeContents(metric);
                                        const rects = [...range.getClientRects()]
                                          .filter(rect => rect.width > 0 && rect.height > 0);
                                        return rects.slice(1).map((rect, line) =>
                                          rect.top - rects[line].bottom);
                                      });
                                      const inside = rect => rect.left >= slideRect.left - 2 &&
                                        rect.top >= slideRect.top - 2 &&
                                        rect.right <= slideRect.right + 2 &&
                                        rect.bottom <= slideRect.bottom + 2;
                                      return {
                                        lines: titleRects.length,
                                        lineGaps: titleRects.slice(1).map((rect, line) =>
                                          rect.top - titleRects[line].bottom),
                                        titleTaskGap: taskRects[0].top - titleRects.at(-1).bottom,
                                        taskContentGap: contentRect.top - taskRects.at(-1).bottom,
                                        metricLineGaps,
                                        titleInside: inside(titleRect),
                                        contentInside: inside(contentRect),
                                      };
                                    }""",
                                    index,
                                )
                                for index in range(3)
                            ]
                            self.assertEqual(
                                [item["lines"] for item in measurements], [3, 2, 1]
                            )
                            for item in measurements:
                                saw_multiline_metric = (
                                    saw_multiline_metric or bool(item["metricLineGaps"])
                                )
                                self.assertTrue(
                                    all(gap >= 1 for gap in item["lineGaps"]), item
                                )
                                self.assertTrue(
                                    all(gap >= 1 for gap in item["metricLineGaps"]), item
                                )
                                self.assertGreaterEqual(item["titleTaskGap"], 1, item)
                                self.assertGreaterEqual(item["taskContentGap"], 1, item)
                                self.assertTrue(item["titleInside"], item)
                                self.assertTrue(item["contentInside"], item)
                            page.close()
                browser.close()
                self.assertTrue(saw_multiline_metric)

    def test_v10_and_v11_corporate_headers_pass_browser_collision_qa(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            theme_dir = PROJECT_THEME_COMPILER.compile_theme(
                FIXTURES / "corporate-family-handoff.json", root / "theme"
            )
            theme_manifest = json.loads(
                (theme_dir / "theme.json").read_text(encoding="utf-8")
            )
            legacy = copy.deepcopy(self.ir)
            legacy["build_binding"]["theme"] = {
                "kind": "project_theme",
                "ref": theme_manifest["id"],
                "version": theme_manifest["schema_version"],
            }
            legacy["build_binding"]["enterprise"] = {
                "profile_ref": "enterprise-orbital",
                "profile_version": 1,
                "shell_policy": "fidelity",
            }
            current = bound_ir(
                legacy,
                "periodic-operations-reporting",
                selection_basis="已确认目标是形成周期运营复盘。",
            )
            checker = SCRIPT_DIR / "check_html_deck.py"
            for version, candidate in (("1.0", legacy), ("1.1", current)):
                with self.subTest(report_ir_version=version):
                    output = root / f"corporate-{version}"
                    COMPILER.compile_ir(
                        candidate,
                        root,
                        output,
                        project_theme_dir=theme_dir,
                    )
                    qa_output = root / f"corporate-{version}-qa"
                    completed = subprocess.run(
                        [
                            sys.executable,
                            str(checker),
                            str(output / "index.html"),
                            str(qa_output),
                            "--width",
                            "1600",
                            "--height",
                            "900",
                            "--max-pages",
                            "1",
                        ],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    report = json.loads(
                        (qa_output / "qa-report.json").read_text(encoding="utf-8")
                    )
                    self.assertEqual(completed.returncode, 0, completed.stdout)
                    self.assertEqual(report["pages"][0]["text_collisions"], [])

    def test_appendix_is_a_deterministic_derived_page(self) -> None:
        self.ir["appendices"] = [
            {
                "id": "appendix-method",
                "title": "研究方法",
                "block_refs": ["block-method-process"],
                "source_refs": ["source-customer-data"],
            }
        ]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            output = root / "build"
            manifest = COMPILER.compile_ir(self.ir, root, output)
            rendered = (output / "index.html").read_text(encoding="utf-8")
            self.assertEqual(manifest["counts"]["appendix_pages"], 1)
            self.assertEqual(manifest["counts"]["output_pages"], 8)
            self.assertIn('data-ir-appendix-ref="appendix-method"', rendered)

    def test_non_monotonic_page_state_fails_instead_of_silently_changing_meaning(self) -> None:
        self.ir["pages"][1]["state_sequence"].extend(
            [
                {
                    "id": "state-growth-regression",
                    "visible_refs": ["block-growth-title"],
                    "emphasized_refs": ["block-growth-title"],
                    "focus_ref": "block-growth-title",
                    "transition_intent": "final",
                },
                {
                    "id": "state-growth-restored",
                    "visible_refs": ["block-growth-title", "block-growth-chart"],
                    "emphasized_refs": ["block-growth-chart"],
                    "focus_ref": "block-growth-chart",
                    "transition_intent": "final",
                },
            ]
        )
        self.ir["pages"][1]["reading_final_state_ref"] = "state-growth-restored"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            with self.assertRaises(COMPILER.CompileError):
                COMPILER.compile_ir(self.ir, root, root / "build")

    def test_project_theme_requires_the_exact_validated_bundle(self) -> None:
        self.ir["build_binding"]["theme"] = {
            "kind": "project_theme",
            "ref": "project-example",
            "version": "1.0",
        }
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            with self.assertRaisesRegex(COMPILER.CompileError, "--project-theme-dir"):
                COMPILER.compile_ir(self.ir, root, root / "build")

    def test_reference_reconstruction_project_theme_compiles_without_enterprise_binding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            theme_dir = PROJECT_THEME_COMPILER.compile_theme(
                FIXTURES / "reference-theme-handoff.json", root / "theme"
            )
            theme_manifest = json.loads(
                (theme_dir / "theme.json").read_text(encoding="utf-8")
            )
            self.ir["build_binding"]["theme"] = {
                "kind": "project_theme",
                "ref": theme_manifest["id"],
                "version": theme_manifest["schema_version"],
            }
            manifest = COMPILER.compile_ir(
                self.ir,
                root,
                root / "build",
                project_theme_dir=theme_dir,
            )
            rendered = (root / "build" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(manifest["theme"]["reference_mode"], "reconstruct")
            self.assertNotIn("enterprise_shell", manifest)
            self.assertEqual(rendered.count('class="slide ri-page'), 7)
            self.assertIn('data-theme-kind="project"', rendered)

    def test_corporate_fidelity_routes_arbitrary_pages_without_mutating_fixed_shells(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            theme_dir = PROJECT_THEME_COMPILER.compile_theme(
                FIXTURES / "corporate-family-handoff.json", root / "theme"
            )
            theme_manifest = json.loads(
                (theme_dir / "theme.json").read_text(encoding="utf-8")
            )
            self.ir["build_binding"]["theme"] = {
                "kind": "project_theme",
                "ref": theme_manifest["id"],
                "version": theme_manifest["schema_version"],
            }
            self.ir["build_binding"]["enterprise"] = {
                "profile_ref": "enterprise-orbital",
                "profile_version": 1,
                "shell_policy": "fidelity",
            }
            self.ir = bound_ir(
                self.ir,
                "brand-communication-editorial-publishing",
                selection_basis="已确认目标是形成面向外部受众的品牌叙事。",
            )
            output = root / "build"
            manifest = COMPILER.compile_ir(
                self.ir,
                root,
                output,
                project_theme_dir=theme_dir,
            )
            rendered = (output / "index.html").read_text(encoding="utf-8")
            output_sections = [
                match.group(0)
                for match in re.finditer(
                    r"<section\b[^>]*>.*?</section>", rendered, flags=re.DOTALL
                )
                if 'data-ir-shell-role="' in match.group(0).split(">", 1)[0]
            ]
            roles = [
                re.search(r'data-ir-shell-role="([^"]+)"', section).group(1)
                for section in output_sections
            ]
            self.assertEqual(
                roles,
                ["cover", "data", "content", "content", "content", "data", "content"],
            )
            self.assertEqual(rendered.count(" ri-corporate-page"), 7)
            self.assertEqual(rendered.count(" ri-corporate-page active"), 1)
            source_sections = COMPILER._project_sections_by_role(
                (theme_dir / "templates.html").read_text(encoding="utf-8")
            )
            for output_section, role in zip(output_sections, roles):
                source_bounds = COMPILER._find_div_content_bounds(
                    source_sections[role], "pt-corporate-fixed-shell"
                )
                output_bounds = COMPILER._find_div_content_bounds(
                    output_section, "pt-corporate-fixed-shell"
                )
                source_fixed = source_sections[role][source_bounds[0] : source_bounds[3]]
                output_fixed = output_section[output_bounds[0] : output_bounds[3]]
                self.assertEqual(source_fixed, output_fixed)
            self.assertEqual(manifest["theme"]["reference_mode"], "corporate_fidelity")
            self.assertEqual(
                manifest["enterprise_shell"]["protected_shell_policy"],
                "fixed_descendants_preserved",
            )
            self.assertEqual(
                manifest["workflow_profile"]["primary_profile_id"],
                "brand-communication-editorial-publishing",
            )
            self.assertEqual(
                manifest["enterprise_shell"]["profile_ref"], "enterprise-orbital"
            )
            self.assertNotIn("profile_ref", manifest["workflow_profile"])
            self.assertNotIn(
                "project_theme_and_enterprise_shell_compilation_not_implemented",
                manifest["open_boundaries"],
            )

    def test_corporate_fidelity_rejects_missing_enterprise_binding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            theme_dir = PROJECT_THEME_COMPILER.compile_theme(
                FIXTURES / "corporate-family-handoff.json", root / "theme"
            )
            theme_manifest = json.loads(
                (theme_dir / "theme.json").read_text(encoding="utf-8")
            )
            self.ir["build_binding"]["theme"] = {
                "kind": "project_theme",
                "ref": theme_manifest["id"],
                "version": theme_manifest["schema_version"],
            }
            with self.assertRaisesRegex(COMPILER.CompileError, "requires build_binding.enterprise"):
                COMPILER.compile_ir(
                    self.ir,
                    root,
                    root / "build",
                    project_theme_dir=theme_dir,
                )

    def test_cli_emits_build_and_machine_readable_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            ir_path = root / "report.ir.json"
            ir_path.write_text(json.dumps(self.ir, ensure_ascii=False), encoding="utf-8")
            output = root / "build"
            result = subprocess.run(
                [
                    str(ROOT / ".venv" / "bin" / "python"),
                    str(SCRIPT_DIR / "compile_report_ir.py"),
                    str(ir_path),
                    "--artifact-root",
                    str(root),
                    "--output-dir",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("REPORT_IR_COMPILED pages=7", result.stdout)
            manifest = json.loads((output / "build-manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["validation"]["compiler_ready"])


if __name__ == "__main__":
    unittest.main()
