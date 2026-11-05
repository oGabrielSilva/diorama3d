# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Gabriel Silva
"""Diorama: declarative, deterministic explainer shots for Blender.

Two ways to run it, both inside Blender:

- script mode (apps and CI, works with --factory-startup):
  ``blender -b --factory-startup --python run.py -- --spec shot.json --out frames``
- Blender extension: ``blender -b -c diorama --spec shot.json --out frames``
"""

# Keep equal to `version` in blender_manifest.toml. Any change that alters
# rendered pixels must bump it: callers key their render caches on it.
__version__ = "0.1.0"

_commands = []


def _command(argv):
    from .cli import main

    if argv and argv[0] == "--":
        argv = argv[1:]
    return main(argv)


def register():
    import bpy

    _commands.append(bpy.utils.register_cli_command("diorama", _command))


def unregister():
    import bpy

    for handle in _commands:
        bpy.utils.unregister_cli_command(handle)
    _commands.clear()
