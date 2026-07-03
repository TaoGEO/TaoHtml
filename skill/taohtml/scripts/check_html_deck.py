#!/usr/bin/env python3
"""Browser QA for local HTML decks at 1600x900.

Checks basic rendering, screenshots, image loading, and obvious viewport overflow.
Requires Playwright:
  python -m pip install playwright
  python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run browser QA for an HTML deck.")
    parser.add_argument("html", type=Path, help="HTML file to test.")
    parser.add_argument("output_dir", type=Path, help="Directory for screenshots and report.")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--max-pages", type=int, default=0, help="Limit slide count. 0 means all.")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("Playwright is required. Install with: python -m pip install playwright") from exc

    args.output_dir.mkdir(parents=True, exist_ok=True)
    url = args.html.resolve().as_uri()
    results: dict[str, object] = {"url": url, "pages": []}
    failures: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        page.goto(url)
        slide_count = page.locator(".slide").count()
        if args.max_pages:
            slide_count = min(slide_count, args.max_pages)
        if slide_count == 0:
            failures.append("No .slide elements found.")
        for i in range(slide_count):
            page.goto(f"{url}#{i + 1}")
            page.wait_for_timeout(250)
            screenshot = args.output_dir / f"page-{i + 1:02d}.png"
            page.screenshot(path=str(screenshot), full_page=False)
            image_failures = page.evaluate(
                """() => [...document.images]
                .filter(img => !img.complete || img.naturalWidth === 0)
                .map(img => img.getAttribute('src') || '')"""
            )
            overflow = page.evaluate(
                """() => [...document.querySelectorAll('.slide.active *')]
                .filter(el => {
                  const r = el.getBoundingClientRect();
                  const style = getComputedStyle(el);
                  if (style.display === 'none' || style.visibility === 'hidden') return false;
                  if (r.width === 0 || r.height === 0) return false;
                  return r.right < -2 || r.bottom < -2 || r.left > innerWidth + 2 || r.top > innerHeight + 2;
                })
                .slice(0, 20)
                .map(el => ({ tag: el.tagName, cls: el.className, text: (el.textContent || '').slice(0, 80) }))"""
            )
            page_result = {
                "page": i + 1,
                "screenshot": str(screenshot),
                "image_failures": image_failures,
                "offscreen_elements": overflow,
            }
            results["pages"].append(page_result)
            if image_failures:
                failures.append(f"Page {i + 1}: image failed to load: {image_failures}")
            if overflow:
                failures.append(f"Page {i + 1}: possible offscreen elements: {overflow[:3]}")
        browser.close()

    report = args.output_dir / "qa-report.json"
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        print("HTML_DECK_QA_FAILED")
        for failure in failures:
            print(failure)
        print(report)
        return 1
    print("HTML_DECK_QA_OK")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
