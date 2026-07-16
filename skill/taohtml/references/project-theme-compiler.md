# Confirmed VI To Project Theme

Read this reference only after the customer has explicitly replied “确认 VI” for the current single-static-reference board. This step compiles that confirmed VI into a deterministic theme for the current project. It does not add a fifth built-in visual system and does not authorize formal report production.

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

- `theme.json` contains the project identity, executable tokens, page roles, components, preserve/forbidden rules, target mode, input hashes, and explicit static-reference motion boundary.
- `theme.css` applies palette, type hierarchy, spacing/grid, border language, image crop/treatment, cards, panels, labels, data treatment, cover, content, evidence/data, and closing-page structures.
- `templates.html` provides five reusable page variants using the same placeholders and `fragment` / `data-step` syntax as the built-in systems.
- `provenance.json` records every VI item, whether it is observed, extension, or unknown, whether it was compiled, every neutral fallback, and the motion boundary.

The output is project-local. Do not copy it into `assets/visual-systems/`, rename it to one of the four built-in ids, add it to the built-in router, or treat it as a globally available style.

## Boundary Compilation Policy

- Compile `observed` items directly when the contract provides an executable value or a deterministic mapping.
- Compile `extension` items only as report adaptations, preserving their extension status in provenance.
- Retain `unknown` records with `compiled: false`. Never use an unknown item as a token source or relabel it as observed.
- When runtime completeness requires a missing value, use a neutral reversible `fallback`. Record its token, source, and basis in `fallback_records`; never describe it as reference evidence.

The compiler may derive a fixed pixel value from an explicit VI measurement, such as converting a confirmed five-percent outer margin against the 1600px theme canvas. Record that deterministic derivation in the token basis. Do not use free-form model judgment inside the script.

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

The renderer validates the four project-theme files, rejects symlinks, extra files, remote assets, manifest/provenance mismatch, invalid selectors, and incomplete templates. It then injects project CSS and pages into `assets/html-deck-template/index.html`. Do not fork the Runtime or add a project-specific state machine.

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
2. Inspect `provenance.json` for distinct observed, extension, unknown, and fallback records.
3. Run `check_assets.py --strict-offline` on the HTML.
4. Run `check_html_deck.py` at 1366×768, 1600×900, and 1920×1080.
5. Build a contact sheet from the 1600×900 screenshots.
6. Compare the original reference, rendered VI board, and final themed sample. Confirm that composition, hierarchy, components, image treatment, and evidence language—not only colors—carry through.

Use fixed synthetic sample content for visual acceptance and label it as illustrative. Do not present the sample as customer evidence or achieved results.

## Remaining Model Work

The compiler does not understand images, choose report content, decide a narrative, verify evidence provenance, or create project-specific motion. Those remain model/Skill/report-task responsibilities within their existing confirmation and verification gates. This v1 does not support video, multiple references, dynamic-reference analysis, dual-screen presentation, or an HTML editor.
