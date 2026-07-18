# Report IR v1 工程合同

Report IR v1 是 TaoHtml 的可重新编译报告源，不是客户问卷、固定 PPT 模板或 HTML DOM 描述。

## 用户选择与 IR 字段

客户只选择真实业务需求，不手工挑选 JSON 字段。

| 客户需求 | IR 组合 |
|---|---|
| 现场演讲 | `presentation` Projection，必要页加 State Sequence 和 Speaker Notes |
| 仅阅读 | `reading` Projection，以完整最终状态为主 |
| 正式研究 | `formal` 证据严谨度，事实和推论必须建立 Claim—Evidence—Source 链 |
| 数据图表 | Dataset、口径、方法、来源与 Data Visualization Block |
| 客户参考风格重构 | Project Theme，不要求 Enterprise Binding |
| 企业模板保真 | `corporate_fidelity` Project Theme 与 Enterprise Binding，内容图不复制 Logo 和页眉页脚 |
| 有待核实内容 | 保留可用内容，将实体绑定到 `traceability.unresolved_items` |

Skill 根据已确认的设计简报生成这些组合。不向客户暴露一份新的工程问卷。

## 固定核心

每个 Report IR 都必须拥有：

- Report：目标、受众、报告原型与证据严谨度；
- Projection：交付模式、信息密度、动效配置与页面顺序；
- Chapter 与 Narrative Unit：与具体页数解耦的叙事结构；
- Content Block：按语义命名的标题、正文、数据、流程、比较和素材；
- Page：页面任务、修辞角色、形式、内容引用和 Visual Intent；
- Build Binding：主题、Runtime 和可选企业绑定；
- Traceability：设计简报引用、修订标识和待核实清单。

`traceability.design_brief_confirmation` 必须显式写入，Validator 不从文件存在或流程上下文
猜测确认状态。只有 `confirmed` 可进入 Compiler；`reconfirmation_required` 保留为可审阅草稿。

Claim、Evidence、Source、Dataset、Asset、State Sequence、Speaker Notes 和 Appendix 只在当前场景需要时出现。

## 不变量

1. 所有工程实体使用全局唯一稳定 ID。
2. 所有引用必须可解析。
3. `page_order` 必须且只能包含当前 Projection 的所有页面。
4. 每个 Page 只有一个主要任务，阅读顺序覆盖所有页面 Block。
5. 有 State Sequence 时，阅读最终状态必须显示该页所有 Block。
6. 正式模式下的已核实事实或推论必须具有已核实支持证据。
7. 示意、推演、争议和待核实实体必须进入 `unresolved_items`。
8. IR 禁止携带 HTML、CSS、JavaScript、事件处理器或远程脚本。
9. Compiler 不重写观点、不发明证据、不修改数据口径。
10. Validator 只验证已有记录，不执行浏览器 QA。

## 验证层

`validate_report_ir.py` 分别输出：

- `schema_valid`：字段、类型和封闭对象合法；
- `references_valid`：稳定 ID 唯一且引用可解析；
- `semantics_valid`：证据、最终状态、待核实和交付模式不变量成立；
- `compiler_ready`：当前主题、扩展和 Runtime 绑定可由当前 Compiler 处理。

这四层不得合并成一个含糊的 PASS。

## CLI

```bash
python scripts/validate_report_ir.py report-ir.json \
  --artifact-root project \
  --output report-ir-validation.json \
  --normalized-output report-ir.normalized.json
```

只有四层全部通过时才写出规范化 IR。规范化只补充中性默认值，不新增观点、证据、页面或文字。

## Compiler 开发节点

`compile_report_ir.py` 已建立第一个无模型编译核心：

- 接受任意章节数、任意页数和稳定 ID，不依赖五页测试顺序；
- 把 Headline、Claim、Evidence、Dataset、Process、Comparison、Image 等语义 Block 编译为可追踪 DOM；
- 把单调展开的 State Sequence 编译为现有 `fragment-v1` Runtime 步骤；
- 同一份语义图可以切换四套内置视觉系统，不重新生成内容；
- 输出 `index.html`、规范化 IR、Source Map 和 Build Manifest；
- Build Manifest 分别记录 IR、语义图、主题、Compiler、Runtime 和输出哈希；
- Source 可记录标题、作者、发布者、日期和页码定位，文件存在与事实核验仍是不同状态；
- Compiler 不调用模型，不发明内容，不因内容放不下而自动删改观点。

```bash
python scripts/compile_report_ir.py report-ir.json \
  --artifact-root project \
  --output-dir project/build
```

客户参考主题或企业模板还需提供已通过 `load_project_theme` 完整校验的主题目录：

```bash
python scripts/compile_report_ir.py report-ir.json \
  --artifact-root project \
  --project-theme-dir project/theme \
  --output-dir project/build
```

`project_theme` 同时覆盖普通参考风格重构与企业模板保真。只有主题清单声明
`reference_mode=corporate_fidelity` 时才必须存在 `build_binding.enterprise`；普通参考风格
重构不能伪装成企业模板保真。

Compiler 只接受四层验证全部通过的 IR。高级状态如果超出当前 Runtime 能力，必须在 Build Manifest 中记录降级；非单调显示、未知必需扩展或语义不安全的降级直接停止编译。

当前 Compiler 开发版本已经接入四套内置主题、客户参考重构主题和企业模板固定壳。
企业保真编译会为任意页数按页面语义路由 cover / toc / section / content / data 壳，只向
已验证的 editable safe region 注入报告内容，并保持固定 Logo、页眉、页脚和装饰子树不变。

Runtime 编辑器现在会在导出的 HTML 内嵌一个受约束的 `Report IR Runtime Patch`。它只记录
Compiler 明确标记的文字字段与内容图片，不携带任意 HTML、CSS 或 JavaScript。Patch 绑定
规范化基础 IR 的 SHA-256、Report ID 和 Projection ID；Agent 必须把它应用回 IR 后重新编译，
不能把导出的 HTML 当作新的报告真源。

```bash
python scripts/apply_report_ir_patch.py report-ir.json \
  --edited-html report-edited.html \
  --artifact-root project \
  --output-ir project/report.ir.edited.json \
  --output-report project/runtime-patch-report.json \
  --meaning-impact preserving
```

`--meaning-impact` 必须由 Agent 或客户明确归类：

- `preserving`：只修正文案、图片或呈现，不改变已经确认的核心含义；Patch 报告允许重新编译；
- `changing`：改变核心观点、证据含义或整体结构；脚本写出草稿 IR 和报告，但以退出码 `2`
  返回 `RECONFIRMATION_REQUIRED`，并把
  `traceability.design_brief_confirmation` 设为 `reconfirmation_required`。Validator 保留
  Schema、引用和语义结果，但令 `compiler_ready=false`；设计简报重新确认并更新该字段前，
  Compiler 必须拒绝构建。

图片替换后，文件字节、格式、路径和哈希会被验证并写回 Asset；因为 Runtime 无法证明新图的
事实、品牌与授权含义，Asset 自动改为 `pending_verification` 并进入 `unresolved_items`。图表
数据、表格结构、版式和动效仍由 Agent 修改，不开放为 Runtime Patch。

受约束高级 Composition Graph、非单调状态 Runtime 和增量编译尚未接入；这些边界同时写入
Build Manifest，不能被误认为已实现。

## 当前阶段边界

本文件、v1 Validator 和通用主题 Compiler 是 Report IR 的研究工程节点。当前代码可用于
研究构建与对照测试，但在复杂构图、增量编译和完整跨模型回归基准完成前，
不对客户声称 Report IR 已经是正式能力，也不进入三平台发布包。
