"""Bounded evidence selection for blinded judges, independent of reviewer outputs."""
from itertools import zip_longest

from .schemas import SearchResult
from .storage import digest, utcnow

JUDGE_RETRIEVAL_PROTOCOL = 'multi_query_shared_evidence_v1'
MAX_JUDGE_PAPERS = 24
HITS_PER_QUERY = 5


def judge_queries(proposal):
    queries = list(proposal['search_queries'][:3])
    queries.append(' '.join((proposal['title']+' '+proposal['methodology']).split()[:40]))
    result, seen = [], set()
    for query in queries:
        query = ' '.join(query.split())[:300]
        if query and query.casefold() not in seen:
            seen.add(query.casefold())
            result.append(query)
    return result


def build_judge_context(proposals, retriever, source_papers=(), max_papers=MAX_JUDGE_PAPERS):
    """Use one common evidence set for all versions/conditions of a matched seed.

    Accepts proposals and source records only; no reviewer objects or scores.
    Citation lookup uses corpus records, then original generator literature.
    Query hits are interleaved so the first broad query cannot monopolize context.
    """
    if max_papers < 1:
        raise ValueError('Judge paper limit must be positive')
    ordered = sorted({digest(p):p for p in proposals}.items())
    queries, cited_ids = [], set()
    for _, proposal in ordered:
        for query in judge_queries(proposal):
            if query.casefold() not in {q.casefold() for q in queries}:
                queries.append(query)
        cited_ids.update(proposal.get('references', []))
        cited_ids.update(item['paper_id'] for item in proposal.get('prior_work_comparison', []))
    # The pinned corpus wins over an older seed copy of the same source record.
    lookup = {p.paper_id:p for p in source_papers}
    corpus = {p.paper_id:p for p in getattr(retriever,'papers',[])}
    lookup.update(corpus)
    searches = []
    for query in queries:
        try:
            searches.extend(retriever.related(query, limit=HITS_PER_QUERY))
        except Exception as exc:
            searches.append(SearchResult(query=query, provider=type(retriever).__name__,
                retrieved_at=utcnow(), papers=[], status='failed', error=type(exc).__name__))
    for search in searches:
        for paper in search.papers:
            if paper.paper_id not in corpus:
                lookup[paper.paper_id] = paper
    cited = [lookup[key] for key in sorted(cited_ids) if key in lookup]
    # Bound input size and explicitly report citations excluded by the cap.
    papers = cited[:max_papers]
    chosen = {p.paper_id for p in papers}
    for row in zip_longest(*(s.papers for s in searches)):
        for paper in row:
            if paper is not None and paper.paper_id not in chosen and len(papers)<max_papers:
                papers.append(lookup[paper.paper_id])
                chosen.add(paper.paper_id)
    all_hits = {p.paper_id for s in searches for p in s.papers} | {p.paper_id for p in cited}
    coverage = {'protocol':JUDGE_RETRIEVAL_PROTOCOL,
                'selection_policy':'Shared evidence per seed/replicate; cited papers first, then interleaved multi-query hits.',
                'query_count':len(queries), 'paper_count':len(papers), 'paper_limit':max_papers,
                'search_failures':sum(s.status=='failed' for s in searches),
                'missing_cited_ids':sorted(cited_ids-lookup.keys()),
                'omitted_cited_ids':sorted({p.paper_id for p in cited}-chosen),
                'omitted_hit_count':len(all_hits-chosen),
                'limitations':'Bounded abstract corpus and lexical search; incomplete retrieval does not establish novelty.'}
    return {'papers':papers,'searches':searches,'coverage':coverage,
            'fingerprint':digest({'protocol':JUDGE_RETRIEVAL_PROTOCOL,
                                  'queries':queries,'retrieval_snapshot':getattr(retriever,'fingerprint',None),
                                  'papers':[p.model_dump() for p in papers],'coverage':coverage}),
            'queries':queries}
