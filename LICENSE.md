# Licenses

Diorama uses two licenses. Each file states its license with an SPDX
identifier; files without one follow [REUSE.toml](REUSE.toml). Full texts are in
[LICENSES/](LICENSES).

| Path                                      | License                                                  |
| ----------------------------------------- | -------------------------------------------------------- |
| `diorama3d/`, `run.py`, `tests/*.py`      | [GPL-3.0-or-later](LICENSES/GPL-3.0-or-later.txt)        |
| `spec/`, `examples/`, `docs/`, `*.md`     | [Apache-2.0](LICENSES/Apache-2.0.txt)                    |

Why two: code that runs inside Blender and uses its Python API (`bpy`) is
distributed under the GPL, like Blender. The shot format is a separate,
documented contract under Apache-2.0, so applications of any license can read,
write and validate shots, and run Diorama as a separate program.

`diorama3d/core/shot.schema.json` is a copy of `spec/shot.schema.json` and keeps
its Apache-2.0 license inside the GPL package.

Copyright (C) 2026 Gabriel Silva and contributors.
