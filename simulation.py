"""
Simulation engine: turn-by-turn movement with zone and link capacity (VII.2, VII.3).

Tracks drone state (in zone or in transit to restricted), respects max_drones
and max_link_capacity, outputs VII.5 format per turn.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from model import Map, Zone
from pathfinding import find_diverse_paths, find_shortest_path


@dataclass
class InZone:
    """Drone is in a zone."""

    zone: str


@dataclass
class InTransit:
    """Drone is on a connection toward a restricted zone; arrives next turn."""

    from_zone: str
    to_zone: str


DroneState = InZone | InTransit


def _connection_key(a: str, b: str) -> Tuple[str, str]:
    """Canonical key for a connection (unordered)."""
    return (min(a, b), max(a, b))


class Simulation:
    """
    Runs the drone simulation: discrete turns, capacity constraints, VII.5 output.

    Each turn: process arrivals (InTransit -> zone), then schedule moves along
    paths (zone + link capacity). Drones that reach end are delivered and omitted.
    """

    def __init__(self, drone_map: Map) -> None:
        self.drone_map = drone_map
        self.n = drone_map.nb_drones
        start_name = drone_map.start_zone.name
        end_name = drone_map.end_zone.name
        self.end_name = end_name
        self.start_name = start_name

        # Use multiple diverse paths only when many drones (e.g. Challenger) to avoid hurting smaller maps
        if self.n >= 15:
            path_list = find_diverse_paths(
                drone_map, start_name, end_name, k=min(12, self.n)
            )
        else:
            base = find_shortest_path(drone_map, start_name, end_name)
            path_list = [base] if base else []

        if not path_list:
            raise ValueError("No path from start to end")
        # Round-robin: spread drones across paths to avoid single-path bottlenecks
        k = len(path_list)
        self.paths = [
            list(path_list[(i - 1) % k]) for i in range(1, self.n + 1)
        ]

    def run(self) -> List[str]:
        """
        Run simulation until all drones delivered. Returns list of output lines
        (one per turn), VII.5 format: space-separated D<ID>-<zone> or D<ID>-<connection>.
        """
        # state[drone_id] = InZone(name) or InTransit(from, to). Drone IDs 1..n.
        state: Dict[int, DroneState] = {}
        for i in range(1, self.n + 1):
            state[i] = InZone(self.start_name)

        lines: List[str] = []
        while True:
            # Zone occupancy at start of turn (after we process arrivals)
            zone_count: Dict[str, int] = {z: 0 for z in self.drone_map.zones}
            link_usage: Dict[Tuple[str, str], int] = {}
            for conn in self.drone_map.connections:
                link_usage[conn.pair()] = 0
            # 1) Process arrivals: InTransit -> InZone(to)
            moves_this_turn: List[str] = []
            arrived_this_turn: set[int] = set()
            for did, s in list(state.items()):
                if isinstance(s, InTransit):
                    to_zone = s.to_zone
                    state[did] = InZone(to_zone)
                    zone_count[to_zone] = zone_count.get(to_zone, 0) + 1
                    arrived_this_turn.add(did)
                    if to_zone == self.end_name:
                        moves_this_turn.append(f"D{did}-{to_zone}")
                        del state[did]
                    else:
                        moves_this_turn.append(f"D{did}-{to_zone}")

            # 2) Count current occupancy (drones already in zones; arrivals already counted in step 1)
            for did, s in state.items():
                if did in arrived_this_turn:
                    continue
                if isinstance(s, InZone):
                    zone_count[s.zone] = zone_count.get(s.zone, 0) + 1

            # How many are InTransit to each zone (for scheduling restricted moves)
            in_transit_to: Dict[str, int] = {z: 0 for z in self.drone_map.zones}
            for s in state.values():
                if isinstance(s, InTransit):
                    in_transit_to[s.to_zone] = in_transit_to.get(s.to_zone, 0) + 1

            # 3) Schedule moves: feed start first (keep bottleneck flowing), then furthest along
            def _path_index(did: int) -> int:
                s = state.get(did)
                if s is None:
                    return -1
                if isinstance(s, InTransit):
                    path = self.paths[did - 1]
                    try:
                        return path.index(s.to_zone)
                    except ValueError:
                        return -1
                assert isinstance(s, InZone)
                path = self.paths[did - 1]
                try:
                    return path.index(s.zone)
                except ValueError:
                    return -1

            # Drones furthest along path first (clear the way for those behind)
            sorted_drones = sorted(
                state.keys(),
                key=lambda did: -_path_index(did),
            )
            for did in sorted_drones:
                if did in arrived_this_turn:
                    continue  # already used their move (arrival) this turn
                s = state.get(did)
                if s is None:
                    continue
                if isinstance(s, InTransit):
                    continue  # already processed
                assert isinstance(s, InZone)
                current = s.zone
                if current == self.end_name:
                    del state[did]
                    continue
                path = self.paths[did - 1]
                try:
                    idx = path.index(current)
                except ValueError:
                    continue
                if idx + 1 >= len(path):
                    continue
                next_zone = path[idx + 1]
                next_z = self.drone_map.get_zone(next_zone)
                if next_z is None or not next_z.zone_type.is_traversable():
                    continue

                conn = self.drone_map.get_connection(current, next_zone)
                if conn is None:
                    continue
                link_key = conn.pair()
                link_cap = conn.max_link_capacity
                if link_usage.get(link_key, 0) >= link_cap:
                    continue

                # Capacity for destination zone (end has no limit)
                if not next_z.is_end:
                    if zone_count.get(next_zone, 0) >= next_z.max_drones:
                        continue

                if next_z.zone_type.value == "restricted":
                    # When we arrive next turn, zone must have room
                    if not next_z.is_end:
                        # current in zone + already arriving there + this drone
                        if (
                            zone_count.get(next_zone, 0)
                            + in_transit_to.get(next_zone, 0)
                            >= next_z.max_drones
                        ):
                            continue
                    # Commit: start move to restricted
                    zone_count[current] = zone_count.get(current, 1) - 1
                    link_usage[link_key] = link_usage.get(link_key, 0) + 1
                    in_transit_to[next_zone] = in_transit_to.get(next_zone, 0) + 1
                    state[did] = InTransit(current, next_zone)
                    conn_name = self.drone_map.connection_name(current, next_zone)
                    moves_this_turn.append(f"D{did}-{conn_name}")
                    continue

                # Commit move (normal/priority)
                zone_count[current] = zone_count.get(current, 1) - 1
                zone_count[next_zone] = zone_count.get(next_zone, 0) + 1
                link_usage[link_key] = link_usage.get(link_key, 0) + 1
                state[did] = InZone(next_zone)
                moves_this_turn.append(f"D{did}-{next_zone}")
                if next_zone == self.end_name:
                    del state[did]

            lines.append(" ".join(moves_this_turn))
            if not state:
                break
            if not moves_this_turn and state:
                raise RuntimeError("No progress this turn; possible deadlock.")

        return lines
