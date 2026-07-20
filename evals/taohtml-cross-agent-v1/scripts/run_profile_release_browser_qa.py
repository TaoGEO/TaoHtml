#!/usr/bin/env python3
"""Run controller-owned three-viewport browser QA for one Profile release run."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from blackbox_contract import (
    ContractError,
    load_json,
    normalize_returned_root,
    resolve_regular_file,
    safe_extract_zip,
    safe_relative_path,
    sha256_file,
    utc_now,
    write_json,
)
from profile_release_contract import (
    BROWSER_REVIEW_CONTRACT_VERSION,
    PRODUCTION_CHECK_RECORD_VERSION,
    RECEIPT_VERSION,
    REQUIRED_VIEWPORTS,
    assert_controller_owned_path,
    scenario_by_id,
)


CHECK_HTML_DECK = (
    Path(__file__).resolve().parents[3]
    / "skill"
    / "taohtml"
    / "scripts"
    / "check_html_deck.py"
)


def _relative_to_controller(path: Path, controller_root: Path, label: str) -> str:
    try:
        return path.resolve().relative_to(controller_root.resolve()).as_posix()
    except ValueError as exc:
        raise ContractError(f"{label} must stay under the controller run root") from exc


def _validate_browser_authorization(record_path: Path, html_sha256: str) -> None:
    record = load_json(record_path)
    if record.get("record_contract_version") != PRODUCTION_CHECK_RECORD_VERSION:
        raise ContractError("browser-qa production check record version mismatch")
    if record.get("action") != "browser-qa" or record.get("process_exit_code") != 0:
        raise ContractError("browser-qa production check did not succeed")
    result = record.get("checker_result")
    if (
        not isinstance(result, dict)
        or result.get("requested_action") != {"name": "browser-qa", "allowed": True}
    ):
        raise ContractError("browser-qa production check is not an allowed checker result")
    if record.get("html_observation") != {
        "path": "build/index.html",
        "state": "present",
        "sha256": html_sha256,
    }:
        raise ContractError("browser-qa production check is not bound to the current HTML")


def run_browser_qa(
    *,
    receipt_path: Path,
    returned_root: Path,
    output_dir: Path,
    production_check_path: Path,
) -> dict[str, object]:
    receipt = load_json(receipt_path)
    if receipt.get("receipt_version") != RECEIPT_VERSION:
        raise ContractError("Profile release receipt version mismatch")
    scenario_by_id(receipt.get("scenario_id", ""))
    run_path = resolve_regular_file(returned_root, "run.json", "returned run manifest")
    run = load_json(run_path)
    for key in ("run_id", "nonce", "case_id", "output_directory"):
        if run.get(key) != receipt.get(key):
            raise ContractError(f"returned run manifest {key} mismatch")
    if sha256_file(run_path) != receipt.get("run_manifest_sha256"):
        raise ContractError("returned run manifest hash mismatch")
    output_relative = safe_relative_path(
        receipt["output_directory"], "receipt output_directory"
    )
    output_root = returned_root.joinpath(*output_relative.parts)
    html_path = resolve_regular_file(
        output_root, "build/index.html", "current Profile release HTML"
    )
    html_sha256 = sha256_file(html_path)
    _validate_browser_authorization(production_check_path, html_sha256)
    controller_root = receipt_path.parent
    _relative_to_controller(output_dir, controller_root, "browser QA output")
    if output_dir.exists():
        raise ContractError(f"browser QA output already exists: {output_dir}")
    viewport_records: list[dict[str, object]] = []
    passed = True
    for width, height in REQUIRED_VIEWPORTS:
        viewport_id = f"{width}x{height}"
        viewport_dir = output_dir / viewport_id
        completed = subprocess.run(
            [
                sys.executable,
                str(CHECK_HTML_DECK),
                str(html_path),
                str(viewport_dir),
                "--width",
                str(width),
                "--height",
                str(height),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        report_path = viewport_dir / "qa-report.json"
        screenshots = {
            _relative_to_controller(path, controller_root, "browser screenshot"): sha256_file(path)
            for path in sorted(viewport_dir.glob("page-*.png"))
            if path.is_file()
        }
        success_marker = (
            "HTML_DECK_QA_OK" if "HTML_DECK_QA_OK" in completed.stdout else None
        )
        viewport_passed = (
            completed.returncode == 0
            and success_marker == "HTML_DECK_QA_OK"
            and report_path.is_file()
            and bool(screenshots)
        )
        passed = passed and viewport_passed
        viewport_records.append(
            {
                "viewport_id": viewport_id,
                "width": width,
                "height": height,
                "html_sha256": html_sha256,
                "process_exit_code": completed.returncode,
                "qa_stdout_marker": success_marker,
                "report_path": _relative_to_controller(
                    report_path, controller_root, "browser QA report"
                ),
                "report_sha256": sha256_file(report_path) if report_path.is_file() else None,
                "screenshots_sha256": screenshots,
            }
        )
    return {
        "review_contract_version": BROWSER_REVIEW_CONTRACT_VERSION,
        "scenario_id": receipt["scenario_id"],
        "run_id": receipt["run_id"],
        "html_sha256": html_sha256,
        "status": "PASS" if passed else "FAIL",
        "tool": "taohtml-check-html-deck",
        "executed_at": utc_now(),
        "viewports": viewport_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--returned", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--production-check", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.record.exists():
            raise ContractError(f"browser review record already exists: {args.record}")
        returned = args.returned.resolve()
        with tempfile.TemporaryDirectory(prefix="taohtml-profile-browser-") as raw:
            if returned.is_file():
                root = safe_extract_zip(returned, Path(raw) / "returned")
            elif returned.is_dir():
                root = normalize_returned_root(returned)
            else:
                raise ContractError("returned artifact must be a ZIP or directory")
            receipt_path = args.receipt.resolve()
            controller_root = receipt_path.parent
            assert_controller_owned_path(receipt_path, root, "controller receipt")
            assert_controller_owned_path(args.output_dir, root, "browser QA output")
            assert_controller_owned_path(args.production_check, root, "production check record")
            assert_controller_owned_path(args.record, root, "browser review record")
            if args.record.resolve() != controller_root / "browser-review.json":
                raise ContractError("browser review record must be controller/browser-review.json")
            if args.production_check.resolve() != controller_root / "production-checks" / "browser-qa.json":
                raise ContractError("browser QA requires the controller browser-qa checker record")
            record = run_browser_qa(
                receipt_path=receipt_path,
                returned_root=root,
                output_dir=args.output_dir.resolve(),
                production_check_path=args.production_check.resolve(),
            )
        write_json(args.record, record)
    except (ContractError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"PROFILE_RELEASE_BROWSER_QA_FAILED {exc}", file=sys.stderr)
        return 2
    print(
        f"PROFILE_RELEASE_BROWSER_QA {record['status']} "
        f"scenario={record['scenario_id']} record={args.record}"
    )
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
