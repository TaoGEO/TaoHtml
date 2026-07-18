#!/usr/bin/env python3
"""Prepare one judge-free Report IR v0 executor workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any


EVAL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = EVAL_ROOT.parents[1]
EXECUTOR_ROOT = EVAL_ROOT / "executor"
CASES_ROOT = EXECUTOR_ROOT / "cases"
ROUTES = ("direct", "ir")
WORKSPACE_VERSION = "report-ir-v0-executor-3"
DEFAULT_CASE = "case-a"
DEFAULT_PAIR_ID = "local-pair"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_case(case_id: str) -> tuple[dict[str, Any], Path, Path]:
    """Resolve one benchmark case without letting executor prompts choose inputs."""

    case_root = CASES_ROOT / case_id
    spec_path = case_root / "case-spec.json"
    if not spec_path.is_file():
        raise ValueError(f"unknown benchmark case: {case_id}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict) or spec.get("case_id") != case_id:
        raise ValueError(f"invalid case spec for {case_id}")
    required = {
        "case_spec_version",
        "case_id",
        "expected_report_id",
        "slide_count",
        "required_text",
        "disclosure_text",
        "required_minimum_disclosures",
        "forbidden_text",
    }
    missing = sorted(required - set(spec))
    if missing:
        raise ValueError(f"case spec missing fields: {', '.join(missing)}")
    if not isinstance(spec["slide_count"], int) or spec["slide_count"] <= 0:
        raise ValueError("case spec slide_count must be a positive integer")
    for field in ("required_text", "disclosure_text", "forbidden_text"):
        if not isinstance(spec[field], list) or not all(
            isinstance(item, str) and item for item in spec[field]
        ):
            raise ValueError(f"case spec {field} must be an array of non-empty strings")
    if not isinstance(spec["required_minimum_disclosures"], int):
        raise ValueError("case spec required_minimum_disclosures must be an integer")

    if case_id == "case-a":
        design_brief = EXECUTOR_ROOT / "input" / "design-brief.md"
        evidence = (
            REPOSITORY_ROOT
            / "evals"
            / "taohtml-quality-v1"
            / "fixtures"
            / "visual-systems-evidence.svg"
        )
    else:
        design_brief = case_root / "design-brief.md"
        evidence = case_root / "evidence.svg"
    if not design_brief.is_file() or not evidence.is_file():
        raise ValueError(f"case {case_id} is missing design brief or evidence")
    return spec, design_brief, evidence


def safe_identifier(value: str, label: str) -> str:
    if not value or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in value):
        raise ValueError(f"{label} may contain only letters, numbers, dash, and underscore")
    return value


def result_archive_name(route: str, case_id: str, pair_id: str) -> str:
    return f"workbuddy-{route}-{case_id}-{pair_id}-result.zip"


def immutable_file_hashes(workspace: Path) -> dict[str, str]:
    """Hash executor inputs while excluding files the task is allowed to create."""

    mutable_roots = {"deliverable"}
    mutable_files = {
        "report-ir.json",
        "run-metadata.json",
        "workbuddy-direct-result.zip",
        "workbuddy-ir-result.zip",
    }
    result: dict[str, str] = {}
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(workspace).as_posix()
        if relative in mutable_files or relative.split("/", 1)[0] in mutable_roots:
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        result[relative] = sha256_file(path)
    return result


def write_controller_receipt(route: str, workspace: Path, receipt_path: Path) -> Path:
    workspace = workspace.resolve()
    receipt_path = receipt_path.resolve()
    try:
        receipt_path.relative_to(workspace)
    except ValueError:
        pass
    else:
        raise ValueError("controller receipt must remain outside the executor workspace")
    files = immutable_file_hashes(workspace)
    manifest = json.loads((workspace / "workspace-manifest.json").read_text(encoding="utf-8"))
    canonical = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    receipt = {
        "receipt_version": "report-ir-v0-controller-receipt-1",
        "route": route,
        "workspace_version": WORKSPACE_VERSION,
        "case_id": manifest["case_id"],
        "pair_id": manifest["pair_id"],
        "case_spec_sha256": files["input/case-spec.json"],
        "immutable_files": files,
        "immutable_tree_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return receipt_path


def prepare(
    route: str,
    destination: Path,
    case_id: str = DEFAULT_CASE,
    pair_id: str = DEFAULT_PAIR_ID,
) -> Path:
    if route not in ROUTES:
        raise ValueError(f"unknown route: {route}")
    case_id = safe_identifier(case_id, "case_id")
    pair_id = safe_identifier(pair_id, "pair_id")
    case_spec, design_brief, evidence = load_case(case_id)
    expected_archive = result_archive_name(route, case_id, pair_id)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"destination is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "input" / "materials").mkdir(parents=True)
    (destination / "deliverable").mkdir()

    prompt = (EXECUTOR_ROOT / "routes" / route / "prompt.md").read_text(encoding="utf-8")
    replacements = {
        "{{CASE_ID}}": case_id,
        "{{PAIR_ID}}": pair_id,
        "{{EXPECTED_REPORT_ID}}": case_spec["expected_report_id"],
        "{{RESULT_ARCHIVE}}": expected_archive,
    }
    for marker, value in replacements.items():
        prompt = prompt.replace(marker, value)
    if "{{" in prompt or "}}" in prompt:
        raise ValueError("executor prompt contains an unresolved template marker")
    (destination / "input" / "prompt.md").write_text(prompt, encoding="utf-8")
    shutil.copy2(design_brief, destination / "input" / "design-brief.md")
    (destination / "input" / "case-spec.json").write_text(
        json.dumps(case_spec, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    metadata = json.loads(
        (EXECUTOR_ROOT / "input" / "run-metadata-template.json").read_text(encoding="utf-8")
    )
    metadata.update(
        {
            "route": route,
            "client": "workbuddy",
            "agent": "workbuddy",
            "model": "auto",
            "skill_version": (REPOSITORY_ROOT / "VERSION").read_text(encoding="utf-8").strip(),
            "case_id": case_id,
            "pair_id": pair_id,
        }
    )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    metadata["skill_commit"] = commit.stdout.strip() if commit.returncode == 0 else "unavailable"
    (destination / "run-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(evidence, destination / "input" / "materials" / "evidence.svg")
    shutil.copytree(
        REPOSITORY_ROOT / "skill" / "taohtml",
        destination / "skill" / "taohtml",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )

    (destination / "tools").mkdir()
    shutil.copy2(
        Path(__file__).with_name("package_result.py"),
        destination / "tools" / "package_result.py",
    )

    if route == "ir":
        shutil.copy2(
            EXECUTOR_ROOT / "input" / "report-ir-contract.md",
            destination / "input" / "report-ir-contract.md",
        )
        shutil.copy2(Path(__file__).with_name("report_ir_adapter.py"), destination / "tools" / "report_ir_adapter.py")

    manifest = {
        "workspace_version": WORKSPACE_VERSION,
        "route": route,
        "case_id": case_id,
        "pair_id": pair_id,
        "expected_report_id": case_spec["expected_report_id"],
        "controller_data_included": False,
        "prompt": "input/prompt.md",
        "design_brief": "input/design-brief.md",
        "case_spec": "input/case-spec.json",
        "case_spec_sha256": sha256_file(destination / "input" / "case-spec.json"),
        "material": "input/materials/evidence.svg",
        "expected_entrypoint": "deliverable/index.html",
        "expected_handoff": "deliverable/handoff.md",
        "run_metadata": "run-metadata.json",
        "result_packager": "tools/package_result.py",
        "expected_result_archive": expected_archive,
        "controller_integrity_receipt_included": False,
    }
    (destination / "workspace-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination


def make_zip(workspace: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(workspace.rglob("*")):
            if (
                path.is_file()
                and path.resolve() != output.resolve()
                and "__pycache__" not in path.parts
                and path.suffix != ".pyc"
            ):
                archive.write(path, path.relative_to(workspace))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("route", choices=ROUTES)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--case", dest="case_id", default=DEFAULT_CASE)
    parser.add_argument("--pair-id", default=DEFAULT_PAIR_ID)
    parser.add_argument("--zip", dest="zip_path", type=Path)
    parser.add_argument("--receipt", dest="receipt_path", type=Path)
    args = parser.parse_args()
    try:
        workspace = prepare(
            args.route,
            args.destination.resolve(),
            case_id=args.case_id,
            pair_id=args.pair_id,
        )
        archive = make_zip(workspace, args.zip_path.resolve()) if args.zip_path else None
        receipt = (
            write_controller_receipt(args.route, workspace, args.receipt_path)
            if args.receipt_path
            else None
        )
    except (FileExistsError, FileNotFoundError, OSError, ValueError) as exc:
        print(f"PREPARE_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"PREPARE_OK {workspace}")
    print(f"PROMPT {workspace / 'input' / 'prompt.md'}")
    if archive:
        print(f"ZIP_OK {archive}")
    if receipt:
        print(f"CONTROLLER_RECEIPT {receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
