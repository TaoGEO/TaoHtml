#!/usr/bin/env python3
"""Run controller-owned browser QA for one returned Profile release artifact."""

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
    safe_relative_path,
    safe_extract_zip,
    sha256_file,
    utc_now,
    write_json,
)
from profile_release_contract import (
    RECEIPT_VERSION,
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


def run_browser_qa(
    *,
    receipt_path: Path,
    returned_root: Path,
    output_dir: Path,
) -> dict[str, object]:
    receipt = load_json(receipt_path)
    if receipt.get("receipt_version") != RECEIPT_VERSION:
        raise ContractError("Profile release receipt version mismatch")
    scenario_by_id(receipt.get("scenario_id", ""))
    run_path = resolve_regular_file(returned_root, "run.json", "returned run manifest")
    run = load_json(run_path)
    for key in ("run_id", "nonce", "scenario_id", "output_directory"):
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
    if output_dir.exists():
        raise ContractError(f"browser QA output already exists: {output_dir}")
    completed = subprocess.run(
        [sys.executable, str(CHECK_HTML_DECK), str(html_path), str(output_dir)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    report_path = output_dir / "qa-report.json"
    screenshots = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.glob("page-*.png"))
        if path.is_file()
    }
    success_marker = "HTML_DECK_QA_OK" if "HTML_DECK_QA_OK" in completed.stdout else None
    passed = (
        completed.returncode == 0
        and success_marker == "HTML_DECK_QA_OK"
        and report_path.is_file()
        and bool(screenshots)
    )
    return {
        "review_contract_version": "taohtml-profile-release-browser-review-1",
        "scenario_id": receipt["scenario_id"],
        "run_id": receipt["run_id"],
        "html_sha256": sha256_file(html_path),
        "status": "PASS" if passed else "FAIL",
        "tool": "taohtml-check-html-deck",
        "executed_at": utc_now(),
        "process_exit_code": completed.returncode,
        "qa_stdout_marker": success_marker,
        "qa_report_sha256": sha256_file(report_path) if report_path.is_file() else None,
        "screenshots_sha256": screenshots,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--returned", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
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
            assert_controller_owned_path(receipt_path, root, "controller receipt")
            assert_controller_owned_path(
                args.output_dir, root, "browser QA output"
            )
            assert_controller_owned_path(
                args.record, root, "browser review record"
            )
            if args.record.resolve().parent != receipt_path.parent:
                raise ContractError(
                    "browser review record must be written beside receipt.json"
                )
            record = run_browser_qa(
                receipt_path=receipt_path,
                returned_root=root,
                output_dir=args.output_dir.resolve(),
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
