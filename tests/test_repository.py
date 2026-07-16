from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class RepositoryMetadataTests(unittest.TestCase):
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
        self.assertIn("previousPage();", previous_step.group("body"))
        self.assertRegex(
            previous_step.group("body"),
            r"(?s)setStage\(state\.index, state\.stages\[state\.index\] - 1\);.*?return;.*?previousPage\(\);",
        )

        self.assertIn("function closeMoreMenu()", template)
        self.assertRegex(
            template,
            r"async function toggleFullscreen\(\) \{\s+closeMoreMenu\(\);\s+wakeControls\(\);",
        )
        self.assertRegex(
            template,
            r"(?s)document\.addEventListener\('fullscreenchange', \(\) => \{\s+closeMoreMenu\(\);.*?wakeControls\(\);",
        )

        self.assertIn("at the initial state, it moves to the previous page", contract)
        self.assertNotIn("at the initial state, it stays on the current page", contract)
        self.assertIn("restarts the auto-hide timer after `fullscreenchange`", contract)
        self.assertNotIn(
            "ArrowLeft at step zero must not perform whole-page navigation", qa_script
        )
        self.assertIn(
            "ArrowLeft at step zero did not return to the previous page and preserve its stage",
            qa_script,
        )
        self.assertIn("fullscreen_idle_hidden", qa_script)
        self.assertIn("fullscreen_pointer_revealed", qa_script)

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
