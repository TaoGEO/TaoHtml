from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import ModuleType

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill" / "taohtml"
RENDERER_PATH = SKILL_ROOT / "scripts" / "render_reference_vi.py"
CONTRACT_PATH = ROOT / "tests" / "fixtures" / "reference-vi-contract.json"
SOURCE_PATH = ROOT / "tests" / "fixtures" / "reference-vi-source.svg"
CHECK_ASSETS = SKILL_ROOT / "scripts" / "check_assets.py"
BUILT_IN_IDS = {
    "black-white-fluorescent-cards",
    "rigorous-consulting-report",
    "corporate-annual-report",
    "editorial-collage",
}


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RENDERER = load_module("taohtml_reference_vi_renderer", RENDERER_PATH)


class VisibleTextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"style", "script"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"style", "script"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            value = " ".join(data.split())
            if value:
                self.text.append(value)


def visible_text(document: str) -> str:
    parser = VisibleTextCollector()
    parser.feed(document)
    return " ".join(parser.text)


class ReferenceVIContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.contract = RENDERER.validate_contract(self.raw)

    def test_single_static_result_has_no_dynamic_analysis_fields_or_copy(self) -> None:
        source_uri = RENDERER.source_data_uri(SOURCE_PATH)
        rendered = RENDERER.render_html(self.contract, source_uri)
        self.assertNotIn("模块动态重排", json.dumps(self.contract, ensure_ascii=False))
        self.assertNotIn("Use timing and sequence cues", visible_text(rendered))

        with self.subTest("unknown top-level field"):
            invalid = copy.deepcopy(self.raw)
            invalid["motion"] = {"enter": "fade"}
            with self.assertRaisesRegex(ValueError, "extra: motion"):
                RENDERER.validate_contract(invalid)

        with self.subTest("unsupported copy"):
            invalid = copy.deepcopy(self.raw)
            invalid["components"][0]["description"] = "Add animation to the label"
            with self.assertRaisesRegex(ValueError, "unsupported dynamic-analysis wording"):
                RENDERER.validate_contract(invalid)

    def test_dynamic_and_time_sequence_rules_are_rejected_semantically(self) -> None:
        asserted_rules = (
            "模块动态重排",
            "标题沿路径运动",
            "按时序逐步变化",
            "使用时间线安排内容",
            "卡片采用缓动曲线",
            "关键帧控制强调色",
            "连续状态逐页展开",
            "Use timing and sequence cues",
            "Reveal labels sequentially",
            "Apply easing to the panel",
            "Use a keyframe for the heading",
            "Morph between the two cards",
            "不使用渐变，模块动态重排",
            "Do not use gradients, use timing cues",
        )
        for rule in asserted_rules:
            with self.subTest(rule=rule):
                invalid = copy.deepcopy(self.raw)
                invalid["components"][0]["description"] = rule
                with self.assertRaisesRegex(
                    ValueError, "unsupported dynamic-analysis wording"
                ):
                    RENDERER.validate_contract(invalid)

    def test_static_and_negated_dynamic_boundary_statements_remain_valid(self) -> None:
        boundary_statements = (
            "静态构图保持清晰",
            "无动态规则，仅记录单帧可见事实",
            "不从单张静态图推断时间线",
            "参考未展示连续状态，保持未知",
            "No animation or timing can be inferred from a still image",
            "Motion is not shown in the reference",
            "禁止把单帧观察写成动态规则",
            "No animation, motion, or timing rules are defined",
        )
        for statement in boundary_statements:
            with self.subTest(statement=statement):
                valid = copy.deepcopy(self.raw)
                valid["components"][0]["description"] = statement
                RENDERER.validate_contract(valid)

    def test_palette_allows_supported_colors_without_fabricating_a_third(self) -> None:
        for count in (1, 2):
            with self.subTest(count=count):
                reduced = copy.deepcopy(self.raw)
                reduced["palette"] = reduced["palette"][:count]
                normalized = RENDERER.validate_contract(reduced)
                self.assertEqual(len(normalized["palette"]), count)
                rendered = RENDERER.render_html(
                    normalized, RENDERER.source_data_uri(SOURCE_PATH)
                )
                for color in reduced["palette"]:
                    self.assertIn(color["value"].upper(), visible_text(rendered))

    def test_unknown_palette_uses_a_non_color_placeholder(self) -> None:
        unknown = copy.deepcopy(self.raw)
        unknown["palette"] = [
            {
                "name": "其他颜色",
                "value": "unknown",
                "role": "参考证据不足",
                "status": "unknown",
                "basis": "单帧中没有可可靠采样的其他色块",
            }
        ]
        normalized = RENDERER.validate_contract(unknown)
        rendered = RENDERER.render_html(
            normalized, RENDERER.source_data_uri(SOURCE_PATH)
        )
        self.assertIn("swatch-color-unknown", rendered)
        self.assertIn("未识别色值", visible_text(rendered))
        self.assertNotIn('style="background:unknown"', rendered)

        fake_unknown = copy.deepcopy(unknown)
        fake_unknown["palette"][0]["value"] = "#FF00FF"
        with self.assertRaisesRegex(ValueError, "would fabricate a color fact"):
            RENDERER.validate_contract(fake_unknown)

        fake_observed = copy.deepcopy(unknown)
        fake_observed["palette"][0]["status"] = "observed"
        with self.assertRaisesRegex(ValueError, "when status is observed or extension"):
            RENDERER.validate_contract(fake_observed)

    def test_observed_extension_unknown_boundaries_are_explicit_and_rendered(self) -> None:
        statuses = {
            item["status"]
            for section in RENDERER.SECTION_LIMITS
            for item in self.contract[section]
        }
        self.assertEqual(statuses, {"observed", "extension", "unknown"})
        rendered = RENDERER.render_html(
            self.contract, RENDERER.source_data_uri(SOURCE_PATH)
        )
        for status, label in RENDERER.STATUS_LABELS.items():
            self.assertIn(f"status-{status}", rendered)
            self.assertIn(label, visible_text(rendered))

    def test_missing_category_cannot_be_silently_promoted_to_observed(self) -> None:
        imagery = {item["label"]: item for item in self.contract["imagery"]}
        self.assertEqual(imagery["人物摄影"]["status"], "unknown")
        self.assertIn("没有人物照片", imagery["人物摄影"]["basis"])
        rendered = RENDERER.render_html(
            self.contract, RENDERER.source_data_uri(SOURCE_PATH)
        )
        self.assertRegex(
            rendered,
            r"人物摄影</strong><span class=\"status status-unknown\">参考中无法判断</span>",
        )

        invalid = copy.deepcopy(self.raw)
        del invalid["imagery"][1]["status"]
        with self.assertRaisesRegex(ValueError, "keys mismatch"):
            RENDERER.validate_contract(invalid)

        no_chart = copy.deepcopy(self.raw)
        no_chart["evidence_language"] = [
            {
                "label": "图表语言",
                "description": "参考中没有图表，无法判断",
                "sample": "none",
                "status": "unknown",
                "basis": "整张参考没有数值图表",
            }
        ]
        normalized = RENDERER.validate_contract(no_chart)
        no_chart_html = RENDERER.render_html(
            normalized, RENDERER.source_data_uri(SOURCE_PATH)
        )
        self.assertIn("evidence-empty", no_chart_html)
        self.assertIn("参考中未出现", visible_text(no_chart_html))
        self.assertNotIn('<div class="evidence-sample evidence-bar"', no_chart_html)

        fake_chart = copy.deepcopy(no_chart)
        fake_chart["evidence_language"][0]["sample"] = "bar"
        with self.assertRaisesRegex(ValueError, "must use sample 'none'"):
            RENDERER.validate_contract(fake_chart)

    def test_contract_requires_all_board_sections_and_page_examples(self) -> None:
        self.assertEqual(
            {item["kind"] for item in self.contract["mini_pages"]},
            {"cover", "content", "data"},
        )
        for section in RENDERER.SECTION_LIMITS:
            self.assertTrue(self.contract[section], section)

        invalid = copy.deepcopy(self.raw)
        invalid["mini_pages"] = invalid["mini_pages"][:2]
        with self.assertRaisesRegex(ValueError, "mini_pages must contain between 3 and 3"):
            RENDERER.validate_contract(invalid)

    def test_executable_layout_grammar_is_exact_typed_and_not_description_parsing(self) -> None:
        self.assertEqual(
            set(self.contract["executable_layout"]),
            set(RENDERER.EXECUTABLE_LAYOUT_OPTIONS),
        )
        self.assertEqual(self.contract["executable_layout"]["cover_structure"]["value"], "split")
        self.assertEqual(self.contract["executable_layout"]["content_columns"]["value"], "3")

        invalid = copy.deepcopy(self.raw)
        invalid["executable_layout"]["content_structure"]["value"] = "free prose"
        with self.assertRaisesRegex(ValueError, "must be one of"):
            RENDERER.validate_contract(invalid)

        unknown = copy.deepcopy(self.raw)
        unknown["executable_layout"]["visual_focus"] = {
            "value": "unknown",
            "status": "unknown",
            "basis": "参考证据不足，视觉焦点保持未知",
        }
        normalized = RENDERER.validate_contract(unknown)
        self.assertEqual(normalized["executable_layout"]["visual_focus"]["value"], "unknown")

        fabricated = copy.deepcopy(unknown)
        fabricated["executable_layout"]["visual_focus"]["value"] = "image-first"
        with self.assertRaisesRegex(ValueError, "must be 'unknown'"):
            RENDERER.validate_contract(fabricated)

    def test_reference_workflow_embeds_a_valid_contract_example(self) -> None:
        workflow = (SKILL_ROOT / "references" / "static-reference-vi.md").read_text(
            encoding="utf-8"
        )
        match = re.search(r"```json\n(?P<body>.*?)\n```", workflow, re.DOTALL)
        self.assertIsNotNone(match)
        example = json.loads(match.group("body"))
        normalized = RENDERER.validate_contract(example)
        self.assertEqual(normalized["schema_version"], "1.1")


class ReferenceVIRenderingTests(unittest.TestCase):
    def test_output_png_exists_is_high_resolution_and_html_is_offline(self) -> None:
        contract = RENDERER.load_contract(CONTRACT_PATH)
        with tempfile.TemporaryDirectory() as temp_dir:
            output_base = Path(temp_dir) / "reference-vi-board"
            html_path, png_path = RENDERER.render_board(
                contract, SOURCE_PATH, output_base
            )
            self.assertTrue(html_path.is_file())
            self.assertTrue(png_path.is_file())
            with Image.open(png_path) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (3200, 2400))

            document = html_path.read_text(encoding="utf-8")
            text = visible_text(document)
            for expected in (
                "VI 设计标准图",
                "#B94B3F",
                "字体层级",
                "卡片 · 面板 · 标签 · 边框",
                "可执行布局语法",
                "source-chart-split",
                "代表性封面",
                "代表性内容页",
                "代表性数据页",
            ):
                self.assertIn(expected, text)
            self.assertIn("data:image/svg+xml;base64,", document)
            self.assertNotRegex(document, r"(?:src|href)=[\"']https?://")

            check = subprocess.run(
                [sys.executable, str(CHECK_ASSETS), str(html_path), "--strict-offline"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(check.returncode, 0, msg=check.stdout + check.stderr)
            self.assertIn("ASSET_CHECK_OK", check.stdout)


class ReferenceVIWorkflowTests(unittest.TestCase):
    def test_existing_four_built_in_theme_route_is_preserved(self) -> None:
        systems_root = SKILL_ROOT / "assets" / "visual-systems"
        self.assertEqual(
            {path.name for path in systems_root.iterdir() if path.is_dir()}, BUILT_IN_IDS
        )
        renderer = load_module(
            "taohtml_builtin_renderer", SKILL_ROOT / "scripts" / "render_visual_system.py"
        )
        self.assertEqual(set(renderer.THEME_IDS), BUILT_IN_IDS)
        router = (SKILL_ROOT / "references" / "visual-systems.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("When no clear reference exists", router)
        self.assertIn("four built-in systems", router)

    def test_vi_confirmation_is_required_before_brief_theme_or_production(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        intake = (SKILL_ROOT / "references" / "intake-workflow.md").read_text(
            encoding="utf-8"
        )
        workflow = (SKILL_ROOT / "references" / "static-reference-vi.md").read_text(
            encoding="utf-8"
        )
        brief = (SKILL_ROOT / "references" / "design-brief-template.md").read_text(
            encoding="utf-8"
        )
        for text in (skill, intake, workflow):
            self.assertIn("确认 VI", text)
        self.assertIn("start formal report production before this confirmation", skill)
        self.assertIn("do not begin project-theme generation or report production", intake)
        self.assertIn("VI confirmation is not Report Design Brief confirmation", workflow)
        self.assertIn("VI 规范图", brief)

    def test_clear_non_single_image_reference_stops_at_unsupported_boundary(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        intake = (SKILL_ROOT / "references" / "intake-workflow.md").read_text(
            encoding="utf-8"
        )
        workflow = (SKILL_ROOT / "references" / "static-reference-vi.md").read_text(
            encoding="utf-8"
        )
        router = (SKILL_ROOT / "references" / "visual-systems.md").read_text(
            encoding="utf-8"
        )
        for text in (skill, intake, workflow, router):
            self.assertIn("one representative static screenshot", text)
        self.assertIn("not “no clear reference.”", workflow)
        self.assertIn("Only when no clear reference exists", skill)
        self.assertIn("do not enter this router", router)
        self.assertIn("Never infer movement", router)

    def test_session_capability_gate_avoids_a_model_matrix(self) -> None:
        workflow = (SKILL_ROOT / "references" / "static-reference-vi.md").read_text(
            encoding="utf-8"
        )
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("On first use in WorkBuddy", workflow)
        self.assertIn("Auto is recommended", workflow)
        self.assertIn("continue with the current session model", workflow)
        self.assertIn("当前会话无法可靠读取参考图", workflow)
        self.assertIn("manually change the model at the platform/session entry", workflow)
        self.assertIn("four built-in visual systems", workflow)
        self.assertNotIn("WorkBuddy", skill)
        self.assertFalse((ROOT / "docs" / "model-capability-matrix.md").exists())
        for volatile_name in ("GPT-", "Sonnet", "Opus", "Gemini"):
            self.assertNotIn(volatile_name, workflow)


if __name__ == "__main__":
    unittest.main()
