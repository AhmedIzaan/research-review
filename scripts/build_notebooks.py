"""Create demonstration notebooks. No prefilled LLM findings or synthetic examples."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def md(text):return {'cell_type':'markdown','metadata':{},'source':text.splitlines(True)}
def code(text):return {'cell_type':'code','metadata':{},'source':text.splitlines(True),'execution_count':None,'outputs':[]}

SETUP='''from pathlib import Path
import sys, os, json
ROOT = Path.cwd() if (Path.cwd() / 'src' / 'research_review').exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / 'src'))
from research_review.config import Settings, budget
from research_review.schemas import Paper, Run
from research_review.storage import load_json
from research_review.literature_retrieval import create_retriever
from research_review.llm import GeminiClient
from research_review.experiments import run_study
settings = Settings.from_env()
study = ROOT / 'results' / os.getenv('RESEARCH_REVIEW_STUDY', 'smoke_v2')
seeds = [Paper.model_validate(p) for p in load_json(ROOT / 'data' / 'smoke_seeds.json')]
retriever = create_retriever(settings)
RUN_LIVE = os.getenv('RUN_LIVE_EXPERIMENTS') == '1'
print('Model:', settings.model, '| rounds:', settings.rounds)
print('Credentials configured:', bool(os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')))
print('Live execution opt-in:', RUN_LIVE)
print('Fixed smoke seeds:', [(p.paper_id, p.year, p.title) for p in seeds])
'''
LOAD="""runs = [Run.model_validate(load_json(p)) for p in (study / 'runs').glob('*.json') if not p.name.endswith('.partial.json')]
print('Saved live runs:', sum(r.provenance == 'live_gemini' for r in runs))
if not runs:
    print('NOT RUN: No live generated proposals are available. Dataset and software checks are not experimental findings.')
"""

one=[md('''# Baseline experiments
**Literature-Grounded Research Idea Generation Using Specialized Multi-Agent Reviewers**

FAST-NUCES Islamabad. We test whether structured review changes proposal-level judged quality.
ResearchAgent inspires retrieval, critique and refinement; this generic baseline is an approximation,
not a reproduction. ResearchAgent already uses criterion-specific reviewers.

**Execution status:** The notebook reads real paper records and available results. Live experiments
require a locally configured Gemini key and network access. Missing findings remain explicitly absent.
Unit-test fixtures never appear as generated examples.
'''),md('''## Dataset and LLM configuration
Two fixed real papers are used for smoke testing; the separate 20-paper manifest is a purposive
AI/NLP ideation/review sample. It is not a random NLP benchmark. Every condition shares its initial
proposal, literature, constraints and model settings. See `data/seed_provenance.json`.
'''),code(SETUP),code("print(json.dumps(budget(len(seeds), settings.rounds), indent=2))\nprint('Free-tier estimates assume the account is on the free tier; quotas are account-specific.')"),md('''## One-shot and generic iterative review
One-shot returns the shared initial proposal. Generic review uses one general critique and one revision
per round, up to three rounds. Specialist conditions consume more calls; the primary comparison uses
natural budgets and cannot isolate role specialization from extra inference. Repeated independent
replicates and budget-matched controls would strengthen the study.

To execute live cells, set `RUN_LIVE_EXPERIMENTS=1` before launching Jupyter. Default cells only inspect
saved artifacts. The CLI runs all six conditions in randomized order and is preferred for the main study.
'''),code("""if RUN_LIVE:
    client = GeminiClient(settings, study / 'api_audit')
    run_study(seeds, client, retriever, settings, study, configurations=['one_shot', 'generic'])
else:
    print('Live baseline execution disabled; inspecting saved results.')
"""),code(LOAD),code("""for r in runs:
    if r.configuration in ('one_shot', 'generic'):
        print('Condition:', r.configuration, '| seed:', r.seed_id, '| stop:', r.stop_reason)
        print(json.dumps(r.final_idea.model_dump(), indent=2))
        print('Review/revision API attempts excluding shared initial:', len(r.api_events))
"""),md('''## Interpretation
Use independently judged scores from Notebook 3. A polished revision or a high reviewer score does
not establish improvement. If no live artifacts were printed above, baseline effectiveness has not
been measured. Initial proposals, raw API records, and revisions are saved by the reusable runner.
''')]

two=[md('''# Specialized multi-agent review
We test the full panel: novelty, feasibility, clarity/importance, and contrarian review.
The agents share a pretrained model but have different task instructions and structured contracts.
The novelty role searches the downloaded ACL corpus locally using BM25. Online retrieval remains optional.
'''),code(SETUP),md('''## Roles, evidence and independence
The novelty role compares proposed mechanisms with searched prior work. Feasibility checks data,
compute, implementation and time. Clarity/importance checks definitions, coherence and scientific value.
The contrarian challenges assumptions and proposes falsification tests.

Each reviewer receives a separate prompt containing the current proposal and appropriate literature,
without other critiques. Sequential API requests preserve this information independence and reduce
free-tier rate pressure. A deterministic aggregator retains every criticism and score disagreement.
The generator then revises. Stop after at most three rounds, an unchanged proposal, revision failure,
all-reviewer failure, or the request cap. All paper text is treated as untrusted data.
'''),code("""if RUN_LIVE:
    client = GeminiClient(settings, study / 'api_audit')
    run_study(seeds, client, retriever, settings, study, configurations=['full'])
else:
    print('Live specialist execution disabled; inspecting saved results.')
"""),code(LOAD),code("""for r in runs:
    if r.configuration != 'full':
        continue
    print('Seed:', r.seed_id, '| engine:', r.settings['resolved_engine'])
    print('Initial idea:', json.dumps(r.initial_idea.model_dump(), indent=2))
    for rd in r.rounds:
        print('Round', rd.index)
        for outcome in rd.reviews:
            print('Reviewer:', outcome.role, '| evidence status:', outcome.evidence_status)
            print(json.dumps(outcome.model_dump(), indent=2))
        print('Aggregation:', json.dumps(rd.aggregation, indent=2))
        print('Revision:', rd.revised_idea.model_dump() if rd.revised_idea else rd.revision_error)
    print('Final idea:', json.dumps(r.final_idea.model_dump(), indent=2))
    print('Stopping reason:', r.stop_reason)
"""),md('''## Inspecting novelty verification
Search records preserve query, timestamp, provider, cache status, titles, authors, years, URLs and DOIs.
Evidence must cite a supplied ID and match an exact excerpt of the retrieved abstract.
This detects fabricated identifiers and quotations; it does not prove semantic entailment or universal
novelty. If search returns no usable evidence, the grounded novelty review is withheld and its failure
remains visible. The no-retrieval ablation retains seed context but removes additional novelty searches.

**Observed interaction examples:** Only saved live traces above count as actual agent interactions.
If none are present, this demonstration remains blocked on API/network access.
''')]

three=[md('''# Evaluation and ablation
We compare proposal-level novelty, feasibility, clarity, importance and evidence grounding (1–5).
A separately prompted judge sees the idea and separately searched local corpus evidence, without system label,
review scores or refinement history. Same-model judging still risks preference and knowledge bias.
A shuffled, blinded human-rating CSV is generated for later calibration; blank ratings are not evidence.
'''),code(SETUP),md('''## Ablations
Removing feasibility tests the contribution of practical constraint critique. Removing contrarian review
tests adversarial challenge. Removing novelty retrieval retains the novelty persona and seed context
but removes its wider prior-art search. These are removal studies at unequal natural call budgets;
any changes may reflect both content and inference allocation.
'''),code("""if RUN_LIVE:
    client = GeminiClient(settings, study / 'api_audit')
    run_study(seeds, client, retriever, settings, study,
              configurations=['no_feasibility', 'no_contrarian', 'no_novelty_retrieval'])
else:
    print('Live ablations disabled; no synthetic scores substituted.')
"""),code(LOAD),code("""from research_review.evaluation import evaluate_runs
if RUN_LIVE and runs:
    judge = GeminiClient(settings, study / 'judge_api_audit')
    evaluate_runs(runs, judge, retriever, settings, study / 'evaluation')
else:
    print('Independent evaluation not executed in this cell.')
"""),md('''## Analysis and figures
Analyze final proposals across baselines and ablations, then the full panel's initial and rounds 1–3.
Reuse one judgment for identical content. The seed is the independent unit; repeated runs collapse
within seed. Report all five dimension scores, paired changes, ties and missing judgments.
Descriptive statistics remain primary for small samples. Exploratory Wilcoxon tests require at least ten
nonzero paired seed differences; Holm adjustment covers tested comparisons. Ordinal score distances,
symmetry assumptions and purposive sampling limit interpretation. API time/calls/tokens are separate
from judging costs; shared initial generation is recorded once in `initials/`.
'''),code("""from research_review.analysis import analyze
status = analyze(study)
print(json.dumps(status, indent=2))
if status['status'] == 'analyzed':
    import pandas as pd
    print(pd.read_csv(study / 'analysis' / 'summary.csv', header=[0,1]).to_string())
    print(pd.read_csv(study / 'analysis' / 'paired_comparisons.csv').to_string(index=False))
    try:
        from IPython.display import display, Image
    except ImportError:
        print('Rich display requires IPython; actual PNG/PDF figures are saved in', study / 'analysis')
    else:
        for filename in ['baseline_comparison', 'ablation_comparison', 'iteration_progression',
                         'novelty_feasibility', 'execution_time']:
            display(Image(filename=str(study / 'analysis' / (filename + '.png'))))
else:
    print('No empirical comparison, statistical claim or quality figure can yet be reported.')
"""),md('''## Findings and limitations
Answer from observed scores: Did novelty or feasibility improve? Was there a trade-off? Which removal
changed scores most? Did quality plateau or reverse across rounds? Did cited prior work reveal overlap?
If results are absent, these questions remain unanswered.

Limits: narrow purposive seed sample; abstract-only local retrieval; bounded corpus coverage and lexical ranking effects;
same-model judge and generator; no completed human calibration; unequal call budgets; possible model
memorization; proposal-level feasibility is not executed research. Do not generalize a two-seed smoke study
or claim training, statistical superiority, or successful scientific discovery.
''')]

for name,cells in [('01_Baseline_Experiments',one),('02_Multi_Agent_Review',two),('03_Evaluation_and_Ablation',three)]:
    notebook={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'}},'cells':cells}
    for i,cell in enumerate(cells):cell['id']=f'cell-{i:03d}'
    (ROOT/'notebooks'/(name+'.ipynb')).write_text(json.dumps(notebook,indent=1))
print('Created three notebooks without fabricated model results.')
