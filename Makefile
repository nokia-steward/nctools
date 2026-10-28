SHELL := /bin/bash -eu -o pipefail
.PHONY: help install check test lint fmt docs docs-serve build clean

UV ?= uv

help: ## Show targets
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install runtime + dev dependencies (uv sync --group dev)
	@command -v $(UV) >/dev/null || { echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
	$(UV) sync --group dev --system-certs

check: test lint ## Tests + lint (core of CI before a PR)
	@:

test: ## pytest
	$(UV) run pytest -q --timeout=120

lint: ## ruff check + format check
	$(UV) run ruff check src tests
	$(UV) run ruff format --check src tests

fmt: ## ruff format + fix
	$(UV) run ruff format src tests
	$(UV) run ruff check --fix src tests

docs: ## mkdocs build (same content as README)
	$(UV) run mkdocs build --strict

docs-serve: ## mkdocs serve locally
	$(UV) run mkdocs serve

build: ## wheel/sdist
	$(UV) run python -m build

clean: ## remove caches and build dirs
	rm -rf build dist site .pytest_cache .ruff_cache
