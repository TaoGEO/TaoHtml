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
  "schema_version": "1.0",
  "task_id": "current-invocation-id",
  "route": "word_pdf",
  "visual_route": "static_reference",
  "material_summary": {
    "status": "confirmed",
    "artifact_id": "material-summary-v2",
    "confirmation_ref": "current conversation turn reference"
  },
  "reference_vi": {
    "status": "pending",
    "artifact_id": null,
    "confirmation_ref": null
  },
  "project_theme_compiled": false,
  "design_brief": {
    "status": "pending",
    "artifact_id": null,
    "confirmation_ref": null
  }
}
```

Use `idea_only | word_pdf | existing_ppt_html` for `route` and
`unresolved | built_in | static_reference` for `visual_route`. Word/PDF and existing
PPT/HTML routes require a current confirmed material summary; idea-only uses
`material_summary.status` = `not_required`. Static reference requires a current confirmed VI and a compiled
project theme; other visual routes use `reference_vi.status` = `not_required` and
`project_theme_compiled` = `false`. Every confirmed gate must name the exact current
artifact and the current conversation confirmation reference.

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
  --action material-summary-preview

python scripts/check_production_authorization.py \
  --state /absolute/path/to/current-production-authorization.json \
  --action reference-vi-preview

python scripts/check_production_authorization.py \
  --state /absolute/path/to/current-production-authorization.json \
  --action formal-html
```

The checker rejects schema drift and impossible ordering, prints JSON, and exits
nonzero when the requested action is not currently allowed. Run `--action formal-html`
immediately before saving the first runnable formal `index.html`, and run
`--action deliver-formal-html` before delivery. Preserve the current state and checker
result with task evidence when possible. Never edit the state merely to bypass a gate;
update it only after the corresponding current artifact and confirmation exist.
