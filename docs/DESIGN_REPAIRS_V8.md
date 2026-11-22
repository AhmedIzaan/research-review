# Design repairs v8

This amendment addresses interactive trace `13b8da15e4534da66906`. It is an engineering change, not new experimental evidence. Historical results and the IEEE paper package remain unchanged.

## Implemented behavior

- Guarded workflows reject changes confined to references, prior-work comparisons and search queries as literature-only updates. The candidate remains available for inspection and independent evaluation. Always-accept ablations retain their specified behavior.
- Every revision records literal changed fields and before/after values. The safeguard receives this audit and must associate each substantive critique with a concrete change or explicitly leave it unresolved. The UI shows both edits and comparative risk judgments. These judgments remain model-dependent; a field edit is not proof that a criticism was resolved.
- Constructed datasets use a distinct `dataset_construction` dependency category. They require a generator/label-oracle/split pilot, not an existing public release. Generic synthetic construction claims have a conservative fallback classifier. Named existing synthetic benchmarks still require external access checks. Construction claims do not trigger external repository searches.
- Bounded deterministic checks flag pilot acceptance criteria requiring significant effects, and lexical explanation metrics without an explicit semantic/human validation procedure. These findings block candidate acceptance while retaining the original proposal and candidate. Persuasion without a rating procedure receives an unresolved warning.
- Prompts require operational repairs, null-compatible experiments, explicit candidate models and access routes, and a distinction between output-level rule tracking and internal causal faithfulness. Simply naming an embedding metric is insufficient.
- Protocol version is `specialized_review_v8_design_repairs`; CLI default output is `results/design_repairs_v8_smoke` to prevent mixing protocols.

## Test and rerun

```bash
../.venv/bin/python -m pytest -q
node --test tests/trace-ui.test.cjs
../.venv/bin/python scripts/serve.py
```

Restart an existing backend and refresh the browser. Repeat the original topic with dependency verification enabled and guarded refinement selected. A one-round run is enough for an initial test; compare actual methodology and controls, not just ratings. Retained initial proposals can still contain unresolved flaws when revision fails; inspect final dependency checks and the suite status.

For the controlled study, first inspect the budget:

```bash
../.venv/bin/python scripts/run_experiments.py --dry-run
```

Then execute the same command without `--dry-run` in the network-enabled terminal. Use identical seeds/settings across conditions. Do not merge older and newer protocol scores as matched observations.

## Evidence boundary for today's paper

The historical trace changed only references and prior-work comparisons. Independent aggregated novelty/feasibility/importance/grounding were unchanged; clarity declined from 4.5 to 4. This is a diagnostic interactive example, not a controlled efficacy experiment.

Offline regression replay can establish that the new checks detect those recorded errors. It cannot show that Gemini now produces better proposals or that online source resolution succeeds. Report v8 as a post-pilot implementation amendment until a fresh live run is evaluated. Do not replace the pilot's mixed findings with expected improvements.

Limitations: regex checks are bounded and can miss paraphrases or flag legitimate wording; model-family recognition is incomplete. A semantic/human-validation mention is not proof of a valid procedure. Generic or ambiguous models remain unresolved rather than guessed. Official lookup still requires a concrete supported repository identity and working network access. No human ratings or generated-hypothesis executions have been performed by this change.
