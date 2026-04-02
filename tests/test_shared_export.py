"""Tests for the shared_export module (epistemic-contracts bridge)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from grounded_research.shared_export import load_handoff_claims


_HANDOFF_DIR = Path(__file__).parent.parent / "output" / "eu_russia_sanctions"
_HANDOFF_PATH = _HANDOFF_DIR / "handoff.json"


@pytest.mark.skipif(
    not _HANDOFF_PATH.exists(),
    reason="EU Russia sanctions handoff not available",
)
class TestLoadHandoffClaims:
    """Test load_handoff_claims against the real EU sanctions handoff."""

    def test_loads_all_claims(self) -> None:
        claims = load_handoff_claims(_HANDOFF_PATH)
        assert len(claims) == 8

    def test_claim_has_statement(self) -> None:
        claims = load_handoff_claims(_HANDOFF_PATH)
        assert all(c.statement for c in claims)

    def test_claim_has_confidence(self) -> None:
        claims = load_handoff_claims(_HANDOFF_PATH)
        assert all(c.confidence is not None for c in claims)
        scores = {c.confidence.score for c in claims}
        # EU sanctions has high (0.8) and medium (0.5) confidence
        assert 0.8 in scores
        assert 0.5 in scores

    def test_claim_has_source_system(self) -> None:
        claims = load_handoff_claims(_HANDOFF_PATH)
        assert all(c.source_system == "grounded-research" for c in claims)

    def test_claim_has_source_ids(self) -> None:
        claims = load_handoff_claims(_HANDOFF_PATH)
        # At least some claims should have source IDs (from evidence)
        claims_with_sources = [c for c in claims if c.source_ids]
        assert len(claims_with_sources) >= 5

    def test_confidence_source_is_adjudication(self) -> None:
        claims = load_handoff_claims(_HANDOFF_PATH)
        assert all(c.confidence.source == "adjudication" for c in claims)


class TestLoadHandoffClaimsSynthetic:
    """Test load_handoff_claims with synthetic data."""

    def test_minimal_handoff(self, tmp_path: Path) -> None:
        handoff = {
            "claim_ledger": {
                "claims": [
                    {
                        "id": "C-test",
                        "statement": "Test claim.",
                        "status": "initial",
                        "confidence": "high",
                        "analyst_sources": ["Alpha"],
                        "evidence_ids": [],
                        "source_raw_claim_ids": [],
                        "status_reason": "",
                    }
                ],
                "disputes": [],
                "arbitration_results": [],
            },
            "sources": [],
            "evidence": [],
            "question": {"text": "Test?"},
            "downstream_target": "onto-canon",
            "generated_at": "2026-04-02T00:00:00Z",
        }
        path = tmp_path / "handoff.json"
        path.write_text(json.dumps(handoff))

        claims = load_handoff_claims(path)
        assert len(claims) == 1
        assert claims[0].id == "C-test"
        assert claims[0].confidence.score == 0.8  # "high" → 0.8
        assert claims[0].source_system == "grounded-research"

    def test_unknown_confidence_defaults(self, tmp_path: Path) -> None:
        handoff = {
            "claim_ledger": {
                "claims": [
                    {
                        "id": "C-x",
                        "statement": "Unknown confidence.",
                        "status": "initial",
                        "confidence": "unknown_value",
                        "analyst_sources": [],
                        "evidence_ids": [],
                        "source_raw_claim_ids": [],
                        "status_reason": "",
                    }
                ],
            },
            "sources": [],
            "evidence": [],
        }
        path = tmp_path / "handoff.json"
        path.write_text(json.dumps(handoff))

        claims = load_handoff_claims(path)
        assert claims[0].confidence.score == 0.5  # default
