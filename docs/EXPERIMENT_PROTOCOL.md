# Historical pilot protocol v3

**For new runs:** see [the guarded refinement amendment](GUARDED_REFINEMENT_V3.md). This file documents the earlier pilot; its two-seed outcomes must not be merged with the amended study.

Objective: test whether specialized reviewers and literature-based overlap checking change independently judged proposal novelty, feasibility, clarity, importance and evidence grounding. Hypotheses are two-sided; improvements are not assumed.

The study is an implementation/replication extension inspired by ResearchAgent, SciMON, InfAL, Many Heads and the supplied completed Business Research review. ResearchAgent already includes criterion-specific reviewers and feasibility evaluation. InnoEval is close prior work. Our bounded comparison is useful as course-level empirical evaluation, without claiming an unprecedented architecture. We do not reproduce ResearchAgent's academic graph, entity store or human-preference elicitation.

## Authorized retrieval amendment — 8 November 2026

Before any successful generated proposal, the user authorized a downloaded local
corpus in place of mandatory live scholarly APIs. This version uses a pinned
2,114-record pool: 2,097 usable abstracts from six official ACL XML collections
and 17 distinct pre-existing project/prior-work anchors. Corpus selection is
independent of outcomes, and the 20 evaluation seeds remain unchanged. See
`LOCAL_CORPUS.md` for source hashes, exclusions, BM25 parameters and attribution.
Every condition and the independent judge use this same frozen pool; their
queries and information contexts differ. The novelty-retrieval ablation removes
additional idea-specific queries, not the initial literature context.

## Citation-format correction after the live pilot

The first pilot used free-form exact quotation transcription and produced thirteen
reviewer failures and five rejected unique judgments. Protocol 3 supplies
selectable source passage IDs and attaches exact quotations programmatically.
Unknown IDs remain invalid; semantic support is not guaranteed by ID selection.
Model, corpus, rubric and treatment roles are unchanged. A fresh `smoke_v2` study
keeps the original pilot intact; do not combine its scores with the new protocol.
See `CITATION_PROTOCOL_FIX.md` and the real pilot findings for evidence and limits.

## Inputs and sampling

`data/seeds.json` fixes 20 records before observing any generated output. Eligibility: a verified existing ACL Anthology publication record in the previous evidence review, relevant to AI/NLP scientific ideation, automated review or evaluation; an available saved abstract bounded by Abstract and Introduction headings; inspectable author/year/source metadata. A relevant survey supplies synthesis context. Selection is purposive, not random or performance-based. The two smoke seeds are ResearchAgent (NAACL 2025) and SciMON (ACL 2024). No benchmark performance claims follow from these two.

`seed_provenance.json` records capture paths and SHA256 hashes. Abstracts remove line/page prefixes, PDF soft-hyphen control characters and whitespace line breaks. Original captures are unchanged. Exact original retrieval times are unavailable; imported records retain a source capture date, not an invented precise timestamp. Metadata inherited from the prior automated evidence review remains subject to its human-verification limitations. Browser primary-source rechecks covered the two smoke seed pages in this session. Other records rely on the saved provenance, rather than new live verification of all 20.

This sample overrepresents scientific ideation itself. Evaluation cannot generalize to arbitrary NLP research or claim a representative random sample. Broader domain-stratified seed selection would be a separate preregistered extension. All records remain in the manifest; failed generations must be reported rather than quietly replacing seeds.

## Controlled treatment

For each seed/replicate, retrieve five related records and generate exactly one original proposal. All six configurations reuse that proposal and original evidence. Fix Gemini model, temperature 0.4, output cap 4,096 tokens, six-week/single-consumer-GPU/public-data constraints and at most three review/revision rounds. No LLM is trained. Only novelty reviewers have additional dynamic literature search; their generated 1–3 queries are saved. The ablation disables those extra searches, not seed literature.

The generic reviewer has all four scoring criteria but no specialist focus or extra search. It is explicitly a simplified generic iterative baseline. The proposed system has four independent contexts, with feedback delivered only to the reviser. Their assessments are independent in information access, not independent learned models. Sequential API execution is intentional for quota management.

Stop rules: configured round limit (0–3), unchanged proposal, all reviewers failing, failed revision or API cap. The last valid proposal is retained. Reviewer failures are not imputed as low scores. A revised final proposal receives independent evaluation even though another panel review would exceed the configured refinement budget. Count completed revisions separately from attempted review rounds when interpreting partial failures.

All CLI condition orders are deterministically shuffled from seed ID, replicate and PRNG seed 20261107. Staging configurations in notebooks imposes a different order; use the CLI for the main experiment. Shared initials reduce initial-quality variation but make conditions dependent, which is why comparisons are paired by seed.

Primary treatment uses natural unequal budgets: per seed at three rounds, shared initial = 1 call; generic = 6; full = 15; no feasibility = 12; no contrarian = 12; no novelty search = 15. Total = 61 before retries. Distinguishing specialist content from extra inference requires a further equal-budget generic-panel control; the current six-condition study cannot make that causal claim. Reviewer-removal effects also include reduced inference allocation.

## Independent assessment

A separate judge call receives only proposal text, constraints and a separate query of the fixed local corpus. It never sees review scores, system condition or revision history. Randomize evaluation order; judge identical seed/replicate/proposal content once and map it to all aliases. The rubric in `evaluation.py` fixes anchors for five individual 1–5 metrics and demands a rationale per dimension. Same-model judging is affordable but not equivalent to external expert validation.

The full condition's initial and rounds 1–3 plus the other four iterative finals yield at most eight unique judged proposals per seed, with one-shot identical to the shared initial. Additional intermediate versions are saved for all methods but are not needed for the primary iteration plot. With 20 seeds, the maximum primary call count is 1,380 before retries. Actual account quotas determine feasible sample size; stop and disclose failures rather than fabricate results.

Evidence grounding is an ordinal judge rating of support from retrieved abstracts, not a measured truth rate. ID membership and excerpt matching are mechanically validated. Semantic claim support, retrieval recall and novelty correctness require human checking. Missing search results are disclosed to the judge and saved; resulting scores must be qualified as unsupported by fresh retrieval, not treated as grounded verification.

Human form: one row per blinded unique proposal, separate scores and comments, blank rater ID. Copy rows for independent raters; keep the blind key away from judges. Seek at least two knowledgeable raters on a fixed subset and report item counts. Do not fill human scores or claim agreement before collection. Weighted kappa or ordinal agreement analysis should follow actual ratings, with limitations and confidence intervals, rather than using literature coefficients.

## Analysis

Keep all individual ratings and raw rationales. For final comparisons, average replicates within each seed first, then report seed-level count, mean, median and standard deviation. Use paired seed-level differences, counts of positive/negative/tied changes, and exploratory rank-biserial effects when enough observations exist. Means of ordinal scores are descriptive summaries, not interval-scale scientific measurements.

For at least ten nonzero paired seed differences, the implementation permits an exploratory two-sided Wilcoxon signed-rank test and Holm correction over all tested metric/condition pairs. This conservative software gate is not a power calculation or proof that symmetry assumptions hold. Below the gate, report descriptive comparisons without p-values. A smoke sample is for debugging, not statistical efficacy claims. Repeated versions, agents, or multiple judge calls are not independent seeds.

Generate five score/resource figures only from real output files: baseline comparison, ablations, full-system iteration, novelty versus feasibility, execution time. Plot all five quality dimensions; report variation in tables. Preserve generation/reviewer failures, invalid outputs and excluded judge rows. Report stopped/incomplete conditions. A longer or more expensive condition can appear better due to extra computation; call budgets and shared initial costs must accompany quality comparisons.

## Validity limits

Abstract-only evidence and lexical query matching miss prior art and implementation details. Scholarly index coverage, query selection, retrieval time and cached results affect novelty claims. A dynamic seed-dependent search may retrieve different evidence for different final proposals; this is part of the evaluation procedure, not a controlled fixed gold prior-art set. Same-family generator/judge bias, possible memorization and persuasive style remain. Human calibration is pending. Proposal-level feasibility does not establish execution success. There is no real hypothesis execution, fine-tuning, human-subject experiment or autonomous scientist platform here.
