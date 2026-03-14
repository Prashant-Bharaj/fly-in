#!/usr/bin/env python3
"""Fly-in: main entry point for the drone routing simulation.

This module runs the drone routing system. See subject and maps/README.md.

Usage:
    python main.py <map_file>           # ANSI terminal output
    python main.py <map_file> --gui     # Pygame graphical interface
"""

from __future__ import annotations

import sys
from pathlib import Path

from parser import MapParser, ParseError
from simulation import Simulation
from visual import VisualRenderer


def main() -> None:
    """Parse, simulate, and render the drone routing result."""
    args = [a for a in sys.argv[1:] if a != "--gui"]
    gui_mode = "--gui" in sys.argv[1:]

    if not args:
        print(
            "Usage: python main.py <map_file> [--gui]"
        )
        print(
            "Example: python main.py"
            " maps/easy/01_linear_path.txt"
        )
        return

    path = Path(args[0])
    if not path.exists():
        print(
            f"Error: file not found: {path}",
            file=sys.stderr,
        )
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

    if gui_mode:
        try:
            from gui import SimulationGUI
        except ImportError as e:
            print(
                f"GUI unavailable: {e}",
                file=sys.stderr,
            )
            sys.exit(1)
        SimulationGUI(drone_map, lines).run()
    else:
        renderer = VisualRenderer(drone_map)
        renderer.print_header()
        total = len(lines)
        for turn_num, line in enumerate(lines, 1):
            renderer.print_turn(turn_num, line, total)
        renderer.print_summary(total)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(1) from exc
