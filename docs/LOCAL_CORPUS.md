# Local literature retrieval

The user authorized replacing mandatory live scholarly API lookup with a
downloaded local corpus on 8 November 2026. Gemini remains the model API.

## Actual downloaded data

Six official ACL Anthology XML collections were downloaded through connected
GitHub tools at commit `3b320071c97927135c7e86d84b6d626b4943dc4a`.
The raw XML has **2,122 paper elements**. After parsing nested XML formatting,
**2,097 have a usable title and abstract**; the remaining 25 are listed in
`data/corpus/manifest.json`. Seventeen additional, distinct project/prior-work
anchors are imported from existing source captures, giving **2,114 indexed
records**. Four evaluation seeds were already present in the downloaded data
and were not duplicated. InnoEval is an extra prior-work anchor, not a new
evaluation seed.

The corpus contains publication metadata and abstracts, not full PDFs. Raw source
hashes match Git blob hashes; derived records preserve authors and source links.
All exclusions and import provenance are saved. Selection did not depend on any
generated idea or outcome. The original 20 evaluation seeds are unchanged.

## Search method

The default `RETRIEVAL_BACKEND=local` builds a lexical BM25 index using Python's
standard library. Title terms receive three times their abstract frequency.
Tokenization lowercases ASCII word tokens and removes a fixed stopword set.
Parameters: `k1=1.5`, `b=0.75`. Query terms and tie breaks are sorted for
deterministic rankings. No embedding model, API, LLM fine-tuning or training is
needed. Nonmatching queries return an empty result rather than arbitrary papers.

Initial generation retrieves related records from this pool. Every grounded
novelty review searches using the current idea's queries. The independent judge
performs its own query without seeing reviewer scores or configuration labels,
using the same frozen corpus. This provides context isolation, not independent
external evidence coverage. The no-novelty-retrieval ablation retains initial
literature but disables the additional idea-specific novelty search.

Every local query records the corpus fingerprint in its provider identifier.
Search caches include this fingerprint, query and limit, preventing reuse across
changed corpora. Study settings and manifests bind the snapshot fingerprint;
mixing a changed corpus into an existing study is rejected. Optional online
Semantic Scholar/arXiv lookup remains available via `RETRIEVAL_BACKEND=online`.

## Verified behavior

`results/local_retrieval_checks.json` records actual local search outputs.
Known-title checks retrieve ResearchAgent and SciMON first; a topical query
retrieves InfAL and related novelty/review literature. These are sanity checks,
not measured retrieval recall or proof of scientific benefit.

Automated tests cover source parsing and hash checks, missing-abstract exclusions,
snapshot-aware caching, no-hit queries, factory selection, and integration of
local search into the novelty reviewer. Synthetic test fixtures remain in
temporary test directories and are not experimental findings.

## Run

From `agentic_research_review`, using the normal terminal that passed the
Gemini connection test:

```bash
../.venv/bin/python scripts/run_experiments.py
```

This needs internet only for Gemini, not scholarly retrieval. It runs the fixed
two-seed, three-round six-configuration smoke study, separate judgments and
analysis. The planned budget is at most 138 model calls before retries and early
stopping. The single command reads the existing `.env`; do not paste the key.

To rebuild the processed corpus entirely offline:

```bash
../.venv/bin/python scripts/build_local_corpus.py
```

Results are saved under `results/smoke/`, including corpus fingerprints,
independent scores, reviewer evidence, raw model responses and failures. A small
smoke study supports demonstration and descriptive comparisons, not a claim of
statistical superiority. Jupyter kernel execution remains a separate check.

## Limitations

The base snapshot emphasizes selected ACL/NAACL and SDP/SIGDIAL collections in
2024–2025. A few 2026 anchors do not make coverage current or comprehensive.
BM25 misses paraphrased mechanisms and cross-domain precedents. Abstracts omit
implementation details, negative results and resource information. Matching a
paper ID or excerpt checks provenance rather than semantic support. Absence of
overlap means only no match in the searched pool. Evaluation and claims must
explicitly state these limits.
