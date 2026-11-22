# Citation protocol correction after the first live pilot

The first live `results/smoke` study ran on 8 November 2026 and saved twelve
seed/configuration outputs. Nine HTTP 503 responses recovered on retry.
The final `completed_with_failures` status primarily concerns **thirteen
reviewer citation failures and five distinct rejected judge outputs**. Six
score-table rows inherit those judge failures through content aliases. Only
seven of twelve final-condition rows have accepted independent ratings.

## Observed cause

The first protocol asked the model to copy exact excerpts from retrieved
abstracts. Actual outputs sometimes replaced PDF extraction artifacts such as
`Chain-ofIdeas` with `Chain-of-Ideas`, changed quote characters, omitted footnote
markers or inserted ellipses. Some outputs also added words absent from the
source. Exact matching correctly rejected these, but a single rejected citation
discarded its review or judgment. In two configurations all reviewers failed,
so the workflow retained the initial proposal. This limits any efficacy analysis.

Three judge API responses also returned empty uncertainty strings. Schema
validation rejected them and retries produced structured responses. The updated
prompt explicitly requires a nonempty uncertainty sentence.

## Corrected interface

`evidence_catalog.py` creates deterministic passage identifiers for exact slices
of each supplied abstract. The model sees source metadata and these passages;
its response selects `passage_id`, states a claim and assigns a relation. The
JSON schema restricts IDs to the supplied catalog. The program attaches the
corresponding original paper ID and exact stored quotation, then runs the same
strict evidence validation. Saved review and judgment formats remain readable.

Unknown identifiers and model-authored quotation fields are rejected. No fuzzy
matching, invented citations, automatic score changes or relaxed quote checks
are used. Valid passage selection establishes provenance only: a model can
still choose an irrelevant passage or make an unsupported semantic claim.

The fix applies equally to specialized reviews, generic reviews and independent
judging. Retrieval corpus, model, temperature, proposal schema, rubric and
stopping rules remain the same. Scientific manifests now record protocol 3 and
`evidence_protocol=passage_ids_v1`. API audits contain the actual wire schema
and passage selections.

## Preservation and rerun

All original raw proposals, reviews, model responses and judgments were
preserved and hashed. Original analysis figures were archived under
`results/smoke/audit/original_analysis`. The pilot report and notebooks contain
genuine outputs with explicit missing-score limitations. The correction has
offline tests; its live Gemini integration still needs verification.

Run the corrected complete smoke study from the normal network-enabled terminal:

```bash
../.venv/bin/python scripts/run_experiments.py --study results/smoke_v2
```

The default suite directory is also now `smoke_v2`, protecting the legacy study.
It keeps the same two fixed seeds and six configurations, with up to three rounds.
Expected budget remains at most 138 calls before retries and early stopping;
token usage may change with the new citation format. Model free-tier quota
remains account-dependent. Do not mix the old and new protocols or silently
replace missing pilot ratings with values from a different run.

To inspect the corrected results in notebooks after the run, set
`RESEARCH_REVIEW_STUDY=smoke_v2` before executing them. By default inspection
continues to show the preserved first pilot; live notebook experiments target
the new directory. Real Jupyter-kernel verification remains separate from the
documented ordinary-Python fallback execution.


## Corrected pilot completed

The `smoke_v2` run completed on 8 November 2026 with all twelve final-condition
ratings available, sixteen accepted unique judgments, and no quotation-validation
failures. One generic reviewer returned the wrong role in round two and its
condition stopped early. That failure remains recorded. Future wire schemas now
restrict each reviewer to its requested role so wrong-role responses are rejected
during structured-output validation and enter the existing retry path. This
additional restriction has unit tests but has not yet been live-verified.

Current results show higher mean feasibility, clarity and grounding with the
full panel, alongside lower novelty than one-shot, across only two seeds. The
current findings document and notebooks use `smoke_v2`; earlier pilot artifacts
remain separate. No statistical significance or human agreement is claimed.
