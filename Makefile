# Makefile — ai-grok-analysis local automation
#
# Usage:
#   make help          Show all targets
#   make analyze       Run void-cluster analysis on all data
#   make temporal      Run temporal pattern analysis
#   make version       Run Grok version change detection
#   make lint          Lint all scripts
#   make all           Run everything
#
# Requirements: Python 3.9+, pip

.PHONY: help all analyze parse temporal version lint format check clean setup

PYTHON     ?= python3
PIP        ?= pip
SCRIPTS    := scripts
DATA       := data
PARSED     := data/parsed
CONVOS     := data/conversations
REPORTS    := reports
REF_DATE   ?= $(shell date +%Y-%m-%d 2>/dev/null || echo 2026-02-04)

# ─── Default ──────────────────────────────────────────────────────
help: ## Show this help
	@echo "ai-grok-analysis — Makefile targets"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Variables:"
	@echo "  PYTHON=$(PYTHON)  REF_DATE=$(REF_DATE)"

all: setup lint parse analyze temporal version ## Run everything

# ─── Setup ────────────────────────────────────────────────────────
setup: ## Install Python dependencies
	$(PIP) install --upgrade pip
	@if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi
	@mkdir -p $(PARSED) $(CONVOS) $(REPORTS)
	@echo "✓ Setup complete"

# ─── Parse ────────────────────────────────────────────────────────
parse: $(PARSED)/conversation_index.json ## Parse conversation history into index

$(PARSED)/conversation_index.json: $(DATA)/conversation-history.md $(SCRIPTS)/parse_conversations.py
	@mkdir -p $(PARSED)
	$(PYTHON) $(SCRIPTS)/parse_conversations.py \
		--index $(DATA)/conversation-history.md \
		--reference-date "$(REF_DATE)" \
		--output $@

parse-batch: parse ## Parse all conversation dumps (requires data/conversations/*.md)
	@if ls $(CONVOS)/*.md 1>/dev/null 2>&1; then \
		$(PYTHON) $(SCRIPTS)/parse_conversations.py --batch $(CONVOS)/; \
	else \
		echo "No conversation files in $(CONVOS)/ — add .md files and re-run"; \
	fi

# ─── Analysis ─────────────────────────────────────────────────────
analyze: parse ## Run void-cluster analysis on all available data
	@echo "═══ Void-Cluster Analysis ═══"
	@if ls $(CONVOS)/*.md 1>/dev/null 2>&1; then \
		for f in $(CONVOS)/*.md; do \
			echo ""; \
			echo "── $$(basename $$f) ──"; \
			$(PYTHON) $(SCRIPTS)/analyze.py "$$f" --format markdown; \
		done; \
	else \
		echo "No conversation text files in $(CONVOS)/"; \
		echo "Analyzing pattern report instead..."; \
		$(PYTHON) $(SCRIPTS)/analyze.py analysis/grok-pattern-analysis.md --format markdown; \
	fi

analyze-json: parse ## Run analysis with JSON output
	@mkdir -p $(REPORTS)
	@if ls $(CONVOS)/*.md 1>/dev/null 2>&1; then \
		for f in $(CONVOS)/*.md; do \
			$(PYTHON) $(SCRIPTS)/analyze.py "$$f" --format json \
				> $(REPORTS)/$$(basename "$$f" .md).json; \
		done; \
		echo "✓ JSON results in $(REPORTS)/"; \
	else \
		$(PYTHON) $(SCRIPTS)/analyze.py analysis/grok-pattern-analysis.md --format json \
			> $(REPORTS)/pattern-analysis.json; \
		echo "✓ $(REPORTS)/pattern-analysis.json"; \
	fi

# ─── Temporal ─────────────────────────────────────────────────────
temporal: parse ## Run temporal drift analysis
	@mkdir -p $(REPORTS)
	$(PYTHON) $(SCRIPTS)/temporal_analysis.py \
		--index $(PARSED)/conversation_index.json \
		--conversations $(CONVOS) \
		--window 7 \
		--output $(REPORTS)/temporal_report.json \
		--markdown $(REPORTS)/temporal_report.md

# ─── Version Detection ───────────────────────────────────────────
version: parse ## Run Grok version change detection
	@mkdir -p $(REPORTS)
	$(PYTHON) $(SCRIPTS)/version_detect.py \
		--index $(PARSED)/conversation_index.json \
		--conversations $(CONVOS) \
		--sensitivity medium \
		--output $(REPORTS)/version_report.json \
		--markdown $(REPORTS)/version_report.md

# ─── C Analyzer ──────────────────────────────────────────────────
build-c: ## Build the C void-cluster analyzer (requires cosmocc)
	@command -v cosmocc >/dev/null 2>&1 || \
		{ echo "cosmocc not found — install Cosmopolitan: https://cosmo.zip"; exit 1; }
	cosmocc -O2 -o void-cluster-analyzer.com $(SCRIPTS)/void-cluster-analyzer.c -lm
	@echo "✓ Built void-cluster-analyzer.com (Actually Portable Executable)"

# ─── Lint ─────────────────────────────────────────────────────────
lint: ## Lint all Python scripts
	@echo "═══ Ruff Lint ═══"
	@command -v ruff >/dev/null 2>&1 && ruff check $(SCRIPTS)/ || \
		echo "ruff not installed — run: pip install ruff"
	@echo ""
	@echo "═══ Syntax Check ═══"
	$(PYTHON) -m py_compile $(SCRIPTS)/analyze.py
	$(PYTHON) -m py_compile $(SCRIPTS)/parse_conversations.py
	$(PYTHON) -m py_compile $(SCRIPTS)/temporal_analysis.py
	$(PYTHON) -m py_compile $(SCRIPTS)/version_detect.py
	@echo "✓ All scripts compile"

format: ## Auto-format Python scripts with ruff
	@command -v ruff >/dev/null 2>&1 && ruff format $(SCRIPTS)/ || \
		echo "ruff not installed — run: pip install ruff"

check: lint ## Run lint + syntax check (alias)

# ─── Smoke Test ───────────────────────────────────────────────────
test: ## Quick smoke test of all scripts
	@echo "═══ Smoke Tests ═══"
	@echo "test: void darkness shadow emptiness" > /tmp/grok-test.txt
	$(PYTHON) $(SCRIPTS)/analyze.py /tmp/grok-test.txt --format json | $(PYTHON) -m json.tool > /dev/null
	@echo "✓ analyze.py"
	@mkdir -p $(PARSED)
	$(PYTHON) $(SCRIPTS)/parse_conversations.py \
		--index $(DATA)/conversation-history.md \
		--reference-date "2026-02-04" \
		--output /tmp/grok-test-index.json
	@echo "✓ parse_conversations.py"
	$(PYTHON) $(SCRIPTS)/temporal_analysis.py \
		--index /tmp/grok-test-index.json \
		--window 7 \
		--output /tmp/grok-temporal.json \
		--markdown /tmp/grok-temporal.md
	@echo "✓ temporal_analysis.py"
	$(PYTHON) $(SCRIPTS)/version_detect.py \
		--index /tmp/grok-test-index.json \
		--sensitivity high \
		--output /tmp/grok-version.json \
		--markdown /tmp/grok-version.md
	@echo "✓ version_detect.py"
	@rm -f /tmp/grok-test.txt /tmp/grok-test-index.json /tmp/grok-temporal.* /tmp/grok-version.*
	@echo ""
	@echo "All smoke tests passed ✓"

# ─── Clean ────────────────────────────────────────────────────────
clean: ## Remove generated files
	rm -rf $(PARSED)/*.json $(REPORTS)/*.json $(REPORTS)/*.md
	rm -f void-cluster-analyzer.com
	rm -rf __pycache__ $(SCRIPTS)/__pycache__
	@echo "✓ Cleaned"
