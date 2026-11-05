# SPDX-License-Identifier: GPL-3.0-or-later
# Diorama — shared modeling helpers.
# This component runs inside Blender and is distributed under the GNU GPL v3
# or later (see ../LICENSE). It only reads declarative shot specifications.

import hashlib
import math
import random

import bmesh
import bpy
from mathutils import Vector


def srgb(hex_color):
    h = hex_color.lstrip("#")
    c = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def seeded_random(*parts):
    """Deterministic RNG per component instance (no global random state)."""
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def material(name, color, roughness=0.6, metal=0.0, emission=None, strength=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = roughness
    p.inputs["Metallic"].default_value = metal
    if coat:
        p.inputs["Coat Weight"].default_value = coat
    if emission:
        p.inputs["Emission Color"].default_value = (*emission, 1)
        p.inputs["Emission Strength"].default_value = strength
    return m


def link(obj, parent=None):
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def empty(name, parent=None, location=(0, 0, 0)):
    obj = link(bpy.data.objects.new(name, None), parent)
    obj.location = location
    return obj


def flat(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = False


def box(name, size, loc, mat, bevel=0.0, parent=None, segments=1):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    obj = link(bpy.data.objects.new(name, me), parent)
    obj.location = loc
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("chamfer", "BEVEL")
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = "ANGLE"
    flat(obj)
    return obj


def faceted_blob(name, radius, loc, mat, rng, subdiv=2, jitter=0.08, scale=(1, 1, 1), parent=None):
    """Low-poly organic form: icosphere with seeded jitter and anisotropic scale."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    for v in bm.verts:
        n = v.co.normalized()
        v.co += n * radius * rng.uniform(-jitter, jitter)
        v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
    bm.to_mesh(me)
    bm.free()
    obj = link(bpy.data.objects.new(name, me), parent)
    obj.location = loc
    obj.data.materials.append(mat)
    flat(obj)
    return obj


def faceted_plane(name, w, h, loc, rot, mat, rng, cuts=(10, 14), jitter=0.006):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=cuts[0], y_segments=cuts[1], size=0.5)
    bmesh.ops.scale(bm, vec=Vector((w, h, 1)), verts=bm.verts)
    for v in bm.verts:
        v.co.z += rng.uniform(-jitter, jitter)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    obj = link(bpy.data.objects.new(name, me))
    obj.location = loc
    obj.rotation_euler = rot
    obj.data.materials.append(mat)
    flat(obj)
    return obj


def wire(name, points, mat, radius=0.0045, parent=None):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 1
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    obj = link(bpy.data.objects.new(name, cu), parent)
    obj.data.materials.append(mat)
    return obj


def world_position(obj, frame):
    """World position of an object at a spec frame (0-based)."""
    scene = bpy.context.scene
    scene.frame_set(frame + 1)
    return obj.matrix_world.translation.copy()


def key(obj, path, frame, value=None, index=-1):
    if value is not None:
        setattr(obj, path, value)
    obj.keyframe_insert(path, frame=frame + 1, index=index)


def radians(value):
    return math.radians(value)
