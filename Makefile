# grounded-research Makefile — adjudication-centered research system
#
# Multi-analyst disagreement, claim extraction, dispute classification,
# selective re-verification, structured report export.
# Usage: make help

SHELL := /bin/bash
.DEFAULT_GOAL := help
PROJECT := $(notdir $(CURDIR))
PYTHON ?= python
DAYS ?= 7
LIMIT ?= 20
QUERY ?=
INPUT ?=

# ─── Shared Targets ─────────────────────────────────────────────────────────

.PHONY: help test test-quick lint typecheck check check-strict status cost errors summary

help: ## Show this help
	@echo "grounded-research — adjudication-centered research system"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Options: DAYS=7 QUERY='topic' INPUT=evidence.json LIMIT=20"

test: ## Run full test suite
	$(PYTHON) -m pytest tests/ -v

test-quick: ## Run tests, minimal output
	$(PYTHON) -m pytest tests/ -x -q

check: ## Run tests + lint + Tyler status gates
	$(PYTHON) scripts/check_local_test_env.py --format json >/dev/null
	$(PYTHON) -m pytest tests/ -x -q
	$(PYTHON) -m ruff check engine.py src/ tests/ scripts/
	$(PYTHON) scripts/check_docstrings.py >/dev/null
	$(PYTHON) scripts/check_tyler_traceability.py --format json --fail-on-issues >/dev/null
	$(PYTHON) scripts/check_tyler_coverage.py --format json --fail-on-grade-f --fail-on-findings >/dev/null
	$(PYTHON) scripts/check_tyler_doc_drift.py --format json --fail-on-findings >/dev/null
	$(PYTHON) scripts/check_tyler_code_audit.py --format json --fail-on-findings >/dev/null
	$(PYTHON) scripts/check_tyler_source_manifest.py --format json --fail-on-findings >/dev/null
	$(PYTHON) scripts/sync_tyler_registry.py --check --format json >/dev/null
	$(PYTHON) scripts/sync_tyler_requirements_yaml.py --check --format json >/dev/null
	$(PYTHON) scripts/generate_tyler_review_packets.py --format json >/dev/null

check-strict: ## Run tests + lint + docstring gate + strict mypy
	$(PYTHON) scripts/check_local_test_env.py --format json >/dev/null
	$(PYTHON) -m pytest tests/ -x -q
	$(PYTHON) -m ruff check engine.py src/ tests/ scripts/
	$(PYTHON) scripts/check_docstrings.py >/dev/null
	$(PYTHON) scripts/check_tyler_traceability.py --format json --fail-on-issues >/dev/null
	$(PYTHON) scripts/check_tyler_coverage.py --format json --fail-on-grade-f --fail-on-findings >/dev/null
	$(PYTHON) scripts/check_tyler_doc_drift.py --format json --fail-on-findings >/dev/null
	$(PYTHON) scripts/check_tyler_code_audit.py --format json --fail-on-findings >/dev/null
	$(PYTHON) scripts/check_tyler_source_manifest.py --format json --fail-on-findings >/dev/null
	$(PYTHON) scripts/sync_tyler_registry.py --check --format json >/dev/null
	$(PYTHON) scripts/sync_tyler_requirements_yaml.py --check --format json >/dev/null
	$(PYTHON) scripts/generate_tyler_review_packets.py --format json >/dev/null
	$(PYTHON) -m mypy src/ --ignore-missing-imports

lint: ## Run Ruff lint checks
	$(PYTHON) -m ruff check engine.py src/ tests/ scripts/

typecheck: ## Run strict mypy typecheck
	$(PYTHON) -m mypy src/ --ignore-missing-imports

status: ## Git status
	@git status --short --branch

cost: ## LLM spend (last N days)
	$(PYTHON) -m llm_client cost --project=$(PROJECT) --days=$(DAYS) 2>/dev/null || echo "llm_client not available"

errors: ## Error breakdown (last N days)
	$(PYTHON) -m llm_client errors --project=$(PROJECT) --days=$(DAYS) 2>/dev/null || echo "llm_client not available"

summary: ## Project summary: recent commits, test count
	@echo "$(PROJECT) summary:"
	@git log --oneline -5
	@echo "---"
	@find tests/ -name "test_*.py" 2>/dev/null | wc -l | xargs -I{} echo "Test files: {}"
	@echo "Output dirs:"; ls -d output/*/ 2>/dev/null | wc -l | xargs -I{} echo "  {} adjudication runs"

# ─── Domain Targets ──────────────────────────────────────────────────────────

.PHONY: adjudicate adjudicate-test bench evaluate check-env restore-frozen-outputs tyler-traceability tyler-traceability-json tyler-coverage tyler-coverage-json tyler-doc-audit tyler-doc-audit-json tyler-code-audit tyler-code-audit-json tyler-source-check tyler-source-check-json tyler-registry-check tyler-registry-json tyler-registry-sync tyler-requirements-yaml-check tyler-requirements-yaml tyler-requirements-yaml-sync tyler-review tyler-review-json tyler-review-packets

adjudicate: ## Run adjudication with Tyler-literal models (QUERY= or INPUT=)
	@if [ -z "$(QUERY)" ] && [ -z "$(INPUT)" ]; then \
		echo "Usage: make adjudicate QUERY='topic' or make adjudicate INPUT=evidence.json"; \
		exit 1; \
	fi
	@if [ -n "$(QUERY)" ]; then \
		$(PYTHON) engine.py "$(QUERY)"; \
	elif [ -n "$(INPUT)" ]; then \
		$(PYTHON) engine.py --fixture "$(INPUT)"; \
	fi

adjudicate-test: ## Run adjudication with cheap testing models (QUERY= or INPUT=)
	@if [ -z "$(QUERY)" ] && [ -z "$(INPUT)" ]; then \
		echo "Usage: make adjudicate-test QUERY='topic' or make adjudicate-test INPUT=evidence.json"; \
		exit 1; \
	fi
	@if [ -n "$(QUERY)" ]; then \
		$(PYTHON) engine.py --config testing "$(QUERY)"; \
	elif [ -n "$(INPUT)" ]; then \
		$(PYTHON) engine.py --config testing --fixture "$(INPUT)"; \
	fi

bench: ## Run evaluation benchmarks
	$(PYTHON) -m pytest tests/ -v -k "bench or eval"

evaluate: ## Show latest adjudication outputs and dispute stats
	@echo "Latest adjudication runs:"
	@ls -dt output/*/ 2>/dev/null | head -5
	@echo "---"
	@echo "Run-specific evaluation: python -m grounded_research.cli evaluate <output_dir>"

check-env: ## Explain local prerequisites required by make check
	@$(PYTHON) scripts/check_local_test_env.py --format markdown

restore-frozen-outputs: ## Restore ignored frozen eval outputs from populated checkout
	@$(PYTHON) scripts/restore_frozen_outputs.py --format markdown

tyler-traceability: ## Summarize Tyler requirements linked to code, tests, and docs
	@$(PYTHON) scripts/check_tyler_traceability.py --format markdown

tyler-traceability-json: ## Emit Tyler requirements traceability as JSON
	@$(PYTHON) scripts/check_tyler_traceability.py --format json

tyler-coverage: ## Summarize Tyler requirement coverage quality and evidence grades
	@$(PYTHON) scripts/check_tyler_coverage.py --format markdown

tyler-coverage-json: ## Emit Tyler requirement coverage quality as JSON
	@$(PYTHON) scripts/check_tyler_coverage.py --format json

tyler-doc-audit: ## Detect stale Tyler status claims in active docs
	@$(PYTHON) scripts/check_tyler_doc_drift.py --format markdown

tyler-doc-audit-json: ## Emit active Tyler doc-drift audit as JSON
	@$(PYTHON) scripts/check_tyler_doc_drift.py --format json

tyler-code-audit: ## Audit current-code evidence for Tyler requirement rows
	@$(PYTHON) scripts/check_tyler_code_audit.py --format markdown

tyler-code-audit-json: ## Emit current-code Tyler evidence audit as JSON
	@$(PYTHON) scripts/check_tyler_code_audit.py --format json

tyler-source-check: ## Verify tracked raw Tyler source packet hashes
	@$(PYTHON) scripts/check_tyler_source_manifest.py --format markdown

tyler-source-check-json: ## Emit raw Tyler source manifest check as JSON
	@$(PYTHON) scripts/check_tyler_source_manifest.py --format json

tyler-registry-check: ## Verify structured Tyler registry snapshot is current
	@$(PYTHON) scripts/sync_tyler_registry.py --check

tyler-registry-json: ## Emit structured Tyler registry JSON
	@$(PYTHON) scripts/sync_tyler_registry.py --format json

tyler-registry-sync: ## Regenerate structured Tyler registry snapshot
	@$(PYTHON) scripts/sync_tyler_registry.py --write

tyler-requirements-yaml-check: ## Verify structured Tyler requirements YAML is current
	@$(PYTHON) scripts/sync_tyler_requirements_yaml.py --check

tyler-requirements-yaml: ## Emit structured Tyler requirements YAML
	@$(PYTHON) scripts/sync_tyler_requirements_yaml.py

tyler-requirements-yaml-sync: ## Regenerate structured Tyler requirements YAML
	@$(PYTHON) scripts/sync_tyler_requirements_yaml.py --write

tyler-review: ## Summarize identify-only Tyler requirement review status
	@$(PYTHON) scripts/generate_tyler_review_packets.py --format markdown

tyler-review-json: ## Emit identify-only Tyler requirement review status as JSON
	@$(PYTHON) scripts/generate_tyler_review_packets.py --format json

tyler-review-packets: ## Generate identify-only Tyler review packets under output/
	@$(PYTHON) scripts/generate_tyler_review_packets.py --write --format markdown
