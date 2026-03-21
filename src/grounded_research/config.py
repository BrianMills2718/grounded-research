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


def get_budget(key: str) -> int | float:
    """Get a budget value from config."""
    cfg = load_config()
    budgets = cfg.get("budgets", {})
    val = budgets.get(key)
    if val is None:
        raise KeyError(f"No budget configured for '{key}' in config/config.yaml")
    return val
