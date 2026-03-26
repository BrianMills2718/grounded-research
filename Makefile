# grounded-research Makefile — adjudication-centered research system
#
# Multi-analyst disagreement, claim extraction, dispute classification,
# selective re-verification, structured report export.
# Usage: make help

SHELL := /bin/bash
.DEFAULT_GOAL := help
PROJECT := $(notdir $(CURDIR))
PYTHON := python3
DAYS ?= 7
LIMIT ?= 20
QUERY ?=
INPUT ?=

# ─── Shared Targets ─────────────────────────────────────────────────────────

.PHONY: help test test-quick check status cost errors summary

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

check: ## Run tests + type check + lint
	$(PYTHON) -m pytest tests/ -x -q
	$(PYTHON) -m ruff check src/ tests/ || true
	$(PYTHON) -m mypy src/ --ignore-missing-imports || true

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

.PHONY: adjudicate bench evaluate

adjudicate: ## Run full adjudication pipeline (QUERY= or INPUT= required)
	@if [ -z "$(QUERY)" ] && [ -z "$(INPUT)" ]; then \
		echo "Usage: make adjudicate QUERY='topic' or make adjudicate INPUT=evidence.json"; \
		exit 1; \
	fi
	@if [ -n "$(QUERY)" ]; then \
		$(PYTHON) -m grounded_research.cli run "$(QUERY)"; \
	elif [ -n "$(INPUT)" ]; then \
		$(PYTHON) -m grounded_research.cli run --input "$(INPUT)"; \
	fi

bench: ## Run evaluation benchmarks
	$(PYTHON) -m pytest tests/ -v -k "bench or eval" 2>/dev/null || echo "No benchmark tests found"

evaluate: ## Show latest adjudication outputs and dispute stats
	@echo "Latest adjudication runs:"
	@ls -dt output/*/ 2>/dev/null | head -5
	@echo "---"
	@echo "Run-specific evaluation: python -m grounded_research.cli evaluate <output_dir>"
