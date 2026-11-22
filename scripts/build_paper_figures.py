#!/usr/bin/env python3
"""Paper figures from real saved scores, plus a schematic of the implemented loop."""
from pathlib import Path
import os,json,csv
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR','/tmp/research-paper-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT=ROOT/'paper/figures';OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7,'axes.titlesize':8,
 'axes.labelsize':7,'xtick.labelsize':6.5,'ytick.labelsize':6.5,'legend.fontsize':6.3,
 'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})

def save(fig,name):
 fig.savefig(OUT/(name+'.png'),dpi=300,bbox_inches='tight',facecolor='white')
 fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight',facecolor='white')
 plt.close(fig)

fig,ax=plt.subplots(figsize=(3.5,2.8));ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
def block(x,y,w,h,label,color='#f0f3f0'):
 ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=0.009,rounding_size=0.015',
  linewidth=.7,edgecolor='#495d53',facecolor=color))
 ax.text(x,y,label,ha='center',va='center',fontsize=6.6)
def arrow(a,b,**kwargs):ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','lw':.7,'color':'#58675f',**kwargs})
block(.5,.93,.64,.09,'Seed paper + retrieved literature')
block(.5,.77,.62,.09,'Structured initial proposal');arrow((.5,.885),(.5,.82))
for x,label,color in zip([.14,.38,.62,.86],['Novelty\n+ search','Feasibility','Clarity /\nimportance','Contrarian'],['#e6eef4','#e8eee0','#f4eedf','#f2e6e0']):
 block(x,.56,.205,.13,label,color);arrow((.5,.72),(x,.635));arrow((x,.488),(.5,.39))
block(.5,.335,.65,.095,'Preserve critiques and disagreements')
block(.5,.17,.6,.09,'Revise / bounded stopping');arrow((.5,.285),(.5,.22))
arrow((.2,.17),(.09,.56),connectionstyle='arc3,rad=-.5')
ax.text(.02,.32,'≤3\nrounds',fontsize=6.4,ha='center')
block(.5,.055,.87,.075,'Separate judge: proposal + independently retrieved evidence','#f7f7f7')
arrow((.5,.122),(.5,.1025))
fig.tight_layout(pad=.1);save(fig,'architecture')
with (ROOT/'paper/results/final_individual_scores.csv').open() as f:rows=list(csv.DictReader(f))
seeds=['2025.naacl-long.342','2024.acl-long.18'];names=['ResearchAgent seed','SciMON seed'];colors=['#2e6086','#af6339'];markers=['o','s']
fig,axes=plt.subplots(1,2,figsize=(3.5,2.05))
for ax,metric,title in zip(axes,['novelty','feasibility'],['Novelty','Feasibility']):
 for seed,name,color,marker in zip(seeds,names,colors,markers):
  values=[int(next(r for r in rows if r['seed_id']==seed and r['configuration']==c)[metric]) for c in ['one_shot','generic','full']]
  # The larger open circle stays visible around the square when scores coincide.
  ax.plot(range(3),values,marker=marker,color=color,lw=1,ms=6 if marker=='o' else 3.2,
          label=name,fillstyle='none' if marker=='o' else 'full')
 ax.set_title(title);ax.set_xticks(range(3),['One-shot','Generic\nreview','Our system\n(full panel)']);ax.set_ylim(.8,5.25);ax.set_yticks([1,2,3,4,5]);ax.grid(axis='y',color='#e8e8e8',lw=.5)
axes[0].set_ylabel('Independent judge score')
handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False,bbox_to_anchor=(.5,-.01))
fig.tight_layout(rect=(0,.13,1,1),pad=.5,w_pad=1.1);save(fig,'baseline_pairs')
with (ROOT/'results/smoke_v2/analysis/iteration_scores.csv').open() as f:progress=list(csv.DictReader(f))
fig,axes=plt.subplots(2,2,figsize=(3.5,2.7),sharex=True,sharey=True)
for ax,metric,title in zip(axes.flat,['novelty','feasibility','clarity','evidence_grounding'],['Novelty','Feasibility','Clarity','Grounding']):
 for seed,name,color,marker in zip(seeds,names,colors,markers):
  rs=sorted([r for r in progress if r['seed_id']==seed],key=lambda r:int(r['round']))
  ax.plot([int(r['round']) for r in rs],[float(r[metric]) for r in rs],color=color,marker=marker,ms=3.5,lw=.9,label=name,fillstyle='none' if marker=='o' else 'full')
 ax.set_title(title);ax.set_ylim(.8,5.3);ax.set_yticks([1,3,5]);ax.set_xticks([0,1,2,3]);ax.grid(axis='y',lw=.5,color='#e8e8e8')
for ax in axes[1]:ax.set_xlabel('Revision round (0 = initial)')
handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False,bbox_to_anchor=(.5,-.01))
fig.tight_layout(rect=(0,.08,1,1),pad=.5,h_pad=.7,w_pad=.8);save(fig,'iteration_pairs')
print('Wrote three figures in PNG and vector PDF formats.')
