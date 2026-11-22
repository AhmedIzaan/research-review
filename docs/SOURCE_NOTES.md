# Source and dependency notes

Local sources inspected: root `context.md`, `literature_review_Agentic.docx`, available `research proposal_business research.pdf`, and completed `MG3010_Assignment_02/MG3010_Assignment_02_Final_Report.pdf` including its selection, extraction and quality appendices. The requested proposal name with `(1)` is absent. The available proposal is used with that discrepancy disclosed. No original files were renamed or overwritten.

The original proposal's broad gap and several bibliographic labels are superseded by the later Business Research audit: ResearchAgent already uses criterion-specific reviewers and feasibility criteria; InnoEval is especially close prior work; SciMON is ACL 2024. The review remains an automated evidence assessment with pending human confirmations, rather than an independently human-verified systematic review. Its published-study results are never used as this implementation's experiment results.

Primary sources checked through browser tools during implementation:

- [ResearchAgent, NAACL 2025](https://aclanthology.org/2025.naacl-long.342/): smoke-seed metadata and system foundation.
- [SciMON, ACL 2024](https://aclanthology.org/2024.acl-long.18/): smoke-seed metadata and novelty-oriented retrieval/refinement foundation.
- [Gemini 3.5 Flash-Lite model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite): user-selected exact model ID and structured-output support.
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing): published free-tier availability. Actual account quota and billing eligibility remain unchecked.
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api): StateGraph, conditional transitions and explicit recursion limits.

Network failures on other documentation endpoints are not treated as successful verification. The Gemini REST integration and LangGraph adapter remain subject to live verification in the actual environment.

The twenty-seed import retains the earlier source capture paths, hashes, original dates and version caveats in `data/seed_provenance.json`; metadata fields are copied rather than invented. It does not imply new successful Python retrieval or independent verification of all twenty sources in this session.
