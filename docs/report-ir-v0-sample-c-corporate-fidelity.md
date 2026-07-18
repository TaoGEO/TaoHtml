# Report IR v0 样例 C：企业模板保真演讲报告

> 状态：概念样例，不是正式 Schema，也不是企业客户交付物<br>
> 主题：某企业知识服务产品的市场增长与进入策略<br>
> 主要投影：现场演讲<br>
> 视觉绑定：仓库现有 `orbital-corporate-family` 项目专用企业模板<br>
> 关键验证：企业固定层保持不动，报告内容、证据和动效只能进入安全内容区

## 目录

- [1. 样例目标](#1-样例目标)
- [2. 与样例 A、B 的共同核心](#2-与样例-ab-的共同核心)
- [3. 企业模板真源与保真边界](#3-企业模板真源与保真边界)
- [4. 概念 IR](#4-概念-ir)
- [5. Page Registry 与 Shell 路由](#5-page-registry-与-shell-路由)
- [6. 关键数据页状态](#6-关键数据页状态)
- [7. 固定层、安全区与动效不变量](#7-固定层安全区与动效不变量)
- [8. 第二视觉绑定实验](#8-第二视觉绑定实验)
- [9. Patch 与失效传播](#9-patch-与失效传播)
- [10. 企业主题复用语义](#10-企业主题复用语义)
- [11. 初步验证结论](#11-初步验证结论)

## 1. 样例目标

这个样例验证同一组报告语义进入企业模板保真模式后，Report IR 是否能够：

1. 把企业固定像素与报告内容严格分开；
2. 让 Page 的语义角色与企业 Shell 角色分别存在；
3. 只把标题、图表、正文和动效状态放入安全内容区；
4. 保留 Logo、页眉、页脚、品牌条和固定装饰的原始像素及定位；
5. 区分截图中直接观察到的 Shell 与项目主题补全的 Shell；
6. 阻止静态参考图被误解为动效来源；
7. 保持样例 A、B 的 Claim、Evidence、Source 和待核实状态不变；
8. 在企业安全区更窄时，通过降级、拆页或失败处理，而不是缩小到不可读；
9. 支持以后复用同一企业主题，但不把它误注册为第五套内置视觉系统。

本样例直接绑定仓库中已有的企业模板保真项目主题，用真实主题文件和哈希研究 IR 边界，不重新生成企业 VI。

### 研究用设计简报摘要

- 输入入口：复用样例 A、B 的固定研究材料。
- 使用模式：现场演讲，同时保留阅读最终状态。
- 报告长度：标准，9 页；增加一页企业目录，不增加新的事实 Claim。
- 受众：企业内部决策团队。
- 目标：说明增长结构和六周验证路径，争取内部验证授权。
- 内容边界：允许重组页面，不改变或遗漏共享核心表达。
- 证据严谨度：formal；模拟材料只能形成明确标注的情景分析。
- 视觉模式：企业模板保真。
- VI 状态：使用仓库现有、已记录“确认 VI”的 `orbital-corporate-family` 项目主题。
- 动效密度：适中；只作用于安全内容区，不从静态模板截图推断动效。
- 企业固定层：Logo、页眉、页脚、品牌条和固定装饰保持原样。
- 待确认式研究边界：`content` 与 `data` 是经过项目主题确认的延展页，不是截图直接观察页。
- 交付边界：本文件只验证概念 IR，不代表生产授权，也不输出客户报告。

## 2. 与样例 A、B 的共同核心

[样例 A](report-ir-v0-sample-a-presentation.md) 采用黑白荧光卡片演讲投影，[样例 B](report-ir-v0-sample-b-formal-reading.md) 采用严谨咨询报告阅读投影，本样例采用企业模板保真演讲投影。

三个样例共享同一个虚构研究主题和同一组模拟素材。

### 共享语义实体

| 类型 | 共享 ID | 共同含义 |
|---|---|---|
| Report | `report_enterprise_knowledge_opportunity` | 企业知识服务增长与进入策略 |
| Claim | `claim_total_growth` | 模型中的总量指数从 100 增长到 142 |
| Claim | `claim_growth_concentrated` | 模型中的主要增量集中在企业服务 |
| Claim | `claim_enterprise_drivers` | 集成、权限治理和持续更新是待验证需求 |
| Claim | `claim_purchase_constraint` | 采购周期是待验证限制 |
| Claim | `claim_validate_enterprise_first` | 先验证企业场景的条件性建议 |
| Claim | `claim_six_week_plan` | 六周验证计划 |
| Evidence | `evidence_total_index` | 模拟总量指数 |
| Evidence | `evidence_enterprise_share` | 模拟企业增量占比 |
| Evidence | `evidence_simulated_interviews` | 示意访谈摘要 |
| Source | `source_market_model` | 本地模拟市场模型 |
| Source | `source_methodology` | 本地方法说明 |
| Source | `source_interview_summary` | 本地示意访谈 |

### 本样例只改变的内容

- 主要 Projection 的页面编排；
- 页面与企业 Shell 的路由；
- Visual Intent 在安全内容区内的实现约束；
- 主题、模板和 VI 的构建绑定；
- 企业模板变化后的 QA 失效范围。

### 本样例绝对不改变的内容

- Source 的来源身份；
- Evidence 的真实性状态；
- Claim 的推演、待核实和条件性边界；
- Narrative Unit 的论证逻辑；
- 客户需要看到的《待核实内容清单》。

企业 Logo 和正式模板只能增强品牌一致性，不能把模拟市场模型变成企业已核验数据。

## 3. 企业模板真源与保真边界

### 3.1 绑定的项目主题

| 构建物 | 路径 | SHA-256 |
|---|---|---|
| Project Theme | `examples/corporate-template-fidelity/project-theme/theme.json` | `26e3ef121d194d673586b40b08a325ba70d440e38edfc8ddd9944318e7a15276` |
| Theme CSS | `examples/corporate-template-fidelity/project-theme/theme.css` | `4c30e8d753ce335a99fb2c5204710981683d8e025fcbba540d64239d6b4e9e2e` |
| Templates | `examples/corporate-template-fidelity/project-theme/templates.html` | `566fc4428fa1d87f6b53593d96fb0d88b3d0313c8cce32b0ed91cd95148d58f5` |
| Provenance | `examples/corporate-template-fidelity/project-theme/provenance.json` | `4ee4f32f3b17509d71cddbcaa4f509ea5db272a07f7d682c093e2ab3ea31b396` |
| VI 标准图 | `examples/corporate-template-fidelity/reference-vi-board.png` | `a28b2d45b756c798d4d320b8d702aa8bc29b84d2abcfca7fca4a882ee93b1bb7` |
| 现有演示样例 | `examples/corporate-template-fidelity/corporate-fidelity-sample.html` | `184981b9f44bec3389b4bb6c03d46ad4b1099487d6df53b1ac68ce471e9dd4c0` |

主题身份：

```yaml
project_theme:
  id: project-orbital-corporate-family
  project_id: orbital-corporate-family
  kind: project
  global_built_in: false
  reference_mode: corporate_fidelity
  target_mode: presentation
  schema_version: "1.0"
  vi_schema_version: "1.3"
  vi_confirmation: 确认 VI
```

### 3.2 观察到的页面与延展页面

| Shell Role | 状态 | 依据 | Editable Region |
|---|---|---|---|
| `cover` | observed | 参考截图直接展示封面 | `cover-safe` = `[0.40, 0.12, 0.54, 0.74]` |
| `toc` | observed | 参考截图直接展示目录 | `toc-safe` = `[0.08, 0.18, 0.84, 0.68]` |
| `section` | observed | 参考截图直接展示章节页 | `section-safe` = `[0.43, 0.18, 0.51, 0.64]` |
| `content` | extension | 截图没有普通内容页，由项目主题补全 | `content-safe` = `[0.08, 0.18, 0.84, 0.68]` |
| `data` | extension | 截图没有数据页，由项目主题补全 | `data-safe` = `[0.08, 0.18, 0.84, 0.68]` |

这里的 `observed` 只表示静态画面直接可见，不表示已得到 PPT 母版、矢量资产、品牌字体文件或动效规则。

### 3.3 固定层身份

```yaml
fixed_layers:
  cover:
    - id: cover-left
      type: composition
      status: observed
      crop_sha256: db834b39cf71fcfa5c8be29f80e02777bc2face29f314a6171b4d3e183a246f8
    - id: cover-rule
      type: brand_bar
      status: observed
      crop_sha256: c4f016bd8f673f63229e35c5743a052bf73dec25bf475ff1e79357dca961a745

  toc:
    - id: toc-header
      type: header
      status: observed
      crop_sha256: 2297df7eb769cd36bdebe23b08bde3303902d628ae491a4f0fd00f2bbfe7d3a4
    - id: toc-footer
      type: footer
      status: observed
      crop_sha256: bf270a489a5ad2adfd1553376336511f4096901caf85dde51b8345eb9c64a387

  section:
    - id: section-left
      type: composition
      status: observed
      crop_sha256: 6f367ebce21767d132889e1e7a949d4cd68dd14d65e93c49bcc8819014f99829
    - id: section-top
      type: header
      status: observed
      crop_sha256: f2d59a993c15780b47c57c2675fbeb267951a86e4f2f2d1b6f1a0fadfac51631
    - id: section-footer
      type: footer
      status: observed
      crop_sha256: bf270a489a5ad2adfd1553376336511f4096901caf85dde51b8345eb9c64a387
```

`content` 与 `data` Shell 复用经过确认的页眉、页脚裁片，但 Shell 本身仍保持 `extension` 身份。

### 3.4 保真边界

本样例允许宣称：

- 已从三张静态参考图提取并确认企业 VI；
- 固定裁片有来源截图、像素框和哈希绑定；
- Logo、页眉、页脚、品牌条和固定装饰在对应 Shell 中保持不动；
- 普通内容页和数据页是基于已观察元素的项目主题延展。

本样例不允许宣称：

- 恢复了原始 PPT 母版；
- 获得了原始 Logo 矢量文件或字体文件；
- 从截图识别了原 PPT 动效；
- 普通内容页和数据页在客户截图中已经存在；
- 企业模板代表客户认可了报告中的市场结论。

## 4. 概念 IR

以下 YAML 是研究伪结构，不承诺生产字段名称。

### 4.1 身份、模式与绑定

```yaml
identity:
  report_ir_version: research-v0
  report_id: report_enterprise_knowledge_opportunity
  revision_id: rev_001_corporate_projection
  research_only: true

design_brief_binding:
  ref: report-ir-v0-sample-c-corporate-fidelity.md
  confirmation_status: simulated_for_research
  production_authorization: false

report:
  title: 企业知识服务增长机会与验证计划
  objective: 为六周企业场景验证计划争取内部批准
  audience: 企业内部决策团队
  report_archetype: internal_strategy_report
  evidence_rigor: formal
  primary_projection_ref: projection_corporate_presentation

projection_profiles:
  projection_corporate_presentation:
    delivery_mode: presentation
    information_density: medium
    customer_motion_choice: medium
    motion_density: medium
    interaction_level: low
    state_complexity: staged_recomposition
    reading_final_state_required: true

build_binding:
  theme_kind: project_theme
  theme_ref: project-orbital-corporate-family
  theme_sha256: 26e3ef121d194d673586b40b08a325ba70d440e38edfc8ddd9944318e7a15276
  theme_css_sha256: 4c30e8d753ce335a99fb2c5204710981683d8e025fcbba540d64239d6b4e9e2e
  templates_sha256: 566fc4428fa1d87f6b53593d96fb0d88b3d0313c8cce32b0ed91cd95148d58f5
  provenance_sha256: 4ee4f32f3b17509d71cddbcaa4f509ea5db272a07f7d682c093e2ab3ea31b396
  vi_board_sha256: a28b2d45b756c798d4d320b8d702aa8bc29b84d2abcfca7fca4a882ee93b1bb7
  corporate_fidelity_mode: locked_shells
  runtime_profile: current_taohtml_single_screen
```

`theme_sha256` 与其他构建哈希属于精确构建输入。任一值变化后，不允许复用旧视觉 QA。

### 4.2 来源、证据与状态保持不变

```yaml
sources:
  source_market_model:
    locator: report-ir-v0-fixtures/sample-a/market-model.csv
    sha256: 77cb67923388107914b1bb33dcbb3772b9887a778b23e4c5a56711920d8d79a2
    source_role: agent_generated_material
    content_status: illustrative
    evidence_verification: not_applicable

  source_methodology:
    locator: report-ir-v0-fixtures/sample-a/methodology.md
    sha256: fc581f63410026023621fe89f500748c02fd753874850697f9fa5af6f9d3eec4
    source_role: agent_generated_material
    content_status: illustrative
    evidence_verification: not_applicable

  source_interview_summary:
    locator: report-ir-v0-fixtures/sample-a/interview-summary.md
    sha256: 305dca2b7e7c40ccc289e9471f44a6147de9f2b57f9ca70f88e667b4c386dadb
    source_role: agent_generated_material
    content_status: illustrative
    evidence_verification: not_applicable

claims:
  claim_total_growth:
    kind: simulation
    statement: 模型中的市场总量指数从 100 增长到 142
    status: scenario_only

  claim_growth_concentrated:
    kind: inference
    statement: 模型中的主要增量集中在企业服务
    status: provisional

  claim_validate_enterprise_first:
    kind: recommendation
    statement: 应优先验证企业场景
    status: conditional

evidence_links:
  - claim_ref: claim_total_growth
    evidence_ref: evidence_total_index
    relation: supports_in_scenario
  - claim_ref: claim_growth_concentrated
    evidence_ref: evidence_enterprise_share
    relation: supports_in_scenario
  - claim_ref: claim_validate_enterprise_first
    evidence_ref: evidence_enterprise_share
    relation: supports_conditionally
  - claim_ref: claim_validate_enterprise_first
    evidence_ref: evidence_simulated_interviews
    relation: qualifies
```

### 4.3 企业 Shell Registry

```yaml
shell_registry:
  shell_cover:
    theme_role: cover
    status: observed
    editable_region_ref: cover-safe
    allowed_page_forms: [poster]
    fixed_motion: none

  shell_toc:
    theme_role: toc
    status: observed
    editable_region_ref: toc-safe
    allowed_page_forms: [navigation]
    fixed_motion: none

  shell_section:
    theme_role: section
    status: observed
    editable_region_ref: section-safe
    allowed_page_forms: [section]
    fixed_motion: none

  shell_content:
    theme_role: content
    status: extension
    editable_region_ref: content-safe
    allowed_page_forms: [poster, process, comparison, matrix, closing]
    fixed_motion: none

  shell_data:
    theme_role: data
    status: extension
    editable_region_ref: data-safe
    allowed_page_forms: [data, table]
    fixed_motion: none
```

Shell Registry 属于 Visual System / Build Binding，不属于报告语义内容。Report IR 只引用能力和版本，不复制裁片像素。

### 4.4 页面绑定结构

```yaml
page:
  id: page_growth_structure
  narrative_unit_refs:
    - unit_total_growth
    - unit_growth_concentration
  role: prove
  form: data
  task: 先确认模型总量增长，再把焦点转向增量结构
  primary_takeaway_ref: claim_growth_concentrated

  shell_binding:
    shell_ref: shell_data
    editable_region_ref: data-safe
    shell_status: extension
    report_dom_scope: editable_region_only
    fixed_region_policy: immutable

  surface_block_refs:
    - block_growth_structure_title
    - block_total_growth_metric
    - block_segment_chart
    - block_enterprise_share_metric
    - block_scenario_label
```

`role=prove` 与 `form=data` 描述报告语义；`shell_ref=shell_data` 描述构建时使用哪一种企业外壳。两者不能合并为一个字段。

## 5. Page Registry 与 Shell 路由

为了覆盖五种企业 Shell，本样例使用 9 页。目录页属于导航投影，不新增 Claim 或 Narrative Unit。

| 页 | Page Role / Form | Narrative Unit | Shell Role | Shell 状态 | 页面任务 |
|---|---|---|---|---|---|
| 1 | orient / poster | 全局 | cover | observed | 建立报告主题与推演边界 |
| 2 | orient / navigation | 全局导航 | toc | observed | 展示三章及其任务 |
| 3 | orient / section | `unit_growth_concentration` | section | observed | 引出“增长结构比总量更重要” |
| 4 | prove / data | `unit_total_growth` + `unit_growth_concentration` | data | extension | 从总量转向增量结构 |
| 5 | explain / process | `unit_enterprise_drivers` | content | extension | 解释三个待验证需求驱动 |
| 6 | compare / comparison | `unit_purchase_constraint` | content | extension | 对比机会与采购限制 |
| 7 | decide / matrix | `unit_entry_priority` | data | extension | 选择优先验证场景 |
| 8 | act / process | `unit_six_week_plan` | content | extension | 给出六周验证步骤 |
| 9 | act / closing | `unit_six_week_plan` | content | extension | 请求内部批准并重申边界 |

### 5.1 Projection

```yaml
projection:
  id: projection_corporate_presentation
  delivery_mode: presentation
  page_order:
    - page_cover
    - page_toc
    - page_opportunity_section
    - page_growth_structure
    - page_enterprise_drivers
    - page_constraints
    - page_priority
    - page_plan
    - page_closing

  reading_behavior:
    same_page_order: true
    show_final_state: true
    animation_required: false

  presentation_behavior:
    advance_by_state: true
    speaker_notes_follow_state: true
    page_navigation_may_skip_remaining_states: true

  shell_policy:
    fixed_regions_immutable: true
    report_content_must_be_descendant_of_editable_region: true
    fixed_regions_must_not_be_fragment_targets: true
    unknown_shell_role: build_error
```

### 5.2 页面路由不变量

1. 封面内容只能进入 `cover-safe`。
2. 目录项目只能进入 `toc-safe`。
3. 章节标题只能进入 `section-safe`。
4. 普通内容页与数据页必须显式保留 `extension` 状态。
5. 任何 Content Block 都不能成为固定裁片的父节点。
6. 任何 State 都不能修改、遮盖或移动固定区域。
7. Page Role 变化不自动改变 Shell；Shell 变化也不自动改写 Page 语义。
8. Shell 不支持当前 Block 数量时，Compiler 必须使用明确 fallback、拆页或失败，不能越过安全区。

## 6. 关键数据页状态

第四页复用样例 A 的“总量让位于结构”状态语义，但必须在 `data-safe` 内完成。

```yaml
page:
  id: page_growth_structure
  role: prove
  form: data
  shell_binding:
    shell_ref: shell_data
    editable_region_ref: data-safe
    fixed_region_policy: immutable

  visual_intent:
    composition_family: staged_focus
    initial_focus: block_total_growth_metric
    final_focus: block_segment_chart
    density: medium
    relationships:
      - block_total_growth_metric establishes claim_total_growth
      - block_segment_chart reframes growth as segment structure
      - block_enterprise_share_metric emphasizes claim_growth_concentrated
      - block_scenario_label limits all displayed numbers

  states:
    - id: page_growth_structure__state_0
      focus: block_total_growth_metric
      visible:
        - block_growth_structure_title
        - block_total_growth_metric
        - block_scenario_label
      semantic_layout:
        block_growth_structure_title: safe_heading_region
        block_total_growth_metric: safe_primary_region
        block_scenario_label: safe_disclosure_region

    - id: page_growth_structure__state_1
      focus: block_segment_chart
      visible:
        - block_growth_structure_title
        - block_total_growth_metric
        - block_segment_chart
        - block_scenario_label
      semantic_layout:
        block_growth_structure_title: safe_heading_region
        block_total_growth_metric: safe_summary_region
        block_segment_chart: safe_primary_region
        block_scenario_label: safe_disclosure_region
      transition_intent:
        - block_total_growth_metric yields_focus
        - block_segment_chart expands_within_editable_region

    - id: page_growth_structure__state_2
      focus: block_enterprise_share_metric
      visible:
        - all_surface_blocks
      semantic_layout:
        block_growth_structure_title: safe_heading_region
        block_total_growth_metric: safe_summary_region
        block_segment_chart: safe_evidence_region
        block_enterprise_share_metric: safe_emphasis_region
        block_scenario_label: safe_disclosure_region

  reading_final_state_ref: page_growth_structure__state_2

  speaker_notes:
    - state_ref: page_growth_structure__state_0
      text: 模型中的市场总量指数三年增长 42%，这不是实际市场预测。
    - state_ref: page_growth_structure__state_1
      text: 决策重点不是总量，而是增量结构。
    - state_ref: page_growth_structure__state_2
      text: 模型把约 64.3% 的增量分配给企业服务，因此下一步是验证，不是直接承诺。
```

### 状态语义与几何实现的边界

IR 可以表达：

- 哪个 Block 是当前焦点；
- 哪个 Block 从主舞台退为摘要；
- 哪个图表扩展为主要证据；
- 哪个待核实标签必须持续可见；
- 最终阅读状态包含什么。

IR 不写入：

- `data-safe` 的具体 CSS 选择器；
- 图表宽高和像素坐标；
- transform、transition、duration 或 easing；
- 页眉、页脚和 Logo 的 DOM；
- 企业裁片的 Base64 数据。

这些属于 Project Theme、Compiler 和 Runtime。

## 7. 固定层、安全区与动效不变量

### 7.1 固定层不是报告内容

以下对象不能进入 Content Graph：

- 企业 Logo；
- 固定页眉；
- 固定页脚；
- 品牌条；
- 固定装饰裁片；
- 企业 Shell 背景。

原因是它们不回答报告问题，也不支撑 Claim。它们属于构建时视觉依赖。

### 7.2 固定层不能参与报告动效

```yaml
corporate_motion_invariants:
  fixed_elements:
    animation: none
    transition: none
    transform: none
    fragment_target: false
    data_step_target: false

  report_motion:
    scope: editable_regions_only
    source: report_state_sequence_and_shared_runtime
    inferred_from_static_reference: false
```

企业截图只提供静态 VI。即使报告选择“丰富动效”，动效也只能由报告任务和共享 Runtime 决定。

### 7.3 安全区冲突处理

当页面内容无法合理放入企业安全区时，处理顺序是：

1. 选择同一 Shell 能力内的等价构图；
2. 把次要内容转入下一页、附录或来源面板；
3. 拆分 Page，同时保持 Narrative Unit 和 Claim 引用；
4. 使用主题声明的 fallback Shell；
5. 仍无法满足时停止正式构建并返回诊断。

禁止：

- 覆盖 Logo、页眉或页脚；
- 把字号无限缩小；
- 让图表标签重叠；
- 把待核实标签藏到固定层下面；
- 静默删除内容；
- 为通过构建而修改报告含义。

### 7.4 企业模板 QA

除普通浏览器 QA 外，本样例还要求：

- 固定裁片哈希与主题绑定一致；
- 固定区域的像素位置未变化；
- 所有报告 DOM 都在对应 Editable Region 内；
- 固定层没有 fragment、data-step 或动效属性；
- `extension` Shell 没有被标成 `observed`；
- 目录、章节、内容和数据页路由正确；
- 每个状态都没有穿越安全区；
- 图表最终状态无文字重叠；
- 页面上的推演和待核实标签仍然可见；
- 企业模板版本变化后旧 QA 不被复用。

## 8. 第二视觉绑定实验

本样例的主要绑定是企业模板保真项目主题。第二绑定选择内置“稳重企业年报”，用于验证同一语义摆脱企业固定壳后仍可编译。

| 语义意图 | 企业模板保真 | 稳重企业年报 |
|---|---|---|
| cover | 固定企业封面裁片 + `cover-safe` 标题 | 品牌化封面构图，不复用企业裁片 |
| toc | 固定页眉页脚 + `toc-safe` 目录 | 舒展编号目录 |
| section | 固定左侧组合裁片 + 右侧章节标题 | 大章标题与品牌色块 |
| data | 固定页眉页脚内的数据安全区 | 更大图表和更舒展的注释区域 |
| content | 固定页眉页脚内的内容安全区 | 图文平衡与适度留白 |
| disclosure | 安全区内持续显示 | 页面脚注或品牌化说明区 |

切换到稳重企业年报时保持：

- Report、Chapter、Narrative Unit；
- Claim、Evidence、Source、Dataset；
- Page Role、Form、任务和顺序；
- State Sequence 的焦点和讲解语义；
- Speaker Notes；
- 待核实内容。

切换时移除或重建：

- `shell_binding`；
- 企业固定裁片；
- Editable Region 引用；
- 企业主题版本和哈希；
- 全部视觉、安全区和浏览器 QA。

第二绑定实验说明：企业 Shell 是可替换的构建依赖，不是报告语义本体。

## 9. Patch 与失效传播

| 请求 | IR / Binding 操作 | 重新编译 | 主要失效项 |
|---|---|---|---|
| 修改第 4 页标题 | Patch 对应 Content Block | 第 4 页 | 页面、碰撞、浏览器 QA |
| 第 4 页拆成两页 | 修改 Projection 与 Page | 两页、导航、总览 | 页面、状态、口播、安全区 QA |
| 替换真实市场数据 | 修改 Source、Dataset、Evidence | 所有依赖页 | Claim、图表、口播、附录、披露与 QA |
| 减少动效 | 修改 State Sequence | 受影响页面 | 动效、口播和最终状态 QA |
| 换为稳重企业年报 | 替换 Build Binding | 全量 | 全部视觉和浏览器 QA；证据状态不变 |
| 更新同一企业 VI | 新建 Project Theme 版本并重绑 | 全量 | 固定像素、安全区、主题和浏览器 QA |
| 只替换 Logo 截图 | 重新编译企业主题，不直接改 Report IR | 全量或所有引用 Shell | 固定层哈希与视觉 QA |
| 改 Shell 路由 | Patch Page 的 `shell_binding` | 相关页面 | 安全区、布局、动效和浏览器 QA |

### 9.1 内容标题 Patch

```yaml
patch:
  base_revision: rev_001_corporate_projection
  operation: replace
  target_ref: block_growth_structure_title.content
  value: 企业服务可能贡献主要增量
  meaning_change: false
  preserves:
    - shell_binding
    - fixed_layer_hashes
    - evidence_links
  invalidates:
    - page_growth_structure.layout_qa
    - page_growth_structure.collision_qa
    - page_growth_structure.browser_qa
```

### 9.2 企业主题更新 Patch

```yaml
patch:
  base_revision: rev_001_corporate_projection
  operation: replace_build_binding
  target_ref: build_binding
  required_inputs:
    - new_theme_ref
    - new_theme_sha256
    - new_vi_confirmation_ref
    - new_provenance_sha256
  preserves:
    - content_graph
    - evidence_graph
    - narrative_units
  invalidates:
    - all_shell_resolution
    - all_layout_qa
    - all_fixed_layer_qa
    - all_collision_qa
    - all_browser_qa
```

企业模板更新不是简单替换一张背景图。安全区、固定裁片和 Shell 能力都必须重新解析并重新确认。

### 9.3 Evidence Patch

```yaml
patch:
  operation: replace_evidence_dependency
  target_ref: evidence_enterprise_share
  preserves:
    - project_theme_binding
    - shell_registry
  invalidates:
    - claim_growth_concentrated
    - dependent_blocks
    - dependent_charts
    - dependent_speaker_notes
    - pending_verification_list
    - affected_pages.browser_qa
```

证据变化不使企业 VI 失效，但会使所有引用旧结论的页面内容失效。

## 10. 企业主题复用语义

首次完成企业模板保真并确认 VI 后，后续项目可以复用已编译的 Project Theme，但需要精确绑定身份。

```yaml
enterprise_theme_profile_ref:
  profile_id: orbital-corporate-family
  theme_ref: project-orbital-corporate-family
  theme_sha256: 26e3ef121d194d673586b40b08a325ba70d440e38edfc8ddd9944318e7a15276
  vi_confirmation_ref: confirmed_vi_contract
  reuse_policy: default_until_customer_requests_change
```

复用原则：

1. 新报告默认使用客户上次确认的企业主题；
2. 不必每次重新提取 VI；
3. 客户明确要求换模板或提供新参考时，生成新版本；
4. 旧项目继续绑定旧版本，不被静默升级；
5. 新主题确认不能替代报告设计简报确认；
6. 企业主题可以复用，但报告 Source、Evidence 和内容不能跨项目自动继承；
7. 项目主题仍然不是 TaoHtml 全局内置主题。

在未来 Workspace 中，用户偏好可以让 TaoHtml 更快进入正确路径，但不能跳过必要的材料理解、报告目标和授权边界。

## 11. 初步验证结论

### 当前能够表达

- 企业固定层与报告内容层分离；
- Page Role / Form 与 Shell Role 分离；
- observed Shell 与 extension Shell 的来源身份；
- 主题、模板、VI 和 provenance 的精确哈希绑定；
- 报告 DOM 和动效只发生在 Editable Region 内；
- 同一多状态页面在企业安全区内保持语义；
- 主题更新、证据更新和内容更新的不同失效范围；
- 企业主题跨项目复用时的版本绑定；
- 从企业模板切回内置主题时保持报告语义不变。

### 当前发现的架构价值

样例 C 说明 Build Binding 必须独立于 Report Content Graph。

如果把 Logo、页眉页脚或安全区写进 Page Content：

- 每页都会重复企业资产；
- 换主题会污染内容 Patch；
- 固定元素可能被模型当成报告模块参与动效；
- 企业模板版本变化会错误地使 Claim 和 Evidence 失效；
- 同一 IR 无法干净切换到内置主题。

因此更合理的关系是：

```text
Page 语义与 Visual Intent
+ Project Theme Binding
+ Shell Capability Resolution
→ 页面布局与 Runtime 状态
```

### 仍未证明

- Compiler 能否在五种 Shell 中确定性解决所有常见 Block 组合；
- 安全区不足时的拆页与 fallback 是否无需模型判断；
- 企业固定层像素级 QA 是否能在 Chrome、Edge、Safari 稳定运行；
- 复杂数据图表在 `data-safe` 内是否仍能避免文字重叠；
- 复用企业主题时，版本漂移和客户更换模板能否被可靠发现；
- 同一 IR 切换企业模板后，强模型设计上限是否明显下降。

### 样例 C 的研究判断

概念层面暂时通过：企业模板保真可以作为 Visual System 的项目级构建绑定，而不需要建立独立的企业报告 IR。

最重要的结论是：

> 企业模板固定层决定“画在哪里”，Report IR 决定“讲什么、为什么、如何推进”；固定层不能进入内容图，也不能获得报告动效。
