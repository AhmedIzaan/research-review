"""Pin an official source downloaded by the researcher; no execution of source content."""
import argparse,hashlib,json,sys
from pathlib import Path
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research_review.storage import load_json,save_json,utcnow
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--entity',required=True);p.add_argument('--url',required=True)
p.add_argument('--text',type=Path,required=True,help='UTF-8 official card/document text, not executable code')
p.add_argument('--output',type=Path,default=Path('data/verification_sources.json'))
p.add_argument('--languages',nargs='*',default=None,help='ISO codes transcribed from the source; completeness is a separate attestation')
p.add_argument('--languages-complete',action='store_true',help='Attest that the source explicitly provides the entire language list')
p.add_argument('--aliases',nargs='*',default=[])
a=p.parse_args()
url=urlparse(a.url)
if url.scheme!='https' or not url.hostname:p.error('Supply the authoritative HTTPS source URL')
if a.languages_complete and a.languages is None:p.error('Complete language coverage requires an explicit list')
text=a.text.read_text(encoding='utf-8')
if not text.strip() or len(text)>100000:p.error('Source must contain 1–100000 characters of text')
records=load_json(a.output) if a.output.exists() else []
source={'source_id':'official_'+hashlib.sha256((a.url+text).encode()).hexdigest()[:20],
 'entity':a.entity,'aliases':a.aliases,'url':a.url,'retrieved_at':utcnow(),'text':text,
 'sha256':hashlib.sha256(text.encode()).hexdigest(),'kind':'researcher_imported_official_document',
 'facts':{'languages':a.languages,'languages_complete':a.languages_complete},
 'provenance_note':'Researcher supplied source URL and local text; hash checks integrity, not authenticity. Structured metadata is a human transcription.'}
if any(s['source_id']==source['source_id'] for s in records):p.error('This snapshot is already present')
save_json(a.output,[*records,source]);print('Pinned source:',source['source_id'])
