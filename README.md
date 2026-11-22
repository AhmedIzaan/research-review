# Literature-Grounded Research Idea Generation Using Specialized Multi-Agent Reviewers

FAST-NUCES Islamabad · Agentic AI final-semester project.

Research Review Studio turns an AI/NLP topic or seed paper into a structured research proposal. Four reviewers examine the proposal, the generator drafts a revision from their feedback, and a safeguard decides whether to retain it. The app shows the evidence, critiques, changes, and evaluation scores so you can see how the proposal developed. The workflow designs experiments for researchers to carry out.

## Start the project

You need Git, Python 3.11 or later (3.12 recommended), and a browser. Clone the repository from GitHub and open a terminal in the folder containing this README.

Create and activate a virtual environment:

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

```powershell
# Windows PowerShell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the web app and start it:

```bash
python -m pip install -r requirements-web.txt
python scripts/serve.py
```

Open **http://127.0.0.1:8000** and click **Open completed example**. You can browse saved results and search the local corpus with no Gemini key. Keep the terminal open while using the app. Press **Ctrl+C** to stop it. If port 8000 is occupied, run `python scripts/serve.py --port 8001` and open **http://127.0.0.1:8001**.

### Enable live runs

Create a plain-text file named `.env` beside this README. Both `.env` and `.env.example` are ignored by Git, so each teammate creates their own local file. Replace the placeholder with a Gemini API key you are authorized to use.

```dotenv
GEMINI_API_KEY=replace_with_your_key
GEMINI_MODEL=gemini-3.5-flash-lite
RETRIEVAL_BACKEND=local
```

The model ID above is the one used in our saved runs. Use a model ID available to your account if it differs. Keep the key in the local file or an environment variable. To check access, run `python scripts/check_gemini.py`. It makes one small Gemini request and reports success or an error without printing the key. Restart the server after editing `.env`.

In the workspace, choose **Seed paper** to start from an existing paper, or **Research topic** to search from your own question. For a first run, pick **Specialized panel · full system** and **1 round · quick test**. Keep dependency verification and guarded refinement enabled. The form shows the request budget before you launch. Live model calls need an internet connection and use your account's quota. After completion, inspect the initial idea, round feedback, candidate changes, and final proposal. Use History to reopen the run or export its JSON. [Demo walkthrough](docs/WEB_DEMONSTRATION.md) · [Example topics](testable_research_questions.md)

## How the system works

1. **Retrieve literature.** The default BM25 search ranks titles and abstracts in a pinned collection of 2,114 scholarly records. The relevant papers provide context for the generator. A seed paper is a starting input, such as ResearchAgent or SciMON. It is distinct from the software configuration that processes it.
2. **Generate a proposal.** Gemini returns a structured initial idea with the problem, gap, method, expected contribution, experimental setup, evaluation plan, and feasibility assumptions. The initial version is saved.
3. **Review the same draft from four perspectives.** The novelty reviewer searches for overlapping methods and cites retrieved passages. The feasibility reviewer checks data, resources, and experimental practicality. The clarity and importance reviewer asks whether the problem and method are specific and worthwhile. The contrarian reviewer challenges the main assumptions and looks for alternative explanations. Each sees the same draft without the other reviewers' responses. They use distinct prompts with the same underlying model.
4. **Revise and decide.** The system preserves disagreements and sends the feedback to the revision agent. Guarded mode records what changed and can reject candidates that introduce regressions or only update the bibliography. Optional dependency verification distinguishes existing resources from plans that need validation, such as generating a dataset or measuring memory use. The retained proposal and rejected candidates remain visible. The loop stops after at most three rounds and can stop earlier.
5. **Evaluate independently of refinement.** A separately prompted judge sees proposals, constraints, and literature evidence with the reviewer feedback and condition labels withheld. It scores novelty, feasibility, clarity, importance, and evidence grounding on separate 1–5 scales. The current protocol shares a capped literature context across comparable versions and records repeated ratings. Timing, API attempts, tokens where available, and failures are logged alongside the quality scores.

[ResearchAgent](https://aclanthology.org/2025.naacl-long.342/) inspired the review and revision loop. Our study tests a four-role panel and proposal-specific novelty search using a local abstract corpus. The generic-review baseline is an in-project approximation of iterative review. Literature checks help inspect overlap within the sources retrieved, and dependency checks can leave claims unresolved. [Corpus and provenance](docs/LOCAL_CORPUS.md) · [Judge retrieval](docs/JUDGE_LITERATURE_RETRIEVAL.md) · [Current refinement protocol](docs/DESIGN_REPAIRS_V8.md)

## Experiments and results

| Condition | What it tests |
|---|---|
| `one_shot` | The original proposal with zero review rounds |
| `generic` | Iterative revision with one general reviewer |
| `full` | Iterative revision with all four specialists and extra novelty search |
| `no_feasibility` | The panel with the feasibility reviewer removed |
| `no_contrarian` | The panel with the contrarian reviewer removed |
| `no_novelty_retrieval` | The panel with extra novelty searches disabled, retaining the initial literature context |

Within each seed and replicate, the conditions start from the same initial proposal and use the same model settings and project constraints. The main comparison uses the natural call count of each configuration. Removing reviewers also reduces calls, so the pilot cannot isolate role specialization from inference cost. Additional controls include `generic_matched` (four general reviewers) and `full_unguarded` (the full panel without the revision safeguard).

The saved controlled pilot in `results/smoke_v2/` used two seeds and up to three review rounds. Relative to one-shot, the full panel's mean feasibility, clarity, and evidence grounding each rose by **0.5 points**, novelty fell by **0.5**, and importance stayed level. One generic run ended early and its last valid proposal was scored. These are descriptive findings from a small sample with a same-model judge. The separate [v8 interactive trace](research-review-9a20994a1b09f4325e70.json) illustrates concrete design revisions under the newer protocol. It is a single case with two ratings per version. [Pilot findings](docs/RESEARCH_FINDINGS.md)

### Run a controlled comparison

Install the full dependencies in the activated environment:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

Start with a small comparison and inspect its budget first:

```bash
python scripts/run_experiments.py --study results/team_smoke --n 1 --rounds 1 --configurations one_shot generic full --dry-run
python scripts/run_experiments.py --study results/team_smoke --n 1 --rounds 1 --configurations one_shot generic full
```

The second command generates proposals, runs the separate judge, and writes tables and plots. To add the three pilot ablations, add `no_feasibility no_contrarian no_novelty_retrieval` after `full` and choose a new `--study` directory. Use `python scripts/run_experiments.py --help` for seeds, replicates, judge model, and attempt limits. The default runner configuration uses a fixed stratified seed list. An interrupted study can reuse completed conditions when restarted with the same settings. Use a fresh path when changing the protocol or settings, and keep the archived `results/smoke_v2/` for reference.

| Location | What to inspect |
|---|---|
| `results/<study>/manifest.json` | Settings, seed and corpus fingerprints |
| `results/<study>/initials/` and `runs/` | Initial proposals, reviewer critiques, revisions, and stop reasons |
| `results/<study>/evaluation/` | Individual scores, judge evidence, and blinded human-rating material |
| `results/<study>/analysis/` | Score comparisons, paired differences, resource tables, and figures |
| `results/<study>/suite_status.json` | Completion status and recorded failures |
| `results/web_runs/` | Interactive runs, separate from controlled studies |

## Notebooks and code map

The notebooks open saved pilot artifacts by default. To use JupyterLab, install it in the activated environment with `python -m pip install jupyterlab`, then run `python -m jupyter lab` from the project root. Select the Python kernel from the project environment.

1. [Baseline experiments](notebooks/01_Baseline_Experiments.ipynb) shows one-shot and generic review.
2. [Multi-agent review](notebooks/02_Multi_Agent_Review.ipynb) walks through the specialized panel, evidence, and revision trace.
3. [Evaluation and ablation](notebooks/03_Evaluation_and_Ablation.ipynb) compares ratings, resource usage, and progression across rounds.

| Path | Responsibility |
|---|---|
| [frontend/](frontend/) | Browser UI, literature browser, and trace viewer |
| [web.py](src/research_review/web.py), [web_jobs.py](src/research_review/web_jobs.py) | FastAPI routes and background runs |
| [orchestration.py](src/research_review/orchestration.py) | Pipeline state, reviewer coordination, and stopping rules |
| [local_corpus.py](src/research_review/local_corpus.py), [literature_retrieval.py](src/research_review/literature_retrieval.py) | Literature search and citation checks |
| [reviewer_agents.py](src/research_review/reviewer_agents.py), [idea_generator.py](src/research_review/idea_generator.py), [schemas.py](src/research_review/schemas.py) | Specialist prompts, generation and revision, and structured outputs |
| [revision_guard.py](src/research_review/revision_guard.py), [factual_verification.py](src/research_review/factual_verification.py) | Revision decisions and checks for factual prerequisites |
| [runner.py](src/research_review/runner.py), [evaluation.py](src/research_review/evaluation.py), [analysis.py](src/research_review/analysis.py) | Matched experiments, separate judging, and analysis |

To run the Python tests, use `python -m pytest -q`. With Node.js installed, run `node --test tests/trace-ui.test.cjs` for the trace UI tests. LangGraph tests require the full dependency set. For the presentation, start with the [demo and viva guide](docs/DEMONSTRATION_AND_VIVA.md). The [experiment protocol](docs/EXPERIMENT_PROTOCOL.md) covers study design and dataset selection.
