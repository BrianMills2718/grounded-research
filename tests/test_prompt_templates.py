"""Structural tests for prompt template rendering.

These tests verify that the Jinja/YAML prompt surfaces used by the pipeline
render successfully with realistic minimal inputs after prompt-layer changes.
"""

from __future__ import annotations

from pathlib import Path

from llm_client import render_prompt


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"


def test_analyst_prompt_renders_with_source_metadata() -> None:
    """Analyst prompt should render with source metadata and evidence context."""
    messages = render_prompt(
        str(PROMPTS_DIR / "analyst.yaml"),
        question={
            "text": "Should we adopt tool X for a latency-sensitive service?",
            "time_sensitivity": "mixed",
            "scope_notes": "Assume a small engineering team.",
        },
        source_records=[
            {
                "id": "S-1",
                "title": "Official benchmark note",
                "quality_tier": "authoritative",
                "recency_score": 0.9,
            }
        ],
        evidence=[
            {
                "id": "E-1",
                "source_id": "S-1",
                "content_type": "text",
                "content": "Tool X handled 10k requests/second with p95 latency under 40ms.",
                "relevance_note": "Direct performance evidence.",
            }
        ],
        frame="verification_first",
        sub_questions=[],
        optimization_axes=[],
        ambiguous_terms=[],
    )

    assert len(messages) == 2
    assert "INDEPENDENCE PROTOCOL" in messages[0]["content"]
    assert "Source Records" in messages[1]["content"]
    assert "specific study, benchmark, organization, population, or numerical" in messages[1]["content"]


def test_dedup_prompt_renders_with_conservative_merge_rules() -> None:
    """Dedup prompt should include the non-merge safeguards."""
    messages = render_prompt(
        str(PROMPTS_DIR / "dedup.yaml"),
        raw_claims=[
            {
                "id": "RC-1",
                "statement": "Latency improved by 20% in the 2025 benchmark.",
                "confidence": "high",
                "evidence_ids": ["E-1"],
            },
            {
                "id": "RC-2",
                "statement": "Latency improved by 20% in the 2024 benchmark.",
                "confidence": "medium",
                "evidence_ids": ["E-2"],
            },
        ],
    )

    assert "Do NOT merge claims that differ in timeframe" in messages[0]["content"]
    assert "Every raw claim ID must appear in exactly one group" in messages[0]["content"]


def test_arbitration_prompt_renders_with_anti_conformity_basis_language() -> None:
    """Arbitration prompt should require explicit basis language."""
    messages = render_prompt(
        str(PROMPTS_DIR / "arbitration.yaml"),
        dispute={
            "id": "D-1",
            "dispute_type": "factual_conflict",
            "description": "Conflicting claims about benchmark throughput.",
        },
        claims=[
            {"id": "C-1", "statement": "Tool X reached 10k req/s.", "confidence": "high", "evidence_ids": ["E-1"]},
            {"id": "C-2", "statement": "Tool X did not exceed 7k req/s.", "confidence": "medium", "evidence_ids": ["E-2"]},
        ],
        evidence=[{"id": "E-1", "source_id": "S-1", "content": "Original benchmark summary."}],
        fresh_evidence=[{"id": "E-3", "source_id": "S-3", "content": "Fresh rerun benchmark with updated numbers."}],
    )

    assert "Anti-conformity rules" in messages[0]["content"]
    assert "new evidence" in messages[0]["content"]
    assert "corrected assumption" in messages[0]["content"]
    assert "resolved contradiction" in messages[0]["content"]
    assert "treat fresh evidence" in messages[1]["content"]
    assert "required basis" in messages[1]["content"]


def test_dispute_classify_prompt_renders_with_type_guidance() -> None:
    """Dispute classifier prompt should render with strengthened type guidance."""
    messages = render_prompt(
        str(PROMPTS_DIR / "dispute_classify.yaml"),
        claims=[
            {
                "id": "C-1",
                "statement": "Tool X is production-ready for small teams.",
                "confidence": "medium",
                "analyst_sources": ["Alpha"],
                "evidence_ids": ["E-1"],
            },
            {
                "id": "C-2",
                "statement": "Tool X is only suitable for experimentation.",
                "confidence": "medium",
                "analyst_sources": ["Beta"],
                "evidence_ids": ["E-2"],
            },
        ],
    )

    assert "Type guidance" in messages[0]["content"]
    assert "Do not create disputes for stylistic differences" in messages[0]["content"]
