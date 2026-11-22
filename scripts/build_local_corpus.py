"""Rebuild searchable records from the downloaded, hash-verified source XML."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from research_review.local_corpus import build_corpus

if __name__ == '__main__':
    manifest = build_corpus(ROOT / 'data/corpus/raw', ROOT / 'data/corpus/papers.json',
                            ROOT / 'data/seeds.json', ROOT / 'data/prior_work_anchors.json')
    print(json.dumps({key: manifest[key] for key in
                     ['paper_count', 'downloaded_raw_records', 'downloaded_usable_abstracts',
                      'imported_project_anchors', 'corpus_fingerprint']}, indent=2))
