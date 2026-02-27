VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
PYTHON := $(VENV_PYTHON)

SRC := main.py parser.py model.py pathfinding.py simulation.py

.PHONY: install run debug clean lint lint-strict test benchmark log-result

install:
	[ -d $(VENV) ] || python3 -m venv $(VENV)
	$(VENV_PIP) install -r requirements-dev.txt

run:
	$(PYTHON) main.py

debug:
	$(PYTHON) -m pdb main.py

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

lint:
	$(PYTHON) -m flake8 $(SRC)
	$(PYTHON) -m mypy $(SRC) --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs

lint-strict:
	$(PYTHON) -m flake8 $(SRC)
	$(PYTHON) -m mypy $(SRC) --strict

test:
	$(PYTHON) run_tests.py

benchmark:
	$(PYTHON) benchmark.py

log-result:
	$(PYTHON) scripts/log_challenger_result.py "$(VARIANT)" "$(DESC)"
