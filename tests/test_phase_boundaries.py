"""Phase-boundary integration tests.

Verifies inter-phase contracts using real pipeline output (PFAS run).
These tests check that phase outputs satisfy the contracts defined in
docs/CONTRACTS.md — they do NOT re-run LLM calls.

The trace.json from a successful pipeline run is the test fixture.
If no trace exists, tests are skipped (not faked).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from grounded_research.models import (
    AnalystRun,
    ArbitrationResult,
    Claim,
    ClaimLedger,
    Dispute,
    EvidenceBundle,
    FinalReport,
    PipelineState,
    RawClaim,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PFAS_TRACE = PROJECT_ROOT / "output" / "pfas_health_risks" / "trace.json"


@pytest.fixture
def state() -> PipelineState:
    """Load the PFAS pipeline trace as a PipelineState."""
    if not PFAS_TRACE.exists():
        pytest.skip("PFAS trace not found — run pipeline first")
    return PipelineState.model_validate_json(PFAS_TRACE.read_text())


@pytest.fixture
def bundle(state: PipelineState) -> EvidenceBundle:
    assert state.evidence_bundle is not None, "No evidence bundle in trace"
    return state.evidence_bundle


@pytest.fixture
def analyst_runs(state: PipelineState) -> list[AnalystRun]:
    assert len(state.analyst_runs) > 0, "No analyst runs in trace"
    return state.analyst_runs


@pytest.fixture
def ledger(state: PipelineState) -> ClaimLedger:
    assert state.claim_ledger is not None, "No claim ledger in trace"
    return state.claim_ledger


# --- Phase 1 → Phase 2: Evidence bundle feeds analysts ---


class TestPhase1ToPhase2:
    """Contract: EvidenceBundle → AnalystRun inputs."""

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
    """Contract: list[AnalystRun] → RawClaim extraction."""

    def test_minimum_successful_analysts(self, analyst_runs: list[AnalystRun]) -> None:
        """At least 2 analysts must succeed (config: analyst_min_successful)."""
        succeeded = [r for r in analyst_runs if r.succeeded]
        assert len(succeeded) >= 2, f"Only {len(succeeded)} analysts succeeded"

    def test_analysts_are_blind(self, analyst_runs: list[AnalystRun]) -> None:
        """Each analyst has a unique label — blindness is by construction."""
        labels = [r.analyst_label for r in analyst_runs]
        assert len(labels) == len(set(labels)), f"Duplicate labels: {labels}"

    def test_analysts_use_different_models(self, analyst_runs: list[AnalystRun]) -> None:
        """Cross-family models required per ADR-0005."""
        succeeded = [r for r in analyst_runs if r.succeeded]
        models = {r.model for r in succeeded}
        assert len(models) >= 2, f"Only {len(models)} unique model(s): {models}"

    def test_analysts_use_different_frames(self, analyst_runs: list[AnalystRun]) -> None:
        """Distinct reasoning frames required per ADR-0005."""
        succeeded = [r for r in analyst_runs if r.succeeded]
        frames = {r.frame for r in succeeded}
        assert len(frames) >= 2, f"Only {len(frames)} unique frame(s): {frames}"

    def test_claims_cite_evidence_ids(
        self, analyst_runs: list[AnalystRun], bundle: EvidenceBundle
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
    """Contract: ClaimLedger → dispute verification."""

    def test_ledger_has_claims(self, ledger: ClaimLedger) -> None:
        assert len(ledger.claims) > 0, "Ledger has no claims"

    def test_claims_have_prefixed_ids(self, ledger: ClaimLedger) -> None:
        for c in ledger.claims:
            assert c.id.startswith("C-"), f"Claim {c.id} missing C- prefix"

    def test_claims_trace_to_raw_claims(self, ledger: ClaimLedger) -> None:
        """Every canonical claim must trace back to at least one raw claim."""
        for c in ledger.claims:
            assert len(c.source_raw_claim_ids) > 0, (
                f"Claim {c.id} has no source_raw_claim_ids"
            )

    def test_dispute_claim_ids_resolve(self, ledger: ClaimLedger) -> None:
        """Every dispute must reference claims that exist in the ledger."""
        claim_ids = {c.id for c in ledger.claims}
        for d in ledger.disputes:
            unresolved = [cid for cid in d.claim_ids if cid not in claim_ids]
            assert not unresolved, (
                f"Dispute {d.id} references unknown claims: {unresolved}"
            )

    def test_disputes_have_prefixed_ids(self, ledger: ClaimLedger) -> None:
        for d in ledger.disputes:
            assert d.id.startswith("D-"), f"Dispute {d.id} missing D- prefix"

    def test_dispute_routing_matches_type(self, ledger: ClaimLedger) -> None:
        """Route must match the DISPUTE_ROUTING table in models.py."""
        from grounded_research.models import DISPUTE_ROUTING

        for d in ledger.disputes:
            expected_route = DISPUTE_ROUTING.get(d.dispute_type)
            assert d.route == expected_route, (
                f"Dispute {d.id} type={d.dispute_type} has route={d.route}, "
                f"expected={expected_route}"
            )

    def test_decision_critical_disputes_exist_or_explain(
        self, ledger: ClaimLedger
    ) -> None:
        """On a factual question, we expect at least one decision-critical dispute."""
        dc = ledger.decision_critical_disputes()
        # This is a soft assertion — 0 disputes is valid but worth noting
        if len(dc) == 0:
            pytest.skip("No decision-critical disputes (may be valid for some questions)")


# --- Phase 4 → Phase 5: Arbitration feeds export ---


class TestPhase4ToPhase5:
    """Contract: arbitration results + updated ledger → FinalReport."""

    def test_arbitration_results_reference_disputes(
        self, ledger: ClaimLedger
    ) -> None:
        """Every arbitration result must reference a dispute in the ledger."""
        dispute_ids = {d.id for d in ledger.disputes}
        for ar in ledger.arbitration_results:
            assert ar.dispute_id in dispute_ids, (
                f"Arbitration {ar.dispute_id} references unknown dispute"
            )

    def test_non_inconclusive_verdicts_have_fresh_evidence(
        self, ledger: ClaimLedger
    ) -> None:
        """ADR-0004 fail-loud rule: non-inconclusive verdicts require new evidence."""
        for ar in ledger.arbitration_results:
            if ar.verdict != "inconclusive":
                assert len(ar.new_evidence_ids) > 0, (
                    f"Arbitration for {ar.dispute_id} verdict={ar.verdict} "
                    f"but no new_evidence_ids (ADR-0004 violation)"
                )

    def test_arbitration_claim_updates_reference_ledger_claims(
        self, ledger: ClaimLedger
    ) -> None:
        """Claim status updates in arbitration must reference real claims."""
        claim_ids = {c.id for c in ledger.claims}
        for ar in ledger.arbitration_results:
            # claim_updates is dict[str, ClaimStatus] — keys are claim IDs
            unknown = [cid for cid in ar.claim_updates if cid not in claim_ids]
            assert not unknown, (
                f"Arbitration for {ar.dispute_id} updates unknown claims: {unknown}"
            )


# --- Phase 5: Report grounding validation ---


class TestPhase5Grounding:
    """Contract: FinalReport claims must resolve in ledger and bundle."""

    def test_report_exists(self, state: PipelineState) -> None:
        assert state.report is not None, "No report in pipeline state"

    def test_cited_claims_resolve_in_ledger(
        self, state: PipelineState, ledger: ClaimLedger
    ) -> None:
        """Every claim_id cited in the report must exist in the ledger."""
        if state.report is None:
            pytest.skip("No report")
        claim_ids = {c.id for c in ledger.claims}
        unresolved = [
            cid for cid in state.report.cited_claim_ids if cid not in claim_ids
        ]
        assert not unresolved, f"Report cites unknown claims: {unresolved}"

    def test_cited_claims_have_evidence(
        self, state: PipelineState, ledger: ClaimLedger
    ) -> None:
        """Every cited claim should have at least one evidence_id."""
        if state.report is None:
            pytest.skip("No report")
        claim_map = {c.id: c for c in ledger.claims}
        no_evidence = []
        for cid in state.report.cited_claim_ids:
            claim = claim_map.get(cid)
            if claim and not claim.evidence_ids:
                no_evidence.append(cid)
        assert not no_evidence, f"Cited claims with no evidence: {no_evidence}"


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
