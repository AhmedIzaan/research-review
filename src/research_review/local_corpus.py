"""Build and search a pinned ACL metadata snapshot without network or embeddings."""
from collections import Counter, defaultdict
import hashlib
import math
from pathlib import Path
import re
from xml.etree import ElementTree as ET

from .schemas import Paper, SearchResult
from .storage import digest, load_json, save_json, utcnow

STOPWORDS = set('a an and are as at be been being by can could did do does for from '
                'has have how i if in into is it its may of on or our paper proposed '
                'research study than that the their them these this those to using '
                'was we were what when which who will with would'.split())


def tokens(text):
    return [t for t in re.findall(r'[a-z][a-z0-9]*', text.lower())
            if len(t) > 1 and t not in STOPWORDS]


def element_text(element):
    return ' '.join(''.join(element.itertext()).split()) if element is not None else ''


def build_corpus(raw_dir: Path, output: Path, seeds_path: Path | None = None,
                 prior_work_path: Path | None = None):
    sources = load_json(raw_dir / 'download_manifest.json')
    records, provenance, exclusions, source_details = {}, {}, [], []
    raw_count = 0
    for source in sources:
        path = raw_dir / source['file']
        raw = path.read_bytes()
        git_hash = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if git_hash != source['git_blob_sha']:
            raise ValueError('Downloaded source hash mismatch: ' + source['file'])
        # ElementTree does not execute XML source text; reject entity declarations.
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise ValueError('Unexpected DTD/entity declaration in corpus XML')
        collection = ET.fromstring(raw)
        count = 0
        for volume in collection.findall('volume'):
            year = volume.findtext('meta/year')
            for item in volume.findall('paper'):
                raw_count += 1
                paper_id = f"{collection.attrib['id']}-{volume.attrib['id']}.{item.attrib['id']}"
                title = element_text(item.find('title'))
                abstract = element_text(item.find('abstract'))
                if not title or not abstract:
                    exclusions.append({'paper_id': paper_id, 'reason': 'Missing title or abstract'})
                    continue
                authors = [' '.join(filter(None, [element_text(a.find('first')),
                                                   element_text(a.find('last'))]))
                           for a in item.findall('author')]
                paper = Paper(paper_id=paper_id, title=title, authors=[a for a in authors if a],
                              year=int(year) if year else None, abstract=abstract,
                              url=f'https://aclanthology.org/{paper_id}/',
                              doi=element_text(item.find('doi')) or None,
                              source='ACL Anthology official XML snapshot',
                              retrieved_at=source['downloaded_at'])
                records[paper_id] = paper
                provenance[paper_id] = {'type': 'downloaded_xml', 'file': source['file'],
                                        'source_url': source['source_url']}
                count += 1
        source_details.append({**source, 'sha256': hashlib.sha256(raw).hexdigest(),
                               'usable_papers': count})
    # Retain already-verified project anchors, including newer ideation papers,
    # while distinguishing this import from the newly downloaded collections.
    imported = []
    for import_path in [path for path in (seeds_path, prior_work_path) if path]:
        for record in load_json(import_path):
            paper = Paper.model_validate(record)
            if paper.paper_id not in records:
                records[paper.paper_id] = paper
                provenance[paper.paper_id] = {'type': 'existing_anchor_import',
                                             'source': ('data/seed_provenance.json' if import_path == seeds_path
                                                        else 'data/prior_work_anchor_provenance.json')}
                imported.append(paper.paper_id)
    ordered = [records[key].model_dump() for key in sorted(records)]
    fingerprint = digest(ordered)
    manifest = {'built_at': utcnow(), 'corpus_fingerprint': fingerprint,
                'paper_count': len(ordered), 'downloaded_raw_records': raw_count,
                'downloaded_usable_abstracts': raw_count - len(exclusions),
                'imported_project_anchors': imported, 'sources': source_details,
                'excluded_records': exclusions,
                'selection': 'All paper elements with nonempty title and abstract in the six pinned collections; no outcome-based filtering.',
                'representation': 'Titles, authors, years, abstracts, URLs, and available DOIs; not full-paper PDFs.',
                'limitations': 'Bounded venue/year snapshot, mostly 2024–2025 plus project anchors; lexical retrieval misses paraphrases and outside-corpus prior art.',
                'licenses': {'ACL_materials_since_2016': 'CC BY 4.0; retain individual attribution; third-party materials may differ',
                             'policy_url': 'https://aclanthology.org/faq/copyright/'}}
    save_json(output, ordered)
    save_json(output.parent / 'manifest.json', manifest)
    save_json(output.parent / 'record_provenance.json', provenance)
    return manifest


class LocalCorpusRetriever:
    """Deterministic BM25 over titles (3x term weight) and abstracts.

    A real query-dependent search is performed for every idea. Zero-overlap
    queries return no matches rather than arbitrarily selected evidence.
    """
    is_local = True

    def __init__(self, corpus_path: Path, cache_dir: Path | None = None):
        self.path = Path(corpus_path)
        raw = load_json(self.path)
        self.papers = [Paper.model_validate(p) for p in raw]
        if not self.papers or len({p.paper_id for p in self.papers}) != len(self.papers):
            raise ValueError('Corpus must contain distinct real paper records')
        self.fingerprint = digest(raw)
        self.provider = 'local_bm25_v1:' + self.fingerprint
        self.cache_dir = cache_dir
        self.log = []
        self.postings = defaultdict(list)
        self.lengths = []
        for index, paper in enumerate(self.papers):
            terms = tokens(paper.title) * 3 + tokens(paper.abstract)
            counts = Counter(terms)
            self.lengths.append(len(terms))
            for term, count in counts.items():
                self.postings[term].append((index, count))
        self.average_length = sum(self.lengths) / len(self.papers) or 1

    def search(self, query, limit=5, provider=None, refresh=False):
        query = ' '.join(query.split())[:300]
        if not query or limit < 1:
            raise ValueError('A nonempty query and positive result limit are required')
        if provider not in (None, 'local', 'local_bm25', self.provider):
            raise ValueError('Local corpus search cannot switch to an online provider')
        key = digest({'query': query, 'limit': limit, 'provider': self.provider})
        path = self.cache_dir / (key + '.json') if self.cache_dir else None
        if path and path.exists() and not refresh:
            result = SearchResult.model_validate(load_json(path)).model_copy(update={'cache_hit': True})
            self.log.append(result.model_dump())
            return result
        scores = defaultdict(float)
        n, k1, b = len(self.papers), 1.5, 0.75
        for term in sorted(set(tokens(query))):
            postings = self.postings.get(term, [])
            if not postings:
                continue
            idf = math.log(1 + (n - len(postings) + 0.5) / (len(postings) + 0.5))
            for index, frequency in postings:
                denominator = frequency + k1 * (1 - b + b * self.lengths[index] / self.average_length)
                scores[index] += idf * frequency * (k1 + 1) / denominator
        ranked = sorted(scores, key=lambda i: (-scores[i], self.papers[i].paper_id))[:limit]
        result = SearchResult(query=query, provider=self.provider, retrieved_at=utcnow(),
                              papers=[self.papers[i] for i in ranked],
                              status='ok' if ranked else 'empty')
        if path:
            save_json(path, result.model_dump())
        self.log.append(result.model_dump())
        return result

    def related(self, query, limit=5):
        return [self.search(query, limit)]
