#!/usr/bin/env python3
"""Check an HTML deck for non-portable or missing local assets."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


ATTR_RE = re.compile(
    r"""(?:src|href|poster|data-source)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
SRCSET_RE = re.compile(r"""srcset\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
CSS_URL_RE = re.compile(r"""url\((?:["']?)([^"')]+)(?:["']?)\)""", re.IGNORECASE)


def is_remote(value: str) -> bool:
    parsed = urlparse(value)
    return value.startswith(("//", "#")) or parsed.scheme.lower() in {
        "blob",
        "data",
        "http",
        "https",
        "javascript",
        "mailto",
        "tel",
    }


def is_absolute_local(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme == "file":
        return True
    return bool(re.match(r"^[a-zA-Z]:[\\/]", value) or value.startswith(("/", "\\")))


def extract_refs(text: str) -> set[str]:
    refs = set(ATTR_RE.findall(text)) | set(CSS_URL_RE.findall(text))
    for srcset in SRCSET_RE.findall(text):
        if srcset.strip().startswith("data:"):
            continue
        for candidate in srcset.split(","):
            value = candidate.strip().split(maxsplit=1)[0]
            if value:
                refs.add(value)
    return refs


def main() -> int:
    parser = argparse.ArgumentParser(description="Check asset paths in an HTML deck.")
    parser.add_argument("html", type=Path, help="HTML file to inspect.")
    args = parser.parse_args()

    text = args.html.read_text(encoding="utf-8")
    base = args.html.parent
    refs = extract_refs(text)
    missing: list[str] = []
    absolute: list[str] = []
    remote: list[str] = []

    for raw in sorted(refs):
        value = raw.strip()
        if not value or value.startswith("--"):
            continue
        if is_remote(value):
            if value.startswith(("http://", "https://")):
                remote.append(value)
            continue
        if is_absolute_local(value):
            absolute.append(value)
            continue
        clean = unquote(value.split("#", 1)[0].split("?", 1)[0])
        if clean and not (base / clean).exists():
            missing.append(value)

    if absolute:
        print("ABSOLUTE_LOCAL_PATHS")
        for item in absolute:
            print(f"  {item}")
    if missing:
        print("MISSING_ASSETS")
        for item in missing:
            print(f"  {item}")
    if remote:
        print("REMOTE_ASSETS")
        for item in remote:
            print(f"  {item}")

    if absolute or missing:
        return 1
    print("ASSET_CHECK_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
