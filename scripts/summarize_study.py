"""Build a descriptive research report from saved study scores, without API calls."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
study = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'results/smoke_v2'
load = lambda path: json.loads(path.read_text())
status = load(study / 'suite_status.json')
audit = load(study / 'audit/data_quality.json')
with (study / 'evaluation/scores.csv').open() as f:
    rows = list(csv.DictReader(f))
metrics = ['novelty','feasibility','clarity','importance','evidence_grounding']
conditions = ['one_shot','generic','full','no_feasibility','no_contrarian','no_novelty_retrieval']
finals = [r for r in rows if r['is_final'].lower() == 'true']
valid = [r for r in finals if all(r[m] for m in metrics)]
seeds = sorted({r['seed_id'] for r in finals})
if study.name != 'smoke_v2' or len(seeds) != 2:
    raise ValueError('This case discussion describes the corrected two-seed smoke_v2 pilot. Use the general analysis report for other studies.')
means = {c: {m: statistics.mean(float(r[m]) for r in valid if r['configuration'] == c)
             for m in metrics} for c in conditions if any(r['configuration'] == c for r in valid)}
report = [
    '# Research findings: corrected live pilot', '',
    '**Literature-Grounded Research Idea Generation Using Specialized Multi-Agent Reviewers**', '',
    f'Study: `{study.name}`. Status: **{status["status"]}**. Independent seed papers: **{len(seeds)}**.', '',
    '## Research objective and architecture', '',
    'Investigate whether specialist novelty, feasibility, clarity/importance and contrarian reviewing, literature-based overlap checking and bounded refinement change independently judged research-proposal quality. ResearchAgent supplies the main inspiration; criterion-specific reviewing already exists, and InnoEval is close prior work. This is a comparative implementation and extension, without a first-invention claim.', '',
    'The implemented controller retrieves literature, generates a shared original proposal, collects independent reviewer contexts, preserves criticisms and disagreements, revises up to three rounds and records all versions. Baselines and ablations share initial proposals, model settings, constraints and source corpus. The same pretrained Gemini model serves separate roles; there is no training or fine-tuning. The Python state engine ran this pilot; the optional LangGraph adapter remains unverified in this environment.', '',
    '## Dataset and generated ideas', '',
    'The frozen local corpus contains 2,114 records with abstracts from pinned official ACL metadata and attributed prior-work anchors. The fixed evaluation manifest contains twenty purposive AI/NLP ideation/review papers. This pilot uses ResearchAgent and SciMON only; it is narrow and not a representative sample of NLP research.', '',
]
for path in sorted((study / 'initials').glob('*.json')):
    data = load(path)
    report.append(f'- Seed `{data["literature"][0]["paper_id"]}` generated **{data["idea"]["title"]}**.')
report += ['', 'These are proposals under review. Their internal experimental plans have not been executed. Each seed has one initial proposal reused across all six conditions.', '',
    '## Configurations and independent evaluation', '',
    'One-shot generation; generic iterative review; the full four-role panel; removal of feasibility; removal of contrarian review; removal of additional novelty searches. All use Gemini 3.5 Flash-Lite with fixed settings. Natural call budgets differ: a generic reviewer consumes fewer calls than the panel, and removal ablations consume fewer calls. The no-novelty-search condition keeps all four reviewers and original context.', '',
    'An isolated judge request receives only the proposal, constraints and separately retrieved evidence, without reviewer scores, condition or round labels. Five 1–5 metrics have explicit anchors. Identical content shares one judgment. Source passage IDs resolve to exact quotations, validating provenance rather than semantic correctness. The same-model judge remains biased and human calibration is uncollected.', '',
    '## Observed execution', '',
    f'- Saved configurations: {audit["saved_configurations"]}. Accepted final-condition ratings: {len(valid)}/{len(finals)}.',
    f'- Unique judgments: {audit["unique_judgments_accepted"]} accepted / {audit["unique_judgments_attempted"]} attempted. Score rows including shared aliases: {len(rows)}; they are not independent experimental units.',
    f'- Reviewer failures: {len(audit["reviewer_failures"])}; rejected unique judgments: {audit["unique_judgments_failed"]}.',
    f'- Saved API attempts: {audit["all_saved_api_attempts"]}. Recovered request failures: {audit["api_error_counts"]}.',
    f'- Provider-reported tokens: at least {audit["provider_reported_total_tokens_lower_bound"]:,}; {audit["attempts_without_usage_metadata"]} requests have unknown usage. Configured free-tier cost rates are estimates, not billing verification.',
    f'- Wall time: {audit.get("latest_suite_wall_seconds",0)/60:.2f} minutes.', '',
]
for failure in audit['reviewer_failures']:
    report.append(f'Remaining failure: seed `{failure["seed_id"]}`, condition `{failure["configuration"]}`, round {failure["round"]}: {failure["error"]}. Its last valid proposal was retained and independently evaluated. This limits comparisons involving that condition; an accepted score does not imply every review round succeeded.')
report += ['', '## Final mean ratings', '',
    '| Configuration | Seeds scored | Novelty | Feasibility | Clarity | Importance | Grounding |',
    '|---|---:|---:|---:|---:|---:|---:|']
for c in conditions:
    group = [r for r in valid if r['configuration'] == c]
    report.append('| ' + c + ' | ' + str(len(group)) + ' | '
                  + ' | '.join(f'{means[c][m]:.2f}' if group else 'missing' for m in metrics) + ' |')
report += ['', 'Individual scores, paired differences and variability remain in the saved CSV files; these means are descriptive summaries of ordinal ratings.', '',
    '## Baseline comparison', '']
for baseline in ['one_shot','generic']:
    differences = ', '.join(f'{m} {means["full"][m]-means[baseline][m]:+.2f}' for m in metrics)
    report.append(f'Full panel minus {baseline}: {differences}.')
report += ['', 'In this pilot, reviewing shifts judged quality toward practicality, clarity and grounding while judged novelty is lower than the one-shot baseline. The generic condition has no mean advantage over one-shot on these five dimensions and includes one early failure. This does not establish a population effect or prove that every revision is useful.', '',
    '## Ablations', '']
for c in ['no_feasibility','no_contrarian','no_novelty_retrieval']:
    changes = ', '.join(f'{m} {means[c][m]-means["full"][m]:+.2f}' for m in metrics)
    report.append(f'{c} minus full: {changes}.')
report += ['', 'Removing feasibility or contrarian review gives identical aggregate ratings here, so the study cannot distinguish which reviewer contributes most. Additional novelty retrieval does not raise judged novelty in this sample, although full-system grounding is higher. Component effects are conditional on the sampled inputs and inference allocation; fewer reviewers also reduce the call budget.', '',
    '## Full-system iterative refinement', '',
    '| Round | Seeds scored | Novelty | Feasibility | Clarity | Importance | Grounding |',
    '|---|---:|---:|---:|---:|---:|---:|']
for index in range(4):
    group = [r for r in rows if r['configuration'] == 'full' and int(r['round']) == index
             and all(r[m] for m in metrics)]
    report.append('| '+str(index)+' | '+str(len(group))+' | '
                  +' | '.join(f'{statistics.mean(float(r[m]) for r in group):.2f}' if group else 'missing' for m in metrics)+' |')
report += ['', 'Gains are not monotonic. The SciMON-seeded full-system proposal receives feasibility 3→4 and final novelty 4→3. The ResearchAgent-seeded proposal receives clarity 4→5 and grounding 4→5. Additional rounds can plateau or reverse a judged metric. With one same-model judgment per content, judge noise cannot be separated reliably from true proposal changes.', '',
    '## Validity, failure handling and conclusion', '',
    'Two purposive seed papers are the independent units, not twelve condition runs, twenty-six score rows, or the number of agents. No statistical significance claim is justified here. Same-family generation/judging, no human calibration, incomplete prior-art coverage, abstract-only evidence, possible memorization, unequal inference budgets and one generic-review failure all limit interpretation. Proposal-level feasibility is not executed scientific success.', '',
    'The first quotation-transcription pilot remains separately preserved under `results/smoke`. The corrected passage-ID run has no quotation-validation or judge failures. The remaining generic wrong-role failure is preserved; future reviewer schemas now restrict the response to the requested role so mismatches trigger structured-output retries. Existing results were not silently repaired or replaced.', '',
    'The workflow now demonstrates real generation, all four specialized roles, local literature grounding, iterative refinement, baseline/ablation execution and independent scoring. Its preliminary finding is a possible novelty–feasibility trade-off rather than uniform improvement. A larger controlled sample and human validation are needed to assess whether that pattern generalizes.', '',
    f'Figures and numeric tables: `results/{study.name}/analysis/RESULTS.md`. Raw responses, per-round traces, human-rating templates and failure audits are saved alongside them. Notebook execution uses the documented ordinary-Python fallback unless a real Jupyter kernel is separately verified.', '']
output = '\n'.join(report)
(study / 'analysis/RESEARCH_DISCUSSION.md').write_text(output,encoding='utf-8')
target = ROOT / 'docs/RESEARCH_FINDINGS.md'
if target.exists():
    digest = hashlib.sha256(target.read_bytes()).hexdigest()[:12]
    archive = ROOT / 'docs/archive' / f'RESEARCH_FINDINGS_{digest}.md'
    archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists(): shutil.copyfile(target,archive)
target.write_text(output,encoding='utf-8')
print('Updated descriptive findings from actual saved scores:',target)
