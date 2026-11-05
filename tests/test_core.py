# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Gabriel Silva
"""Core tests: plain Python, no Blender. Run: python -m unittest discover tests"""

import json
import pathlib
import tomllib
import unittest

import diorama3d
from diorama3d.core import SpecError, load_shot, shot_schema

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFORMANCE = ROOT / "spec" / "conformance"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ConformanceTest(unittest.TestCase):
    def test_valid_shots_normalize_like_the_reference(self):
        cases = sorted(p for p in (CONFORMANCE / "valid").glob("*.json") if ".normalized" not in p.name)
        self.assertGreaterEqual(len(cases), 3)
        for case in cases:
            with self.subTest(case=case.stem):
                expected = read(case.with_name(f"{case.stem}.normalized.json"))
                self.assertEqual(load_shot(read(case)), expected)

    def test_invalid_shots_fail_with_the_reference_code(self):
        expected = read(CONFORMANCE / "invalid" / "expected.json")
        self.assertGreaterEqual(len(expected), 10)
        for name, code in expected.items():
            with self.subTest(case=name):
                with self.assertRaises(SpecError) as raised:
                    load_shot(read(CONFORMANCE / "invalid" / f"{name}.json"))
                self.assertEqual(raised.exception.code, code)

    def test_examples_are_valid(self):
        for example in sorted((ROOT / "examples").glob("*.json")):
            with self.subTest(example=example.name):
                load_shot(read(example))


class CoreTest(unittest.TestCase):
    def setUp(self):
        self.minimal = read(CONFORMANCE / "valid" / "minimal.json")

    def test_input_is_never_mutated(self):
        before = json.dumps(self.minimal, sort_keys=True)
        load_shot(self.minimal)
        self.assertEqual(json.dumps(self.minimal, sort_keys=True), before)

    def test_original_format_name_is_an_alias(self):
        legacy = dict(self.minimal, schema="qvid.diorama.shot/0")
        self.assertEqual(load_shot(legacy)["schema"], "diorama.shot/1")

    def test_patterns_do_not_accept_a_trailing_newline(self):
        with self.assertRaises(SpecError) as raised:
            load_shot(dict(self.minimal, id="minimal\n"))
        self.assertEqual(raised.exception.code, "dioramaInvalidSpec")
        self.assertEqual(raised.exception.issues[0][0], ("id",))

    def test_booleans_are_not_numbers(self):
        with self.assertRaises(SpecError):
            load_shot(dict(self.minimal, durationFrames=True))

    def test_non_object_input_is_unsupported(self):
        for value in (None, [], "shot", 3):
            with self.subTest(value=value):
                with self.assertRaises(SpecError) as raised:
                    load_shot(value)
                self.assertEqual(raised.exception.code, "dioramaUnsupportedSpec")


class PackagingTest(unittest.TestCase):
    def test_bundled_schema_matches_the_spec(self):
        self.assertEqual(shot_schema(), read(ROOT / "spec" / "shot.schema.json"))

    def test_extension_ships_the_gpl_text(self):
        self.assertEqual(
            (ROOT / "diorama3d" / "LICENSE.txt").read_bytes(), (ROOT / "LICENSES" / "GPL-3.0-or-later.txt").read_bytes()
        )

    def test_manifest_version_matches_the_package(self):
        manifest = tomllib.loads((ROOT / "diorama3d" / "blender_manifest.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], diorama3d.__version__)
        self.assertEqual(manifest["license"], ["SPDX:GPL-3.0-or-later"])

    def test_every_python_file_declares_its_license(self):
        for path in sorted(ROOT.glob("**/*.py")):
            if ".git" in path.parts:
                continue
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertIn("SPDX-License-Identifier:", path.read_text(encoding="utf-8").splitlines()[0])


if __name__ == "__main__":
    unittest.main()
