# Production Authorization

Use this fail-closed state contract for the current invocation. It separates
confirmation previews from formal HTML production and delivery. A previous task's
confirmation, an existing HTML file, or the user's initial request to “continue” does
not authorize the current formal output.

## Current-Task State

Before any preview gate or formal production action, write a task-local JSON file that
uses this exact shape:

```json
{
  "schema_version": "1.1",
  "task_id": "current-invocation-id",
  "route": "word_pdf",
  "visual_route": "static_reference",
  "material_summary": {
    "status": "confirmed",
    "artifact_path": "gates/material-summary.md",
    "artifact_sha256": "9b41e9e597cd42bd247366d8435fc48eff12d24a818677eaf82c68c2a4ec8fbb",
    "confirmation_ref": "current conversation turn reference"
  },
  "reference_vi": {
    "status": "pending",
    "artifact_path": "gates/reference-vi.html",
    "artifact_sha256": null,
    "confirmation_ref": null
  },
  "project_theme_compiled": false,
  "design_brief": {
    "status": "pending",
    "artifact_path": "gates/report-design-brief.md",
    "artifact_sha256": null,
    "confirmation_ref": null
  }
}
```

Use `idea_only | word_pdf | existing_ppt_html` for `route` and
`unresolved | built_in | static_reference` for `visual_route`. Word/PDF and existing
PPT/HTML routes require a current confirmed material summary; idea-only uses
`material_summary.status` = `not_required`. Static reference requires a current confirmed VI and a compiled
project theme; other visual routes use `reference_vi.status` = `not_required` and
`project_theme_compiled` = `false`. Before requesting confirmation, save every
applicable material summary, VI board, or design brief as a customer-readable file
inside the current task artifact root. A `confirmed` gate records its safe relative
`artifact_path`, the SHA-256 of those exact current bytes, and the current conversation
`confirmation_ref`. Recompute and record the digest only when that exact file is the
artifact the user confirmed. A later byte change invalidates the gate until the changed
artifact is confirmed again. `pending` may name the planned artifact path but keeps the
digest and confirmation reference null; `not_required` keeps all three null.

## Allowed-Action Matrix

| Current blocking gate | Allowed next artifact/action | Still forbidden |
|---|---|---|
| Bound material summary unconfirmed | inspect the eligible bound material, render/update the Material Understanding Summary, request its confirmation | VI, design brief, formal HTML, browser QA, delivery |
| Visual route unresolved | ask the one current visual-source decision | VI, design brief, formal HTML, browser QA, delivery |
| Static-reference VI unconfirmed | run the environment/readability gates, render/update the VI standards-board preview, request confirmation/correction of that exact artifact | project theme, design brief, formal HTML, browser QA, delivery |
| VI confirmed but project theme not compiled | compile the exact confirmed project theme | design brief, formal HTML, browser QA, delivery |
| Design brief unconfirmed | render/update the Report Design Brief and request its confirmation | formal HTML, browser QA, delivery |
| Every applicable current gate complete | create/refine formal HTML, run browser QA, deliver formal HTML | none from this authorization contract |

The material summary, VI standards board, and Report Design Brief are gate artifacts,
not formal report HTML. Do not use “preview” to create or hand over a nearly finished
deck before authorization.

## Machine Gate

Run the bundled standard-library checker before the requested action:

```bash
python scripts/check_production_authorization.py \
  --state /absolute/path/to/current-production-authorization.json \
  --artifact-root /absolute/path/to/current-task \
  --action material-summary-preview

python scripts/check_production_authorization.py \
  --state /absolute/path/to/current-production-authorization.json \
  --artifact-root /absolute/path/to/current-task \
  --action reference-vi-preview

python scripts/check_production_authorization.py \
  --state /absolute/path/to/current-production-authorization.json \
  --artifact-root /absolute/path/to/current-task \
  --action formal-html
```

The checker resolves each confirmed file under `--artifact-root`, rejects absolute
paths, traversal, symlink escape, missing files, and current-byte hash mismatches. It
also rejects schema drift and impossible ordering, prints JSON, and exits nonzero when
the requested action is not currently allowed. Run `--action formal-html` immediately
before saving the first runnable formal `index.html`; run `--action browser-qa` before
browser QA and `--action deliver-formal-html` before delivery so a post-confirmation
change fails closed at every formal boundary. Preserve the current state and checker
result with task evidence when possible. Never edit the state merely to bypass a gate;
update it only after the corresponding current artifact and confirmation exist.

## Trust Boundary

The task-local path and verified SHA-256 prove that the checked file still has the
bytes recorded at confirmation time. `confirmation_ref` is trace metadata supplied by
the executing Agent; this standard-library checker does not access or independently
authenticate the conversation platform. Therefore a missing or malformed reference is
rejected, but the checker does not claim that a non-empty reference proves user intent.
Keep the reference auditable and retain the corresponding conversation evidence under
the platform's own access controls.
