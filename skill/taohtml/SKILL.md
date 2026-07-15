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

1. **Idea only**: build the report definition from the conversation, then produce a brief only when it is design-ready.
2. **Word / PDF**: extract and confirm the material before design. This is the fully specified reference route.
3. **Existing PPT / HTML**: confirm whether to preserve the structure or reorganize it while keeping all core viewpoints.

Never ask for information already present in the conversation or source files.

## Required State Flow

Follow this route-aware sequence without skipping confirmation gates:

1. Identify the route, use mode, and length. When more than one is missing, compress these startup choices into one short interaction; skip known choices.
2. For Word/PDF, read `references/material-understanding.md`, inspect the source, show a Material Understanding Summary, and wait for confirmation or correction. For an idea-only input, do not invent a source-summary gate.
3. Read `references/intake-workflow.md`. Resolve only the current largest missing decision that would change the report design. Stop according to its readiness, repetition, information-gain, risk, and question-budget rules.
4. When several report structures are genuinely reasonable, present 2-3 chapter-level options and let the user choose or delegate. Do not ask about structure when one option clearly follows from the confirmed goal and evidence.
5. After the applicable source gate passes and no high-risk gap remains, read `references/design-brief-template.md` and produce one adaptive Report Design Brief. Put every safe inference in its confirmation section.
6. Wait for explicit confirmation of the current brief. This confirmation does not count toward the clarification-question budget. A previous "agree", "continue", or request to use TaoHtml is not production authorization.
7. After confirmation, read `references/process-playbook.md` and produce the HTML directly. Do not insert a separate full prose manuscript step. Follow its **first runnable artifact** cadence: lock a concise page plan, save a complete runnable `index.html`, then refine and QA in bounded passes.
8. Implement only the runtime capabilities documented in `references/runtime-contract.md` unless the user separately authorizes new runtime engineering.
9. Run asset and browser QA, fix objective failures, and report the files, checks, and production-stage judgment calls.

If the user adds source material or changes a core viewpoint after confirming the brief, update the brief and request confirmation again. Local copy, color, layout, or motion revisions after delivery do not require a new brief unless they change the report's core meaning or structure.

## Question Discipline

Maintain the `known | confirmed | inferred | missing` ledger defined in `references/intake-workflow.md`. Re-read the conversation, sources, and prior answers before every question; never ask the user to repeat known or safely inferable information.

Ask one decision question per round: the current largest missing item whose answer could change the report design. Closely related items may be combined only when they decide the same thing; the compact startup choice is the explicit exception. Do not turn the intake into a fixed questionnaire.

A clear input may need 0 clarification questions; ordinary intake should usually finish in 3-5; never exceed 6 agent-initiated clarification questions in one intake cycle. Ask about the same key gap at most twice, changing the second attempt to a concrete example or 2-3 real options. Stop questioning after three consecutive rounds without actionable new information.

Infer low-risk gaps transparently and place them in the brief for confirmation. If a high-risk gap remains, do not fabricate a brief or start production; use the blocked-intake output in `references/intake-workflow.md`. Treat "decide for me", "not important", or equivalent wording as delegation. A user-initiated change to the core goal or scope starts a new intake cycle rather than a seventh question.

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

- Build a brief-to-output traceability ledger and verify every confirmed core viewpoint, correction, evidence gap, and decision boundary against a visible output location. Check every conjunct in compound requirements; a source screenshot may support a point but must not silently replace it in the designed narrative.
- Check all local and remote asset references.
- Exercise reading and presentation modes, step navigation, whole-page navigation, return-state preservation, and hash routes.
- Check console errors and visible bounds at the target viewport.
- Prefer a single self-contained HTML when it stays responsive; otherwise deliver `index.html + assets` as a zip.
- List any reasonable assumptions made during production that were not already in the confirmed brief.
