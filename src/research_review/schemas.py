"""Strict interchange contracts for agents, evidence, and saved traces."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1)]
Score = Annotated[int, Field(ge=1, le=5, strict=True)]
Role = Literal['novelty', 'feasibility', 'clarity', 'contrarian', 'generic']
ROLE_METRICS = {'novelty': ('novelty',), 'feasibility': ('feasibility',),
                'clarity': ('clarity', 'importance'), 'contrarian': (),
                'generic': ('novelty', 'feasibility', 'clarity', 'importance')}

class Record(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Paper(Record):
    paper_id: Text
    title: Text
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=1900, le=2100)
    abstract: str = ''
    url: Text
    doi: str | None = None
    source: Text
    retrieved_at: Text

class SearchResult(Record):
    query: Text
    provider: Text
    retrieved_at: Text
    papers: list[Paper]
    status: Literal['ok', 'empty', 'failed']
    error: str | None = None
    cache_hit: bool = False

class AssumptionCheck(Record):
    assumption: Text
    validation_step: Text
    acceptance_criterion: Text
    fallback: Text

class PriorWorkComparison(Record):
    paper_id: Text
    shared_mechanism: Text
    proposed_difference: Text
    verification_needed: Text

class Idea(Record):
    title: Text
    research_problem: Text
    research_gap: Text
    methodology: Text
    expected_contribution: Text
    experimental_setup: Text
    evaluation_strategy: Text
    feasibility_assumptions: list[Text] = Field(min_length=1)
    references: list[str] = Field(default_factory=list)
    search_queries: list[Text] = Field(min_length=1, max_length=3)
    # Defaults preserve readability of historical experiment records.
    assumption_checks: list[AssumptionCheck] = Field(default_factory=list)
    prior_work_comparison: list[PriorWorkComparison] = Field(default_factory=list)
    core_hypothesis: str | None = None
    distinctive_mechanism: str | None = None
    minimum_test: str | None = None

class ProposalDraft(Idea):
    """New model outputs must operationalize assumptions and compare prior art."""
    assumption_checks: list[AssumptionCheck] = Field(min_length=1, max_length=4)
    prior_work_comparison: list[PriorWorkComparison] = Field(min_length=1, max_length=4)
    core_hypothesis: Text
    distinctive_mechanism: Text
    minimum_test: Text

class Evidence(Record):
    paper_id: Text
    claim: Text
    supporting_excerpt: Text
    relation: Literal['supports', 'overlaps', 'contradicts', 'context']

class Review(Record):
    role: Role
    novelty: Score | None = None
    feasibility: Score | None = None
    clarity: Score | None = None
    importance: Score | None = None
    explanation: Text
    problems: list[Text] = Field(min_length=1)
    improvements: list[Text] = Field(min_length=1)
    evidence: list[Evidence] = Field(default_factory=list)
    uncertainty: Text
    tradeoffs: list[Text] = Field(default_factory=list)
    falsification_test: Text | None = None

    @model_validator(mode='after')
    def required_scores(self):
        for key in ROLE_METRICS[self.role]:
            if getattr(self, key) is None:
                raise ValueError(f'{self.role} requires {key}')
        return self

class Judgment(Record):
    novelty: Score
    feasibility: Score
    clarity: Score
    importance: Score
    evidence_grounding: Score
    rationale: dict[str, Text]
    evidence: list[Evidence] = Field(default_factory=list)
    uncertainty: Text

    @model_validator(mode='after')
    def rationales(self):
        required = {'novelty','feasibility','clarity','importance','evidence_grounding'}
        if set(self.rationale) != required:
            raise ValueError('One rationale is required for each of the five metrics')
        return self

class ReviewOutcome(Record):
    role: Role
    review: Review | None = None
    search: list[SearchResult] = Field(default_factory=list)
    error: str | None = None
    evidence_status: Literal['verified_excerpt', 'not_required', 'unavailable', 'disabled'] = 'not_required'
    reviewer_id: str | None = None

Change = Literal['improved','unchanged','reduced','uncertain']

class ComparativeRisk(Record):
    issue: Text
    incumbent_state: Text
    candidate_state: Text
    change: Literal['introduced','worsened','unchanged','mitigated','resolved']
    severity: Literal['blocking','manageable']
    reasoning: Text
    next_check: Text

class RevisionCheck(Record):
    comparative_risks: list[ComparativeRisk] | None = None
    mechanism_status: Literal['preserved','meaningful_pivot','lost','uncertain']
    pivot_reason: Text
    novelty: Change
    feasibility: Change
    clarity: Change
    importance: Change
    evidence_grounding: Change
    explanation: Text
    critical_issues: list[Text] = Field(default_factory=list)
    improvements: list[Text] = Field(default_factory=list)
    unresolved_issues: list[Text] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    uncertainty: Text

class ComparativeRevisionCheck(RevisionCheck):
    """New provider outputs require explicit comparison; old traces remain readable."""
    comparative_risks: list[ComparativeRisk]

class Round(Record):
    index: int = Field(ge=1, le=3)
    input_idea: Idea
    reviews: list[ReviewOutcome]
    aggregation: dict
    revised_idea: Idea | None = None
    revision_error: str | None = None
    input_verification: dict | None = None
    candidate_verification: dict | None = None
    candidate_idea: Idea | None = None
    revision_changes: dict = Field(default_factory=dict)
    revision_check: RevisionCheck | None = None
    selection: Literal['legacy','accepted','rejected','unchanged','check_failed'] = 'legacy'
    selection_reason: str | None = None

class CitationAssessment(Record):
    citation_id: Text
    verdict: Literal['supported', 'partial', 'unsupported']
    explanation: Text

class EvidenceAudit(Record):
    assessments: list[CitationAssessment] = Field(min_length=1)
    limitations: Text

    @model_validator(mode='after')
    def distinct_citations(self):
        ids = [a.citation_id for a in self.assessments]
        if len(set(ids)) != len(ids):
            raise ValueError('Every citation must be assessed exactly once')
        return self

class Run(Record):
    initial_verification: dict | None = None
    final_verification: dict | None = None
    run_id: Text
    seed_id: Text
    configuration: Text
    replicate: int
    settings: dict
    literature: list[Paper]
    initial_idea: Idea
    final_idea: Idea
    rounds: list[Round]
    stop_reason: Text
    elapsed_seconds: float
    api_events: list[dict]
    provenance: Literal['live_gemini', 'unit_test_fixture']
    final_reviews: list[ReviewOutcome] = Field(default_factory=list)
    final_aggregation: dict = Field(default_factory=dict)
    final_review_status: Literal['not_requested', 'completed', 'partial', 'failed', 'skipped'] = 'not_requested'
    evidence_audit: EvidenceAudit | None = None
    evidence_audit_error: str | None = None
    evidence_audit_citations: dict = Field(default_factory=dict)
