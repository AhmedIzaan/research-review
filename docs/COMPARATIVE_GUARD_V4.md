# Comparative refinement amendment

The live Urdu calibration trace `c38e53f68a543cfcc090` completed 16 successful calls in 19 attempts, with three recovered HTTP 503 failures. Both initial and rejected candidate received repeated scores of 3/4/4/4/4 for novelty/feasibility/clarity/importance/grounding. Both used the same 22-paper context. The guard described improvements but rejected the candidate for risks already present in the incumbent. These observations do not establish that the candidate was better.

New runs use `specialized_review_v4_comparative`. Every new safeguard output must compare each important risk's incumbent state, candidate state, change, severity, reasoning and next check. Introduced or worsened blocking risks veto a candidate; inherited or mitigated risks alone do not. Explicit metric regressions, uncertain mechanism preservation, uncertain novelty/feasibility, and no substantive progress still prevent acceptance. Acceptance remains provisional. Historical checks without comparative evidence retain their old interpretation.

The number of calls and bounded stopping rules are unchanged. A rejected revision still stops; the change addresses inappropriate rejection rather than forcing additional rounds. Both candidates remain independently evaluated. Comparative risk judgments can themselves be wrong and need evaluation against independent outcomes.

Generation/refinement now request concrete model and dataset candidates, probability access, resource pilots, exact confidence aggregation, disjoint calibration/test splits, and operational controls. Reviewer prompts discourage unsupported hardware/sample-size assertions, automatic demands for wider scope, and causal overclaims. Independent judge prompts check the same practical omissions without seeing reviewer decisions or scores. Citation instructions distinguish background relevance from support for the specific task, language and transfer direction.

Restart `../.venv/bin/python scripts/serve.py` and repeat Q06 with the same constraints to inspect the changes. Use a fresh controlled study directory, for example:

```bash
../.venv/bin/python scripts/run_experiments.py --study results/comparative_v4_smoke --dry-run
../.venv/bin/python scripts/run_experiments.py --study results/comparative_v4_smoke
```

A fresh interactive run generates a fresh initial idea; it is not a paired causal comparison with the earlier trace. The controlled runner shares initials among its conditions. Prompt and judge changes mean old/new scores must be reported as separate protocols. No new empirical improvement, live run, or human evaluation is claimed by this amendment. Earlier results and the paper remain historical evidence.
