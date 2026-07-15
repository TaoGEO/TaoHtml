#!/usr/bin/env python3
"""Build one self-contained Codex and Claude marketplace bundle from TaoHtml's source skill."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILL_SOURCE = ROOT / "skill" / "taohtml"
CLAUDE_MANIFEST_SOURCE = ROOT / ".claude-plugin" / "plugin.json"
BUNDLE_NAME = "taohtml-marketplace"
PLUGIN_NAME = "taohtml"
MARKETPLACE_NAME = "taohtml"
DESCRIPTION = (
    "Turn ideas and source material into confirmed design briefs and polished "
    "offline HTML reports."
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_bundle(bundle_root: Path, version: str) -> Path:
    plugin_root = bundle_root / "plugins" / PLUGIN_NAME
    skill_target = plugin_root / "skills" / PLUGIN_NAME
    shutil.copytree(
        SKILL_SOURCE,
        skill_target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    shutil.copy2(ROOT / "LICENSE", plugin_root / "LICENSE")

    claude_manifest = read_json(CLAUDE_MANIFEST_SOURCE)
    claude_manifest["skills"] = "./skills/"
    claude_manifest["version"] = version
    codex_manifest = {
        **claude_manifest,
        "interface": {
            "displayName": "TaoHtml",
            "shortDescription": "Turn source material into polished offline HTML",
            "longDescription": DESCRIPTION,
            "developerName": "Tao",
            "category": "Productivity",
            "capabilities": ["Write"],
            "defaultPrompt": [
                "Use $taohtml to turn my idea or source material into a confirmed report design brief."
            ],
        },
    }
    write_json(plugin_root / ".codex-plugin" / "plugin.json", codex_manifest)
    write_json(plugin_root / ".claude-plugin" / "plugin.json", claude_manifest)

    write_json(
        bundle_root / ".agents" / "plugins" / "marketplace.json",
        {
            "name": MARKETPLACE_NAME,
            "interface": {"displayName": "TaoHtml"},
            "plugins": [
                {
                    "name": PLUGIN_NAME,
                    "source": {
                        "source": "local",
                        "path": f"./plugins/{PLUGIN_NAME}",
                    },
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_INSTALL",
                    },
                    "category": "Productivity",
                }
            ],
        },
    )
    write_json(
        bundle_root / ".claude-plugin" / "marketplace.json",
        {
            "name": MARKETPLACE_NAME,
            "metadata": {
                "description": "Install TaoHtml for Codex or Claude Code."
            },
            "owner": {
                "name": "Tao",
                "url": "https://github.com/TaoGEO",
            },
            "plugins": [
                {
                    "name": PLUGIN_NAME,
                    "source": f"./plugins/{PLUGIN_NAME}",
                    "description": DESCRIPTION,
                }
            ],
        },
    )
    return plugin_root


def package_bundle(output_zip: Path) -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    output_zip = output_zip.resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="taohtml-marketplace-") as temp_dir:
        bundle_root = Path(temp_dir) / BUNDLE_NAME
        build_bundle(bundle_root, version)
        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(bundle_root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(bundle_root.parent))

    print(f"Packaged TaoHtml marketplace {version}: {output_zip}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Package one local marketplace bundle for Codex and Claude Code."
    )
    parser.add_argument("output_zip", type=Path, help="Destination .zip path.")
    args = parser.parse_args()
    if args.output_zip.suffix.lower() != ".zip":
        parser.error("output path must end in .zip")
    package_bundle(args.output_zip)


if __name__ == "__main__":
    main()
