"""
Input parser for drone map files (Chapter VI Let the drone fly, VII.4 Parser constraints).

Reads nb_drones, zones (start_hub, end_hub, hub), and connections with optional
metadata. Validates structure and raises clear errors with line number and cause.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from model import Connection, Map, Zone, ZoneType


class ParseError(Exception):
    """Raised when the map file is invalid. Message includes line number and cause."""

    def __init__(self, line_no: Optional[int], message: str) -> None:
        self.line_no = line_no
        self.message = message
        if line_no is not None:
            super().__init__(f"Line {line_no}: {message}")
        else:
            super().__init__(message)


# Zone type must be one of these (VII.4).
VALID_ZONE_TYPES = frozenset(ZoneType)

# Metadata keys for zones and connections.
ZONE_META_KEYS = frozenset({"zone", "color", "max_drones"})
CONN_META_KEYS = frozenset({"max_link_capacity"})


def _parse_metadata(s: str, allowed_keys: frozenset[str]) -> dict[str, str]:
    """Parse [key=value key=value ...] into a dict. Values are single tokens."""
    s = s.strip()
    if not s.startswith("[") or not s.endswith("]"):
        raise ValueError("Metadata must be enclosed in [...]")
    inner = s[1:-1].strip()
    if not inner:
        return {}
    out: dict[str, str] = {}
    for part in inner.split():
        if "=" not in part:
            raise ValueError(f"Invalid metadata token: {part!r}")
        key, _, value = part.partition("=")
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise ValueError(f"Invalid metadata key=value: {part!r}")
        if key not in allowed_keys:
            raise ValueError(f"Unknown metadata key: {key!r}")
        out[key] = value
    return out


def _parse_zone_type(raw: str) -> ZoneType:
    """Parse zone type string; raise if invalid (VII.4)."""
    try:
        return ZoneType(raw.strip().lower())
    except ValueError:
        raise ValueError(
            f"Invalid zone type: {raw!r}. Must be one of: "
            "normal, blocked, restricted, priority"
        )


def _positive_int(value: str, name: str) -> int:
    """Parse positive integer; raise with clear message."""
    value = value.strip()
    if not value:
        raise ValueError(f"{name} must not be empty")
    try:
        n = int(value)
    except ValueError:
        raise ValueError(f"{name} must be an integer: {value!r}")
    if n < 1:
        raise ValueError(f"{name} must be a positive integer: {n}")
    return n


def _parse_zone_line(
    line: str,
    line_no: int,
    kind: str,
) -> tuple[str, int, int, dict[str, str]]:
    """
    Parse start_hub / end_hub / hub line.
    Returns (name, x, y, metadata_dict). Metadata may be empty.
    """
    # Prefix already stripped by caller: "start_hub:", "end_hub:", "hub:"
    rest = line.strip()
    if not rest:
        raise ParseError(line_no, f"Missing name and coordinates after {kind}")

    # Optional metadata at the end [...]
    meta: dict[str, str] = {}
    bracket = rest.find("[")
    if bracket >= 0:
        if "]" not in rest[bracket:]:
            raise ParseError(line_no, "Unclosed metadata bracket [...]")
        meta_str = rest[bracket:]
        rest = rest[:bracket].strip()
        meta = _parse_metadata(meta_str, ZONE_META_KEYS)

    parts = rest.split()
    if len(parts) < 3:
        raise ParseError(
            line_no,
            f"{kind} requires name and two integer coordinates (x y)",
        )
    name = parts[0]
    if "-" in name or " " in name:
        raise ParseError(
            line_no,
            "Zone names cannot contain dashes or spaces (connection syntax)",
        )
    try:
        x, y = int(parts[1]), int(parts[2])
    except ValueError:
        raise ParseError(line_no, "Zone coordinates must be integers")
    if len(parts) > 3:
        raise ParseError(line_no, "Extra tokens after coordinates (put metadata in [...])")

    return (name, x, y, meta)


def _parse_connection_line(rest: str, line_no: int) -> tuple[str, str, dict[str, str]]:
    """Parse zone1-zone2 [metadata] (content after 'connection:'). Returns (name1, name2, metadata)."""
    rest = rest.strip()
    if not rest:
        raise ParseError(line_no, "Missing zone1-zone2 after connection:")

    meta: dict[str, str] = {}
    bracket = rest.find("[")
    if bracket >= 0:
        if "]" not in rest[bracket:]:
            raise ParseError(line_no, "Unclosed metadata bracket [...]")
        meta_str = rest[bracket:]
        rest = rest[:bracket].strip()
        meta = _parse_metadata(meta_str, CONN_META_KEYS)

    if "-" not in rest:
        raise ParseError(line_no, "Connection must be zone1-zone2 (exactly one dash)")
    parts = rest.split("-", 1)
    zone_a, zone_b = parts[0].strip(), parts[1].strip()
    if not zone_a or not zone_b:
        raise ParseError(line_no, "Both zone names in connection must be non-empty")
    if " " in zone_a or " " in zone_b:
        raise ParseError(line_no, "Zone names cannot contain spaces")

    return (zone_a, zone_b, meta)


class MapParser:
    """
    Parses a map file (Chapter VI format) into a Map object.

    Enforces VII.4: first line nb_drones, exactly one start and end hub,
    unique zone names, connections only to defined zones, no duplicate
    connections, valid zone types and positive capacities.
    """

    def __init__(self) -> None:
        self._zones: dict[str, Zone] = {}
        self._connections: list[Connection] = []
        self._start: Optional[Zone] = None
        self._end: Optional[Zone] = None
        self._nb_drones: Optional[int] = None
        self._seen_connection_pairs: set[tuple[str, str]] = set()

    def parse_file(self, path: Path) -> Map:
        """
        Parse the map file and return a Map. Uses context manager for the file.

        Raises:
            ParseError: On any syntax or validation error (with line number and cause).
        """
        with open(path, encoding="utf-8") as f:
            return self._parse_lines(f, path)

    def _parse_lines(self, lines: Any, path: Path) -> Map:
        self._zones = {}
        self._connections = []
        self._start = None
        self._end = None
        self._nb_drones = None
        self._seen_connection_pairs = set()

        line_no = 0
        phase: str = "header"  # header -> zones -> connections

        for raw in lines:
            line_no += 1
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            if phase == "header":
                if not line.startswith("nb_drones:"):
                    raise ParseError(
                        line_no,
                        "First non-comment line must be nb_drones: <positive_integer>",
                    )
                rest = line[len("nb_drones:"):].strip()
                try:
                    self._nb_drones = _positive_int(rest, "nb_drones")
                except ValueError as e:
                    raise ParseError(line_no, str(e))
                phase = "zones"
                continue

            if line.startswith("connection:"):
                phase = "connections"
                # fall through to parse this connection line below

            if phase == "zones":
                if line.startswith("connection:"):
                    phase = "connections"
                    # parse connection in same iteration
                else:
                    self._parse_zone_line_at(line_no, line)
                    continue

            if phase == "connections":
                if not line.startswith("connection:"):
                    raise ParseError(
                        line_no,
                        "Expected connection: zone1-zone2 or zone definitions before connections",
                    )
                self._parse_connection_line_at(line_no, line)

        if self._nb_drones is None:
            raise ParseError(None, "File must define nb_drones: <positive_integer>")
        if self._start is None:
            raise ParseError(None, "File must define exactly one start_hub:")
        if self._end is None:
            raise ParseError(None, "File must define exactly one end_hub:")

        return Map(
            nb_drones=self._nb_drones,
            start_zone=self._start,
            end_zone=self._end,
            zones=dict(self._zones),
            connections=list(self._connections),
        )

    def _parse_zone_line_at(self, line_no: int, line: str) -> None:
        """Parse a single zone line and add to state."""
        def make_zone(
            n: str, xx: int, yy: int, m: dict[str, str], start: bool, end: bool
        ) -> Zone:
            try:
                return self._zone_from_meta(n, xx, yy, m, is_start=start, is_end=end)
            except ValueError as e:
                raise ParseError(line_no, str(e)) from e

        if line.startswith("start_hub:"):
            rest = line[len("start_hub:"):]
            name, x, y, meta = _parse_zone_line(rest, line_no, "start_hub")
            if self._start is not None:
                raise ParseError(line_no, "Duplicate start_hub: exactly one allowed")
            zone = make_zone(name, x, y, meta, True, False)
            self._zones[name] = zone
            self._start = zone
            return
        if line.startswith("end_hub:"):
            rest = line[len("end_hub:"):]
            name, x, y, meta = _parse_zone_line(rest, line_no, "end_hub")
            if self._end is not None:
                raise ParseError(line_no, "Duplicate end_hub: exactly one allowed")
            zone = make_zone(name, x, y, meta, False, True)
            self._zones[name] = zone
            self._end = zone
            return
        if line.startswith("hub:"):
            rest = line[len("hub:"):]
            name, x, y, meta = _parse_zone_line(rest, line_no, "hub")
            if name in self._zones:
                raise ParseError(line_no, f"Duplicate zone name: {name!r}")
            zone = make_zone(name, x, y, meta, False, False)
            self._zones[name] = zone
            return
        raise ParseError(
            line_no,
            "Expected start_hub:, end_hub:, or hub: (or connection: after zones)",
        )

    def _zone_from_meta(
        self,
        name: str,
        x: int,
        y: int,
        meta: dict[str, str],
        *,
        is_start: bool,
        is_end: bool,
    ) -> Zone:
        """Build a Zone from name, coords, and metadata dict."""
        zone_type = ZoneType.NORMAL
        color: Optional[str] = None
        max_drones = 1
        for k, v in meta.items():
            if k == "zone":
                zone_type = _parse_zone_type(v)
            elif k == "color":
                v = v.strip()
                if not v or " " in v:
                    raise ValueError("color must be a single-word string")
                color = v
            elif k == "max_drones":
                max_drones = _positive_int(v, "max_drones")
        return Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            max_drones=max_drones,
            is_start=is_start,
            is_end=is_end,
        )

    def _parse_connection_line_at(self, line_no: int, line: str) -> None:
        """Parse a single connection line and add to state."""
        rest = line[len("connection:"):].strip()
        zone_a, zone_b, meta = _parse_connection_line(rest, line_no)

        for zname in (zone_a, zone_b):
            if zname not in self._zones:
                raise ParseError(line_no, f"Connection references undefined zone: {zname!r}")

        pair = (min(zone_a, zone_b), max(zone_a, zone_b))
        if pair in self._seen_connection_pairs:
            raise ParseError(
                line_no,
                f"Duplicate connection: {zone_a}-{zone_b} (same as {zone_b}-{zone_a})",
            )
        self._seen_connection_pairs.add(pair)

        max_link_capacity = 1
        for k, v in meta.items():
            if k == "max_link_capacity":
                max_link_capacity = _positive_int(v, "max_link_capacity")

        self._connections.append(
            Connection(zone_a=zone_a, zone_b=zone_b, max_link_capacity=max_link_capacity)
        )
