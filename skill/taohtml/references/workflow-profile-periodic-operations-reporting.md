# 周期经营与数据汇报

## 身份与版本

- `profile_id`: `periodic-operations-reporting`
- Definition version: `1.0`
- Status: non-empty foundation definition loaded on demand

## 适用目标

Use as primary for weekly, monthly, quarterly, annual, or other recurring management
reporting whose main job is to explain results, variance, drivers, risks, and actions.

## 排除范围

Do not use as primary for a one-time strategic proposal, open-ended research study, or
project-only status report whose scope is governed by a project baseline rather than
an operating cadence.

## 成品

An offline operating report with governed metrics, period comparisons, causal
interpretation, management decisions, accountable next actions, QA evidence, and the
standard delivery handoff.

## 所需信息

Reuse the reporting period, audience, metric definitions, data cutoff, targets,
baselines, comparison periods, anomalies, known drivers, risk thresholds, owners, and
management questions from eligible sources.

## design-ready 条件

The time boundary, metric definitions, comparison basis, material data gaps, decision
questions, and responsibility boundary are clear. Data likely to change conclusions
must be verified or visibly withheld.

## 叙事任务

State the period result, compare it with the right baseline, explain material drivers,
surface risks and opportunities, identify decisions, and close with owned next actions.

## 证据规则

Bind each important metric to source, cutoff, unit, denominator, and comparison basis.
Separate measured results from forecasts and explanations; label simulated or
projected data that could be mistaken for actual performance.

## 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `reading` recommendation only after explicit delegation; otherwise inherit or resolve the existing startup choice
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `formal`
- `information_density`: `high`
- `motion_density`: `minimal`
- `continuation_state`: inherit the Handoff decision

## IR 映射边界

On an independently authorized IR route, the Profile may guide existing dataset,
data-visualization, comparison, process, and traceability semantics. It cannot add
metric fields, data connectors, or incremental compilation.

## Runtime/主题使用

Use current reading or presentation behavior after use mode is established and the
existing chart/evidence treatments. The Profile does not implement dashboards, live
data refresh, or new visualization components.

## QA 验收

Verify metric math, unit and period consistency, target/baseline labels, chart-source
traceability, forecast separation, action ownership, compound requirement coverage,
and existing asset, browser, traceability, and delivery gates.

## 能力叠加与冲突处理

Research explanation or live presentation may be bounded overlays. If the baseline is
a single project's scope, plan, and milestones, use `project-lifecycle-reporting`; if
the report chiefly seeks approval for a new option, use `proposal-planning-decision`.
