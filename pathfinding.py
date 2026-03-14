"""
Shortest-path finding on the map (no graph libraries).

Edge cost = movement cost of the destination zone
(normal/priority=1, restricted=2). Blocked zones are excluded
from neighbors by Map.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Set, Tuple

from model import Map

# Penalty so we prefer unpenalized edges when finding alternatives.
# Smaller value yields more path diversity.
EDGE_PENALTY = 100


class Pathfinder:
    """Dijkstra-based shortest-path finder for the drone map.

    No external graph libraries are used. Edge cost equals the
    movement cost of the destination zone. Blocked zones are
    skipped via Map.neighbors.
    """

    def __init__(self, drone_map: Map) -> None:
        """Initialize pathfinder with the map to search."""
        self._map = drone_map

    @staticmethod
    def _path_edges(
        path: List[str],
    ) -> Set[Tuple[str, str]]:
        """Return canonical edge pairs for consecutive nodes in path."""
        out: Set[Tuple[str, str]] = set()
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            out.add((min(a, b), max(a, b)))
        return out

    def find_shortest_path(
        self,
        start: str,
        end: str,
        edge_penalty: Optional[Dict[Tuple[str, str], int]] = None,
    ) -> List[str]:
        """Find shortest path from start to end by total turn cost.

        Uses Dijkstra. Cost of moving A -> B equals B's movement_cost
        (1 or 2) plus optional edge_penalty for (min(A,B), max(A,B)).

        Args:
            start: Name of the starting zone.
            end: Name of the destination zone.
            edge_penalty: Optional extra cost per canonical edge pair.

        Returns:
            List of zone names [start, ..., end], or [] if no path.
        """
        if (
            start not in self._map.zones
            or end not in self._map.zones
        ):
            return []
        if start == end:
            return [start]
        penalty = edge_penalty or {}

        heap: List[tuple[int, str]] = [(0, start)]
        best_cost: dict[str, int] = {start: 0}
        parent: dict[str, Optional[str]] = {start: None}

        while heap:
            cost, u = heapq.heappop(heap)
            if u == end:
                path: List[str] = []
                cur: Optional[str] = end
                while cur is not None:
                    path.append(cur)
                    cur = parent[cur]
                path.reverse()
                return path
            if cost > best_cost.get(u, 0):
                continue
            for v in self._map.neighbors(u):
                z = self._map.get_zone(v)
                if z is None:
                    continue
                step_cost = z.zone_type.movement_cost()
                if step_cost <= 0:
                    continue
                key = (min(u, v), max(u, v))
                step_cost += penalty.get(key, 0)
                new_cost = cost + step_cost
                if new_cost < best_cost.get(v, 0x7FFFFFFF):
                    best_cost[v] = new_cost
                    parent[v] = u
                    heapq.heappush(heap, (new_cost, v))

        return []

    def find_diverse_paths(
        self,
        start: str,
        end: str,
        k: int = 6,
    ) -> List[List[str]]:
        """Find up to k diverse paths to distribute drone load.

        The first path is the true shortest. Each subsequent path is
        shortest when penalizing edges used by previous paths.
        Used to reduce bottlenecks for large drone counts.

        Args:
            start: Name of the starting zone.
            end: Name of the destination zone.
            k: Maximum number of paths to return.

        Returns:
            List of up to k paths, each a list of zone names.
        """
        paths: List[List[str]] = []
        penalized: Dict[Tuple[str, str], int] = {}

        for _ in range(k):
            p = self.find_shortest_path(
                start, end, edge_penalty=penalized
            )
            if not p:
                break
            if paths and p == paths[-1]:
                break
            paths.append(p)
            for edge in self._path_edges(p):
                penalized[edge] = (
                    penalized.get(edge, 0) + EDGE_PENALTY
                )

        return paths
