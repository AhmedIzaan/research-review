import json
from pathlib import Path
import pytest
from research_review.online_sources import OnlineSources,public_get
SHA='a'*40

def fake_fetch(url):
    if '?search=' in url:return json.dumps([{'id':'publisher/ag_news'}])
    if '/api/datasets/' in url:return json.dumps({'id':'publisher/ag_news','sha':SHA,'private':False,'gated':False,'cardData':{'language':['en'],'task_categories':['text-classification']}})
    if '/resolve/' in url:return '# Fixture dataset card\nThis synthetic dataset has text and class labels.'
    raise AssertionError(url)

def test_metadata_card_and_immutable_cache(tmp_path):
    calls=[]
    def fetch(url):calls.append(url);return fake_fetch(url)
    lookup=OnlineSources(tmp_path,fetch=fetch)
    result=lookup.lookup('AG News','dataset')
    assert result['status']=='retrieved' and len(result['sources'])==2
    assert result['sources'][0]['revision']==SHA
    assert all(s['facts']=={} for s in result['sources']) # tags are not exhaustive coverage
    count=len(calls)
    assert lookup.lookup('AG News','dataset')['cache_hit']
    assert len(calls)==count

def test_ambiguous_repositories_are_not_silently_selected(tmp_path):
    lookup=OnlineSources(tmp_path,fetch=lambda _:json.dumps([{'id':'one/ag_news'},{'id':'two/ag_news'}]))
    result=lookup.lookup('AG News','dataset')
    assert result['status']=='ambiguous' and not result['sources']

def test_explicit_repository_and_linked_github(tmp_path):
    import base64
    def fetch(url):
        if '/resolve/' in url:return 'Project: https://github.com/publisher/project'
        if 'api.github.com' in url:return json.dumps({'encoding':'base64','content':base64.b64encode(b'Synthetic README').decode(),'sha':'b'*40,'html_url':'https://github.com/publisher/project/blob/main/README.md'})
        return fake_fetch(url)
    result=OnlineSources(tmp_path,fetch=fetch).lookup('publisher/ag_news','dataset')
    assert len(result['sources'])==3
    assert result['sources'][-1]['kind']=='linked_github_readme'

def test_failure_and_request_budget_are_explicit(tmp_path):
    def fail(url):raise OSError('Synthetic offline')
    result=OnlineSources(tmp_path,fetch=fail).lookup('AG News','dataset')
    assert result['status']=='unavailable' and result['errors'] and not result['sources']
    result=OnlineSources(tmp_path/'limited',fetch=fake_fetch,max_requests=1).lookup('AG News','dataset')
    assert result['status']=='unavailable' and result['errors']

@pytest.mark.parametrize('url',['http://huggingface.co/a','https://localhost/a','https://huggingface.co@evil.example/a','https://api.github.com:8443/a'])
def test_disallowed_urls_rejected_before_network(url):
    with pytest.raises(ValueError,match='Disallowed'):public_get(url)

def test_cached_text_tampering_fails(tmp_path):
    lookup=OnlineSources(tmp_path,fetch=fake_fetch);lookup.lookup('AG News','dataset')
    path=next(tmp_path.glob('*.json'));record=json.loads(path.read_text());record['sources'][0]['text']='Changed';path.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='integrity'):lookup.lookup('AG News','dataset')

def test_verifier_receives_online_documents_without_reviewer_scores(idea,paper,tmp_path):
    from research_review.factual_verification import verify_proposal
    from conftest import FixtureClient,FixtureRetriever
    class Client(FixtureClient):
        def generate(self,schema,instruction,content,label,model=None):
            if label=='dependency_extraction':
                return schema(claims=[{'claim':'AG News provides classification examples','proposal_excerpt':idea.experimental_setup,
                    'entity':'AG News','category':'dataset_task','required_value':'text classification','essential':True}])
            return super().generate(schema,instruction,content,label,model)
    client=Client(idea)
    report=verify_proposal(client,FixtureRetriever(paper),idea,[paper],online=OnlineSources(tmp_path,fetch=fake_fetch))
    assert report.online_lookups[0]['status']=='retrieved'
    assert any(s['kind']=='repository_card' for s in report.sources)
    payload=next(c for label,c in client.inputs if label=='dependency_verification')
    assert 'feedback' not in payload and 'scores' not in payload
    assert payload['online_lookup_status'][0]['status']=='retrieved'
