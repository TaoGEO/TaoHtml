# Single Static Reference To VI Board

Read this reference only when the customer chooses “use my reference” and supplies exactly one static image. This v1 route turns that image into a customer-viewable VI design standards board before any project theme or report production begins.

## Contents

- Scope and readability gate
- Boundary labels and extraction dimensions
- Minimal structured contract and executable layout grammar
- Deterministic render and confirmation
- Confirmed-VI handoff

## Scope Boundary

Analyze only visual properties visible in the supplied still image. Do not inspect, infer, or write rules for movement, animation, transitions, timing, or sequential states. A still image cannot establish those facts.

Route here only for exactly one still image. A clear reference supplied as a PPT, webpage, dynamic HTML, video, multiple images, or a screenshot/state sequence is an unsupported reference input in v1, not “no clear reference.” State the boundary and ask the customer to provide one representative static screenshot. Do not infer movement from the source, silently reduce it to this contract, or route it to the four built-in systems unless the customer explicitly abandons the reference route.

The model performs visual understanding and fills both the descriptive observations and the machine-executable layout grammar. This reference defines the extraction dimensions, evidence boundary, confirmation gate, and handoff contract. `scripts/render_reference_vi.py` only validates structured data, embeds the verified local reference, renders the fixed HTML/CSS board, and exports PNG.

## Current-Session Readability Gate

Treat model choice as a platform or session-entry decision, not a mid-task TaoHtml workflow. Never claim that an Agent can switch models automatically inside the current task, never maintain a cross-platform model matrix, and never recommend a named model here.

- On first use in WorkBuddy, say only that Auto is recommended. Do not ask which model is active and do not ask the customer to switch repeatedly during the task.
- In Codex and Claude Code, continue with the current session model without recommending another model.

Before analysis, perform only a minimal readability check in the current session: verify that the image opens and accurately identify a few locatable static facts, such as where the main heading sits, which large color fields are visible, or where a hard border appears. This is a capability check, not customer-facing VI analysis and not a scoring system.

If those facts can be located reliably, continue. If they cannot, stop and say exactly:

> 当前会话无法可靠读取参考图

Then offer only two recovery paths: the customer may manually change the model at the platform/session entry and restart the reference task, or downgrade to TaoHtml's four built-in visual systems. Do not guess, do not create a partial VI board, and do not turn the failure into a model-selection interview.

## Boundary Labels

Assign one explicit `status` to every item. Never default or silently promote a status.

| Status | Customer label | Use |
|---|---|---|
| `observed` | 直接观察 | The property is visibly supported by a named region of the reference. |
| `extension` | 报告适配建议 | The property is a reversible proposal for adapting the observed language to a report. |
| `unknown` | 参考中无法判断 | The category is absent, cropped, illegible, or otherwise unsupported by the reference. |

For every item, write a concise `basis`. Point `observed` items to the visible region or repeated feature, explain the adaptation logic for `extension`, and state exactly why the reference cannot support an `unknown` item. An absent category must remain `unknown`; never fill it with an invented observation.

## Required Extraction Dimensions

Create one board that includes all of these dimensions. A dimension not shown by the reference still appears as an `unknown` item so the omission is visible rather than silently fabricated.

1. Reference thumbnail and a plain-language scope label.
2. Palette with only the exact hex values that can be sampled or carefully estimated from the visible image. One or two supported colors are sufficient; never invent a third color to fill the board.
3. Typography hierarchy with level, visible sample, size/weight/line-height description, and boundary status.
4. Grid, whitespace, outer margin, column, alignment, and spacing rhythm.
5. Cards, panels, labels, borders, rules, corners, shadows, and other visible component language.
6. Image crop, aspect ratio, masking, color treatment, captions, and annotation treatment.
7. Only chart or evidence language actually visible in the image; otherwise mark the category `unknown` and keep any report adaptation separate as `extension`.
8. Cover, content, and data-page miniatures. These are report adaptations unless the corresponding page type is directly visible in the reference.
9. Preserve and avoid guardrails, each tied to observed evidence or clearly labeled adaptation logic.
10. Executable layout grammar for page axis/alignment, cover structure, content organization, image position/ratio/treatment, data structure, module organization, density, and visual focus. Assign status and basis field by field; never derive these values later by keyword-matching prose descriptions.

Do not reduce the result to a prose “visual DNA summary.” The PNG board is the primary customer deliverable; the JSON is an internal rendering contract.

## Minimal Structured Contract

Use UTF-8 JSON with these exact top-level keys:

```json
{
  "schema_version": "1.1",
  "board": {
    "title": "VI 设计标准图",
    "subtitle": "基于单张静态参考的视觉语言确认稿",
    "reference_label": "客户静态参考"
  },
  "palette": [
    {"name": "主墨色", "value": "#111111", "role": "标题与边框", "status": "observed", "basis": "标题与粗边框"},
    {"name": "强调色", "value": "#C84B3F", "role": "标签与关键数据", "status": "observed", "basis": "页首标签与数据柱"},
    {"name": "纸张色", "value": "#F4EFE5", "role": "画布与卡片底色", "status": "observed", "basis": "整页底色与卡片留白"}
  ],
  "typography": [
    {"level": "H1", "sample": "结论先行", "spec": "约 64px / 粗黑 / 紧行距", "status": "observed", "basis": "左上主标题"},
    {"level": "BODY", "sample": "正文说明", "spec": "约 20px / 常规 / 宽松行距", "status": "observed", "basis": "主标题下方说明文字"}
  ],
  "layout": [
    {"label": "外边距", "value": "约画布宽度的 6%", "status": "observed", "basis": "四周稳定留白"},
    {"label": "模块间距", "value": "约 24px", "status": "extension", "basis": "把可见间距适配为报告节奏"}
  ],
  "executable_layout": {
    "page_axis": {"value": "row", "status": "observed", "basis": "主要模块沿横向展开"},
    "alignment": {"value": "start", "status": "observed", "basis": "标题与正文统一左对齐"},
    "cover_structure": {"value": "split", "status": "extension", "basis": "把标题和主图分区适配为封面"},
    "cover_split": {"value": "7:5", "status": "observed", "basis": "标题区明显宽于主图区"},
    "content_structure": {"value": "card-grid", "status": "extension", "basis": "把可见模块适配为内容卡片组"},
    "content_columns": {"value": "3", "status": "observed", "basis": "参考呈现三列等距模块"},
    "image_placement": {"value": "right", "status": "observed", "basis": "主图位于标题右侧"},
    "image_aspect_ratio": {"value": "4:3", "status": "extension", "basis": "以可见主图比例适配报告图片"},
    "image_fit": {"value": "cover", "status": "observed", "basis": "主图填满矩形面板"},
    "image_treatment": {"value": "muted", "status": "extension", "basis": "将克制色彩延展为轻度降饱和"},
    "data_structure": {"value": "source-chart-split", "status": "extension", "basis": "适配为来源与图表并列页"},
    "data_columns": {"value": "2", "status": "extension", "basis": "数据页按来源与图表形成两列"},
    "module_organization": {"value": "hard-grid", "status": "observed", "basis": "粗线和直角形成硬网格"},
    "density": {"value": "medium", "status": "observed", "basis": "标题与模块保持中等密度"},
    "visual_focus": {"value": "headline-and-image", "status": "observed", "basis": "标题与主图共同形成焦点"}
  },
  "components": [
    {"name": "结论标签", "description": "实色底、短文本、硬边", "status": "observed", "basis": "标题上方标签"},
    {"name": "证据卡片", "description": "细边框、短结论、来源脚注", "status": "extension", "basis": "把参考模块适配为报告证据卡"}
  ],
  "imagery": [
    {"label": "图片裁切", "description": "横向硬裁切并保留主体", "status": "observed", "basis": "右侧主图"}
  ],
  "evidence_language": [
    {"label": "数据图表", "description": "参考中未出现，不能识别图表语法", "sample": "none", "status": "unknown", "basis": "整张参考没有图表或数值证据"}
  ],
  "mini_pages": [
    {"kind": "cover", "title": "代表性封面", "description": "延展主标题、标签与主图比例", "status": "extension", "basis": "把已观察层级适配为报告封面"},
    {"kind": "content", "title": "代表性内容页", "description": "延展网格与卡片节奏", "status": "extension", "basis": "把已观察模块适配为正文页"},
    {"kind": "data", "title": "代表性数据页", "description": "仅定义信息区，不声称参考已有图表语法", "status": "extension", "basis": "数据页是报告需要，图表样式仍待后续定义"}
  ],
  "guardrails": [
    {"mode": "preserve", "title": "保留", "description": "保持大标题与硬边框的对比", "status": "observed", "basis": "两者在参考中反复出现"},
    {"mode": "avoid", "title": "禁用", "description": "不加入柔和渐变和玻璃拟态", "status": "extension", "basis": "避免冲淡已观察的硬朗语言"}
  ]
}
```

Every list must be non-empty. `palette` accepts one to six items, so one or two supported colors are valid. A palette item with `observed` or `extension` status must carry a six-digit hex value. An `unknown` palette item must use the literal value `unknown`; the renderer shows a neutral hatched placeholder and “未识别色值”, never a real color swatch. Do not add an unknown palette item when the supported colors already express the category clearly.

`executable_layout` is an exact object, not a prose summary. Every field uses exactly `value`, `status`, and `basis`. Use these enums:

| Field | Values before `unknown` |
|---|---|
| `page_axis` | `row`, `column` |
| `alignment` | `start`, `center`, `end` |
| `cover_structure` | `split`, `single-column` |
| `cover_split` | `7:5`, `5:7`, `1:1`, `none` |
| `content_structure` | `card-grid`, `stack`, `single-focus` |
| `content_columns`, `data_columns` | `1`, `2`, `3` |
| `image_placement` | `left`, `right`, `top`, `bottom`, `background`, `inline` |
| `image_aspect_ratio` | `16:9`, `4:3`, `3:2`, `1:1`, `3:4` |
| `image_fit` | `cover`, `contain` |
| `image_treatment` | `natural`, `muted`, `monochrome`, `high-contrast` |
| `data_structure` | `source-chart-split`, `chart-focus`, `table-focus`, `metrics-grid` |
| `module_organization` | `hard-grid`, `soft-stack`, `open-field` |
| `density` | `low`, `medium`, `high` |
| `visual_focus` | `headline-and-image`, `headline-only`, `image-first`, `data-first`, `balanced` |

Every enum also accepts `unknown`, but only together with `status: unknown`; an unknown field cannot carry a concrete value. A `single-column` cover uses `cover_split: none`, while a `split` cover cannot use `none`. The upstream model must select these values from the confirmed static observation and explicitly labeled report adaptation. Descriptive `layout`, `components`, and `mini_pages` remain useful review material, but they are not the compiler's primary structural input.

Choose `density` from the visible relationship between labels, titles, explanatory copy, and major modules—not from the number of words in the eventual report. Use `low` for conspicuous whitespace and one dominant focal group, `medium` for a balanced report rhythm, and `high` for deliberately compact information groupings. The compiler turns this enum into semantic relationship spacing; the model must not invent pixel gaps. If the static reference does not establish density, use `unknown` so the compiler can record its neutral medium fallback separately.

`mini_pages` must contain exactly one each of `cover`, `content`, and `data`. `guardrails` must contain at least one `preserve` and one `avoid`. Across the whole contract, all three boundary statuses must appear at least once. Use an `unknown` item for a missing category instead of omitting the category. For `evidence_language`, set `sample` to `bar`, `line`, `table`, `metric`, or `citation` only when that language is directly observed or explicitly proposed as an `extension`; an `unknown` item must use `none`, which renders an explicit “参考中未出现” state instead of a fabricated chart.

## Deterministic Render

Render the contract and the verified local source image with:

```bash
python scripts/render_reference_vi.py \
  --data /absolute/path/to/reference-vi.json \
  --source-image /absolute/path/to/reference.png \
  --output /absolute/path/to/reference-vi-board
```

The command creates `reference-vi-board.html` and a 3200×2400 `reference-vi-board.png` beside it. It accepts readable PNG, JPEG, WebP, or safe offline SVG input, embeds that image as a `data:` URI, and fails closed on invalid contracts, active SVG content, remote SVG references, fabricated unknown color values, or unsupported dynamic/time-sequence wording. Boundary statements such as “静态” or “无动态” remain valid; positive rules about movement, timing, sequences, easing, keyframes, or morphing do not.

Run `check_assets.py --strict-offline` on the rendered HTML. Open the HTML in a real browser, verify the status labels and all sections, and inspect the PNG at original resolution for Chinese text, hex values, type hierarchy, component samples, and the three mini pages.

## Customer Confirmation Gate

Show the PNG as the primary deliverable, optionally provide the HTML, and end with:

> 请确认这张《VI 设计标准图》中的直接观察、报告适配建议和参考中无法判断三类边界。回复“确认 VI”后，TaoHtml 才会把它作为项目专用主题生成的输入；确认前不会开始正式报告制作。

Treat only a clear confirmation of the current board as VI authorization. If the customer corrects a color, boundary label, crop rule, component, or guardrail, update the JSON, rerender the whole board, and request confirmation again. Earlier approval to use the reference is not VI confirmation, and VI confirmation is not Report Design Brief confirmation.

## Confirmed-VI Handoff Boundary

After confirmation, retain these inputs and read `project-theme-compiler.md`:

- confirmed VI JSON contract;
- exact source-image path or packaged local copy;
- rendered board HTML and PNG for comparison and human review;
- customer corrections incorporated into the current contract;
- target reading/presentation mode and any confirmed accessibility or brand constraints.

Create the machine-checkable handoff in `project-theme-compiler.md`, bind the confirmation to the exact VI JSON and reference-image hashes, and compile the project-specific manifest, CSS, templates, and provenance. The compiler is a separate deterministic step: this reference renderer still does not compile theme assets. The result does not substitute or extend the four built-in themes and does not authorize report production without the remaining Report Design Brief gate.
