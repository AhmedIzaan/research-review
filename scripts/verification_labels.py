"""Export blinded claim labels or assess verifier predictions against real human labels."""
import argparse,csv,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('trace',type=Path);p.add_argument('--output',type=Path,required=True)
p.add_argument('--labels',type=Path)
a=p.parse_args();job=json.loads(a.trace.read_text());run=job.get('result',job)
reports=[run.get('initial_verification'),run.get('final_verification')]
reports += [r.get('candidate_verification') for r in run.get('rounds',[])]
claims={}
for report in reports:
    if not report:continue
    for c in report['claims']:
        key=report['proposal_hash']+':'+c['claim_id']
        claims[key]=(c,report['sources'])
if not claims:p.error('Trace contains no dependency checks')
if a.output.exists():p.error('Output exists; use a new filename')
a.output.parent.mkdir(parents=True,exist_ok=True)
if not a.labels:
    with a.output.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['id','claim','proposal_excerpt','sources_json','human_verdict','rater_id','notes']);w.writeheader()
        for key,(c,sources) in claims.items():w.writerow({'id':key,'claim':c['claim'],'proposal_excerpt':c['proposal_excerpt'],
            'sources_json':json.dumps(sources),'human_verdict':'','rater_id':'','notes':''})
else:
    rows=list(csv.DictReader(a.labels.open()));scored=[];seen=set()
    for row in rows:
        if not row.get('human_verdict'):continue
        key=row['id'];truth=row['human_verdict']
        if key not in claims or key in seen or truth not in {'supported','contradicted','unverified','requires_measurement'} or not row.get('rater_id'):
            raise ValueError('Invalid or duplicate label; submit one adjudicated label per claim')
        seen.add(key);scored.append((truth,claims[key][0]['verdict']))
    if not scored:raise ValueError('No real labels supplied')
    approved=[(t,v) for t,v in scored if v=='supported'];contradictions=[(t,v) for t,v in scored if t=='contradicted']
    report={'labeled_claims':len(scored),'accuracy':sum(t==v for t,v in scored)/len(scored),
      'false_approval_fraction':sum(t!='supported' for t,v in approved)/len(approved) if approved else None,
      'contradiction_recall':sum(v=='contradicted' for t,v in contradictions)/len(contradictions) if contradictions else None,
      'limitations':'Descriptive agreement with supplied human labels, not guaranteed truth. Sampling and label adjudication must be documented.'}
    a.output.write_text(json.dumps(report,indent=2)+'\n')
print('Saved',a.output)
