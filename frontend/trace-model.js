/* Pure presentation helpers. Scores and text always come from the saved trace. */
(function(root){
  'use strict';
  const metricNames={novelty:'Novelty',feasibility:'Feasibility',clarity:'Clarity',importance:'Importance',evidence_grounding:'Grounding'};
  const roleMetrics={novelty:['novelty'],feasibility:['feasibility'],clarity:['clarity','importance'],contrarian:[],generic:['novelty','feasibility','clarity','importance']};
  const fields={title:'Title',research_problem:'Research problem',research_gap:'Research gap',core_hypothesis:'Core hypothesis',distinctive_mechanism:'Distinctive mechanism',minimum_test:'Minimum decisive test',methodology:'Methodology',expected_contribution:'Expected contribution',experimental_setup:'Experimental setup',evaluation_strategy:'Evaluation strategy',feasibility_assumptions:'Feasibility assumptions',assumption_checks:'Validation plan',prior_work_comparison:'Prior-work comparison',references:'References',search_queries:'Search queries'};
  function score(value){if(value===null||value===undefined||value===''||typeof value==='boolean')return null;const n=Number(value);return Number.isInteger(n*2)&&n>=1&&n<=5?n:null;}
  function judgments(rows=[]){
    const valid=rows.filter(r=>!r.judge_error);
    return {initial:valid.find(r=>Number(r.round)===0)||null,final:valid.filter(r=>r.is_final===true||r.is_final==='True'||r.is_final==='true').sort((a,b)=>Number(b.round)-Number(a.round))[0]||null};
  }
  function changes(rows=[]){const pair=judgments(rows);return Object.keys(metricNames).map(metric=>{const before=score(pair.initial?.[metric]),after=score(pair.final?.[metric]);return {metric,before,after,delta:before!==null&&after!==null?after-before:null};});}
  function formatValue(value){
    if(value===undefined||value===null)return '';
    if(Array.isArray(value))return value.map(v=>typeof v==='object'?Object.entries(v).map(([k,text])=>`${k.replaceAll('_',' ')}: ${text}`).join('\n'):String(v)).join('\n\n');
    return String(value);
  }
  function changedFields(before={},after={}){return Object.keys(fields).map(key=>({key,label:fields[key],before:formatValue(before[key]),after:formatValue(after[key]),changed:JSON.stringify(before[key]??null)!==JSON.stringify(after[key]??null)}));}
  function wordDiff(before,after){
    const a=String(before).match(/\S+/g)||[],b=String(after).match(/\S+/g)||[];
    if(a.length>450||b.length>450)return {before:[{text:String(before),change:before===after?'same':'removed'}],after:[{text:String(after),change:before===after?'same':'added'}]};
    const dp=Array.from({length:a.length+1},()=>new Uint16Array(b.length+1));
    for(let i=a.length-1;i>=0;i--)for(let j=b.length-1;j>=0;j--)dp[i][j]=a[i]===b[j]?1+dp[i+1][j+1]:Math.max(dp[i+1][j],dp[i][j+1]);
    const left=[],right=[];let i=0,j=0;
    while(i<a.length||j<b.length){
      if(i<a.length&&j<b.length&&a[i]===b[j]){left.push({text:a[i++],change:'same'});right.push({text:b[j++],change:'same'});}
      else if(i<a.length&&(j===b.length||dp[i+1][j]>=dp[i][j+1]))left.push({text:a[i++],change:'removed'});
      else right.push({text:b[j++],change:'added'});
    }
    return {before:left,after:right};
  }
  function telemetry(run,job){
    const events=job?.api_events||run.api_events||[];
    return {calls:events.length,tokens:events.reduce((s,e)=>s+(e.total_tokens||0),0),unknown:events.filter(e=>e.total_tokens==null).length,failures:events.filter(e=>e.status!=='ok').length,seconds:job?.elapsed_seconds??run.elapsed_seconds??null};
  }
  function paperIndex(run,job){
    const papers=new Map();const add=ps=>(ps||[]).forEach(p=>papers.set(p.paper_id,p));add(run.literature);
    for(const o of [...(run.rounds||[]).flatMap(r=>r.reviews),...(run.final_reviews||[])])for(const search of o.search||[])add(search.papers);
    for(const detail of job?.evaluation_details||[]){add(detail.literature_context?.papers);for(const search of detail.search||[])add(search.papers);}
    return papers;
  }
  function disagreements(run,rows){
    const final=judgments(rows).final;if(!final)return [];
    return (run.final_reviews||[]).filter(o=>o.review).flatMap(o=>(roleMetrics[o.role]||[]).flatMap(metric=>{
      const reviewer=score(o.review[metric]),judge=score(final[metric]);return reviewer!==null&&judge!==null&&Math.abs(judge-reviewer)>=2?[{role:o.role,metric,reviewer,judge}]:[];
    }));
  }
  function duration(seconds){if(seconds===null||!Number.isFinite(Number(seconds)))return 'Not recorded';const total=Math.round(Number(seconds));return total<60?`${total}s`:`${Math.floor(total/60)}m ${String(total%60).padStart(2,'0')}s`;}
  const api={metricNames,roleMetrics,fields,score,judgments,changes,formatValue,changedFields,wordDiff,telemetry,paperIndex,disagreements,duration};
  root.TraceModel=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
