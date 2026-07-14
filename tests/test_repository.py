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


if __name__ == "__main__":
    unittest.main()
