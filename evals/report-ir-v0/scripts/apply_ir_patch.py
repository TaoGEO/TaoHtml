#!/usr/bin/env python3
"""Apply one stable-id text patch to a Report IR v0 research fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        ir = load_object(args.ir)
        patch = load_object(args.patch)
        if set(patch) != {"patch_version", "operation", "target_ref", "value"}:
            raise ValueError("patch must contain exactly patch_version, operation, target_ref, value")
        if patch["patch_version"] != "research-v0":
            raise ValueError("unsupported patch_version")
        if patch["operation"] != "replace_block_content":
            raise ValueError("unsupported patch operation")
        target = patch["target_ref"]
        value = patch["value"]
        if not isinstance(target, str) or target not in ir.get("blocks", {}):
            raise ValueError(f"unknown block target: {target!r}")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("patch value must be non-empty text")
        before = ir["blocks"][target]["content"]
        ir["blocks"][target]["content"] = value
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(ir, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"IR_PATCH_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"IR_PATCH_OK {args.output.resolve()}")
    print(f"TARGET {target}")
    print(f"BEFORE {before}")
    print(f"AFTER {value}")
    print(f"PATCH_SHA256 {hashlib.sha256(canonical_bytes(patch)).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
