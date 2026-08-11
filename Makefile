RUFF ?= ruff
PYTEST ?= pytest

.PHONY: lint
lint: lint-python

.PHONY: lint-python
lint-python:
	@echo ">> lint python"
	@$(RUFF) check .
	@$(RUFF) format --check .

.PHONY: test
test: test-unit

.PHONY: test-unit
test-unit:
	@echo ">> unit test"
	@$(PYTEST) \
		--cov=custom_components/callmebot \
		--cov-report=term-missing \
		--cov-report=xml \
		tests
