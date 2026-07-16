# Changelog

TaoHtml follows Semantic Versioning. Release tags use the `vMAJOR.MINOR.PATCH` form.

## [Unreleased]

### Added

- Add a hash-bound confirmed-VI handoff and deterministic compiler for project-local theme manifests, CSS, page templates, and provenance.
- Add fail-closed coverage for confirmation, schema, paths, input hashes, observed/extension/unknown boundaries, neutral fallbacks, offline output, and deterministic reproduction.

### Changed

- Allow the production renderer to load an explicit project theme while preserving all four built-in theme ids and the shared Runtime shell.

### Fixed

- Wait for reveal transitions to settle before browser QA captures final-state screenshots.

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
