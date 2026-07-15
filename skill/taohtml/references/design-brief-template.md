# Report Design Brief Template

Generate this brief only after the route-appropriate source gate and the design-ready gate in `intake-workflow.md` both pass. Word/PDF requires a confirmed Material Understanding Summary; an idea-only route does not. If any high-risk gap remains, use the blocked-intake output instead of this template.

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
- 希望受众理解、相信或采取的行动：...

## 必须保留的核心观点
1. ...

## 章节结构

### 第一章：...
- 本章任务：...
- 核心观点：...
- 支撑证据：...
- 预期结论：...

## 视觉与动效方向
- 视觉方向或参考：...
- 选择理由：...
- 动效密度：少量 / 适中 / 丰富
- 阅读与演讲行为：...

## 来源与证据记录
- 来源：...
- 支撑观点：...
- 最终页面是否展示及展示位置：...

## 交付约束
- 离线、画布、浏览器、素材和附件要求

## 待确认项
- TaoHtml 的自动推断及依据：...
- 补全内容：...
- 数据修正及原因：...
- 其他会影响成品的判断：...

回复“确认”后，TaoHtml 将按这份设计简报开始制作 HTML。
```

## Adaptation Rules

- For a simple report, merge short sections and keep the brief compact.
- For a complex report, preserve the chapter-level viewpoint, evidence, and conclusion mapping.
- If the user supplied a clear visual reference, record whether it should be closely reproduced or treated as design DNA.
- If TaoHtml recommends a visual direction, explain why it suits the topic, audience, and use mode.
- Put every automatic inference and its basis, content addition, and data correction in `待确认项`, even when confidence is high. This is where all `inferred` ledger items receive unified confirmation.
- Never disguise a high-risk unresolved decision as an inference. Return to the blocked-intake output in `intake-workflow.md` instead.
- Keep source records in the brief whether or not the final pages visibly cite them.
- Do not split content into slide copy, speaker notes, and appendix at this stage; production makes that allocation from the confirmed mode.

## Authorization

The brief must be displayed as a whole before asking for confirmation. If the customer edits one section, revise the whole current brief and request one final confirmation. Only then begin production.
