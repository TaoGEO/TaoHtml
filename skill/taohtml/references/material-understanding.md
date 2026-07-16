# Material Understanding

Use this reference for an explicitly bound Word, PDF, PPT, or HTML input before designing or migrating the report.

## Goal

Build a source-grounded understanding that the user can correct. Do not propose page layouts, visual styles, or animation during this stage.

## Inspection

Before opening a PDF, run the `pdf` profile in `environment-preflight.md`. Inspect
only materials already eligible under the intake workflow's source-binding rules.
Do not open a workspace candidate to decide whether it should be bound.

Inspect the complete available source, not only the first pages. Extract:

- Topic and intended purpose stated by the material
- Original section structure
- Core viewpoints that must not be lost
- Data, examples, screenshots, cases, quotations, and other evidence
- Source labels, links, footnotes, and attachment references
- Repeated, weak, or contradictory claims
- Missing units, inconsistent definitions, or data that cannot be interpreted safely

If the file cannot be read completely, say exactly which part is unavailable and request a usable copy. Do not pretend the source was fully inspected.

## Complexity

Judge complexity from the combination of:

- Amount and variety of source material
- Length and likely page count
- Number of claims and evidence relationships
- Logical or data conflicts
- Importance of the intended use

For simple material, keep the summary short. For complex material, include evidence gaps and conflicts.

## Material Understanding Summary

Use this adaptive structure:

```markdown
# 材料理解摘要

## 主题与目的
...

## 原始结构
1. ...

## 必须保留的核心观点
- ...

## 已有证据与数据
- 观点：...
  - 支撑材料：...

## 材料来源绑定
- 材料：路径或上传标识
  - source_binding：current_upload_or_user_explicit / task_instruction_explicit / candidate_confirmed
  - 来源理由：用户当前上传或明确指定 / 当前任务说明明确声明 / Agent 展示候选路径后获用户确认

## 发现的问题
- 重复、缺口、冲突或数据口径问题

## 当前理解
- TaoHtml 对材料整体逻辑的简要复述

请确认以上理解是否准确，或直接指出需要修正的部分。
```

Remove empty sections rather than filling them with placeholders.

Keep `材料来源绑定` for every material actually used. This is provenance, not a
creative-supplement disclosure. Do not describe an explicitly bound material as
TaoHtml-generated content.

## Evidence And Data

Determine required evidence from the report type and claim. Data, cases, outcomes, comparisons, risk claims, and conclusion-level judgments normally require support.

Use this order:

1. Search the customer's material.
2. If a required gap remains and browsing is available, find public evidence.
3. Show the public source and the conclusion it would support for customer confirmation.
4. If public evidence conflicts with customer material, show both sides and the impact; do not choose silently when it changes the conclusion.

Customer data visualized by the agent remains customer evidence. Never alter it, relabel it as generated, or invent values and present them as customer evidence. When a useful report needs an illustrative chart, use separately tracked simulated values, label the chart `示意 / 模拟 / 待核实` next to the visual, and include the values in the delivery verification list.

When units or definitions are inconsistent, correct only what can be determined safely. Put every correction, reason, and consequence in the design brief's confirmation section.

Keep a source record even when the customer does not want citations displayed in the final pages. The design brief should identify the source, supported viewpoint, and intended use.

## Summary Confirmation

Wait for explicit confirmation or correction. A confirmed summary freezes the source interpretation, not the final report structure. Structure and visual decisions follow in the intake workflow.
