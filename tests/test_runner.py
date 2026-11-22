"""Synthetic orchestration checks; never treated as experiment findings."""
from types import SimpleNamespace

from research_review import runner
from research_review.config import CONFIGURATIONS, Settings
from research_review.orchestration import Workflow
from research_review.storage import load_json
from conftest import FixtureClient, FixtureRetriever


def test_suite_marks_complete_only_when_all_conditions_are_scored(idea, paper):
    runs = [Workflow(FixtureClient(idea), FixtureRetriever(paper),
                     Settings(rounds=1, engine='python')).run(paper.paper_id, name, idea, [paper])
            for name in CONFIGURATIONS]
    rows = [{'seed_id': r.seed_id, 'configuration': r.configuration,
             'replicate': 0, 'is_final': True, 'judge_error': None} for r in runs]
    result = runner.assess_completion(runs, rows, {'status': 'analyzed'}, [paper], 1)
    assert result['status'] == 'completed'
    incomplete = runner.assess_completion(runs, rows[:-1], {'status': 'analyzed'}, [paper], 1)
    assert incomplete['status'] == 'completed_with_failures'
    assert len(incomplete['unscored_final_configurations']) == 1


def test_suite_preserves_failed_reviewer_in_completion_status(idea, paper):
    run = Workflow(FixtureClient(idea, fail_roles=['feasibility']), FixtureRetriever(paper),
                   Settings(rounds=1, engine='python')).run(paper.paper_id, 'full', idea, [paper])
    result = runner.assess_completion([run], [], {'status': 'analyzed'}, [paper], 1)
    assert result['reviewer_failures'] == 1
    assert result['status'] == 'completed_with_failures'


def test_retrieval_gate_refuses_empty_sources():
    class EmptyRetriever:
        def related(self, *args, **kwargs):
            return [SimpleNamespace(papers=[])]
        def search(self, *args, **kwargs):
            return SimpleNamespace(papers=[])
    import pytest
    with pytest.raises(RuntimeError, match='No model experiments started'):
        runner.check_retrieval(EmptyRetriever(), 'test')


def test_missing_credentials_stop_before_model_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.Settings, 'from_env', lambda **kwargs: Settings(**kwargs))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    def forbidden_client(*args, **kwargs):
        raise AssertionError('No model call should be attempted')
    monkeypatch.setattr(runner, 'ProgressClient', forbidden_client)
    assert runner.main(['--study', str(tmp_path)]) == 1
    state = load_json(tmp_path / 'suite_status.json')
    assert state['status'] == 'blocked_or_failed'
    assert state['stage'] == 'preflight'


def test_new_methodology_refuses_old_study_without_modifying_status(tmp_path,monkeypatch):
    from research_review.storage import save_json
    monkeypatch.setattr(runner.Settings,'from_env',lambda **kwargs:Settings(**kwargs))
    save_json(tmp_path/'manifest.json',{'specification':{'evidence_protocol':'passage_ids_v1','settings':{}}})
    save_json(tmp_path/'suite_status.json',{'status':'original_completed_state'})
    before=(tmp_path/'suite_status.json').read_bytes()
    assert runner.main(['--study',str(tmp_path)])==1
    assert (tmp_path/'suite_status.json').read_bytes()==before
