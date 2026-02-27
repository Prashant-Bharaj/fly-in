"""Domain model for the drone map (Chapter VI). No graph libraries used."""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ZoneType(Enum):
    """Zone type: movement cost and accessibility (Chapter VI)."""

    NORMAL = "normal"       # 1 turn, default
    BLOCKED = "blocked"      # Inaccessible; any path using it is invalid
    RESTRICTED = "restricted"  # 2 turns to enter
    PRIORITY = "priority"    # 1 turn, should be preferred in pathfinding

    def movement_cost(self) -> int:
        """Turns required to enter this zone."""
        if self == ZoneType.BLOCKED:
            return -1  # Cannot enter
        if self == ZoneType.RESTRICTED:
            return 2
        return 1  # normal, priority

    def is_traversable(self) -> bool:
        """True if drones may enter this zone."""
        return self != ZoneType.BLOCKED


class Zone:
    """A zone (hub) in the map: name, coordinates, type, optional color and capacity."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: ZoneType = ZoneType.NORMAL,
        color: Optional[str] = None,
        max_drones: int = 1,
        *,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.max_drones = max_drones
        self.is_start = is_start
        self.is_end = is_end

    def __repr__(self) -> str:
        return f"Zone({self.name!r}, {self.x}, {self.y}, {self.zone_type.value})"


class Connection:
    """A bidirectional connection between two zones with optional link capacity."""

    def __init__(
        self,
        zone_a: str,
        zone_b: str,
        max_link_capacity: int = 1,
    ) -> None:
        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_link_capacity = max_link_capacity

    def pair(self) -> tuple[str, str]:
        """Canonical unordered pair for duplicate detection (a-b same as b-a)."""
        return (min(self.zone_a, self.zone_b), max(self.zone_a, self.zone_b))

    def __repr__(self) -> str:
        return f"Connection({self.zone_a!r}-{self.zone_b!r}, cap={self.max_link_capacity})"


class Map:
    """
    Parsed map: number of drones, start/end zones, all zones and connections.

    Graph is represented without external graph libraries: zones by name,
    connections as edges. Adjacency can be computed from connections.
    """

    def __init__(
        self,
        nb_drones: int,
        start_zone: Zone,
        end_zone: Zone,
        zones: dict[str, Zone],
        connections: list[Connection],
    ) -> None:
        self.nb_drones = nb_drones
        self.start_zone = start_zone
        self.end_zone = end_zone
        self.zones = zones
        self.connections = connections

    def get_zone(self, name: str) -> Optional[Zone]:
        """Return zone by name, or None."""
        return self.zones.get(name)

    def neighbors(self, zone_name: str) -> list[str]:
        """Return list of zone names connected to the given zone (traversable only)."""
        result: list[str] = []
        for conn in self.connections:
            other: Optional[str] = None
            if conn.zone_a == zone_name:
                other = conn.zone_b
            elif conn.zone_b == zone_name:
                other = conn.zone_a
            if other is not None:
                z = self.get_zone(other)
                if z is not None and z.zone_type.is_traversable():
                    result.append(other)
        return result

    def get_connection(self, zone_a: str, zone_b: str) -> Optional[Connection]:
        """Return the connection between two zones (order does not matter), or None."""
        key = (min(zone_a, zone_b), max(zone_a, zone_b))
        for conn in self.connections:
            if conn.pair() == key:
                return conn
        return None

    def connection_name(self, from_zone: str, to_zone: str) -> str:
        """Canonical name for the connection (for VII.5 output: D<ID>-<connection>)."""
        return f"{from_zone}-{to_zone}"
