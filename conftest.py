"""Root conftest: auto-select cheap testing config for all test runs."""

import os

# Set before any grounded_research imports so config.py picks it up
os.environ.setdefault("GROUNDED_RESEARCH_CONFIG", "testing")
