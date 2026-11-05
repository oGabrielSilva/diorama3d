# Contributing to Diorama

Thanks for helping. Bug reports, examples, documentation, new components and
reviews are all welcome. By participating you agree to the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Setup

- [Blender 5.2 LTS](https://www.blender.org/download/lts/) for rendering.
- Python 3.11 or newer (latest security release of its series) for the core
  tests. No packages are needed.

```sh
python -m unittest discover -s tests          # core: schema, rules, conformance
blender -b --factory-startup --python-exit-code 1 --python run.py -- \
  --spec examples/electrical-panel-opening.json --out frames --start 60 --end 60 --scale 25 --samples 8
```

Run the core tests also with Blender's Python before sending a change to
`diorama3d/core/`:

```sh
blender -b --factory-startup --python-exit-code 1 --python-expr \
  "import sys,unittest; sys.path[:0]=['.','tests']; r=unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('tests')); sys.exit(not r.wasSuccessful())"
```

## Rules that keep Diorama trustworthy

1. **Shots are data.** Never `eval`, `exec`, import or open a path taken from a
   shot. New fields go into `spec/shot.schema.json` first.
2. **Determinism.** Animation depends only on the frame. No wall clock, no
   unseeded randomness (seed from the shot or entity `id`), no state that
   differs between runs or between frame ranges rendered separately.
3. **Version on pixels.** Any change that alters rendered pixels bumps
   `__version__` in `diorama3d/__init__.py` and `version` in
   `diorama3d/blender_manifest.toml` (a test keeps them equal).
4. **The schema has one source.** Edit `spec/shot.schema.json`, then copy it to
   `diorama3d/core/shot.schema.json` (a test checks they match). Add
   conformance cases in `spec/conformance/` for every new rule.
5. **Licenses.** Every Python file starts with an SPDX line: code under
   `diorama3d/` is `GPL-3.0-or-later`; `spec/`, `examples/` and `docs/` are
   `Apache-2.0`.

## Adding a component

A component is a versioned module in `diorama3d/components/` that builds
objects for one entity and implements its events.

1. Pick an id `name@1`. A later incompatible change becomes `name@2`.
2. Describe its `params` and events in `spec/shot.schema.json`, its anchors and
   event targets in `diorama3d/core/rules.py`.
3. Implement building, anchors and events; derive every animation from frames.
4. Add an example in `examples/`, conformance cases, and a still in the PR.

Open an issue first for a new component, so we can agree on the vocabulary.

## Pull requests

- One topic per PR, with a short description and, for visual changes, before
  and after images.
- Sign off each commit (Developer Certificate of Origin):
  `git commit -s` adds `Signed-off-by: Your Name <you@example.com>`, stating that
  you wrote the change or have the right to submit it under the project's
  licenses (<https://developercertificate.org/>).
- CI must pass: core tests on every supported Python version and lint.
