---
name: taohtml
description: TaoHtml turns ideas, Word/PDF source material, existing slides, and HTML into polished, offline HTML layouts, paged reports, and presentation-ready decks. Use when the user explicitly invokes TaoHtml or asks an agent to understand source material, preserve core viewpoints and evidence, confirm a report design brief, create or redesign visual HTML, add reading or single-screen presentation behavior, or run portable delivery QA.
---

# TaoHtml

Turn source material or an incomplete idea into a finished HTML report that can be read or presented without further layout work. Optimize for a usable report first: ordinary missing details may be completed creatively, then disclosed for customer verification at delivery.

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

1. Identify the route, use mode, and content length one decision at a time; skip every known choice. For presentation mode, treat a user-provided hard duration as a constraint, but never require duration to start.
2. For Word/PDF, read `references/material-understanding.md`, inspect the source, show a Material Understanding Summary, and wait for confirmation or correction. For an idea-only input, do not invent a source-summary gate.
3. Read `references/intake-workflow.md`. Resolve only the current largest missing decision that would change the report design. For an external conversion goal, distinguish the desired action from its verified real action path; do not impose this requirement on non-conversion reports. Complete ordinary missing scenes, numbers, viewpoints, and expression as creative supplements instead of extending intake. Stop according to the reference's readiness, repetition, information-gain, hard-boundary, and question-budget rules.
4. When several report structures are genuinely reasonable, present 2-3 chapter-level options and let the user choose or delegate. Do not ask about structure when one option clearly follows from the confirmed goal and evidence.
5. After content and structure are clear, resolve the visual source. If the user chooses “use my reference” and supplies exactly one static image, read `references/static-reference-vi.md`, pass its current-session readability gate, analyze static design language only, fill its exact v1.1 executable layout grammar with per-field boundaries, render a VI design standards board, and wait for the current board's explicit “确认 VI”. Do not infer dynamic rules, force an internal theme, create a prose-only visual summary, begin project-theme generation, or start formal report production before this confirmation. If a clear reference exists but is a PPT, webpage, video, multiple images, or a state sequence, treat it as unsupported in v1 and ask for one representative static screenshot; do not infer movement or route it as “no reference.” Only when no clear reference exists, read `references/visual-systems.md`, recommend 2-3 suitable built-in systems with name, description, and preview, then accept the user's selection or delegation. Stay inside the existing clarification-question budget; when the budget is exhausted or the user delegates, select one and disclose the choice.
6. After “确认 VI” on the single-static-reference route, read `references/project-theme-compiler.md`, create its hash-bound handoff, and compile the current project's theme before the Report Design Brief. Do not add the result to the four built-in systems, compile an unconfirmed or changed VI, or infer motion from the still. On the no-reference route, keep the selected built-in system instead. Then, after the applicable source gate passes and no hard-boundary gap remains, read `references/design-brief-template.md` and produce one adaptive Report Design Brief. Record the visual source, confirmed VI and compiled project theme when applicable, selected built-in system when applicable, any necessary deviation, and the planned creative-supplement scope. For a conversion goal, record the desired action, exact verified path, provenance and verification status, and final display method. Put outcome-changing safe design inferences in its confirmation section, but do not require the customer to pre-approve every sentence or illustrative value that production may add. VI confirmation is not Report Design Brief confirmation.
7. Wait for explicit confirmation of the current brief. This confirmation does not count toward the clarification-question budget. A previous "agree", "continue", or request to use TaoHtml is not production authorization.
8. After confirmation, read `references/process-playbook.md` and produce the HTML directly. Do not insert a separate full prose manuscript step. Follow its **first runnable artifact** cadence: lock a concise page plan, save a complete runnable `index.html`, then refine and QA in bounded passes. On the single-static-reference route, explicitly load the compiled project theme through the shared renderer; never substitute one of the four built-in themes.
9. Implement only the runtime capabilities documented in `references/runtime-contract.md` unless the user separately authorizes new runtime engineering.
10. Run asset and browser QA, fix objective failures, and report the files, checks, and production-stage judgment calls. Deliver the usable report together with the concise `《待核实内容清单》` defined in `references/process-playbook.md`; do not withhold the report merely because ordinary creative supplements still await customer verification.

If the user adds source material or changes a core viewpoint after confirming the brief, update the brief and request confirmation again. Local copy, color, layout, or motion revisions after delivery do not require a new brief unless they change the report's core meaning or structure.

## Question Discipline

Maintain the `known | confirmed | inferred | missing` ledger defined in `references/intake-workflow.md`. Re-read the conversation, sources, and prior answers before every question; never ask the user to repeat known or safely inferable information.

Ask one decision question per round: the current largest missing item whose answer could change the report design. Do not bundle independent startup choices or turn the intake into a fixed questionnaire.

A clear input may need 0 clarification questions; ordinary intake should usually finish in 3-5; even the most complex idea-only intake must never exceed 6 agent-initiated clarification questions in one intake cycle. Ask about the same key gap at most twice, changing the second attempt to a concrete example or 2-3 real options. Stop as soon as the project is design-ready, and stop questioning after three consecutive rounds without actionable new information.

Infer reversible design decisions transparently and place them in the brief for confirmation. Complete ordinary missing scenes, numbers, viewpoints, and expression during production, track them as `creative supplement | projected content | illustrative content | pending verification`, and disclose them at delivery. Do not describe these customer-facing categories as fabrication or hallucination.

Block only on the hard boundaries in `references/intake-workflow.md`: never invent a real customer or company identity, quotation, citation, literature, or source; never present an illustrative case as an achieved customer outcome; require explicit verification for legal, medical, financial, safety, and similar high-risk facts; and never replace confirmed real sources, data, or action channels. Treat "decide for me", "not important", or equivalent wording as delegation. A user-initiated change to the core goal or scope starts a new intake cycle rather than a seventh question.

## Source And Meaning Protection

- You may reorganize, compress, and improve expression, but preserve every confirmed core viewpoint.
- Separate source facts from interpretation.
- Keep creative supplements distinct from source facts without treating the supplements as automatic errors.
- Resolve contradictions that affect the conclusion before the design brief is confirmed.
- Use customer screenshots, photographs, logos, and documents as real material; do not regenerate them as fictional substitutes.
- Do not rename customer-provided or independently verified facts as creative supplements. Preserve their provenance and exact confirmed meaning.
- Keep public evidence and automatic data corrections visible in the design brief's source and confirmation sections.
- Treat faithful migration versus redesign as a source-handling strategy, not as a substitute for choosing reading versus presentation mode.

## Production Routing

After brief confirmation, load only what the task needs:

- `references/process-playbook.md`: story, evidence, visual, production, and delivery workflow.
- `references/layout-pattern-library.md`: layout selection for composed presentation pages.
- `references/visual-systems.md`: built-in system routing and selection policy; after selection, load only that system's `theme.json`, `theme.css`, and `templates.html` under `assets/visual-systems/`.
- `references/static-reference-vi.md`: single-static-reference readability gate, observed/extension/unknown boundary, exact executable layout grammar, VI board contract, confirmation gate, and next-task handoff.
- `references/project-theme-compiler.md`: post-“确认 VI” hash-bound handoff, deterministic structural project-theme compilation, eligible/compiled usage mapping, fallback policy, explicit project rendering, and verification.
- `references/design-quality-rubric.md`: optional diagnosis when the user asks for a design review or says the result feels ordinary; do not use a fixed aesthetic score as the production authorization gate.
- `references/runtime-contract.md`: implemented DOM, controls, state, modes, and extension boundary.
- `assets/html-deck-template/`: dependency-free 16:9 starting shell for paged reading and single-screen presentations.

Use the bundled scripts where relevant:

- `scripts/extract_pdf_pages.py`: render PDF pages into evidence assets.
- `scripts/check_assets.py`: find missing, remote, or non-portable assets.
- `scripts/check_html_deck.py`: exercise routes, reveal states, runtime behavior, media, console errors, bounds, and screenshots.
- `scripts/build_contact_sheet.py`: build a visual QA overview.
- `scripts/package_deck.py`: package HTML plus local assets when a single file is not appropriate.
- `scripts/render_visual_system.py`: render content through one built-in id or an explicit `--project-theme` directory while retaining the shared runtime shell. Pass a real local source image as `--source-kind verified`; verified provenance is never inferred from a local path. If `source_kind` / `--source-kind` is omitted, the Python API and CLI default to `illustrative` even when a local image is supplied. When no real evidence image exists, use the renderer's automatically labeled illustrative placeholder or pass a local image as `--source-kind illustrative`. The renderer never labels illustrative material as verified evidence.
- `scripts/render_reference_vi.py`: validate the single-static-reference VI contract, embed the verified reference, render the standards-board HTML, and export a 3200×2400 PNG. It does not analyze the image or compile a project theme.
- `scripts/compile_project_theme.py`: validate the exact confirmed-VI handoff and shared executable-layout compatibility matrix, then deterministically write project-local manifest, CSS, templates, and provenance. It does not call a model or add a built-in theme.

## Current Runtime Boundary

The standard template supports paged reading and single-screen presentation. It does not yet promise dual-screen presenter view, in-browser editing/export, interactive chart authoring, cross-page morphing, or crash recovery. Keep those capabilities out of user promises until they are implemented and tested.

## Delivery Gate

Before delivery:

- Build a brief-to-output traceability ledger and verify every confirmed core viewpoint, correction, evidence gap, and decision boundary against a visible output location. For conversion reports, also verify that the real action path is visible, usable, aligned with the desired action, and consistent with its recorded source and verification status. Check every conjunct in compound requirements; a source screenshot may support a point but must not silently replace it in the designed narrative.
- Check all local and remote asset references.
- Exercise reading and presentation modes, step navigation, whole-page navigation, return-state preservation, and hash routes.
- Check console errors and visible bounds at the target viewport.
- Prefer a single self-contained HTML when it stays responsive; otherwise deliver `index.html + assets` as a zip.
- Deliver `《待核实内容清单》` after the report. Each entry must locate the page/content, name the supplement type, state the source status, and recommend `confirm | modify | delete | ask TaoHtml to replace`. Do not collapse the list into a generic disclaimer.
- Keep ordinary projected content in the delivery note so the presentation remains clean. Add an adjacent `示意 / 模拟 / 待核实` label inside the HTML only for simulated charts, fictional customer cases, generated evidence-like artifacts, or data likely to be mistaken for real proof.
