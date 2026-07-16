# Confirmed VI To Project Theme

Read this reference only after the customer has explicitly replied “确认 VI” for the current single-static-reference board. This step compiles that confirmed VI into a deterministic theme for the current project. It does not add a fifth built-in visual system and does not authorize formal report production.

## Contents

- Responsibility and handoff contract
- Fail-closed compilation
- Executable layout and provenance policy
- Shared Runtime rendering
- Verification and remaining model work

## Responsibility Boundary

- The model understands the single still image and produces the confirmed VI JSON under `static-reference-vi.md`.
- The Skill maintains the observed / extension / unknown boundary and requires the confirmation handoff below.
- `scripts/compile_project_theme.py` validates the handoff and deterministically writes the project theme.
- `scripts/render_visual_system.py --project-theme ...` injects that theme into the existing shared Runtime shell.

Never infer motion, transitions, timing, interaction, or sequential state from a still image. The project manifest records motion as a TaoHtml Runtime and report-task decision with `observed_from_reference: false`.

## Minimal Handoff Contract

Create one UTF-8 JSON file beside the confirmed VI JSON and reference image. Use exactly these keys:

```json
{
  "schema_version": "1.0",
  "project": {
    "id": "urban-renewal-observation",
    "display_name": "城市更新观察｜项目专用主题"
  },
  "confirmation": {
    "status": "confirmed",
    "phrase": "确认 VI",
    "vi_contract_sha256": "<64 lowercase hex characters>",
    "reference_image_sha256": "<64 lowercase hex characters>"
  },
  "inputs": {
    "vi_contract": "reference-vi-contract.json",
    "reference_image": "reference.png"
  },
  "target_mode": "presentation",
  "customer_corrections": [
    "已并入当前 VI 的客户修正；没有修正时使用空数组。"
  ]
}
```

Use `reading` or `presentation` for `target_mode`. Use a lowercase hyphenated slug for `project.id`. Keep input paths relative to the handoff file and inside the same handoff directory. Compute SHA-256 after the current VI JSON and reference image are final. The hashes bind “确认 VI” to exact bytes; changing either file invalidates the handoff and requires a new confirmation.

Do not record an approval timestamp, machine path, or volatile build metadata in the contract. The minimal contract stays portable and produces byte-identical theme assets from identical inputs.

## Fail-Closed Gate

Compilation must stop before creating the output directory when any of these is true:

- confirmation status is not `confirmed` or phrase is not exactly `确认 VI`;
- the handoff has missing or extra schema fields;
- an input path is absolute, leaves the handoff directory, is missing, or is not a regular file;
- either SHA-256 digest does not match the current file;
- the VI JSON fails the validator in `render_reference_vi.py`;
- the reference image is unreadable, active SVG, or contains a non-offline SVG reference;
- target mode, project id, or customer corrections violate the contract.

Never repair, downgrade, or silently regenerate the confirmed inputs inside the compiler.

## Compile

Run:

```bash
python scripts/compile_project_theme.py \
  --request /absolute/path/to/confirmed-vi-handoff.json \
  --output-theme /absolute/path/to/project-theme
```

The output directory contains exactly:

```text
project-theme/
├── theme.json
├── theme.css
├── templates.html
└── provenance.json
```

- `theme.json` contains the project identity, executable tokens, normalized `executable_layout`, per-field `structure_sources`, generated page roles, components, preserve/forbidden rules, target mode, input hashes, and explicit static-reference motion boundary.
- `theme.css` applies palette, type hierarchy, spacing/grid, border language, image crop/treatment, cards, panels, labels, data treatment, cover, content, evidence/data, and closing-page structures selected from the executable layout grammar.
- `templates.html` provides five reusable, grammar-selected DOM variants using the same placeholders and `fragment` / `data-step` syntax as the built-in systems. It is not a fixed template set with VI color substitution.
- `provenance.json` records every VI item, eligibility, actual compiled state, concrete usage targets, every neutral fallback, and the motion boundary.

The output is project-local. Do not copy it into `assets/visual-systems/`, rename it to one of the four built-in ids, add it to the built-in router, or treat it as a globally available style.

## Boundary Compilation Policy

- `eligible: true` means an `observed` or `extension` item may enter deterministic compilation. Eligibility alone never implies use.
- Set `compiled: true` only when the item actually enters a token, CSS rule, template DOM branch, manifest execution field, or explicit preserve/forbidden guardrail. Every compiled record must list concrete `usage` targets.
- An unused `observed` or `extension` item remains `eligible: true`, `compiled: false`, with an empty usage list. Descriptive layout, component, imagery, evidence, or miniature copy must not be promoted merely because it appears in the confirmed JSON.
- Compile `extension` items only as report adaptations and preserve their extension status in provenance.
- Retain `unknown` records with `eligible: false`, `compiled: false`, and no usage. Never use an unknown item as a token source or relabel it as observed.
- When runtime completeness requires a missing value, use a neutral reversible `fallback`. Record its token or executable-layout field, value, source, basis, and concrete usage in `fallback_records`; never describe it as reference evidence.

The compiler reads structure only from the exact `executable_layout` object defined in `static-reference-vi.md`. It uses those enums to choose cover split versus single-column DOM, card grid versus stack/single-focus content, row versus column process, evidence/data DOM, image placement/ratio/fit/treatment, module border/radius/shadow language, density, alignment, and focus. Natural-language descriptions remain review context and may supply parseable scalar tokens such as an explicit margin, but they are not the primary source of structural branching.

`scripts/project_theme_layout.py` is the machine single source for the enum sets, neutral fallbacks, and cover/image, content/columns, and data/columns compatibility matrices. Both VI validation and the production theme loader call it. Every accepted concrete value must reach a DOM branch, computed CSS geometry, manifest execution field, and accurate provenance usage; a class name or layout id alone does not count. Undefined combinations fail during VI validation with the incompatible fields and allowed values. Do not silently normalize a concrete contract. Compatibility-aware unknown fallbacks remain allowed only when they are separately recorded and the unknown boundary stays `compiled: false`.

The v1 image placement program is exact: split covers accept left/right, single-column covers accept top/bottom/background, and a source/chart split additionally requires left/right. Background creates an absolute visual layer and requires cover fit. Content stacks and single-focus pages are one-column; card grids accept one to three. Chart/table focus pages are one-column, source/chart splits are two-column, and metric grids apply one to three columns to their inner metric cards.

The compiler may derive a fixed pixel value from an explicit VI measurement, such as converting a confirmed five-percent outer margin against the 1600px theme canvas. Record that deterministic derivation in the token basis. Do not use free-form model judgment inside the script.

## Semantic Rhythm Policy

The project theme does not use heading margins to encode relationships. Its scoped low-level reset sets `h1`, `h2`, `h3`, and `p` margins to zero; the nearest semantic container owns the space between its direct children through CSS `gap`. This prevents a more-specific reset from silently collapsing an intended label-to-title distance.

The confirmed `executable_layout.density` enum deterministically selects five relationship tokens:

| Density | label → title | title → lede | page heading → content | card title → body | evidence → source |
|---|---:|---:|---:|---:|---:|
| `low` | 24px | 20px | 44px | 14px | 20px |
| `medium` | 18px | 16px | 32px | 12px | 18px |
| `high` | 12px | 10px | 24px | 8px | 12px |

These compile to `theme.json` tokens and `--pt-rhythm-*` CSS properties, with exact provenance usage targets attributed to `executable_layout.density`. An unknown density does not become observed; it uses the neutral `medium` scale and produces separate field and token fallback records.

Generated templates mark the relationship owner and its direct endpoints with `data-rhythm-check`, `data-rhythm-from`, and `data-rhythm-to`. Horizontal relationships additionally use `data-rhythm-axis="inline"`; vertical relationships default to the block axis. `check_html_deck.py` measures the computed browser rectangles and fails when the actual distance differs from the declared token. This check complements overflow QA: a page can fit its viewport and still have a broken visual relationship.

## Render Through The Shared Runtime

Render a report explicitly with the compiled directory:

```bash
python scripts/render_visual_system.py \
  --content /absolute/path/to/content.json \
  --project-theme /absolute/path/to/project-theme \
  --source-image /absolute/path/to/local-visual.svg \
  --source-kind illustrative \
  --output /absolute/path/to/report.html
```

Use `--source-kind verified` only when the local image is grounded in confirmed source material. A generated image, ordinary local file, or missing source kind remains illustrative and receives the adjacent `示意 / 待核实` label. Project themes never weaken this fail-safe source contract.

The renderer validates the four project-theme files, rejects symlinks, extra files, remote assets, invalid selectors, and incomplete templates. For every machine-executed layout field it also checks that manifest value, structure source, provenance status/value/compiled flag/usage targets, neutral fallback when applicable, and template `data-layout` ids agree. It then injects project CSS and pages into `assets/html-deck-template/index.html`. Do not fork the Runtime or add a project-specific state machine.

The four built-in calls remain unchanged:

```bash
python scripts/render_visual_system.py \
  --content /absolute/path/to/content.json \
  --theme rigorous-consulting-report \
  --output /absolute/path/to/report.html
```

## Verification

For the compiled theme and at least one full sample deck:

1. Compile twice into separate directories and compare every output file hash.
2. Compile a second, schema-complete VI with an intentionally opposite layout grammar. Compare `templates.html`, key DOM classes, structural CSS, `layout_variants`, and `identity.composition`; all must differ.
3. Parameterize every allowed compatibility-matrix pair and every remaining scalar enum. Require an expected DOM order/branch or structural CSS value for each legal case, and a clear validation error for every illegal pair.
4. Inspect `provenance.json` for distinct observed, extension, unknown, and fallback records, concrete usage targets, and at least one eligible-but-unused record that remains `compiled: false`.
5. Run `check_assets.py --strict-offline` on the HTML.
6. Run `check_html_deck.py` at 1366×768, 1600×900, and 1920×1080; require empty overflow and semantic-rhythm failure lists on every page.
7. Build a contact sheet from the 1600×900 screenshots.
8. Compare the original reference, rendered VI board, and final themed sample. Confirm that composition, hierarchy, components, image treatment, and evidence language—not only colors—carry through.

Use fixed synthetic sample content for visual acceptance and label it as illustrative. Do not present the sample as customer evidence or achieved results.

## Remaining Model Work

The compiler does not understand images, choose report content, decide a narrative, verify evidence provenance, or create project-specific motion. Those remain model/Skill/report-task responsibilities within their existing confirmation and verification gates. This v1 does not support video, multiple references, dynamic-reference analysis, dual-screen presentation, or an HTML editor.
