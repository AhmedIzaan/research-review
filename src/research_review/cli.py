"""python -m research_review.cli --help"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
from .config import ROOT,Settings,budget,CONFIGURATIONS
from .schemas import Paper,Run
from .storage import load_json,save_json,utcnow
from .llm import GeminiClient
from .literature_retrieval import create_retriever

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['preflight','budget','retrieve','run','evaluate','analyze'])
    parser.add_argument('--study',type=Path,default=ROOT/'results'/'smoke_v4')
    parser.add_argument('--seeds',type=Path,default=ROOT/'data'/'smoke_seeds.json')
    parser.add_argument('--n',type=int,default=2)
    parser.add_argument('--rounds',type=int,default=3)
    parser.add_argument('--replicates',type=int,default=1)
    parser.add_argument('--topic',default='retrieval augmented generation evaluation')
    parser.add_argument('--configurations', nargs='+', choices=list(CONFIGURATIONS), default=None)
    parser.add_argument('--engine',choices=['auto','python','langgraph'],default='auto')
    args=parser.parse_args()
    settings=Settings.from_env(rounds=args.rounds,engine=args.engine)
    retriever=create_retriever(settings)
    if args.command=='budget':
        result=budget(args.n,args.rounds,settings.max_attempts)
    elif args.command=='preflight':
        result={'timestamp':utcnow(),'model':settings.model,'credential_present':bool(os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')),
                'retrieval_backend':settings.retrieval_backend,'corpus_fingerprint':settings.corpus_fingerprint,
                'dependencies':{name:bool(importlib.util.find_spec(name)) for name in ['pydantic','langgraph','pandas','matplotlib','scipy','nbformat','nbclient']},
                'retrieval':[s.model_dump() for s in retriever.related(args.topic,limit=2)]}
        save_json(ROOT/'results'/'preflight.json',result)
    elif args.command=='retrieve':
        result=[s.model_dump() for s in retriever.related(args.topic,limit=args.n)]
        save_json(args.study/'topic_retrieval.json',result)
    elif args.command=='run':
        if not (os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')):
            parser.exit(2,'Missing GEMINI_API_KEY. Configure .env; no live experiment was performed.\n')
        from .experiments import run_study
        if args.topic!='retrieval augmented generation evaluation':
            found=[p for s in retriever.related(args.topic,args.n) for p in s.papers]
            if not found:parser.exit(2,'Topic literature retrieval failed; no seeds invented.\n')
            seeds=found[:args.n]
        else:
            seeds=[Paper.model_validate(p) for p in load_json(args.seeds)][:args.n]
        client=GeminiClient(settings,args.study/'api_audit')
        runs=run_study(seeds,client,retriever,settings,args.study,args.replicates,args.configurations)
        result={'completed_runs':len(runs),'study':str(args.study)}
    elif args.command=='evaluate':
        from .evaluation import evaluate_runs
        runs=[Run.model_validate(load_json(p)) for p in (args.study/'runs').glob('*.json') if not p.name.endswith('.partial.json')]
        if not runs:parser.exit(2,'No saved live runs to evaluate.\n')
        judge=GeminiClient(settings,args.study/'judge_api_audit')
        rows=evaluate_runs(runs,judge,retriever,settings,args.study/'evaluation')
        result={'scored_rows':len(rows)}
    else:
        from .analysis import analyze
        result=analyze(args.study)
        save_json(args.study/'analysis_status.json',result)
    print(json.dumps(result,indent=2,default=str))

if __name__=='__main__':main()
