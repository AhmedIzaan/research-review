"""Local retrieval tests. Synthetic unit data stay in temporary directories."""
import hashlib
from pathlib import Path
import pytest

from research_review.config import ROOT, Settings
from research_review.literature_retrieval import create_retriever
from research_review.local_corpus import LocalCorpusRetriever, build_corpus
from research_review.orchestration import Workflow
from research_review.storage import load_json, save_json
from conftest import FixtureClient


def test_real_corpus_is_larger_than_seed_set_and_retrieves_known_papers():
    retriever = LocalCorpusRetriever(ROOT / 'data/corpus/papers.json')
    manifest = load_json(ROOT / 'data/corpus/manifest.json')
    assert len(retriever.papers) == manifest['paper_count']
    assert len(retriever.papers) > 2000
    result = retriever.search('ResearchAgent iterative research idea generation scientific literature')
    assert result.papers[0].paper_id == '2025.naacl-long.342'
    assert retriever.search('SciMON Scientific Inspiration Machines Optimized for Novelty').papers[0].paper_id == '2024.acl-long.18'
    assert any(p.paper_id == 'arxiv:2602.14367v1' for p in retriever.papers)


def test_local_query_with_no_overlap_returns_empty(paper, tmp_path):
    path = tmp_path / 'papers.json'
    save_json(path, [paper.model_dump()])
    retriever = LocalCorpusRetriever(path)
    result = retriever.search('zzzzzzunknownterm')
    assert result.status == 'empty' and not result.papers
    with pytest.raises(ValueError): retriever.search('test', provider='arxiv')
    with pytest.raises(ValueError): retriever.search(' ')
    with pytest.raises(ValueError): retriever.search('test', limit=0)


def test_cache_changes_when_corpus_snapshot_changes(paper, tmp_path):
    path, cache = tmp_path / 'papers.json', tmp_path / 'cache'
    save_json(path, [paper.model_dump()])
    retriever = LocalCorpusRetriever(path, cache)
    assert not retriever.search('retrieval').cache_hit
    assert retriever.search('retrieval').cache_hit
    save_json(path, [paper.model_copy(update={'abstract': 'Completely different subject matter'}).model_dump()])
    changed = LocalCorpusRetriever(path, cache)
    assert changed.fingerprint != retriever.fingerprint
    assert not changed.search('retrieval').cache_hit


def test_factory_pins_fingerprint_without_network():
    settings = Settings(retrieval_backend='local')
    retriever = create_retriever(settings)
    assert settings.corpus_fingerprint == retriever.fingerprint
    assert retriever.is_local


def test_workflow_novelty_uses_local_retrieval(idea, paper, tmp_path):
    path = tmp_path / 'papers.json'
    save_json(path, [paper.model_dump()])
    retriever = LocalCorpusRetriever(path)
    run = Workflow(FixtureClient(idea), retriever,
                   Settings(rounds=1, engine='python')).run('fixture-seed', 'full', idea, [paper])
    novelty = run.rounds[0].reviews[0]
    assert novelty.evidence_status == 'verified_excerpt'
    assert novelty.search[0].provider.startswith('local_bm25_v1:')
    assert not novelty.error


def test_xml_builder_preserves_markup_authors_doi_and_exclusions(tmp_path):
    xml = b'''<collection id="2025.test"><volume id="1"><meta><year>2025</year></meta>
    <paper id="1"><title>A <fixed-case>Test</fixed-case> Paper</title>
    <author><first>Jane</first><last>Doe</last></author><abstract>Scientific abstract text.</abstract>
    <doi>10.test/example</doi></paper><paper id="2"><title>No abstract</title></paper>
    </volume></collection>'''
    raw = tmp_path / 'raw'; raw.mkdir()
    (raw / 'fixture.xml').write_bytes(xml)
    git_sha = hashlib.sha1(b'blob ' + str(len(xml)).encode() + b'\0' + xml).hexdigest()
    save_json(raw / 'download_manifest.json', [{'file': 'fixture.xml', 'git_blob_sha': git_sha,
              'downloaded_at': '2026-11-08', 'source_url': 'https://example.invalid/fixture'}])
    manifest = build_corpus(raw, tmp_path / 'corpus/papers.json')
    records = load_json(tmp_path / 'corpus/papers.json')
    assert manifest['paper_count'] == 1 and manifest['downloaded_raw_records'] == 2
    assert records[0]['title'] == 'A Test Paper'
    assert records[0]['authors'] == ['Jane Doe']
    assert records[0]['doi'] == '10.test/example'
    assert records[0]['paper_id'] == '2025.test-1.1'
    (raw / 'fixture.xml').write_bytes(xml + b'bad')
    with pytest.raises(ValueError, match='hash mismatch'):
        build_corpus(raw, tmp_path / 'other/papers.json')
