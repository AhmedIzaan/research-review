"""Package the verified manuscript and data; exclude recursive archives."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib,json
P=Path(__file__).resolve().parents[1]/'paper'

def main():
    verification=json.loads((P/'verification.json').read_text())
    assert verification['status']=='passed'
    with ZipFile(P/'IEEE_LaTeX_Source.zip','w',ZIP_DEFLATED) as z:
        for f in [P/'main.tex',P/'references.bib',*sorted((P/'figures').glob('*.pdf'))]:
            z.write(f,f.relative_to(P))
    with ZipFile(P/'Research_Paper_Package.zip','w',ZIP_DEFLATED) as z:
        for f in sorted(P.rglob('*')):
            if f.is_file() and f.name not in {'Research_Paper_Package.zip','artifact_hashes.json'}:
                z.write(f,f.relative_to(P))
    hashes={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(P.rglob('*')) if f.is_file() and f.name!='artifact_hashes.json'}
    (P/'artifact_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    for name in ['IEEE_LaTeX_Source.zip','Research_Paper_Package.zip']:
        with ZipFile(P/name) as z:assert z.testzip() is None
    print('Rebuilt and checked both archives; recorded artifact hashes.')
if __name__=='__main__':main()
