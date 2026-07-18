# 项目全过程汇报

## 身份与版本

- `profile_id`: `project-lifecycle-reporting`
- Definition version: `1.0`
- Status: non-empty foundation definition loaded on demand

## 适用目标

Use as primary when stakeholders must understand and govern a project's objective,
scope, plan, current phase, progress, changes, risks, decisions, outcomes, or closure.

## 排除范围

Do not use as primary for organization-wide recurring operations, an unstarted option
proposal, or an application governed by external scoring rules. A project example
inside another report does not select this Profile.

## 成品

An offline lifecycle report appropriate to the current project phase, with baseline,
status, decisions, risk/change history, next steps or closure evidence, current QA,
and the standard delivery handoff.

## 所需信息

Reuse the project objective, sponsor and audience, scope baseline, phase, milestones,
deliverables, progress evidence, changes, issues, risks, decisions, owners, dependencies,
and success/closure criteria.

## design-ready 条件

The project identity, phase, baseline, reporting cutoff, material deviations, decision
needs, source availability, and responsibility boundary are clear. Achieved outcomes
must be supported by current project evidence.

## 叙事任务

Re-establish objective and baseline, locate the current phase, show completed and
remaining work, explain changes and variance, surface risks and decisions, and close
with owned next steps or verified closure.

## 证据规则

Bind status and outcomes to dated artifacts, records, or explicit confirmations.
Distinguish planned, in-progress, blocked, delivered, and accepted; never collapse an
existing artifact or handoff claim into verified acceptance.

## 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `reading` recommendation only after explicit delegation; otherwise inherit or resolve the existing startup choice
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `formal`
- `information_density`: `high`
- `motion_density`: `minimal`
- `continuation_state`: inherit the Handoff decision

## IR 映射边界

On an independently authorized IR route, the Profile may guide existing timeline,
process, evidence, comparison, status narrative, and appendix semantics. It does not
create project databases, live status integrations, or a new Handoff schema.

## Runtime/主题使用

Use existing Runtime modes and visual routes after use mode is established. The
Profile does not implement project management controls, live timelines, or persistent
workspace state.

## QA 验收

Verify baseline/current-state distinction, milestone and date consistency, change and
risk coverage, owner/decision clarity, outcome acceptance evidence, handoff readiness
language, traceability, and existing technical/delivery gates.

## 能力叠加与冲突处理

Periodic metrics or decision-proposal modules may be bounded overlays. If the artifact
governs a recurring business cadence rather than one project baseline, use
`periodic-operations-reporting`.
