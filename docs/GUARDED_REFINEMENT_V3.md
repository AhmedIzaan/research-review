# Guarded refinement and evaluation amendment — 15 November 2026

This is a new protocol to test the weaknesses observed in the two-seed pilot. No new live outcomes have been collected under it. Earlier experiment outputs and the IEEE paper are preserved; they must not be relabeled as evidence for these changes. Mixed or negative future results remain reportable.

## Refinement changes

Every newly generated proposal must include a falsifiable `core_hypothesis`, a `distinctive_mechanism` relative to supplied prior work, and a `minimum_test`. Revisions are asked to reduce resource demands without silently replacing the scientific question with a generic pipeline. Literature-overlapped distinctions may be replaced by a justified, testable pivot. These are proposal requirements, not verified originality.

Independent reviewers still see the same entering proposal, without each other's feedback. Provider schemas allow only their designated numerical metrics. Numerical scores remain in the saved trace but are removed from revision and safeguard prompts; every textual critique, evidence citation and trade-off remains. The independent outcome judge receives neither reviewer feedback nor safeguard decisions, scores, configuration labels or acceptance labels.

The guarded policy adds one source-grounded comparison call after each changed candidate. It accepts a candidate only if the safeguard identifies at least one improved dimension, no reduced dimension, no critical issue, a preserved mechanism or justified pivot, and no unresolved novelty/feasibility direction. Otherwise it retains the incumbent and stops. Exact unchanged proposals stop without this extra call. Failed safeguard validation preserves the incumbent and records an execution failure; quota exhaustion remains explicit.

Both candidates and the exact selection reason are saved, including rejected candidates. The guard is a refinement agent using the generator model, **not an independent evaluator or a proof of quality**. It can be overly conservative or wrong, favor the initial idea, or stop prematurely. Independent post-hoc candidate scores in `revision_decisions.csv` are needed to check these errors. No outcome-judge score feeds back into revision.

## Controls and ablations

All configurations for a seed/replicate share the same saved initial idea and model settings. Condition order is deterministically randomized.

| Configuration | Purpose |
|---|---|
| `one_shot` | Literature-conditioned initial proposal |
| `generic` | One general reviewer per round |
| `generic_matched` | Four independently prompted generic reviews per round; compare panel size with full specialization |
| `full` | Four specialists plus idea-specific novelty search and guarded refinement |
| `full_unguarded` | Same specialist workflow, accepts every valid revision; tests the safeguard |
| `no_feasibility` | Natural removal of feasibility reviewer |
| `no_contrarian` | Natural removal of contrarian reviewer |
| `no_novelty_retrieval` | No extra novelty queries; initial scholarly context remains |
| `feasibility_to_generic` | Replace feasibility slot with general review; keeps four reviewer calls |
| `contrarian_to_generic` | Replace contrarian slot with general review; keeps four reviewer calls |

Natural removals change call budgets. Replacement controls retain reviewer call counts, **not token counts or evidence access**. Four generic agents are four isolated calls to one model, not four independently trained experts. The full-versus-generic contrast combines specialization and novelty search; the separate retrieval ablation helps disentangle these effects. No reviewer is assumed helpful. Use the same round limit and policy across matched conditions except the explicit safeguard ablation.

`Settings.from_env()` and the interactive demo default to guarded refinement and two ratings. Bare `Settings()` retains the previous always-accept, single-rating library default for compatibility; set these fields explicitly in custom scripts.

## Dataset and independent evaluation

`data/evaluation_seeds_v3.json` contains 12 distinct real papers, two each from six prespecified topic strata: retrieval, factuality, efficiency, reasoning, multilingual transfer and evaluation. Selection uses top remaining BM25 records in the pinned corpus, years 2024–2025, abstracts of at least 80 words, excludes the original ideation/review seeds and uses no generated outcomes. Interleaving ensures the first six cover six strata. Selection queries, identifiers and fingerprints are in the accompanying manifest; reproduce with `scripts/build_evaluation_seeds.py`.

This is a bounded purposive sample, not random or representative of all AI research. Strata are query-based and may overlap. Twelve is a manageable expansion, not a power guarantee. Generation repetitions remain nested within seeds; analysis collapses them within seed before paired tests.

Every initial proposal and **every candidate in every condition**, accepted or rejected, is eligible for independent judging. Duplicate content is reused within a seed/replicate. All versions/conditions in that block receive an identical, capped multi-query scholarly evidence context. It includes proposal citations where available and records omissions, missing references and search failures. The judge searches independently of review feedback. The corpus remains abstract-only and cannot establish global novelty.

Each distinct proposal receives the prespecified number of independent rating calls (default two). Individual integer scores, rationales, evidence and events remain saved. Summaries use the median and report min/max; a failed planned repetition withholds that proposal's aggregate, rather than silently averaging only successful ratings. Repetitions are not extra independent scientific samples and do not remove shared model bias. Different available Gemini judge models can be selected explicitly; access errors do not trigger an undisclosed fallback.

`analysis/revision_decisions.csv` links selection decisions with independently judged candidate-minus-incumbent differences. Iteration plots show accepted proposals; rejected candidates stay in scores and the decision table. `judge_variability.csv` exposes rating ranges. Existing paired analysis reports seed-level differences; Wilcoxon is exploratory and only attempted with enough nonzero seed differences and available SciPy. Larger samples do not automatically establish significance.

## Rerun

Restart the backend after pulling these changes:

```bash
../.venv/bin/python scripts/serve.py
```

The UI enables the revision safeguard and two judge ratings by default. It exposes matched controls, an optional judge model ID, rejection reasons, candidate text differences and individual rating rationales. Existing examples retain their historical behavior and scores. A default full one-round demo plans **16 calls** before retries (12 pipeline calls including final panel/audit, 4 judging calls), with fewer after early stops/content reuse.

Start with the three-seed, one-round five-condition engineering smoke study:

```bash
../.venv/bin/python scripts/run_experiments.py --study results/guarded_v3_smoke --dry-run
../.venv/bin/python scripts/run_experiments.py --study results/guarded_v3_smoke
```

This plans **93 calls**, at most **279 attempts** including retries, before content reuse/early stops. Configured free-tier monetary estimate is zero; quota and model availability remain external constraints. The normal 160-attempt client cap may interrupt retry-heavy jobs. Resume the exact command with an explicitly larger `--max-api-calls` if needed; the cap is excluded from the study-compatibility fingerprint. Never increase other settings while reusing a study directory.

For a full 12-seed, two-round comparison and all ablations, inspect the larger plan first:

```bash
../.venv/bin/python scripts/run_experiments.py \
  --study results/guarded_v3_12seeds --n 12 --rounds 2 \
  --configurations one_shot generic generic_matched full full_unguarded \
    no_feasibility no_contrarian no_novelty_retrieval feasibility_to_generic contrarian_to_generic \
  --max-api-calls 5000 --dry-run
```

This plans **1,620 calls**, at most **4,860 attempts** across generation and judge clients, and about 10.53M input + 2.268M output planning tokens. Token estimates are heuristic, not guaranteed maxima. The attempt cap is a ceiling, not a request to spend it. Only run after checking your free-tier quota or billing; remove `--dry-run` deliberately. You can use `--rounds 3`, `--replicates 2` or `--judge-model AVAILABLE_MODEL_ID`, but re-estimate and use a fresh study path. A three-round, 12-seed, two-generation-replicate all-condition plan is 4,824 calls before retries. This larger run has not been started by the coding agent.

Do not select seeds, stop conditions or rating repetitions based on favorable observed outcomes. Report missing conditions, guard failures and judge failures rather than quietly dropping them.

## Real human evaluation

A successful evaluation exports `evaluation/human_packet.html` and `human_ratings.csv`. Give each rater the packet and a separate CSV copy; withhold traces, scores, condition labels and `blind_key.json`. Have at least two people familiar with AI/NLP score proposals independently with the rubric. These are optional facilities until humans actually complete the forms.

```bash
../.venv/bin/python scripts/analyze_human_ratings.py \
  --evaluation results/guarded_v3_smoke/evaluation \
  --ratings /path/to/rater_a.csv /path/to/rater_b.csv \
  --output results/guarded_v3_smoke/human_analysis
```

Imports reject unknown IDs, duplicate rater/proposal pairs, missing assessed scores and noninteger/out-of-range scores. Unassessed blank rows are skipped. Outputs preserve individual ratings, proposal medians, seed-level condition scores and pairwise quadratic weighted Cohen kappa. Kappa can be undefined for constant scores; sparse agreement is descriptive, not validation of truth. Record raters' expertise, blinding, rubric training and disagreements in the eventual paper. No human ratings have been fabricated or supplied here.

## Verification and remaining work

Software checks cover guard acceptance/rejection/failure, bounded stopping, rejected-candidate evaluation, score isolation, independent generic slots, budget bounds, repeat medians/ranges, failure handling, cache compatibility, human import and trace navigation. Synthetic fixtures remain in tests and temporary directories, never research findings. Run:

```bash
../.venv/bin/python -m pytest -q
node tests/trace-ui.test.cjs
```

Live provider execution, human ratings and empirical quality gains remain to be measured in the user's next run. The existing IEEE paper should be amended only after those outputs are inspected; historical pilot results must remain distinguishable from the new protocol.
