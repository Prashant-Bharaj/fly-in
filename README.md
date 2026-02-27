# Fly-in

Drone routing system: route a fleet of drones from start to end through connected zones (see subject and `maps/README.md`).

## Constraints (Chapter V)

These constraints are mandatory and must be respected:

### Forbidden

- **Graph libraries:** Any library that implements or helps with graph logic is **forbidden**. Examples:
  - `networkx`
  - `graphlib` (stdlib)
  - Any other graph/network library
- Graph representation, pathfinding, and routing must be implemented **by hand** (your own data structures and algorithms).

### Required

- **flake8:** The project must comply with the flake8 coding standard. Run `make lint` (or `make lint-strict`).
- **mypy:** The project must be fully type-checked with mypy and pass without errors. Run `make lint` (or `make lint-strict`).
- **Object-oriented:** The project must be **completely object-oriented**. Logic must be organized in classes and objects; this will be checked during peer review.

---

## Chapter III — Common Instructions

### Setup

Use a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
make install
```

### Makefile targets

| Target        | Description                                      |
|---------------|--------------------------------------------------|
| `make install` | Install dependencies (flake8, mypy, pytest)     |
| `make run`     | Run the main script                             |
| `make debug`   | Run under Python debugger (pdb)                 |
| `make clean`   | Remove `__pycache__`, `.mypy_cache`, caches     |
| `make lint`    | flake8 + mypy (required flags)                  |
| `make lint-strict` | flake8 + mypy --strict (recommended)       |

### General rules (III.1)

- Python 3.10+, flake8, type hints and mypy, docstrings (PEP 257), exception handling and context managers.
- See `.cursor/rules/common-instructions.mdc` for the full checklist.

### Tests (III.3)

Tests live in `tests/`. Run without pytest: `make test` or `python3 run_tests.py`. With pytest: `pytest tests/ -v`.

---

## VII.7 Performance Benchmarks

Expected optimization level (subject reference):

- **Easy maps:** &lt; 10 turns
- **Medium maps:** 10–30 turns  
- **Hard maps:** &lt; 60 turns  
- **Challenger (optional):** aim to beat 41 turns

Reference targets per map:

| Category | Map | Target | Run `make benchmark` to see current turns |
|----------|-----|--------|------------------------------------------|
| Easy | Linear path (2 drones) | ≤ 6 | |
| Easy | Simple fork (3 drones) | ≤ 6 | |
| Easy | Basic capacity (4 drones) | ≤ 8 | |
| Medium | Dead end trap (5 drones) | ≤ 15 | |
| Medium | Circular loop (6 drones) | ≤ 20 | |
| Medium | Priority puzzle (4 drones) | ≤ 12 | |
| Hard | Maze nightmare (8 drones) | ≤ 45 | |
| Hard | Capacity hell (12 drones) | ≤ 60 | |
| Hard | Ultimate challenge (15 drones) | ≤ 35 | |
| Challenger (optional) | The Impossible Dream (25 drones) | &lt; 41 (record) | |

### Answers (peer evaluation)

- **Can your algorithm meet these performance benchmarks?**  
  Yes for all easy, medium, and hard maps (see `make benchmark`). Challenger is optional; current implementation solves it but does not beat the 41-turn record.

- **How does your solution compare to the reference targets?**  
  Run `make benchmark` (or `python3 benchmark.py`) to print actual turn counts vs targets. The implementation uses a single shortest path (Dijkstra by zone cost) and a greedy per-turn scheduler that respects zone and link capacity; it meets or beats the listed targets for the non-challenger maps.

- **What optimizations did you implement to achieve better performance?**  
  (1) Shortest path by turn cost (Dijkstra, cost = destination zone movement cost). (2) Per-turn scheduling that respects zone capacity and link capacity and avoids over-subscribing restricted-zone arrivals. (3) All drones share the same path and advance in order, which keeps throughput high on linear or fork-shaped maps. Further optimizations (e.g. multiple paths, look-ahead scheduling, Challenger-specific tuning) can improve turn count further.

- **Can you solve the Challenger map and beat the 41-turn record?**  
  The Challenger map is **solved** (our best: 52 turns; colleague’s best: 43). **Beating 41 turns is not doable** for this map: the start has a single capacity-1 exit and the shortest path has cost 19, so the theoretical minimum is **19 + 24 = 43** turns. The bonus target (41) is below that minimum. See **docs/CHALLENGER_REPORT.md** for the proof and **docs/ALGORITHM_RESULTS.md** for logged variants.
