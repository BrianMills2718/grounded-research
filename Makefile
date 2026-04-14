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

.PHONY: adjudicate adjudicate-test bench evaluate

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
	$(PYTHON) -m pytest tests/ -v -k "bench or eval" 2>/dev/null || echo "No benchmark tests found"

evaluate: ## Show latest adjudication outputs and dispute stats
	@echo "Latest adjudication runs:"
	@ls -dt output/*/ 2>/dev/null | head -5
	@echo "---"
	@echo "Run-specific evaluation: python -m grounded_research.cli evaluate <output_dir>"

# --- Quality ---
.PHONY: dead-code dead-code-audit dead-code-validate

dead-code:  ## Run dead code detection
	@python scripts/meta/check_dead_code.py

dead-code-audit:  ## Refresh reviewed dead-code audit file
	@python scripts/meta/audit_dead_code.py --write

dead-code-validate:  ## Validate reviewed dead-code dispositions
	@python scripts/meta/validate_dead_code_audit.py

# >>> META-PROCESS WORKTREE TARGETS >>>
WORKTREE_CREATE_SCRIPT := scripts/meta/worktree-coordination/create_worktree.py
WORKTREE_REMOVE_SCRIPT := scripts/meta/worktree-coordination/safe_worktree_remove.py
WORKTREE_CLAIMS_SCRIPT := scripts/meta/worktree-coordination/../check_coordination_claims.py
WORKTREE_SESSION_START_SCRIPT := scripts/meta/worktree-coordination/../session_start.py
WORKTREE_SESSION_HEARTBEAT_SCRIPT := scripts/meta/worktree-coordination/../session_heartbeat.py
WORKTREE_SESSION_STATUS_SCRIPT := scripts/meta/worktree-coordination/../session_status.py
WORKTREE_SESSION_FINISH_SCRIPT := scripts/meta/worktree-coordination/../session_finish.py
WORKTREE_SESSION_CLOSE_SCRIPT := scripts/meta/worktree-coordination/../session_close.py
WORKTREE_REVIEW_CLAIM_SCRIPT := scripts/meta/worktree-coordination/create_review_claim.py
WORKTREE_RAISE_CONCERN_SCRIPT := scripts/meta/worktree-coordination/raise_concern.py
WORKTREE_DIR ?= $(shell python "$(WORKTREE_CREATE_SCRIPT)" --repo-root . --print-default-worktree-dir)
WORKTREE_START_POINT ?= HEAD
WORKTREE_PROJECT ?= $(notdir $(CURDIR))
WORKTREE_AGENT ?= $(shell if [ -n "$$CODEX_THREAD_ID" ]; then printf codex; elif [ -n "$$CLAUDE_SESSION_ID" ] || [ -n "$$CLAUDE_CODE_SSE_PORT" ]; then printf claude-code; elif [ -n "$$OPENCLAW_SESSION_ID" ] || [ -n "$$OPENCLAW_RUN_ID" ]; then printf openclaw; fi)
SESSION_GOAL ?=
SESSION_PHASE ?=
SESSION_NEXT ?=
SESSION_DEPENDS ?=
SESSION_STOP_CONDITIONS ?=
SESSION_NOTE ?=
REVIEW_SCOPE ?=
REVIEW_NOTES ?=
RECIPIENT ?=

.PHONY: worktree worktree-list worktree-remove session-start session-heartbeat session-status session-finish session-close review-claim raise-concern

worktree:  ## Create claimed worktree (BRANCH=name TASK="..." [PLAN=N] [AGENT=name])
ifndef BRANCH
	$(error BRANCH is required. Usage: make worktree BRANCH=plan-42-feature TASK="Describe the task")
endif
ifndef TASK
	$(error TASK is required. Usage: make worktree BRANCH=plan-42-feature TASK="Describe the task")
endif
ifndef SESSION_GOAL
	$(error SESSION_GOAL is required. Name the broader objective, not the local branch)
endif
ifndef SESSION_PHASE
	$(error SESSION_PHASE is required. Describe the current execution phase)
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@if [ ! -f "$(WORKTREE_CREATE_SCRIPT)" ]; then \
		echo "Missing worktree coordination module: $(WORKTREE_CREATE_SCRIPT)"; \
		echo "Install or sync the sanctioned worktree-coordination module before using make worktree."; \
		exit 1; \
	fi
	@if [ ! -f "$(WORKTREE_CLAIMS_SCRIPT)" ]; then \
		echo "Missing worktree coordination module: $(WORKTREE_CLAIMS_SCRIPT)"; \
		echo "Install or sync the sanctioned worktree-coordination module before using make worktree."; \
		exit 1; \
	fi
	@if [ ! -f "$(WORKTREE_SESSION_START_SCRIPT)" ]; then \
		echo "Missing session lifecycle module: $(WORKTREE_SESSION_START_SCRIPT)"; \
		echo "Install or sync the sanctioned session lifecycle module before using make worktree."; \
		exit 1; \
	fi
	@python "$(WORKTREE_CLAIMS_SCRIPT)" --claim \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--scope "$(BRANCH)" \
		--intent "$(TASK)" \
		--claim-type program \
		--branch "$(BRANCH)" \
		--worktree-path "$(WORKTREE_DIR)/$(BRANCH)" \
		$(if $(PLAN),--plan "Plan #$(PLAN)",)
	@mkdir -p "$(WORKTREE_DIR)"
	@if ! python "$(WORKTREE_CREATE_SCRIPT)" --repo-root . --path "$(WORKTREE_DIR)/$(BRANCH)" --branch "$(BRANCH)" --start-point "$(WORKTREE_START_POINT)"; then \
		python "$(WORKTREE_CLAIMS_SCRIPT)" --release --agent "$(WORKTREE_AGENT)" --project "$(WORKTREE_PROJECT)" --scope "$(BRANCH)" >/dev/null 2>&1 || true; \
		exit 1; \
	fi
	@if ! python "$(WORKTREE_SESSION_START_SCRIPT)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--scope "$(BRANCH)" \
		--intent "$(TASK)" \
		--repo-root "$(CURDIR)" \
		--worktree-path "$(WORKTREE_DIR)/$(BRANCH)" \
		--branch "$(BRANCH)" \
		--broader-goal "$(SESSION_GOAL)" \
		--current-phase "$(SESSION_PHASE)" \
		$(if $(PLAN),--plan "Plan #$(PLAN)",) \
		$(if $(SESSION_NEXT),--next-phase "$(SESSION_NEXT)",) \
		$(if $(SESSION_DEPENDS),--depends-on "$(SESSION_DEPENDS)",) \
		$(if $(SESSION_STOP_CONDITIONS),--stop-condition "$(SESSION_STOP_CONDITIONS)",) \
		$(if $(SESSION_NOTE),--notes "$(SESSION_NOTE)",); then \
		git worktree remove --force "$(WORKTREE_DIR)/$(BRANCH)" >/dev/null 2>&1 || true; \
		git branch -D "$(BRANCH)" >/dev/null 2>&1 || true; \
		python "$(WORKTREE_CLAIMS_SCRIPT)" --release --agent "$(WORKTREE_AGENT)" --project "$(WORKTREE_PROJECT)" --scope "$(BRANCH)" >/dev/null 2>&1 || true; \
		exit 1; \
	fi
	@echo ""
	@echo "Worktree created at $(WORKTREE_DIR)/$(BRANCH)"
	@echo "Claim created for branch $(BRANCH)"
	@echo "Session contract started for $(SESSION_GOAL)"

session-start:  ## Create or refresh the active session contract for BRANCH=name
ifndef BRANCH
	$(error BRANCH is required. Usage: make session-start BRANCH=plan-42-feature TASK="..." SESSION_GOAL="..." SESSION_PHASE="...")
endif
ifndef TASK
	$(error TASK is required. Usage: make session-start BRANCH=plan-42-feature TASK="...")
endif
ifndef SESSION_GOAL
	$(error SESSION_GOAL is required. Name the broader objective, not the local branch)
endif
ifndef SESSION_PHASE
	$(error SESSION_PHASE is required. Describe the current execution phase)
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@python "$(WORKTREE_SESSION_START_SCRIPT)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--scope "$(BRANCH)" \
		--intent "$(TASK)" \
		--repo-root "$(CURDIR)" \
		--worktree-path "$(WORKTREE_DIR)/$(BRANCH)" \
		--branch "$(BRANCH)" \
		--broader-goal "$(SESSION_GOAL)" \
		--current-phase "$(SESSION_PHASE)" \
		$(if $(PLAN),--plan "Plan #$(PLAN)",) \
		$(if $(SESSION_NEXT),--next-phase "$(SESSION_NEXT)",) \
		$(if $(SESSION_DEPENDS),--depends-on "$(SESSION_DEPENDS)",) \
		$(if $(SESSION_STOP_CONDITIONS),--stop-condition "$(SESSION_STOP_CONDITIONS)",) \
		$(if $(SESSION_NOTE),--notes "$(SESSION_NOTE)",)

session-heartbeat:  ## Refresh heartbeat and optional phase for BRANCH=name
ifndef BRANCH
	$(error BRANCH is required. Usage: make session-heartbeat BRANCH=plan-42-feature)
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@python "$(WORKTREE_SESSION_HEARTBEAT_SCRIPT)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--scope "$(BRANCH)" \
		--branch "$(BRANCH)" \
		$(if $(SESSION_PHASE),--current-phase "$(SESSION_PHASE)",)

session-status:  ## Show live session summaries for this repo
	@python "$(WORKTREE_SESSION_STATUS_SCRIPT)" --project "$(WORKTREE_PROJECT)"

session-finish:  ## Finish the session for BRANCH=name; blocks if the worktree is dirty
ifndef BRANCH
	$(error BRANCH is required. Usage: make session-finish BRANCH=plan-42-feature)
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@python "$(WORKTREE_SESSION_FINISH_SCRIPT)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--scope "$(BRANCH)" \
		--worktree-path "$(WORKTREE_DIR)/$(BRANCH)" \
		$(if $(SESSION_NOTE),--note "$(SESSION_NOTE)",)

session-close:  ## Close the claimed lane for BRANCH=name: cleanup worktree + branch + claim together
ifndef BRANCH
	$(error BRANCH is required. Usage: make session-close BRANCH=plan-42-feature)
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@python "$(WORKTREE_SESSION_CLOSE_SCRIPT)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--scope "$(BRANCH)" \
		--worktree-path "$(WORKTREE_DIR)/$(BRANCH)" \
		--branch "$(BRANCH)" \
		$(if $(SESSION_NOTE),--note "$(SESSION_NOTE)",)

worktree-list:  ## Show claimed worktree coordination status
	@if [ ! -f "$(WORKTREE_CLAIMS_SCRIPT)" ]; then \
		echo "Missing worktree coordination module: $(WORKTREE_CLAIMS_SCRIPT)"; \
		echo "Install or sync the sanctioned worktree-coordination module before using make worktree-list."; \
		exit 1; \
	fi
	@python "$(WORKTREE_CLAIMS_SCRIPT)" --list

worktree-remove:  ## Safely remove worktree for BRANCH=name
ifndef BRANCH
	$(error BRANCH is required. Usage: make worktree-remove BRANCH=plan-42-feature)
endif
	@if [ ! -f "$(WORKTREE_SESSION_CLOSE_SCRIPT)" ]; then \
		echo "Missing session lifecycle module: $(WORKTREE_SESSION_CLOSE_SCRIPT)"; \
		echo "Install or sync the sanctioned session lifecycle module before using make worktree-remove."; \
		exit 1; \
	fi
	@$(MAKE) session-close BRANCH="$(BRANCH)" $(if $(SESSION_NOTE),SESSION_NOTE="$(SESSION_NOTE)",)

review-claim:  ## Create a review claim for TARGET_BRANCH=name WRITE_PATHS="a|b" TASK="..."
ifndef TARGET_BRANCH
	$(error TARGET_BRANCH is required. Usage: make review-claim TARGET_BRANCH=plan-42-feature WRITE_PATHS="src/foo.py|tests/test_foo.py" TASK="Review concern")
endif
ifndef WRITE_PATHS
	$(error WRITE_PATHS is required. Provide one or more repo-relative paths separated by '|')
endif
ifndef TASK
	$(error TASK is required. Describe the review intent)
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@python "$(WORKTREE_REVIEW_CLAIM_SCRIPT)" \
		--repo-root "$(CURDIR)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--target-branch "$(TARGET_BRANCH)" \
		--intent "$(TASK)" \
		--write-path "$(WRITE_PATHS)" \
		$(if $(PLAN),--plan "Plan #$(PLAN)",) \
		$(if $(REVIEW_SCOPE),--scope "$(REVIEW_SCOPE)",) \
		$(if $(REVIEW_NOTES),--notes "$(REVIEW_NOTES)",)

raise-concern:  ## Route concern to TARGET_BRANCH via PR comment or local inbox
ifndef TARGET_BRANCH
	$(error TARGET_BRANCH is required. Usage: make raise-concern TARGET_BRANCH=plan-42-feature SUBJECT="..." MESSAGE="...")
endif
ifndef SUBJECT
	$(error SUBJECT is required. Usage: make raise-concern TARGET_BRANCH=plan-42-feature SUBJECT="..." MESSAGE="...")
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
ifndef MESSAGE
ifndef MESSAGE_FILE
	$(error MESSAGE or MESSAGE_FILE is required. Provide inline content or a path to a concern file)
endif
endif
	@python "$(WORKTREE_RAISE_CONCERN_SCRIPT)" \
		--repo-root "$(CURDIR)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--target-branch "$(TARGET_BRANCH)" \
		--subject "$(SUBJECT)" \
		$(if $(MESSAGE),--content "$(MESSAGE)",) \
		$(if $(MESSAGE_FILE),--content-file "$(MESSAGE_FILE)",) \
		$(if $(RECIPIENT),--recipient "$(RECIPIENT)",)
# <<< META-PROCESS WORKTREE TARGETS <<<

# >>> META-PROCESS PUBLISH TARGETS >>>
PUBLISH_PUSH_CHECK_SCRIPT := scripts/meta/check_push_safety.py
PUBLISH_DEAD_CODE_SCRIPT := scripts/meta/check_dead_code.py
PUBLISH_DEAD_CODE_VALIDATE_SCRIPT := scripts/meta/validate_dead_code_audit.py

.PHONY: publish-check

publish-check:  ## Run the governed publish gate (coordination, repo checks, reviewed dead-code)
	@if [ ! -f "$(PUBLISH_PUSH_CHECK_SCRIPT)" ]; then \
		echo "Missing push-safety validator: $(PUBLISH_PUSH_CHECK_SCRIPT)"; \
		echo "Install or sync the sanctioned governed-repo support before publishing."; \
		exit 1; \
	fi
	@if [ ! -f "$(PUBLISH_DEAD_CODE_SCRIPT)" ]; then \
		echo "Missing dead-code detector: $(PUBLISH_DEAD_CODE_SCRIPT)"; \
		echo "Install or sync the sanctioned governed-repo support before publishing."; \
		exit 1; \
	fi
	@if [ ! -f "$(PUBLISH_DEAD_CODE_VALIDATE_SCRIPT)" ]; then \
		echo "Missing dead-code audit validator: $(PUBLISH_DEAD_CODE_VALIDATE_SCRIPT)"; \
		echo "Install or sync the sanctioned governed-repo support before publishing."; \
		exit 1; \
	fi
	@python "$(PUBLISH_PUSH_CHECK_SCRIPT)"
	@python "$(PUBLISH_DEAD_CODE_SCRIPT)"
	@python "$(PUBLISH_DEAD_CODE_VALIDATE_SCRIPT)"
	@if $(MAKE) -n publish-check-extra >/dev/null 2>&1; then \
		$(MAKE) publish-check-extra; \
	fi
# <<< META-PROCESS PUBLISH TARGETS <<<
