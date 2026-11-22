# Research findings: corrected live pilot

**Literature-Grounded Research Idea Generation Using Specialized Multi-Agent Reviewers**

Study: `smoke_v2`. Status: **completed_with_failures**. Independent seed papers: **2**.

## Research objective and architecture

Investigate whether specialist novelty, feasibility, clarity/importance and contrarian reviewing, literature-based overlap checking and bounded refinement change independently judged research-proposal quality. ResearchAgent supplies the main inspiration; criterion-specific reviewing already exists, and InnoEval is close prior work. This is a comparative implementation and extension, without a first-invention claim.

The implemented controller retrieves literature, generates a shared original proposal, collects independent reviewer contexts, preserves criticisms and disagreements, revises up to three rounds and records all versions. Baselines and ablations share initial proposals, model settings, constraints and source corpus. The same pretrained Gemini model serves separate roles; there is no training or fine-tuning. The Python state engine ran this pilot; the optional LangGraph adapter remains unverified in this environment.

## Dataset and generated ideas

The frozen local corpus contains 2,114 records with abstracts from pinned official ACL metadata and attributed prior-work anchors. The fixed evaluation manifest contains twenty purposive AI/NLP ideation/review papers. This pilot uses ResearchAgent and SciMON only; it is narrow and not a representative sample of NLP research.

- Seed `2024.acl-long.18` generated **Latent-Probed Multi-Agent Iterative Refinement for Novel Scientific Idea Generation**.
- Seed `2025.naacl-long.342` generated **Integrating Automated Novelty Checking into Chain-of-Ideas Scientific Generation Frameworks**.

These are proposals under review. Their internal experimental plans have not been executed. Each seed has one initial proposal reused across all six conditions.

## Configurations and independent evaluation

One-shot generation; generic iterative review; the full four-role panel; removal of feasibility; removal of contrarian review; removal of additional novelty searches. All use Gemini 3.5 Flash-Lite with fixed settings. Natural call budgets differ: a generic reviewer consumes fewer calls than the panel, and removal ablations consume fewer calls. The no-novelty-search condition keeps all four reviewers and original context.

An isolated judge request receives only the proposal, constraints and separately retrieved evidence, without reviewer scores, condition or round labels. Five 1–5 metrics have explicit anchors. Identical content shares one judgment. Source passage IDs resolve to exact quotations, validating provenance rather than semantic correctness. The same-model judge remains biased and human calibration is uncollected.

## Observed execution

- Saved configurations: 12. Accepted final-condition ratings: 12/12.
- Unique judgments: 16 accepted / 16 attempted. Score rows including shared aliases: 26; they are not independent experimental units.
- Reviewer failures: 1; rejected unique judgments: 0.
- Saved API attempts: 141. Recovered request failures: {'NetworkOrTimeoutError': 2, 'HTTP 503': 4}.
- Provider-reported tokens: at least 815,568; 6 requests have unknown usage. Configured free-tier cost rates are estimates, not billing verification.
- Wall time: 38.56 minutes.

Remaining failure: seed `2024.acl-long.18`, condition `generic`, round 2: Reviewer returned wrong role. Its last valid proposal was retained and independently evaluated. This limits comparisons involving that condition; an accepted score does not imply every review round succeeded.

## Final mean ratings

| Configuration | Seeds scored | Novelty | Feasibility | Clarity | Importance | Grounding |
|---|---:|---:|---:|---:|---:|---:|
| one_shot | 2 | 4.00 | 3.50 | 4.00 | 4.00 | 4.00 |
| generic | 2 | 3.50 | 3.50 | 4.00 | 4.00 | 4.00 |
| full | 2 | 3.50 | 4.00 | 4.50 | 4.00 | 4.50 |
| no_feasibility | 2 | 4.00 | 3.50 | 4.00 | 4.00 | 4.00 |
| no_contrarian | 2 | 4.00 | 3.50 | 4.00 | 4.00 | 4.00 |
| no_novelty_retrieval | 2 | 4.00 | 3.50 | 4.00 | 4.50 | 4.00 |

Individual scores, paired differences and variability remain in the saved CSV files; these means are descriptive summaries of ordinal ratings.

## Baseline comparison

Full panel minus one_shot: novelty -0.50, feasibility +0.50, clarity +0.50, importance +0.00, evidence_grounding +0.50.
Full panel minus generic: novelty +0.00, feasibility +0.50, clarity +0.50, importance +0.00, evidence_grounding +0.50.

In this pilot, reviewing shifts judged quality toward practicality, clarity and grounding while judged novelty is lower than the one-shot baseline. The generic condition has no mean advantage over one-shot on these five dimensions and includes one early failure. This does not establish a population effect or prove that every revision is useful.

## Ablations

no_feasibility minus full: novelty +0.50, feasibility -0.50, clarity -0.50, importance +0.00, evidence_grounding -0.50.
no_contrarian minus full: novelty +0.50, feasibility -0.50, clarity -0.50, importance +0.00, evidence_grounding -0.50.
no_novelty_retrieval minus full: novelty +0.50, feasibility -0.50, clarity -0.50, importance +0.50, evidence_grounding -0.50.

Removing feasibility or contrarian review gives identical aggregate ratings here, so the study cannot distinguish which reviewer contributes most. Additional novelty retrieval does not raise judged novelty in this sample, although full-system grounding is higher. Component effects are conditional on the sampled inputs and inference allocation; fewer reviewers also reduce the call budget.

## Full-system iterative refinement

| Round | Seeds scored | Novelty | Feasibility | Clarity | Importance | Grounding |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 2 | 4.00 | 3.50 | 4.00 | 4.00 | 4.00 |
| 1 | 2 | 4.00 | 4.00 | 5.00 | 4.00 | 4.00 |
| 2 | 2 | 4.00 | 4.00 | 4.50 | 4.50 | 4.50 |
| 3 | 2 | 3.50 | 4.00 | 4.50 | 4.00 | 4.50 |

Gains are not monotonic. The SciMON-seeded full-system proposal receives feasibility 3→4 and final novelty 4→3. The ResearchAgent-seeded proposal receives clarity 4→5 and grounding 4→5. Additional rounds can plateau or reverse a judged metric. With one same-model judgment per content, judge noise cannot be separated reliably from true proposal changes.

## Validity, failure handling and conclusion

Two purposive seed papers are the independent units, not twelve condition runs, twenty-six score rows, or the number of agents. No statistical significance claim is justified here. Same-family generation/judging, no human calibration, incomplete prior-art coverage, abstract-only evidence, possible memorization, unequal inference budgets and one generic-review failure all limit interpretation. Proposal-level feasibility is not executed scientific success.

The first quotation-transcription pilot remains separately preserved under `results/smoke`. The corrected passage-ID run has no quotation-validation or judge failures. The remaining generic wrong-role failure is preserved; future reviewer schemas now restrict the response to the requested role so mismatches trigger structured-output retries. Existing results were not silently repaired or replaced.

The workflow now demonstrates real generation, all four specialized roles, local literature grounding, iterative refinement, baseline/ablation execution and independent scoring. Its preliminary finding is a possible novelty–feasibility trade-off rather than uniform improvement. A larger controlled sample and human validation are needed to assess whether that pattern generalizes.

Figures and numeric tables: `results/smoke_v2/analysis/RESULTS.md`. Raw responses, per-round traces, human-rating templates and failure audits are saved alongside them. Notebook execution uses the documented ordinary-Python fallback unless a real Jupyter kernel is separately verified.
