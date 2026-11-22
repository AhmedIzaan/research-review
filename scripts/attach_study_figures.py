"""Embed actual saved study PNGs in Notebook 3 as portable Markdown attachments."""
import base64
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
study = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'results/smoke'
path = ROOT / 'notebooks/03_Evaluation_and_Ablation.ipynb'
notebook = json.loads(path.read_text())
notebook['cells'] = [c for c in notebook['cells'] if c.get('id') != 'actual-study-figures']
attachments, lines = {}, [f'## Actual saved figures: {study.name}\n',
    'These figures use saved independent ratings. Sample counts and missing judgments limit comparisons.\n']
for name in ['baseline_comparison', 'ablation_comparison', 'iteration_progression',
             'novelty_feasibility', 'execution_time']:
    image = study / 'analysis' / (name + '.png')
    if image.exists():
        attachments[image.name] = {'image/png': base64.b64encode(image.read_bytes()).decode()}
        lines.append(f'\n![{name}](attachment:{image.name})\n')
if attachments:
    notebook['cells'].append({'cell_type':'markdown', 'id':'actual-study-figures',
                              'metadata':{}, 'source':lines, 'attachments':attachments})
path.write_text(json.dumps(notebook, indent=1))
print(f'Embedded {len(attachments)} actual study figures; no Jupyter kernel execution claimed.')
