# Project Handoff And Continuation

Use this reference whenever the request concerns an existing project, a handoff
record, a current HTML artifact, a review, or continued work. This is a task-intent
overlay on the three content routes in `intake-workflow.md`; it is not a fourth
content entry.

## Contents

- [Task Intent Overlay](#task-intent-overlay)
- [Source Role And Availability Map](#source-role-and-availability-map)
- [Candidate Discovery Boundary](#candidate-discovery-boundary)
- [Read-Only Handoff](#read-only-handoff)
- [Continue Existing Work](#continue-existing-work)
- [Readiness And Operation Claims](#readiness-and-operation-claims)

## Task Intent Overlay

Record exactly one current task intent:

- `new_build`: create a new report through the ordinary route-aware workflow.
- `review_only`: read and map the handed-off state without changing files or
  producing HTML.
- `continue_existing`: take over an existing project and make an explicitly
  requested revision or continue production from its verified state.

Keep the content route separately as `idea_only | word_pdf |
existing_ppt_html`. A handoff can describe any of those routes, and an unresolved
route may remain unresolved during a read-only review. Do not show an extra entry
choice for “handoff.”

Infer the task intent from the user's requested action. Do not use filenames,
operating-system paths, company names, or a fixed keyword list to classify it. If
the user asks only to read, understand, audit, or take inventory, use `review_only`
even when they also say they may continue later. Move to `continue_existing` only
when they ask to change or resume the artifact.

## Source Role And Availability Map

For every bound item in a handoff, record these independent fields:

```text
source identity | source_binding | source_role | availability_status |
inspection coverage | supports | limits | observation basis
```

Use one of these source roles:

- `original_customer_material`: first-party material supplied by the customer,
  such as source documents, real data, screenshots, quotations, or evidence.
- `secondary_handoff_summary`: an Agent- or human-written account of earlier work.
  It can orient the next Agent but does not replace the original material it
  describes.
- `current_artifact`: the current HTML, asset package, PDF export, or other report
  output. It proves what is presently rendered, not where its claims came from.
- `visual_reference`: a bound image or other supported reference used to define
  visual treatment or corporate fidelity.
- `agent_generated_material`: generated copy, simulated values, diagrams,
  placeholders, or other creative supplements.
- `described_unavailable_material`: material named or described in the handoff but
  not currently available for inspection.

Use one of these availability states:

- `workspace_readable`: the exact bound item can be opened in the current task
  workspace. Record `complete | partial` inspection coverage separately.
- `platform_visible_not_retrieved`: the platform shows the exact item, but its
  bytes have not been retrieved into the current task.
- `handoff_record_only`: the item exists only as a statement in a handoff record.
- `confirmed_missing`: the user or an authoritative platform/source state confirms
  that the exact item has been lost, deleted, or is no longer recoverable.
- `not_yet_verified`: current availability has not been established.

Do not promote a role or status silently. A secondary summary remains secondary
even when it is detailed. A current artifact remains an artifact rather than
original evidence. A local file lookup that returns no match proves only that the
checked location did not produce the item; it does not prove that the material was
cleaned, deleted, or permanently lost. Keep the status `not_yet_verified` or
`handoff_record_only` until stronger evidence exists.

## Candidate Discovery Boundary

Apply the existing source-binding rules without exception. Inspect content only
after the item is a current upload or explicit user selection, is explicitly bound
by the current task instruction, or is an exact candidate path the user has
confirmed.

After the task route or handoff scope exists, candidate discovery may inspect only
task-scoped metadata or directory locations the user has placed in scope. It may
list a precise candidate path for confirmation, but it must not read that candidate
first. Do not recursively scan a home directory, Desktop, Downloads, platform cache,
cloud-sync root, unrelated workspaces, or other broad user locations in search of a
presumed source.

If a platform exposes an attachment or artifact that has not been retrieved, record
`platform_visible_not_retrieved` and use the platform's supported retrieval path.
Do not substitute a broad filesystem search. If retrieval is unavailable, report
the limitation without converting it to `confirmed_missing`.

## Read-Only Handoff

Default a `review_only` handoff to **0 clarification questions**. Read only eligible
bound items, build the role/availability map, and report:

1. what is directly available and inspected;
2. what is inherited only from a secondary account;
3. what the current artifact visibly contains;
4. what is platform-visible, record-only, confirmed missing, or not yet verified;
5. what work can safely continue; and
6. what would need source recovery or confirmation before a meaning-changing edit.

Do not restart the full route interview, create a Material Understanding Summary or
Report Design Brief merely for the audit, run formal production, or create/modify
HTML. If a missing item limits the review, state the limit and the smallest useful
next input without turning the read-only response into a question. Do not say that a
secondary handoff is “sufficient for all subsequent changes.”

The read-only result is a state map, not production authorization. It may say an
exact artifact was **found** or **can be previewed** when that is observed. It must
not say the report is **ready** or **formally deliverable**.

## Continue Existing Work

For `continue_existing`, reuse every still-supported fact from the role/availability
map and prior verified artifacts. Perform delta intake: do not replay startup,
audience, goal, length, visual, or structure questions whose answers remain known.
If one missing decision would materially change the requested result, ask only that
single largest gap and apply the existing repetition, information-gain, and six-
question limits in `intake-workflow.md`.

Continuation without restored original sources is normally safe for:

- layout, spacing, typography, color, and other reversible visual adjustments;
- Runtime-compatible navigation, technical, portability, and local asset fixes; and
- local wording improvements that preserve the current claim, data, provenance,
  responsibility boundary, and conclusion.

Restore the original source or obtain explicit user confirmation of the exact change
before modifying:

- real data, quotations, citations, source attribution, or source status;
- which evidence supports which claim, and any uncertainty or contradiction;
- real customer/company identity or achieved outcomes; or
- a core viewpoint, main conclusion, scope promise, or responsibility boundary.

Explicit confirmation does not waive independent verification required for legal,
medical, financial, safety, or other high-risk facts. When an ordinary scene,
example, projected value, viewpoint, or expression is missing, continue under the
existing output-first rules, keep it separate from source facts, and add it to the
delivery-time `《待核实内容清单》`. Do not turn every unavailable original into a
block.

Previous gate artifacts and handoff claims may seed the current ledger, but they do
not by themselves authorize a new formal artifact. Rebuild only the affected source
interpretation and brief fields, then display and confirm the complete current brief
through the existing gate and satisfy the current-task contract in
`production-authorization.md`. A local copy, layout, color, or motion revision does
not change the brief's core meaning, but formal HTML, browser QA, and delivery still
require the current applicable machine gates.

## Readiness And Operation Claims

Before claiming **ready** or **formally deliverable**, verify at least:

- the exact current artifact and every used material have eligible bindings, roles,
  availability states, and inspection coverage;
- the current production-authorization action succeeds where formal output is in
  scope;
- strict offline asset QA and the required browser preflight/HTML QA pass on the
  current artifact;
- core-viewpoint/evidence traceability and any executable action path still match
  the current confirmed brief; and
- the delivery verification handoff is current.

If these checks are incomplete, use bounded language such as **found**, **can be
previewed**, or **not yet verified**. Do not convert the existence of an HTML file,
a successful open, or a handoff assertion into **ready**, **QA passed**, or
**formally deliverable**.

Give operating instructions only from one of two evidence bases:

1. `current_artifact_tested`: exercise the controls on the exact current HTML and
   describe only what passed; or
2. `current_runtime_contract`: describe the generic behavior currently documented
   in `runtime-contract.md`, clearly stating when the handed-off artifact has not
   been verified to implement it.

Do not repeat an untested control description from a handoff summary. This overlay
does not add Runtime capabilities, bypass the content-editor boundary, create a new
corporate Profile data category, or weaken profile isolation and validation in
`profile-memory.md`.
