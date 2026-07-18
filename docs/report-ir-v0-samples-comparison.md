# Report IR v0 三样例共同核心与差异复核

> 状态：阶段二概念复核，不是 Compiler 实测结果<br>
> 对象：[样例 A：演讲型](report-ir-v0-sample-a-presentation.md)、[样例 B：正式阅读型](report-ir-v0-sample-b-formal-reading.md)、[样例 C：企业模板保真](report-ir-v0-sample-c-corporate-fidelity.md)

## 1. 复核结论

三个样例在概念层面支持“一套核心 IR，多种投影与视觉绑定”的方向，没有发现必须按报告类型或企业模板建立独立 Schema 的理由。

共同核心可以稳定保存：

- Report 目标与受众；
- Chapter 与 Narrative Unit；
- Claim、Evidence、Evidence Link、Source 和 Dataset；
- Content Block；
- Page 任务、Role、Form 和 Visual Intent；
- 待核实、推演、示意和条件性状态；
- 稳定 ID、引用关系和失效传播。

真正发生变化的是：

- Projection；
- 页面数量与信息密度；
- State Sequence 与 Speaker Notes；
- 来源和方法在页面、附录或口播中的投影方式；
- Theme / Project Theme Binding；
- 企业 Shell 和安全区约束；
- 构建与 QA 范围。

## 2. 三样例配置对照

| 维度 | 样例 A：演讲型 | 样例 B：正式阅读型 | 样例 C：企业模板保真 |
|---|---|---|---|
| delivery_mode | presentation | reading | presentation |
| information_density | low | high | medium |
| customer_motion_choice | rich | low | medium |
| motion_density | rich | minimal | medium |
| interaction_level | low | medium | low |
| evidence_rigor | standard | formal | formal |
| 页面数量 | 8 | 8 | 9，增加目录投影页 |
| 主要视觉 | 黑白荧光卡片 | 严谨咨询报告 | 项目专用企业模板 |
| Theme 类型 | built-in | built-in | project theme |
| 固定企业 Shell | 无 | 无 | 有 |
| 安全内容区 | 主题一般安全区 | 主题一般安全区 | 每类 Shell 显式 Editable Region |
| Speaker Notes | 按状态绑定 | 无 | 按状态绑定 |
| 来源呈现 | 页面标签 + 交付清单 | 页面 + 方法 + 附录 + 清单 | 页面标签 + 清单，品牌壳不替代披露 |
| 核心风险 | 低密度导致证据边界消失 | 正式感导致模拟材料被升级 | 企业品牌导致来源状态被误认或内容越界 |

## 3. 同一语义如何投影

以 `claim_growth_concentrated` 为例：

> 模型中的主要增量集中在企业服务。

### 样例 A

- 先出现总量指标；
- 图表随后扩展为主舞台；
- 企业增量占比最后出现；
- 口播明确这是推演；
- 最终阅读状态包含全部内容。

### 样例 B

- 图表、假设表、方法和限制同时可读；
- 标题明确是情景模型结果；
- 无需播放动效；
- 来源与验证积压进入附录；
- `formal_real_world_claim_ready=false`。

### 样例 C

- 沿用演讲状态语义；
- 所有报告 Block 只在 `data-safe` 内重排；
- 固定页眉、页脚和品牌元素不动；
- 数据页 Shell 明确标记为 `extension`；
- 企业模板不改变推演状态。

因此“同一内容”不是“相同页面 DOM”，而是同一语义实体被不同 Projection 与 Build Binding 投影。

## 4. 共同最小核心

三个样例共同要求每个报告至少拥有：

```yaml
report:
  id: stable_report_id
  objective: why_this_report_exists
  audience: intended_audience
  primary_projection_ref: projection_id

narrative_unit:
  id: stable_unit_id
  question: question_to_answer
  takeaway: core_expression
  claim_refs: []
  block_refs: []
  narrative_role: orient_or_assert_or_prove_or_explain_or_decide_or_act

page:
  id: stable_page_id
  narrative_unit_refs: []
  task: page_specific_task
  role: rhetorical_role
  form: visual_form
  surface_block_refs: []
  visual_intent:
    primary_focus: block_id
    reading_order: []
    relationships: []

traceability:
  source_refs: []
  revision_id: stable_revision_id
```

有事实、推论、数据或外部材料时，再强制引入 Claim、Evidence、Evidence Link、Source 和 Dataset。

有演讲状态时，再引入 State Sequence 和 Speaker Notes。

有企业模板时，再通过 Build Binding 引用 Project Theme 与 Shell Capability；不把固定层写入 Content Graph。

## 5. 不能合并的维度

### 5.1 Page Role 与 Shell Role

- Page Role 描述这一页在论证中做什么；
- Shell Role 描述企业主题提供哪种固定外壳。

`prove / data` 可以路由到企业 `data` Shell，也可以在内置主题中映射为普通数据版式。

### 5.2 evidence_rigor 与 information_density

- 正式演讲可以低密度，但证据仍然严格；
- 阅读报告可以高密度，但仍然只是一份明确标注的情景分析；
- 页面文字少不等于证据少；
- 页面正式不等于事实已核验。

### 5.3 motion_density 与 interaction_level

客户界面可以继续只显示一个“动效密度”选项，但规范化 IR 需要拆分：

- motion_density：页面状态和构图变化；
- interaction_level：图表、表格和探索能力；
- state_complexity：状态编排复杂度。

样例 B 就是 `motion=minimal`、`interaction=medium`。

### 5.4 Theme 与 Enterprise Shell

内置主题描述通用设计语言；企业 Shell 描述项目专用固定层和安全区。

未来允许组合时，也必须保持两个引用：

```text
theme_ref
brand_shell_ref
```

当前样例 C 直接使用已经编译好的 Project Theme，不把它注册为第五套内置主题。

## 6. Evidence 不变量复核

三个样例均使用同一组合成 fixture：

| Source | SHA-256 | 身份 |
|---|---|---|
| `market-model.csv` | `77cb67923388107914b1bb33dcbb3772b9887a778b23e4c5a56711920d8d79a2` | Agent 生成推演数据 |
| `methodology.md` | `fc581f63410026023621fe89f500748c02fd753874850697f9fa5af6f9d3eec4` | Agent 生成方法说明 |
| `interview-summary.md` | `305dca2b7e7c40ccc289e9471f44a6147de9f2b57f9ca70f88e667b4c386dadb` | Agent 生成示意访谈 |

跨三个样例必须保持：

1. 文件存在不等于事实核验；
2. 方法说明只解释推演口径；
3. 示意访谈不能写成真实客户反馈；
4. 正式阅读主题不能升级 Source 状态；
5. 企业 Logo 不能升级 Source 状态；
6. 图表是 Evidence 的呈现，不是原始 Source；
7. Evidence 替换必须使所有依赖页面、口播、附录和 QA 失效；
8. 输出时仍需提供《待核实内容清单》。

## 7. Visual Intent 能力复核

三个样例至少使用了以下通用意图：

- `poster`：单一结论焦点；
- `staged_focus`：焦点从指标转向图表；
- `process`：多个模块按讲解顺序进入并重组；
- `comparison`：机会与限制并列；
- `matrix`：候选进入同一决策框架；
- `analytical_report`：图表、方法、限制同时可读；
- `navigation`：目录和章节结构；
- `closing`：行动与边界收束。

目前没有一个意图必须写入任意 HTML、CSS 或 JavaScript。

但这只是概念表达通过，尚未证明 Compiler 能确定性解决：

- 极长中文标题；
- 高密度正式页面；
- 企业安全区中的复杂图表；
- 多状态页面的碰撞；
- 主题能力不足时的自动降级。

## 8. Patch 复核

| 修改 | 共同 IR 操作 | 样例 A | 样例 B | 样例 C |
|---|---|---|---|---|
| 改标题 | Patch Content Block | 页面 QA | 页面 QA + 正式语气校验 | 页面 QA + 安全区 QA |
| 拆页 | 修改 Page / Projection | 状态、口播、导航失效 | 方法、来源可见性需保留 | Shell 路由、安全区、状态失效 |
| 换证据 | 修改 Source / Dataset / Evidence | 图表、口播、披露失效 | 摘要、方法、附录、发布状态失效 | 同左，企业主题仍有效 |
| 换主题 | 修改 Build Binding | 全量视觉 QA | 全量视觉 QA | 去除或替换企业 Shell，全量视觉 QA |
| 减少动效 | 修改 State Sequence | 口播同步失效 | 通常无影响 | 只改安全区内报告状态，固定层不动 |
| 更新企业 VI | 不适用 | 不适用 | 不适用 | 新建 Project Theme 版本，全量企业 QA |

稳定 ID 可以定位修改范围，但不能自动证明修改后的语义仍然正确。

## 9. 初步架构判断

### 概念层面通过

1. 一套核心 IR 可以表达演讲、正式阅读和企业模板保真。
2. Narrative Unit 能把语义内容与具体页数分开。
3. Claim—Evidence—Source 图能跨投影复用。
4. Page Role / Form 与 Theme / Shell Binding 可以分层。
5. State Sequence 能表达构图变化而不绑定动画库。
6. 企业固定层可以作为项目主题依赖，不污染内容图。
7. 待核实和推演状态能够跨三种投影保留。

### 仍未通过

1. 已有研究 Validator 验证引用、可执行内容禁区和固定五页合同，但还不是正式 Schema Validator。
2. 已有无模型调用的研究 Compiler，并已通过重复编译、局部标题 Patch 和主题切换；它仍只覆盖固定五页原型，不是生产级通用 Compiler。
3. 黑白荧光卡片与严谨咨询报告已有真实构建和三视口浏览器截图对照，当前 fixture 通过；其他主题与开放页面结构仍未验证。
4. 尚无 Token 实测。
5. 尚无强、中、弱模型重复对照；WorkBuddy Auto 只完成了一次修复前独立执行。
6. 尚未验证浏览器编辑 Patch 能回写 IR。
7. 尚未证明企业安全区内所有复杂图表都不会文字重叠。

### 阶段二结论

三个代表性样例已完成概念表达，小型 Validator 与固定五页 Compiler 可行性也已通过。下一步应重复独立模型盲测，并验证局部修改成本、开放页面结构和 Token，而不是继续增加更多行业字段。

当前不能据此宣布 Report IR 已经成为 TaoHtml 的生产能力，也不能修改 Handoff 的真源定义。
