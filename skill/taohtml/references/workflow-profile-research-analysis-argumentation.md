# 研究分析与专业论证

## 身份与版本

- `profile_id`: `research-analysis-argumentation`
- Definition version: `1.0`
- Status: non-empty foundation definition loaded on demand

## 适用目标

Use as primary when the report must answer a substantive question, evaluate a
hypothesis, explain a mechanism, or defend a professional conclusion through visible
method and evidence.

## 排除范围

Do not use as primary for a fixed institutional submission, routine KPI cycle, or
public brand story when original analysis is not the dominant outcome. A citation-rich
document is not automatically a research Profile.

## 成品

An evidence-led offline HTML analysis with a clear question, method, claim-evidence
chain, bounded conclusion, limitations, QA record, and delivery verification handoff.

## 所需信息

Reuse the research question, audience, decision context, scope, source corpus,
definitions, methods, competing explanations, and required conclusion strength.
Request only gaps that can reverse the conclusion or invalidate the method.

## design-ready 条件

The central question, scope, method, evidence boundary, material conflicts, and
acceptable conclusion strength are clear. Unsupported high-impact claims are removed,
bounded, or held pending authoritative evidence.

## 叙事任务

Frame the question, explain the method and evidence base, test claims and alternatives,
show the reasoning, state the conclusion, and expose limitations and unresolved items.

## 证据规则

Maintain explicit Claim-Evidence-Source relationships for material conclusions.
Distinguish observation, inference, projection, and unresolved conflict; never convert
a plausible explanation into a verified finding.

## 横向参数默认值

- `input_entry_route`: inherit the established material route
- `use_mode`: `reading` recommendation only after explicit delegation; otherwise inherit or resolve the existing startup choice
- `visual_binding`: inherit the validated visual route
- `evidence_rigor`: `formal`
- `information_density`: `high`
- `motion_density`: `minimal`
- `continuation_state`: inherit the Handoff decision

## IR 映射边界

On an independently authorized IR route, the Profile may guide research prototype,
formal evidence rigor, semantic claims, evidence, sources, datasets, and appendices
already supported by the current contract. It does not modify or bypass the Validator.

## Runtime/主题使用

Use existing reading or presentation behavior according to the confirmed use mode.
Themes organize evidence but must not change claim strength or imply unsupported
authority.

## QA 验收

Verify question-to-conclusion traceability, method clarity, source coverage, claim
support, counterevidence, data definitions, limitations, source visibility, and all
existing technical and delivery checks.

## 能力叠加与冲突处理

Live explanation or editorial polish may be overlays. If the artifact primarily asks
decision makers to choose among actions, use `proposal-planning-decision`; if it must
meet an external rule matrix, use `rule-response-application-defense`.
