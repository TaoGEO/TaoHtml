from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill" / "taohtml"
SYSTEMS_ROOT = SKILL_ROOT / "assets" / "visual-systems"
FIXTURE = ROOT / "evals" / "taohtml-quality-v1" / "fixtures" / "visual-systems-content.json"
EVIDENCE_FIXTURE = (
    ROOT / "evals" / "taohtml-quality-v1" / "fixtures" / "visual-systems-evidence.svg"
)
CHECK_ASSETS = SKILL_ROOT / "scripts" / "check_assets.py"
EXPECTED = {
    "black-white-fluorescent-cards": ("黑白荧光卡片", "高反差、模块卡片、大标题，适合路演和强表达"),
    "rigorous-consulting-report": ("严谨咨询报告", "白底、结论式标题、高信息密度、严谨图表"),
    "corporate-annual-report": ("稳重企业年报", "稳重配色、图文平衡、品牌化版面、适度留白"),
    "editorial-collage": ("杂志图文拼贴", "图片切片、错位排版、大字标题和编辑杂志感"),
}


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RENDERER = load_module(
    "taohtml_visual_renderer", SKILL_ROOT / "scripts" / "render_visual_system.py"
)
BUILDER = load_module(
    "taohtml_visual_builder",
    ROOT / "evals" / "taohtml-quality-v1" / "scripts" / "build_visual_system_samples.py",
)


class SlideTextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.section_depth = 0
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "section":
            self.section_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "section" and self.section_depth:
            self.section_depth -= 1

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if self.section_depth and value:
            self.text.append(value)


def slide_text(html_text: str) -> Counter[str]:
    parser = SlideTextCollector()
    parser.feed(html_text)
    return Counter(parser.text)


class VisualSystemAssetTests(unittest.TestCase):
    def test_exactly_four_complete_system_directories_exist(self) -> None:
        actual = {path.name for path in SYSTEMS_ROOT.iterdir() if path.is_dir()}
        self.assertEqual(actual, set(EXPECTED))
        for theme_id, (name, description) in EXPECTED.items():
            theme_dir = SYSTEMS_ROOT / theme_id
            self.assertEqual(
                {path.name for path in theme_dir.iterdir() if path.is_file()},
                {"theme.json", "theme.css", "templates.html", "preview.svg"},
            )
            manifest = json.loads((theme_dir / "theme.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["id"], theme_id)
            self.assertEqual(manifest["display_name"], name)
            self.assertEqual(manifest["description"], description)

    def test_manifests_cover_executable_visual_grammar(self) -> None:
        identity_fields = {
            "composition",
            "hierarchy",
            "image_treatment",
            "module_language",
            "chart_evidence",
            "motion",
        }
        token_fields = {"colors", "font_stacks", "type_scale", "spacing", "borders"}
        component_fields = {"chart", "table", "evidence_card", "image"}
        for theme_id in EXPECTED:
            manifest = json.loads(
                (SYSTEMS_ROOT / theme_id / "theme.json").read_text(encoding="utf-8")
            )
            self.assertEqual(set(manifest["identity"]), identity_fields)
            self.assertEqual(set(manifest["tokens"]), token_fields)
            self.assertEqual(set(manifest["components"]), component_fields)
            self.assertEqual(manifest["canvas"]["aspect_ratio"], "16:9")
            self.assertGreaterEqual(len(manifest["layout_variants"]), 5)
            self.assertTrue(manifest["motion"]["disabled"])
            self.assertTrue(manifest["forbidden"])
            self.assertGreaterEqual(manifest["template_contract"]["minimum_slides"], 5)

    def test_css_templates_and_previews_are_directly_reusable(self) -> None:
        for theme_id, (name, description) in EXPECTED.items():
            theme_dir = SYSTEMS_ROOT / theme_id
            css = (theme_dir / "theme.css").read_text(encoding="utf-8")
            templates = (theme_dir / "templates.html").read_text(encoding="utf-8")
            preview = (theme_dir / "preview.svg").read_text(encoding="utf-8")
            self.assertIn(f'.deck[data-theme="{theme_id}"]', css)
            for token in ("--vs-bg", "--vs-ink"):
                self.assertIn(token, css)
            self.assertEqual(templates.count('<section class="slide'), 5)
            self.assertGreaterEqual(templates.count("data-layout="), 5)
            self.assertIn("fragment", templates)
            self.assertIn("data-step=", templates)
            self.assertIn("<img", templates)
            self.assertIn("<svg", preview)
            self.assertIn(name, preview)
            self.assertIn(description, preview)
            self.assertNotRegex(
                css + templates + preview, r"(?:src|href)=[\"']https?://"
            )

    def test_production_skill_contains_no_evaluation_evidence(self) -> None:
        forbidden = ("固定内容样张", "合成证据记录")
        text_suffixes = {".css", ".html", ".json", ".md", ".py", ".svg", ".yaml", ".yml"}
        for path in SKILL_ROOT.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in text_suffixes:
                continue
            text = path.read_text(encoding="utf-8")
            for marker in forbidden:
                self.assertNotIn(marker, text, msg=f"{marker} leaked into {path}")


class VisualSystemRoutingTests(unittest.TestCase):
    def test_skill_routes_progressively_to_visual_systems(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        router = (SKILL_ROOT / "references" / "visual-systems.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("references/visual-systems.md", skill)
        self.assertIn("load only that system", skill)
        self.assertIn("Load Only The Selected System", router)
        for theme_id, (name, description) in EXPECTED.items():
            self.assertIn(name, router)
            self.assertIn(description, router)
            self.assertIn(f"assets/visual-systems/{theme_id}/preview.svg", router)

    def test_reference_precedence_and_question_budget_are_explicit(self) -> None:
        intake = (SKILL_ROOT / "references" / "intake-workflow.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("one to three representative static", intake)
        self.assertIn("read `static-reference-vi.md`", intake)
        self.assertIn("render one VI board", intake)
        self.assertIn("infer dynamic behavior", intake)
        self.assertIn("recommend 2-3 genuinely suitable built-in systems", intake)
        self.assertIn("exact customer-facing name, one-line description, and bundled preview", intake)
        self.assertIn("Do not ask open-ended aesthetic questions", intake)
        self.assertIn("never expands the six-question hard maximum", intake)
        self.assertIn("choose the lowest-risk fit", intake)

    def test_brief_records_source_selection_and_deviation(self) -> None:
        brief = (SKILL_ROOT / "references" / "design-brief-template.md").read_text(
            encoding="utf-8"
        )
        for field in ("视觉来源", "用户参考", "所选内置主题", "必要偏离说明"):
            self.assertIn(field, brief)
        self.assertIn("do not add a competing built-in-theme requirement", brief)


class VisualSystemRenderingTests(unittest.TestCase):
    def test_fixed_content_renders_four_structurally_distinct_offline_decks(self) -> None:
        content = RENDERER.load_content(FIXTURE)
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs = RENDERER.render_all(content, Path(temp_dir), EVIDENCE_FIXTURE)
            self.assertEqual(len(outputs), 4)
            texts: list[Counter[str]] = []
            layout_signatures: list[tuple[str, ...]] = []
            shell_script = re.search(
                r"<script>(?P<body>.*?)</script>",
                RENDERER.SHELL_PATH.read_text(encoding="utf-8"),
                re.DOTALL,
            )
            self.assertIsNotNone(shell_script)
            for output in outputs:
                html_text = output.read_text(encoding="utf-8")
                self.assertIn("window.TaoHtmlRuntime", html_text)
                self.assertIn("data:image/svg+xml;base64,", html_text)
                self.assertNotRegex(html_text, r"(?:src|href)=[\"']https?://")
                rendered_script = re.search(
                    r"<script>(?P<body>.*?)</script>", html_text, re.DOTALL
                )
                self.assertIsNotNone(rendered_script)
                self.assertEqual(rendered_script.group("body"), shell_script.group("body"))
                texts.append(slide_text(html_text))
                layout_signatures.append(tuple(re.findall(r'data-layout="([^"]+)"', html_text)))
            self.assertTrue(all(text == texts[0] for text in texts[1:]))
            self.assertEqual(len(set(layout_signatures)), 4)
            self.assertTrue(all(len(signature) == 5 for signature in layout_signatures))

    def test_production_renderer_uses_labeled_illustration_without_evidence(self) -> None:
        content = RENDERER.load_content(FIXTURE)
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.html"
            RENDERER.render_theme(
                content,
                "black-white-fluorescent-cards",
                output,
            )
            html_text = output.read_text(encoding="utf-8")
            self.assertIn('data-source-kind="illustrative"', html_text)
            self.assertIn("示意 / 待核实", html_text)
            self.assertIn("示意内容图片（待核实）", html_text)

    def test_verified_source_kind_still_fails_closed_without_image(self) -> None:
        content = RENDERER.load_content(FIXTURE)
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.html"
            with self.assertRaisesRegex(ValueError, "requires --source-image"):
                RENDERER.render_theme(
                    content,
                    "black-white-fluorescent-cards",
                    output,
                    source_kind="verified",
                )
            self.assertFalse(output.exists())

    def test_local_image_without_kind_is_embedded_as_illustrative(self) -> None:
        from PIL import Image

        content = RENDERER.load_content(FIXTURE)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "verified-evidence.png"
            Image.new("RGB", (12, 8), color=(23, 32, 42)).save(source)
            output = root / "report.html"
            RENDERER.render_theme(
                content,
                "black-white-fluorescent-cards",
                output,
                source,
            )
            html_text = output.read_text(encoding="utf-8")
            self.assertIn("data:image/png;base64,", html_text)
            self.assertIn('data-source-kind="illustrative"', html_text)
            self.assertIn("示意内容图片（待核实）", html_text)
            self.assertNotIn('data-source-kind="verified"', html_text)
            self.assertNotIn("来源证据图片（已核实）", html_text)
            self.assertNotIn(str(source), html_text)

    def test_explicit_verified_local_image_passes_strict_offline_check(self) -> None:
        from PIL import Image

        content = RENDERER.load_content(FIXTURE)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "verified-evidence.png"
            Image.new("RGB", (12, 8), color=(23, 32, 42)).save(source)
            output = root / "report.html"
            RENDERER.render_theme(
                content,
                "black-white-fluorescent-cards",
                output,
                source,
                source_kind="verified",
            )
            html_text = output.read_text(encoding="utf-8")
            self.assertIn('data-source-kind="verified"', html_text)
            self.assertIn("来源证据图片（已核实）", html_text)
            check = subprocess.run(
                [sys.executable, str(CHECK_ASSETS), str(output), "--strict-offline"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(check.returncode, 0, msg=check.stdout + check.stderr)
            self.assertIn("ASSET_CHECK_OK", check.stdout)

    def test_explicit_illustrative_local_image_keeps_illustrative_label(self) -> None:
        content = RENDERER.load_content(FIXTURE)
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.html"
            RENDERER.render_theme(
                content,
                "black-white-fluorescent-cards",
                output,
                EVIDENCE_FIXTURE,
                source_kind="illustrative",
            )
            html_text = output.read_text(encoding="utf-8")
            self.assertIn('data-source-kind="illustrative"', html_text)
            self.assertIn("示意内容图片（待核实）", html_text)
            self.assertNotIn("来源证据图片（已核实）", html_text)

    def test_cli_local_image_without_kind_defaults_to_illustrative(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.html"
            run = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts" / "render_visual_system.py"),
                    "--content",
                    str(FIXTURE),
                    "--theme",
                    "black-white-fluorescent-cards",
                    "--source-image",
                    str(EVIDENCE_FIXTURE),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 0, msg=run.stdout + run.stderr)
            html_text = output.read_text(encoding="utf-8")
            self.assertIn('data-source-kind="illustrative"', html_text)
            self.assertNotIn('data-source-kind="verified"', html_text)

    def test_invalid_local_evidence_is_rejected(self) -> None:
        content = RENDERER.load_content(FIXTURE)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            unsupported = root / "evidence.txt"
            unsupported.write_text("not an image", encoding="utf-8")
            corrupt = root / "evidence.png"
            corrupt.write_bytes(b"not a png")
            external_svg = root / "external.svg"
            external_svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><image href="other.png"/></svg>',
                encoding="utf-8",
            )
            missing = root / "missing.svg"
            for source, message in (
                (unsupported, "Unsupported source image type"),
                (corrupt, "not a readable PNG"),
                (external_svg, "non-offline external reference"),
                (missing, "does not exist"),
            ):
                with self.subTest(source=source.name):
                    with self.assertRaisesRegex(ValueError, message):
                        RENDERER.render_theme(
                            content,
                            "black-white-fluorescent-cards",
                            root / f"{source.stem}.html",
                            source,
                        )

    def test_benchmark_builder_outputs_samples_and_offline_overview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            samples, overview = BUILDER.build(Path(temp_dir))
            self.assertEqual(len(samples), 4)
            self.assertTrue(all(path.is_file() for path in samples))
            overview_text = overview.read_text(encoding="utf-8")
            for theme_id, (name, _) in EXPECTED.items():
                self.assertIn(theme_id, overview_text)
                self.assertIn(name, overview_text)
            self.assertNotRegex(overview_text, r"https?://")

    def test_deterministic_benchmark_has_no_model_api_path(self) -> None:
        script = (
            ROOT
            / "evals"
            / "taohtml-quality-v1"
            / "scripts"
            / "build_visual_system_samples.py"
        ).read_text(encoding="utf-8")
        lowered = script.lower()
        for api_marker in ("openai", "anthropic", "gemini", "model api"):
            self.assertNotIn(api_marker, lowered)


if __name__ == "__main__":
    unittest.main()
