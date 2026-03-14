"""ANSI color visual renderer for the drone simulation (VII.1).

Prints colored turn-by-turn drone movements and zone state to the
terminal. Colors come from zone color metadata or zone type.
Auto-detects TTY; falls back to plain text when piped.
"""

from __future__ import annotations

import sys
from typing import Dict, List, Optional, Tuple

from model import Map, ZoneType

# ── ANSI primitives ───────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Zone type → ANSI foreground code
_ZONE_TYPE_CODE: Dict[ZoneType, str] = {
    ZoneType.NORMAL: "\033[37m",
    ZoneType.PRIORITY: "\033[92m",
    ZoneType.RESTRICTED: "\033[91m",
    ZoneType.BLOCKED: "\033[90m",
}

# Named color string (zone metadata) → ANSI code
_NAMED_COLOR: Dict[str, str] = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "gray": "\033[90m",
    "grey": "\033[90m",
    "orange": "\033[33m",
    "pink": "\033[95m",
    "purple": "\033[35m",
}

# Drone ID colors (cycle for many drones)
_DRONE_CODES: List[str] = [
    "\033[93m",  # bright yellow
    "\033[94m",  # bright blue
    "\033[95m",  # bright magenta
    "\033[96m",  # bright cyan
    "\033[33m",  # yellow
    "\033[34m",  # blue
    "\033[35m",  # magenta
    "\033[36m",  # cyan
]

_TRANSIT_CODE = "\033[33m"
_TURN_CODE = "\033[1;34m"
_HEADER_CODE = "\033[1;37m"
_SEP_CODE = "\033[90m"
_OK_CODE = "\033[1;32m"
_START_CODE = "\033[1;32m"
_END_CODE = "\033[1;33m"
_STATE_INDENT = "           "


def _parse_token(
    token: str,
) -> Tuple[int, str]:
    """Parse 'D<id>-<target>' into (drone_id, target_str)."""
    dash = token.index("-")
    did = int(token[1:dash])
    target = token[dash + 1:]
    return did, target


class VisualRenderer:
    """Renders colored turn output and live zone-state to the terminal.

    Uses ANSI escape codes when stdout is a TTY; plain text otherwise.
    Zone names are colored by their color metadata then zone type.
    Drone IDs cycle through a palette for easy visual tracking.
    """

    def __init__(self, drone_map: Map) -> None:
        """Initialize renderer with the parsed map."""
        self._map = drone_map
        self._color: bool = sys.stdout.isatty()
        # positions[did] = zone_name | "~from-to" (transit) | None (delivered)
        self._pos: Dict[int, Optional[str]] = {
            i: drone_map.start_zone.name
            for i in range(1, drone_map.nb_drones + 1)
        }

    # ── color helpers ─────────────────────────────────────────────

    def _c(self, code: str, text: str) -> str:
        """Wrap text in ANSI code + reset if color is enabled."""
        if not self._color:
            return text
        return f"{code}{text}{RESET}"

    def _zone_code(self, zone_name: str) -> str:
        """ANSI code for a zone: color metadata first, else zone type."""
        zone = self._map.get_zone(zone_name)
        if zone is None:
            return ""
        if zone.color:
            named = _NAMED_COLOR.get(zone.color.lower())
            if named:
                return named
        return _ZONE_TYPE_CODE.get(zone.zone_type, "")

    def _drone_code(self, did: int) -> str:
        """ANSI code for drone did (cycles through palette)."""
        return _DRONE_CODES[(did - 1) % len(_DRONE_CODES)]

    # ── token colorizer ───────────────────────────────────────────

    def _colorize_token(self, token: str) -> str:
        """Return ANSI-colored version of 'D<id>-<target>'."""
        did, target = _parse_token(token)
        c_did = self._c(self._drone_code(did) + BOLD, f"D{did}")
        if "-" in target:
            # In-transit on a connection (restricted zone move)
            c_target = self._c(_TRANSIT_CODE, target)
        else:
            c_target = self._c(self._zone_code(target), target)
        return f"{c_did}-{c_target}"

    # ── state tracker ─────────────────────────────────────────────

    def _update_positions(self, line: str) -> None:
        """Update drone position tracking from a raw turn line."""
        if not line.strip():
            return
        end_name = self._map.end_zone.name
        for token in line.split():
            did, target = _parse_token(token)
            if "-" in target:
                self._pos[did] = f"~{target}"
            elif target == end_name:
                self._pos[did] = None  # delivered
            else:
                self._pos[did] = target

    def _format_state(self) -> str:
        """One-line zone-state: zone:[D1,D2]  transit:[D3->...]."""
        zone_drones: Dict[str, List[int]] = {}
        transit: List[str] = []

        for did, pos in self._pos.items():
            if pos is None:
                continue
            if pos.startswith("~"):
                conn = pos[1:]
                c_did = self._c(self._drone_code(did), f"D{did}")
                c_conn = self._c(_TRANSIT_CODE, conn)
                transit.append(f"{c_did}:{c_conn}")
            else:
                zone_drones.setdefault(pos, []).append(did)

        parts: List[str] = []
        for zname, ids in zone_drones.items():
            c_zone = self._c(self._zone_code(zname), zname)
            c_ids = ",".join(
                self._c(self._drone_code(d), f"D{d}") for d in ids
            )
            parts.append(f"{c_zone}:[{c_ids}]")

        if transit:
            parts.append(
                "transit:[" + "  ".join(transit) + "]"
            )

        return _STATE_INDENT + "  ".join(parts)

    # ── public API ────────────────────────────────────────────────

    def print_header(self) -> None:
        """Print a map-info header before the simulation output."""
        m = self._map
        n = m.nb_drones
        nz = len(m.zones)
        nc = len(m.connections)
        drone_w = "drone" if n == 1 else "drones"
        c_start = self._c(_START_CODE, m.start_zone.name)
        c_end = self._c(_END_CODE, m.end_zone.name)
        info = (
            f"Fly-in  {n} {drone_w}  "
            f"{nz} zones  {nc} connections  "
            f"{c_start} -> {c_end}"
        )
        print(self._c(_HEADER_CODE, info))
        print(self._c(_SEP_CODE, "─" * 60))

    def print_turn(
        self,
        turn_num: int,
        line: str,
        total_turns: int,
    ) -> None:
        """Print one colored turn line followed by the zone-state."""
        label = self._c(
            _TURN_CODE,
            f"Turn {turn_num:>3}/{total_turns}",
        )
        if line.strip():
            tokens = [
                self._colorize_token(t) for t in line.split()
            ]
            moves = "  " + " ".join(tokens)
        else:
            moves = self._c(DIM, "  (no moves)")

        print(f"{label} │{moves}")
        self._update_positions(line)
        print(self._format_state())

    def print_summary(self, total_turns: int) -> None:
        """Print final delivery summary."""
        n = self._map.nb_drones
        drone_w = "drone" if n == 1 else "drones"
        turn_w = "turn" if total_turns == 1 else "turns"
        print(self._c(_SEP_CODE, "─" * 60))
        msg = (
            f"All {n} {drone_w} delivered "
            f"in {total_turns} {turn_w}."
        )
        print(self._c(_OK_CODE, msg))
