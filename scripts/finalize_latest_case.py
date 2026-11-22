"""Export the v8 interactive case separately from the controlled pilot; no API calls."""
import csv, hashlib, json, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'research-review-9a20994a1b09f4325e70.json'
OUT=ROOT/'paper/results'
METRICS=['novelty','feasibility','clarity','importance','evidence_grounding']

def main():
    x=json.loads(SOURCE.read_text());r=x['result']
    assert r['provenance']=='live_gemini'
    rows=sorted(x['evaluation'],key=lambda a:a['round'])
    assert [a['round'] for a in rows]==[0,1,2,3]
    details={d['blind_id']:d for d in x['evaluation_details']}
    repetitions=[]
    for row in rows:
        d=details[row['blind_id']]
        assert row['judge_error'] is None and len(d['replications'])==2
        for m in METRICS:
            assert statistics.median(p['judgment'][m] for p in d['replications'])==row[m]
        for p in d['replications']:
            repetitions.append({'round':row['round'],'repeat':p['repeat'],**{m:p['judgment'][m] for m in METRICS}})
    contexts=[d['literature_context'] for d in details.values()]
    assert len({c['fingerprint'] for c in contexts})==1
    summary={'run_id':r['run_id'],'protocol':r['settings']['methodology_version'],
        'source_file':SOURCE.name,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'study_type':'single interactive case; not pooled with controlled pilot','independent_topics':1,
        'judge_repeats':2,'aggregation':'median per metric across two judge calls',
        'scores':[{k:a[k] for k in ['round',*METRICS]} for a in rows],
        'final_minus_initial':{m:rows[-1][m]-rows[0][m] for m in METRICS},
        'shared_judge_context':contexts[0]['coverage'],'context_fingerprint':contexts[0]['fingerprint'],
        'attempts':len(x['api_events']),'successful_attempts':sum(e['status']=='ok' for e in x['api_events']),
        'reported_tokens_lower_bound':sum(e.get('total_tokens') or 0 for e in x['api_events']),
        'unknown_token_attempts':sum(e.get('total_tokens') is None for e in x['api_events']),
        'elapsed_seconds':x['elapsed_seconds'],'stop_reason':r['stop_reason'],
        'initial_verification_status':r['initial_verification']['status'],
        'initial_verification_error':r['initial_verification']['error'],
        'final_verification_status':r['final_verification']['status'],
        'rounds':[{'round':a['index'],'selection':a['selection'],
            'changed_fields':[k for k in a['input_idea'] if a['input_idea'][k]!=a['candidate_idea'][k]]} for a in r['rounds']],
        'limitation':'No human ratings, controlled baseline rerun, or execution of the generated experiment.'}
    OUT.mkdir(exist_ok=True)
    (OUT/'v8_case_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for name,data in [('v8_case_scores.csv',summary['scores']),('v8_case_judge_repetitions.csv',repetitions)]:
        with (OUT/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    final_path=OUT.parent/'FINAL_RESULTS.md'
    final=final_path.read_text().split('\n## Revised-protocol case (v8)')[0]
    final=final.replace('No new live shared-evidence ratings are available.', 'That earlier case was not rejudged; a later live shared-evidence case is reported separately below.')
    final+='\n## Revised-protocol case (v8)\n\n'
    final+=f"Trace `{r['run_id']}` is a single interactive diagnostic, not an additional controlled seed. Each version has two judge calls, aggregated by metric-wise median.\n\n"
    final+='| Stage | N | F | C | I | G |\n|---|---:|---:|---:|---:|---:|\n'
    for row in summary['scores']:
        final+='| '+str(row['round'])+' | '+' | '.join(f"{row[m]:.1f}" for m in METRICS)+' |\n'
    final+='\nGrounding increased 0.5, clarity decreased 0.5, and the other dimensions were unchanged. Three substantive revisions were accepted. All four versions shared 19 source papers from five queries. Execution used 43 attempts (40 successful), 633.24 seconds and at least 496,679 reported tokens; three attempts have unknown token usage. Initial dependency verification failed quotation validation; final verification completed but model access remained unverified.\n\n'
    final+='The NLI/symbolic-oracle inconsistency, unmeasured persuasiveness, unspecified free-text formalization and imprecise memory arithmetic remain limitations and future-work priorities. These results do not establish general superiority. The summary JSON binds the data to the raw trace hash; `v8_case_judge_repetitions.csv` preserves individual ratings.\n'
    final_path.write_text(final)
    print(json.dumps({k:summary[k] for k in ['run_id','final_minus_initial','attempts','unknown_token_attempts']},indent=2))
if __name__=='__main__':main()
