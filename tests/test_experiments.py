from research_review.config import Settings,CONFIGURATIONS
from research_review.experiments import run_study
from research_review.schemas import Paper
from research_review.storage import load_json
from conftest import FixtureClient,FixtureRetriever

def test_study_reuses_initials_and_resumes_without_calls(idea,paper,tmp_path):
    client=FixtureClient(idea)
    settings=Settings(rounds=1,engine='python')
    runs=run_study([paper],client,FixtureRetriever(paper),settings,tmp_path)
    assert len(runs)==len(CONFIGURATIONS)
    assert len({r.initial_idea.model_dump_json() for r in runs})==1
    before=len(client.events)
    again=run_study([paper],client,FixtureRetriever(paper),settings,tmp_path)
    assert len(again)==len(CONFIGURATIONS) and len(client.events)==before

def test_dataset_has_twenty_distinct_real_source_records():
    from research_review.config import ROOT
    data=[Paper.model_validate(p) for p in load_json(ROOT/'data'/'seeds.json')]
    assert len(data)==20 and len({p.paper_id for p in data})==20
    assert all(p.abstract and p.authors and p.url.startswith('https://aclanthology.org/') for p in data)
