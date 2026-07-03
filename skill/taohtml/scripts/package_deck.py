#!/usr/bin/env python3
"""Zip an HTML deck folder for portable delivery."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a portable zip for an HTML deck folder.")
    parser.add_argument("deck_dir", type=Path, help="Folder containing index.html and assets.")
    parser.add_argument("zip_path", type=Path, help="Output zip path.")
    args = parser.parse_args()

    if not args.deck_dir.is_dir():
        raise SystemExit(f"Not a directory: {args.deck_dir}")
    if not (args.deck_dir / "index.html").exists():
        raise SystemExit(f"index.html not found in: {args.deck_dir}")

    args.zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(args.deck_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(args.deck_dir.parent))
    print(args.zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
