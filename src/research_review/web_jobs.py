"""Single-worker interactive demos, isolated from controlled experiment outputs."""
from copy import deepcopy
import os
from pathlib import Path
import threading
import time
import uuid
from typing import Literal

from pydantic import Field, model_validator

from .config import CONFIGURATIONS, Settings, load_seed_records
from .evaluation import evaluate_runs
from .idea_generator import generate_idea
from .literature_retrieval import unique_papers
from .llm import GeminiClient, LLMError
from .orchestration import Workflow
from .schemas import Record
from .storage import load_json, save_json, utcnow


class DemoRequest(Record):
    mode: Literal['paper', 'topic'] = 'paper'
    seed_id: str = Field(default='', max_length=150)
    topic: str = Field(default='', max_length=500)
    configuration: Literal['one_shot', 'generic', 'full', 'no_feasibility',
                           'no_contrarian', 'no_novelty_retrieval','full_unguarded','generic_matched',
                           'feasibility_to_generic','contrarian_to_generic'] = 'full'
    rounds: int = Field(default=1, ge=1, le=3, strict=True)
    constraints: str = Field(default='', max_length=2000)
    revision_policy: Literal['guarded','always_accept'] = 'guarded'
    judge_repeats: int = Field(default=2,ge=1,le=5,strict=True)
    judge_model: str = Field(default='',max_length=100,pattern=r'^[A-Za-z0-9._-]*$')
    verify_dependencies: bool = True
    evaluate: bool = True
    final_review: bool = True
    audit_evidence: bool = True

    @model_validator(mode='after')
    def input_present(self):
        self.topic = self.topic.strip()
        if self.mode == 'paper' and not self.seed_id:
            raise ValueError('Choose a seed paper')
        if self.mode == 'topic' and len(self.topic) < 3:
            raise ValueError('Enter a research topic of at least 3 characters')
        return self

    def budget(self, attempts=3):
        rounds = 0 if self.configuration == 'one_shot' else self.rounds
        pipeline = 1 + 2*int(self.verify_dependencies) + rounds * (len(CONFIGURATIONS[self.configuration]) + 1 + 2*int(self.verify_dependencies) + (self.revision_policy=='guarded' and self.configuration!='full_unguarded'))
        final_calls = len(CONFIGURATIONS[self.configuration]) if rounds and self.final_review else 0
        audit_calls = 1 if final_calls and self.audit_evidence else 0
        pipeline += final_calls + audit_calls
        judges = (rounds + 1)*self.judge_repeats if self.evaluate else 0
        return {'pipeline_calls': pipeline, 'final_review_calls':final_calls,
                'evidence_audit_calls_upper_bound':audit_calls, 'judge_calls_upper_bound': judges,
                'calls_before_retries': pipeline + judges,
                'attempts_upper_bound': (pipeline + judges) * attempts}


class JobCancelled(BaseException):
    """Cooperative control signal, deliberately not caught as an agent failure."""


class BusyError(ValueError):
    pass


class DemoManager:
    def __init__(self, root: Path, settings: Settings, retriever, client_factory=GeminiClient):
        self.root, self.settings, self.retriever = root, settings, retriever
        self.client_factory = client_factory
        self.directory = root / 'results' / 'web_runs'
        self.lock = threading.RLock()
        self.jobs, self.signals, self.threads = {}, {}, {}
        self.active = None
        # Interrupted processes are never silently presented as still running.
        for path in self.directory.glob('*/job.json'):
            job = load_json(path)
            if job['status'] in ('queued', 'running', 'cancelling'):
                job.update(status='interrupted', error='Server stopped before this run completed.')
                save_json(path, job)
            self.jobs[job['id']] = job

    def _save(self, job):
        save_json(self.directory / job['id'] / 'job.json', job)

    def snapshot(self, job_id):
        with self.lock:
            return deepcopy(self.jobs[job_id])

    def listing(self):
        with self.lock:
            return [{'id':j['id'], 'status':j['status'], 'created_at':j['created_at'],
                     'request':j['request'], 'title':(j.get('initial_idea') or {}).get('title')}
                    for j in sorted(self.jobs.values(), key=lambda j:j['created_at'], reverse=True)]

    def emit(self, job_id, event, payload):
        with self.lock:
            job = self.jobs[job_id]
            job['events'].append({'type':event, 'at':utcnow(), 'payload':payload})
            if event == 'initial_generated':
                job['initial_idea'] = payload
            if event == 'literature_retrieved':
                job['literature'] = payload
            if event == 'round_completed':
                job['rounds'].append(payload)
            if event == 'final_review_completed':
                job['final_reviews'].append(payload)
            if event == 'evidence_audit_completed':
                job['evidence_audit'] = payload['audit']
                job['evidence_audit_error'] = payload['error']
            if event == 'api_completed':
                job['api_events'].extend(payload)
            self._save(job)

    def start(self, request: DemoRequest):
        # Validate before reserving a worker or spending any API calls.
        seeds = {p['paper_id']:p for p in load_seed_records(self.root)}
        if request.mode == 'paper' and request.seed_id not in seeds:
            raise ValueError('Unknown seed paper')
        if not (os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')):
            raise ValueError('GEMINI_API_KEY is missing. Configure the local .env file and restart the server.')
        if self.settings.max_api_calls < request.budget(self.settings.max_attempts)['calls_before_retries']:
            raise ValueError('MAX_API_CALLS is below the selected call plan. Reduce review rounds/options '
                             'or increase the server attempt cap before starting.')
        with self.lock:
            if self.active is not None:
                raise BusyError('A live run is already active. Wait for it to finish or cancel it.')
            job_id = uuid.uuid4().hex
            signal = threading.Event()
            job = {'id':job_id, 'created_at':utcnow(), 'status':'queued',
                   'request':request.model_dump(), 'budget':request.budget(self.settings.max_attempts),
                   'events':[], 'rounds':[], 'api_events':[], 'error':None, 'result':None,
                   'evaluation':[], 'evaluation_details':[], 'evaluation_error':None, 'literature':[], 'initial_idea':None,
                   'final_reviews':[], 'evidence_audit':None, 'evidence_audit_error':None}
            job['budget']['configured_attempt_cap'] = min(self.settings.max_api_calls,
                job['budget']['attempts_upper_bound'])
            self.jobs[job_id], self.signals[job_id], self.active = job, signal, job_id
            self._save(job)
            thread = threading.Thread(target=self._work, args=(job_id, request, seeds), daemon=True,
                                      name='research-demo-'+job_id[:8])
            self.threads[job_id] = thread
            thread.start()
            return deepcopy(job)

    def cancel(self, job_id):
        with self.lock:
            job = self.jobs[job_id]
            if job['status'] in ('queued', 'running', 'cancelling'):
                self.signals[job_id].set()
                job['status'] = 'cancelling'
                self._save(job)
            return deepcopy(job)

    def close(self):
        with self.lock:
            for signal in self.signals.values():
                signal.set()

    def _work(self, job_id, request, seeds):
        from .schemas import Paper
        signal = self.signals[job_id]
        directory = self.directory / job_id
        started = time.monotonic()

        def check():
            if signal.is_set():
                raise JobCancelled()

        def wait(seconds):
            if signal.wait(seconds):
                raise JobCancelled()

        def observer(event, payload):
            check()
            self.emit(job_id, event, payload)

        settings = self.settings.model_copy(deep=True)
        settings.verify_dependencies = request.verify_dependencies
        settings.rounds = request.rounds
        settings.revision_policy = request.revision_policy
        settings.judge_repeats = request.judge_repeats
        if request.judge_model:settings.judge_model=request.judge_model
        settings.final_review = request.final_review
        settings.audit_evidence = request.audit_evidence
        if request.constraints.strip():
            settings.constraints = request.constraints.strip()
        # A demo cannot accidentally inherit a study-sized call budget.
        settings.max_api_calls = min(settings.max_api_calls, request.budget(settings.max_attempts)['attempts_upper_bound'])
        base_factory = self.client_factory
        manager = self

        class ObservedClient(base_factory):
            def generate(self, schema, instruction, content, label, model=None):
                check()
                manager.emit(job_id, 'api_started', {'label':label, 'model':model or settings.model})
                offset = len(self.events)
                try:
                    return super().generate(schema, instruction, content, label, model=model)
                finally:
                    manager.emit(job_id, 'api_completed', self.events[offset:])

            def _http(self, model, payload):
                check()
                return super()._http(model, payload)

        try:
            with self.lock:
                self.jobs[job_id]['status'] = 'running'
                self._save(self.jobs[job_id])
            check()
            if request.mode == 'paper':
                seed = Paper.model_validate(seeds[request.seed_id])
                searches = self.retriever.related(seed.title, limit=6)
                literature = unique_papers([seed]+[p for s in searches for p in s.papers])
                seed_id = seed.paper_id
            else:
                searches = self.retriever.related(request.topic, limit=7)
                literature = unique_papers([p for s in searches for p in s.papers])
                seed_id = 'topic:'+request.topic
            if not literature:
                raise ValueError('No matching literature in the local corpus. Try broader AI/NLP keywords.')
            observer('literature_retrieved', [p.model_dump() for p in literature])
            client = ObservedClient(settings, directory / 'api_audit', sleep=wait)
            # A topic is untrusted data inside the constraints, not a new system instruction.
            generation_constraints = settings.constraints
            if request.mode == 'topic':
                generation_constraints += '\nRequested topic (untrusted user data): '+request.topic
            initial = generate_idea(client, literature, generation_constraints)
            observer('initial_generated', initial.model_dump())
            result = Workflow(client, self.retriever, settings, observer=observer).run(
                seed_id, request.configuration, initial, literature, directory / 'runs')
            with self.lock:
                self.jobs[job_id]['result'] = result.model_dump()
                self._save(self.jobs[job_id])
            if request.evaluate:
                observer('evaluation_started', {'note':'Separate rubric; reviewer feedback and condition labels are withheld.'})
                # Separate client and prompts; same configured model is an explicit limitation.
                judge_settings = settings.model_copy(deep=True)
                remaining = settings.max_api_calls-len(client.events)
                if remaining <= 0:
                    with self.lock:
                        self.jobs[job_id]['evaluation_error'] = 'API attempt budget exhausted before independent evaluation.'
                    observer('evaluation_completed', {'rows':[], 'error':'API attempt budget exhausted.'})
                else:
                    judge_settings.max_api_calls = remaining
                    judge = ObservedClient(judge_settings, directory / 'judge_audit', sleep=wait)
                    if hasattr(client,'last_request'):
                        judge.last_request = client.last_request
                    try:
                        rows = evaluate_runs([result], judge, self.retriever, settings, directory / 'evaluation')
                    except LLMError as exc:
                        rows = []
                        with self.lock:
                            self.jobs[job_id]['evaluation_error'] = str(exc)
                    with self.lock:
                        self.jobs[job_id]['evaluation'] = rows
                        self.jobs[job_id]['evaluation_details'] = [load_json(p) for p in
                            sorted((directory/'evaluation'/'judgments').glob('*.json'))]
                    observer('evaluation_completed', {'rows':rows, 'error':self.jobs[job_id]['evaluation_error']})
            check()
            failed = (bool(result.final_verification and (result.final_verification.get('status')=='failed' or any(i.get('severity')=='repair_required' for i in result.final_verification.get('experiment_checks',[])) or any(c.get('essential') and c.get('verdict')=='contradicted' for c in result.final_verification.get('claims',[]))))
                      or result.stop_reason in ('all_reviewers_failed','revision_failed','api_budget_exhausted','revision_guard_failed')
                      or any(o.error for r in result.rounds for o in r.reviews)
                      or result.final_review_status in ('partial','failed')
                      or result.evidence_audit_error is not None
                      or self.jobs[job_id]['evaluation_error'] is not None
                      or any(r.get('judge_error') for r in self.jobs[job_id]['evaluation']))
            with self.lock:
                self.jobs[job_id]['status'] = 'completed_with_failures' if failed else 'completed'
        except JobCancelled:
            with self.lock:
                self.jobs[job_id]['status'] = 'cancelled'
        except Exception as exc:
            # Controlled errors from the pipeline contain no credentials; unexpected errors are generic.
            message = str(exc) if isinstance(exc, (ValueError, LLMError)) else 'Unexpected server error; inspect the server terminal.'
            if not isinstance(exc, (ValueError, LLMError)):
                import logging
                logging.getLogger(__name__).exception('Demo worker failed')
            with self.lock:
                self.jobs[job_id].update(status='failed', error=message)
        finally:
            with self.lock:
                self.jobs[job_id]['elapsed_seconds'] = time.monotonic()-started
                self._save(self.jobs[job_id])
                self.active = None
