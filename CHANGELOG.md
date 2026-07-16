# Changelog

TaoHtml follows Semantic Versioning. Release tags use the `vMAJOR.MINOR.PATCH` form.

## [Unreleased]

## [0.3.2] - 2026-07-16

### Added

- Add a standard-library environment preflight with capability-specific `core`, `pdf`, `static-reference`, and `browser` profiles, machine-readable JSON, customer-readable recovery choices, isolated dependency imports, and a real Chromium launch/minimal-screenshot probe.
- Add a skill-local dependency declaration carried by raw Skill, marketplace, and Skill Hub packages, plus a `windows-latest` smoke job for imports, preflight, Chromium, static-reference VI rendering, and project-theme compilation.
- Add a current-task production-authorization state checker that verifies each confirmed gate's safe task-local path and current file SHA-256, exposes the allowed next gate artifact, and blocks formal HTML, browser QA, and delivery until every applicable material-summary, VI, project-theme, and design-brief gate is complete.
- Add rendered browser QA gates for a named controlled-presentation-step contract, active-slide canvas coverage, and independent visible HTML/SVG text collisions with a one-pixel safety gap and local reasoned opt-outs.

### Changed

- Start every new invocation with a route handshake: explicit topics and task-bound materials advance immediately, while input-free invocations show the three entry routes before any material analysis, brief, or HTML work.
- Bind compact answers only to the Agent's latest active conversation options, and require every used material to record a current upload/user instruction, explicit task instruction, or user-confirmed candidate path as its source binding.
- Require capability preflight immediately before PDF extraction, customer-reference image processing, and browser QA without making idea-only reports on built-in visual systems depend on the heavier reference/browser chain.
- Bind VI and formal-production confirmations to the exact current artifact bytes, current conversation reference, and source hashes instead of treating a fixed reply phrase as a reusable authorization token; keep published VI handoff v1.0/v1.1 readable and assign the new `confirmation_ref` shapes to v2.0/v2.1.

### Fixed

- Prevent low-information platform placeholder text and stale workspace conventions such as `input/prompt.md` from being interpreted as a report route or current source.
- Fail fast when the customer-reference rendering chain is unavailable: do not bypass deterministic corporate fidelity manually, and do not present reference-style reconstruction as a downgrade because it uses the same Pillow/Playwright/Chromium path.
- Reject presentation-mode decks with zero controlled steps, slides whose rendered rectangle underfills the deck canvas, and colliding chart/text labels instead of allowing vacuous or container-only QA passes; distinguish shallow HTML Range font-metric overlap in separated normal-flow boxes from positioned/transformed HTML and SVG collisions.

### Verification scope

- Windows claims are limited to the automated `windows-latest` smoke path. WorkBuddy's managed Windows runtime, policies, installed browser, and native stability still require an on-device acceptance run; this release does not claim support for every WorkBuddy Windows environment.

## [0.3.1] - 2026-07-16

### Fixed

- Generate the Skill Hub root `SKILL.md` as a Chinese, text-only customer overview derived deterministically from the GitHub README, while packaging the canonical Agent execution body separately as `references/agent-workflow.md` and requiring it to be read before execution.
- Keep README screenshots out of the Skill Hub package and add drift, execution-source, image-exclusion, and deterministic-packaging regression coverage for the channel split.

## [0.3.0] - 2026-07-16

### Added

- Add a three-scenario quality benchmark for idea-only conversion talks, evidence-faithful PDF reports, and content-locked HTML upgrades, with isolated executor inputs, machine-readable results, human review dimensions, and cross-run aggregation ([#5](https://github.com/TaoGEO/TaoHtml/pull/5)).
- Add four executable built-in visual systems—黑白荧光卡片、严谨咨询报告、稳重企业年报、杂志图文拼贴—with machine-readable tokens, layout/component grammar, five-page templates, previews, and deterministic same-content samples ([#6](https://github.com/TaoGEO/TaoHtml/pull/6)).
- Add verified and illustrative source modes to the visual renderer. Verified mode requires a real local source image; illustrative mode uses an adjacent `示意 / 待核实` label instead of presenting generated material as source evidence ([#6](https://github.com/TaoGEO/TaoHtml/pull/6), [#7](https://github.com/TaoGEO/TaoHtml/pull/7)).
- Add a structured delivery-time `《待核实内容清单》` and benchmark-level `PASS / CONDITIONAL / FAIL` semantics that separate artifact usability from verification-handoff completeness ([#7](https://github.com/TaoGEO/TaoHtml/pull/7)).
- Add the single-static-reference VI workflow: a deterministic 3200×2400 standards board that distinguishes directly observed facts, report adaptations, and unknowns before the user confirms the VI ([#8](https://github.com/TaoGEO/TaoHtml/pull/8)).
- Add a hash-bound confirmed-VI handoff and deterministic project-theme compiler for manifests, CSS, page templates, semantic rhythm, provenance, and structurally distinct cover/content/process/evidence/closing layouts ([#9](https://github.com/TaoGEO/TaoHtml/pull/9)).
- Add corporate template fidelity for one to three same-family screenshots, including `cover / toc / section / content / data` role recognition, screenshot-cropped fixed assets, safe editable regions, multi-shell routing, and backward-compatible v1.1/v1.2 inputs ([#10](https://github.com/TaoGEO/TaoHtml/pull/10)).
- Add public, self-made, unbranded corporate-family fixtures plus a five-page acceptance sample and VI board; no real client screenshots or derivative assets are included ([#10](https://github.com/TaoGEO/TaoHtml/pull/10)).

### Changed

- Require conversion-oriented reports to record a sourced or verified real action path, not only persuasive CTA wording; explanatory, educational, and internal reports do not gain an unnecessary CTA questionnaire item ([#3](https://github.com/TaoGEO/TaoHtml/pull/3)).
- Ask only one outcome-changing idea-intake question per round, distinguish content length from optional presentation duration, skip already known decisions, preserve the six-question cap, and stop immediately when the project is design-ready ([#4](https://github.com/TaoGEO/TaoHtml/pull/4)).
- Record platform token and billing usage only when exact values and provenance are available; unavailable WorkBuddy points remain unavailable instead of being reported as zero or estimated ([#5](https://github.com/TaoGEO/TaoHtml/pull/5)).
- Shift ordinary evidence gaps to an output-first workflow: complete reversible creative supplements during production, deliver the usable report first, then disclose those supplements for verification while preserving hard boundaries around real identities, quotations, sources, achieved results, high-risk facts, and confirmed channels ([#7](https://github.com/TaoGEO/TaoHtml/pull/7)).
- Route supported static references through `reference -> VI board -> 确认 VI -> project theme`, without forcing one of the four built-in systems or inferring motion from static frames ([#8](https://github.com/TaoGEO/TaoHtml/pull/8), [#9](https://github.com/TaoGEO/TaoHtml/pull/9)).
- Compile exact executable-layout enums into materially different DOM/CSS programs and make semantic containers own typography spacing through density-derived `gap` tokens measured in Chromium ([#9](https://github.com/TaoGEO/TaoHtml/pull/9)).
- Preserve screenshot-visible corporate pixels only: fixed crops stay immobile, report content stays inside the matching shell's editable region, and fidelity does not claim recovery of PPT masters, vector logos, source fonts, unseen assets, or motion ([#10](https://github.com/TaoGEO/TaoHtml/pull/10)).

### Fixed

- Prevent benchmark false positives by keeping unavailable usage out of medians/ranges and by judging artifact usability separately from workflow disclosure ([#5](https://github.com/TaoGEO/TaoHtml/pull/5), [#7](https://github.com/TaoGEO/TaoHtml/pull/7)).
- Require verified source evidence in generated visual-system samples and harden adjacent evidence labels and delivery handoffs so illustrative content cannot be mistaken for confirmed source material ([#6](https://github.com/TaoGEO/TaoHtml/pull/6), [#7](https://github.com/TaoGEO/TaoHtml/pull/7)).
- Wait for reveal transitions before browser screenshots, keep eligible-but-unused VI records uncompiled, prevent scoped heading resets from collapsing confirmed rhythm, and reject incompatible layout combinations instead of silently normalizing them ([#9](https://github.com/TaoGEO/TaoHtml/pull/9)).
- Reject corporate-theme drift in decoded crop bytes, hashes, dimensions, source/role mappings, placement, editable regions, active content, event handlers, `javascript:` URLs, and any noncanonical CSS rule that can directly target fixed layers or their pseudo-elements ([#10](https://github.com/TaoGEO/TaoHtml/pull/10)).

## [0.2.0] - 2026-07-15

### Added

- Add the first Word/PDF vertical-slice workflow with material-summary and design-brief confirmation gates.
- Add a documented minimal runtime contract for reading and single-screen presentation.
- Add strict offline asset validation and runtime behavior checks.
- Add a self-contained local marketplace ZIP for Codex and Claude Code, generated from the canonical Skill source.

### Changed

- Separate presentation steps from whole-page navigation and preserve per-page reveal state.
- Add reading/presentation switching, fullscreen control, page count, and auto-hiding controls to the template.
- Require an early runnable `index.html` during production and a brief-to-output traceability check before delivery.
- Run browser QA at three target viewports in CI.
- Document the supported Claude GitHub marketplace, raw Skill, and offline ZIP installation and update paths.

### Fixed

- Make the Claude GitHub marketplace install from the repository root and use commit-based updates without a pinned manifest version.

## [0.1.0] - 2026-07-13

### Added

- Add the first explicit project version and repository quality workflow.
- Add automated checks for skill metadata, portable assets, packaging, and browser rendering.
- Add a portable source-evidence placeholder to the bundled HTML deck template.

### Changed

- Expand asset discovery to cover `data-source` and `srcset` references.
- Exercise hash routing, staged fragments, source modals, console errors, media loading, and visible bounds during browser QA.
- Make direct hash navigation update the active slide in the bundled template.

### Fixed

- Prevent the template source modal from opening a missing example image.
- Prevent asset and browser checks from reporting success when interactive source evidence is broken.
