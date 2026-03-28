"""Domain models for the grounded-research adjudication pipeline.

Every core entity in the system is defined here at field level. These models
serve as the single source of truth for:

- stage-boundary contracts (what flows between pipeline phases)
- notebook fixture shapes (what realistic test data looks like)
- structured-output schemas (what LLMs must return)
- trace serialization (what gets persisted on success or failure)

Design decisions:
- Prefixed IDs (S-, E-, A-, RC-, C-, D-, AR-) for human readability in traces.
- UUIDs for uniqueness; deterministic IDs only where content-addressability matters.
- Literal unions for small enum-like fields (Pydantic-native, no separate enum classes).
- Every model has a docstring explaining what it represents and why it exists.
- Fields use Field(description=...) where the name alone is ambiguous.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from grounded_research.tyler_v1_models import AnalysisObject as TylerAnalysisObject
from grounded_research.tyler_v1_models import ClaimExtractionResult as TylerClaimExtractionResult
from grounded_research.tyler_v1_models import DecompositionResult as TylerDecompositionResult
from grounded_research.tyler_v1_models import EvidencePackage as TylerEvidencePackage
from grounded_research.tyler_v1_models import VerificationResult as TylerVerificationResult
from grounded_research.tyler_v1_models import SynthesisReport as TylerSynthesisReport


# ---------------------------------------------------------------------------
# ID generation helpers
# ---------------------------------------------------------------------------

def _make_id(prefix: str) -> str:
    """Generate a prefixed short UUID (prefix + 8 hex chars)."""
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Enums as Literal unions
# ---------------------------------------------------------------------------

TimeSensitivity = Literal["stable", "mixed", "time_sensitive"]

SourceType = Literal[
    "government_db",
    "court_record",
    "news",
    "academic",
    "primary_document",
    "web_search",
    "social_media",
    "platform_transparency",
    "other",
]

QualityTier = Literal["authoritative", "reliable", "unknown", "unreliable"]

ClaimStatus = Literal[
    "initial",
    "supported",
    "revised",
    "refuted",
    "inconclusive",
]

DisputeType = Literal[
    "factual_conflict",
    "interpretive_conflict",
    "preference_conflict",
    "ambiguity",
]

DisputeRoute = Literal[
    "verify",       # factual — re-search and check
    "arbitrate",    # interpretive — LLM arbitration with evidence
    "surface",      # preference/ambiguity — surface to user, no auto-resolution in v1
]

DecompositionVerdict = Literal["proceed", "revise"]


class DecompositionValidation(BaseModel):
    """Validation of Tyler Stage 1 decomposition quality and coverage."""

    coverage_ok: bool = Field(description="Do the sub-questions collectively cover the full research question?")
    coverage_gaps: list[str] = Field(
        default_factory=list,
        description="Aspects of the question that no sub-question addresses.",
    )
    bias_flags: list[str] = Field(
        default_factory=list,
        description="Sub-questions with leading or directional framing that assumes an answer.",
    )
    granularity_issues: list[str] = Field(
        default_factory=list,
        description="Sub-questions that are too broad, too narrow, or redundant with each other.",
    )
    verdict: DecompositionVerdict = Field(
        description="proceed = decomposition is good enough. revise = re-decompose with guidance.",
    )
    revision_guidance: str = Field(
        default="",
        description="If verdict is revise, specific guidance on what to fix.",
    )
PipelinePhase = Literal[
    "init",
    "ingest",
    "analyze",
    "canonicalize",
    "adjudicate",
    "export",
    "complete",
    "failed",
]


# ---------------------------------------------------------------------------
# Evidence layer
# ---------------------------------------------------------------------------

class SourceRecord(BaseModel):
    """A document or API record from which evidence was extracted.

    Maps closely to research_v3's Source model to simplify ingest adapters.
    The key additions for grounded-research are quality_tier and recency_score,
    which feed into the recent-first evidence policy.
    """

    id: str = Field(default_factory=lambda: _make_id("S-"))
    url: str = Field(description="Primary locator — URL, filing reference, or citation string.")
    title: str = Field(default="", description="Human-readable title when available.")
    source_type: SourceType = "other"
    quality_tier: QualityTier = "unknown"
    published_at: datetime | None = Field(
        default=None,
        description="Publication date of the source material. None if unknown.",
    )
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this source was fetched or imported.",
    )
    recency_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Computed score combining age and quality_tier. 1.0 = most recent+authoritative.",
    )
    api_record_id: str | None = Field(
        default=None,
        description="Upstream record ID (e.g., USAspending award_id, Senate LDA filing UUID).",
    )
    upstream_source_id: str | None = Field(
        default=None,
        description="Original ID from the upstream system (e.g., research_v3 Source.id).",
    )


class EvidenceItem(BaseModel):
    """A discrete piece of evidence extracted from a source.

    One SourceRecord can produce multiple EvidenceItems (e.g., different
    passages or data points from the same document). Each item carries the
    extract text and a link back to its source.
    """

    id: str = Field(default_factory=lambda: _make_id("E-"))
    source_id: str = Field(description="FK to SourceRecord.id.")
    content: str = Field(description="The extracted text, data point, or quotation.")
    content_type: Literal["text", "data_point", "quotation", "summary"] = "text"
    relevance_note: str = Field(
        default="",
        description="Brief note on why this evidence is relevant to the research question.",
    )
    extraction_method: Literal["manual", "llm", "upstream"] = Field(
        default="upstream",
        description="How this evidence was extracted. 'upstream' = imported from research_v3 or similar.",
    )
    sub_question_ids: list[str] = Field(
        default_factory=list,
        description=(
            "SQ- IDs of the sub-questions whose search queries surfaced this evidence. "
            "Empty for non-decomposed runs."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_sub_question_field(cls, data: Any) -> Any:
        """Accept older traces that stored only one sub-question tag."""
        if not isinstance(data, dict):
            return data

        if "sub_question_ids" in data:
            return data

        legacy_id = data.get("sub_question_id")
        if legacy_id:
            upgraded = dict(data)
            upgraded["sub_question_ids"] = [legacy_id]
            return upgraded
        return data


class EvidenceBundle(BaseModel):
    """Container for all evidence associated with a research question.

    This is the primary input to the Analyze phase. It bundles the question
    context with normalized source records and evidence items, plus metadata
    about what's missing.
    """

    question: ResearchQuestion
    sources: list[SourceRecord] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    gaps: list[str] = Field(
        default_factory=list,
        description="Known evidence gaps — topics or sub-questions where evidence is weak or missing.",
    )
    imported_from: str | None = Field(
        default=None,
        description="Upstream system that produced this bundle (e.g., 'research_v3', 'manual').",
    )
    imported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def source_by_id(self, source_id: str) -> SourceRecord | None:
        """Look up a source record by ID. Returns None if not found."""
        return next((s for s in self.sources if s.id == source_id), None)

    def evidence_for_source(self, source_id: str) -> list[EvidenceItem]:
        """Return all evidence items linked to a given source."""
        return [e for e in self.evidence if e.source_id == source_id]


# ---------------------------------------------------------------------------
# Research question
# ---------------------------------------------------------------------------

class ResearchQuestion(BaseModel):
    """The normalized research question that drives the entire pipeline.

    Carries the raw question text plus metadata that influences evidence
    ranking (time_sensitivity) and scope bounding.
    """

    text: str = Field(description="The research question in natural language.")
    time_sensitivity: TimeSensitivity = "mixed"
    scope_notes: str = Field(
        default="",
        description="Optional constraints or context that bound the question's scope.",
    )
    key_entities: list[str] = Field(
        default_factory=list,
        description="Named entities central to the question (for evidence filtering).",
    )


# ---------------------------------------------------------------------------
# Analyst layer
# ---------------------------------------------------------------------------

class RawClaim(BaseModel):
    """A claim as extracted from a single analyst's output.

    This is the pre-deduplication form. Multiple RawClaims from different
    analysts may refer to the same underlying assertion — the Canonicalize
    phase merges them into canonical Claims.
    """

    id: str = Field(default_factory=lambda: _make_id("RC-"))
    statement: str = Field(
        description=(
            "The claim text. MUST include specific quantitative detail where "
            "available: numbers, percentages, sample sizes (N=), effect sizes, "
            "durations, study names. 'Weight loss of 3-8% over 8-12 weeks (N=150)' "
            "not 'weight loss was observed.'"
        ),
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Evidence items the analyst cited for this claim.",
    )
    confidence: Literal["high", "medium", "low"] = "medium"
    reasoning: str = Field(
        default="",
        description="The analyst's reasoning chain supporting this claim.",
    )


class Assumption(BaseModel):
    """An assumption surfaced by an analyst during reasoning.

    Assumptions are first-class objects so they can be tracked, challenged,
    and referenced in the final report. They are distinct from claims: a claim
    asserts something about the evidence; an assumption asserts something the
    analyst took as given.
    """

    id: str = Field(default_factory=lambda: _make_id("A-"))
    statement: str = Field(description="What the analyst assumed.")
    basis: str = Field(
        default="",
        description="Why the analyst considered this assumption reasonable.",
    )
    challenged: bool = Field(
        default=False,
        description="Whether another analyst or the arbitration phase challenged this.",
    )


class Recommendation(BaseModel):
    """A recommendation made by an analyst, grounded in their claims.

    Separated from claims because recommendations are prescriptive ('you should
    do X') while claims are descriptive ('the evidence shows Y').
    """

    statement: str = Field(description="The recommendation text.")
    supporting_claim_ids: list[str] = Field(
        default_factory=list,
        description="RawClaim IDs that support this recommendation.",
    )
    conditions: str = Field(
        default="",
        description="Conditions under which this recommendation holds.",
    )


class Counterargument(BaseModel):
    """A counterargument raised by an analyst against a potential conclusion.

    These help surface the strongest objections and prevent premature consensus.
    """

    target: str = Field(description="What this counterargument is directed against.")
    argument: str = Field(description="The counterargument itself.")
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Evidence items supporting the counterargument.",
    )


class Claim(BaseModel):
    """A canonical claim in the claim ledger.

    This is the post-deduplication form. Each Claim may have been derived from
    one or more RawClaims across analysts. It carries merged provenance and a
    mutable status that the Adjudicate phase can update.
    """

    id: str = Field(default_factory=lambda: _make_id("C-"))
    statement: str = Field(description="The canonical claim text after deduplication.")
    status: ClaimStatus = "initial"
    source_raw_claim_ids: list[str] = Field(
        description="RawClaim IDs that were merged into this canonical claim.",
    )
    analyst_sources: list[str] = Field(
        description="Analyst labels that produced raw claims merged into this one.",
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="All evidence items supporting this claim (merged across analysts).",
    )
    confidence: Literal["high", "medium", "low"] = "medium"
    status_reason: str = Field(
        default="",
        description="Why the claim has its current status (set during arbitration).",
    )


class Dispute(BaseModel):
    """A conflict between claims from different analysts.

    Disputes are the core signal of the adjudication layer. Each dispute
    links two or more claims that are in tension and carries a type that
    determines its routing.
    """

    id: str = Field(default_factory=lambda: _make_id("D-"))
    dispute_type: DisputeType
    route: DisputeRoute = Field(
        description="Deterministic routing assignment based on dispute_type.",
    )
    claim_ids: list[str] = Field(
        description="Canonical Claim IDs that are in conflict.",
        min_length=2,
    )
    description: str = Field(
        description="Human-readable description of the conflict.",
    )
    severity: Literal["decision_critical", "notable", "minor"] = "notable"
    resolved: bool = False
    resolution_summary: str = Field(
        default="",
        description="Summary of how this dispute was resolved (empty if unresolved).",
    )


class TylerDownstreamHandoff(BaseModel):
    """Canonical downstream artifact for the Tyler-native runtime.

    This handoff preserves adjudicated Tyler artifacts directly as the only
    shipped downstream export contract.
    """

    downstream_target: str = Field(
        default="onto-canon",
        description="Intended downstream consumer of this artifact.",
    )
    question: ResearchQuestion
    stage_2_evidence_package: TylerEvidencePackage
    stage_5_verification_result: TylerVerificationResult
    stage_6_synthesis_report: TylerSynthesisReport
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Pipeline state and trace
# ---------------------------------------------------------------------------

class PipelineWarning(BaseModel):
    """A non-fatal issue encountered during pipeline execution.

    Warnings are collected in the trace rather than swallowed silently.
    They do not abort the pipeline but must be visible in the final output.
    """

    phase: PipelinePhase
    code: str = Field(description="Machine-readable warning code (e.g., 'low_evidence_count').")
    message: str = Field(description="Human-readable description of the issue.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary context for debugging (e.g., counts, IDs, thresholds).",
    )


class PhaseTrace(BaseModel):
    """Trace record for a single pipeline phase execution.

    Captures timing, LLM call metadata, and the phase's output artifact
    for post-hoc inspection and debugging.
    """

    phase: PipelinePhase
    started_at: datetime
    completed_at: datetime | None = None
    succeeded: bool = False
    error: str | None = None
    llm_calls: int = 0
    llm_cost_usd: float = 0.0
    output_summary: str = Field(
        default="",
        description="Brief human-readable summary of what this phase produced.",
    )


class Stage3AttemptTrace(BaseModel):
    """Non-semantic observability record for one Tyler Stage 3 analyst attempt.

    This exists to preserve human-readable execution visibility after removing
    legacy analyst compatibility objects from canonical pipeline state. It is intentionally
    narrow: enough to inspect success/failure and output density, but not a
    second semantic Stage 3 contract.
    """

    analyst_label: str = Field(description="Human-readable analyst label, e.g. Alpha/Beta/Gamma.")
    model_alias: str = Field(description="Tyler Stage 3 anonymized alias, e.g. A/B/C.")
    model: str = Field(description="Concrete model used for the attempt.")
    frame: str = Field(description="Assigned reasoning frame for the attempt.")
    succeeded: bool = Field(description="Whether the Stage 3 attempt produced a valid AnalysisObject.")
    claim_count: int = Field(default=0, ge=0, description="Number of Tyler Stage 3 claims emitted.")
    error: str | None = Field(default=None, description="Error message for failed attempts.")
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PipelineState(BaseModel):
    """Top-level pipeline state — the trace artifact.

    This is serialized to trace.json on every run (including failed runs).
    It carries the full pipeline context: inputs, intermediate artifacts,
    final outputs, warnings, and per-phase execution traces.

    On failure, partially-populated fields remain — a failed run with a rich
    trace is more useful than no output at all.
    """

    # --- Metadata ---
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    current_phase: PipelinePhase = "init"
    success: bool = False

    # --- Inputs ---
    question: ResearchQuestion | None = None
    evidence_bundle: EvidenceBundle | None = None

    # --- Intermediate artifacts ---
    tyler_stage_1_result: TylerDecompositionResult | None = None
    tyler_stage_2_result: TylerEvidencePackage | None = None
    # Narrow observability-only trace for Stage 3 attempts. The semantic Stage 3
    # artifact is `tyler_stage_3_results`; this is only for debugging/summaries.
    stage3_attempts: list[Stage3AttemptTrace] = Field(default_factory=list)
    tyler_stage_3_alias_mapping: dict[str, str] = Field(default_factory=dict)
    tyler_stage_3_results: list[TylerAnalysisObject] = Field(default_factory=list)
    tyler_stage_4_result: TylerClaimExtractionResult | None = None
    tyler_stage_5_result: TylerVerificationResult | None = None

    # --- Outputs ---
    tyler_stage_6_result: TylerSynthesisReport | None = None
    tyler_handoff: TylerDownstreamHandoff | None = None

    # --- Observability ---
    user_guidance_notes: list[str] = Field(default_factory=list)
    phase_traces: list[PhaseTrace] = Field(default_factory=list)
    warnings: list[PipelineWarning] = Field(default_factory=list)

    def add_warning(self, phase: PipelinePhase, code: str, message: str, **context: Any) -> None:
        """Convenience method to append a pipeline warning."""
        self.warnings.append(
            PipelineWarning(phase=phase, code=code, message=message, context=context)
        )


# ---------------------------------------------------------------------------
# Dispute routing table
# ---------------------------------------------------------------------------

DISPUTE_ROUTING: dict[DisputeType, DisputeRoute] = {
    "factual_conflict": "verify",
    "interpretive_conflict": "arbitrate",
    "preference_conflict": "surface",
    "ambiguity": "surface",
}
"""Deterministic mapping from dispute type to resolution route.

This is code-owned, not LLM-owned. The LLM classifies the dispute type;
the routing table determines what happens next. In v1, 'surface' routes
are included in the report but not auto-resolved.
"""


# ---------------------------------------------------------------------------
# Forward-reference rebuilds
# ---------------------------------------------------------------------------

EvidenceBundle.model_rebuild()
PipelineState.model_rebuild()
