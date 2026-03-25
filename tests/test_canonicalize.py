"""Tests for claim extraction and claim canonicalization helpers."""

from __future__ import annotations

import pytest

from grounded_research.canonicalize import deduplicate_claims, extract_raw_claims
from grounded_research.models import (
    AnalystRun,
    Counterargument,
    EvidenceBundle,
    EvidenceItem,
    RawClaim,
    Recommendation,
    ResearchQuestion,
    SourceRecord,
)


@pytest.mark.asyncio
async def test_extract_raw_claims_uses_claim_extraction_with_valid_evidence_whitelist(monkeypatch: pytest.MonkeyPatch) -> None:
    """Claim extraction should expose the valid evidence whitelist in the prompt and output."""
    # mock-ok: LLM boundary is external; this test verifies local prompt wiring and post-processing.
    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models):
        assert task == "claim_extraction"
        assert "Analyst Claims" in messages[1]["content"]
        assert "Valid Evidence IDs" in messages[1]["content"]
        result = response_model(
            claims=[
                {
                    "statement": "The Finnish Basic Income Experiment (2017-2018, N=2,000) found no employment gain.",
                    "evidence_ids": ["E-1"],
                    "confidence": "high",
                    "reasoning": "Split from the analyst's broader summary claim.",
                }
            ]
        )
        return result, {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    bundle = EvidenceBundle(
        question=ResearchQuestion(text="Did the Finnish basic income trial improve employment?"),
        sources=[
            SourceRecord(
                id="S-1",
                url="https://example.com/finnish-trial",
                title="Finnish basic income report",
                quality_tier="authoritative",
            )
        ],
        evidence=[
            EvidenceItem(
                id="E-1",
                source_id="S-1",
                content="The trial found no statistically significant employment effect.",
                content_type="text",
            )
        ],
    )
    analyst_runs = [
        AnalystRun(
            analyst_label="Alpha",
            model="openrouter/openai/gpt-5-nano",
            frame="verification_first",
            claims=[
                RawClaim(
                    statement="Pilot programs show mixed labor-market effects.",
                    evidence_ids=["E-1"],
                    confidence="medium",
                )
            ],
            recommendations=[Recommendation(statement="Do not assume employment gains from UBI pilots.")],
            counterarguments=[Counterargument(target="recommendation", argument="The results may not generalize.", evidence_ids=["E-1"])],
            summary="The Finnish trial did not improve employment.",
        )
    ]

    raw_claims, claim_to_analyst = await extract_raw_claims(
        analyst_runs,
        bundle,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert len(raw_claims) == 1
    assert raw_claims[0].id.startswith("RC-")
    assert raw_claims[0].evidence_ids == ["E-1"]
    assert claim_to_analyst[raw_claims[0].id] == "Alpha"


@pytest.mark.asyncio
async def test_extract_raw_claims_drops_claims_without_any_valid_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claims that lose all evidence during cleanup must not enter the ledger."""
    # mock-ok: verifies local post-processing for ungrounded claim extraction output.
    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models):
        assert task == "claim_extraction"
        result = response_model(
            claims=[
                {
                    "statement": "Ungrounded synthesized claim about pilot design heterogeneity.",
                    "evidence_ids": [],
                    "confidence": "medium",
                    "reasoning": "This should be dropped because it cites no valid evidence items.",
                }
            ]
        )
        return result, {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    bundle = EvidenceBundle(
        question=ResearchQuestion(text="Do UBI pilots reduce workforce participation?"),
        sources=[
            SourceRecord(
                id="S-1",
                url="https://example.com/ubi",
                title="UBI paper",
                quality_tier="reliable",
            )
        ],
        evidence=[
            EvidenceItem(
                id="E-1",
                source_id="S-1",
                content="A valid evidence item exists, but the extracted claim does not cite it.",
                content_type="text",
            )
        ],
    )
    analyst_runs = [
        AnalystRun(
            analyst_label="Alpha",
            model="openrouter/openai/gpt-5-nano",
            frame="verification_first",
            claims=[
                RawClaim(
                    statement="Some pilots vary substantially in design.",
                    evidence_ids=["E-1"],
                    confidence="medium",
                )
            ],
            recommendations=[Recommendation(statement="Compare pilot designs before generalizing.")],
            counterarguments=[Counterargument(target="recommendation", argument="Design variation may still hide common effects.", evidence_ids=["E-1"])],
            summary="Pilot design varies substantially.",
        )
    ]

    raw_claims, claim_to_analyst = await extract_raw_claims(
        analyst_runs,
        bundle,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert raw_claims == []
    assert claim_to_analyst == {}


@pytest.mark.asyncio
async def test_extract_raw_claims_skips_failed_analysts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failed analyst runs should not trigger claim extraction calls."""
    # mock-ok: verifies no external LLM call occurs when all analysts failed.
    async def fake_acall_llm_structured(*args, **kwargs):  # pragma: no cover
        raise AssertionError("Should not call LLM for failed analysts")

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    bundle = EvidenceBundle(
        question=ResearchQuestion(text="Test question"),
        sources=[],
        evidence=[],
    )
    analyst_runs = [
        AnalystRun(
            analyst_label="Alpha",
            model="openrouter/openai/gpt-5-nano",
            frame="verification_first",
            error="rate limit",
        )
    ]

    raw_claims, claim_to_analyst = await extract_raw_claims(
        analyst_runs,
        bundle,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert raw_claims == []
    assert claim_to_analyst == {}


@pytest.mark.asyncio
async def test_dedup_retry_then_fallback_on_invalid_grouping(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid dedup output should retry once, then promote claims 1:1 on failure."""
    # mock-ok: verifies local retry/fallback control flow around the external LLM boundary.
    call_count = 0

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models):
        nonlocal call_count
        call_count += 1
        assert task == "claim_deduplication"
        if call_count == 1:
            return response_model(
                groups=[
                    {
                        "canonical_statement": "Merged claim",
                        "raw_claim_ids": ["RC-1", "RC-1"],
                        "confidence": "medium",
                    }
                ]
            ), {}
        return response_model(
            groups=[
                {
                    "canonical_statement": "Still invalid",
                    "raw_claim_ids": ["RC-unknown"],
                    "confidence": "medium",
                }
            ]
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    raw_claims = [
        RawClaim(id="RC-1", statement="Claim one", evidence_ids=["E-1"], confidence="high"),
        RawClaim(id="RC-2", statement="Claim two", evidence_ids=["E-2"], confidence="medium"),
    ]
    claim_to_analyst = {"RC-1": "Alpha", "RC-2": "Beta"}

    canonical_claims = await deduplicate_claims(
        raw_claims,
        claim_to_analyst,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert call_count == 2
    assert len(canonical_claims) == 2
    assert [claim.source_raw_claim_ids for claim in canonical_claims] == [["RC-1"], ["RC-2"]]


@pytest.mark.asyncio
async def test_dedup_retry_accepts_corrected_grouping(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid retry result should be accepted instead of triggering fallback."""
    # mock-ok: verifies local retry acceptance logic around the external LLM boundary.
    call_count = 0

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models):
        nonlocal call_count
        call_count += 1
        assert task == "claim_deduplication"
        if call_count == 1:
            return response_model(
                groups=[
                    {
                        "canonical_statement": "Incomplete grouping",
                        "raw_claim_ids": ["RC-1"],
                        "confidence": "medium",
                    }
                ]
            ), {}
        return response_model(
            groups=[
                {
                    "canonical_statement": "Merged claim",
                    "raw_claim_ids": ["RC-1", "RC-2"],
                    "confidence": "high",
                }
            ]
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    raw_claims = [
        RawClaim(id="RC-1", statement="Claim one", evidence_ids=["E-1"], confidence="high"),
        RawClaim(id="RC-2", statement="Claim one rephrased", evidence_ids=["E-2"], confidence="medium"),
    ]
    claim_to_analyst = {"RC-1": "Alpha", "RC-2": "Beta"}

    canonical_claims = await deduplicate_claims(
        raw_claims,
        claim_to_analyst,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert call_count == 2
    assert len(canonical_claims) == 1
    assert canonical_claims[0].source_raw_claim_ids == ["RC-1", "RC-2"]
    assert canonical_claims[0].analyst_sources == ["Alpha", "Beta"] or canonical_claims[0].analyst_sources == ["Beta", "Alpha"]
