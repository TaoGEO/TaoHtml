# Report IR v0 样例 B：正式阅读型情景分析

> 状态：概念样例，不是正式 Schema，也不是真实市场研究<br>
> 主题：某企业知识服务产品的市场增长与进入策略<br>
> 主要投影：正式阅读<br>
> 视觉方向：严谨咨询报告<br>
> 关键验证：正式模式不能把模拟材料升级为真实证据

## 目录

- [1. 样例目标](#1-样例目标)
- [2. 与样例 A 的共同核心](#2-与样例-a-的共同核心)
- [3. 正式模式的就绪语义](#3-正式模式的就绪语义)
- [4. 概念 IR](#4-概念-ir)
- [5. Page Registry](#5-page-registry)
- [6. 关键分析页](#6-关键分析页)
- [7. 附录与待核实内容](#7-附录与待核实内容)
- [8. 第二主题映射假设](#8-第二主题映射假设)
- [9. Patch 与失效传播](#9-patch-与失效传播)
- [10. 初步验证结论](#10-初步验证结论)

## 1. 样例目标

这个样例验证同一组语义内容和模拟素材进入正式阅读模式后，是否能够：

1. 保留完整方法、来源、假设和限制；
2. 把页面标题从“确定结论”收紧为“情景模型结果”；
3. 区分“报告结构正式”和“事实已核验”；
4. 在不阻塞报告产出的前提下，阻止模拟材料被写成真实市场事实；
5. 让阅读模式使用完整页面，而不是依赖动画才能理解；
6. 让动效密度与图表交互能力在 IR 内部分开；
7. 复用样例 A 的 Claim、Evidence、Source 和 Narrative Unit 身份。

本样例允许生成一份结构完整的情景分析报告，但不允许宣称已经形成真实市场研究结论。

## 2. 与样例 A 的共同核心

[样例 A](report-ir-v0-sample-a-presentation.md) 与本样例使用同一主题、数据、访谈假设和语义实体。

### 共享实体

| 类型 | 共享 ID | 共同含义 |
|---|---|---|
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

研究文档为了可独立阅读会重复展示必要摘要；目标 IR 中这些实体只保存一次，不因阅读或演讲投影而复制。

### 投影差异

| 维度 | 样例 A：演讲 | 样例 B：正式阅读 |
|---|---|---|
| delivery_mode | presentation | reading |
| information_density | low | high |
| motion_density | rich | minimal |
| interaction_level | low | medium |
| evidence_rigor | standard | formal |
| 页面标题 | 强结论，但明确推演边界 | 条件化、方法化标题 |
| 来源 | 页面标签与交付清单 | 页面脚注、方法页、来源附录与交付清单 |
| 口播稿 | 按状态绑定 | 不需要 |
| 页面状态 | 多步构图 | 默认最终完整状态 |

## 3. 正式模式的就绪语义

`evidence_rigor=formal` 只提高证据关系、核验边界和披露要求，不改变 Source 的真实身份。

### 本样例的正确状态

```yaml
readiness:
  ir_structure_valid: conceptually_valid
  report_build_allowed: true_with_scenario_scope_and_disclosure
  formal_structure_complete: true
  formal_real_world_claim_ready: false
  simulated_content_labeled: required
  verification_backlog_required: true
```

含义是：

- 可以完成一份正式排版、完整论证的“情景分析”；
- 不能把标题改成“市场未来三年将增长 42%”；
- 不能把示意访谈写成“六位客户访谈证实”；
- 不能因为格式更严谨就把 `illustrative` 改成 `verified`；
- 若客户后续提供真实数据和来源，可通过 Evidence Patch 提升相应 Claim 的就绪状态。

### 三种结果必须分开

| 结果 | 含义 |
|---|---|
| 构建成功 | IR 可以被 Compiler 生成 HTML |
| 正式结构完整 | 方法、假设、限制、来源和附录齐全 |
| 真实结论可发布 | 事实与推论已经得到适配来源核验 |

前两项通过，不代表第三项通过。

## 4. 概念 IR

以下 YAML 是概念伪结构，不承诺生产字段名称。

### 4.1 身份、模式与构建绑定

```yaml
identity:
  report_ir_version: research-v0
  report_id: report_enterprise_knowledge_opportunity
  revision_id: rev_001_reading_projection
  research_only: true

report:
  title: 企业知识服务增长机会情景分析
  objective: 评估当前假设是否值得进入真实市场验证
  audience: 企业知识服务产品内部决策与研究团队
  report_archetype: strategy_research
  evidence_rigor: formal
  primary_projection_ref: projection_formal_reading

projection_profiles:
  projection_formal_reading:
    delivery_mode: reading
    information_density: high
    customer_motion_choice: low
    motion_density: minimal
    interaction_level: medium
    state_complexity: final_state_only
    reading_final_state_required: true

build_binding:
  theme_ref: rigorous-consulting-report
  enterprise_binding: null
  runtime_profile: current_taohtml_reading
```

这里刻意保留 `motion_density=minimal` 与 `interaction_level=medium`：正式阅读报告可以几乎没有动画，但仍允许图表悬停、指标查看或表格筛选。

### 4.2 来源身份保持不变

```yaml
sources:
  source_market_model:
    locator: report-ir-v0-fixtures/sample-a/market-model.csv
    sha256: 77cb67923388107914b1bb33dcbb3772b9887a778b23e4c5a56711920d8d79a2
    source_role: agent_generated_material
    availability: workspace_readable
    content_status: illustrative
    evidence_verification: not_applicable

  source_methodology:
    locator: report-ir-v0-fixtures/sample-a/methodology.md
    sha256: fc581f63410026023621fe89f500748c02fd753874850697f9fa5af6f9d3eec4
    source_role: agent_generated_material
    availability: workspace_readable
    content_status: illustrative
    evidence_verification: not_applicable

  source_interview_summary:
    locator: report-ir-v0-fixtures/sample-a/interview-summary.md
    sha256: 305dca2b7e7c40ccc289e9471f44a6147de9f2b57f9ca70f88e667b4c386dadb
    source_role: agent_generated_material
    availability: workspace_readable
    content_status: illustrative
    evidence_verification: not_applicable

dataset_registry:
  dataset_market_projection:
    source_ref: source_market_model
    methodology_source_ref: source_methodology
    base_year: 2024
    base_index: 100
    time_range: 2024-2027
    unit: index
    content_status: projected
    publication_scope: scenario_only
```

正式模式不能把 `source_role` 改成 `original_customer_material`，也不能把 `evidence_verification` 改成 `verified`。

### 4.3 Claim 与 Evidence 状态

```yaml
claim_registry:
  claim_total_growth:
    kind: simulation
    statement: 情景模型中的总量指数从 100 增长到 142
    content_status: projected
    publication_scope: scenario_only

  claim_growth_concentrated:
    kind: inference
    statement: 在当前模拟参数下，企业服务贡献主要增量
    content_status: projected
    verification: pending_verification
    publication_scope: scenario_only

  claim_enterprise_drivers:
    kind: assumption
    statement: 集成、权限治理和持续更新可能驱动企业需求
    content_status: illustrative
    verification: pending_verification

  claim_purchase_constraint:
    kind: assumption
    statement: 采购周期可能限制短期转化
    content_status: illustrative
    verification: pending_verification

  claim_validate_enterprise_first:
    kind: recommendation
    statement: 在扩大投入前，优先验证企业场景
    content_status: creative_supplement
    depends_on_unverified_claims: true

  claim_six_week_plan:
    kind: recommendation
    statement: 使用六周完成需求、集成和采购路径验证
    content_status: creative_supplement
    depends_on_unverified_claims: true
```

```yaml
evidence_registry:
  evidence_total_index:
    source_refs: [source_market_model, source_methodology]
    content_status: projected
    claim_fit: simulation_only

  evidence_enterprise_share:
    source_refs: [source_market_model, source_methodology]
    content_status: projected
    claim_fit: simulation_only

  evidence_simulated_interviews:
    source_refs: [source_interview_summary]
    content_status: illustrative
    claim_fit: illustrative_only
```

```yaml
formal_evidence_policy:
  allow_report_completion: true
  allow_real_world_fact_claim: false
  required_actions:
    - scope titles and conclusions to scenario analysis
    - label projected numbers beside charts and metrics
    - keep methodology and limitations visible
    - include verification backlog
    - keep delivery verification list
  forbidden_actions:
    - upgrade simulated source roles
    - describe illustrative interviews as completed research
    - remove caveats from executive summary
```

### 4.4 Narrative Unit 保持语义身份

| Narrative Unit | 正式阅读页中的表达任务 |
|---|---|
| `unit_total_growth` | 说明模型总量变化、计算口径与适用范围 |
| `unit_growth_concentration` | 分析企业增量占比，并明确这是情景参数 |
| `unit_enterprise_drivers` | 把示意访谈整理成待验证假设，而不是客户事实 |
| `unit_purchase_constraint` | 说明采购周期对建议的限制 |
| `unit_entry_priority` | 形成条件性验证优先级 |
| `unit_six_week_plan` | 建立真实数据和客户访谈的补证计划 |

### 4.5 Content Block

```yaml
content_blocks:
  block_report_title:
    type: headline
    content: 企业知识服务增长机会情景分析

  block_executive_summary:
    type: body_text
    content: 当前模拟模型显示企业服务可能贡献主要增量，但现有材料不足以形成真实市场结论；建议先完成六周验证。

  block_status_banner:
    type: caveat
    content: 本报告为情景分析；全部市场数字和访谈均为推演或示意内容。

  block_evidence_status_table:
    type: table
    columns: [主张, 当前材料, 可支持范围, 核验缺口]
    row_refs:
      - claim_total_growth
      - claim_growth_concentrated
      - claim_enterprise_drivers
      - claim_purchase_constraint

  block_total_forecast_chart:
    type: data_visualization
    dataset_ref: dataset_market_projection
    chart_intent: show_scenario_total_index
    content_status: projected
    adjacent_label: 推演数据 / 待核实

  block_total_methodology:
    type: methodology
    source_ref: source_methodology
    content: 2024 年指数设为 100；后续数据为人工构造的情景参数。

  block_segment_contribution_chart:
    type: data_visualization
    dataset_ref: dataset_market_projection
    chart_intent: compare_segment_increment_contribution
    content_status: projected
    adjacent_label: 推演数据 / 待核实

  block_segment_assumption_table:
    type: table
    columns: [参数, 2025, 2026, 2027, 状态]
    dataset_ref: dataset_market_projection

  block_driver_evidence_matrix:
    type: table
    rows: [系统集成, 权限治理, 内容持续更新, 价格]
    columns: [示意反馈, 当前判断, 所需真实验证]
    source_ref: source_interview_summary
    content_status: illustrative
    adjacent_label: 示意访谈 / 待核实

  block_purchase_constraint:
    type: caveat
    content: 采购周期可能超过一个季度；该限制来自示意访谈，尚未核验。
    content_status: illustrative

  block_conditional_recommendation:
    type: claim
    claim_ref: claim_validate_enterprise_first
    display_text: 仅当真实访谈和集成评估支持当前假设时，才扩大企业场景投入。

  block_six_week_verification_plan:
    type: process
    items:
      - 真实访谈：验证需求、角色和购买动机
      - 技术验证：核对集成、权限和数据边界
      - 商务验证：核对采购周期、预算和决策链

  block_source_register:
    type: evidence_excerpt
    source_refs:
      - source_market_model
      - source_methodology
      - source_interview_summary

  block_verification_backlog:
    type: list
    items:
      - 替换模拟市场模型
      - 补充真实客户访谈
      - 核验采购周期与预算
      - 重新计算企业增量占比
```

## 5. Page Registry

```yaml
pages:
  page_cover:
    narrative_unit_refs: []
    role: orient
    form: poster
    task: 定义情景分析范围
    surface_block_refs:
      - block_report_title
      - block_status_banner
    reading_final_state: all_surface_blocks

  page_executive_summary:
    narrative_unit_refs:
      - unit_growth_concentration
      - unit_entry_priority
    role: synthesize
    form: evidence
    task: 给出条件化结论和建议
    surface_block_refs:
      - block_executive_summary
      - block_status_banner
    reading_final_state: all_surface_blocks

  page_evidence_status:
    narrative_unit_refs:
      - unit_total_growth
      - unit_growth_concentration
      - unit_enterprise_drivers
      - unit_purchase_constraint
    role: orient
    form: source
    task: 先说明每条主张目前能被什么支持
    surface_block_refs:
      - block_evidence_status_table
    reading_final_state: all_surface_blocks

  page_total_scenario:
    narrative_unit_refs: [unit_total_growth]
    role: prove
    form: data
    task: 展示模拟总量变化与方法边界
    surface_block_refs:
      - block_total_forecast_chart
      - block_total_methodology
      - block_status_banner
    reading_final_state: all_surface_blocks

  page_segment_contribution:
    narrative_unit_refs: [unit_growth_concentration]
    role: prove
    form: data
    task: 分析模拟企业增量贡献
    surface_block_refs:
      - block_segment_contribution_chart
      - block_segment_assumption_table
      - block_total_methodology
      - block_status_banner
    reading_final_state: all_surface_blocks

  page_driver_and_constraint:
    narrative_unit_refs:
      - unit_enterprise_drivers
      - unit_purchase_constraint
    role: compare
    form: matrix
    task: 并列展示需求假设和采购限制
    surface_block_refs:
      - block_driver_evidence_matrix
      - block_purchase_constraint
    reading_final_state: all_surface_blocks

  page_conditional_strategy:
    narrative_unit_refs:
      - unit_entry_priority
      - unit_six_week_plan
    role: decide
    form: framework
    task: 把建议写成有进入条件的验证决策
    surface_block_refs:
      - block_conditional_recommendation
      - block_six_week_verification_plan
    reading_final_state: all_surface_blocks

  page_method_and_sources:
    narrative_unit_refs: [unit_six_week_plan]
    role: act
    form: source
    task: 汇总方法、来源和补证任务
    surface_block_refs:
      - block_source_register
      - block_verification_backlog
    reading_final_state: all_surface_blocks
```

```yaml
projection:
  id: projection_formal_reading
  page_order:
    - page_cover
    - page_executive_summary
    - page_evidence_status
    - page_total_scenario
    - page_segment_contribution
    - page_driver_and_constraint
    - page_conditional_strategy
    - page_method_and_sources
  default_display: final_state
  requires_animation_for_comprehension: false
  speaker_notes: none
```

## 6. 关键分析页

第五页复用样例 A 第三页的 `unit_growth_concentration`，但投影方式不同。

```yaml
page:
  id: page_segment_contribution
  role: prove
  form: data
  task: 完整说明企业增量占比的计算、结果和限制
  primary_takeaway_ref: claim_growth_concentrated

  visual_intent:
    composition_family: analytical_report
    primary_focus: block_segment_contribution_chart
    reading_order:
      - block_status_banner
      - block_segment_contribution_chart
      - block_segment_assumption_table
      - block_total_methodology
    relationships:
      - block_segment_contribution_chart visualizes evidence_enterprise_share
      - block_segment_assumption_table exposes scenario parameters
      - block_total_methodology limits claim_growth_concentrated
      - block_status_banner prevents real-world overclaim
    density: high
    evidence_visibility: explicit

  state_sequence:
    - id: page_segment_contribution__final
      visible: all_surface_blocks
      focus: block_segment_contribution_chart

  reading_final_state_ref: page_segment_contribution__final
```

对比演讲页：

- 不先展示大数字再展开图表；
- 不依赖点击顺序；
- 计算参数、方法和限制与图表同时可读；
- 模拟状态在页面上直接可见；
- Evidence Graph 仍与演讲页共享。

## 7. 附录与待核实内容

```yaml
appendix:
  id: appendix_formal_reading
  sections:
    - id: appendix_method
      block_refs: [block_total_methodology]
    - id: appendix_sources
      block_refs: [block_source_register]
    - id: appendix_verification
      block_refs: [block_verification_backlog]
```

### 交付时的《待核实内容清单》

| 页面/内容 | 补充类型 | 来源状态 | 建议动作 |
|---|---|---|---|
| 第 4—5 页市场指数 | 推演数据 | Agent 生成研究 fixture | 用真实市场数据替换并重新计算 |
| 第 5 页企业增量占比 64.3% | 推演数字 | Agent 生成研究 fixture | 核验分群、口径和预测假设 |
| 第 6 页需求驱动 | 示意访谈 | 不代表真实客户反馈 | 完成真实访谈并更新 Evidence |
| 第 7 页六周计划 | 创作性建议 | TaoHtml 研究样例补全 | 客户确认周期、责任人和成功标准 |

正式阅读模式增加方法和来源展示，但不能用附录取代交付时的待核实清单。

## 8. 第二主题映射假设

主要主题为严谨咨询报告，第二主题选择稳重企业年报。

| 语义意图 | 严谨咨询报告 | 稳重企业年报 |
|---|---|---|
| executive summary | 结论式标题、密集摘要、证据状态栏 | 稳重标题、摘要段落、品牌化信息层级 |
| evidence status | 高密度证据矩阵 | 较舒展的来源与状态分区 |
| data analysis | 白底严谨坐标、方法注释并列 | 图文平衡、主图更大、方法进入侧栏 |
| caveat | 明确限制框和脚注 | 稳重色块与页脚说明 |
| appendix | 高密度来源表 | 分节来源页与较多留白 |

允许发生：

- 图表和文字占比变化；
- 证据矩阵拆成两块；
- 方法说明从右栏移动到页脚；
- 页面留白和图片比重变化。

不得发生：

- 删除模拟标签；
- 隐藏方法或来源；
- 把条件性建议改成确定性结论；
- 因企业年报视觉更舒展而无限缩小正文。

## 9. Patch 与失效传播

| 请求 | 允许的 Patch | 正式模式额外影响 |
|---|---|---|
| 修改报告标题 | 修改 `block_report_title.content` | 新标题必须保持“情景分析”边界，否则语义验证失败 |
| 拆分第 5 页 | 修改 Page 与 Projection | 方法、限制和模拟标签必须在两页中保持可见或明确引用 |
| 替换真实市场数据 | 替换 Source、Dataset、Evidence | 重新计算 Claim、图表、摘要、附录和发布就绪状态 |
| 切换稳重企业年报 | 修改 Theme Binding | 全量视觉 QA，不改变证据状态 |
| 改为演讲模式 | 新建或修改 Projection | 不能只删正文；必须决定证据、限制和方法进入页面、口播还是附录 |

### 证据替换后的升级条件

只有同时满足以下条件，才能把某个 Claim 从 `scenario_only` 提升：

1. 新 Source 已绑定并检查字节身份；
2. 数据时间、地区、对象和口径明确；
3. Evidence 与 Claim 的适配关系重新核验；
4. 所有派生图表重新计算；
5. 摘要、标题、口播和附录没有保留旧数字；
6. 新构建完成浏览器 QA；
7. 交付清单同步更新。

## 10. 初步验证结论

### 当前能够表达

- 同一语义核心的正式阅读投影；
- 动效最少但交互能力独立存在；
- 方法、参数、来源、限制和验证计划；
- 构建成功与真实结论可发布的分离；
- 模拟素材在 formal 模式中保持原身份；
- 页面、附录和交付清单三处披露的不同职责；
- Evidence Patch 对摘要、图表、附录和 QA 的失效传播。

### 当前发现的架构价值

样例 B 说明 `evidence_rigor` 不应只是一个视觉或措辞开关。它必须控制：

- 哪些 Claim 可以写成事实；
- 方法和限制是否必须显性出现；
- 是否需要验证积压清单；
- 标题和摘要允许采用什么确定性语气；
- Evidence 更新后哪些构建记录失效。

### 仍未证明

- Validator 能否用通用规则识别“情景分析标题被改成真实结论”；
- 两套商务主题能否在高信息密度下避免溢出和重复表格；
- 图表交互与正式阅读状态如何进入 Runtime Manifest；
- 把完整方法和来源写入 IR 后，Token 优势是否仍然成立；
- 弱模型是否会为了让报告显得正式而擅自升级来源状态。

### 样例 B 的研究判断

概念层面暂时通过：一套核心 IR 可以同时支持低密度演讲和高密度正式阅读；证据严谨度与信息密度是独立维度。

最重要的结论是：

> formal 可以要求完整论证和严格披露，但不能把模拟材料变成真实证据，也不必因此拒绝完成一份明确标注边界的情景分析报告。
