"""Make one tiny Gemini request using the project's .env; never print the key."""
import json
import os
from pathlib import Path
import sys
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from pydantic import BaseModel
from research_review.config import Settings
from research_review.llm import GeminiClient, LLMError
from research_review.storage import save_json, utcnow


class ConnectionResponse(BaseModel):
    status: Literal['ok']


def main():
    settings = Settings.from_env(
        max_attempts=1, max_api_calls=1, request_interval=0,
        max_output_tokens=512,
    )
    key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    report = {
        'checked_at': utcnow(), 'credential_present': bool(key),
        'model': settings.model, 'status': 'not_tested',
    }

    def transport(model, payload):
        request = Request(
            'https://generativelanguage.googleapis.com/v1beta/models/'
            + quote(model, safe='') + ':generateContent',
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json', 'x-goog-api-key': key},
            method='POST',
        )
        try:
            with urlopen(request, timeout=25) as response:
                return json.load(response)
        except HTTPError as exc:
            report['http_status'] = exc.code
            try:
                error = json.loads(exc.read()).get('error', {})
                report['provider_status'] = error.get('status')
                report['provider_message'] = str(error.get('message', '')).replace(
                    key, '[REDACTED]'
                )[:1200]
            except (ValueError, UnicodeError):
                pass
            raise
        except URLError as exc:
            report['network_detail'] = str(exc.reason).replace(key, '[REDACTED]')[:250]
            raise

    if key:
        client = GeminiClient(settings, None, transport=transport)
        try:
            response = client.generate(
                ConnectionResponse,
                'Connection test: return JSON with status equal to ok.',
                {'request': 'check'}, 'connection_check',
            )
            report.update(status='success', response=response.model_dump())
        except LLMError as exc:
            report.update(status='failed', error=str(exc))
        report['api_events'] = client.events
    else:
        report['status'] = 'missing_credential'
    save_json(ROOT / 'results' / 'gemini_connection_check.json', report)
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())
