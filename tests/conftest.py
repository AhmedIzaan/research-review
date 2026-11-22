"""Synthetic fixtures for software tests only. Never experimental data."""
import pytest
from research_review.schemas import Idea,Paper,Review,SearchResult,ROLE_METRICS
from research_review.llm import LLMError

@pytest.fixture
def paper():
    return Paper(paper_id='fixture-paper',title='Synthetic test paper',authors=['Test Author'],year=2024,
        abstract='This synthetic abstract describes a controlled comparison of retrieval methods.',
        url='https://example.invalid/test',source='unit_test_fixture',retrieved_at='2026-11-07T00:00:00Z')

@pytest.fixture
def idea():
    return Idea(title='Synthetic test idea',research_problem='Synthetic test problem',research_gap='Synthetic gap',
        core_hypothesis='Fixture hypothesis',distinctive_mechanism='Fixture mechanism',minimum_test='Fixture minimum test',
        methodology='Compare methods',expected_contribution='Test coverage',experimental_setup='Fixture data',
        evaluation_strategy='Measure error',feasibility_assumptions=['Fixture only'],
        references=['fixture-paper'],search_queries=['synthetic retrieval'],
        assumption_checks=[{'assumption':'Fixture compute fits','validation_step':'Run a fixture memory check',
            'acceptance_criterion':'Peak memory below the fixture limit','fallback':'Reduce the fixture workload'}],
        prior_work_comparison=[{'paper_id':'fixture-paper','shared_mechanism':'Fixture retrieval',
            'proposed_difference':'A synthetic test comparison','verification_needed':'Check against the fixture source'}])

class FixtureClient:
    provenance='unit_test_fixture'
    def __init__(self,idea,fail_roles=(),unchanged=False,fail_revision=False):
        self.idea=idea;self.events=[];self.inputs=[];self.fail_roles=fail_roles
        self.unchanged=unchanged;self.fail_revision=fail_revision
    def generate(self,schema,instruction,content,label,model=None):
        self.events.append({'label':label,'status':'ok'})
        self.inputs.append((label,content))
        if issubclass(schema,Idea):
            if self.fail_revision:raise LLMError('Synthetic revision failure')
            if self.unchanged:return self.idea
            return self.idea.model_copy(update={'title':'Revised '+label})
        if label=='evidence_support_audit':
            return schema(assessments=[{'citation_id':c['citation_id'],'verdict':'partial',
                'explanation':'Synthetic audit fixture only'} for c in content['citations']],
                limitations='Synthetic fixture, not a scientific finding')
        if label.startswith('revision_guard_'):
            return schema(comparative_risks=[],mechanism_status='preserved',pivot_reason='No pivot',novelty='unchanged',
                feasibility='unchanged',clarity='improved',importance='unchanged',evidence_grounding='unchanged',
                explanation='Synthetic fixture only',uncertainty='Not empirical evidence')
        if label=='dependency_extraction':
            return schema(claims=[{'claim':'Fixture data availability','proposal_excerpt':content['proposal']['experimental_setup'],
                'entity':'fixture-paper','category':'dataset_access','required_value':'','essential':True}])
        if label=='dependency_verification':
            return schema(verdicts=[{'claim_id':c['claim_id'],'verdict':'unverified','source_ids':[],
                'supporting_excerpt':'','explanation':'Synthetic missing evidence','repair':'Verify access'} for c in content['claims']])
        role=content['role']
        if role in self.fail_roles:raise LLMError('Synthetic reviewer failure')
        scores={k:3 for k in ROLE_METRICS[role]}
        evidence=[]
        if role=='novelty':
            passage=next(p for paper in content['literature'] if paper['paper_id']=='fixture-paper'
                         for p in paper['passages'])
            evidence=[{'passage_id':passage['passage_id'],'claim':'Test overlap','relation':'overlaps'}]
        return schema(role=role,**scores,explanation='Fixture review',problems=['Fixture weakness'],
                      improvements=['Fixture change'],uncertainty='Fixture only',evidence=evidence,
                      falsification_test='A synthetic falsification test' if role=='contrarian' else None,
                      tradeoffs=['Fixture novelty versus scope tension'])

class FixtureRetriever:
    def __init__(self,paper,empty=False):self.paper=paper;self.calls=[];self.empty=empty;self.log=[]
    def related(self,query,limit=5):
        self.calls.append(query)
        return [SearchResult(query=query,provider='fixture',retrieved_at='2026-11-07',
             papers=[] if self.empty else [self.paper],status='empty' if self.empty else 'ok')]
