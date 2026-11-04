# SPDX-License-Identifier: GPL-3.0-or-later
# Diorama component appliance@1: countertop toaster or kettle with a power state.
# Powering on lights the heating elements (toaster slots / kettle base ring) and
# the status LED; powering off fades them out. kitchen-corner@1 reuses the same
# models for its built-in props so both paths look identical.

import math

from mathutils import Vector

import bpy

from .common import box, empty, faceted_blob, link, material, seeded_random, srgb, wire

HEAT = srgb("#FF7A2E")


def _glow_key(mat, frame, strength):
    socket = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    socket.default_value = strength
    socket.keyframe_insert("default_value", frame=frame + 1)


def build_toaster(name, root, color="#C9D3D2", brand="#00DC82"):
    steel = material(f"{name} | body", srgb(color), 0.25, metal=0.9)
    dark = material(f"{name} | dark parts", srgb("#2A3231"), 0.5)
    heat = material(f"{name} | heating elements", srgb("#3A1A10"), 0.6, emission=HEAT, strength=0.0)
    led = material(f"{name} | led", srgb("#10261E"), 0.3, emission=srgb(brand), strength=0.0)
    box(f"{name}.body", (0.28, 0.17, 0.19), (0, 0, 0.095), steel, 0.035, root, 3)
    for k in (-0.05, 0.05):
        box(f"{name}.slot.{k}", (0.2, 0.025, 0.01), (0, k, 0.188), dark, 0.004, root)
        box(f"{name}.element.{k}", (0.18, 0.012, 0.004), (0, k, 0.183), heat, 0.001, root)
    box(f"{name}.lever", (0.03, 0.04, 0.02), (0.15, 0, 0.12), dark, 0.006, root)
    box(f"{name}.led", (0.012, 0.012, 0.012), (0.15, -0.04, 0.06), led, 0.003, root)
    return {"glow": [heat], "led": [led], "indicator": (0.15, -0.04, 0.06)}


def build_kettle(name, root, color="#1B8F77", brand="#00DC82"):
    rng = seeded_random("appliance@1", name)
    shell = material(f"{name} | body", srgb(color), 0.3, coat=0.5)
    dark = material(f"{name} | dark parts", srgb("#2A3231"), 0.5)
    ring = material(f"{name} | base ring", srgb("#3A1A10"), 0.6, emission=HEAT, strength=0.0)
    led = material(f"{name} | led", srgb("#10261E"), 0.3, emission=srgb(brand), strength=0.0)
    faceted_blob(f"{name}.body", 0.1, (0, 0, 0.12), shell, rng, 2, 0.03, (1, 1, 1.15), root)
    box(f"{name}.lid", (0.07, 0.07, 0.03), (0, 0, 0.235), dark, 0.01, root)
    wire(f"{name}.handle", [(0.07, 0, 0.1), (0.13, 0, 0.17), (0.06, 0, 0.23)], dark, 0.012, root)
    box(f"{name}.base", (0.2, 0.2, 0.02), (0, 0, 0.01), dark, 0.008, root)
    box(f"{name}.ring", (0.17, 0.17, 0.004), (0, 0, 0.021), ring, 0.002, root)
    box(f"{name}.led", (0.014, 0.01, 0.01), (0, -0.1, 0.012), led, 0.002, root)
    return {"glow": [ring], "led": [led], "indicator": (0, -0.1, 0.012)}


class Appliance:
    def __init__(self, spec, brand):
        self.id = spec["id"]
        params = spec["params"]
        self.root = empty(self.id, location=tuple(spec["position"]))
        self.root.rotation_euler.z = math.radians(spec.get("yawDegrees", 0))
        builder = build_toaster if params["kind"] == "toaster" else build_kettle
        kwargs = {"brand": brand["primary"]}
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

    def anchor(self, name):
        return self.anchors[name]


def world(obj):
    return Vector(obj.matrix_world.translation)
