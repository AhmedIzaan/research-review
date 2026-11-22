"""Local FastAPI application for live demos and read-only experiment inspection."""
from contextlib import asynccontextmanager
import csv
from functools import lru_cache
import os
from pathlib import Path
import re

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import CONFIGURATIONS, ROOT, Settings
from .evaluation import METRICS
from .llm import GeminiClient
from .local_corpus import LocalCorpusRetriever
from .schemas import Run
from .storage import load_json
from .web_jobs import BusyError, DemoManager, DemoRequest

FIGURES = {'baseline_comparison', 'ablation_comparison', 'iteration_progression',
           'novelty_feasibility', 'execution_time'}


def csv_rows(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def create_app(root=ROOT, settings=None, client_factory=GeminiClient):
    root = Path(root)
    settings = settings or Settings.from_env()
    # Interactive inspection always uses the pinned local scholarly snapshot.
    corpus_path = Path(settings.corpus_path)
    corpus_path = corpus_path if corpus_path.is_absolute() else root / corpus_path
    retriever = LocalCorpusRetriever(corpus_path)
    settings = settings.model_copy(update={'retrieval_backend':'local',
                                           'corpus_fingerprint':retriever.fingerprint})
    manager = DemoManager(root, settings, retriever, client_factory)

    @asynccontextmanager
    async def lifespan(app):
        yield
        manager.close()

    # Keep the app offline-capable; default Swagger/Redoc pages depend on CDN scripts.
    app = FastAPI(title='Research Review Studio', version='1.0.0', lifespan=lifespan,
                  docs_url=None, redoc_url=None)
    app.state.manager = manager
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost','127.0.0.1','[::1]','testserver'])

    @app.middleware('http')
    async def local_requests(request: Request, call_next):
        if request.method in ('POST','PUT','PATCH','DELETE'):
            origin = request.headers.get('origin')
            # Block a third-party page from spending the user's local API quota.
            if origin and origin != f'{request.url.scheme}://{request.headers.get("host", "")}':
                return JSONResponse({'detail':'Cross-origin writes are not allowed'}, status_code=403)
            if request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail':'Cross-site writes are not allowed'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = ("default-src 'self'; script-src 'self'; "
            "style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'")
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    def study_path(study):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', study) or study == 'web_runs':
            raise HTTPException(404, 'Unknown study')
        path = root / 'results' / study
        if not (path / 'suite_status.json').is_file():
            raise HTTPException(404, 'Unknown study')
        return path

    @lru_cache(maxsize=256)
    def read_run(path):
        return Run.model_validate(load_json(Path(path))).model_dump()

    def run_paths():
        paths = {}
        for path in (root / 'results').glob('*/runs/*.json'):
            if not path.name.endswith('.partial.json'):
                paths[path.parent.parent.name+':'+path.stem] = path
        for path in (root / 'results' / 'web_runs').glob('*/runs/*.json'):
            if not path.name.endswith('.partial.json'):
                paths['web-'+path.parent.parent.name+':'+path.stem] = path
        return paths

    @app.get('/api/config')
    def config():
        return {'model':settings.model, 'judge_model':settings.judge_model,
                'methodology_version':settings.methodology_version,
                'credential_present':bool(os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')),
                'corpus_count':len(retriever.papers), 'corpus_fingerprint':retriever.fingerprint,
                'retrieval_backend':'local BM25 over scholarly abstracts',
                'constraints':settings.constraints, 'max_rounds':3,
                'max_attempts':settings.max_attempts, 'max_api_calls':settings.max_api_calls,
                'demo_defaults':{'evaluate':True,'final_review':True,'audit_evidence':True,'revision_policy':'guarded','judge_repeats':2},
                'request_interval':settings.request_interval,
                'configurations':{k:list(v) for k,v in CONFIGURATIONS.items()},
                'active_job':manager.active,
                'cost_note':'Estimates use your configured rates. A rate of zero is not a billing guarantee.'}

    @app.get('/api/seeds')
    def seeds():
        from .config import load_seed_records
        return load_seed_records(root)

    @app.get('/api/literature')
    def literature(q: str = Query(min_length=1, max_length=300), limit: int = Query(default=8, ge=1, le=20)):
        if not q.strip():
            raise HTTPException(422, 'Enter search keywords')
        return retriever.search(q, limit).model_dump()

    @app.get('/api/runs')
    def runs():
        result = []
        for key,path in run_paths().items():
            run = read_run(str(path))
            result.append({'id':key, 'run_id':run['run_id'], 'study':key.split(':')[0],
                           'seed_id':run['seed_id'], 'configuration':run['configuration'],
                           'title':run['initial_idea']['title'], 'rounds':len(run['rounds']),
                           'stop_reason':run['stop_reason'], 'provenance':run['provenance']})
        return sorted(result, key=lambda r:(r['study'] != 'smoke_v2', r['configuration'] != 'full', r['id']))

    @app.get('/api/runs/{key}')
    def run_detail(key: str):
        path = run_paths().get(key)
        if path is None:
            raise HTTPException(404, 'Unknown run')
        return read_run(str(path))

    @app.get('/api/runs/{key}/download')
    def download_run(key: str):
        path = run_paths().get(key)
        if path is None:
            raise HTTPException(404, 'Unknown run')
        return FileResponse(path, filename=path.name, media_type='application/json')

    @app.get('/api/studies')
    def studies():
        return [{'id':p.parent.name, 'status':load_json(p)['status']}
                for p in sorted((root/'results').glob('*/suite_status.json'))]

    @app.get('/api/studies/{study}')
    def study_detail(study: str):
        path = study_path(study)
        scores = csv_rows(path / 'evaluation' / 'scores.csv')
        valid = [r for r in scores if not r.get('judge_error') and all(r.get(m) for m in METRICS)]
        finals = [r for r in valid if r['is_final'].lower() == 'true']
        summary = []
        for configuration in CONFIGURATIONS:
            rows = [r for r in finals if r['configuration'] == configuration]
            groups={}
            for row in rows:groups.setdefault(row['seed_id'],[]).append(row)
            means=[{m:sum(float(r[m]) for r in group)/len(group) for m in METRICS} for group in groups.values()]
            summary.append({'configuration':configuration,'n':len(means),'final_outputs':len(rows),
                            **{m:sum(r[m] for r in means)/len(means) if means else None for m in METRICS}})
        return {'id':study, 'status':load_json(path/'suite_status.json'), 'summary':summary,
                'scores':scores, 'resources':csv_rows(path/'analysis'/'resources.csv'),
                'figures':[f for f in sorted(FIGURES) if (path/'analysis'/(f+'.png')).exists()],
                'limitations':'Purposive seed sample; possible shared LLM judge bias, '
                    'abstract-only bounded retrieval, unequal call budgets, and no human calibration. '
                    'Reviewer scores are feedback, not independent evaluation. No significance claims.'}

    @app.get('/api/studies/{study}/figures/{figure}')
    def figure(study: str, figure: str):
        path = study_path(study) / 'analysis' / (figure+'.png')
        if figure not in FIGURES or not path.is_file():
            raise HTTPException(404, 'Unknown figure')
        return FileResponse(path, media_type='image/png')

    @app.get('/api/jobs')
    def jobs():
        return manager.listing()

    @app.post('/api/jobs', status_code=202)
    def start_job(body: DemoRequest):
        try:
            return manager.start(body)
        except BusyError as exc:
            raise HTTPException(409, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @app.post('/api/budget')
    def budget(body: DemoRequest):
        return body.budget(settings.max_attempts)

    @app.get('/api/jobs/{job_id}')
    def job_detail(job_id: str):
        try:
            return manager.snapshot(job_id)
        except KeyError:
            raise HTTPException(404, 'Unknown job') from None

    @app.post('/api/jobs/{job_id}/cancel')
    def cancel_job(job_id: str):
        try:
            return manager.cancel(job_id)
        except KeyError:
            raise HTTPException(404, 'Unknown job') from None

    static = root / 'frontend'
    app.mount('/assets', StaticFiles(directory=static), name='assets')

    @app.get('/', include_in_schema=False)
    def index():
        return FileResponse(static / 'index.html', media_type='text/html')

    return app
