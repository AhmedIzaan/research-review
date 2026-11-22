"""Bounded state workflow, with LangGraph adapter and dependency-light engine."""
import importlib.util
import time
from pathlib import Path
from typing import TypedDict
from .config import CONFIGURATIONS, ROOT
from .factual_verification import verify_proposal, VerificationReport, acceptance_issue
from .schemas import Round, Run, ReviewOutcome
from .revision_guard import check_revision, select_revision
from .idea_generator import revise_idea
from .reviewer_agents import aggregate_feedback, review_idea
from .literature_retrieval import unique_papers
from .llm import BudgetExceeded, LLMError
from .storage import digest, save_json
from .evidence_audit import audit_claim_support, collect_citations

class State(TypedDict):
    idea: object
    rounds: list
    stop_reason: str
    evidence_papers: list

class Workflow:
    def __init__(self,client,retriever,settings,observer=None):
        self.client,self.retriever,self.settings = client,retriever,settings
        self.observer = observer or (lambda event, payload: None)

    def run(self,seed_id,configuration,initial,literature,output_dir=None,replicate=0):
        if configuration not in CONFIGURATIONS:
            raise ValueError('Unknown experimental configuration')
        started, offset = time.monotonic(),len(self.client.events)
        state = {'idea':initial.model_copy(deep=True),'rounds':[],'stop_reason':'','evidence_papers':list(literature)}
        run_id = digest({'seed':seed_id,'configuration':configuration,'replicate':replicate,
                         'initial':initial.model_dump(),'settings':self.settings.model_dump()})[:20]
        checkpoint = Path(output_dir)/f'{run_id}.partial.json' if output_dir else None
        if output_dir and (Path(output_dir)/f'{run_id}.json').exists():
            raise FileExistsError('A saved run already exists; select a new study directory')

        from .online_sources import OnlineSources
        online=OnlineSources(Path(output_dir).parent/'online_sources') if self.settings.online_source_lookup and output_dir else None
        if self.settings.online_source_lookup and online is None:
            raise ValueError('Online lookup requires an output directory for pinned source evidence')
        verification_cache={}
        def verify(idea,papers):
            key=digest(idea.model_dump())
            if key not in verification_cache:
                self.observer('dependency_verification_started',{'proposal_hash':key})
                try:
                    report=verify_proposal(self.client,self.retriever,idea,papers,
                        ROOT/self.settings.verification_sources,online=online)
                except BudgetExceeded:
                    raise
                except (LLMError,ValueError,OSError) as exc:
                    report=VerificationReport(proposal_hash=key,status='failed',error=str(exc))
                verification_cache[key]=report
                self.observer('dependency_verification_completed',report.model_dump())
            return verification_cache[key]
        initial_verification=None
        if self.settings.verify_dependencies:
            initial_verification=verify(initial,literature)

        def step(s):
            index = len(s['rounds'])+1
            outcomes = []
            budget_exhausted = False
            for slot,role in enumerate(CONFIGURATIONS[configuration],1):
                self.observer('review_started', {'round':index,'role':role})
                try:
                    outcomes.append(review_idea(self.client,self.retriever,role,s['idea'].model_copy(deep=True),
                                    literature,self.settings.constraints,index,configuration!='no_novelty_retrieval',
                                    reviewer_id=f'{role}_{slot}'))
                except BudgetExceeded as exc:
                    outcomes.append(ReviewOutcome(role=role,error=str(exc)))
                    budget_exhausted = True
                    break
                self.observer('review_completed', {'round':index,**outcomes[-1].model_dump()})
            # Each reviewer sees identical current idea and seed context, never other critiques.
            aggregation = aggregate_feedback(outcomes)
            record = Round(index=index,input_idea=s['idea'],reviews=outcomes,aggregation=aggregation)
            if self.settings.verify_dependencies:
                report=verify(s['idea'],s['evidence_papers'])
                record.input_verification=report.model_dump()
                aggregation['dependency_verification']=report.model_dump()
            stop = ''
            if budget_exhausted:
                stop = 'api_budget_exhausted'
            elif not any(o.review for o in outcomes):
                stop = 'all_reviewers_failed'
            else:
                papers = unique_papers(s['evidence_papers']+[p for o in outcomes for search in o.search for p in search.papers])
                try:
                    candidate = revise_idea(self.client,s['idea'],aggregation,papers,self.settings.constraints,index)
                    record.candidate_idea = candidate
                    from .proposal_checks import revision_changes
                    record.revision_changes = revision_changes(s['idea'],candidate)
                    factual_issue=None
                    if self.settings.verify_dependencies:
                        candidate_report=verify(candidate,papers)
                        record.candidate_verification=candidate_report.model_dump()
                        factual_issue=acceptance_issue(candidate_report)
                        from .proposal_checks import named_model_mentions,searchable_entity
                        has_replacement=any(c['category']=='model_access' and searchable_entity(c['entity']) for c in candidate_report.claims)
                        if not has_replacement and named_model_mentions(s['idea']) and not named_model_mentions(candidate):
                            factual_issue='Candidate removed the identifiable model without specifying a replacement. Preserve an explicit implementation target.'
                    if factual_issue:
                        record.selection,record.selection_reason='rejected',factual_issue
                        stop='dependency_verification_rejected'
                    elif candidate == s['idea']:
                        record.selection,record.selection_reason = 'unchanged','No proposal change.'
                        stop = 'unchanged_proposal'
                    elif (self.settings.revision_policy == 'guarded' and configuration!='full_unguarded'
                          and record.revision_changes['literature_only']):
                        record.selection='rejected'
                        record.selection_reason='Literature-only update: references/comparisons changed, but the experimental proposal was not repaired. Candidate retained for inspection.'
                        stop='revision_guard_rejected'
                    elif self.settings.revision_policy == 'guarded' and configuration!='full_unguarded':
                        try:
                            record.revision_check = check_revision(self.client,s['idea'],candidate,
                                aggregation,papers,self.settings.constraints,index)
                            accepted,reason = select_revision(record.revision_check)
                            record.selection_reason = reason
                            record.selection = 'accepted' if accepted else 'rejected'
                            if accepted:
                                record.revised_idea = candidate
                            else:
                                stop = 'revision_guard_rejected'
                        except BudgetExceeded:
                            raise
                        except (LLMError,ValueError) as exc:
                            record.selection,record.revision_error = 'check_failed',str(exc)
                            record.selection_reason = 'Safeguard failed; incumbent retained.'
                            stop = 'revision_guard_failed'
                    else:
                        record.revised_idea = candidate
                        record.selection,record.selection_reason = 'accepted','Always-accept comparison policy.'
                except BudgetExceeded as exc:
                    record.revision_error,stop = str(exc),'api_budget_exhausted'
                except (LLMError,ValueError) as exc:
                    record.revision_error,stop = str(exc),'revision_failed'
            new = {'idea':record.revised_idea or s['idea'],'rounds':s['rounds']+[record],'stop_reason':stop,
                   'evidence_papers':unique_papers(s['evidence_papers']+[p for o in outcomes for search in o.search for p in search.papers])}
            if checkpoint:
                save_json(checkpoint,{'run_id':run_id,'seed_id':seed_id,'configuration':configuration,
                    'initial_idea':initial.model_dump(),'literature':[p.model_dump() for p in literature],
                    'rounds':[r.model_dump() for r in new['rounds']],'stop_reason':stop})
            self.observer('round_completed', record.model_dump())
            return new

        engine = self.settings.engine
        if engine == 'auto':
            engine = 'langgraph' if importlib.util.find_spec('langgraph') else 'python'
        if engine not in ('langgraph','python'):
            raise ValueError('Engine must be auto, langgraph or python')
        limit = 0 if configuration=='one_shot' else self.settings.rounds
        if engine == 'langgraph' and limit:
            from langgraph.graph import END, START, StateGraph
            graph = StateGraph(State)
            graph.add_node('independent_review_aggregate_revise',step)
            graph.add_edge(START,'independent_review_aggregate_revise')
            graph.add_conditional_edges('independent_review_aggregate_revise',
                lambda s: END if s['stop_reason'] or len(s['rounds'])>=limit else 'independent_review_aggregate_revise')
            state = graph.compile().invoke(state,{'recursion_limit':2*limit+3})
        else:
            while len(state['rounds'])<limit and not state['stop_reason']:
                state = step(state)
        final_reviews, final_status = [], 'not_requested'
        audit, audit_error = None, None
        if self.settings.final_review:
            if not limit or state['stop_reason'] == 'api_budget_exhausted':
                final_status = 'skipped'
            else:
                # Assessment only: the last revision is never left implicitly "approved".
                # Each role still sees the same final proposal without other critiques.
                for slot,role in enumerate(CONFIGURATIONS[configuration],1):
                    self.observer('final_review_started', {'role':role})
                    try:
                        outcome = review_idea(self.client,self.retriever,role,
                            state['idea'].model_copy(deep=True),state['evidence_papers'],
                            self.settings.constraints,'final',configuration!='no_novelty_retrieval',reviewer_id=f'{role}_{slot}')
                    except BudgetExceeded as exc:
                        outcome = ReviewOutcome(role=role,error=str(exc))
                        final_reviews.append(outcome)
                        self.observer('final_review_completed',outcome.model_dump())
                        break
                    final_reviews.append(outcome)
                    self.observer('final_review_completed',outcome.model_dump())
                successes = sum(o.review is not None for o in final_reviews)
                final_status = ('completed' if successes == len(CONFIGURATIONS[configuration])
                                else 'partial' if successes else 'failed')
                state['evidence_papers'] = unique_papers(state['evidence_papers']+
                    [p for o in final_reviews for search in o.search for p in search.papers])
                if self.settings.audit_evidence and successes:
                    self.observer('evidence_audit_started',{})
                    try:
                        audit = audit_claim_support(self.client,final_reviews,state['evidence_papers'])
                    except (LLMError,ValueError) as exc:
                        audit_error = str(exc)
                    self.observer('evidence_audit_completed',{'audit':audit.model_dump() if audit else None,
                                                            'error':audit_error})
        result = Run(initial_verification=initial_verification.model_dump() if initial_verification else None,
                     final_verification=verification_cache[digest(state['idea'].model_dump())].model_dump() if self.settings.verify_dependencies else None,run_id=run_id,seed_id=seed_id,configuration=configuration,replicate=replicate,
                     settings={**self.settings.model_dump(),'resolved_engine':engine},literature=literature,
                     initial_idea=initial,final_idea=state['idea'],rounds=state['rounds'],
                     stop_reason=state['stop_reason'] or ('one_shot' if configuration=='one_shot' else 'zero_review_rounds' if limit==0 else 'iteration_limit'),
                     elapsed_seconds=time.monotonic()-started,api_events=self.client.events[offset:],
                     provenance=self.client.provenance,final_reviews=final_reviews,
                     final_review_status=final_status,
                     final_aggregation=aggregate_feedback(final_reviews) if final_reviews else {},
                     evidence_audit=audit,evidence_audit_error=audit_error,
                     evidence_audit_citations=collect_citations(final_reviews))
        if output_dir and result.stop_reason != 'api_budget_exhausted':
            target = Path(output_dir)/f'{run_id}.json'
            if target.exists():
                raise FileExistsError('A saved run already exists; select a new study directory')
            save_json(target,result.model_dump())
            if checkpoint and checkpoint.exists():
                checkpoint.unlink()
        return result
