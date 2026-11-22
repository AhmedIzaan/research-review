"""Prevent quotation transcription failures without accepting invented evidence."""
import pytest
from research_review.evidence_catalog import make_catalog, resolve_evidence, wire_schema
from research_review.literature_retrieval import verify_evidence
from research_review.schemas import Review


def test_catalog_preserves_source_hyphens_quotes_and_decimals(paper):
    paper = paper.model_copy(update={'abstract':
        'The Chain-ofIdeas method is budgetfriendly at $0.50 per run. '
        'It calls ideas “medium novel” without rewriting source punctuation.'})
    catalog, literature = make_catalog([paper])
    assert len(catalog) == 2
    assert '$0.50' in next(iter(catalog.values()))['supporting_excerpt']
    assert any('Chain-ofIdeas' in span['supporting_excerpt'] for span in catalog.values())
    selected = [{'passage_id': key, 'claim': 'A proposed comparison', 'relation': 'context'}
                for key in catalog]
    evidence = resolve_evidence(selected, catalog)
    verify_evidence(evidence, [paper])
    assert all(item.supporting_excerpt in paper.abstract for item in evidence)
    assert 'abstract' not in literature[0]


def test_unknown_passage_id_rejected(paper):
    catalog, _ = make_catalog([paper])
    with pytest.raises(ValueError, match='Unknown evidence'):
        resolve_evidence([{'passage_id':'invented', 'claim':'unsupported', 'relation':'supports'}], catalog)


def test_wire_schema_rejects_invented_id_and_copied_quote(paper):
    catalog, _ = make_catalog([paper])
    schema = wire_schema(Review, catalog)
    data = dict(role='novelty', novelty=3, explanation='Test', problems=['Test'],
                improvements=['Test'], uncertainty='Fixture only')
    with pytest.raises(ValueError):
        schema(**data, evidence=[{'passage_id':'invented', 'claim':'Test', 'relation':'context'}])
    with pytest.raises(ValueError):
        schema(**data, evidence=[{'passage_id':next(iter(catalog)), 'claim':'Test',
                                 'relation':'context', 'supporting_excerpt':'Invented quote'}])


def test_reviewer_role_is_restricted_before_provider_response_is_accepted(paper):
    catalog, _ = make_catalog([paper])
    schema = wire_schema(Review, catalog, expected_role='generic')
    data = dict(novelty=3, feasibility=3, clarity=3, importance=3,
                explanation='Test', problems=['Test'], improvements=['Test'], uncertainty='Fixture only')
    assert schema(role='generic', **data).role == 'generic'
    with pytest.raises(ValueError):
        schema(role='clarity', **data)


def test_empty_corpus_allows_no_evidence_only():
    schema = wire_schema(Review, {})
    data = dict(role='contrarian', explanation='Test', problems=['Test'],
                improvements=['Test'], uncertainty='Fixture only')
    assert not schema(**data).evidence
    with pytest.raises(ValueError):
        schema(**data, evidence=[{'passage_id':'fake', 'claim':'Test', 'relation':'context'}])


def test_gemini_wire_response_resolves_to_canonical_evidence(paper):
    import json
    from research_review.config import Settings
    from research_review.evidence_catalog import generate_grounded
    from research_review.llm import GeminiClient
    def transport(model, payload):
        content = json.loads(payload['contents'][0]['parts'][0]['text'])
        passage = content['literature'][0]['passages'][0]
        response = dict(role='novelty', novelty=3, explanation='Fixture', problems=['Fixture'],
                        improvements=['Fixture'], uncertainty='Synthetic unit test only',
                        evidence=[{'passage_id':passage['passage_id'], 'claim':'Fixture', 'relation':'overlaps'}])
        return {'candidates':[{'content':{'parts':[{'text':json.dumps(response)}]}}]}
    client = GeminiClient(Settings(request_interval=0), None, transport=transport)
    result = generate_grounded(client, Review, 'Synthetic test', {'role':'novelty'}, [paper], 'unit_test')
    assert isinstance(result, Review)
    assert result.evidence[0].paper_id == paper.paper_id
    verify_evidence(result.evidence, [paper])
