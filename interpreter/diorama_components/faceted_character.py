# SPDX-License-Identifier: GPL-3.0-or-later
# Diorama component faceted-character@1: continuous skinned body in the channel's
# faceted family, a named 17-bone rig, IK on both arms (A-pose rest), gaze by a
# damped track constraint, lean, blink and brow raise. Fingers and a facial rig
# arrive with the Rigify-based character in a later component version.

import math

import bpy
from mathutils import Matrix, Vector

from .common import box, faceted_blob, flat, key, link, material, seeded_random, srgb

JOINTS = {
    "pelvis": (0, 0, 0.80),
    "spine": (0, 0.005, 1.00),
    "chest": (0, 0.0, 1.20),
    "neck": (0, 0.0, 1.31),
    "head": (0, -0.005, 1.37),
}
for _s, _x in (("L", 1), ("R", -1)):
    JOINTS.update(
        {
            f"clav.{_s}": (_x * 0.06, 0.0, 1.27),
            f"shoulder.{_s}": (_x * 0.17, 0.0, 1.26),
            f"elbow.{_s}": (_x * 0.33, 0.03, 1.08),
            f"wrist.{_s}": (_x * 0.47, 0.0, 0.91),
            f"hand.{_s}": (_x * 0.53, -0.01, 0.85),
            f"thumb.{_s}": (_x * 0.49, -0.045, 0.875),
            f"hip.{_s}": (_x * 0.085, 0.0, 0.78),
            f"knee.{_s}": (_x * 0.095, -0.01, 0.43),
            f"ankle.{_s}": (_x * 0.10, 0.02, 0.08),
            f"toe.{_s}": (_x * 0.105, -0.12, 0.035),
        }
    )
HEAD_TOP = (0, -0.005, 1.62)
EDGES = [("pelvis", "spine"), ("spine", "chest"), ("chest", "neck"), ("neck", "head")]
RADII = {"pelvis": (0.135, 0.10), "spine": (0.125, 0.09), "chest": (0.15, 0.10), "neck": (0.058, 0.055), "head": (0.055, 0.05)}
for _s in ("L", "R"):
    EDGES += [
        ("chest", f"clav.{_s}"),
        (f"clav.{_s}", f"shoulder.{_s}"),
        (f"shoulder.{_s}", f"elbow.{_s}"),
        (f"elbow.{_s}", f"wrist.{_s}"),
        (f"wrist.{_s}", f"hand.{_s}"),
        (f"wrist.{_s}", f"thumb.{_s}"),
        ("pelvis", f"hip.{_s}"),
        (f"hip.{_s}", f"knee.{_s}"),
        (f"knee.{_s}", f"ankle.{_s}"),
        (f"ankle.{_s}", f"toe.{_s}"),
    ]
    RADII.update(
        {
            f"clav.{_s}": (0.07, 0.07),
            f"shoulder.{_s}": (0.06, 0.06),
            f"elbow.{_s}": (0.048, 0.048),
            f"wrist.{_s}": (0.034, 0.03),
            f"hand.{_s}": (0.04, 0.022),
            f"thumb.{_s}": (0.016, 0.016),
            f"hip.{_s}": (0.085, 0.085),
            f"knee.{_s}": (0.06, 0.06),
            f"ankle.{_s}": (0.045, 0.045),
            f"toe.{_s}": (0.05, 0.035),
        }
    )
BONES = [("root", None, "pelvis"), ("spine", "pelvis", "spine"), ("chest", "spine", "chest"), ("neck", "chest", "neck"), ("head", "head", "head_top")]
PARENT = {"spine": "root", "chest": "spine", "neck": "chest", "head": "neck"}
for _s in ("L", "R"):
    BONES += [
        (f"clavicle.{_s}", f"clav.{_s}", f"shoulder.{_s}"),
        (f"upper_arm.{_s}", f"shoulder.{_s}", f"elbow.{_s}"),
        (f"forearm.{_s}", f"elbow.{_s}", f"wrist.{_s}"),
        (f"hand.{_s}", f"wrist.{_s}", f"hand.{_s}"),
        (f"thigh.{_s}", f"hip.{_s}", f"knee.{_s}"),
        (f"shin.{_s}", f"knee.{_s}", f"ankle.{_s}"),
        (f"foot.{_s}", f"ankle.{_s}", f"toe.{_s}"),
    ]
    PARENT.update(
        {
            f"clavicle.{_s}": "chest",
            f"upper_arm.{_s}": f"clavicle.{_s}",
            f"forearm.{_s}": f"upper_arm.{_s}",
            f"hand.{_s}": f"forearm.{_s}",
            f"thigh.{_s}": "root",
            f"shin.{_s}": f"thigh.{_s}",
            f"foot.{_s}": f"shin.{_s}",
        }
    )
CONNECTED = {"forearm.L", "forearm.R", "shin.L", "shin.R", "hand.L", "hand.R", "foot.L", "foot.R"}
ZONES = ("jacket", "jacket_trim", "pants", "skin", "shoe", "shoe_sole")


def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length


class FacetedCharacter:
    def __init__(self, spec):
        self.id = spec["id"]
        params = spec["params"]
        self.rng = seeded_random("faceted-character@1", self.id)
        self.mats = {
            "jacket": material(f"{self.id} | jacket", srgb(params["jacket"]), 0.6),
            "jacket_trim": material(f"{self.id} | jacket trim", srgb("#E9F6F1"), 0.5),
            "pants": material(f"{self.id} | pants", srgb(params["pants"]), 0.7),
            "skin": material(f"{self.id} | skin", srgb(params["skin"]), 0.55),
            "shoe": material(f"{self.id} | shoes", srgb("#ECEFF0"), 0.5),
            "shoe_sole": material(f"{self.id} | soles", srgb("#30393A"), 0.7),
            "hair": material(f"{self.id} | hair", srgb(params["hair"]), 0.6),
            "eye": material(f"{self.id} | eyes", srgb("#121616"), 0.15),
            "eye_hi": material(f"{self.id} | eye highlight", (1, 1, 1), 0.2, emission=(1, 1, 1), strength=2.0),
            "mouth": material(f"{self.id} | mouth", srgb("#5A2A26"), 0.5),
        }
        self._body()
        self._rig()
        self._weights_and_zones()
        self._head()
        self.rig.location = Vector(spec["position"])
        self.rig.rotation_euler.z = math.radians(spec["yawDegrees"])
        bpy.context.view_layer.update()
        self._controls()

    # -- construction ---------------------------------------------------------
    def _body(self):
        names = list(JOINTS)
        me = bpy.data.meshes.new(f"{self.id}.skeleton")
        me.from_pydata([JOINTS[n] for n in names], [(names.index(a), names.index(b)) for a, b in EDGES], [])
        source = link(bpy.data.objects.new(f"{self.id}.skin_source", me))
        skin = source.modifiers.new("skin", "SKIN")
        skin.use_smooth_shade = False
        sub = source.modifiers.new("subdiv", "SUBSURF")
        sub.levels = sub.render_levels = 1
        for i, n in enumerate(names):
            me.skin_vertices[0].data[i].radius = RADII[n]
        me.skin_vertices[0].data[names.index("pelvis")].use_root = True
        deps = bpy.context.evaluated_depsgraph_get()
        body_me = bpy.data.meshes.new_from_object(source.evaluated_get(deps))
        body_me.name = f"{self.id}.body"
        bpy.data.objects.remove(source)
        bpy.data.meshes.remove(me)
        self.body = link(bpy.data.objects.new(f"{self.id}.body", body_me))
        for zone in ZONES:
            body_me.materials.append(self.mats[zone])

    def _rig(self):
        data = bpy.data.armatures.new(f"{self.id}.rig")
        self.rig = link(bpy.data.objects.new(f"{self.id}.rig", data))
        bpy.context.view_layer.objects.active = self.rig
        bpy.ops.object.mode_set(mode="EDIT")
        points = {**JOINTS, "head_top": HEAD_TOP}
        for name, head, tail in BONES:
            eb = data.edit_bones.new(name)
            eb.head = Vector(points[head]) if head else Vector((0, 0, 0.5))
            eb.tail = Vector(points[tail])
        for name, parent in PARENT.items():
            eb = data.edit_bones[name]
            eb.parent = data.edit_bones[parent]
            eb.use_connect = name in CONNECTED
        self.segments = {n: (Vector(data.edit_bones[n].head), Vector(data.edit_bones[n].tail)) for n, *_ in BONES}
        bpy.ops.object.mode_set(mode="OBJECT")

    def _weights_and_zones(self):
        me = self.body.data
        groups = {n: self.body.vertex_groups.new(name=n) for n in self.segments if n != "root"}
        for v in me.vertices:
            d = sorted((_seg_dist(v.co, *self.segments[n]), n) for n in groups)
            (d0, n0), (d1, n1) = d[0], d[1]
            w0, w1 = 1 / (d0 + 1e-4) ** 4, 1 / (d1 + 1e-4) ** 4
            if w1 / (w0 + w1) < 0.15:
                groups[n0].add([v.index], 1.0, "REPLACE")
            else:
                groups[n0].add([v.index], w0 / (w0 + w1), "REPLACE")
                groups[n1].add([v.index], w1 / (w0 + w1), "REPLACE")
        index = {z: i for i, z in enumerate(ZONES)}
        for poly in me.polygons:
            c = poly.center
            nearest = min(groups, key=lambda n: _seg_dist(c, *self.segments[n]))
            if nearest.startswith("foot") or (nearest.startswith("shin") and c.z < 0.13):
                zone = "shoe_sole" if c.z < 0.03 else "shoe"
            elif nearest.startswith(("thigh", "shin")) or (nearest == "spine" and c.z < 0.86):
                zone = "pants"
            elif nearest.startswith("hand") or (nearest.startswith("forearm") and c.z < 0.85):
                zone = "skin"
            elif nearest == "neck" and c.z > 1.31:
                zone = "skin"
            elif nearest == "spine" and 0.86 <= c.z < 0.9:
                zone = "jacket_trim"
            else:
                zone = "jacket"
            poly.material_index = index[zone]
        flat(self.body)
        self.body.parent = self.rig
        self.body.modifiers.new("rig", "ARMATURE").object = self.rig

    def _bone_child(self, obj, bone):
        obj.parent = self.rig
        obj.parent_type = "BONE"
        obj.parent_bone = bone
        pb = self.rig.pose.bones[bone]
        obj.matrix_parent_inverse = (self.rig.matrix_world @ Matrix.Translation(pb.tail) @ pb.matrix.to_3x3().to_4x4()).inverted()

    def _head(self):
        bpy.context.view_layer.update()
        m, rng, c = self.mats, self.rng, Vector((0, -0.01, 1.485))
        parts = [
            faceted_blob(f"{self.id}.head", 0.115, c, m["skin"], rng, 2, 0.035, (0.92, 0.95, 1.08)),
            faceted_blob(f"{self.id}.jaw", 0.075, c + Vector((0, -0.035, -0.07)), m["skin"], rng, 1, 0.03, (1.05, 0.9, 0.75)),
            faceted_blob(f"{self.id}.nose", 0.022, c + Vector((0, -0.112, -0.01)), m["skin"], rng, 1, 0.05, (0.8, 1.0, 1.1)),
        ]
        self.eyes, self.brows = [], []
        for s, sx in (("L", 1), ("R", -1)):
            parts.append(faceted_blob(f"{self.id}.ear.{s}", 0.03, c + Vector((sx * 0.105, 0.0, -0.005)), m["skin"], rng, 1, 0.05, (0.45, 0.8, 1.1)))
            eye = faceted_blob(f"{self.id}.eye.{s}", 0.017, c + Vector((sx * 0.04, -0.093, 0.02)), m["eye"], rng, 1, 0.0, (1, 0.6, 1.25))
            hi = faceted_blob(f"{self.id}.eye_hi.{s}", 0.005, c + Vector((sx * 0.04 + 0.006, -0.103, 0.03)), m["eye_hi"], rng, 1, 0.0)
            brow = box(f"{self.id}.brow.{s}", (0.04, 0.012, 0.011), c + Vector((sx * 0.042, -0.086, 0.06)), m["hair"], 0.003)
            brow.rotation_euler.y = math.radians(sx * 7)
            self.eyes.append(eye)
            self.brows.append(brow)
            parts += [eye, hi, brow]
        hair = faceted_blob(f"{self.id}.hair", 0.124, c + Vector((0, 0.012, 0.035)), m["hair"], rng, 2, 0.12, (0.95, 1.0, 0.9))
        import bmesh

        bm = bmesh.new()
        bm.from_mesh(hair.data)
        cut = [v for v in bm.verts if (v.co.y < -0.06 and v.co.z < 0.03) or v.co.z < -0.035]
        bmesh.ops.delete(bm, geom=cut, context="VERTS")
        bm.to_mesh(hair.data)
        bm.free()
        parts += [hair, box(f"{self.id}.mouth", (0.04, 0.008, 0.008), c + Vector((0, -0.1, -0.055)), m["mouth"], 0.003)]
        for part in parts:
            self._bone_child(part, "head")
        self.brow_rest = [b.location.z for b in self.brows]

    def _controls(self):
        matrix = self.rig.matrix_world.copy()
        self.ik = {}
        self.rest = {}
        for s, sx, hand in (("L", 1, "left"), ("R", -1, "right")):
            target = link(bpy.data.objects.new(f"{self.id}.ik.{hand}", None))
            constraint = self.rig.pose.bones[f"forearm.{s}"].constraints.new("IK")
            constraint.target = target
            constraint.chain_count = 2
            constraint.use_tail = True
            self.ik[hand] = target
            self.rest[hand] = matrix @ Vector((sx * 0.215, 0.03, 0.80))
            key(target, "location", 0, self.rest[hand])
        self.gaze = link(bpy.data.objects.new(f"{self.id}.gaze", None))
        look = self.rig.pose.bones["head"].constraints.new("DAMPED_TRACK")
        look.target = self.gaze
        look.track_axis = "TRACK_Z"  # a vertical bone's local +Z is the face direction
        look.influence = 0.85
        key(self.gaze, "location", 0, matrix @ Vector((0, -2.0, 1.45)))
        # breathing and weight shift: slow, frame-derived, deterministic
        root = self.rig.pose.bones["root"]
        chest = self.rig.pose.bones["chest"]
        chest.rotation_mode = "XYZ"
        for f in range(0, 9000, 30):
            chest.rotation_euler = (math.radians(1.5 * math.sin(f / 20)), 0, 0)
            chest.keyframe_insert("rotation_euler", frame=f + 1)
            root.location = (0.008 * math.sin(f / 33), 0, 0)
            root.keyframe_insert("location", frame=f + 1)
        self.anchors = {
            "head": self.rig.pose.bones["head"],
            "hand-left": self.ik["left"],
            "hand-right": self.ik["right"],
        }
        self.brow_raise = 0.0
        spine = self.rig.pose.bones["spine"]
        spine.rotation_mode = "XYZ"
        key(spine, "rotation_euler", 0, (0, 0, 0))
        for eye in self.eyes:
            key(eye, "scale", 0, (1, 1, 1))
        for brow, z in zip(self.brows, self.brow_rest):
            brow.location.z = z
            brow.keyframe_insert("location", frame=1)

    # -- events -----------------------------------------------------------------
    def hand(self, side, frame, position):
        key(self.ik[side], "location", frame, position if position is not None else self.rest[side])

    def look(self, frame, position):
        key(self.gaze, "location", frame, position)

    def lean(self, frame, degrees):
        spine = self.rig.pose.bones["spine"]
        spine.rotation_mode = "XYZ"
        spine.rotation_euler = (math.radians(degrees), 0, 0)
        spine.keyframe_insert("rotation_euler", frame=frame + 1)

    def blink(self, frame):
        for eye in self.eyes:
            for f, s in ((frame - 2, 1), (frame, 0.12), (frame + 2, 1)):
                if f >= 0:
                    key(eye, "scale", f, (1, 1, s))

    def brows_to(self, frame, amount):
        for brow, z in zip(self.brows, self.brow_rest):
            brow.location.z = z + 0.012 * amount
            brow.keyframe_insert("location", frame=frame + 1)

    def anchor_position(self, name, frame):
        bpy.context.scene.frame_set(frame + 1)
        if name == "head":
            bone = self.rig.pose.bones["head"]
            return (self.rig.matrix_world @ bone.head).copy() + Vector((0, 0, 0.12))
        return self.anchors[name].matrix_world.translation.copy()
