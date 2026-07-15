#!/usr/bin/env python3
"""Aggregate repeated TaoHtml benchmark result files without model calls."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable


DEFAULT_GROUP_FIELDS = (
    "scenario_id",
    "client",
    "agent",
    "model",
    "skill.version",
    "skill.commit",
)


def nested_value(data: dict[str, Any], dotted: str) -> Any:
    value: Any = data
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return "unavailable"
        value = value.get(part, "unavailable")
    return value


def numeric_stats(values: Iterable[float | int]) -> dict[str, Any]:
    collected = list(values)
    if not collected:
        return {"count": 0, "median": None, "range": None}
    return {
        "count": len(collected),
        "median": statistics.median(collected),
        "range": [min(collected), max(collected)],
    }


def availability_stats(results: list[dict[str, Any]], field: str) -> dict[str, Any]:
    exact = sum(
        item.get("run", {}).get(field, {}).get("availability") == "exact"
        for item in results
    )
    total = len(results)
    return {
        "exact_count": exact,
        "unavailable_count": total - exact,
        "availability_rate": round(exact / total, 4) if total else None,
    }


def exact_usage_values(
    results: list[dict[str, Any]], field: str, value_key: str
) -> Iterable[float | int]:
    for item in results:
        usage = item.get("run", {}).get(field, {})
        value = usage.get(value_key)
        if (
            usage.get("availability") == "exact"
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            yield value


def validate_result(result: dict[str, Any], path: Path) -> None:
    for key in ("schema_version", "run", "objective", "human", "comparison", "failure_samples"):
        if key not in result:
            raise ValueError(f"{path}: missing {key}")
    if result["schema_version"] != "1.0":
        raise ValueError(f"{path}: unsupported schema_version")
    run = result.get("run")
    if not isinstance(run, dict):
        raise ValueError(f"{path}: run must be an object")
    for field in ("token_usage", "billing_usage"):
        usage = run.get(field)
        if not isinstance(usage, dict) or usage.get("availability") not in {
            "exact",
            "unavailable",
        }:
            raise ValueError(f"{path}: invalid or missing run.{field}")


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    comparable = [item for item in results if item["comparison"].get("comparable")]
    successful = [item for item in comparable if item["comparison"].get("benchmark_success")]
    dimensions = sorted(
        {
            key
            for item in results
            for key in item.get("human", {}).get("dimensions", {})
        }
    )
    human_stats = {
        key: numeric_stats(
            score
            for item in results
            for score in [item.get("human", {}).get("dimensions", {}).get(key, {}).get("score")]
            if isinstance(score, (int, float))
        )
        for key in dimensions
    }
    revision_values = [
        item.get("human", {}).get("manual_revision_count") for item in results
    ]
    reference_floor_distribution: dict[str, int] = {}
    for item in results:
        status = (
            item.get("human", {})
            .get("reference_floor", {})
            .get("status", "unavailable")
        )
        reference_floor_distribution[status] = reference_floor_distribution.get(status, 0) + 1
    return {
        "run_count": len(results),
        "comparable_run_count": len(comparable),
        "unavailable_run_count": len(results) - len(comparable),
        "successful_run_count": len(successful),
        "success_rate": round(len(successful) / len(comparable), 4) if comparable else None,
        "question_count": numeric_stats(item["run"]["question_count"] for item in results),
        "usage_availability": {
            "tokens": availability_stats(results, "token_usage"),
            "workbuddy_points": availability_stats(results, "billing_usage"),
        },
        "total_tokens": numeric_stats(
            exact_usage_values(results, "token_usage", "total_tokens")
        ),
        "workbuddy_points": numeric_stats(
            exact_usage_values(results, "billing_usage", "workbuddy_points")
        ),
        "hard_failure_count": {
            "total": sum(item["objective"]["hard_failure_count"] for item in results),
            "per_run": numeric_stats(item["objective"]["hard_failure_count"] for item in results),
        },
        "human_dimensions": human_stats,
        "manual_revision_count": numeric_stats(
            value for value in revision_values if isinstance(value, (int, float))
        ),
        "reference_floor_distribution": dict(sorted(reference_floor_distribution.items())),
    }


def aggregate(
    results: list[dict[str, Any]], group_fields: tuple[str, ...] = DEFAULT_GROUP_FIELDS
) -> dict[str, Any]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for item in results:
        key = tuple(str(nested_value(item["run"], field)) for field in group_fields)
        grouped.setdefault(key, []).append(item)
    groups = []
    for key, group_results in sorted(grouped.items()):
        groups.append(
            {
                "key": dict(zip(group_fields, key, strict=True)),
                "metrics": summarize(group_results),
            }
        )
    return {
        "definition": {
            "success": "all required objective checks available and zero hard failures",
            "visual_scores": "reported by dimension only; never a production permission score",
            "usage": "availability rates use all runs; unavailable values are excluded from numeric statistics and never treated as zero",
        },
        "overall": summarize(results),
        "groups": groups,
    }


def discover(paths: list[Path]) -> list[Path]:
    discovered: set[Path] = set()
    for path in paths:
        if path.is_dir():
            discovered.update(path.rglob("result.json"))
            discovered.update(path.rglob("*-result.json"))
        elif path.is_file():
            discovered.add(path)
    return sorted(discovered)


def render_markdown(report: dict[str, Any]) -> str:
    overall = report["overall"]
    success_rate = (
        "unavailable"
        if overall["success_rate"] is None
        else f"{overall['success_rate'] * 100:.1f}%"
    )
    token_availability = overall["usage_availability"]["tokens"]
    points_availability = overall["usage_availability"]["workbuddy_points"]
    token_rate = (
        "unavailable"
        if token_availability["availability_rate"] is None
        else f"{token_availability['availability_rate'] * 100:.1f}%"
    )
    points_rate = (
        "unavailable"
        if points_availability["availability_rate"] is None
        else f"{points_availability['availability_rate'] * 100:.1f}%"
    )
    lines = [
        "# TaoHtml quality benchmark summary",
        "",
        f"- Runs: {overall['run_count']} ({overall['comparable_run_count']} comparable)",
        f"- Success rate: {success_rate}",
        f"- Hard failures: {overall['hard_failure_count']['total']}",
        f"- Question count median/range: {overall['question_count']['median']} / {overall['question_count']['range']}",
        f"- Token availability: {token_rate} ({token_availability['exact_count']}/{overall['run_count']})",
        f"- Total tokens median/range: {overall['total_tokens']['median']} / {overall['total_tokens']['range']}",
        f"- WorkBuddy points availability: {points_rate} ({points_availability['exact_count']}/{overall['run_count']})",
        f"- WorkBuddy points median/range: {overall['workbuddy_points']['median']} / {overall['workbuddy_points']['range']}",
        f"- Manual revisions median/range: {overall['manual_revision_count']['median']} / {overall['manual_revision_count']['range']}",
        f"- Prior 9-page visual floor: {overall['reference_floor_distribution']}",
        "",
        "## Human dimensions",
        "",
        "| Dimension | n | Median | Range |",
        "|---|---:|---:|---:|",
    ]
    for key, stats in overall["human_dimensions"].items():
        lines.append(f"| {key} | {stats['count']} | {stats['median']} | {stats['range']} |")
    lines.extend(["", "## Comparison groups", ""])
    for group in report["groups"]:
        label = ", ".join(f"{key}={value}" for key, value in group["key"].items())
        metrics = group["metrics"]
        rate = "unavailable" if metrics["success_rate"] is None else f"{metrics['success_rate'] * 100:.1f}%"
        group_token_rate = metrics["usage_availability"]["tokens"]["availability_rate"]
        group_points_rate = metrics["usage_availability"]["workbuddy_points"]["availability_rate"]
        lines.append(
            f"- {label}: runs={metrics['run_count']}, success={rate}, "
            f"hard_failures={metrics['hard_failure_count']['total']}, "
            f"token_availability={group_token_rate}, "
            f"workbuddy_points_availability={group_points_rate}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate TaoHtml benchmark JSON results.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--group-by",
        action="append",
        dest="group_fields",
        help="Run metadata field, dot notation allowed. Repeat for multiple fields.",
    )
    args = parser.parse_args()
    try:
        files = discover(args.paths)
        if not files:
            raise ValueError("No JSON result files found")
        results = []
        for path in files:
            item = json.loads(path.read_text(encoding="utf-8"))
            validate_result(item, path)
            results.append(item)
        fields = tuple(args.group_fields) if args.group_fields else DEFAULT_GROUP_FIELDS
        report = aggregate(results, fields)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"AGGREGATE_FAILED: {exc}", file=sys.stderr)
        return 2
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_markdown(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"AGGREGATE_OK {args.output}")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
