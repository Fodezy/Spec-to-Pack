# Spec-to-Pack Studio Makefile

.PHONY: help install lint test e2e gen package clean

help: ## Show this help message
	@echo "Spec-to-Pack Studio - Make targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Create venv and install dependencies
	python -m venv .venv || python3 -m venv .venv
	. .venv/bin/activate && pip install -e ".[dev]"
	@echo "✅ Installation complete. Activate venv: source .venv/bin/activate"

lint: ## Run ruff, black, isort
	ruff check src tests
	black --check src tests
	isort --check-only src tests
	@echo "✅ Lint checks passed"

format: ## Format code with black and isort
	black src tests
	isort src tests
	ruff check --fix src tests
	@echo "✅ Code formatted"

test: ## Run pytest all tests
	pytest tests/
	@echo "✅ Tests completed"

e2e: ## Run end-to-end acceptance tests
	pytest tests/e2e/
	@echo "✅ E2E tests completed"

gen: ## Run studiogen generate (example)
	studiogen generate \
		--idea fixtures/idea_card.md \
		--decisions fixtures/decision_sheet.md \
		--out ./example_output
	@echo "✅ Generation completed"

package: ## Create zip packages of outputs
	@echo "📦 Packaging outputs..."
	@echo "✅ Packaging completed (stub)"

clean: ## Clean build artifacts and cache
	rm -rf build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	@echo "✅ Cleaned build artifacts"