"""Experiment settings. Keys remain outside serialized settings."""
import os
from pathlib import Path
from typing import Literal
from pydantic import Field
from .schemas import Record

ROOT = Path(__file__).resolve().parents[2]

class Settings(Record):
    methodology_version: str = 'specialized_review_v8_design_repairs'
    revision_policy: Literal['always_accept','guarded'] = 'always_accept'
    judge_repeats: int = Field(default=1,ge=1,le=5,strict=True)
    online_source_lookup: bool = False
    verify_dependencies: bool = False
    verification_source_fingerprint: str | None = None
    verification_sources: str = 'data/verification_sources.json'
    final_review: bool = False
    audit_evidence: bool = False
    model: str = 'gemini-3.5-flash-lite'
    judge_model: str = 'gemini-3.5-flash-lite'
    temperature: float = Field(default=0.4, ge=0, le=2)
    max_output_tokens: int = Field(default=4096, ge=512)
    rounds: int = Field(default=3, ge=0, le=3)
    max_attempts: int = Field(default=3, ge=1, le=5)
    request_interval: float = Field(default=15, ge=0)
    max_api_calls: int = Field(default=160, ge=1)
    input_rate: float | None = Field(default=0, ge=0)
    output_rate: float | None = Field(default=0, ge=0)
    engine: str = 'auto'
    retrieval_backend: Literal['local', 'online'] = 'local'
    corpus_path: str = 'data/corpus/papers.json'
    corpus_fingerprint: str | None = None
    random_seed: int = 20261107
    constraints: str = 'University AI/NLP project: 6 weeks, 1 consumer GPU (12 GB) or API access, public lawful datasets, no LLM training.'

    @classmethod
    def from_env(cls, **overrides):
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
        load_dotenv(ROOT.parent / '.env')
        values = dict(online_source_lookup=os.getenv('ONLINE_SOURCE_LOOKUP','true').lower()=='true',verify_dependencies=os.getenv('VERIFY_DEPENDENCIES','true').lower()=='true',model=os.getenv('GEMINI_MODEL','gemini-3.5-flash-lite'),
                      revision_policy=os.getenv('REVISION_POLICY','guarded'),
                      judge_repeats=int(os.getenv('JUDGE_REPEATS','2')),
                      judge_model=os.getenv('JUDGE_MODEL',os.getenv('GEMINI_MODEL','gemini-3.5-flash-lite')),
                      temperature=float(os.getenv('TEMPERATURE','0.4')),
                      max_output_tokens=int(os.getenv('MAX_OUTPUT_TOKENS','4096')),
                      request_interval=float(os.getenv('REQUEST_INTERVAL_SECONDS','15')),
                      max_api_calls=int(os.getenv('MAX_API_CALLS','160')),
                      retrieval_backend=os.getenv('RETRIEVAL_BACKEND','local'),
                      corpus_path=os.getenv('CORPUS_PATH','data/corpus/papers.json'),
                      input_rate=float(os.getenv('INPUT_USD_PER_MILLION','0')),
                      output_rate=float(os.getenv('OUTPUT_USD_PER_MILLION','0')))
        values.update(overrides)
        from .storage import digest,load_json
        source=ROOT/values.get('verification_sources','data/verification_sources.json')
        values['verification_source_fingerprint']=digest(load_json(source)) if source.exists() else None
        return cls(**values)

CONFIGURATIONS = {
    'one_shot': (),
    'generic': ('generic',),
    'full': ('novelty','feasibility','clarity','contrarian'),
    'no_feasibility': ('novelty','clarity','contrarian'),
    'no_contrarian': ('novelty','feasibility','clarity'),
    'no_novelty_retrieval': ('novelty','feasibility','clarity','contrarian'),
    'full_unguarded': ('novelty','feasibility','clarity','contrarian'),
    'generic_matched': ('generic','generic','generic','generic'),
    'feasibility_to_generic': ('novelty','generic','clarity','contrarian'),
    'contrarian_to_generic': ('novelty','feasibility','clarity','generic'),
}

PRIMARY_CONFIGURATIONS = ('one_shot','generic','full','no_feasibility',
                          'no_contrarian','no_novelty_retrieval')

def budget(n: int, rounds: int = 3, attempts: int = 3, *, configurations=None,
           revision_policy='always_accept', judge_repeats=1, final_review=False,
           audit_evidence=False, verify_dependencies=False) -> dict:
    configs=list(CONFIGURATIONS if configurations is None else configurations)
    if not configs or len(configs)!=len(set(configs)) or not set(configs)<=set(CONFIGURATIONS):
        raise ValueError('Choose nonempty, distinct known configurations')
    pipeline=1+2*len(configs)*int(verify_dependencies)
    for c in configs:
        roles=CONFIGURATIONS[c]
        if not roles or not rounds:continue
        pipeline+=rounds*(len(roles)+1+2*int(verify_dependencies)+(revision_policy=='guarded' and c!='full_unguarded'))
        if final_review:pipeline+=len(roles)+int(audit_evidence)
    # One shared initial and all candidate/accepted versions; duplicates reused.
    versions=1+sum(rounds for c in configs if CONFIGURATIONS[c] and rounds)
    judges=versions*judge_repeats
    total = n * (pipeline + judges)
    return {'seeds':n, 'rounds':rounds, 'generation_review_calls':n*pipeline,
            'judge_calls_upper_bound':n*judges, 'total_calls_upper_bound':total,
            'with_retries_upper_bound':total*attempts,
            'planning_input_tokens':total*6500, 'planning_output_tokens':total*1400,
            'configurations':configs,'revision_policy':revision_policy,'judge_repeats':judge_repeats,
            'note':'Upper planning bounds before early stops and content reuse. Call-matched controls are not token-matched.'}


def load_seed_records(root=ROOT):
    from .storage import load_json
    records={}
    for path in (root/'data/seeds.json',root/'data/evaluation_seeds_v3.json'):
        if path.exists():
            for record in load_json(path):records[record['paper_id']]=record
    return list(records.values())
