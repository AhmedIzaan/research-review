#!/usr/bin/env python3
"""Freeze paper tables from saved live data. Does not call a model or alter experiments."""
import csv
from collections import Counter,defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from research_review.storage import digest,save_json

STUDY=ROOT/'results/smoke_v2';OUT=ROOT/'paper/results'
METRICS=['novelty','feasibility','clarity','importance','evidence_grounding']
CONFIGS=['one_shot','generic','full','no_feasibility','no_contrarian','no_novelty_retrieval']
OWN={'novelty':['novelty'],'feasibility':['feasibility'],'clarity':['clarity','importance'],'contrarian':[],'generic':METRICS[:4]}

def load(p):return json.loads(p.read_text())
def write_csv(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    runs=[load(p) for p in sorted((STUDY/'runs').glob('*.json')) if not p.name.endswith('.partial.json')]
    with (STUDY/'evaluation/scores.csv').open() as f:rows=list(csv.DictReader(f))
    finals=[r for r in rows if r['is_final'].lower()=='true' and not r['judge_error']]
    assert len(runs)==12 and len(finals)==12 and len({r['seed_id'] for r in runs})==2
    assert all(r['provenance']=='live_gemini' for r in runs)
    for seed in {r['seed_id'] for r in runs}:
        assert len({digest(r['initial_idea']) for r in runs if r['seed_id']==seed})==1
    for row in finals:
        for m in METRICS:row[m]=int(row[m])
    means=[]
    for c in CONFIGS:
        rs=[r for r in finals if r['configuration']==c]
        means.append({'configuration':c,'n':len(rs),**{m:sum(r[m] for r in rs)/len(rs) for m in METRICS}})
    paired=[]
    for c in CONFIGS:
        if c=='full':continue
        for seed in sorted({r['seed_id'] for r in finals}):
            f=next(r for r in finals if r['configuration']=='full' and r['seed_id']==seed)
            a=next(r for r in finals if r['configuration']==c and r['seed_id']==seed)
            paired.append({'seed_id':seed,'comparison':'full_minus_'+c,**{m:f[m]-a[m] for m in METRICS}})
    progression=[]
    for index in range(4):
        values=[r for r in rows if r['configuration']=='full' and int(r['round'])==index]
        assert len(values)==2
        progression.append({'round':index,'n':2,**{m:sum(float(r[m]) for r in values)/2 for m in METRICS}})
    events=[load(p)['event'] for folder in ['api_audit','judge_api_audit'] for p in (STUDY/folder).glob('*.json')]
    judgments=[load(p) for p in (STUDY/'evaluation/judgments').glob('*.json')]
    initial_lookup={}
    for p in (STUDY/'initials').glob('*.json'):
        initial=load(p);initial_lookup[digest(initial['idea'])]=initial
    resources=[]
    for r in runs:
        initial=initial_lookup[digest(r['initial_idea'])]
        resources.append({'seed_id':r['seed_id'],'configuration':r['configuration'],
            'additional_api_attempts':len(r['api_events']),'additional_seconds':r['elapsed_seconds'],
            'successful_revisions':sum(x['revised_idea'] is not None for x in r['rounds']),
            'round_records':len(r['rounds']),'stop_reason':r['stop_reason'],
            'shared_initial_attempts':len(initial['events']),'shared_initial_seconds':initial['elapsed_seconds']})
    leakage=Counter();review_count=Counter()
    for r in runs:
        for rd in r['rounds']:
            for o in rd['reviews']:
                if o['review']:
                    review_count[o['role']]+=1
                    if any(o['review'].get(m) is not None for m in METRICS[:4] if m not in OWN[o['role']]):leakage[o['role']]+=1
    status=load(STUDY/'suite_status.json')
    duration=(datetime.fromisoformat(status['finished_at'])-datetime.fromisoformat(status['started_at'])).total_seconds()
    protected={}
    for study in ['smoke','smoke_v2']:
        root=ROOT/'results'/study; hashes=load(root/'audit/unchanged_raw_hashes.json')
        changed=[n for n,h in hashes.items() if hashlib.sha256((root/n).read_bytes()).hexdigest()!=h]
        assert not changed
        protected[study]={'files':len(hashes),'changed':changed}
    cases=[]
    for p in sorted((ROOT/'results/web_runs').glob('*/job.json')):
        j=load(p);r=j.get('result')
        if not r:continue
        es=j['api_events'];details=j.get('evaluation_details',[])
        cases.append({'job_id':j['id'],'run_id':r['run_id'],'topic':j['request'].get('topic'),
            'status':j['status'],'rounds':len(r['rounds']),'elapsed_seconds':j['elapsed_seconds'],
            'attempts':len(es),'request_failures':sum(e['status']!='ok' for e in es),
            'reported_tokens':sum(e.get('total_tokens') or 0 for e in es),
            'unknown_usage_attempts':sum(e.get('total_tokens') is None for e in es),
            'initial_idea':r['initial_idea'],'final_idea':r['final_idea'],
            'evaluation':j.get('evaluation',[]),
            'final_reviewer_scores':[{k:o['review'].get(k) for k in ['role']+METRICS[:4]} for o in r.get('final_reviews',[]) if o['review']],
            'audit':r.get('evidence_audit'),
            'judge_paper_ids':[sorted({p['paper_id'] for s in d['search'] for p in s['papers']}) for d in details]})
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [STUDY/'manifest.json',STUDY/'evaluation/scores.csv',STUDY/'suite_status.json',ROOT/'data/corpus/manifest.json',ROOT/'data/corpus/papers.json',ROOT/'data/seeds.json']+
        list((STUDY/'runs').glob('*.json'))+list((STUDY/'evaluation/judgments').glob('*.json'))+
        list((STUDY/'api_audit').glob('*.json'))+list((STUDY/'judge_api_audit').glob('*.json'))+
        list((ROOT/'results/web_runs').glob('*/job.json'))}
    result={'controlled_study':'smoke_v2','independent_seeds':2,'saved_conditions':12,'final_score_rows':12,
        'score_rows_including_aliases':len(rows),'unique_accepted_judgments':sum(j['judgment'] is not None for j in judgments),
        'api_attempts':len(events),'successful_api_attempts':sum(e['status']=='ok' for e in events),
        'request_failures':dict(Counter(e.get('error') for e in events if e.get('error'))),
        'reported_tokens_lower_bound':sum(e.get('total_tokens') or 0 for e in events),
        'unknown_usage_attempts':sum(e.get('total_tokens') is None for e in events),
        'wall_seconds':duration,'reviewer_failures':sum(bool(o['error']) for r in runs for rd in r['rounds'] for o in rd['reviews']),
        'judge_failures':sum(j['judgment'] is None for j in judgments),
        'successful_reviews_by_role':dict(review_count),'reviews_with_off_role_scores':dict(leakage),
        'main_means':means,'progression_means':progression,'cases':cases,'protected_integrity':protected,
        'inference':'Descriptive only. No p-values, power claims, human agreement estimates or causal role ranking.'}
    write_csv('final_individual_scores.csv',finals);write_csv('mean_scores.csv',means)
    write_csv('paired_differences.csv',paired);write_csv('iteration_means.csv',progression)
    write_csv('resource_records.csv',resources)
    save_json(OUT/'finalized_results.json',result);save_json(OUT/'source_hashes.json',hashes)
    print(json.dumps({k:result[k] for k in ['independent_seeds','saved_conditions','unique_accepted_judgments','api_attempts','request_failures','reported_tokens_lower_bound','wall_seconds','successful_reviews_by_role','reviews_with_off_role_scores']},indent=2))

if __name__=='__main__':main()
