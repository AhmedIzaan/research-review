"""Isolated reviewer assessments: no reviewer receives another agent's critique."""
from .schemas import Review, ReviewOutcome, ROLE_METRICS
from .idea_generator import SAFETY
from .literature_retrieval import unique_papers, verify_evidence
from .llm import BudgetExceeded, LLMError
from .evidence_catalog import generate_grounded

ROLE_PROMPTS = {
 'novelty': '''Review originality only. Compare the proposed mechanism, task and evaluation with retrieved
prior work. Identify overlaps and distinguish incremental changes from meaningful contributions.
Provide novelty 1-5, explanation, concrete problems and novelty improvements. Select supplied source
passage IDs for overlaps. Compare the closest existing mechanism with the proposed difference,
including newly added filtering, gating or interventions. Cite a passage describing the actual
overlapping mechanism, not a generic motivation sentence. Do not discuss GPU sizing or score other
dimensions. Explicitly state search coverage limitations; never infer originality from no hits.''',
 'feasibility': '''Review practical implementability only. Examine public data access/licensing, leakage,
compute/memory, API dependency, implementation difficulty, time and statistical design under the constraints.
Give feasibility 1-5 and actionable scope reductions or substitute datasets/methods. Treat unsupported
availability and performance expectations as assumptions. Distinguish frozen LLM inference from fitting
an auxiliary classifier. A 12GB GPU is not automatically impossible: consider model size, context length,
batch size, selected layers, quantization, and actual memory measurements. Require a pilot memory/time
check, dataset verification and a power or precision plan with fallbacks. Do not score other dimensions.''',
 'clarity': '''Review clarity and scientific importance. Give separate clarity and importance scores 1-5.
Check operational definitions, logical consistency, testable predictions, named baselines, meaningful metrics,
confounders and why the result would be useful even if negative. Focus criticism on operational
definitions and the link between measurements and claims, rather than repeating hardware criticism.
Require ablations/simpler baselines and distinguish intervention effects from correlation.
Suggest precise revisions. Do not score novelty or feasibility.''',
 'contrarian': '''Act as a substantive adversarial reviewer. Challenge the central mechanism and assumptions,
identify a plausible null explanation, strongest simpler alternative, failure modes and a decisive falsification
experiment. Explain reasons and recommendations. Do not manufacture disagreement or use insults.
All numerical scores must be null. Provide a concrete falsification_test that would distinguish the
proposed mechanism from the strongest simpler explanation. Focus on scientific assumptions rather than
repeating generic GPU concerns. Literature claims must use supplied evidence or be marked conjectures.''',
 'generic': '''Give one general research review with novelty, feasibility, clarity and importance scores 1-5.
Identify weaknesses and suggest improvements across the proposal using the supplied initial literature.''',
}

ROLE_PROMPTS['novelty'] += """ A useful empirical contribution need not invent an algorithm.
Do not demand more languages or a new confidence metric automatically. Identify the closest actual
mechanism and a bounded unanswered question. Background motivation is not evidence of overlap."""
ROLE_PROMPTS['feasibility'] += """ Do not assert that an unnamed model fits 12GB or that 200 examples
are adequate/inadequate without a workload or precision argument. Require a named model, data route,
probability-access plan, memory pilot, disjoint splits and sampling uncertainty. Mark unknowns."""
ROLE_PROMPTS['contrarian'] += """ Separate a plausible alternative explanation from a demonstrated flaw.
Avoid claims that one failed transfer test 'proves' a cause: domain and annotation shifts may explain it.
Propose the smallest discriminating control rather than demanding unlimited additional datasets."""

def review_idea(client, retriever, role, idea, literature, constraints, index, novelty_retrieval=True, reviewer_id=None):
    searches, papers = [], list(literature)
    status = 'not_required'
    if role == 'novelty':
        if novelty_retrieval:
            queries = list(idea.search_queries)
            if index == 'final':
                # Cover the revised mechanism even if the model repeats its old broad queries.
                mechanism_query = ' '.join((idea.title+' '+idea.methodology).split()[:40])[:300]
                if mechanism_query not in queries:
                    queries.append(mechanism_query)
            for query in queries:
                searches.extend(retriever.related(query,limit=5))
            evidence_papers = unique_papers([p for s in searches for p in s.papers])
            papers = unique_papers(papers+evidence_papers)
            status = 'unavailable'  # set only after citations pass validation
            if not evidence_papers:
                return ReviewOutcome(role=role,reviewer_id=reviewer_id,search=searches,error='No prior-art search evidence available; novelty review withheld',evidence_status='unavailable')
        else:
            status = 'disabled'
    content = {'role':role,'reviewer_id':reviewer_id,'proposal':idea.model_dump(),'literature':[p.model_dump() for p in papers],
               'constraints':constraints,'novelty_search_enabled':novelty_retrieval if role=='novelty' else None}
    try:
        review = generate_grounded(client,Review,SAFETY+'\n'+ROLE_PROMPTS[role]+'''
Set role to the requested role exactly. Unused scores must be null. Include uncertainty.
Use tradeoffs to record substantive tensions (e.g. novelty versus resource scope); do not manufacture them.
Score anchors: 1=serious deficiencies, 2=weak, 3=adequate with limitations, 4=strong, 5=exceptional.''',content,papers,f'{role}_review_{index}' if not reviewer_id or role!='generic' else f'{reviewer_id}_review_{index}')
        if review.role != role:
            raise ValueError('Reviewer returned wrong role')
        verify_evidence(review.evidence,papers)
        if role == 'novelty' and novelty_retrieval:
            searched_ids = {p.paper_id for s in searches for p in s.papers}
            if not any(e.paper_id in searched_ids for e in review.evidence):
                raise ValueError('Novelty reviewer must cite at least one searched paper with a verified excerpt')
            status = 'verified_excerpt'
        elif review.evidence and status != 'disabled':
            status = 'verified_excerpt'
        return ReviewOutcome(role=role,reviewer_id=reviewer_id,review=review,search=searches,evidence_status=status)
    except BudgetExceeded:
        raise
    except (LLMError, ValueError) as exc:
        return ReviewOutcome(role=role,reviewer_id=reviewer_id,search=searches,error=str(exc),evidence_status=status)

def aggregate_feedback(outcomes):
    """Lossless critiques and explicit score disagreement; no extra synthesis LLM."""
    reviews = [o.review for o in outcomes if o.review is not None]
    scores, disagreements = {}, []
    for metric in ('novelty','feasibility','clarity','importance'):
        values = {(o.reviewer_id or o.role):getattr(o.review,metric) for o in outcomes
                  if o.review and metric in ROLE_METRICS[o.role] and getattr(o.review,metric) is not None}
        scores[metric] = values
        if values and max(values.values())-min(values.values()) >= 2:
            disagreements.append({'metric':metric,'scores':values})
    return {'independent_reviews':[{**o.review.model_dump(),'reviewer_id':o.reviewer_id} for o in outcomes if o.review], 'scores_by_role':scores,
            'score_disagreements':disagreements,
            'qualitative_tradeoffs':[{'role':r.role,'tension':t} for r in reviews for t in r.tradeoffs],
            'score_policy':'Only designated role scores are aggregated. Distinct scores do not imply distinct model beliefs.',
            'instruction':'Preserve all criticisms and textual trade-offs; absence of score disagreement does not imply agreement.',
            'failures':[{'role':o.role,'error':o.error} for o in outcomes if o.error],
            'evidence_status':{o.role:o.evidence_status for o in outcomes}}
