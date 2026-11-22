"""Claim-level dependency checking against pinned sources, never model memory.

LLM interpretation is distinguished from exact structured metadata checks. Unknown
coverage stays unverified; resource sufficiency always requires measurement.
"""
import re
from pathlib import Path
from typing import Literal
from pydantic import Field
from .schemas import Record,Text
from .storage import digest,load_json
from .idea_generator import SAFETY
from .proposal_checks import named_model_mentions,searchable_entity,experiment_checks,constructed_dataset_claim

class DependencyClaim(Record):
    claim: Text
    proposal_excerpt: Text
    entity: Text
    category: Literal['dataset_language','dataset_task','dataset_access','model_access','model_capability','resource','dataset_construction']
    required_value: str = ''
    essential: bool

class ClaimExtraction(Record):
    claims: list[DependencyClaim] = Field(min_length=1,max_length=10)

class ClaimVerdict(Record):
    claim_id: Text
    verdict: Literal['supported','contradicted','unverified','requires_measurement']
    source_ids: list[str]
    supporting_excerpt: str
    explanation: Text
    repair: Text

class VerdictBatch(Record):
    verdicts: list[ClaimVerdict]

class VerificationReport(Record):
    proposal_hash: str
    status: Literal['completed','failed']
    claims: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    online_lookups: list[dict] = Field(default_factory=list)
    experiment_checks: list[dict] = Field(default_factory=list)
    error: str | None = None
    limitations: str = 'Bounded source coverage; LLM verdicts require human validation. Exact excerpts verify provenance, not semantic truth.'


def source_snapshot(path):
    """Reject altered or malformed snapshots rather than trust supplied metadata."""
    if not Path(path).exists():return []
    records=load_json(path)
    for source in records:
        required={'source_id','entity','url','retrieved_at','text','sha256','facts'}
        if not required<=source.keys():raise ValueError('Incomplete authoritative source snapshot')
        import hashlib
        if hashlib.sha256(source['text'].encode()).hexdigest()!=source['sha256']:
            raise ValueError('Authoritative source text hash mismatch')
        if not source['url'].startswith('https://'):raise ValueError('Source requires HTTPS attribution')
    return records


def verify_proposal(client,retriever,idea,literature,source_path=None,online=None):
    """Two model calls; extraction and verdicts are isolated from reviewer opinions."""
    extraction=client.generate(ClaimExtraction,SAFETY+'''
Extract up to ten concrete dependencies from this proposal. Include dataset language/task/access,
model availability and output capabilities, hardware sufficiency. Include every named dataset/model
central to execution. proposal_excerpt must be an exact substring of one proposal field.
For data that the proposal will create, use dataset_construction, not dataset_access.
This includes synthetic examples generated from templates: require a generator, label oracle,
seed and split validation; do not require a pre-existing publication or repository.
Named existing synthetic benchmarks still require dataset_access verification.
Extract atomic factual prerequisites, not whole experimental plans. For 'evaluate AG News using
4-shot prompts', extract 'AG News is accessible' and 'AG News has classification labels'; do NOT
require an existing paper to have used four-shot prompting. A model must have a specific name to
resolve online; preserve unnamed-model limitations. Split hardware sufficiency from model access.
Do not invent a dependency or treat a hypothesis as an established fact. Normalize required_value
for languages to an ISO code if known. essential means the proposed experiment depends on it.''',
        {'proposal':idea.model_dump(),'explicit_model_mentions':[name for name,_ in named_model_mentions(idea)]},'dependency_extraction')
    texts=[str(v) for v in idea.model_dump().values()]
    claims=[]
    for c in extraction.claims:
        if not any(c.proposal_excerpt in t for t in texts):
            raise ValueError('Extracted dependency is not anchored in proposal text')
        claims.append({'claim_id':'dep_'+digest(c.model_dump())[:16],**c.model_dump()})
    for claim in claims:
        if constructed_dataset_claim(claim,idea):
            claim['category']='dataset_construction'
    # Recover explicit model mentions even when the model extractor overlooks them.
    for entity,excerpt in named_model_mentions(idea):
        if not any(c['entity'].casefold()==entity.casefold() and c['category']=='model_access' for c in claims):
            c=DependencyClaim(claim=f'The named model {entity} is available through the proposed access route.',
                proposal_excerpt=excerpt,entity=entity,category='model_access',required_value='access',essential=True)
            claims.append({'claim_id':'dep_'+digest(c.model_dump())[:16],**c.model_dump()})
    checks=experiment_checks(idea)
    if len({c['claim_id'] for c in claims})!=len(claims):raise ValueError('Duplicate dependency claim')
    lookups=[]
    if online:
        entities=sorted({(c['entity'],'dataset' if c['category'].startswith('dataset') else 'model')
                         for c in claims if c['category'] not in ('resource','dataset_construction')})
        for entity,kind in entities:
            if not searchable_entity(entity):
                lookups.append({'entity':entity,'kind':kind,'status':'needs_specific_entity','sources':[],
                    'candidates':[],'errors':['Generic concept is not a repository identity. Specify a model or dataset.'],'cache_hit':False})
            elif sum(x['status']!='needs_specific_entity' for x in lookups)<5:
                lookups.append(online.lookup(entity,kind))
            else:
                lookups.append({'entity':entity,'kind':kind,'status':'budget_skipped','sources':[],
                    'candidates':[],'errors':['Entity lookup limit reached; unresolved.'],'cache_hit':False})
    sources=[s for lookup in lookups for s in lookup['sources']]
    for p in literature:
        sources.append({'source_id':p.paper_id,'entity':p.title,'url':p.url,
                        'retrieved_at':p.retrieved_at,'text':p.abstract,'facts':{},'kind':'paper_abstract'})
    for c in claims:
        if c['category']=='dataset_construction':continue
        for search in retriever.related(c['entity'],limit=3):
            for p in search.papers:
                sources.append({'source_id':p.paper_id,'entity':p.title,'url':p.url,
                                'retrieved_at':p.retrieved_at,'text':p.abstract,'facts':{},'kind':'paper_abstract'})
    snapshots=source_snapshot(source_path) if source_path else []
    entities={c['entity'].casefold() for c in claims}
    sources += [s for s in snapshots if s['entity'].casefold() in entities or
                entities.intersection(a.casefold() for a in s.get('aliases',[]))]
    sources=list({s['source_id']:s for s in sources}.values())
    response=client.generate(VerdictBatch,SAFETY+'''
Verify each supplied claim against the supplied sources only, without reviewer scores.
For dataset_construction use requires_measurement: validate generator reproducibility,
logical label oracle, valid interventions and template-disjoint held-out splits.
For planned model output quality or formatting, require a capability pilot, not proof of the desired result.
Verify factual prerequisites separately from planned interventions. Do not demand precedent for
shot count, permutation count or a new experiment. A hosting platform is not proof of original-author
ownership. Check repository identity/version; if ambiguous keep unverified. Metadata omissions do
not mean a capability or language is absent. A public card does not imply ungated data access.
Return exactly one verdict for every claim_id. Supported requires direct evidence for the exact
entity, version, language, task and access claim. A nearby task or another transfer direction is not
support. Absence of a language from an abstract is not a contradiction unless coverage is explicitly
exhaustive. Missing evidence is unverified. Hardware fit, runtime, quality and sample sufficiency
require measurement, even when quantization is proposed. For supported/contradicted verdicts give
an exact complete passage from one supplied source and identify that source. Prefer official cards
and structured metadata to general background abstracts. Include a concrete repair/check for each
claim. Do not infer that a dataset supplies a translated version merely because it studies translation.
A claim about Urdu cannot be supported by an African-language benchmark description.''',
        {'claims':claims,'sources':sources,'online_lookup_status':[{k:v for k,v in x.items() if k!='sources'} for x in lookups]},'dependency_verification')
    if {v.claim_id for v in response.verdicts}!={c['claim_id'] for c in claims} or len(response.verdicts)!=len(claims):
        raise ValueError('Verifier must assess each dependency exactly once')
    by_id={s['source_id']:s for s in sources};verdicts={v.claim_id:v for v in response.verdicts}
    assessed=[]
    for c in claims:
        v=verdicts[c['claim_id']].model_dump();method='llm_source_interpretation'
        if any(i not in by_id for i in v['source_ids']):raise ValueError('Unknown verification source')
        if v['verdict'] in ('supported','contradicted'):
            if not v['supporting_excerpt'] or not any(v['supporting_excerpt'] in by_id[i]['text'] for i in v['source_ids']):
                raise ValueError('Verdict lacks an exact source passage')
        if v['verdict']=='supported' and c['category'] in ('model_access','model_capability'):
            # A generic constraint paper cannot prove access for a concrete implementation.
            identity=c['entity'].casefold()
            direct=any(identity in (by_id[i].get('entity','')+' '+by_id[i]['text']).casefold()
                       and searchable_entity(c['entity']) for i in v['source_ids'])
            if not direct:
                v.update(verdict='unverified',explanation='Supplied evidence does not identify the claimed model/runtime capability. '+v['explanation'],
                         repair='Resolve the exact model and runtime and obtain implementation-specific documentation or a capability pilot.')
                method='entity_specific_support_required'
        if c['category']=='dataset_construction':
            v.update(verdict='requires_measurement',source_ids=[],supporting_excerpt='',
                     explanation='This is a proposed data construction task, not a claim that a public dataset already exists.',
                     repair='Implement a seeded generator and label oracle; test intervention validity, duplicates and template-disjoint calibration/test splits. Record pilot results.')
            method='construction_validation_required'
        if c['category']=='resource':
            v.update(verdict='requires_measurement',explanation='Resource sufficiency requires an actual pilot measurement. '+v['explanation'])
            method='measurement_required_rule'
        # Explicit complete language metadata can settle membership without an LLM.
        matches=[s for s in snapshots if c['entity'].casefold() in
                 {s['entity'].casefold(),*(a.casefold() for a in s.get('aliases',[]))}]
        applicable=[s for s in matches if s['facts'].get('languages_complete') is True]
        if c['category']=='dataset_language' and c['required_value'] and applicable:
            sets={tuple(sorted(s['facts']['languages'])) for s in applicable}
            if len(sets)==1:
                s=applicable[0];langs=s['facts']['languages']
                v.update(verdict='supported' if c['required_value'] in langs else 'contradicted',
                         source_ids=[s['source_id']],supporting_excerpt=s['text'],
                         explanation=f"Exact membership check against explicitly exhaustive language metadata: {langs}")
                method='structured_language_membership'
            else:
                v.update(verdict='unverified',explanation='Authoritative snapshots disagree on language coverage.')
                method='conflicting_metadata'
        assessed.append({**c,**v,'verification_method':method})
    return VerificationReport(proposal_hash=digest(idea.model_dump()),status='completed',claims=assessed,sources=sources,experiment_checks=checks,online_lookups=[{k:v for k,v in x.items() if k!='sources'} for x in lookups])


def acceptance_issue(report):
    if report.status!='completed':return 'Dependency verification failed; candidate cannot be accepted as verified.'
    issues=[i for i in report.experiment_checks if i['severity']=='repair_required']
    if issues:return 'Experimental design requires repair: '+'; '.join(i['explanation'] for i in issues)
    bad=[c for c in report.claims if c['essential'] and c['verdict']=='contradicted']
    return 'Contradicted essential dependencies: '+'; '.join(c['claim'] for c in bad) if bad else None
