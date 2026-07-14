---
name: taohtml
description: TaoHtml turns ideas, Word/PDF source material, existing slides, and HTML into polished, offline HTML layouts, paged reports, and presentation-ready decks. Use when the user explicitly invokes TaoHtml or asks an agent to understand source material, preserve core viewpoints and evidence, confirm a report design brief, create or redesign visual HTML, add reading or single-screen presentation behavior, or run portable delivery QA.
---

# TaoHtml

Turn source material into a finished HTML report that can be read or presented without further layout work.

Treat TaoHtml as two cooperating layers:

- The skill directs material understanding, decisions, visual composition, generation, QA, and delivery.
- The bundled runtime supplies stable navigation, reveal state, reading/presentation modes, and other implemented behaviors.

Do not claim runtime features that are not present in `references/runtime-contract.md`.

## Explicit Invocation

Prefer explicit invocation. Use the host agent's real skill syntax, such as `$taohtml` in Codex. Do not assume `/TaoHtml` is portable across agents.

## Entry Routes

Identify one route before continuing:

1. **Idea only**: help the user clarify the report before producing a brief.
2. **Word / PDF**: extract and confirm the material before design. This is the fully specified reference route.
3. **Existing PPT / HTML**: confirm whether to preserve the structure or reorganize it while keeping all core viewpoints.

Never ask for information already present in the conversation or source files.

## Required State Flow

For Word/PDF work, follow this sequence without skipping confirmation gates:

1. Identify the route, then determine reading or presentation mode and concise, standard, or detailed length. Skip any choice the user already made.
2. Read `references/material-understanding.md`, inspect the source, and output a Material Understanding Summary. Do not design pages yet.
3. Wait for the user to confirm or correct that summary.
4. Read `references/intake-workflow.md`. Fill only the missing decisions that would change structure, evidence, visual direction, or delivery.
5. When several report structures are genuinely reasonable, present 2-3 chapter-level options and let the user choose.
6. Read `references/design-brief-template.md` and produce one adaptive Report Design Brief.
7. Wait for explicit confirmation of the current brief. A previous "agree", "continue", or request to use TaoHtml is not production authorization.
8. After confirmation, read `references/process-playbook.md` and produce the HTML directly. Do not insert a separate full prose manuscript step.
9. Implement only the runtime capabilities documented in `references/runtime-contract.md` unless the user separately authorizes new runtime engineering.
10. Run asset and browser QA, fix objective failures, and report the files, checks, and production-stage judgment calls.

If the user adds source material or changes a core viewpoint after confirming the brief, update the brief and request confirmation again. Local copy, color, layout, or motion revisions after delivery do not require a new brief unless they change the report's core meaning or structure.

## Question Discipline

Maintain an internal ledger with four buckets:

```text
known | confirmed | inferred | missing
```

Before asking anything:

- Re-read the conversation, material summary, and prior answers.
- Extract answers from the source instead of asking the user to repeat them.
- Ask one question at a time.
- Ask only when the answer changes structure, evidence, visual direction, or delivery.
- Offer 2-3 choices only when a real tradeoff exists, and explain the difference briefly.
- Treat "decide for me", "not important", or equivalent wording as authorization to use a reasonable default; do not ask the same question again.
- Stop asking as soon as the project is design-ready.

Do not use a fixed questionnaire. `references/intake-workflow.md` defines readiness and the confirmation gates.

## Source And Meaning Protection

- You may reorganize, compress, and improve expression, but preserve every confirmed core viewpoint.
- Separate source facts from interpretation.
- Resolve contradictions that affect the conclusion before the design brief is confirmed.
- Use customer screenshots, photographs, logos, and documents as real material; do not regenerate them as fictional substitutes.
- Keep public evidence and automatic data corrections visible in the design brief's source and confirmation sections.
- Treat faithful migration versus redesign as a source-handling strategy, not as a substitute for choosing reading versus presentation mode.

## Production Routing

After brief confirmation, load only what the task needs:

- `references/process-playbook.md`: story, evidence, visual, production, and delivery workflow.
- `references/layout-pattern-library.md`: layout selection for composed presentation pages.
- `references/design-quality-rubric.md`: optional diagnosis when the user asks for a design review or says the result feels ordinary; do not use a fixed aesthetic score as the production authorization gate.
- `references/runtime-contract.md`: implemented DOM, controls, state, modes, and extension boundary.
- `assets/html-deck-template/`: dependency-free 16:9 starting shell for paged reading and single-screen presentations.

Use the bundled scripts where relevant:

- `scripts/extract_pdf_pages.py`: render PDF pages into evidence assets.
- `scripts/check_assets.py`: find missing, remote, or non-portable assets.
- `scripts/check_html_deck.py`: exercise routes, reveal states, runtime behavior, media, console errors, bounds, and screenshots.
- `scripts/build_contact_sheet.py`: build a visual QA overview.
- `scripts/package_deck.py`: package HTML plus local assets when a single file is not appropriate.

## Current Runtime Boundary

The standard template supports paged reading and single-screen presentation. It does not yet promise dual-screen presenter view, in-browser editing/export, interactive chart authoring, cross-page morphing, or crash recovery. Keep those capabilities out of user promises until they are implemented and tested.

## Delivery Gate

Before delivery:

- Verify confirmed core viewpoints against the source and brief.
- Check all local and remote asset references.
- Exercise reading and presentation modes, step navigation, whole-page navigation, return-state preservation, and hash routes.
- Check console errors and visible bounds at the target viewport.
- Prefer a single self-contained HTML when it stays responsive; otherwise deliver `index.html + assets` as a zip.
- List any reasonable assumptions made during production that were not already in the confirmed brief.
