# Workflow

Use this workflow when applying TaoHtml to a real project.

## 1. Intake

Identify:

- Audience
- Occasion
- Desired action
- Time budget
- Source materials
- Delivery format
- Offline or portability constraints

If the user does not provide all answers, proceed with safe assumptions and state them.

## 2. Choose Output Mode

Choose one:

- Faithful migration: preserve source pages as the main surface.
- Roadshow redesign: use source material as evidence and rebuild the main slides.

If the user asks for both "do not lose information" and "better design", keep full source pages as source views, appendix pages, or downloadable assets.

## 3. Build Story Spine

Write the page role sequence before editing HTML.

Useful movement:

1. Current behavior
2. Visible example
3. Risk or gap
4. Definition
5. Mechanism
6. Framework
7. Evidence
8. Operating model
9. Offer or next action
10. Closing

## 4. Create Visual Thesis

Write one sentence that describes the visual world.

Example:

> This report should feel like a data factory cutaway: manual inputs enter on the left, standardized assets accumulate in the center, and decision outputs leave on the right.

Then select 3-5 recurring motifs.

## 5. Select Layout Patterns

Use `references/layout-pattern-library.md`.

Avoid using cards as the default. Choose a pattern based on the slide job:

- opener
- evidence
- mechanism
- framework
- case
- system
- demo
- offer
- close

## 6. Implement HTML

Start with `assets/html-deck-template/` unless the existing deck already has stronger infrastructure.

Keep:

- local assets
- relative paths
- 16:9 layout
- keyboard navigation
- clicker-friendly staged reveals
- source modals
- consistent visual system

## 7. Preserve Source Information

For dense sources:

- render original pages
- crop or slice important areas
- show full source in modal or appendix
- separate source facts from speaker interpretation

## 8. QA

Run:

```bash
python skill/taohtml/scripts/check_assets.py path/to/index.html
python skill/taohtml/scripts/check_html_deck.py path/to/index.html path/to/qa
python skill/taohtml/scripts/build_contact_sheet.py path/to/qa path/to/qa/contact-sheet.png
```

Check:

- first page
- dense page
- evidence page
- media page
- final page
- all local assets
- 1600x900 layout
- navigation and staged reveal reset

## 9. Package

Run:

```bash
python skill/taohtml/scripts/package_deck.py path/to/deck path/to/deck.zip
```

Send the whole zip when the deck will be used on another computer.
