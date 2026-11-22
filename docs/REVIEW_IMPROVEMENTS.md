# Improvements after the RAG demonstration

The motivating run is `082836f447f4bec330ef` (topic: evaluating factual reliability in RAG). It completed one review–revision round but did not assess its revised proposal or run independent evaluation. Its reviewers also supplied scores outside their specialist roles. Existing records and scores remain unchanged.

## What changed

| Observed weakness | Implemented change |
|---|---|
| Novelty reviewer supplied a feasibility score; specialist boundaries blurred | Model response schemas now allow only each role's designated scores. Off-role numbers fail structured-output validation and use the existing retry mechanism. Contrarian reviews require a falsification test and no numeric scores. Prompts emphasize different scientific responsibilities. |
| Final revision was never reviewed | The default interactive run includes a final assessment by the configured panel. This assesses the final proposal without another revision or an extra refinement round. Failures, low scores and unresolved criticism remain visible. |
| New filtering mechanism was not searched after revision | Final novelty assessment searches the revised idea's queries plus a bounded query from its title and method. This checks new mechanisms even if the model repeats broad old queries. The no-novelty-retrieval ablation disables these searches. |
| GPU fit and statistical power were asserted without measurements | Newly generated proposals require structured assumption checks: assumption, validation step, acceptance criterion and fallback. The UI labels them untested. Prompts and the independent rubric explicitly reject unmeasured guarantees. The system does not actually benchmark a proposed GPU workload or establish statistical power. |
| Novelty was asserted by combining existing components | Proposals must compare their mechanism with supplied paper IDs, identify overlap, describe a proposed difference, and state what remains to be verified. Unknown comparison IDs are rejected. A hardware constraint alone does not establish novelty. |
| Exact citations did not establish claim support | A separate, default-enabled audit assesses every unique final-review citation as supported, partial or unsupported using its excerpt and source abstract. Its prompt receives no reviewer identities or scores. It is a same-model semantic judgment, not proof of entailment or an external fact check. Source matching and semantic judgments remain separate. |
| Independent evaluation was optional and absent in the test | Enabled by default. The existing separately prompted judge evaluates initial and revised proposals with condition labels and reviewer feedback withheld. The UI shows final-minus-initial score changes, individual scores, rationales and failures. Identical content is judged once and reused. |
| Aggregation mixed unwanted cross-role numbers | Only designated role scores enter score summaries. All criticism and explicit qualitative trade-offs are retained. Historical records remain readable, including their original cross-role scores. |
| Old results could be confused with the updated methodology | New runs record `specialized_review_v2` and the updated evidence protocol. The experiment runner defaults to `results/smoke_v3` and rejects an old-method study before modifying its status. No new experimental improvement is claimed until real runs are evaluated. |

## Test the updated app

Stop the existing server with Ctrl+C, then restart from the project directory:

```bash
../.venv/bin/python scripts/serve.py
```

Open `http://127.0.0.1:8000` and perform a hard refresh (Ctrl+Shift+R).

Use the same RAG topic and select **full system / one round**. Leave these defaults checked:

- Assess the final revised proposal.
- Audit citation support.
- Compare with independent rubric evaluation.

The plan is **13 model calls before retries**: one generation, four initial reviews, one revision, four final reviews, one citation-support audit and up to two independent judgments. With three attempts per call, the upper planning bound is 39 attempts, further limited by the server's configured cap. Failed calls, early stopping, and identical-content judgment reuse can alter actual usage. The app rejects a configured cap below the selected planned call count before any live requests.

For comparison, two refinement rounds plan 19 calls; three plan 25. One-shot with independent evaluation plans two calls and has no reviewer panel. You can explicitly disable all three additional options for a six-call one-round full run, but the final proposal then remains unassessed and there is no independent improvement measure.

Inspect the final proposal's comparison and assumption-check sections. Then inspect **Final proposal assessment**, **Do the citations support the claims?**, and **Independent rubric judgments**. A completed workflow can still have poor final scores, unsupported citations or practical risks. Those are findings to preserve, not errors to hide.

## Limits and reproducibility

The default model is unchanged. The separate judge and citation auditor may share model biases. The corpus is still a bounded abstract snapshot; none of these checks proves global novelty. Reviewers use distinct prompts and isolated inputs, not independent model weights. Prompt changes can reduce repetitive criticism, but the next live run must establish how well the roles actually specialize.

Interactive runs continue under unique `results/web_runs/<job-id>` directories. Different interactive runs do not share an initial idea, so they are not matched experimental comparisons. For controlled comparisons use a fresh study directory. The core workflow's new final assessment and support audit are explicit `Settings` options; the web defaults enable them. CLI study defaults retain the original bounded review schedule plus independent judging, using the updated role/proposal contracts. Do not pool those outputs with older pilot scores as if the methodology were unchanged.

Automated tests use synthetic responses in temporary directories and separately check that real historical traces still load. They cover schema restrictions and retries, final reviewer isolation, revised-mechanism searches, citation-audit completeness, assumption contracts, budget handling, failures and old-study preservation. New live Gemini outputs are deliberately left for the user's next test. Browser verification remains unavailable in this restricted shell.
