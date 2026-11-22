# Dependency verification: implemented scope and limits

New runs use `specialized_review_v5_dependencies`. Each distinct proposal gets two additional model calls: extraction of up to ten concrete dependencies, then source-based verification without reviewer feedback. Claims are anchored to exact proposal text. Retrieval searches the named entities in the pinned scholarly corpus; relevant imported official documents are also supplied. Verdicts are supported, contradicted, unverified, or requires measurement.

Exact citations and identifiers are validated. Hardware sufficiency is always classified as requiring measurement. Where an imported source contains an explicitly exhaustive language list, membership is checked deterministically; incomplete lists cannot establish absence. Conflicting lists remain unverified. Structured metadata currently covers language membership only; task/access/capability judgments use model interpretation of sources. No empirical reliability claim is made for those interpretations.

Initial findings go into revision feedback. A contradicted essential dependency or failed candidate verification blocks candidate acceptance. Unverified claims remain visible and provisional; the system does not pretend that every unknown is false. If the retained final proposal has contradicted essential dependencies, the job/study reports failures even if its API calls completed. One-shot conditions are assessed without revision. Both accepted and rejected candidates remain independently scored. The independent outcome judge does not receive verifier opinions.

The final-assessment and round views display claims, verdicts, methods, source links, quotations and repair suggestions. Old traces have no dependency report. Unchanged candidates are cached within a run. Study settings fingerprint the imported source file so it cannot silently change during resume. Exact-content reuse across conditions is not yet implemented for verification, so budget estimates include repeated initial checks.

## Authoritative evidence beyond abstracts

The pipeline does not autonomously browse arbitrary model-generated URLs. Use official dataset/model cards or repository documents and import a pinned snapshot. The explicit-URL downloader permits HTTPS documents on Hugging Face, GitHub's raw host and ACL Anthology, refuses redirects, caps downloads and never executes source content.

```bash
../.venv/bin/python scripts/fetch_verification_source.py \
  --url HTTPS_URL_OF_OFFICIAL_RAW_DOCUMENT --output /tmp/source-card.txt
../.venv/bin/python scripts/import_verification_source.py \
  --entity EXACT_DATASET_OR_MODEL_NAME --url HTTPS_URL_OF_OFFICIAL_RAW_DOCUMENT \
  --text /tmp/source-card.txt --aliases ALTERNATIVE_NAME
```

Replace the placeholders with actual official URLs and entity names. For an explicitly exhaustive dataset language list, add `--languages en ur ... --languages-complete` using the actual ISO codes in that document. Do not assert completeness merely because a language is absent from an abstract. The list is a researcher transcription: hashes verify stored text integrity, not source authenticity or transcription correctness. Imported records retain that provenance limitation. Review source text and metadata before use. Restart the server after imports so its configuration fingerprint reflects them.

A download attempt in the coding environment failed with DNS resolution unavailable. No official card was fabricated or imported as a substitute. Without imports, the stage uses available scholarly abstracts and must qualify coverage; authoritative-document fetching still needs validation in the user's network environment. Sources should be curated for the chosen experimental entities before comparing conditions. This is a bounded verification implementation, not a complete autonomous fact-checking service.

## Rerun and budgets

```bash
../.venv/bin/python scripts/serve.py
```

Dependency verification is enabled by default in the UI and environment-loaded settings. Disable it explicitly for an ablation with the UI checkbox or `VERIFY_DEPENDENCIES=false`; keep the study protocol fixed. Bare `Settings()` leaves it disabled for legacy library callers. Default full one-round demos plan 20 calls before retries. The default three-seed five-condition smoke study plans 147 calls, at most 441 attempts across clients before reuse/early stops:

```bash
../.venv/bin/python scripts/run_experiments.py --study results/dependencies_v5_smoke --dry-run
../.venv/bin/python scripts/run_experiments.py --study results/dependencies_v5_smoke
```

The old paper and traces are not rewritten. New passage segmentation avoids abbreviation fragments and preserves complete sentence slices. Final-version mapping now identifies the last accepted revision rather than an unchanged candidate alias.

## Evaluate the verifier using actual human labels

```bash
../.venv/bin/python scripts/verification_labels.py YOUR_NEW_TRACE.json --output /tmp/claim_labels.csv
```

The exported CSV withholds predicted verdicts. Have a knowledgeable rater inspect the claim and source documents, then enter one of the four verdicts, a rater ID, and notes. Missing source evidence must not be equated with contradiction. Include independently selected false and uncertain claims as well as correct claims; a convenient trace alone is a biased reliability sample. For multiple raters, adjudicate one label per claim before scoring.

```bash
../.venv/bin/python scripts/verification_labels.py YOUR_NEW_TRACE.json \
  --labels /tmp/claim_labels.csv --output /tmp/verifier_agreement.json
```

The script reports descriptive agreement, false approvals among supported predictions, and recall of human-labeled contradictions. No human labels or reliability scores have been generated here. Extraction coverage, omitted dependencies, and human disagreement also require separate review.
