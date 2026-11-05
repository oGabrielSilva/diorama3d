# Security policy

## Reporting a vulnerability

Report privately through GitHub: **Security › Report a vulnerability** on this
repository. Please do not open a public issue. The maintainer aims to answer within
7 days and to share a fix or mitigation plan within 30 days for confirmed issues.

## Threat model

A shot file is **untrusted input**: it may come from a user, another program or
a language model. Diorama's guarantees:

- Nothing in a shot is executed. Shots are data validated against
  `spec/shot.schema.json` and the cross-field rules before Blender builds
  anything; unknown fields are rejected.
- Component code ships with the package. Third-party code is never loaded
  because a shot asks for it.
- Library files are referenced by SHA-256 and resolved by the caller; a `.blend`
  that pulls external libraries or unpacked images is refused.
- Rendering needs no network: run Blender with `--offline-mode`.

These count as vulnerabilities: a shot that executes code, reads or writes
files outside the paths given on the command line, or makes Blender reach the
network.

## Python versions

- **Inside Blender** Diorama runs on the Python that Blender bundles (Blender
  5.2.2 ships CPython 3.13.13). Diorama cannot patch it. Diorama itself uses no
  TLS, archive extraction or XML parsing, which is where recent CPython fixes
  concentrate. Keep Blender on the latest 5.2.x release, and start it from a
  working directory you control (not a shared or downloads folder), as Python's
  module search path includes it on Windows.
- **Outside Blender** (the pure-Python core, tests and future host tools):
  Python 3.11 or newer, always on the latest security release of its series.
  As of November 2026 those are 3.15.2, 3.14.10, 3.13.18, 3.12.16 and 3.11.18,
  which fix CVE-2026-115557 (compromised CA trust in `ssl`) and earlier `ssl`,
  `zipfile` and `tarfile` issues. Python 3.10 reached end of life in
  October 2026 and is not supported.

## Supported versions

Only the latest release receives security fixes before 1.0.
