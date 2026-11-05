# SPDX-License-Identifier: GPL-3.0-or-later
# Diorama library assets: asset@1 (models appended from .blend or imported from
# .glb), PBR texture-set materials and HDRI worlds. Paths come from the
# resolved-assets file written by QVid after re-hashing every library file; the
# shot specification itself only carries asset ids and SHA-256 hashes.
# Loading a .blend never runs its scripts: Blender starts with
# --factory-startup, so auto-run of Python (scripts, drivers) stays disabled.

import math
import os

import bpy
from mathutils import Vector

from .common import empty

SKIPPED_TYPES = {"CAMERA", "LIGHT", "LIGHT_PROBE", "SPEAKER"}
BOUNDED_TYPES = {"MESH", "CURVE", "SURFACE", "META", "FONT", "CURVES", "POINTCLOUD", "VOLUME"}
DATA_SPACES = ("Non-Color", "Generic Data", "Raw")


def _colorspace(image, names):
    for name in names:
        try:
            image.colorspace_settings.name = name
            return
        except TypeError:
            continue


def load_image(path, data=False):
    image = bpy.data.images.load(path, check_existing=True)
    if data:
        _colorspace(image, DATA_SPACES)
    elif not path.lower().endswith((".exr", ".hdr")):
        _colorspace(image, ("sRGB",))
    return image


def pbr_material(name, files, scale_meters=1.0):
    """Texture set on object-space box projection: needs no UVs and keeps a
    real-world tile size (`scale_meters`) on any surface of the set."""
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = next(node for node in nt.nodes if node.type == "BSDF_PRINCIPLED")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.0 / scale_meters,) * 3
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])

    def texture(role, data):
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = load_image(files[role], data)
        node.projection = "BOX"
        node.projection_blend = 0.2
        nt.links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        return node.outputs["Color"]

    nt.links.new(texture("baseColor", False), bsdf.inputs["Base Color"])
    if "arm" in files:
        split = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(texture("arm", True), split.inputs["Color"])
        nt.links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    if "roughness" in files:
        nt.links.new(texture("roughness", True), bsdf.inputs["Roughness"])
    if "metallic" in files:
        nt.links.new(texture("metallic", True), bsdf.inputs["Metallic"])
    if "normal" in files:
        normal = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(texture("normal", True), normal.inputs["Color"])
        nt.links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def world_environment(world, path, strength=1.0, rotation_degrees=0.0):
    """Replaces the world color with an equirectangular HDRI."""
    nt = world.node_tree
    background = next(node for node in nt.nodes if node.type == "BACKGROUND")
    environment = nt.nodes.new("ShaderNodeTexEnvironment")
    environment.image = load_image(path)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(rotation_degrees))
    nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], environment.inputs["Vector"])
    nt.links.new(environment.outputs["Color"], background.inputs["Color"])
    background.inputs["Strength"].default_value = strength


def load_model(path):
    """Appends every object of a .blend (or imports a .glb) into the scene.
    Cameras and lights of the asset are dropped: the shot owns those."""
    scene = bpy.context.scene
    if path.lower().endswith(".blend"):
        images_before = set(bpy.data.images)
        with bpy.data.libraries.load(path, link=False) as (source, target):
            target.objects = list(source.objects)
        objects = [obj for obj in target.objects if obj is not None]
        # Only the hashed .blend may feed pixels: unpacked images or nested
        # libraries would load files outside the library and break the cache.
        own = os.path.normcase(os.path.abspath(path))
        for library in bpy.data.libraries:
            if os.path.normcase(os.path.abspath(bpy.path.abspath(library.filepath))) != own:
                raise RuntimeError("dioramaAssetExternalFiles")
        for image in set(bpy.data.images) - images_before:
            if image.source in {"FILE", "SEQUENCE", "MOVIE", "TILED"} and image.packed_file is None:
                raise RuntimeError("dioramaAssetExternalFiles")
        for obj in objects:
            if not obj.users_collection:
                scene.collection.objects.link(obj)
    else:
        before = set(bpy.data.objects)
        if "FINISHED" not in bpy.ops.import_scene.gltf(filepath=path):
            raise RuntimeError("dioramaAssetImportFailed")
        objects = [obj for obj in bpy.data.objects if obj not in before]
    kept = []
    for obj in objects:
        if obj.type in SKIPPED_TYPES:
            bpy.data.objects.remove(obj, do_unlink=True)
        else:
            kept.append(obj)
    if not kept:
        raise RuntimeError("dioramaAssetEmpty")
    return kept


def world_bounds(objects):
    """Axis-aligned world bounds of the evaluated, renderable objects."""
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    low = Vector((math.inf,) * 3)
    high = Vector((-math.inf,) * 3)
    for obj in objects:
        if obj.type not in BOUNDED_TYPES or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        matrix = evaluated.matrix_world
        if obj.type == "MESH":
            points = [matrix @ Vector(corner) for corner in evaluated.bound_box]
        else:
            # Curve bound boxes are unreliable in background mode; use the evaluated mesh.
            try:
                mesh = evaluated.to_mesh()
            except RuntimeError:
                continue
            points = [matrix @ vertex.co for vertex in mesh.vertices] if mesh else []
            evaluated.to_mesh_clear()
        for point in points:
            low = Vector(map(min, low, point))
            high = Vector(map(max, high, point))
    if low.x == math.inf:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    return low, high


class AssetInstance:
    """asset@1: a library model under one root (position, yaw, uniform scale).
    Anchors: `center` of the bounds and `top` (center of the upper face)."""

    def __init__(self, spec, resolved):
        self.id = spec["id"]
        objects = load_model(resolved["files"]["model"])
        low, high = world_bounds(objects)
        self.root = empty(self.id, location=tuple(spec["position"]))
        for obj in objects:
            if obj.parent is None:
                obj.parent = self.root
        self.root.rotation_euler.z = math.radians(spec.get("yawDegrees", 0))
        self.root.scale = (spec.get("scale", 1),) * 3
        center = (low + high) / 2
        self.anchors = {
            "center": empty(f"{self.id}.anchor.center", self.root, tuple(center)),
            "top": empty(f"{self.id}.anchor.top", self.root, (center.x, center.y, high.z)),
        }

    def anchor(self, name):
        return self.anchors[name]
