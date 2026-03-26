"""Tests for claim extraction and claim canonicalization helpers."""

from __future__ import annotations

import asyncio

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
async def test_extract_raw_claims_respects_configured_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claim extraction fan-out should obey the configured concurrency cap."""
    active_calls = 0
    max_active_calls = 0

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models):
        nonlocal active_calls, max_active_calls
        assert task == "claim_extraction"
        active_calls += 1
        max_active_calls = max(max_active_calls, active_calls)
        await asyncio.sleep(0.01)
        active_calls -= 1
        return response_model(
            claims=[
                {
                    "statement": f"Extracted claim for {trace_id}",
                    "evidence_ids": ["E-1"],
                    "confidence": "medium",
                    "reasoning": "Concurrency test",
                }
            ]
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr(
        "grounded_research.canonicalize.get_phase_concurrency_config",
        lambda: {"claim_extraction_max_concurrency": 1},
    )

    bundle = EvidenceBundle(
        question=ResearchQuestion(text="Test question"),
        sources=[
            SourceRecord(
                id="S-1",
                url="https://example.com/source",
                title="Source",
                quality_tier="authoritative",
            )
        ],
        evidence=[
            EvidenceItem(
                id="E-1",
                source_id="S-1",
                content="Evidence content",
                content_type="text",
            )
        ],
    )
    analyst_runs = [
        AnalystRun(
            analyst_label=label,
            model="openrouter/openai/gpt-5-nano",
            frame="verification_first",
            claims=[
                RawClaim(
                    statement=f"Claim from {label}",
                    evidence_ids=["E-1"],
                    confidence="medium",
                )
            ],
            recommendations=[Recommendation(statement="Recommendation")],
            counterarguments=[Counterargument(target="recommendation", argument="Counter", evidence_ids=["E-1"])],
            summary=f"Summary {label}",
        )
        for label in ("Alpha", "Beta", "Gamma")
    ]

    raw_claims, claim_to_analyst = await extract_raw_claims(
        analyst_runs,
        bundle,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert len(raw_claims) == 3
    assert len(claim_to_analyst) == 3
    assert max_active_calls == 1


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


@pytest.mark.asyncio
async def test_dense_dedup_partitions_claims_into_similarity_buckets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dense claim sets should be deduped in smaller semantic buckets."""
    # mock-ok: verifies local staged-partition control flow around the external LLM boundary.
    bucket_calls: list[list[str]] = []

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models):
        assert task == "claim_deduplication"
        raw_claim_ids = []
        for message in messages:
            content = message.get("content", "")
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("### RC-"):
                    raw_claim_ids.append(stripped.removeprefix("### ").strip())
        bucket_calls.append(raw_claim_ids)

        if set(raw_claim_ids) == {"RC-1", "RC-2"}:
            return response_model(
                groups=[
                    {
                        "canonical_statement": "Finland's basic income trial showed no employment gain.",
                        "raw_claim_ids": ["RC-1", "RC-2"],
                        "confidence": "high",
                    }
                ]
            ), {}
        if set(raw_claim_ids) == {"RC-3", "RC-4"}:
            return response_model(
                groups=[
                    {
                        "canonical_statement": "Stockton's SEED pilot improved transitions into full-time work.",
                        "raw_claim_ids": ["RC-3", "RC-4"],
                        "confidence": "high",
                    }
                ]
            ), {}

        raise AssertionError(f"Unexpected dedup bucket: {raw_claim_ids}")

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr(
        "grounded_research.canonicalize.get_dedup_config",
        lambda: {
            "staged_trigger_claims": 4,
            "bucket_max_claims": 2,
            "max_doc_frequency_ratio": 0.8,
            "min_shared_informative_tokens": 1,
        },
    )

    raw_claims = [
        RawClaim(
            id="RC-1",
            statement="Finland basic income trial found no employment gain.",
            evidence_ids=["E-1"],
            confidence="high",
        ),
        RawClaim(
            id="RC-2",
            statement="The Finland basic income experiment showed no increase in employment.",
            evidence_ids=["E-2"],
            confidence="medium",
        ),
        RawClaim(
            id="RC-3",
            statement="Stockton SEED improved transitions into full-time work.",
            evidence_ids=["E-3"],
            confidence="high",
        ),
        RawClaim(
            id="RC-4",
            statement="The Stockton pilot increased full-time employment transitions for recipients.",
            evidence_ids=["E-4"],
            confidence="medium",
        ),
    ]
    claim_to_analyst = {
        "RC-1": "Alpha",
        "RC-2": "Beta",
        "RC-3": "Gamma",
        "RC-4": "Alpha",
    }

    canonical_claims = await deduplicate_claims(
        raw_claims,
        claim_to_analyst,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert len(bucket_calls) == 2
    assert {frozenset(call) for call in bucket_calls} == {
        frozenset({"RC-1", "RC-2"}),
        frozenset({"RC-3", "RC-4"}),
    }
    assert len(canonical_claims) == 2
    assert {frozenset(claim.source_raw_claim_ids) for claim in canonical_claims} == {
        frozenset({"RC-1", "RC-2"}),
        frozenset({"RC-3", "RC-4"}),
    }
