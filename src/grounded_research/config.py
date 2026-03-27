"""Project configuration loader.

Loads config/config.yaml and provides typed access to operational policy
values. All config access should go through this module, not through
direct YAML parsing in pipeline code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.yaml"

_cached_config: dict[str, Any] | None = None


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load and cache project configuration."""
    global _cached_config
    if _cached_config is not None and path is None:
        return _cached_config
    p = path or _CONFIG_PATH
    with open(p) as f:
        cfg = yaml.safe_load(f)
    if path is None:
        _cached_config = cfg
    return cfg


def get_model(task: str) -> str:
    """Get the configured model for a given task."""
    cfg = load_config()
    models = cfg.get("models", {})
    model = models.get(task)
    if not model:
        raise KeyError(f"No model configured for task '{task}' in config/config.yaml")
    return model


def get_fallback_models(task: str) -> list[str] | None:
    """Get the fallback model chain for a given task, or None if not configured."""
    cfg = load_config()
    fallbacks = cfg.get("model_fallbacks", {})
    chain = fallbacks.get(task)
    return chain if chain else None


_DEPTH_PROFILES = {
    "standard": {
        "num_queries": 15,
        "max_sources": 50,
        "compression_threshold": 80,
        "analyst_claim_target": 8,
        "synthesis_word_target": "5,000-6,000",
        "pipeline_max_budget_usd": 5.0,
        "arbitration_max_rounds": 1,
        "evidence_extraction_enabled": False,
        "evidence_extraction_max_sources": 0,
        "evidence_extraction_items_per_source": 0,
        "evidence_extraction_max_chars": 0,
    },
    "deep": {
        "num_queries": 30,
        "max_sources": 100,
        "compression_threshold": 150,
        "analyst_claim_target": 15,
        "synthesis_word_target": "8,000-10,000",
        "pipeline_max_budget_usd": 10.0,
        "arbitration_max_rounds": 2,
        "evidence_extraction_enabled": True,
        "evidence_extraction_max_sources": 20,
        "evidence_extraction_items_per_source": 4,
        "evidence_extraction_max_chars": 12000,
    },
    "thorough": {
        "num_queries": 50,
        "max_sources": 150,
        "compression_threshold": 300,
        "analyst_claim_target": 20,
        "synthesis_word_target": "10,000-15,000",
        "pipeline_max_budget_usd": 20.0,
        "arbitration_max_rounds": 3,
        "evidence_extraction_enabled": True,
        "evidence_extraction_max_sources": 30,
        "evidence_extraction_items_per_source": 6,
        "evidence_extraction_max_chars": 16000,
    },
}


def get_depth_config() -> dict[str, Any]:
    """Get the depth-dependent configuration values.

    Reads `depth` from config.yaml (default: "standard") and returns
    the corresponding profile. Config values explicitly set in
    config.yaml override the profile defaults.
    """
    cfg = load_config()
    depth = cfg.get("depth", "standard")
    profile = _DEPTH_PROFILES.get(depth, _DEPTH_PROFILES["standard"]).copy()

    # For non-standard depth, the profile values take precedence.
    # Config.yaml collection/budgets values only apply when depth is "standard"
    # (they're the legacy config surface for backward compatibility).
    if depth == "standard":
        collection = cfg.get("collection", {})
        for key in ("num_queries", "max_sources"):
            if key in collection:
                profile[key] = collection[key]

        evidence = cfg.get("evidence_policy", {})
        if "compression_threshold" in evidence:
            profile["compression_threshold"] = evidence["compression_threshold"]

        budgets = cfg.get("budgets", {})
        if "pipeline_max_budget_usd" in budgets:
            profile["pipeline_max_budget_usd"] = budgets["pipeline_max_budget_usd"]

    return profile


def get_budget(key: str) -> int | float:
    """Get a budget value from config."""
    cfg = load_config()
    budgets = cfg.get("budgets", {})
    val = budgets.get(key)
    if val is None:
        raise KeyError(f"No budget configured for '{key}' in config/config.yaml")
    return val


def get_dedup_config() -> dict[str, int | float]:
    """Get dedup-specific policy with config overrides.

    These controls are intentionally separate from general evidence policy
    because dense-claim canonicalization has its own stability tradeoffs.
    """
    cfg = load_config()
    configured = cfg.get("deduplication", {})
    defaults: dict[str, int | float] = {
        "staged_trigger_claims": 20,
        "bucket_max_claims": 12,
        "max_doc_frequency_ratio": 0.45,
        "min_shared_informative_tokens": 1,
    }
    defaults.update(configured)
    return defaults


def get_collection_ranking_config() -> dict[str, Any]:
    """Get search-result ranking policy with config overrides.

    Collection ranking is separate from source-quality scoring because it is a
    pre-fetch mechanical policy for deciding which URLs are worth spending
    fetch budget on.
    """
    cfg = load_config()
    collection = cfg.get("collection", {})
    configured = collection.get("ranking", {})
    defaults: dict[str, Any] = {
        "preferred_domain_patterns": [],
        "deprioritized_domain_patterns": [],
        "preferred_title_terms": [],
        "deprioritized_title_terms": [],
        "pdf_bonus": 3,
        "preferred_domain_bonus": 5,
        "deprioritized_domain_penalty": 6,
        "preferred_title_bonus": 2,
        "deprioritized_title_penalty": 3,
        "quality_tier_bonus": {
            "authoritative": 8,
            "reliable": 3,
            "unknown": 0,
            "unreliable": -6,
        },
    }
    defaults.update(configured)
    return defaults


def get_evidence_policy_config() -> dict[str, Any]:
    """Get evidence-presentation policy with stable defaults.

    This keeps prompt rendering limits in config rather than hidden in
    individual templates.
    """
    cfg = load_config()
    configured = cfg.get("evidence_policy", {})
    defaults: dict[str, Any] = {
        "default_time_sensitivity": "mixed",
        "recency_weight": 0.5,
        "compression_threshold": 80,
        "synthesis_evidence_cap": 30,
        "structured_content_truncation_chars": 500,
        "long_report_content_truncation_chars": 400,
    }
    defaults.update(configured)
    return defaults


def get_phase_concurrency_config() -> dict[str, int]:
    """Get per-phase concurrency controls with safe defaults."""
    cfg = load_config()
    configured = cfg.get("phase_concurrency", {})
    defaults: dict[str, int] = {
        "claim_extraction_max_concurrency": 1,
        "evidence_extraction_max_concurrency": 2,
    }
    defaults.update(configured)
    return defaults


def get_analysis_coverage_config() -> dict[str, int | float | bool]:
    """Get analyst coverage policy with config overrides.

    This policy governs whether rich evidence bundles trigger a single
    corrective retry when an analyst returns materially fewer claims than the
    configured depth-profile target.
    """
    cfg = load_config()
    configured = cfg.get("analysis_coverage", {})
    defaults: dict[str, int | float | bool] = {
        "analyst_retry_on_undercoverage": True,
        "analyst_retry_min_evidence_items": 25,
        "analyst_retry_min_claim_ratio": 0.75,
        "analyst_retry_max_attempts": 1,
    }
    defaults.update(configured)
    return defaults


def get_tyler_literal_parity_config() -> dict[str, Any]:
    """Get Tyler literal-parity runtime safety policy with config overrides.

    The Tyler-native runtime uses stricter, larger structured schemas than the
    original shipped pipeline. These settings guard against schema-valid but
    analytically empty artifacts during live runs.
    """
    cfg = load_config()
    configured = cfg.get("tyler_literal_parity", {})
    defaults: dict[str, Any] = {
        "stage4_retry_on_empty_claims": True,
        "stage4_retry_model": "openrouter/google/gemini-2.5-flash",
        "stage4_retry_fallback_models": ["openrouter/openai/gpt-5-nano"],
    }
    defaults.update(configured)
    return defaults


def get_runtime_reliability_config() -> dict[str, Any]:
    """Get benchmark/runtime reliability policy with config overrides.

    These settings exist to make long benchmark and evaluation runs complete
    predictably. They are operational policy, not prompt logic.
    """
    cfg = load_config()
    configured = cfg.get("runtime_reliability", {})
    defaults: dict[str, Any] = {
        "use_run_local_observability_db": True,
        "timeout_policy": "allow",
        "request_timeouts_s": {
            "decomposition": 120,
            "query_generation": 120,
            "source_scoring": 180,
            "analyst": 180,
            "claim_extraction": 240,
            "deduplication": 180,
            "dispute_classification": 180,
            "verification_query_generation": 120,
            "arbitration": 240,
            "synthesis": 240,
            "long_report": 300,
        },
    }
    if isinstance(configured, dict):
        request_timeouts = configured.get("request_timeouts_s", {})
        if isinstance(request_timeouts, dict):
            defaults["request_timeouts_s"].update(request_timeouts)
        defaults.update({k: v for k, v in configured.items() if k != "request_timeouts_s"})
    return defaults


def get_export_policy_config() -> dict[str, Any]:
    """Get export-specific rendering policy with config overrides.

    Export policy is separate from evidence policy because sectioned synthesis
    changes how the report is rendered, not what evidence is shown in prompts.
    """
    cfg = load_config()
    configured = cfg.get("export_policy", {})
    defaults: dict[str, Any] = {
        "sectioned_synthesis_min_word_target": 9000,
        "sectioned_synthesis_max_distinction_sections": 4,
        "sectioned_synthesis_enabled_depths": ["thorough"],
    }
    defaults.update(configured)
    return defaults
