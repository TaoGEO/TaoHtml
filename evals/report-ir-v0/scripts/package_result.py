#!/usr/bin/env python3
"""Create one complete WorkBuddy result archive for controller review."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any


ROUTES = ("direct", "ir")
COMMON_REQUIRED = (
    "deliverable/index.html",
    "deliverable/handoff.md",
    "run-metadata.json",
    "workspace-manifest.json",
)
IR_REQUIRED = (
    "report-ir.json",
    "deliverable/build-manifest.json",
    "tools/report_ir_adapter.py",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def compiler_dependency_hashes(workspace: Path, adapter: Path) -> dict[str, str]:
    skill_root = workspace / "skill" / "taohtml"
    shell_root = skill_root / "assets" / "html-deck-template"
    return {
        "adapter_sha256": sha256_file(adapter),
        "renderer_sha256": sha256_file(skill_root / "scripts" / "render_visual_system.py"),
        "theme_runtime_sha256": sha256_file(skill_root / "scripts" / "theme_runtime.py"),
        "runtime_shell_sha256": sha256_file(shell_root / "index.html"),
        "editor_css_sha256": sha256_file(
            shell_root / "assets" / "runtime" / "taohtml-editor.css"
        ),
        "editor_js_sha256": sha256_file(
            shell_root / "assets" / "runtime" / "taohtml-editor.js"
        ),
    }


def validate_ir_result(workspace: Path) -> None:
    ir = workspace / "report-ir.json"
    html = workspace / "deliverable" / "index.html"
    manifest_path = workspace / "deliverable" / "build-manifest.json"
    adapter = workspace / "tools" / "report_ir_adapter.py"
    manifest = load_json(manifest_path)
    compiler = manifest.get("compiler")
    input_hashes = manifest.get("input_hashes")
    output = manifest.get("output")
    if manifest.get("manifest_version") != "research-v0":
        raise ValueError("IR result manifest_version must be research-v0")
    if manifest.get("artifact_status") != "preview_unverified":
        raise ValueError("IR result must remain preview_unverified")
    if manifest.get("formal_delivery_ready") is not False:
        raise ValueError("IR compiler cannot mark formal_delivery_ready=true")
    if not isinstance(compiler, dict) or compiler.get("sha256") != sha256_file(adapter):
        raise ValueError("manifest compiler.sha256 does not match tools/report_ir_adapter.py")
    if manifest.get("compiler_dependencies") != compiler_dependency_hashes(workspace, adapter):
        raise ValueError("manifest compiler dependency hashes do not match executor inputs")
    if not isinstance(input_hashes, dict) or input_hashes.get("report_ir_sha256") != sha256_file(ir):
        raise ValueError("manifest report_ir_sha256 does not match report-ir.json")
    if not isinstance(output, dict) or output.get("sha256") != sha256_file(html):
        raise ValueError("manifest output.sha256 does not match deliverable/index.html")


def result_files(workspace: Path, output: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file() or path.resolve() == output.resolve():
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".zip"}:
            continue
        files.append(path)
    return files


def package(route: str, workspace: Path, output: Path) -> Path:
    workspace = workspace.resolve()
    output = output.resolve()
    workspace_manifest = load_json(workspace / "workspace-manifest.json")
    if workspace_manifest.get("route") != route:
        raise ValueError("workspace manifest route mismatch")
    expected_archive = workspace_manifest.get("expected_result_archive")
    if not isinstance(expected_archive, str) or output.name != expected_archive:
        raise ValueError(f"result archive must be named {expected_archive!r}")
    required = COMMON_REQUIRED + (IR_REQUIRED if route == "ir" else ())
    missing = [relative for relative in required if not (workspace / relative).is_file()]
    if missing:
        raise ValueError(f"missing result files: {', '.join(missing)}")
    if route == "ir":
        validate_ir_result(workspace)
    files = result_files(workspace, output)
    index = {
        "result_index_version": "report-ir-v0-result-index-2",
        "route": route,
        "case_id": workspace_manifest.get("case_id"),
        "pair_id": workspace_manifest.get("pair_id"),
        "case_spec_sha256": workspace_manifest.get("case_spec_sha256"),
        "files": {
            path.relative_to(workspace).as_posix(): sha256_file(path)
            for path in files
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(workspace).as_posix())
        archive.writestr(
            "result-index.json",
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("route", choices=ROUTES)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        output = package(args.route, args.workspace, args.output)
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"RESULT_PACKAGE_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"RESULT_PACKAGE_OK {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
