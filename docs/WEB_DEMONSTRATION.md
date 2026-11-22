# Research Review Studio

A local frontend and FastAPI backend for the existing research pipeline. It uses real saved experiments for inspection and the configured Gemini API for new runs. No generated examples or scores are inserted as fallback results.

## Launch

From the project directory with the existing parent environment:

```bash
../.venv/bin/python scripts/serve.py
```

Open **http://127.0.0.1:8000** in Chrome or Firefox. Keep that terminal open. Stop with Ctrl+C. To change the port: `../.venv/bin/python scripts/serve.py --port 8080`.

For a clean environment (Python 3.11+):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-web.txt
.venv/bin/python scripts/serve.py
```

The launch script adds `src` to Python's import path. Notebook packages, Pandas, and LangGraph are not required just to launch this app. The workflow uses LangGraph when installed and otherwise the same bounded Python engine; `resolved_engine` is recorded in each trace. Keep the supplied corpus, data, frontend, and results directories in the checkout.

The server loads the project `.env` using the existing settings loader. `GEMINI_API_KEY` and `GEMINI_MODEL` remain server-side. “Key configured” means a credential is present, not that a live request succeeded. A live run requires working internet access from the terminal that launches the app.

## Five-minute demonstration

1. Open the workspace and click **Open completed example**. This loads an actual three-round Gemini trace from `smoke_v2`; it makes no model calls.
2. Read the initial idea. Explain that it is a generated research proposal, not the project's implemented research method and not an executed scientific hypothesis.
3. Select **Round 1**. Expand **Exact proposal assessed by this round’s reviewers**. Each reviewer received this same input without access to the other critiques.
4. Inspect the **Novelty** card. Open the search queries and literature evidence. Follow a real paper link and inspect the attached exact abstract passage. This is corpus-backed overlap checking; a source match alone does not establish semantic support or novelty.
5. Compare **Feasibility**, **Clarity & importance**, and **Contrarian** criticism. Open the feedback aggregation to show how disagreements are retained. Reviewers are distinct prompts using the same model, not independently trained models.
6. Select rounds 2 and 3 and compare the revised proposal with the preserved initial version. Open the input details to see what was actually reviewed at each step.
7. Open **Experiment results**. Select `smoke_v2` and show the actual baseline, ablation, iteration, trade-off, and runtime plots. There are only two seeds. The full panel improved mean feasibility, clarity and grounding relative to one-shot, while mean novelty decreased; this is descriptive pilot evidence. One generic run failed early. Avoid a general superiority or significance claim.
8. For a live demonstration, choose a seed, **Specialized panel**, and **1 round**. With the new default final panel, support audit and independent evaluation, the estimate is **13 calls before retries**. See [the retest guide](REVIEW_IMPROVEMENTS.md). Click **Generate & review**. The initial idea, individual critiques and rounds appear as they finish. Typical timing depends on Gemini, the 15-second request interval, retries, and internet connectivity.
9. Independent evaluation is now enabled by default; it can be disabled. A one-round full run adds up to two judge calls, for initial and revised ideas. Judge prompts receive the proposal, retrieved literature and constraints; no reviewer feedback or configuration labels. Same-model bias remains a limitation.
10. Export the trace, reopen it from **Run history**, and demonstrate a query in **Literature library**.

## Functionalities to test

| Action | Expected behavior |
|---|---|
| Open completed example | Shows a genuine saved Gemini run without spending API calls. |
| Search a topic in Literature library | Returns real matching abstracts, source URLs, years and available DOIs. |
| Start a full one-round run | Shows literature, the initial proposal, four independent reviews, then a revision. |
| Run one-shot or generic baseline | Uses the corresponding existing pipeline configuration. |
| Remove a reviewer or novelty retrieval | Uses an actual ablation; disabled novelty retrieval is shown in the trace. |
| Enable independent evaluation | Shows separate rubric scores; review scores are never treated as independent ratings. |
| Cancel an active run | Stops before the next request or retry; an already in-flight HTTP call may finish first (timeout up to 120 seconds). Partial feedback is preserved in the job. |
| Start a second concurrent run | Returns a clear conflict, preventing overlapping free-tier runs. |
| Refresh / restart | A refresh can reconnect to the active job. After a process restart, unfinished jobs are marked interrupted, not silently resumed. |
| Inspect a failed run | Shows the failure and retains any valid initial proposal, reviews and final result. |
| Export | Downloads the selected complete trace or interactive job as JSON. |

Interactive runs use the same model settings, roles, retrieval and refinement code. Starting separate interactive runs generates separate initial ideas. These are **not** controlled matched comparisons. Use `scripts/run_experiments.py` for shared-initial, fixed-seed comparisons across conditions.

## Storage and API

Frontend: `frontend/index.html`, `styles.css`, `app.js`. Backend: `src/research_review/web.py`. Worker: `web_jobs.py`. The app serves only its dedicated assets, not the project directory.

New method outputs include structured prior-work comparisons and untested assumption checks, a final panel assessment and a separate citation-support audit when enabled. New runs are written under `results/web_runs/<job-id>/`, including `job.json`, API audit records, completed run JSON, partial workflow checkpoints, and optional evaluation outputs. Existing `smoke` and `smoke_v2` experiment records are read-only to the app. Restarted unfinished runs can be inspected, but resume from an intermediate round is not implemented. Export before deleting any demo files.

The OpenAPI schema is available at `/openapi.json`; the UI has no CDN dependencies. Main endpoints:

- `GET /api/config`, `/api/seeds`, `/api/literature?q=...`
- `GET /api/runs`, `/api/runs/{id}`, `/api/runs/{id}/download`
- `GET /api/studies`, `/api/studies/{study}`, `/api/studies/{study}/figures/{name}`
- `POST /api/budget`, `POST /api/jobs`
- `GET /api/jobs`, `/api/jobs/{id}`; `POST /api/jobs/{id}/cancel`

`POST /api/jobs` example (no credentials in the request):

```json
{
  "mode": "paper",
  "seed_id": "2025.naacl-long.342",
  "configuration": "full",
  "rounds": 1,
  "evaluate": false
}
```

The server binds to loopback with a single worker. It is designed for local course demonstrations, not public deployment or multiple authenticated users. Cross-origin writes and unexpected hosts are rejected. Paper and model text render as text; source links accept only HTTP(S). Secrets are never returned by configuration endpoints. Settings and call caps come from the server's environment.

## Verification

```bash
../.venv/bin/python -m pytest -q
node --check frontend/app.js
```

Web tests use explicitly marked synthetic model responses only in temporary test directories. They exercise API contracts, retrieval, real saved pilot loading, worker execution, call planning, cancellation, concurrency, persistence, failures, origin/host restrictions, and secret non-disclosure. These are software tests, not scientific findings.

In the restricted development shell, the backend starts and in-process HTTP tests run, but normal loopback HTTP checks are blocked and Chrome fails during startup with `setsockopt: Operation not permitted`. Visual browser verification and a new live Gemini request through the UI therefore remain to be performed from your normal terminal. Existing live pilot outputs remain genuine and independently inspectable.
