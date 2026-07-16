from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill" / "taohtml"
SCRIPTS_ROOT = SKILL_ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
HANDOFF_FIXTURE = FIXTURES / "reference-theme-handoff.json"
VI_FIXTURE = FIXTURES / "reference-vi-contract.json"
REFERENCE_FIXTURE = FIXTURES / "reference-vi-source.svg"
CENTERED_HANDOFF_FIXTURE = FIXTURES / "reference-theme-centered-handoff.json"
CENTERED_VI_FIXTURE = FIXTURES / "reference-vi-centered-contract.json"
CENTERED_REFERENCE_FIXTURE = FIXTURES / "reference-vi-centered-source.svg"
CONTENT_FIXTURE = (
    ROOT / "evals" / "taohtml-quality-v1" / "fixtures" / "visual-systems-content.json"
)
ILLUSTRATION_FIXTURE = (
    ROOT / "evals" / "taohtml-quality-v1" / "fixtures" / "visual-systems-evidence.svg"
)
CHECK_ASSETS = SCRIPTS_ROOT / "check_assets.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER = load_module("taohtml_project_theme_compiler", SCRIPTS_ROOT / "compile_project_theme.py")
RENDERER = load_module("taohtml_project_theme_renderer", SCRIPTS_ROOT / "render_visual_system.py")
THEME_RUNTIME = load_module("taohtml_theme_runtime", SCRIPTS_ROOT / "theme_runtime.py")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_handoff(root: Path) -> tuple[Path, dict[str, object]]:
    for source in (VI_FIXTURE, REFERENCE_FIXTURE):
        shutil.copy2(source, root / source.name)
    raw = json.loads(HANDOFF_FIXTURE.read_text(encoding="utf-8"))
    handoff = root / "handoff.json"
    handoff.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return handoff, raw


def write_handoff(path: Path, raw: dict[str, object]) -> None:
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


class ProjectThemeHandoffTests(unittest.TestCase):
    def test_fixture_records_exact_confirmation_inputs_mode_and_corrections(self) -> None:
        request, contract, vi_path, reference_path = COMPILER.load_handoff(HANDOFF_FIXTURE)
        self.assertEqual(request["confirmation"]["phrase"], "确认 VI")
        self.assertEqual(request["target_mode"], "presentation")
        self.assertTrue(request["customer_corrections"])
        self.assertEqual(request["confirmation"]["vi_contract_sha256"], sha256(vi_path))
        self.assertEqual(
            request["confirmation"]["reference_image_sha256"], sha256(reference_path)
        )
        self.assertEqual(contract["schema_version"], "1.1")

    def test_unconfirmed_vi_fails_closed_before_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            handoff, raw = stage_handoff(root)
            raw["confirmation"]["status"] = "pending"
            raw["confirmation"]["phrase"] = "继续"
            write_handoff(handoff, raw)
            output = root / "theme"
            with self.assertRaisesRegex(ValueError, "VI is not confirmed"):
                COMPILER.compile_theme(handoff, output)
            self.assertFalse(output.exists())

    def test_missing_invalid_and_schema_drift_fail_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            handoff, raw = stage_handoff(root)
            cases: list[tuple[str, dict[str, object], str]] = []

            missing = copy.deepcopy(raw)
            missing["inputs"]["reference_image"] = "missing.svg"
            cases.append(("missing", missing, "does not exist"))

            traversal = copy.deepcopy(raw)
            traversal["inputs"]["vi_contract"] = "../outside.json"
            cases.append(("traversal", traversal, "safe path relative"))

            wrong_hash = copy.deepcopy(raw)
            wrong_hash["confirmation"]["vi_contract_sha256"] = "0" * 64
            cases.append(("hash", wrong_hash, "hash does not match"))

            extra = copy.deepcopy(raw)
            extra["unexpected"] = True
            cases.append(("schema", extra, "keys mismatch"))

            for label, case, message in cases:
                with self.subTest(label=label):
                    write_handoff(handoff, case)
                    output = root / f"theme-{label}"
                    with self.assertRaisesRegex(ValueError, message):
                        COMPILER.compile_theme(handoff, output)
                    self.assertFalse(output.exists())

    def test_invalid_vi_contract_and_reference_image_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            handoff, raw = stage_handoff(root)
            vi_path = root / VI_FIXTURE.name
            vi_raw = json.loads(vi_path.read_text(encoding="utf-8"))
            vi_raw["schema_version"] = "9.0"
            write_handoff(vi_path, vi_raw)
            raw["confirmation"]["vi_contract_sha256"] = sha256(vi_path)
            write_handoff(handoff, raw)
            with self.assertRaisesRegex(ValueError, "schema_version must be 1.1"):
                COMPILER.compile_theme(handoff, root / "bad-vi")

            shutil.copy2(VI_FIXTURE, vi_path)
            reference_path = root / REFERENCE_FIXTURE.name
            reference_path.write_text("not svg", encoding="utf-8")
            raw["confirmation"]["vi_contract_sha256"] = sha256(vi_path)
            raw["confirmation"]["reference_image_sha256"] = sha256(reference_path)
            write_handoff(handoff, raw)
            with self.assertRaisesRegex(ValueError, "not readable XML"):
                COMPILER.compile_theme(handoff, root / "bad-image")


class ProjectThemeCompilationTests(unittest.TestCase):
    def test_theme_directory_is_complete_deterministic_and_offline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = COMPILER.compile_theme(HANDOFF_FIXTURE, root / "first")
            second = COMPILER.compile_theme(HANDOFF_FIXTURE, root / "second")
            self.assertEqual({path.name for path in first.iterdir()}, COMPILER.OUTPUT_FILES)
            self.assertEqual(
                {path.name: sha256(path) for path in first.iterdir()},
                {path.name: sha256(second / path.name) for path in first.iterdir()},
            )
            combined = "".join(path.read_text(encoding="utf-8") for path in first.iterdir())
            self.assertNotRegex(combined, r"(?:src|href)=[\"']https?://|@import\b")
            bundle = THEME_RUNTIME.load_project_theme(first)
            self.assertEqual(bundle.theme_id, "project-urban-renewal-observation")

    def test_boundaries_remain_distinct_and_unknown_is_never_observed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            theme = COMPILER.compile_theme(HANDOFF_FIXTURE, Path(temp_dir) / "theme")
            manifest = json.loads((theme / "theme.json").read_text(encoding="utf-8"))
            provenance = json.loads((theme / "provenance.json").read_text(encoding="utf-8"))
            records = {record["path"]: record for record in provenance["boundary_records"]}
            self.assertEqual(records["components[3]"]["status"], "extension")
            self.assertTrue(records["components[3]"]["eligible"])
            self.assertFalse(records["components[3]"]["compiled"])
            self.assertEqual(records["components[3]"]["usage"], [])
            self.assertEqual(records["layout[1]"]["status"], "observed")
            self.assertTrue(records["layout[1]"]["eligible"])
            self.assertFalse(records["layout[1]"]["compiled"])
            self.assertEqual(records["layout[1]"]["usage"], [])
            self.assertTrue(records["evidence_language[0]"]["compiled"])
            self.assertTrue(records["evidence_language[0]"]["usage"])
            self.assertTrue(records["executable_layout.cover_structure"]["compiled"])
            self.assertTrue(records["executable_layout.cover_structure"]["usage"])
            self.assertEqual(records["imagery[1]"]["status"], "unknown")
            self.assertFalse(records["imagery[1]"]["compiled"])
            self.assertNotIn(
                "imagery[1]", {source["source"] for source in manifest["token_sources"].values()}
            )
            self.assertTrue(provenance["fallback_records"])
            self.assertTrue(
                all(
                    record["status"] == "fallback" and record["usage"]
                    for record in provenance["fallback_records"]
                )
            )

    def test_unknown_executable_layout_uses_separate_reversible_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            handoff, raw = stage_handoff(root)
            vi_path = root / VI_FIXTURE.name
            contract = json.loads(vi_path.read_text(encoding="utf-8"))
            contract["executable_layout"]["visual_focus"] = {
                "value": "unknown",
                "status": "unknown",
                "basis": "参考没有足够证据确定单一视觉焦点",
            }
            write_handoff(vi_path, contract)
            raw["confirmation"]["vi_contract_sha256"] = sha256(vi_path)
            write_handoff(handoff, raw)

            theme = COMPILER.compile_theme(handoff, root / "theme")
            manifest = json.loads((theme / "theme.json").read_text(encoding="utf-8"))
            provenance = json.loads((theme / "provenance.json").read_text(encoding="utf-8"))
            boundary = next(
                record
                for record in provenance["boundary_records"]
                if record["path"] == "executable_layout.visual_focus"
            )
            fallback = next(
                record
                for record in provenance["fallback_records"]
                if record.get("field") == "executable_layout.visual_focus"
            )
            self.assertFalse(boundary["eligible"])
            self.assertFalse(boundary["compiled"])
            self.assertEqual(boundary["usage"], [])
            self.assertEqual(fallback["status"], "fallback")
            self.assertEqual(fallback["value"], "balanced")
            self.assertTrue(fallback["usage"])
            self.assertEqual(manifest["executable_layout"]["visual_focus"], "balanced")
            self.assertEqual(manifest["structure_sources"]["visual_focus"]["status"], "fallback")
            THEME_RUNTIME.load_project_theme(theme)

    def test_unknown_density_uses_medium_rhythm_without_becoming_observed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            handoff, raw = stage_handoff(root)
            vi_path = root / VI_FIXTURE.name
            contract = json.loads(vi_path.read_text(encoding="utf-8"))
            contract["executable_layout"]["density"] = {
                "value": "unknown",
                "status": "unknown",
                "basis": "参考没有足够证据判断跨页面信息密度",
            }
            write_handoff(vi_path, contract)
            raw["confirmation"]["vi_contract_sha256"] = sha256(vi_path)
            write_handoff(handoff, raw)

            theme = COMPILER.compile_theme(handoff, root / "theme")
            manifest = json.loads((theme / "theme.json").read_text(encoding="utf-8"))
            provenance = json.loads((theme / "provenance.json").read_text(encoding="utf-8"))
            boundary = next(
                record
                for record in provenance["boundary_records"]
                if record["path"] == "executable_layout.density"
            )
            field_fallback = next(
                record
                for record in provenance["fallback_records"]
                if record.get("field") == "executable_layout.density"
            )
            token_fallback = next(
                record
                for record in provenance["fallback_records"]
                if record.get("token") == "rhythm.label_title"
            )
            self.assertFalse(boundary["eligible"])
            self.assertFalse(boundary["compiled"])
            self.assertEqual(boundary["usage"], [])
            self.assertEqual(manifest["executable_layout"]["density"], "medium")
            self.assertEqual(manifest["tokens"]["rhythm_label_title"], "18px")
            self.assertEqual(field_fallback["status"], "fallback")
            self.assertEqual(token_fallback["status"], "fallback")
            self.assertEqual(token_fallback["source"], "compiler-neutral-default")
            THEME_RUNTIME.load_project_theme(theme)

    def test_opposite_vi_contracts_compile_different_dom_css_variants_and_composition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            city = COMPILER.compile_theme(HANDOFF_FIXTURE, root / "city")
            centered = COMPILER.compile_theme(CENTERED_HANDOFF_FIXTURE, root / "centered")
            city_templates = (city / "templates.html").read_text(encoding="utf-8")
            centered_templates = (centered / "templates.html").read_text(encoding="utf-8")
            city_css = (city / "theme.css").read_text(encoding="utf-8")
            centered_css = (centered / "theme.css").read_text(encoding="utf-8")
            city_manifest = json.loads((city / "theme.json").read_text(encoding="utf-8"))
            centered_manifest = json.loads((centered / "theme.json").read_text(encoding="utf-8"))

            self.assertNotEqual(city_templates, centered_templates)
            self.assertNotEqual(city_manifest["layout_variants"], centered_manifest["layout_variants"])
            self.assertNotEqual(city_manifest["identity"]["composition"], centered_manifest["identity"]["composition"])
            self.assertIn("pt-card-grid", city_templates)
            self.assertIn("pt-process-row", city_templates)
            self.assertIn("pt-evidence-layout", city_templates)
            self.assertNotIn("pt-content-focus", city_templates)
            self.assertIn("pt-content-focus", centered_templates)
            self.assertIn('<ol class="pt-process pt-process-column">', centered_templates)
            self.assertIn("pt-chart-focus", centered_templates)
            self.assertNotIn("pt-card-grid", centered_templates)
            self.assertIn("grid-template-columns:7fr 5fr", city_css)
            self.assertIn("flex-direction:column", centered_css)
            self.assertIn("--pt-radius: 0", city_css)
            self.assertIn("--pt-radius: 22px", centered_css)
            self.assertIn('data-rhythm-check="--pt-rhythm-label-title"', city_templates)
            self.assertIn('data-rhythm-check="--pt-rhythm-heading-content"', centered_templates)
            self.assertIn(":where(h1, h2, h3, p) { margin: 0; }", city_css)
            self.assertNotIn(".pt-cover h1 { margin:", city_css)
            self.assertEqual(city_manifest["tokens"]["rhythm_label_title"], "18px")
            self.assertEqual(city_manifest["tokens"]["rhythm_heading_content"], "32px")
            self.assertEqual(centered_manifest["tokens"]["rhythm_label_title"], "24px")
            self.assertEqual(centered_manifest["tokens"]["rhythm_heading_content"], "44px")

            city_provenance = json.loads(
                (city / "provenance.json").read_text(encoding="utf-8")
            )
            density = next(
                record
                for record in city_provenance["boundary_records"]
                if record["path"] == "executable_layout.density"
            )
            self.assertIn("theme.json:tokens.rhythm_label_title", density["usage"])
            self.assertIn("theme.css:--pt-rhythm-heading-content", density["usage"])
            self.assertEqual(
                set(density["usage"]),
                set(city_manifest["structure_sources"]["density"]["usage"]),
            )

    def test_manifest_encodes_full_visual_grammar_and_static_motion_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            theme = COMPILER.compile_theme(HANDOFF_FIXTURE, Path(temp_dir) / "theme")
            manifest = json.loads((theme / "theme.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["project"]["global_built_in"])
            self.assertEqual(manifest["project"]["target_mode"], "presentation")
            self.assertEqual(
                set(manifest["identity"]),
                {"composition", "hierarchy", "image_treatment", "module_language", "chart_evidence", "motion"},
            )
            self.assertEqual(
                set(manifest["components"]), {"card", "panel", "label", "border", "image", "chart"}
            )
            self.assertEqual(
                set(manifest["executable_layout"]),
                set(THEME_RUNTIME.EXECUTABLE_LAYOUT_OPTIONS),
            )
            self.assertEqual({item["role"] for item in manifest["layout_variants"]}, {"cover", "content", "evidence-data", "closing"})
            self.assertFalse(manifest["motion"]["observed_from_reference"])
            self.assertIn("shared Runtime", manifest["motion"]["source"])
            self.assertTrue(manifest["preserve"])
            self.assertTrue(manifest["forbidden"])

    def test_loader_rejects_structure_provenance_or_variant_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            theme = COMPILER.compile_theme(HANDOFF_FIXTURE, root / "theme")
            provenance_path = theme / "provenance.json"
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            record = next(
                item
                for item in provenance["boundary_records"]
                if item["path"] == "executable_layout.cover_structure"
            )
            record["compiled"] = False
            provenance_path.write_text(json.dumps(provenance, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "compiled state|compiled provenance mismatch"):
                THEME_RUNTIME.load_project_theme(theme)

            COMPILER.compile_theme(HANDOFF_FIXTURE, theme)
            manifest_path = theme / "theme.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["layout_variants"][0]["id"] = "drifted-cover"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "layout_variants"):
                THEME_RUNTIME.load_project_theme(theme)

    def test_compiler_writes_only_inside_clean_target_and_rejects_extras(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "theme"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("user", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected files"):
                COMPILER.compile_theme(HANDOFF_FIXTURE, output)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "user")
            self.assertEqual({path.name for path in output.iterdir()}, {"keep.txt"})


class ProjectThemeRendererTests(unittest.TestCase):
    def test_explicit_project_theme_uses_shared_runtime_and_source_contract(self) -> None:
        content = RENDERER.load_content(CONTENT_FIXTURE)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            theme = COMPILER.compile_theme(HANDOFF_FIXTURE, root / "theme")
            output = RENDERER.render_project_theme(
                content,
                theme,
                root / "report.html",
                ILLUSTRATION_FIXTURE,
                source_kind="illustrative",
            )
            document = output.read_text(encoding="utf-8")
            self.assertIn("window.TaoHtmlRuntime", document)
            self.assertIn('data-theme-kind="project"', document)
            self.assertIn('data-mode="presentation"', document)
            self.assertIn('data-source-kind="illustrative"', document)
            self.assertIn("示意内容图片（待核实）", document)
            self.assertIn("示意 / 待核实", document)
            self.assertIn('data-layout="cover-split-7-5-image-right-start"', document)
            self.assertIn('data-layout="data-source-chart-split-2-col-image-right"', document)
            check = subprocess.run(
                [sys.executable, str(CHECK_ASSETS), str(output), "--strict-offline"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(check.returncode, 0, msg=check.stdout + check.stderr)

    def test_project_theme_is_structurally_distinct_not_a_color_swap(self) -> None:
        content = RENDERER.load_content(CONTENT_FIXTURE)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            theme = COMPILER.compile_theme(HANDOFF_FIXTURE, root / "theme")
            project_output = RENDERER.render_project_theme(content, theme, root / "project.html")
            built_in_output = RENDERER.render_theme(
                content, "black-white-fluorescent-cards", root / "built-in.html"
            )
            project_html = project_output.read_text(encoding="utf-8")
            built_in_html = built_in_output.read_text(encoding="utf-8")
            project_layouts = re.findall(r'data-layout="([^"]+)"', project_html)
            built_in_layouts = re.findall(r'data-layout="([^"]+)"', built_in_html)
            self.assertNotEqual(project_layouts, built_in_layouts)
            self.assertIn("pt-cover-layout", project_html)
            self.assertNotIn("pt-cover-layout", built_in_html)
            self.assertIn("grid-template-columns:7fr 5fr", project_html)
            self.assertIn('data-rhythm-check="--pt-rhythm-label-title"', project_html)

    def test_existing_four_built_in_ids_and_cli_calls_remain_unchanged(self) -> None:
        self.assertEqual(RENDERER.THEME_IDS, THEME_RUNTIME.BUILT_IN_THEME_IDS)
        for theme_id in RENDERER.THEME_IDS:
            manifest = RENDERER.load_manifest(theme_id)
            self.assertEqual(manifest["id"], theme_id)
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "built-in.html"
            run = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_ROOT / "render_visual_system.py"),
                    "--content",
                    str(CONTENT_FIXTURE),
                    "--theme",
                    "rigorous-consulting-report",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, msg=run.stdout + run.stderr)
            self.assertTrue(output.is_file())


class ProjectThemeWorkflowTests(unittest.TestCase):
    def test_skill_routes_confirmed_vi_to_project_compiler_before_brief(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        reference = (SKILL_ROOT / "references" / "project-theme-compiler.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("references/project-theme-compiler.md", skill)
        self.assertLess(
            skill.index('After “确认 VI”'), skill.index("Report Design Brief", skill.index('After “确认 VI”'))
        )
        for marker in (
            '"phrase": "确认 VI"',
            '"vi_contract_sha256"',
            '"reference_image_sha256"',
            '"target_mode"',
            '"customer_corrections"',
            "unknown",
            "fallback",
            "--project-theme",
        ):
            self.assertIn(marker, reference)

    def test_docs_keep_project_theme_out_of_four_built_ins_and_static_motion(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        workflow = (ROOT / "docs" / "workflow.md").read_text(encoding="utf-8")
        router = (SKILL_ROOT / "references" / "visual-systems.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("不是第五套内置主题", readme)
        self.assertIn("项目主题不是第五套内置风格", workflow)
        self.assertIn("This router remains exactly four built-in systems", router)
        self.assertIn("动效由 Runtime 和报告任务决定，不从单图推断", readme)


if __name__ == "__main__":
    unittest.main()
