# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/). The shot format has its own version
(`diorama.shot/1`), described in [spec/README.md](spec/README.md).

## [Unreleased]

## [0.1.1] — not yet released

### Added

- `switch-on` on an `electrical-panel@1` accepts `circuit` (with `controls: "circuits"`)
  to re-arm a single circuit; the other levers stay still.

### Fixed

- Re-arming a tripped circuit returns its status label to the brand color
  (it stayed in the warning color). Pixels change: version bumped.

## [0.1.0] — not yet released

First public version, extracted from QVid Studio with its history.

### Added

- Shot format `diorama.shot/1` as JSON Schema 2020-12 (`spec/shot.schema.json`),
  with conformance cases recorded from the reference implementation.
- Pure-Python core (`diorama3d.core`, no Blender needed): validation, defaults
  and cross-field rules with stable error codes.
- Script entry point `run.py` (works with `--factory-startup`) and a Blender
  extension that registers `blender -c diorama`.
- Components `kitchen-corner@1`, `electrical-panel@1`, `circuit-breaker@1`,
  `appliance@1` and `asset@1`; events `power`, `open-door`, `highlight`,
  `flow`, `trip`, `switch-on`, `section`, `explode` and `assemble`.
- Examples `circuit-breaker-inside` and `electrical-panel-opening`.

### Changed

- The format name `qvid.diorama.shot/0` became `diorama.shot/1`; the old name
  is still accepted as an alias.
- Known failures return exit code 3 instead of ending Blender from inside the
  script, so the same code runs as a Blender command.

### Removed

- `faceted-character@1` and its events (`hand`, `lean`, `blink`, `brows`,
  `look`), which were frozen in QVid and are outside the project's scope.
