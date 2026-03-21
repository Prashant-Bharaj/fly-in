"""
Shortest-path finding on the map (no graph libraries).

Edge cost = movement cost of the destination zone
(normal/priority=1, restricted=2). Blocked zones are excluded
from neighbors by Map.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Set, Tuple

from model import Map, ZoneType

# Penalty so we prefer unpenalized edges when finding alternatives.
# Smaller value yields more path diversity.
EDGE_PENALTY = 100


class Pathfinder:
    """Dijkstra-based shortest-path finder for the drone map.

    Edge cost equals the movement cost of the destination zone.
    Blocked zones are skipped via Map.neighbors.
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


class ParallelChainRouter:
    """Custom router: same-cost paths through different restricted chains.

    Problem with Dijkstra diverse paths: penalizing all edges of a path
    forces the next path to take a longer early route, producing high-cost
    detours that slow the last drone.

    Problem with Edmonds-Karp BFS: finds the shortest-hop path, assigns
    all drones to it. When that path includes a restricted zone with
    cap > 1 acting as a buffer (e.g. overflow_hell with cap=2), drones
    pile up: the drone that just arrived (InTransit→InZone) cannot move
    the same turn, so successive drones stall every 2 turns → half
    throughput → 2× expected turns.

    This router:
    1. Finds the shortest path (Dijkstra, cost-weighted).
    2. Penalizes only edges that *enter* a restricted zone (chain-entry
       edges). Subsequent paths may reuse the same cheap prefix but
       diverge into a different parallel restricted chain.
    3. Accepts a new path only if its cost equals the first path's cost.
       This guarantees every drone takes an equally fast route.
    4. Assigns drones round-robin across the accepted paths.

    Effect: with k same-cost parallel chains, consecutive drones on
    each chain are k turns apart — well above the 2-turn minimum
    separation — eliminating the restricted-zone pipeline stall.
    """

    def __init__(self, drone_map: Map) -> None:
        """Initialize with the parsed map."""
        self._map = drone_map
        self._pf = Pathfinder(drone_map)

    def _chain_entries(self, path: List[str]) -> List[Tuple[str, str]]:
        """Return canonical edge pairs in path
        that first enter a restricted zone."""
        entries: List[Tuple[str, str]] = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            zu = self._map.get_zone(u)
            zv = self._map.get_zone(v)
            if zu is None or zv is None:
                continue
            if (
                zu.zone_type != ZoneType.RESTRICTED
                and zv.zone_type == ZoneType.RESTRICTED
            ):
                entries.append((min(u, v), max(u, v)))
        return entries

    def find_paths(
        self, start: str, end: str, n_drones: int
    ) -> List[List[str]]:
        """Return one path per drone using parallel-chain routing.

        Finds the shortest path, then discovers alternative same-cost
        paths that enter different restricted chains. Stops when no
        further same-cost alternative exists.

        Args:
            start: Start zone name.
            end: End zone name.
            n_drones: Number of drones to route.

        Returns:
            List of n_drones paths (round-robin over discovered paths).
        """
        first = self._pf.find_shortest_path(start, end)
        if not first:
            return []

        min_cost = sum(
            self._map.zones[z].zone_type.movement_cost()
            for z in first[1:]
        )

        paths: List[List[str]] = [first]
        penalized: Dict[Tuple[str, str], int] = {}

        # Seed penalties with chain-entry edges of the first path
        for edge in self._chain_entries(first):
            penalized[edge] = penalized.get(edge, 0) + EDGE_PENALTY

        for _ in range(min(n_drones - 1, 11)):
            nxt = self._pf.find_shortest_path(start, end, penalized)
            if not nxt or nxt == paths[-1]:
                break
            cost = sum(
                self._map.zones[z].zone_type.movement_cost()
                for z in nxt[1:]
            )
            # Only accept paths with the same optimal cost
            if cost > min_cost:
                break
            paths.append(nxt)
            for edge in self._chain_entries(nxt):
                penalized[edge] = penalized.get(edge, 0) + EDGE_PENALTY

        k = len(paths)
        return [list(paths[(i) % k]) for i in range(n_drones)]


class EdmondsKarp:
    """Max-flow path finder using Edmonds-Karp (BFS Ford-Fulkerson).

    Builds a node-split graph to respect zone capacity constraints.
    Each zone becomes two nodes (in/out) joined by an edge with
    capacity = zone.max_drones. Connections become directed edges
    between out-nodes and in-nodes with capacity = max_link_capacity.

    Runs BFS augmentation to find max-flow paths. All n_drones
    slots are filled from the discovered paths (repeated if max
    flow < n_drones, so every drone gets the best available path).
    """

    def __init__(self, drone_map: Map) -> None:
        """Initialize with the parsed map."""
        self._map = drone_map

    def find_paths(
        self, start: str, end: str, n_drones: int
    ) -> List[List[str]]:
        """Return one path per drone using Edmonds-Karp max flow.

        Args:
            start: Name of the start zone.
            end: Name of the end zone.
            n_drones: Number of drones to route.

        Returns:
            List of n_drones zone-name lists. When max spatial
            flow < n_drones (bottlenecked map), remaining slots
            are filled with the shortest discovered path so all
            drones share the optimal route.
        """
        zones = list(self._map.zones.keys())
        n = len(zones)
        zone_idx: Dict[str, int] = {z: i for i, z in enumerate(zones)}

        # Node layout: zone i -> in-node 2i, out-node 2i+1
        total = 2 * n
        src = 2 * zone_idx[start]       # start zone in-node
        snk = 2 * zone_idx[end] + 1     # end zone out-node

        # Capacity and adjacency for residual graph
        cap: List[Dict[int, int]] = [{} for _ in range(total)]
        adj: List[List[int]] = [[] for _ in range(total)]

        def _add(u: int, v: int, c: int) -> None:
            if v in cap[u]:
                cap[u][v] += c
            else:
                cap[u][v] = c
                adj[u].append(v)
            if u not in cap[v]:
                cap[v][u] = 0
                adj[v].append(u)

        # Internal zone edges (in -> out)
        for zname, zone in self._map.zones.items():
            if zone.zone_type == ZoneType.BLOCKED:
                continue
            i = zone_idx[zname]
            c = n_drones if zone.is_end else zone.max_drones
            _add(2 * i, 2 * i + 1, c)

        # Connection edges (out -> in, both directions)
        for conn in self._map.connections:
            za = self._map.get_zone(conn.zone_a)
            zb = self._map.get_zone(conn.zone_b)
            if za is None or zb is None:
                continue
            if (
                za.zone_type == ZoneType.BLOCKED
                or zb.zone_type == ZoneType.BLOCKED
            ):
                continue
            ia = zone_idx[conn.zone_a]
            ib = zone_idx[conn.zone_b]
            c = conn.max_link_capacity
            _add(2 * ia + 1, 2 * ib, c)
            _add(2 * ib + 1, 2 * ia, c)

        # Flow matrix (same shape as cap)
        flow: List[Dict[int, int]] = [{} for _ in range(total)]

        def _bfs() -> Optional[Dict[int, int]]:
            """BFS augmenting path; returns parent dict or None."""
            parent: Dict[int, int] = {src: -1}
            queue: List[int] = [src]
            while queue:
                u = queue.pop(0)
                if u == snk:
                    return parent
                for v in adj[u]:
                    if v not in parent:
                        residual = (
                            cap[u].get(v, 0) - flow[u].get(v, 0)
                        )
                        if residual > 0:
                            parent[v] = u
                            queue.append(v)
            return None

        # Collect (node_path, bottleneck) pairs
        aug: List[Tuple[List[int], int]] = []
        total_flow = 0

        while total_flow < n_drones:
            parent = _bfs()
            if parent is None:
                break
            # Bottleneck along this augmenting path
            bottleneck = n_drones - total_flow
            v = snk
            while v != src:
                u = parent[v]
                residual = cap[u].get(v, 0) - flow[u].get(v, 0)
                bottleneck = min(bottleneck, residual)
                v = u
            # Reconstruct node path and update flow
            path_nodes: List[int] = []
            v = snk
            while v != src:
                u = parent[v]
                path_nodes.append(v)
                flow[u][v] = flow[u].get(v, 0) + bottleneck
                flow[v][u] = flow[v].get(u, 0) - bottleneck
                v = u
            path_nodes.append(src)
            path_nodes.reverse()
            aug.append((path_nodes, bottleneck))
            total_flow += bottleneck

        if not aug:
            return []

        def _to_zones(node_path: List[int]) -> List[str]:
            """Collapse node-split path back to zone-name list."""
            zpath: List[str] = []
            for node in node_path:
                zname = zones[node // 2]
                if not zpath or zpath[-1] != zname:
                    zpath.append(zname)
            return zpath

        # Expand augmenting paths into per-drone path list
        zone_paths: List[List[str]] = []
        for node_path, count in aug:
            zp = _to_zones(node_path)
            for _ in range(count):
                zone_paths.append(zp)

        # If max flow < n_drones, fill remaining with shortest path
        if len(zone_paths) < n_drones:
            best = min(zone_paths, key=len)
            while len(zone_paths) < n_drones:
                zone_paths.append(best)

        # Round-robin drone assignment across discovered paths
        k = len(zone_paths)
        return [
            list(zone_paths[(i - 1) % k]) for i in range(1, n_drones + 1)
        ]
