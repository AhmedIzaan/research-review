"""Import separately completed, blinded human rating CSVs."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research_review.human_evaluation import analyze_humans
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--evaluation',type=Path,required=True)
p.add_argument('--ratings',type=Path,nargs='+',required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
rows=analyze_humans(a.evaluation,a.ratings,a.output)
print(f'Imported real ratings for {len(rows)} proposals. Results: {a.output}')
