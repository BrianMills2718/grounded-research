"""Structural tests for prompt template rendering.

These tests verify that the Jinja/YAML prompt surfaces used by the pipeline
render successfully with realistic minimal inputs after prompt-layer changes.
"""

from __future__ import annotations

from pathlib import Path

from llm_client import render_prompt


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"


def test_tyler_stage1_decompose_prompt_renders_literal_shared_protocol() -> None:
    """Tyler Stage 1 prompt should render the literal shared-output protocol."""
    messages = render_prompt(
        str(PROMPTS_DIR / "tyler_v1_decompose.yaml"),
        original_query="Should a city run a UBI pilot?",
        response_schema_json={"type": "object", "properties": {}},
    )

    assert "Return exactly one JSON object that validates against the provided response schema." in messages[0]["content"]
    assert "If information is insufficient, express that through the schema fields rather than guessing." in messages[0]["content"]
    assert "DECISION PROTOCOL (applies at every stage):" in messages[0]["content"]
    assert "REASONING REQUIREMENT:" in messages[0]["content"]
    assert "Original user query repeated for context anchoring:" in messages[1]["content"]


def test_tyler_stage2_query_diversification_prompt_renders_literal_contract() -> None:
    """Tyler Stage 2 query diversification prompt should render the literal query-role contract."""
    messages = render_prompt(
        str(PROMPTS_DIR / "tyler_v1_query_diversification.yaml"),
        sub_question={
            "question": "What do pilot results show about employment effects?",
            "search_guidance": "official evaluations, labor-force results, follow-up studies",
            "type": "empirical",
        },
    )

    assert "Each query variant must use a DIFFERENT retrieval strategy" in messages[0]["content"]
    assert "Do NOT use site: operators" in messages[0]["content"]
    assert "Generate exactly 3 search query variants for Tavily" in messages[1]["content"]
    assert "Additionally, generate 1 query variant for Exa" in messages[1]["content"]
    assert "SEMANTIC DESCRIPTION" in messages[1]["content"]


def test_tyler_stage2_extract_findings_prompt_renders_literal_shared_protocol() -> None:
    """Tyler Stage 2 extraction prompt should render the shared protocol minus unsupported reasoning text."""
    messages = render_prompt(
        str(PROMPTS_DIR / "tyler_v1_extract_findings.yaml"),
        original_query="Should a city run a UBI pilot?",
        sub_question_id="Q-1",
        sub_question_text="What happened in prior pilots?",
        source_title="Pilot report",
        source_url="https://example.com/report",
        source_type="academic",
        source_content="Recipients reported lower stress and similar labor participation.",
        response_schema_json={"type": "object", "properties": {}},
    )

    assert "Return exactly one JSON object that validates against the provided response schema." in messages[0]["content"]
    assert "Keep working notes internal. Output only locked structured results." in messages[0]["content"]
    assert "DECISION PROTOCOL (applies at every stage):" in messages[0]["content"]
    assert "REASONING REQUIREMENT:" not in messages[0]["content"]
    assert "Research question repeated for context anchoring:" in messages[1]["content"]


def test_tyler_analyst_prompt_renders_with_stage_inputs() -> None:
    """Tyler Stage 3 prompt should render with canonical Stage 1/2 inputs."""
    messages = render_prompt(
        str(PROMPTS_DIR / "tyler_v1_analyst.yaml"),
        original_query="Should we adopt tool X for a latency-sensitive service?",
        stage_1={
            "core_question": "Should we adopt tool X for a latency-sensitive service?",
            "sub_questions": [
                {
                    "id": "Q-1",
                    "question": "What do the performance benchmarks show?",
                    "type": "empirical",
                    "research_priority": "high",
                    "search_guidance": "benchmarks",
                }
            ],
            "optimization_axes": ["latency vs reliability"],
            "research_plan": {
                "what_to_verify": ["performance claims"],
                "critical_source_types": ["benchmarks"],
                "falsification_targets": ["contradictory benchmark"],
            },
            "stage_summary": {
                "stage_name": "Stage 1",
                "goal": "goal",
                "key_findings": ["k1", "k2", "k3"],
                "decisions_made": ["d1"],
                "outcome": "outcome",
                "reasoning": "reasoning",
            },
        },
        stage_2={
            "sub_question_evidence": [
                {
                    "sub_question_id": "Q-1",
                    "sources": [
                        {
                            "id": "S-1",
                            "url": "https://example.com/benchmark",
                            "title": "Official benchmark note",
                            "source_type": "official_docs",
                            "quality_score": 0.9,
                            "publication_date": "2026-01-01",
                            "retrieval_date": "2026-03-28",
                            "key_findings": [
                                {
                                    "finding": "Tool X handled 10k requests/second with p95 latency under 40ms.",
                                    "evidence_label": "vendor_documented",
                                    "original_quote": "Tool X handled 10k requests/second with p95 latency under 40ms.",
                                }
                            ],
                        }
                    ],
                    "meets_sufficiency": True,
                    "gap_description": None,
                }
            ],
            "total_queries_used": 3,
            "queries_per_sub_question": {"Q-1": 3},
            "stage_summary": {
                "stage_name": "Stage 2",
                "goal": "goal",
                "key_findings": ["k1", "k2", "k3"],
                "decisions_made": ["d1"],
                "outcome": "outcome",
                "reasoning": "reasoning",
            },
        },
        model_alias="A",
        reasoning_frame="verification_first",
        response_schema_json={"type": "object"},
    )

    assert len(messages) == 2
    assert "INDEPENDENCE PROTOCOL" in messages[0]["content"]
    assert "Your model alias: A" in messages[1]["content"]
    assert "DECOMPOSITION:" in messages[1]["content"]
    assert "EVIDENCE PACKAGE:" in messages[1]["content"]


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


def test_tyler_stage4_prompt_renders_with_literal_claimify_contract() -> None:
    """Tyler Stage 4 prompt should render the literal claim/dispute contract."""
    messages = render_prompt(
        str(PROMPTS_DIR / "tyler_v1_stage4.yaml"),
        original_query="Should cities adopt UBI pilots?",
        stage_1={"core_question": "Should cities adopt UBI pilots?"},
        stage_3_results=[
            {
                "model_alias": "A",
                "recommendation": "Run a bounded pilot.",
                "claims": [
                    {
                        "id": "C-1",
                        "statement": "Employment stayed flat in one pilot.",
                        "evidence_label": "empirically_observed",
                        "source_references": ["S-1"],
                    }
                ],
                "assumptions": [
                    {"id": "A-1", "statement": "The pilot population is relevant.", "if_wrong_impact": "Recommendation weakens."}
                ],
                "counter_argument": {"argument": "The evidence base is still narrow."},
                "falsification_conditions": ["A larger pilot shows harms."],
            },
            {
                "model_alias": "B",
                "recommendation": "Run a bounded pilot.",
                "claims": [
                    {
                        "id": "C-2",
                        "statement": "Recipients reported lower stress.",
                        "evidence_label": "empirically_observed",
                        "source_references": ["S-2"],
                    }
                ],
                "assumptions": [],
                "counter_argument": {"argument": "The labor effects remain mixed."},
                "falsification_conditions": ["A larger pilot shows labor harms."],
            },
        ],
        response_schema_json={"type": "object", "properties": {}},
    )

    assert "CONSERVATIVE DEDUPLICATION" in messages[0]["content"]
    assert "Classify each dispute into exactly one type" in messages[0]["content"]
    assert "ANALYST A's ANALYSIS" in messages[1]["content"]
    assert "Response schema" in messages[1]["content"]


def test_tyler_stage5_arbitration_prompt_renders_literal_contract() -> None:
    """Tyler Stage 5 arbitration prompt should render the literal dispute contract."""
    messages = render_prompt(
        str(PROMPTS_DIR / "tyler_v1_arbitration.yaml"),
        original_query="Should cities adopt UBI pilots?",
        dispute={
            "id": "D-1",
            "type": "empirical",
            "description": "Whether pilots changed employment.",
            "decision_critical_rationale": "Could change the recommendation.",
            "model_positions": [{"model_alias": "A", "position": "No labor harm."}],
        },
        claim_ledger=[
            {
                "id": "C-1",
                "statement": "Employment stayed flat.",
                "evidence_label": "empirically_observed",
                "source_references": ["S-1"],
                "supporting_models": ["A"],
                "contesting_models": ["B"],
            }
        ],
        relevant_original_sources=[
            {
                "id": "S-1",
                "title": "Pilot study",
                "source_type": "academic",
                "quality_score": 0.9,
                "key_findings": [{"finding": "Employment stayed flat.", "evidence_label": "empirically_observed"}],
            }
        ],
        new_evidence=[
            {
                "source_id": "S-99",
                "title": "Fresh follow-up",
                "quality_score": 0.8,
                "key_findings": ["A follow-up found no labor decline."],
            }
        ],
        response_schema_json={"type": "object", "properties": {}},
    )

    assert "ARBITRATION RULES" in messages[0]["content"]
    assert "ANTI-CONFORMITY RULE" in messages[0]["content"]
    assert "DISPUTE TO RESOLVE" in messages[1]["content"]
    assert "NEW EVIDENCE" in messages[1]["content"]


def test_tyler_stage6_synthesis_prompt_renders_literal_contract() -> None:
    """Tyler Stage 6 synthesis prompt should render the literal final-report contract."""
    messages = render_prompt(
        str(PROMPTS_DIR / "tyler_v1_synthesis.yaml"),
        original_query="Should cities adopt UBI pilots?",
        stage_6_user_input="Prefer lower downside risk.",
        decision_critical_claims=[
            {
                "id": "C-1",
                "statement": "Claim one.",
                "status": "verified",
                "evidence_label": "empirically_observed",
                "source_references": ["S-1"],
                "supporting_models": ["A"],
                "contesting_models": ["B"],
                "related_assumptions": ["A-1"],
            }
        ],
        noncritical_claims=[],
        assumption_set=[
            {
                "id": "A-1",
                "statement": "Assumption one.",
                "dependent_claims": ["C-1"],
                "if_wrong_impact": "Recommendation weakens.",
                "shared_across_models": True,
            }
        ],
        dispute_queue=[
            {
                "id": "D-1",
                "type": "interpretive",
                "description": "Interpretation conflict.",
                "status": "resolved",
                "resolution_details": "Resolved in Stage 5.",
                "remaining_uncertainty": "",
                "decision_critical": True,
                "decision_critical_rationale": "Changes answer.",
            }
        ],
        top_sources=[
            {
                "id": "S-1",
                "title": "Source one",
                "quality_score": 0.9,
                "source_type": "academic",
                "contribution_summary": "Supports C-1",
                "conflicts_resolved": ["D-1"],
            }
        ],
        evidence_gaps=["Need a longer follow-up."],
        all_stage_summaries=[
            {
                "stage_name": "Stage 1",
                "goal": "goal",
                "key_findings": ["k1", "k2"],
                "decisions_made": ["d1"],
                "outcome": "outcome",
                "reasoning": "reasoning",
            }
        ],
        response_schema_json={"type": "object", "properties": {}},
    )

    assert "SUBORDINATION PRINCIPLE" in messages[0]["content"]
    assert "PRIMARY OBLIGATION" in messages[0]["content"]
    assert "EVIDENCE LAUNDERING" in messages[0]["content"]
    assert "FALSE CONSENSUS" in messages[0]["content"]
    assert "CONDITIONS OF VALIDITY" in messages[0]["content"]
    assert "CLAIM LEDGER (decision-critical claims)" in messages[1]["content"]
    assert "KEY EVIDENCE SOURCES" in messages[1]["content"]
    assert "Original query repeated" in messages[1]["content"]


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
