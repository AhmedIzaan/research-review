"""Import fixed seeds from existing verified source captures, without modifying them.

Run from project directory. These are source abstracts, never generated proposals.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'outputs'/'mg3010-a2-final'
IDS=['S01','S02','S03','S11','S12','S13','S14','S15','S17','S18','S19','S20',
     'S003','S008','S009','S069','S083','S077','S103','S126']

def main():
    metadata=json.loads((SOURCE/'verified_metadata.json').read_text())
    papers,provenance=[],[]
    for id in IDS:
        v=metadata[id]
        filename=('P'+id[1:] if len(id)==4 else id)+'.txt'
        if id=='S20':filename='S20_published.txt'
        path=SOURCE/'fulltext'/filename
        original=path.read_text()
        text=re.sub(r'^L\d+: (?:PDF p\.\d+ \| ?)?','',original,flags=re.M)
        start=re.search(r'(?im)^\s*Abstract\s*$',text)
        assert start, id
        end=re.search(r'(?im)^\s*1\.?\s+Introduction\s*$',text[start.end():])
        assert end, id
        abstract=' '.join(text[start.end():start.end()+end.start()].replace('\\u0002','').replace('\x02','').split())
        authors=[]
        for name in v['author'].split(' and '):
            names=name.split(', ',1)
            authors.append(' '.join(reversed(names)) if len(names)==2 else name)
        papers.append({'paper_id':v['url'].rstrip('/').rsplit('/',1)[-1],'title':v['title'],
             'authors':authors,'year':int(v['year']),'abstract':abstract,'url':v['url'],
             'doi':v.get('doi'),'source':'ACL Anthology; imported saved primary-source capture',
             'retrieved_at':'2026-11-07'})
        provenance.append({'paper_id':papers[-1]['paper_id'],'source_capture':str(path.relative_to(ROOT.parent)),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'timestamp_note':'Date from existing review provenance; exact retrieval time not recorded in this import.',
            'processing':'Extract Abstract to Introduction, remove capture line/page prefixes and PDF soft-hyphen control character, join whitespace.',
            'version_note':v.get('peer_review','See original review metadata')})
    for filename,rows in [('seeds.json',papers),('smoke_seeds.json',papers[:2]),('seed_provenance.json',provenance)]:
        (ROOT/'data'/filename).write_text(json.dumps(rows,indent=2,ensure_ascii=False))
    print(f'Imported {len(papers)} real-paper records, {len(papers[:2])} smoke seeds; zero generated ideas.')

if __name__=='__main__':main()
