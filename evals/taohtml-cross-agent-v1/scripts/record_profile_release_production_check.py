#!/usr/bin/env python3
"""Run the current Production Authorization checker and retain controller evidence."""

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
    write_json,
)
from profile_release_contract import (
    PRODUCTION_ACTIONS,
    PRODUCTION_CHECK_RECORD_VERSION,
    RECEIPT_VERSION,
    assert_controller_owned_path,
    scenario_by_id,
)


PRODUCTION_CHECKER = (
    Path(__file__).resolve().parents[3]
    / "skill"
    / "taohtml"
    / "scripts"
    / "check_production_authorization.py"
)
CHECKER_REF = "skill/taohtml/scripts/check_production_authorization.py"


def _returned_output_root(receipt: dict[str, object], returned_root: Path) -> Path:
    run_path = resolve_regular_file(returned_root, "run.json", "returned run manifest")
    run = load_json(run_path)
    for key in ("run_id", "nonce", "case_id", "output_directory"):
        if run.get(key) != receipt.get(key):
            raise ContractError(f"returned run manifest {key} mismatch")
    if sha256_file(run_path) != receipt.get("run_manifest_sha256"):
        raise ContractError("returned run manifest hash mismatch")
    output_relative = safe_relative_path(
        str(receipt["output_directory"]), "receipt output_directory"
    )
    output_root = returned_root.joinpath(*output_relative.parts)
    if not output_root.is_dir() or output_root.is_symlink():
        raise ContractError("unique Profile release output directory is missing")
    return output_root


def capture_production_check(
    *,
    receipt_path: Path,
    returned_root: Path,
    action: str,
) -> dict[str, object]:
    if action not in PRODUCTION_ACTIONS:
        raise ContractError(f"unsupported production check action: {action}")
    receipt = load_json(receipt_path)
    if receipt.get("receipt_version") != RECEIPT_VERSION:
        raise ContractError("Profile release receipt version mismatch")
    scenario_by_id(receipt.get("scenario_id", ""))
    output_root = _returned_output_root(receipt, returned_root)
    state_path = resolve_regular_file(
        output_root, "gates/production-state.json", "current production state"
    )
    brief_path = resolve_regular_file(
        output_root, "design-brief.md", "current Report Design Brief"
    )
    html_path = output_root / "build" / "index.html"
    controller_root = receipt_path.parent
    browser_review_path = controller_root / "browser-review.json"
    if action == "formal-html":
        if html_path.exists():
            raise ContractError(
                "formal-html check must be captured before build/index.html exists"
            )
        html_observation = {
            "path": "build/index.html",
            "state": "absent",
            "sha256": None,
        }
        browser_review_observation = None
    else:
        current_html = resolve_regular_file(
            output_root, "build/index.html", "current Profile release HTML"
        )
        html_observation = {
            "path": "build/index.html",
            "state": "present",
            "sha256": sha256_file(current_html),
        }
        if action == "browser-qa":
            if browser_review_path.exists() or (controller_root / "browser-qa").exists():
                raise ContractError(
                    "browser-qa check must be captured before controller browser QA exists"
                )
            browser_review_observation = None
        else:
            browser_review = load_json(
                resolve_regular_file(
                    controller_root,
                    "browser-review.json",
                    "controller browser review before delivery",
                )
            )
            if (
                browser_review.get("status") != "PASS"
                or browser_review.get("html_sha256") != html_observation["sha256"]
            ):
                raise ContractError(
                    "deliver-formal-html check requires PASS browser QA for current HTML"
                )
            browser_review_observation = {
                "path": "browser-review.json",
                "sha256": sha256_file(browser_review_path),
                "html_sha256": browser_review["html_sha256"],
                "status": "PASS",
            }
    completed = subprocess.run(
        [
            sys.executable,
            str(PRODUCTION_CHECKER),
            "--state",
            str(state_path),
            "--artifact-root",
            str(output_root),
            "--action",
            action,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        checker_result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ContractError("Production Authorization checker did not return JSON") from exc
    return {
        "record_contract_version": PRODUCTION_CHECK_RECORD_VERSION,
        "run_id": receipt["run_id"],
        "scenario_id": receipt["scenario_id"],
        "action": action,
        "checker_path": CHECKER_REF,
        "checker_sha256": sha256_file(PRODUCTION_CHECKER),
        "production_state_path": "gates/production-state.json",
        "production_state_sha256": sha256_file(state_path),
        "design_brief_path": "design-brief.md",
        "design_brief_sha256": sha256_file(brief_path),
        "html_observation": html_observation,
        "browser_review_observation": browser_review_observation,
        "process_exit_code": completed.returncode,
        "checker_result": checker_result,
        "stderr": completed.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--returned", type=Path, required=True)
    parser.add_argument("--action", choices=PRODUCTION_ACTIONS, required=True)
    args = parser.parse_args()
    try:
        receipt_path = args.receipt.resolve()
        returned = args.returned.resolve()
        expected_record = (
            receipt_path.parent / "production-checks" / f"{args.action}.json"
        )
        if expected_record.exists():
            raise ContractError(f"production check record already exists: {expected_record}")
        with tempfile.TemporaryDirectory(prefix="taohtml-profile-production-") as raw:
            if returned.is_file():
                root = safe_extract_zip(returned, Path(raw) / "returned")
            elif returned.is_dir():
                root = normalize_returned_root(returned)
            else:
                raise ContractError("returned artifact must be a ZIP or directory")
            assert_controller_owned_path(receipt_path, root, "controller receipt")
            assert_controller_owned_path(expected_record, root, "production check record")
            record = capture_production_check(
                receipt_path=receipt_path,
                returned_root=root,
                action=args.action,
            )
        write_json(expected_record, record)
    except (ContractError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"PROFILE_RELEASE_PRODUCTION_CHECK_FAILED {exc}", file=sys.stderr)
        return 2
    print(
        f"PROFILE_RELEASE_PRODUCTION_CHECK action={args.action} "
        f"allowed={record['checker_result'].get('requested_action', {}).get('allowed')} "
        f"record={expected_record}"
    )
    return 0 if record["process_exit_code"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
