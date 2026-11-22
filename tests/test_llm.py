import json
import pytest
from research_review.config import Settings
from research_review.llm import GeminiClient,LLMError,BudgetExceeded
from research_review.schemas import Idea

def test_structured_output_retry_and_tokens(idea,tmp_path):
    calls=[]
    def transport(model,payload):
        calls.append(payload)
        return {'candidates':[{'content':{'parts':[{'text':'{}' if len(calls)==1 else idea.model_dump_json()}]}}],
                'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':50,'thoughtsTokenCount':10,'totalTokenCount':160}}
    settings=Settings(request_interval=0,input_rate=1,output_rate=2)
    client=GeminiClient(settings,tmp_path,transport=transport,sleep=lambda _:None)
    assert client.generate(Idea,'instruction',{},'test')==idea
    assert len(client.events)==2 and client.events[0]['validation_failure']
    assert client.events[1]['estimated_cost_usd']==pytest.approx(0.00022)

def test_budget_cap_no_network(idea):
    client=GeminiClient(Settings(max_api_calls=1,request_interval=0),None,
        transport=lambda *_:{'candidates':[{'content':{'parts':[{'text':idea.model_dump_json()}]}}]})
    client.generate(Idea,'instruction',{},'first')
    with pytest.raises(BudgetExceeded):client.generate(Idea,'instruction',{},'second')

def test_no_credentials_fails_without_exposing_secrets(monkeypatch,tmp_path):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False);monkeypatch.delenv('GOOGLE_API_KEY',raising=False)
    client=GeminiClient(Settings(request_interval=0),tmp_path)
    with pytest.raises(LLMError,match='GEMINI_API_KEY'):client.generate(Idea,'instruction',{},'test')
    assert len(client.events)==1
