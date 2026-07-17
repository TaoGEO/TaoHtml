from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill" / "taohtml"
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "html-deck-template"
EDITOR_JS = TEMPLATE_ROOT / "assets" / "runtime" / "taohtml-editor.js"
EDITOR_CSS = TEMPLATE_ROOT / "assets" / "runtime" / "taohtml-editor.css"
CONTENT = ROOT / "evals" / "taohtml-quality-v1" / "fixtures" / "visual-systems-content.json"


def load_renderer():
    path = SKILL_ROOT / "scripts" / "render_visual_system.py"
    spec = importlib.util.spec_from_file_location("taohtml_editor_renderer", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContentEditorAssetTests(unittest.TestCase):
    def test_template_loads_one_reusable_offline_editor_module(self) -> None:
        template = (TEMPLATE_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertTrue(EDITOR_JS.is_file())
        self.assertTrue(EDITOR_CSS.is_file())
        self.assertEqual(template.count('data-taohtml-editor-bundle="style"'), 1)
        self.assertEqual(template.count('data-taohtml-editor-bundle="script"'), 1)
        self.assertIn('href="assets/runtime/taohtml-editor.css"', template)
        self.assertIn('src="assets/runtime/taohtml-editor.js"', template)
        self.assertNotRegex(template, r"https?://|//cdn")

    def test_editor_contract_is_generic_and_has_no_undo_button(self) -> None:
        template = (TEMPLATE_ROOT / "index.html").read_text(encoding="utf-8")
        javascript = EDITOR_JS.read_text(encoding="utf-8")
        contract = (SKILL_ROOT / "references" / "content-editor.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("data-taohtml-edit-lock", template)
        self.assertIn("[data-taohtml-edit-lock]", javascript)
        self.assertIn('data-taohtml-edit="off"', contract)
        self.assertIn('data-taohtml-edit="text"', contract)
        self.assertIn('data-taohtml-edit="image"', contract)
        self.assertNotRegex(template + javascript, r'<button[^>]+(?:undo|redo)')
        self.assertIn("sessionStorage", javascript)
        self.assertNotIn("localStorage", javascript)
        self.assertIn("Ctrl/Cmd+Z", javascript)
        self.assertIn("new Blob", javascript)
        self.assertIn("编辑器不会生成 ZIP", javascript)

    def test_core_runtime_adds_editing_state_without_replacing_legacy_state(self) -> None:
        template = (TEMPLATE_ROOT / "index.html").read_text(encoding="utf-8")
        contract = (SKILL_ROOT / "references" / "runtime-contract.md").read_text(
            encoding="utf-8"
        )
        for legacy in ("mode: state.mode", "index: state.index", "stages: [...state.stages]"):
            self.assertIn(legacy, template)
        self.assertIn("editing: state.editing", template)
        self.assertIn("function setEditing(editing)", template)
        self.assertIn("Event consumers must ignore unknown future snapshot fields", contract)

    def test_renderer_inlines_editor_for_single_file_output(self) -> None:
        renderer = load_renderer()
        content = renderer.load_content(CONTENT)
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.html"
            renderer.render_theme(content, "black-white-fluorescent-cards", output)
            rendered = output.read_text(encoding="utf-8")
        self.assertIn('<style data-taohtml-editor-bundle="style">', rendered)
        self.assertIn('<script data-taohtml-editor-bundle="script">', rendered)
        self.assertIn("window.TaoHtmlEditor", rendered)
        self.assertNotIn('href="assets/runtime/taohtml-editor.css"', rendered)
        self.assertNotIn('src="assets/runtime/taohtml-editor.js"', rendered)

    def test_accessibility_hidden_fixed_shells_are_excluded_without_compiler_drift(self) -> None:
        javascript = EDITOR_JS.read_text(encoding="utf-8")
        compiler = (SKILL_ROOT / "scripts" / "compile_project_theme.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('[aria-hidden="true"]', javascript)
        self.assertEqual(
            compiler.count('<div class="pt-corporate-fixed-shell" aria-hidden="true" '),
            2,
        )


if __name__ == "__main__":
    unittest.main()
