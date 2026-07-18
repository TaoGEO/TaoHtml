# 教学培训与知识传递

## 身份与版本

- `profile_id`: `teaching-training-knowledge-transfer`
- Definition version: `1.0`
- Status: non-empty foundation definition loaded on demand

## 适用目标

Use as primary when learners must acquire, retain, practice, or apply defined knowledge
or a method, rather than merely agree with a proposition.

## 排除范围

Do not use as primary for a pure persuasive speech, a research conclusion, or a
project/operations status report. Explanatory pages inside another Profile are only a
bounded teaching overlay.

## 成品

Offline HTML courseware or a training deck with clear learning progression, examples,
practice/review moments where supported, facilitator support when requested, current
QA evidence, and the standard delivery handoff.

## 所需信息

Reuse learner baseline, learning objectives, concepts or skills, session context,
available time when provided, examples, misconceptions, practice needs, and assessment
or completion boundaries.

## design-ready 条件

The learner, target capability, prerequisite knowledge, instructional scope,
progression, examples, and any high-risk knowledge sources are clear enough to design
the learning path.

## 叙事任务

Activate prior knowledge, explain the concept or method, demonstrate it, let the
learner rehearse or inspect application, correct common misunderstandings, and close
with a usable review or next step.

## 证据规则

Source factual teaching claims at the rigor required by the domain. Distinguish
verified examples from illustrative exercises and never present a fictional classroom
or customer outcome as achieved evidence.

## 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `presentation` recommendation only after explicit delegation; otherwise inherit or resolve the existing startup choice
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `standard`
- `information_density`: `medium`
- `motion_density`: `moderate`
- `continuation_state`: inherit the Handoff decision

## IR 映射边界

On an independently authorized IR route, the Profile may guide existing narrative,
process, comparison, example, final-state, and notes semantics. It does not add quiz,
assessment, LMS, or learner-state schema.

## Runtime/主题使用

Use current reading or presentation behavior based on the confirmed delivery context.
Any staged explanation must use existing Runtime steps; the Profile creates no
interactive exercise engine or new teaching theme.

## QA 验收

Verify objective-to-content traceability, prerequisite order, concept consistency,
example labeling, exercise instructions, final-state completeness, presenter/reader
usability, and existing technical and delivery gates.

## 能力叠加与冲突处理

Research evidence, brand polish, or live persuasion may be bounded overlays. If the
dominant outcome is audience agreement or purchase rather than learning transfer, use
`live-presentation-persuasion` or `brand-communication-editorial-publishing`.
