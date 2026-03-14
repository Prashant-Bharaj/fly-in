*This project has been created as part of the 42 curriculum by prasingh*

# Fly-in

## Description

Fly-in is a drone routing system. You are given a map: a graph of **zones** (nodes) and **connections** (edges). One zone is the **start**, one is the **end**. A number of drones start in the start zone and must all reach the end zone. The simulation runs in **discrete turns**: each turn, each drone may move to an adjacent zone or stay put. Moving into a zone has a **cost in turns** (1 for normal/priority zones, 2 for restricted zones; blocked zones cannot be entered). Zones and connections can have **capacity limits** (e.g. at most one drone in a zone, or at most two on a link per turn). The goal is to move all drones to the end in **as few turns as possible**.

Maps are text files: they define the number of drones, zones (start, end, and hubs with optional type, color, and max capacity), and connections between zones. The program parses a map file, runs the simulation respecting all movement and capacity rules, and outputs one line per turn listing the moves (e.g. `D1-zoneName D2-zoneName`).

---

## Map File Format

Map files use the following structure:

```
nb_drones: 5
start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: roof2 6 2 [zone=normal color=blue]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: tunnelB 7 4 [zone=normal color=red]
hub: obstacleX 5 5 [zone=blocked color=gray]
connection: hub-roof1
connection: hub-corridorA
connection: roof1-roof2
connection: corridorA-tunnelB [max_link_capacity=2]
connection: tunnelB-goal
```

- First line: `nb_drones: <number>` — number of drones to route.
- `start_hub: <name> <x> <y> [metadata]` — unique start zone.
- `end_hub: <name> <x> <y> [metadata]` — unique end zone.
- `hub: <name> <x> <y> [metadata]` — regular intermediate zone.
- `connection: <zone1>-<zone2> [metadata]` — bidirectional edge; zone names may not contain dashes.
- Comments start with `#` and are ignored.
- Zone coordinates are always positive integers.

### Zone Metadata (all optional, brackets `[...]`, any order)

| Key | Default | Description |
|-----|---------|-------------|
| `zone=<type>` | `normal` | Zone type (see below) |
| `color=<value>` | none | Any single-word color string for visual output |
| `max_drones=<n>` | `1` | Max drones that can occupy this zone simultaneously |

### Zone Types

| Type | Movement Cost | Notes |
|------|--------------|-------|
| `normal` | 1 turn | Default |
| `priority` | 1 turn | Preferred in pathfinding |
| `restricted` | 2 turns | Drone occupies connection during transit; must arrive next turn |
| `blocked` | N/A | Inaccessible — drones may not enter |

### Connection Metadata (optional)

| Key | Default | Description |
|-----|---------|-------------|
| `max_link_capacity=<n>` | `1` | Max drones traversing this connection simultaneously |

---

## Constraints

The project must respect the following:

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

## Zone Occupancy Rules

- By default, a zone may contain at most **one drone** at any given turn.
- Zones with `max_drones=N` can hold up to N drones simultaneously.
- **Exceptions:**
  - **Start zone:** all drones begin here and may share the space initially.
  - **End zone:** multiple drones can arrive here and are considered delivered.
- Two drones may not enter the same zone on the same turn unless the zone's capacity allows it.
- A drone may not move into a zone that would exceed its maximum capacity.
- `max_link_capacity` limits how many drones can traverse the same connection simultaneously.
- Drones moving out of a zone free up capacity for that same turn.

---

## Movement and Turn Mechanics

The simulation proceeds in discrete turns. Each turn, every drone may:

- **Move** to an adjacent connected zone (if capacity allows).
- **Enter transit** toward a restricted zone (occupies the connection for 1 turn, then must arrive — cannot wait on the connection).
- **Stay in place** (waiting, or blocked).

Movement costs (based on destination zone type):

| Destination | Cost |
|-------------|------|
| `normal` | 1 turn |
| `priority` | 1 turn (preferred) |
| `restricted` | 2 turns (drone in transit on connection during turn 1, arrives on turn 2) |
| `blocked` | Cannot be entered |

---

## Parser Constraints

- First line must be `nb_drones: <positive_integer>`.
- Exactly one `start_hub:` and one `end_hub:` must exist.
- Each zone must have a unique name and valid integer coordinates.
- Zone names may use any valid characters except **dashes** and **spaces**.
- Connections must reference only previously defined zones.
- The same connection must not appear more than once (`a-b` and `b-a` are duplicates).
- Zone types must be one of: `normal`, `blocked`, `restricted`, `priority` — any invalid type raises a parsing error.
- Capacity values must be positive integers.
- Any other parsing error stops the program with a clear message indicating the line and cause.

---

## Simulation Output Format

- One line per simulation turn listing all drone movements, space-separated.
- Format per move: `D<ID>-<zone>` or `D<ID>-<connection>` (for drones in transit to a restricted zone).
- Drones that do not move in a turn are omitted.
- Drones that reach the end zone are delivered and no longer tracked.
- Simulation ends when all drones reach the end zone.

Example output:
```
D1-roof1 D2-corridorA
D1-roof2 D2-tunnelB
D1-goal D2-goal
```

---

## Scoring System

Performance is evaluated by the **total number of simulation turns** to route all drones. Fewer turns = better score.

A valid simulation must:
- Comply with all movement and occupancy rules.
- Correctly handle movement costs for each zone type.
- Respect all zone and connection capacity constraints.
- Avoid all conflicts (e.g., exceeding capacity).

Secondary (optional) metrics (encouraged but not mandatory):
- Number of drones moved per turn (throughput).
- Average turns per drone.
- Total path cost (sum of weighted movement costs across all drones).
- Quality and usefulness of visual representation.

---

## Instructions

### Setup

We use `uv` for dependency management and virtual environment setup. `make install` installs `uv` if needed and runs `uv sync --group dev`, which installs dependencies from `pyproject.toml`. After that, `make run` and `make lint` execute via `uv run`.

```bash
make install
```

If you prefer installing it manually first, see: `https://docs.astral.sh/uv/`.

To run the simulation directly with uv, pass a map file path:

```bash
uv run python main.py path/to/map.txt
```

Example: `uv run python main.py maps/easy/01_linear_path.txt`

Optional: activate the venv yourself (`source .venv/bin/activate`) for ad‑hoc commands.

### Makefile targets

| Target        | Description                                      |
|---------------|--------------------------------------------------|
| `make install` | Install/sync dependencies from `pyproject.toml` |
| `make run`     | Run the main script                             |
| `make debug`   | Run under Python debugger (pdb)                 |
| `make clean`   | Remove `__pycache__`, `.mypy_cache`, caches     |
| `make lint`    | flake8 + mypy (required flags)                  |
| `make lint-strict` | flake8 + mypy --strict (recommended)       |

### General rules

- Python 3.10+, flake8, type hints and mypy, docstrings (PEP 257), exception handling and context managers.

### Tests

Unit tests are used locally for verification (not submitted).

---

## Resources

- **Pathfinding and graphs**: `https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm`, `https://cp-algorithms.com/graph/breadth-first-search.html`
- **Python typing and static analysis**: `https://docs.python.org/3/library/typing.html`, `https://mypy.readthedocs.io/`
- **Code style and linting**: `https://peps.python.org/pep-0008/`, `https://flake8.pycqa.org/`
- **AI usage**: 
  - AI is used to understand the subject, input/output format, understand and brainstrom different algorithms.
  - Also used AI to try out different algorithms and compare there results.



---

## Algorithm and implementation strategy

The implementation is organized into separate modules for parsing, modeling, pathfinding, and simulation:

- **Parsing and model**: `parser.py` reads the map file format (zones, connections, metadata) and builds a `Map` made of `Zone` and `Connection` objects defined in `model.py`. All constraints from the subject (unique start/end, valid types, capacities, no duplicate connections, etc.) are enforced here.
- **Pathfinding**: `pathfinding.py` computes shortest paths using Dijkstra’s algorithm, where edge weights are derived from the movement cost of the destination zone (1 turn for normal/priority, 2 turns for restricted, blocked is not traversable). For larger drone counts, it can compute several diverse paths and assign drones in a round-robin way to reduce bottlenecks.
- **Simulation engine**: `simulation.py` runs the turn-by-turn simulation. Each drone is either **in a zone** or **in transit** toward a restricted zone. At every turn, the engine:
  - Processes arrivals from restricted connections.
  - Recomputes zone occupancy and connection usage.
  - Schedules moves along the precomputed paths, honoring zone capacities (`max_drones`), connection capacities (`max_link_capacity`), and multi-turn moves to restricted zones.
  - Emits one output line per turn in the required `D<ID>-<zone>` / `D<ID>-<connection>` format.
  If no drone can move and some drones are still undelivered, the simulation stops with a clear error to avoid deadlocks.
- **Complexity considerations**: Pathfinding is \(O((V + E) \log V)\) per Dijkstra run, and each simulation turn iterates over all drones and their paths with simple dictionary lookups for capacities, which scales well for the provided maps.

The overall strategy is to precompute good paths once, then use a capacity-aware scheduler each turn to keep the main bottlenecks flowing while avoiding invalid moves or deadlocks.

---

## Visual representation

The project currently uses a **text-based visual representation**:

- Each simulation turn is printed as a single line, listing all drone moves in the required format (e.g. `D1-roof1 D2-corridorA`).
- By reading the log line by line, you can follow how drones progress through the network, where they wait, and how bottlenecks behave.
- This simple output is easy to inspect in a terminal, save to a file, or feed into additional visualization tools if desired.

---

## Bonus Part

Reviewed only if all mandatory requirements are met:

- **Exceptional performance:** Meet or beat all reference performance targets for every provided map (exactly at or fewer turns than the target).
- **Challenger map:** Solve *The Impossible Dream* (25 drones) and beat the reference record of **41 turns**.

---

## Performance benchmarks

Expected optimization level:

- **Easy maps:** &lt; 10 turns
- **Medium maps:** 10–30 turns  
- **Hard maps:** &lt; 60 turns  
- **Challenger (optional):** aim to beat 41 turns

Reference targets per map:

| Category | Map | Target |
|----------|-----|--------|
| Easy | Linear path (2 drones) | ≤ 6 |
| Easy | Simple fork (3 drones) | ≤ 6 |
| Easy | Basic capacity (4 drones) | ≤ 8 |
| Medium | Dead end trap (5 drones) | ≤ 15 |
| Medium | Circular loop (6 drones) | ≤ 20 |
| Medium | Priority puzzle (4 drones) | ≤ 12 |
| Hard | Maze nightmare (8 drones) | ≤ 45 |
| Hard | Capacity hell (12 drones) | ≤ 60 |
| Hard | Ultimate challenge (15 drones) | ≤ 35 |
| Challenger (optional) | The Impossible Dream (25 drones) | &lt; 41 (record) |

### Faced Questions

- **Can the algorithm meet the performance benchmarks?**  
  Yes for all easy, medium, and hard maps. Challenger is optional; the current implementation solves it but does not beat the 41-turn record.

- **How does the solution compare to the reference targets?**  
  The implementation uses shortest path by turn cost (Dijkstra) and a per-turn scheduler that respects zone and link capacity. It meets or beats the listed targets for the non-challenger maps.

- **What optimizations were implemented?**  
  (1) Shortest path by turn cost (Dijkstra; cost = destination zone movement cost). (2) Per-turn scheduling with zone and link capacity and restricted-zone arrival checks. (3) For maps with many drones, diverse paths and round-robin assignment to reduce bottleneck queueing. Further optimizations (e.g. look-ahead scheduling) can improve turn count.

- **Can the Challenger map be solved in under 41 turns?**  
  The Challenger map is solved. Beating 41 turns is not doable on this map: the start has a single capacity-1 exit and the shortest path has cost 19, so the theoretical minimum is **19 + 24 = 43** turns; the bonus target (41) is below that minimum.
