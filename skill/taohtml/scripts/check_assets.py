#!/usr/bin/env python3
"""Check an HTML deck for non-portable or missing local assets."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


ATTR_RE = re.compile(
    r"""(src|href|poster|data-source)\s*=\s*["']([^"']+)["']""",
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
    refs = {value for _, value in ATTR_RE.findall(text)} | set(CSS_URL_RE.findall(text))
    refs.update(extract_srcset_refs(text))
    return refs


def extract_srcset_refs(text: str) -> set[str]:
    refs: set[str] = set()
    for srcset in SRCSET_RE.findall(text):
        if srcset.strip().startswith("data:"):
            continue
        for candidate in srcset.split(","):
            value = candidate.strip().split(maxsplit=1)[0]
            if value:
                refs.add(value)
    return refs


def extract_resource_refs(text: str) -> set[str]:
    refs = {
        value
        for attribute, value in ATTR_RE.findall(text)
        if attribute.lower() != "href"
    }
    refs.update(CSS_URL_RE.findall(text))
    refs.update(extract_srcset_refs(text))
    return refs


def main() -> int:
    parser = argparse.ArgumentParser(description="Check asset paths in an HTML deck.")
    parser.add_argument("html", type=Path, help="HTML file to inspect.")
    parser.add_argument(
        "--strict-offline",
        action="store_true",
        help="Fail when HTTP or HTTPS assets are present.",
    )
    args = parser.parse_args()

    text = args.html.read_text(encoding="utf-8")
    base = args.html.parent
    refs = extract_refs(text)
    resource_refs = extract_resource_refs(text)
    missing: list[str] = []
    absolute: list[str] = []
    remote: list[str] = []
    remote_links: list[str] = []

    for raw in sorted(refs):
        value = raw.strip()
        if not value or value.startswith("--"):
            continue
        if is_remote(value):
            if value.startswith(("http://", "https://")):
                if raw in resource_refs:
                    remote.append(value)
                else:
                    remote_links.append(value)
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
    if remote_links:
        print("REMOTE_LINKS")
        for item in remote_links:
            print(f"  {item}")

    if absolute or missing or (args.strict_offline and remote):
        return 1
    print("ASSET_CHECK_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
