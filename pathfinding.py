"""
Shortest-path finding on the map (no graph libraries).

Edge cost = movement cost of the destination zone (normal/priority=1, restricted=2).
Blocked zones are excluded from neighbors by Map.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Set, Tuple

from model import Map

# Penalty so we prefer unpenalized edges when finding alternative paths
# Smaller value yields more path diversity (more alternatives found)
EDGE_PENALTY = 100


def _path_edges(path: List[str]) -> Set[Tuple[str, str]]:
    """Set of (min(a,b), max(a,b)) for consecutive nodes in path."""
    out: Set[Tuple[str, str]] = set()
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        out.add((min(a, b), max(a, b)))
    return out


def find_shortest_path(
    drone_map: Map,
    start: str,
    end: str,
    edge_penalty: Optional[Dict[Tuple[str, str], int]] = None,
) -> List[str]:
    """
    Find a shortest path from start zone to end zone by total turn cost.

    Uses Dijkstra. Cost of moving A -> B = B's movement_cost (1 or 2)
    plus optional edge_penalty for (min(A,B), max(A,B)).
    Returns list of zone names [start, ..., end], or empty list if no path.
    """
    if start not in drone_map.zones or end not in drone_map.zones:
        return []
    if start == end:
        return [start]
    penalty = edge_penalty or {}

    # (cost, zone_name)
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
        for v in drone_map.neighbors(u):
            z = drone_map.get_zone(v)
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
    drone_map: Map, start: str, end: str, k: int = 6
) -> List[List[str]]:
    """
    Find up to k diverse paths from start to end to distribute drone load.

    First path is the true shortest. Each next path is shortest when penalizing
    edges used by previous paths. Used to beat Challenger (25 drones).
    """
    paths: List[List[str]] = []
    penalized_edges: Dict[Tuple[str, str], int] = {}

    for _ in range(k):
        p = find_shortest_path(drone_map, start, end, edge_penalty=penalized_edges)
        if not p:
            break
        if paths and p == paths[-1]:
            break
        paths.append(p)
        for edge in _path_edges(p):
            penalized_edges[edge] = penalized_edges.get(edge, 0) + EDGE_PENALTY

    return paths
