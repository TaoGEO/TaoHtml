# TaoHtml

TaoHtml is a Codex skill for building high-design HTML presentations from PDFs, screenshots, outlines, source documents, and existing decks.

It is designed for reports that need more than a clean conversion. TaoHtml helps an AI agent decide whether to preserve source material faithfully or rebuild it into a roadshow-style HTML deck with story structure, evidence pages, motion, QA, and portable packaging.

## What TaoHtml Does

TaoHtml turns messy source material into a presentable HTML deck:

- Convert PDFs and source documents into portable HTML presentations.
- Redesign ordinary reports into high-design roadshow decks.
- Preserve dense source information through source-page buttons, appendix views, and evidence modals.
- Build slide sequences around audience decision, story spine, and proof chain.
- Use a design quality rubric to avoid generic "title + cards" output.
- Use layout patterns for cover pages, evidence stages, mechanism diagrams, system cutaways, case teardowns, demo shells, offer pages, and closings.
- Generate dependency-free local HTML decks with keyboard navigation, staged reveals, modal source views, and progress indicators.
- Run asset checks, browser QA, contact-sheet generation, and portable zip packaging.

## Why It Exists

Most AI-generated presentation pages fail in one of two ways:

1. They preserve the original document but look like a PDF viewer.
2. They look decorated but lose source facts, charts, evidence, and business logic.

TaoHtml is built around a different standard:

> Keep the source truthful, but redesign the live presentation surface.

The main deck should persuade. The source layer should preserve. The QA scripts should verify.

## Good Use Cases

- Roadshow decks
- Client proposal decks
- Internal strategy reports
- Training courseware
- Product demo decks
- Diagnostic reports
- Commercial service presentations
- PDF-to-HTML report redesign
- Speaker-note-ready presentation systems

## Repository Structure

```text
TaoHtml/
├─ README.md
├─ LICENSE
├─ docs/
│  ├─ product-introduction.md
│  └─ workflow.md
├─ examples/
│  └─ prompts.md
└─ skill/
   └─ taohtml/
      ├─ SKILL.md
      ├─ agents/
      ├─ assets/
      ├─ references/
      └─ scripts/
```

The installable Codex skill is `skill/taohtml`.

## Installation

Copy the skill folder into your Codex skills directory:

```powershell
Copy-Item -Recurse -Force .\skill\taohtml $env:USERPROFILE\.codex\skills\taohtml
```

On macOS or Linux:

```bash
cp -R ./skill/taohtml ~/.codex/skills/taohtml
```

Restart Codex or open a new thread so the skill list refreshes.

## Quick Start

Ask Codex:

```text
Use $taohtml to turn this PDF into a high-design HTML roadshow deck.
Keep the source information traceable, but redesign the main slides for live presentation.
```

Or:

```text
Use $taohtml to polish this existing HTML presentation.
Improve story structure, visual hierarchy, evidence pages, animation rhythm, and portable packaging.
```

## Core Workflow

TaoHtml guides the agent through:

1. Audience decision: what should the audience believe or do?
2. Story spine: what sequence earns that decision?
3. Output mode: faithful migration or roadshow redesign?
4. Evidence layer: where do source facts, screenshots, charts, and originals live?
5. Visual thesis: what design world fits this subject?
6. Layout pattern selection: which pages need which composition?
7. HTML implementation: local, dependency-free, 16:9, presenter-friendly.
8. QA: asset check, browser screenshots, contact sheet, portable zip.

## Included Resources

### References

- `process-playbook.md`: end-to-end report and deck-building workflow.
- `design-quality-rubric.md`: 100-point quality rubric and hard gates.
- `layout-pattern-library.md`: 12 reusable layout patterns for high-design decks.

### HTML Template

- `assets/html-deck-template/index.html`: local 16:9 slide shell with navigation, staged reveals, source modal, and progress bar.

### Scripts

- `extract_pdf_pages.py`: render PDF pages into PNG evidence assets.
- `check_assets.py`: detect missing assets and non-portable local paths.
- `check_html_deck.py`: run Playwright browser QA at 1600x900.
- `build_contact_sheet.py`: create a contact sheet from QA screenshots.
- `package_deck.py`: package an HTML deck folder into a portable zip.

## Design Standard

TaoHtml is opinionated:

- Do not start from slides. Start from audience decision and proof chain.
- Do not decorate a bad structure. Fix the story first.
- Do not copy a reference style as colors only. Extract composition, typography, motifs, evidence treatment, and motion grammar.
- Do not make source screenshots decorative. Make them readable or move them into source views.
- Do not require mouse-only interaction for live decks. A clicker should advance staged content.
- Do not ship without QA when the deck includes local assets or media.

## License

MIT License. See `LICENSE`.
