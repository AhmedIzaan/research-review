"""Summarize actual saved pilot artifacts; preserve the previous report version."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
study = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'results/smoke'
load = lambda path: json.loads(path.read_text())
runs = [load(p) for p in (study / 'runs').glob('*.json') if not p.name.endswith('.partial.json')]
audit = load(study / 'audit/data_quality.json')
status = load(study / 'suite_status.json')
if len({r['seed_id'] for r in runs}) != 2 or load(study / 'manifest.json')['specification']['protocol_version'] != '2':
    raise ValueError('This diagnostic report describes the two-seed legacy-quotation pilot only. Use the new study analysis report for other protocols.')
with (study / 'evaluation/scores.csv').open() as f:
    rows = list(csv.DictReader(f))
metrics = ['novelty','feasibility','clarity','importance','evidence_grounding']
finals = [row for row in rows if row['is_final'].lower() == 'true']
valid = [row for row in finals if all(row[m] for m in metrics)]
run_map = {(r['seed_id'], r['configuration'], r['replicate']): r for r in runs}
corpus = load(ROOT / 'data/corpus/manifest.json')
report = [
    '# Live pilot findings and research discussion', '',
    '**Literature-Grounded Research Idea Generation Using Specialized Multi-Agent Reviewers**', '',
    f'Study: `{study.name}`. Status: **{status["status"]}**. This is a real two-seed debugging pilot, not a completed efficacy study.', '',
    '## Objective and implemented method', '',
    'Test whether distinct novelty, feasibility, clarity/importance and contrarian reviewers, literature-based overlap checking and bounded revision change independently judged proposal quality. ResearchAgent inspires the workflow; it already uses criterion-specific reviewers. Multi-agent reviewing and evidence-grounded evaluation are established, with InnoEval as close prior work. Our contribution is a course-level comparative implementation and ablation study, not a first-invention claim.', '',
    'The implemented workflow searches real literature, generates one shared initial proposal per seed, collects independent reviewer contexts, preserves all feedback and failures, and revises up to three rounds. Early stopping retains the last valid idea. No model is trained and no proposed scientific experiment is executed. This pilot used the Python state engine; the LangGraph adapter remains separately unverified because its dependency is unavailable.', '',
    '## Dataset and experimental configurations', '',
    f'The local retrieval pool has {corpus["paper_count"]:,} real records with abstracts: six pinned official ACL metadata downloads plus attributed project/prior-work anchors. The fixed evaluation manifest has twenty seeds; this pilot used ResearchAgent and SciMON only. They are purposive scientific-ideation inputs, not a representative sample of NLP research. The corpus fingerprint and raw-source hashes are saved.', '',
    'Conditions: one-shot, generic iterative review, full specialist panel, no feasibility reviewer, no contrarian reviewer, and no additional novelty retrieval. Within each seed all conditions share the initial proposal, original literature, Gemini model/settings and constraints. The no-retrieval condition retains original context. Natural API budgets differ, so additional computation confounds a pure specialization effect.', '',
    '## Evaluation procedure', '',
    'A separately prompted Gemini judge receives proposal text and its own literature query, without configuration labels, reviewer scores or refinement history. It scores novelty, feasibility, clarity, importance and evidence grounding from 1–5 with separate rationales. Identical proposal content shares one judgment. Human forms are prepared but no human ratings have been collected. Same-model judging remains vulnerable to shared knowledge and preference bias.', '',
    'The pilot required verbatim evidence excerpts and rejected quotations that did not match source text. Mechanical quotation matching establishes provenance only; it does not validate semantic support or universal novelty.', '',
    '## Observed execution and failures', '',
    f'- Saved configurations: {len(runs)} across {audit["distinct_seeds"]} seeds.',
    f'- Accepted final-condition rating rows: {len(valid)} of {len(finals)}.',
    f'- Distinct judgment contents attempted: {audit["unique_judgments_attempted"]}; accepted: {audit["unique_judgments_accepted"]}; rejected: {audit["unique_judgments_failed"]}. Aliases are not independent observations.',
    f'- Reviewer failures: {len(audit["reviewer_failures"])}. All recorded reviewer failures concern evidence excerpt validation.',
    f'- Stopping reasons: {audit["stopping_reasons"]}.',
    f'- Saved API attempts across the study ledger: {audit["all_saved_api_attempts"]}; failure types: {audit["api_error_counts"]}. The ledger includes earlier agent-network failures before the successful terminal run.',
    f'- Provider-reported token total, where available: {audit["provider_reported_total_tokens_lower_bound"]:,}; {audit["attempts_without_usage_metadata"]} attempts lack usage metadata. This is a lower bound, not a complete billed-token total.',
    f'- Latest suite wall time: {audit.get("latest_suite_wall_seconds",0)/60:.2f} minutes.', '',
    'The configured token rates are zero for the user-confirmed free tier. This is an estimate, not an independently verified bill. Shared initial-generation resources and judge resources are recorded separately from condition-level resource tables.', '',
    '## Individual final ratings', '',
    '| Seed | Condition | Novelty | Feasibility | Clarity | Importance | Grounding | Stop | Reviewer failures |',
    '|---|---|---:|---:|---:|---:|---:|---|---:|',
]
for row in sorted(finals, key=lambda r: (r['seed_id'],r['configuration'])):
    run = run_map[(row['seed_id'], row['configuration'], int(row['replicate']))]
    failures = sum(bool(o['error']) for rd in run['rounds'] for o in rd['reviews'])
    report.append('| ' + ' | '.join([row['seed_id'],row['configuration']]
                  + [row[m] or 'missing' for m in metrics]
                  + [run['stop_reason'],str(failures)]) + ' |')
report += ['', 'Missing ratings are not imputed. A final proposal retained after all reviewers failed can still have a reused initial judgment; that is fallback behavior, not successful refinement.', '',
    '## Baseline comparison and ablations', '',
    'Only one seed has accepted final ratings for both one-shot and full review. Different valid sample counts mean the configuration averages cannot be interpreted as matched treatment effects. Both no-novelty-retrieval final judgments were rejected, preventing that ablation comparison. The contribution of feasibility or contrarian review therefore remains unresolved.', '']
by_key = {(r['seed_id'],r['configuration']):r for r in valid}
for seed in sorted({r['seed_id'] for r in valid}):
    if (seed,'one_shot') in by_key and (seed,'full') in by_key:
        initial, full = by_key[(seed,'one_shot')], by_key[(seed,'full')]
        changes = ', '.join(f'{m}: {float(full[m])-float(initial[m]):+.0f}' for m in metrics)
        report.append(f'The single accepted paired case ({seed}) has full-minus-one-shot changes of {changes}. Its full run also had failed reviewer messages. This isolated, same-model-judged case does not establish improvement or general superiority.')
report += ['', '## Iterative refinement', '',
    'The full panel stopped on an unchanged proposal after two rounds for one seed and three for the other. This is an implemented stopping rule, not evidence that quality rose monotonically. Some version judgments are missing. Figures now show each seed separately with gaps; pooling different available seeds at different rounds could produce a misleading trend. No conclusion about continued gains, plateau or reversal is supported by these incomplete ratings.', '',
    '## Diagnosis and engineering correction', '',
    'Several rejected quotations changed PDF-extracted hyphenation or punctuation; others inserted ellipses or additional words. The strict validator correctly rejected source mismatches, but free-form quotation transcription made the pipeline fragile. Three judge responses also returned empty uncertainty strings and succeeded after schema retries. HTTP 503 failures recovered through the existing retry path.', '',
    'The corrected code supplies deterministic source-passage IDs, restricts model evidence selections to those IDs, and attaches exact stored quotations programmatically. Unknown IDs and invented quotation fields remain invalid. This prevents transcription errors without treating fuzzy matches as evidence. Semantic support still requires evaluation and human checking.', '',
    'The original raw proposals, reviews, API responses and judgments are preserved. Original plots are archived under `audit/original_analysis`; the failure audit and raw-file hashes are also saved. A fresh controlled rerun must use `results/smoke_v2` and the corrected evidence protocol; the correction has software tests but has not yet been verified through a live Gemini study.', '',
    '## Figures and tables', '',
    'See `results/smoke/analysis/RESULTS.md`, the five PNG/PDF figures, `summary.csv`, `paired_comparisons.csv`, `iteration_scores.csv`, `missing_evaluation_rows.csv`, and `resources.csv`. The three project notebooks now inspect genuine saved pilot outputs; ordinary Python cells were verified with the documented fallback. Real Jupyter-kernel verification is still pending.', '',
    '## Limitations and conclusion', '',
    'Two purposive seeds, incomplete matched scores, citation-validation failures, shared-model judging, no human calibration, a bounded abstract corpus, possible memorization, unequal API budgets, and proposal-level rather than executed feasibility all limit interpretation. No significance claim is made. Agent/version counts do not enlarge the independent sample size.', '',
    'The live pilot demonstrates functioning generation, specialist review, refinement, ablations and separate judging, while exposing a citation-interface failure that prevents a defensible efficacy conclusion. Whether specialized review improves novelty or feasibility, which reviewer is most useful, and whether added rounds help remain open until the corrected controlled study is evaluated.', '']
target = ROOT / 'docs/RESEARCH_FINDINGS.md'
if target.exists():
    previous = target.read_bytes()
    archive = ROOT / 'docs/archive' / ('RESEARCH_FINDINGS_' + hashlib.sha256(previous).hexdigest()[:12] + '.md')
    archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists(): shutil.copyfile(target,archive)
target.write_text('\n'.join(report),encoding='utf-8')
print('Wrote research discussion from actual saved live artifacts:',target)
