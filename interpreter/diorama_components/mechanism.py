# SPDX-License-Identifier: GPL-3.0-or-later
# Diorama mechanism helpers shared by object components: extruded profiles,
# hollow housings, animated cutaways (`section`) with solid caps and exploded
# views (`explode` / `assemble`) whose parts travel along designed vectors.
# This component runs inside Blender and is distributed under the GNU GPL v3
# or later (see ../LICENSE). It only reads declarative shot specifications.

import math

import bmesh
import bpy
from bpy_extras import anim_utils
from mathutils import Matrix, Vector

from .common import box, empty, flat, key, link

CUTTER_SIZE = 4.0


def fcurves_of(id_data):
    """F-curves of an ID through its action slot (Blender 5 slotted actions)."""
    data = getattr(id_data, "animation_data", None)
    if data is None or data.action is None:
        return []
    bag = anim_utils.action_get_channelbag_for_slot(data.action, data.action_slot)
    return list(bag.fcurves) if bag else []


def set_interpolation(id_data, mode):
    for fcurve in fcurves_of(id_data):
        for point in fcurve.keyframe_points:
            point.interpolation = mode


def _object(name, bm, mats, parent, location=(0, 0, 0)):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = link(bpy.data.objects.new(name, mesh), parent)
    obj.location = location
    for mat in mats:
        obj.data.materials.append(mat)
    flat(obj)
    return obj


def _lift(u, v, axis, w):
    """2D profile point (u, v) on the plane normal to `axis`, at depth w."""
    if axis == "x":
        return (w, u, v)
    if axis == "y":
        return (u, w, v)
    return (u, v, w)


def bevel(obj, width, segments=1):
    mod = obj.modifiers.new("chamfer", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    return obj


def prism(name, profile, axis, a0, a1, mat, parent=None, chamfer=0.0):
    """Closed solid: a simple 2D polygon extruded along an axis from a0 to a1."""
    bm = bmesh.new()
    low = [bm.verts.new(_lift(u, v, axis, a0)) for u, v in profile]
    high = [bm.verts.new(_lift(u, v, axis, a1)) for u, v in profile]
    bm.faces.new(low)
    bm.faces.new(high)
    for k in range(len(profile)):
        j = (k + 1) % len(profile)
        bm.faces.new((low[k], low[j], high[j], high[k]))
    obj = _object(name, bm, [mat], parent)
    return bevel(obj, chamfer) if chamfer else obj


def hollow_prism(name, outer, inner, axis, outside, rim, floor, mats, parent=None):
    """Closed tray (half shell): outer profile from `outside` to the open `rim`,
    walls following `inner` back to the cavity `floor`. Material slot 0 is the
    outer surface and the rim, slot 1 the cavity, so cut caps read clearly."""
    bm = bmesh.new()
    n = len(outer)
    o_out = [bm.verts.new(_lift(u, v, axis, outside)) for u, v in outer]
    o_rim = [bm.verts.new(_lift(u, v, axis, rim)) for u, v in outer]
    i_rim = [bm.verts.new(_lift(u, v, axis, rim)) for u, v in inner]
    i_floor = [bm.verts.new(_lift(u, v, axis, floor)) for u, v in inner]
    bm.faces.new(o_out).material_index = 0
    bm.faces.new(i_floor).material_index = 1
    for k in range(n):
        j = (k + 1) % n
        bm.faces.new((o_out[k], o_out[j], o_rim[j], o_rim[k])).material_index = 0
        bm.faces.new((o_rim[k], o_rim[j], i_rim[j], i_rim[k])).material_index = 0
        bm.faces.new((i_rim[k], i_rim[j], i_floor[j], i_floor[k])).material_index = 1
    return _object(name, bm, mats, parent)


def hollow(obj, inner_scale, inner_mat):
    """Turns a closed mesh into a shell: an inward-facing copy scaled about the
    object origin becomes the cavity, painted with inner_mat."""
    obj.data.materials.append(inner_mat)
    index = len(obj.data.materials) - 1
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    copy = bmesh.ops.duplicate(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces))["geom"]
    sx, sy, sz = inner_scale
    for vert in (item for item in copy if isinstance(item, bmesh.types.BMVert)):
        vert.co = Vector((vert.co.x * sx, vert.co.y * sy, vert.co.z * sz))
    faces = [item for item in copy if isinstance(item, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=faces)
    for face in faces:
        face.material_index = index
    bm.to_mesh(obj.data)
    bm.free()
    flat(obj)
    return obj


def cylinder(name, radius, length, center, axis, mat, parent=None, segments=12, chamfer=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=segments, radius1=radius, radius2=radius, depth=length
    )
    if axis == "x":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
    elif axis == "y":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "X"))
    obj = _object(name, bm, [mat], parent, center)
    return bevel(obj, chamfer) if chamfer else obj


def bar(name, p0, p1, width, thickness, mat, parent=None, chamfer=0.0):
    """Box from p0 to p1 lying in the y-z plane (x is the bar width)."""
    a, b = Vector(p0), Vector(p1)
    direction = b - a
    obj = box(name, (width, direction.length, thickness), tuple((a + b) / 2), mat, chamfer, parent)
    obj.rotation_euler.x = math.atan2(direction.z, direction.y)
    return obj


class Exploder:
    """Parts are grouped under pivots; explode/assemble key the pivots along
    designed vectors with stagger, an eased start and a small settle."""

    def __init__(self):
        self.groups = []
        self.scale = 0.0

    def group(self, name, parent, vector):
        pivot = empty(name, parent)
        key(pivot, "location", 0, (0, 0, 0))
        self.groups.append((pivot, Vector(vector)))
        return pivot

    def animate(self, event, assemble=False):
        start, end = event["frame"], event["endFrame"]
        span = end - start
        count = len(self.groups)
        stagger = event["staggerFrames"]
        if count > 1:
            stagger = max(0, min(stagger, (span - 6) // (count - 1)))
        duration = max(2, span - stagger * (count - 1))
        before = self.scale
        after = 0.0 if assemble else event["distance"]
        order = list(reversed(self.groups)) if assemble else self.groups
        for index, (pivot, vector) in enumerate(order):
            first = start + index * stagger
            last = first + duration
            key(pivot, "location", first, tuple(vector * before))
            overshoot = after + (after - before) * 0.04
            key(pivot, "location", first + round(duration * 0.8), tuple(vector * overshoot))
            key(pivot, "location", last, tuple(vector * after))
        self.scale = after


def section(name, targets, axis, side, plane, z_top, z_bottom, frame, end, cap):
    """Animated cutaway. A hidden cutter box removes the `side` half of every
    target (beyond `plane` along `axis`), sweeping from z_top down to z_bottom
    between frame and end. targets: (object, cutter parent, material mode);
    TRANSFER paints new faces with the cap material, INDEX keeps the part's own
    material (water, for example). Returns the frame at which height z is cut."""
    sign = -1.0 if side == "negative" else 1.0
    half = CUTTER_SIZE / 2
    for index, (obj, parent, mode) in enumerate(targets):
        offset = plane + sign * half
        location = (offset, 0, 0) if axis == "x" else (0, offset, 0)
        cutter = box(f"{name}.cutter.{index}", (CUTTER_SIZE,) * 3, location, cap, 0.0, parent)
        cutter.hide_render = True
        cutter.display_type = "WIRE"
        key(cutter, "location", 0, (location[0], location[1], z_top + half))
        key(cutter, "location", frame, (location[0], location[1], z_top + half))
        key(cutter, "location", end, (location[0], location[1], z_bottom + half))
        mod = obj.modifiers.new(f"section.{name}", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = cutter
        mod.material_mode = mode

    def frame_at(z):
        t = min(1.0, max(0.0, (z_top - z) / (z_top - z_bottom)))
        return frame + round((end - frame) * t)

    return frame_at
