"""Read saved live artifacts and write a failure audit without altering raw results."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from research_review.storage import load_json, save_json


def audit(study):
    runs = [load_json(p) for p in (study / 'runs').glob('*.json')
            if not p.name.endswith('.partial.json')]
    judgments = [load_json(p) for p in (study / 'evaluation/judgments').glob('*.json')]
    events = [load_json(p)['event'] for directory in ('api_audit', 'judge_api_audit')
              for p in (study / directory).glob('*.json')]
    failures = [{'seed_id': r['seed_id'], 'configuration': r['configuration'],
                 'round': rd['index'], 'role': o['role'], 'error': o['error']}
                for r in runs for rd in r['rounds'] for o in rd['reviews'] if o['error']]
    errors = Counter(e.get('error', 'none') for e in events if e['status'] != 'ok')
    result = {'saved_configurations': len(runs), 'distinct_seeds': len({r['seed_id'] for r in runs}),
              'reviewer_failures': failures,
              'stopping_reasons': dict(Counter(r['stop_reason'] for r in runs)),
              'unique_judgments_attempted': len(judgments),
              'unique_judgments_accepted': sum(j['judgment'] is not None for j in judgments),
              'unique_judgments_failed': sum(j['error'] is not None for j in judgments),
              'judgment_errors': [{'blind_id': j['blind_id'], 'error': j['error']}
                                 for j in judgments if j['error']],
              'all_saved_api_attempts': len(events), 'api_error_counts': dict(errors),
              'provider_reported_total_tokens_lower_bound': sum(e.get('total_tokens') or 0 for e in events),
              'attempts_without_usage_metadata': sum(e.get('total_tokens') is None for e in events),
              'scientific_interpretation': 'Small pilot: score coverage and execution failures must be examined separately; no population efficacy or significance conclusion.'}
    if (study / 'suite_status.json').exists():
        status = load_json(study / 'suite_status.json')
        if status.get('finished_at'):
            result['latest_suite_wall_seconds'] = (datetime.fromisoformat(status['finished_at'])
                                                    - datetime.fromisoformat(status['started_at'])).total_seconds()
    save_json(study / 'audit/data_quality.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    audit(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'results/smoke')
