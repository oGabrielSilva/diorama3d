# SPDX-License-Identifier: GPL-3.0-or-later
# Diorama component electrical-panel@1: residential distribution board with a
# hinged door, DIN rails, main breaker, optional RCD (DR) and surge protector
# (DPS), up to eight circuit breakers, color-coded wiring and labels that light
# up when their protection is switched on.

import math

from mathutils import Vector

from .common import box, empty, key, material, srgb, wire

PW, PH, PD = 0.40, 0.52, 0.10
MODULE = 0.0178 * 1.6  # DIN module, stylized x1.6 so it reads on a phone
ROWS = (0.11, -0.10)
DEPTH = 0.07
OFF, ON, SETTLE = math.radians(-35), math.radians(38), math.radians(32)


class ElectricalPanel:
    def __init__(self, spec, brand):
        self.id = spec["id"]
        params = spec["params"]
        self.mats = {
            "shell": material(f"{self.id} | ABS white", srgb("#E9EEEC"), 0.38),
            "inner": material(f"{self.id} | back plate", srgb("#33413F"), 0.7),
            "window": material(f"{self.id} | smoked window", srgb("#20302E"), 0.15),
            "rail": material(f"{self.id} | DIN rail", srgb("#B8C2C2"), 0.3, metal=1.0),
            "module": material(f"{self.id} | breaker", srgb("#F3F5F4"), 0.42),
            "main": material(f"{self.id} | main breaker", srgb("#DCE3E1"), 0.42),
            "lever": material(f"{self.id} | lever", srgb("#22302E"), 0.45),
            "test": material(f"{self.id} | test button", srgb("#F2C14E"), 0.4),
            "screw": material(f"{self.id} | screws", srgb("#9AA5A5"), 0.25, metal=1.0),
            "warning": material(f"{self.id} | warning label", srgb("#F2C14E"), 0.5),
            "conduit": material(f"{self.id} | conduit", srgb("#E6E1D2"), 0.6),
        }
        self.wires = [
            material(f"{self.id} | wire {n}", srgb(c), 0.4)
            for n, c in (("phase black", "#1A1D1D"), ("phase red", "#C8322B"), ("neutral", "#1F6FD1"), ("earth", "#3BAA3B"))
        ]
        self.brand = srgb(brand["primary"])
        self.groups = {"main": [], "protections": [], "circuits": []}
        self.root = empty(f"{self.id}", location=tuple(spec["position"]))
        self._shell()
        self._modules(params)
        self._wiring(params["circuits"])
        self._door()
        self.anchors = {
            "center": empty(f"{self.id}.anchor.center", self.root),
            "inside": empty(f"{self.id}.anchor.inside", self.root, (0, PD / 2 - 0.04, 0)),
            "lower-row": empty(f"{self.id}.anchor.lower-row", self.root, (0, PD / 2 - 0.02 - DEPTH, ROWS[1])),
            "main-lever": empty(
                f"{self.id}.anchor.main-lever",
                self.root,
                (-PW / 2 + 0.05 + MODULE, PD / 2 - 0.02 - DEPTH - 0.03, ROWS[0] - 0.02),
            ),
            "door-handle": empty(f"{self.id}.anchor.door-handle", self.door_pivot, (-self.door_w + 0.03, -0.045, 0)),
        }

    # -- construction ---------------------------------------------------------
    def _shell(self):
        m, r = self.mats, self.root
        box(f"{self.id}.back", (PW, 0.01, PH), (0, PD / 2 - 0.005, 0), m["inner"], 0.0, r)
        for side, sx in (("L", -1), ("R", 1)):
            box(f"{self.id}.side.{side}", (0.018, PD, PH), (sx * (PW / 2 - 0.009), 0, 0), m["shell"], 0.006, r)
        for side, sz in (("T", 1), ("B", -1)):
            box(f"{self.id}.cap.{side}", (PW, PD, 0.022), (0, 0, sz * (PH / 2 - 0.011)), m["shell"], 0.006, r)
        lip = -PD / 2 - 0.004
        box(f"{self.id}.frame.top", (PW + 0.03, 0.012, 0.03), (0, lip, PH / 2), m["shell"], 0.008, r, 2)
        box(f"{self.id}.frame.bottom", (PW + 0.03, 0.012, 0.03), (0, lip, -PH / 2), m["shell"], 0.008, r, 2)
        box(f"{self.id}.frame.left", (0.03, 0.012, PH + 0.03), (-PW / 2, lip, 0), m["shell"], 0.008, r, 2)
        box(f"{self.id}.frame.right", (0.03, 0.012, PH + 0.03), (PW / 2, lip, 0), m["shell"], 0.008, r, 2)
        for i, z in enumerate(ROWS):
            box(f"{self.id}.rail.{i}", (PW - 0.06, 0.008, 0.035), (0, PD / 2 - 0.02, z), m["rail"], 0.002, r)
        conduit = box(f"{self.id}.conduit", (0.05, 0.05, 0.8), (-0.08, PD / 2 - 0.03, PH / 2 + 0.4), m["conduit"], 0.01, r)
        conduit["diorama_frame_ignore"] = True  # peripheral: thumbnails frame the panel

    def _breaker(self, name, x, z, modules, mat, group, lit=True):
        m, r = self.mats, self.root
        w = MODULE * modules
        front_y = PD / 2 - 0.02 - DEPTH
        box(f"{name}.body", (w - 0.003, DEPTH, 0.085), (x, PD / 2 - 0.02 - DEPTH / 2, z), mat, 0.004, r, 2)
        box(f"{name}.front", (w - 0.008, 0.012, 0.045), (x, front_y - 0.004, z), mat, 0.003, r, 2)
        label_mat = (
            material(f"{name} | status label", srgb("#0D2A22"), 0.3, emission=self.brand, strength=0.0)
            if lit
            else m["inner"]
        )
        box(f"{name}.label", (w - 0.012, 0.004, 0.012), (x, front_y - 0.002, z + 0.034), label_mat, 0.001, r)
        pivots = []
        for k in range(modules):
            pivot = empty(f"{name}.lever_pivot.{k}", r, (x - w / 2 + (k + 0.5) * (w / modules), front_y - 0.01, z))
            box(f"{name}.lever.{k}", (w / modules * 0.55, 0.026, 0.012), (0, -0.012, 0), m["lever"], 0.003, pivot, 2)
            pivot.rotation_euler.x = OFF
            pivots.append(pivot)
        for dz in (0.04, -0.04):
            box(f"{name}.screw.{dz}", (0.006, 0.004, 0.006), (x, front_y - 0.001, z + dz), m["screw"], 0.001, r)
        self.groups[group].append({"levers": pivots, "label": label_mat if lit else None, "x": x, "w": w, "z": z})

    def _modules(self, params):
        left = -PW / 2 + 0.05
        self._breaker(f"{self.id}.main", left + MODULE, ROWS[0], 2, self.mats["main"], "main", lit=False)
        x = left + MODULE * 2 + 0.012
        if params["residualCurrentDevice"]:
            self._breaker(f"{self.id}.dr", x + MODULE * 2, ROWS[0], 4, self.mats["module"], "protections")
            box(
                f"{self.id}.dr.test",
                (0.012, 0.008, 0.012),
                (x + MODULE * 2 + 0.03, PD / 2 - 0.02 - DEPTH - 0.012, ROWS[0] - 0.02),
                self.mats["test"],
                0.002,
                self.root,
            )
            x += MODULE * 4 + 0.012
        if params["surgeProtector"]:
            self._breaker(f"{self.id}.dps", x + MODULE, ROWS[0], 2, self.mats["module"], "protections")
        for i in range(params["circuits"]):
            cx = left + MODULE * (i + 0.5) * 1.15 + 0.01
            self._breaker(f"{self.id}.circuit.{i}", cx, ROWS[1], 1, self.mats["module"], "circuits")

    def _wiring(self, circuits):
        """Two feeds (phase, neutral) into the main breaker, one phase wire per
        circuit breaker, plus earth and neutral bars, so current can be shown
        flowing through the exact wires of a circuit."""
        self.wire_paths = {"main": []}
        main_x = self.groups["main"][0]["x"]
        runs = [("main", main_x - 0.008, ROWS[0], 0), ("main", main_x + 0.008, ROWS[0], 2)]
        for i, item in enumerate(self.groups["circuits"]):
            runs.append((i + 1, item["x"], ROWS[1], i % 2))
        for i, (key, tx, row, color) in enumerate(runs):
            points = [
                (-0.09 + 0.008 * (i % 4), PD / 2 - 0.03, PH / 2 + 0.05),
                (-0.09 + 0.01 * i, PD / 2 - 0.035, PH / 2 - 0.05),
                (tx, PD / 2 - 0.03 - 0.004 * (i % 3), row + 0.075),
                (tx, PD / 2 - 0.02 - DEPTH / 2, row + 0.045),
            ]
            wire(f"{self.id}.wire.{i}", points, self.wires[color], 0.0042, self.root)
            self.wire_paths.setdefault(key, []).append(points)

    def _door(self):
        m = self.mats
        self.door_w = PW + 0.024
        self.door_pivot = empty(f"{self.id}.door_pivot", self.root, (PW / 2 + 0.012, -PD / 2 - 0.012, 0))
        p, w = self.door_pivot, self.door_w
        box(f"{self.id}.door", (w, 0.016, PH + 0.024), (-w / 2, -0.008, 0), m["shell"], 0.007, p, 2)
        for i, z in enumerate(ROWS):
            box(f"{self.id}.door.window.{i}", (w * 0.7, 0.004, 0.06), (-w / 2, -0.018, z), m["window"], 0.003, p)
        box(f"{self.id}.door.handle", (0.018, 0.022, 0.07), (-w + 0.03, -0.026, 0), m["inner"], 0.005, p, 2)
        box(f"{self.id}.door.warning", (0.035, 0.004, 0.035), (-w / 2, -0.018, PH / 2 - 0.05), m["warning"], 0.002, p)

    # -- events -----------------------------------------------------------------
    def open_door(self, event):
        start, end, angle = event["frame"], event["endFrame"], math.radians(event["angleDegrees"])
        span = end - start
        p = self.door_pivot
        key(p, "rotation_euler", 0, (0, 0, 0))
        key(p, "rotation_euler", start, (0, 0, 0))
        # pull, overshoot and settle: the hinge carries weight instead of a linear swing
        for t, fraction in ((0.25, 0.18), (0.5, 0.55), (0.75, 0.85), (0.9, 1.04), (1.0, 1.0)):
            key(p, "rotation_euler", start + round(span * t), (0, 0, angle * fraction))

    def switch_on(self, event):
        groups = ["main", "protections", "circuits"] if event["controls"] == "all" else [event["controls"]]
        frame = event["frame"]
        for group in groups:
            for item in self.groups[group]:
                for pivot in item["levers"]:
                    key(pivot, "rotation_euler", frame, (OFF, 0, 0))
                    key(pivot, "rotation_euler", frame + 3, (ON, 0, 0))
                    key(pivot, "rotation_euler", frame + 5, (SETTLE, 0, 0))
                if item["label"] is not None:
                    socket = item["label"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
                    for f, value in ((frame + 3, 0.0), (frame + 6, 6.0), (frame + 13, 2.5)):
                        socket.default_value = value
                        socket.keyframe_insert("default_value", frame=f + 1)
                frame += event["staggerFrames"]

    def flow(self, event, fps):
        """Pulses of light run along the circuit's wires: each pulse is a thick
        emissive copy of the wire whose bevel factors slide from 0 to 1."""
        start, end = event["frame"], event["endFrame"]
        period = max(4, round(fps / event["pulsesPerSecond"]))
        length = 0.3
        current = material(f"{self.id} | current {start}", srgb("#FFE58A"), 0.3, emission=srgb("#FFE58A"), strength=6.0)
        for n, points in enumerate(self.wire_paths[event["circuit"]]):
            pulse = wire(f"{self.id}.flow.{event['circuit']}.{start}.{n}", points, current, 0.011, self.root)
            data = pulse.data
            data.bevel_factor_mapping_start = "SPLINE"
            data.bevel_factor_mapping_end = "SPLINE"
            pulse.hide_render = True
            pulse.keyframe_insert("hide_render", frame=1)
            pulse.keyframe_insert("hide_render", frame=end + 2)
            pulse.hide_render = False
            pulse.keyframe_insert("hide_render", frame=start + 1)
            for f in range(start, end + 1, 2):
                phase = ((f - start) % period) / period
                head = phase * (1 + length)
                data.bevel_factor_start = max(0.0, min(1.0, head - length))
                data.bevel_factor_end = max(0.0, min(1.0, head))
                data.keyframe_insert("bevel_factor_start", frame=f + 1)
                data.keyframe_insert("bevel_factor_end", frame=f + 1)
            for fcurve in getattr(data.animation_data.action, "fcurves", []):
                for point in fcurve.keyframe_points:
                    point.interpolation = "LINEAR"
            for fcurve in getattr(pulse.animation_data.action, "fcurves", []):
                for point in fcurve.keyframe_points:
                    point.interpolation = "CONSTANT"

    def trip(self, event):
        item = self.groups["circuits"][event["circuit"] - 1]
        frame = event["frame"]
        for pivot in item["levers"]:
            key(pivot, "rotation_euler", frame, (SETTLE, 0, 0))
            key(pivot, "rotation_euler", frame + 2, (OFF - math.radians(6), 0, 0))
            key(pivot, "rotation_euler", frame + 5, (OFF, 0, 0))
        label = item["label"]
        if label is not None:
            principled = label.node_tree.nodes["Principled BSDF"]
            color, strength = principled.inputs["Emission Color"], principled.inputs["Emission Strength"]
            color.keyframe_insert("default_value", frame=frame + 1)
            color.default_value = (*srgb("#FF6B3D"), 1)
            color.keyframe_insert("default_value", frame=frame + 2)
            for f, value in ((frame, 2.5), (frame + 2, 8.0), (frame + 12, 4.0)):
                strength.default_value = value
                strength.keyframe_insert("default_value", frame=f + 1)

    def highlight(self, event):
        if event["controls"] == "circuit":
            items = [self.groups["circuits"][event["circuit"] - 1]]
        else:
            items = self.groups[event["controls"]]
        left = min(i["x"] - i["w"] / 2 for i in items) - 0.008
        right = max(i["x"] + i["w"] / 2 for i in items) + 0.008
        z = items[0]["z"]
        glow = material(
            f"{self.id} | highlight {event['frame']}", srgb("#0D2A22"), 0.3, emission=self.brand, strength=0.0
        )
        y = PD / 2 - 0.02 - DEPTH - 0.012
        cx, width, height = (left + right) / 2, right - left, 0.11
        for name, size, offset in (
            ("top", (width, 0.004, 0.004), (0, 0, height / 2)),
            ("bottom", (width, 0.004, 0.004), (0, 0, -height / 2)),
            ("left", (0.004, 0.004, height), (-width / 2, 0, 0)),
            ("right", (0.004, 0.004, height), (width / 2, 0, 0)),
        ):
            box(f"{self.id}.highlight.{event['frame']}.{name}", size, (cx + offset[0], y, z + offset[2]), glow, 0.0, self.root)
        socket = glow.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
        for f, value in ((0, 0.0), (event["frame"], 0.0), (event["frame"] + 6, 7.0), (event["endFrame"] - 6, 4.0), (event["endFrame"], 0.0)):
            socket.default_value = value
            socket.keyframe_insert("default_value", frame=f + 1)

    def anchor(self, name):
        return self.anchors[name]


def initial_levers_rest(panel):
    """Keep every lever OFF from frame 0 so cache keys never depend on defaults."""
    for group in panel.groups.values():
        for item in group:
            for pivot in item["levers"]:
                key(pivot, "rotation_euler", 0, (OFF, 0, 0))


def world(obj):
    return Vector(obj.matrix_world.translation)
