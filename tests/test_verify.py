"""Tests for arbitration protocol enforcement.

These tests exercise the local anti-conformity validation layer around
arbitration output. The LLM boundary is mocked elsewhere; here we verify that
live claim-status changes only survive when they are tied to structured fresh
evidence support.
"""

from __future__ import annotations

import pytest

from grounded_research.models import ArbitrationResult, Claim, ClaimUpdate, Dispute
from grounded_research.verify import _enforce_arbitration_protocol, arbitrate_dispute


def _make_claim(claim_id: str) -> Claim:
    """Create a minimal canonical claim for verification tests."""
    return Claim(
        id=claim_id,
        statement=f"Claim {claim_id}",
        source_raw_claim_ids=[f"RC-{claim_id}"],
        analyst_sources=["Alpha"],
        evidence_ids=["E-base"],
        confidence="medium",
    )


def _make_dispute(claim_ids: list[str]) -> Dispute:
    """Create a minimal dispute covering the supplied claims."""
    return Dispute(
        id="D-1",
        dispute_type="factual_conflict",
        route="verify",
        claim_ids=claim_ids,
        description="Conflicting evidence about the same factual question.",
        severity="decision_critical",
    )


def test_enforce_arbitration_protocol_demotes_invalid_claim_updates() -> None:
    """Non-inconclusive verdicts without valid structured updates must fail loud."""
    dispute = _make_dispute(["C-1", "C-2"])
    claim_map = {"C-1": _make_claim("C-1"), "C-2": _make_claim("C-2")}
    result = ArbitrationResult(
        dispute_id=dispute.id,
        verdict="supported",
        new_evidence_ids=["E-fresh"],
        reasoning="Fresh evidence supposedly supports the claim.",
        claim_updates=[
            ClaimUpdate(
                claim_id="C-1",
                new_status="supported",
                basis_type="new_evidence",
                cited_evidence_ids=["E-not-fresh"],
                justification="This should be rejected because it cites the wrong evidence.",
            )
        ],
    )

    cleaned, warnings = _enforce_arbitration_protocol(
        dispute=dispute,
        result=result,
        claim_map=claim_map,
        fresh_evidence_ids={"E-fresh"},
    )

    assert cleaned.verdict == "inconclusive"
    assert cleaned.claim_updates == []
    warning_codes = {warning.code for warning in warnings}
    assert "verification_claim_update_missing_fresh_evidence" in warning_codes
    assert "verification_no_valid_claim_updates" in warning_codes


def test_enforce_arbitration_protocol_keeps_valid_updates() -> None:
    """Valid structured updates tied to fresh evidence should survive."""
    dispute = _make_dispute(["C-1", "C-2"])
    claim_map = {"C-1": _make_claim("C-1"), "C-2": _make_claim("C-2")}
    result = ArbitrationResult(
        dispute_id=dispute.id,
        verdict="revised",
        new_evidence_ids=["E-fresh", "E-stale"],
        reasoning="Fresh evidence narrows the claim.",
        claim_updates=[
            ClaimUpdate(
                claim_id="C-1",
                new_status="revised",
                basis_type="resolved_contradiction",
                cited_evidence_ids=["E-fresh", "E-stale"],
                justification="The fresh rerun resolves the earlier contradiction by narrowing the claim scope.",
            )
        ],
    )

    cleaned, warnings = _enforce_arbitration_protocol(
        dispute=dispute,
        result=result,
        claim_map=claim_map,
        fresh_evidence_ids={"E-fresh"},
    )

    assert cleaned.verdict == "revised"
    assert cleaned.new_evidence_ids == ["E-fresh"]
    assert len(cleaned.claim_updates) == 1
    assert cleaned.claim_updates[0].cited_evidence_ids == ["E-fresh"]
    assert warnings == []


def test_arbitration_result_accepts_legacy_dict_claim_updates() -> None:
    """Historical traces using dict claim_updates should still parse."""
    result = ArbitrationResult.model_validate(
        {
            "dispute_id": "D-legacy",
            "verdict": "revised",
            "new_evidence_ids": ["E-1"],
            "reasoning": "Legacy trace payload.",
            "claim_updates": {"C-1": "revised"},
        }
    )

    assert len(result.claim_updates) == 1
    assert result.claim_updates[0].claim_id == "C-1"
    assert result.claim_updates[0].new_status == "revised"


@pytest.mark.asyncio
async def test_arbitrate_dispute_passes_configured_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Arbitration calls should use the configured finite request timeout."""
    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
        assert task == "dispute_arbitration"
        assert timeout == 240
        return response_model(
            verdict="inconclusive",
            new_evidence_ids=[],
            reasoning="No fresh evidence materially changed the claim.",
            claim_updates=[],
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    dispute = _make_dispute(["C-1", "C-2"])
    claims = [_make_claim("C-1"), _make_claim("C-2")]
    evidence = []

    result = await arbitrate_dispute(
        dispute=dispute,
        claims=claims,
        available_evidence=evidence,
        fresh_evidence=evidence,
        trace_id="trace-1",
        max_budget=0.5,
    )

    assert result.verdict == "inconclusive"
