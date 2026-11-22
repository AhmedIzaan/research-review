# Verification record

This directory was created separately from the user's source documents and existing Business Research work. Source imports are read-only. The proposal available on disk lacks the `(1)` suffix in the requested filename; the available `research proposal_business research.pdf` was inspected alongside `context.md`, `literature_review_Agentic.docx` and the completed Business Research report.

## Local corpus update — 8 November 2026

Six official XML collections downloaded through connected GitHub tools;
2,122 raw paper records and 2,097 usable abstracts verified by source hash.
With 17 additional distinct anchors, local BM25 search now indexes 2,114 records.
Retrieval preflight succeeds without network. Tests cover corpus parsing,
fingerprints, cache invalidation and local novelty-review integration.
The Gemini key was verified in the normal user terminal. This agent shell still
cannot make outbound Gemini calls; that restriction is separate from the now
working literature component.

## First live pilot and citation correction

The user terminal completed all twelve configuration runs and independent judging.
The pilot has thirteen reviewer citation failures and five rejected unique
judgments, leaving seven of twelve final-condition rows with accepted scores.
Original data are retained. The current passage-ID correction passes 57 tests
(one LangGraph test skipped) and an offline provenance check across 98 actual
request contexts / 5,037 exact source passages; no new model judgments were
created by that check. Its live Gemini rerun remains pending.

The three notebooks now contain actual pilot outputs, with fourteen ordinary
Python cells verified by the fallback runner and five real PNG figure attachments.
Real Jupyter-kernel verification is still pending. See the current research
findings and citation-protocol correction documents for the diagnosis.

## Exercised

- Python 3.12.15 with existing read-only cached packages: Pydantic 2.12.5, python-dotenv 1.2.1, Pytest 9.0.3, Pandas 3.0.6, Matplotlib 3.11.2.
- Software tests for score contracts, reviewer-specific required fields, evidence ID/excerpt checks, real-record import, metadata caching and failed retrieval, arXiv parsing, shared initials, six condition transitions, stopping limits, early stopping, reviewer/revision failure, anti-fixture evaluation guards, persistence and resume, retry/cost telemetry and API caps.
- Three notebooks' ordinary Python cells using the documented trusted-cell fallback runner. Configuration and real-source dataset outputs are saved; live experiment cells remain disabled. `results/notebook_verification.json` records the scope.
- Actual preflight requests to Semantic Scholar and arXiv failed in the runtime. `results/preflight.json` retains failure statuses. A live-run command correctly refused to run without a key.
- Browser verification of ResearchAgent and SciMON primary source pages succeeded separately. This is source verification, not Python retrieval validation.

`results/pytest.xml` is the authoritative latest test result. Synthetic tests write only into temporary Pytest directories. They never populate experimental scores or evidence of scientific improvement.

## Not exercised

- LangGraph execution: unavailable package; conditional engine test skipped.
- Gemini project Idea/Review/Judgment schemas and study quota: not yet live-verified. A small structured-output connection check succeeded in the user terminal.
- Successful live Semantic Scholar/arXiv retrieval: runtime DNS/network unavailable.
- Corrected passage-ID protocol through live Gemini: pending. The earlier verbatim-quotation pilot did execute generation, specialist review, revisions and independent judgments, with failures preserved.
- Scientific efficacy on a reliable complete sample: pending. Five actual pilot figures and individual ratings exist, with missingness and small-sample limitations.
- Real Jupyter kernel execution and rich output: nbformat/nbclient/ipykernel unavailable.
- SciPy/Seaborn paths: unavailable in the Python 3.12 test environment. The host Python has separate scientific packages; environments were not conflated.
- A fully clean network installation: PyPI resolution failed. Dependency ranges for missing packages remain to be resolved and locked in the actual experiment environment.

## Resume checklist

1. Use the network-enabled normal terminal for Gemini calls. Local scholarly retrieval works without network; missing optional packages still require a network-enabled install.
2. Retain the already-configured `.env` and user-verified `gemini-3.5-flash-lite` key; local retrieval is the default.
3. Install dependencies in a clean environment and preserve its freeze.
4. Rerun tests including the LangGraph path, then run preflight.
5. Run one focused full workflow and inspect evidence; then run the complete two-seed six-condition smoke experiment and separate judge.
6. Fix observed live integration problems before scaling. Do not interpret a missing configuration or stopped run as a completed comparison.
7. Generate real tables/figures, execute the notebooks with Jupyter, and write the findings from saved individual scores. Collect human ratings if feasible.


## Corrected pilot completed

The `smoke_v2` run completed on 8 November 2026 with all twelve final-condition
ratings available, sixteen accepted unique judgments, and no quotation-validation
failures. One generic reviewer returned the wrong role in round two and its
condition stopped early. That failure remains recorded. Future wire schemas now
restrict each reviewer to its requested role so wrong-role responses are rejected
during structured-output validation and enter the existing retry path. This
additional restriction has unit tests but has not yet been live-verified.

Current results show higher mean feasibility, clarity and grounding with the
full panel, alongside lower novelty than one-shot, across only two seeds. The
current findings document and notebooks use `smoke_v2`; earlier pilot artifacts
remain separate. No statistical significance or human agreement is claimed.
