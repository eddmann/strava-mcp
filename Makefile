.PHONY: *
.DEFAULT_GOAL := help

SHELL := /bin/bash
IMAGE_NAME := ghcr.io/eddmann/strava-mcp
VERSION := $(shell grep '^version' pyproject.toml | cut -d '"' -f 2)

##@ Setup

install: ## Install dependencies using uv
	uv sync

install/prod: ## Install production dependencies only
	uv sync --no-dev

update: ## Update all dependencies to latest versions
	uv lock --upgrade
	uv sync

lock: ## Regenerate lock file from scratch
	rm -f uv.lock
	uv lock

clean: ## Clean up cache files and build artifacts
	rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/ .pyright/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf dist/ build/ *.egg-info/

##@ Testing/Linting

can-release: test lint ## Run all the same checks as CI to ensure code can be released

test: ## Run the test suite
	uv run pytest

test/%: ## Run tests with a filter (e.g., make test/activity)
	uv run pytest -k $*

test/verbose: ## Run tests with verbose output
	uv run pytest -v

test/coverage: ## Run tests with coverage report
	uv run pytest --cov=src/strava_mcp --cov-report=term-missing

lint: lint/ruff lint/pyright ## Run all linting tools

lint/ruff: ## Run ruff linter
	uv run ruff check

lint/pyright: ## Run pyright type checker
	uv run pyright

fmt: format
format: ## Fix style violations and format code
	uv run ruff check --fix
	uv run ruff format

##@ Development

auth: ## Run the Strava authentication setup
	uv run strava-mcp-auth

run: ## Run the MCP server locally
	uv run strava-mcp

shell: ## Open a Python shell with the project context
	uv run python

##@ Docker

docker/build: ## Build Docker image locally
	docker build -t $(IMAGE_NAME):latest -t $(IMAGE_NAME):$(VERSION) .

docker/build/multiplatform: ## Build multi-platform Docker image
	docker buildx build --platform linux/amd64,linux/arm64 -t $(IMAGE_NAME):latest -t $(IMAGE_NAME):$(VERSION) .

docker/run: ## Run the Docker container locally
	docker run -it --rm \
		-v $(PWD)/.strava_tokens:/app/.strava_tokens \
		-e STRAVA_CLIENT_ID \
		-e STRAVA_CLIENT_SECRET \
		$(IMAGE_NAME):latest

docker/push: ## Push Docker image to registry (requires authentication)
	docker push $(IMAGE_NAME):latest
	docker push $(IMAGE_NAME):$(VERSION)

docker/login: ## Login to GitHub Container Registry
	echo $(GITHUB_TOKEN) | docker login ghcr.io -u $(GITHUB_USER) --password-stdin

##@ Info

version: ## Show current version
	@echo $(VERSION)

deps: ## Show installed dependencies
	uv pip list

info: ## Show project information
	@echo "Project: strava-mcp"
	@echo "Version: $(VERSION)"
	@echo "Python: $$(python --version)"
	@echo "Image: $(IMAGE_NAME)"

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_\-\/]+:.*?##/ { printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
