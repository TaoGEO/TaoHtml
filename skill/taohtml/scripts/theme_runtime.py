#!/usr/bin/env python3
"""Load and validate built-in or project-specific TaoHtml theme assets."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, NamedTuple


SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from project_theme_layout import EXECUTABLE_LAYOUT_OPTIONS, validate_layout_values


SKILL_ROOT = Path(__file__).resolve().parents[1]
SYSTEMS_ROOT = SKILL_ROOT / "assets" / "visual-systems"
BUILT_IN_THEME_IDS = (
    "black-white-fluorescent-cards",
    "rigorous-consulting-report",
    "corporate-annual-report",
    "editorial-collage",
)
PROJECT_THEME_FILES = {"theme.json", "theme.css", "templates.html", "provenance.json"}
PROJECT_ID = re.compile(r"^project-[a-z0-9]+(?:-[a-z0-9]+)*$")
REMOTE_ASSET = re.compile(
    r"(?:src|href)\s*=\s*['\"]\s*(?:https?:)?//|@import\b|url\(\s*['\"]?\s*(?:https?:)?//",
    re.IGNORECASE,
)


class ThemeBundle(NamedTuple):
    theme_id: str
    display_name: str
    kind: str
    root: Path
    manifest: dict[str, Any]
    css: str
    templates: str
    target_mode: str | None


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{label} is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return raw


def _read_theme_assets(root: Path, manifest: dict[str, Any]) -> tuple[str, str]:
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError(f"Theme manifest files must be an object: {root / 'theme.json'}")
    if files.get("tokens") != "theme.css" or files.get("templates") != "templates.html":
        raise ValueError("Theme manifest must route tokens to theme.css and templates to templates.html.")
    css_path = root / "theme.css"
    templates_path = root / "templates.html"
    try:
        css = css_path.read_text(encoding="utf-8").strip()
        templates = templates_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ValueError(f"Theme asset is missing: {exc.filename}") from exc
    if not css or not templates:
        raise ValueError(f"Theme CSS and templates must be non-empty: {root}")
    if "</style" in css.lower():
        raise ValueError(f"Theme CSS contains a closing style tag: {root}")
    if REMOTE_ASSET.search(css + templates):
        raise ValueError(f"Theme contains a remote asset reference: {root}")
    if templates.count('<section class="slide') < 5:
        raise ValueError("A theme must provide at least five slide templates.")
    for marker in ("data-layout=", "fragment", "data-step="):
        if marker not in templates:
            raise ValueError(f"Theme templates are missing required marker: {marker}")
    return css, templates


def _validate_project_structure(
    manifest: dict[str, Any], provenance: dict[str, Any], templates: str
) -> None:
    layout = manifest.get("executable_layout")
    sources = manifest.get("structure_sources")
    if not isinstance(layout, dict) or set(layout) != set(EXECUTABLE_LAYOUT_OPTIONS):
        raise ValueError("Project theme executable_layout contract is incomplete.")
    if not isinstance(sources, dict) or set(sources) != set(EXECUTABLE_LAYOUT_OPTIONS):
        raise ValueError("Project theme structure_sources contract is incomplete.")
    for field, options in EXECUTABLE_LAYOUT_OPTIONS.items():
        if layout[field] not in options:
            raise ValueError(f"Project theme executable_layout.{field} is invalid.")
    validate_layout_values(layout)

    raw_records = provenance.get("boundary_records")
    raw_fallbacks = provenance.get("fallback_records")
    if not isinstance(raw_records, list) or not isinstance(raw_fallbacks, list):
        raise ValueError("Project theme provenance must include boundary and fallback records.")
    records = {
        record.get("path"): record for record in raw_records if isinstance(record, dict)
    }
    fallbacks = {
        record.get("field"): record
        for record in raw_fallbacks
        if isinstance(record, dict) and isinstance(record.get("field"), str)
    }
    for record in raw_records:
        if not isinstance(record, dict):
            raise ValueError("Project theme provenance boundary record must be an object.")
        compiled = record.get("compiled")
        eligible = record.get("eligible")
        usage = record.get("usage")
        if not isinstance(compiled, bool) or not isinstance(eligible, bool) or not isinstance(usage, list):
            raise ValueError("Project theme provenance eligible, compiled, and usage fields are invalid.")
        if eligible != (record.get("status") in {"observed", "extension"}):
            raise ValueError("Project theme provenance eligibility does not match boundary status.")
        if compiled != bool(usage) or (compiled and record.get("status") == "unknown"):
            raise ValueError("Project theme provenance compiled state does not match usage targets.")

    for field, source in sources.items():
        if not isinstance(source, dict):
            raise ValueError(f"Project theme structure_sources.{field} must be an object.")
        status = source.get("status")
        usage = source.get("usage")
        source_path = source.get("source")
        if not isinstance(usage, list) or not usage:
            raise ValueError(f"Project theme structure_sources.{field} requires usage targets.")
        contract_path = f"executable_layout.{field}"
        if status == "fallback":
            fallback = fallbacks.get(contract_path)
            boundary = records.get(contract_path)
            if (
                source_path != "compiler-neutral-default"
                or not isinstance(fallback, dict)
                or fallback.get("status") != "fallback"
                or fallback.get("value") != layout[field]
                or set(fallback.get("usage", [])) != set(usage)
                or not isinstance(boundary, dict)
                or boundary.get("status") != "unknown"
                or boundary.get("compiled") is not False
            ):
                raise ValueError(f"Project theme fallback provenance mismatch for {field}.")
        else:
            record = records.get(contract_path)
            if (
                source_path != contract_path
                or status not in {"observed", "extension"}
                or not isinstance(record, dict)
                or record.get("status") != status
                or record.get("value") != layout[field]
                or record.get("compiled") is not True
                or set(record.get("usage", [])) != set(usage)
            ):
                raise ValueError(f"Project theme compiled provenance mismatch for {field}.")

    variants = manifest.get("layout_variants")
    if not isinstance(variants, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("id"), str)
        for item in variants
    ):
        raise ValueError("Project theme layout_variants contract is invalid.")
    manifest_ids = [item["id"] for item in variants]
    template_ids = re.findall(r'data-layout="([^"]+)"', templates)
    if template_ids != manifest_ids:
        raise ValueError("Project theme templates do not match manifest layout_variants.")
    identity = manifest.get("identity")
    if not isinstance(identity, dict) or not isinstance(identity.get("composition"), str) or not identity["composition"].strip():
        raise ValueError("Project theme identity.composition must be non-empty.")


def load_built_in_theme(theme_id: str) -> ThemeBundle:
    if theme_id not in BUILT_IN_THEME_IDS:
        raise ValueError(f"Unknown theme: {theme_id}")
    root = SYSTEMS_ROOT / theme_id
    manifest = _load_json(root / "theme.json", "Theme manifest")
    if manifest.get("id") != theme_id:
        raise ValueError(f"Theme manifest id mismatch: {root / 'theme.json'}")
    css, templates = _read_theme_assets(root, manifest)
    return ThemeBundle(
        theme_id=theme_id,
        display_name=str(manifest.get("display_name", theme_id)),
        kind="built-in",
        root=root,
        manifest=manifest,
        css=css,
        templates=templates,
        target_mode=None,
    )


def load_project_theme(theme_dir: Path) -> ThemeBundle:
    supplied = theme_dir.expanduser()
    if supplied.is_symlink():
        raise ValueError(f"Project theme directory must not be a symlink: {supplied}")
    try:
        root = supplied.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"Project theme directory does not exist: {theme_dir}") from exc
    if not root.is_dir():
        raise ValueError(f"Project theme path is not a directory: {root}")
    actual = {path.name for path in root.iterdir()}
    if actual != PROJECT_THEME_FILES:
        missing = ", ".join(sorted(PROJECT_THEME_FILES - actual)) or "none"
        extra = ", ".join(sorted(actual - PROJECT_THEME_FILES)) or "none"
        raise ValueError(
            f"Project theme directory is incomplete; missing: {missing}; extra: {extra}."
        )
    if any(path.is_symlink() or not path.is_file() for path in root.iterdir()):
        raise ValueError(f"Project theme assets must be regular files, not symlinks: {root}")

    manifest = _load_json(root / "theme.json", "Project theme manifest")
    if manifest.get("schema_version") != "1.0" or manifest.get("kind") != "project":
        raise ValueError("Project theme manifest must declare schema_version 1.0 and kind project.")
    theme_id = manifest.get("id")
    if not isinstance(theme_id, str) or not PROJECT_ID.fullmatch(theme_id):
        raise ValueError("Project theme id must use the project-<slug> form.")
    if manifest.get("files") != {
        "tokens": "theme.css",
        "templates": "templates.html",
        "provenance": "provenance.json",
    }:
        raise ValueError("Project theme manifest files contract is invalid.")
    project = manifest.get("project")
    if not isinstance(project, dict) or project.get("target_mode") not in {
        "reading",
        "presentation",
    }:
        raise ValueError("Project theme target mode must be reading or presentation.")

    provenance = _load_json(root / "provenance.json", "Project theme provenance")
    if provenance.get("schema_version") != "1.0" or provenance.get("theme_id") != theme_id:
        raise ValueError("Project theme provenance does not match the manifest.")
    css, templates = _read_theme_assets(root, manifest)
    _validate_project_structure(manifest, provenance, templates)
    selector = f'.deck[data-theme="{theme_id}"]'
    if selector not in css:
        raise ValueError(f"Project theme CSS is not scoped to {selector}.")
    return ThemeBundle(
        theme_id=theme_id,
        display_name=str(manifest.get("display_name", theme_id)),
        kind="project",
        root=root,
        manifest=manifest,
        css=css,
        templates=templates,
        target_mode=str(project["target_mode"]),
    )
