# Runtime Contract

Use this contract for paged reading reports and single-screen presentations generated from the bundled template.

## Supported Core

The current core supports:

- Fixed 16:9 canvas scaled inside the browser viewport
- Hash-addressable pages
- Reading and single-screen presentation modes
- Per-page reveal progress retained while moving between pages
- Separate step navigation and whole-page navigation
- Click-to-advance in presentation mode
- Whole-page previous/next buttons
- Fullscreen entry and exit
- Page number
- Auto-hiding controls
- Source evidence modal
- Lightweight report text/image editing with unified undo/redo
- Session-scoped refresh recovery and export to a newly named HTML
- Offline local assets and portable packaging

Do not promise dual-screen presenter view, embedded speaker notes, free element movement, layout rebuilding, interactive chart authoring, animation editing, cross-page morphing, durable version history, or browser ZIP export from this core. Read `content-editor.md` before authoring or testing editable content.

## DOM Contract

Keep these hooks when generating or redesigning a deck:

```html
<main class="deck" id="deck" data-mode="presentation" data-taohtml-step-contract="fragment-v1">
  <section class="slide active" data-title="...">
    <div class="fragment" data-step="1">...</div>
    <div class="fragment" data-step="1">...</div>
    <div class="fragment" data-step="2">...</div>
  </section>
</main>
```

- `.deck`: runtime root and current `data-mode`.
- `.slide`: one paged scene; DOM order is page order.
- `.slide.active`: the one visible page.
- `.fragment`: an element controlled by a presentation step.
- `data-step`: optional positive step number. Elements sharing a number change together. Fragments without it are numbered in DOM order for backward compatibility.
- `.fragment.visible`: a step already revealed in presentation mode.
- `data-taohtml-step-contract="fragment-v1"`: the current single controlled-presentation-step contract. QA normalizes `.fragment` plus `data-step` into per-page `data-taohtml-step` values through this named contract. A future equivalent state-node system must declare a new contract and update Runtime and QA together; it must not bypass the zero-step gate with an unrelated selector.
- `data-step-index` on each slide: current numeric presentation state, available to page-specific CSS.
- `#pageIndicator`: current page and total pages.
- `#prev` / `#next`: whole-page navigation controls.
- `#modeToggle`: reading/presentation switch.
- `#fullscreenToggle`: fullscreen control.
- `#editToggle`: enter/leave the bundled content editor.
- `data-taohtml-edit-lock`: exclude a system, fixed-brand, or other non-report subtree from editing.

Page-specific design may add classes and data attributes, but must not remove these hooks.

## Input Contract

### Presentation mode

- `ArrowRight`, Space, or a blank-page click advances one fragment; after the last fragment, it moves to the next page.
- `ArrowLeft` reverses one fragment; at the initial state, it moves to the previous page. The first page safely remains at the first page.
- `PageDown` moves to the next page immediately without completing remaining fragments.
- `PageUp` moves to the previous page immediately.
- Returning to a page restores its prior fragment stage.

### Reading mode

- Every fragment is visibly complete.
- `ArrowRight`, `ArrowLeft`, Space, `PageDown`, `PageUp`, blank-page click, and navigation buttons move by whole page.
- Switching from reading to presentation resets the current page to its first presentation state.

Buttons, links, inputs, and open modals must consume their own events rather than advancing the page.

### Edit mode

- `setEditing(true)` preserves `mode`, page index, and every stored stage while exposing all fragments for editing.
- Page-step keys, blank-page advance, reveal transitions, and report animations pause. Previous/next page buttons remain available for moving through the same edit session.
- System controls and locked subtrees never become content targets.
- `setMode`, `nextStep`, and `previousStep` do nothing until `setEditing(false)` restores normal Runtime behavior.

### Controls and fullscreen

- Opening the more menu keeps controls visible and suspends the auto-hide timer.
- Entering or exiting fullscreen closes the more menu, sets its toggle to `aria-expanded="false"`, and restarts the auto-hide timer after `fullscreenchange`.
- Pointer movement reveals the controls again. Fullscreen and non-fullscreen states must not retain a stale menu overlay.
- Edit mode keeps controls visible; leaving it rearms the ordinary auto-hide timer.

## Public API

Expose `window.TaoHtmlRuntime` with:

```text
getState()
setMode("reading" | "presentation")
showPage(index)
nextStep()
previousStep()
nextPage()
previousPage()
toggleFullscreen()
setEditing(true | false)
```

`getState()` returns a copy containing `mode`, zero-based `index`, the per-page `stages` array, and boolean `editing`. Runtime changes dispatch `taohtml:statechange` on `window` with the same state snapshot in `event.detail`.

The `editing` field and `setEditing()` method are additive. Existing consumers may continue reading only `mode`, `index`, and `stages`; their meaning and types do not change. Event consumers must ignore unknown future snapshot fields. Editor consumers must not mutate `event.detail` and must use `setEditing()` instead of replacing the core Runtime or synthesizing navigation state.

Optional future modules must use this API and event rather than replacing core navigation.

## Performance Rules

- Do no work while the presenter is idle except the control-hide timer.
- Animate with `transform` and `opacity` when possible.
- Do not start hidden-page animations or media.
- Keep large media and full fonts out of the single file when they make loading or interaction visibly slow.
- Add optional modules only when the confirmed brief requires them.

## QA Contract

Before delivery, verify:

- A deck whose initial mode is presentation has at least one controlled presentation step across the report. Reading mode may validly contain zero steps.
- Reading mode exposes all current-page fragments.
- Presentation mode starts with unrevealed fragments.
- Step and whole-page keys have different behavior.
- Elements that share `data-step` change together.
- Whole-page jumps work before all fragments are revealed.
- `ArrowLeft` returns to the previous page from stage 0 while preserving that page's prior stage; the first page does not underflow.
- Returning to a page restores its stage.
- Hash routes and page numbers match the active page.
- Controls and fullscreen actions do not advance the report; fullscreen closes the more menu and controls auto-hide again after idle time.
- Edit mode pauses keyboard/blank-click/reveal advance, keeps page buttons usable, locks system UI, and restores the pre-edit Runtime state on exit.
- Text, image replacement, and crop focus share Ctrl/Cmd undo and redo; refresh recovery and export/reopen pass `content-editor.md`.
- Asset, console, and visible-bound checks pass at the target viewport.
- Every active slide's rendered rectangle covers the deck canvas within the QA tolerance at each target viewport.
- Independent visible text labels, including HTML text and SVG `<text>`, do not intersect and retain the small QA safety gap. SVG labels and positioned/transformed HTML labels remain strict; a shallow HTML Range font-metric overlap is excluded only when both static, independently untransformed layout boxes are actually separate, and that exclusion is recorded in QA JSON. Exempt an intentional overlay only on the exact text owner with `data-qa-ignore-text-collision="reason"`; the report must list every opt-out.
