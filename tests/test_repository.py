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


if __name__ == "__main__":
    unittest.main()
