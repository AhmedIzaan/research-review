# Research findings and execution status

**Literature-Grounded Research Idea Generation Using Specialized Multi-Agent Reviewers**

Prepared for the FAST-NUCES Islamabad Agentic AI project. This is an honest interim results document: scientific comparisons are pending live API access. It must not be submitted as a completed evaluated study.

## Objective and architecture

Investigate whether distinct novelty, feasibility, clarity/importance and contrarian reviewer roles, with retrieved prior-art evidence and bounded revision, improve independently judged research proposals. A retriever supplies scientific metadata; a generator writes a validated proposal; independent reviewers critique it; a lossless aggregator retains conflicting advice; a reviser produces up to three versions. A separate blinded judge evaluates outcomes. LangGraph is supported; the dependency-light state machine was the locally exercised engine.

ResearchAgent is the primary methodological inspiration, not an exact reproduced baseline. It already uses criterion-specific review. SciMON motivates comparison with prior literature; InfAL motivates adversarial critique. Existing multi-agent ideation and InnoEval preclude first-invention claims. The contribution is a controlled comparative course implementation and component-removal analysis.

## Dataset and comparison configurations

A separate 2,114-record local corpus supplies retrieval evidence. A fixed 20-paper purposive AI/NLP ideation/review evaluation dataset was imported from saved primary-source evidence with provenance hashes. The smoke subset contains ResearchAgent and SciMON. Original documents and review artifacts remain intact. Selection criteria and inherited verification limitations are in the protocol.

Conditions: one-shot; generic iterative review; full specialist panel; without feasibility; without contrarian; without additional novelty retrieval. All reuse the exact initial idea per seed/replicate. Model ID: `gemini-3.5-flash-lite`, chosen by the user for free-tier use. Natural request budgets differ and will be reported.

## Evaluation procedure

Separate 1–5 novelty, feasibility, clarity, importance and evidence-grounding ratings; fresh judge evidence; no system labels or review feedback supplied to the judge. Store per-item rationale, evidence and uncertainty. Human ratings remain optional and uncollected. Paired summaries operate on seed-level outcomes, not on the number of agents or versions. Five figure-generation routines and exploratory ordinal tests are implemented but cannot yield findings before live data exist.

## Actual observations

| Item | Observation |
|---|---|
| Fixed paper records | 20 imported; 2 fixed smoke seeds |
| Automated tests | 52 passed, 1 skipped at the latest local verification; see current `results/pytest.xml` for authoritative latest counts |
| Skipped verification | LangGraph adapter: library unavailable |
| Notebook code | 14 ordinary Python cells executed across three notebooks using the documented fallback runner |
| Live Gemini proposals | 0; the key works in the user terminal, but this agent shell has restricted networking |
| Literature retrieval | Local BM25 search works over 2,114 real records; scholarly APIs are optional |
| Browser primary-page checks | Two smoke seed pages verified; this does not validate Python API connectivity |
| Independent quality scores | 0 |
| Human ratings | 0 |
| Baseline/ablation/iteration findings | Not available |
| Quality figures/statistical findings | Not generated from absent data |

These are engineering verification observations, not evidence that specialized reviewers improve scientific ideas. Unit tests use explicitly synthetic fixtures in temporary test directories and are excluded from experimental evaluation.

The two-paper three-round study is estimated at at most 138 model calls before retries; twenty papers at 1,380. These are planned counts, not actual usage. Free-tier token-rate settings are zero; account quota and eligibility have not been tested. No paid usage was initiated.

## Research questions still unanswered

- Did specialized reviewing improve novelty? **Not measured.**
- Did it improve feasibility? **Not measured.**
- Was there a novelty–feasibility trade-off? **Not measured.**
- Which reviewer was most useful, or did a removal help? **Not measured.**
- Did additional novelty retrieval identify actual overlapping ideas? **No live generated idea has been checked.**
- Did further rounds help, plateau, or reverse? **Not measured.**

The implemented analysis preserves negative, neutral and positive differences. No conclusion favors the proposed system in advance.

## Limitations and completion requirements

The Gemini key is verified in the user terminal; enable Gemini access in the experiment process or run the suite from that terminal. Install the missing LangGraph/Jupyter/statistical dependencies, run the smoke pipeline, inspect actual citations and reviewer outputs, then scale only within account quotas. Execute all baselines, ablations and the judge, generate tables/figures, rerun notebooks in a real Jupyter kernel, and replace this interim document with an interpretation of saved individual results. Human calibration, stronger held-out judging, broader sampling and equal-inference-budget controls would improve validity.

Current scientific limitations include purposive domain sampling, abstract-only evidence, incomplete search recall, same-model judge bias, possible model memorization, unequal inference budgets and proposal-level rather than executed feasibility. Matching a paper ID or excerpt is not semantic verification. A two-seed smoke result would remain a demonstration, not evidence of general superiority.

## Conclusion

The local implementation and offline verification are available. The project's required experimentally evaluated result is **not complete** because this agent shell cannot reach Gemini. Local scholarly retrieval is now working. This status is preserved explicitly rather than substituting mocked findings.
