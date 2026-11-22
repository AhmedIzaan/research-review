"""Synthetic verifier tests; no experimental quality claims."""
import hashlib
import pytest
from research_review.factual_verification import verify_proposal,acceptance_issue,source_snapshot
from research_review.storage import save_json
from research_review.evidence_catalog import make_catalog
from research_review.orchestration import Workflow
from research_review.config import Settings
from research_review.evaluation import prepare_blind_items
from conftest import FixtureClient,FixtureRetriever

class ClaimsClient(FixtureClient):
    def __init__(self,idea,category='dataset_language',bad_quote=False):
        super().__init__(idea);self.category=category;self.bad_quote=bad_quote
    def generate(self,schema,instruction,content,label,model=None):
        if label=='dependency_extraction':
            return schema(claims=[dict(claim='Fixture supports Urdu',proposal_excerpt=content['proposal']['experimental_setup'],
                entity='FixtureBench',category=self.category,required_value='ur',essential=True)])
        if label=='dependency_verification':
            return schema(verdicts=[dict(claim_id=c['claim_id'],verdict='supported' if self.bad_quote else 'unverified',
                source_ids=['fixture-paper'] if self.bad_quote else [],supporting_excerpt='Invented excerpt' if self.bad_quote else '',
                explanation='Synthetic interpretation',repair='Find verified data') for c in content['claims']])
        return super().generate(schema,instruction,content,label,model)

def snapshot(tmp_path,languages,complete=True):
    text='Complete test language list: '+', '.join(languages)
    path=tmp_path/'sources.json'
    save_json(path,[dict(source_id='official_fixture',entity='FixtureBench',url='https://example.invalid/card',
        retrieved_at='fixture',text=text,sha256=hashlib.sha256(text.encode()).hexdigest(),
        facts={'languages':languages,'languages_complete':complete})])
    return path

@pytest.mark.parametrize('languages,expected',[(['en','fr'],'contradicted'),(['en','ur'],'supported')])
def test_exhaustive_metadata_overrides_model_guess(idea,paper,tmp_path,languages,expected):
    report=verify_proposal(ClaimsClient(idea),FixtureRetriever(paper),idea,[paper],snapshot(tmp_path,languages))
    assert report.claims[0]['verdict']==expected
    assert report.claims[0]['verification_method']=='structured_language_membership'
    assert bool(acceptance_issue(report))==(expected=='contradicted')

def test_nonexhaustive_missing_language_is_not_contradiction(idea,paper,tmp_path):
    report=verify_proposal(ClaimsClient(idea),FixtureRetriever(paper),idea,[paper],snapshot(tmp_path,['en'],False))
    assert report.claims[0]['verdict']=='unverified'

def test_resource_claims_require_actual_measurement(idea,paper):
    report=verify_proposal(ClaimsClient(idea,category='resource'),FixtureRetriever(paper),idea,[paper])
    assert report.claims[0]['verdict']=='requires_measurement'

def test_fabricated_quotes_and_tampered_snapshots_rejected(idea,paper,tmp_path):
    with pytest.raises(ValueError,match='exact source'):verify_proposal(ClaimsClient(idea,bad_quote=True),FixtureRetriever(paper),idea,[paper])
    path=snapshot(tmp_path,['ur']);path.write_text(path.read_text().replace('Complete test','Altered test'))
    with pytest.raises(ValueError,match='hash mismatch'):source_snapshot(path)

def test_dependency_contradiction_blocks_candidate_and_preserves_trace(idea,paper,tmp_path):
    settings=Settings(engine='python',rounds=3,verify_dependencies=True,verification_sources=str(snapshot(tmp_path,['en'])))
    run=Workflow(ClaimsClient(idea),FixtureRetriever(paper),settings).run('s','full',idea,[paper])
    assert run.stop_reason=='dependency_verification_rejected'
    assert run.final_idea==idea and run.rounds[0].candidate_idea
    assert run.final_verification['claims'][0]['verdict']=='contradicted'
    assert run.rounds[0].candidate_verification['claims'][0]['essential']

def test_unchanged_alias_does_not_steal_final_accepted_label(idea,paper):
    class Client(FixtureClient):
        def generate(self,*a,**kw):
            if a[3]=='revision_2':return self.idea.model_copy(update={'title':'Revised revision_1'})
            return super().generate(*a,**kw)
    run=Workflow(Client(idea),FixtureRetriever(paper),Settings(engine='python')).run('s','full',idea,[paper])
    items=prepare_blind_items([run],42)
    final=[i for i in items if i['is_final']]
    assert len(final)==1 and final[0]['round']==1 and final[0]['accepted']

def test_abbreviation_does_not_create_fragment(paper):
    text='Additionally, many low-resource languages (e.g. Urdu) need evaluation. Another complete sentence follows.'
    catalog,_=make_catalog([paper.model_copy(update={'abstract':text})])
    excerpts=[c['supporting_excerpt'] for c in catalog.values()]
    assert excerpts[0]=='Additionally, many low-resource languages (e.g. Urdu) need evaluation.'
    assert all(e in text for e in excerpts)
