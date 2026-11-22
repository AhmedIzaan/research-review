"""Separate claim–excerpt support check; a model opinion, not source verification."""
from typing import Literal
from pydantic import Field, create_model

from .idea_generator import SAFETY
from .schemas import CitationAssessment, EvidenceAudit
from .storage import digest

INSTRUCTION = '''Audit whether each cited source excerpt supports its associated claim.
You receive no reviewer scores, role labels or refinement feedback. For every citation_id,
return exactly one assessment: supported (excerpt directly justifies the claim), partial
(only part is supported or the claim is stronger than the source), or unsupported
(the cited material does not establish the claim). Assess the given excerpt, using its
abstract for context, not unsupplied knowledge. A matching quotation or valid paper ID
alone does not establish support. Explain the specific mismatch or support. Do not rate
novelty or idea quality. State limitations of abstract-only, same-model auditing.'''


def collect_citations(outcomes):
    citations = {}
    for outcome in outcomes:
        if outcome.review:
            for evidence in outcome.review.evidence:
                item = evidence.model_dump()
                citation_id = 'c_' + digest(item)[:20]
                citations[citation_id] = {'citation_id':citation_id, **item}
    return citations


def audit_claim_support(client, outcomes, papers):
    citations = collect_citations(outcomes)
    if not citations:
        return None
    ids = Literal[tuple(sorted(citations))]
    assessment = create_model('BoundedCitationAssessment', __base__=CitationAssessment,
                              citation_id=(ids, ...))
    schema = create_model('CompleteEvidenceAudit', __base__=EvidenceAudit,
                          assessments=(list[assessment], Field(min_length=len(citations), max_length=len(citations))))
    supplied = {p.paper_id:p for p in papers}
    records = [{**item, 'source_abstract':supplied[item['paper_id']].abstract}
               for item in citations.values()]
    reply = client.generate(schema, SAFETY+'\n'+INSTRUCTION,
                            {'citations':records}, 'evidence_support_audit')
    return EvidenceAudit.model_validate(reply.model_dump())
