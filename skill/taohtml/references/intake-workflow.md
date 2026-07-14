# Intake Workflow

Use this workflow after a source summary is confirmed and before editing or creating HTML.

## State Machine

Move through these states in order:

| State | Result | Exit condition |
|---|---|---|
| S0 Route | Idea, Word/PDF, or PPT/HTML selected | Route is known |
| S1 Base choices | Reading/presentation and concise/standard/detailed selected | Both choices are known or safely inferred |
| S2 Material understanding | Source summary is shown | User confirms or corrects it |
| S3 Design completion | Missing design decisions are resolved | Project passes the design-ready gate |
| S4 Design brief | One customer-readable brief is shown | User explicitly confirms the current brief |
| S5 Production | HTML, visual system, motion, and objective QA are completed | Objective failures are fixed |
| S6 Delivery | Files, checks, and production assumptions are reported | Deliverables are usable |

Do not move from S2 to design completion until the material summary is confirmed. Do not write HTML before the current S4 brief is explicitly confirmed.

## Internal Decision Ledger

Maintain these four buckets without turning them into a visible questionnaire:

```text
known | confirmed | inferred | missing
```

Update the ledger after reading each source and after every user answer. If the user delegates a decision, record the chosen default under `inferred` and do not ask again.

## Base Choices

Only ask for a base choice when the user has not already made it.

### Use mode

- **Reading**: every page is understandable without a presenter; all content is visible by default.
- **Presentation**: the visible copy is tighter; the page follows a spoken sequence through staged states.

### Length

- **Concise**: only the argument and evidence required for the goal.
- **Standard**: enough context, mechanism, proof, and conclusion for the normal use case.
- **Detailed**: additional evidence, explanation, and appendix depth.

Estimate the page range from the actual material. Do not use a fixed range shared by every project.

## Question Selection

Check missing decisions in this dependency order:

1. Desired audience outcome
2. Audience knowledge, concern, and decision context
3. Core viewpoints and scope
4. Evidence, data, and unresolved conflicts
5. Chapter structure
6. Visual direction and motion density
7. Delivery constraints

This is not a fixed questionnaire. Skip known items. Ask one question at a time and only if the answer would change the design.

When a logic gap or conflict has more than one defensible resolution, present 2-3 options with their impact. When several chapter structures are reasonable, show only the chapter names and one sentence describing each chapter's job; do not design individual pages yet.

## Design-Ready Gate

A project is design-ready when:

- The report goal and audience are clear enough to choose a narrative.
- All core viewpoints to preserve are identified.
- Evidence required by this report type is present or explicitly resolved.
- No unresolved conflict can reverse the main conclusion.
- One chapter structure has been selected.
- The visual direction is selected or delegated to TaoHtml.
- Reading/presentation mode, length, and offline delivery constraints are known.

Stop asking questions as soon as these conditions are met.

## Confirmation Rules

### Material summary gate

Ask the user to confirm or correct the displayed Material Understanding Summary. If they correct it, issue an updated summary and ask again.

### Design brief gate

Show one current Report Design Brief and end with:

> 回复“确认”后，TaoHtml 将按这份设计简报开始制作 HTML。

Only a reply that clearly confirms this displayed brief opens the production gate. Earlier approval to discuss, use TaoHtml, or begin the intake does not count.

If the user adds source material or changes a core viewpoint after confirmation, invalidate the brief, update it, and ask for confirmation again. During production, resolve non-core omissions with a reasonable default and list the decision at delivery rather than repeatedly interrupting the user.
