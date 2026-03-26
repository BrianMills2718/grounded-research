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
        claim_target=8,
        source_count=1,
        evidence_count=1,
        coverage_retry_note="",
    )

    assert len(messages) == 2
    assert "INDEPENDENCE PROTOCOL" in messages[0]["content"]
    assert "Source Records" in messages[1]["content"]
    assert "specific study, benchmark, organization, population, or numerical" in messages[1]["content"]
    assert "approximately 8 distinct evidence-backed claims" in messages[1]["content"]


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


def test_claimify_prompt_renders_with_atomic_extraction_rules() -> None:
    """Claimify prompt should render with atomization and lineage rules."""
    messages = render_prompt(
        str(PROMPTS_DIR / "claimify.yaml"),
        analyst_label="Alpha",
        analyst_summary="The benchmark result is mixed.",
        analyst_claims=[
            {
                "id": "RC-source-1",
                "statement": "Tool X is faster than Tool Y but has higher memory usage.",
                "confidence": "medium",
                "evidence_ids": ["E-1"],
            }
        ],
        assumptions=[],
        recommendations=[],
        counterarguments=[],
        source_records=[
            {
                "id": "S-1",
                "title": "Benchmark report",
                "quality_tier": "reliable",
                "recency_score": 0.7,
            }
        ],
        evidence=[
            {
                "id": "E-1",
                "source_id": "S-1",
                "content_type": "text",
                "content": "Tool X beat Tool Y by 20% but used 2x the memory.",
            }
        ],
        valid_evidence_ids=["E-1"],
    )

    assert "atomize compound claims into single assertions" in messages[0]["content"]
    assert "Do not invent new evidence IDs" in messages[0]["content"]
    assert "Never emit source IDs" in messages[0]["content"]
    assert "Analyst Claims" in messages[1]["content"]
    assert "Valid Evidence IDs" in messages[1]["content"]


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
    assert "`claim_updates` is a list of structured objects" in messages[0]["content"]
    assert "cited_evidence_ids" in messages[0]["content"]
    assert "justification" in messages[0]["content"]
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


def test_query_generation_prompt_renders_sub_question_mode() -> None:
    """Query-generation prompt should render the sub-question contract via YAML."""
    messages = render_prompt(
        str(PROMPTS_DIR / "query_generation.yaml"),
        mode="sub_question",
        question="What is the evidence on Universal Basic Income and labor outcomes?",
        topic_anchors=["Universal Basic Income", "UBI"],
        sub_question={
            "type": "comparative",
            "text": "How do labor effects vary across pilots?",
            "falsification_target": "Evidence showing no meaningful variation.",
        },
        recency_note="Include the current year in at least half the queries.",
        query_count=4,
    )

    assert "keep every query explicitly anchored to the parent topic" in messages[0]["content"]
    assert "generate exactly 4 queries" in messages[0]["content"]
    assert "Required topic anchors" in messages[1]["content"]
    assert "Universal Basic Income" in messages[1]["content"]


def test_source_scoring_prompt_renders_yaml_template() -> None:
    """Source-scoring prompt should render from prompt data, not inline strings."""
    messages = render_prompt(
        str(PROMPTS_DIR / "source_scoring.yaml"),
        source_lines=[
            "- S-1: National Bureau of Economic Research | https://nber.org/paper",
            "- S-2: Personal blog | https://example.com/post",
        ],
    )

    assert "Assign each source one quality tier" in messages[0]["content"]
    assert "Score the quality of each source" in messages[1]["content"]
    assert "S-1" in messages[1]["content"]


def test_synthesis_prompt_renders_with_repair_feedback() -> None:
    """Structured synthesis prompt should render repair feedback when provided."""
    messages = render_prompt(
        str(PROMPTS_DIR / "synthesis.yaml"),
        question={"text": "What is the evidence?"},
        evidence=[],
        claims=[],
        disputes=[],
        arbitration_results=[],
        evidence_gaps=[],
        validation_feedback=["Unresolved dispute D-1 not mentioned in report"],
        synthesis_evidence_cap=30,
        structured_content_truncation_chars=500,
    )

    assert "Repair Feedback" in messages[1]["content"]
    assert "D-1" in messages[1]["content"]


def test_long_report_prompt_renders_with_placeholder_ban_and_repair_feedback() -> None:
    """Long-report prompt should forbid placeholders and accept repair feedback."""
    messages = render_prompt(
        str(PROMPTS_DIR / "long_report.yaml"),
        question={"text": "What is the evidence?", "scope_notes": ""},
        sources=[],
        evidence=[],
        claims=[],
        disputes=[],
        arbitration_results=[],
        evidence_gaps=[],
        analyst_count=3,
        synthesis_mode="analytical",
        word_target="5,000-6,000",
        sub_questions=[],
        optimization_axes=[],
        repair_feedback=["Remove symbolic placeholder token matching `X-Y%?`."],
        long_report_content_truncation_chars=400,
    )

    assert "Never use symbolic placeholders" in messages[0]["content"]
    assert "Comparative evidence table" in messages[0]["content"]
    assert "Reconciling the apparent contradictions" in messages[0]["content"]
    assert "Repair Feedback" in messages[1]["content"]


def test_long_report_prompt_renders_section_mode() -> None:
    """Long-report prompt should support the sectioned synthesis mode."""
    messages = render_prompt(
        str(PROMPTS_DIR / "long_report.yaml"),
        question={"text": "What is the evidence?", "scope_notes": ""},
        sources=[],
        evidence=[],
        claims=[],
        disputes=[],
        arbitration_results=[],
        evidence_gaps=[],
        analyst_count=3,
        synthesis_mode="analytical",
        word_target="10,000-15,000",
        sub_questions=[],
        optimization_axes=[],
        repair_feedback=[],
        section_mode=True,
        section_kind="distinction",
        section_title="Fiscal feasibility versus labor response",
        section_brief="Analyze the distinction in depth.",
        section_position=2,
        section_count=5,
        long_report_content_truncation_chars=400,
    )

    assert "Section Mode" in messages[0]["content"]
    assert "kind: distinction" in messages[0]["content"]
    assert "Write only this section of the larger report." in messages[1]["content"]
