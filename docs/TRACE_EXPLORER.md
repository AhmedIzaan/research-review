# Trace explorer

The trace reader is now a dedicated page, reached from **Trace explorer** in the sidebar. It opens saved data without generating another idea or spending Gemini calls. The run selector includes interactive jobs and controlled experiment traces. **Open completed example** chooses the latest completed interactive run when available.

## Read a trace in order

1. **Overview** — see the proposal title, execution status, refinement count, independent novelty comparison when available, citation-support count and runtime. Unresolved final reviewer concerns and large reviewer/judge score differences are highlighted. Workflow completion is explicitly separate from scientific success.
2. **Starting idea** — read the preserved original proposal. Experimental details, untested assumptions, prior-work comparisons and references are available as disclosures rather than long parallel columns.
3. **Review round** — select one of the role cards to read its explanation, criticism, recommendations and falsification test. Expand citations or searches when needed. Keyboard users can move among reviewer tabs using arrow keys, Home and End.
4. **What changed** — switch from feedback to a field-by-field comparison. Red marks removed words; green marks additions. The before version is that round's actual input, not always the global initial proposal. Text edits are not automatically classified as improvements or as resolved criticisms.
5. **Final assessment** — inspect the independent final panel's critiques. It is visually separate from the judge's evaluation. Disabled, incomplete and historical assessments are described explicitly.
6. **Evidence & sources** — filter final-review citation audits by supported, partial or unsupported claims. Each claim has an explanation, expandable exact excerpt and source link. The source library can be filtered by title, author or paper ID.
7. **Independent evaluation** — compare initial and revised scores on five separate dimensions using paired bars and numeric changes. Inspect initial/final rationales and the actual judge literature. Older evidence protocols are identified; missing scores are not replaced with reviewer scores or zeros.
8. **Execution details** — inspect API attempts, token usage, failures, events and optional technical metadata. Raw JSON is kept behind a disclosure; the full export is still available at the top.

The stage rail becomes horizontal on narrower screens. Feedback columns and comparisons stack on mobile. Live updates preserve the selected stage, reviewer, and expanded evidence. All source/model text is rendered as text; paper links accept HTTP(S) only.

## Open and test

Hard-refresh the browser with Ctrl+Shift+R, then choose **Trace explorer**. If the server is not running:

```bash
../.venv/bin/python scripts/serve.py
```

No experiment rerun is required to see the new reader. Existing JSON exports, saved runs and independent scores are unchanged. No new model calls are made by viewing, filtering, or comparing saved traces.

## Verification

```bash
node --check frontend/app.js
node --check frontend/trace-model.js
node --check frontend/trace-view.js
node tests/trace-ui.test.cjs
../.venv/bin/python -m pytest -q
```

The JavaScript checks include pure score/diff tests and interaction tests using a small DOM harness with actual saved research data. They cover app startup, stage navigation, reviewer tabs, revision comparison, audit filtering, source search, legacy empty states, live selection preservation and safe text rendering. This harness is not a browser and does not verify pixel layout. Browser visual verification remains unavailable in the restricted development environment. Node is needed for these tests only; the local app has no Node build or package-install requirement.
