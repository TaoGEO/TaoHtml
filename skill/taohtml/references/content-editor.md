# Content Editor Contract

Use the bundled content editor for lightweight corrections inside a finished TaoHtml report. It is not a browser-based PPT editor: page structure, free element movement, layout rebuilding, chart data, table structure, animation timing, and animation authoring remain outside this module.

## Contents

- User flow and editor boundaries
- Report DOM and locking hooks
- Image frame/crop behavior
- History and session recovery
- Export boundary and Safari fallback
- Runtime/editor APIs and QA

## User Flow

1. Open **More → 编辑模式**.
2. Edit report copy directly. Click a report image to choose a replacement; drag the image to change its crop focal point.
3. Use `Ctrl/Cmd+Z` for undo and `Ctrl/Cmd+Shift+Z` for redo across text edits, image replacement, and crop changes. The UI intentionally has no undo button.
4. Move between pages with the previous/next page buttons. While editing, page-step keyboard shortcuts, blank-page advance, reveal transitions, and report animations are paused.
5. Choose **More → 退出编辑模式**. If changes have not been exported, choose **继续编辑**, **放弃修改**, or **导出新 HTML**.

Leaving edit mode restores normal behavior in the retained reading/presentation mode, current page, fragment stages, hash route, controls, and animations. Modified nodes remain the same DOM nodes, so their existing report CSS and motion rules continue to apply.

## Report DOM And Locking Contract

The editor discovers content only below `.slide`:

- HTML elements that own visible text are direct-edit targets.
- `<img>` elements are image-edit targets.
- Table-cell text remains editable, but rows, columns, formulas, and table structure do not.
- Inline SVG/chart internals, CSS background images, pseudo-elements, video, canvas, and embedded documents are not content-edit targets. Put ordinary report copy in HTML and content images in `<img>` when they must be revisable.

Use these generic hooks instead of sample-specific ids or copy:

```html
<div data-taohtml-edit-lock>System UI or a fixed corporate shell</div>
<div data-taohtml-edit="off">A locally excluded subtree</div>
<p data-taohtml-edit="text">Force this HTML node to be one text target.</p>
<img data-taohtml-edit="image" src="..." alt="...">
```

- `data-taohtml-edit-lock` excludes the element and all descendants. Apply it to controls, menus, page numbers, modals, source viewers, fixed brand layers, and any other non-report surface.
- `data-taohtml-edit="off"` is the content-author opt-out alias.
- `data-taohtml-edit="text"` forces one text owner when automatic direct-text discovery would choose a different ancestor.
- `data-taohtml-edit="image"` documents an intended image target; unlocked report `<img>` elements are discovered automatically.
- A lock always wins over a force marker. An `aria-hidden="true"` subtree is also excluded because it cannot be report content exposed to the reader.

The standard template locks navigation, the More menu, page number, source modal, and editor UI. The corporate-fidelity compiler's existing `aria-hidden="true"` fixed shell remains excluded without changing its strict attribute allowlist, while report content inside the editable region stays discoverable.

## Image Frame And Crop Contract

Replacement changes the existing `<img>` source in place; it does not move or recreate the element. The editor:

- removes `srcset`/`sizes` so they cannot override the chosen replacement;
- records the existing rendered aspect ratio inline before changing the source, preserving responsive frame geometry;
- leaves the element's CSS position, width, height, transform, filter, and computed `object-fit` rules intact;
- stores crop focus only as inline `object-position` percentages.

For deterministic crop behavior, generate content images inside a stable frame and use `width: 100%`, `height: 100%`, plus `object-fit: cover` or `contain`. Dragging changes focus for `cover`; `contain` has no hidden crop area, so a different focus may not be visually apparent. Fixed/decorative corporate crops must be locked rather than presented as report content images.

## History And Temporary Recovery

The editor owns one bounded, in-memory history across text, image, and crop commands. Native browser undo is intercepted only while edit mode is active. A refresh-recovery delta is also written to `sessionStorage`:

- it is scoped to the current tab/page session and survives reload in that tab;
- normal tab closure ends the browser page session, so it is not durable report storage;
- a document signature prevents applying a delta to changed source HTML;
- successful export clears the temporary record;
- storage-quota failure does not discard the live edit, but the editor warns that refresh recovery is unavailable. Large replacement images should be exported promptly.

The editor never uses `localStorage`, IndexedDB, a remote service, or an online dependency.

## Export Boundary

Export always downloads a newly named `.html`; it never writes over the source file.

- When every resource is embedded, the result is a portable offline single HTML file.
- When the report still references relative local resources, the browser exports only the revised HTML. Keep/move it beside the original `index.html` and preserve the original `assets` directory.
- The in-browser editor does **not** create a ZIP. Agent-side delivery may still use `scripts/package_deck.py` to package an existing HTML-plus-assets directory.
- The editor reports `single-file` versus `html-with-assets` from `TaoHtmlEditor.exportHtml()` and lists the detected external asset references.

Chromium/Chrome is the primary browser QA path. Safari is a documented best-effort path: content editing and session recovery use standard browser APIs, but TaoHtml does not claim automated Safari coverage. If Safari does not honor the Blob download filename/flow, use the page it opens and **Save As**, then keep relative assets beside it. No File System Access API or ZIP fallback is claimed.

## Module API

The bundled module exposes `window.TaoHtmlEditor`:

```text
getState()
enter()
requestExit()
undo()
redo()
exportHtml()
```

`getState()` returns `active`, `dirty`, `canUndo`, `canRedo`, and `recoveryAvailable`. Changes dispatch `taohtml:editorstatechange` on `window` with the same snapshot in `event.detail`.

The editor calls `TaoHtmlRuntime.setEditing(boolean)`; it must not replace navigation state or attach a second page state machine. Read `runtime-contract.md` for the core API and `taohtml:statechange` compatibility rules.

## QA

For an editor-enabled deliverable, run both:

```bash
python skill/taohtml/scripts/check_html_deck.py path/to/index.html path/to/qa
python skill/taohtml/scripts/check_editor_runtime.py path/to/index.html path/to/editor-qa
```

The editor QA must use a self-contained rendered report with at least one text target, one `<img>`, and one fragment. It covers continuous text/image editing, crop focus, unified undo/redo, dirty-exit choices, reload recovery, export/reopen, locked controls, and restored reading/presentation behavior.
