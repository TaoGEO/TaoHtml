#!/usr/bin/env python3
"""Validate TaoHtml confirmation state before previews or formal HTML production."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

SCHEMA_VERSION = "1.2"
LEGACY_SCHEMA_VERSION = "1.1"
ROUTES = {"idea_only", "word_pdf", "existing_ppt_html"}
VISUAL_ROUTES = {"unresolved", "built_in", "static_reference", "profile_reuse"}
ACTIONS = {
    "status",
    "material-summary-preview",
    "visual-route-decision",
    "reference-vi-preview",
    "project-theme-compile",
    "profile-use-bind",
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
    "profile_use",
    "project_theme_compiled",
    "design_brief",
}
GATE_KEYS = {
    "status",
    "artifact_path",
    "artifact_sha256",
    "confirmation_ref",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PROFILE_USE_KEYS = {"status", "artifact_path", "artifact_sha256"}


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _current_artifact(
    artifact_root: Path,
    value: object,
    expected_sha256: object,
    label: str,
) -> tuple[str, str]:
    relative_text = _short_text(value, f"{label}.artifact_path")
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(
            f"{label}.artifact_path must be a safe task-local relative path"
        )
    if not isinstance(expected_sha256, str) or not SHA256.fullmatch(expected_sha256):
        raise ValueError(
            f"{label}.artifact_sha256 must be a lowercase SHA-256 digest"
        )
    supplied = artifact_root / relative
    cursor = artifact_root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"{label}.artifact_path must not use symlinks")
    try:
        current = supplied.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"{label}.artifact_path does not exist: {relative_text}") from exc
    try:
        current.relative_to(artifact_root)
    except ValueError as exc:
        raise ValueError(
            f"{label}.artifact_path escapes the task artifact root: {relative_text}"
        ) from exc
    if not current.is_file():
        raise ValueError(f"{label}.artifact_path is not a file: {relative_text}")
    current_sha256 = _sha256(current)
    if current_sha256 != expected_sha256:
        raise ValueError(
            f"{label}.artifact_sha256 does not match the current file"
        )
    return relative.as_posix(), current_sha256


def _profile_use_gate(
    raw: object,
    artifact_root: Path,
) -> dict[str, Any]:
    gate = _exact_object(raw, PROFILE_USE_KEYS, "profile_use")
    status = gate["status"]
    if status not in {"not_required", "pending", "bound"}:
        raise ValueError("profile_use.status must be not_required, pending, or bound")
    artifact_path = _optional_text(gate["artifact_path"], "profile_use.artifact_path")
    artifact_sha256 = _optional_text(
        gate["artifact_sha256"], "profile_use.artifact_sha256"
    )
    validation_status = None
    temporary_override = None
    if status == "bound":
        import profile_store

        if artifact_path is None or artifact_sha256 is None:
            raise ValueError(
                "profile_use bound state requires artifact_path and artifact_sha256"
            )
        artifact_path, artifact_sha256 = _current_artifact(
            artifact_root,
            artifact_path,
            artifact_sha256,
            "profile_use",
        )
        current = artifact_root / artifact_path
        validated = profile_store.validate_binding(current)
        validation_status = validated["status"]
        temporary_override = bool(validated["binding"]["temporary_override"])
    elif status == "pending":
        if artifact_sha256 is not None:
            raise ValueError("profile_use pending state cannot contain artifact_sha256")
    elif artifact_path is not None or artifact_sha256 is not None:
        raise ValueError("profile_use not_required state cannot bind an artifact")
    return {
        "status": status,
        "artifact_path": artifact_path,
        "artifact_sha256": artifact_sha256,
        "validation_status": validation_status,
        "temporary_override": temporary_override,
    }


def _confirmation_gate(
    raw: object,
    label: str,
    artifact_root: Path,
    *,
    allowed_statuses: set[str],
) -> dict[str, str | None]:
    gate = _exact_object(raw, GATE_KEYS, label)
    status = gate["status"]
    if status not in allowed_statuses:
        raise ValueError(
            f"{label}.status must be one of: {', '.join(sorted(allowed_statuses))}"
        )
    artifact_path = _optional_text(gate["artifact_path"], f"{label}.artifact_path")
    artifact_sha256 = _optional_text(
        gate["artifact_sha256"], f"{label}.artifact_sha256"
    )
    confirmation_ref = _optional_text(
        gate["confirmation_ref"], f"{label}.confirmation_ref"
    )
    if status == "confirmed":
        if artifact_path is None or artifact_sha256 is None or confirmation_ref is None:
            raise ValueError(
                f"{label} confirmed state requires artifact_path, artifact_sha256, and confirmation_ref"
            )
        artifact_path, artifact_sha256 = _current_artifact(
            artifact_root,
            artifact_path,
            artifact_sha256,
            label,
        )
    elif status == "pending":
        if artifact_sha256 is not None or confirmation_ref is not None:
            raise ValueError(
                f"{label} pending state cannot contain artifact_sha256 or confirmation_ref"
            )
    elif (
        artifact_path is not None
        or artifact_sha256 is not None
        or confirmation_ref is not None
    ):
        raise ValueError(f"{label} not_required state cannot bind an artifact or confirmation")
    return {
        "status": status,
        "artifact_path": artifact_path,
        "artifact_sha256": artifact_sha256,
        "confirmation_ref": confirmation_ref,
    }


def validate_state(raw: object, artifact_root: Path) -> dict[str, Any]:
    try:
        resolved_artifact_root = artifact_root.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"artifact_root does not exist: {artifact_root}") from exc
    if not resolved_artifact_root.is_dir():
        raise ValueError(f"artifact_root is not a directory: {resolved_artifact_root}")
    if not isinstance(raw, dict):
        raise ValueError("state must be an object")
    schema_version = raw.get("schema_version")
    if schema_version == LEGACY_SCHEMA_VERSION:
        legacy_keys = TOP_LEVEL_KEYS - {"profile_use"}
        legacy = _exact_object(raw, legacy_keys, "state")
        state = {**legacy, "schema_version": SCHEMA_VERSION}
        state["profile_use"] = {
            "status": "not_required",
            "artifact_path": None,
            "artifact_sha256": None,
        }
    else:
        state = _exact_object(raw, TOP_LEVEL_KEYS, "state")
        if schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {SCHEMA_VERSION} (or legacy {LEGACY_SCHEMA_VERSION})"
            )
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
        resolved_artifact_root,
        allowed_statuses={"not_required", "pending", "confirmed"},
    )
    reference_vi = _confirmation_gate(
        state["reference_vi"],
        "reference_vi",
        resolved_artifact_root,
        allowed_statuses={"not_required", "pending", "confirmed"},
    )
    brief = _confirmation_gate(
        state["design_brief"],
        "design_brief",
        resolved_artifact_root,
        allowed_statuses={"pending", "confirmed"},
    )
    profile_use = _profile_use_gate(state["profile_use"], resolved_artifact_root)
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
        if project_theme_compiled and visual_route not in {"profile_reuse"}:
            raise ValueError(
                "project_theme_compiled can be true only for static_reference or profile_reuse"
            )

    if visual_route == "profile_reuse":
        if profile_use["status"] == "bound" and profile_use["temporary_override"]:
            raise ValueError("profile_reuse cannot use a temporary-override binding")
    elif profile_use["status"] == "pending":
        raise ValueError("profile_use pending state is valid only for profile_reuse")
    elif profile_use["status"] == "bound" and not profile_use["temporary_override"]:
        raise ValueError(
            "A reusable profile binding requires visual_route=profile_reuse"
        )

    source_ready = not source_backed_route or material["status"] == "confirmed"
    vi_ready = (
        visual_route != "static_reference"
        or reference_vi["status"] == "confirmed"
    )
    profile_ready = (
        visual_route != "profile_reuse"
        or (
            profile_use["status"] == "bound"
            and profile_use["validation_status"] == "valid_reuse"
        )
    )
    if reference_vi["status"] == "confirmed" and not source_ready:
        raise ValueError("reference VI cannot be confirmed before source grounding")
    if project_theme_compiled and not (vi_ready and profile_ready):
        raise ValueError("project theme cannot be compiled before reference VI confirmation")
    upstream_ready = (
        source_ready
        and visual_route != "unresolved"
        and vi_ready
        and profile_ready
        and (
            visual_route not in {"static_reference", "profile_reuse"}
            or project_theme_compiled
        )
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
        "profile_use": profile_use,
        "project_theme_compiled": project_theme_compiled,
        "design_brief": brief,
        "artifact_root": str(resolved_artifact_root),
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
    profile_ready = (
        state["visual_route"] != "profile_reuse"
        or (
            state["profile_use"]["status"] == "bound"
            and state["profile_use"]["validation_status"] == "valid_reuse"
        )
    )
    theme_ready = (
        state["visual_route"] not in {"static_reference", "profile_reuse"}
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
    if visual_ready and vi_ready and not profile_ready:
        blocking_gates.append("profile_use_binding")
    if visual_ready and vi_ready and profile_ready and not theme_ready:
        blocking_gates.append("project_theme_compilation")
    if material_ready and visual_ready and vi_ready and profile_ready and theme_ready and not brief_ready:
        blocking_gates.append("design_brief_confirmation")

    allowed = {"status"}
    if not material_ready:
        allowed.add("material-summary-preview")
    else:
        if not visual_ready:
            allowed.add("visual-route-decision")
        elif not vi_ready:
            allowed.add("reference-vi-preview")
        elif not profile_ready:
            allowed.add("profile-use-bind")
        elif not theme_ready:
            allowed.add("project-theme-compile")
        elif not brief_ready:
            allowed.add("design-brief-preview")
        else:
            allowed.update({"formal-html", "browser-qa", "deliver-formal-html"})

    authorized = not blocking_gates and brief_ready
    verified_artifacts = [
        {
            "gate": name,
            "artifact_path": state[name]["artifact_path"],
            "artifact_sha256": state[name]["artifact_sha256"],
        }
        for name in ("material_summary", "reference_vi", "design_brief")
        if state[name]["status"] == "confirmed"
    ]
    if state["profile_use"]["status"] == "bound":
        verified_artifacts.append(
            {
                "gate": "profile_use",
                "artifact_path": state["profile_use"]["artifact_path"],
                "artifact_sha256": state["profile_use"]["artifact_sha256"],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": state["task_id"],
        "status": "authorized" if authorized else "blocked",
        "authorized_for_formal_html": authorized,
        "blocking_gates": blocking_gates,
        "allowed_actions": sorted(allowed),
        "verified_artifacts": verified_artifacts,
        "forbidden_formal_actions": (
            [] if authorized else ["formal-html", "browser-qa", "deliver-formal-html"]
        ),
    }


def load_state(path: Path, artifact_root: Path) -> dict[str, Any]:
    return validate_state(json.loads(path.read_text(encoding="utf-8")), artifact_root)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check TaoHtml confirmation state before a requested action."
    )
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        required=True,
        help="Task-local root containing every bound gate artifact.",
    )
    parser.add_argument("--action", choices=sorted(ACTIONS), default="status")
    args = parser.parse_args()
    try:
        result = evaluate_state(
            load_state(args.state.resolve(), args.artifact_root)
        )
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
