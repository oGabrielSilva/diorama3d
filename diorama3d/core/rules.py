# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Gabriel Silva
"""Cross-field rules of a shot that JSON Schema cannot express.

Each rule reports a stable code (documented in spec/README.md) and the path of
the offending field. Run on a shot that already passed the schema.
"""

# Anchors each component exposes to events and camera focus.
COMPONENT_ANCHORS = {
    "electrical-panel@1": ("center", "door-handle", "main-lever", "inside", "lower-row"),
    "appliance@1": ("center", "indicator"),
    "asset@1": ("center", "top"),
    "circuit-breaker@1": ("center", "lever", "contacts", "bimetal", "coil", "arc-chute"),
}

# Object events and the components that implement them.
EVENT_TARGETS = {
    "power": (("appliance@1",), "dioramaTargetMustBeAppliance"),
    "open-door": (("electrical-panel@1",), "dioramaTargetMustBePanel"),
    "highlight": (("electrical-panel@1",), "dioramaTargetMustBePanel"),
    "flow": (("electrical-panel@1", "circuit-breaker@1"), "dioramaTargetMustBePanelOrBreaker"),
    "trip": (("electrical-panel@1", "circuit-breaker@1"), "dioramaTargetMustBePanelOrBreaker"),
    "switch-on": (("electrical-panel@1", "circuit-breaker@1"), "dioramaTargetMustBePanelOrBreaker"),
    "section": (("circuit-breaker@1", "appliance@1"), "dioramaTargetMustBeSectionable"),
    "explode": (("circuit-breaker@1",), "dioramaTargetMustBeBreaker"),
    "assemble": (("circuit-breaker@1",), "dioramaTargetMustBeBreaker"),
}

# Event fields only one component understands: required on the panel, rejected
# on the breaker (and the breaker-only fields rejected on the panel).
PANEL_REQUIRED = {"flow": "circuit", "trip": "circuit", "switch-on": "controls"}
BREAKER_ONLY = {"flow": "load", "trip": "cause"}


def check(spec):
    """Returns a list of (path, code) issues; empty means the shot is coherent."""
    issues = []

    def issue(path, code):
        issues.append((tuple(path), code))

    entities = {}
    for index, entity in enumerate(spec["entities"]):
        if entity["id"] in entities:
            issue(("entities", index, "id"), "dioramaDuplicateEntity")
        entities[entity["id"]] = entity

    # Within a shot, one library asset id always points at one content hash.
    hashes = {}

    def check_ref(ref, path):
        if hashes.get(ref["assetId"], ref["sha256"]) != ref["sha256"]:
            issue(path, "dioramaAssetHashConflict")
        hashes[ref["assetId"]] = ref["sha256"]

    for index, entity in enumerate(spec["entities"]):
        if entity["component"] == "asset@1":
            check_ref(entity["params"], ("entities", index, "params"))
    if spec["look"].get("environment"):
        check_ref(spec["look"]["environment"], ("look", "environment"))
    for surface, ref in spec["set"]["params"].get("surfaces", {}).items():
        check_ref(ref, ("set", "params", "surfaces", surface))

    def check_anchor(reference, path):
        entity = entities.get(reference["entity"])
        if entity is None:
            return issue(path, "dioramaUnknownEntity")
        if reference["anchor"] not in COMPONENT_ANCHORS[entity["component"]]:
            issue(path, "dioramaUnknownAnchor")

    last = spec["durationFrames"] - 1
    for index, event in enumerate(spec["events"]):
        path = ("events", index)
        if event["frame"] > last:
            issue(path + ("frame",), "dioramaFrameOutOfRange")
        if "endFrame" in event and (event["endFrame"] <= event["frame"] or event["endFrame"] > last):
            issue(path + ("endFrame",), "dioramaFrameOutOfRange")
        rule = EVENT_TARGETS.get(event["action"])
        if rule:
            components, code = rule
            target = entities.get(event["target"]) if isinstance(event["target"], str) else None
            component = target["component"] if target else None
            if component not in components:
                issue(path + ("target",), code)
            panel_field = PANEL_REQUIRED.get(event["action"])
            breaker_field = BREAKER_ONLY.get(event["action"])
            if component == "electrical-panel@1":
                if panel_field and panel_field not in event:
                    issue(path + (panel_field,), "dioramaEventParamRequired")
                if breaker_field and breaker_field in event:
                    issue(path + (breaker_field,), "dioramaEventParamNotSupported")
                circuit = event.get("circuit")
                if isinstance(circuit, int) and not isinstance(circuit, bool):
                    if circuit > target["params"]["circuits"]:
                        issue(path + ("circuit",), "dioramaUnknownCircuit")
            elif component == "circuit-breaker@1" and panel_field and panel_field in event:
                issue(path + (panel_field,), "dioramaEventParamNotSupported")
            if event["action"] == "highlight" and (event.get("controls") == "circuit") != bool(
                event.get("circuit")
            ):
                issue(path + ("circuit",), "dioramaHighlightCircuit")
        if isinstance(event.get("target"), dict):
            check_anchor(event["target"], path + ("target",))

    previous = -1
    for index, key in enumerate(spec["camera"]["keys"]):
        path = ("camera", "keys", index)
        if key["frame"] <= previous:
            issue(path + ("frame",), "dioramaCameraKeysOrder")
        if key["frame"] > last:
            issue(path + ("frame",), "dioramaFrameOutOfRange")
        previous = key["frame"]
        if isinstance(key.get("focus"), dict):
            check_anchor(key["focus"], path + ("focus",))
    return issues
