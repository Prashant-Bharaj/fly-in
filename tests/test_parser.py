"""Tests for the map parser (Chapter VI, VII.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from parser import MapParser, ParseError


def test_parse_linear_path() -> None:
    """Parse maps/easy/01_linear_path.txt."""
    path = Path(__file__).resolve().parent.parent / "maps" / "easy" / "01_linear_path.txt"
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
    """Parse maps/easy/02_simple_fork.txt."""
    path = Path(__file__).resolve().parent.parent / "maps" / "easy" / "02_simple_fork.txt"
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
    """Parse maps/easy/03_basic_capacity.txt."""
    path = Path(__file__).resolve().parent.parent / "maps" / "easy" / "03_basic_capacity.txt"
    parser = MapParser()
    m = parser.parse_file(path)
    assert m.nb_drones == 4
    assert m.get_zone("bottleneck").max_drones == 2
    assert m.get_zone("wide_area").max_drones == 3


def test_missing_nb_drones_raises() -> None:
    """Missing nb_drones raises ParseError."""
    parser = MapParser()
    with pytest.raises(ParseError) as exc_info:
        parser._parse_lines(["# only comment\n"], Path("x"))
    assert "nb_drones" in str(exc_info.value).lower()


def test_duplicate_connection_raises() -> None:
    """Duplicate connection (a-b and b-a) raises ParseError."""
    lines = [
        "nb_drones: 1\n",
        "start_hub: a 0 0\n",
        "end_hub: b 1 0\n",
        "connection: a-b\n",
        "connection: b-a\n",
    ]
    parser = MapParser()
    with pytest.raises(ParseError) as exc_info:
        parser._parse_lines(lines, Path("x"))
    assert "duplicate" in str(exc_info.value).lower() or "same as" in str(exc_info.value).lower()


def test_invalid_zone_type_raises() -> None:
    """Invalid zone type raises ParseError."""
    lines = [
        "nb_drones: 1\n",
        "start_hub: a 0 0 [zone=invalid]\n",
        "end_hub: b 1 0\n",
    ]
    parser = MapParser()
    with pytest.raises(ParseError) as exc_info:
        parser._parse_lines(lines, Path("x"))
    assert "invalid" in str(exc_info.value).lower() or "zone type" in str(exc_info.value).lower()
