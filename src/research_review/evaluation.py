"""Blinded, separately prompted judge. Never supplies review scores or system labels."""
import csv
import random
import statistics
from .schemas import Judgment
from .idea_generator import SAFETY
from .literature_retrieval import unique_papers, verify_evidence
from .storage import digest, load_json, save_json
from .evidence_catalog import PROTOCOL, generate_grounded
from .judge_retrieval import build_judge_context, JUDGE_RETRIEVAL_PROTOCOL

METRICS = ['novelty','feasibility','clarity','importance','evidence_grounding']
RUBRIC = '''Independently evaluate the proposal, not its writing style or presumed source.
Score each metric 1-5, using the full scale and a rationale per metric.
Novelty: 1=duplicates supplied prior art, 2=minor change, 3=plausible incremental advance,
4=substantive distinct mechanism/test, 5=exceptionally distinct and well justified.
Feasibility: 1=critical unresolvable resource/data flaw, 2=major gaps, 3=implementable with stated risks,
4=concrete realistic plan, 5=fully specified robust plan under given constraints.
Clarity: 1=uninterpretable, 2=ambiguous, 3=understandable with omissions, 4=precise/testable,
5=unambiguous operational definitions and reproducible experiment specification.
Importance: 1=trivial/unsupported need, 2=weak benefit, 3=meaningful bounded question,
4=valuable problem with useful outcomes, 5=exceptional scientific value with strong justification.
Evidence grounding: 1=unsupported/contradicted claims, 2=mostly unsupported, 3=mixed support,
4=mostly supported with qualified gaps, 5=all central literature claims traceably supported.
Cite only supplied passages by their passage_id. Do not assume novelty from missing hits.
Evidence grounding is a judged support score; resolving IDs or matching excerpts alone is not correctness.
If search failed, explicitly qualify novelty and grounding uncertainty. Keep rationale keys exactly the five metrics.'''

RUBRIC += '''\nInspect prior_work_comparison rather than assuming that combining methods is novel.
Treat assumption_checks as plans, not executed validation. Penalize unsupported guarantees about
memory fit, dataset accessibility, statistical power, causal effects or expected performance.
Distinguish an auxiliary probe's training from LLM training. State important unresolved checks.'''
RUBRIC += '''\nUse the supplied source passages to inspect the closest mechanisms, including papers
explicitly cited or compared by the proposal. Source availability does not validate the proposal's
interpretation of that paper. Consider reported missing/omitted citations, search failures and the
context cap when expressing uncertainty. Never infer novelty from missing evidence.'''

RUBRIC += """
Do not reward removal of a named model or insertion of citations as feasibility improvement. Evaluate the complete precision sweep and its reference, not just its cheapest configuration. Check that the minimum test identifies the claimed effect and that hypotheses are not treated as pilot success criteria.
Do not award feasibility 4 merely because a proposal mentions a small dataset and 12GB GPU.
Inspect named model/data access, uncertainty-output availability, memory checks, and separate calibration
and test splits. Distinguish operational definitions from merely naming metrics. Unsupported assumptions
must affect the relevant score and rationale. Do not force a score difference between similar proposals.
A background citation supports only its actual task, population and transfer direction; reward-model
transfer and fairness post-processing alone do not establish QA calibration in Urdu. A citation audit
of reviewer claims is not an audit of the whole proposal. Use the full rubric without presuming progress.
"""

def prepare_blind_items(runs,random_seed):
    items = []
    for run in runs:
        versions = [(0,run.initial_idea)]
        # Include every candidate, including rejected ones, so selection is auditable.
        revisions = [(r.index,r.candidate_idea or r.revised_idea) for r in run.rounds
                     if r.candidate_idea or r.revised_idea]
        versions += revisions
        final_index = max((r.index for r in run.rounds if r.revised_idea==run.final_idea),default=0)
        for index,idea in versions:
            content_id = digest({'seed':run.seed_id,'replicate':run.replicate,'idea':idea.model_dump()})[:24]
            items.append({'blind_id':content_id,'seed_id':run.seed_id,'replicate':run.replicate,
                          'configuration':run.configuration,'round':index,'run_id':run.run_id,
                          'is_final':idea==run.final_idea and index==final_index,
                          'accepted':index==0 or any(r.index==index and r.revised_idea==idea for r in run.rounds),
                          'idea':idea.model_dump()})
    random.Random(random_seed).shuffle(items)
    return items

def evaluate_runs(runs,judge,retriever,settings,output_dir):
    if any(r.provenance!='live_gemini' for r in runs):
        raise ValueError('Experimental evaluation refuses unit-test fixtures')
    items = prepare_blind_items(runs,settings.random_seed)
    groups = {}
    for item in items:
        groups.setdefault((item['seed_id'],item['replicate']),[]).append(item['idea'])
    contexts = {}
    for key, proposals in groups.items():
        sources = unique_papers([p for run in runs if (run.seed_id,run.replicate)==key
                                 for p in run.literature])
        contexts[key] = build_judge_context(proposals,retriever,sources)
    hashes = {}
    # Refuse incompatible caches before modifying blind keys, scores, or judgments.
    for item in items:
        context = contexts[(item['seed_id'],item['replicate'])]
        hashes[item['blind_id']] = digest({'idea':item['idea'],'model':settings.judge_model,'rubric':RUBRIC,
            'settings':settings.model_dump(exclude={'max_api_calls'}),'evidence_protocol':PROTOCOL,
            'judge_retrieval_protocol':JUDGE_RETRIEVAL_PROTOCOL,'context_fingerprint':context['fingerprint']})
        path = output_dir/'judgments'/f"{item['blind_id']}.json"
        if path.exists() and load_json(path)['spec_hash'] != hashes[item['blind_id']]:
            raise ValueError('Judge settings or evidence changed; use a new evaluation directory')
    save_json(output_dir/'blind_key.json',items)
    judged, rows = {}, []
    # Duplicate content is evaluated once; aliases retain mapping for paired analysis.
    for item in items:
        blind_id = item['blind_id']
        if blind_id not in judged:
            path = output_dir/'judgments'/f'{blind_id}.json'
            spec_hash = hashes[blind_id]
            context = contexts[(item['seed_id'],item['replicate'])]
            if path.exists():
                cached = load_json(path)
                if cached['spec_hash'] != spec_hash:
                    raise ValueError('Judge settings changed; use a new evaluation directory')
                judged[blind_id] = cached
            else:
                searches, papers = context['searches'], context['papers']
                start = len(judge.events)
                replications=[]
                for repeat in range(settings.judge_repeats):
                    repeat_start=len(judge.events)
                    try:
                        result = generate_grounded(judge,Judgment,SAFETY+'\n'+RUBRIC,{
                            'proposal':item['idea'],'constraints':settings.constraints,
                            'literature':[p.model_dump() for p in papers],
                            'search_status':[s.status for s in searches],
                            'retrieval_coverage':context['coverage']},papers,'blinded_judge',model=settings.judge_model)
                        verify_evidence(result.evidence,papers)
                        if papers and not result.evidence:
                            raise ValueError('Grounded judge must cite retrieved evidence')
                        replications.append({'repeat':repeat,'judgment':result.model_dump(),'error':None,
                                             'events':judge.events[repeat_start:]})
                    except Exception as exc:
                        from .llm import BudgetExceeded
                        if isinstance(exc,BudgetExceeded):raise
                        replications.append({'repeat':repeat,'judgment':None,'error':str(exc),
                                             'events':judge.events[repeat_start:]})
                complete=all(r['judgment'] for r in replications)
                summary={m:{'median':statistics.median(r['judgment'][m] for r in replications),
                            'min':min(r['judgment'][m] for r in replications),
                            'max':max(r['judgment'][m] for r in replications)} for m in METRICS} if complete else {}
                record={'blind_id':blind_id,'spec_hash':spec_hash,
                        'judgment':replications[0]['judgment'] if complete else None,
                        'replications':replications,'score_summary':summary,
                        'search':[s.model_dump() for s in searches],'events':judge.events[start:],
                        'error':None if complete else 'One or more planned judge repetitions failed; aggregate withheld.'}
                record['literature_context'] = {'coverage':context['coverage'],
                    'fingerprint':context['fingerprint'],'queries':context['queries'],
                    'papers':[p.model_dump() for p in papers]}
                save_json(path,record)
                judged[blind_id] = record
        record = judged[blind_id]
        row = {k:v for k,v in item.items() if k!='idea'}
        row.update({m:(record.get('score_summary',{}).get(m,{}).get('median',record['judgment'][m]) if record['judgment'] else None) for m in METRICS})
        row.update(judge_error=record['error'],judge_model=settings.judge_model,judge_repeats=settings.judge_repeats,
                   max_rating_range=max((v['max']-v['min'] for v in record.get('score_summary',{}).values()),default=0))
        rows.append(row)
    write_csv(output_dir/'scores.csv',rows)
    human = [{'blind_id':i['blind_id'],'proposal_json':__import__('json').dumps(i['idea']),
              'rater_id':'',**{m:'' for m in METRICS},'comments':''} for i in {i['blind_id']:i for i in items}.values()]
    random.Random(settings.random_seed+1).shuffle(human)
    # Preserve ratings a human may already have filled in on a resumed run.
    if not (output_dir/'human_ratings.csv').exists():
        write_csv(output_dir/'human_ratings.csv',human)
    from .human_evaluation import write_packet
    write_packet(output_dir,items,contexts,RUBRIC)
    return rows

def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    if rows:
        with path.open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
