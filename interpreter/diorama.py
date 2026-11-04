# SPDX-License-Identifier: GPL-3.0-or-later
# Diorama interpreter for QVid Studio.
#
# Copyright (C) 2026 Gabriel Silva
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. See LICENSE in this directory.
#
# It runs inside Blender as a separate process:
#   blender -b --factory-startup --offline-mode -noaudio --python-exit-code 1 \
#     --python diorama.py -- --spec shot.json --out <dir> --start 0 --end 59 \
#     --scale 100 --samples 32 --motion-blur 1
#   blender -b ... --python diorama.py -- --probe <dir>
# It reads only a declarative shot specification (validated by QVid with Zod)
# and never executes code from the specification.

import argparse
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

# Never write __pycache__ next to the shipped source (read-only when installed).
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from diorama_components import electrical_panel, faceted_character, kitchen_corner, look  # noqa: E402

INTERPRETER_VERSION = "0.1.0"
SUPPORTED_BLENDER = (5, 2)
FORMATS = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}


def fail(code, detail=""):
    print(f"DIORAMA_ERROR {code} {detail}".strip(), flush=True)
    sys.exit(3)


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="diorama")
    parser.add_argument("--spec")
    parser.add_argument("--out", required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=-1)
    parser.add_argument("--scale", type=int, default=100)
    parser.add_argument("--samples", type=int, default=32)
    parser.add_argument("--motion-blur", type=int, default=1)
    parser.add_argument("--probe", action="store_true")
    return parser.parse_args(argv)


def check_blender():
    if tuple(bpy.app.version[:2]) != SUPPORTED_BLENDER:
        fail("dioramaBlenderVersionMismatch", ".".join(map(str, bpy.app.version)))


def probe(out):
    """Smallest EEVEE render that proves a usable GPU context."""
    started = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    look.configure_render(scene, {"scale": 100, "samples": 4, "motionBlur": False}, (64, 64))
    bpy.ops.mesh.primitive_cube_add()
    light = bpy.data.lights.new("probe.light", "SUN")
    scene.collection.objects.link(bpy.data.objects.new("probe.light", light))
    camera = bpy.data.objects.new("probe.camera", bpy.data.cameras.new("probe.camera"))
    scene.collection.objects.link(camera)
    camera.location = (4, -4, 3)
    camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    scene.render.filepath = os.path.join(out, "probe.png")
    bpy.ops.render.render(write_still=True)
    print(f"DIORAMA_PROBE_OK engine={scene.render.engine} seconds={time.time() - started:.2f}", flush=True)


class Shot:
    def __init__(self, spec):
        self.spec = spec
        self.entities = {}

    def anchor(self, ref, frame):
        entity = self.entities[ref["entity"]]
        if isinstance(entity, faceted_character.FacetedCharacter):
            return entity.anchor_position(ref["anchor"], frame)
        bpy.context.scene.frame_set(frame + 1)
        return entity.anchor(ref["anchor"]).matrix_world.translation.copy()

    def build(self):
        spec = self.spec
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.fps = spec["fps"]
        scene.frame_start, scene.frame_end = 1, spec["durationFrames"]
        kitchen_corner.build(spec["set"]["params"])
        focus_point = (0, 0, 1.42)
        for entity in spec["entities"]:
            if entity["component"] == "electrical-panel@1":
                panel = electrical_panel.ElectricalPanel(entity, spec["look"]["brand"])
                electrical_panel.initial_levers_rest(panel)
                self.entities[entity["id"]] = panel
                focus_point = tuple(entity["position"])
            elif entity["component"] == "faceted-character@1":
                self.entities[entity["id"]] = faceted_character.FacetedCharacter(entity)
            else:
                fail("dioramaUnknownComponent", entity["component"])
        look.interior_window(scene, spec["look"], focus_point)
        events = sorted(enumerate(spec["events"]), key=lambda item: (item[1]["frame"], item[0]))
        # 1) world state that other anchors depend on (doors, switches)
        for _, event in events:
            if event["action"] == "open-door":
                self.entities[event["target"]].open_door(event)
            elif event["action"] == "switch-on":
                self.entities[event["target"]].switch_on(event)
        # 2) body motion; hand targets are evaluated on the already-animated world
        for _, event in events:
            actor = self.entities.get(event.get("actor"))
            if event["action"] == "hand":
                target = event["target"]
                position = None if target == "rest" else self.anchor(target, event["frame"])
                actor.hand(event["hand"], event["frame"], position)
            elif event["action"] == "lean":
                actor.lean(event["frame"], event["degrees"])
            elif event["action"] == "blink":
                actor.blink(event["frame"])
            elif event["action"] == "brows":
                actor.brows_to(event["frame"], event["raise"])
        # 3) camera (focus may follow anchors), then gaze (may look at the camera)
        self.camera(scene)
        for _, event in events:
            if event["action"] == "look":
                target = event["target"]
                if target == "camera":
                    scene.frame_set(event["frame"] + 1)
                    position = scene.camera.matrix_world.translation.copy()
                else:
                    position = self.anchor(target, event["frame"])
                self.entities[event["actor"]].look(event["frame"], position)
        for action in bpy.data.actions:
            for fcurve in getattr(action, "fcurves", []):
                for point in fcurve.keyframe_points:
                    point.interpolation = "BEZIER"
                    point.easing = "AUTO"
        scene.frame_set(1)

    def camera(self, scene):
        settings = self.spec["camera"]
        data = bpy.data.cameras.new("camera")
        data.sensor_fit = "VERTICAL"
        data.dof.use_dof = True
        data.dof.aperture_fstop = settings["apertureFStop"]
        cam = bpy.data.objects.new("camera", data)
        scene.collection.objects.link(cam)
        scene.camera = cam
        aim = bpy.data.objects.new("camera.aim", None)
        focus = bpy.data.objects.new("camera.focus", None)
        for obj in (aim, focus):
            scene.collection.objects.link(obj)
        data.dof.focus_object = focus
        track = cam.constraints.new("TRACK_TO")
        track.target = aim
        track.track_axis = "TRACK_NEGATIVE_Z"
        track.up_axis = "UP_Y"
        for key in settings["keys"]:
            frame = key["frame"] + 1
            cam.location = key["position"]
            cam.keyframe_insert("location", frame=frame)
            aim.location = key["target"]
            aim.keyframe_insert("location", frame=frame)
            data.lens = key["lens"]
            data.keyframe_insert("lens", frame=frame)
            focus_point = key.get("focus", key["target"])
            if isinstance(focus_point, dict):
                focus_point = self.anchor(focus_point, key["frame"])
            focus.location = focus_point
            focus.keyframe_insert("location", frame=frame)


def render(args, spec):
    scene = bpy.context.scene
    look.configure_render(
        scene,
        {"scale": args.scale, "samples": args.samples, "motionBlur": args.motion_blur},
        FORMATS[spec["format"]],
    )
    last = spec["durationFrames"] - 1
    end = last if args.end < 0 else min(args.end, last)
    if not 0 <= args.start <= end:
        fail("dioramaInvalidFrameRange", f"{args.start}..{end}")
    scene.frame_start, scene.frame_end = args.start + 1, end + 1
    scene.render.filepath = os.path.join(args.out, "f_#####")

    def written(_scene, *_):
        print(f"DIORAMA_FRAME {_scene.frame_current - 1}", flush=True)

    bpy.app.handlers.render_write.append(written)
    bpy.ops.render.render(animation=True)


def main():
    args = arguments()
    check_blender()
    os.makedirs(args.out, exist_ok=True)
    if args.probe:
        probe(args.out)
        return
    if not args.spec:
        fail("dioramaSpecMissing")
    with open(args.spec, encoding="utf-8") as handle:
        spec = json.load(handle)
    if spec.get("schema") != "qvid.diorama.shot/0":
        fail("dioramaUnsupportedSpec", str(spec.get("schema")))
    started = time.time()
    Shot(spec).build()
    print(f"DIORAMA_BUILD seconds={time.time() - started:.2f} interpreter={INTERPRETER_VERSION}", flush=True)
    render(args, spec)
    print("DIORAMA_DONE", flush=True)


main()
