# Testable research questions

These questions are inputs for testing the research-idea generation and review system. They are proposed investigations, not verified novel contributions or completed experiments. Literature retrieval and review should establish what overlaps with existing work.

## How to use this file

1. Open **Start review**, select **Research topic**, and paste the question in a blockquote below.
2. Keep the revision safeguard, final assessment, citation audit, and independent evaluation enabled. Start with one round and two judge ratings.
3. Use the same practical constraints: six weeks, public lawful data, one 12 GB GPU or available API access, and no LLM training or fine-tuning. Auxiliary classifiers are optional and must be identified separately from LLM training.
4. Inspect the initial hypothesis, distinctive mechanism, closest prior work, reviewer critiques, candidate changes, selection decision, and independent scores. An accepted revision is not proof of improvement.
5. Export the trace and record the question ID. Use two or three rounds on a prespecified subset to investigate progression and stopping.

**Start with Q01, Q05, and Q09** for three different areas. Q13–Q16 are deliberately challenging controls. They should not be counted as ordinary candidate contributions when summarizing the main topic set.

The implementation sketches below help you assess whether the generated proposal is concrete. They do not establish dataset availability, expected performance, or scientific originality. Search terms help inspect the local corpus; poor search coverage must remain an explicit limitation.

## Main questions

### Q01 — Separating useful evidence from distracting evidence

> At a fixed context-token budget, does selecting retrieved passages for complementary answer evidence improve question-answering accuracy over relevance-only selection, and when does diversity instead introduce distracting evidence?

- **Small experiment:** Use questions with reference answers and a fixed candidate passage pool. Keep the generator and retrieval results fixed across selectors.
- **Comparisons:** Relevance ranking, diversity-based selection, and the proposed evidence-complementarity selector.
- **Measurements:** Answer accuracy, answer support, relevant evidence coverage, context tokens, and latency. Include questions where one passage is sufficient.
- **Review focus:** Define complementarity without consulting test answers. Check whether an existing selection method already implements the proposed mechanism.
- **Search terms:** passage selection, retrieval diversity, evidence coverage, question answering.

### Q02 — Repeated evidence versus independent corroboration

> Do language models become more confident in an incorrect answer when the same supporting passage is duplicated, compared with receiving distinct corroborating passages, after controlling context length and passage order?

- **Small experiment:** Construct matched contexts with duplicates, distinct support, and irrelevant length-matched padding. Manually check the evidence labels on a small subset.
- **Comparisons:** Duplicate evidence, distinct corroboration, and single-source evidence.
- **Measurements:** Answer accuracy, sensitivity to duplication count, elicited confidence calibration, and robustness across passage orders. Treat verbal confidence as an imperfect measure.
- **Review focus:** Separate repetition effects from context length, source count, lexical overlap, and position. A null effect is informative.
- **Search terms:** evidence redundancy, source diversity, confidence calibration, context bias.

### Q03 — Contradiction-aware abstention

> Can a retrieval-based question-answering system distinguish conflicting evidence from insufficient evidence well enough to improve selective answer accuracy without unnecessarily refusing answerable questions?

- **Small experiment:** Build separately labeled answerable, insufficient-evidence, and conflicting-evidence cases. Keep retrieval and the answer model fixed.
- **Comparisons:** Always answer, confidence-threshold abstention, and a contradiction-aware decision rule.
- **Measurements:** Risk–coverage curves, answer accuracy at matched coverage, false abstention, and classification errors between contradiction and insufficiency.
- **Review focus:** Require held-out threshold calibration and a simpler contradiction baseline. Check overlap with existing answerability and abstention methods.
- **Search terms:** contradictory evidence, answerability, selective prediction, abstention.

### Q04 — Citation correctness under source reordering

> How much do passage order and citation-label changes affect citation correctness in source-grounded answers when passage content remains identical, and can a separate citation-verification step reduce these errors?

- **Small experiment:** Permute a fixed set of passages and relabel source identifiers consistently. Verify that each variant preserves the same facts.
- **Comparisons:** Direct answer generation, a second generation without a verification rubric, and explicit citation verification with a comparable call budget.
- **Measurements:** Citation precision, claim coverage, answer accuracy, variation across permutations, and additional calls.
- **Review focus:** Distinguish correct source formatting from actual support for a claim. Check whether source identifiers themselves create artifacts.
- **Search terms:** citation attribution, grounded generation, source order, citation verification.

### Q05 — Meaning-preserving variation in Roman Urdu

> How sensitive are pretrained language models to meaning-preserving Roman Urdu spelling variation in sentiment classification, and does normalization improve robustness without changing sentiment-bearing expressions?

- **Small experiment:** Begin with a public dataset whose access and license are verified. Have proficient speakers validate spelling variants and a small set of normalization outputs.
- **Comparisons:** Original input, a simple deterministic normalization rule, and model-assisted normalization. Use the same classifier prompt.
- **Measurements:** Macro-F1, prediction consistency across variants, normalization meaning errors, and API usage.
- **Review focus:** Roman Urdu resources and human validation may be limiting factors. Do not assume a generated spelling variant preserves meaning.
- **Search terms:** Roman Urdu, transliteration, spelling variation, sentiment classification, normalization.

### Q06 — Cross-language transfer of abstention thresholds

> Does an abstention threshold calibrated on English factual question answering remain reliable on translated Urdu questions, and can a small separate Urdu calibration set reduce the resulting coverage and accuracy gap?

- **Small experiment:** Use matched questions with checked translations and disjoint calibration/test splits. Verify that answerability survives translation.
- **Comparisons:** English-calibrated threshold, target-language-calibrated threshold, and always-answer behavior.
- **Measurements:** Selective accuracy at matched coverage, false abstention, calibration error, and translation-related failures.
- **Review focus:** This is a threshold-calibration experiment, not LLM fine-tuning. Distinguish language effects from translation quality and answer leakage.
- **Search terms:** multilingual calibration, cross-lingual transfer, selective prediction, Urdu question answering.

### Q07 — Few-shot example order and label imbalance

> How do few-shot example order and class imbalance affect pretrained language-model classification, and does balancing example labels improve worst-order performance at a fixed prompt length?

- **Small experiment:** Use a public classification dataset with a held-out test set. Sample several example sets and prespecified orders.
- **Comparisons:** Random examples, label-balanced examples, and a fixed ordering rule. Match the number of examples and approximate token budget.
- **Measurements:** Macro-F1, per-class recall, worst-order performance, variance across orders, and prompt tokens.
- **Review focus:** Ordering and demonstration selection have substantial potential prior-art overlap. Ask the novelty reviewer for a precise remaining question rather than a broad novelty claim.
- **Search terms:** in-context learning, demonstration order, label bias, few-shot classification.

### Q08 — Quantization and structured-output reliability

> Does model quantization change schema-valid JSON generation more than task-answer accuracy, and can constrained decoding recover format reliability without masking semantic errors?

- **Small experiment:** Compare accessible checkpoints of the same small open model under matched prompts and decoding settings. First measure memory and runtime on the available hardware.
- **Comparisons:** A higher-precision reference that fits, a quantized variant, and constrained versus unconstrained decoding where supported.
- **Measurements:** Schema validity, field-level correctness, task accuracy, memory, and latency. Report formatting and semantic errors separately.
- **Review focus:** This question requires local model access and compatible decoding tools; an API-only system may not expose precision settings. A smaller model is a fallback, not proof of equivalent behavior.
- **Search terms:** quantization, structured generation, constrained decoding, JSON reliability.

### Q09 — Explanations that survive counterfactual tests

> Do language-model explanations for rule-based classification track the rules that determine the answer, or can explanations remain persuasive when a minimal rule change should reverse the prediction?

- **Small experiment:** Construct a small rule-governed classification task with an executable reference solver. Make paired examples differing in one decisive rule or fact.
- **Comparisons:** Direct prediction, explanation-first prediction, and a structured rule-checking prompt.
- **Measurements:** Prediction accuracy, correct counterfactual flips, explanation–answer consistency, and invalid claimed rule applications.
- **Review focus:** Explain how the task avoids trivial lexical cues. Persuasiveness is not an explanation-faithfulness measure, and a correct flip alone does not establish internal reasoning faithfulness.
- **Search terms:** logical reasoning, counterfactual consistency, explanation faithfulness, rule reasoning.

### Q10 — Decomposition versus a matched inference budget

> Does decomposing multi-step reasoning questions into subquestions improve final-answer accuracy over repeated direct attempts with the same approximate inference-token budget, and which subquestion errors propagate to the final answer?

- **Small experiment:** Select questions with verifiable answers and inspect a sample of intermediate steps. Prespecify a budget and the rule for combining direct attempts.
- **Comparisons:** One direct attempt, repeated direct attempts, and decomposition with matched approximate total tokens.
- **Measurements:** Final accuracy, intermediate error rates, error propagation, total tokens, and latency.
- **Review focus:** Extra calls or longer reasoning alone may explain gains. Distinguish a new mechanism from an established decomposition technique.
- **Search terms:** question decomposition, multi-step reasoning, inference budget, error propagation.

### Q11 — Judges that favor longer proposals

> Do LLM judges assign different research-proposal quality scores to concise and expanded versions containing the same substantive claims, and does requiring evidence-linked rubric rationales reduce this sensitivity?

- **Small experiment:** Create checked concise/expanded pairs that preserve the same methods, assumptions, and claims. Randomize presentation order and hide version labels.
- **Comparisons:** A general quality prompt and an evidence-linked rubric prompt, with repeated independent ratings.
- **Measurements:** Paired differences in novelty, feasibility, clarity, and importance; rating spread; and agreement with blinded human ratings where available.
- **Review focus:** Expansion may introduce real clarity changes. Human equivalence checks are necessary before interpreting score differences as verbosity bias.
- **Search terms:** LLM judge bias, verbosity bias, rubric evaluation, reviewer reliability.

### Q12 — Reviewer disagreement as a predictor of revision risk

> Does disagreement between independent research-idea reviewers predict revisions that independent judges later rate worse, after accounting for initial proposal quality and the number of review calls?

- **Small experiment:** Use a prespecified collection of proposal traces. Define disagreement before examining outcomes and retain rejected candidates as well as accepted revisions.
- **Comparisons:** Disagreement measures against simple predictors such as initial judged quality and critique count.
- **Measurements:** Association with candidate-minus-incumbent score changes, uncertainty intervals where justified, and prediction error under seed-level held-out evaluation.
- **Review focus:** This is observational: disagreement does not establish the cause of a bad revision. Avoid treating repeated versions of one seed as independent samples or tuning on the final test traces.
- **Search terms:** reviewer disagreement, scientific reviewing, multi-agent evaluation, revision quality.

## Deliberate stress tests

Keep these separate from the main questions. Their purpose is to expose system weaknesses, including unsupported originality claims and inadequate scope reduction. They do not have a predetermined score or required reviewer verdict.

### Q13 — Familiar technique presented as a new contribution

> Would asking a pretrained language model to solve a reasoning problem through intermediate steps improve accuracy over asking for only the final answer, and is this alone a sufficiently original research contribution?

- **Purpose:** Test whether literature-grounded novelty review identifies relevant existing techniques and distinguishes reproducing a useful baseline from making an original contribution.
- **What to inspect:** Actual overlapping papers and passages, qualified novelty criticism, and whether any proposed pivot adds a specific falsifiable distinction.
- **Search terms:** chain of thought, intermediate reasoning, reasoning prompting.

### Q14 — Deliberately excessive scope

> Can a six-week student project use one 12 GB GPU and public data to evaluate factual reliability across 100 languages, 20 large language models, and 50 scientific domains without training an LLM, while also obtaining expert human judgments for every output?

- **Purpose:** Test feasibility review, prioritization, and the ability to propose a smaller defensible experiment.
- **What to inspect:** Explicit data, compute, annotation and time assumptions. Scope reduction should retain a meaningful research question rather than merely changing the title.
- **Search terms:** multilingual evaluation, factuality benchmarks, annotation cost, evaluation resources.

### Q15 — No improvement is plausible

> When every retrieved passage already contains the same sufficient answer evidence, does an additional evidence-selection agent improve answer accuracy over passing the top-ranked passage directly, after controlling generation settings and measuring added latency and calls?

- **Purpose:** Test whether reviewers can recognize a condition where another agent may offer little benefit.
- **What to inspect:** A direct baseline, an explicit null hypothesis, verification that contexts are equally sufficient, and willingness to retain a negative result.
- **Search terms:** evidence sufficiency, retrieval selection, agent overhead, question answering.

### Q16 — Unavailable labels and circular evaluation

> Can a model predict whether its own newly generated research ideas will achieve real scientific impact using only its immediate self-ratings, without external outcomes, historical impact labels, independent judges, or human evaluation?

- **Purpose:** Test whether the panel identifies an unobservable outcome and circular validation.
- **What to inspect:** A clear distinction between predicting scientific impact and predicting a proxy score. Any revised proposal must state the narrower outcome it can actually measure.
- **Search terms:** scientific impact prediction, self-evaluation, evaluator bias, proxy validity.

## What to record after each test

Use this blank log in a separate file or spreadsheet. Record failures and unchanged proposals as well as successful runs.

| Question ID | Trace ID | Configuration | Round limit | Generator / judge models | Initial → final N / F / C / I / G | Accepted / rejected candidates | Main literature overlap | Calls / tokens | Notes |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |

N = novelty; F = feasibility; C = clarity; I = importance; G = evidence grounding. Use independent evaluation scores, not the reviewers' own feedback scores. Mark missing scores as missing.

For systematic evaluation, choose the question subset and settings before running, retain every trace, and report the selection procedure. Separate interactive runs can generate different initial ideas even when the topic text matches; they are demonstrations, not automatically controlled comparisons. The controlled study runner shares initial proposals across conditions and uses the fixed paper dataset described in [the protocol amendment](docs/GUARDED_REFINEMENT_V3.md). Comparing topic-based conditions with shared initials requires extending that runner; the frontend does not provide that control by itself.
