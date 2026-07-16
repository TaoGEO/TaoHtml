from __future__ import annotations

import copy
import base64
import hashlib
import io
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
LAYOUT_GRAMMAR_PATH = SKILL_ROOT / "scripts" / "project_theme_layout.py"
CONTRACT_PATH = ROOT / "tests" / "fixtures" / "reference-vi-contract.json"
SOURCE_PATH = ROOT / "tests" / "fixtures" / "reference-vi-source.svg"
CORPORATE_CONTRACT_PATH = ROOT / "tests" / "fixtures" / "corporate-template-vi-contract.json"
CORPORATE_SOURCE_PATH = ROOT / "tests" / "fixtures" / "corporate-template-reference.png"
FAMILY_CONTRACT_PATH = ROOT / "tests" / "fixtures" / "corporate-family-vi-contract.json"
FAMILY_SOURCE_PATHS = [
    ROOT / "tests" / "fixtures" / f"corporate-family-{role}.png"
    for role in ("cover", "toc", "section")
]
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
LAYOUT_GRAMMAR = load_module("taohtml_project_theme_layout", LAYOUT_GRAMMAR_PATH)


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

    def layout_contract(self, **values: str) -> dict[str, object]:
        contract = copy.deepcopy(self.raw)
        for field, value in values.items():
            contract["executable_layout"][field] = {
                "value": value,
                "status": "unknown" if value == "unknown" else "extension",
                "basis": f"参数化布局合同：{field}={value}",
            }
        return contract

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

    def test_executable_layout_compatibility_matrices_accept_every_defined_combination(self) -> None:
        cover_cases = (
            {"cover_structure": "split", "cover_split": "7:5", "image_placement": "left"},
            {"cover_structure": "split", "cover_split": "5:7", "image_placement": "right"},
            {"cover_structure": "split", "cover_split": "1:1", "image_placement": "right"},
            {
                "cover_structure": "single-column",
                "cover_split": "none",
                "image_placement": "top",
                "data_structure": "chart-focus",
                "data_columns": "1",
            },
            {
                "cover_structure": "single-column",
                "cover_split": "none",
                "image_placement": "bottom",
                "data_structure": "table-focus",
                "data_columns": "1",
            },
            {
                "cover_structure": "single-column",
                "cover_split": "none",
                "image_placement": "background",
                "image_fit": "cover",
                "data_structure": "metrics-grid",
                "data_columns": "3",
            },
        )
        content_cases = (
            ("card-grid", "1"),
            ("card-grid", "2"),
            ("card-grid", "3"),
            ("stack", "1"),
            ("single-focus", "1"),
        )
        data_cases = (
            ("source-chart-split", "2"),
            ("chart-focus", "1"),
            ("table-focus", "1"),
            ("metrics-grid", "1"),
            ("metrics-grid", "2"),
            ("metrics-grid", "3"),
        )

        for values in cover_cases:
            with self.subTest(cover=values):
                RENDERER.validate_contract(self.layout_contract(**values))
        for structure, columns in content_cases:
            with self.subTest(content=(structure, columns)):
                RENDERER.validate_contract(
                    self.layout_contract(
                        content_structure=structure, content_columns=columns
                    )
                )
        for structure, columns in data_cases:
            with self.subTest(data=(structure, columns)):
                RENDERER.validate_contract(
                    self.layout_contract(
                        data_structure=structure, data_columns=columns
                    )
                )

        self.assertEqual(
            set(LAYOUT_GRAMMAR.COVER_SPLIT_BY_STRUCTURE),
            RENDERER.EXECUTABLE_LAYOUT_OPTIONS["cover_structure"] - {"unknown"},
        )
        self.assertEqual(
            set().union(*LAYOUT_GRAMMAR.COVER_SPLIT_BY_STRUCTURE.values()),
            RENDERER.EXECUTABLE_LAYOUT_OPTIONS["cover_split"] - {"unknown"},
        )
        self.assertEqual(
            set().union(*LAYOUT_GRAMMAR.COVER_PLACEMENT_BY_STRUCTURE.values()),
            RENDERER.EXECUTABLE_LAYOUT_OPTIONS["image_placement"] - {"unknown"},
        )
        self.assertEqual(
            set(LAYOUT_GRAMMAR.CONTENT_COLUMNS_BY_STRUCTURE),
            RENDERER.EXECUTABLE_LAYOUT_OPTIONS["content_structure"] - {"unknown"},
        )
        self.assertEqual(
            set().union(*LAYOUT_GRAMMAR.CONTENT_COLUMNS_BY_STRUCTURE.values()),
            RENDERER.EXECUTABLE_LAYOUT_OPTIONS["content_columns"] - {"unknown"},
        )
        self.assertEqual(
            set(LAYOUT_GRAMMAR.DATA_COLUMNS_BY_STRUCTURE),
            RENDERER.EXECUTABLE_LAYOUT_OPTIONS["data_structure"] - {"unknown"},
        )
        self.assertEqual(
            set().union(*LAYOUT_GRAMMAR.DATA_COLUMNS_BY_STRUCTURE.values()),
            RENDERER.EXECUTABLE_LAYOUT_OPTIONS["data_columns"] - {"unknown"},
        )

    def test_executable_layout_compatibility_matrices_reject_undefined_programs(self) -> None:
        invalid_cases = (
            (
                {"cover_structure": "split", "cover_split": "7:5", "image_placement": "top"},
                "cover_structure=split is incompatible with image_placement=top",
            ),
            (
                {"cover_structure": "single-column", "cover_split": "none", "image_placement": "left"},
                "cover_structure=single-column is incompatible with image_placement=left",
            ),
            (
                {"cover_structure": "split", "cover_split": "none"},
                "cover_structure=split is incompatible with cover_split=none",
            ),
            (
                {
                    "cover_structure": "single-column",
                    "cover_split": "none",
                    "image_placement": "background",
                    "image_fit": "contain",
                    "data_structure": "chart-focus",
                    "data_columns": "1",
                },
                "image_placement=background requires image_fit=cover",
            ),
            (
                {"content_structure": "stack", "content_columns": "2"},
                "content_structure=stack is incompatible with content_columns=2",
            ),
            (
                {"content_structure": "single-focus", "content_columns": "3"},
                "content_structure=single-focus is incompatible with content_columns=3",
            ),
            (
                {"data_structure": "chart-focus", "data_columns": "3"},
                "data_structure=chart-focus is incompatible with data_columns=3",
            ),
            (
                {"data_structure": "source-chart-split", "data_columns": "1"},
                "data_structure=source-chart-split is incompatible with data_columns=1",
            ),
            (
                {
                    "cover_structure": "single-column",
                    "cover_split": "none",
                    "image_placement": "top",
                    "data_structure": "source-chart-split",
                    "data_columns": "2",
                },
                "data_structure=source-chart-split is incompatible with image_placement=top",
            ),
        )
        for values, message in invalid_cases:
            with self.subTest(values=values):
                with self.assertRaisesRegex(ValueError, re.escape(message)):
                    RENDERER.validate_contract(self.layout_contract(**values))

        for field, removed in (
            ("image_placement", "inline"),
            ("visual_focus", "headline-only"),
            ("visual_focus", "data-first"),
        ):
            with self.subTest(removed=(field, removed)):
                with self.assertRaisesRegex(ValueError, "must be one of"):
                    RENDERER.validate_contract(self.layout_contract(**{field: removed}))

    def test_reference_workflow_embeds_a_valid_contract_example(self) -> None:
        workflow = (SKILL_ROOT / "references" / "static-reference-vi.md").read_text(
            encoding="utf-8"
        )
        match = re.search(r"```json\n(?P<body>.*?)\n```", workflow, re.DOTALL)
        self.assertIsNotNone(match)
        example = json.loads(match.group("body"))
        normalized = RENDERER.validate_contract(example)
        self.assertEqual(normalized["schema_version"], "1.1")


class CorporateFidelityVIContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = json.loads(CORPORATE_CONTRACT_PATH.read_text(encoding="utf-8"))
        self.contract = RENDERER.validate_contract(self.raw)

    def test_v12_extends_the_same_contract_and_legacy_reconstruct_stays_compatible(self) -> None:
        self.assertEqual(self.contract["schema_version"], "1.2")
        self.assertEqual(self.contract["reference_mode"], "corporate_fidelity")
        legacy = RENDERER.load_contract(CONTRACT_PATH)
        self.assertEqual(legacy["schema_version"], "1.1")
        self.assertNotIn("reference_mode", legacy)
        reconstruct = copy.deepcopy(self.raw)
        reconstruct["reference_mode"] = "reconstruct"
        for field in ("locked_regions", "editable_regions", "extension_pages", "limitations"):
            reconstruct[field] = []
        normalized = RENDERER.validate_contract(reconstruct)
        self.assertEqual(normalized["reference_mode"], "reconstruct")
        self.assertEqual(normalized["locked_regions"], [])

    def test_normalized_bbox_and_locked_editable_conflicts_fail_closed(self) -> None:
        outside = copy.deepcopy(self.raw)
        outside["locked_regions"][0]["bbox"] = [0.95, 0.04, 0.12, 0.06]
        with self.assertRaisesRegex(ValueError, "normalized coordinates 0..1"):
            RENDERER.validate_contract(outside)

        overlap = copy.deepcopy(self.raw)
        overlap["editable_regions"][0]["bbox"] = [0.08, 0.04, 0.84, 0.82]
        with self.assertRaisesRegex(ValueError, "overlaps editable_regions"):
            RENDERER.validate_contract(overlap)

    def test_locked_logo_is_observed_crop_only_and_extensions_cannot_masquerade_as_observed(self) -> None:
        logo = self.contract["locked_regions"][0]
        self.assertEqual(
            {key: logo[key] for key in ("type", "status", "extraction")},
            {"type": "logo", "status": "observed", "extraction": "crop"},
        )
        redraw = copy.deepcopy(self.raw)
        redraw["locked_regions"][0]["extraction"] = "redraw"
        with self.assertRaisesRegex(ValueError, "never model-redrawn"):
            RENDERER.validate_contract(redraw)

        fake_observed = copy.deepcopy(self.raw)
        fake_observed["extension_pages"][0]["status"] = "observed"
        with self.assertRaisesRegex(ValueError, "must be extension"):
            RENDERER.validate_contract(fake_observed)

    def test_source_hash_dimensions_resolution_and_raster_boundary_are_enforced(self) -> None:
        binding = RENDERER.validate_source_binding(self.contract, CORPORATE_SOURCE_PATH)
        self.assertEqual(binding, self.contract["source_image"])

        wrong_hash = copy.deepcopy(self.raw)
        wrong_hash["source_image"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "sha256 or dimensions do not match"):
            RENDERER.validate_source_binding(
                RENDERER.validate_contract(wrong_hash), CORPORATE_SOURCE_PATH
            )

        with self.assertRaisesRegex(ValueError, "PNG, JPEG, or WebP"):
            RENDERER.validate_source_binding(self.contract, SOURCE_PATH)

        with tempfile.TemporaryDirectory() as temp_dir:
            low_path = Path(temp_dir) / "low.png"
            Image.new("RGB", (800, 450), "white").save(low_path)
            low = copy.deepcopy(self.raw)
            low["source_image"] = {
                "sha256": hashlib.sha256(low_path.read_bytes()).hexdigest(),
                "width": 800,
                "height": 450,
            }
            with self.assertRaisesRegex(ValueError, "too low for reliable"):
                RENDERER.validate_source_binding(
                    RENDERER.validate_contract(low), low_path
                )

    def test_locked_regions_are_exact_deterministic_crops_with_hashes(self) -> None:
        first = RENDERER.extract_locked_regions(self.contract, CORPORATE_SOURCE_PATH)
        second = RENDERER.extract_locked_regions(self.contract, CORPORATE_SOURCE_PATH)
        self.assertEqual(first, second)
        self.assertEqual(
            {item["id"]: item["pixel_bbox"] for item in first},
            {
                "company-logo": [64, 36, 256, 90],
                "page-header": [288, 36, 1536, 90],
                "left-brand-bar": [64, 126, 88, 774],
                "page-footer": [64, 819, 1536, 855],
            },
        )
        with Image.open(CORPORATE_SOURCE_PATH) as source:
            source_rgba = source.convert("RGBA")
            for item in first:
                encoded = item["data_uri"].split(",", 1)[1]
                payload = base64.b64decode(encoded)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), item["sha256"])
                with Image.open(io.BytesIO(payload)) as crop:
                    expected = source_rgba.crop(tuple(item["pixel_bbox"]))
                    self.assertEqual(crop.size, expected.size)
                    self.assertEqual(crop.tobytes(), expected.tobytes())

    def test_corporate_board_shows_overlay_crops_safe_area_extensions_and_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            html_path, png_path = RENDERER.render_board(
                self.contract,
                CORPORATE_SOURCE_PATH,
                Path(temp_dir) / "corporate-reference-vi",
            )
            document = html_path.read_text(encoding="utf-8")
            text = visible_text(document)
            self.assertTrue(png_path.is_file())
            self.assertEqual(document.count('class="crop-preview"'), 4)
            self.assertEqual(document.count('data-locked-region="'), 4)
            self.assertIn('data-editable-region="safe-content"', document)
            for marker in ("固定企业元素清单", "未知项 / 限制", "企业框架封面", "报告适配建议"):
                self.assertIn(marker, text)


class CorporateTemplateFamilyVIContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = json.loads(FAMILY_CONTRACT_PATH.read_text(encoding="utf-8"))
        self.contract = RENDERER.validate_contract(self.raw)

    def test_family_contract_binds_three_observed_roles_and_two_extensions(self) -> None:
        self.assertEqual(self.contract["schema_version"], "1.3")
        self.assertEqual(
            [page["role"] for page in self.contract["reference_pages"]],
            ["cover", "toc", "section"],
        )
        self.assertEqual(
            [shell["role"] for shell in self.contract["shell_variants"]],
            ["cover", "toc", "section", "content", "data"],
        )
        self.assertEqual(
            {item["role"] for item in self.contract["extension_pages"]},
            {"content", "data"},
        )
        drift = copy.deepcopy(self.raw)
        drift["reference_pages"][1]["role"] = "cover"
        with self.assertRaisesRegex(ValueError, "unique role"):
            RENDERER.validate_contract(drift)

    def test_single_image_family_remains_valid_with_four_explicit_extensions(self) -> None:
        single = copy.deepcopy(self.raw)
        single["reference_pages"] = single["reference_pages"][:1]
        single["shared_assets"] = single["shared_assets"][:2]
        for shell in single["shell_variants"][1:]:
            role = shell["role"]
            shell["status"] = "extension"
            shell["reference_page_id"] = None
            shell["locked_regions"] = [
                {
                    "id": f"{role}-rule",
                    "type": "brand_bar",
                    "asset_id": "cover-top-rule",
                    "bbox": [0.0, 0.0, 1.0, 0.03],
                    "status": "extension",
                    "basis": "单图输入中复用已观察的封面品牌线",
                }
            ]
            shell["editable_region"]["bbox"] = [0.08, 0.12, 0.84, 0.72]
        single["extension_pages"] = [
            {
                "role": role,
                "status": "extension",
                "basis": "单张封面截图未展示此页面角色",
            }
            for role in ("toc", "section", "content", "data")
        ]
        normalized = RENDERER.validate_contract(single)
        bindings = RENDERER.validate_source_bindings(
            normalized, FAMILY_SOURCE_PATHS[:1]
        )
        self.assertEqual([page["role"] for page in normalized["reference_pages"]], ["cover"])
        self.assertEqual(
            {item["role"] for item in normalized["extension_pages"]},
            {"toc", "section", "content", "data"},
        )
        self.assertEqual(bindings[0]["canvas_size"], [1600, 900])

    def test_canvas_crop_is_strict_16_by_9_and_multi_frame_rasters_fail(self) -> None:
        bindings = RENDERER.validate_source_bindings(
            self.contract, FAMILY_SOURCE_PATHS
        )
        self.assertEqual([item["canvas_size"] for item in bindings], [[1600, 900]] * 3)

        bad_ratio = copy.deepcopy(self.raw)
        bad_ratio["reference_pages"][0]["canvas_bbox"] = [0, 0, 1, 1]
        with self.assertRaisesRegex(ValueError, "must be 16:9 within"):
            RENDERER.validate_source_bindings(
                RENDERER.validate_contract(bad_ratio), FAMILY_SOURCE_PATHS
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            animated = Path(temp_dir) / "animated.webp"
            frames = [Image.new("RGB", (1200, 675), color) for color in ("red", "blue")]
            frames[0].save(
                animated,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=100,
                loop=0,
            )
            with self.assertRaisesRegex(ValueError, "one static raster frame"):
                RENDERER.source_image_binding(animated)

    def test_assets_crop_from_canvas_not_screenshot_border(self) -> None:
        first = RENDERER.extract_corporate_assets(
            self.contract, FAMILY_SOURCE_PATHS
        )
        second = RENDERER.extract_corporate_assets(
            self.contract, FAMILY_SOURCE_PATHS
        )
        self.assertEqual(first, second)
        by_id = {item["id"]: item for item in first}
        self.assertEqual(by_id["cover-left-composition"]["canvas_pixel_bbox"], [6, 6, 1606, 906])
        self.assertEqual(by_id["cover-left-composition"]["source_pixel_bbox"], [6, 6, 582, 906])
        for item in first:
            payload = base64.b64decode(item["data_uri"].split(",", 1)[1])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), item["sha256"])

    def test_unified_board_shows_sources_observed_shells_extensions_and_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            html_path, png_path = RENDERER.render_board(
                self.contract,
                FAMILY_SOURCE_PATHS,
                Path(temp_dir) / "corporate-family-vi",
            )
            document = html_path.read_text(encoding="utf-8")
            self.assertTrue(png_path.is_file())
            self.assertEqual(document.count('class="reference-page-card"'), 3)
            self.assertEqual(document.count('class="crop-preview"'), 6)
            self.assertEqual(document.count('class="mini-page-card'), 5)
            for marker in ("source-cover", "source-toc", "source-section", "content", "data", "未知项 / 限制"):
                self.assertIn(marker, visible_text(document))


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

    def test_corporate_mode_uses_shared_vi_gate_and_screenshot_visible_fidelity(self) -> None:
        reference = (SKILL_ROOT / "references" / "static-reference-vi.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "One-Time Reference Mode Routing",
            "`reconstruct`",
            "`corporate_fidelity`",
            "screenshot-visible fidelity only",
            "Never model-redraw a Logo",
            "locked-region and editable-region overlays",
            "all five corporate-frame miniatures",
            "does not recover an original PPT master",
        ):
            self.assertIn(marker, reference)
        self.assertIn("Both modes use the same", reference)
        self.assertIn("artifact-bound confirmation gate", reference)

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
            self.assertIn("current", text)
            self.assertIn("confirmation", text)
        self.assertNotIn("exact authorization phrase", intake)
        self.assertNotIn("exact “确认 VI” gate", workflow)
        self.assertIn("start formal report production before this confirmation", skill)
        self.assertIn("begin project-theme generation/report production before confirmation", intake)
        self.assertIn("VI confirmation is not Report Design Brief confirmation", workflow)
        self.assertIn("VI 规范图", brief)

    def test_reference_input_counts_route_by_mode_and_keep_unsupported_inputs_out(self) -> None:
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
            self.assertIn("one to three", text)
            self.assertIn("multiple", text)
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
