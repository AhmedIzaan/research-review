"""Gemini REST structured output, throttling, retries and per-attempt telemetry.

Uses the documented GenerateContent API directly to reduce SDK coupling.
Never logs API headers, URLs containing secrets, or exception response bodies.
"""
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from pydantic import ValidationError
from .storage import digest, save_json, utcnow

class LLMError(RuntimeError):
    pass

class BudgetExceeded(LLMError):
    pass

class GeminiClient:
    provenance = 'live_gemini'

    def __init__(self, settings, audit_dir, transport=None, sleep=time.sleep):
        self.settings = settings
        self.audit_dir = audit_dir
        self.events = []
        if audit_dir and audit_dir.exists():
            from .storage import load_json
            self.events = sorted([load_json(p)['event'] for p in audit_dir.glob('*.json')], key=lambda e:e['timestamp'])
        self.transport = transport or self._http
        self.sleep = sleep
        self.last_request = 0.0

    def _http(self, model, payload):
        key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not key:
            raise LLMError('Set GEMINI_API_KEY in .env or the environment; no live call was made')
        url = 'https://generativelanguage.googleapis.com/v1beta/models/'+quote(model,safe='')+':generateContent'
        req = Request(url, data=json.dumps(payload).encode(), headers={
            'Content-Type':'application/json','x-goog-api-key':key},method='POST')
        with urlopen(req,timeout=120) as response:
            return json.load(response)

    def generate(self, schema, instruction, content, label, model=None):
        model = model or self.settings.model
        payload = {'systemInstruction':{'parts':[{'text':instruction}]},
                   'contents':[{'role':'user','parts':[{'text':json.dumps(content,ensure_ascii=False)}]}],
                   'generationConfig':{'temperature':self.settings.temperature,
                       'maxOutputTokens':self.settings.max_output_tokens,
                       'responseMimeType':'application/json', 'responseJsonSchema':schema.model_json_schema()}}
        for attempt in range(self.settings.max_attempts):
            if len(self.events) >= self.settings.max_api_calls:
                raise BudgetExceeded('Configured global API attempt cap reached')
            wait = self.settings.request_interval - (time.monotonic()-self.last_request)
            if wait > 0:
                self.sleep(wait)
            start = time.monotonic()
            self.last_request = start
            event = {'label':label,'model':model,'attempt':attempt+1,'timestamp':utcnow(),
                     'prompt_hash':digest(payload),'input_tokens':None,'output_tokens':None,
                     'thinking_tokens':None,'total_tokens':None,'estimated_cost_usd':None,
                     'status':'failed','validation_failure':False}
            retry = True
            raw = None
            try:
                raw = self.transport(model,payload)
                usage = raw.get('usageMetadata',{})
                event.update(input_tokens=usage.get('promptTokenCount'),output_tokens=usage.get('candidatesTokenCount'),
                             thinking_tokens=usage.get('thoughtsTokenCount',0),total_tokens=usage.get('totalTokenCount'))
                if event['input_tokens'] is not None and event['output_tokens'] is not None and self.settings.input_rate is not None and self.settings.output_rate is not None:
                    event['estimated_cost_usd'] = (event['input_tokens']*self.settings.input_rate +
                         (event['output_tokens']+(event['thinking_tokens'] or 0))*self.settings.output_rate)/1e6
                parts = raw.get('candidates',[{}])[0].get('content',{}).get('parts',[])
                text = ''.join(p.get('text','') for p in parts if not p.get('thought',False))
                result = schema.model_validate_json(text)
                event['status'] = 'ok'
                return result
            except ValidationError:
                event.update(error='StructuredOutputValidationError',validation_failure=True)
            except HTTPError as exc:
                event['error'] = f'HTTP {exc.code}'
                retry = exc.code in (429,500,502,503,504)
            except (URLError, TimeoutError):
                event['error'] = 'NetworkOrTimeoutError'
            except (ValueError, KeyError, IndexError):
                event.update(error='InvalidProviderResponse',validation_failure=True)
            except LLMError as exc:
                event['error'] = str(exc)
                retry = False
            finally:
                event['elapsed_seconds'] = time.monotonic()-start
                self.events.append(event)
                if self.audit_dir:
                    save_json(self.audit_dir / f'{__import__("uuid").uuid4().hex}.json',
                              {'event':event,'request':payload,'response':locals().get('raw')})
            if not retry or attempt + 1 == self.settings.max_attempts:
                raise LLMError(event.get('error','Gemini request failed')) from None
            self.sleep(min(2**attempt*3,30))
