# Intake Workflow

Use this workflow after identifying the available input and before editing or creating HTML. Apply it to every route, with the source gate appropriate to that route.

## State Machine

Move through these states in order:

| State | Result | Exit condition |
|---|---|---|
| S0 Route handshake | Idea, Word/PDF, or PPT/HTML is bound to this invocation | A specific topic, an eligible bound source, or the user's answer to the latest active route options establishes the route |
| S0A Startup completion | Reading/presentation and concise/standard/detailed are selected | Choices are known, evident from the input, or explicitly delegated |
| S1 Source grounding | The available idea or source is represented accurately | The route-specific source gate passes |
| S2 Design completion | Only outcome-changing decisions and hard-boundary gaps are resolved, and the visual route is selected | The project passes the design-ready gate, or intake stops on a minimum hard boundary |
| S3 Reference VI | On the supported static-reference route, one unified VI design standards board is shown; other visual routes bypass this state | The user clearly confirms the exact current board and its conversation reference is recorded, or the state is not applicable |
| S4 Design brief | One customer-readable brief is shown | The user explicitly confirms the current brief |
| S5 Production | HTML, visual system, presentation behavior, and objective QA are completed | Objective failures are fixed |
| S6 Delivery | Files, checks, and a structured verification handoff are reported | Deliverables are usable and creative supplements are easy for the customer to review |

Apply the source gate as follows:

- **Idea only**: seed the ledger from the conversation. Do not create or ask the user to confirm a fictional Material Understanding Summary.
- **Word/PDF**: show the Material Understanding Summary defined in `material-understanding.md` and wait for confirmation or correction.
- **PPT/HTML**: show the same source-grounded Material Understanding Summary, preserve its confirmed core viewpoints, and resolve faithful migration versus reorganization only if both remain reasonable.

Never write a Report Design Brief while a minimum hard-boundary gap remains. Never write HTML before the current brief is explicitly confirmed. Ordinary absent facts are not a reason to stop: plan reasonable creative supplements, finish the report, and disclose the generated details at delivery.
On the static-reference route, never write the brief before the current VI board is confirmed.

Maintain the exact current-task state and allowed actions in
`production-authorization.md`. A Material Understanding Summary, VI standards board,
and Report Design Brief are confirmation artifacts. Formal report HTML, browser QA,
and delivery remain forbidden until the machine gate authorizes them for the current
task. Do not treat a formal or nearly finished HTML deck as a confirmation preview.

## New Invocation Handshake

Every new explicit TaoHtml invocation starts at S0 even when the platform requires
the user to attach some text to send the Skill. Establish only the current task entry
in this first phase.

Treat the current message as route-bearing only when it contains at least one of:

- a specific topic, question, claim, or outcome that the user clearly wants TaoHtml
  to turn into a report; or
- an upload, path, filename, or material description explicitly identified as input
  for this task and eligible under `Source Binding` below.

When either is present, infer the matching route and continue to the next genuinely
missing startup decision without asking for the route again. When neither is present,
show exactly one route choice with **Idea only / Word or PDF / Existing PPT or HTML**,
record that option set as `latest_options`, and stop. Do not inspect the workspace,
read `input/prompt.md`, summarize materials, draft a brief, or create HTML while S0 is
unresolved.

Judge semantic binding from the message's task meaning, not from a blacklist or an
enumeration of tokens. Text that merely enables sending, acknowledges the Skill, or
signals attention without identifying a report topic or material supplies no route.
This rule must generalize across languages, punctuation, emoji, and platform UI.

### Conversation-Scoped Option Binding

Maintain at most one active option record:

```text
latest_options = decision id | Agent turn | exact choices | active/inactive
```

A short label, ordinal, or compact answer binds only when it is a plausible direct
answer to the Agent's most recent active option record in this same conversation.
Consume the record after one answer and invalidate it whenever a newer option set or
changed task supersedes it. Never map a compact answer to section numbering in this
Skill, an earlier conversation, a platform menu, or a route number remembered from
documentation. Thus a compact answer after the Agent has just shown the three entry
routes can select that route; the same compact text attached to a fresh invocation
cannot.

## Source Binding

Maintain a source ledger separate from the design and creative-supplement ledgers.
A local or uploaded material is eligible only through one of these bindings:

1. `current_upload_or_user_explicit`: the user uploads it now or explicitly names it
   as material for this task;
2. `task_instruction_explicit`: the current task instruction explicitly declares the
   file or prepared input as this run's source; or
3. `candidate_confirmed`: after the route exists, the Agent discovers a candidate,
   states its exact path, and receives user confirmation to use it.

Mere workspace presence, a conventional filename such as `input/prompt.md`, a
directory convention, or residue from a previous task is never a binding. Do not
silently promote such a file to `known`, even when its content looks relevant. Before
route establishment, do not scan for candidates at all. After route establishment,
candidate discovery is allowed only to present the path for confirmation; do not read
or process its content before that confirmation.

For every material actually used, record:

```text
source identity/path | source_binding | binding reason | bound conversation/task turn
```

Carry these fields into the Material Understanding Summary and the Report Design
Brief's source records. A customer-bound or independently verified source remains a
real source and must never be relabeled as a creative supplement.

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

Resolve at most one missing startup choice per round and skip every choice already made. Complete the route handshake before asking use mode or length. If presentation mode is already known, do not ask the user to select the use mode again. Do not bundle route, use mode, and length into one prompt. For a message with a specific idea-only topic, the route is already known. When route and use mode are known but content length is missing, ask one question that offers **concise / standard / detailed**; do not infer a default length without explicit delegation, and do not replace these choices with duration or page-count options.

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

- Read `profile-memory.md` and parse enterprise identity from the eligible current material and conversation before asking for a new visual source. Pass only explicit identity candidates to `profile_store.py resolve`; do not add a fixed identity/reuse questionnaire and do not treat the previous task's choice as a permanent preference. One unique active profile binds automatically without reopening reference images, regenerating VI, or asking whether to reuse. Show its concise customer notice, then continue to the Report Design Brief unless the customer objects. Several candidates, unclear identity, alias conflict, or a current requirement/profile conflict permits exactly one selection question; never guess or combine profiles. A different company/customer always uses a separate profile.
- Interpret “这次不用 / 这次换一个” as a task-local `temporary_override` binding that leaves the active version unchanged. Interpret “以后改用 / 更新公司模板” as a new corporate-fidelity VI confirmation plus immutable profile version and atomic active-pointer switch. Do not perform or imply destructive deletion; use archive when the customer wants the profile out of automatic resolution.
- Reading versus presentation is the current task Runtime mode, not a profile conflict. Run the minimal `profile-reuse` preflight, bind the active corporate version with the current mode, and pass that mode to the renderer. Do not ask the customer to rebuild VI, create v2, or abandon the profile for a mode-only change.
- If the user chooses “use my reference”, resolve `reference_mode` once. `reconstruct` accepts exactly one static PNG/JPEG/WebP; `corporate_fidelity` accepts one to three representative static PNG/JPEG/WebP screenshots from the same template family. When the user already asks for “企业模板保真”, “公司模板原样采用”, or equivalent screenshot-visible fidelity, record `corporate_fidelity` without asking again. When intent is still unclear, ask one binary question: **参考风格重构**—提取设计语言，允许重新构图和创新；or **企业模板保真**—锁定截图中可见的企业固定元素，只设计各页面壳的安全内容区. Record `reconstruct` or `corporate_fidelity`, count this as one ordinary clarification question, and never repeat it after the answer is known.
- For either mode, read `static-reference-vi.md`. Use the current session for only the minimal readability check defined there. When readable, analyze static visual facts, render one VI board through the shared contract, and wait for clear confirmation of that exact board without requiring a fixed reply phrase. In corporate fidelity, automatically identify each source role unless truly ambiguous; the board must expose all source thumbnails and role bindings, screenshot-visible fidelity boundary, shell-specific locked/editable regions, exact observed/extension/unknown labels, proposed unseen roles, and limitations. Customer corrections before confirmation replace the current contract. Do not require an internal-theme choice, infer dynamic behavior, or begin project-theme generation/report production before confirmation.
- If the user has a clear reference but it is a PPT, webpage, video, state sequence, more than three corporate screenshots, or multiple screenshots for reconstruct, stop at the unsupported boundary and ask for a supported representative raster input. This is not the no-reference route: do not infer movement and do not recommend the four built-in systems unless the user explicitly abandons the reference route.
- Treat model choice as a platform/session-entry decision. WorkBuddy first use gets one recommendation to use Auto; Codex and Claude Code continue with the current session model. Never ask the user to select or repeatedly switch models inside the intake. If the current session cannot locate reliable static facts, say “当前会话无法可靠读取参考图” and offer only a manual model change followed by a restarted task, or a downgrade to the four built-in systems.
- If no clear reference exists, read `visual-systems.md` and recommend 2-3 genuinely suitable built-in systems. Show each system's exact customer-facing name, one-line description, and bundled preview. Ask the user to choose once, or invite explicit delegation to TaoHtml.
- Do not ask open-ended aesthetic questions such as “What style do you like?”. Do not repeat a theme-selection question after the user chooses or delegates.
- Reference-mode resolution and theme selection use the same clarification counter; visual route selection never expands the six-question hard maximum. Do not ask the reference-mode question after explicit intent. If the project reaches the maximum or the three-no-gain stop before a low-risk visual choice is selected, apply only a safely delegated choice: choose the lowest-risk fit and disclose the basis in the Report Design Brief. Never infer corporate fidelity from an ambiguous request because it creates a fixed-asset lock.
- A selected theme fixes a reusable visual grammar, not a palette. Preserve its composition, hierarchy, image treatment, module language, chart/evidence treatment, and motion grammar unless the brief records a necessary deviation.

## Select The Next Question

Before asking, re-read the conversation, available source, ledger, prior attempts, and counters. Then:

1. Remove gaps whose answers are already present or can be safely inferred.
2. Resolve S0 first, then any missing startup choice according to `Startup Decisions`; after startup, rank the remaining gaps by how much they could change narrative, scope, conclusion, evidence, structure, or delivery.
3. Ask only the largest current gap whose answer would change the report design.

Ask exactly one decision question per round. Do not pack independent questionnaire fields together. Offer 2-3 options only when they are real alternatives and state their design impact briefly.

Treat "decide for me", "not important", or equivalent wording as delegation: choose a reasonable low-risk default, move it to `inferred`, and do not ask again.

For a missing conversion action path, delegation authorizes TaoHtml to locate and verify a channel; it does not authorize invention or an unverified default.

## Question Budget And Stop Rules

Count agent-initiated clarification prompts within the current intake cycle. Count each single-decision startup prompt and the one-time ambiguous reference-mode choice as one. The prompt that asks the user to confirm the displayed Report Design Brief is a separate authorization gate and does not count toward this budget.

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
- The visual source is recorded as one selected built-in visual system, a user reference with known `reference_mode`, or one live-validated corporate-profile binding. Corporate fidelity also records the screenshot-visible fidelity boundary, locked elements, and editable region. Profile reuse records profile id/version, theme fingerprint, resolution basis, and temporary-override state. Any necessary deviation is explicit.
- On the static-reference route, the current VI board is explicitly confirmed and its contract/output paths are recorded; VI approval is not inferred from earlier agreement to use the reference.
- On the profile-reuse route, the current task binding validates against the active profile/version and existing project-theme loader. It substitutes only the repeated VI step; it does not count as Report Design Brief confirmation.
- Route and use mode are known or evident from the input, length is known or explicitly delegated, and required material delivery constraints are known or safely inferred; optional presentation duration may remain unspecified.
- Every material in use has an eligible `source_binding` and recorded binding reason; no workspace convention or residue is acting as an implicit source.
- For a conversion objective, the exact real action path, its source, and its verification status are recorded; non-conversion reports do not need this field.
- No minimum hard-boundary item remains in `missing`; ordinary creative supplements may remain pending customer verification.

Stop asking as soon as these conditions are met. A clear idea can therefore proceed directly to a brief with zero clarification questions.

## Confirmation Rules

### Material summary gate

For any bound Word/PDF/PPT/HTML material route, ask the user to confirm or correct the displayed Material Understanding Summary. If they correct it, issue an updated summary before continuing. Do not impose this gate on an idea-only input.

### Static-reference VI gate

After the content and structure are clear enough to interpret visual fit, follow `static-reference-vi.md`, show the rendered VI PNG, and ask the user to confirm or correct the current board. Bind any clear confirmation to the exact current artifact and conversation turn; never use a fixed authorization phrase as a cross-task token. If the user corrects any visual item or boundary status, rerender the complete board and request confirmation again.

VI confirmation authorizes only the confirmed-VI handoff to the separate project-theme step. It does not confirm the Report Design Brief and does not authorize formal report production. If the project-specific theme output is not yet available, stop at the handoff boundary rather than substituting a built-in theme.

### Design brief gate

Show one current Report Design Brief and ask the user to confirm or correct that exact artifact. Only a reply that clearly confirms this displayed brief opens production; record its current conversation reference rather than matching a fixed reply phrase. Earlier approval to discuss, use TaoHtml, or begin intake does not count. Brief confirmation is authorization, not clarification, so it remains required even when the clarification counter is already six.

If the user adds source material or changes a core viewpoint after confirmation, invalidate the brief, update it, and ask for confirmation again. During production, resolve non-core omissions with a reasonable default or creative supplement, add the exact item to the delivery verification ledger, and continue instead of repeatedly interrupting the user.
