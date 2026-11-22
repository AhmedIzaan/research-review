"""Judge/plot software integration uses synthetic data only in temporary directories."""
import pytest
from research_review.config import Settings,CONFIGURATIONS
from research_review.orchestration import Workflow
from research_review.schemas import Judgment
from research_review.evaluation import evaluate_runs,METRICS
from research_review.storage import save_json
from research_review.analysis import analyze
from conftest import FixtureClient,FixtureRetriever

class SyntheticJudge:
    def __init__(self):self.events=[];self.contexts=[]
    def generate(self,schema,instruction,content,label,model=None):
        self.contexts.append(content)
        self.events.append({'label':label})
        passage=next(p for paper in content['literature'] if paper['paper_id']=='fixture-paper'
                     for p in paper['passages'])
        return schema(**{m:3 for m in METRICS},rationale={m:'Synthetic testing rationale' for m in METRICS},
                        uncertainty='Synthetic unit test only',evidence=[{
                        'passage_id':passage['passage_id'],'claim':'Synthetic claim','relation':'context'}])

def synthetic_saved_runs(idea,paper,tmp_path):
    runs=[]
    for config in CONFIGURATIONS:
        r=Workflow(FixtureClient(idea),FixtureRetriever(paper),Settings(rounds=3,engine='python')).run('synthetic-seed',config,idea,[paper])
        # Exercise the provider boundary in an isolated unit-test directory; never export these as live findings.
        r=r.model_copy(update={'provenance':'live_gemini'})
        save_json(tmp_path/'runs'/f'{config}.json',r.model_dump())
        runs.append(r)
    return runs

def test_judge_blinding_cache_and_evidence(idea,paper,tmp_path):
    runs=synthetic_saved_runs(idea,paper,tmp_path)
    judge=SyntheticJudge();settings=Settings(rounds=3,engine='python')
    rows=evaluate_runs(runs,judge,FixtureRetriever(paper),settings,tmp_path/'evaluation')
    assert all(row['novelty']==3 for row in rows)
    assert len(judge.events)<=8
    assert all('configuration' not in c and 'feedback' not in c and 'reviews' not in c for c in judge.contexts)
    before=len(judge.events)
    evaluate_runs(runs,judge,FixtureRetriever(paper),settings,tmp_path/'evaluation')
    assert len(judge.events)==before
    assert (tmp_path/'evaluation'/'human_ratings.csv').exists()

def test_analysis_renders_from_test_scores_in_temporary_directory(idea,paper,tmp_path,monkeypatch):
    pytest.importorskip('pandas');pytest.importorskip('matplotlib')
    monkeypatch.setenv('MPLCONFIGDIR',str(tmp_path/'mpl_cache'))
    runs=synthetic_saved_runs(idea,paper,tmp_path)
    evaluate_runs(runs,SyntheticJudge(),FixtureRetriever(paper),Settings(engine='python'),tmp_path/'evaluation')
    result=analyze(tmp_path)
    assert result['status']=='analyzed' and result['n_seeds']==1
    assert len(list((tmp_path/'analysis').glob('*.png')))==5
    assert 'descriptive only' in (tmp_path/'analysis'/'paired_comparisons.csv').read_text()
    assert (tmp_path/'analysis'/'RESULTS.md').exists()
