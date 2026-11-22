import pytest
from research_review.config import Settings,CONFIGURATIONS,budget
from research_review.orchestration import Workflow
from research_review.evaluation import evaluate_runs,prepare_blind_items
from research_review.reviewer_agents import aggregate_feedback
from conftest import FixtureClient,FixtureRetriever

@pytest.mark.parametrize('condition',list(CONFIGURATIONS))
def test_bounded_workflow_and_shared_initial(condition,idea,paper):
    client=FixtureClient(idea);retriever=FixtureRetriever(paper)
    run=Workflow(client,retriever,Settings(rounds=3,engine='python')).run('s',condition,idea,[paper])
    assert run.initial_idea==idea
    assert len(run.rounds)==(0 if condition=='one_shot' else 3)
    assert len(client.events)==(0 if condition=='one_shot' else 3*(len(CONFIGURATIONS[condition])+1))
    assert bool(retriever.calls)==(condition not in ['one_shot','generic','generic_matched','no_novelty_retrieval'])
    for label,content in client.inputs:
        if 'review' in label:
            assert 'feedback' not in content
            assert 'reviews' not in content

@pytest.mark.parametrize('rounds',[0,1,2,3])
def test_round_limits(rounds,idea,paper):
    run=Workflow(FixtureClient(idea),FixtureRetriever(paper),Settings(rounds=rounds,engine='python')).run('s','full',idea,[paper])
    assert len(run.rounds)==rounds

@pytest.mark.parametrize('rounds',[-1,4,100])
def test_invalid_limits(rounds):
    with pytest.raises(ValueError):Settings(rounds=rounds)

def test_early_stop_on_unchanged_proposal(idea,paper):
    r=Workflow(FixtureClient(idea,unchanged=True),FixtureRetriever(paper),Settings(engine='python')).run('s','full',idea,[paper])
    assert len(r.rounds)==1 and r.stop_reason=='unchanged_proposal'

def test_reviewer_failure_does_not_discard_other_reviews(idea,paper):
    r=Workflow(FixtureClient(idea,fail_roles=['feasibility']),FixtureRetriever(paper),Settings(rounds=1,engine='python')).run('s','full',idea,[paper])
    assert r.rounds[0].reviews[1].error
    assert r.rounds[0].revised_idea
    assert len(r.rounds[0].aggregation['independent_reviews'])==3

def test_all_failed_reviewers_stop(idea,paper):
    r=Workflow(FixtureClient(idea,fail_roles=list(CONFIGURATIONS['full'])),FixtureRetriever(paper),Settings(engine='python')).run('s','full',idea,[paper])
    assert len(r.rounds)==1 and r.stop_reason=='all_reviewers_failed'

def test_revision_failure_retains_last_valid_idea(idea,paper):
    r=Workflow(FixtureClient(idea,fail_revision=True),FixtureRetriever(paper),Settings(engine='python')).run('s','full',idea,[paper])
    assert r.stop_reason=='revision_failed' and r.final_idea==idea

def test_novelty_withheld_without_search_evidence(idea,paper):
    r=Workflow(FixtureClient(idea),FixtureRetriever(paper,empty=True),Settings(rounds=1,engine='python')).run('s','full',idea,[paper])
    assert r.rounds[0].reviews[0].review is None
    assert r.rounds[0].reviews[0].evidence_status=='unavailable'

def test_blind_judge_refuses_fixture_runs(idea,paper,tmp_path):
    r=Workflow(FixtureClient(idea),FixtureRetriever(paper),Settings(engine='python')).run('s','one_shot',idea,[paper])
    with pytest.raises(ValueError,match='fixtures'):evaluate_runs([r],None,None,Settings(),tmp_path)

def test_save_and_no_overwrite(idea,paper,tmp_path):
    workflow=Workflow(FixtureClient(idea),FixtureRetriever(paper),Settings(engine='python'))
    r=workflow.run('s','one_shot',idea,[paper],tmp_path)
    assert (tmp_path/(r.run_id+'.json')).exists()
    with pytest.raises(FileExistsError):workflow.run('s','one_shot',idea,[paper],tmp_path)

def test_reviewer_scores_not_used_in_blinding(idea,paper):
    r=Workflow(FixtureClient(idea),FixtureRetriever(paper),Settings(rounds=1,engine='python')).run('s','full',idea,[paper])
    items=prepare_blind_items([r],42)
    assert len(items)==2
    assert all('reviews' not in i and 'aggregation' not in i for i in items)

def test_budget_exact():
    assert budget(2)['total_calls_upper_bound']==298

def test_langgraph_engine_when_installed(idea,paper):
    pytest.importorskip('langgraph')
    r=Workflow(FixtureClient(idea),FixtureRetriever(paper),Settings(rounds=3,engine='langgraph')).run('s','full',idea,[paper])
    assert len(r.rounds)==3

def test_blind_items_include_all_candidates_for_all_conditions(idea,paper):
    runs=[]
    for config in CONFIGURATIONS:
        runs.append(Workflow(FixtureClient(idea),FixtureRetriever(paper),Settings(rounds=3,engine='python')).run('s',config,idea,[paper]))
    items=prepare_blind_items(runs,42)
    assert len([i for i in items if i['configuration']=='full'])==4
    assert len([i for i in items if i['configuration']=='generic'])==4
    # Identical synthetic candidate content is still deduplicated.
    assert len({i['blind_id'] for i in items})<=8
