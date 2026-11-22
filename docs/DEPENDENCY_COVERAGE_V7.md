# Dependency coverage and experiment checks

This amendment addresses the failures in trace `0be0f4db5ca65dd08f70`. It introduces no extra LLM calls. New runs record `specialized_review_v7_dependency_coverage` and should use a new study directory.

## Implemented changes

- Versioned model-family names and qualified identifiers are recovered from proposal text by a bounded deterministic scanner and provided to the extraction agent. Omitted model-access claims are appended for verification. The scanner covers Llama, Qwen, Mistral, Gemma, Phi and DeepSeek naming patterns; it is not a universal named-entity recognizer. The LLM extraction path remains responsible for other names and datasets.
- Generic concepts such as “Logits or token-level masks”, “Hugging Face runtime” and “Public JSON extraction datasets” produce `needs_specific_entity`, without an HTTP search. Entity-cap overflow is reported as `budget_skipped`. Neither status implies the resource does not exist.
- Supported model capability/access claims require entity-specific evidence. A generic paper describing the need for logits no longer verifies a particular implementation. This lexical specificity filter is a conservative screen, not a semantic truth guarantee.
- Experiment checks calculate the weight-storage floor when an explicit parameter count, GPU capacity and FP16/BF16 comparison are present. Eight billion resident parameters at two bytes each require about 16 GB decimal before KV cache and activations. A lower GPU capacity requires a repaired reference plan. An explicit offload/sharding plan is treated as requiring verification, not automatically impossible.
- A quantization minimum test mentioning only a 4-bit model without a higher-precision reference receives a missing-control flag. These are transparent heuristics, not a full experiment-design theorem prover.
- Repair-required findings are passed to revision and block candidate acceptance until resolved. An identifiable model cannot simply disappear without a replacement. The selected final proposal can still be the unresolved incumbent; final design failures are explicitly reflected in job/study completion status and displayed in the trace.
- Prompts now distinguish alternative scientific hypotheses from implementation acceptance criteria, demand feasible references for every precision, discourage score gains based on citation insertion, and require concrete controls and semantic ground truth.

## Interpretation

A feasibility improvement must correspond to an actual implementation change, not removing the model name. A pilot need not obtain the desired scientific result to succeed. Adding a citation does not prove a dataset, runtime capability or memory claim.

Remaining limits include incomplete name recognition, abstract-only scholarly coverage, repository identity ambiguity, LLM interpretation errors, and unexecuted hardware assumptions. Resource estimates assume the stated parameter count and precision refer to the planned resident weights; mixed experiments and nonstandard architectures may require human interpretation. Independent judging remains separate and can disagree. No empirical quality gain is claimed before new live experiments.

## Test again

Restart the server:

```bash
../.venv/bin/python scripts/serve.py
```

Repeat the quantization topic with the same constraints. Inspect **Candidate dependency checks** for recovered model names, actual lookup status, precision-memory findings and reference-control requirements. Old traces retain the old verdicts.

For controlled experiments use a fresh path:

```bash
../.venv/bin/python scripts/run_experiments.py --study results/dependency_coverage_v7_smoke --dry-run
../.venv/bin/python scripts/run_experiments.py --study results/dependency_coverage_v7_smoke
```

Regression tests exercise the exported failure, generic-query suppression, missed-model recovery, entity-specific evidence, infeasible reference planning and feasible/offloaded alternatives. Synthetic tests are software evidence only. Existing paper source records and original results must remain separate from the amended protocol.
