# Built-In Visual Systems

Use this router only after content and chapter structure are clear. Its purpose is to choose a reusable visual grammar without turning intake into an aesthetic interview.

## Reference Precedence

A unique eligible active enterprise profile remains the automatic route defined in `profile-memory.md`; do not enter this router, reopen its reference images, or present built-in choices for that route.

When the user chooses “use my reference” and supplies one supported reconstruct still or one to three supported corporate-family stills, do not use this router. Read `static-reference-vi.md`, apply its current-session readability gate, extract only visible static composition, hierarchy, image treatment, module language, and evidence treatment, render the unified VI standards board, and wait for clear confirmation of that exact current board. Do not infer dynamic rules, force one of the built-in systems, or reduce the reference to colors.

If the current session cannot reliably locate static visual facts, follow the two recovery paths in `static-reference-vi.md`; do not guess or maintain a model matrix here. A clear PPT, webpage, video, state sequence, more than three corporate screenshots, or multiple reconstruct screenshots is an unsupported reference input rather than “no clear reference”: ask for a supported representative raster input and do not enter this router unless the customer explicitly abandons the reference route. Never infer movement from those sources.

## Catalog Display And Selection

When no clear reference exists and no enterprise profile applies, enter this router. Apply one of these mutually exclusive rules:

- If the user has already specified one concrete built-in system, adopt it directly without displaying the catalog.
- Show a category subset only when the user has proactively and explicitly constrained the acceptable range of the built-in catalog and that constraint maps unambiguously to one declared category. Determine the user's stated scope from meaning rather than literal phrase matching. The current business-oriented subset is **严谨咨询报告** and **稳重企业年报**; the current design-led or less-business-oriented subset is **黑白荧光卡片** and **杂志图文拼贴**.
- Otherwise, in the same round, show every system in the complete current built-in catalog below. Include each exact customer-facing name, one-line description, and bundled preview. Never omit a catalog entry because the Agent considers it less suitable.

Report goal, audience, content, report type, and reading or presentation mode are recommendation inputs only. Use them to mark one or two displayed systems as **更推荐** and briefly explain the reason, but never to shrink the catalog or treat them as a user catalog-range constraint. Recommendation may order attention, but recommendation never replaces complete catalog display or removes an entry.

If a user preference or constraint does not map unambiguously to a declared category, show the complete current catalog, reflect that preference in the recommendation reason, and never invent an ad hoc subset.

Read the complete current catalog rather than a fixed count or shortlist. Future built-in additions automatically join the default complete display; update the catalog metadata and preview table with the new system instead of retaining a four-system or shortlist cap.

Keep catalog display, recommendation marking, and selection in one selection round. Let the user choose once or delegate to TaoHtml. Never ask an open-ended taste question. Theme selection shares the existing six-question budget. At the cap, after three no-gain rounds, or under delegation, do not open another selection round: show the applicable catalog if it has not yet been shown, choose the lowest-risk fit, and disclose it in the Report Design Brief.

## Customer-Facing Route Table

| System | Exact description | Best fit | Preview |
|---|---|---|---|
| 黑白荧光卡片 | 高反差、模块卡片、大标题，适合路演和强表达 | Pitch, launch, manifesto, decisive sales story | `assets/visual-systems/black-white-fluorescent-cards/preview.svg` |
| 严谨咨询报告 | 白底、结论式标题、高信息密度、严谨图表 | Strategy, diagnosis, research, evidence-heavy internal decision | `assets/visual-systems/rigorous-consulting-report/preview.svg` |
| 稳重企业年报 | 稳重配色、图文平衡、品牌化版面、适度留白 | Board update, annual review, corporate narrative, ESG | `assets/visual-systems/corporate-annual-report/preview.svg` |
| 杂志图文拼贴 | 图片切片、错位排版、大字标题和编辑杂志感 | Brand story, culture, editorial feature, image-led thought leadership | `assets/visual-systems/editorial-collage/preview.svg` |

Customer-facing naming always follows a familiar layout or visual name plus one concrete picture description. Preserve the four names and descriptions exactly.

## Load Only The Selected System

After selection, load only these files from the selected directory:

1. `theme.json` for identity, tokens, canvas, component, evidence, image, motion, and forbidden rules.
2. `theme.css` for executable tokens and component/layout styling.
3. `templates.html` for copyable page variants and low-capability-model examples.

Use `preview.svg` only when presenting the choice. Do not load all four manifests or templates into the production context.

## Runtime Isolation

Treat `assets/html-deck-template/index.html` as the runtime shell and the selected system as the presentation layer. Replace content sections and inject theme CSS, but keep runtime controls, navigation, hash routing, reveal state, fullscreen behavior, and offline constraints unchanged. A theme switch must never add a new state machine or require a remote asset.

This router remains exactly four built-in systems in the current catalog; that current asset count is not a future catalog or default-display cap. A theme compiled after current-board confirmation is project-local and must be loaded explicitly with `--project-theme` under `project-theme-compiler.md`; never add it to this table or built-in asset directory.

Use the production renderer with an explicit source kind. For a real local source image:

```bash
python scripts/render_visual_system.py \
  --content /absolute/path/to/content.json \
  --theme black-white-fluorescent-cards \
  --source-image /absolute/path/to/verified-evidence.png \
  --source-kind verified \
  --output /absolute/path/to/report.html
```

The renderer accepts readable PNG, JPEG, WebP, or safe SVG files, validates the file contents, and embeds the bytes as an offline `data:` URI. `--source-kind verified` requires `--source-image` and means the Agent has grounded the image in customer material or another confirmed source. A local file path alone never establishes provenance: when `source_kind` / `--source-kind` is omitted, both the Python API and CLI fail safe to `illustrative`, even if `source_image` / `--source-image` is present. If a verified file is missing, unsupported, unreadable, active, or remotely linked, rendering fails; the renderer never substitutes illustrative material under a verified label.

When no real evidence image exists, omit `--source-image` or pass a local generated image with `--source-kind illustrative`. The renderer then uses or embeds an illustrative image and automatically places an adjacent `示意 / 待核实` label. This keeps idea-only production moving without presenting the visual as source evidence. Record the specific illustration, simulated values, and related claims in `《待核实内容清单》`. Never use an illustrative mode to replace a confirmed real customer screenshot, chart, logo, source page, or data point.

## Deviation Rule

Preserve the selected system across composition, hierarchy, image treatment, cards/modules, chart and evidence treatment, and motion. Deviate only when the source material, accessibility, or confirmed brand constraint requires it. Record the exact deviation and reason in the Report Design Brief.
