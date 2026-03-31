"""Literal Tyler V1 schema contract.

These models codify the schema package in:

- `tyler_response_20260326/3. V1_SCHEMAS (1).md`

They intentionally live alongside the current shipped runtime models instead of
replacing them immediately. The literal-parity refactor uses this module as the
contract target for subsequent runtime migration waves.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EvidenceLabel(str, Enum):
    """Hierarchy from Tyler V1 DESIGN constraint #5.

    Numeric weights per Tyler spec: vendor-documented (1.0) >
    empirically-observed (0.8) > model-self-characterization (0.5) >
    speculative-inference (0.3).
    """

    VENDOR_DOCUMENTED = "vendor_documented"
    EMPIRICALLY_OBSERVED = "empirically_observed"
    MODEL_SELF_CHARACTERIZATION = "model_self_characterization"
    SPECULATIVE_INFERENCE = "speculative_inference"

    @property
    def weight(self) -> float:
        """Tyler V1 numeric weight for this evidence tier."""
        return _EVIDENCE_LABEL_WEIGHTS[self]


_EVIDENCE_LABEL_WEIGHTS: dict["EvidenceLabel", float] = {
    EvidenceLabel.VENDOR_DOCUMENTED: 1.0,
    EvidenceLabel.EMPIRICALLY_OBSERVED: 0.8,
    EvidenceLabel.MODEL_SELF_CHARACTERIZATION: 0.5,
    EvidenceLabel.SPECULATIVE_INFERENCE: 0.3,
}


class DisputeType(str, Enum):
    """Five-type Tyler V1 disagreement taxonomy."""

    EMPIRICAL = "empirical"
    INTERPRETIVE = "interpretive"
    PREFERENCE_WEIGHTED = "preference_weighted"
    SPEC_AMBIGUITY = "spec_ambiguity"
    OTHER = "other"


class ClaimStatus(str, Enum):
    """Tyler V1 claim lifecycle."""

    INITIAL = "initial"
    SUPPORTED = "supported"
    CONTESTED = "contested"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    VERIFIED = "verified"
    REFUTED = "refuted"
    UNRESOLVED = "unresolved"


class DisputeStatus(str, Enum):
    """Tyler V1 dispute lifecycle."""

    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    DEFERRED_TO_USER = "deferred_to_user"
    LOGGED_ONLY = "logged_only"


class ConfidenceLevel(str, Enum):
    """Telemetry-only confidence for Tyler V1 outputs."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResolutionOutcome(str, Enum):
    """Tyler V1 arbitration resolution outcomes."""

    CLAIM_SUPPORTED = "claim_supported"
    CLAIM_REFUTED = "claim_refuted"
    EVIDENCE_INSUFFICIENT = "evidence_insufficient"
    INTERPRETATION_REVISED = "interpretation_revised"


class StageSummary(BaseModel):
    """Summary emitted by every Tyler V1 stage."""

    stage_name: str = Field(description="e.g., 'Stage 1: Intake & Decomposition'")
    goal: str = Field(description="What this stage was trying to accomplish")
    key_findings: list[str] = Field(description="3-6 bullet points: conflicts, tradeoffs, signals found")
    decisions_made: list[str] = Field(description="What the stage decided and why")
    outcome: str = Field(description="What it produced — one sentence summary")
    reasoning: str = Field(description="How the stage got from input to output — the thinking behind the decisions")


class SubQuestion(BaseModel):
    """Tyler V1 decomposition sub-question."""

    id: str = Field(description="Format: Q-{n}")
    question: str = Field(description="Specific, researchable question")
    type: str = Field(description="'empirical' | 'interpretive' | 'preference'")
    research_priority: str = Field(description="'high' | 'medium' | 'low'")
    search_guidance: str = Field(description="What to look for — source types, keywords, practitioner signals")


class ResearchPlan(BaseModel):
    """Tyler V1 research plan from Stage 1."""

    what_to_verify: list[str] = Field(description="Key factual claims to check")
    critical_source_types: list[str] = Field(description="Types of sources that matter most")
    falsification_targets: list[str] = Field(description="What evidence would change the answer")


class DecompositionResult(BaseModel):
    """Tyler V1 Stage 1 output."""

    core_question: str = Field(description="The central question or decision, restated precisely")
    sub_questions: list[SubQuestion] = Field(description="2-6 sub-questions to research", min_length=2, max_length=6)
    optimization_axes: list[str] = Field(description="Likely tradeoff dimensions")
    research_plan: ResearchPlan
    stage_summary: StageSummary


class Finding(BaseModel):
    """Specific information extracted from a source."""

    finding: str = Field(description="Factual statement extracted from the source")
    evidence_label: EvidenceLabel
    original_quote: Optional[str] = Field(
        default=None,
        description="Preserved verbatim for conflict-bearing findings",
    )


class Source(BaseModel):
    """Tyler V1 normalized source object."""

    id: str = Field(description="Format: S-{n}, globally unique across the pipeline")
    url: str
    title: str
    source_type: str = Field(description="'official_docs' | 'academic' | 'practitioner_report' | 'forum' | 'blog' | 'news'")
    quality_score: float = Field(ge=0.0, le=1.0, description="Final blended authority/freshness score")
    publication_date: Optional[str] = Field(default=None, description="ISO 8601 date of original publication")
    retrieval_date: str = Field(description="ISO 8601 date")
    key_findings: list[Finding]


class SubQuestionEvidence(BaseModel):
    """Evidence grouped by sub-question."""

    sub_question_id: str = Field(description="References DecompositionResult.sub_questions[].id")
    sources: list[Source]
    meets_sufficiency: bool = Field(description="True if min 2 independent high-quality sources found")
    gap_description: Optional[str] = Field(default=None, description="What's missing, if below sufficiency threshold")


class EvidencePackage(BaseModel):
    """Tyler V1 Stage 2 output."""

    sub_question_evidence: list[SubQuestionEvidence]
    total_queries_used: int
    queries_per_sub_question: dict[str, int] = Field(description="Map of Q-{n} → query count")
    stage_summary: StageSummary


class Claim(BaseModel):
    """Tyler V1 Stage 3 claim."""

    id: str = Field(description="Format: C-{n}, unique within this analysis")
    statement: str = Field(description="Specific, falsifiable claim")
    evidence_label: EvidenceLabel
    source_references: list[str] = Field(description="List of S-{n} IDs from the evidence package")
    confidence: ConfidenceLevel = Field(description="TELEMETRY ONLY — not used for arbitration")


class Assumption(BaseModel):
    """Tyler V1 Stage 3 assumption."""

    id: str = Field(description="Format: A-{n}, unique within this analysis")
    statement: str = Field(description="Stated explicitly — first-class citizen, not afterthought")
    depends_on_claims: list[str] = Field(description="List of C-{n} IDs this assumption supports")
    if_wrong_impact: str = Field(description="What changes if this assumption is false")


class CounterArgument(BaseModel):
    """Tyler V1 mandatory counterargument."""

    argument: str = Field(description="Strongest case against the model's own recommendation")
    strongest_evidence_against: str = Field(description="Most compelling counter-evidence")
    counter_confidence: ConfidenceLevel = Field(description="TELEMETRY ONLY")


class AnalysisObject(BaseModel):
    """Tyler V1 Stage 3 analyst output."""

    model_alias: str = Field(description="'A', 'B', or 'C' — anonymized")
    reasoning_frame: str = Field(description="Assigned frame: 'step_back_abstraction' | 'structured_decomposition' | 'verification_first'")
    recommendation: str = Field(description="Bottom-line answer — a recommendation, not a survey")
    claims: list[Claim] = Field(description="All claims supporting the recommendation")
    assumptions: list[Assumption] = Field(description="All assumptions, stated explicitly")
    evidence_used: list[str] = Field(description="S-{n} IDs of sources actually referenced")
    counter_argument: CounterArgument
    falsification_conditions: list[str] = Field(description="What would prove this recommendation wrong")
    reasoning: str = Field(description="How the model got from evidence to conclusion")
    stage_summary: StageSummary


class ClaimLedgerEntry(BaseModel):
    """Tyler V1 canonical claim ledger entry.

    Tyler constraint #4: track lineage of thought changes. The
    status_at_extraction field preserves the claim's initial status
    at Stage 4 extraction so post-arbitration changes are traceable.
    """

    id: str = Field(description="Format: C-{n}, globally unique across all models")
    statement: str = Field(description="Canonical statement — disambiguated and deduplicated")
    source_models: list[str] = Field(description="Which model aliases made this claim")
    evidence_label: EvidenceLabel
    source_references: list[str] = Field(description="S-{n} IDs from evidence package")
    status: ClaimStatus
    status_at_extraction: Optional[ClaimStatus] = Field(
        default=None,
        description="Claim status when first extracted at Stage 4. Preserved for lineage tracking.",
    )
    supporting_models: list[str] = Field(description="Model aliases that agree with this claim")
    contesting_models: list[str] = Field(description="Model aliases that disagree")
    related_assumptions: list[str] = Field(description="A-{n} IDs of assumptions this claim depends on")


class AssumptionSetEntry(BaseModel):
    """Tyler V1 canonical assumption set entry."""

    id: str = Field(description="Format: A-{n}, globally unique")
    statement: str
    source_models: list[str] = Field(description="Which model aliases made this assumption")
    dependent_claims: list[str] = Field(description="C-{n} IDs of claims that depend on this assumption")
    if_wrong_impact: str
    shared_across_models: bool = Field(description="True if 2+ models share this assumption")


class ModelPosition(BaseModel):
    """A model's position on a dispute."""

    model_alias: str
    position: str = Field(description="What this model believes about the disputed claims")


class DisputeQueueEntry(BaseModel):
    """Tyler V1 dispute queue entry."""

    id: str = Field(description="Format: D-{n}")
    type: DisputeType
    description: str = Field(description="Plain language: what's being disputed and why it matters")
    claims_involved: list[str] = Field(description="C-{n} IDs of the conflicting claims")
    model_positions: list[ModelPosition]
    decision_critical: bool = Field(description="Whether flipping this dispute would change the recommendation")
    decision_critical_rationale: str = Field(description="Why this does/doesn't affect the recommendation")
    status: DisputeStatus
    resolution_routing: str = Field(description="Orchestrator-computed routing")


class ExtractionStatistics(BaseModel):
    """Tyler V1 Stage 4 telemetry."""

    total_claims: int
    total_assumptions: int
    total_disputes: int
    disputes_by_type: dict[str, int] = Field(description="DisputeType → count")
    decision_critical_disputes: int
    claims_per_model: dict[str, int] = Field(description="Model alias → claim count")


class ClaimExtractionResult(BaseModel):
    """Tyler V1 Stage 4 output."""

    claim_ledger: list[ClaimLedgerEntry]
    assumption_set: list[AssumptionSetEntry]
    dispute_queue: list[DisputeQueueEntry]
    statistics: ExtractionStatistics
    stage_summary: StageSummary


class ChangeBasicType(str, Enum):
    """Tyler V1 anti-conformity constraint #9: allowed basis for claim changes."""

    NEW_EVIDENCE = "new_evidence"
    CORRECTED_ASSUMPTION = "corrected_assumption"
    RESOLVED_CONTRADICTION = "resolved_contradiction"


class ClaimStatusUpdate(BaseModel):
    """Typed Stage 5 claim update.

    Tyler V1 constraint #9: a claim may only change status when citing
    new evidence, a corrected assumption, or a resolved contradiction.
    """

    claim_id: str = Field(description="C-{n} of the claim being updated")
    new_status: ClaimStatus = Field(description="Post-verification status: verified, refuted, or unresolved")
    basis_for_change: ChangeBasicType = Field(
        default=ChangeBasicType.NEW_EVIDENCE,
        description=(
            "Why this claim's status changed. Must be one of: "
            "new_evidence (fresh evidence found), "
            "corrected_assumption (an assumption was wrong), "
            "resolved_contradiction (a contradiction was resolved). "
            "Anti-conformity rule: status changes are NOT allowed based on "
            "persuasiveness or authority alone."
        ),
    )
    confidence_in_resolution: ConfidenceLevel = Field(description="TELEMETRY ONLY")
    remaining_uncertainty: Optional[str] = Field(default=None, description="What's still unknown after investigation")


class ArbitrationAssessment(BaseModel):
    """Tyler V1 model output for one investigated dispute."""

    dispute_id: str = Field(description="D-{n} from the dispute queue")
    new_evidence_summary: str = Field(description="What the targeted search found")
    reasoning: str = Field(description="Step-by-step assessment of the dispute given new evidence")
    resolution: ResolutionOutcome
    updated_claim_statuses: list[ClaimStatusUpdate] = Field(description="One entry per claim affected by this dispute")


class AdditionalSource(BaseModel):
    """Evidence found during targeted verification."""

    source_id: str = Field(description="S-{n}, globally unique — must not collide with Stage 2 IDs")
    url: str
    title: str
    quality_score: float = Field(ge=0.0, le=1.0)
    key_findings: list[str] = Field(description="Simplified findings as strings")
    retrieved_for_dispute: str = Field(description="D-{n} this was retrieved to investigate")


class VerificationResult(BaseModel):
    """Tyler V1 Stage 5 output."""

    disputes_investigated: list[ArbitrationAssessment]
    additional_sources: list[AdditionalSource]
    updated_claim_ledger: list[ClaimLedgerEntry] = Field(description="Full ledger with updated statuses")
    updated_dispute_queue: list[DisputeQueueEntry] = Field(description="Full queue with updated statuses")
    search_budget: dict[str, int] = Field(description="D-{n} → queries used")
    rounds_used: int = Field(description="1 or 2 (max 2 per design)")
    stage_summary: StageSummary


class Tradeoff(BaseModel):
    """Tyler V1 decision-relevant tradeoff."""

    if_optimize_for: str
    then_recommend: str


class DisagreementMapEntry(BaseModel):
    """Tyler V1 disagreement map row."""

    dispute_id: str = Field(description="D-{n}")
    type: DisputeType
    summary: str
    resolution: str = Field(description="How it was resolved or why it remains open")
    action_taken: str = Field(description="What the pipeline did about it")
    chosen_interpretation: Optional[str] = Field(
        default=None,
        description="For interpretive disputes: which interpretation was selected and why it's strongest",
    )


class PreservedAlternative(BaseModel):
    """Only alternatives that survived critique."""

    alternative: str
    conditions_for_preference: str = Field(description="When this alternative is better than the recommendation")
    supporting_claims: list[str] = Field(description="C-{n} IDs")


class KeyAssumption(BaseModel):
    """Assumption surfaced in the final synthesis."""

    assumption_id: str = Field(description="A-{n}")
    statement: str
    if_wrong: str = Field(description="What changes if this assumption is false")


class ConfidenceAssessment(BaseModel):
    """Confidence row for final synthesis."""

    claim_summary: str
    confidence: ConfidenceLevel
    basis: str = Field(description="Why this confidence level — cite evidence")


class ClaimLedgerExcerpt(BaseModel):
    """Decision-critical subset of the claim ledger."""

    claim_id: str
    statement: str
    final_status: ClaimStatus
    resolution_path: str = Field(description="How this claim was validated/invalidated")


class EvidenceTrailEntry(BaseModel):
    """Source contribution record in final synthesis."""

    source_id: str
    url: str
    quality_score: float
    key_contribution: str = Field(description="What this source contributed to the analysis")
    conflicts_resolved: Optional[list[str]] = Field(default=None, description="D-{n} IDs if this source helped resolve disputes")


class SynthesisReport(BaseModel):
    """Tyler V1 Stage 6b output."""

    executive_recommendation: str = Field(description="1-3 paragraphs. Bottom-line answer as a recommendation, not a survey.")
    conditions_of_validity: list[str] = Field(description="What would flip the recommendation. Stated upfront.")
    decision_relevant_tradeoffs: list[Tradeoff]
    disagreement_map: list[DisagreementMapEntry]
    preserved_alternatives: list[PreservedAlternative]
    key_assumptions: list[KeyAssumption]
    confidence_assessment: list[ConfidenceAssessment]
    process_summary: list[StageSummary] = Field(description="Compiled from all stage summaries. Scannable in 30 seconds.")
    claim_ledger_excerpt: list[ClaimLedgerExcerpt] = Field(description="Decision-critical claims only")
    evidence_trail: list[EvidenceTrailEntry]
    evidence_gaps: list[str] = Field(description="What the system looked for but couldn't find")
    reasoning: str = Field(description="How the synthesis model arrived at this recommendation from the pipeline state")
    stage_summary: StageSummary


class PipelineError(BaseModel):
    """Tyler V1 pipeline error record."""

    stage: int
    error_type: str = Field(description="'api_failure' | 'invalid_json' | 'timeout' | 'validation_error' | 'budget_exceeded'")
    message: str
    recoverable: bool
    action_taken: str = Field(description="What the orchestrator did: 'retried' | 'skipped_model' | 'used_fallback' | 'aborted'")


class PipelineState(BaseModel):
    """Tyler V1 master pipeline state object."""

    query_id: str = Field(description="UUID for this pipeline run")
    original_query: str
    started_at: str = Field(description="ISO 8601 timestamp")
    current_stage: int = Field(description="1-6")
    stage_1_result: Optional[DecompositionResult] = None
    stage_2_result: Optional[EvidencePackage] = None
    stage_3_alias_mapping: Optional[dict[str, str]] = None
    stage_3_results: Optional[list[AnalysisObject]] = None
    stage_4_result: Optional[ClaimExtractionResult] = None
    stage_5_result: Optional[VerificationResult] = None
    stage_5_skipped: bool = False
    stage_6_user_input: Optional[str] = None
    stage_6_result: Optional[SynthesisReport] = None
    completed_at: Optional[str] = None
    errors: list[PipelineError] = Field(default_factory=list)
    total_cost_usd: Optional[float] = None
