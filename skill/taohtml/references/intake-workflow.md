# Intake Workflow

Use this workflow after identifying the available input and before editing or creating HTML. Apply it to every route, with the source gate appropriate to that route.

## State Machine

Move through these states in order:

| State | Result | Exit condition |
|---|---|---|
| S0 Startup | Idea, Word/PDF, or PPT/HTML plus reading/presentation and concise/standard/detailed are selected | Choices are known, evident from the input, or explicitly delegated |
| S1 Source grounding | The available idea or source is represented accurately | The route-specific source gate passes |
| S2 Design completion | Only outcome-changing decisions and hard-boundary gaps are resolved | The project passes the design-ready gate, or intake stops on a minimum hard boundary |
| S3 Design brief | One customer-readable brief is shown | The user explicitly confirms the current brief |
| S4 Production | HTML, visual system, motion, and objective QA are completed | Objective failures are fixed |
| S5 Delivery | Files, checks, and a structured verification handoff are reported | Deliverables are usable and creative supplements are easy for the customer to review |

Apply the source gate as follows:

- **Idea only**: seed the ledger from the conversation. Do not create or ask the user to confirm a fictional Material Understanding Summary.
- **Word/PDF**: show the Material Understanding Summary defined in `material-understanding.md` and wait for confirmation or correction.
- **PPT/HTML**: inspect the available artifact and preserve its confirmed core viewpoints; resolve faithful migration versus reorganization only if both remain reasonable.

Never write a Report Design Brief while a minimum hard-boundary gap remains. Never write HTML before the current brief is explicitly confirmed. Ordinary absent facts are not a reason to stop: plan reasonable creative supplements, finish the report, and disclose the generated details at delivery.

## Decision Ledger

Maintain these buckets internally; do not expose them as a questionnaire:

```text
known | confirmed | inferred | missing
```

- **known**: stated in the current conversation or directly supported by the source.
- **confirmed**: explicitly accepted or corrected by the user.
- **inferred**: a reversible design decision TaoHtml can make from context or user delegation; record its basis and expose it in the brief.
- **missing**: an outcome-changing decision or hard-boundary fact that is not yet known and cannot be safely delegated.

Rebuild the ledger after reading each source and update it after every answer. Move information instead of copying it across buckets. Treat a stated route, use mode, audience, desired outcome, content length, real action path, or hard presentation duration as `known`; do not ask for or confirm the same information again. Do not ask about any other `known`, `confirmed`, or safely `inferred` item.

The design ledger is not the delivery verification list. During production, maintain a separate creative-supplement ledger with `page/content | supplement type | source status | suggested action`. A missing ordinary scene, number, viewpoint, or expression may enter this ledger directly instead of becoming another intake question. Customer-provided and independently verified facts stay in `known` or `confirmed`; never relabel them as creative supplements.

## Desired Action And Real Action Path

Keep two decisions separate:

- **Desired action**: what the audience should decide or do after the report.
- **Real action path**: the exact channel through which the audience can complete that action, such as a verified URL, host-agent invocation, installation command, booking route, download location, or contact detail.

Treat trial, purchase, booking, download, installation, contact, registration, subscription, and similar external-action goals as **conversion objectives**. A conversion objective is not design-ready until the desired action and a real action path are both resolved. Do not ask for an action path when the report is explanatory, educational, or internal and its confirmed goal does not require an external action.

Accept an action path only when it is:

1. explicitly provided by the user;
2. present in the source material or project context and verified against that context; or
3. selected under explicit user delegation and independently verified by the Agent before the brief.

Do not ask for an action path already supported by the source or project context; record the value, source, and verification result in the ledger instead. Where independent verification is required, establish that the intended audience can use the complete channel and that it leads to the intended action. For URLs, open the target and confirm its purpose. For host-agent syntax or commands, check authoritative host or project documentation without triggering the external action. For user-provided contact details or prices, preserve the exact value and mark it as user-provided rather than implying independent verification. A QR code is a presentation of a verified value, not a source: decode it and compare the result with that value before delivery.

Never invent a URL, QR code, contact detail, price, command, or product entry. If the user delegates channel selection but the Agent cannot verify a candidate, keep the action path in `missing`.

When a conversion objective lacks a real action path, ask one minimal decision question at the point where it is the largest outcome-changing gap: request the exact channel, request authorization to locate and verify one, or offer to explicitly downgrade the goal so the report no longer promises direct action. This prompt counts toward the same six-question limit; it is not a fixed questionnaire item. A downgrade is valid only when the user clearly accepts the changed goal.

## Startup Decisions

Preserve the three product choices:

- **Route**: idea only, Word/PDF, or existing PPT/HTML.
- **Use mode**: reading, where each page stands alone and content is visible by default; or presentation, where tighter copy follows a spoken staged sequence.
- **Length**: concise, standard, or detailed.

Resolve at most one missing startup choice per round and skip every choice already made. If presentation mode is already known, do not ask the user to select the use mode again. Do not bundle route, use mode, and length into one prompt. For an idea-only input, the route is already known. When route and use mode are known but content length is missing, ask one question that offers **concise / standard / detailed**; do not infer a default length without explicit delegation, and do not replace these choices with duration or page-count options.

Estimate the page count dynamically from the actual material after the content length is selected, and record that estimate in the design brief. Never assign or present a fixed page range by length label alone.

Presentation duration is an optional delivery constraint, not a startup choice or a design-ready prerequisite. In presentation mode, do not ask for a duration by default and do not block progress when no duration was given. If the user provides a hard duration, record it as `known`, use it to constrain scope, pacing, and content density, and do not ask the user to repeat or confirm that duration. A hard duration does not replace the content-length choice.

## Idea-Only Judgment Layer

For an idea-only route, evaluate these layers in order and skip any layer already resolved or safely inferable:

1. **Audience and desired outcome**: who should understand, believe, decide, or do what after the report.
2. **Core viewpoint or core question**: the claim the report should establish, or the question it must answer.
3. **Evidence or conclusion-level conflict**: proof required for important claims and any ambiguity that could reverse the main conclusion.
4. **Structure choice**: ask only when multiple chapter structures are genuinely reasonable and would produce meaningfully different reports.

Treat this as a judgment layer, not a four-question form. Visual style, motion density, minor chapter naming, and ordinary delivery defaults are normally low-risk inferences unless the user has made them consequential.

## Visual Source Selection

Resolve the visual source only after content and chapter structure are clear enough to judge fit.

- If the user supplies a clear visual reference, use that reference as the authority. Do not require an internal-theme choice. Record whether to reproduce it closely or use it as design DNA.
- If no clear reference exists, read `visual-systems.md` and recommend 2-3 genuinely suitable built-in systems. Show each system's exact customer-facing name, one-line description, and bundled preview. Ask the user to choose once, or invite explicit delegation to TaoHtml.
- Do not ask open-ended aesthetic questions such as “What style do you like?”. Do not repeat a theme-selection question after the user chooses or delegates.
- Theme selection uses the same clarification counter and never expands the six-question hard maximum. If the project reaches the maximum or the three-no-gain stop before a theme is selected, choose the lowest-risk fit, move it to `inferred`, and disclose the basis in the Report Design Brief.
- A selected theme fixes a reusable visual grammar, not a palette. Preserve its composition, hierarchy, image treatment, module language, chart/evidence treatment, and motion grammar unless the brief records a necessary deviation.

## Select The Next Question

Before asking, re-read the conversation, available source, ledger, prior attempts, and counters. Then:

1. Remove gaps whose answers are already present or can be safely inferred.
2. Resolve any missing startup choice according to `Startup Decisions`; after startup, rank the remaining gaps by how much they could change narrative, scope, conclusion, evidence, structure, or delivery.
3. Ask only the largest current gap whose answer would change the report design.

Ask exactly one decision question per round. Do not pack independent questionnaire fields together. Offer 2-3 options only when they are real alternatives and state their design impact briefly.

Treat "decide for me", "not important", or equivalent wording as delegation: choose a reasonable low-risk default, move it to `inferred`, and do not ask again.

For a missing conversion action path, delegation authorizes TaoHtml to locate and verify a channel; it does not authorize invention or an unverified default.

## Question Budget And Stop Rules

Count agent-initiated clarification prompts within the current intake cycle. Count each single-decision startup prompt as one. The prompt that asks the user to confirm the displayed Report Design Brief is a separate authorization gate and does not count toward this budget.

- Allow **0 clarification questions** when the input already passes the source and design-ready gates.
- Treat **3-5 clarification questions** as the ordinary target, not a quota.
- Enforce **6 clarification questions** as a hard maximum, including for the most complex idea-only intake. Do not ask a seventh.
- Ask about the same key gap at most **twice**. On the second attempt, replace the abstract wording with a concrete example or 2-3 real options. After that, infer or block according to risk.
- Track whether each response produces actionable new information: it resolves or narrows a missing decision, corrects the ledger, supplies evidence, or clearly delegates a decision.
- Stop questioning immediately after **three consecutive rounds without actionable new information**. Then infer all remaining low-risk gaps and either issue the brief or use the blocked-intake output.

Stop immediately when the design-ready gate passes; never continue asking to approach a target or maximum. At the hard maximum, apply the same resolution: infer reversible design decisions, route ordinary missing content to the creative-supplement ledger, and stop. Never use budget pressure as permission to cross a minimum hard boundary.

If the user initiates a change to the core goal or scope, invalidate any affected brief and start a new intake cycle with fresh counters. Preserve reusable facts in the ledger, but do not count the first question of the new cycle as question seven of the old one. Local wording, color, layout, or motion revisions do not start a new cycle unless they change the report's meaning or scope.

## Output-First And Hard-Boundary Rules

Infer an outcome-changing design decision only when a reasonable choice is reversible during brief confirmation and cannot materially change the report's promise, scope, central meaning, factual integrity, or main conclusion. Record the inference and its basis in `待确认项`.

Ordinary information gaps do not automatically create a block. TaoHtml may add plausible scenes, numbers, viewpoints, comparisons, examples, and expression as creative supplements when they help complete a useful report. These are pending-verification generated content, not source facts and not automatic errors. Track the exact additions for the delivery list. Put an adjacent `示意 / 模拟 / 待核实` label in the HTML only when a simulated chart, fictional customer case, generated evidence-like artifact, or numeric display could reasonably be mistaken for real proof; keep ordinary projections in the delivery note so risk disclosure does not damage the presentation.

The minimum hard boundaries are:

- never invent a real customer or company identity, quotation, citation, literature, or source;
- never state that an illustrative or fictional case is an achieved customer result;
- explicitly verify legal, medical, financial, safety, and similar high-risk facts before presenting them as guidance or fact;
- never replace, reinterpret as generated, or silently alter a confirmed real source, data point, quotation, or action channel;
- never claim that an audience can complete a conversion action without a verified real action path; and
- never silently choose between goals, conclusions, or structures that materially change the promised outcome or responsibility boundary.

When a conversion objective's real action path remains missing at a stop condition, do not generate a Report Design Brief or begin production. Use the blocked-intake output below, unless the user has explicitly downgraded the goal to one that does not require direct action. Never replace the missing channel with a slogan, a generic process such as “choose material → hand it over → see the result,” or an implied future entry point.

When a minimum hard-boundary gap remains after its second attempt, the six-question maximum, or the three-no-gain stop, do not generate a Report Design Brief and do not begin production. Ordinary missing support belongs in the creative-supplement ledger and must not trigger this block. Output only:

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
- Evidence required by the report type is present, explicitly bounded, or separated from planned creative supplements without presenting those supplements as verified proof.
- No unresolved conflict can reverse the main conclusion.
- One chapter structure is selected or only one reasonable structure follows from the ledger.
- Visual direction is known or safely delegated to TaoHtml.
- The visual source is recorded as a user reference or one selected built-in visual system; any necessary deviation is explicit.
- Route and use mode are known or evident from the input, length is known or explicitly delegated, and required material delivery constraints are known or safely inferred; optional presentation duration may remain unspecified.
- For a conversion objective, the exact real action path, its source, and its verification status are recorded; non-conversion reports do not need this field.
- No minimum hard-boundary item remains in `missing`; ordinary creative supplements may remain pending customer verification.

Stop asking as soon as these conditions are met. A clear idea can therefore proceed directly to a brief with zero clarification questions.

## Confirmation Rules

### Material summary gate

For Word/PDF only, ask the user to confirm or correct the displayed Material Understanding Summary. If they correct it, issue an updated summary before continuing. Do not impose this gate on an idea-only input.

### Design brief gate

Show one current Report Design Brief and end with:

> 回复“确认”后，TaoHtml 将按这份设计简报开始制作 HTML。

Only a reply that clearly confirms this displayed brief opens production. Earlier approval to discuss, use TaoHtml, or begin intake does not count. Brief confirmation is authorization, not clarification, so it remains required even when the clarification counter is already six.

If the user adds source material or changes a core viewpoint after confirmation, invalidate the brief, update it, and ask for confirmation again. During production, resolve non-core omissions with a reasonable default or creative supplement, add the exact item to the delivery verification ledger, and continue instead of repeatedly interrupting the user.
