# --- Shell & Defaults ---
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

# --- Vars ---
UV ?= uv

# --- Phony ---
.PHONY: help bootstrap update env sandbox-image slice dabench-data dabench grade \
	compare test test-all fmt fmt-check lint typecheck typecheck-api test-api \
	qa qa-api precommit clean deep-clean

help: ## Show available targets
	@awk '\
	  BEGIN { FS=":.*##"; printf "\nTargets:\n" } \
	  /^[a-zA-Z0-9_.-]+:.*##/ { \
	    name = $$1; desc = $$2; \
	    gsub(/^[ \t]+|[ \t]+$$/, "", desc); \
	    if (!seen[name]++) printf "  \033[36m%-16s\033[0m %s\n", name, desc; \
	  }' $(MAKEFILE_LIST)

# ---------- Setup ----------
bootstrap: ## Install Python (if needed), sync deps (incl. apps/api), install git hooks
	$(UV) python install
	$(UV) sync --all-packages
	$(UV) run pre-commit install

update: ## Upgrade locked package versions (respecting constraints)
	$(UV) lock --upgrade
	$(UV) sync
	$(UV) run pre-commit autoupdate
	$(UV) run pre-commit install

env: ## Print tool versions
	@echo "Python:  $$($(UV) run python -V)"
	@echo "uv:      $$($(UV) --version)"
	@echo "Ruff:    $$($(UV) run ruff --version || true)"
	@echo "Mypy:    $$($(UV) run mypy --version || true)"
	@echo "pytest:  $$($(UV) run pytest --version | head -n1 || true)"

# ---------- Sandbox ----------
sandbox-image: ## Build the pinned sandbox execution image (statskills-sandbox:0.1.0)
	docker build -f src/statskills/sandbox/Dockerfile \
		-t statskills-sandbox:0.1.0 src/statskills/sandbox

slice: ## Run the authored vertical slice (needs EDENAI_API_KEY; Docker sandbox)
	$(UV) run python scripts/run.py

dabench-data: ## Download the InfiAgent-DABench dev set into data/benchmarks/dabench/
	$(UV) run python scripts/fetch_dabench.py

dabench: ## Run the DABench subset via Ollama (run `make dabench-data` first)
	$(UV) run python scripts/run.py --config configs/dabench_ollama.yaml

grade: ## Grade a saved run (RUN=results/run-...)
	$(UV) run python scripts/grade.py $(RUN)

compare: ## Compare two graded runs (A=results/run-off B=results/run-curated)
	$(UV) run python scripts/compare.py $(A) $(B)

# ---------- Code quality ----------
test: ## Run fast tests (skip slow)
	$(UV) run pytest -m "not slow"

test-all: ## Run all tests including slow
	$(UV) run pytest

fmt: ## Auto-fix lint + format
	$(UV) run ruff check --select I --fix src tests apps || true
	$(UV) run ruff check --fix src tests apps || true
	$(UV) run ruff format .

fmt-check: ## Check formatting (CI gate)
	$(UV) run ruff check --select I src tests apps
	$(UV) run ruff format --check .

lint: ## Ruff lint
	$(UV) run ruff check .

typecheck: ## Mypy type check (core)
	$(UV) run mypy

typecheck-api: ## Mypy type check (apps/api; needs `uv sync --all-packages`)
	MYPYPATH=apps/api/src:apps/api $(UV) run mypy apps/api/src apps/api/tests

test-api: ## Run the apps/api test suite (hermetic; no Docker/API key)
	$(UV) run pytest apps/api/tests

qa: fmt-check typecheck lint test qa-api ## Full quality gate (core + apps/api)

qa-api: typecheck-api test-api ## apps/api gate (mypy + pytest of the member)

precommit: ## Run all pre-commit hooks on tracked files
	$(UV) run pre-commit run --all-files

# ---------- Housekeeping ----------
clean: ## Remove caches
	-rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache .coverage
	-find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	-find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	-find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +

deep-clean: clean ## Also remove env and build artifacts
	-rm -rf .venv htmlcov coverage.xml .dist build dist *.egg-info
