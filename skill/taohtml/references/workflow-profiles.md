# Workflow Profiles

This is the foundation catalog for TaoHtml's nine business-production paths. Load it
only after reading `workflow-profile-contract.md` and only when Profile selection or
the selected Profile's definition is needed. TaoHtml remains one installed Skill.

## Contents

- [Catalog](#catalog)
- [1. 规范报送与正式写作](#1-规范报送与正式写作)
- [2. 研究分析与专业论证](#2-研究分析与专业论证)
- [3. 周期经营与数据汇报](#3-周期经营与数据汇报)
- [4. 方案策划与决策提案](#4-方案策划与决策提案)
- [5. 现场演讲与说服表达](#5-现场演讲与说服表达)
- [6. 教学培训与知识传递](#6-教学培训与知识传递)
- [7. 项目全过程汇报](#7-项目全过程汇报)
- [8. 品牌传播与编辑出版](#8-品牌传播与编辑出版)
- [9. 规则响应、申报与答辩](#9-规则响应申报与答辩)

## Catalog

| profile_id | Stable customer-facing name | Primary outcome |
|---|---|---|
| `formal-submission-writing` | 规范报送与正式写作 | Produce a formal, institution-ready artifact whose wording, required sections, and responsibility boundary can withstand review. |
| `research-analysis-argumentation` | 研究分析与专业论证 | Answer a substantive question through transparent method, evidence, reasoning, and bounded conclusions. |
| `periodic-operations-reporting` | 周期经营与数据汇报 | Explain period performance, variance, drivers, risks, and next management actions from governed data. |
| `proposal-planning-decision` | 方案策划与决策提案 | Enable a defined decision through options, criteria, trade-offs, recommendation, and implementation risk. |
| `live-presentation-persuasion` | 现场演讲与说服表达 | Help a presenter move a live audience toward a belief, decision, or action through spoken rhythm and visible proof. |
| `teaching-training-knowledge-transfer` | 教学培训与知识传递 | Move learners from current understanding to usable knowledge through explanation, demonstration, practice, and review. |
| `project-lifecycle-reporting` | 项目全过程汇报 | Keep project stakeholders aligned on objective, scope, phase, progress, change, risk, decisions, and closure. |
| `brand-communication-editorial-publishing` | 品牌传播与编辑出版 | Shape a credible, memorable public-facing narrative while protecting identity, claims, assets, and action paths. |
| `rule-response-application-defense` | 规则响应、申报与答辩 | Satisfy authoritative rules or scoring criteria with complete responses, traceable evidence, and defensible answers. |

When routing is ambiguous, display all nine names above in the same round and ask the
user to choose the primary business goal. Do not show internal ids or the definitions
below unless they help explain a material decision.

## Foundation Definitions

### 1. 规范报送与正式写作

#### 身份与版本

- `profile_id`: `formal-submission-writing`
- Definition version: `1.0`
- Status: foundation definition; no separate detailed workflow file in this node

#### 适用目标

Use as primary when the finished artifact must be formally submitted, circulated, or
archived under institutional expectations, and correctness of required sections,
terminology, tone, and responsibility boundary is more important than novelty or
stage performance.

#### 排除范围

Do not use as primary when the central job is new research reasoning, recurring
operating analysis, option selection, or compliance against an explicit scoring
rubric. Formal tone alone does not select this Profile.

#### 成品

A customer-readable, offline formal HTML report with the required chapter coverage,
traceable source handling, current QA evidence, and the standard delivery verification
handoff. Supporting export formats remain subject to existing TaoHtml capabilities.

#### 所需信息

Reuse the known recipient, purpose, mandatory sections, terminology, scope, deadline,
source authority, and submission constraints. Ask only for a genuinely result-changing
gap not already present in eligible material.

#### design-ready 条件

In addition to the common gate, the addressee, formal purpose, required content,
responsibility boundary, and authoritative source set must be clear. Mandatory facts
and high-risk statements must be verified or explicitly blocked.

#### 叙事任务

Establish the mandate and scope, present the relevant facts, develop the required
analysis, state conclusions or requests precisely, and make responsibilities and
follow-up conditions unambiguous.

#### 证据规则

Preserve exact official terminology, dates, identities, citations, and source status.
Separate facts, interpretation, and proposed language. Never use creative supplements
to fill mandatory official facts or authoritative-source gaps.

#### 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `reading`
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `formal`
- `information_density`: `medium`
- `motion_density`: `low`
- `continuation_state`: inherit the Handoff decision

#### IR 映射边界

If the explicit IR engineering route is independently authorized, this Profile may
guide formal evidence rigor and institutional narrative semantics. It does not create
schema fields, activate the Compiler, or expose IR choices to the user.

#### Runtime/主题使用

Use the existing reading Runtime by default and the selected built-in, project, or
enterprise theme. The Profile does not define formal-document CSS, Runtime behavior,
or a new theme family.

#### QA 验收

Verify required-section completeness, terminology consistency, source traceability,
date/version accuracy, responsibility wording, offline assets, exact-artifact browser
QA, and the existing delivery gate.

#### 能力叠加与冲突处理

Data summaries or teaching explanations may be bounded overlays. If an authoritative
rule or scoring matrix determines success, use `rule-response-application-defense` as
primary; if new knowledge claims and methods dominate, use
`research-analysis-argumentation`.

### 2. 研究分析与专业论证

#### 身份与版本

- `profile_id`: `research-analysis-argumentation`
- Definition version: `1.0`
- Status: foundation definition; no separate detailed workflow file in this node

#### 适用目标

Use as primary when the report must answer a substantive question, evaluate a
hypothesis, explain a mechanism, or defend a professional conclusion through visible
method and evidence.

#### 排除范围

Do not use as primary for a fixed institutional submission, routine KPI cycle, or
public brand story when original analysis is not the dominant outcome. A citation-rich
document is not automatically a research Profile.

#### 成品

An evidence-led offline HTML analysis with a clear question, method, claim-evidence
chain, bounded conclusion, limitations, QA record, and delivery verification handoff.

#### 所需信息

Reuse the research question, audience, decision context, scope, source corpus,
definitions, methods, competing explanations, and required conclusion strength.
Request only gaps that can reverse the conclusion or invalidate the method.

#### design-ready 条件

The central question, scope, method, evidence boundary, material conflicts, and
acceptable conclusion strength are clear. Unsupported high-impact claims are removed,
bounded, or held pending authoritative evidence.

#### 叙事任务

Frame the question, explain the method and evidence base, test claims and alternatives,
show the reasoning, state the conclusion, and expose limitations and unresolved items.

#### 证据规则

Maintain explicit Claim-Evidence-Source relationships for material conclusions.
Distinguish observation, inference, projection, and unresolved conflict; never convert
a plausible explanation into a verified finding.

#### 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `reading`
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `formal`
- `information_density`: `high`
- `motion_density`: `low`
- `continuation_state`: inherit the Handoff decision

#### IR 映射边界

On an independently authorized IR route, the Profile may guide research prototype,
formal evidence rigor, semantic claims, evidence, sources, datasets, and appendices
already supported by the current contract. It does not modify or bypass the Validator.

#### Runtime/主题使用

Use existing reading or presentation behavior according to the confirmed use mode.
Themes organize evidence but must not change claim strength or imply unsupported
authority.

#### QA 验收

Verify question-to-conclusion traceability, method clarity, source coverage, claim
support, counterevidence, data definitions, limitations, source visibility, and all
existing technical and delivery checks.

#### 能力叠加与冲突处理

Live explanation or editorial polish may be overlays. If the artifact primarily asks
decision makers to choose among actions, use `proposal-planning-decision`; if it must
meet an external rule matrix, use `rule-response-application-defense`.

### 3. 周期经营与数据汇报

#### 身份与版本

- `profile_id`: `periodic-operations-reporting`
- Definition version: `1.0`
- Status: foundation definition; no separate detailed workflow file in this node

#### 适用目标

Use as primary for weekly, monthly, quarterly, annual, or other recurring management
reporting whose main job is to explain results, variance, drivers, risks, and actions.

#### 排除范围

Do not use as primary for a one-time strategic proposal, open-ended research study, or
project-only status report whose scope is governed by a project baseline rather than
an operating cadence.

#### 成品

An offline operating report with governed metrics, period comparisons, causal
interpretation, management decisions, accountable next actions, QA evidence, and the
standard delivery handoff.

#### 所需信息

Reuse the reporting period, audience, metric definitions, data cutoff, targets,
baselines, comparison periods, anomalies, known drivers, risk thresholds, owners, and
management questions from eligible sources.

#### design-ready 条件

The time boundary, metric definitions, comparison basis, material data gaps, decision
questions, and responsibility boundary are clear. Data likely to change conclusions
must be verified or visibly withheld.

#### 叙事任务

State the period result, compare it with the right baseline, explain material drivers,
surface risks and opportunities, identify decisions, and close with owned next actions.

#### 证据规则

Bind each important metric to source, cutoff, unit, denominator, and comparison basis.
Separate measured results from forecasts and explanations; label simulated or
projected data that could be mistaken for actual performance.

#### 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `reading`
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `formal`
- `information_density`: `high`
- `motion_density`: `low`
- `continuation_state`: inherit the Handoff decision

#### IR 映射边界

On an independently authorized IR route, the Profile may guide existing dataset,
data-visualization, comparison, process, and traceability semantics. It cannot add
metric fields, data connectors, or incremental compilation.

#### Runtime/主题使用

Use current reading or presentation behavior and existing chart/evidence treatments.
The Profile does not implement dashboards, live data refresh, or new visualization
components.

#### QA 验收

Verify metric math, unit and period consistency, target/baseline labels, chart-source
traceability, forecast separation, action ownership, compound requirement coverage,
and existing asset, browser, traceability, and delivery gates.

#### 能力叠加与冲突处理

Research explanation or live presentation may be bounded overlays. If the baseline is
a single project's scope, plan, and milestones, use `project-lifecycle-reporting`; if
the report chiefly seeks approval for a new option, use `proposal-planning-decision`.

### 4. 方案策划与决策提案

#### 身份与版本

- `profile_id`: `proposal-planning-decision`
- Definition version: `1.0`
- Status: foundation definition only; the Golden Path detailed workflow is explicitly
  outside this engineering node

#### 适用目标

Use as primary when a defined decision maker must choose, approve, fund, prioritize,
or authorize a plan based on options, criteria, trade-offs, recommendation, and risk.

#### 排除范围

Do not use as primary when live stage performance itself is the main product, when the
artifact only reports recurring results, or when success is governed by an external
application/scoring rule rather than the decision case.

#### 成品

A decision-ready offline HTML proposal that makes the decision, options, trade-offs,
recommendation, assumptions, implementation boundary, and risks independently clear,
with existing QA and delivery evidence.

#### 所需信息

Reuse the decision owner, decision to make, constraints, criteria, available options,
non-negotiables, evidence, budget/time boundaries, implementation responsibilities,
and required next action. Do not introduce a Profile questionnaire.

#### design-ready 条件

The decision, decision maker, evaluation criteria, plausible alternatives, material
trade-offs, evidence boundary, implementation responsibility, and action path when
external action is required are sufficiently clear for brief confirmation.

#### 叙事任务

Frame the decision, make criteria visible, compare viable options, explain the
recommendation, expose assumptions and risks, and show the implementation and decision
closure without prescribing fixed pages.

#### 证据规则

Tie material benefits, costs, feasibility, and risks to sources or explicit
assumptions. Never disguise a preferred option as the only option or present projected
outcomes as achieved results.

#### 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `reading`
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `balanced`
- `information_density`: `medium`
- `motion_density`: `low`
- `continuation_state`: inherit the Handoff decision

#### IR 映射边界

On an independently authorized IR route, the Profile may guide existing comparison,
process, claim, evidence, and narrative-unit semantics. It does not define a proposal
schema, decision engine, scoring algorithm, or Compiler branch.

#### Runtime/主题使用

Use the confirmed reading/presentation mode and the existing visual route. The Profile
does not add complex composition, cross-page motion, or decision-model widgets.

#### QA 验收

Verify decision clarity, option completeness, criteria consistency, trade-off and risk
visibility, recommendation support, implementation ownership, exact action-path
traceability when applicable, and all existing objective QA and delivery gates.

#### 能力叠加与冲突处理

Research support, operating data, or live delivery may be bounded overlays. If the
primary success condition becomes spoken audience persuasion, switch to
`live-presentation-persuasion`; never run both Golden Paths as full workflows.

### 5. 现场演讲与说服表达

#### 身份与版本

- `profile_id`: `live-presentation-persuasion`
- Definition version: `1.0`
- Status: foundation definition only; the Golden Path detailed workflow is explicitly
  outside this engineering node

#### 适用目标

Use as primary when the presenter and live audience interaction are central, and the
deck must move listeners toward a belief, decision, or action through spoken rhythm,
visible proof, and controlled reveals.

#### 排除范围

Do not use as primary merely because presentation mode is selected. Use another
Profile when the artifact's dominant success condition is independent formal reading,
research validity, recurring management control, or compliance with an authoritative
rule/scoring matrix.

#### 成品

A presentation-ready offline HTML deck within the current Runtime boundary, with a
clear story, staged proof where needed, speaker-support content when requested,
presenter-operability QA, and the standard delivery handoff.

#### 所需信息

Reuse the audience, intended belief/decision/action, presenter context, venue or device
constraints, available evidence, and any hard duration already supplied. Duration is
optional and must not be asked by default.

#### design-ready 条件

The audience movement, central claim, proof boundary, story direction, desired action,
and verified action path when conversion is promised are clear. Missing optional
duration does not block readiness.

#### 叙事任务

Open a live tension, sequence claims and proof for spoken explanation, create clear
transitions and emphasis, preserve a complete final state on every staged page, and
land the confirmed audience action or conclusion.

#### 证据规则

Make decisive proof visible at the moment the claim is made. Spoken emphasis cannot
upgrade weak evidence; projected examples and simulated data remain visibly bounded
and enter the delivery verification list.

#### 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `presentation`
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `balanced`
- `information_density`: `medium`
- `motion_density`: `medium`
- `continuation_state`: inherit the Handoff decision

#### IR 映射边界

On an independently authorized IR route, the Profile may guide an existing
presentation Projection, monotonic State Sequence, and Speaker Notes semantics. It
does not authorize new Runtime states, complex animation, or Compiler behavior.

#### Runtime/主题使用

Use only the current presentation Runtime and documented `fragment-v1` behavior.
Theme and motion choices stay inside existing built-in or validated project-theme
capabilities; no cross-page morphing or new presenter system is implied.

#### QA 验收

Verify clicker-operable forward flow, staged order, complete final state, page/step
navigation separation, return-state preservation, viewport bounds, evidence timing,
current-artifact controls, and all existing delivery checks.

#### 能力叠加与冲突处理

Decision comparison, teaching explanation, or rule-response content may be bounded
overlays. If a formal scoring or eligibility matrix determines success, keep
`rule-response-application-defense` primary and add live-delivery capability only.

### 6. 教学培训与知识传递

#### 身份与版本

- `profile_id`: `teaching-training-knowledge-transfer`
- Definition version: `1.0`
- Status: foundation definition; no separate detailed workflow file in this node

#### 适用目标

Use as primary when learners must acquire, retain, practice, or apply defined knowledge
or a method, rather than merely agree with a proposition.

#### 排除范围

Do not use as primary for a pure persuasive speech, a research conclusion, or a
project/operations status report. Explanatory pages inside another Profile are only a
bounded teaching overlay.

#### 成品

Offline HTML courseware or a training deck with clear learning progression, examples,
practice/review moments where supported, facilitator support when requested, current
QA evidence, and the standard delivery handoff.

#### 所需信息

Reuse learner baseline, learning objectives, concepts or skills, session context,
available time when provided, examples, misconceptions, practice needs, and assessment
or completion boundaries.

#### design-ready 条件

The learner, target capability, prerequisite knowledge, instructional scope,
progression, examples, and any high-risk knowledge sources are clear enough to design
the learning path.

#### 叙事任务

Activate prior knowledge, explain the concept or method, demonstrate it, let the
learner rehearse or inspect application, correct common misunderstandings, and close
with a usable review or next step.

#### 证据规则

Source factual teaching claims at the rigor required by the domain. Distinguish
verified examples from illustrative exercises and never present a fictional classroom
or customer outcome as achieved evidence.

#### 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `presentation`
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `balanced`
- `information_density`: `medium`
- `motion_density`: `medium`
- `continuation_state`: inherit the Handoff decision

#### IR 映射边界

On an independently authorized IR route, the Profile may guide existing narrative,
process, comparison, example, final-state, and notes semantics. It does not add quiz,
assessment, LMS, or learner-state schema.

#### Runtime/主题使用

Use current reading or presentation behavior based on the confirmed delivery context.
Any staged explanation must use existing Runtime steps; the Profile creates no
interactive exercise engine or new teaching theme.

#### QA 验收

Verify objective-to-content traceability, prerequisite order, concept consistency,
example labeling, exercise instructions, final-state completeness, presenter/reader
usability, and existing technical and delivery gates.

#### 能力叠加与冲突处理

Research evidence, brand polish, or live persuasion may be bounded overlays. If the
dominant outcome is audience agreement or purchase rather than learning transfer, use
`live-presentation-persuasion` or `brand-communication-editorial-publishing`.

### 7. 项目全过程汇报

#### 身份与版本

- `profile_id`: `project-lifecycle-reporting`
- Definition version: `1.0`
- Status: foundation definition; no separate detailed workflow file in this node

#### 适用目标

Use as primary when stakeholders must understand and govern a project's objective,
scope, plan, current phase, progress, changes, risks, decisions, outcomes, or closure.

#### 排除范围

Do not use as primary for organization-wide recurring operations, an unstarted option
proposal, or an application governed by external scoring rules. A project example
inside another report does not select this Profile.

#### 成品

An offline lifecycle report appropriate to the current project phase, with baseline,
status, decisions, risk/change history, next steps or closure evidence, current QA,
and the standard delivery handoff.

#### 所需信息

Reuse the project objective, sponsor and audience, scope baseline, phase, milestones,
deliverables, progress evidence, changes, issues, risks, decisions, owners, dependencies,
and success/closure criteria.

#### design-ready 条件

The project identity, phase, baseline, reporting cutoff, material deviations, decision
needs, source availability, and responsibility boundary are clear. Achieved outcomes
must be supported by current project evidence.

#### 叙事任务

Re-establish objective and baseline, locate the current phase, show completed and
remaining work, explain changes and variance, surface risks and decisions, and close
with owned next steps or verified closure.

#### 证据规则

Bind status and outcomes to dated artifacts, records, or explicit confirmations.
Distinguish planned, in-progress, blocked, delivered, and accepted; never collapse an
existing artifact or handoff claim into verified acceptance.

#### 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `reading`
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `formal`
- `information_density`: `high`
- `motion_density`: `low`
- `continuation_state`: inherit the Handoff decision

#### IR 映射边界

On an independently authorized IR route, the Profile may guide existing timeline,
process, evidence, comparison, status narrative, and appendix semantics. It does not
create project databases, live status integrations, or a new Handoff schema.

#### Runtime/主题使用

Use existing Runtime modes and visual routes. The Profile does not implement project
management controls, live timelines, or persistent workspace state.

#### QA 验收

Verify baseline/current-state distinction, milestone and date consistency, change and
risk coverage, owner/decision clarity, outcome acceptance evidence, handoff readiness
language, traceability, and existing technical/delivery gates.

#### 能力叠加与冲突处理

Periodic metrics or decision-proposal modules may be bounded overlays. If the artifact
governs a recurring business cadence rather than one project baseline, use
`periodic-operations-reporting`.

### 8. 品牌传播与编辑出版

#### 身份与版本

- `profile_id`: `brand-communication-editorial-publishing`
- Definition version: `1.0`
- Status: foundation definition; no separate detailed workflow file in this node

#### 适用目标

Use as primary when the artifact must communicate a brand, idea, launch, campaign, or
editorial story to an external or broad audience with credibility, memorability, and
controlled calls to action.

#### 排除范围

Do not use as primary for formal institutional submission, research validity,
recurring internal control, or a live speech whose presenter rhythm is the dominant
product. Visual polish alone does not select this Profile.

#### 成品

A polished offline editorial HTML artifact or presentation-ready brand deck within
the current packaging boundary, with source/asset provenance, verified action paths
when applicable, current QA, and the standard delivery handoff.

#### 所需信息

Reuse the audience, communication objective, central message, brand identity and
constraints, publication context, approved claims, source/assets and rights, tone,
desired action, and real action path when conversion is promised.

#### design-ready 条件

The audience, message, brand/identity boundary, story angle, claims, usable assets,
rights or source limits, visual route, and any conversion path are clear enough for
brief confirmation.

#### 叙事任务

Earn attention, establish relevance, express the central idea, make proof and identity
credible, create a memorable structure, and close with the confirmed meaning or
verified action without overclaiming.

#### 证据规则

Protect real identity, quotations, public claims, assets, and action channels. Record
external evidence provenance and distinguish editorial illustration, projection, and
customer-verified fact.

#### 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `reading`
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `balanced`
- `information_density`: `medium`
- `motion_density`: `medium`
- `continuation_state`: inherit the Handoff decision

#### IR 映射边界

On an independently authorized IR route, the Profile may guide existing editorial
narrative, image, claim, evidence, action-path, and Projection semantics. It does not
add publishing, campaign, analytics, or distribution schema.

#### Runtime/主题使用

Use existing reading/presentation Runtime and validated visual routes. The Profile
does not create a public website, host content, add tracking, or invent a brand theme
outside confirmed visual bindings.

#### QA 验收

Verify identity and claim accuracy, asset provenance and portability, brand consistency,
reader flow, action-path exactness and usability, risk labels, traceability, browser
behavior, and the existing delivery gate.

#### 能力叠加与冲突处理

Teaching, research, or live delivery may be bounded overlays. If spoken stage rhythm
becomes the main success condition, use `live-presentation-persuasion`; if formal
submission rules dominate, use `formal-submission-writing` or
`rule-response-application-defense`.

### 9. 规则响应、申报与答辩

#### 身份与版本

- `profile_id`: `rule-response-application-defense`
- Definition version: `1.0`
- Status: foundation definition; no separate detailed workflow file in this node

#### 适用目标

Use as primary when success depends on satisfying authoritative eligibility,
submission, compliance, tender, grant, award, evaluation, scoring, or defense rules
with complete and traceable responses.

#### 排除范围

Do not use as primary for ordinary formal writing without an authoritative rule set,
for an open-ended research report, or for a general live pitch whose success is not
governed by declared criteria.

#### 成品

An offline rule-responsive submission or defense deck with requirement coverage,
evidence mapping, gap/risk visibility, defensible answers, current QA evidence, and
the standard delivery verification handoff.

#### 所需信息

Reuse the authoritative rule and version, issuing body, eligibility, mandatory
sections, scoring criteria, deadlines, format/length constraints, evidence requirements,
known gaps, defense context, and responsibility boundary.

#### design-ready 条件

The applicable rule set and version are bound and inspected; mandatory requirements,
scoring logic, evidence availability, unresolved conflicts, format constraints, and
responsibilities are mapped. Missing mandatory proof remains a hard gap.

#### 叙事任务

Mirror the governing requirement structure, answer each material criterion, attach
the right evidence, expose gaps and mitigations, make differentiators easy to score,
and prepare clear responses to likely rule-bound questions.

#### 证据规则

Every eligibility, qualification, score-bearing claim, credential, commitment, and
achieved result must trace to authoritative or explicitly confirmed evidence. Never
invent compliance, certification, citations, clients, or performance.

#### 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `reading`
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `formal`
- `information_density`: `high`
- `motion_density`: `low`
- `continuation_state`: inherit the Handoff decision

#### IR 映射边界

On an independently authorized IR route, the Profile may guide existing requirement,
claim, evidence, source, comparison, appendix, and presentation semantics. It does not
add a compliance schema, scoring engine, or rule parser.

#### Runtime/主题使用

Use existing reading behavior for submissions and presentation behavior for an
explicit defense. The rule response remains one primary Profile in both modes; live
delivery is a bounded capability overlay, not a second full workflow.

#### QA 验收

Verify authoritative rule/version binding, one-by-one mandatory requirement coverage,
score-bearing claim support, evidence locator accuracy, format/length constraints,
gap disclosure, defense readability, exact-artifact QA, and delivery readiness.

#### 能力叠加与冲突处理

Formal writing, research support, and live delivery may be bounded overlays. Keep this
Profile primary whenever external rules or scoring determine success; otherwise route
to the business outcome that actually governs acceptance.
