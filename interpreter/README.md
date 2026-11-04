# Diorama interpreter (GPL-3.0-or-later)

Python code executed **inside Blender 5.2 LTS** by QVid Studio, as a separate
process. It turns a declarative shot specification (`qvid.diorama.shot/0`,
validated by QVid) into a Blender scene and renders frame ranges to PNG.

- License: GNU General Public License v3.0 or later — see [LICENSE](LICENSE).
  This folder is the complete corresponding source of the interpreter.
- Entry point: `diorama.py`. Components: `diorama_components/`.
- The interpreter never executes code taken from a specification.
- Changing pixels requires bumping `INTERPRETER_VERSION` here and
  `DIORAMA_INTERPRETER_VERSION` in `src/constants/diorama.js`.

Usage and contract: [docs/diorama.md](../../../docs/diorama.md).
