#!/usr/bin/env python3
"""Validate TaoHtml confirmation state before previews or formal HTML production."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
ROUTES = {"idea_only", "word_pdf", "existing_ppt_html"}
VISUAL_ROUTES = {"unresolved", "built_in", "static_reference"}
ACTIONS = {
    "status",
    "material-summary-preview",
    "visual-route-decision",
    "reference-vi-preview",
    "project-theme-compile",
    "design-brief-preview",
    "formal-html",
    "browser-qa",
    "deliver-formal-html",
}
TOP_LEVEL_KEYS = {
    "schema_version",
    "task_id",
    "route",
    "visual_route",
    "material_summary",
    "reference_vi",
    "project_theme_compiled",
    "design_brief",
}
GATE_KEYS = {"status", "artifact_id", "confirmation_ref"}


def _exact_object(raw: object, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object")
    actual = set(raw)
    if actual != keys:
        missing = ", ".join(sorted(keys - actual)) or "none"
        extra = ", ".join(sorted(actual - keys)) or "none"
        raise ValueError(f"{label} fields drifted; missing={missing}; extra={extra}")
    return raw


def _short_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 160:
        raise ValueError(f"{label} must be a non-empty string of at most 160 characters")
    return value.strip()


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _short_text(value, label)


def _confirmation_gate(
    raw: object,
    label: str,
    *,
    allowed_statuses: set[str],
) -> dict[str, str | None]:
    gate = _exact_object(raw, GATE_KEYS, label)
    status = gate["status"]
    if status not in allowed_statuses:
        raise ValueError(
            f"{label}.status must be one of: {', '.join(sorted(allowed_statuses))}"
        )
    artifact_id = _optional_text(gate["artifact_id"], f"{label}.artifact_id")
    confirmation_ref = _optional_text(
        gate["confirmation_ref"], f"{label}.confirmation_ref"
    )
    if status == "confirmed":
        if artifact_id is None or confirmation_ref is None:
            raise ValueError(
                f"{label} confirmed state requires artifact_id and confirmation_ref"
            )
    elif status == "pending":
        if confirmation_ref is not None:
            raise ValueError(f"{label} pending state cannot contain confirmation_ref")
    elif artifact_id is not None or confirmation_ref is not None:
        raise ValueError(f"{label} not_required state cannot bind an artifact or confirmation")
    return {
        "status": status,
        "artifact_id": artifact_id,
        "confirmation_ref": confirmation_ref,
    }


def validate_state(raw: object) -> dict[str, Any]:
    state = _exact_object(raw, TOP_LEVEL_KEYS, "state")
    if state["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    task_id = _short_text(state["task_id"], "task_id")
    route = state["route"]
    if route not in ROUTES:
        raise ValueError(f"route must be one of: {', '.join(sorted(ROUTES))}")
    visual_route = state["visual_route"]
    if visual_route not in VISUAL_ROUTES:
        raise ValueError(
            f"visual_route must be one of: {', '.join(sorted(VISUAL_ROUTES))}"
        )
    material = _confirmation_gate(
        state["material_summary"],
        "material_summary",
        allowed_statuses={"not_required", "pending", "confirmed"},
    )
    reference_vi = _confirmation_gate(
        state["reference_vi"],
        "reference_vi",
        allowed_statuses={"not_required", "pending", "confirmed"},
    )
    brief = _confirmation_gate(
        state["design_brief"],
        "design_brief",
        allowed_statuses={"pending", "confirmed"},
    )
    project_theme_compiled = state["project_theme_compiled"]
    if not isinstance(project_theme_compiled, bool):
        raise ValueError("project_theme_compiled must be a boolean")

    source_backed_route = route in {"word_pdf", "existing_ppt_html"}
    if source_backed_route:
        if material["status"] == "not_required":
            raise ValueError(
                f"{route} requires a pending or confirmed material summary"
            )
    elif material["status"] != "not_required":
        raise ValueError(f"{route} requires material_summary.status=not_required")

    if visual_route == "static_reference":
        if reference_vi["status"] == "not_required":
            raise ValueError(
                "static_reference requires a pending or confirmed reference VI"
            )
    else:
        if reference_vi["status"] != "not_required":
            raise ValueError(
                f"{visual_route} requires reference_vi.status=not_required"
            )
        if project_theme_compiled:
            raise ValueError(
                "project_theme_compiled can be true only for static_reference"
            )

    source_ready = not source_backed_route or material["status"] == "confirmed"
    vi_ready = (
        visual_route != "static_reference"
        or reference_vi["status"] == "confirmed"
    )
    if reference_vi["status"] == "confirmed" and not source_ready:
        raise ValueError("reference VI cannot be confirmed before source grounding")
    if project_theme_compiled and not vi_ready:
        raise ValueError("project theme cannot be compiled before reference VI confirmation")
    upstream_ready = (
        source_ready
        and visual_route != "unresolved"
        and vi_ready
        and (visual_route != "static_reference" or project_theme_compiled)
    )
    if brief["status"] == "confirmed" and not upstream_ready:
        raise ValueError(
            "design brief cannot be confirmed before all applicable upstream gates"
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "route": route,
        "visual_route": visual_route,
        "material_summary": material,
        "reference_vi": reference_vi,
        "project_theme_compiled": project_theme_compiled,
        "design_brief": brief,
    }


def evaluate_state(state: dict[str, Any]) -> dict[str, object]:
    source_backed_route = state["route"] in {"word_pdf", "existing_ppt_html"}
    material_ready = (
        not source_backed_route
        or state["material_summary"]["status"] == "confirmed"
    )
    visual_ready = state["visual_route"] != "unresolved"
    vi_ready = (
        state["visual_route"] != "static_reference"
        or state["reference_vi"]["status"] == "confirmed"
    )
    theme_ready = (
        state["visual_route"] != "static_reference"
        or state["project_theme_compiled"]
    )
    brief_ready = state["design_brief"]["status"] == "confirmed"

    blocking_gates: list[str] = []
    if not material_ready:
        blocking_gates.append("material_summary_confirmation")
    if not visual_ready:
        blocking_gates.append("visual_route_selection")
    if visual_ready and not vi_ready:
        blocking_gates.append("reference_vi_confirmation")
    if visual_ready and vi_ready and not theme_ready:
        blocking_gates.append("project_theme_compilation")
    if material_ready and visual_ready and vi_ready and theme_ready and not brief_ready:
        blocking_gates.append("design_brief_confirmation")

    allowed = {"status"}
    if not material_ready:
        allowed.add("material-summary-preview")
    else:
        if not visual_ready:
            allowed.add("visual-route-decision")
        elif not vi_ready:
            allowed.add("reference-vi-preview")
        elif not theme_ready:
            allowed.add("project-theme-compile")
        elif not brief_ready:
            allowed.add("design-brief-preview")
        else:
            allowed.update({"formal-html", "browser-qa", "deliver-formal-html"})

    authorized = not blocking_gates and brief_ready
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": state["task_id"],
        "status": "authorized" if authorized else "blocked",
        "authorized_for_formal_html": authorized,
        "blocking_gates": blocking_gates,
        "allowed_actions": sorted(allowed),
        "forbidden_formal_actions": (
            [] if authorized else ["formal-html", "browser-qa", "deliver-formal-html"]
        ),
    }


def load_state(path: Path) -> dict[str, Any]:
    return validate_state(json.loads(path.read_text(encoding="utf-8")))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check TaoHtml confirmation state before a requested action."
    )
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--action", choices=sorted(ACTIONS), default="status")
    args = parser.parse_args()
    try:
        result = evaluate_state(load_state(args.state.resolve()))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "invalid",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    allowed = args.action in result["allowed_actions"]
    result["requested_action"] = {"name": args.action, "allowed": allowed}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
