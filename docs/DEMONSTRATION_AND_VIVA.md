# Demonstration and viva guide

**Present state:** a real two-seed pilot has saved all twelve configurations and separate judgments. Thirteen reviewer messages and five distinct judgments failed citation checks, leaving incomplete final scores. The notebooks now show genuine agent traces and actual diagnostic figures. A corrected passage-ID interface is tested locally; its live rerun is pending. Never present this incomplete pilot as evidence of superiority.

## Six-minute explanation

1. **Problem:** LLM research proposals may overlap prior literature, lack realistic data/compute plans, or sound clearer than their underlying method. Novelty and feasibility can conflict.
2. **Foundation:** ResearchAgent supplies the literature → idea → critique → revision pattern. It already includes criterion-specific reviewing. We use a simplified loop and compare specialist roles and additional novelty evidence; this is not a claim to invent multi-agent reviewing.
3. **Roles:** novelty compares mechanisms with searched papers; feasibility examines data, compute and implementation; clarity/importance checks specificity and value; contrarian challenges assumptions and proposes failure tests.
4. **Evidence:** show a saved novelty query, actual returned titles/DOIs/URLs, then the cited ID and matching abstract excerpt. Explain why missing hits do not prove originality and why matching a quotation does not prove entailment.
5. **Communication:** independent reviewer prompts receive the same current proposal, with no other critiques. The aggregator preserves all feedback, failures and disagreements. Only the reviser sees the collected critiques.
6. **Refinement:** show the untouched initial proposal, a round's feedback and its revision, then the final version. Stop after the configured limit or explicit failure/unchanged criteria.
7. **Comparisons:** one-shot returns the shared initial idea; generic uses one broad reviewer; full uses four roles and prior-art search. Removing feasibility, contrarian or novelty search tests component contributions. Unequal call budgets remain a confound.
8. **Evidence of benefit:** show independent judge scores and paired seed results, if available. If not, state exactly that effectiveness is not yet measured. Improvements, regressions and trade-offs must all be reported.

## Reproducible full-workflow example

Seed: Baek et al., *ResearchAgent*, NAACL 2025, DOI `10.18653/v1/2025.naacl-long.342`; source `https://aclanthology.org/2025.naacl-long.342/`. The first entry of `data/smoke_seeds.json` is a source record, not a generated proposal.

After following README setup and configuring `.env`:

```bash
python -m research_review.cli preflight
python -m research_review.cli run --n 1 --rounds 3 --configurations full --study results/demo
python -m research_review.cli evaluate --study results/demo
```

This focused run needs at most 16 generation/review calls and four full-system version judgments, before retries. It demonstrates the entire workflow but is not a baseline comparison. Inspect `results/demo/initials/`, `runs/`, `evaluation/judgments/`, and API ledgers. The saved `results/smoke` full-system ResearchAgent run is an actual end-to-end example, with its failed reviewer messages visible. The command above starts a separate run using the corrected citation interface.

For the actual comparative demonstration:

```bash
python -m research_review.cli run --n 2 --study results/smoke
python -m research_review.cli evaluate --study results/smoke
python -m research_review.cli analyze --study results/smoke
```

Open the three notebooks after the CLI run. Verify `provenance='live_gemini'`, actual model IDs, retrieved evidence, nonempty individual scores and complete configuration coverage. Explain the 138-call two-seed budget, rate limits and the separate shared-initial accounting. With a 15-second request interval, throttle waiting alone is roughly 35 minutes at this upper-bound call count, plus response and retrieval time; do not promise an instant fresh classroom run. Prepare a saved successful trace once API access is available.

## Potential viva questions

**What is agentic about the implementation?** A controller manages state and bounded feedback; the novelty reviewer uses retrieval tools; distinct reviewer tasks produce validated messages that guide subsequent generation. These are role-based agents over a pretrained model, not separately trained neural networks.

**Did you train an LLM?** No. We implement and test an inference-time orchestration methodology. There is no supervised training, fine-tuning or reward-model optimization.

**How does this differ from ResearchAgent?** We use a simplified metadata/abstract retrieval loop with four explicit roles, evidence validation and controlled removals. ResearchAgent's full academic graph, entity store and human-preference elicitation are not reproduced. The generic baseline is an approximation.

**Are specialized reviewers a new invention?** No. ResearchAgent, multi-agent ideation work and InnoEval already explore related specialization and evidence grounding. Our contribution is a bounded implementation and empirical comparison, with its limitations stated.

**How are reviewers independent if they share one model?** Their prompts and contexts are separate and they cannot inspect other critiques before aggregation. Their learned biases and knowledge remain shared, so this is information independence, not statistical independence.

**Why run reviewer calls sequentially?** To reduce free-tier quota pressure while preserving independent contexts. Concurrency is not required to implement the methodology.

**How do agents communicate?** Pydantic-validated JSON in explicit workflow state. Reviews include scores, reasoning, problems, recommendations, evidence and uncertainty. The aggregator passes all critiques to the reviser.

**What is novelty verification actually verifying?** It searches prior work and requires cited IDs and exact abstract excerpts. This supports auditable overlap critique. It cannot prove that no similar research exists or that every cited claim is semantically supported.

**What happens when retrieval fails?** The error remains in the trace; failed searches are not cached as successful empty results. The grounded novelty review is withheld if no usable search evidence is available. Other reviewers may continue.

**What if one reviewer fails?** Preserve the failure and valid reviews. Revise using available feedback with the missing role disclosed. If all reviews fail, stop and retain the last valid proposal.

**What if feedback contradicts?** The aggregator retains every critique and flags large score disagreements; the reviser is instructed to address trade-offs explicitly. It does not resolve all semantic disagreements mechanically.

**Can the loop run forever?** No. Configuration validates 0–3 rounds, with explicit stop conditions. LangGraph also receives a recursion limit. The Python engine uses the same bounded step logic.

**How do you prevent invented citations?** Agents may cite only supplied paper IDs, and evidence excerpts must occur in the supplied abstract. Metadata joins recover the actual URLs and DOIs. These checks do not establish claim entailment.

**What is the no-retrieval ablation?** It retains the novelty persona and original seed/related context but removes additional idea-specific prior-art searches. It does not remove all literature from generation.

**Why use ablations?** They reveal how outcomes change when a component is removed. A reviewer may harm a dimension. Removal also changes compute, so the interpretation is conditional on the implemented resource allocation.

**Is this a fair comparison if full review uses more calls?** Seed, initial proposal, model, settings and round limits are matched. Call budgets are unequal and disclosed. We cannot attribute all improvement to specialization rather than extra inference without an additional equal-budget control.

**Who evaluates the generated ideas?** A separate blinded judge context with a fixed rubric and fresh literature. System reviewers are not the sole outcome evaluators. Optional human forms support later calibration; no uncollected human ratings are claimed.

**Why is the same-model judge limited?** It may favor the model's own style, repeat its knowledge gaps or reward persuasive detail. Isolation removes direct feedback leakage but not shared-model bias.

**Why not report significance for two papers?** A smoke study checks execution and examples, not population efficacy. Independent units are seeds, not agents or rounds. The software reports descriptive differences for small samples.

**What is Wilcoxon testing?** Paired ordinal-score differences under distributional assumptions including approximate symmetry. The implementation gates exploratory tests and applies Holm correction; adequate sample size alone does not validate those assumptions.

**How do you measure the novelty–feasibility trade-off?** Preserve separate independent ratings, inspect paired changes and scatter plots, and examine cases where one dimension rises while the other falls. Do not hide the trade-off in one aggregate score.

**Can a high feasibility rating prove the proposed research works?** No. It is proposal-level implementability judgment. Actual execution would supply stronger evidence and is outside this project's scope.

**What are the actual results today?** The first live pilot saved twelve configurations. Seven final-condition rows have accepted ratings; thirteen reviewer messages and five distinct judgments failed strict citation matching. The main scientific questions remain unresolved. The source-passage ID correction has software tests but needs a separate live rerun. Read the current XML/status and failure audit for exact counts.

**What would strengthen the study?** Broader fixed sampling, repeated independent seeds/replicates, expert blinded ratings, another judge family, semantic evidence audits, equal-inference-budget controls and transparent reporting of failures and negative findings.
