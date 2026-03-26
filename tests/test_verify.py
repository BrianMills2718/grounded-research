"""Tests for arbitration protocol enforcement and verification wiring.

These tests exercise the local anti-conformity validation layer around
arbitration output. The LLM boundary is mocked elsewhere; here we verify that
live claim-status changes only survive when they are tied to structured fresh
evidence support.
"""

from __future__ import annotations

import json

import pytest

from grounded_research.models import (
    ArbitrationResult,
    Claim,
    ClaimLedger,
    ClaimUpdate,
    Dispute,
    EvidenceBundle,
    EvidenceItem,
    ResearchQuestion,
    SourceRecord,
    VerificationQueryBatch,
)
from grounded_research.verify import (
    _collect_fresh_evidence_for_dispute,
    _enforce_arbitration_protocol,
    arbitrate_dispute,
    verify_disputes,
)


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


@pytest.mark.asyncio
async def test_collect_fresh_evidence_uses_verification_search_trace_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verification-time search should propagate trace metadata for observability."""
    captured: dict[str, str | None] = {}

    async def fake_search_web(query: str, count: int = 10, freshness: str = "none", *, trace_id=None, task=None):
        captured["trace_id"] = trace_id
        captured["task"] = task
        return json.dumps({"results": []})

    monkeypatch.setattr("grounded_research.tools.brave_search.search_web", fake_search_web)

    dispute = _make_dispute(["C-1", "C-2"])
    bundle = EvidenceBundle(
        question=ResearchQuestion(text="What is the evidence?"),
        sources=[],
        evidence=[],
        gaps=[],
    )

    _sources, _evidence, warnings = await _collect_fresh_evidence_for_dispute(
        dispute=dispute,
        queries=["test query"],
        bundle=bundle,
        trace_id="trace-root",
    )

    assert captured["trace_id"] == "trace-root/search/D-1"
    assert captured["task"] == "verification.search"
    assert any(w.code == "verification_no_results" for w in warnings)


@pytest.mark.asyncio
async def test_verify_disputes_retries_inconclusive_rounds_until_resolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deep modes should take another round when the first arbitration is inconclusive."""
    monkeypatch.setattr("grounded_research.verify.get_depth_config", lambda: {"arbitration_max_rounds": 2})

    query_calls: list[str] = []
    arbitration_calls: list[str] = []

    async def fake_generate_verification_queries(disputes, claims, trace_id, question_text="", max_budget=1.0):
        query_calls.append(trace_id)
        return [VerificationQueryBatch(dispute_id=disputes[0].id, queries=[f"query-{len(query_calls)}"])]

    async def fake_collect_fresh_evidence_for_dispute(dispute, queries, bundle, trace_id):
        round_idx = len(query_calls)
        source = SourceRecord(url=f"https://example.com/{round_idx}", title=f"Round {round_idx}")
        evidence = EvidenceItem(
            source_id=source.id,
            content=f"Fresh evidence round {round_idx}",
            content_type="text",
            relevance_note="fresh",
            extraction_method="llm",
        )
        return [source], [evidence], []

    async def fake_arbitrate_dispute(dispute, claims, available_evidence, fresh_evidence, trace_id, max_budget=1.0):
        arbitration_calls.append(trace_id)
        if len(arbitration_calls) == 1:
            return ArbitrationResult(
                dispute_id=dispute.id,
                verdict="inconclusive",
                new_evidence_ids=[],
                reasoning="Still mixed after round one.",
                claim_updates=[],
            )
        return ArbitrationResult(
            dispute_id=dispute.id,
            verdict="supported",
            new_evidence_ids=[fresh_evidence[-1].id],
            reasoning="Round two resolves the conflict.",
            claim_updates=[
                ClaimUpdate(
                    claim_id="C-1",
                    new_status="supported",
                    basis_type="new_evidence",
                    cited_evidence_ids=[fresh_evidence[-1].id],
                    justification="Fresh round-two evidence resolves the claim.",
                )
            ],
        )

    monkeypatch.setattr("grounded_research.verify.generate_verification_queries", fake_generate_verification_queries)
    monkeypatch.setattr("grounded_research.verify._collect_fresh_evidence_for_dispute", fake_collect_fresh_evidence_for_dispute)
    monkeypatch.setattr("grounded_research.verify.arbitrate_dispute", fake_arbitrate_dispute)

    ledger = ClaimLedger(
        claims=[_make_claim("C-1"), _make_claim("C-2")],
        disputes=[_make_dispute(["C-1", "C-2"])],
        arbitration_results=[],
    )
    bundle = EvidenceBundle(
        question=ResearchQuestion(text="What is the evidence?"),
        sources=[],
        evidence=[],
        gaps=[],
    )

    updated_ledger, results, warnings, llm_calls = await verify_disputes(
        ledger=ledger,
        bundle=bundle,
        trace_id="trace-root",
        max_disputes=1,
        max_budget=2.0,
    )

    assert len(query_calls) == 2
    assert len(arbitration_calls) == 2
    assert llm_calls == 4
    assert results[0].verdict == "supported"
    assert updated_ledger.disputes[0].resolved is True
    assert updated_ledger.claims[0].status == "supported"
    assert warnings == []


@pytest.mark.asyncio
async def test_verify_disputes_stops_after_first_resolved_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolved first-round disputes should not consume extra configured rounds."""
    monkeypatch.setattr("grounded_research.verify.get_depth_config", lambda: {"arbitration_max_rounds": 3})

    query_calls = 0
    arbitration_calls = 0

    async def fake_generate_verification_queries(disputes, claims, trace_id, question_text="", max_budget=1.0):
        nonlocal query_calls
        query_calls += 1
        return [VerificationQueryBatch(dispute_id=disputes[0].id, queries=["query-1"])]

    async def fake_collect_fresh_evidence_for_dispute(dispute, queries, bundle, trace_id):
        source = SourceRecord(url="https://example.com/1", title="Round 1")
        evidence = EvidenceItem(
            source_id=source.id,
            content="Fresh evidence round 1",
            content_type="text",
            relevance_note="fresh",
            extraction_method="llm",
        )
        return [source], [evidence], []

    async def fake_arbitrate_dispute(dispute, claims, available_evidence, fresh_evidence, trace_id, max_budget=1.0):
        nonlocal arbitration_calls
        arbitration_calls += 1
        return ArbitrationResult(
            dispute_id=dispute.id,
            verdict="refuted",
            new_evidence_ids=[fresh_evidence[-1].id],
            reasoning="Round one resolves the conflict immediately.",
            claim_updates=[
                ClaimUpdate(
                    claim_id="C-1",
                    new_status="refuted",
                    basis_type="new_evidence",
                    cited_evidence_ids=[fresh_evidence[-1].id],
                    justification="Fresh round-one evidence refutes the claim.",
                )
            ],
        )

    monkeypatch.setattr("grounded_research.verify.generate_verification_queries", fake_generate_verification_queries)
    monkeypatch.setattr("grounded_research.verify._collect_fresh_evidence_for_dispute", fake_collect_fresh_evidence_for_dispute)
    monkeypatch.setattr("grounded_research.verify.arbitrate_dispute", fake_arbitrate_dispute)

    ledger = ClaimLedger(
        claims=[_make_claim("C-1"), _make_claim("C-2")],
        disputes=[_make_dispute(["C-1", "C-2"])],
        arbitration_results=[],
    )
    bundle = EvidenceBundle(
        question=ResearchQuestion(text="What is the evidence?"),
        sources=[],
        evidence=[],
        gaps=[],
    )

    updated_ledger, results, warnings, llm_calls = await verify_disputes(
        ledger=ledger,
        bundle=bundle,
        trace_id="trace-root",
        max_disputes=1,
        max_budget=2.0,
    )

    assert query_calls == 1
    assert arbitration_calls == 1
    assert llm_calls == 2
    assert results[0].verdict == "refuted"
    assert updated_ledger.disputes[0].resolved is True
    assert updated_ledger.claims[0].status == "refuted"
    assert warnings == []
