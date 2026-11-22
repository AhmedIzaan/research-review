# Corpus sources and attribution

This corpus contains real scholarly metadata and abstracts, not generated
publications or executed research results. Individual records preserve titles,
authors, years, source URLs and available DOIs.

The six original XML collections were downloaded from the official
`acl-org/acl-anthology` repository at commit
`3b320071c97927135c7e86d84b6d626b4943dc4a` using the connected GitHub read tools:

- `2024.acl.xml`
- `2025.naacl.xml`
- `2024.sdp.xml`
- `2025.sdp.xml`
- `2024.sigdial.xml`
- `2025.sigdial.xml`

Raw files are unchanged and verified against Git blob hashes.
`raw/download_manifest.json` records original URLs, timestamps and hashes.
`manifest.json` records derived-file provenance and exclusions.
`record_provenance.json` maps every indexed record back to a source.

The derived `papers.json` normalizes XML markup and whitespace and excludes
records without a title or abstract. It also imports separately attributed
project anchors from existing source captures, including InnoEval; these are
distinguished from the newly downloaded collections. Evaluation seeds remain
unchanged. No full-paper PDFs are claimed to be included.

The ACL policy states ACL materials published since 2016 are available under
Creative Commons Attribution 4.0; third-party materials may have different
terms. Retain author and source attribution. The repository's Apache software
license is not presented as a blanket license for all scholarly content.
Imported non-ACL anchors retain their own source/version and applicable rights.

- Official metadata: https://aclanthology.org/info/development/
- Copyright policy: https://aclanthology.org/faq/copyright/
- Original repository: https://github.com/acl-org/acl-anthology

The corpus is a fixed, bounded snapshot, mostly 2024–2025 plus project anchors.
It is neither all scientific literature nor proof that an unmatched idea is novel.
