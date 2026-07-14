#!/usr/bin/env python3
"""Browser QA for local HTML decks.

Checks the runtime contract, routing, staged reveals, source modals, media
loading, console errors, screenshots, and visible content bounds. Requires Playwright:
  python -m pip install playwright
  python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


OVERFLOW_CHECK = """() => {
  const root = document.querySelector('.slide.active');
  if (!root) return [];
  const bounds = root.getBoundingClientRect();
  const selector = 'h1,h2,h3,h4,p,li,button,img,video,table,svg,[data-qa-bounds]';
  return [...root.querySelectorAll(selector)]
    .filter(el => {
      if (el.closest('[data-qa-ignore-overflow]')) return false;
      const r = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
      if (r.width === 0 || r.height === 0) return false;
      return r.left < bounds.left - 2 || r.top < bounds.top - 2 ||
        r.right > bounds.right + 2 || r.bottom > bounds.bottom + 2;
    })
    .slice(0, 20)
    .map(el => {
      const r = el.getBoundingClientRect();
      return {
        tag: el.tagName,
        cls: typeof el.className === 'string' ? el.className : '',
        text: (el.textContent || '').trim().slice(0, 80),
        rect: { left: r.left, top: r.top, right: r.right, bottom: r.bottom },
      };
    });
}"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run browser QA for an HTML deck.")
    parser.add_argument("html", type=Path, help="HTML file to test.")
    parser.add_argument("output_dir", type=Path, help="Directory for screenshots and report.")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--max-pages", type=int, default=0, help="Limit slide count. 0 means all.")
    parser.add_argument(
        "--executable-path",
        type=Path,
        help="Optional Chromium executable path for environments without Playwright's headless shell.",
    )
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("Playwright is required. Install with: python -m pip install playwright") from exc

    args.output_dir.mkdir(parents=True, exist_ok=True)
    url = args.html.resolve().as_uri()
    results: dict[str, object] = {
        "url": url,
        "viewport": {"width": args.width, "height": args.height},
        "pages": [],
    }
    failures: list[str] = []

    with sync_playwright() as pw:
        launch_options = {}
        if args.executable_path:
            if not args.executable_path.is_file():
                raise SystemExit(f"Chromium executable not found: {args.executable_path}")
            launch_options["executable_path"] = str(args.executable_path)
        browser = pw.chromium.launch(**launch_options)
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        console_errors: list[str] = []
        page_errors: list[str] = []
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        page.goto(url, wait_until="load")
        slide_count = page.locator(".slide").count()
        if args.max_pages:
            slide_count = min(slide_count, args.max_pages)
        if slide_count == 0:
            failures.append("No .slide elements found.")

        runtime_methods = [
            "getState",
            "setMode",
            "showPage",
            "nextStep",
            "previousStep",
            "nextPage",
            "previousPage",
            "toggleFullscreen",
        ]
        runtime_contract = page.evaluate(
            """methods => {
              const runtime = window.TaoHtmlRuntime;
              return {
                available: Boolean(runtime),
                missing: runtime ? methods.filter(name => typeof runtime[name] !== 'function') : methods,
              };
            }""",
            runtime_methods,
        )
        results["runtime_contract"] = runtime_contract
        if not runtime_contract["available"] or runtime_contract["missing"]:
            failures.append(f"Runtime contract is incomplete: {runtime_contract}")

        runtime_behavior: dict[str, object] = {"tested": False}
        if runtime_contract["available"] and slide_count >= 2:
            page.goto(f"{url}#1")
            page.evaluate("() => window.TaoHtmlRuntime.setMode('presentation')")
            first_fragment_count = page.locator(".slide.active .fragment").count()
            before = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            if first_fragment_count:
                page.keyboard.press("ArrowRight")
            after_step = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.keyboard.press("PageDown")
            after_page_down = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.keyboard.press("PageUp")
            after_return = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.evaluate("() => window.TaoHtmlRuntime.setMode('reading')")
            reading_visible = page.evaluate(
                """() => [...document.querySelectorAll('.slide.active .fragment')]
                .every(el => getComputedStyle(el).opacity === '1')"""
            )
            reading_state = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.evaluate("() => window.TaoHtmlRuntime.setMode('presentation')")
            presentation_state = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.keyboard.press("ArrowLeft")
            after_left_at_zero = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            control_before = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.locator("#moreToggle").focus()
            page.keyboard.press("Space")
            control_after = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            control_menu_open = page.locator("#moreMenu:not([hidden])").count() == 1
            page.locator("#moreToggle").click()
            grouped_step = page.evaluate(
                """() => {
                  const targetIndex = [...document.querySelectorAll('.slide')]
                    .findIndex(slide => slide.querySelectorAll('.fragment').length >= 2);
                  if (targetIndex < 0) return { tested: false };
                  const runtime = window.TaoHtmlRuntime;
                  runtime.showPage(targetIndex);
                  runtime.setMode('reading');
                  document.querySelectorAll('.slide.active .fragment')
                    .forEach(el => { el.dataset.taohtmlStep = '1'; });
                  runtime.setMode('presentation');
                  runtime.nextStep();
                  return {
                    tested: true,
                    state: runtime.getState(),
                    total: document.querySelectorAll('.slide.active .fragment').length,
                    visible: document.querySelectorAll('.slide.active .fragment.visible').length,
                  };
                }"""
            )

            expected_stage = 1 if first_fragment_count else 0
            runtime_behavior = {
                "tested": True,
                "before": before,
                "after_step": after_step,
                "after_page_down": after_page_down,
                "after_return": after_return,
                "reading_state": reading_state,
                "reading_visible": reading_visible,
                "presentation_state": presentation_state,
                "after_left_at_zero": after_left_at_zero,
                "control_keyboard": {
                    "before": control_before,
                    "after": control_after,
                    "menu_open": control_menu_open,
                },
                "grouped_step": grouped_step,
            }
            if after_step["stages"][0] != expected_stage:
                failures.append("ArrowRight did not advance exactly one presentation step.")
            if after_page_down["index"] != 1:
                failures.append("PageDown did not jump directly to the next page.")
            if after_return["index"] != 0 or after_return["stages"][0] != expected_stage:
                failures.append("Returning to a page did not restore its presentation stage.")
            if reading_state["mode"] != "reading" or not reading_visible:
                failures.append("Reading mode did not expose all current-page fragments.")
            if presentation_state["mode"] != "presentation" or presentation_state["stages"][0] != 0:
                failures.append("Switching from reading to presentation did not reset the current page.")
            if after_left_at_zero["index"] != 0 or after_left_at_zero["stages"][0] != 0:
                failures.append("ArrowLeft at step zero must not perform whole-page navigation.")
            if control_after != control_before or not control_menu_open:
                failures.append("Focused controls did not consume Space without advancing the report.")
            if grouped_step["tested"] and grouped_step["visible"] != grouped_step["total"]:
                failures.append("Elements sharing one data-step did not reveal together.")
        results["runtime_behavior"] = runtime_behavior
        page.reload(wait_until="load")

        for i in range(slide_count):
            console_start = 0 if i == 0 else len(console_errors)
            page_error_start = 0 if i == 0 else len(page_errors)
            page.goto(f"{url}#{i + 1}")
            page.wait_for_timeout(150)

            active = page.locator(".slide.active")
            active_count = active.count()
            active_index = page.evaluate(
                "() => [...document.querySelectorAll('.slide')].indexOf(document.querySelector('.slide.active'))"
            )
            route_ok = active_count == 1 and active_index == i

            fragment_count = active.locator(".fragment").count() if active_count == 1 else 0
            step_count = (
                active.locator(".fragment").evaluate_all(
                    "els => Math.max(0, ...els.map(el => Number.parseInt(el.dataset.taohtmlStep || '0', 10)))"
                )
                if active_count == 1
                else 0
            )
            for _ in range(step_count):
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(40)
            visible_fragments = active.locator(".fragment.visible").count() if active_count == 1 else 0
            for _ in range(step_count):
                page.keyboard.press("ArrowLeft")
                page.wait_for_timeout(40)
            rewound_fragments = active.locator(".fragment.visible").count() if active_count == 1 else 0
            for _ in range(step_count):
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(40)

            source_failures: list[str] = []
            source_buttons = active.locator(".source-btn") if active_count == 1 else page.locator(".never-match")
            for source_index in range(source_buttons.count()):
                button = source_buttons.nth(source_index)
                source = button.get_attribute("data-source") or "<missing data-source>"
                button.click()
                page.wait_for_timeout(200)
                modal_open = page.locator("#modal.open").count() == 1
                if not modal_open:
                    source_failures.append(f"{source}: modal did not open")
                media_error = page.locator("#modalBody").get_attribute("data-media-error")
                if media_error:
                    source_failures.append(f"{source}: failed to load")
                source_media_failed = page.evaluate(
                    """() => {
                      const media = document.querySelector('#modalBody img, #modalBody video');
                      if (!media) return Boolean(document.querySelector('#modalBody [data-media-error], #modalBody .source-error'));
                      if (media.tagName === 'IMG') return !media.complete || media.naturalWidth === 0;
                      return Boolean(media.error);
                    }"""
                )
                if source_media_failed and not media_error:
                    source_failures.append(f"{source}: media element failed")
                if modal_open:
                    page.locator("#modalClose").click()

            image_failures = page.evaluate(
                """() => [...document.images]
                .filter(img => !img.complete || img.naturalWidth === 0)
                .map(img => img.getAttribute('src') || '')"""
            )
            overflow = page.evaluate(OVERFLOW_CHECK)
            screenshot = args.output_dir / f"page-{i + 1:02d}.png"
            page.screenshot(path=str(screenshot), full_page=False)
            current_console_errors = console_errors[console_start:]
            current_page_errors = page_errors[page_error_start:]

            page_result = {
                "page": i + 1,
                "title": active.get_attribute("data-title") if active_count == 1 else None,
                "screenshot": str(screenshot),
                "route_ok": route_ok,
                "fragments": {
                    "total": fragment_count,
                    "steps": step_count,
                    "visible": visible_fragments,
                    "rewound": rewound_fragments,
                },
                "source_failures": source_failures,
                "image_failures": image_failures,
                "offscreen_elements": overflow,
                "console_errors": current_console_errors,
                "page_errors": current_page_errors,
            }
            results["pages"].append(page_result)

            if not route_ok:
                failures.append(f"Page {i + 1}: hash route did not activate the expected slide.")
            if visible_fragments != fragment_count:
                failures.append(
                    f"Page {i + 1}: only {visible_fragments}/{fragment_count} fragments became visible."
                )
            if rewound_fragments != 0:
                failures.append(
                    f"Page {i + 1}: {rewound_fragments}/{fragment_count} fragments remained after rewind."
                )
            if source_failures:
                failures.append(f"Page {i + 1}: source modal failures: {source_failures}")
            if image_failures:
                failures.append(f"Page {i + 1}: image failed to load: {image_failures}")
            if overflow:
                failures.append(f"Page {i + 1}: visible content exceeds slide bounds: {overflow[:3]}")
            if current_console_errors:
                failures.append(f"Page {i + 1}: console errors: {current_console_errors}")
            if current_page_errors:
                failures.append(f"Page {i + 1}: page errors: {current_page_errors}")
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
