"""Matched-seed runner with shared initials, randomized condition order and resume."""
import random
import time
from .config import CONFIGURATIONS
from .schemas import Paper, Run
from .idea_generator import generate_idea
from .literature_retrieval import unique_papers
from .orchestration import Workflow
from .storage import digest, load_json, save_json
from .evidence_catalog import PROTOCOL
from .judge_retrieval import JUDGE_RETRIEVAL_PROTOCOL


def run_study(seeds,client,retriever,settings,study_dir,replicates=1,configurations=None,progress=None):
    configurations = configurations or list(CONFIGURATIONS)
    if len(set(configurations))!=len(configurations) or not set(configurations)<=set(CONFIGURATIONS):
        raise ValueError('Invalid or duplicated configurations')
    spec = {'seeds':[p.model_dump() for p in seeds],'settings':settings.model_dump(),
            'replicates':replicates,'configurations':list(configurations),'protocol_version':'5',
            'evidence_protocol':PROTOCOL,
            'judge_retrieval_protocol':JUDGE_RETRIEVAL_PROTOCOL,
            'retrieval_snapshot':getattr(retriever,'fingerprint',None)}
    manifest = study_dir/'manifest.json'
    comparison_spec = {**spec, 'settings':settings.model_dump(exclude={'max_api_calls'})}
    if manifest.exists() and load_json(manifest)['fingerprint'] != digest(comparison_spec):
        raise ValueError('Study inputs/settings changed: choose a new study directory')
    if not manifest.exists():
        save_json(manifest,{'fingerprint':digest(comparison_spec),'specification':spec})
    runs=[]
    for seed in seeds:
        for replicate in range(replicates):
            prefix=digest({'seed':seed.paper_id,'replicate':replicate})[:16]
            initial_path=study_dir/'initials'/f'{prefix}.json'
            if initial_path.exists():
                saved=load_json(initial_path)
                from .schemas import Idea
                initial=Idea.model_validate(saved['idea'])
                literature=[Paper.model_validate(p) for p in saved['literature']]
            else:
                searches=retriever.related(seed.title,limit=5)
                literature=unique_papers([seed]+[p for s in searches for p in s.papers])
                start,offset=time.monotonic(),len(client.events)
                initial=generate_idea(client,literature,settings.constraints)
                save_json(initial_path,{'idea':initial.model_dump(),'literature':[p.model_dump() for p in literature],
                         'search':[s.model_dump() for s in searches],'elapsed_seconds':time.monotonic()-start,
                         'events':client.events[offset:]})
            order=list(configurations)
            rng_seed=int(digest({'seed':seed.paper_id,'replicate':replicate,'random_seed':settings.random_seed})[:12],16)
            random.Random(rng_seed).shuffle(order)
            for configuration in order:
                existing=[]
                for p in (study_dir/'runs').glob('*.json'):
                    if p.name.endswith('.partial.json'): continue
                    r=Run.model_validate(load_json(p))
                    if (r.seed_id,r.configuration,r.replicate)==(seed.paper_id,configuration,replicate): existing.append(r)
                if existing:
                    runs.extend(existing)
                    if progress:
                        progress(f'Reusing seed={seed.paper_id} condition={configuration} replicate={replicate}')
                    continue
                if progress:
                    progress(f'Starting seed={seed.paper_id} condition={configuration} replicate={replicate}')
                result=Workflow(client,retriever,settings).run(seed.paper_id,configuration,initial,literature,study_dir/'runs',replicate)
                runs.append(result)
                if progress:
                    failures=sum(bool(o.error) for rd in result.rounds for o in rd.reviews)
                    progress(f'Finished condition={configuration}; stop={result.stop_reason}; reviewer_failures={failures}')
                if result.stop_reason=='api_budget_exhausted':
                    raise RuntimeError('API attempt cap reached; study is incomplete; resume with an explicit larger cap/new study')
    save_json(study_dir/'retrieval_log.json',retriever.log)
    return runs
