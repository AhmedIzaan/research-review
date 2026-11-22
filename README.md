# Literature-Grounded Research Idea Generation Using Specialized Multi-Agent Reviewers

FAST-NUCES Islamabad · Agentic AI final-semester project.

## New protocol: guarded refinement and fairer evaluation

[Design repairs v8](docs/DESIGN_REPAIRS_V8.md) blocks literature-only revisions in guarded runs, separates constructed data from external dataset access, and checks measurement validity and hypothesis-as-prerequisite errors. Exact edits and comparative repair judgments are visible in the trace. Restart the server before a fresh run.

[Dependency coverage v7](docs/DEPENDENCY_COVERAGE_V7.md) adds missed-model recovery, generic-query suppression and explicit precision/control checks based on the latest quantization trace. Restart the server and use a fresh study directory.

[Online source lookup v6](docs/ONLINE_SOURCES_V6.md) now adds Hugging Face metadata/cards and linked GitHub documentation to dependency checks. It is enabled in environment-loaded settings; run the documented no-Gemini connectivity check before testing.

See [dependency verification v5](docs/FACTUAL_VERIFICATION_V5.md) for the latest implementation, source import instructions and limitations. New runs check concrete proposal claims; the default smoke plan is now 147 calls and a full one-round demo is 20 calls before retries. Earlier budgets below describe earlier protocols.

The [comparative safeguard amendment](docs/COMPARATIVE_GUARD_V4.md) addresses premature rejection observed in the Urdu calibration trace. New checks distinguish inherited risks from introduced or worsened blockers. Restart the server before testing.

New runs preserve a falsifiable hypothesis and distinctive mechanism, check candidates for regressions before acceptance, and retain rejected candidates for independent evaluation. There are call-matched generic/replacement controls, a safeguard ablation, a fixed 12-paper stratified seed set, repeated blinded judging, and real human-rating import. The UI exposes the new controls and decisions. **No new empirical improvement is claimed yet; the old results and IEEE paper are unchanged.** See [rerun instructions and limitations](docs/GUARDED_REFINEMENT_V3.md). The CLI now starts with three seeds, one round and five configurations (93 planned calls); use `--dry-run` before a larger study.

## Open the local frontend and backend

From this directory, using the existing parent virtual environment:

```bash
../.venv/bin/python scripts/serve.py
```

Open **http://127.0.0.1:8000**. The app loads your local `.env` on the backend.
Use **Open completed example** to inspect a genuine saved trace without API
calls, or start a live run from a seed paper or topic. The workspace shows the
exact proposal reviewed, individual critiques, evidence, aggregation and revisions.
The literature library, experimental charts, run history and JSON export are included.
A full one-round live run now plans 16 calls before retries: it includes a final
review panel, citation-support audit, revision safeguard and two independent ratings per proposal, all enabled by default. New interactive runs are stored separately in `results/web_runs`.

For a fresh environment, install `requirements-web.txt` for just this app, or
`requirements.txt` for the complete project. See the
[web demonstration guide](docs/WEB_DEMONSTRATION.md) for setup, professor walkthrough,
API endpoints, testing and verification limits. The API and worker have automated
tests. The user has completed a genuine live run through the interface; the latest
methodology changes still need a new live test. Chrome remains unavailable in this restricted shell.
See [the improvements and retest guide](docs/REVIEW_IMPROVEMENTS.md).
The [trace explorer](docs/TRACE_EXPLORER.md) presents stages, reviewer tabs, highlighted
revisions, citation audits and independent scores in a dedicated reader.
Independent judging now uses multiple queries, cited source records and shared evidence
for matched proposals; see [judge literature retrieval](docs/JUDGE_LITERATURE_RETRIEVAL.md).

**Current state: corrected live pilot executed and independently evaluated.**
All twelve final-condition outputs have accepted ratings and all sixteen distinct
judgments passed citation validation. One generic-review run stopped early on a
wrong-role response; its last valid proposal was retained and scored. The two-seed
pilot suggests a novelty–feasibility trade-off, with no significance claim.
See [current findings](docs/RESEARCH_FINDINGS.md). Original live outputs are
preserved under `results/smoke` and corrected outputs under `results/smoke_v2`.
The source-passage citation interface has now run successfully through Gemini.
A later interactive RAG run demonstrated successful role identity validation. The
latest revision further restricts score dimensions and adds final assessments and
claim-support auditing; these changes have software tests and await a fresh live test.

## Method and contribution

We comparatively evaluate feasibility-focused critique, adversarial challenge, and retrieval-backed novelty checking in a bounded literature-grounded refinement workflow. This is an implementation/replication extension. ResearchAgent already includes criterion-specific reviewers and feasibility criteria; InnoEval is particularly close prior work. We do not claim to invent multi-agent reviewing or reproduce published ResearchAgent exactly.

The workflow retrieves related literature, generates one structured initial proposal, collects independent critiques, preserves their disagreements, and revises for at most three rounds. Four specialist roles use the same pretrained model with distinct instructions. The novelty role additionally searches prior art, selects supplied passage IDs, and verifies paper IDs and program-attached exact excerpts, and withholds grounded scoring when evidence is unavailable. No full-paper graph, LLM training, or autonomous scientific experimentation is implemented.

`Workflow` supports LangGraph and a dependency-light Python state machine. `engine='auto'` prefers LangGraph when installed. Reviewers run in separate sequential calls to respect free-tier rate limits; they receive no other reviewer critiques. This is information independence, not independent model weights or concurrent execution.

## Setup

Python 3.11+ (local verification used Python 3.12.15):

```bash
cd agentic_research_review
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
cp -n .env.example .env
```

Edit `.env` locally: set `GEMINI_API_KEY` and retain `GEMINI_MODEL=gemini-3.5-flash-lite`. Never put the key in a notebook or commit it. An existing root `.env` is also supported, with environment variables taking precedence. Core execution uses Pydantic, dotenv and Python's standard-library HTTPS client against Gemini GenerateContent; no SDK is required. Model discovery errors are reported, never silently substituted with another model.

The machine-specific parent `.venv` used for this session references read-only cached dependencies. It is not a portable installation or a substitute for the clean setup above. The optional dependency ranges in `requirements.txt` are not a fully resolved lockfile. After installing in a networked environment, preserve `python -m pip freeze > results/environment-freeze.txt` for the actual study.

## Downloaded corpus

The default retriever now searches **2,114 local scholarly records** with BM25.
Six pinned ACL Anthology XML downloads supplied 2,097 usable abstracts, and 17
additional distinct project/prior-work anchors were imported with provenance.
The original 20 evaluation seeds are unchanged. No scholarly API request is
required during experiments. Source hashes, dates, URLs and processing details
are saved in [the corpus manifest](data/corpus/manifest.json), with limitations
in [the local corpus documentation](docs/LOCAL_CORPUS.md).

Set `RETRIEVAL_BACKEND=local` (the default) and retain the existing Gemini key.
Optional `RETRIEVAL_BACKEND=online` restores Semantic Scholar/arXiv lookup.
The local corpus is a bounded abstract collection, not all prior literature or
full-paper PDFs. Its fingerprint is pinned in experiment settings and caches.

## Run in stages

To run all six configurations, independent judging, tables and plots with progress
output from your network-enabled terminal, use this single command from this
directory (the existing session environment is in the parent folder):

```bash
../.venv/bin/python scripts/run_experiments.py --study results/smoke_v4
```

If you installed a project-local virtual environment, use `.venv/bin/python`
instead. The default is the two-seed, three-round smoke study. The updated runner checks
scholarly retrieval before starting model calls and uses a fresh study directory so
methodology changes cannot be mixed with the completed pilot. For a new study,
failures are recorded in `results/smoke_v4/suite_status.json`; tables and plots go
in `results/smoke_v4/analysis/`. The existing completed pilot remains in `smoke_v2`. It does not claim
Jupyter execution or scientific success just because all stages returned.

This suite is estimated at 138 model calls before retries and early stopping.
Start it outside the restricted agent shell, whose network permission must be
enabled separately. The user's terminal has successfully verified the Gemini key;
local retrieval now works inside this agent shell, while Gemini calls still require network access.

```bash
python -m pytest -q --junitxml=results/pytest.xml
python -m research_review.cli preflight
python -m research_review.cli budget --n 2 --rounds 3
python -m research_review.cli run --n 2 --rounds 3 --study results/smoke_v2
python -m research_review.cli evaluate --study results/smoke_v2
python -m research_review.cli analyze --study results/smoke_v2
```

Preflight checks credentials and searches the configured corpus. The default local mode makes no scholarly network requests; optional online mode queries Semantic Scholar/arXiv. It never prints keys. A missing key causes `run` to exit before making LLM requests. A retrieval outage is recorded as failure, not cached as an empty successful result. Keep a completed cache fixed during a study; `refresh=True` intentionally changes the retrieval snapshot.

To generate ideas from a topic rather than the default seed file:

```bash
python -m research_review.cli retrieve --topic 'retrieval augmented generation calibration' --n 3
python -m research_review.cli run --topic 'retrieval augmented generation calibration' --n 2 --study results/topic_smoke
```

The default smoke study uses ResearchAgent and SciMON as fixed seeds. For a larger study:

```bash
python -m research_review.cli budget --n 20
python -m research_review.cli run --seeds data/seeds.json --n 20 --study results/main
python -m research_review.cli evaluate --study results/main
python -m research_review.cli analyze --study results/main
```

Set `MAX_API_CALLS` explicitly for larger experiments. The default 160-attempt cap applies separately to persisted generation and judge ledgers; retries count. Free-tier access is user-confirmed, not a billing guarantee checked by this software. Requests are spaced 15 seconds apart by default; adjust to your account's limits. No paid search grounding is used. Metadata APIs are separate from Gemini's paid Google Search tool.

A two-seed, three-round six-condition run needs at most **122 generation/review requests + 16 unique-content judge requests = 138**, before retries and early stopping. A 20-seed run needs at most **1,380**. At the configured zero free-tier token rates, estimated token cost is $0; requests remain quota-limited. Planning assumes 6,500 input and 1,400 output tokens per request; actual usage comes from provider metadata. Retry worst-case planning is 3×; never confuse these estimates with observed consumption.

## Experiments and fairness

| Configuration | Feedback per round | Additional novelty search |
|---|---|---|
| One-shot | None | None |
| Generic iterative | One general reviewer | None |
| Full | Novelty, feasibility, clarity/importance, contrarian | Yes |
| No feasibility | Other three specialists | Yes |
| No contrarian | Other three specialists | Yes |
| No novelty retrieval | All four specialists | No; original context retained |

All conditions reuse the exact initial idea within a seed/replicate and hold model, temperature, proposal schema, output limit, practical constraints and round limit fixed. Conditions are shuffled deterministically per seed in the CLI. The main comparison uses unequal **natural** request budgets; it does not identify a pure specialization effect at equal inference cost. Reviewer removals also reduce calls. Record resource differences and avoid causal overclaiming. Repeated replicates are supported by `--replicates`; model outputs are not guaranteed deterministic even at low temperature.

Twenty seed records come from saved primary-source captures of the prior Business Research review. They are a fixed purposive AI/NLP scientific-ideation/review set, with one survey; this is narrow and not a representative NLP benchmark. Selection preceded generated outputs. URLs, authors, years, available DOIs, source paths, hashes and extraction steps are preserved. See [dataset protocol](docs/EXPERIMENT_PROTOCOL.md). `scripts/prepare_dataset.py` can rebuild this import while the original captures remain available.

## Evaluation and artifacts

The judge receives proposal text and evidence from its own query of the frozen local corpus, without configuration, reviewer feedback or round labels. Identical proposals share one judgment. The same-model judge is isolated by prompt/context but remains statistically and epistemically dependent on the generating model. Human calibration remains pending. Novelty, feasibility, clarity, importance and evidence grounding are separate 1–5 ratings with explicit anchors and rationales.

Matching evidence IDs and exact excerpts checks provenance only; it does not prove semantic support, citation correctness, complete prior-art coverage or scientific validity. Judge evidence may be incomplete. Paper text is untrusted data and is never executed.

Study outputs:

- `manifest.json`: fixed dataset and settings fingerprint.
- `initials/`: shared originals, initial-generation time/calls and retrieved context.
- `runs/`: each condition's final idea, all reviews, queries, revision history, stop reason and telemetry.
- `api_audit/`, `judge_api_audit/`: prompt schemas, raw JSON outputs and per-attempt token/cost/error events, without credentials.
- `evaluation/`: individual scores, separate blind mapping, shuffled blank human-rating CSV, raw judgments and evidence.
- `analysis/`: summary/paired/resource tables and five PNG/PDF figures, generated only from actual scores.

Shared initial costs are reported separately, not duplicated across conditions. Generation and judging ledgers are separate. Unknown token/cost fields remain missing and are counted as missing; zero is not assumed to be measured usage. Failures, discarded invalid responses and retries remain in telemetry. Per-round checkpoints survive interrupted calls; completed conditions are reused on resume. A partially completed condition may restart its rounds and consume additional calls; inspect `.partial.json` first. Never mix a changed scientific configuration into an existing study directory.

## Notebooks

1. [Baseline experiments](notebooks/01_Baseline_Experiments.ipynb)
2. [Multi-agent review](notebooks/02_Multi_Agent_Review.ipynb)
3. [Evaluation and ablation](notebooks/03_Evaluation_and_Ablation.ipynb)

They now contain genuine saved first-pilot proposals, reviewer traces, independent ratings and diagnostic findings, with the failures explicitly disclosed. Notebook 3 embeds five actual figures. Ordinary Python cells were executed through the documented fallback; a real Jupyter kernel is still unverified. Default cells inspect `smoke_v2` without API use. Set `RESEARCH_REVIEW_STUDY=smoke` to inspect the archived first pilot. To run notebook experiments, start Jupyter with `RUN_LIVE_EXPERIMENTS=1`; cells stage baselines, full method and ablations in the same smoke study. For controlled randomized ordering, execute the CLI study first, then open the notebooks to inspect it.

With dependencies installed, execute via a real Jupyter kernel:

```python
from pathlib import Path
import nbformat
from nbclient import NotebookClient
for path in sorted(Path('notebooks').glob('*.ipynb')):
    nb = nbformat.read(path, as_version=4)
    NotebookClient(nb, timeout=1200, kernel_name='python3',
                   resources={'metadata': {'path': str(path.parent.resolve())}}).execute()
    nbformat.write(nb, path)
```

This session used `scripts/verify_notebooks.py` to execute trusted Python cells because Jupyter dependencies are unavailable. That fallback verifies ordinary code cells and captures stdout; it does not claim kernel/rich-display verification. Do not run that fallback on untrusted notebooks.

## Research and demonstration documents

[Protocol](docs/EXPERIMENT_PROTOCOL.md) · [Research findings/status](docs/RESEARCH_FINDINGS.md) · [Demonstration and viva](docs/DEMONSTRATION_AND_VIVA.md) · [Verification](docs/VERIFICATION.md).
