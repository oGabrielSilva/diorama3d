# SPDX-License-Identifier: GPL-3.0-or-later
# Diorama component circuit-breaker@1: one DIN-rail thermomagnetic circuit
# breaker at macro scale (1 mm of the real part = 4 mm in the scene), built to
# explain why it trips. Two half shells, lever, latch, fixed and moving
# contacts, bimetal strip, magnetic coil and plunger, arc chute with splitter
# plates, screw terminals with their wires, DIN clip and a rail section.
# Events: flow (current along the conductive path; `load: overload` heats the
# bimetal), trip (overload or short circuit, with arc flash), switch-on,
# section (cutaway with solid caps), explode and assemble.
# This component runs inside Blender and is distributed under the GNU GPL v3
# or later (see ../LICENSE). It only reads declarative shot specifications.

import math

import bpy
from .common import box, empty, key, link, material, srgb, wire
from .mechanism import Exploder, bar, bevel, cylinder, hollow_prism, prism, section, set_interpolation

S = 0.004
HALF_W, RIM_GAP, SIDE_WALL = 9.0, 0.15, 1.5
# Side profile (y = depth, front is -y; z = height) of the "hat" housing, in mm.
OUTER = [(35, -45), (35, 45), (-10, 45), (-10, 22.5), (-35, 22.5), (-35, -22.5), (-10, -22.5), (-10, -45)]
INNER = [(32.5, -42.5), (32.5, 42.5), (-7.5, 42.5), (-7.5, 20), (-32.5, 20), (-32.5, -20), (-7.5, -20), (-7.5, -42.5)]
LEVER_ON, LEVER_OFF = math.radians(-35), math.radians(35)
ARM_OPEN = math.radians(-28)
LATCH_RELEASED = math.radians(18)
BIMETAL_SEGMENT = 7.6
BIMETAL_FULL = math.radians(-8.5)  # per segment; three segments make the curve
HEAT = srgb("#FF4A0A")
ARC = srgb("#8FC2FF")
CURRENT = {"normal": "#FFD84A", "overload": "#FF6A1A"}
HELIX = [
    (5.9 * math.cos(a), 13 + 5.9 * math.sin(a), 6.4 + 13.2 * a / (9 * 2 * math.pi))
    for a in (i * 2 * math.pi / 12 for i in range(9 * 12 + 1))
]
# The conductive path, line terminal to load terminal (mm): line wire, terminal,
# bimetal, braid, moving contact, fixed contact, coil, rear conductor, terminal.
CURRENT_PATH = (
    [(0, -6, 150), (0, -2, 95), (0, 0, 60), (0, 0, 46.5), (0, 0, 36), (0, -3, 31), (0, -3, 20), (0, -3, 9)]
    + [(0, -0.5, 4), (0, 0.5, -1), (0, -2.5, -7.2), (0, 3, -6.2), (0, 9, -3.2), (0, 9, -1.5), (0, 11, 1.5)]
    + [(5.9, 13, 5.2)]
    + HELIX
    + [(0, 13, 22.2), (0, 18, 25), (0, 27, 24), (0, 30.5, 18), (0, 30.5, -20), (0, 30, -38.5), (0, 20, -39.5)]
    + [(0, 7.5, -37), (0, 0, -36), (0, 0, -46.5), (0, 0, -60), (0, -2, -95), (0, -6, -150)]
)


def mm(*values):
    return tuple(v * S for v in values)


def _emit(mat, frame, strength):
    socket = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    socket.default_value = strength
    socket.keyframe_insert("default_value", frame=frame + 1)


def _energy(light, frame, value):
    light.data.energy = value
    light.data.keyframe_insert("energy", frame=frame + 1)


def _visible(obj, frame, shown):
    obj.hide_render = not shown
    obj.keyframe_insert("hide_render", frame=frame + 1)


def _point_light(name, parent, location, color, radius):
    data = bpy.data.lights.new(name, "POINT")
    data.color = color
    data.shadow_soft_size = radius
    data.energy = 0.0
    obj = link(bpy.data.objects.new(name, data), parent)
    obj.location = location
    data.keyframe_insert("energy", frame=1)
    return obj


class CircuitBreaker:
    def __init__(self, spec, brand):
        self.id = spec["id"]
        params = spec["params"]
        n = self.id
        self.root = empty(n, location=tuple(spec["position"]))
        self.root.rotation_euler.z = math.radians(spec.get("yawDegrees", 0))
        self.brand = brand
        self.mats = {
            "shell": material(f"{n} | housing", srgb(params["color"]), 0.4),
            "cavity": material(f"{n} | housing inside", srgb("#2F3A39"), 0.75),
            "copper": material(f"{n} | copper", srgb("#C8793F"), 0.32, metal=1.0),
            "braid": material(f"{n} | copper braid", srgb("#B9703C"), 0.55, metal=1.0),
            "enamel": material(f"{n} | coil enamel", srgb("#B5652E"), 0.25, metal=0.9),
            "silver": material(f"{n} | silver contacts", srgb("#E3E6E6"), 0.2, metal=1.0),
            "steel": material(f"{n} | steel", srgb("#9AA5A5"), 0.3, metal=1.0),
            "latch": material(f"{n} | latch steel", srgb("#6F7B7B"), 0.35, metal=1.0),
            "dark": material(f"{n} | dark plastic", srgb("#22302E"), 0.45),
            "bobbin": material(f"{n} | bobbin", srgb("#3B4544"), 0.6),
            "fiber": material(f"{n} | arc chute fiber", srgb("#8A2F22"), 0.7),
            "clip": material(f"{n} | DIN clip", srgb("#6E7A78"), 0.5),
            "rail": material(f"{n} | DIN rail", srgb("#B8C2C2"), 0.3, metal=1.0),
            "line": material(f"{n} | line wire", srgb("#C8322B"), 0.4),
            "load": material(f"{n} | load wire", srgb("#1A1D1D"), 0.4),
            "brand": material(f"{n} | brand", srgb(brand["primary"]), 0.35),
            "brass": material(f"{n} | bimetal brass", srgb("#C9A24A"), 0.35, metal=1.0, emission=HEAT, strength=0.0),
            "invar": material(f"{n} | bimetal steel", srgb("#8E9999"), 0.3, metal=1.0, emission=HEAT, strength=0.0),
            "plates": material(f"{n} | splitter plates", srgb("#5D6868"), 0.4, metal=0.8, emission=HEAT, strength=0.0),
            "arc": material(f"{n} | arc", srgb("#FFFFFF"), 0.3, emission=ARC, strength=0.0),
        }
        self.exploder = Exploder()
        g = self.exploder.group
        # Explode order and designed vectors (m at distance 1): shells first, then the inside.
        self.groups = {
            name: g(f"{n}.part.{name}", self.root, vector)
            for name, vector in (
                ("shell-left", (-0.34, 0.0, 0.0)),
                ("shell-right", (0.12, 0.0, 0.0)),
                ("din-clip", (-0.04, 0.08, -0.15)),
                ("screw-top", (-0.11, -0.06, 0.13)),
                ("screw-bottom", (-0.11, -0.06, -0.13)),
                ("terminal-top", (-0.06, 0.0, 0.13)),
                ("terminal-bottom", (-0.06, 0.0, -0.13)),
                ("lever", (-0.14, -0.03, -0.05)),
                ("latch", (-0.13, -0.05, 0.03)),
                ("bimetal", (-0.15, -0.04, 0.07)),
                ("contact", (-0.15, 0.0, -0.06)),
                ("coil", (-0.10, 0.06, 0.07)),
                ("plunger", (-0.11, 0.06, 0.14)),
                ("arc-chute", (-0.10, 0.08, -0.1)),
            )
        }
        self.pulses = []
        self._housing(params)
        self._terminals()
        self._lever()
        self._latch()
        self._bimetal()
        self._contact()
        self._coil()
        self._arc_chute()
        self._clip_and_rail(params["rail"])
        gr = self.groups
        self.anchors = {
            "center": empty(f"{n}.anchor.center", self.root),
            "lever": empty(f"{n}.anchor.lever", self.lever, mm(0, -22, 0)),
            "contacts": empty(f"{n}.anchor.contacts", self.arm, mm(0, 15, 6.2)),
            "bimetal": empty(f"{n}.anchor.bimetal", gr["bimetal"], mm(0, -3, 19)),
            "coil": empty(f"{n}.anchor.coil", gr["coil"], mm(0, 13, 13)),
            "arc-chute": empty(f"{n}.anchor.arc-chute", gr["arc-chute"], mm(0, 21, -20)),
        }
        self.state = params["state"]
        self.latch_angle = 0.0
        self.heat = (0, 0.0, 0.0)  # last keyed (frame, bend, glow) of the bimetal
        closed = self.state == "on"
        key(self.lever, "rotation_euler", 0, (LEVER_ON if closed else LEVER_OFF, 0, 0))
        key(self.arm, "rotation_euler", 0, (0 if closed else ARM_OPEN, 0, 0))
        key(self.latch, "rotation_euler", 0, (0, 0, 0))
        key(self.plunger, "location", 0, (0, 0, 0))
        self._bimetal_key(0, 0.0, 0.0)
        _emit(self.mats["plates"], 0, 0.0)
        _emit(self.mats["arc"], 0, 0.0)
        for arc in self.arcs:
            _visible(arc, 0, False)

    # -- construction ---------------------------------------------------------
    def _housing(self, params):
        n, m, gr = self.id, self.mats, self.groups
        outer = [(y * S, z * S) for y, z in OUTER]
        inner = [(y * S, z * S) for y, z in INNER]
        mats = [m["shell"], m["cavity"]]
        self.shells = []
        for side, sign in (("left", -1), ("right", 1)):
            shell = hollow_prism(
                f"{n}.shell.{side}",
                outer,
                inner,
                "x",
                sign * HALF_W * S,
                sign * RIM_GAP * S,
                sign * (HALF_W - SIDE_WALL) * S,
                mats,
                gr[f"shell-{side}"],
            )
            bevel(shell, 0.45 * S)
            self.shells.append(shell)
        decal_parent = gr["shell-left"]
        text = bpy.data.curves.new(f"{n}.rating", "FONT")
        text.body = params["rating"]
        text.align_x = "CENTER"
        text.align_y = "CENTER"
        text.size = 6.5 * S
        text.extrude = 0.15 * S
        label = link(bpy.data.objects.new(f"{n}.rating", text), decal_parent)
        label.location = mm(0, -35.25, 14.5)
        label.rotation_euler.x = math.radians(90)
        label.data.materials.append(m["dark"])
        stripe = box(f"{n}.stripe", mm(13, 0.4, 1.4), mm(0, -35.2, 20.2), m["brand"], 0.0, decal_parent)
        self.decals = [(label, 14.5), (stripe, 20.2)]

    def _terminals(self):
        n, m, gr = self.id, self.mats, self.groups
        for side, sign, insulation in (("top", 1, m["line"]), ("bottom", -1, m["load"])):
            parent = gr[f"terminal-{side}"]
            box(f"{n}.terminal.{side}.cage", mm(12, 14, 9), mm(0, 0, 35 * sign), m["copper"], 0.5 * S, parent)
            box(f"{n}.terminal.{side}.clamp", mm(10.5, 4, 1.2), mm(0, -1, 35 * sign - 3.6 * sign), m["steel"], 0.0, parent)
            cylinder(f"{n}.terminal.{side}.core", 1.0 * S, 10.5 * S, mm(0, 0, 41.2 * sign), "z", m["copper"], parent, 8)
            points = [mm(0, 0, 46.5 * sign), mm(0, 0, 60 * sign), mm(0, -2, 95 * sign), mm(0, -6, 150 * sign)]
            lead = wire(f"{n}.wire.{side}", points, insulation, 1.9 * S, parent)
            lead["diorama_frame_ignore"] = True  # peripheral: thumbnails frame the breaker
            screw = gr[f"screw-{side}"]
            z = 35 * sign
            cylinder(f"{n}.screw.{side}.head", 3.3 * S, 2.8 * S, mm(0, -11, z), "y", m["steel"], screw, 14, 0.3 * S)
            cylinder(f"{n}.screw.{side}.shaft", 1.6 * S, 14 * S, mm(0, -2, z), "y", m["steel"], screw, 10)
            box(f"{n}.screw.{side}.slot.a", mm(5, 0.8, 0.9), mm(0, -12.45, z), m["dark"], 0.0, screw)
            box(f"{n}.screw.{side}.slot.b", mm(0.9, 0.8, 5), mm(0, -12.45, z), m["dark"], 0.0, screw)

    def _lever(self):
        n, m = self.id, self.mats
        self.lever = empty(f"{n}.lever.pivot", self.groups["lever"], mm(0, -24, -5))
        cylinder(f"{n}.lever.hub", 6 * S, 12 * S, (0, 0, 0), "x", m["dark"], self.lever, 16, 0.4 * S)
        box(f"{n}.lever.handle", mm(8, 22, 7), mm(0, -13, 0), m["dark"], 0.8 * S, self.lever, 2)
        box(f"{n}.lever.grip", mm(9, 3, 8.6), mm(0, -23, 0), m["dark"], 0.6 * S, self.lever, 2)
        box(f"{n}.lever.mark", mm(8.4, 6, 0.4), mm(0, -18.5, 3.6), m["brand"], 0.0, self.lever)
        cylinder(f"{n}.lever.pin", 1.4 * S, 15 * S, (0, 0, 0), "x", m["steel"], self.lever, 10)

    def _latch(self):
        n, m = self.id, self.mats
        self.latch = empty(f"{n}.latch.pivot", self.groups["latch"], mm(0, -12, 6))
        hook = [(2.5, 2), (-1.5, 2), (-7.5, -4), (-7.5, -7), (-5, -7), (-5, -5.5), (2.5, -0.5)]
        prism(f"{n}.latch", [(y * S, z * S) for y, z in hook], "x", -2 * S, 2 * S, m["latch"], self.latch)
        cylinder(f"{n}.latch.pin", 1.1 * S, 6 * S, (0, 0, 0), "x", m["steel"], self.latch, 10)

    def _bimetal(self):
        n, m = self.id, self.mats
        parent = self.groups["bimetal"]
        box(f"{n}.bimetal.bracket", mm(7, 3.2, 1.6), mm(0, -3, 30.9), m["copper"], 0.0, parent)
        pivot = empty(f"{n}.bimetal.pivot.0", parent, mm(0, -3, 30.5))
        self.bimetal_pivots = []
        for k in range(3):
            if k:
                pivot = empty(f"{n}.bimetal.pivot.{k}", pivot, mm(0, 0, -BIMETAL_SEGMENT))
            self.bimetal_pivots.append(pivot)
            length = BIMETAL_SEGMENT + 0.3
            box(f"{n}.bimetal.brass.{k}", mm(6, 0.7, length), mm(0, 0.36, -length / 2), m["brass"], 0.0, pivot)
            box(f"{n}.bimetal.steel.{k}", mm(6, 0.7, length), mm(0, -0.36, -length / 2), m["invar"], 0.0, pivot)
        self.heat_light = _point_light(f"{n}.bimetal.glow", parent, mm(-7, -6, 18), HEAT, 2 * S)

    def _contact(self):
        n, m = self.id, self.mats
        pivot_yz = (-6, -9)
        self.arm = empty(f"{n}.contact.pivot", self.groups["contact"], mm(0, *pivot_yz))

        def rel(y, z):
            return mm(0, y - pivot_yz[0], z - pivot_yz[1])

        bar(f"{n}.contact.arm", (0, 0, 0), rel(13, -4), 5 * S, 1.6 * S, m["copper"], self.arm)
        box(f"{n}.contact.moving", mm(4, 3.5, 1.6), rel(9, -3.45), m["silver"], 0.3 * S, self.arm)
        bar(f"{n}.contact.link", (0, 0, 0), rel(-20, -4), 3 * S, 1.5 * S, m["steel"], self.arm)
        cylinder(f"{n}.contact.pin", 1.4 * S, 10 * S, (0, 0, 0), "x", m["steel"], self.arm, 10)
        braid = [rel(-3, 8.6), rel(-0.5, 4), rel(0.5, -1), rel(-2.5, -7.2)]
        wire(f"{n}.contact.braid", braid, m["braid"], 0.9 * S, self.arm)

    def _coil(self):
        n, m = self.id, self.mats
        parent = self.groups["coil"]
        for z in (5.2, 20.8):
            cylinder(f"{n}.coil.flange.{z}", 7.0 * S, 1.2 * S, mm(0, 13, z), "z", m["bobbin"], parent, 16)
        cylinder(f"{n}.coil.core", 4.4 * S, 16 * S, mm(0, 13, 13), "z", m["bobbin"], parent, 16)
        wire(f"{n}.coil.winding", [mm(*p) for p in HELIX], m["enamel"], 0.55 * S, parent)
        wire(f"{n}.coil.lead", [mm(0, 13, 20.6), mm(0, 13, 22.2), mm(0, 18, 25)], m["copper"], 0.8 * S, parent)
        bar(f"{n}.coil.bracket", mm(0, 9, -1), mm(0, 13, 4.6), 5 * S, 1.6 * S, m["copper"], parent)
        box(f"{n}.contact.fixed", mm(4, 3.5, 1.6), mm(0, 9, -1.75), m["silver"], 0.3 * S, parent)
        bar(f"{n}.runner.upper", mm(0, 11.2, -2.2), mm(0, 17, -6.5), 4 * S, 1.0 * S, m["copper"], parent)
        conductor = [(0, 18, 25), (0, 27, 24), (0, 30.5, 18), (0, 30.5, -20), (0, 30, -38.5), (0, 20, -39.5), (0, 7.5, -37)]
        wire(f"{n}.conductor", [mm(*p) for p in conductor], m["copper"], 1.3 * S, parent)
        self.plunger = empty(f"{n}.plunger.pivot", self.groups["plunger"])
        cylinder(f"{n}.plunger.body", 2.4 * S, 15 * S, mm(0, 13, 11), "z", m["steel"], self.plunger, 12)
        cylinder(f"{n}.plunger.pin", 1.2 * S, 3 * S, mm(0, 13, 2.6), "z", m["steel"], self.plunger, 10)

    def _arc_chute(self):
        n, m = self.id, self.mats
        parent = self.groups["arc-chute"]
        # the fiber side plates hide the splitter plates, so a cutaway removes them with the housing
        self.chute_sides = [
            box(f"{n}.chute.side.{sx}", mm(1, 15.5, 27.5), mm(6.4 * sx, 21.75, -19.75), m["fiber"], 0.2 * S, parent)
            for sx in (-1, 1)
        ]
        plate = [(-5.9, 29), (5.9, 29), (5.9, 15), (1.8, 15), (0, 18.5), (-1.8, 15), (-5.9, 15)]
        for k in range(8):
            z0 = -31.5 + k * 3.1
            prism(f"{n}.chute.plate.{k}", [(x * S, y * S) for x, y in plate], "z", z0 * S, (z0 + 0.9) * S, m["plates"], parent)
        bar(f"{n}.runner.lower", mm(0, 5, -12), mm(0, 15.5, -31), 4 * S, 1.0 * S, m["copper"], parent)
        self.arc_light = _point_light(f"{n}.arc.flash", self.root, mm(-4, 14, -10), ARC, 3 * S)
        self.arcs = []
        for k, jitter in enumerate(((0.6, -0.5, 0.7, -0.6, 0.5, -0.4, 0.6), (-0.5, 0.7, -0.6, 0.5, -0.7, 0.4, -0.5))):
            route = [(9, -2.4), (11.5, -4.5), (14.5, -6.2), (17, -9.5), (19.5, -13), (17.5, -16.5), (13, -14.5), (10.5, -12.5), (9.6, -10.5)]
            points = [mm(0, *route[0])] + [
                mm(jitter[i], y + 0.6 * jitter[i] * (k * 2 - 1), z) for i, (y, z) in enumerate(route[1:-1])
            ] + [mm(0, *route[-1])]
            self.arcs.append(wire(f"{n}.arc.{k}", points, m["arc"], 0.8 * S, self.root))

    def _clip_and_rail(self, rail):
        """DIN clip tab; the rail section travels with the back shell when exploded."""
        n, m = self.id, self.mats
        parent = self.groups["din-clip"]
        box(f"{n}.clip.tab", mm(8, 7, 9), mm(0, 30, -47.3), m["clip"], 0.6 * S, parent, 2)
        box(f"{n}.clip.slot", mm(4.5, 0.6, 1.4), mm(0, 26.3, -49.5), m["dark"], 0.0, parent)
        if not rail:
            return
        f, b = 35.0, 42.5
        hat = [
            (b, -17.5), (b - 1, -17.5), (b - 1, -13.5), (f, -13.5), (f, 13.5), (b - 1, 13.5),
            (b - 1, 17.5), (b, 17.5), (b, 12.5), (f + 1, 12.5), (f + 1, -12.5), (b, -12.5),
        ]
        prism(f"{n}.rail", [(y * S, z * S) for y, z in hat], "x", -30 * S, 30 * S, m["rail"], self.groups["shell-right"], 0.2 * S)

    # -- state helpers ----------------------------------------------------------
    def _bimetal_key(self, frame, bend, glow):
        for pivot in self.bimetal_pivots:
            key(pivot, "rotation_euler", frame, (BIMETAL_FULL * bend, 0, 0))
        for name in ("brass", "invar"):
            _emit(self.mats[name], frame, 2.6 * glow)
        _energy(self.heat_light, frame, 0.6 * glow)
        self.heat = (frame, bend, glow)

    def _heat_to(self, frame, bend, glow):
        """Eases the bimetal from its last keyed state to (bend, glow) at frame."""
        if frame > self.heat[0]:
            self._bimetal_key(frame, bend, glow)

    # -- events -----------------------------------------------------------------
    def flow(self, event, fps):
        start, end = event["frame"], event["endFrame"]
        load = event.get("load") or "normal"
        overload = load == "overload"
        color = srgb(CURRENT[load])
        current = material(f"{self.id} | current {start}", color, 0.3, emission=color, strength=2.4 if overload else 2.0)
        period = max(3, round(fps / event["pulsesPerSecond"]))
        travel = max(period, round(fps * (0.8 if overload else 1.3)))
        copies = max(1, math.ceil(travel / period))
        cycle = copies * period
        length = 0.045
        points = [mm(*p) for p in CURRENT_PATH]
        for c in range(copies):
            pulse = wire(f"{self.id}.flow.{start}.{c}", points, current, 2.4 * S, self.root)
            data = pulse.data
            # thick over the insulated wires outside, slimmer over the inner conductors
            for point in data.splines[0].bezier_points:
                outside = abs(point.co.z) > 45 * S
                point.radius = 1.0 if outside else 0.72
            data.bevel_factor_mapping_start = "SPLINE"
            data.bevel_factor_mapping_end = "SPLINE"
            _visible(pulse, 0, False)
            _visible(pulse, start, True)
            _visible(pulse, end + 1, False)
            for f in range(start, end + 1):
                head = (((f - start + c * period) % cycle) / travel) * (1 + length)
                data.bevel_factor_start = max(0.0, min(1.0, head - length))
                data.bevel_factor_end = max(0.0, min(1.0, head))
                data.keyframe_insert("bevel_factor_start", frame=f + 1)
                data.keyframe_insert("bevel_factor_end", frame=f + 1)
            set_interpolation(data, "CONSTANT")
            self.pulses.append((pulse, end))
        if overload and self.state == "on":
            self._heat_to(start, *self.heat[1:])
            self._heat_to(end, max(self.heat[1], 0.6), max(self.heat[2], 0.8))

    def trip(self, event):
        if self.state != "on":
            return
        frame = event["frame"]
        cause = event.get("cause") or "overload"
        if cause == "overload":
            self._heat_to(frame - 3, *self.heat[1:])
            self._heat_to(frame, 1.0, 1.0)
            self._heat_to(frame + 14, 0.8, 0.7)
            self._heat_to(frame + 80, 0.0, 0.0)
        else:
            for f, z in ((frame - 1, 0.0), (frame + 1, -5.0), (frame + 4, -5.0), (frame + 14, 0.0)):
                key(self.plunger, "location", f, (0, 0, z * S))
        key(self.latch, "rotation_euler", frame, (self.latch_angle, 0, 0))
        key(self.latch, "rotation_euler", frame + 2, (LATCH_RELEASED, 0, 0))
        self.latch_angle = LATCH_RELEASED
        for f, angle in ((frame + 1, LEVER_ON), (frame + 3, LEVER_OFF + math.radians(7)), (frame + 6, LEVER_OFF)):
            key(self.lever, "rotation_euler", f, (angle, 0, 0))
        for f, angle in ((frame + 1, 0.0), (frame + 3, ARM_OPEN - math.radians(3)), (frame + 5, ARM_OPEN)):
            key(self.arm, "rotation_euler", f, (angle, 0, 0))
        # arc: two jagged shapes alternate for flicker, then the chute plates cool down
        a, b = self.arcs
        for f, shown in ((frame + 2, a), (frame + 3, b), (frame + 4, a), (frame + 5, b)):
            _visible(a, f, shown is a)
            _visible(b, f, shown is b)
        _visible(a, frame + 6, False)
        _visible(b, frame + 6, False)
        scale = 1.6 if cause == "short-circuit" else 1.0
        for f, value in ((frame + 1, 0.0), (frame + 2, 24.0 * scale), (frame + 4, 14.0 * scale), (frame + 6, 0.0)):
            _emit(self.mats["arc"], f, value)
        for f, value in ((frame + 1, 0.0), (frame + 2, 6.0 * scale), (frame + 4, 3.5 * scale), (frame + 7, 0.0)):
            _energy(self.arc_light, f, value)
        for f, value in ((frame + 2, 0.0), (frame + 5, 3.0), (frame + 30, 0.0)):
            _emit(self.mats["plates"], f, value)
        for pulse, end in self.pulses:
            if end >= frame + 1:
                _visible(pulse, frame + 2, False)
        self.state = "off"

    def switch_on(self, event):
        if self.state == "on":
            return
        frame = event["frame"]
        key(self.latch, "rotation_euler", frame, (self.latch_angle, 0, 0))
        key(self.latch, "rotation_euler", frame + 2, (0, 0, 0))
        self.latch_angle = 0.0
        for f, angle in ((frame, LEVER_OFF), (frame + 4, LEVER_ON - math.radians(5)), (frame + 6, LEVER_ON)):
            key(self.lever, "rotation_euler", f, (angle, 0, 0))
        key(self.arm, "rotation_euler", frame + 2, (ARM_OPEN, 0, 0))
        key(self.arm, "rotation_euler", frame + 4, (0, 0, 0))
        self.state = "on"

    def section(self, event, brand):
        cap_color = event.get("capColor") or brand["primary"]
        cap = material(f"{self.id} | section cap {event['frame']}", srgb(cap_color), 0.55)
        axis, side = event["axis"], event["side"]
        sign = -1.0 if side == "negative" else 1.0
        plane = -sign * 2.5 * S if axis == "x" else 0.0
        targets = [(part, part.parent, "TRANSFER") for part in self.shells + self.chute_sides]
        frame_at = section(
            f"{self.id}.section.{event['frame']}", targets, axis, side, plane, 48 * S, -48 * S,
            event["frame"], event["endFrame"], cap,
        )
        if axis == "x" or side == "negative":
            for decal, z in self.decals:
                _visible(decal, 0, True)
                _visible(decal, frame_at(z * S), False)

    def explode(self, event, assemble=False):
        self.exploder.animate(event, assemble)

    def anchor(self, name):
        return self.anchors[name]

