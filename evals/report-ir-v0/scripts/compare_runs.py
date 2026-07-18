#!/usr/bin/env python3
"""Compare one controller-judged Direct run with one controller-judged IR run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_result(path: Path, route: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("route") != route:
        raise ValueError(f"{path}: expected {route} judge result")
    return value


def exact_points(result: dict[str, Any]) -> float | int | None:
    recorded = result.get("usage", {}).get("recorded")
    if not isinstance(recorded, dict):
        return None
    billing = recorded.get("billing_usage")
    if not isinstance(billing, dict) or billing.get("availability") != "exact":
        return None
    points = billing.get("workbuddy_points")
    if isinstance(points, bool) or not isinstance(points, (int, float)):
        return None
    return points


def compare(direct: dict[str, Any], ir: dict[str, Any]) -> dict[str, Any]:
    direct_case = direct.get("case")
    ir_case = ir.get("case")
    pair_compatible = (
        isinstance(direct_case, dict)
        and isinstance(ir_case, dict)
        and direct_case.get("case_id") is not None
        and direct_case.get("case_id") == ir_case.get("case_id")
        and direct_case.get("pair_id") is not None
        and direct_case.get("pair_id") == ir_case.get("pair_id")
        and direct_case.get("case_spec_sha256") == ir_case.get("case_spec_sha256")
        and direct_case.get("expected_report_id") == ir_case.get("expected_report_id")
    )
    direct_points = exact_points(direct)
    ir_points = exact_points(ir)
    points: dict[str, Any]
    if direct_points is None or ir_points is None:
        points = {
            "availability": "unavailable",
            "direct": direct_points,
            "ir": ir_points,
            "interpretation": "WorkBuddy points are not model tokens; no percentage is inferred.",
        }
    else:
        difference = direct_points - ir_points
        ratio = ir_points / direct_points if direct_points else None
        reduction = difference / direct_points * 100 if direct_points else None
        points = {
            "availability": "exact",
            "unit": "workbuddy_points",
            "direct": direct_points,
            "ir": ir_points,
            "difference": difference,
            "ir_to_direct_ratio": round(ratio, 6) if ratio is not None else None,
            "reduction_percent": round(reduction, 2) if reduction is not None else None,
            "interpretation": "Platform billing points, not model tokens.",
        }
    both_pass = (
        pair_compatible
        and direct.get("status") == "PASS"
        and ir.get("status") == "PASS"
    )
    return {
        "comparison_version": "report-ir-v0-comparison-2",
        "status": "PASS" if both_pass else "FAIL",
        "pair_integrity": {
            "status": "PASS" if pair_compatible else "FAIL",
            "direct": direct_case,
            "ir": ir_case,
        },
        "routes": {
            "direct": direct.get("status"),
            "ir": ir.get("status"),
        },
        "workbuddy_points": points,
        "claim_boundary": (
            "A cost reduction claim is allowed only when both controller-judged routes PASS "
            "for the same immutable case/pair and both point values are exact."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("direct_result", type=Path)
    parser.add_argument("ir_result", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = compare(
            load_result(args.direct_result, "direct"),
            load_result(args.ir_result, "ir"),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"COMPARE_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"COMPARE_{result['status']} {args.output.resolve()}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
