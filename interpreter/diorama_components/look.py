# SPDX-License-Identifier: GPL-3.0-or-later
# Diorama look interior-window: AgX color management, EEVEE quality settings,
# cool window key light, warm kitchen fill, rim light and a brand-colored bounce.

import bpy
from mathutils import Vector

from .common import link, srgb


def configure_render(scene, profile, size):
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = profile["scale"]
    scene.render.use_motion_blur = bool(profile["motionBlur"])
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    eevee = scene.eevee
    for attr, value in (
        ("taa_render_samples", profile["samples"]),
        ("use_raytracing", True),
        ("use_shadows", True),
        ("shadow_ray_count", 2),
        ("shadow_step_count", 8),
        ("fast_gi_method", "GLOBAL_ILLUMINATION"),
    ):
        try:
            setattr(eevee, attr, value)
        except (AttributeError, TypeError):
            pass


def _area(name, loc, target, power, size, color, size_y=None):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.shape = "RECTANGLE"
    data.size = size
    data.size_y = size_y or size
    data.color = color
    obj = link(bpy.data.objects.new(name, data))
    obj.location = loc
    obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return obj


def interior_window(scene, look, focus_point):
    scene.view_settings.exposure = look["exposure"]
    world = bpy.data.worlds.new("World")
    scene.world = world
    background = world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (0.035, 0.075, 0.08, 1)
    background.inputs[1].default_value = 0.6
    accent = srgb(look["brand"]["accent"])
    f = Vector(focus_point)
    _area("light.window_key", f + Vector((-1.6, -1.2, 0.7)), f + Vector((-0.1, 0, -0.2)), 380, 1.2, (0.82, 0.92, 1.0), 1.6)
    _area("light.kitchen_warm", f + Vector((1.6, -1.4, 0.4)), f + Vector((0.2, -0.2, -0.3)), 160, 1.0, (1.0, 0.78, 0.58))
    _area("light.rim", f + Vector((-0.2, 0.6, 1.2)), f + Vector((-0.46, -0.36, -0.2)), 120, 0.6, (0.75, 1.0, 0.92))
    _area("light.bounce", f + Vector((0.0, -0.7, -0.1)), f, 18, 0.4, accent)
