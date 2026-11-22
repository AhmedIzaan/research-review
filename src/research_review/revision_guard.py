"""A conservative refinement safeguard, separate from independent outcome evaluation."""
from .proposal_checks import revision_changes
from .schemas import ComparativeRevisionCheck
from .idea_generator import SAFETY,qualitative_feedback
from .evidence_catalog import generate_grounded
from .literature_retrieval import verify_evidence

PROMPT='''Compare the incumbent proposal and proposed revision against the same source literature.
You are a refinement safeguard, not the independent experimental judge. Do not reward persuasive wording.
Check whether the distinctive scientific mechanism and falsifiable hypothesis survived scope reductions.
Check the feedback dependency_verification experiment_checks. Explain how each repair_required issue changed. Removing a resource name is loss of specificity, not a feasibility gain. Resource fit remains untested until measured.
A pivot is meaningful only if a concrete scientific distinction replaces a literature-overlapped claim.
Rate each direction as improved, unchanged, reduced, or uncertain; use uncertain when evidence is insufficient.
List critical regressions, genuinely addressed feedback, and unresolved issues. Treat resource checks as
unexecuted plans. Check baselines, calibration, confounds, data access and realistic resource assumptions.
A feasibility gain does not erase a novelty loss. Do not invent evidence or demand ever-increasing complexity.
Explain why any pivot is justified. Select passages only for claims the supplied text actually supports.'''

PROMPT += """
Compare risks explicitly in comparative_risks. For each important concern, describe its state in
both proposals, classify introduced/worsened/unchanged/mitigated/resolved, severity and next_check.
A generic concern already present in the incumbent is not a new regression. Do not veto a partial
improvement simply because an empirical assumption remains untested. Reserve blocking severity for
concrete failures of validity or implementation, explaining why the candidate is worse than the incumbent.
For each substantive reviewer criticism, identify the specific candidate field and changed
procedure in candidate_state. If the relevant procedure is unchanged, mark the risk unchanged,
not mitigated/resolved. Additional references do not fix measurement validity. A named metric
without an operational procedure is unresolved. Explain any intentionally deferred repair.
Include every critical_issues entry in comparative_risks. List inherited uncertainties transparently.
Do not call a new control or bootstrap interval a novel mechanism or a solution to sample scarcity.
Claim improved only for an identifiable substantive change; name the change in your explanation.
A source about reward-model transfer or fairness does not establish Urdu QA calibration performance.
Match population, task and direction of transfer before citing support; otherwise label context only.
"""


def check_revision(client,before,candidate,feedback,papers,constraints,index):
    result=generate_grounded(client,ComparativeRevisionCheck,SAFETY+'\n'+PROMPT,{
        'incumbent':before.model_dump(),'candidate':candidate.model_dump(),
        'observed_field_changes':revision_changes(before,candidate),'feedback':qualitative_feedback(feedback),'literature':[p.model_dump() for p in papers],
        'constraints':constraints},papers,f'revision_guard_{index}')
    verify_evidence(result.evidence,papers)
    return result


def select_revision(check):
    """Reject explicit regressions, unsupported pivots, and wholly uncertain progress.

    This is a judgment-dependent safeguard, never a guarantee about true quality.
    Both proposals remain in the trace and are eligible for independent evaluation.
    """
    if check.comparative_risks is None:
        # Historical/manual checks retain their original conservative interpretation.
        if check.critical_issues:
            return False,'Legacy check lacks comparative risk evidence: '+'; '.join(check.critical_issues)
    else:
        blockers=[r for r in check.comparative_risks
                  if r.change in ('introduced','worsened') and r.severity=='blocking']
        if blockers:
            return False,'Candidate introduces or worsens blocking risks: '+'; '.join(
                r.issue+' — '+r.reasoning for r in blockers)
        if check.critical_issues and not check.comparative_risks:
            return False,'Critical concerns lack the required incumbent/candidate comparison.'
    if check.mechanism_status in ('lost','uncertain'):
        return False,'The scientific mechanism was lost or its preservation is uncertain.'
    directions=[getattr(check,m) for m in ['novelty','feasibility','clarity','importance','evidence_grounding']]
    if 'reduced' in directions:
        return False,'A judged regression was identified; keep the incumbent and retain the candidate for inspection.'
    if check.novelty=='uncertain' or check.feasibility=='uncertain':
        return False,'Novelty or feasibility is unresolved; preserve the incumbent rather than claim progress.'
    if 'improved' not in directions:
        return False,'No substantive improvement was identified; stop at a plateau.'
    return True,'Substantive improvement with no identified regression or new blocking risk. Inherited risks remain provisional and require the recorded checks.'
