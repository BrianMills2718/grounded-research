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


