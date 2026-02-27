# Fly-in — Makefile (Chapter III.2 Common Instructions)
# Python 3.10+, flake8, mypy. III.3: virtual env recommended — install creates .venv and uses pip.

VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
# Use venv if it exists (after make install), else system python
PYTHON := $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),python3)

.PHONY: install run debug clean lint lint-strict test benchmark log-result

# Create .venv with Python 3 (III.3); install deps with pip. Needs python3-venv on Debian/Ubuntu.
install:
	[ -d $(VENV) ] || python3 -m venv $(VENV)
	$(VENV_PIP) install -r requirements-dev.txt
# After install, $(PYTHON) is .venv/bin/python (Python 3)

run:
	$(PYTHON) main.py

debug:
	$(PYTHON) -m pdb main.py

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Prefer tools from venv when present
lint:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs

lint-strict:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --strict

test:
	$(PYTHON) run_tests.py

benchmark:
	$(PYTHON) benchmark.py

# Log current Challenger result to docs/ALGORITHM_RESULTS.md (usage: make log-result VARIANT="name" DESC="description")
log-result:
	$(PYTHON) scripts/log_challenger_result.py "$(VARIANT)" "$(DESC)"
