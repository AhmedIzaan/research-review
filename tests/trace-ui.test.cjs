/* Node tests: pure helpers and a minimal DOM interaction harness, not a browser. */
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const M=require('../frontend/trace-model.js');

test('missing and malformed scores stay unknown rather than becoming zero',()=>{
  for(const value of [null,undefined,'',false,true,0,6,3.25,'bad'])assert.equal(M.score(value),null);
  assert.equal(M.score(3.5),3.5);assert.equal(M.score(3),3);assert.equal(M.score('4'),4);
});
test('independent score changes never substitute reviewer scores',()=>{
  assert.ok(M.changes([]).every(m=>m.delta===null));
  const rows=[{round:0,is_final:false,novelty:3},{round:1,is_final:true,novelty:4}];
  assert.equal(M.changes(rows)[0].delta,1);
  assert.equal(M.changes(rows)[1].delta,null);
  rows[0].judge_error='failed';assert.equal(M.changes(rows)[0].delta,null);
});
test('diff preserves words and highlights additions and deletions',()=>{
  const d=M.wordDiff('Use all layers for confidence','Use selected layers for confidence and abstention');
  assert.equal(d.before.map(x=>x.text).join(' '),'Use all layers for confidence');
  assert.equal(d.after.map(x=>x.text).join(' '),'Use selected layers for confidence and abstention');
  assert.equal(d.before.find(x=>x.text==='all').change,'removed');
  assert.equal(d.after.find(x=>x.text==='selected').change,'added');
  assert.equal(M.wordDiff('same','same').after[0].change,'same');
  assert.equal(M.wordDiff('', 'new').after[0].change,'added');
  assert.equal(M.wordDiff('old','').before[0].change,'removed');
});
test('changed-field comparison uses the actual input to a round',()=>{
  const fields=M.changedFields({methodology:'round two input',references:['p1']},{methodology:'round two output',references:['p1']});
  assert.equal(fields.find(f=>f.key==='methodology').before,'round two input');
  assert.equal(fields.find(f=>f.key==='methodology').changed,true);
  assert.equal(fields.find(f=>f.key==='references').changed,false);
});
test('unknown API usage and failed attempts stay visible',()=>{
  const stats=M.telemetry({}, {api_events:[{status:'ok',total_tokens:10},{status:'failed',total_tokens:null}],elapsed_seconds:183});
  assert.deepEqual(stats,{calls:2,tokens:10,unknown:1,failures:1,seconds:183});
  assert.equal(M.duration(183),'3m 03s');assert.equal(M.duration(null),'Not recorded');
});

class Element {
  constructor(tag,doc){this.tagName=tag.toLowerCase();this.doc=doc;this.children=[];this.dataset={};this.attributes={};this.handlers={};this.className='';this.id='';this.open=false;this.value='';this._text='';this.hidden=false;this.checked=false;this.classList={toggle:(name,on)=>{const names=new Set(this.className.split(' ').filter(Boolean));if(on)names.add(name);else names.delete(name);this.className=[...names].join(' ');}};}
  append(...nodes){for(let n of nodes){if(typeof n==='string')n=new Text(n,this.doc);this.children.push(n);}}
  replaceChildren(...nodes){this.children=[];this._text='';this.append(...nodes);}
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
  setAttribute(key,value){this.attributes[key]=String(value);if(key==='id')this.id=String(value);if(key==='class')this.className=String(value);}
  getAttribute(key){return this.attributes[key]??null;}
  addEventListener(name,fn){(this.handlers[name]??=[]).push(fn);}
  click(){this.emit('click');}
  emit(name,data={}){for(const fn of this.handlers[name]||[])fn({preventDefault(){},...data});}
  focus(){this.doc.activeElement=this;}
  descendants(){return this.children.flatMap(c=>[c,...c.descendants()]);}
  matches(selector){if(selector==='[data-focus]')return Boolean(this.dataset.focus);if(selector==='details[open]')return this.tagName==='details'&&this.open;if(selector.startsWith('.'))return this.className.split(' ').includes(selector.slice(1));return this.tagName===selector;}
  querySelectorAll(selector){if(selector.includes(' ')){const [a,b]=selector.split(' ');return this.descendants().filter(n=>n.matches(a)).flatMap(n=>n.querySelectorAll(b));}return this.descendants().filter(n=>n.matches(selector));}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
}
class Text extends Element{constructor(text,doc){super('#text',doc);this._text=String(text);}}
function dom(){const doc={activeElement:null,createElement(tag){return new Element(tag,this);},createTextNode(text){return new Text(text,this);},getElementById(id){return this.body.descendants().find(n=>n.id===id)||null;}};doc.body=new Element('body',doc);doc.querySelectorAll=selector=>doc.body.querySelectorAll(selector);global.document=doc;const root=doc.createElement('section');root.id='trace';doc.body.append(root);return {doc,root};}
require('../frontend/trace-view.js');
function clickText(root,cls,text){const b=root.querySelectorAll(cls).find(n=>n.textContent.includes(text));assert.ok(b,`Missing control: ${text}`);b.click();}
function loadRealJob(){const file=path.join(__dirname,'../results/web_runs/6d9ed451f6b54a36b21af75090a8a2a8/job.json');return fs.existsSync(file)?JSON.parse(fs.readFileSync(file,'utf8')):null;}

test('real saved trace navigates reviews, changes, final assessment, audit and judgment',{skip:!loadRealJob()},()=>{
  const job=loadRealJob(),{root}=dom();TraceExplorer.render(root,job.result,job);
  assert.ok(root.textContent.includes('What happened in this run?'));
  assert.ok(root.textContent.includes('3 → 4'));
  clickText(root,'.te-stage-button','Review round 1');
  assert.ok(root.textContent.includes('From criticism to revision'));
  assert.equal(root.querySelectorAll('.te-role-tab').length,4);
  clickText(root,'.te-role-tab','Contrarian');
  assert.ok(root.querySelector('.te-review-panel').textContent.includes(job.result.rounds[0].reviews[3].review.falsification_test));
  clickText(root,'.te-mode-button','What changed');
  assert.ok(root.querySelectorAll('ins').length>0);
  clickText(root,'.te-stage-button','Final assessment');
  clickText(root,'.te-role-tab','Novelty');
  assert.ok(root.querySelector('.te-review-panel').textContent.includes('Novelty 2/5'));
  clickText(root,'.te-stage-button','Evidence & sources');
  assert.equal(root.querySelectorAll('.te-audit-card').length,6);
  clickText(root,'.te-filter','Unsupported');
  assert.ok(root.textContent.includes('No claims in this category'));
  clickText(root,'.te-mode-button','Source library');
  const input=root.querySelector('input');input.value='Transform Retrieval';input.emit('input');
  assert.equal(root.querySelectorAll('.te-paper').length,1);
  clickText(root,'.te-stage-button','Independent evaluation');
  assert.ok(root.textContent.includes('Reviewer / judge disagreement'));
  assert.equal(root.querySelectorAll('.te-metric-card').length,5);
  assert.ok(root.textContent.includes('does not record the shared multi-query retrieval protocol'));
});
test('live refresh preserves selected stage, reviewer and open evidence',{skip:!loadRealJob()},()=>{
  const job=loadRealJob(),{root}=dom();TraceExplorer.render(root,job.result,job);
  clickText(root,'.te-stage-button','Final assessment');clickText(root,'.te-role-tab','Contrarian');
  const evidence=root.querySelectorAll('details').find(d=>d.textContent.includes('Evidence behind this review'));evidence.open=true;
  TraceExplorer.render(root,job.result,{...job,status:'running'});
  assert.equal(root.querySelector('.te-review-panel').getAttribute('aria-labelledby'),'te-role-contrarian');
  assert.ok(root.querySelectorAll('details').find(d=>d.dataset.disclosure===evidence.dataset.disclosure).open);
});
test('one-shot / historical run has honest empty assessment states',()=>{
  const files=fs.readdirSync(path.join(__dirname,'../results/smoke_v2/runs')).filter(f=>f.endsWith('.json'));
  const run=files.map(f=>JSON.parse(fs.readFileSync(path.join(__dirname,'../results/smoke_v2/runs',f),'utf8'))).find(r=>r.configuration==='one_shot');
  const {root}=dom();TraceExplorer.render(root,run,null);
  clickText(root,'.te-stage-button','Final assessment');assert.ok(root.textContent.includes('No final assessment recorded'));
  clickText(root,'.te-stage-button','Independent evaluation');assert.ok(root.textContent.includes('No independent scores available'));
});

test('full app bootstrap loads latest saved trace without starting model work',{skip:!loadRealJob()},async()=>{
  const vm=require('node:vm'),job=loadRealJob(),{doc,root}=dom(),html=fs.readFileSync(path.join(__dirname,'../frontend/index.html'),'utf8');
  for(const match of html.matchAll(/<([a-z][a-z0-9-]*)\b([^>]*\bid="([^"]+)"[^>]*)>/g)){
    const [,tag,attrs,id]=match;if(id==='trace')continue;const element=doc.createElement(tag);element.id=id;element.hidden=/\bhidden\b/.test(attrs);element.checked=/\bchecked\b/.test(attrs);doc.body.append(element);
  }
  doc.getElementById('configuration').value='full';doc.getElementById('rounds').value='1';
  const seeds=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/seeds.json'),'utf8'));
  const configs={full:['novelty','feasibility','clarity','contrarian'],generic:['generic'],one_shot:[],no_feasibility:['novelty','clarity','contrarian'],no_contrarian:['novelty','feasibility','clarity'],no_novelty_retrieval:['novelty','feasibility','clarity','contrarian']};
  const responses={
    '/api/config':{model:'fixture-config-only',credential_present:false,corpus_count:2114,constraints:'Fixture config only',configurations:configs,max_attempts:3,max_api_calls:160,active_job:null},
    '/api/seeds':seeds,'/api/studies':[],'/api/runs':[],
    '/api/jobs':[{id:job.id,status:job.status,title:job.initial_idea.title,request:job.request}],
    ['/api/jobs/'+job.id]:job
  },calls=[];
  const context={document:doc,TraceExplorer:global.TraceExplorer,console,location:{hash:'#trace'},window:{addEventListener(){},scrollTo(){}},setTimeout,clearTimeout,URL,Blob,
    fetch:async(url,options)=>{calls.push([url,options]);assert.ok(url in responses,'Unexpected request: '+url);return {ok:true,json:async()=>responses[url]};}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../frontend/app.js'),'utf8'),context);
  await new Promise(resolve=>setTimeout(resolve,25));
  assert.equal(doc.getElementById('notification').hidden,true,doc.getElementById('notification').textContent);
  assert.equal(doc.getElementById('page-trace').hidden,false);
  assert.ok(root.textContent.includes(job.result.final_idea.title));
  assert.equal(doc.getElementById('trace-picker').value,'job:'+job.id);
  assert.ok(calls.every(([,options])=>!options.method));
});

test('untrusted proposal text is rendered as text, not markup',()=>{
  const run=loadRealJob()?.result;if(!run)return;
  const copy=JSON.parse(JSON.stringify(run));copy.run_id='xss-fixture';copy.final_idea.title='<img src=x onerror=alert(1)>';
  const {root}=dom();TraceExplorer.render(root,copy,null);
  assert.ok(root.textContent.includes('<img src=x onerror=alert(1)>'));
  assert.equal(root.querySelectorAll('img').length,0);
});

test('reviewer tabs support arrow-key navigation and focus',{skip:!loadRealJob()},()=>{
  const job=loadRealJob(),{doc,root}=dom();TraceExplorer.render(root,job.result,job);
  clickText(root,'.te-stage-button','Final assessment');clickText(root,'.te-role-tab','Novelty');
  doc.getElementById('te-role-novelty').emit('keydown',{key:'ArrowRight'});
  assert.equal(doc.activeElement.id,'te-role-feasibility');
  assert.equal(doc.getElementById('te-role-feasibility').getAttribute('aria-selected'),'true');
});

test('guarded trace shows rejected candidate without presenting it as the final proposal',{skip:!loadRealJob()},()=>{
  const job=structuredClone(loadRealJob()),run=job.result;run.run_id='synthetic-guard-ui';job.id='synthetic-guard-ui';
  const r=run.rounds[0];r.candidate_idea=r.revised_idea;r.revised_idea=null;r.selection='rejected';
  r.selection_reason='Synthetic novelty regression; incumbent retained';run.final_idea=r.input_idea;
  r.revision_check={mechanism_status:'lost',pivot_reason:'Synthetic lost distinction',explanation:'Synthetic safeguard fixture',novelty:'reduced',feasibility:'improved',clarity:'unchanged',importance:'unchanged',evidence_grounding:'unchanged',unresolved_issues:['Synthetic issue'],uncertainty:'Fixture only'};
  const {root}=dom();TraceExplorer.render(root,run,job);
  clickText(root,'.te-stage-button','Review round 1');
  assert.ok(root.textContent.includes('Revision decision: rejected'));
  assert.ok(root.textContent.includes('Synthetic novelty regression'));
  clickText(root,'.te-mode-button','What changed');
  assert.ok(root.textContent.includes('Rejected candidate'));
  assert.ok(root.querySelectorAll('ins').length>0);
});
test('four generic reviewers have separate keyboard-accessible tabs',{skip:!loadRealJob()},()=>{
  const job=structuredClone(loadRealJob()),run=job.result;run.run_id='synthetic-generic-ui';job.id='synthetic-generic-ui';
  run.rounds[0].reviews=Array.from({length:4},(_,i)=>({role:'generic',reviewer_id:'generic_'+(i+1),review:{role:'generic',novelty:3,feasibility:3,clarity:3,importance:3,explanation:'Synthetic independent critique '+i,problems:['Fixture'],improvements:['Fixture'],evidence:[],tradeoffs:[],uncertainty:'Fixture'}}));
  const {root,doc}=dom();TraceExplorer.render(root,run,job);clickText(root,'.te-stage-button','Review round 1');
  assert.equal(root.querySelectorAll('.te-role-tab').length,4);
  doc.getElementById('te-role-generic_1').emit('keydown',{key:'ArrowRight'});
  assert.equal(doc.activeElement.id,'te-role-generic_2');
  assert.ok(root.querySelector('.te-review-panel').textContent.includes('Synthetic independent critique 1'));
});

test('repeated ratings show medians, ranges and individual rationales',{skip:!loadRealJob()},()=>{
  const job=structuredClone(loadRealJob());job.id='synthetic-repeats-ui';
  for(const d of job.evaluation_details){const j=structuredClone(d.judgment);d.replications=[{repeat:0,judgment:j},{repeat:1,judgment:{...j,novelty:4}}];d.score_summary={novelty:{median:3.5,min:3,max:4}};}
  for(const row of job.evaluation)row.novelty=3.5;
  const {root}=dom();TraceExplorer.render(root,job.result,job);clickText(root,'.te-stage-button','Independent evaluation');
  assert.ok(root.textContent.includes('Rating repetition 1'));
  assert.ok(root.textContent.includes('Rating repetition 2'));
  assert.ok(root.textContent.includes('median 3.5'));
  assert.ok(root.textContent.includes('range 3–4'));
});

test('dependency verdicts and repairs remain visible in final assessment',{skip:!loadRealJob()},()=>{
  const job=structuredClone(loadRealJob());job.id='synthetic-dependencies';
  job.result.final_verification={status:'completed',limitations:'Synthetic source coverage',sources:[{source_id:'s',entity:'FixtureBench',url:'https://example.invalid/card'}],claims:[{claim:'Fixture supports Urdu',verdict:'contradicted',explanation:'Synthetic exhaustive list excludes Urdu',repair:'Use verified language data',verification_method:'structured_language_membership',supporting_excerpt:'Fixture language list',source_ids:['s']}]};
  const {root}=dom();TraceExplorer.render(root,job.result,job);clickText(root,'.te-stage-button','Final assessment');
  assert.ok(root.textContent.includes('Final proposal dependency checks'));
  assert.ok(root.textContent.includes('contradicted'));
  assert.ok(root.textContent.includes('Use verified language data'));
});
