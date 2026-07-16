from __future__ import annotations

import copy
import base64
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
CORPORATE_HANDOFF_FIXTURE = FIXTURES / "corporate-template-handoff.json"
CORPORATE_VI_FIXTURE = FIXTURES / "corporate-template-vi-contract.json"
CORPORATE_REFERENCE_FIXTURE = FIXTURES / "corporate-template-reference.png"
FAMILY_HANDOFF_FIXTURE = FIXTURES / "corporate-family-handoff.json"
FAMILY_VI_FIXTURE = FIXTURES / "corporate-family-vi-contract.json"
FAMILY_REFERENCE_FIXTURES = [
    FIXTURES / f"corporate-family-{role}.png"
    for role in ("cover", "toc", "section")
]
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


def compile_layout(
    root: Path, label: str, **values: str
) -> Path:
    stage = root / f"{label}-input"
    stage.mkdir()
    for source in (VI_FIXTURE, REFERENCE_FIXTURE):
        shutil.copy2(source, stage / source.name)
    contract_path = stage / VI_FIXTURE.name
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    for field, value in values.items():
        contract["executable_layout"][field] = {
            "value": value,
            "status": "unknown" if value == "unknown" else "extension",
            "basis": f"参数化编译合同：{field}={value}",
        }
    write_handoff(contract_path, contract)
    raw = json.loads(HANDOFF_FIXTURE.read_text(encoding="utf-8"))
    raw["confirmation"]["vi_contract_sha256"] = sha256(contract_path)
    handoff = stage / "handoff.json"
    write_handoff(handoff, raw)
    return COMPILER.compile_theme(handoff, root / f"{label}-theme")


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

    def test_every_legal_cover_combination_compiles_real_order_or_background_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            programs: set[tuple[str, str]] = set()
            cases: list[tuple[str, dict[str, str], str, str]] = []
            for split in ("7:5", "5:7", "1:1"):
                copy_image = {
                    "7:5": ("7fr", "5fr"),
                    "5:7": ("5fr", "7fr"),
                    "1:1": ("1fr", "1fr"),
                }[split]
                cases.extend(
                    [
                        (
                            f"split-left-{split.replace(':', '-')}",
                            {"cover_structure": "split", "cover_split": split, "image_placement": "left"},
                            "art-first",
                            f"grid-template-columns:{copy_image[1]} {copy_image[0]}",
                        ),
                        (
                            f"split-right-{split.replace(':', '-')}",
                            {"cover_structure": "split", "cover_split": split, "image_placement": "right"},
                            "copy-first",
                            f"grid-template-columns:{copy_image[0]} {copy_image[1]}",
                        ),
                    ]
                )
            cases.extend(
                [
                    (
                        "single-top",
                        {
                            "cover_structure": "single-column",
                            "cover_split": "none",
                            "image_placement": "top",
                            "data_structure": "chart-focus",
                            "data_columns": "1",
                        },
                        "art-first",
                        "flex-direction:column",
                    ),
                    (
                        "single-bottom",
                        {
                            "cover_structure": "single-column",
                            "cover_split": "none",
                            "image_placement": "bottom",
                            "data_structure": "chart-focus",
                            "data_columns": "1",
                        },
                        "copy-first",
                        "flex-direction:column",
                    ),
                    (
                        "single-background",
                        {
                            "cover_structure": "single-column",
                            "cover_split": "none",
                            "image_placement": "background",
                            "image_fit": "cover",
                            "data_structure": "chart-focus",
                            "data_columns": "1",
                        },
                        "copy-first",
                        "position:relative;overflow:hidden;isolation:isolate",
                    ),
                ]
            )

            for label, values, order, css_marker in cases:
                with self.subTest(label=label):
                    theme = compile_layout(root, label, **values)
                    templates = (theme / "templates.html").read_text(encoding="utf-8")
                    css = (theme / "theme.css").read_text(encoding="utf-8")
                    cover = templates.split("</section>", 1)[0]
                    art_index = cover.index('class="pt-cover-art"')
                    copy_index = cover.index('class="pt-cover-copy"')
                    if order == "art-first":
                        self.assertLess(art_index, copy_index)
                    else:
                        self.assertLess(copy_index, art_index)
                    self.assertIn(css_marker, css)
                    if values["image_placement"] == "background":
                        self.assertIn("pt-cover-image-background", cover)
                        self.assertIn("pt-background-claim", cover)
                        self.assertNotIn('class="pt-claim fragment"', cover)
                        self.assertIn(".pt-cover-image-background .pt-cover-art", css)
                    if values["cover_structure"] == "split":
                        data_slide = templates.split(
                            'data-title="证据与数据"', 1
                        )[1].split("</section>", 1)[0]
                        source_index = data_slide.index("pt-source-frame")
                        panel_index = data_slide.index("pt-data-panel")
                        if values["image_placement"] == "left":
                            self.assertLess(source_index, panel_index)
                        else:
                            self.assertLess(panel_index, source_index)
                    programs.add((cover, css))
            self.assertEqual(len(programs), len(cases))

    def test_every_legal_content_structure_column_pair_executes_its_grid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cases = (
                ("card-grid", "1", "pt-card-grid"),
                ("card-grid", "2", "pt-card-grid"),
                ("card-grid", "3", "pt-card-grid"),
                ("stack", "1", "pt-content-stack"),
                ("single-focus", "1", "pt-content-focus"),
            )
            programs: set[tuple[str, str]] = set()
            for structure, columns, marker in cases:
                with self.subTest(structure=structure, columns=columns):
                    theme = compile_layout(
                        root,
                        f"content-{structure}-{columns}",
                        content_structure=structure,
                        content_columns=columns,
                    )
                    templates = (theme / "templates.html").read_text(encoding="utf-8")
                    css = (theme / "theme.css").read_text(encoding="utf-8")
                    self.assertIn(marker, templates)
                    if structure == "card-grid":
                        self.assertIn(
                            f"grid-template-columns: repeat({columns}, minmax(0,1fr))",
                            css,
                        )
                    else:
                        self.assertIn(
                            f"grid-template-columns:repeat({columns},minmax(0,1fr))",
                            css,
                        )
                    programs.add((templates, css))
            self.assertEqual(len(programs), len(cases))

    def test_every_legal_data_structure_column_pair_executes_outer_or_metric_grid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cases = (
                ("source-chart-split", "2", "pt-data-panel", "repeat(2,minmax(0,1fr))"),
                ("chart-focus", "1", "pt-chart-focus", "repeat(1,minmax(0,1fr))"),
                ("table-focus", "1", "pt-table-focus-wrap", "repeat(1,minmax(0,1fr))"),
                ("metrics-grid", "1", "pt-metrics-grid", "repeat(1,minmax(0,1fr))"),
                ("metrics-grid", "2", "pt-metrics-grid", "repeat(2,minmax(0,1fr))"),
                ("metrics-grid", "3", "pt-metrics-grid", "repeat(3,minmax(0,1fr))"),
            )
            programs: set[tuple[str, str]] = set()
            for structure, columns, marker, grid in cases:
                with self.subTest(structure=structure, columns=columns):
                    theme = compile_layout(
                        root,
                        f"data-{structure}-{columns}",
                        data_structure=structure,
                        data_columns=columns,
                    )
                    templates = (theme / "templates.html").read_text(encoding="utf-8")
                    css = (theme / "theme.css").read_text(encoding="utf-8")
                    self.assertIn(marker, templates)
                    self.assertIn(grid, css)
                    if structure == "source-chart-split":
                        data_slide = templates.split('data-title="证据与数据"', 1)[1].split(
                            "</section>", 1
                        )[0]
                        self.assertLess(
                            data_slide.index("pt-data-panel"),
                            data_slide.index("pt-source-frame"),
                        )
                    programs.add((templates, css))
            self.assertEqual(len(programs), len(cases))

    def test_every_remaining_scalar_enum_value_changes_executable_output(self) -> None:
        field_values = {
            "page_axis": ("row", "column"),
            "alignment": ("start", "center", "end"),
            "image_aspect_ratio": ("16:9", "4:3", "3:2", "1:1", "3:4"),
            "image_fit": ("cover", "contain"),
            "image_treatment": ("natural", "muted", "monochrome", "high-contrast"),
            "module_organization": ("hard-grid", "soft-stack", "open-field"),
            "density": ("low", "medium", "high"),
            "visual_focus": ("headline-and-image", "image-first", "balanced"),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for field, values in field_values.items():
                programs: set[tuple[str, str]] = set()
                for value in values:
                    with self.subTest(field=field, value=value):
                        theme = compile_layout(root, f"scalar-{field}-{value}", **{field: value})
                        programs.add(
                            (
                                (theme / "templates.html").read_text(encoding="utf-8"),
                                (theme / "theme.css").read_text(encoding="utf-8"),
                            )
                        )
                self.assertEqual(len(programs), len(values), field)

    def test_conditional_usage_and_fallback_provenance_match_executed_program(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            city = COMPILER.compile_theme(HANDOFF_FIXTURE, root / "city")
            centered = COMPILER.compile_theme(CENTERED_HANDOFF_FIXTURE, root / "centered")
            city_provenance = json.loads(
                (city / "provenance.json").read_text(encoding="utf-8")
            )
            centered_provenance = json.loads(
                (centered / "provenance.json").read_text(encoding="utf-8")
            )
            city_placement = next(
                record
                for record in city_provenance["boundary_records"]
                if record["path"] == "executable_layout.image_placement"
            )
            centered_placement = next(
                record
                for record in centered_provenance["boundary_records"]
                if record["path"] == "executable_layout.image_placement"
            )
            city_split = next(
                record
                for record in city_provenance["boundary_records"]
                if record["path"] == "executable_layout.cover_split"
            )
            centered_split = next(
                record
                for record in centered_provenance["boundary_records"]
                if record["path"] == "executable_layout.cover_split"
            )
            self.assertIn("templates.html:data source DOM order", city_placement["usage"])
            self.assertIn("theme.json:layout_variants[3]", city_placement["usage"])
            self.assertNotIn(
                "templates.html:data source DOM order", centered_placement["usage"]
            )
            self.assertNotIn("theme.json:layout_variants[3]", centered_placement["usage"])
            self.assertIn(
                "theme.css:.pt-cover-layout grid-template-columns",
                city_split["usage"],
            )
            self.assertNotIn(
                "theme.css:.pt-cover-layout grid-template-columns",
                centered_split["usage"],
            )
            self.assertIn(
                "compiler guardrail:single-column cover requires cover_split=none",
                centered_split["usage"],
            )

            fallback_theme = compile_layout(
                root, "conditional-fallback", cover_split="unknown"
            )
            fallback_manifest = json.loads(
                (fallback_theme / "theme.json").read_text(encoding="utf-8")
            )
            fallback_provenance = json.loads(
                (fallback_theme / "provenance.json").read_text(encoding="utf-8")
            )
            fallback = next(
                record
                for record in fallback_provenance["fallback_records"]
                if record.get("field") == "executable_layout.cover_split"
            )
            boundary = next(
                record
                for record in fallback_provenance["boundary_records"]
                if record["path"] == "executable_layout.cover_split"
            )
            self.assertEqual(fallback_manifest["executable_layout"]["cover_split"], "1:1")
            self.assertEqual(fallback["value"], "1:1")
            self.assertIn("compatible with split", fallback["basis"])
            self.assertFalse(boundary["compiled"])
            THEME_RUNTIME.load_project_theme(fallback_theme)

            compatible_theme = compile_layout(
                root,
                "compatible-cover-fallbacks",
                cover_structure="unknown",
                cover_split="unknown",
                image_placement="unknown",
            )
            compatible_manifest = json.loads(
                (compatible_theme / "theme.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                {
                    field: compatible_manifest["executable_layout"][field]
                    for field in (
                        "cover_structure",
                        "cover_split",
                        "image_placement",
                    )
                },
                {
                    "cover_structure": "split",
                    "cover_split": "1:1",
                    "image_placement": "right",
                },
            )
            THEME_RUNTIME.load_project_theme(compatible_theme)

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
            manifest["executable_layout"]["content_structure"] = "stack"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,
                "content_structure=stack is incompatible with content_columns=3",
            ):
                THEME_RUNTIME.load_project_theme(theme)

            COMPILER.compile_theme(HANDOFF_FIXTURE, theme)
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


class CorporateFidelityThemeTests(unittest.TestCase):
    def test_compiler_embeds_only_exact_fixed_crops_and_records_source_and_crop_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            theme = COMPILER.compile_theme(
                CORPORATE_HANDOFF_FIXTURE, root / "theme"
            )
            repeated = COMPILER.compile_theme(
                CORPORATE_HANDOFF_FIXTURE, root / "theme-repeated"
            )
            for name in ("theme.json", "theme.css", "templates.html", "provenance.json"):
                self.assertEqual(sha256(theme / name), sha256(repeated / name), name)
            manifest = json.loads((theme / "theme.json").read_text(encoding="utf-8"))
            provenance = json.loads(
                (theme / "provenance.json").read_text(encoding="utf-8")
            )
            templates = (theme / "templates.html").read_text(encoding="utf-8")
            shell = manifest["corporate_shell"]
            self.assertEqual(manifest["project"]["reference_mode"], "corporate_fidelity")
            self.assertEqual(
                shell["source_image_sha256"], sha256(CORPORATE_REFERENCE_FIXTURE)
            )
            self.assertEqual(shell["source_image_size"], [1600, 900])
            self.assertFalse(shell["full_screenshot_background"])
            self.assertFalse(shell["logo_redraw"])
            self.assertEqual(shell["fixed_motion"], "none")
            self.assertEqual(shell["content_motion_scope"], "editable_region_only")
            self.assertEqual(provenance["corporate_fidelity"], shell)
            self.assertEqual(len(shell["fixed_elements"]), 4)
            self.assertEqual(templates.count('data-fixed-motion="none"'), 5)
            self.assertEqual(templates.count('data-editable-region="safe-content"'), 5)
            self.assertEqual(templates.count('data-content-role="'), 5)
            self.assertEqual(templates.count("data:image/png;base64,"), 20)
            full_source_uri = base64.b64encode(
                CORPORATE_REFERENCE_FIXTURE.read_bytes()
            ).decode("ascii")
            self.assertNotIn(full_source_uri, templates)
            self.assertNotIn("示例正文 · 不得作为背景复用", templates)
            for item in shell["fixed_elements"]:
                self.assertEqual(
                    templates.count(f'data-locked-region="{item["id"]}"'), 5
                )
                self.assertEqual(
                    templates.count(f'data-crop-sha256="{item["crop_sha256"]}"'), 5
                )
            self.assertNotRegex(
                templates,
                r'class="[^"]*fragment[^"]*"[^>]*data-locked-region',
            )
            THEME_RUNTIME.load_project_theme(theme)

    def test_corporate_content_renders_five_pages_inside_safe_region_with_shared_runtime(self) -> None:
        content = RENDERER.load_content(CONTENT_FIXTURE)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            theme = COMPILER.compile_theme(CORPORATE_HANDOFF_FIXTURE, root / "theme")
            output = RENDERER.render_project_theme(
                content, theme, root / "report.html", source_kind="illustrative"
            )
            document = output.read_text(encoding="utf-8")
            self.assertEqual(document.count('<section class="slide'), 5)
            self.assertEqual(document.count('data-editable-region="safe-content"'), 5)
            self.assertIn("window.TaoHtmlRuntime", document)
            self.assertIn('data-theme-kind="project"', document)
            check = subprocess.run(
                [sys.executable, str(CHECK_ASSETS), str(output), "--strict-offline"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(check.returncode, 0, msg=check.stdout + check.stderr)

    def test_loader_rejects_fixed_element_motion_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            theme = COMPILER.compile_theme(
                CORPORATE_HANDOFF_FIXTURE, Path(temp_dir) / "theme"
            )
            css_path = theme / "theme.css"
            css = css_path.read_text(encoding="utf-8")
            css_path.write_text(
                css.replace("animation:none !important", "animation:spin 1s infinite", 1),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "disable fixed-element animation"):
                THEME_RUNTIME.load_project_theme(theme)


class CorporateTemplateFamilyThemeTests(unittest.TestCase):
    def test_family_compiler_routes_five_roles_and_embeds_only_exact_crops(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            theme = COMPILER.compile_theme(FAMILY_HANDOFF_FIXTURE, root / "theme")
            repeated = COMPILER.compile_theme(
                FAMILY_HANDOFF_FIXTURE, root / "theme-repeated"
            )
            for name in COMPILER.OUTPUT_FILES:
                self.assertEqual(sha256(theme / name), sha256(repeated / name), name)
            manifest = json.loads((theme / "theme.json").read_text(encoding="utf-8"))
            css = (theme / "theme.css").read_text(encoding="utf-8")
            templates = (theme / "templates.html").read_text(encoding="utf-8")
            family = manifest["corporate_template_family"]
            self.assertEqual(
                [item["role"] for item in family["reference_pages"]],
                ["cover", "toc", "section"],
            )
            self.assertEqual(
                [item["role"] for item in family["shell_variants"]],
                ["cover", "toc", "section", "content", "data"],
            )
            self.assertEqual(
                re.findall(r'data-shell-role="([^"]+)"', templates),
                ["cover", "toc", "section", "content", "data"],
            )
            self.assertEqual(templates.count('data-fixed-motion="none"'), 5)
            self.assertEqual(templates.count('data-editable-region="'), 5)
            self.assertIn(
                '[data-shell-role="cover"] .pt-cover-art { display:none !important; }',
                css,
            )
            self.assertNotIn('class="pt-cover-art"', templates)
            self.assertNotIn("corporate_shell", manifest)
            for source in FAMILY_REFERENCE_FIXTURES:
                self.assertNotIn(base64.b64encode(source.read_bytes()).decode("ascii"), templates)
            for shell in family["shell_variants"]:
                role = shell["role"]
                section = re.search(
                    rf'<section[^>]+data-shell-role="{role}".*?</section>',
                    templates,
                    re.DOTALL,
                )
                self.assertIsNotNone(section)
                assert section is not None
                self.assertEqual(
                    section.group(0).count('data-locked-region="'),
                    len(shell["fixed_regions"]),
                )
            THEME_RUNTIME.load_project_theme(theme)

    def test_runtime_fails_closed_on_crop_position_role_and_source_mapping_tamper(self) -> None:
        cases = {
            "crop bytes": (
                lambda text: re.sub(
                    r'(src="data:image/png;base64,)([A-Za-z0-9+/])',
                    lambda match: match.group(1) + ("B" if match.group(2) != "B" else "C"),
                    text,
                    count=1,
                ),
                "embedded crop bytes",
            ),
            "position": (
                lambda text: text.replace("left:0.000000%;", "left:0.100000%;", 1),
                "fixed placement drifted",
            ),
            "role": (
                lambda text: text.replace('data-shell-role="cover"', 'data-shell-role="toc"', 1),
                "source mapping drifted|unknown shell role|role or source mapping drifted",
            ),
            "source mapping": (
                lambda text: text.replace(
                    'data-shell-role="section" data-shell-status="observed" data-source-page-id="source-section"',
                    'data-shell-role="section" data-shell-status="observed" data-source-page-id="source-cover"',
                    1,
                ),
                "role or source mapping drifted",
            ),
        }
        for label, (tamper, message) in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                theme = COMPILER.compile_theme(
                    FAMILY_HANDOFF_FIXTURE, Path(temp_dir) / "theme"
                )
                templates_path = theme / "templates.html"
                original = templates_path.read_text(encoding="utf-8")
                changed = tamper(original)
                self.assertNotEqual(changed, original)
                templates_path.write_text(changed, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    THEME_RUNTIME.load_project_theme(theme)

    def test_runtime_rejects_late_cascade_overrides_for_fixed_and_editable_regions(self) -> None:
        attacks = {
            "fixed animation": (
                '.deck[data-theme="project-orbital-corporate-family"] '
                ".pt-corporate-fixed-region { "
                "animation: spin 1s infinite !important; }",
                "protected CSS|disable fixed-element animation",
            ),
            "editable geometry": (
                '.deck[data-theme="project-orbital-corporate-family"] '
                ".pt-corporate-editable { left:0 !important; top:0 !important; "
                "width:100% !important; height:100% !important; "
                "overflow:visible !important; }",
                "protected CSS|preserve protected geometry",
            ),
            "generic image motion": (
                "img { transform:translateX(20px) !important; }",
                "fixed-layer CSS|protected CSS",
            ),
            "fixed filter": (
                ".pt-corporate-fixed-region { filter:blur(20px) !important; }",
                "fixed-layer CSS",
            ),
            "fixed clip path": (
                ".pt-corporate-fixed-region { clip-path:inset(50%) !important; }",
                "fixed-layer CSS",
            ),
            "fixed mask": (
                ".pt-corporate-fixed-region { "
                "mask-image:linear-gradient(transparent,transparent) !important; }",
                "fixed-layer CSS",
            ),
            "fixed object position": (
                ".pt-corporate-fixed-region { "
                "object-position:100px 100px !important; }",
                "fixed-layer CSS",
            ),
            "fixed under unknown host": (
                ".future-host .pt-corporate-fixed-region { filter:blur(1px); }",
                "fixed-layer CSS",
            ),
            "editable under unknown host": (
                ".future-host .pt-corporate-editable { left:0 !important; }",
                "protected CSS",
            ),
        }
        for label, (attack, message) in attacks.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                theme = COMPILER.compile_theme(
                    FAMILY_HANDOFF_FIXTURE, Path(temp_dir) / "theme"
                )
                css_path = theme / "theme.css"
                css_path.write_text(
                    css_path.read_text(encoding="utf-8") + "\n" + attack + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ValueError, message):
                    THEME_RUNTIME.load_project_theme(theme)

    def test_runtime_allows_editable_descendant_geometry_without_weakening_container(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            theme = COMPILER.compile_theme(
                FAMILY_HANDOFF_FIXTURE, Path(temp_dir) / "theme"
            )
            css_path = theme / "theme.css"
            css_path.write_text(
                css_path.read_text(encoding="utf-8")
                + "\n"
                + '.deck[data-theme="project-orbital-corporate-family"] '
                + ".pt-corporate-editable .source-btn { top:9px; right:9px; }\n"
                + ".pt-corporate-editable .pt-card { filter:blur(0); "
                + "clip-path:inset(0); mask-image:none; object-position:center; }\n",
                encoding="utf-8",
            )
            THEME_RUNTIME.load_project_theme(theme)

    def test_runtime_rejects_active_content_anywhere_in_corporate_templates(self) -> None:
        attacks = {
            "script": (
                '<script>document.querySelectorAll(".pt-corporate-fixed-region")'
                '.forEach(e=>e.animate([{transform:"none"},'
                '{transform:"translateX(100px)"}],1000))</script>',
                "active script",
            ),
            "event attribute": (
                '<div onclick="document.body.dataset.pwned=1"></div>',
                "event attribute onclick",
            ),
            "javascript url": (
                '<a href="java&#x73;cript:document.body.dataset.pwned=1">x</a>',
                "javascript:",
            ),
        }
        for label, (payload, message) in attacks.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                theme = COMPILER.compile_theme(
                    FAMILY_HANDOFF_FIXTURE, Path(temp_dir) / "theme"
                )
                templates_path = theme / "templates.html"
                original = templates_path.read_text(encoding="utf-8")
                changed = original.replace(
                    "</section>", payload + "</section>", 1
                )
                self.assertNotEqual(changed, original)
                templates_path.write_text(changed, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    THEME_RUNTIME.load_project_theme(theme)

    def test_runtime_rejects_fixed_element_id_class_specificity_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            theme = COMPILER.compile_theme(
                FAMILY_HANDOFF_FIXTURE, Path(temp_dir) / "theme"
            )
            templates_path = theme / "templates.html"
            original = templates_path.read_text(encoding="utf-8")
            changed = original.replace(
                'class="pt-corporate-fixed-region"',
                'id="fixed-bypass" class="pt-corporate-fixed-region bypass"',
                1,
            )
            self.assertNotEqual(changed, original)
            templates_path.write_text(changed, encoding="utf-8")
            css_path = theme / "theme.css"
            css_path.write_text(
                css_path.read_text(encoding="utf-8")
                + "\n#fixed-bypass.bypass { transform:translateX(20px) !important; }\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "allowlist"):
                THEME_RUNTIME.load_project_theme(theme)

    def test_family_renders_five_page_offline_report_with_shared_runtime(self) -> None:
        content = RENDERER.load_content(CONTENT_FIXTURE)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            theme = COMPILER.compile_theme(FAMILY_HANDOFF_FIXTURE, root / "theme")
            output = RENDERER.render_project_theme(
                content, theme, root / "report.html", source_kind="illustrative"
            )
            document = output.read_text(encoding="utf-8")
            self.assertEqual(document.count('<section class="slide'), 5)
            self.assertEqual(
                re.findall(
                    r'<section\b[^>]+data-shell-role="([^"]+)"',
                    document,
                ),
                ["cover", "toc", "section", "content", "data"],
            )
            self.assertIn("window.TaoHtmlRuntime", document)
            check = subprocess.run(
                [sys.executable, str(CHECK_ASSETS), str(output), "--strict-offline"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(check.returncode, 0, msg=check.stdout + check.stderr)


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
        reference = (SKILL_ROOT / "references" / "project-theme-compiler.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("不是第五套内置主题", readme)
        self.assertIn("项目主题不是第五套内置风格", workflow)
        self.assertIn("This router remains exactly four built-in systems", router)
        self.assertIn(
            "动效由 Runtime 和报告任务决定，不从一张或多张静态图推断",
            readme,
        )
        for marker in (
            "参考风格重构",
            "企业模板保真",
            "截图中可见效果",
            "不重绘 Logo",
            "可编辑安全区",
        ):
            self.assertIn(marker, readme)
        self.assertIn("Corporate Template-Family Shell Boundary", reference)
        self.assertIn("Never embed the complete screenshot", reference)


if __name__ == "__main__":
    unittest.main()
