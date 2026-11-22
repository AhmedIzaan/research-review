"""Blinded human packets and strict import of real ratings; no generated ratings."""
import csv
import html
import json
import statistics
from urllib.parse import urlparse
from itertools import combinations
from .evaluation import METRICS,write_csv
from .storage import load_json,save_json


def write_packet(output_dir,items,contexts,rubric):
    """Keep condition labels, reviewer scores and guard decisions out of the packet."""
    cards=[]
    for item in {i['blind_id']:i for i in items}.values():
        papers=contexts[(item['seed_id'],item['replicate'])]['papers']
        context=contexts[(item['seed_id'],item['replicate'])]
        sources=''.join('<li><a href="'+html.escape(p.url if urlparse(p.url).scheme in ('http','https') else '#',quote=True)+'">'+html.escape(p.title)+
                        '</a><p>'+html.escape(p.abstract)+'</p></li>' for p in papers)
        cards.append('<article><h2>'+item['blind_id']+'</h2><pre>'+html.escape(json.dumps(item['idea'],indent=2))+
                     '</pre><details><summary>Shared scholarly evidence and retrieval limitations</summary><pre>'+
                     html.escape(json.dumps(context['coverage'],indent=2))+'</pre><ol>'+sources+'</ol></details></article>')
    page='''<!doctype html><meta charset="utf-8"><title>Blinded research proposal evaluation</title>
<style>body{max-width:960px;margin:40px auto;font:17px/1.6 system-ui;padding:16px;background:#f5f7fa;color:#172132}
article{background:white;border:1px solid #ccd5e1;padding:24px;margin:24px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.6 system-ui}a{color:#124a99}</style>
<h1>Independent human evaluation</h1><p>Read each proposal and evidence, then fill the five integer scores (1–5),
a stable anonymous rater_id and comments in a separate copy of human_ratings.csv. Do not consult system traces,
condition mappings or model scores. Submit separate files per rater. Leave genuinely unassessed rows blank.</p><pre>'''+html.escape(rubric)+'</pre>'+''.join(cards)
    (output_dir/'human_packet.html').write_text(page,encoding='utf-8')


def weighted_kappa(a,b):
    """Quadratic weighted Cohen kappa on paired ordinal ratings; None if undefined."""
    n=len(a)
    if not n:return None
    observed=sum((x-y)**2 for x,y in zip(a,b))/n
    expected=sum(a.count(x)*b.count(y)*(x-y)**2 for x in range(1,6) for y in range(1,6))/(n*n)
    return 1-observed/expected if expected else None


def analyze_humans(evaluation_dir,paths,output_dir):
    known={i['blind_id'] for i in load_json(evaluation_dir/'blind_key.json')}
    rows=[];seen=set()
    for path in paths:
        with path.open(newline='',encoding='utf-8-sig') as f:
            for raw in csv.DictReader(f):
                if not any(str(raw.get(k,'') or '').strip() for k in ['rater_id',*METRICS]):continue
                blind=raw.get('blind_id');rater=(raw.get('rater_id') or '').strip()
                if blind not in known or not rater:raise ValueError('Unknown blind ID or missing rater ID')
                if (blind,rater) in seen:raise ValueError('Duplicate proposal/rater rating')
                row={'blind_id':blind,'rater_id':rater,'comments':raw.get('comments','')}
                for metric in METRICS:
                    value=(raw.get(metric) or '').strip()
                    if value not in {'1','2','3','4','5'}:raise ValueError('Each assessed proposal needs all five integer scores from 1 to 5')
                    row[metric]=int(value)
                rows.append(row);seen.add((blind,rater))
    if not rows:raise ValueError('No completed human ratings were supplied')
    raters=sorted({r['rater_id'] for r in rows});agreement=[]
    for left,right in combinations(raters,2):
        aa={r['blind_id']:r for r in rows if r['rater_id']==left}
        bb={r['blind_id']:r for r in rows if r['rater_id']==right}
        shared=sorted(aa.keys()&bb.keys())
        for metric in METRICS:
            agreement.append({'rater_a':left,'rater_b':right,'metric':metric,'paired_proposals':len(shared),
                'quadratic_weighted_kappa':weighted_kappa([aa[k][metric] for k in shared],[bb[k][metric] for k in shared])})
    summary=[{'blind_id':blind,'raters':len(rr),**{m:statistics.median(r[m] for r in rr) for m in METRICS}}
             for blind in sorted({r['blind_id'] for r in rows})
             for rr in [[r for r in rows if r['blind_id']==blind]]]
    # Mapping is used only by the analyst after ratings are submitted.
    aliases=load_json(evaluation_dir/'blind_key.json')
    by_id={r['blind_id']:r for r in summary}
    joined=[{**{k:v for k,v in item.items() if k!='idea'},**by_id[item['blind_id']]}
            for item in aliases if item['blind_id'] in by_id]
    write_csv(output_dir/'mapped_scores.csv',joined)
    # Collapse generation repetitions within each seed before condition summaries.
    cells={}
    for item in joined:
        if item.get('is_final'):cells.setdefault((item['seed_id'],item['configuration']),[]).append(item)
    seed_rows=[{'seed_id':seed,'configuration':config,**{m:statistics.mean(r[m] for r in rr) for m in METRICS}}
               for (seed,config),rr in cells.items()]
    write_csv(output_dir/'seed_scores.csv',seed_rows)
    groups={}
    for r in seed_rows:groups.setdefault(r['configuration'],[]).append(r)
    write_csv(output_dir/'condition_summary.csv',[{'configuration':config,'independent_seeds':len(rr),
        **{m:statistics.mean(r[m] for r in rr) for m in METRICS}} for config,rr in groups.items()])
    write_csv(output_dir/'individual_ratings.csv',rows);write_csv(output_dir/'proposal_medians.csv',summary)
    save_json(output_dir/'agreement.json',{'ratings':len(rows),'raters':len(raters),'agreement':agreement,
        'limitations':'Agreement is descriptive. Proposal repetitions are not independent seed samples; no ratings were imputed.'})
    return summary
