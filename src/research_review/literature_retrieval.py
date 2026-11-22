"""Real Semantic Scholar/arXiv search with query cache and explicit failures."""
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from .schemas import Paper, SearchResult
from .storage import digest, load_json, save_json, utcnow

class RetrievalError(RuntimeError):
    pass

def create_retriever(settings):
    """Select retrieval and bind the exact local snapshot into run settings."""
    from pathlib import Path
    from .config import ROOT
    if settings.retrieval_backend == 'local':
        from .local_corpus import LocalCorpusRetriever
        path = Path(settings.corpus_path)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            raise RetrievalError('Local corpus missing; run scripts/build_local_corpus.py')
        retriever = LocalCorpusRetriever(path, ROOT / 'data' / 'local_retrieval_cache')
        settings.corpus_fingerprint = retriever.fingerprint
        return retriever
    settings.corpus_fingerprint = None
    return LiteratureRetriever(ROOT / 'data' / 'retrieval_cache', timeout=20, attempts=2)

class LiteratureRetriever:
    def __init__(self, cache_dir, timeout=30, attempts=3, transport=None):
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.attempts = attempts
        self.transport = transport or self._request
        self.log = []

    def _request(self, url, headers):
        for attempt in range(self.attempts):
            try:
                with urlopen(Request(url,headers=headers), timeout=self.timeout) as response:
                    return response.read().decode('utf-8')
            except (HTTPError, URLError, TimeoutError) as exc:
                if isinstance(exc, HTTPError) and exc.code not in (429,500,502,503,504):
                    raise RetrievalError(f'HTTP {exc.code}') from None
                if attempt + 1 == self.attempts:
                    raise RetrievalError(type(exc).__name__ + ': scholarly endpoint unavailable') from None
                time.sleep(min(2**attempt*2,15))

    def search(self, query: str, limit=5, provider='semantic_scholar', refresh=False):
        query = ' '.join(query.split())[:300]
        if not query:
            raise ValueError('Empty literature query')
        if provider not in ('semantic_scholar','arxiv'):
            raise ValueError('Unknown provider')
        path = self.cache_dir / (digest({'query':query,'limit':limit,'provider':provider})+'.json')
        if path.exists() and not refresh:
            result = SearchResult.model_validate(load_json(path)).model_copy(update={'cache_hit':True})
            self.log.append(result.model_dump())
            return result
        now = utcnow()
        try:
            headers = {'User-Agent':'UniversityResearchReview/0.1 (metadata research)'}
            if provider == 'semantic_scholar':
                if os.getenv('SEMANTIC_SCHOLAR_API_KEY'):
                    headers['x-api-key'] = os.environ['SEMANTIC_SCHOLAR_API_KEY']
                url = 'https://api.semanticscholar.org/graph/v1/paper/search?' + urlencode({
                    'query':query,'limit':limit,'fields':'title,authors,year,abstract,url,externalIds'})
                rows = json.loads(self.transport(url,headers)).get('data',[])
                papers = [Paper(paper_id=r['paperId'],title=r['title'],
                           authors=[a['name'] for a in r.get('authors',[])], year=r.get('year'),
                           abstract=r.get('abstract') or '',url=r.get('url') or 'https://www.semanticscholar.org/paper/'+r['paperId'],
                           doi=(r.get('externalIds') or {}).get('DOI'),source=provider,retrieved_at=now) for r in rows]
            else:
                terms = re.findall(r'[\w-]+',query)[:16]
                search = 'all:(' + ' AND '.join(terms) + ')'
                url = 'https://export.arxiv.org/api/query?' + urlencode({'search_query':search,'max_results':limit,'sortBy':'relevance'})
                papers = parse_arxiv(self.transport(url,headers),now)
            result = SearchResult(query=query,provider=provider,retrieved_at=now,papers=papers,status='ok' if papers else 'empty')
            save_json(path,result.model_dump())
        except (RetrievalError, ValueError, KeyError, ET.ParseError) as exc:
            result = SearchResult(query=query,provider=provider,retrieved_at=now,papers=[],status='failed',error=str(exc))
            # Never persist failed requests as successful empty cache entries.
        self.log.append(result.model_dump())
        return result

    def related(self, query, limit=5):
        result = self.search(query,limit)
        if result.status != 'ok':
            fallback = self.search(query,limit,'arxiv')
            return [result,fallback]
        return [result]

def parse_arxiv(xml, now):
    ns = {'a':'http://www.w3.org/2005/Atom','ar':'http://arxiv.org/schemas/atom'}
    root = ET.fromstring(xml)
    papers = []
    for e in root.findall('a:entry',ns):
        get = lambda tag: ' '.join((e.findtext(tag,default='',namespaces=ns)).split())
        url = get('a:id')
        if not url or 'api/errors' in url:
            raise RetrievalError('arXiv returned an error entry')
        papers.append(Paper(paper_id=url.rsplit('/',1)[-1],title=get('a:title'),
             authors=[a.findtext('a:name',namespaces=ns) for a in e.findall('a:author',ns)],
             year=int(get('a:published')[:4]),abstract=get('a:summary'),url=url,
             doi=get('ar:doi') or None,source='arxiv',retrieved_at=now))
    return papers

def unique_papers(papers):
    seen_dois, seen_titles, result = set(), set(), []
    for paper in papers:
        doi = paper.doi.lower() if paper.doi else None
        title = re.sub(r'\W','',paper.title.lower())
        if title not in seen_titles and (doi is None or doi not in seen_dois):
            result.append(paper)
        seen_titles.add(title)
        if doi:
            seen_dois.add(doi)
    return result


def verify_evidence(evidence, papers):
    """Validate identity and exact excerpt membership; not semantic entailment."""
    by_id = {p.paper_id:p for p in papers}
    for item in evidence:
        if item.paper_id not in by_id:
            raise ValueError('Evidence cites a paper not supplied to this agent')
        text = ' '.join((by_id[item.paper_id].abstract).split()).lower()
        excerpt = ' '.join(item.supporting_excerpt.split()).lower()
        if len(excerpt) < 15 or excerpt not in text:
            raise ValueError('Evidence excerpt does not match retrieved abstract')

def verify_references(idea, papers):
    if not set(idea.references) <= {p.paper_id for p in papers}:
        raise ValueError('Proposal cites an unsupplied paper ID')
