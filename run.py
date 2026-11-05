# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Gabriel Silva
"""Script entry point, for apps and CI:

    blender -b --factory-startup --offline-mode -noaudio --python-exit-code 1 \
      --python run.py -- --spec examples/circuit-breaker-inside.json --out frames

--factory-startup disables installed extensions, so this file puts the
package on sys.path itself. Exit code: 0 ok, 3 known failure (DIORAMA_ERROR).
"""

import os
import sys

# Never write __pycache__ next to the source (it may be read-only).
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from diorama3d.cli import main  # noqa: E402

sys.exit(main(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []))
