"""Identity scrubbing for analyst outputs.

This module enforces model-anonymization at the code boundary rather than
relying only on prompt instructions. Only self-identification phrases are
scrubbed; subject-matter mentions of providers or models in the evidence are
left untouched.
"""

from __future__ import annotations

import re

from grounded_research.models import AnalystRun


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


def scrub_analyst_run(run: AnalystRun) -> list[str]:
    """Scrub self-identification from all downstream-reused analyst fields.

    Returns a list of field paths that were modified. The AnalystRun is mutated
    in place because the sanitized text should be what every downstream stage
    sees.
    """
    redactions: list[str] = []

    def _scrub_field(obj: object, field_name: str, path: str) -> None:
        value = getattr(obj, field_name)
        if not isinstance(value, str) or not value:
            return
        cleaned, changed = scrub_identity_markers(value)
        if changed:
            setattr(obj, field_name, cleaned)
            redactions.append(path)

    for claim in run.claims:
        _scrub_field(claim, "statement", f"claim:{claim.id}:statement")
        _scrub_field(claim, "reasoning", f"claim:{claim.id}:reasoning")

    for assumption in run.assumptions:
        _scrub_field(assumption, "statement", f"assumption:{assumption.id}:statement")
        _scrub_field(assumption, "basis", f"assumption:{assumption.id}:basis")

    for idx, recommendation in enumerate(run.recommendations):
        _scrub_field(recommendation, "statement", f"recommendation:{idx}:statement")
        _scrub_field(recommendation, "conditions", f"recommendation:{idx}:conditions")

    for idx, counterargument in enumerate(run.counterarguments):
        _scrub_field(counterargument, "target", f"counterargument:{idx}:target")
        _scrub_field(counterargument, "argument", f"counterargument:{idx}:argument")

    _scrub_field(run, "summary", "summary")
    return redactions
