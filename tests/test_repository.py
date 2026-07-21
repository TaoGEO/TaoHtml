from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class RepositoryMetadataTests(unittest.TestCase):
    def test_hash_bound_text_fixtures_keep_lf_bytes_cross_platform(self) -> None:
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("tests/fixtures/*.json text eol=lf", attributes)
        self.assertIn("tests/fixtures/*.svg text eol=lf", attributes)

    def test_version_uses_semver(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## [{version}]", changelog)

    def test_skill_frontmatter_and_agent_metadata(self) -> None:
        skill_text = (ROOT / "skill" / "taohtml" / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", skill_text, re.DOTALL)
        self.assertIsNotNone(match, "SKILL.md must start with YAML frontmatter")
        frontmatter = yaml.safe_load(match.group(1))
        self.assertEqual(set(frontmatter), {"name", "description"})
        self.assertEqual(frontmatter["name"], "taohtml")
        self.assertLessEqual(len(frontmatter["description"]), 1024)

        agent_metadata = yaml.safe_load(
            (ROOT / "skill" / "taohtml" / "agents" / "openai.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(
            set(agent_metadata["interface"]),
            {"display_name", "short_description", "default_prompt"},
        )
        self.assertIn("$taohtml", agent_metadata["interface"]["default_prompt"])
        self.assertFalse(agent_metadata["policy"]["allow_implicit_invocation"])

    def test_skill_routes_to_existing_references(self) -> None:
        skill_dir = ROOT / "skill" / "taohtml"
        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        references = set(re.findall(r"`(references/[^`]+\.md)`", skill_text))
        self.assertTrue(references)
        for reference in references:
            self.assertTrue((skill_dir / reference).is_file(), reference)

    def test_skill_has_summary_and_design_brief_gates(self) -> None:
        skill_text = (ROOT / "skill" / "taohtml" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Material Understanding Summary", skill_text)
        self.assertIn("explicit confirmation of the current brief", skill_text)
        self.assertIn("A previous \"agree\"", skill_text)

    def test_production_requires_an_early_runnable_artifact(self) -> None:
        skill_dir = ROOT / "skill" / "taohtml"
        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        playbook_text = (skill_dir / "references" / "process-playbook.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("first runnable artifact", skill_text)
        self.assertIn("Land The First Runnable Artifact Early", playbook_text)
        self.assertIn("save a complete runnable `index.html`", playbook_text)
        self.assertIn("Do not add unrequested pages", playbook_text)

    def test_delivery_requires_brief_to_output_traceability(self) -> None:
        skill_dir = ROOT / "skill" / "taohtml"
        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        playbook_text = (skill_dir / "references" / "process-playbook.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("brief-to-output traceability ledger", skill_text)
        self.assertIn("every conjunct in compound requirements", skill_text)
        self.assertIn("brief-to-output traceability check", playbook_text)
        self.assertIn("responsibility boundary", playbook_text)

    def test_runtime_exposes_the_core_contract(self) -> None:
        template = (
            ROOT / "skill" / "taohtml" / "assets" / "html-deck-template" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("window.TaoHtmlRuntime", template)
        for method in (
            "getState",
            "setMode",
            "showPage",
            "nextStep",
            "previousStep",
            "nextPage",
            "previousPage",
            "toggleFullscreen",
            "setEditing",
        ):
            self.assertRegex(template, rf"\b{method}\b")

    def test_runtime_previous_step_and_fullscreen_control_contract(self) -> None:
        skill_dir = ROOT / "skill" / "taohtml"
        template = (
            skill_dir / "assets" / "html-deck-template" / "index.html"
        ).read_text(encoding="utf-8")
        contract = (skill_dir / "references" / "runtime-contract.md").read_text(
            encoding="utf-8"
        )
        qa_script = (skill_dir / "scripts" / "check_html_deck.py").read_text(
            encoding="utf-8"
        )
        previous_step = re.search(
            r"function previousStep\(\) \{(?P<body>.*?)\n    \}",
            template,
            re.DOTALL,
        )
        self.assertIsNotNone(previous_step)
        reading_branch = "if (state.mode === 'reading') return previousPage();"
        self.assertIn(reading_branch, previous_step.group("body"))
        self.assertNotIn(
            "previousPage();",
            previous_step.group("body").replace(reading_branch, ""),
        )
        self.assertIn(
            "setStage(state.index, state.stages[state.index] - 1);",
            previous_step.group("body"),
        )

        self.assertIn("const CONTROL_HIDE_DELAY_MS = 2000;", template)
        self.assertIn("function closeMoreMenu({ rearm = true } = {})", template)
        self.assertIn("function revealControlsFromMouse()", template)
        self.assertIn("document.addEventListener('mousemove', event => {", template)
        self.assertIn("if (!event.isTrusted", template)
        self.assertNotIn("['mousemove', 'pointerdown']", template)
        self.assertIn("syncControlsForContext({ fullscreenChanged: true });", template)

        self.assertIn("At the initial state it is a no-op", contract)
        self.assertIn("Only a trusted `mousemove`", contract)
        self.assertIn("`#pageIndicator` remains visible", contract)
        self.assertIn(
            "ArrowLeft at step zero must not perform whole-page navigation", qa_script
        )
        self.assertIn(
            "A non-mousemove input revealed presentation fullscreen controls",
            qa_script,
        )
        self.assertIn("menu_pinned_controls", qa_script)
        self.assertIn("hidden_more_keyboard_blocked", qa_script)
        self.assertIn("edit_mode_pinned_controls", qa_script)

    def test_runtime_browser_input_mapping_and_control_visibility(self) -> None:
        from playwright.sync_api import sync_playwright

        template = (
            ROOT / "skill" / "taohtml" / "assets" / "html-deck-template" / "index.html"
        )
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=["--disable-gpu"])
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            page.goto(template.resolve().as_uri(), wait_until="load")
            reset_presentation = """index => {
              const runtime = window.TaoHtmlRuntime;
              if (runtime.getState().mode === 'presentation') runtime.setMode('reading');
              runtime.showPage(index);
              runtime.setMode('presentation');
            }"""
            page.evaluate(reset_presentation, 0)

            initial = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.keyboard.press("ArrowLeft")
            self.assertEqual(page.evaluate("() => window.TaoHtmlRuntime.getState()"), initial)
            page.keyboard.press("ArrowRight")
            stepped = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            self.assertEqual((stepped["index"], stepped["stages"][0]), (0, 1))
            page.keyboard.press("ArrowRight")
            self.assertEqual(page.evaluate("() => window.TaoHtmlRuntime.getState().index"), 1)
            second_at_zero = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.keyboard.press("ArrowLeft")
            self.assertEqual(
                page.evaluate("() => window.TaoHtmlRuntime.getState()"),
                second_at_zero,
            )
            page.keyboard.press("PageUp")
            restored = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            self.assertEqual((restored["index"], restored["stages"][0]), (0, 1))
            page.keyboard.press("PageDown")
            self.assertEqual(page.evaluate("() => window.TaoHtmlRuntime.getState().index"), 1)

            page.evaluate("() => window.TaoHtmlRuntime.setMode('reading')")
            page.evaluate("() => window.TaoHtmlRuntime.showPage(0)")
            page.wait_for_timeout(520)
            self.assertTrue(
                page.locator(".slide.active .fragment").evaluate_all(
                    "els => els.every(el => getComputedStyle(el).opacity === '1')"
                )
            )
            page.keyboard.press("ArrowRight")
            self.assertEqual(page.evaluate("() => window.TaoHtmlRuntime.getState().index"), 1)
            page.keyboard.press("ArrowLeft")
            self.assertEqual(page.evaluate("() => window.TaoHtmlRuntime.getState().index"), 0)
            page.keyboard.press("Space")
            self.assertEqual(page.evaluate("() => window.TaoHtmlRuntime.getState().index"), 1)
            page.keyboard.press("PageUp")
            self.assertEqual(page.evaluate("() => window.TaoHtmlRuntime.getState().index"), 0)
            page.evaluate(
                """() => document.querySelector('.slide.active').dispatchEvent(
                  new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 })
                )"""
            )
            self.assertEqual(page.evaluate("() => window.TaoHtmlRuntime.getState().index"), 1)
            page.evaluate("() => window.TaoHtmlRuntime.setMode('presentation')")
            reset = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            self.assertEqual((reset["index"], reset["stages"][1]), (1, 0))

            page.evaluate(reset_presentation, 0)
            protected_before = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            protected_after = page.evaluate(
                """() => {
                  const slide = document.querySelector('.slide.active');
                  const sandbox = document.createElement('div');
                  sandbox.innerHTML = `
                    <a data-target href="#1">link</a>
                    <div data-target data-taohtml-attachment>attachment</div>
                    <div data-target class="ri-chart">chart</div>
                    <form data-target>form</form>
                    <div data-target contenteditable="true">editable</div>
                    <div data-target role="dialog">dialog</div>
                    <canvas data-target></canvas>`;
                  slide.appendChild(sandbox);
                  const states = [];
                  sandbox.querySelectorAll('[data-target]').forEach(target => {
                    target.dispatchEvent(new MouseEvent('click', {
                      bubbles: true, cancelable: true, button: 0,
                    }));
                    states.push(window.TaoHtmlRuntime.getState());
                  });
                  sandbox.remove();
                  return states;
                }"""
            )
            self.assertTrue(all(state == protected_before for state in protected_after))

            page.locator("#moreToggle").click()
            page.locator("#fullscreenToggle").click()
            page.wait_for_function(
                """() => Boolean(document.fullscreenElement) &&
                  document.querySelector('#deck').classList.contains('controls-hidden')"""
            )
            page.keyboard.press("ArrowRight")
            page.dispatch_event("#deck", "pointerdown")
            page.evaluate(
                """() => document.dispatchEvent(new MouseEvent('mousemove', {
                  bubbles: true, movementX: 10, movementY: 10,
                }))"""
            )
            self.assertEqual(page.locator("#deck.controls-hidden").count(), 1)
            page.evaluate(
                """() => document.querySelector('.slide.active').dispatchEvent(
                  new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 })
                )"""
            )
            self.assertEqual(page.locator("#deck.controls-hidden").count(), 1)
            page.mouse.move(420, 320)
            page.wait_for_function(
                "() => !document.querySelector('#deck').classList.contains('controls-hidden')"
            )
            page.wait_for_timeout(2200)
            self.assertEqual(page.locator("#deck.controls-hidden").count(), 1)
            self.assertTrue(
                page.locator("#pageIndicator").evaluate(
                    "el => getComputedStyle(el).opacity !== '0' && el.getBoundingClientRect().width > 0"
                )
            )
            page.evaluate("() => document.exitFullscreen()")
            browser.close()

    def test_runtime_names_controlled_steps_canvas_and_text_collision_gates(self) -> None:
        skill_dir = ROOT / "skill" / "taohtml"
        template = (
            skill_dir / "assets" / "html-deck-template" / "index.html"
        ).read_text(encoding="utf-8")
        contract = (skill_dir / "references" / "runtime-contract.md").read_text(
            encoding="utf-8"
        )
        qa_script = (skill_dir / "scripts" / "check_html_deck.py").read_text(
            encoding="utf-8"
        )
        renderer = (skill_dir / "scripts" / "render_visual_system.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('data-taohtml-step-contract="fragment-v1"', template)
        self.assertIn("CONTROLLED_STEP_CONTRACT = \"fragment-v1\"", qa_script)
        self.assertIn("CONTROLLED_STEP_SELECTOR = '.fragment'", template)
        self.assertIn("CONTROLLED_STEP_CONTRACT = \"fragment-v1\"", renderer)
        self.assertIn("CANVAS_COVERAGE_CHECK", qa_script)
        self.assertIn("TEXT_COLLISION_CHECK", qa_script)
        self.assertIn("data-qa-ignore-text-collision", contract)
        self.assertIn("SVG `<text>`", contract)


if __name__ == "__main__":
    unittest.main()
