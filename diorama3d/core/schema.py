# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Gabriel Silva
"""Minimal JSON Schema (2020-12) validator that also applies defaults.

Pure Python, no dependencies: it runs inside Blender's bundled interpreter.
It supports exactly the keywords used by spec/shot.schema.json: type, const,
enum, minimum, maximum, pattern, properties, required, additionalProperties,
items, prefixItems, minItems, maxItems, anyOf, oneOf and default. A missing
property with a default receives a deep copy of it, and defaults nested inside
that value are applied too.
"""

import copy
import re

_PATTERNS = {}


def _pattern(source):
    compiled = _PATTERNS.get(source)
    if compiled is None:
        # In Python "$" also matches before a trailing newline; JSON Schema does not.
        python = source[:-1] + r"\Z" if source.endswith("$") and not source.endswith(r"\$") else source
        compiled = _PATTERNS[source] = re.compile(python)
    return compiled


def _is_type(value, name):
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    if isinstance(value, bool):
        return False
    if name == "integer":
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    if name == "number":
        return isinstance(value, (int, float))
    raise ValueError(f"unsupported type {name!r}")


def _same(value, expected):
    return isinstance(value, bool) == isinstance(expected, bool) and value == expected


def _discriminates(schema, value):
    """True when a branch's const properties match the value (best error source)."""
    if not isinstance(value, dict):
        return False
    consts = {
        name: sub["const"]
        for name, sub in schema.get("properties", {}).items()
        if isinstance(sub, dict) and "const" in sub
    }
    return bool(consts) and all(_same(value.get(name), const) for name, const in consts.items())


def coerce(schema, value, path=(), issues=None):
    """Returns `value` with defaults applied; appends (path, message) issues."""
    if issues is None:
        issues = []
    if schema is True or schema == {}:
        return value
    if schema is False:
        issues.append((path, "notAllowed"))
        return value

    for keyword in ("oneOf", "anyOf"):
        if keyword in schema:
            passing, best = [], None
            for branch in schema[keyword]:
                local = []
                candidate = coerce(branch, copy.deepcopy(value), path, local)
                if not local:
                    passing.append(candidate)
                    if keyword == "anyOf":
                        break
                elif best is None and _discriminates(branch, value):
                    best = local
            if len(passing) == 1 or (keyword == "anyOf" and passing):
                return passing[0]
            if passing:
                issues.append((path, "ambiguousVariant"))
            else:
                issues.extend(best or [(path, "noMatchingVariant")])
            return value

    if "const" in schema and not _same(value, schema["const"]):
        issues.append((path, f"mustEqual {schema['const']!r}"))
        return value
    if "enum" in schema and not any(_same(value, item) for item in schema["enum"]):
        issues.append((path, f"mustBeOneOf {schema['enum']!r}"))
        return value
    expected = schema.get("type")
    if expected is not None:
        names = expected if isinstance(expected, list) else [expected]
        if not any(_is_type(value, name) for name in names):
            issues.append((path, f"mustBe {'|'.join(names)}"))
            return value

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for name, sub in properties.items():
            if name not in value and isinstance(sub, dict) and "default" in sub:
                value[name] = copy.deepcopy(sub["default"])
        for name in schema.get("required", []):
            if name not in value:
                issues.append((path + (name,), "required"))
        extra = schema.get("additionalProperties", True)
        for name in list(value):
            if name in properties:
                value[name] = coerce(properties[name], value[name], path + (name,), issues)
            elif extra is False:
                issues.append((path + (name,), "unknownProperty"))
            elif isinstance(extra, dict):
                value[name] = coerce(extra, value[name], path + (name,), issues)
    elif isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            issues.append((path, f"minItems {schema['minItems']}"))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            issues.append((path, f"maxItems {schema['maxItems']}"))
            return value
        prefix = schema.get("prefixItems", [])
        rest = schema.get("items", True)
        for index, item in enumerate(value):
            sub = prefix[index] if index < len(prefix) else rest
            value[index] = coerce(sub, item, path + (index,), issues)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            issues.append((path, f"minimum {schema['minimum']}"))
        if "maximum" in schema and value > schema["maximum"]:
            issues.append((path, f"maximum {schema['maximum']}"))
    elif isinstance(value, str):
        if "pattern" in schema and not _pattern(schema["pattern"]).search(value):
            issues.append((path, f"pattern {schema['pattern']}"))
    return value
