# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Gabriel Silva
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. See LICENSES/GPL-3.0-or-later.txt.
#
# Diorama command line, executed inside Blender as a separate process:
#   blender -b --factory-startup --offline-mode -noaudio --python-exit-code 1 \
#     --python run.py -- --spec shot.json --out <dir> --start 0 --end 59 \
#     --scale 100 --samples 32 --motion-blur 1
#   blender -b ... --python run.py -- --probe --out <dir>
#   blender -b ... --python run.py -- --thumbnail job.json --out <dir>
# With the Blender extension installed: blender -b -c diorama -- <same arguments>.
# Shots that use library assets also get --assets <resolved.json>: asset id ->
# kind, SHA-256 and absolute file paths, written by the caller after hashing.
# The shot specification is data (spec/shot.schema.json); nothing in it is
# ever executed.

import argparse
import json
import os
import time

import bpy
from mathutils import Vector

from . import __version__
from .core import SpecError, load_shot
from .components import (
    appliance,
    circuit_breaker,
    electrical_panel,
    kitchen_corner,
    library,
    look,
    thumbnail,
)

INTERPRETER_VERSION = __version__
SUPPORTED_BLENDER = (5, 2)
FORMATS = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}


class DioramaError(Exception):
    """A failure with a stable, documented code (see spec/README.md)."""

    def __init__(self, code, detail=""):
        super().__init__(code)
        self.code = code
        self.detail = detail


def fail(code, detail=""):
    raise DioramaError(code, detail)


def checked(spec):
    """Validated, normalized shot (every default applied) or a DioramaError."""
    try:
        return load_shot(spec)
    except SpecError as error:
        path, message = error.issues[0]
        fail(error.code, f"{'/'.join(map(str, path))}: {message}".strip(": "))


def arguments(argv):
    parser = argparse.ArgumentParser(prog="diorama")
    parser.add_argument("--spec")
    parser.add_argument("--out", required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=-1)
    parser.add_argument("--scale", type=int, default=100)
    parser.add_argument("--samples", type=int, default=32)
    parser.add_argument("--motion-blur", type=int, default=1)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--assets")
    parser.add_argument("--thumbnail")
    parser.add_argument("--version", action="version", version=f"diorama3d {__version__}")
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


def resolved_asset(assets, ref, kind):
    item = assets.get(ref["assetId"])
    if not item or item["sha256"] != ref["sha256"] or item["kind"] != kind:
        fail("dioramaAssetMissing", ref["assetId"])
    return item


class Shot:
    def __init__(self, spec, assets=None):
        self.spec = spec
        self.assets = assets or {}
        self.entities = {}

    def anchor(self, ref, frame):
        entity = self.entities[ref["entity"]]
        bpy.context.scene.frame_set(frame + 1)
        return entity.anchor(ref["anchor"]).matrix_world.translation.copy()

    def build(self, studio=False):
        """studio=True builds only the entities (component thumbnails)."""
        spec = self.spec
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.fps = spec["fps"]
        scene.frame_start, scene.frame_end = 1, spec["durationFrames"]
        if not studio:
            surfaces = {
                name: library.pbr_material(
                    f"set | {name} | {ref['assetId']}",
                    resolved_asset(self.assets, ref, "material")["files"],
                    ref["scaleMeters"],
                )
                for name, ref in spec["set"]["params"].get("surfaces", {}).items()
            }
            kitchen_corner.build(spec["set"]["params"], surfaces)
        focus_point = (0, 0, 1.42)
        brand = spec["look"]["brand"]
        # Appliances only get a hollow body and interior when a shot cuts them open.
        sectioned = {event["target"] for event in spec["events"] if event["action"] == "section"}
        for entity in spec["entities"]:
            if entity["component"] == "electrical-panel@1":
                panel = electrical_panel.ElectricalPanel(entity, spec["look"]["brand"])
                electrical_panel.initial_levers_rest(panel)
                self.entities[entity["id"]] = panel
                focus_point = tuple(entity["position"])
            elif entity["component"] == "appliance@1":
                self.entities[entity["id"]] = appliance.Appliance(entity, brand, entity["id"] in sectioned)
            elif entity["component"] == "circuit-breaker@1":
                self.entities[entity["id"]] = circuit_breaker.CircuitBreaker(entity, brand)
                focus_point = tuple(entity["position"])
            elif entity["component"] == "asset@1":
                item = resolved_asset(self.assets, entity["params"], "model")
                self.entities[entity["id"]] = library.AssetInstance(entity, item)
            else:
                fail("dioramaUnknownComponent", entity["component"])
        if not studio:
            look.interior_window(scene, spec["look"], focus_point)
            environment = spec["look"].get("environment")
            if environment:
                item = resolved_asset(self.assets, environment, "hdri")
                library.world_environment(
                    scene.world, item["files"]["hdri"], environment["strength"], environment["rotationDegrees"]
                )
        events = sorted(enumerate(spec["events"]), key=lambda item: (item[1]["frame"], item[0]))
        # 1) world state that other anchors depend on (doors, switches)
        for _, event in events:
            if event["action"] == "open-door":
                self.entities[event["target"]].open_door(event)
            elif event["action"] == "switch-on":
                self.entities[event["target"]].switch_on(event)
            elif event["action"] == "trip":
                self.entities[event["target"]].trip(event)
            elif event["action"] == "flow":
                self.entities[event["target"]].flow(event, spec["fps"])
            elif event["action"] == "highlight":
                self.entities[event["target"]].highlight(event)
            elif event["action"] == "power":
                self.entities[event["target"]].power(event)
            elif event["action"] == "section":
                self.entities[event["target"]].section(event, brand)
            elif event["action"] in ("explode", "assemble"):
                self.entities[event["target"]].explode(event, event["action"] == "assemble")
        # 2) camera last: its focus may follow anchors of the animated world
        if not studio:
            self.camera(scene)
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


def render_thumbnail(args):
    """512 x 512 still for the library: assets or a component example shot."""
    with open(args.thumbnail, encoding="utf-8") as handle:
        job = json.load(handle)
    scene_frame = 1
    if job["mode"] == "asset":
        bpy.ops.wm.read_factory_settings(use_empty=True)
        thumbnail.build_asset(job)
    elif job["mode"] == "component":
        spec = checked(job["spec"])
        Shot(spec).build(studio=job["studio"])
        scene_frame = spec["durationFrames"]
        if job["studio"]:
            bpy.context.scene.frame_set(scene_frame)
            low, high = library.world_bounds(list(bpy.context.scene.objects))
            thumbnail.studio(bpy.context.scene, low, high)
    else:
        fail("dioramaThumbnailFailed", str(job.get("mode")))
    path = os.path.join(args.out, "thumb.png")
    thumbnail.render(bpy.context.scene, path, job["size"], job["samples"], scene_frame)
    print(f"DIORAMA_THUMBNAIL_OK interpreter={INTERPRETER_VERSION}", flush=True)


def run(args):
    check_blender()
    os.makedirs(args.out, exist_ok=True)
    if args.probe:
        probe(args.out)
        return
    if args.thumbnail:
        render_thumbnail(args)
        return
    if not args.spec:
        fail("dioramaSpecMissing")
    with open(args.spec, encoding="utf-8") as handle:
        spec = checked(json.load(handle))
    assets = {}
    if args.assets:
        with open(args.assets, encoding="utf-8") as handle:
            assets = json.load(handle)
    started = time.time()
    Shot(spec, assets).build()
    print(f"DIORAMA_BUILD seconds={time.time() - started:.2f} interpreter={INTERPRETER_VERSION}", flush=True)
    render(args, spec)
    print("DIORAMA_DONE", flush=True)



def main(argv):
    """Runs one command; returns the process exit code (0 ok, 3 known failure)."""
    args = arguments(argv)
    try:
        run(args)
    except DioramaError as error:
        print(f"DIORAMA_ERROR {error.code} {error.detail}".strip(), flush=True)
        return 3
    except RuntimeError as error:
        # Component errors carry a stable code (e.g. dioramaAssetExternalFiles).
        if str(error).startswith("diorama"):
            print(f"DIORAMA_ERROR {error}", flush=True)
            return 3
        raise
    return 0
