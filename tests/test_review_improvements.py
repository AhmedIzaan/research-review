"""Regression tests for the weaknesses observed in the real RAG demo trace."""
import json

import pytest
from pydantic import ValidationError

from research_review.config import ROOT, Settings
from research_review.evidence_catalog import make_catalog, wire_schema
from research_review.evidence_audit import audit_claim_support, collect_citations
from research_review.idea_generator import generate_idea, validate_comparisons
from research_review.llm import BudgetExceeded, GeminiClient, LLMError
from research_review.orchestration import Workflow
from research_review.reviewer_agents import aggregate_feedback
from research_review.schemas import Idea, ProposalDraft, Review, ReviewOutcome, ROLE_METRICS, Run
from conftest import FixtureClient, FixtureRetriever


@pytest.mark.parametrize('role',list(ROLE_METRICS))
def test_provider_schema_forbids_off_role_scores(role,paper):
    catalog,_=make_catalog([paper])
    schema=wire_schema(Review,catalog,expected_role=role)
    data=dict(role=role,explanation='Fixture',problems=['Fixture'],improvements=['Fixture'],
              uncertainty='Fixture',falsification_test='Fixture falsification' if role=='contrarian' else None,
              **{metric:3 for metric in ROLE_METRICS[role]})
    schema(**data)
    for metric in {'novelty','feasibility','clarity','importance'}-set(ROLE_METRICS[role]):
        with pytest.raises(ValidationError):
            schema(**{**data,metric:4})


def test_wrong_dimension_triggers_existing_provider_validation_retry(paper):
    catalog,_=make_catalog([paper])
    schema=wire_schema(Review,catalog,expected_role='novelty')
    counter=[]
    def transport(model,payload):
        counter.append(payload)
        data=dict(role='novelty',novelty=2,explanation='Fixture',problems=['Fixture'],
                  improvements=['Fixture'],uncertainty='Fixture')
        if len(counter)==1:
            data['feasibility']=4
        return {'candidates':[{'content':{'parts':[{'text':json.dumps(data)}]}}]}
    client=GeminiClient(Settings(request_interval=0),None,transport=transport,sleep=lambda _:None)
    reply=client.generate(schema,'fixture',{},'fixture')
    assert reply.novelty==2 and reply.feasibility is None
    assert len(client.events)==2 and client.events[0]['validation_failure']


def test_proposal_requires_operational_checks_but_old_schema_is_readable(idea):
    legacy=idea.model_dump(exclude={'assumption_checks','prior_work_comparison'})
    assert Idea.model_validate(legacy).assumption_checks==[]
    with pytest.raises(ValidationError):
        ProposalDraft.model_validate(legacy)
    assert ProposalDraft.model_validate(idea.model_dump()).assumption_checks[0].fallback


def test_invented_prior_work_comparison_rejected(idea,paper):
    bad=idea.model_copy(deep=True)
    bad.prior_work_comparison[0].paper_id='invented-paper'
    with pytest.raises(ValueError,match='unsupplied'):
        validate_comparisons(bad,[paper])


def test_generation_prompt_demands_unexecuted_checks_and_qualified_gaps(idea,paper):
    class Capture(FixtureClient):
        def generate(self,schema,instruction,content,label,model=None):
            assert issubclass(schema,ProposalDraft)
            assert 'No resource checks or scientific experiments have run' in instruction
            assert 'fallback' in instruction and 'shared_mechanism' in instruction
            return schema.model_validate(idea.model_dump())
    assert generate_idea(Capture(idea),[paper],'Fixture constraints').assumption_checks


def test_final_panel_reviews_revised_idea_independently_and_searches_again(idea,paper):
    class ChangedQueries(FixtureClient):
        def generate(self,schema,instruction,content,label,model=None):
            reply=super().generate(schema,instruction,content,label,model)
            if label.startswith('revision_'):
                return reply.model_copy(update={'search_queries':['revised mechanism prior art']})
            return reply
    client=ChangedQueries(idea)
    retriever=FixtureRetriever(paper)
    settings=Settings(rounds=1,engine='python',final_review=True,audit_evidence=True)
    run=Workflow(client,retriever,settings).run('fixture','full',idea,[paper])
    assert run.final_review_status=='completed'
    assert len(run.rounds)==1 and len(run.final_reviews)==4
    assert retriever.calls[:2]==['synthetic retrieval','revised mechanism prior art']
    assert len(retriever.calls)==3 and run.final_idea.title in retriever.calls[-1]
    assessed=[content for label,content in client.inputs if label.endswith('_review_final')]
    assert len(assessed)==4
    assert all(c['proposal']==run.final_idea.model_dump() and 'feedback' not in c for c in assessed)
    assert all('reviews' not in c for c in assessed)
    assert run.evidence_audit and run.evidence_audit_citations
    for outcome in run.final_reviews:
        for metric in {'novelty','feasibility','clarity','importance'}-set(ROLE_METRICS[outcome.role]):
            assert getattr(outcome.review,metric) is None


def test_final_review_failure_retains_revised_proposal(idea,paper):
    class FinalFailure(FixtureClient):
        def generate(self,schema,instruction,content,label,model=None):
            if label=='feasibility_review_final':
                raise LLMError('Fixture final reviewer failure')
            return super().generate(schema,instruction,content,label,model)
    run=Workflow(FinalFailure(idea),FixtureRetriever(paper),
        Settings(rounds=1,engine='python',final_review=True)).run('fixture','full',idea,[paper])
    assert run.final_review_status=='partial'
    assert run.final_reviews[1].error=='Fixture final reviewer failure'
    assert run.final_idea==run.rounds[0].revised_idea
    assert run.initial_idea==idea


def test_final_budget_exhaustion_is_explicit_and_does_not_loop(idea,paper):
    class Capped(FixtureClient):
        def generate(self,schema,instruction,content,label,model=None):
            if len(self.events)>=6:
                raise BudgetExceeded('Fixture cap')
            return super().generate(schema,instruction,content,label,model)
    client=Capped(idea)
    run=Workflow(client,FixtureRetriever(paper),Settings(rounds=1,engine='python',
        final_review=True,audit_evidence=True)).run('fixture','full',idea,[paper])
    assert run.final_review_status=='partial' and len(run.final_reviews)==2
    assert run.final_reviews[1].error=='Fixture cap'
    assert run.evidence_audit_error=='Fixture cap'
    assert len(client.events)==6


@pytest.mark.parametrize('configuration,rounds',[('one_shot',1),('full',0)])
def test_final_panel_skips_conditions_without_review_rounds(configuration,rounds,idea,paper):
    client=FixtureClient(idea)
    run=Workflow(client,FixtureRetriever(paper),Settings(rounds=rounds,engine='python',
        final_review=True,audit_evidence=True)).run('fixture',configuration,idea,[paper])
    assert run.final_review_status=='skipped' and not run.final_reviews
    assert not client.events


def test_aggregation_ignores_legacy_cross_scores_and_retains_text():
    novelty=Review(role='novelty',novelty=2,feasibility=5,explanation='Fixture',problems=['Overlap'],
                   improvements=['Different mechanism'],uncertainty='Fixture',tradeoffs=['Novelty versus scope'])
    feasibility=Review(role='feasibility',feasibility=2,novelty=5,explanation='Fixture',problems=['Too costly'],
                       improvements=['Narrow scope'],uncertainty='Fixture')
    agg=aggregate_feedback([ReviewOutcome(role='novelty',review=novelty),
                            ReviewOutcome(role='feasibility',review=feasibility)])
    assert agg['scores_by_role']['novelty']=={'novelty':2}
    assert agg['scores_by_role']['feasibility']=={'feasibility':2}
    assert len(agg['independent_reviews'])==2
    assert agg['qualitative_tradeoffs']==[{'role':'novelty','tension':'Novelty versus scope'}]


def test_support_audit_is_blind_to_review_scores_and_feedback(idea,paper):
    client=FixtureClient(idea)
    run=Workflow(client,FixtureRetriever(paper),Settings(rounds=1,engine='python')).run('fixture','full',idea,[paper])
    audit=audit_claim_support(client,run.rounds[0].reviews,[paper])
    assert audit.assessments[0].verdict=='partial'
    payload=client.inputs[-1][1]
    assert set(payload)=={'citations'}
    assert all('source_abstract' in item for item in payload['citations'])
    assert all('role' not in item and 'novelty' not in item for item in payload['citations'])
    assert {a.citation_id for a in audit.assessments}==set(collect_citations(run.rounds[0].reviews))


def test_support_audit_rejects_partial_inventory_and_invented_ids(idea,paper):
    run=Workflow(FixtureClient(idea),FixtureRetriever(paper),Settings(rounds=1,engine='python')).run('fixture','full',idea,[paper])
    class BadClient:
        def generate(self,schema,*args,**kwargs):
            return schema(assessments=[{'citation_id':'invented','verdict':'supported','explanation':'Fixture'}],
                          limitations='Fixture')
    with pytest.raises(ValidationError):
        audit_claim_support(BadClient(),run.rounds[0].reviews,[paper])


def test_user_original_rag_export_remains_readable():
    path=ROOT/'research-review-082836f447f4bec330ef.json'
    if not path.exists():
        pytest.skip('Original user export is optional in a clean clone')
    exported=json.loads(path.read_text())
    run=Run.model_validate(exported['result'])
    assert run.final_review_status=='not_requested' and not run.evidence_audit
    assert run.initial_idea.title.startswith('Evaluating Factual Reliability')
    assert run.rounds[0].reviews[0].review.feasibility==4  # Historical cross-score is preserved.


def test_support_audit_requires_every_citation_exactly_once(idea,paper):
    run=Workflow(FixtureClient(idea),FixtureRetriever(paper),Settings(rounds=1,engine='python')).run('fixture','full',idea,[paper])
    outcomes=run.rounds[0].reviews
    copied=outcomes[0].review.evidence[0].model_copy(update={'claim':'Another synthetic claim'})
    outcomes[0].review.evidence.append(copied)
    assert len(collect_citations(outcomes))==2
    class Incomplete:
        def generate(self,schema,instruction,content,label,model=None):
            item={'citation_id':content['citations'][0]['citation_id'],'verdict':'supported','explanation':'Fixture'}
            return schema(assessments=[item],limitations='Fixture')
    with pytest.raises(ValidationError):
        audit_claim_support(Incomplete(),outcomes,[paper])
    class Duplicate:
        def generate(self,schema,instruction,content,label,model=None):
            item={'citation_id':content['citations'][0]['citation_id'],'verdict':'supported','explanation':'Fixture'}
            return schema(assessments=[item,item],limitations='Fixture')
    with pytest.raises(ValidationError,match='exactly once'):
        audit_claim_support(Duplicate(),outcomes,[paper])
