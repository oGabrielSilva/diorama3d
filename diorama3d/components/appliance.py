# SPDX-License-Identifier: GPL-3.0-or-later
# Diorama component appliance@1: countertop toaster or kettle with a power state.
# Powering on lights the heating elements (toaster slots / kettle base ring) and
# the status LED; powering off fades them out. kitchen-corner@1 reuses the same
# models for its built-in props so both paths look identical. A shot that cuts
# an appliance open (`section`) gets a hollow body and a modeled interior:
# toaster slots with mica boards, glowing nichrome and bread; kettle water over
# a heating element.

import math

from mathutils import Vector

import bpy

from .common import box, empty, faceted_blob, link, material, seeded_random, srgb, wire
from .mechanism import cylinder, hollow, section

HEAT = srgb("#FF7A2E")


def _glow_key(mat, frame, strength):
    socket = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    socket.default_value = strength
    socket.keyframe_insert("default_value", frame=frame + 1)


def build_toaster(name, root, color="#C9D3D2", brand="#00DC82", interior=False):
    steel = material(f"{name} | body", srgb(color), 0.25, metal=0.9)
    dark = material(f"{name} | dark parts", srgb("#2A3231"), 0.5)
    heat = material(f"{name} | heating elements", srgb("#3A1A10"), 0.6, emission=HEAT, strength=0.0)
    led = material(f"{name} | led", srgb("#10261E"), 0.3, emission=srgb(brand), strength=0.0)
    body = box(f"{name}.body", (0.28, 0.17, 0.19), (0, 0, 0.095), steel, 0.035, root, 3)
    cut = [body]
    for k in (-0.05, 0.05):
        cut.append(box(f"{name}.slot.{k}", (0.2, 0.025, 0.01), (0, k, 0.188), dark, 0.004, root))
        cut.append(box(f"{name}.element.{k}", (0.18, 0.012, 0.004), (0, k, 0.183), heat, 0.001, root))
    cut.append(box(f"{name}.lever", (0.03, 0.04, 0.02), (0.15, 0, 0.12), dark, 0.006, root))
    cut.append(box(f"{name}.led", (0.012, 0.012, 0.012), (0.15, -0.04, 0.06), led, 0.003, root))
    parts = {"glow": [heat], "led": [led], "indicator": (0.15, -0.04, 0.06), "cut": [(o, "TRANSFER") for o in cut]}
    if interior:
        hollow(body, (0.25 / 0.28, 0.15 / 0.17, 0.17 / 0.19), material(f"{name} | inside", srgb("#3A3F3E"), 0.6, metal=0.6))
        mica = material(f"{name} | mica boards", srgb("#D8C9A3"), 0.7)
        bread = material(f"{name} | bread", srgb("#D9A55B"), 0.8)
        for k in (-0.05, 0.05):
            box(f"{name}.bread.{k}", (0.17, 0.014, 0.125), (0, k, 0.105), bread, 0.012, root, 2)
            for side in (-1, 1):
                y = k + side * 0.018
                box(f"{name}.mica.{k}.{side}", (0.2, 0.003, 0.15), (0, y, 0.1), mica, 0.0, root)
                # the ribbon is wound around the board, so it shows on both faces
                for face in (-1, 1):
                    zig = [(-0.09 + 0.18 * i / 12, y + face * 0.0032, 0.035 if i % 2 else 0.165) for i in range(13)]
                    wire(f"{name}.nichrome.{k}.{side}.{face}", zig, heat, 0.0016, root)
        parts["section_range"] = (0.2, -0.005)
    return parts


def build_kettle(name, root, color="#1B8F77", brand="#00DC82", interior=False):
    rng = seeded_random("appliance@1", name)
    shell = material(f"{name} | body", srgb(color), 0.3, coat=0.5)
    dark = material(f"{name} | dark parts", srgb("#2A3231"), 0.5)
    ring = material(f"{name} | base ring", srgb("#3A1A10"), 0.6, emission=HEAT, strength=0.0)
    led = material(f"{name} | led", srgb("#10261E"), 0.3, emission=srgb(brand), strength=0.0)
    body = faceted_blob(f"{name}.body", 0.1, (0, 0, 0.12), shell, rng, 2, 0.03, (1, 1, 1.15), root)
    lid = box(f"{name}.lid", (0.07, 0.07, 0.03), (0, 0, 0.235), dark, 0.01, root)
    wire(f"{name}.handle", [(0.07, 0, 0.1), (0.13, 0, 0.17), (0.06, 0, 0.23)], dark, 0.012, root)
    box(f"{name}.base", (0.2, 0.2, 0.02), (0, 0, 0.01), dark, 0.008, root)
    box(f"{name}.ring", (0.17, 0.17, 0.004), (0, 0, 0.021), ring, 0.002, root)
    box(f"{name}.led", (0.014, 0.01, 0.01), (0, -0.1, 0.012), led, 0.002, root)
    parts = {"glow": [ring], "led": [led], "indicator": (0, -0.1, 0.012), "cut": [(body, "TRANSFER"), (lid, "TRANSFER")]}
    if interior:
        hollow(body, (0.9, 0.9, 0.92), material(f"{name} | inside", srgb("#C7D0CF"), 0.35, metal=0.8))
        water = material(f"{name} | water", srgb("#3C9BE0"), 0.08, coat=0.6)
        volume = cylinder(f"{name}.water", 0.058, 0.1, (0, 0, 0.105), "z", water, root, 16)
        parts["cut"].append((volume, "INDEX"))
        plate = material(f"{name} | element plate", srgb("#9AA5A5"), 0.3, metal=1.0)
        cylinder(f"{name}.element.plate", 0.05, 0.004, (0, 0, 0.047), "z", plate, root, 16)
        coil = [(0.038 * math.cos(a * math.pi / 8), 0.038 * math.sin(a * math.pi / 8), 0.052) for a in range(17)]
        wire(f"{name}.element.coil", coil, ring, 0.0045, root)
        parts["section_range"] = (0.27, 0.0)
    return parts


class Appliance:
    def __init__(self, spec, brand, interior=False):
        self.id = spec["id"]
        params = spec["params"]
        self.root = empty(self.id, location=tuple(spec["position"]))
        self.root.rotation_euler.z = math.radians(spec.get("yawDegrees", 0))
        builder = build_toaster if params["kind"] == "toaster" else build_kettle
        kwargs = {"brand": brand["primary"], "interior": interior}
        if params.get("color"):
            kwargs["color"] = params["color"]
        self.parts = builder(self.id, self.root, **kwargs)
        self.anchors = {
            "center": empty(f"{self.id}.anchor.center", self.root, (0, 0, 0.1)),
            "indicator": empty(f"{self.id}.anchor.indicator", self.root, self.parts["indicator"]),
        }
        for mat in self.parts["glow"] + self.parts["led"]:
            _glow_key(mat, 0, 0.0)
        # warm light that spills on the wall/backsplash so heating reads from any angle
        data = bpy.data.lights.new(f"{self.id}.heat_light", "POINT")
        data.color = HEAT
        data.shadow_soft_size = 0.05
        self.heat_light = link(bpy.data.objects.new(f"{self.id}.heat_light", data), self.root)
        self.heat_light.location = (0, 0.03, 0.26 if params["kind"] == "toaster" else 0.06)
        data.energy = 0.0
        data.keyframe_insert("energy", frame=1)

    def power(self, event):
        frame, on = event["frame"], event["state"] == "on"
        for mat in self.parts["led"]:
            _glow_key(mat, frame, 0.0 if on else 3.0)
            _glow_key(mat, frame + 3, 3.0 if on else 0.0)
        # heating elements warm up slowly and cool down a little faster
        light = self.heat_light.data
        for f, value in ((frame, 0.0 if on else 6.0), (frame + (18 if on else 10), 6.0 if on else 0.0)):
            light.energy = value
            light.keyframe_insert("energy", frame=f + 1)
        for mat in self.parts["glow"]:
            if on:
                _glow_key(mat, frame, 0.0)
                _glow_key(mat, frame + 18, 4.0)
            else:
                _glow_key(mat, frame, 4.0)
                _glow_key(mat, frame + 10, 0.0)

    def section(self, event, brand):
        """Cuts the shell (and the water) open; interior parts stay whole."""
        cap_color = event.get("capColor") or brand["primary"]
        cap = material(f"{self.id} | section cap {event['frame']}", srgb(cap_color), 0.55)
        top, bottom = self.parts["section_range"]
        targets = [(obj, self.root, mode) for obj, mode in self.parts["cut"]]
        section(
            f"{self.id}.section.{event['frame']}", targets, event["axis"], event["side"], 0.0, top, bottom,
            event["frame"], event["endFrame"], cap,
        )

    def anchor(self, name):
        return self.anchors[name]


def world(obj):
    return Vector(obj.matrix_world.translation)
