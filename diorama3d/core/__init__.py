# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Gabriel Silva
"""Pure-Python core (no bpy): shot validation and normalization.

    from diorama3d.core import load_shot
    shot = load_shot(json.load(open("shot.json")))  # raises SpecError

Usable from any Python 3.11+, inside or outside Blender.
"""

import copy
import json
import os

from . import rules
from .schema import coerce

SUPPORTED_SCHEMAS = ("diorama.shot/1", "qvid.diorama.shot/0")
_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shot.schema.json")
_SCHEMA = None


class SpecError(ValueError):
    """An invalid shot. `issues` is a list of (path, code-or-message) pairs."""

    def __init__(self, code, issues):
        self.code = code
        self.issues = issues
        path, message = issues[0]
        super().__init__(f"{code}: {'/'.join(map(str, path)) or '(root)'}: {message}")


def shot_schema():
    """The bundled copy of spec/shot.schema.json."""
    global _SCHEMA
    if _SCHEMA is None:
        with open(_SCHEMA_PATH, encoding="utf-8") as handle:
            _SCHEMA = json.load(handle)
    return _SCHEMA


def load_shot(spec):
    """Validates a shot and returns a normalized copy with every default applied.

    Raises SpecError with code dioramaUnsupportedSpec, dioramaInvalidSpec (schema)
    or the code of the first broken cross-field rule (see rules.py).
    """
    if not isinstance(spec, dict) or spec.get("schema") not in SUPPORTED_SCHEMAS:
        found = spec.get("schema") if isinstance(spec, dict) else type(spec).__name__
        raise SpecError("dioramaUnsupportedSpec", [((), repr(found))])
    # The original format name is accepted and normalized to the public one.
    candidate = dict(copy.deepcopy(spec), schema="diorama.shot/1")
    issues = []
    shot = coerce(shot_schema(), candidate, (), issues)
    if issues:
        raise SpecError("dioramaInvalidSpec", issues)
    broken = rules.check(shot)
    if broken:
        raise SpecError(broken[0][1], broken)
    return shot
