# SPDX-License-Identifier: GPL-3.0-or-later
# Diorama thumbnails: neutral studio (grey floor and world, three area lights,
# 3/4 camera framed on the subject bounds) for models, materials and
# components; HDRIs shown as a mirror/diffuse sphere pair under that HDRI.

import math

import bmesh
import bpy
from mathutils import Vector

from . import library
from .common import link, material, srgb
from .look import configure_render

STUDIO_GREY = srgb("#8A8F92")


def _area(name, location, target, power, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.size = size
    obj = link(bpy.data.objects.new(name, data))
    obj.location = location
    obj.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    return obj


def _world(scene, color, strength):
    world = bpy.data.worlds.new("thumbnail.world")
    scene.world = world
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (*color, 1)
    background.inputs["Strength"].default_value = strength
    return world


def _camera(scene, center, radius, azimuth=35.0, elevation=22.0, lens=50.0):
    data = bpy.data.cameras.new("thumbnail.camera")
    data.lens = lens
    data.sensor_fit = "AUTO"
    camera = link(bpy.data.objects.new("thumbnail.camera", data))
    a, e = math.radians(azimuth), math.radians(elevation)
    direction = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    half_fov = math.atan(data.sensor_width / 2 / lens)
    distance = radius / math.sin(half_fov) * 1.08
    camera.location = center + direction * distance
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    data.clip_start = max(distance / 1000, 0.001)
    data.clip_end = distance * 50
    scene.camera = camera
    return distance


def studio(scene, low, high):
    """Grey floor under the subject, soft key/fill/rim and a framed camera."""
    center = (low + high) / 2
    radius = max((high - low).length / 2, 0.03)
    _world(scene, STUDIO_GREY, 0.8)
    floor_mat = material("thumbnail | floor", STUDIO_GREY, 0.85)
    mesh = bpy.data.meshes.new("thumbnail.floor")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=radius * 30)
    bm.to_mesh(mesh)
    bm.free()
    floor = link(bpy.data.objects.new("thumbnail.floor", mesh))
    floor.location = (center.x, center.y, low.z)
    floor.data.materials.append(floor_mat)
    distance = _camera(scene, center, radius)
    reach = distance * 0.9
    scale = reach * reach
    _area("thumbnail.key", center + Vector((-0.55, -0.7, 0.75)).normalized() * reach, center, 22 * scale, radius * 2.2)
    _area("thumbnail.fill", center + Vector((0.85, -0.45, 0.3)).normalized() * reach, center, 7 * scale, radius * 3)
    _area("thumbnail.rim", center + Vector((0.2, 0.9, 0.65)).normalized() * reach, center, 14 * scale, radius * 1.5)


def _sphere(name, location, mat, radius=0.5):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=radius, calc_uvs=True)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj = link(bpy.data.objects.new(name, mesh))
    obj.location = location
    obj.data.materials.append(mat)
    return obj


def build_asset(job):
    """Builds a thumbnail scene for a library asset (model, material or HDRI)."""
    scene = bpy.context.scene
    kind, files = job["kind"], job["files"]
    if kind == "model":
        objects = library.load_model(files["model"])
        low, high = library.world_bounds(objects)
        studio(scene, low, high)
    elif kind == "material":
        mat = library.pbr_material("thumbnail | material", files, job.get("scaleMeters", 1.0))
        sphere = _sphere("thumbnail.sphere", (0, 0, 0.5), mat)
        low, high = library.world_bounds([sphere])
        studio(scene, low, high)
    elif kind == "hdri":
        world = _world(scene, (0, 0, 0), 1.0)
        library.world_environment(world, files["hdri"], 1.0, 0.0)
        mirror = material("thumbnail | mirror", (0.9, 0.9, 0.9), 0.04, metal=1.0)
        diffuse = material("thumbnail | diffuse", (0.8, 0.8, 0.8), 0.95)
        _sphere("thumbnail.mirror", (-0.56, 0, 0), mirror)
        _sphere("thumbnail.diffuse", (0.56, 0, 0), diffuse)
        _camera(scene, Vector((0, 0, 0)), 1.12, azimuth=0.0, elevation=6.0)
    else:
        raise RuntimeError(f"dioramaThumbnailKind {kind}")


def render(scene, path, size, samples, frame=1):
    configure_render(scene, {"scale": 100, "samples": samples, "motionBlur": False}, (size, size))
    scene.frame_set(frame)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
