/* Focused, accessible trace reader. No generated summaries or invented scores. */
(function(root){
  'use strict';
  const M=root.TraceModel;
  const roleNames={novelty:'Novelty',feasibility:'Feasibility',clarity:'Clarity & importance',contrarian:'Contrarian',generic:'General review'};
  const roleDescriptions={novelty:'Originality & prior art',feasibility:'Resources & implementation',clarity:'Definitions & scientific value',contrarian:'Assumptions & failure modes',generic:'General research critique'};
  const roleMarks={novelty:'N',feasibility:'F',clarity:'C',contrarian:'X',generic:'G'};
  const ui={key:null,stage:'overview',roles:{},mode:{},field:null,auditFilter:'all',evidenceTab:'audit',judgeVersion:'final',run:null,job:null,root:null};
  function el(tag,cls='',text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=String(text);return n;}
  function box(cls,...children){const n=el('div',cls);n.append(...children.filter(Boolean));return n;}
  function text(value,cls=''){return el('p',cls,value||'Not recorded.');}
  function action(label,fn,cls='te-button',key){const n=el('button',cls,label);n.type='button';if(key)n.dataset.focus=key;n.addEventListener('click',fn);return n;}
  function badge(label,type='neutral'){return el('span','te-badge te-'+type,label);}
  function detail(key,title,...contents){const n=el('details','te-disclosure');n.dataset.disclosure=key;n.append(el('summary','',title),box('te-disclosure-body',...contents));return n;}
  function sourceLink(label,url){const a=el('a','te-source-link',label);try{const parsed=new URL(url);if(['http:','https:'].includes(parsed.protocol)){a.href=parsed.href;a.target='_blank';a.rel='noopener noreferrer';}}catch{}return a;}
  function heading(kicker,title,description){return box('te-section-heading',el('span','te-kicker',kicker),el('h2','',title),description?text(description,'te-muted'):null);}
  function empty(title,description){return box('te-empty',el('span','te-empty-glyph','○'),el('h3','',title),text(description,'te-muted'));}
  function list(items,cls='te-list'){const ul=el('ul',cls);ul.append(...(items||[]).map(v=>el('li','',v)));return ul;}
  function metricLabel(metric){return M.metricNames[metric]||metric;}
  function number(value){return value===null?'—':Number(value).toFixed(Number.isInteger(Number(value))?0:1);}
  function deltaBadge(value){return value===null?badge('Not assessed'):badge(value===0?'No change':`${value>0?'+':''}${number(value)} point${Math.abs(value)===1?'':'s'}`,value>0?'positive':value<0?'negative':'neutral');}
  function stages(){return [{id:'overview',label:'Overview',hint:'The run at a glance',mark:'◎'},
    {id:'initial',label:'Starting idea',hint:'Preserved original proposal',mark:'01'},
    ...(ui.run.rounds||[]).map(r=>({id:'round-'+r.index,label:'Review round '+r.index,hint:r.selection==='rejected'?'Candidate rejected · incumbent kept':r.revised_idea?'Critiques → revision':'See revision decision',mark:String(r.index+1).padStart(2,'0')})),
    {id:'final',label:'Final assessment',hint:'What still needs work',mark:'✓'},
    {id:'evidence',label:'Evidence & sources',hint:'Claims, excerpts, prior art',mark:'▤'},
    {id:'evaluation',label:'Independent evaluation',hint:'Initial versus revised scores',mark:'↗'},
    {id:'log',label:'Execution details',hint:'Requests, timing & failures',mark:'◷'}];}
  function go(stage){ui.stage=stage;draw();const h=ui.root.querySelector('.te-section-heading h2');if(h){h.tabIndex=-1;h.focus({preventScroll:true});}const announcer=document.getElementById('trace-announcer');if(announcer)announcer.textContent=stages().find(s=>s.id===stage)?.label||stage;}
  function paperCard(paper){
    return box('te-paper',box('te-paper-meta',badge(paper.year||'Year unavailable'),el('span','',paper.paper_id)),
      el('h4','',paper.title),text((paper.authors||[]).slice(0,4).join(', ')+((paper.authors||[]).length>4?' et al.':''),'te-muted'),
      detail('abstract-'+paper.paper_id,'Read abstract',text(paper.abstract||'Abstract unavailable.')),
      box('te-paper-links',sourceLink('Open source ↗',paper.url),paper.doi?sourceLink('DOI ↗','https://doi.org/'+paper.doi.replace(/^https?:\/\/doi.org\//,'')):null));
  }
  function proposal(idea,title){
    if(!idea)return empty('No proposal yet','The generator has not returned a valid proposal.');
    const n=box('te-proposal',el('span','te-kicker',title),el('h3','te-proposal-title',idea.title));
    for(const key of ['research_problem','research_gap','core_hypothesis','distinctive_mechanism','minimum_test','methodology','expected_contribution'])n.append(box('te-proposal-field',el('h4','',M.fields[key]),text(idea[key])));
    n.append(detail('experiment-'+title,'Experimental setup & evaluation',el('h4','','Dataset / experimental setup'),text(idea.experimental_setup),el('h4','','Evaluation strategy'),text(idea.evaluation_strategy),el('h4','','Feasibility assumptions'),list(idea.feasibility_assumptions)));
    const checks=box('te-check-list',text('These are proposed checks. No GPU workload, dataset access, or statistical power calculation has been verified by this workflow.','te-callout'));
    for(const item of idea.assumption_checks||[])checks.append(box('te-check',badge('Untested','warning'),el('h4','',item.assumption),text('Test: '+item.validation_step),text('Accept if: '+item.acceptance_criterion),text('Fallback: '+item.fallback)));
    if(!idea.assumption_checks?.length)checks.append(text('This older proposal has no structured validation plan.','te-muted'));
    n.append(detail('assumptions-'+title,`Assumptions to validate (${idea.assumption_checks?.length||0})`,checks));
    const comparisons=box('te-check-list');for(const c of idea.prior_work_comparison||[]){const paper=ui.papers.get(c.paper_id);comparisons.append(box('te-check',paper?sourceLink(paper.title+' ↗',paper.url):el('strong','',c.paper_id),text('Shared mechanism: '+c.shared_mechanism),text('Proposed difference: '+c.proposed_difference),text('Still to verify: '+c.verification_needed,'te-muted')));}
    if(!idea.prior_work_comparison?.length)comparisons.append(text('No structured comparison was recorded.','te-muted'));
    n.append(detail('comparisons-'+title,`Comparison with prior work (${idea.prior_work_comparison?.length||0})`,comparisons));
    n.append(detail('references-'+title,`References & search queries`,list(idea.references||[]),el('h4','','Prior-art queries'),list(idea.search_queries||[])));
    return n;
  }
  function outcomeStatus(){
    const status=ui.job?.status||ui.run.stop_reason;
    if(['queued','running','cancelling','in progress'].includes(status))return badge(status==='cancelling'?'Stopping after current request':'Run in progress','working');
    if(['failed','interrupted','cancelled','completed_with_failures','all_reviewers_failed','revision_failed','api_budget_exhausted'].includes(status))return badge(status.replaceAll('_',' '),'warning');
    return badge('Execution complete','positive');
  }
  function hero(){
    const stats=M.telemetry(ui.run,ui.job),changes=M.changes(ui.job?.evaluation||[]),novelty=changes.find(m=>m.metric==='novelty');
    const audit=ui.run.evidence_audit, total=audit?.assessments.length||0, supported=audit?.assessments.filter(a=>a.verdict==='supported').length||0;
    const meta=[['Refinement rounds',String((ui.run.rounds||[]).filter(r=>r.revised_idea).length),'Completed revisions'],
      ['Independent novelty',novelty.before!==null&&novelty.after!==null?`${number(novelty.before)} → ${number(novelty.after)}`:'Not attached','Separate rubric · 1–5'],
      ['Citation support',total?`${supported} / ${total}`:'Not audited','Final-review claims · model audit'],
      ['Recorded runtime',M.duration(stats.seconds),`${stats.calls} API attempts${stats.unknown?' · incomplete token usage':''}`]];
    const cards=el('div','te-run-stats');for(const [label,value,note] of meta)cards.append(box('te-stat',el('span','te-stat-label',label),el('strong','',value),el('span','te-stat-note',note)));
    const id=ui.run.run_id||ui.job?.id?.slice(0,20)||'Generating';
    return box('te-hero',box('te-hero-top',box('te-meta',el('span','te-kicker',ui.job?'INTERACTIVE RESEARCH RUN':'SAVED CONTROLLED EXPERIMENT'),el('code','',id)),outcomeStatus()),el('h2','te-run-title',ui.run.final_idea?.title||ui.run.initial_idea?.title||'Generating a research idea…'),text('Workflow completion records execution. It does not establish novelty, feasibility, or scientific success.','te-muted'),cards);
  }
  function summary(){
    const run=ui.run, n=box('',heading('READ THIS FIRST','What happened in this run?','Start with the outcome, then follow each decision in the timeline.'));
    const journey=el('div','te-journey');
    const steps=[['initial','Generated',(run.literature||[]).length+' source papers'],...((run.rounds||[]).length?[[`round-${run.rounds.at(-1).index}`,'Reviewed',run.rounds.length+' round(s)']]:[]),['final','Reassessed',run.final_review_status==='completed'?'Final panel completed':'See assessment status'],['evaluation','Evaluated',ui.job?.evaluation?.length?'Independent scores saved':'No scores attached']];
    steps.forEach(([id,label,note],i)=>{const b=action('',()=>go(id),'te-journey-step','journey-'+id);b.append(el('span','te-step-number',String(i+1).padStart(2,'0')),el('strong','',label),el('small','',note));journey.append(b);});n.append(journey);
    const outcomes=(run.final_reviews||[]).filter(o=>o.review),issues=outcomes.flatMap(o=>(o.review.problems||[]).slice(0,1).map(p=>({role:o.role,problem:p})));
    if(issues.length){const panel=box('te-panel te-open-questions',box('te-panel-top',el('h3','','Questions still open'),badge('Reviewer concerns','warning')));for(const issue of issues)panel.append(box('te-question',el('span',`te-role-dot te-${issue.role}`,roleMarks[issue.role]),box('',el('strong','',roleNames[issue.role]),text(issue.problem))));panel.append(action('Inspect final reviewer feedback →',()=>go('final'),'te-text-button'));n.append(panel);}
    const disagreement=M.disagreements(run,ui.job?.evaluation||[]);for(const d of disagreement)n.append(box('te-callout te-callout-warning',el('strong','','Assessments disagree'),text(`${roleNames[d.role]} reviewer: ${d.reviewer}/5. Independent judge: ${d.judge}/5 for ${metricLabel(d.metric).toLowerCase()}. Compare their reasoning and source coverage before drawing a conclusion.`),action('Compare independent evaluation →',()=>go('evaluation'),'te-text-button')));
    const final=run.final_idea||run.initial_idea;
    n.append(box('te-panel',el('span','te-kicker','THE CURRENT PROPOSAL'),el('h3','',final.title),text(final.research_problem),el('h4','','Proposed approach'),text(final.methodology),detail('overview-full-proposal','Read the complete proposal',proposal(final,'Current proposal'))));
    if(!outcomes.length)n.append(box('te-callout',text('No final reviewer assessment is recorded. Open a review round to inspect what was assessed before refinement.')));
    return n;
  }
  function reviewPanel(outcomes,phase){
    if(!outcomes?.length)return empty('No reviewer feedback recorded','This may be a one-shot baseline, a pending review, or an unavailable assessment.');
    let selected=ui.roles[ui.stage]||(outcomes[0].reviewer_id||outcomes[0].role);if(!outcomes.some(o=>(o.reviewer_id||o.role)===selected))selected=(outcomes[0].reviewer_id||outcomes[0].role);ui.roles[ui.stage]=selected;
    const wrapper=el('div','te-review-reader'),tabs=el('div','te-review-tabs');tabs.dataset.count=outcomes.length;tabs.setAttribute('role','tablist');tabs.setAttribute('aria-label',phase+' reviewers');
    outcomes.forEach((o,index)=>{
      const b=action('',()=>{ui.roles[ui.stage]=(o.reviewer_id||o.role);draw();},'te-role-tab'+(selected===(o.reviewer_id||o.role)?' is-selected':''),'role-'+(o.reviewer_id||o.role));b.id='te-role-'+(o.reviewer_id||o.role);b.setAttribute('role','tab');b.setAttribute('aria-selected',String(selected===(o.reviewer_id||o.role)));b.setAttribute('aria-controls','te-review-panel');b.tabIndex=selected===(o.reviewer_id||o.role)?0:-1;
      const own=(M.roleMetrics[o.role]||[]).map(m=>M.score(o.review?.[m])).filter(v=>v!==null);
      b.append(box('te-role-tab-top',el('span',`te-role-dot te-${o.role}`,roleMarks[o.role]),el('span','te-role-score',o.error?'Failed':own.length?own.length===1?number(own[0])+'/5':own.map(number).join(' · '):o.role==='contrarian'?'Challenge':'Pending')),el('strong','',roleNames[o.role]),el('small','',own.length>1?(M.roleMetrics[o.role]||[]).map(metricLabel).join(' · ')+' (1–5)':roleDescriptions[o.role]));
      b.addEventListener('keydown',event=>{let next;if(event.key==='ArrowRight')next=(index+1)%outcomes.length;if(event.key==='ArrowLeft')next=(index-1+outcomes.length)%outcomes.length;if(event.key==='Home')next=0;if(event.key==='End')next=outcomes.length-1;if(next!==undefined){event.preventDefault();ui.roles[ui.stage]=(outcomes[next].reviewer_id||outcomes[next].role);draw();document.getElementById('te-role-'+(outcomes[next].reviewer_id||outcomes[next].role))?.focus();}});tabs.append(b);
    });
    wrapper.append(tabs);const o=outcomes.find(o=>(o.reviewer_id||o.role)===selected),review=o.review;
    const panel=box('te-review-panel');panel.id='te-review-panel';panel.setAttribute('role','tabpanel');panel.setAttribute('aria-labelledby','te-role-'+selected);
    if(!review){panel.append(empty('This review did not complete',o.error||'Waiting for reviewer feedback.'));wrapper.append(panel);return wrapper;}
    const scores=box('te-inline-scores');for(const metric of M.roleMetrics[o.role]||[])scores.append(badge(`${metricLabel(metric)} ${number(M.score(review[metric]))}/5`));
    panel.append(box('te-panel-top',box('',el('span','te-kicker',phase+' · REVIEWER OPINION'),el('h3','',roleNames[o.role]+' review')),scores),text(review.explanation,'te-review-explanation'));
    panel.append(box('te-feedback-columns',box('te-feedback-block',el('h4','','What needs attention'),list(review.problems,'te-criticism-list')),box('te-feedback-block te-recommendations',el('h4','','Recommended changes'),list(review.improvements,'te-recommendation-list'))));
    if(review.falsification_test)panel.append(box('te-falsification',el('span','te-kicker','HOW THIS IDEA COULD FAIL'),text(review.falsification_test)));
    if(review.tradeoffs?.length)panel.append(detail('tradeoffs-'+phase+o.role,'Trade-offs to preserve',list(review.tradeoffs)));
    const citations=box('te-citation-list');for(const e of review.evidence||[]){const p=ui.papers.get(e.paper_id);citations.append(box('te-citation',badge(e.relation),el('h4','',e.claim),el('blockquote','',e.supporting_excerpt),p?sourceLink(p.title+' ↗',p.url):el('span','te-muted',e.paper_id)));}
    panel.append(detail('citations-'+phase+o.role,`Evidence behind this review (${review.evidence?.length||0} citations)`,text('Exact excerpts establish traceability. Claim support is assessed separately in Evidence & sources.','te-muted'),review.evidence?.length?citations:text('No excerpts were cited in this review.','te-muted')));
    if(o.search?.length){const searches=box('');for(const s of o.search)searches.append(box('te-search-record',el('h4','',s.query),badge(`${s.status} · ${s.papers.length} results`),...s.papers.map(p=>box('',sourceLink(p.title+' ↗',p.url)))));panel.append(detail('queries-'+phase+o.role,`Prior-art search queries (${o.search.length})`,searches));}
    panel.append(box('te-uncertainty',el('strong','','Uncertainty'),text(review.uncertainty)));wrapper.append(panel);return wrapper;
  }
  function aggregation(record,key){
    const a=record||{},n=box('te-panel',el('h3','','How feedback was carried forward'),text('The revision step received independent critiques together. Listed tensions remain part of the trace; their presence does not mean they were resolved.','te-muted'));
    if(a.qualitative_tradeoffs?.length)for(const t of a.qualitative_tradeoffs)n.append(box('te-tradeoff-row',badge(roleNames[t.role]||t.role),text(t.tension)));
    else n.append(text('No structured trade-off entries were recorded. Full feedback is retained in the exported trace.','te-muted'));
    for(const f of a.failures||[])n.append(box('te-callout te-callout-warning',text(`${roleNames[f.role]}: ${f.error}`)));
    const raw=el('pre','te-raw');raw.textContent=JSON.stringify(a,null,2);n.append(detail('raw-'+key,'Technical aggregation record (JSON)',raw));return n;
  }
  function diffView(round){
    const candidate=round.candidate_idea||round.revised_idea;
    if(!candidate)return empty('No revision was produced',round.revision_error||'Review feedback is available; revision is pending or did not complete.');
    const fields=M.changedFields(round.input_idea,candidate),changed=fields.filter(f=>f.changed),field=fields.find(f=>f.key===ui.field)||changed.find(f=>f.key==='methodology')||changed[0]||fields[0];ui.field=field.key;
    const n=box('',box('te-callout',el('strong','',`${changed.length} of ${fields.length} proposal fields changed`),text('Green highlights show added words; red highlights show removed words. Text changes alone do not establish an improvement.')));
    const layout=box('te-diff-layout'),nav=el('div','te-field-picker');nav.setAttribute('role','group');nav.setAttribute('aria-label','Compare proposal fields');for(const f of fields){const b=action('',()=>{ui.field=f.key;draw();},'te-field-button'+(f.key===field.key?' is-selected':''),'field-'+f.key);b.append(el('span','',f.label),el('small',f.changed?'te-changed-dot':'',f.changed?'Changed':'Same'));b.setAttribute('aria-pressed',String(f.key===field.key));nav.append(b);}
    const diff=M.wordDiff(field.before,field.after),panels=box('te-diff-panels');
    for(const [side,label] of [['before','Before round '+round.index],['after',(round.selection==='rejected'?'Rejected candidate · round ':'Candidate · round ')+round.index]]){const content=el('p','te-diff-text');for(const [i,segment] of diff[side].entries()){if(i)content.append(document.createTextNode(' '));content.append(el(segment.change==='added'?'ins':segment.change==='removed'?'del':'span','',segment.text));}if(!diff[side].length)content.append(el('span','te-muted','Not recorded.'));panels.append(box('te-diff-side te-diff-'+side,box('te-diff-heading',el('span','te-kicker',label),el('h3','',field.label)),content));}
    layout.append(nav,panels);n.append(layout);return n;
  }
  function roundView(round){
    const n=box('',heading('REFINEMENT / ROUND '+round.index,'From criticism to revision','The reviewers assessed the proposal entering this round. Use Changes to inspect the exact revision.'));
    if(round.selection&&round.selection!=='legacy')n.append(box('te-callout'+(round.selection==='accepted'?'':' te-callout-warning'),el('strong','','Revision decision: '+round.selection.replaceAll('_',' ')),text(round.selection_reason)));
    if(round.revision_changes?.changed_fields)n.append(box('te-callout',el('strong','','Recorded proposal edits'),text(round.revision_changes.changed_fields.join(', ')||'No fields changed.'),text(round.revision_changes.literature_only?'Literature-only update; experimental design unchanged.':round.revision_changes.limitation)));
    if(round.revision_check?.comparative_risks?.length){const risks=box('te-panel',el('h3','','Criticism and repair assessment'));for(const risk of round.revision_check.comparative_risks)risks.append(box('te-feedback-block',badge(risk.change),el('h4','',risk.issue),text('Before: '+risk.incumbent_state),text('Candidate: '+risk.candidate_state),text(risk.reasoning),text('Next check: '+risk.next_check)));risks.append(text('These are safeguard judgments; inspect the recorded edits to verify the claimed repair.','te-muted'));n.append(risks);}
    if(round.revision_check){const check=round.revision_check,panel=box('te-panel',el('h3','','Revision safeguard · refinement feedback'),text(check.explanation),text('Mechanism: '+check.mechanism_status+' · '+check.pivot_reason));for(const metric of Object.keys(M.metricNames))panel.append(badge(metricLabel(metric)+': '+check[metric]));panel.append(el('h4','','Unresolved issues'),list(check.unresolved_issues),text(check.uncertainty,'te-muted'));n.append(panel);}
    const mode=ui.mode[ui.stage]||'reviews',switcher=box('te-mode-switch');switcher.setAttribute('role','group');switcher.setAttribute('aria-label','Round view');for(const [id,label] of [['reviews','Reviewer feedback'],['changes','What changed']]){const b=action(label,()=>{ui.mode[ui.stage]=id;draw();},'te-mode-button'+(mode===id?' is-selected':''),'mode-'+id);b.setAttribute('aria-pressed',String(mode===id));switcher.append(b);}n.append(switcher);
    if(mode==='changes')n.append(diffView(round));else n.append(reviewPanel(round.reviews,'Round '+round.index),detail('round-input-'+round.index,'Read the exact proposal these reviewers assessed',proposal(round.input_idea,'Input to round '+round.index)),aggregation(round.aggregation,'round-'+round.index));
    if(round.input_verification)n.append(detail('input-facts-'+round.index,'Input dependency checks',verificationPanel(round.input_verification,'Entering proposal')));
    if(round.candidate_verification)n.append(verificationPanel(round.candidate_verification,'Candidate dependency checks'));
    if(round.revision_error)n.append(box('te-callout te-callout-warning',text('Revision failed: '+round.revision_error)));
    return n;
  }
  function verificationPanel(report,label){
    const n=box('te-panel',el('h3','',label));
    if(!report){n.append(text('Dependency verification was not recorded.'));return n;}
    n.append(text(report.limitations,'te-muted'));
    for(const lookup of report.online_lookups||[])n.append(box('te-callout',el('strong','',lookup.entity+' · online lookup: '+lookup.status),text((lookup.cache_hit?'Pinned cache. ':'')+(lookup.errors||[]).join(' ')),text('Repository candidates: '+(lookup.candidates||[]).join(', '))));
    if(report.error)n.append(box('te-callout te-callout-warning',text(report.error)));
    for(const issue of report.experiment_checks||[])n.append(box('te-callout te-callout-warning',el('strong','',issue.code.replaceAll('_',' ')),text(issue.explanation),text('Required next step: '+issue.repair)));
    for(const c of report.claims||[]){const card=box('te-feedback-block',badge(c.verdict.replaceAll('_',' ')),el('h4','',c.claim),text(c.explanation),text('Next step: '+c.repair),text('Method: '+c.verification_method,'te-muted'));
      if(c.supporting_excerpt)card.append(el('blockquote','',c.supporting_excerpt));
      for(const id of c.source_ids||[]){const source=(report.sources||[]).find(s=>s.source_id===id);if(source)card.append(sourceLink(source.entity+' ↗',source.url));}
      n.append(card);
    }return n;
  }
  function finalView(){
    const r=ui.run,n=box('',heading('AFTER REFINEMENT','What does the final panel think?','These are specialist opinions about the final proposal. The independent judge is shown separately.'));
    if(r.final_verification)n.append(verificationPanel(r.final_verification,'Final proposal dependency checks'));
    const status=r.final_review_status||'not_requested';
    if(!r.final_reviews?.length){const active=['queued','running','cancelling'].includes(ui.job?.status);return box('',n,empty(status==='pending'&&active?'Final assessment is pending':'No final assessment recorded',status==='skipped'?'This configuration skipped the final panel.':'The last revision has not been assessed by a final panel in this trace.'));}
    if(status!=='completed')n.append(box('te-callout te-callout-warning',text('Final assessment status: '+status+'. Some dimensions may remain unassessed.')));
    n.append(reviewPanel(r.final_reviews,'Final assessment'),detail('final-proposal','Read the final proposal assessed by this panel',proposal(r.final_idea,'Final proposal')),aggregation(r.final_aggregation,'final'));return n;
  }
  function sourcesView(){
    const n=box('te-panel');const input=el('input','te-source-search');input.type='search';input.dataset.focus='source-filter';input.placeholder='Filter sources by title, author, or paper ID…';input.setAttribute('aria-label','Filter trace source papers');input.value=ui.sourceFilter||'';const results=el('div','te-source-results');
    function filter(){ui.sourceFilter=input.value;const q=input.value.toLowerCase().trim(),papers=[...ui.papers.values()].filter(p=>`${p.paper_id} ${p.title} ${(p.authors||[]).join(' ')}`.toLowerCase().includes(q));results.replaceChildren(text(`${papers.length} source records · abstracts, not full PDFs`,'te-muted'),...papers.map(paperCard));}
    input.addEventListener('input',filter);n.append(input,results);filter();return n;
  }
  function evidenceView(){
    const r=ui.run,n=box('',heading('FOLLOW THE SOURCE','Evidence, with a visible paper trail','Source matching and semantic support are different checks. Neither establishes global novelty.'));
    const tabs=box('te-mode-switch');for(const [id,label] of [['audit','Citation-support audit'],['sources','Source library']]){const b=action(label,()=>{ui.evidenceTab=id;draw();},'te-mode-button'+(ui.evidenceTab===id?' is-selected':''),'evidence-'+id);b.setAttribute('aria-pressed',String(ui.evidenceTab===id));tabs.append(b);}n.append(tabs);
    if(ui.evidenceTab==='sources'){n.append(sourcesView());return n;}
    if(!r.evidence_audit){n.append(empty('No support audit recorded',r.evidence_audit_error||'This check was disabled, is pending, or was not part of this older run. Review citations remain available in each reviewer panel.'));return n;}
    const assessments=r.evidence_audit.assessments,counts=box('te-audit-counts');for(const [verdict,label] of [['supported','Supported'],['partial','Partially supported'],['unsupported','Unsupported']])counts.append(box('te-audit-count te-audit-'+verdict,el('strong','',assessments.filter(a=>a.verdict===verdict).length),el('span','',label)));n.append(counts,text('Scope: unique claims cited by the final reviewers. These are model judgments about claim–excerpt support.','te-muted'));
    const filters=box('te-filter-row');for(const value of ['all','supported','partial','unsupported']){const b=action(value==='all'?'All claims':value==='partial'?'Partial support':value[0].toUpperCase()+value.slice(1),()=>{ui.auditFilter=value;draw();},'te-filter'+(ui.auditFilter===value?' is-selected':''),'audit-'+value);b.setAttribute('aria-pressed',String(ui.auditFilter===value));filters.append(b);}n.append(filters);
    const shown=assessments.filter(a=>ui.auditFilter==='all'||a.verdict===ui.auditFilter);for(const a of shown){const citation=r.evidence_audit_citations?.[a.citation_id],paper=citation&&ui.papers.get(citation.paper_id);n.append(box('te-audit-card te-audit-'+a.verdict,box('te-panel-top',badge(a.verdict==='partial'?'Partial support':a.verdict,'support-'+a.verdict),el('span','te-muted',citation?.paper_id||a.citation_id)),el('h3','',citation?.claim||'Citation assessment'),text(a.explanation),citation?detail('audit-'+a.citation_id,'Read the exact source excerpt',el('blockquote','',citation.supporting_excerpt),paper?sourceLink(paper.title+' ↗',paper.url):null):null));}
    if(!shown.length)n.append(empty('No claims in this category','Try another audit filter.'));n.append(box('te-callout',text(r.evidence_audit.limitations)));return n;
  }
  function scoreBar(label,value,variant){const track=el('span','te-score-track');track.setAttribute('aria-hidden','true');const fill=el('span','te-score-fill '+variant);fill.dataset.score=value??0;track.append(fill);return box('te-bar-row',el('span','',label),track,el('strong','',value===null?'—':number(value)+'/5'));}
  function evaluationView(){
    const job=ui.job,rows=job?.evaluation||[],n=box('',heading('SEPARATE RUBRIC / 1–5','Did the idea improve?','The judge receives proposals and source literature, with reviewer feedback and condition labels withheld. Same-model bias remains possible.'));
    if(job?.evaluation_error)n.append(box('te-callout te-callout-warning',text(job.evaluation_error)));
    if(!rows.length){n.append(empty('No independent scores available','Evaluation may be disabled, pending, or stored separately from this trace. Reviewer scores are not substituted here.'));return n;}
    const cards=box('te-metric-grid');for(const c of M.changes(rows))cards.append(box('te-metric-card',box('te-panel-top',el('h3','',metricLabel(c.metric)),deltaBadge(c.delta)),scoreBar('Initial',c.before,'te-bar-initial'),scoreBar('Revised',c.after,'te-bar-final')));n.append(cards,text('Single-proposal score differences are descriptive, not statistical evidence of general improvement.','te-muted'));
    for(const row of rows.filter(r=>r.judge_error))n.append(box('te-callout te-callout-warning',text(`Round ${row.round}: ${row.judge_error}`)));
    const disagreement=M.disagreements(ui.run,rows);for(const d of disagreement)n.append(box('te-callout te-callout-warning',el('strong','','Reviewer / judge disagreement'),text(`${metricLabel(d.metric)}: final ${roleNames[d.role].toLowerCase()} reviewer ${d.reviewer}/5; independent judge ${d.judge}/5. Inspect their evidence before interpreting this difference.`)));
    const pair=M.judgments(rows),switcher=box('te-mode-switch');for(const [id,label] of [['initial','Initial idea rationale'],['final','Revised idea rationale']]){const b=action(label,()=>{ui.judgeVersion=id;draw();},'te-mode-button'+(ui.judgeVersion===id?' is-selected':''),'judge-'+id);b.setAttribute('aria-pressed',String(ui.judgeVersion===id));switcher.append(b);}n.append(switcher);
    const row=pair[ui.judgeVersion],d=job.evaluation_details?.find(d=>d.blind_id===row?.blind_id);
    if(!d?.judgment&&!d?.replications?.length){n.append(empty('Detailed rationale unavailable','Individual scores remain shown above.'));return n;}
    const context=d.literature_context,panel=box('te-panel',el('span','te-kicker',ui.judgeVersion==='initial'?'INITIAL IDEA':'REVISED IDEA'),el('h3','','Why the judge gave these scores'));
    if(d.replications?.length)panel.append(text('Available aggregate scores above are medians of '+d.replications.length+' planned independent rating calls. Individual rationales and score ranges follow; repetitions do not remove shared model bias.','te-muted'));
    for(const rep of d.replications||[]){const block=box('te-panel',el('h4','','Rating repetition '+(rep.repeat+1)));if(rep.judgment){for(const metric of Object.keys(M.metricNames))block.append(detail('repeat-'+ui.judgeVersion+rep.repeat+metric,metricLabel(metric)+' · '+rep.judgment[metric]+'/5',text(rep.judgment.rationale[metric])));block.append(text(rep.judgment.uncertainty,'te-muted'));}else block.append(text(rep.error));panel.append(block);}
    if(d.score_summary)for(const metric of Object.keys(M.metricNames)){const v=d.score_summary[metric];if(v)panel.append(badge(metricLabel(metric)+': median '+v.median+' · range '+v.min+'–'+v.max));}
    if(!d.replications?.length&&d.judgment)for(const metric of Object.keys(M.metricNames))panel.append(detail('rationale-'+ui.judgeVersion+metric,`${metricLabel(metric)} · ${number(M.score(d.judgment[metric]))}/5`,text(d.judgment.rationale[metric])));
    if(d.judgment)panel.append(box('te-uncertainty',el('strong','','Judge uncertainty'),text(d.judgment.uncertainty)));
    if(d.error)panel.append(box('te-callout te-callout-warning',text(d.error)));
    if(context){const coverage=context.coverage;panel.append(box('te-coverage',badge(`${coverage.query_count} queries`),badge(`${coverage.paper_count} papers`),badge('Evidence cap '+coverage.paper_limit)));const allContexts=(job.evaluation_details||[]).map(d=>d.literature_context?.fingerprint);panel.append(text(allContexts.length>1&&allContexts.every(x=>x&&x===allContexts[0])?'Matched versions were judged using the same selected evidence set.':'A shared evidence set across versions is not confirmed by this trace.','te-muted'));const missing=[...(coverage.missing_cited_ids||[]),...(coverage.omitted_cited_ids||[])];if(missing.length||coverage.search_failures)panel.append(box('te-callout te-callout-warning',text(`Missing or excluded cited papers: ${missing.join(', ')||'none'}. Failed searches: ${coverage.search_failures}.`)));panel.append(detail('judge-sources-'+ui.judgeVersion,'Inspect judge search queries & source papers',list(context.queries),...(context.papers||[]).map(paperCard)));}
    else {panel.append(box('te-callout te-callout-warning',text('This older judgment does not record the shared multi-query retrieval protocol. Its evidence may differ from the novelty reviewer’s.')));const oldSources=(d.search||[]).flatMap(s=>s.papers);panel.append(detail('legacy-judge-sources-'+ui.judgeVersion,'Inspect the original judge sources',...oldSources.map(paperCard)));}
    n.append(panel);return n;
  }
  function logView(){
    const r=ui.run,j=ui.job,stats=M.telemetry(r,j),n=box('',heading('EXECUTION / NOT IDEA QUALITY','What ran, and what failed?','Every request is recorded. A successful API call does not verify the proposed scientific experiment.'));
    n.append(box('te-log-stats',box('te-stat',el('span','te-stat-label','API attempts'),el('strong','',stats.calls)),box('te-stat',el('span','te-stat-label','Reported tokens'),el('strong','',stats.tokens.toLocaleString()),text(stats.unknown?`${stats.unknown} attempts have unknown usage`:'All recorded attempts have token usage','te-muted')),box('te-stat',el('span','te-stat-label','API failures'),el('strong','',stats.failures))));
    const events=j?.events||[],timeline=el('ol','te-event-timeline');for(const e of events){let label=e.type.replaceAll('_',' ');if(e.payload?.role)label+=' · '+roleNames[e.payload.role];if(e.payload?.round)label+=' · round '+e.payload.round;if(e.payload?.label)label+=' · '+e.payload.label;timeline.append(el('li','',`${e.at?.slice(11,19)||''} UTC · ${label}`));}if(events.length)n.append(box('te-panel',el('h3','','Execution timeline'),timeline));
    const raw=el('pre','te-raw');raw.textContent=JSON.stringify({settings:r.settings,stop_reason:r.stop_reason,api_events:j?.api_events||r.api_events},null,2);n.append(detail('execution-json','Technical request metadata (JSON)',raw));if(!j)n.append(text('Controlled-run timing and request records may exclude shared initial generation.','te-muted'));return n;
  }
  function draw(){
    const focus=document.activeElement?.dataset?.focus,open=new Set([...ui.root.querySelectorAll('details[open]')].map(d=>d.dataset.disclosure));
    if(!stages().some(s=>s.id===ui.stage))ui.stage='overview';
    const rail=el('nav','te-timeline');rail.setAttribute('aria-label','Trace stages');rail.append(el('span','te-timeline-title','FOLLOW THE PROCESS'));
    for(const stage of stages()){const b=action('',()=>go(stage.id),'te-stage-button'+(ui.stage===stage.id?' is-active':''),'stage-'+stage.id);b.append(el('span','te-stage-mark',stage.mark),box('te-stage-label',el('strong','',stage.label),el('small','',stage.hint)));if(ui.stage===stage.id)b.setAttribute('aria-current','step');rail.append(b);}
    const pane=el('div','te-content');
    if(ui.stage==='overview')pane.append(summary());
    else if(ui.stage==='initial')pane.append(heading('BEFORE ANY CRITIQUE','The starting idea','This original proposal is preserved so you can compare it with every revision.'),box('te-panel',proposal(ui.run.initial_idea,'Initial generation')));
    else if(ui.stage.startsWith('round-'))pane.append(roundView(ui.run.rounds.find(r=>'round-'+r.index===ui.stage)));
    else if(ui.stage==='final')pane.append(finalView());else if(ui.stage==='evidence')pane.append(evidenceView());else if(ui.stage==='evaluation')pane.append(evaluationView());else pane.append(logView());
    const order=stages(),index=order.findIndex(s=>s.id===ui.stage),next=order[index+1];if(next)pane.append(box('te-next',text('Continue through the trace','te-muted'),action(next.label+' →',()=>go(next.id),'te-button te-button-dark','next-stage')));
    ui.root.replaceChildren(hero(),box('te-reader-layout',rail,pane));
    for(const d of ui.root.querySelectorAll('details'))if(open.has(d.dataset.disclosure))d.open=true;
    if(focus){const active=[...ui.root.querySelectorAll('[data-focus]')].find(n=>n.dataset.focus===focus);active?.focus({preventScroll:true});}
  }
  root.TraceExplorer={render(element,run,job){const key=job?.id||run.run_id||'pending';if(ui.key!==key){ui.key=key;ui.stage='overview';ui.roles={};ui.mode={};ui.field=null;ui.sourceFilter='';ui.auditFilter='all';ui.evidenceTab='audit';}ui.root=element;ui.run=run;ui.job=job;ui.papers=M.paperIndex(run,job);draw();}};
})(globalThis);
