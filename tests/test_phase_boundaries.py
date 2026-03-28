"""Phase-boundary integration tests.

Verifies inter-phase contracts using a real Tyler-native pipeline trace.
These tests check that phase outputs satisfy the contracts defined in
docs/CONTRACTS.md — they do NOT re-run LLM calls.

The trace.json from a successful Tyler-native pipeline run is the fixture.
If no trace exists, tests are skipped (not faked).
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pytest

from grounded_research.models import (
    EvidenceBundle,
    EvidenceItem,
    PipelineState,
)
from grounded_research.tyler_v1_models import AnalysisObject

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TYLER_TRACE = PROJECT_ROOT / "output" / "tyler_literal_parity_ubi_reanchor_v8" / "trace.json"


@dataclass
class BoundaryClaim:
    """Minimal Stage 3 claim view for boundary assertions."""

    id: str
    statement: str
    evidence_ids: list[str]


@dataclass
class BoundaryAnalystRun:
    """Minimal analyst view rebuilt from canonical Tyler Stage 3 artifacts."""

    analyst_label: str
    model: str
    frame: str
    claims: list[BoundaryClaim]
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        """Mirror the shipped analyst success boolean for boundary checks."""
        return self.error is None


@pytest.fixture
def state() -> PipelineState:
    """Load the Tyler-native pipeline trace as a PipelineState.

    The canonical saved trace persists Tyler Stage 3 artifacts plus an execution
    trace. Older historical traces may still carry projected `analyst_runs`, but
    boundary checks rebuild their minimal analyst view from Tyler Stage 3 instead
    of treating that projection as canonical truth.
    """
    if not TYLER_TRACE.exists():
        pytest.skip("Tyler-native trace not found — run pipeline first")
    raw = json.loads(TYLER_TRACE.read_text())
    raw.pop("analyst_runs", None)
    return PipelineState.model_validate(raw)


@pytest.fixture
def bundle(state: PipelineState) -> EvidenceBundle:
    assert state.evidence_bundle is not None, "No evidence bundle in trace"
    return state.evidence_bundle


def _rebuild_boundary_analyst_runs(
    *,
    raw_trace: dict[str, object],
    bundle: EvidenceBundle,
) -> list[BoundaryAnalystRun]:
    """Rebuild analyst boundary views from canonical Tyler Stage 3 results."""
    source_to_evidence_ids: dict[str, list[str]] = {}
    for item in bundle.evidence:
        source_to_evidence_ids.setdefault(item.source_id, []).append(item.id)

    alias_mapping = raw_trace.get("tyler_stage_3_alias_mapping", {})
    raw_attempts = raw_trace.get("stage3_attempts", [])
    if raw_attempts:
        alias_to_attempt = {
            attempt["model_alias"]: attempt
            for attempt in raw_attempts
        }
    else:
        alias_to_attempt = {
            alias_mapping.get(run["analyst_label"], run["analyst_label"]): {
                "analyst_label": run["analyst_label"],
                "model": run["model"],
                "frame": run.get("frame"),
                "error": run.get("error"),
            }
            for run in raw_trace.get("analyst_runs", [])
        }

    rebuilt: list[BoundaryAnalystRun] = []
    for result_data in raw_trace.get("tyler_stage_3_results", []):
        analysis = AnalysisObject.model_validate(result_data)
        attempt = alias_to_attempt.get(analysis.model_alias)
        if attempt is None:
            continue
        claims = []
        for idx, claim in enumerate(analysis.claims, start=1):
            evidence_ids = []
            for source_id in claim.source_references:
                evidence_ids.extend(source_to_evidence_ids.get(source_id, [])[:2])
            claims.append(
                BoundaryClaim(
                    id=f"RC-{idx}",
                    statement=claim.statement,
                    evidence_ids=list(dict.fromkeys(evidence_ids)),
                )
            )
        rebuilt.append(
            BoundaryAnalystRun(
                analyst_label=attempt["analyst_label"],
                model=attempt["model"],
                frame=analysis.reasoning_frame,
                claims=claims,
                error=attempt.get("error"),
            )
        )
    return rebuilt


@pytest.fixture
def analyst_runs(bundle: EvidenceBundle) -> list[BoundaryAnalystRun]:
    """Load analyst boundary views from canonical Tyler Stage 3 artifacts."""
    raw = json.loads(TYLER_TRACE.read_text())
    rebuilt = _rebuild_boundary_analyst_runs(raw_trace=raw, bundle=bundle)
    assert len(rebuilt) > 0, "No Tyler Stage 3 analyst results in trace"
    return rebuilt


@pytest.fixture
def stage_4_result(state: PipelineState):
    assert state.tyler_stage_4_result is not None, "No Tyler Stage 4 result in trace"
    return state.tyler_stage_4_result


@pytest.fixture
def stage_5_result(state: PipelineState):
    assert state.tyler_stage_5_result is not None, "No Tyler Stage 5 result in trace"
    return state.tyler_stage_5_result


# --- Phase 1 → Phase 2: Evidence bundle feeds analysts ---


class TestPhase1ToPhase2:
    """Contract: EvidenceBundle feeds canonical Tyler Stage 3 analysis."""

    def test_bundle_has_question(self, bundle: EvidenceBundle) -> None:
        assert bundle.question.text, "Question text is empty"

    def test_bundle_has_sources(self, bundle: EvidenceBundle) -> None:
        assert len(bundle.sources) > 0, "No sources in bundle"

    def test_bundle_has_evidence(self, bundle: EvidenceBundle) -> None:
        assert len(bundle.evidence) > 0, "No evidence items in bundle"

    def test_evidence_source_ids_resolve(self, bundle: EvidenceBundle) -> None:
        """Every evidence item must reference a source that exists."""
        source_ids = {s.id for s in bundle.sources}
        orphans = [e.id for e in bundle.evidence if e.source_id not in source_ids]
        assert not orphans, f"Orphan evidence items: {orphans}"

    def test_source_ids_are_prefixed(self, bundle: EvidenceBundle) -> None:
        for s in bundle.sources:
            assert s.id.startswith("S-"), f"Source {s.id} missing S- prefix"

    def test_evidence_ids_are_prefixed(self, bundle: EvidenceBundle) -> None:
        for e in bundle.evidence:
            assert e.id.startswith("E-"), f"Evidence {e.id} missing E- prefix"


# --- Phase 2 → Phase 3a: Analysts feed claim extraction ---


class TestPhase2ToPhase3:
    """Contract: rebuilt Stage 3 analyst views → Tyler Stage 4 extraction."""

    def test_minimum_successful_analysts(self, analyst_runs: list[BoundaryAnalystRun]) -> None:
        """At least 2 analysts must succeed (config: analyst_min_successful)."""
        succeeded = [r for r in analyst_runs if r.succeeded]
        assert len(succeeded) >= 2, f"Only {len(succeeded)} analysts succeeded"

    def test_analysts_are_blind(self, analyst_runs: list[BoundaryAnalystRun]) -> None:
        """Each analyst has a unique label — blindness is by construction."""
        labels = [r.analyst_label for r in analyst_runs]
        assert len(labels) == len(set(labels)), f"Duplicate labels: {labels}"

    def test_analysts_use_different_models(self, analyst_runs: list[BoundaryAnalystRun]) -> None:
        """Cross-family models required per ADR-0005."""
        succeeded = [r for r in analyst_runs if r.succeeded]
        models = {r.model for r in succeeded}
        assert len(models) >= 2, f"Only {len(models)} unique model(s): {models}"

    def test_analysts_use_different_frames(self, analyst_runs: list[BoundaryAnalystRun]) -> None:
        """Distinct reasoning frames required per ADR-0005."""
        succeeded = [r for r in analyst_runs if r.succeeded]
        frames = {r.frame for r in succeeded}
        assert len(frames) >= 2, f"Only {len(frames)} unique frame(s): {frames}"

    def test_claims_cite_evidence_ids(
        self, analyst_runs: list[BoundaryAnalystRun], bundle: EvidenceBundle
    ) -> None:
        """Claims should reference evidence IDs from the bundle."""
        evidence_ids = {e.id for e in bundle.evidence}
        succeeded = [r for r in analyst_runs if r.succeeded]
        total_claims = sum(len(r.claims) for r in succeeded)
        assert total_claims > 0, "No claims produced by any analyst"

        # At least some claims should have evidence_ids that resolve
        claims_with_valid_refs = 0
        for run in succeeded:
            for claim in run.claims:
                if any(eid in evidence_ids for eid in claim.evidence_ids):
                    claims_with_valid_refs += 1
        assert claims_with_valid_refs > 0, "No claims reference valid evidence IDs"


# --- Phase 3 → Phase 4: Ledger feeds verification ---


class TestPhase3ToPhase4:
    """Contract: Tyler Stage 4 artifact → Tyler Stage 5 verification."""

    def test_stage4_has_claims(self, stage_4_result) -> None:
        assert len(stage_4_result.claim_ledger) > 0, "Tyler Stage 4 has no claims"

    def test_claims_have_prefixed_ids(self, stage_4_result) -> None:
        for c in stage_4_result.claim_ledger:
            assert c.id.startswith("C-"), f"Claim {c.id} missing C- prefix"

    def test_claims_reference_sources(self, stage_4_result) -> None:
        """Grounded Tyler Stage 4 claims should reference at least one source.

        Stage 4 can also carry explicit uncertainty-preserving claims
        (`insufficient_evidence` or `contested`) before Stage 5 resolves them.
        Those may legitimately have no source references.
        """
        for c in stage_4_result.claim_ledger:
            if c.status.value in {"insufficient_evidence", "contested"}:
                continue
            assert len(c.source_references) > 0, f"Claim {c.id} has no source_references"

    def test_dispute_claim_ids_resolve(self, stage_4_result) -> None:
        """Every Tyler dispute must reference claims that exist in the Stage 4 ledger."""
        claim_ids = {c.id for c in stage_4_result.claim_ledger}
        for d in stage_4_result.dispute_queue:
            unresolved = [cid for cid in d.claims_involved if cid not in claim_ids]
            assert not unresolved, (
                f"Dispute {d.id} references unknown claims: {unresolved}"
            )

    def test_disputes_have_prefixed_ids(self, stage_4_result) -> None:
        for d in stage_4_result.dispute_queue:
            assert d.id.startswith("D-"), f"Dispute {d.id} missing D- prefix"

    def test_decision_critical_disputes_have_stage5_routing(self, stage_4_result) -> None:
        """Decision-critical Tyler disputes should route into Stage 5 or explicit user input."""
        allowed = {"stage_5_evidence", "stage_5_arbitration", "stage_6_user_input"}
        for d in stage_4_result.dispute_queue:
            if d.decision_critical:
                assert d.resolution_routing in allowed, (
                    f"Dispute {d.id} has invalid routing {d.resolution_routing}"
                )

    def test_decision_critical_disputes_exist_or_explain(
        self, stage_4_result
    ) -> None:
        """On a factual question, we expect at least one decision-critical dispute."""
        dc = [d for d in stage_4_result.dispute_queue if d.decision_critical]
        # This is a soft assertion — 0 disputes is valid but worth noting
        if len(dc) == 0:
            pytest.skip("No decision-critical disputes (may be valid for some questions)")


# --- Phase 4 → Phase 5: Arbitration feeds export ---


class TestPhase4ToPhase5:
    """Contract: Stage 5 verification result remains structurally coherent."""

    def test_tyler_stage5_exists(self, stage_5_result) -> None:
        assert stage_5_result is not None

    def test_arbitration_results_reference_disputes(
        self, stage_4_result, stage_5_result
    ) -> None:
        """Every Tyler arbitration assessment must reference a Stage 4 dispute."""
        dispute_ids = {d.id for d in stage_4_result.dispute_queue}
        for ar in stage_5_result.disputes_investigated:
            assert ar.dispute_id in dispute_ids, (
                f"Arbitration {ar.dispute_id} references unknown dispute"
            )

    def test_non_inconclusive_verdicts_have_fresh_evidence(
        self, stage_5_result
    ) -> None:
        """Resolved Tyler disputes should have targeted additional sources."""
        additional_sources_by_dispute = {}
        for source in stage_5_result.additional_sources:
            additional_sources_by_dispute.setdefault(source.retrieved_for_dispute, []).append(source.source_id)
        for ar in stage_5_result.disputes_investigated:
            if ar.resolution.value != "evidence_insufficient":
                assert additional_sources_by_dispute.get(ar.dispute_id), (
                    f"Arbitration for {ar.dispute_id} resolved without additional sources"
                )

    def test_arbitration_claim_updates_reference_ledger_claims(
        self, stage_5_result
    ) -> None:
        """Tyler claim status updates in arbitration must reference real claims."""
        claim_ids = {c.id for c in stage_5_result.updated_claim_ledger}
        for ar in stage_5_result.disputes_investigated:
            unknown = [
                update.claim_id
                for update in ar.updated_claim_statuses
                if update.claim_id not in claim_ids
            ]
            assert not unknown, (
                f"Arbitration for {ar.dispute_id} updates unknown claims: {unknown}"
            )


# --- Phase 5: Report grounding validation ---


class TestPhase5Grounding:
    """Contract: Tyler Stage 6 claims must resolve in Tyler Stage 5 and bundle."""

    def test_tyler_stage6_exists(self, state: PipelineState) -> None:
        assert state.tyler_stage_6_result is not None, "No Tyler Stage 6 result in pipeline state"

    def test_cited_claims_resolve_in_ledger(
        self, state: PipelineState, stage_5_result
    ) -> None:
        """Every Tyler claim excerpt must exist in the Tyler Stage 5 ledger."""
        assert state.tyler_stage_6_result is not None
        claim_ids = {c.id for c in stage_5_result.updated_claim_ledger}
        unresolved = [
            excerpt.claim_id
            for excerpt in state.tyler_stage_6_result.claim_ledger_excerpt
            if excerpt.claim_id not in claim_ids
        ]
        assert not unresolved, f"Tyler Stage 6 cites unknown claims: {unresolved}"

    def test_cited_claims_have_evidence(
        self, state: PipelineState, stage_5_result
    ) -> None:
        """Every Tyler claim excerpt should map to a Stage 5 claim with source references."""
        assert state.tyler_stage_6_result is not None
        claim_map = {c.id: c for c in stage_5_result.updated_claim_ledger}
        no_evidence = []
        for excerpt in state.tyler_stage_6_result.claim_ledger_excerpt:
            claim = claim_map.get(excerpt.claim_id)
            if claim and not claim.source_references:
                no_evidence.append(excerpt.claim_id)
        assert not no_evidence, f"Tyler cited claims with no source references: {no_evidence}"


# --- Trace completeness ---


class TestTraceCompleteness:
    """Contract: PipelineState must capture full execution trace."""

    def test_phase_traces_cover_all_phases(self, state: PipelineState) -> None:
        """Every pipeline phase should have a trace entry."""
        phase_names = {t.phase for t in state.phase_traces}
        expected = {"ingest", "analyze", "canonicalize", "adjudicate", "export"}
        missing = expected - phase_names
        assert not missing, f"Missing phase traces: {missing}"

    def test_all_phases_have_timestamps(self, state: PipelineState) -> None:
        for t in state.phase_traces:
            assert t.started_at is not None, f"Phase {t.phase} missing started_at"
            assert t.completed_at is not None, f"Phase {t.phase} missing completed_at"

    def test_successful_run_is_marked_complete(self, state: PipelineState) -> None:
        if state.success:
            assert state.current_phase == "complete"

    def test_warnings_are_structured(self, state: PipelineState) -> None:
        """Warnings should have phase and code fields."""
        for w in state.warnings:
            assert w.phase, f"Warning missing phase: {w}"
            assert w.code, f"Warning missing code: {w}"
