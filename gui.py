"""Pygame graphical interface for the drone simulation (VII.1).

Displays the zone network, connections, and drone movements
turn-by-turn with color-coded visual feedback.

Launch via: python main.py <map_file> --gui
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple, Union

import pygame

from model import Map, Zone, ZoneType

# ── Window layout ─────────────────────────────────────────────────
_WIN_W, _WIN_H = 1280, 720
_PANEL_W = 320
_MAP_W = _WIN_W - _PANEL_W   # 960
_MAP_PAD = 50
_FPS = 60
_AUTO_MS = 800   # ms between auto-advance turns

# ── Colours ───────────────────────────────────────────────────────
_C_BG = (18, 18, 30)
_C_MAP_BG = (22, 27, 50)
_C_PANEL_BG = (28, 28, 45)
_C_TEXT = (220, 220, 230)
_C_DIM = (120, 125, 145)
_C_CONN = (70, 85, 110)
_C_SEP = (55, 65, 90)
_C_BAR_BG = (45, 55, 75)
_C_TURN = (100, 180, 255)
_C_START = (80, 220, 100)
_C_END = (220, 180, 60)
_C_TRANSIT = (220, 180, 60)   # gold ring on in-transit drones
_C_OK = (80, 220, 100)

# Zone type fallback colours
_ZONE_TYPE_RGB: Dict[ZoneType, Tuple[int, int, int]] = {
    ZoneType.NORMAL:     (65,  95, 155),
    ZoneType.PRIORITY:   (45, 155,  75),
    ZoneType.RESTRICTED: (175,  65,  65),
    ZoneType.BLOCKED:    (55,   55,  65),
}

# Named colour metadata → RGB
_NAME_RGB: Dict[str, Tuple[int, int, int]] = {
    "red":      (200, 60,  60),
    "green":    (60,  180, 60),
    "blue":     (60,  100, 200),
    "yellow":   (210, 190, 50),
    "orange":   (220, 130, 50),
    "cyan":     (50,  185, 195),
    "purple":   (145, 75,  195),
    "gray":     (115, 115, 120),
    "grey":     (115, 115, 120),
    "black":    (45,  45,  55),
    "white":    (225, 225, 230),
    "magenta":  (195, 55,  195),
    "brown":    (135, 85,  50),
    "maroon":   (125, 40,  40),
    "gold":     (215, 175, 50),
    "pink":     (215, 125, 175),
}

# Drone palette (cycles for many drones)
_DRONE_PAL: List[Tuple[int, int, int]] = [
    (240, 220, 50),    # bright yellow
    (80,  140, 240),   # bright blue
    (220, 80,  220),   # bright magenta
    (80,  220, 220),   # bright cyan
    (240, 150, 60),    # orange
    (100, 240, 100),   # lime green
    (240, 80,  80),    # red
    (160, 80,  240),   # purple
]

# Type alias for drone position in snapshots:
#   str  → drone is in this zone
#   tuple → drone is in transit (from_zone, to_zone)
_DronePos = Union[str, Tuple[str, str]]


class SimulationGUI:
    """Pygame GUI: animated zone graph and drone movements.

    Zones are circles coloured by their color metadata or zone type.
    Connections are grey lines. Drones are small labelled dots that
    move each turn. A side panel shows turn info and drone states.
    """

    def __init__(
        self, drone_map: Map, lines: List[str]
    ) -> None:
        """Initialize window, fonts, layout, and turn snapshots."""
        self._map = drone_map
        self._lines = lines
        self._turn = 0          # 0 = initial state, 1..N after turn N
        self._snapshots = self._compute_snapshots()

        pygame.init()
        self._screen = pygame.display.set_mode(
            (_WIN_W, _WIN_H)
        )
        pygame.display.set_caption(
            "Fly-in - Drone Simulation"
        )
        self._clock = pygame.time.Clock()
        self._font_sm = pygame.font.SysFont("monospace", 11)
        self._font_md = pygame.font.SysFont("monospace", 14)
        self._font_lg = pygame.font.SysFont(
            "monospace", 18, bold=True
        )
        self._font_xl = pygame.font.SysFont(
            "monospace", 26, bold=True
        )

        # Adaptive radii; set by _compute_layout
        self._zone_r = 22
        self._drone_r = 8
        self._screen_pos: Dict[str, Tuple[float, float]] = {}
        self._compute_layout()

        self._auto_play = False
        self._last_adv = 0   # ticks of last auto-advance

    # ── Snapshot computation ───────────────────────────────────────

    def _compute_snapshots(
        self,
    ) -> List[Dict[int, _DronePos]]:
        """Pre-compute drone positions for every turn (0=initial)."""
        n = self._map.nb_drones
        end = self._map.end_zone.name
        start = self._map.start_zone.name

        state: Dict[int, Optional[_DronePos]] = {
            i: start for i in range(1, n + 1)
        }
        snaps: List[Dict[int, _DronePos]] = [
            {i: start for i in range(1, n + 1)}
        ]

        for line in self._lines:
            for token in line.split():
                dash = token.index("-")
                did = int(token[1:dash])
                target = token[dash + 1:]
                if "-" in target:
                    # In-transit: target is "from_zone-to_zone"
                    a, b = target.split("-", 1)
                    state[did] = (a, b)
                elif target == end:
                    state[did] = None   # delivered
                else:
                    state[did] = target
            snaps.append(
                {
                    d: p
                    for d, p in state.items()
                    if p is not None
                }
            )
        return snaps

    # ── Layout ────────────────────────────────────────────────────

    def _compute_layout(self) -> None:
        """Fit zone coordinates into the map area; set radii."""
        zones = list(self._map.zones.values())
        xs = [z.x for z in zones]
        ys = [z.y for z in zones]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        rx = float(max_x - min_x) or 1.0
        ry = float(max_y - min_y) or 1.0
        avail_w = float(_MAP_W - 2 * _MAP_PAD)
        avail_h = float(_WIN_H - 2 * _MAP_PAD)

        scale = min(avail_w / rx, avail_h / ry)
        used_w = rx * scale
        used_h = ry * scale
        off_x = _MAP_PAD + (avail_w - used_w) / 2.0
        off_y = _MAP_PAD + (avail_h - used_h) / 2.0

        # Shrink circles when zones are densely packed
        self._zone_r = max(8, min(22, int(scale * 0.45)))
        self._drone_r = max(4, self._zone_r // 3)

        for z in zones:
            sx = off_x + (z.x - min_x) * scale
            # Flip y: map y up, screen y down
            sy = off_y + (max_y - z.y) * scale
            self._screen_pos[z.name] = (sx, sy)

    # ── Colour helpers ────────────────────────────────────────────

    @staticmethod
    def _zone_rgb(zone: Zone) -> Tuple[int, int, int]:
        """RGB for a zone: color metadata first, then zone type."""
        if zone.color:
            rgb = _NAME_RGB.get(zone.color.lower())
            if rgb is not None:
                return rgb
        return _ZONE_TYPE_RGB.get(
            zone.zone_type, (65, 95, 155)
        )

    @staticmethod
    def _drone_rgb(did: int) -> Tuple[int, int, int]:
        """RGB for drone did; cycles through the palette."""
        return _DRONE_PAL[(did - 1) % len(_DRONE_PAL)]

    # ── Draw: connections ─────────────────────────────────────────

    def _draw_connections(
        self, surf: pygame.Surface
    ) -> None:
        """Draw all connection edges on the map area."""
        for conn in self._map.connections:
            a = self._screen_pos.get(conn.zone_a)
            b = self._screen_pos.get(conn.zone_b)
            if a is None or b is None:
                continue
            pygame.draw.line(
                surf,
                _C_CONN,
                (int(a[0]), int(a[1])),
                (int(b[0]), int(b[1])),
                2,
            )

    # ── Draw: zones ───────────────────────────────────────────────

    def _draw_zones(self, surf: pygame.Surface) -> None:
        """Draw zone circles and truncated name labels."""
        zr = self._zone_r
        for z in self._map.zones.values():
            pos = self._screen_pos.get(z.name)
            if pos is None:
                continue
            cx, cy = int(pos[0]), int(pos[1])
            rgb = self._zone_rgb(z)

            pygame.draw.circle(surf, rgb, (cx, cy), zr)

            if z.is_end:
                border: Tuple[int, int, int] = _C_END
                bw = 3
            elif z.is_start:
                border = _C_START
                bw = 3
            else:
                border = (195, 195, 205)
                bw = 1
            pygame.draw.circle(
                surf, border, (cx, cy), zr, bw
            )

            label = z.name
            if len(label) > 9:
                label = label[:8] + "~"
            ts = self._font_sm.render(
                label, True, (240, 240, 240)
            )
            surf.blit(
                ts,
                (cx - ts.get_width() // 2, cy + zr + 2),
            )

    # ── Draw: drones ──────────────────────────────────────────────

    def _draw_drones(self, surf: pygame.Surface) -> None:
        """Dispatch drone drawing for in-zone and in-transit."""
        snap = self._snapshots[self._turn]
        in_zone: Dict[str, List[int]] = {}
        in_trans: Dict[Tuple[str, str], List[int]] = {}

        for did, pos in snap.items():
            if isinstance(pos, tuple):
                in_trans.setdefault(pos, []).append(did)
            else:
                in_zone.setdefault(pos, []).append(did)

        self._draw_zone_drones(surf, in_zone)
        self._draw_transit_drones(surf, in_trans)

    def _draw_zone_drones(
        self,
        surf: pygame.Surface,
        in_zone: Dict[str, List[int]],
    ) -> None:
        """Draw drones clustered around their zone centre."""
        dr = self._drone_r
        for zone_name, ids in in_zone.items():
            pos = self._screen_pos.get(zone_name)
            if pos is None:
                continue
            sx, sy = pos[0], pos[1]
            n = len(ids)
            for i, did in enumerate(ids):
                if n == 1:
                    dx, dy = int(sx), int(sy)
                else:
                    angle = 2.0 * math.pi * i / n
                    r_off = self._zone_r * 0.65
                    dx = int(sx + r_off * math.cos(angle))
                    dy = int(sy + r_off * math.sin(angle))
                rgb = self._drone_rgb(did)
                pygame.draw.circle(
                    surf, rgb, (dx, dy), dr
                )
                pygame.draw.circle(
                    surf, (0, 0, 0), (dx, dy), dr, 1
                )
                txt = self._font_sm.render(
                    str(did), True, (10, 10, 10)
                )
                surf.blit(
                    txt,
                    (
                        dx - txt.get_width() // 2,
                        dy - txt.get_height() // 2,
                    ),
                )

    def _draw_transit_drones(
        self,
        surf: pygame.Surface,
        in_trans: Dict[Tuple[str, str], List[int]],
    ) -> None:
        """Draw in-transit drones at their connection midpoint."""
        dr = self._drone_r
        for (from_z, to_z), ids in in_trans.items():
            a = self._screen_pos.get(from_z)
            b = self._screen_pos.get(to_z)
            if a is None or b is None:
                continue
            mid_x = (a[0] + b[0]) / 2.0
            mid_y = (a[1] + b[1]) / 2.0
            n = len(ids)
            # Perpendicular offset to separate concurrent transits
            if n > 1:
                dx_l = b[0] - a[0]
                dy_l = b[1] - a[1]
                length = math.hypot(dx_l, dy_l) or 1.0
                perp_x = -dy_l / length
                perp_y = dx_l / length
            else:
                perp_x = perp_y = 0.0

            for i, did in enumerate(ids):
                off = (i - (n - 1) / 2.0) * 12.0
                ex = int(mid_x + perp_x * off)
                ey = int(mid_y + perp_y * off)
                rgb = self._drone_rgb(did)
                pygame.draw.circle(
                    surf, rgb, (ex, ey), dr
                )
                # Gold ring marks in-transit status
                pygame.draw.circle(
                    surf, _C_TRANSIT, (ex, ey), dr, 2
                )
                txt = self._font_sm.render(
                    str(did), True, (10, 10, 10)
                )
                surf.blit(
                    txt,
                    (
                        ex - txt.get_width() // 2,
                        ey - txt.get_height() // 2,
                    ),
                )

    # ── Draw: info panel ──────────────────────────────────────────

    def _draw_panel(self) -> None:
        """Draw the right-side info and controls panel."""
        surf = self._screen
        px = _MAP_W

        pygame.draw.rect(
            surf, _C_PANEL_BG, (px, 0, _PANEL_W, _WIN_H)
        )
        pygame.draw.line(
            surf, _C_SEP, (px, 0), (px, _WIN_H), 1
        )

        y = 18

        # Title
        surf.blit(
            self._font_lg.render(
                "Fly-in", True, _C_TEXT
            ),
            (px + 16, y),
        )
        y += 30

        # Map summary
        m = self._map
        n = m.nb_drones
        info = (
            f"{n} drone{'s' if n != 1 else ''},"
            f" {len(m.zones)} zones"
        )
        surf.blit(
            self._font_md.render(info, True, _C_DIM),
            (px + 16, y),
        )
        y += 20

        surf.blit(
            self._font_md.render(
                f"Start: {m.start_zone.name}",
                True, _C_START,
            ),
            (px + 16, y),
        )
        y += 18
        surf.blit(
            self._font_md.render(
                f"End:   {m.end_zone.name}",
                True, _C_END,
            ),
            (px + 16, y),
        )
        y += 28

        # Turn counter + auto indicator
        total = len(self._lines)
        if self._turn == 0:
            t_str = "Initial"
        else:
            t_str = f"Turn {self._turn} / {total}"
        surf.blit(
            self._font_xl.render(t_str, True, _C_TURN),
            (px + 16, y),
        )
        y += 36

        ap_txt, ap_col = (
            ("[AUTO]", (100, 240, 100))
            if self._auto_play
            else ("[paused]", _C_DIM)
        )
        surf.blit(
            self._font_sm.render(ap_txt, True, ap_col),
            (px + 16, y),
        )
        y += 18

        # Progress bar
        bar_w = _PANEL_W - 32
        prog = (self._turn / total) if total else 0.0
        pygame.draw.rect(
            surf, _C_BAR_BG, (px + 16, y, bar_w, 8)
        )
        pygame.draw.rect(
            surf,
            _C_TURN,
            (px + 16, y, int(bar_w * prog), 8),
        )
        y += 22

        # Separator
        pygame.draw.line(
            surf, _C_SEP,
            (px + 10, y), (px + _PANEL_W - 10, y), 1,
        )
        y += 10

        # Drone list
        surf.blit(
            self._font_md.render(
                "Drones", True, _C_TEXT
            ),
            (px + 16, y),
        )
        y += 18

        snap = self._snapshots[self._turn]
        max_list_y = _WIN_H - 95

        for did in range(1, m.nb_drones + 1):
            if y + 14 > max_list_y:
                remaining = m.nb_drones - did + 1
                surf.blit(
                    self._font_sm.render(
                        f"... +{remaining} more",
                        True, _C_DIM,
                    ),
                    (px + 16, y),
                )
                break
            rgb = self._drone_rgb(did)
            pos = snap.get(did)
            if pos is None:
                lbl = f"D{did}: delivered"
                clr: Tuple[int, int, int] = (80, 215, 95)
            elif isinstance(pos, tuple):
                lbl = f"D{did}: ->{pos[1]}"
                clr = rgb
            else:
                lbl = f"D{did}: {pos}"
                clr = rgb
            if len(lbl) > 24:
                lbl = lbl[:23] + "~"

            pygame.draw.circle(
                surf, rgb, (px + 22, y + 5), 5
            )
            surf.blit(
                self._font_sm.render(lbl, True, clr),
                (px + 32, y),
            )
            y += 14

        # Zone-type legend
        y = _WIN_H - 88
        pygame.draw.line(
            surf, _C_SEP,
            (px + 10, y), (px + _PANEL_W - 10, y), 1,
        )
        y += 8
        legend: List[Tuple[str, Tuple[int, int, int]]] = [
            ("normal",     _ZONE_TYPE_RGB[ZoneType.NORMAL]),
            ("priority",   _ZONE_TYPE_RGB[ZoneType.PRIORITY]),
            (
                "restricted",
                _ZONE_TYPE_RGB[ZoneType.RESTRICTED],
            ),
        ]
        for lname, lcol in legend:
            pygame.draw.circle(
                surf, lcol, (px + 22, y + 5), 5
            )
            surf.blit(
                self._font_sm.render(
                    lname, True, _C_DIM
                ),
                (px + 32, y),
            )
            y += 14

        # Controls hint
        y = _WIN_H - 28
        surf.blit(
            self._font_sm.render(
                "SPC/->:fwd  <-:back  A:auto  ESC",
                True, _C_DIM,
            ),
            (px + 8, y),
        )

    # ── Main draw + event loop ────────────────────────────────────

    def _draw(self) -> None:
        """Render a complete frame."""
        self._screen.fill(_C_BG)
        pygame.draw.rect(
            self._screen, _C_MAP_BG,
            (0, 0, _MAP_W, _WIN_H),
        )
        self._draw_connections(self._screen)
        self._draw_zones(self._screen)
        self._draw_drones(self._screen)
        self._draw_panel()
        pygame.display.flip()

    def run(self) -> None:
        """Start the event loop; blocks until the window closes."""
        total = len(self._lines)
        running = True

        while running:
            self._clock.tick(_FPS)
            now = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (
                        pygame.K_SPACE,
                        pygame.K_RIGHT,
                    ):
                        if self._turn < total:
                            self._turn += 1
                        self._auto_play = False
                    elif event.key == pygame.K_LEFT:
                        if self._turn > 0:
                            self._turn -= 1
                        self._auto_play = False
                    elif event.key == pygame.K_a:
                        self._auto_play = not self._auto_play
                        self._last_adv = now

            # Auto-advance
            if (
                self._auto_play
                and self._turn < total
                and now - self._last_adv >= _AUTO_MS
            ):
                self._turn += 1
                self._last_adv = now
                if self._turn >= total:
                    self._auto_play = False

            self._draw()

        pygame.quit()
