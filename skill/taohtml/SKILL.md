---
name: taohtml
description: TaoHtml creates, restructures, and polishes high-design HTML presentations, PPT-like reports, roadshow decks, training courseware, business proposals, diagnostic reports, and speaker-note-ready decks. Use when the user provides an outline, screenshots, PDFs, source documents, existing slides or HTML, or asks to build or upgrade a presentation with coherent story structure, premium visual design, evidence pages, interaction, animations, speaker notes, final CTA, portable delivery package, faithful source conversion, or high-design roadshow redesign.
---

# TaoHtml

## Core Principle

Do not start from slides. Start from the audience decision, the story spine, and the proof chain.

TaoHtml turns source material into a performable HTML presentation. A good deck is a controlled sequence:

1. Reframe the audience's problem.
2. Show evidence that the problem is real.
3. Explain the mechanism.
4. Demonstrate the method or system.
5. Reduce risk with proof, boundaries, and process.
6. End with a clear next action.

For full-deck creation, major restructuring, or process documentation, read `references/process-playbook.md` before acting.

For high-design roadshow redesign, also read:

- `references/design-quality-rubric.md` when the user asks for high aesthetic standards, says a result feels ordinary, or you need to judge whether the deck is premium enough.
- `references/layout-pattern-library.md` before composing pages, especially when the deck risks becoming title + cards.

For HTML output, reuse:

- `assets/html-deck-template/` as the default local, dependency-free 16:9 deck shell when starting from scratch.
- `scripts/extract_pdf_pages.py` to render PDF source pages into evidence assets.
- `scripts/check_assets.py` to detect missing assets, remote links, and non-portable absolute paths.
- `scripts/check_html_deck.py` to run browser QA and screenshots at 1600x900.
- `scripts/build_contact_sheet.py` to create a QA overview image from screenshots.
- `scripts/package_deck.py` to create a portable zip after QA passes.

## Working Mode

Choose the mode from the user's wording.

- **Discuss / plan only**: when the user asks for suggestions, options, structure, or wants to discuss first. Do not edit files unless they explicitly agree.
- **Build / edit**: when the user says to start, agrees, asks to generate, or asks to modify the deck/report. Inspect existing files and implement.
- **Rehearse / package**: when the deck is near final and the user asks for speaker notes, rehearsal script, portable packaging, final close, pricing page, or handoff.

## Output Mode Gate

When the user provides an existing PDF, PPT, HTML deck, or screenshots, decide the output mode before designing.

- **Faithful migration**: preserve every source page, chart, and layout as primary content. Use this for "do not lose information", archive browsing, review, searchable HTML, or portable PDF-to-HTML presentation. The design work is the viewer shell, navigation, zoom, text extraction, and packaging.
- **Roadshow redesign**: use the source as information input and evidence layer, then rebuild the main slides with a new story spine, visual metaphor, layout system, motion, and presenter rhythm. Use this when the user asks for "roadshow", "design sense", "make it like my previous deck", "not ordinary", "polish the presentation", or criticizes a result as merely preserving the original layout.

Do not confuse the two modes. If the request includes both "do not lose information" and "redesign", keep full source information through source-page buttons, evidence modals, appendix pages, or downloadable originals, but redesign the main slide surface.

In roadshow redesign mode:

- Treat original pages as source material, not as the slide layout to preserve.
- Do not keep the original page-by-page structure unless it serves the new story.
- Replace "title + generic cards + data blocks" with a deliberate stage composition.
- Give each page a distinct visual job: opener, conflict, proof, mechanism, system map, case teardown, live demo, decision, or close.
- Preserve source facts and exact numbers, but rewrite their presentation as scenes, flows, contrasts, or systems.
- Use the design rubric and layout library before implementation when the user expects high design. Do not wait until QA to discover that every page has the same structure.

## Intake Checklist

Before building, identify:

- Audience: who will watch or read this?
- Occasion: live salon, client proposal, internal report, sales deck, training course, diagnostic report, pitch, etc.
- Desired action: what should the audience do after the report?
- Time budget: total speaking time and depth per section.
- Source materials: outline, screenshots, documents, reports, videos, posters, pricing images, existing decks/HTML.
- Delivery format: PPTX, HTML slide deck, PDF report, web page, portable zip.
- Constraints: brand style, color palette, screen ratio, offline use, no external dependencies, privacy boundaries.

If information is missing but a reasonable assumption is safe, proceed and state the assumption. Ask only when the answer changes the structure or risk materially.

## Story Architecture

Build the deck as sections, not independent pages. Each section should have:

- **Opening page**: one sentence that names the shift or tension.
- **Evidence pages**: real screenshots, data, cases, report snippets, demo recordings, or specific examples.
- **Mechanism page**: explain why the evidence happens.
- **Method page**: turn the mechanism into a framework or operating model.
- **Closing / hinge page**: summarize the section and open the next one.

Default section grammar:

1. Cover / welcome.
2. Situation or customer behavior shift.
3. Real example or simulation.
4. Risk or gap.
5. Definition.
6. Mechanism.
7. Framework.
8. Case / proof.
9. Operating system or workflow.
10. Service / product / tool.
11. Boundaries and promises.
12. Pricing or CTA.
13. Closing.

For roadshow redesign, first write the page role sequence in plain language before making HTML. Example: "manual-report production line collapses", "data capability evolves into an asset layer", "data factory cutaway", "case evidence teardown". If the page roles still sound like the original PDF titles, redesign the story spine again.

## Slide Role Rules

Every slide must have one job. Name the role before writing the page.

- **Cover**: signal topic, tone, identity, and occasion.
- **Chapter opener**: one strong proposition, minimal text, visual rhythm reset.
- **Demonstration**: let the audience see the behavior, not read an explanation.
- **Evidence page**: preserve real proof; add framing, callouts, and hierarchy.
- **Mechanism page**: show process, path, causality, or system logic.
- **Framework page**: compress action into memorable categories.
- **Case page**: use actual details and show what changed.
- **Summary page**: close a section with "so what".
- **Offer / pricing page**: make the commercial next step concrete.
- **Appendix**: hold dense details that are not needed in live flow.

If two adjacent slides look similar but have different jobs, change the layout rhythm. Repeated layouts are acceptable only when they intentionally show a sequence.

## Evidence-First Writing

Prefer proof over explanation.

- Use the user's real screenshots, source reports, video recordings, data tables, or customer cases when available.
- Do not over-summarize a source screenshot if the point is to show the source itself.
- Separate source facts from speaker interpretation.
- Turn vague claims into verifiable examples.
- Use before/process/after only when there is actual evidence for each part.
- Avoid fake certainty. If the deck makes a promise, state the boundary.

For dense source material:

1. Keep the original visible enough to preserve credibility.
2. Crop or split it into readable slices.
3. Add a title that states why this proof matters.
4. Add 1-3 callouts, not a wall of commentary.
5. End with the implication for the audience.

## Visual System

Create one deck-level visual thesis before designing pages.

Define:

- Primary palette and accent color.
- Typography scale for title, subtitle, body, labels, and captions.
- Background logic: light, dark, grid, document, dashboard, photo, etc.
- Recurring motifs: rulers, dots, cards, frames, labels, arrows, timelines, console windows, report panels.
- Page furniture: kicker, footer, progress, page number, section label.
- Asset treatment: screenshots, portraits, product images, videos, QR codes, pricing posters.

Avoid generic card mosaics. Cards are for repeated items or framed evidence, not a default page design.

When high design is required, write the visual thesis and page role sequence before editing files. Use `references/layout-pattern-library.md` to assign patterns to key pages. Use `references/design-quality-rubric.md` after the first working version and revise anything below professional quality.

## Design DNA Extraction

When the user references an existing deck, image, or prior design they like, extract its design DNA before editing.

Extract:

- Composition: symmetric vs asymmetric, centered vs stage-like, dense vs sparse.
- Typography: title scale, weight contrast, label system, text density.
- Color behavior: primary surfaces, accent colors, warning colors, contrast level.
- Motifs: rulers, grids, dot matrices, circles, cutaways, floating panels, source windows, report panels, terminal windows, evidence callouts.
- Motion grammar: serial reveal, typewriter, scan, focus zoom, modal reveal, report scroll, staged comparison.
- Evidence treatment: whether source material appears as screenshot, cropped slice, modal, miniature, or live panel.
- Emotional tone: premium, technical, urgent, institutional, editorial, product-like, operational.

Then apply the extracted DNA to the new subject. Do not copy only the color palette. If the reference deck gets its design power from large typography, black/heavy blocks, asymmetry, source evidence windows, and staged reveals, the new deck must carry those behaviors too.

## Interaction And Motion

For live presentation decks, interaction must follow presenter logic.

- Right arrow / click should advance the next visible step before moving to the next slide.
- Avoid mouse-only reveals, hover-only content, or interactions that a clicker cannot operate.
- If a page has staged content, the final stage should usually show the complete page before the next slide.
- If a modal opens for video or demo, provide replay and return behavior.
- Keep animations purposeful: reveal sequence, process flow, typing simulation, scanning, report scroll, focus zoom.
- Do not let animation obscure readability or cause layout shift.

Roadshow redesign should feel performable. If a page can be fully understood as a static report card, add staged tension: reveal the problem, then the evidence, then the implication. The final stage should show the complete page before moving on.

For HTML decks, preserve existing keyboard navigation, hash routing, progress bars, and page counts when editing.

## HTML Deck Implementation

When implementing a PPT-like report as HTML:

- Use local HTML, CSS, and native JS unless the user explicitly accepts external dependencies.
- Start from `assets/html-deck-template/` when building a new deck unless an existing deck already has stronger local infrastructure.
- Keep reusable CSS variables for palette, spacing, type, and animation timing.
- Use stable 16:9 layout constraints and test at 1600x900.
- Keep all asset paths relative to the HTML when packaging.
- Copy referenced images, videos, and documents into an assets folder or sibling output folder.
- Do not assume the HTML alone is portable if it references local absolute paths.
- For large media, use poster frames, modals, and explicit play controls.
- For screenshots of web reports, slice or embed them so that all important charts are readable.
- Run `scripts/check_assets.py` and `scripts/check_html_deck.py` before delivery when feasible. Build a contact sheet from QA screenshots for visual review on multi-page decks.

## Speaker Notes

Write speaker notes only after the deck structure is stable.

For each slide, include:

- Page number and page title.
- Opening sentence.
- Main explanation in spoken language requested by the user.
- Transition to the next slide.
- Optional timing note if the deck is for a live session.

For transition pages, write transition language rather than detailed lecture text.

## Packaging

Before delivery, produce or check:

- Main deck file.
- Assets folder with every referenced image/video/report.
- Speaker script, if requested.
- Portable zip for another computer.
- Clear instruction on which file to open.

If the deck includes local assets, tell the user the whole folder or zip is required, not just the HTML file.

## QA Checklist

Run a practical check before finalizing:

- Cover page renders correctly.
- Section openers and closers make sense in sequence.
- Page count and progress are correct.
- Keyboard/click navigation works.
- Staged reveals replay correctly when returning to a page.
- Videos open, play, replay, and close correctly.
- Screenshots and report slices are readable.
- No text overflow or element collision at 1600x900.
- Final CTA/pricing/contact page is present if the deck is commercial.
- Portable package opens without missing assets.

Roadshow redesign quality gate:

- Does it look like a designed presentation, not a decorated source document?
- Is there a visual metaphor for the subject?
- Do at least the key pages avoid the ordinary pattern of title + cards + small labels?
- Are there strong focal points, oversized moments, or stage compositions?
- Does each page use the source information as proof while still feeling newly composed?
- If compared to the user's reference deck, does it share the same level of visual confidence, not merely a similar palette?
- Would it score at least 80 using `references/design-quality-rubric.md`? If not, revise before delivery.

## Common Fixes

- If a page feels abstract, add a real question, real screenshot, real metric, or concrete mini-case.
- If a page feels like decoration, rewrite the page job before redesigning.
- If a section transition feels abrupt, add a hinge slide that says what was proven and what remains unsolved.
- If the deck sells too early, move offer pages after diagnosis, mechanism, and proof.
- If the slide is too dense, split into staged reveals or multiple pages.
- If the audience cannot operate it with a clicker, convert mouse interactions into serial reveal stages.
- If the result feels ordinary, stop adjusting colors and redesign the visual metaphor, page role sequence, and composition system.
- If a source-to-HTML result looks like a PDF viewer, ask whether the user intended faithful migration. If they wanted redesign, rebuild the main slides and keep the original pages only as evidence.
