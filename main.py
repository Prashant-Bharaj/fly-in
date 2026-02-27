#!/usr/bin/env python3
"""Fly-in: main entry point for the drone routing simulation.

This module runs the drone routing system. See subject and maps/README.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

from parser import MapParser, ParseError
from simulation import Simulation


def main() -> None:
    """Run the drone routing simulation: parse map, run turns, output VII.5 format."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <map_file>")
        print("Example: python main.py maps/easy/01_linear_path.txt")
        return
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        parser = MapParser()
        drone_map = parser.parse_file(path)
    except ParseError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        sim = Simulation(drone_map)
        lines = sim.run()
    except (ValueError, RuntimeError) as e:
        print(f"Simulation error: {e}", file=sys.stderr)
        sys.exit(1)
    for line in lines:
        print(line)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(1) from exc
