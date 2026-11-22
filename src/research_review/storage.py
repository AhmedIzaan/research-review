"""Atomic persistence and stable fingerprints, without silently replacing prior runs."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

def digest(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()

def save_json(path: Path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
    os.replace(tmp,path)

def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))
