#!/usr/bin/env python3
"""Evaluate the six-row smoke gate without fabricating missing platform runs."""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any

from blackbox_contract import (
    CONTROLLER_ROOT,
    RESULT_CONTRACT_VERSION,
    ContractError,
    load_json,
    utc_now,
    write_json,
)


def result_paths(inputs: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for value in inputs:
        if value.is_dir():
            paths.extend(sorted(value.rglob("result.json")))
            paths.extend(sorted(value.rglob("*-result.json")))
        elif value.is_file():
            paths.append(value)
        else:
            raise ContractError(f"result input does not exist: {value}")
    unique: dict[Path, None] = {}
    for path in paths:
        unique[path.resolve()] = None
    return list(unique)


def evaluate(inputs: list[Path]) -> dict[str, Any]:
    matrix = load_json(CONTROLLER_ROOT / "matrix.json")
    expected_rows = {
        (scenario, platform)
        for scenario, platform in itertools.product(
            matrix["smoke"]["scenarios"], matrix["platforms"]
        )
    }
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    unexpected: list[dict[str, str]] = []
    duplicates: list[dict[str, str]] = []
    for path in result_paths(inputs):
        result = load_json(path)
        if result.get("result_contract_version") != RESULT_CONTRACT_VERSION:
            raise ContractError(f"unsupported result contract: {path}")
        run = result.get("run")
        if not isinstance(run, dict):
            raise ContractError(f"result run record is invalid: {path}")
        row = (run.get("scenario_id"), run.get("target_platform"))
        if row not in expected_rows:
            unexpected.append(
                {"scenario_id": str(row[0]), "platform": str(row[1]), "path": str(path)}
            )
            continue
        if row in rows:
            duplicates.append(
                {"scenario_id": row[0], "platform": row[1], "path": str(path)}
            )
            continue
        rows[row] = result

    records: list[dict[str, Any]] = []
    for scenario, platform in sorted(expected_rows):
        result = rows.get((scenario, platform))
        if result is None:
            records.append(
                {
                    "scenario_id": scenario,
                    "platform": platform,
                    "status": "MISSING",
                    "automatic_status": None,
                    "human_status": None,
                    "run_id": None,
                }
            )
            continue
        automatic = result.get("automatic_status")
        human = result.get("human_review", {}).get("status")
        passed = automatic == "PASS" and human == "PASS"
        records.append(
            {
                "scenario_id": scenario,
                "platform": platform,
                "status": "PASS" if passed else "NOT_PASSED",
                "automatic_status": automatic,
                "human_status": human,
                "run_id": result["run"]["run_id"],
            }
        )
    smoke_pass = (
        len(records) == matrix["smoke"]["expected_run_count"]
        and all(record["status"] == "PASS" for record in records)
        and not duplicates
        and not unexpected
    )
    return {
        "matrix_result_version": "taohtml-cross-agent-matrix-result-1",
        "evaluated_at": utc_now(),
        "smoke_status": "PASS" if smoke_pass else "NOT_PASSED",
        "smoke_rows": records,
        "duplicate_rows": duplicates,
        "unexpected_rows": unexpected,
        "full_matrix": {
            "enabled": smoke_pass,
            "reason": (
                "all six smoke rows passed automatic and human acceptance"
                if smoke_pass
                else "full remains disabled until every smoke row passes"
            ),
            "expected_run_count": matrix["full"]["expected_run_count"],
            "profiles": matrix["full"]["profile_ids"],
            "platforms": matrix["platforms"],
            "scenario_fixtures_in_this_node": matrix["full"][
                "scenario_fixtures_in_this_node"
            ],
        },
        "workbuddy_results_synthesized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        print(f"MATRIX_FAILED output already exists: {args.output}", file=sys.stderr)
        return 1
    try:
        result = evaluate([path.resolve() for path in args.results])
        write_json(args.output.resolve(), result)
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"MATRIX_FAILED {exc}", file=sys.stderr)
        return 1
    print(
        f"MATRIX_RESULT smoke={result['smoke_status']} "
        f"full_enabled={str(result['full_matrix']['enabled']).lower()}"
    )
    print(args.output.resolve())
    return 0 if result["full_matrix"]["enabled"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
