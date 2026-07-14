# Changelog

TaoHtml follows Semantic Versioning. Release tags use the `vMAJOR.MINOR.PATCH` form.

## [Unreleased]

### Added

- Add the first Word/PDF vertical-slice workflow with material-summary and design-brief confirmation gates.
- Add a documented minimal runtime contract for reading and single-screen presentation.
- Add strict offline asset validation and runtime behavior checks.

### Changed

- Separate presentation steps from whole-page navigation and preserve per-page reveal state.
- Add reading/presentation switching, fullscreen control, page count, and auto-hiding controls to the template.
- Run browser QA at three target viewports in CI.

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
