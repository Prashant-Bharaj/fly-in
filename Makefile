UV_RUN := uv run

SRC := main.py parser.py model.py pathfinding.py simulation.py visual.py gui.py

install: pyproject.toml
	command -v uv >/dev/null 2>&1 || pip install uv
	uv sync --group dev

run:
	$(UV_RUN) python main.py

debug:
	$(UV_RUN) python -m pdb main.py

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

lint:
	$(UV_RUN) flake8 $(SRC)
	$(UV_RUN) mypy $(SRC) --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs

lint-strict:
	$(UV_RUN) flake8 $(SRC)
	$(UV_RUN) mypy $(SRC) --strict

test:
	$(UV_RUN) python run_tests.py

benchmark:
	$(UV_RUN) python benchmark.py

log-result:
	$(UV_RUN) python scripts/log_challenger_result.py "$(VARIANT)" "$(DESC)"

.PHONY: install run debug clean lint lint-strict test benchmark log-result

