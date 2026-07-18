# Workflow Profile Contract

This contract defines how one installed TaoHtml Skill selects and applies one primary
Workflow Profile. A Profile is a business-production path loaded on demand; it is not
an independently installed Skill, a replacement for intake, or a second production
engine.

## Contents

- [Contract Identity](#contract-identity)
- [Layering Model](#layering-model)
- [Routing Contract](#routing-contract)
- [Primary Profile And Capability Overlays](#primary-profile-and-capability-overlays)
- [Horizontal Parameters](#horizontal-parameters)
- [Required Profile Sections](#required-profile-sections)
- [IR Mapping Boundary](#ir-mapping-boundary)
- [Existing Gates And Implementations](#existing-gates-and-implementations)
- [Conflict Resolution](#conflict-resolution)

## Contract Identity

- Contract id: `taohtml.workflow-profile`
- Contract version: `1.0`
- Catalog: `workflow-profiles.md`
- Cardinality: exactly one primary Profile per project after routing is resolved
- Definition status in this engineering node: nine foundation definitions; no
  Golden Path detail implementation

Each Profile has one stable `profile_id`, one exact customer-facing Chinese name, and
one definition version. The definition version is an internal Profile-contract
identity; it does not by itself change TaoHtml's release version, Report IR schema,
Compiler, Runtime, theme, Handoff schema, or any other implementation version.

## Layering Model

Keep these dimensions independent:

1. Apply the existing `new_build | review_only | continue_existing` task-intent
   overlay from `project-handoff.md` when applicable.
2. Establish one of the existing material entry routes: idea only, Word/PDF, or
   existing PPT/HTML. The Profile layer never adds a fourth entry route.
3. Select one primary Workflow Profile from the user's business objective and the
   semantics of eligible material.
4. Add only bounded capabilities from other Profiles when needed; never run two
   complete Profile workflows in parallel.
5. Resolve horizontal parameters through the existing intake, source, visual,
   Runtime, evidence, and continuation contracts.

The task-intent overlay, material entry, primary Profile, capability overlays, and
horizontal parameters must remain separately recorded. A value in one layer must not
be used as a hidden substitute for another.

## Routing Contract

Route by semantic outcome, not by labels alone:

1. Re-read the user's explicit objective, audience outcome, desired decision or
   action, eligible inspected material, confirmed Material Understanding Summary,
   and still-supported handoff state.
2. If one business-production path is clearly dominant, automatically select that
   primary Profile, record the selection basis, load only its foundation definition
   from `workflow-profiles.md`, and continue without a Profile question or catalog
   display.
3. Do not ask again when a prior answer, confirmed report goal, or material semantics
   already establishes the primary Profile. A report-type recommendation is not a
   reason to repeat a known business-goal question.
4. When the primary business objective remains genuinely ambiguous after using the
   eligible semantic evidence, read `workflow-profiles.md`, display all nine exact
   customer-facing Profile names in one round, and ask exactly one routing question:
   which business goal should the finished report primarily accomplish? After the
   answer, apply only the selected foundation definition.
5. Record that catalog as the latest active option set. A short answer or ordinal can
   select an item only when it directly answers that still-active catalog in the same
   conversation; numbering in documentation is never a global command interface.
6. Ask the user to choose a business objective, never a Profile id, Report IR field,
   Projection, schema property, Compiler mode, Runtime feature, or theme implementation.

Do not route with a keyword blacklist, a hard-coded numeric command, filename-only
matching, directory conventions, or a fixed mapping from report type to Profile.
Terms and document types may contribute semantic evidence, but the deciding question
is the outcome the artifact must accomplish. Do not inspect an unbound source merely
to classify a Profile.

Profile routing uses the existing clarification budget. Automatic routing uses zero
questions; the full-catalog fallback is one routing question. It does not create a
new intake cycle, a nine-part questionnaire, or extra questions beyond the existing
maximum.

## Primary Profile And Capability Overlays

Record the resolved state as:

```text
primary_profile = profile_id | exact name | definition version | selection basis
capability_overlays = bounded capability | source Profile | reason | affected scope
```

The primary Profile owns the overall design-ready interpretation, narrative promise,
and Profile-specific acceptance emphasis. A capability overlay may borrow one bounded
need, such as a data review module, a teaching explanation, or live delivery support.
It must not import a second Profile's complete intake, design-ready gate, narrative
sequence, artifact set, or QA workflow.

If the requested result changes so another business outcome becomes dominant, replace
the primary Profile explicitly. Treat that as a result-changing design decision and
re-evaluate the affected source interpretation and Report Design Brief under the
existing continuation and confirmation rules. Do not silently keep two primary
Profiles.

## Horizontal Parameters

These are cross-cutting parameters, not Profiles. A Profile may provide a low-risk
default only when the value is not already known, confirmed, inherited, or delegated.
The existing source, brief, visual, Runtime, evidence, and Handoff contracts remain
authoritative.

| Parameter | Contract boundary |
|---|---|
| `input_entry_route` | Idea only, Word/PDF, or existing PPT/HTML; preserve the existing route handshake and source gate. |
| `use_mode` | Reading or presentation; it remains a Runtime/delivery choice, not a scenario. |
| `visual_binding` | Built-in visual system, confirmed project theme, or validated enterprise Profile binding; never copy theme implementation into a Workflow Profile. |
| `evidence_rigor` | `contextual`, `balanced`, or `formal` Profile default and minimum evidence emphasis; high-risk and source-protection rules always override it. |
| `information_density` | Low, medium, or high production guidance after content length and actual material are known. |
| `motion_density` | Low, medium, or high intent constrained by the current Runtime contract; it cannot authorize new motion engineering. |
| `continuation_state` | New build, review-only, meaning-preserving local continuation, or meaning-changing continuation under the existing Handoff contract. |

Do not ask the user to fill these as a Profile form. Reuse values already established
by conversation, eligible material, the Report Design Brief, or a valid handoff.

## Required Profile Sections

Every Profile foundation definition must contain these exact sections:

| Section | Required content |
|---|---|
| 身份与版本 | Stable id, exact name, definition version, and foundation/detailed status. |
| 适用目标 | The dominant business outcome that makes this the primary Profile. |
| 排除范围 | Nearby outcomes that require another primary Profile or an existing subsystem. |
| 成品 | Customer-usable TaoHtml output within the current delivery boundary. |
| 所需信息 | Business information needed to judge the result; reuse known/source-backed items and never expose a new questionnaire. |
| design-ready 条件 | Profile-specific readiness additions to the existing common gate. |
| 叙事任务 | The jobs the narrative must accomplish, without prescribing fixed pages. |
| 证据规则 | Profile-specific evidence emphasis while retaining common source and hard-boundary rules. |
| 横向参数默认值 | Defaults for the cross-cutting parameters; they never override known or confirmed values. |
| IR 映射边界 | Semantic intent only and the conditions under which the existing explicit IR engineering route may use it. |
| Runtime/主题使用 | Use of existing Runtime and visual routes without copied implementation. |
| QA 验收 | Profile-specific acceptance emphasis in addition to existing objective QA and delivery gates. |
| 能力叠加与冲突处理 | Allowed bounded overlays and the rule for choosing or replacing the primary Profile. |

Definitions may be centralized in the catalog while they remain foundation-level.
Create a separate Profile file only when a later engineering node implements enough
real workflow detail to justify on-demand loading. Do not create empty placeholders.

## IR Mapping Boundary

Workflow Profiles are upstream semantic guidance, not Report IR:

- Do not add or change Report IR schema fields for Profile routing.
- Do not expose Report IR as a user choice or add an IR questionnaire.
- Do not invoke the Report IR route merely because a Profile was selected.
- Only an explicit Report IR engineering request or current project pilot
  authorization may use the existing IR workflow after the Report Design Brief is
  confirmed.
- When that route is already authorized, a Profile may guide the selection of existing
  semantic combinations such as report prototype, evidence rigor, narrative units,
  Projection intent, or optional entities. It must not invent unsupported fields,
  mutate the Compiler, or bypass validation.

The Report Design Brief remains the customer-readable source of confirmed business
decisions. IR derivation, when separately authorized, remains downstream and does not
replace Profile routing, brief confirmation, or production authorization.

## Existing Gates And Implementations

Profile selection changes none of these existing behaviors:

- The three material entry routes and conversation-scoped option binding.
- Source binding, PDF preflight, and the Word/PDF/PPT/HTML Material Understanding
  Summary confirmation gate.
- Handoff overlay, source-role/availability distinctions, continuation matrix, and
  four independent structured handoff conclusions.
- Visual source selection, profile reuse, static-reference VI confirmation, and
  project-theme compilation.
- The complete current Report Design Brief and its explicit confirmation.
- Current-file Production Authorization for formal HTML, browser QA, and delivery.
- Direct-HTML default production, existing Runtime and theme implementations,
  objective QA, traceability, and `《待核实内容清单》` delivery.

A Profile may point to these contracts but must not copy their schemas, scripts,
algorithms, theme assets, QA logic, or gate state.

## Conflict Resolution

Apply conflicts in this order:

1. User-confirmed business outcome and responsibility boundary.
2. Hard source, evidence, safety, legal, and action-path boundaries.
3. Existing Handoff, brief-confirmation, and Production Authorization gates.
4. Primary Profile contract.
5. Bounded capability overlays.
6. Profile defaults for horizontal parameters.

When a lower layer conflicts with a higher one, keep the higher rule and record the
deviation or unresolved gap. When an overlay would change the dominant outcome,
required artifact, or acceptance promise, it is no longer an overlay: explicitly
re-route the primary Profile and reapply the affected existing gates.
