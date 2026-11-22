"""Download a bounded official document for subsequent snapshot import.

Explicit URLs only; no model-generated requests, credentials, or source execution.
"""
import argparse
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.parse import urlparse
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Redirect refused; supply the final authoritative URL explicitly')
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();u=urlparse(a.url)
allowed={'huggingface.co','raw.githubusercontent.com','aclanthology.org'}
if u.scheme!='https' or u.hostname not in allowed or u.port not in (None,443) or u.username or u.password or u.query:
    p.error('Use an explicit HTTPS document URL on huggingface.co, raw.githubusercontent.com or aclanthology.org without credentials/query parameters')
if a.output.exists():p.error('Output already exists; use a new snapshot filename')
with build_opener(NoRedirect()).open(Request(a.url,headers={'User-Agent':'ResearchReview-SourceSnapshot/1.0'}),timeout=30) as response:
    raw=response.read(100001)
    if len(raw)>100000:raise ValueError('Document exceeds 100KB; use a specific metadata document')
    text=raw.decode('utf-8')
    if '\x00' in text:raise ValueError('Binary document refused')
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(text,encoding='utf-8')
print('Downloaded source text to',a.output,'; inspect and import with import_verification_source.py')
