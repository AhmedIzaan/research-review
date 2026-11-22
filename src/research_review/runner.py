"""Run the controlled study, independent judging, and analysis in one process."""
import argparse
import importlib.util
import os
from pathlib import Path
import sys

from .config import CONFIGURATIONS, ROOT, Settings, budget
from .evaluation import evaluate_runs
from .experiments import run_study
from .literature_retrieval import create_retriever
from .llm import GeminiClient
from .schemas import Paper
from .storage import load_json, save_json, utcnow
from .evidence_catalog import PROTOCOL
from .judge_retrieval import JUDGE_RETRIEVAL_PROTOCOL


class ProgressClient(GeminiClient):
    def generate(self, schema, instruction, content, label, model=None):
        print(f'[{utcnow()}] Requesting {label} ({model or self.settings.model})', flush=True)
        start = len(self.events)
        try:
            return super().generate(schema, instruction, content, label, model)
        finally:
            for event in self.events[start:]:
                print(f"  attempt {event['attempt']}: {event['status']}; "
                      f"tokens={event.get('total_tokens')}; error={event.get('error', 'none')}", flush=True)


def check_retrieval(retriever, query):
    searches = retriever.related(query, limit=3)
    if (not any(p.abstract.strip() for search in searches for p in search.papers)
            and not getattr(retriever, 'is_local', False)):
        searches.append(retriever.search(query, limit=3, provider='arxiv'))
    if not any(p.abstract.strip() for search in searches for p in search.papers):
        raise RuntimeError(
            'Scholarly retrieval returned no usable abstracts. No model experiments started. '
            'Inspect suite_preflight.json for endpoint errors or rate limits.'
        )
    return searches


def assess_completion(runs, rows, analysis, seeds, replicates, configurations=None):
    expected = {(p.paper_id, name, rep) for p in seeds
                for name in (configurations or CONFIGURATIONS) for rep in range(replicates)}
    actual = {(r.seed_id, r.configuration, r.replicate) for r in runs}
    failed_runs = [r.run_id for r in runs if r.stop_reason in
                   {'all_reviewers_failed', 'revision_failed', 'api_budget_exhausted', 'revision_guard_failed'}]
    failed_reviews = sum(bool(o.error) for r in runs
                         for o in [item for rd in r.rounds for item in rd.reviews]+r.final_reviews)
    failed_audits = sum(bool(r.evidence_audit_error) for r in runs)
    dependency_failures=sum(bool(r.final_verification and (r.final_verification.get('status')=='failed' or any(i.get('severity')=='repair_required' for i in r.final_verification.get('experiment_checks',[])) or any(c.get('essential') and c.get('verdict')=='contradicted' for c in r.final_verification.get('claims',[])))) for r in runs)
    failed_judgments = sum(bool(row.get('judge_error')) for row in rows)
    scored_finals = {(row['seed_id'], row['configuration'], row['replicate'])
                     for row in rows if row['is_final'] and not row.get('judge_error')}
    complete = (actual == expected and expected <= scored_finals and not failed_runs
                and not failed_reviews and not failed_judgments and not failed_audits and not dependency_failures
                and analysis.get('status') == 'analyzed')
    return {'status': 'completed' if complete else 'completed_with_failures',
            'expected_configurations': len(expected), 'saved_configurations': len(actual),
            'missing_configurations': sorted(expected - actual),
            'unscored_final_configurations': sorted(expected - scored_finals),
            'failed_runs': failed_runs, 'reviewer_failures': failed_reviews,
            'dependency_failures':dependency_failures,'judge_failures': failed_judgments, 'evidence_audit_failures':failed_audits, 'analysis': analysis}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--n', type=int, default=3, help='Number of fixed stratified seeds; 3 is a smoke test, 12 the complete sample')
    parser.add_argument('--rounds', type=int, choices=range(1, 4), default=1)
    parser.add_argument('--replicates', type=int, default=1)
    parser.add_argument('--study', type=Path, default=ROOT / 'results' / 'design_repairs_v8_smoke')
    parser.add_argument('--seeds',type=Path,default=ROOT/'data/evaluation_seeds_v3.json')
    parser.add_argument('--configurations',nargs='+',choices=list(CONFIGURATIONS),default=['one_shot','generic','generic_matched','full','full_unguarded'])
    parser.add_argument('--revision-policy',choices=['guarded','always_accept'],default='guarded')
    parser.add_argument('--judge-repeats',type=int,choices=range(1,6),default=2)
    parser.add_argument('--judge-model',default=None,help='Optional available independent model; no automatic substitution')
    parser.add_argument('--max-api-calls',type=int,default=None,help='Explicit attempt cap per generation/judging client')
    parser.add_argument('--dry-run',action='store_true',help='Print plan without API calls or study writes')
    args = parser.parse_args(argv)
    if args.n < 1 or args.replicates < 1:
        parser.error('n and replicates must be positive')
    overrides=dict(rounds=args.rounds,revision_policy=args.revision_policy,judge_repeats=args.judge_repeats)
    if args.judge_model:overrides['judge_model']=args.judge_model
    if args.max_api_calls:overrides['max_api_calls']=args.max_api_calls
    settings = Settings.from_env(**overrides)
    study = args.study.resolve()
    manifest = study / 'manifest.json'
    if manifest.exists():
        previous = load_json(manifest)['specification']
        if (previous.get('evidence_protocol') != PROTOCOL or
                previous.get('judge_retrieval_protocol') != JUDGE_RETRIEVAL_PROTOCOL or
                previous.get('settings',{}).get('methodology_version') != settings.methodology_version):
            print('This study uses an earlier methodology. Choose a new study directory; existing outputs were preserved.',flush=True)
            return 1
    seeds = [Paper.model_validate(p) for p in load_json(args.seeds)]
    if args.n > len(seeds):
        parser.error(f'Only {len(seeds)} fixed seeds are available')
    seeds = seeds[:args.n]
    plan = budget(args.n * args.replicates, settings.rounds, settings.max_attempts,
                  configurations=args.configurations,revision_policy=settings.revision_policy,judge_repeats=settings.judge_repeats,verify_dependencies=settings.verify_dependencies)
    print(f'Study: {study}\nModel: {settings.model}\nJudge: {settings.judge_model}', flush=True)
    print(f"Planned calls before retries: {plan['total_calls_upper_bound']}; "
          'completed saved conditions and judgments are reused.', flush=True)
    print(f'Policy: {settings.revision_policy}; judge repetitions: {settings.judge_repeats}; independent seeds: {args.n}',flush=True)
    print(f"Upper attempts including retries: {plan['with_retries_upper_bound']}; planning tokens: "
          f"{plan['planning_input_tokens']} input + {plan['planning_output_tokens']} output",flush=True)
    estimated=(None if settings.input_rate is None or settings.output_rate is None else
               (plan['planning_input_tokens']*settings.input_rate+plan['planning_output_tokens']*settings.output_rate)/1_000_000)
    print(f'Configured-rate planning cost USD: {estimated}; free-tier quota availability is not guaranteed.',flush=True)
    if args.dry_run:return 0
    status_path = study / 'suite_status.json'
    state = {'started_at': utcnow(), 'stage': 'preflight', 'status': 'running', 'plan': plan}
    save_json(status_path, state)
    try:
        if not (os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')):
            raise RuntimeError('Missing Gemini key: configure the project .env locally.')
        missing = [name for name in ('pandas', 'matplotlib') if not importlib.util.find_spec(name)]
        if missing:
            raise RuntimeError('Install analysis dependencies before API use: '
                               + sys.executable + ' -m pip install pandas matplotlib')
        if settings.model != settings.judge_model:
            print('Generator and judge models differ; verify both are accessible on your account.', flush=True)
        if max(plan['generation_review_calls'],plan['judge_calls_upper_bound']) > settings.max_api_calls:
            raise RuntimeError('MAX_API_CALLS is below the planned generation budget. '
                               'Explicitly increase it in .env or reduce the sample.')
        retriever = create_retriever(settings)
        print(f'Retrieval backend: {settings.retrieval_backend}; '
              f'corpus fingerprint: {settings.corpus_fingerprint}', flush=True)
        print('Checking actual scholarly retrieval before spending model calls...', flush=True)
        try:
            searches = check_retrieval(retriever, seeds[0].title)
        finally:
            save_json(study / 'suite_preflight.json', {'checked_at': utcnow(),
                                                     'retrieval': retriever.log})
        print('Scholarly abstracts available. Starting matched experiments.', flush=True)
        state['stage'] = 'generation_and_review'
        save_json(status_path, state)
        client = ProgressClient(settings, study / 'api_audit')
        runs = run_study(seeds, client, retriever, settings, study, args.replicates,configurations=args.configurations,
                         progress=lambda message: print(message, flush=True))
        state['stage'] = 'independent_evaluation'
        save_json(status_path, state)
        print(f'{len(runs)} configurations saved. Starting blinded judgments.', flush=True)
        judge = ProgressClient(settings, study / 'judge_api_audit')
        rows = evaluate_runs(runs, judge, retriever, settings, study / 'evaluation')
        state['stage'] = 'analysis'
        save_json(status_path, state)
        from .analysis import analyze
        analysis = analyze(study)
        save_json(study / 'analysis_status.json', analysis)
        state.update(assess_completion(runs, rows, analysis, seeds, args.replicates,args.configurations))
        state.update(stage='finished', finished_at=utcnow())
        notebooks_ready = all(importlib.util.find_spec(name) for name in ('nbclient', 'nbformat', 'ipykernel'))
        state['jupyter_dependencies_available'] = notebooks_ready
        state['notebook_execution'] = 'pending; inspect saved study with the project notebooks'
        save_json(status_path, state)
        print(f"Suite status: {state['status']}. Results: {study / 'analysis' / 'RESULTS.md'}", flush=True)
        print('This small smoke sample supports debugging and descriptive comparisons, not significance claims.', flush=True)
        print('Jupyter execution remains a separate verification step.', flush=True)
        return 0 if state['status'] == 'completed' else 2
    except (Exception, KeyboardInterrupt) as exc:
        # Do not expose request headers, environment contents, or raw provider errors.
        message = 'Interrupted; saved completed conditions can be reused.' if isinstance(exc, KeyboardInterrupt) else str(exc)
        for name in ('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'SEMANTIC_SCHOLAR_API_KEY'):
            if os.getenv(name):
                message = message.replace(os.environ[name], '[REDACTED]')
        state.update(status='blocked_or_failed', finished_at=utcnow(), error=message)
        save_json(status_path, state)
        print(f"Stopped during {state['stage']}: {message}", file=sys.stderr, flush=True)
        print(f'Saved status: {status_path}', file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
