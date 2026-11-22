"""Exercise public-source retrieval without Gemini calls."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research_review.online_sources import OnlineSources
from research_review.config import Settings
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--entity',default='AG News');p.add_argument('--kind',choices=['dataset','model'],default='dataset')
p.add_argument('--cache',type=Path,default=Path('results/source_lookup_check'))
a=p.parse_args();Settings.from_env()
r=OnlineSources(a.cache).lookup(a.entity,a.kind)
print(json.dumps({k:v for k,v in r.items() if k!='sources'},indent=2))
print('Source documents:',len(r['sources']))
raise SystemExit(0 if r['status']=='retrieved' else 1)
