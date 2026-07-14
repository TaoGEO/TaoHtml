# Intake Workflow

Use this workflow after identifying the available input and before editing or creating HTML. Apply it to every route, with the source gate appropriate to that route.

## State Machine

Move through these states in order:

| State | Result | Exit condition |
|---|---|---|
| S0 Startup | Idea, Word/PDF, or PPT/HTML plus reading/presentation and concise/standard/detailed are selected | Choices are known or safely inferred |
| S1 Source grounding | The available idea or source is represented accurately | The route-specific source gate passes |
| S2 Design completion | Only outcome-changing gaps are resolved | The project passes the design-ready gate, or intake stops as blocked |
| S3 Design brief | One customer-readable brief is shown | The user explicitly confirms the current brief |
| S4 Production | HTML, visual system, motion, and objective QA are completed | Objective failures are fixed |
| S5 Delivery | Files, checks, and production assumptions are reported | Deliverables are usable |

Apply the source gate as follows:

- **Idea only**: seed the ledger from the conversation. Do not create or ask the user to confirm a fictional Material Understanding Summary.
- **Word/PDF**: show the Material Understanding Summary defined in `material-understanding.md` and wait for confirmation or correction.
- **PPT/HTML**: inspect the available artifact and preserve its confirmed core viewpoints; resolve faithful migration versus reorganization only if both remain reasonable.

Never write a Report Design Brief while a high-risk gap remains. Never write HTML before the current brief is explicitly confirmed.

## Decision Ledger

Maintain these buckets internally; do not expose them as a questionnaire:

```text
known | confirmed | inferred | missing
```

- **known**: stated in the current conversation or directly supported by the source.
- **confirmed**: explicitly accepted or corrected by the user.
- **inferred**: a low-risk decision TaoHtml can make from context or user delegation; record its basis and expose it in the brief.
- **missing**: not yet known and not safe to infer.

Rebuild the ledger after reading each source and update it after every answer. Move information instead of copying it across buckets. Do not ask about `known`, `confirmed`, or safely `inferred` items.

## Compact Startup

Preserve the three product choices:

- **Route**: idea only, Word/PDF, or existing PPT/HTML.
- **Use mode**: reading, where each page stands alone and content is visible by default; or presentation, where tighter copy follows a spoken staged sequence.
- **Length**: concise, standard, or detailed.

Skip every choice already made. When two or three remain missing, ask for them in one compact startup interaction instead of spreading setup across several rounds. This bundled startup prompt counts as one clarification question. Estimate pages from the actual content; never assign a fixed page range by length label alone.

## Idea-Only Judgment Layer

For an idea-only route, evaluate these layers in order and skip any layer already resolved or safely inferable:

1. **Audience and desired outcome**: who should understand, believe, decide, or do what after the report.
2. **Core viewpoint or core question**: the claim the report should establish, or the question it must answer.
3. **Evidence or conclusion-level conflict**: proof required for important claims and any ambiguity that could reverse the main conclusion.
4. **Structure choice**: ask only when multiple chapter structures are genuinely reasonable and would produce meaningfully different reports.

Treat this as a judgment layer, not a four-question form. Visual style, motion density, minor chapter naming, and ordinary delivery defaults are normally low-risk inferences unless the user has made them consequential.

## Select The Next Question

Before asking, re-read the conversation, available source, ledger, prior attempts, and counters. Then:

1. Remove gaps whose answers are already present or can be safely inferred.
2. Rank the remaining gaps by how much they could change narrative, scope, conclusion, evidence, structure, or delivery.
3. Ask only the largest current gap.

Ask one decision question per round. Combine closely related details only when they jointly decide one outcome; do not pack independent questionnaire fields together. Offer 2-3 options only when they are real alternatives and state their design impact briefly.

Treat "decide for me", "not important", or equivalent wording as delegation: choose a reasonable low-risk default, move it to `inferred`, and do not ask again.

## Question Budget And Stop Rules

Count agent-initiated clarification prompts within the current intake cycle. Count the bundled startup prompt as one. The prompt that asks the user to confirm the displayed Report Design Brief is a separate authorization gate and does not count toward this budget.

- Allow **0 clarification questions** when the input already passes the source and design-ready gates.
- Treat **3-5 clarification questions** as the ordinary target, not a quota.
- Enforce **6 clarification questions** as a hard maximum. Do not ask a seventh.
- Ask about the same key gap at most **twice**. On the second attempt, replace the abstract wording with a concrete example or 2-3 real options. After that, infer or block according to risk.
- Track whether each response produces actionable new information: it resolves or narrows a missing decision, corrects the ledger, supplies evidence, or clearly delegates a decision.
- Stop questioning immediately after **three consecutive rounds without actionable new information**. Then infer all remaining low-risk gaps and either issue the brief or use the blocked-intake output.

At the hard maximum, apply the same resolution: infer low-risk gaps and stop; never use the budget pressure as permission to invent a high-risk decision.

If the user initiates a change to the core goal or scope, invalidate any affected brief and start a new intake cycle with fresh counters. Preserve reusable facts in the ledger, but do not count the first question of the new cycle as question seven of the old one. Local wording, color, layout, or motion revisions do not start a new cycle unless they change the report's meaning or scope.

## Risk Rules

Infer a gap only when a reasonable choice is reversible during brief confirmation and cannot materially change the report's promise, scope, central meaning, factual integrity, or main conclusion. Record the inference and its basis in `待确认项`.

Treat a gap as high risk when guessing could:

- choose the wrong audience outcome or core viewpoint;
- change the report's promised scope or responsibility boundary;
- reverse or materially distort the main conclusion;
- create an unsupported factual, quantitative, legal, safety, or outcome claim; or
- silently choose between structures that embody different goals or conclusions.

When any high-risk gap remains after its second attempt, the six-question maximum, or the three-no-gain stop, do not generate a Report Design Brief and do not begin production. Output only:

```markdown
# 问诊暂停

## 当前已知
- ...

## 未决缺口
- ...

## 为什么不能推断
- ...

## 最小补充材料
- ...

## 恢复条件
- ...
```

Ask for the smallest specific item that would unlock the decision. Resume the same intake cycle when that item arrives, unless the user changes the core goal or scope.

## Design-Ready Gate

Treat a project as design-ready when:

- The audience outcome is clear enough to choose a narrative.
- The core viewpoint or core question and scope are clear.
- Evidence required by the report type is present, explicitly bounded, or safely deferred without inventing a conclusion.
- No unresolved conflict can reverse the main conclusion.
- One chapter structure is selected or only one reasonable structure follows from the ledger.
- Visual direction is known or safely delegated to TaoHtml.
- Route, use mode, length, and material delivery constraints are known or safely inferred.
- No high-risk item remains in `missing`.

Stop asking as soon as these conditions are met. A clear idea can therefore proceed directly to a brief with zero clarification questions.

## Confirmation Rules

### Material summary gate

For Word/PDF only, ask the user to confirm or correct the displayed Material Understanding Summary. If they correct it, issue an updated summary before continuing. Do not impose this gate on an idea-only input.

### Design brief gate

Show one current Report Design Brief and end with:

> 回复“确认”后，TaoHtml 将按这份设计简报开始制作 HTML。

Only a reply that clearly confirms this displayed brief opens production. Earlier approval to discuss, use TaoHtml, or begin intake does not count. Brief confirmation is authorization, not clarification, so it remains required even when the clarification counter is already six.

If the user adds source material or changes a core viewpoint after confirmation, invalidate the brief, update it, and ask for confirmation again. During production, resolve non-core omissions with a reasonable default and list the decision at delivery rather than repeatedly interrupting the user.
