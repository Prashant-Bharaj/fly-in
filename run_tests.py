#!/usr/bin/env python3
"""Run all tests without pytest (works when pytest is not installed)."""

from __future__ import annotations

import sys
from pathlib import Path

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from parser import MapParser, ParseError
from pathfinding import find_shortest_path
from simulation import Simulation


def _run(name: str, fn: object) -> bool:
    """Run one test; return True if pass."""
    try:
        fn()
        print(f"  OK {name}")
        return True
    except Exception as e:
        print(f"  FAIL {name}: {e}")
        return False


def test_parse_linear_path() -> None:
    path = Path(__file__).resolve().parent / "maps" / "easy" / "01_linear_path.txt"
    parser = MapParser()
    m = parser.parse_file(path)
    assert m.nb_drones == 2
    assert m.start_zone.name == "start"
    assert m.end_zone.name == "goal"
    assert len(m.zones) == 4
    assert len(m.connections) == 3
    assert m.start_zone.zone_type.value == "normal"
    assert m.get_zone("waypoint1") is not None
    assert "waypoint1" in m.neighbors("start")
    assert "start" in m.neighbors("waypoint1")


def test_parse_simple_fork() -> None:
    path = Path(__file__).resolve().parent / "maps" / "easy" / "02_simple_fork.txt"
    parser = MapParser()
    m = parser.parse_file(path)
    assert m.nb_drones == 3
    assert m.start_zone.name == "start"
    assert m.end_zone.name == "goal"
    assert len(m.zones) == 5
    assert len(m.connections) == 5
    junction = m.get_zone("junction")
    assert junction is not None
    assert junction.max_drones == 2


def test_parse_basic_capacity() -> None:
    path = Path(__file__).resolve().parent / "maps" / "easy" / "03_basic_capacity.txt"
    parser = MapParser()
    m = parser.parse_file(path)
    assert m.nb_drones == 4
    assert m.get_zone("bottleneck").max_drones == 2
    assert m.get_zone("wide_area").max_drones == 3


def test_missing_nb_drones_raises() -> None:
    parser = MapParser()
    try:
        parser._parse_lines(["# only comment\n"], Path("x"))
        raise AssertionError("Expected ParseError")
    except ParseError as e:
        assert "nb_drones" in str(e).lower()


def test_duplicate_connection_raises() -> None:
    lines = [
        "nb_drones: 1\n",
        "start_hub: a 0 0\n",
        "end_hub: b 1 0\n",
        "connection: a-b\n",
        "connection: b-a\n",
    ]
    parser = MapParser()
    try:
        parser._parse_lines(lines, Path("x"))
        raise AssertionError("Expected ParseError")
    except ParseError as e:
        assert "duplicate" in str(e).lower() or "same as" in str(e).lower()


def test_invalid_zone_type_raises() -> None:
    lines = [
        "nb_drones: 1\n",
        "start_hub: a 0 0 [zone=invalid]\n",
        "end_hub: b 1 0\n",
    ]
    parser = MapParser()
    try:
        parser._parse_lines(lines, Path("x"))
        raise AssertionError("Expected ParseError")
    except ParseError as e:
        assert "invalid" in str(e).lower() or "zone type" in str(e).lower()


def test_pathfinding_linear() -> None:
    path = Path(__file__).resolve().parent / "maps" / "easy" / "01_linear_path.txt"
    m = MapParser().parse_file(path)
    p = find_shortest_path(m, m.start_zone.name, m.end_zone.name)
    assert p == ["start", "waypoint1", "waypoint2", "goal"]


def test_simulation_linear_output_format() -> None:
    path = Path(__file__).resolve().parent / "maps" / "easy" / "01_linear_path.txt"
    m = MapParser().parse_file(path)
    sim = Simulation(m)
    lines = sim.run()
    assert len(lines) >= 1
    for line in lines:
        for part in line.split():
            assert part.startswith("D"), part
            assert "-" in part, part
            did, dest = part.split("-", 1)
            assert did[1:].isdigit(), part
            assert dest, part


def test_simulation_linear_all_delivered() -> None:
    path = Path(__file__).resolve().parent / "maps" / "easy" / "01_linear_path.txt"
    m = MapParser().parse_file(path)
    sim = Simulation(m)
    lines = sim.run()
    assert lines
    last = lines[-1]
    assert "goal" in last


def main() -> None:
    tests = [
        ("test_parse_linear_path", test_parse_linear_path),
        ("test_parse_simple_fork", test_parse_simple_fork),
        ("test_parse_basic_capacity", test_parse_basic_capacity),
        ("test_missing_nb_drones_raises", test_missing_nb_drones_raises),
        ("test_duplicate_connection_raises", test_duplicate_connection_raises),
        ("test_invalid_zone_type_raises", test_invalid_zone_type_raises),
        ("test_pathfinding_linear", test_pathfinding_linear),
        ("test_simulation_linear_output_format", test_simulation_linear_output_format),
        ("test_simulation_linear_all_delivered", test_simulation_linear_all_delivered),
    ]
    print("Running tests...")
    passed = sum(1 for _, fn in tests if _run(_, fn))
    total = len(tests)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
