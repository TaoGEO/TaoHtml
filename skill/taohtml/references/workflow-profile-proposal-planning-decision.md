# 方案策划与决策提案

## 身份与版本

- `profile_id`: `proposal-planning-decision`
- Definition version: `1.0`
- Status: non-empty foundation definition only; the Golden Path detailed workflow is outside this engineering node

## 适用目标

Use as primary when a defined decision maker must choose, approve, fund, prioritize,
or authorize a plan based on options, criteria, trade-offs, recommendation, and risk.

## 排除范围

Do not use as primary when live stage performance itself is the main product, when the
artifact only reports recurring results, or when success is governed by an external
application/scoring rule rather than the decision case.

## 成品

A decision-ready offline HTML proposal that makes the decision, options, trade-offs,
recommendation, assumptions, implementation boundary, and risks independently clear,
with existing QA and delivery evidence.

## 所需信息

Reuse the decision owner, decision to make, constraints, criteria, available options,
non-negotiables, evidence, budget/time boundaries, implementation responsibilities,
and required next action. Do not introduce a Profile questionnaire.

## design-ready 条件

The decision, decision maker, evaluation criteria, plausible alternatives, material
trade-offs, evidence boundary, implementation responsibility, and action path when
external action is required are sufficiently clear for brief confirmation.

## 叙事任务

Frame the decision, make criteria visible, compare viable options, explain the
recommendation, expose assumptions and risks, and show the implementation and decision
closure without prescribing fixed pages.

## 证据规则

Tie material benefits, costs, feasibility, and risks to sources or explicit
assumptions. Never disguise a preferred option as the only option or present projected
outcomes as achieved results.

## 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `reading` recommendation only after explicit delegation; otherwise inherit or resolve the existing startup choice
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `standard`
- `information_density`: `medium`
- `motion_density`: `minimal`
- `continuation_state`: inherit the Handoff decision

## IR 映射边界

On an independently authorized IR route, the Profile may guide existing comparison,
process, claim, evidence, and narrative-unit semantics. It does not define a proposal
schema, decision engine, scoring algorithm, or Compiler branch.

## Runtime/主题使用

Use the confirmed reading/presentation mode and the existing visual route. The Profile
does not add complex composition, cross-page motion, or decision-model widgets.

## QA 验收

Verify decision clarity, option completeness, criteria consistency, trade-off and risk
visibility, recommendation support, implementation ownership, exact action-path
traceability when applicable, and all existing objective QA and delivery gates.

## 能力叠加与冲突处理

Research support, operating data, or live delivery may be bounded overlays. If the
primary success condition becomes spoken audience persuasion, switch to
`live-presentation-persuasion`; never run both Golden Paths as full workflows.
