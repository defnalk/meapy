.PHONY: install lint test clean docs help

PYTHON  := python
SRC     := src/meapy
TESTS   := tests

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Install package in editable mode with dev extras
	pip install --upgrade pip
	pip install -e ".[dev]"

lint:  ## Run ruff linter + formatter check + mypy type checker
	ruff check $(SRC) $(TESTS)
	ruff format --check $(SRC) $(TESTS)
	mypy $(SRC)

format:  ## Auto-fix ruff lint issues and reformat code
	ruff check --fix $(SRC) $(TESTS)
	ruff format $(SRC) $(TESTS)

test:  ## Run full test suite with coverage (≥ 90 % enforced)
	pytest $(TESTS) \
	  -v \
	  --cov=$(SRC) \
	  --cov-report=term-missing \
	  --cov-fail-under=90

test-unit:  ## Run unit tests only (fast)
	pytest $(TESTS)/unit/ -v

test-integration:  ## Run integration tests only
	pytest $(TESTS)/integration/ -v -m integration

clean:  ## Remove build artefacts and cache directories
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info"  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache"  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache"  -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ coverage.xml .coverage

docs:  ## Build Sphinx documentation (requires docs extras)
	sphinx-build -b html docs/source docs/_build/html

examples:  ## Run all example scripts
	$(PYTHON) examples/heat_exchanger_analysis.py
	$(PYTHON) examples/pump_commissioning.py
