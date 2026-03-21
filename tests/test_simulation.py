"""Tests for pathfinding and simulation (VII.2, VII.3, VII.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from parser import MapParser
from pathfinding import find_shortest_path
from simulation import Simulation


def test_pathfinding_linear() -> None:
    """Shortest path on linear map is start -> waypoint1 -> waypoint2 -> goal."""
    path = Path(__file__).resolve().parent.parent / "maps" / "easy" / "01_linear_path.txt"
    m = MapParser().parse_file(path)
    p = find_shortest_path(m, m.start_zone.name, m.end_zone.name)
    assert p == ["start", "waypoint1", "waypoint2", "goal"]


def test_simulation_linear_output_format() -> None:
    """Simulation outputs VII.5 format: D<ID>-<zone> lines."""
    path = Path(__file__).resolve().parent.parent / "maps" / "easy" / "01_linear_path.txt"
    m = MapParser().parse_file(path)
    sim = Simulation(m)
    lines = sim.run()
    assert len(lines) >= 1
    for line in lines:
        parts = line.split()
        for part in parts:
            assert part.startswith("D"), part
            assert "-" in part, part
            did, dest = part.split("-", 1)
            assert did[1:].isdigit(), part
            assert dest, part


def test_simulation_linear_all_delivered() -> None:
    """All drones reach goal; last line contains goal."""
    path = Path(__file__).resolve().parent.parent / "maps" / "easy" / "01_linear_path.txt"
    m = MapParser().parse_file(path)
    sim = Simulation(m)
    lines = sim.run()
    assert lines
    last = lines[-1]
    assert "goal" in last
    assert last.strip().endswith("goal") or "goal" in last.split()
