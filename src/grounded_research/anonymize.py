"""Identity scrubbing for analyst outputs.

This module enforces model-anonymization at the code boundary rather than
relying only on prompt instructions. Only self-identification phrases are
scrubbed; subject-matter mentions of providers or models in the evidence are
left untouched.
"""

from __future__ import annotations

import re

from grounded_research.tyler_v1_models import AnalysisObject


_SELF_IDENTIFICATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\bAs an? (?:OpenAI|Anthropic|Google|DeepSeek)\s+(?:model|assistant)\b",
            re.IGNORECASE,
        ),
        "As an analyst",
    ),
    (
        re.compile(
            r"\bAs (?:Claude|Gemini|ChatGPT|DeepSeek(?: Chat)?|GPT-[A-Za-z0-9.\-]+)\b",
            re.IGNORECASE,
        ),
        "As an analyst",
    ),
    (
        re.compile(
            r"\bI(?:'m| am) (?:an? )?(?:OpenAI|Anthropic|Google|DeepSeek)\s+(?:model|assistant)\b",
            re.IGNORECASE,
        ),
        "I am an analyst",
    ),
    (
        re.compile(
            r"\bI(?:'m| am) (?:Claude|Gemini|ChatGPT|DeepSeek(?: Chat)?|GPT-[A-Za-z0-9.\-]+)\b",
            re.IGNORECASE,
        ),
        "I am an analyst",
    ),
    (
        re.compile(r"\bmy training data\b", re.IGNORECASE),
        "the provided evidence",
    ),
]


def scrub_identity_markers(text: str) -> tuple[str, bool]:
    """Remove model self-identification phrases from analyst text."""
    cleaned = text
    changed = False
    for pattern, replacement in _SELF_IDENTIFICATION_PATTERNS:
        next_cleaned, replacements = pattern.subn(replacement, cleaned)
        if replacements:
            changed = True
            cleaned = next_cleaned
    return cleaned, changed
def scrub_tyler_analysis_object(analysis: AnalysisObject) -> list[str]:
    """Scrub self-identification from Tyler Stage 3 fields reused downstream."""
    redactions: list[str] = []

    def _scrub_field(obj: object, field_name: str, path: str) -> None:
        value = getattr(obj, field_name)
        if not isinstance(value, str) or not value:
            return
        cleaned, changed = scrub_identity_markers(value)
        if changed:
            setattr(obj, field_name, cleaned)
            redactions.append(path)

    _scrub_field(analysis, "recommendation", "recommendation")
    _scrub_field(analysis, "reasoning", "reasoning")

    for claim in analysis.claims:
        _scrub_field(claim, "statement", f"claim:{claim.id}:statement")

    for assumption in analysis.assumptions:
        _scrub_field(assumption, "statement", f"assumption:{assumption.id}:statement")
        _scrub_field(assumption, "if_wrong_impact", f"assumption:{assumption.id}:if_wrong_impact")

    _scrub_field(analysis.counter_argument, "argument", "counter_argument:argument")
    _scrub_field(
        analysis.counter_argument,
        "strongest_evidence_against",
        "counter_argument:strongest_evidence_against",
    )

    for idx, condition in enumerate(analysis.falsification_conditions):
        cleaned, changed = scrub_identity_markers(condition)
        if changed:
            analysis.falsification_conditions[idx] = cleaned
            redactions.append(f"falsification_conditions:{idx}")

    return redactions
