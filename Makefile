# Fly-in — Makefile (Chapter III.2 Common Instructions)
# Python 3.10+, flake8, mypy

PYTHON ?= python3
PIP ?= pip

.PHONY: install run debug clean lint lint-strict test benchmark log-result

install:
	$(PIP) install -r requirements-dev.txt

run:
	$(PYTHON) main.py

debug:
	$(PYTHON) -m pdb main.py

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

test:
	$(PYTHON) run_tests.py

benchmark:
	$(PYTHON) benchmark.py

# Log current Challenger result to docs/ALGORITHM_RESULTS.md (usage: make log-result VARIANT="name" DESC="description")
log-result:
	$(PYTHON) scripts/log_challenger_result.py "$(VARIANT)" "$(DESC)"
