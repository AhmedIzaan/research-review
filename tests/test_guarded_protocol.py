"""Protocol regressions; all scores here are synthetic software fixtures, never findings."""
import csv
from pathlib import Path
import pytest
from research_review.config import Settings,CONFIGURATIONS,ROOT,budget
from research_review.schemas import RevisionCheck
from research_review.revision_guard import select_revision
from research_review.orchestration import Workflow
from research_review.idea_generator import qualitative_feedback
from research_review.evaluation import prepare_blind_items,evaluate_runs,METRICS
from research_review.human_evaluation import analyze_humans,weighted_kappa
from research_review.storage import load_json,save_json
from research_review.llm import LLMError,BudgetExceeded
from conftest import FixtureClient,FixtureRetriever
from test_evaluation import SyntheticJudge,synthetic_saved_runs


def check(**updates):
    return RevisionCheck(**{'mechanism_status':'preserved','pivot_reason':'No pivot',
        **{m:'unchanged' for m in METRICS},'clarity':'improved',
        'explanation':'Synthetic comparison','uncertainty':'Synthetic only',**updates})

@pytest.mark.parametrize('updates',[{'novelty':'reduced'},{'feasibility':'reduced'},
    {'evidence_grounding':'reduced'},{'mechanism_status':'lost'},{'mechanism_status':'uncertain'},
    {'novelty':'uncertain'},{'critical_issues':['Critical synthetic issue']},{'clarity':'unchanged'}])
def test_guard_rejects_regression_uncertainty_and_plateau(updates):
    assert not select_revision(check(**updates))[0]


def test_guard_accepts_qualified_progress_and_justified_pivot():
    assert select_revision(check())[0]
    assert select_revision(check(mechanism_status='meaningful_pivot',pivot_reason='New testable distinction'))[0]


def test_rejection_retains_incumbent_and_independently_evaluates_candidate(idea,paper,monkeypatch):
    monkeypatch.setattr('research_review.orchestration.check_revision',lambda *a:check(novelty='reduced'))
    run=Workflow(FixtureClient(idea),FixtureRetriever(paper),Settings(rounds=3,engine='python',revision_policy='guarded')).run('s','full',idea,[paper])
    assert run.final_idea==idea and len(run.rounds)==1
    assert run.stop_reason=='revision_guard_rejected'
    assert run.rounds[0].candidate_idea!=idea and run.rounds[0].revised_idea is None
    items=prepare_blind_items([run],42)
    assert len(items)==2
    assert sum(i['is_final'] for i in items)==1
    assert next(i for i in items if i['is_final'])['round']==0
    assert next(i for i in items if i['round']==1)['accepted'] is False

@pytest.mark.parametrize('error,reason',[(LLMError('fixture failure'),'revision_guard_failed'),
                                        (BudgetExceeded('fixture cap'),'api_budget_exhausted')])
def test_guard_error_retains_candidate_and_incumbent(idea,paper,monkeypatch,error,reason):
    def fail(*a):raise error
    monkeypatch.setattr('research_review.orchestration.check_revision',fail)
    run=Workflow(FixtureClient(idea),FixtureRetriever(paper),Settings(rounds=3,engine='python',revision_policy='guarded')).run('s','full',idea,[paper])
    assert run.final_idea==idea and run.rounds[0].candidate_idea and run.stop_reason==reason


def test_call_matched_reviews_are_independent_and_aggregation_does_not_collapse(idea,paper):
    client=FixtureClient(idea)
    run=Workflow(client,FixtureRetriever(paper),Settings(rounds=1,engine='python',revision_policy='guarded')).run('s','generic_matched',idea,[paper])
    reviews=run.rounds[0].reviews
    assert len({o.reviewer_id for o in reviews})==4
    assert len(run.rounds[0].aggregation['scores_by_role']['novelty'])==4
    inputs=[c for label,c in client.inputs if label.startswith('generic_')]
    assert len(inputs)==4 and all(c['proposal']==idea.model_dump() and 'feedback' not in c for c in inputs)
    revision=next(c for label,c in client.inputs if label=='revision_1')
    guard=next(c for label,c in client.inputs if label=='revision_guard_1')
    for payload in [revision,guard]:
        assert 'scores_by_role' not in payload['feedback']
        assert all(not set(METRICS)&r.keys() for r in payload['feedback']['independent_reviews'])
    assert run.rounds[0].revised_idea and run.rounds[0].selection=='accepted'


def test_safeguard_ablation_shares_initial_and_uses_one_less_call(idea,paper):
    counts=[]
    for config in ['full','full_unguarded']:
        client=FixtureClient(idea)
        run=Workflow(client,FixtureRetriever(paper),Settings(rounds=1,engine='python',revision_policy='guarded')).run('s',config,idea,[paper])
        assert run.initial_idea==idea
        counts.append(len(client.events))
    assert counts==[6,5]


def test_planner_bounds_all_unique_candidates_and_repetitions(idea,paper):
    for config in CONFIGURATIONS:
        client=FixtureClient(idea)
        settings=Settings(rounds=3,engine='python',revision_policy='guarded',judge_repeats=2)
        run=Workflow(client,FixtureRetriever(paper),settings).run('s',config,idea,[paper])
        plan=budget(1,3,configurations=[config],revision_policy='guarded',judge_repeats=2)
        assert plan['generation_review_calls']==1+len(client.events)
        assert plan['judge_calls_upper_bound']>=2*len({i['blind_id'] for i in prepare_blind_items([run],42)})


def test_repeated_judgments_preserve_individuals_medians_and_cache(idea,paper,tmp_path):
    runs=synthetic_saved_runs(idea,paper,tmp_path)
    class Alternating(SyntheticJudge):
        def generate(self,*a,**kw):
            result=super().generate(*a,**kw)
            return result.model_copy(update={m:3 if len(self.events)%2 else 4 for m in METRICS})
    judge=Alternating();settings=Settings(judge_repeats=2)
    output=tmp_path/'evaluation'
    rows=evaluate_runs(runs,judge,FixtureRetriever(paper),settings,output)
    assert all(r['novelty']==3.5 and r['max_rating_range']==1 for r in rows)
    records=[load_json(p) for p in (output/'judgments').glob('*.json')]
    assert all(len(r['replications'])==2 for r in records)
    assert all(r['score_summary']['novelty']=={'median':3.5,'min':3,'max':4} for r in records)
    human=output/'human_ratings.csv';human.write_text(human.read_text()+'\n')
    saved=human.read_bytes();before=len(judge.events)
    evaluate_runs(runs,judge,FixtureRetriever(paper),settings,output)
    assert len(judge.events)==before and human.read_bytes()==saved
    packet=(output/'human_packet.html').read_text()
    assert 'condition=' not in packet and 'scores_by_role' not in packet


def test_failed_repeat_withholds_aggregate_not_only_failed_rating(idea,paper,tmp_path):
    class Failing(SyntheticJudge):
        def generate(self,*a,**kw):
            if len(self.events)%2:
                self.events.append({'label':'fixture_failure'})
                raise ValueError('Synthetic failure')
            return super().generate(*a,**kw)
    rows=evaluate_runs(synthetic_saved_runs(idea,paper,tmp_path),Failing(),FixtureRetriever(paper),Settings(judge_repeats=2),tmp_path/'evaluation')
    assert all(r['novelty'] is None and r['judge_error'] for r in rows)


def test_fixed_dataset_is_distinct_preoutcome_and_six_strata():
    seeds=load_json(ROOT/'data/evaluation_seeds_v3.json')
    manifest=load_json(ROOT/'data/evaluation_seeds_v3_manifest.json')
    assert len(seeds)==12 and len({p['paper_id'] for p in seeds})==12
    assert len({r['stratum'] for r in manifest['selection'][:6]})==6
    assert all(p['authors'] and len(p['abstract'].split())>=80 and p['url'].startswith('https://aclanthology.org/') for p in seeds)


def test_human_import_is_strict_and_reports_real_agreement(tmp_path):
    save_json(tmp_path/'blind_key.json',[{'blind_id':'abc'}])
    paths=[]
    for rater,value in [('a',3),('b',4)]:
        path=tmp_path/(rater+'.csv');paths.append(path)
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['blind_id','rater_id',*METRICS]);w.writeheader()
            w.writerow({'blind_id':'abc','rater_id':rater,**{m:value for m in METRICS}})
    summary=analyze_humans(tmp_path,paths,tmp_path/'human')
    assert summary[0]['novelty']==3.5
    assert len(load_json(tmp_path/'human/agreement.json')['agreement'])==5
    with pytest.raises(ValueError,match='Duplicate'):analyze_humans(tmp_path,[paths[0],paths[0]],tmp_path/'bad')
    paths[0].write_text(paths[0].read_text().replace(',3',',3.5'))
    with pytest.raises(ValueError,match='integer'):analyze_humans(tmp_path,[paths[0]],tmp_path/'bad')
    assert weighted_kappa([1,2,3],[1,2,3])==1
    assert weighted_kappa([3,3],[3,3]) is None


def test_judge_resume_accept_cap_change_does_not_invalidate_scores(idea,paper,tmp_path):
    runs=synthetic_saved_runs(idea,paper,tmp_path)
    settings=Settings(judge_repeats=2)
    judge=SyntheticJudge();output=tmp_path/'evaluation'
    evaluate_runs(runs,judge,FixtureRetriever(paper),settings,output)
    resumed=SyntheticJudge()
    evaluate_runs(runs,resumed,FixtureRetriever(paper),settings.model_copy(update={'max_api_calls':500}),output)
    assert not resumed.events


def test_default_cli_dry_run_is_network_free_and_does_not_write_study(tmp_path,capsys):
    from research_review.runner import main
    target=tmp_path/'study'
    assert main(['--study',str(target),'--dry-run'])==0
    output=capsys.readouterr().out
    assert '147' in output and '441' in output
    assert not target.exists()

@pytest.mark.parametrize('change,expected',[('introduced',False),('worsened',False),('unchanged',True),('mitigated',True),('resolved',True)])
def test_comparative_guard_distinguishes_inherited_risks(change,expected):
    risk={'issue':'Calibration variance','incumbent_state':'Small sample without intervals',
          'candidate_state':'Same sample with stability checks','change':change,'severity':'blocking',
          'reasoning':'Synthetic comparative assessment','next_check':'Measure interval width on held-out data'}
    result=check(critical_issues=['Calibration variance'],comparative_risks=[risk])
    assert select_revision(result)[0] is expected


def test_saved_urdu_guard_is_not_retroactively_reinterpreted():
    path=ROOT/'research-review-c38e53f68a543cfcc090.json'
    if not path.exists():pytest.skip('Optional user trace')
    raw=load_json(path)['result']['rounds'][0]['revision_check']
    historic=RevisionCheck.model_validate(raw)
    assert historic.novelty=='improved' and historic.critical_issues
    assert not select_revision(historic)[0]
