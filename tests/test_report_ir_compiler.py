from __future__ import annotations

import base64
import copy
import hashlib
import io
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image, ImageChops, ImageStat

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
DENSE_LAYOUT_CASES = json.loads(
    (FIXTURES / "report-ir" / "dense-layout-cases.json").read_text(encoding="utf-8")
)["cases"]


def load_script(name: str) -> ModuleType:
    path = SCRIPT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"taohtml_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER = load_script("compile_report_ir")
PROJECT_THEME_COMPILER = load_script("compile_project_theme")
HTML_QA = load_script("check_html_deck")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def assert_fixed_asset_visible(
    test: unittest.TestCase,
    locator: Any,
    painted_page: Image.Image,
    *,
    page_index: int,
) -> None:
    """Compare the painted page crop with the locked asset, independent of brand colors."""
    box = locator.bounding_box()
    test.assertIsNotNone(box)
    assert box is not None
    actual = painted_page.crop(
        (
            round(box["x"]),
            round(box["y"]),
            round(box["x"] + box["width"]),
            round(box["y"] + box["height"]),
        )
    ).convert("RGB")
    source = locator.get_attribute("src")
    test.assertIsNotNone(source)
    assert source is not None
    test.assertTrue(source.startswith("data:image/png;base64,"), source[:32])
    expected = Image.open(
        io.BytesIO(base64.b64decode(source.split(",", 1)[1]))
    ).convert("RGB")
    expected = expected.resize(actual.size, Image.Resampling.BILINEAR)
    difference = ImageChops.difference(actual, expected)
    mean_error = sum(ImageStat.Stat(difference).mean) / 3
    mismatch_ratio = sum(
        1 for pixel in difference.get_flattened_data() if max(pixel) > 32
    ) / (actual.width * actual.height)
    asset_id = locator.get_attribute("data-asset-id")
    test.assertLess(
        mean_error,
        12,
        f"page {page_index + 1} locked asset {asset_id} is visually occluded",
    )
    test.assertLess(
        mismatch_ratio,
        0.15,
        f"page {page_index + 1} locked asset {asset_id} does not match its crop",
    )


class ReportIrCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_bytes = b"segment,value\nenterprise,28\nother,7\n"
        self.ir = valid_ir(sha256(self.source_bytes))

    def _project(self, root: Path) -> None:
        materials = root / "materials"
        materials.mkdir(parents=True)
        (materials / "growth.csv").write_bytes(self.source_bytes)

    def _dense_layout_ir(self, case: dict, *, profile_bound: bool) -> dict:
        candidate = copy.deepcopy(self.ir)
        title = next(
            block for block in candidate["blocks"] if block["id"] == "block-compare-title"
        )
        title["text"] = case["title"]
        items = next(
            block for block in candidate["blocks"] if block["id"] == "block-compare"
        )
        items.clear()
        items.update(
            {
                "id": "block-compare",
                "kind": case["kind"],
                "items": copy.deepcopy(case["items"]),
                "claim_refs": ["claim-growth"],
            }
        )
        page = next(page for page in candidate["pages"] if page["id"] == "page-compare")
        page["form"] = case["form"]
        page["task"] = case["task"]
        block_refs = ["block-compare-title", "block-compare"]
        if case["auxiliary_block"]:
            candidate["blocks"].append(
                {
                    "id": "block-density-boundary",
                    "kind": "body_text",
                    "text": (
                        "本页保留一项独立的边界说明，用来验证高密度条目不会挤压"
                        "相邻内容，也不会把说明移出固定画布。"
                    ),
                    "claim_refs": ["claim-growth"],
                }
            )
            block_refs.append("block-density-boundary")
        page["block_refs"] = block_refs
        page["visual_intent"].update(
            {
                "primary_focus_ref": "block-compare",
                "reading_order": list(block_refs),
                "relationships": [],
                "composition_family": f"{case['form']}-adaptive-density",
            }
        )
        unit = next(
            unit
            for unit in candidate["narrative_units"]
            if unit["id"] == "unit-compare"
        )
        unit["block_refs"] = list(block_refs)
        unit["takeaway"] = case["title"]
        if profile_bound:
            candidate = bound_ir(
                candidate,
                "research-analysis-argumentation",
                selection_basis="已确认目标是形成证据与推理可检查的专业结论。",
            )
        return candidate

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

    def test_data_visualization_caption_is_preserved(self) -> None:
        chart = next(
            block
            for block in self.ir["blocks"]
            if block["id"] == "block-growth-chart"
        )
        chart["caption"] = "图注保留数据范围、比较口径与阅读边界。"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            output = root / "build"
            COMPILER.compile_ir(self.ir, root, output)
            rendered = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn('class="ri-chart-caption"', rendered)
            self.assertIn(chart["caption"], rendered)
            self.assertIn(
                'data-ir-edit-key="block:block-growth-chart:caption"', rendered
            )

    def test_page_task_is_internal_and_explicit_subtitle_is_visible_at_1366(self) -> None:
        from playwright.sync_api import sync_playwright

        candidate = copy.deepcopy(self.ir)
        candidate["pages"][0]["subtitle_ref"] = "block-cover-lede"
        task_values = [page["task"] for page in candidate["pages"]]
        subtitle = next(
            block["text"]
            for block in candidate["blocks"]
            if block["id"] == "block-cover-lede"
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            output = root / "build"
            COMPILER.compile_ir(candidate, root, output)
            rendered = (output / "index.html").read_text(encoding="utf-8")
            source_map = json.loads(
                (output / "source-map.json").read_text(encoding="utf-8")
            )
            self.assertNotIn('class="ri-task"', rendered)
            self.assertNotIn('data-ir-edit-entity="page"', rendered)
            for task in task_values:
                self.assertNotIn(task, rendered)
            self.assertEqual(rendered.count(subtitle), 1)
            self.assertIn('class="ri-subtitle', rendered)
            self.assertEqual(
                source_map["pages"]["page-cover"]["subtitle_ref"],
                "block-cover-lede",
            )

            screenshot = root / "page-cover-1366x768.png"
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(args=["--disable-gpu"])
                page = browser.new_page(viewport={"width": 1366, "height": 768})
                page.goto((output / "index.html").resolve().as_uri(), wait_until="load")
                page.evaluate("() => window.TaoHtmlRuntime.setMode('reading')")
                self.assertEqual(page.locator(".slide.active .ri-task").count(), 0)
                self.assertEqual(page.get_by_text(task_values[0], exact=True).count(), 0)
                self.assertEqual(page.locator(".slide.active .ri-subtitle").count(), 1)
                bounds = page.locator(".slide.active .ri-subtitle").evaluate(
                    """subtitle => {
                      const box = subtitle.getBoundingClientRect();
                      const slide = subtitle.closest('.slide').getBoundingClientRect();
                      return {
                        inside: box.left >= slide.left && box.top >= slide.top &&
                          box.right <= slide.right && box.bottom <= slide.bottom,
                        width: box.width,
                        height: box.height,
                      };
                    }"""
                )
                self.assertTrue(bounds["inside"], bounds)
                self.assertGreater(bounds["width"], 0)
                self.assertGreater(bounds["height"], 0)
                self.assertEqual(page.evaluate(HTML_QA.OVERFLOW_CHECK), [])
                page.screenshot(path=str(screenshot))
                browser.close()
            with Image.open(screenshot) as image:
                self.assertEqual(image.size, (1366, 768))

    def test_generalized_density_cases_select_readable_item_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            for case in DENSE_LAYOUT_CASES:
                for version, profile_bound in (("1.0", False), ("1.1", True)):
                    with self.subTest(case=case["id"], report_ir_version=version):
                        candidate = self._dense_layout_ir(
                            case,
                            profile_bound=profile_bound,
                        )
                        output = root / f"{case['id']}-{version}"
                        COMPILER.compile_ir(candidate, root, output)
                        rendered = (output / "index.html").read_text(encoding="utf-8")
                        source_map = json.loads(
                            (output / "source-map.json").read_text(encoding="utf-8")
                        )
                        plan = source_map["pages"]["page-compare"]["layout_plan"]
                        self.assertEqual(
                            plan["arrangement"], case["expected_arrangement"]
                        )
                        self.assertEqual(
                            plan["item_columns"]["block-compare"],
                            case["expected_item_columns"],
                        )
                        self.assertIn(
                            f'ri-arrangement-{case["expected_arrangement"]}', rendered
                        )
                        self.assertIn(
                            f'ri-item-columns-{case["expected_item_columns"]}', rendered
                        )
                        self.assertIn(case["title"], rendered)
                        for item in case["items"]:
                            self.assertIn(item["label"], rendered)
                            self.assertIn(item["value"], rendered)

    def test_density_layout_fails_closed_beyond_safe_item_budget(self) -> None:
        case = copy.deepcopy(DENSE_LAYOUT_CASES[-1])
        case["items"][0]["label"] = "无法在固定画布安全容纳的完整条目" * 20
        candidate = self._dense_layout_ir(case, profile_bound=True)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            with self.assertRaisesRegex(
                COMPILER.CompileError,
                "safe item layout budget",
            ):
                COMPILER.compile_ir(candidate, root, root / "build")

    def test_project_theme_narrow_editable_region_limits_item_columns(self) -> None:
        from playwright.sync_api import sync_playwright

        case = copy.deepcopy(DENSE_LAYOUT_CASES[1])
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            theme_dir = PROJECT_THEME_COMPILER.compile_theme(
                FIXTURES / "corporate-family-handoff.json", root / "theme"
            )
            theme_manifest = json.loads(
                (theme_dir / "theme.json").read_text(encoding="utf-8")
            )
            candidate = self._dense_layout_ir(case, profile_bound=True)
            page = next(
                page for page in candidate["pages"] if page["id"] == "page-compare"
            )
            page["form"] = "section"
            page["visual_intent"]["composition_family"] = "section-adaptive-density"
            candidate["build_binding"]["theme"] = {
                "kind": "project_theme",
                "ref": theme_manifest["id"],
                "version": theme_manifest["schema_version"],
            }
            candidate["build_binding"]["enterprise"] = {
                "profile_ref": "enterprise-orbital",
                "profile_version": 1,
                "shell_policy": "fidelity",
            }
            project_output = root / "project-build"
            COMPILER.compile_ir(
                candidate,
                root,
                project_output,
                project_theme_dir=theme_dir,
            )
            project_source_map = json.loads(
                (project_output / "source-map.json").read_text(encoding="utf-8")
            )
            project_plan = project_source_map["pages"]["page-compare"]["layout_plan"]
            section_shell = next(
                shell
                for shell in theme_manifest["corporate_template_family"]["shell_variants"]
                if shell["role"] == "section"
            )
            expected_width = (
                COMPILER.MIN_LAYOUT_VIEWPORT_WIDTH
                * section_shell["editable_region"]["bbox"][2]
                - COMPILER.CORPORATE_EDITABLE_HORIZONTAL_PADDING
            )
            self.assertAlmostEqual(project_plan["content_width"], expected_width, places=2)
            self.assertEqual(project_plan["item_columns"]["block-compare"], 2)

            built_in = copy.deepcopy(candidate)
            built_in["build_binding"].pop("enterprise")
            built_in["build_binding"]["theme"] = {
                "kind": "built_in",
                "ref": "rigorous-consulting-report",
            }
            built_in_output = root / "built-in-build"
            COMPILER.compile_ir(built_in, root, built_in_output)
            built_in_source_map = json.loads(
                (built_in_output / "source-map.json").read_text(encoding="utf-8")
            )
            built_in_plan = built_in_source_map["pages"]["page-compare"]["layout_plan"]
            self.assertGreater(
                built_in_plan["content_width"], project_plan["content_width"]
            )
            self.assertEqual(built_in_plan["item_columns"]["block-compare"], 4)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(args=["--disable-gpu"])
                browser_page = browser.new_page(viewport={"width": 1366, "height": 768})
                browser_page.goto(
                    (project_output / "index.html").resolve().as_uri(),
                    wait_until="load",
                )
                browser_page.evaluate("() => window.TaoHtmlRuntime.showPage(3)")
                browser_page.evaluate("() => window.TaoHtmlRuntime.setMode('reading')")
                columns = browser_page.locator(
                    ".slide.active .ri-item-columns-2"
                ).evaluate(
                    "element => getComputedStyle(element).gridTemplateColumns.split(' ').length"
                )
                self.assertEqual(columns, 2)
                self.assertEqual(browser_page.evaluate(HTML_QA.OVERFLOW_CHECK), [])
                collisions = browser_page.evaluate(HTML_QA.TEXT_COLLISION_CHECK)
                self.assertEqual(collisions["collisions"], [])
                self.assertEqual(collisions["intra_element_collisions"], [])
                browser.close()

    def test_high_density_fixture_passes_browser_qa_across_viewports(self) -> None:
        from playwright.sync_api import sync_playwright

        case = copy.deepcopy(DENSE_LAYOUT_CASES[-1])
        candidate = self._dense_layout_ir(case, profile_bound=True)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            output = root / "build"
            COMPILER.compile_ir(candidate, root, output)
            rendered = (output / "index.html").read_text(encoding="utf-8")
            for item in case["items"]:
                self.assertIn(item["label"], rendered)
                self.assertIn(item["value"], rendered)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(args=["--disable-gpu"])
                for width, height in ((1366, 768), (1600, 900), (1920, 1080)):
                    with self.subTest(viewport=(width, height)):
                        page = browser.new_page(viewport={"width": width, "height": height})
                        console_errors: list[str] = []
                        page_errors: list[str] = []
                        page.on(
                            "console",
                            lambda message: console_errors.append(message.text)
                            if message.type == "error"
                            else None,
                        )
                        page.on("pageerror", lambda error: page_errors.append(str(error)))
                        page.goto((output / "index.html").resolve().as_uri(), wait_until="load")
                        page.evaluate("() => window.TaoHtmlRuntime.showPage(3)")
                        page.evaluate("() => window.TaoHtmlRuntime.setMode('reading')")
                        overflow = page.evaluate(HTML_QA.OVERFLOW_CHECK)
                        collisions = page.evaluate(HTML_QA.TEXT_COLLISION_CHECK)
                        self.assertEqual(overflow, [])
                        self.assertEqual(collisions["collisions"], [])
                        self.assertEqual(collisions["intra_element_collisions"], [])
                        self.assertEqual(collisions["invalid_opt_outs"], [])
                        self.assertEqual(console_errors, [])
                        self.assertEqual(page_errors, [])
                        page.close()
                browser.close()

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
        from playwright.sync_api import sync_playwright

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            normalized_hashes: set[str] = set()
            semantic_hashes: set[str] = set()
            html_hashes: set[str] = set()
            outputs: list[Path] = []
            shell_runtime = re.search(
                r"<script>(?P<body>\s*const slides = .*?)</script>",
                COMPILER.SHELL_PATH.read_text(encoding="utf-8"),
                re.DOTALL,
            )
            self.assertIsNotNone(shell_runtime)
            for theme_id in THEME_IDS:
                candidate = copy.deepcopy(self.ir)
                candidate["build_binding"]["theme"]["ref"] = theme_id
                output = root / theme_id
                manifest = COMPILER.compile_ir(candidate, root, output)
                outputs.append(output / "index.html")
                rendered = (output / "index.html").read_text(encoding="utf-8")
                normalized_hashes.add(manifest["report_ir"]["normalized_sha256"])
                semantic_hashes.add(manifest["report_ir"]["semantic_graph_sha256"])
                html_hashes.add(manifest["outputs"]["html"]["sha256"])
                self.assertIn(f'data-theme="{theme_id}"', rendered)
                self.assertEqual(manifest["counts"]["output_pages"], 7)
                rendered_runtime = re.search(
                    r"<script>(?P<body>\s*const slides = .*?)</script>",
                    rendered,
                    re.DOTALL,
                )
                self.assertIsNotNone(rendered_runtime)
                self.assertEqual(rendered_runtime.group("body"), shell_runtime.group("body"))
            self.assertEqual(len(normalized_hashes), 4)
            self.assertEqual(len(semantic_hashes), 1)
            self.assertEqual(len(html_hashes), 4)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(args=["--disable-gpu"])
                for output in outputs:
                    page = browser.new_page(viewport={"width": 1600, "height": 900})
                    page.goto(output.resolve().as_uri(), wait_until="load")
                    target_index = page.evaluate(
                        """() => [...document.querySelectorAll('.slide')]
                          .findIndex((slide, index, slides) =>
                            index < slides.length - 1 && slide.querySelector('.fragment'))"""
                    )
                    self.assertGreaterEqual(target_index, 0)
                    page.evaluate(
                        """index => {
                          const runtime = window.TaoHtmlRuntime;
                          if (runtime.getState().mode === 'presentation') runtime.setMode('reading');
                          runtime.showPage(index);
                          runtime.setMode('presentation');
                        }""",
                        target_index,
                    )
                    before = page.evaluate("() => window.TaoHtmlRuntime.getState()")
                    page.keyboard.press("ArrowLeft")
                    self.assertEqual(
                        page.evaluate("() => window.TaoHtmlRuntime.getState()"),
                        before,
                    )
                    page.keyboard.press("ArrowRight")
                    after_step = page.evaluate("() => window.TaoHtmlRuntime.getState()")
                    self.assertEqual(after_step["index"], target_index)
                    self.assertEqual(after_step["stages"][target_index], 1)
                    page.evaluate(
                        """index => {
                          const runtime = window.TaoHtmlRuntime;
                          runtime.setMode('reading');
                          runtime.showPage(index);
                          runtime.setMode('presentation');
                        }""",
                        target_index,
                    )
                    page.keyboard.press("PageDown")
                    after_page = page.evaluate("() => window.TaoHtmlRuntime.getState()")
                    self.assertEqual(after_page["index"], target_index + 1)
                    self.assertEqual(after_page["stages"][target_index], 0)
                    page.close()
                browser.close()

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
                                      const content = slide.querySelector('.ri-content');
                                      const titleRange = document.createRange();
                                      titleRange.selectNodeContents(title);
                                      const titleRects = [...titleRange.getClientRects()]
                                        .filter(rect => rect.width > 0 && rect.height > 0)
                                        .map(rect => ({
                                          top: rect.top,
                                          bottom: rect.bottom,
                                        }));
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
                                        titleContentGap:
                                          contentRect.top - titleRects.at(-1).bottom,
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
                                self.assertGreaterEqual(item["titleContentGap"], 1, item)
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
        from playwright.sync_api import sync_playwright

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
            self.ir["pages"][2]["form"] = "section"
            self.ir["pages"][2]["visual_intent"]["composition_family"] = (
                "section-standard"
            )
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
                ["cover", "data", "section", "content", "content", "data", "content"],
            )
            self.assertEqual(rendered.count(" ri-corporate-page"), 7)
            self.assertEqual(rendered.count(" ri-corporate-page active"), 1)
            self.assertNotIn('class="ri-task"', rendered)
            for page in self.ir["pages"]:
                self.assertNotIn(page["task"], rendered)
            for output_section in output_sections:
                self.assertEqual(output_section.count('class="ri-page-number"'), 0)
            self.assertEqual(rendered.count('id="pageIndicator"'), 1)
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

            screenshots: list[Path] = []
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(args=["--disable-gpu"])
                browser_page = browser.new_page(
                    viewport={"width": 1366, "height": 768}
                )
                browser_page.goto(
                    (output / "index.html").resolve().as_uri(), wait_until="load"
                )
                expected_assets = {
                    0: ["cover-left-composition", "cover-top-rule"],
                    1: ["shared-header", "shared-footer"],
                    2: [
                        "section-left-composition",
                        "section-header",
                        "shared-footer",
                    ],
                    3: ["shared-header", "shared-footer"],
                    4: ["shared-header", "shared-footer"],
                    5: ["shared-header", "shared-footer"],
                    6: ["shared-header", "shared-footer"],
                }
                for page_index, expected in expected_assets.items():
                    browser_page.evaluate(
                        "index => window.TaoHtmlRuntime.showPage(index)", page_index
                    )
                    active_page = browser_page.locator(".slide.active")
                    self.assertEqual(
                        active_page.get_attribute("data-ir-shell-role"),
                        roles[page_index],
                    )
                    self.assertEqual(
                        active_page.get_attribute("data-ir-form"),
                        self.ir["pages"][page_index]["form"],
                    )
                    layer_contract = active_page.evaluate(
                        """page => {
                          const shell = page.querySelector('.pt-corporate-fixed-shell');
                          const editable = page.querySelector('.pt-corporate-editable');
                          const editableBox = editable.getBoundingClientRect();
                          const overlaps = [...shell.querySelectorAll(
                            '.pt-corporate-fixed-region'
                          )].filter(item => {
                            const box = item.getBoundingClientRect();
                            return box.left < editableBox.right &&
                              box.right > editableBox.left &&
                              box.top < editableBox.bottom &&
                              box.bottom > editableBox.top;
                          }).map(item => item.dataset.assetId);
                          return {
                            isolation: getComputedStyle(page).isolation,
                            shellZ: Number(getComputedStyle(shell).zIndex),
                            editableZ: Number(getComputedStyle(editable).zIndex),
                            overlaps,
                          };
                        }"""
                    )
                    self.assertEqual(layer_contract["isolation"], "isolate")
                    self.assertGreater(
                        layer_contract["shellZ"], layer_contract["editableZ"]
                    )
                    self.assertEqual(layer_contract["overlaps"], [])
                    self.assertEqual(
                        browser_page.locator(
                            ".slide.active .ri-page-number"
                        ).count(),
                        0,
                    )
                    self.assertEqual(
                        browser_page.locator("#pageIndicator").inner_text(),
                        f"{page_index + 1:02d} / 07",
                    )
                    self.assertEqual(
                        browser_page.get_by_text(
                            f"{page_index + 1:02d} / 07", exact=True
                        ).count(),
                        1,
                    )
                    assets = browser_page.locator(
                        ".slide.active .pt-corporate-fixed-region"
                    ).evaluate_all(
                        """items => items.map(item => {
                          const box = item.getBoundingClientRect();
                          const slide = item.closest('.slide').getBoundingClientRect();
                          return {
                            id: item.dataset.assetId,
                            loaded: item.complete && item.naturalWidth > 0,
                            inside: box.left >= slide.left - 1 &&
                              box.top >= slide.top - 1 &&
                              box.right <= slide.right + 1 &&
                              box.bottom <= slide.bottom + 1,
                            width: box.width,
                            height: box.height,
                          };
                        })"""
                    )
                    self.assertEqual([asset["id"] for asset in assets], expected)
                    for asset in assets:
                        self.assertTrue(asset["loaded"], asset)
                        self.assertTrue(asset["inside"], asset)
                        self.assertGreater(asset["width"], 0)
                        self.assertGreater(asset["height"], 0)
                    self.assertEqual(
                        browser_page.evaluate(HTML_QA.OVERFLOW_CHECK), []
                    )
                    collisions = browser_page.evaluate(HTML_QA.TEXT_COLLISION_CHECK)
                    self.assertEqual(collisions["collisions"], [])
                    self.assertEqual(collisions["intra_element_collisions"], [])
                    screenshot = root / f"corporate-page-{page_index + 1}-1366x768.png"
                    browser_page.screenshot(path=str(screenshot))
                    screenshots.append(screenshot)
                    with Image.open(screenshot) as captured:
                        painted_page = captured.convert("RGB")
                    for asset_locator in browser_page.locator(
                        ".slide.active .pt-corporate-fixed-region"
                    ).all():
                        assert_fixed_asset_visible(
                            self,
                            asset_locator,
                            painted_page,
                            page_index=page_index,
                        )
                browser.close()
            for screenshot in screenshots:
                with Image.open(screenshot) as image:
                    self.assertEqual(image.size, (1366, 768))
                    self.assertNotEqual(image.getbbox(), None)

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
                    sys.executable,
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
