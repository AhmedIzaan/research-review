"""Regression checks for v8; fixtures and replay are not live research results."""
import json
from pathlib import Path
import pytest
from research_review.schemas import Idea
from research_review.proposal_checks import experiment_checks, revision_changes, constructed_dataset_claim
from research_review.factual_verification import verify_proposal
from research_review.orchestration import Workflow
from research_review.config import Settings
from conftest import FixtureClient, FixtureRetriever


def test_literature_only_candidate_is_retained_but_not_accepted(idea, paper):
    class Client(FixtureClient):
        def generate(self, schema, instruction, content, label, model=None):
            if label=='revision_1':
                return idea.model_copy(update={'search_queries':['a more specific search']})
            return super().generate(schema,instruction,content,label,model)
    client=Client(idea)
    run=Workflow(client,FixtureRetriever(paper),Settings(engine='python',revision_policy='guarded',rounds=1)).run('s','full',idea,[paper])
    assert run.final_idea==idea
    assert run.rounds[0].selection=='rejected'
    assert run.rounds[0].candidate_idea is not None
    assert run.rounds[0].revision_changes['literature_only']
    assert not any(e['label'].startswith('revision_guard') for e in client.events)


def test_real_trace_replay_detects_original_failures():
    path=Path('research-review-13b8da15e4534da66906.json')
    if not path.exists():pytest.skip('Optional historical trace not distributed')
    run=json.loads(path.read_text())['result']
    before,after=(Idea.model_validate(run[k]) for k in ('initial_idea','final_idea'))
    assert revision_changes(before,after)['literature_only']
    codes={c['code'] for c in experiment_checks(after)}
    assert {'hypothesis_as_prerequisite','explanation_measure_validation','persuasiveness_not_operationalized'}<=codes


def test_generated_data_not_searched_as_existing_repository(idea,paper):
    idea=idea.model_copy(update={'methodology':'We construct synthetic examples with a seeded logical oracle.'})
    class Client(FixtureClient):
        def generate(self,schema,instruction,content,label,model=None):
            if label=='dependency_extraction':
                return schema(claims=[dict(claim='Synthetic dataset available',
                    proposal_excerpt=idea.methodology,entity='synthetic rule-based classification dataset',
                    category='dataset_access',required_value='available',essential=True)])
            return super().generate(schema,instruction,content,label,model)
    class NoLookup:
        def lookup(self,*args):raise AssertionError('Constructed data must not trigger a repository search')
    retriever=FixtureRetriever(paper)
    report=verify_proposal(Client(idea),retriever,idea,[paper],online=NoLookup())
    assert report.claims[0]['category']=='dataset_construction'
    assert report.claims[0]['verdict']=='requires_measurement'
    assert report.claims[0]['verification_method']=='construction_validation_required'
    assert not retriever.calls and not report.online_lookups


def test_named_synthetic_benchmark_is_not_reclassified(idea):
    idea=idea.model_copy(update={'methodology':'We construct perturbations of an existing benchmark.'})
    assert not constructed_dataset_claim({'entity':'SyntheticNLI','category':'dataset_access'},idea)
    assert not constructed_dataset_claim({'entity':'org/synthetic-dataset','category':'dataset_access'},idea)


def test_resource_pilot_threshold_is_allowed(idea):
    assert 'hypothesis_as_prerequisite' not in {x['code'] for x in experiment_checks(idea)}


def test_lexical_metric_with_human_validation_not_automatically_blocked(idea):
    idea=idea.model_copy(update={'research_problem':'Test explanation rule tracking.',
        'evaluation_strategy':'Report token-overlap, validate against blinded human annotations, and include paraphrase controls.'})
    assert 'explanation_measure_validation' not in {x['code'] for x in experiment_checks(idea)}


def test_method_change_is_not_bibliography_only(idea):
    after=idea.model_copy(update={'evaluation_strategy':'Measure error against a held-out annotation oracle.'})
    audit=revision_changes(idea,after)
    assert not audit['literature_only']
    assert audit['field_changes']['evaluation_strategy']['before']==idea.evaluation_strategy
