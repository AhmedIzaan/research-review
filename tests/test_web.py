"""Web contract and background-worker tests. All model responses here are fixtures."""
import asyncio
import json
from pathlib import Path
import threading

import httpx
import pytest

from research_review.config import ROOT, Settings
from research_review.llm import LLMError
from research_review.schemas import Idea
from research_review.storage import load_json, save_json
from research_review.web import create_app
from research_review.web_jobs import BusyError, DemoManager, DemoRequest
from conftest import FixtureClient, FixtureRetriever


def call(app, method, path, **kwargs):
    async def request():
        # Regular timer also supports restricted runners without thread wake-up sockets.
        async def heartbeat():
            while True:
                await asyncio.sleep(.01)
        tick = asyncio.create_task(heartbeat())
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                         base_url='http://testserver') as client:
                return await asyncio.wait_for(client.request(method, path, **kwargs), timeout=10)
        finally:
            tick.cancel()
            try:
                await tick
            except asyncio.CancelledError:
                pass
    return asyncio.run(request())


@pytest.fixture
def web_root(tmp_path, paper):
    save_json(tmp_path/'data'/'seeds.json', [paper.model_dump()])
    save_json(tmp_path/'data'/'corpus'/'papers.json', [paper.model_dump()])
    frontend = tmp_path/'frontend'
    frontend.mkdir()
    for file in (ROOT/'frontend').iterdir():
        (frontend/file.name).write_bytes(file.read_bytes())
    return tmp_path


@pytest.fixture
def app(web_root):
    return create_app(web_root, Settings(request_interval=0, engine='python'))


@pytest.mark.parametrize('path', ['/', '/assets/app.js', '/assets/styles.css',
                                  '/assets/trace-model.js', '/assets/trace-view.js', '/assets/trace.css',
                                  '/api/config', '/api/seeds', '/api/runs', '/api/jobs'])
def test_web_routes(app, path):
    response = call(app, 'GET', path)
    assert response.status_code == 200
    assert response.headers['x-content-type-options'] == 'nosniff'


def test_key_not_exposed_and_unknown_files_not_served(app, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fixture-private-key-never-show')
    response = call(app, 'GET', '/api/config')
    assert response.json()['credential_present'] is True
    assert 'fixture-private-key' not in response.text
    assert 'GEMINI_API_KEY' not in response.text
    for path in ['/.env', '/assets/.env', '/data/corpus/papers.json', '/api/runs/missing']:
        assert call(app, 'GET', path).status_code == 404
    assert call(app, 'GET', '/api/config', headers={'host':'malicious.example'}).status_code == 400


def test_source_search_and_empty_search(app):
    hit = call(app, 'GET', '/api/literature?q=retrieval').json()
    assert hit['papers'][0]['paper_id'] == 'fixture-paper'
    assert call(app, 'GET', '/api/literature?q=zzzzunmatched').json()['papers'] == []
    assert call(app, 'GET', '/api/literature?q=%20%20').status_code == 422
    assert call(app, 'GET', '/api/literature?q=retrieval&limit=1000').status_code == 422


def test_budgets_and_input_bounds(app):
    assert call(app, 'POST', '/api/budget', json={'seed_id':'fixture-paper'}).json()['calls_before_retries'] == 20
    b=call(app,'POST','/api/budget',json={'seed_id':'fixture-paper','rounds':3,'evaluate':True}).json()
    assert b['pipeline_calls'] == 32 and b['judge_calls_upper_bound'] == 8
    assert b['attempts_upper_bound'] == 120
    one=DemoRequest(seed_id='fixture-paper', configuration='one_shot', evaluate=True)
    assert one.budget()['calls_before_retries'] == 5
    for value in [{'rounds':4}, {'rounds':True}, {'configuration':'unknown'}, {'mode':'topic','topic':'a'}]:
        assert call(app,'POST','/api/jobs',json={'seed_id':'fixture-paper',**value}).status_code == 422


def test_missing_key_and_cross_origin_writes(app, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    assert call(app,'POST','/api/jobs',json={'seed_id':'fixture-paper'}).status_code == 422
    assert app.state.manager.listing() == []
    for headers in [{'origin':'https://elsewhere.invalid'}, {'sec-fetch-site':'cross-site'}]:
        assert call(app,'POST','/api/jobs',json={'seed_id':'fixture-paper'},headers=headers).status_code == 403
    assert call(app,'POST','/api/jobs/nope/cancel').status_code == 404


def fake_factory(idea, barrier=None, fail=False):
    class FakeClient(FixtureClient):
        def __init__(self, settings, audit_dir, sleep):
            super().__init__(idea)
            self.sleep = sleep
        def generate(self, schema, instruction, content, label, model=None):
            if barrier:
                barrier.set()
                self.sleep(20)
            if fail:
                raise LLMError('Fixture model failure')
            if label == 'initial_generation':
                self.events.append({'label':label,'status':'ok','total_tokens':10})
                return idea.model_copy(deep=True)
            return super().generate(schema, instruction, content, label, model)
    return FakeClient


def wait_job(manager, job_id):
    manager.threads[job_id].join(timeout=5)
    assert not manager.threads[job_id].is_alive()
    return manager.snapshot(job_id)


def test_actual_worker_executes_pipeline_and_persists_trace(web_root, idea, paper, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','fixture-key')
    manager=DemoManager(web_root, Settings(request_interval=0,engine='python'),
                        FixtureRetriever(paper), fake_factory(idea))
    job=manager.start(DemoRequest(seed_id=paper.paper_id,evaluate=False))
    result=wait_job(manager,job['id'])
    assert result['status'] == 'completed'
    assert len(result['rounds']) == 1
    assert [r['role'] for r in result['rounds'][0]['reviews']] == ['novelty','feasibility','clarity','contrarian']
    assert result['result']['provenance'] == 'unit_test_fixture'
    events=[e['type'] for e in result['events']]
    assert events.index('initial_generated') < events.index('review_completed') < events.index('round_completed')
    assert len([e for e in events if e=='review_completed']) == 4
    assert len([e for e in events if e=='final_review_completed']) == 4
    assert result['result']['final_review_status']=='completed'
    assert result['result']['evidence_audit']['assessments']
    assert len(list((web_root/'results'/'web_runs'/job['id']/'runs').glob('*.json'))) == 1
    assert manager.active is None
    # A new process can inspect the same finished demo without regenerating it.
    restored=DemoManager(web_root,Settings(),FixtureRetriever(paper))
    assert restored.snapshot(job['id'])['result'] == result['result']


def test_single_active_job_and_cooperative_cancellation(web_root, idea, paper, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','fixture-key')
    barrier=threading.Event()
    manager=DemoManager(web_root,Settings(),FixtureRetriever(paper),fake_factory(idea,barrier))
    job=manager.start(DemoRequest(seed_id=paper.paper_id))
    assert barrier.wait(3)
    with pytest.raises(BusyError):
        manager.start(DemoRequest(seed_id=paper.paper_id))
    manager.cancel(job['id'])
    assert wait_job(manager,job['id'])['status'] == 'cancelled'
    assert manager.active is None


def test_worker_error_is_visible_and_releases_slot(web_root, idea, paper, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','fixture-key')
    manager=DemoManager(web_root,Settings(),FixtureRetriever(paper),fake_factory(idea,fail=True))
    job=manager.start(DemoRequest(seed_id=paper.paper_id))
    result=wait_job(manager,job['id'])
    assert result['status']=='failed' and result['error']=='Fixture model failure'
    assert manager.active is None
    assert manager.snapshot(job['id'])['result'] is None


def test_restart_marks_unfinished_run_interrupted(web_root, paper):
    save_json(web_root/'results'/'web_runs'/'unfinished'/'job.json',
              {'id':'unfinished','status':'running','created_at':'2026-11-13','request':{}})
    manager=DemoManager(web_root,Settings(),FixtureRetriever(paper))
    assert manager.snapshot('unfinished')['status'] == 'interrupted'


def test_real_saved_pilot_is_available_without_model_calls():
    app=create_app(ROOT,Settings())
    rows=call(app,'GET','/api/runs').json()
    full=next(r for r in rows if r['study']=='smoke_v2' and r['configuration']=='full')
    run=call(app,'GET','/api/runs/'+full['id']).json()
    assert len(run['rounds']) == 3 and run['provenance']=='live_gemini'
    assert all(len(r['reviews']) == 4 for r in run['rounds'])
    data=call(app,'GET','/api/studies/smoke_v2').json()
    full_scores=next(r for r in data['summary'] if r['configuration']=='full')
    assert full_scores['n']==2 and full_scores['feasibility']==4.0
    assert data['status']['reviewer_failures']==1
    assert call(app,'GET','/api/studies/smoke_v2/figures/baseline_comparison').headers['content-type']=='image/png'
    assert call(app,'GET','/api/studies/not-real').status_code==404
    assert call(app,'GET','/api/studies/smoke_v2/figures/not-real').status_code==404


def test_job_routes_and_download_preserve_fixture_provenance(web_root, idea, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','fixture-key')
    app=create_app(web_root,Settings(request_interval=0,engine='python'),fake_factory(idea))
    response=call(app,'POST','/api/jobs',json={'seed_id':'fixture-paper','configuration':'one_shot','evaluate':False})
    assert response.status_code==202
    job_id=response.json()['id']
    wait_job(app.state.manager,job_id)
    job=call(app,'GET','/api/jobs/'+job_id).json()
    assert job['status']=='completed' and job['result']['provenance']=='unit_test_fixture'
    runs=call(app,'GET','/api/runs').json()
    download=call(app,'GET','/api/runs/'+runs[0]['id']+'/download')
    assert download.status_code==200
    assert download.json()['provenance']=='unit_test_fixture'
    assert 'attachment' in download.headers['content-disposition']
    assert len(call(app,'GET','/api/jobs').json())==1


def test_web_judging_refuses_fixtures_and_preserves_pipeline_result(web_root, idea, paper, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','fixture-key')
    manager=DemoManager(web_root,Settings(),FixtureRetriever(paper),fake_factory(idea))
    job=manager.start(DemoRequest(seed_id=paper.paper_id,configuration='one_shot',evaluate=True))
    result=wait_job(manager,job['id'])
    assert result['status']=='failed' and 'fixtures' in result['error']
    assert result['result']['provenance']=='unit_test_fixture'
    assert result['evaluation']==[]


def test_default_ui_plan_rejects_too_small_cap_before_spending_calls(web_root, idea, paper, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','fixture-key')
    manager=DemoManager(web_root,Settings(max_api_calls=6),FixtureRetriever(paper),fake_factory(idea))
    with pytest.raises(ValueError,match='below the selected call plan'):
        manager.start(DemoRequest(seed_id=paper.paper_id))
    assert manager.listing()==[] and manager.active is None


def test_legacy_six_call_demo_remains_explicitly_available():
    request=DemoRequest(seed_id='fixture-paper',evaluate=False,final_review=False,audit_evidence=False,revision_policy='always_accept',verify_dependencies=False)
    assert request.budget()['calls_before_retries']==6
    assert request.budget()['final_review_calls']==0
