import json
import pytest
from research_review.schemas import Review,Evidence,Judgment
from research_review.literature_retrieval import LiteratureRetriever,RetrievalError,verify_evidence,parse_arxiv,unique_papers
from research_review.reviewer_agents import aggregate_feedback

@pytest.mark.parametrize('score',[0,6,3.5,'4',True])
def test_scores_reject_out_of_range_and_non_integer(score):
    with pytest.raises(ValueError):
        Review(role='novelty',novelty=score,explanation='x',problems=['p'],improvements=['i'],uncertainty='u')

def test_role_specific_scores_required():
    with pytest.raises(ValueError):Review(role='clarity',clarity=3,explanation='x',problems=['p'],improvements=['i'],uncertainty='u')

def test_evidence_ids_and_excerpt_checked(paper):
    good=Evidence(paper_id=paper.paper_id,claim='x',supporting_excerpt='controlled comparison of retrieval methods',relation='context')
    verify_evidence([good],[paper])
    with pytest.raises(ValueError):verify_evidence([good.model_copy(update={'paper_id':'invented'})],[paper])
    with pytest.raises(ValueError):verify_evidence([good.model_copy(update={'supporting_excerpt':'invented abstract quotation'})],[paper])

def test_deduplication(paper):
    assert len(unique_papers([paper,paper.model_copy(update={'paper_id':'another-id'})]))==1

def test_search_cache_preserves_provenance(tmp_path):
    calls=[]
    def transport(url,headers):
        calls.append(url)
        return json.dumps({'data':[{'paperId':'real-returned-id','title':'Returned title','abstract':'Returned abstract','authors':[{'name':'Author'}],'year':2024,'externalIds':{'DOI':'10.test/value'}}]})
    r=LiteratureRetriever(tmp_path,transport=transport)
    first=r.search('test query');second=r.search('test query')
    assert first.status=='ok' and second.cache_hit and len(calls)==1
    assert first.papers[0].doi=='10.test/value'

def test_retrieval_failure_not_cached(tmp_path):
    def fail(*args):raise RetrievalError('Synthetic network failure')
    r=LiteratureRetriever(tmp_path,transport=fail)
    assert r.search('query').status=='failed'
    assert not list(tmp_path.glob('*.json'))
    assert len(r.related('query'))==2

def test_arxiv_xml_parser():
    xml='''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/1234.5678v1</id><title>Title</title><published>2024-01-01</published><summary>Abstract</summary><author><name>Author</name></author></entry></feed>'''
    paper=parse_arxiv(xml,'now')[0]
    assert paper.year==2024 and paper.authors==['Author']

def test_disagreements_are_preserved():
    from research_review.schemas import ReviewOutcome
    def review(role,score):return Review(role=role,novelty=score,feasibility=3,clarity=3,importance=3,explanation='x',problems=['p'],improvements=['i'],uncertainty='u')
    result=aggregate_feedback([ReviewOutcome(role='generic',review=review('generic',1)),ReviewOutcome(role='novelty',review=review('novelty',5))])
    assert len(result['independent_reviews'])==2 and result['score_disagreements']
