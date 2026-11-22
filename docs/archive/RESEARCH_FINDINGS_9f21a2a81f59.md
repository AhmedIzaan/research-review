# Live pilot findings and research discussion

**Literature-Grounded Research Idea Generation Using Specialized Multi-Agent Reviewers**

Study: `smoke`. Status: **completed_with_failures**. This is a real two-seed debugging pilot, not a completed efficacy study.

## Objective and implemented method

Test whether distinct novelty, feasibility, clarity/importance and contrarian reviewers, literature-based overlap checking and bounded revision change independently judged proposal quality. ResearchAgent inspires the workflow; it already uses criterion-specific reviewers. Multi-agent reviewing and evidence-grounded evaluation are established, with InnoEval as close prior work. Our contribution is a course-level comparative implementation and ablation study, not a first-invention claim.

The implemented workflow searches real literature, generates one shared initial proposal per seed, collects independent reviewer contexts, preserves all feedback and failures, and revises up to three rounds. Early stopping retains the last valid idea. No model is trained and no proposed scientific experiment is executed. This pilot used the Python state engine; the LangGraph adapter remains separately unverified because its dependency is unavailable.

## Dataset and experimental configurations

The local retrieval pool has 2,114 real records with abstracts: six pinned official ACL metadata downloads plus attributed project/prior-work anchors. The fixed evaluation manifest has twenty seeds; this pilot used ResearchAgent and SciMON only. They are purposive scientific-ideation inputs, not a representative sample of NLP research. The corpus fingerprint and raw-source hashes are saved.

Conditions: one-shot, generic iterative review, full specialist panel, no feasibility reviewer, no contrarian reviewer, and no additional novelty retrieval. Within each seed all conditions share the initial proposal, original literature, Gemini model/settings and constraints. The no-retrieval condition retains original context. Natural API budgets differ, so additional computation confounds a pure specialization effect.

## Evaluation procedure

A separately prompted Gemini judge receives proposal text and its own literature query, without configuration labels, reviewer scores or refinement history. It scores novelty, feasibility, clarity, importance and evidence grounding from 1–5 with separate rationales. Identical proposal content shares one judgment. Human forms are prepared but no human ratings have been collected. Same-model judging remains vulnerable to shared knowledge and preference bias.

The pilot required verbatim evidence excerpts and rejected quotations that did not match source text. Mechanical quotation matching establishes provenance only; it does not validate semantic support or universal novelty.

## Observed execution and failures

- Saved configurations: 12 across 2 seeds.
- Accepted final-condition rating rows: 7 of 12.
- Distinct judgment contents attempted: 11; accepted: 6; rejected: 5. Aliases are not independent observations.
- Reviewer failures: 13. All recorded reviewer failures concern evidence excerpt validation.
- Stopping reasons: {'one_shot': 2, 'iteration_limit': 6, 'all_reviewers_failed': 2, 'unchanged_proposal': 2}.
- Saved API attempts across the study ledger: 129; failure types: {'HTTP 503': 9, 'NetworkOrTimeoutError': 3, 'StructuredOutputValidationError': 3}. The ledger includes earlier agent-network failures before the successful terminal run.
- Provider-reported token total, where available: 570,648; 12 attempts lack usage metadata. This is a lower bound, not a complete billed-token total.
- Latest suite wall time: 31.27 minutes.

The configured token rates are zero for the user-confirmed free tier. This is an estimate, not an independently verified bill. Shared initial-generation resources and judge resources are recorded separately from condition-level resource tables.

## Individual final ratings

| Seed | Condition | Novelty | Feasibility | Clarity | Importance | Grounding | Stop | Reviewer failures |
|---|---|---:|---:|---:|---:|---:|---|---:|
| 2024.acl-long.18 | full | missing | missing | missing | missing | missing | unchanged_proposal | 0 |
| 2024.acl-long.18 | generic | missing | missing | missing | missing | missing | iteration_limit | 0 |
| 2024.acl-long.18 | no_contrarian | 5 | 4 | 5 | 5 | 5 | iteration_limit | 0 |
| 2024.acl-long.18 | no_feasibility | 4 | 4 | 5 | 5 | 5 | iteration_limit | 1 |
| 2024.acl-long.18 | no_novelty_retrieval | missing | missing | missing | missing | missing | iteration_limit | 0 |
| 2024.acl-long.18 | one_shot | 4 | 3 | 4 | 5 | 5 | one_shot | 0 |
| 2025.naacl-long.342 | full | 4 | 4 | 5 | 5 | 4 | unchanged_proposal | 2 |
| 2025.naacl-long.342 | generic | 3 | 4 | 4 | 4 | 4 | all_reviewers_failed | 1 |
| 2025.naacl-long.342 | no_contrarian | 3 | 4 | 4 | 4 | 4 | all_reviewers_failed | 3 |
| 2025.naacl-long.342 | no_feasibility | missing | missing | missing | missing | missing | iteration_limit | 2 |
| 2025.naacl-long.342 | no_novelty_retrieval | missing | missing | missing | missing | missing | iteration_limit | 4 |
| 2025.naacl-long.342 | one_shot | 3 | 4 | 4 | 4 | 4 | one_shot | 0 |

Missing ratings are not imputed. A final proposal retained after all reviewers failed can still have a reused initial judgment; that is fallback behavior, not successful refinement.

## Baseline comparison and ablations

Only one seed has accepted final ratings for both one-shot and full review. Different valid sample counts mean the configuration averages cannot be interpreted as matched treatment effects. Both no-novelty-retrieval final judgments were rejected, preventing that ablation comparison. The contribution of feasibility or contrarian review therefore remains unresolved.

The single accepted paired case (2025.naacl-long.342) has full-minus-one-shot changes of novelty: +1, feasibility: +0, clarity: +1, importance: +1, evidence_grounding: +0. Its full run also had failed reviewer messages. This isolated, same-model-judged case does not establish improvement or general superiority.

## Iterative refinement

The full panel stopped on an unchanged proposal after two rounds for one seed and three for the other. This is an implemented stopping rule, not evidence that quality rose monotonically. Some version judgments are missing. Figures now show each seed separately with gaps; pooling different available seeds at different rounds could produce a misleading trend. No conclusion about continued gains, plateau or reversal is supported by these incomplete ratings.

## Diagnosis and engineering correction

Several rejected quotations changed PDF-extracted hyphenation or punctuation; others inserted ellipses or additional words. The strict validator correctly rejected source mismatches, but free-form quotation transcription made the pipeline fragile. Three judge responses also returned empty uncertainty strings and succeeded after schema retries. HTTP 503 failures recovered through the existing retry path.

The corrected code supplies deterministic source-passage IDs, restricts model evidence selections to those IDs, and attaches exact stored quotations programmatically. Unknown IDs and invented quotation fields remain invalid. This prevents transcription errors without treating fuzzy matches as evidence. Semantic support still requires evaluation and human checking.

The original raw proposals, reviews, API responses and judgments are preserved. Original plots are archived under `audit/original_analysis`; the failure audit and raw-file hashes are also saved. A fresh controlled rerun must use `results/smoke_v2` and the corrected evidence protocol; the correction has software tests but has not yet been verified through a live Gemini study.

## Figures and tables

See `results/smoke/analysis/RESULTS.md`, the five PNG/PDF figures, `summary.csv`, `paired_comparisons.csv`, `iteration_scores.csv`, `missing_evaluation_rows.csv`, and `resources.csv`. The three project notebooks now inspect genuine saved pilot outputs; ordinary Python cells were verified with the documented fallback. Real Jupyter-kernel verification is still pending.

## Limitations and conclusion

Two purposive seeds, incomplete matched scores, citation-validation failures, shared-model judging, no human calibration, a bounded abstract corpus, possible memorization, unequal API budgets, and proposal-level rather than executed feasibility all limit interpretation. No significance claim is made. Agent/version counts do not enlarge the independent sample size.

The live pilot demonstrates functioning generation, specialist review, refinement, ablations and separate judging, while exposing a citation-interface failure that prevents a defensible efficacy conclusion. Whether specialized review improves novelty or feasibility, which reviewer is most useful, and whether added rounds help remain open until the corrected controlled study is evaluated.
