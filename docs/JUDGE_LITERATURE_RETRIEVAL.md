# Literature retrieval for the independent judge

The live run `fff8592ef95a73dda616` exposed an evaluation weakness: the novelty reviewer found close prior work through several searches, but the judge used only the first broad search query. Its evidence omitted Transform Retrieval (`2025.naacl-short.50`) and the related NLI work (`2025.sdp-1.34`). Reviewer novelty scores and independent ratings therefore rested on uneven source coverage.

The updated evaluation builds a bounded literature context before judging:

1. Search all supplied queries for each proposal (up to three).
2. Add a query from the proposal's title and methodology to cover the mechanism.
3. Resolve the proposal's `references` and `prior_work_comparison` IDs against the pinned corpus, with original generator literature and search results as fallbacks. No reviewer feedback or scores are inspected.
4. Combine evidence across evaluated proposals for the same seed and replicate. The initial idea, intermediate revisions and comparison configurations receive the same selected source set. This is a retrospective matched evaluation, with each proposal still judged separately and condition labels withheld.
5. Include cited/compared sources first, then interleave query hits to avoid letting the first broad query dominate. Deduplicate paper IDs and cap the prompt at 24 source records. Missing citations, citations excluded by the cap, search failures and omitted-hit counts are explicitly recorded.
6. Supply verified source passages through the existing citation-selection protocol. The judge must distinguish the proposal's interpretation of prior work from what the source passages actually establish.

`judgments/*.json` now records `literature_context`, containing queries, selected papers, coverage limitations and a fingerprint. The web interface shows this under **Independent rubric judgments → Judge rationale & literature → Inspect judge queries and source papers**. Reviewer opinions and condition labels are still excluded from judge prompts.

No extra Gemini calls are added: a full one-round run with all default checks still plans 13 calls before retries. Default local corpus searches need no scholarly API calls. Larger evidence contexts consume more input tokens; actual usage remains recorded in each trace. The 24-paper cap limits prompt growth, but it is not exhaustive literature coverage.

Evaluation caches include the retrieval protocol and selected-evidence fingerprint. Changed evidence/settings require a fresh evaluation directory before any existing keys, scores or judgments are rewritten. New controlled studies default to `results/smoke_v4`; completed older studies remain intact. Interactive runs already use unique job directories.

To test, restart `scripts/serve.py`, hard-refresh the browser, and rerun the same topic with independent evaluation enabled. Earlier scores remain unchanged. An offline regression using the actual exported proposals confirms that the new evidence selection includes both previously missed close matches. New LLM ratings require a new live run; no score improvement is assumed. Bounded abstract retrieval, lexical matching and same-model judge bias remain limitations.
