# Changelog

TaoHtml follows Semantic Versioning. Release tags use the `vMAJOR.MINOR.PATCH` form.

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
