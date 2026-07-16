# Report Design Brief Template

Generate this brief only after the route-appropriate source gate and the design-ready gate in `intake-workflow.md` both pass. Word/PDF requires a confirmed Material Understanding Summary; an idea-only route does not. If a minimum hard-boundary gap remains, use the blocked-intake output instead of this template. Ordinary missing details may be completed after confirmation and disclosed in the delivery verification list.

Keep it readable by the customer. Include only fields that affect this project. Do not emit a separate JSON configuration and do not pre-design every page.

```markdown
# 报告设计简报

## 项目定义
- 输入入口：只有想法 / Word / PDF / 已有 PPT / HTML
- 使用模式：阅读 / 现场演讲
- 内容长度：精简 / 标准 / 详细
- 预计页数：根据当前材料动态估算
- 交付形式：单 HTML，或 HTML + assets / ZIP

## 报告目标
- 受众：...
- 希望受众理解或相信：...
- 期望行动：...

## 行动闭环（仅在目标要求外部行动时保留）
- 真实执行路径：完整 URL / Agent 调用语法 / 命令 / 下载或预约入口 / 联系方式
- 渠道来源与验证状态：用户明确提供 / 来源材料或项目上下文 + 验证方式与结果 / 用户授权 TaoHtml 选择 + 独立验证结果
- 最终页面展示方式：可见链接、完整命令、联系方式，或已解码核对且同时展示文本入口的二维码

## 必须保留的核心观点
1. ...

## 章节结构

### 第一章：...
- 本章任务：...
- 核心观点：...
- 支撑证据：...
- 预期结论：...

## 视觉方向
- 视觉来源：用户明确参考 / TaoHtml 内置主题
- 用户参考（如适用）：本地文件或可定位描述
- 参考图模式（如适用）：`reconstruct` 参考风格重构 / `corporate_fidelity` 企业模板保真
- 保真边界（企业模板保真时保留）：只承诺截图中可见效果；不承诺恢复原始 PPT 母版、矢量 Logo、字体源文件或截图外资产
- 来源页面与角色（企业模板保真时保留）：每页 id、自动识别的 cover / toc / section / content / data 角色、源图哈希与尺寸、canvas_bbox、observed 状态
- 锁定企业元素（企业模板保真时保留）：shared asset 与各 shell 固定 placement 的 id、类型、来源页、归一化 bbox、确认状态
- 可编辑安全区（企业模板保真时保留）：每个 shell 的区域 id、归一化 bbox、唯一允许内容角色；固定层不参与排版或动效
- 参考事实边界（如适用）：`observed` 直接观察 / `extension` 可确认延展 / `unknown` 截图无法判断；按 source / shell / asset / page role 分别记录
- 延展页面与限制（企业模板保真时保留）：所有未观察角色的 proposed extension 状态；更清晰截图等真实阻塞项；不承诺独立 Logo 上传
- VI 规范图（静态参考时保留）：统一 PNG / HTML 路径 + 已确认状态
- 所选内置主题（如适用）：完整主题名称 + 一句具体画面描述
- 选择理由：...
- 必要偏离说明：无 / 偏离项、原因及仍保留的主题语法
- 阅读与演讲行为：...

## 来源与证据记录
- 来源：路径或上传标识
- source_binding：current_upload_or_user_explicit / task_instruction_explicit / candidate_confirmed
- 来源理由：...
- 支撑观点：...
- 最终页面是否展示及展示位置：...

## 交付约束
- 离线、画布、浏览器、素材和附件要求

## 待确认项
- TaoHtml 的自动推断及依据：...
- 预计创作性补全范围：可能补充的场景、数字、观点、示例或表达；具体生成内容将在交付时逐条列入《待核实内容清单》
- 数据修正及原因：...
- 其他会影响成品的判断：...

回复“确认”后，TaoHtml 将按这份设计简报开始制作 HTML。
```

## Adaptation Rules

- For a simple report, merge short sections and keep the brief compact.
- For a complex report, preserve the chapter-level viewpoint, evidence, and conclusion mapping.
- If the user supplied a clear visual reference, record `reference_mode`. Do not reduce `corporate_fidelity` to “closely reproduced”: state the screenshot-visible fidelity boundary, locked elements, editable region, and extension/unknown limits explicitly.
- If the user supplied a clear visual reference, do not add a competing built-in-theme requirement.
- For supported static-reference inputs, include the confirmed unified VI board path and confirmation state. In corporate fidelity, copy the exact source-role, canvas, shared-asset, shell placement, editable-region, extension, and limitation summary from the confirmed contract; do not silently alter it after “确认 VI”. Do not include a dynamic-analysis field or infer sequential behavior from multiple stills.
- Treat VI confirmation and Report Design Brief confirmation as separate gates. A confirmed VI board may enter the separate project-theme handoff, but it does not authorize report production.
- If TaoHtml recommends or selects a built-in visual system, copy its full customer-facing name and one-line description, explain why it suits the topic, audience, and use mode, and record every necessary deviation. Write `无` when there is no deviation.
- Include `行动闭环` only when the confirmed goal requires the audience to complete an external action. Omit it for explanatory, educational, or internal reports that do not require conversion; do not add a gratuitous CTA.
- Copy the exact verified action path into the brief. Record its provenance and verification status separately from the desired action, and state how the audience will see and use it on the final page.
- Put every outcome-changing design inference and its basis, planned creative-supplement scope, and source-data correction in `待确认项`. This is where `inferred` design-ledger items receive unified confirmation; do not require the customer to pre-approve every production sentence or illustrative value.
- During production, record each actual creative supplement in the delivery verification ledger rather than silently converting it into a source fact. Do not list customer-provided or independently verified facts as creative supplements.
- Never disguise a minimum hard-boundary decision as an inference. Return to the blocked-intake output in `intake-workflow.md` instead.
- Keep source records in the brief whether or not the final pages visibly cite them.
- Copy every used material's source identity, `source_binding`, and binding reason from the source ledger. Do not include a merely discovered or conventionally named workspace file, and do not relabel an eligible bound source as a creative supplement.
- Do not split content into slide copy, speaker notes, and appendix at this stage; production makes that allocation from the confirmed mode.

## Authorization

The brief must be displayed as a whole before asking for confirmation. If the customer edits one section, revise the whole current brief and request one final confirmation. Only then begin production.
