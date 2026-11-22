import json
import pytest
from research_review.proposal_checks import named_model_mentions,experiment_checks,searchable_entity
from research_review.schemas import Idea
from research_review.config import ROOT
from research_review.factual_verification import verify_proposal,acceptance_issue
from research_review.online_sources import OnlineSources
from conftest import FixtureClient,FixtureRetriever

@pytest.mark.parametrize('entity',['Logits or token-level masks','Public JSON extraction datasets','Hugging Face runtime','off-the-shelf instruction-tuned model'])
def test_generic_lookup_does_not_hit_network(entity,tmp_path):
    def fail(url):raise AssertionError('Generic entity reached HTTP')
    assert not searchable_entity(entity)
    assert OnlineSources(tmp_path,fetch=fail).lookup(entity,'model')['status']=='needs_specific_entity'

def quantization_idea(idea):
    return idea.model_copy(update={'research_problem':'Does quantization affect schema validity?',
        'methodology':'Compare FP16, INT8 and INT4.',
        'experimental_setup':'Use Llama-3-8B on a 12 GB GPU.',
        'minimum_test':'Evaluate a 4-bit model with and without constrained decoding.'})

def test_explicit_name_is_recovered_and_missing_controls_flagged(idea):
    proposal=quantization_idea(idea)
    assert ('Llama-3-8B','Llama-3-8B') in named_model_mentions(proposal)
    codes={c['code'] for c in experiment_checks(proposal)}
    assert {'precision_memory_plan','missing_precision_control'}<=codes

def test_smaller_model_and_reference_clear_specific_checks(idea):
    proposal=quantization_idea(idea).model_copy(update={'experimental_setup':'Use Llama-3-3B on a 12 GB GPU.',
        'minimum_test':'Compare FP16 and INT4 with identical model weights and inputs.'})
    assert not experiment_checks(proposal)

def test_omitted_model_enters_verification_and_lookup(idea,paper):
    proposal=quantization_idea(idea)
    class Online:
        def __init__(self):self.calls=[]
        def lookup(self,entity,kind):
            self.calls.append((entity,kind))
            return {'entity':entity,'kind':kind,'status':'not_found','sources':[]}
    online=Online()
    report=verify_proposal(FixtureClient(proposal),FixtureRetriever(paper),proposal,[paper],online=online)
    assert ('Llama-3-8B','model') in online.calls
    assert any(c['entity']=='Llama-3-8B' for c in report.claims)
    assert 'Experimental design requires repair' in acceptance_issue(report)

def test_actual_trace_regression_offline():
    path=ROOT/'research-review-0be0f4db5ca65dd08f70.json'
    if not path.exists():pytest.skip('Optional user export')
    run=json.loads(path.read_text())['result']
    idea=Idea.model_validate(run['initial_idea'])
    assert any(name=='Llama-3-8B' for name,_ in named_model_mentions(idea))
    assert {'precision_memory_plan','missing_precision_control'}<={x['code'] for x in experiment_checks(idea)}

def test_explicit_offload_is_a_measurement_requirement_not_impossible_claim(idea):
    proposal=quantization_idea(idea).model_copy(update={'methodology':'Compare FP16 with CPU offload and INT4 on GPU.'})
    finding=next(c for c in experiment_checks(proposal) if c['code']=='precision_memory_plan')
    assert finding['severity']=='needs_resolution'

def test_generic_capability_paper_cannot_verify_specific_implementation(idea,paper):
    class Client(FixtureClient):
        def generate(self,schema,instruction,content,label,model=None):
            if label=='dependency_extraction':
                return schema(claims=[dict(claim='Logits are available',proposal_excerpt=idea.methodology,
                    entity='Logits or token-level masks',category='model_capability',required_value='access',essential=True)])
            if label=='dependency_verification':
                return schema(verdicts=[dict(claim_id=content['claims'][0]['claim_id'],verdict='supported',
                    source_ids=[paper.paper_id],supporting_excerpt=paper.abstract,explanation='Synthetic generic citation',repair='Check runtime')])
            return super().generate(schema,instruction,content,label,model)
    report=verify_proposal(Client(idea),FixtureRetriever(paper),idea,[paper])
    assert report.claims[0]['verdict']=='unverified'
    assert report.claims[0]['verification_method']=='entity_specific_support_required'
