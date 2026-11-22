"""Execute our trusted Python-only notebook cells when Jupyter is unavailable.

This fallback captures stdout/errors, not rich displays or kernel behavior. Prefer nbclient
for final submission. Never use this runner for untrusted notebooks/source literature.
"""
import contextlib
import io
import json
import os
import traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT/'notebooks')
reports=[]
for path in sorted((ROOT/'notebooks').glob('*.ipynb')):
    notebook=json.loads(path.read_text())
    namespace={'__name__':'__main__'}
    count=0
    for cell in notebook['cells']:
        if cell['cell_type']!='code':continue
        count+=1;cell['execution_count']=count
        stdout=io.StringIO()
        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stdout):
            try:
                exec(compile(''.join(cell['source']),str(path),'exec'),namespace)
            except Exception:
                traceback.print_exc()
                raise
        cell['outputs']=[{'output_type':'stream','name':'stdout','text':stdout.getvalue().splitlines(True)}]
    notebook['metadata']['verification']={'runner':'trusted Python-cell fallback; not Jupyter kernel execution','live_calls_enabled':os.getenv('RUN_LIVE_EXPERIMENTS')=='1'}
    path.write_text(json.dumps(notebook,indent=1))
    reports.append({'notebook':path.name,'executed_python_cells':count,'status':'passed','runner':'trusted Python-cell fallback'})
(ROOT/'results'/'notebook_verification.json').write_text(json.dumps(reports,indent=2))
print(json.dumps(reports,indent=2))
