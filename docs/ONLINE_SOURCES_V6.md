# Online source lookup

New runs use `specialized_review_v6_online_sources`. Environment-loaded settings enable online dataset/model lookup alongside dependency verification. Scholarly novelty retrieval remains the pinned local corpus: this change adds repository evidence for factual dependencies, not general web paper search.

The lookup searches the Hugging Face Hub for up to five candidates per entity. An explicit qualified repository ID is used directly; otherwise only a unique normalized repository-name match is resolved. Multiple matches or no exact match remain ambiguous/not found. A name match is not proof of identity or official authorship. All online sources carry that limitation into verification.

For a resolved repository the system fetches metadata, records its immutable revision, and requests README content at that revision. It attempts one GitHub README linked in the card as supplementary documentation. This is a linked-document fallback, not unrestricted GitHub search. Hosting on either platform alone does not establish authority. The verifier must inspect the publisher, task and version rather than infer correctness from hosting.

Metadata includes available language/task tags, access restrictions, card fields and model pipeline information. Missing fields are not negative evidence; automatic Hub tags are not treated as exhaustive language lists. Original source documents and exact excerpts are retained. The existing manually imported exhaustive language metadata still supports deterministic membership checks. Experimental choices such as shot counts are explicitly separated from factual prerequisites in extraction and verification prompts.

## Configuration

Restart the backend after updating:

```bash
../.venv/bin/python scripts/serve.py
```

Optional local `.env` settings:

```dotenv
ONLINE_SOURCE_LOOKUP=true
HF_TOKEN=
GITHUB_TOKEN=
```

Tokens are optional for public access. Keep any token values local. The HTTP client sends each credential only to its respective service; redirects are refused. Repository cards that require a redirect may be unavailable, in which case metadata remains available and the limitation is recorded. No remote code, dataset scripts or model weights are executed/downloaded.

Each workflow has a 24 logical-request cap, a 12-second request timeout, bounded documents, and one short retry on selected transient errors. Lookup covers at most five dataset/model entities per proposal. Resource-only claims do not trigger repository searches. These HTTP requests add latency and input context but do not add Gemini generation calls beyond the existing two verification calls per distinct proposal. Request caps count logical requests; a retry can add an extra HTTP attempt.

Run this no-Gemini connectivity check first:

```bash
../.venv/bin/python scripts/check_online_sources.py --entity "AG News"
```

If several repositories match, inspect candidates and repeat with a verified qualified repository ID. An exact name match still needs provenance checks. To repeat a failed check after fixing connectivity, use a fresh cache directory:

```bash
../.venv/bin/python scripts/check_online_sources.py --entity "AG News" --cache results/source_lookup_check_retry
```

The implementation's live connectivity check could not reach the service in the coding environment and returned `unavailable`; successful production retrieval has not been demonstrated here. Tests use synthetic HTTP responses and are not research findings.

## Reproducibility and failure behavior

Snapshots are saved under each study/demo's `online_sources/` directory. Runs in the same study reuse the first lookup for an entity, including failures and ambiguity, rather than silently changing evidence between conditions. Exact source text hashes are checked on cache reuse. A new study creates a fresh snapshot; do not delete or edit evidence caches while interpreting a completed study. Network failures are visible in `online_lookups` and the trace UI. They never establish that a dataset is unavailable or a claim false.

Manual official-document snapshots remain available as supplementary evidence. Online evidence is used by dependency verification and repair; the independent outcome judge still uses its separate shared scholarly context and does not receive verifier scores or decisions. This evidence difference must be disclosed when interpreting judge grounding scores.

For new experiments:

```bash
../.venv/bin/python scripts/run_experiments.py --study results/online_sources_v6_smoke --dry-run
../.venv/bin/python scripts/run_experiments.py --study results/online_sources_v6_smoke
```

Use a new study path for this methodology. Previously saved results and the paper remain historical evidence. Evaluate false approvals and extraction coverage using real human labels before claiming reliable factual verification.
