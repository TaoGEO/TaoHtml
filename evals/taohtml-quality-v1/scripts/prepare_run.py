#!/usr/bin/env python3
"""Prepare an isolated TaoHtml benchmark workspace without judge-only data."""

from __future__ import annotations

import argparse
import shutil
import sys
import textwrap
from pathlib import Path


BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BENCHMARK_ROOT.parents[1]
EXECUTOR_ROOT = BENCHMARK_ROOT / "executor" / "scenarios"
SCENARIO_IDS = (
    "idea-live-conversion",
    "pdf-evidence-report",
    "existing-html-upgrade",
)


def build_pdf(source: Path, output: Path) -> None:
    """Render the small ASCII source fixture as a deterministic PDF."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - dependency failure path
        raise RuntimeError("PyMuPDF is required; install repository requirements") from exc

    sections = source.read_text(encoding="utf-8").split("\n---PAGE---\n")
    document = fitz.open()
    document.set_metadata(
        {
            "title": "Orbit Urban Pilot Review",
            "author": "TaoHtml quality benchmark v1",
            "subject": "Synthetic evaluation material",
        }
    )
    for page_number, section in enumerate(sections, start=1):
        page = document.new_page(width=595, height=842)
        y = 58.0
        for raw_line in section.splitlines():
            line = raw_line.rstrip()
            if not line:
                y += 12
                continue
            is_heading = line.isupper() and len(line) <= 72
            size = 15 if is_heading else 10.5
            width = 66 if is_heading else 88
            for wrapped in textwrap.wrap(line, width=width) or [""]:
                page.insert_text(
                    (54, y),
                    wrapped,
                    fontsize=size,
                    fontname="helv",
                    color=(0.08, 0.10, 0.14),
                )
                y += size * 1.55
            y += 2 if is_heading else 0
        page.insert_text(
            (54, 812),
            f"Synthetic benchmark source | page {page_number}/{len(sections)}",
            fontsize=8,
            fontname="helv",
            color=(0.38, 0.42, 0.48),
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output, garbage=4, deflate=True)
    document.close()


def prepare_workspace(scenario_id: str, destination: Path) -> Path:
    if scenario_id not in SCENARIO_IDS:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Destination is not empty: {destination}")

    scenario_root = EXECUTOR_ROOT / scenario_id
    prompt = scenario_root / "prompt.md"
    if not prompt.is_file():
        raise FileNotFoundError(prompt)

    destination.mkdir(parents=True, exist_ok=True)
    (destination / "input" / "materials").mkdir(parents=True)
    (destination / "deliverable").mkdir()
    shutil.copy2(prompt, destination / "input" / "prompt.md")
    shutil.copytree(REPOSITORY_ROOT / "skill" / "taohtml", destination / "skill" / "taohtml")

    if scenario_id == "pdf-evidence-report":
        build_pdf(
            scenario_root / "materials" / "orbit-pilot-review.source.txt",
            destination / "input" / "materials" / "orbit-pilot-review.pdf",
        )
    elif scenario_id == "existing-html-upgrade":
        shutil.copy2(
            scenario_root / "materials" / "legacy-deck.html",
            destination / "input" / "materials" / "legacy-deck.html",
        )

    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy one benchmark scenario and TaoHtml into a judge-free workspace."
    )
    parser.add_argument("scenario", choices=SCENARIO_IDS)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        prepared = prepare_workspace(args.scenario, args.destination.resolve())
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"PREPARE_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"PREPARE_OK {prepared}")
    print(f"PROMPT {prepared / 'input' / 'prompt.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
