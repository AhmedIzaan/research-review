"""Regression tests for the evidence gap observed in the second live RAG run."""
import json
from pathlib import Path

import pytest

from research_review.config import ROOT,Settings
from research_review.judge_retrieval import build_judge_context,judge_queries
from research_review.local_corpus import LocalCorpusRetriever
from research_review.schemas import SearchResult
from research_review.evaluation import evaluate_runs
from research_review.storage import load_json
from test_evaluation import synthetic_saved_runs,SyntheticJudge
from conftest import FixtureRetriever


def test_all_queries_and_proposed_mechanism_are_searched(idea,paper):
    proposal=idea.model_dump()
    proposal['search_queries']=['first broad query','second mechanism','third task']
    retriever=FixtureRetriever(paper)
    context=build_judge_context([proposal],retriever,[paper])
    assert retriever.calls[:3]==proposal['search_queries']
    assert proposal['title'] in retriever.calls[3]
    assert len(context['papers'])==1  # Duplicate hits are deduplicated.


def test_cited_and_compared_sources_are_loaded_without_query_hits(idea,paper):
    compared=paper.model_copy(update={'paper_id':'compared-source','title':'Compared source'})
    retriever=FixtureRetriever(paper,empty=True)
    retriever.papers=[paper,compared]
    proposal=idea.model_dump()
    proposal['prior_work_comparison'][0]['paper_id']=compared.paper_id
    context=build_judge_context([proposal],retriever)
    assert {p.paper_id for p in context['papers']}=={paper.paper_id,compared.paper_id}
    assert not context['coverage']['missing_cited_ids']


def test_context_limit_reports_missing_and_omitted_citations(idea,paper):
    other=paper.model_copy(update={'paper_id':'other-source'})
    retriever=FixtureRetriever(paper)
    retriever.papers=[paper,other]
    proposal=idea.model_dump()
    proposal['references']=[paper.paper_id,other.paper_id,'unavailable-source']
    context=build_judge_context([proposal],retriever,max_papers=1)
    assert len(context['papers'])==1
    assert context['coverage']['missing_cited_ids']==['unavailable-source']
    assert len(context['coverage']['omitted_cited_ids'])==1


def test_later_query_gets_context_space_when_first_query_has_many_hits(idea,paper):
    copies=[paper.model_copy(update={'paper_id':f'p{i}'}) for i in range(8)]
    class Search:
        def related(self,query,limit):
            return [SearchResult(query=query,provider='fixture',retrieved_at='fixture',status='ok',
                                 papers=copies[:5] if query=='broad' else copies[5:])]
    proposal=idea.model_dump();proposal['references']=[];proposal['prior_work_comparison']=[]
    proposal['search_queries']=['broad','specific']
    context=build_judge_context([proposal],Search(),max_papers=2)
    assert [p.paper_id for p in context['papers']]==['p0','p5']


def test_search_failure_is_recorded_not_misreported_as_zero_prior_art(idea,paper):
    class Broken:
        def related(self,*args,**kwargs):
            raise TimeoutError('fixture')
    context=build_judge_context([idea.model_dump()],Broken(),[paper])
    assert context['coverage']['search_failures']==len(context['queries'])
    assert context['papers']==[paper]
    assert all(s.status=='failed' for s in context['searches'])


def test_judge_uses_identical_context_for_initial_and_final_and_is_still_blind(idea,paper,tmp_path):
    runs=synthetic_saved_runs(idea,paper,tmp_path)
    judge=SyntheticJudge()
    evaluate_runs(runs,judge,FixtureRetriever(paper),Settings(),tmp_path/'evaluation')
    assert len(judge.contexts)>1
    assert len({json.dumps(c['literature'],sort_keys=True) for c in judge.contexts})==1
    assert all(set(c)=={'proposal','constraints','literature','search_status','retrieval_coverage','evidence_protocol'} for c in judge.contexts)
    records=[load_json(p) for p in (tmp_path/'evaluation'/'judgments').glob('*.json')]
    assert len({r['literature_context']['fingerprint'] for r in records})==1
    assert all(r['literature_context']['coverage']['query_count']>=2 for r in records)


def test_changed_context_refuses_cache_before_rewriting_old_outputs(idea,paper,tmp_path):
    runs=synthetic_saved_runs(idea,paper,tmp_path)
    output=tmp_path/'evaluation';settings=Settings()
    evaluate_runs(runs,SyntheticJudge(),FixtureRetriever(paper),settings,output)
    before={p.relative_to(output):p.read_bytes() for p in output.rglob('*.json')}
    changed=paper.model_copy(update={'abstract':paper.abstract+' Additional synthetic source context.'})
    judge=SyntheticJudge()
    with pytest.raises(ValueError,match='new evaluation directory'):
        evaluate_runs(runs,judge,FixtureRetriever(changed),settings,output)
    assert not judge.events
    assert all((output/name).read_bytes()==content for name,content in before.items())


def test_known_live_rag_example_now_includes_both_missing_close_matches():
    path=ROOT/'research-review-fff8592ef95a73dda616.json'
    if not path.exists():
        pytest.skip('User export optional in a clean checkout')
    run=load_json(path)['result']
    retriever=LocalCorpusRetriever(ROOT/'data/corpus/papers.json')
    proposals=[run['initial_idea'],run['final_idea']]
    context=build_judge_context(proposals,retriever)
    ids={p.paper_id for p in context['papers']}
    assert {'2025.naacl-short.50','2025.sdp-1.34'}<=ids
    assert context['coverage']['paper_count']<=24
    assert not context['coverage']['missing_cited_ids']
