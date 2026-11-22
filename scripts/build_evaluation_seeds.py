"""Deterministic, pre-outcome purposive sampling from the pinned scholarly corpus."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research_review.config import ROOT
from research_review.local_corpus import LocalCorpusRetriever
from research_review.storage import load_json,save_json,digest

STRATA={
    'retrieval':'retrieval augmented generation evidence grounding',
    'factuality':'factuality hallucination verification factual consistency',
    'efficiency':'efficient inference quantization compression language model',
    'reasoning':'compositional reasoning logical reasoning language models',
    'multilinguality':'multilingual cross lingual low resource transfer',
    'evaluation':'benchmark evaluation reliability language models',
}

def main():
    retriever=LocalCorpusRetriever(ROOT/'data/corpus/papers.json')
    exclude={p['paper_id'] for p in load_json(ROOT/'data/seeds.json')}
    selected=[];mapping=[]
    for rank in range(2):
        for stratum,query in STRATA.items():
            result=retriever.search(query,limit=100)
            eligible=[p for p in result.papers if p.paper_id not in exclude
                      and p.year in (2024,2025) and len(p.abstract.split())>=80]
            if not eligible:raise ValueError('Not enough eligible records for '+stratum)
            paper=eligible[0];exclude.add(paper.paper_id);selected.append(paper.model_dump())
            mapping.append({'paper_id':paper.paper_id,'stratum':stratum,'query':query,'pass':rank+1})
    save_json(ROOT/'data/evaluation_seeds_v3.json',selected)
    save_json(ROOT/'data/evaluation_seeds_v3_manifest.json',{
        'protocol':'stratified_purposive_bm25_v1','corpus_fingerprint':retriever.fingerprint,
        'seeds_fingerprint':digest(selected),'selection':mapping,
        'criteria':'Two per six predefined topic strata, interleaved; BM25 top remaining abstract >=80 words, year 2024–2025, exclude original ideation/review seeds. No experiment outcomes used.',
        'limitations':'Purposive lexical sample from a bounded ACL corpus, not a random sample of science. Prefixes are smoke tests; full 12 covers all strata twice. Generation repetitions do not increase independent seed count.'})
    for row,p in zip(mapping,selected):print(row['stratum']+': '+p['paper_id']+' '+p['title'])

if __name__=='__main__':main()
