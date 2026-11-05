# SPDX-License-Identifier: GPL-3.0-or-later
# Diorama component kitchen-corner@1: faceted interior wall, floor, side wall,
# backsplash tiles, switch/outlet and an optional breakfast counter.

import math

from .appliance import build_kettle, build_toaster
from .common import box, empty, faceted_plane, material, seeded_random, srgb, wire


def build(params, surfaces=None):
    """`surfaces` maps wall/floor/backsplash/counter to library materials that
    replace the procedural colors of those surfaces."""
    surfaces = surfaces or {}
    rng = seeded_random("kitchen-corner@1")
    wall = surfaces.get("wall") or material("wall | painted plaster", srgb(params["wall"]), 0.85)
    tile = surfaces.get("backsplash") or material("wall | backsplash tile", srgb("#5E8C86"), 0.35, coat=0.3)
    floor = surfaces.get("floor") or material("floor | wood", srgb(params["floor"]), 0.7)
    trim = material("wall | baseboard", srgb("#E7F0EC"), 0.5)
    plastic = material("wall | switch plate", srgb("#E9EEEC"), 0.38)

    faceted_plane("set.wall", 5.0, 3.2, (0, 0, 1.6), (math.radians(90), 0, 0), wall, rng, (18, 12), 0.01)
    faceted_plane("set.wall_left", 3.0, 3.2, (-1.7, -1.5, 1.6), (math.radians(90), 0, math.radians(90)), wall, rng, (10, 12), 0.01)
    faceted_plane("set.floor", 5.0, 4.0, (0, -2.0, 0), (0, 0, 0), floor, rng, (16, 14), 0.004)
    box("set.baseboard", (5.0, 0.02, 0.09), (0, -0.01, 0.045), trim, 0.004)
    box("set.baseboard_left", (0.02, 3.0, 0.09), (-1.69, -1.5, 0.045), trim, 0.004)
    for i in range(7):
        for j in range(4):
            box(f"set.tile.{i}.{j}", (0.145, 0.012, 0.145), (0.42 + i * 0.152, -0.006, 0.98 + j * 0.152), tile, 0.012)
    box("set.switch", (0.08, 0.012, 0.12), (-0.62, -0.006, 1.18), trim, 0.006, segments=2)
    box("set.switch.key", (0.035, 0.012, 0.05), (-0.62, -0.014, 1.18), plastic, 0.004, segments=2)
    box("set.outlet", (0.08, 0.012, 0.12), (0.72, -0.006, 1.10), trim, 0.006, segments=2)

    if not params["counter"]:
        return
    counter = surfaces.get("counter") or material("kitchen | counter top", srgb("#2E3B3A"), 0.3, coat=0.4)
    cabinet = material("kitchen | cabinet", srgb("#D8E3DF"), 0.55)
    dark = material("kitchen | dark parts", srgb("#2A3231"), 0.5)
    cord = material("kitchen | cord", srgb("#1A1D1D"), 0.4)
    box("set.cabinet", (1.4, 0.58, 0.86), (1.05, -0.30, 0.43), cabinet, 0.01)
    box("set.counter", (1.46, 0.62, 0.04), (1.05, -0.31, 0.88), counter, 0.006)
    for i in range(2):
        box(f"set.cabinet.line.{i}", (0.005, 0.005, 0.7), (0.7 + i * 0.7, -0.592, 0.45), dark)
    if not params["appliances"]:
        return
    build_toaster("set.toaster", empty("set.toaster", location=(0.52, -0.30, 0.9)))
    build_kettle("set.kettle", empty("set.kettle", location=(0.86, -0.28, 0.9)))
    wire("set.toaster.cord", [(0.66, -0.25, 0.93), (0.7, -0.12, 0.905), (0.72, -0.02, 1.05), (0.72, -0.01, 1.10)], cord, 0.004)
