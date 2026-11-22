"""Descriptive plots and paired ordinal comparisons from actual judge outputs only."""
import json
from pathlib import Path
from .evaluation import METRICS, write_csv
from .storage import load_json
from .config import CONFIGURATIONS


def analyze(study_dir):
    scores_path=study_dir/'evaluation'/'scores.csv'
    if not scores_path.exists():
        return {'status':'not_run','reason':'No independent evaluation scores exist. No charts or findings fabricated.'}
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    df=pd.read_csv(scores_path)
    valid=df.dropna(subset=METRICS)
    if valid.empty:
        return {'status':'no_valid_judgments','judge_failures':len(df)}
    out=study_dir/'analysis';out.mkdir(parents=True,exist_ok=True)
    # Repeated runs collapse within seed before statistical tests.
    final=valid[valid.is_final.astype(str).str.lower().eq('true')]
    seed_scores=final.groupby(['seed_id','configuration'])[METRICS].mean().reset_index()
    summary=seed_scores.groupby('configuration')[METRICS].agg(['count','mean','median','std']).reindex(list(CONFIGURATIONS))
    for metric in METRICS:
        summary[(metric,'count')]=summary[(metric,'count')].fillna(0).astype(int)
    summary.to_csv(out/'summary.csv')
    df[df[METRICS].isna().any(axis=1)].to_csv(out/'missing_evaluation_rows.csv',index=False)
    comparisons=[]
    for metric in METRICS:
        table=seed_scores.pivot(index='seed_id',columns='configuration',values=metric).reindex(columns=list(CONFIGURATIONS))
        if 'full' not in table: continue
        for other in table.columns.drop('full'):
            paired=table[['full',other]].dropna()
            dif=paired['full']-paired[other]
            row={'metric':metric,'comparison':'full vs '+other,'n_seeds':len(dif),
                 'mean_paired_difference':dif.mean(),'median_paired_difference':dif.median(),
                 'positive':int((dif>0).sum()),'negative':int((dif<0).sum()),'ties':int((dif==0).sum()),
                 'wilcoxon_p':None,'holm_adjusted_p':None,'rank_biserial':None,
                 'inference_status':'descriptive only: fewer than 10 nonzero paired seed differences'}
            nonzero=dif[dif!=0]
            if len(nonzero)>=10:
                try:
                    from scipy.stats import rankdata,wilcoxon
                    ranks=rankdata(abs(nonzero))
                    row['rank_biserial']=float((ranks[nonzero>0].sum()-ranks[nonzero<0].sum())/ranks.sum())
                    row['wilcoxon_p']=float(wilcoxon(dif,zero_method='wilcox',alternative='two-sided',method='approx').pvalue)
                    row['inference_status']='exploratory paired ordinal test; symmetry assumed; Holm family correction'
                except ImportError:
                    row['inference_status']='descriptive only: SciPy unavailable'
            comparisons.append(row)
    tested=sorted([r for r in comparisons if r['wilcoxon_p'] is not None],key=lambda x:x['wilcoxon_p'])
    previous=0
    for i,row in enumerate(tested):
        previous=max(previous,min(1,row['wilcoxon_p']*(len(tested)-i)))
        row['holm_adjusted_p']=previous
    if comparisons:
        write_csv(out/'paired_comparisons.csv',comparisons)
    else:
        (out/'paired_comparisons.csv').write_text('metric,comparison,n_seeds,mean_paired_difference,median_paired_difference,wilcoxon_p\n')
    plt.rcParams.update({'figure.dpi':150,'savefig.dpi':300,'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    def save(name):
        plt.tight_layout();plt.savefig(out/(name+'.png'),bbox_inches='tight');plt.savefig(out/(name+'.pdf'),bbox_inches='tight');plt.close()
    def bars(configs,name):
        data=seed_scores[seed_scores.configuration.isin(configs)]
        counts=data.groupby('configuration').seed_id.nunique()
        ax=data.groupby('configuration')[METRICS].mean().reindex(configs).plot.bar(figsize=(10,4),ylim=(0,5.3))
        ax.set_xticklabels([f'{c}\n(n={counts.get(c,0)})' for c in configs],rotation=20,ha='right')
        for index,condition in enumerate(configs):
            if not counts.get(condition,0):
                ax.text(index,0.2,'Unscored',ha='center',fontsize=8)
        ax.set_ylabel('Independent judge score (1–5)');ax.set_xlabel('');ax.legend(bbox_to_anchor=(1.01,1));save(name)
    bars(['one_shot','generic','generic_matched','full'],'baseline_comparison')
    bars(['full','full_unguarded','no_feasibility','no_contrarian','no_novelty_retrieval','feasibility_to_generic','contrarian_to_generic'],'ablation_comparison')
    accepted=valid if 'accepted' not in valid else valid[valid.accepted.astype(str).str.lower().eq('true')]
    full=accepted[accepted.configuration.eq('full')].groupby(['seed_id','round'])[METRICS].mean().reset_index()
    full.to_csv(out/'iteration_scores.csv',index=False)
    seed_ids=list(full.seed_id.unique())
    fig,axes=plt.subplots(1,max(1,len(seed_ids)),figsize=(7*max(1,len(seed_ids)),4),squeeze=False)
    for ax,seed_id in zip(axes[0],seed_ids):
        data=full[full.seed_id.eq(seed_id)].set_index('round')[METRICS].reindex([0,1,2,3])
        data.plot(ax=ax,marker='o',ylim=(0.8,5.2),legend=False)
        ax.set(title=seed_id,ylabel='Independent judge score',xlabel='Revision round',xticks=[0,1,2,3])
    if seed_ids:
        handles,labels=axes[0][0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(0.5,1.0),ncol=5,fontsize=8)
    save('iteration_progression')
    fig,ax=plt.subplots(figsize=(6,5))
    for condition,g in seed_scores.groupby('configuration'):
        ax.scatter(g.novelty,g.feasibility,label=condition,alpha=0.7)
    ax.set(xlabel='Novelty',ylabel='Feasibility',xlim=(0.8,5.2),ylim=(0.8,5.2));ax.legend(fontsize=7);save('novelty_feasibility')
    resources=[]
    guard_decisions=[]
    for path in (study_dir/'runs').glob('*.json'):
        if path.name.endswith('.partial.json'):continue
        r=load_json(path)
        if r['provenance']!='live_gemini':raise ValueError('Analysis refuses fixtures')
        events=r['api_events']
        for rd in r['rounds']:
            candidate=rd.get('candidate_idea')
            if not candidate:continue
            from .storage import digest
            def identifier(idea):return digest({'seed':r['seed_id'],'replicate':r['replicate'],'idea':idea})[:24]
            before=df[(df.run_id==r['run_id']) & df.blind_id.eq(identifier(rd['input_idea']))]
            after=df[(df.run_id==r['run_id']) & df.blind_id.eq(identifier(candidate))]
            guard_decisions.append({'run_id':r['run_id'],'seed_id':r['seed_id'],'configuration':r['configuration'],
                'round':rd['index'],'selection':rd.get('selection','legacy'),'reason':rd.get('selection_reason'),
                **{m+'_candidate_minus_incumbent':float(after.iloc[0][m]-before.iloc[0][m]) if len(before) and len(after) else None for m in METRICS}})
        resources.append({'configuration':r['configuration'],'seed_id':r['seed_id'],'replicate':r['replicate'],
             'seconds_excluding_shared_initial':r['elapsed_seconds'],'calls_excluding_shared_initial':len(events),
             'total_tokens':None if any(e.get('total_tokens') is None for e in events) else sum(e['total_tokens'] for e in events),
             'tokens_missing':sum(e.get('total_tokens') is None for e in events),
             'estimated_cost_usd':None if any(e.get('estimated_cost_usd') is None for e in events) else sum(e['estimated_cost_usd'] for e in events),
             'cost_missing':sum(e.get('estimated_cost_usd') is None for e in events),
             'agent_failures':sum(bool(o['error']) for rd in r['rounds'] for o in rd['reviews'])+sum(bool(o.get('error')) for o in r.get('final_reviews',[])),
             'guard_failures':sum(rd.get('selection')=='check_failed' for rd in r['rounds']),
             'api_failures':sum(e.get('status')=='failed' for e in events),
             'validation_failures':sum(bool(e.get('validation_failure')) for e in events),
             'iterations':len(r['rounds']),'stop_reason':r['stop_reason']})
    write_csv(out/'resources.csv',resources)
    write_csv(out/'revision_decisions.csv',guard_decisions)
    if 'max_rating_range' in df:df[['blind_id','judge_repeats','max_rating_range','judge_error']].drop_duplicates('blind_id').to_csv(out/'judge_variability.csv',index=False)
    if resources:
        resources_df=pd.DataFrame(resources)
        ax=resources_df.groupby('configuration').seconds_excluding_shared_initial.mean().plot.bar(figsize=(8,4));ax.set_ylabel('Mean seconds (excludes shared initial)');ax.set_xlabel('');save('execution_time')
    report_lines = ['# Observed experiment results', '', 'Generated from saved live Gemini runs and independent judgments.', '',
                    f'Independent seeds with final scores: {seed_scores.seed_id.nunique()}. Valid score rows: {len(valid)}; missing/failed rows: {len(df)-len(valid)}.', '',
                    '## Final mean scores by configuration', '', '| Configuration | Seeds | Novelty | Feasibility | Clarity | Importance | Grounding |', '|---|---:|---:|---:|---:|---:|---:|']
    for name in CONFIGURATIONS:
        group=seed_scores[seed_scores.configuration.eq(name)]
        report_lines.append('| '+name+' | '+str(len(group))+' | '+' | '.join(f'{group[m].mean():.2f}' if len(group) else 'unscored' for m in METRICS)+' |')
    report_lines += ['', 'Variation and individual scores are preserved in summary.csv and evaluation/scores.csv. Descriptive paired changes are in paired_comparisons.csv.', '',
                     '## Interpretation limits', '', 'Same-model judge; purposive sample; abstract-only retrieval; unequal natural call budgets. These scores concern proposals and do not establish executed scientific success. Check incomplete runs, failures, and configuration coverage before claiming an efficacy comparison. Different valid seed counts prevent interpreting unmatched group means as treatment effects. Iteration plots show accepted proposals only, with gaps for rejected or missing versions. All candidate decisions and independently judged candidate-minus-incumbent differences are in revision_decisions.csv. Judge repetitions share model biases; median and range do not calibrate correctness. Natural removal ablations change review budgets; replacement controls keep reviewer call counts, not tokens, matched.', '',
                     '## Figures', '']
    for name in ['baseline_comparison','ablation_comparison','iteration_progression','novelty_feasibility','execution_time']:
        if (out/(name+'.png')).exists(): report_lines.append(f'![{name}]({name}.png)')
    (out/'RESULTS.md').write_text('\n'.join(report_lines),encoding='utf-8')
    return {'status':'analyzed','valid_score_rows':len(valid),'failed_score_rows':len(df)-len(valid),
            'n_seeds':int(seed_scores.seed_id.nunique()),'n_final_rows':len(final),
            'limitations':'Same-model judge bias, abstract-only search coverage, natural unequal budgets, purposive seeds, no human calibration yet. Missing judgments excluded and counted; no claim of scientific success.'}
