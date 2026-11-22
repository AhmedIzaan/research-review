"""Let models select real source passages instead of transcribing quotations.

Saved Review/Judgment records still contain paper IDs and exact quotations.
The model wire format contains only an allowed passage ID, claim and relation.
Passage selection validates provenance; it does not establish semantic support.
"""
import re
from enum import Enum
from typing import Literal
from pydantic import Field, create_model

from .schemas import Evidence, Record, Text, Score, ROLE_METRICS
from .storage import digest

PROTOCOL = 'passage_ids_v3_complete_sentences'
INSTRUCTIONS = '''Evidence must select a passage_id from the supplied literature passages.
Return each citation as passage_id, claim, and relation. Do not transcribe or rewrite quotations.
The program will attach the exact source excerpt and its paper ID. Select only passages relevant
to the claim; a valid identifier alone does not establish support. Use an empty evidence list
when no supplied passage supports a claim, rather than inventing an identifier.
uncertainty must be a nonempty sentence describing limitations; never return an empty string.'''


def make_catalog(papers):
    catalog, literature = {}, []
    for paper in papers:
        passages = []
        abstract = paper.abstract
        # Source-preserving slices: punctuation and whitespace are never repaired.
        # Split only at likely sentence boundaries, preserving abbreviations and exact text.
        boundaries=[0]
        for match in re.finditer(r'[.!?](?=\s+[A-Z]|$)',abstract):
            prefix=abstract[:match.end()]
            if re.search(r'(?:e\.g\.|i\.e\.|et al\.|Dr\.|Mr\.|Ms\.|Fig\.|vs\.)$',prefix):continue
            boundaries.append(match.end())
        if boundaries[-1]!=len(abstract):boundaries.append(len(abstract))
        for start,stop in zip(boundaries,boundaries[1:]):
            chunk=abstract[start:stop]
            excerpt=chunk.strip()
            if len(excerpt)<15:continue
            begin=start+len(chunk)-len(chunk.lstrip());end=begin+len(excerpt)
            passage_id='s_'+digest({'paper_id':paper.paper_id,'begin':begin,'end':end,'excerpt':excerpt})[:20]
            catalog[passage_id]={'paper_id':paper.paper_id,'supporting_excerpt':excerpt}
            passages.append({'passage_id':passage_id,'text':excerpt})
        metadata = paper.model_dump(exclude={'abstract'})
        literature.append({**metadata, 'passages': passages})
    return catalog, literature


def wire_schema(canonical_schema, catalog, expected_role=None):
    allowed_ids = Literal[tuple(sorted(catalog))] if catalog else Text
    citation = create_model('SelectedPassage', __base__=Record,
                            passage_id=(allowed_ids, ...), claim=(Text, ...),
                            relation=(Literal['supports', 'overlaps', 'contradicts', 'context'], ...))
    evidence_field = Field(default_factory=list) if catalog else Field(default_factory=list, max_length=0)
    overrides = {'evidence': (list[citation], evidence_field)}
    if expected_role is not None:
        role_type = Enum('ExpectedReviewerRole', {'EXPECTED': expected_role}, type=str)
        overrides['role'] = (role_type, ...)
        for metric in ('novelty', 'feasibility', 'clarity', 'importance'):
            if metric in ROLE_METRICS[expected_role]:
                overrides[metric] = (Score, ...)
            else:
                overrides[metric] = (type(None), None)
        if expected_role == 'contrarian':
            overrides['falsification_test'] = (Text, ...)
    return create_model(canonical_schema.__name__ + 'PassageSelection',
                        __base__=canonical_schema, **overrides)


def resolve_evidence(selections, catalog):
    evidence = []
    for selection in selections:
        if selection['passage_id'] not in catalog:
            raise ValueError('Unknown evidence passage ID')
        source = catalog[selection['passage_id']]
        evidence.append(Evidence(**source, claim=selection['claim'], relation=selection['relation']))
    return evidence


def generate_grounded(client, canonical_schema, instruction, content, papers, label, model=None):
    catalog, literature = make_catalog(papers)
    schema = wire_schema(canonical_schema, catalog,
                         expected_role=content.get('role') if 'role' in canonical_schema.model_fields else None)
    payload = {**content, 'literature': literature, 'evidence_protocol': PROTOCOL}
    reply = client.generate(schema, instruction + '\n' + INSTRUCTIONS, payload, label, model=model)
    data = reply.model_dump(mode='json')
    data['evidence'] = [item.model_dump() for item in resolve_evidence(data['evidence'], catalog)]
    return canonical_schema.model_validate(data)
