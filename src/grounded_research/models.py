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

from pydantic import BaseModel, Field


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

QualityTier = Literal["authoritative", "reliable", "secondary", "unknown"]

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

ArbitrationVerdict = Literal[
    "supported",
    "revised",
    "refuted",
    "inconclusive",
]

SubQuestionType = Literal["factual", "causal", "comparative", "evaluative", "scope"]


class SubQuestion(BaseModel):
    """One dimension of a research question, typed for focused search and analysis."""

    id: str = Field(default_factory=lambda: _make_id("SQ-"))
    text: str = Field(description="The sub-question, phrased as a searchable question.")
    type: SubQuestionType = Field(
        description=(
            "What kind of question this is. Factual: what happened/exists. "
            "Causal: why/how something happened. Comparative: X vs Y. "
            "Evaluative: how good/effective. Scope: what's the boundary."
        ),
    )
    falsification_target: str = Field(
        description="What evidence would disprove or weaken the expected answer to this sub-question.",
    )


class QuestionDecomposition(BaseModel):
    """Structured decomposition of a research question into searchable sub-questions.

    Produced by the decomposition step before search and analysis.
    Drives per-sub-question search queries, analyst context, and synthesis structure.
    """

    core_question: str = Field(
        description="Precise reformulation of the user's raw question. Unambiguous and searchable.",
    )
    sub_questions: list[SubQuestion] = Field(
        description="2-6 typed sub-questions that collectively cover the full question.",
        min_length=2,
        max_length=6,
    )
    optimization_axes: list[str] = Field(
        description=(
            "2-4 key tradeoffs or dimensions a reader needs to evaluate. "
            "E.g., 'short-term revenue impact vs long-term structural change'."
        ),
        min_length=1,
        max_length=4,
    )
    research_plan: str = Field(
        description="Brief plan: what to search for, which source types matter most, what critical evidence to prioritize.",
    )


AnalystFrame = Literal[
    "verification_first",
    "structured_decomposition",
    "step_back_abstraction",
    "general",  # used in early slices before named frames are locked in
]

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
    statement: str = Field(description="The claim text as stated by the analyst.")
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


class AnalystRun(BaseModel):
    """The structured output from a single independent analyst pass.

    Each analyst receives the same ResearchQuestion + EvidenceBundle but uses
    a different reasoning frame. Analysts never see each other's outputs.
    """

    id: str = Field(default_factory=lambda: _make_id("AN-"))
    analyst_label: str = Field(description="Human-readable label (e.g., 'Alpha', 'Beta', 'Gamma').")
    frame: AnalystFrame = "general"
    model: str = Field(description="The LLM model used for this analyst run.")
    claims: list[RawClaim] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    counterarguments: list[Counterargument] = Field(default_factory=list)
    summary: str = Field(
        default="",
        description="The analyst's overall synthesis of the evidence.",
    )
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = Field(
        default=None,
        description="Non-None if the analyst run failed. Preserved for trace.",
    )

    @property
    def succeeded(self) -> bool:
        """Whether this analyst run completed without error."""
        return self.error is None


# ---------------------------------------------------------------------------
# Claim ledger
# ---------------------------------------------------------------------------

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


class ArbitrationResult(BaseModel):
    """The outcome of verifying or arbitrating a dispute.

    Produced by Phase 4 (Adjudicate). Each result references the dispute,
    the new evidence used, and the verdict that updates claim statuses.
    """

    id: str = Field(default_factory=lambda: _make_id("AR-"))
    dispute_id: str = Field(description="FK to Dispute.id.")
    verdict: ArbitrationVerdict
    new_evidence_ids: list[str] = Field(
        default_factory=list,
        description="Evidence items retrieved specifically for this arbitration.",
    )
    reasoning: str = Field(
        description="The arbitration reasoning chain.",
    )
    claim_updates: dict[str, ClaimStatus] = Field(
        default_factory=dict,
        description="Map of Claim.id → new ClaimStatus resulting from this arbitration.",
    )
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClaimLedger(BaseModel):
    """The canonical artifact of the grounded-research system.

    The claim ledger is the product. The report is a rendering of this state.
    It holds all canonical claims, disputes, and arbitration results, with
    full provenance back to analyst runs and evidence items.
    """

    claims: list[Claim] = Field(default_factory=list)
    disputes: list[Dispute] = Field(default_factory=list)
    arbitration_results: list[ArbitrationResult] = Field(default_factory=list)

    def claim_by_id(self, claim_id: str) -> Claim | None:
        """Look up a claim by ID."""
        return next((c for c in self.claims if c.id == claim_id), None)

    def disputes_for_claim(self, claim_id: str) -> list[Dispute]:
        """Return all disputes involving a given claim."""
        return [d for d in self.disputes if claim_id in d.claim_ids]

    def unresolved_disputes(self) -> list[Dispute]:
        """Return disputes that have not been resolved."""
        return [d for d in self.disputes if not d.resolved]

    def decision_critical_disputes(self) -> list[Dispute]:
        """Return unresolved disputes marked as decision-critical."""
        return [d for d in self.unresolved_disputes() if d.severity == "decision_critical"]


# ---------------------------------------------------------------------------
# Verification and handoff artifacts
# ---------------------------------------------------------------------------

class VerificationQueryBatch(BaseModel):
    """Search queries generated to investigate a single dispute.

    This is the contract between verification-query generation and the
    arbitration stage. It keeps the query set explicit in the trace so the
    project can inspect whether verification searched the right counterfactuals.
    """

    dispute_id: str = Field(description="FK to Dispute.id.")
    queries: list[str] = Field(
        default_factory=list,
        description="Search queries intended to gather fresh evidence for this dispute.",
        min_length=1,
    )
    rationale: str = Field(
        default="",
        description="Why these queries are expected to clarify the dispute.",
    )


class DownstreamHandoff(BaseModel):
    """The structured artifact passed to downstream systems such as onto-canon.

    This keeps the handoff format explicit instead of leaving it as an ad hoc
    JSON blob. It includes enough context to reconstruct claim provenance
    without re-reading the full pipeline trace.
    """

    downstream_target: str = Field(
        default="onto-canon",
        description="Intended downstream consumer of this artifact.",
    )
    question: ResearchQuestion
    claim_ledger: ClaimLedger
    sources: list[SourceRecord] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Export layer
# ---------------------------------------------------------------------------

class FinalReport(BaseModel):
    """The rendered output of the pipeline, grounded in the claim ledger.

    Synthesis must not invent structure absent from the ledger. Every
    recommendation must cite claim IDs; every cited claim must trace back
    to evidence.
    """

    title: str
    question: str = Field(description="The original research question text.")
    recommendation: str = Field(
        description=(
            "Primary recommendation grounded in the claim ledger. Must cite claim IDs "
            "(C-...) for every factual assertion. Structure around 2-4 key distinctions "
            "that organize the analysis. Explain the reasoning chain from evidence "
            "through claims to conclusion. Should be 400-800 words — substantive, not "
            "a summary."
        ),
    )
    alternatives: list[str] = Field(
        default_factory=list,
        description=(
            "Genuinely different courses of action or interpretations. Each alternative "
            "should explain when it would be the better choice and cite supporting claims."
        ),
    )
    disagreement_summary: str = Field(
        default="",
        description=(
            "Explain WHY analysts disagreed, not just which disputes exist. What "
            "underlying interpretive or factual differences drove the conflicts? How "
            "were they resolved (or not)? Reference dispute IDs (D-...) and claim IDs."
        ),
    )
    evidence_gaps: list[str] = Field(
        default_factory=list,
        description="Specific gaps in the evidence base that limit confidence in the recommendation.",
    )
    flip_conditions: list[str] = Field(
        default_factory=list,
        description=(
            "Concrete, testable conditions that would change the recommendation. "
            "Each should name what would change and how it would alter the conclusion."
        ),
    )
    cited_claim_ids: list[str] = Field(
        default_factory=list,
        description="All claim IDs referenced in the report. Used for grounding validation.",
    )
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
    analyst_runs: list[AnalystRun] = Field(default_factory=list)
    claim_ledger: ClaimLedger | None = None

    # --- Outputs ---
    report: FinalReport | None = None

    # --- Observability ---
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
DownstreamHandoff.model_rebuild()
PipelineState.model_rebuild()
