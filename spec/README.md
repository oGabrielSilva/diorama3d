# Diorama shot format — `diorama.shot/1`

<!-- SPDX-License-Identifier: Apache-2.0 -->

This folder is the language-neutral contract of Diorama, licensed Apache-2.0 so
that any application can produce and validate shots.

- [`shot.schema.json`](shot.schema.json): JSON Schema 2020-12 of a shot.
- [`conformance/`](conformance): inputs every implementation must accept or
  reject, with the expected normalized output or error code.
- This page: rules JSON Schema cannot express, error codes and the process
  protocol.

The previous name of the format, `qvid.diorama.shot/0`, is accepted as an alias
of `diorama.shot/1` and normalized to it.

## Versioning

The format version changes only with breaking changes. New optional fields,
components (`name@1`) and events can be added within `diorama.shot/1`; a
component that changes incompatibly becomes `name@2`. Before Diorama 1.0, fields
may still change, and every change is listed in the changelog.

## Normalization

A shot is normalized before rendering: every missing field that has a `default`
in the schema receives it, including defaults nested inside that default. The
normalized shot is what participates in render signatures. Inputs and normalized
outputs for reference shots are in `conformance/valid/`.

## Cross-field rules

Checked after the schema. The first broken rule found is reported with
its code and the path of the field.

| Code                                 | Rule                                                                                                 |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `dioramaDuplicateEntity`             | Entity ids are unique.                                                                               |
| `dioramaAssetHashConflict`           | Within a shot, one `assetId` always refers to the same `sha256`.                                     |
| `dioramaFrameOutOfRange`             | `frame` ≤ `durationFrames − 1`; `endFrame` > `frame` and ≤ `durationFrames − 1`; same for camera keys. |
| `dioramaTargetMustBeAppliance`       | `power` targets an `appliance@1`.                                                                    |
| `dioramaTargetMustBePanel`           | `open-door` and `highlight` target an `electrical-panel@1`.                                          |
| `dioramaTargetMustBePanelOrBreaker`  | `flow`, `trip` and `switch-on` target a panel or a `circuit-breaker@1`.                              |
| `dioramaTargetMustBeSectionable`     | `section` targets a breaker or an appliance.                                                         |
| `dioramaTargetMustBeBreaker`         | `explode` and `assemble` target a breaker.                                                           |
| `dioramaEventParamRequired`          | On a panel, `flow` and `trip` need `circuit`, and `switch-on` needs `controls`.                      |
| `dioramaEventParamNotSupported`      | `load` (flow) and `cause` (trip) only apply to a breaker; `circuit`/`controls` only to a panel.      |
| `dioramaUnknownCircuit`              | `circuit` ≤ the panel's `circuits`.                                                                  |
| `dioramaHighlightCircuit`            | `highlight` has `circuit` exactly when `controls` is `circuit`.                                      |
| `dioramaUnknownEntity`               | An anchor reference names an existing entity.                                                        |
| `dioramaUnknownAnchor`               | The anchor exists on that component (see the table in the main README).                              |
| `dioramaCameraKeysOrder`             | Camera key frames are strictly increasing.                                                           |

A shot that fails the schema itself is reported as `dioramaInvalidSpec`; one
whose `schema` field is not a supported format name, as `dioramaUnsupportedSpec`.

## Assets

Shots reference library files by id and SHA-256 only (`asset@1`,
`look.environment`, `set.params.surfaces`). The caller resolves them, checks the
hashes, and passes a JSON file with `--assets`:

```json
{
  "studio": {
    "kind": "hdri",
    "sha256": "…64 hex…",
    "files": { "hdri": "C:/library/objects/….hdr" }
  }
}
```

`kind` is `model` (files: `model`, a `.blend` or `.glb`), `hdri` (files: `hdri`)
or `material` (files: `baseColor` and optionally `arm`, `roughness`, `metallic`,
`normal`). A `.blend` that links other libraries or unpacked images is refused
with `dioramaAssetExternalFiles`: every pixel must come from a hashed file.

## Process protocol

Diorama runs inside Blender as a separate process (see the main README for the
command). Arguments after `--`:

| Argument                         | Meaning                                              |
| -------------------------------- | ---------------------------------------------------- |
| `--spec FILE`                    | Shot to render.                                      |
| `--out DIR`                      | Output folder; frames are `f_00001.png`, ...         |
| `--start N`, `--end N`           | Frame range, 0-based and inclusive (`--end -1`: last). |
| `--scale P`                      | Resolution percentage (100 = 1080 × 1920 vertical).  |
| `--samples N`                    | Render samples.                                      |
| `--motion-blur 0/1`              | Motion blur.                                         |
| `--assets FILE`                  | Resolved assets (above).                             |
| `--probe`                        | Smallest render that proves a usable GPU context.    |
| `--version`                      | Print the package version.                           |

Lines on stdout, one per event (Blender prints its own lines too; read only
these prefixes):

| Line                                       | Meaning                                    |
| ------------------------------------------ | ------------------------------------------ |
| `DIORAMA_BUILD seconds=S interpreter=V`    | Scene built; `V` is the package version.   |
| `DIORAMA_FRAME N`                          | Frame `N` (0-based) written.               |
| `DIORAMA_DONE`                             | Range finished.                            |
| `DIORAMA_PROBE_OK engine=E seconds=S`      | Probe succeeded.                           |
| `DIORAMA_ERROR CODE [DETAIL]`              | Known failure; exit code 3.                |

Exit codes: `0` success, `3` known failure (`DIORAMA_ERROR`), anything else an
unexpected error (with `--python-exit-code 1`, Blender exits with `1`).

A structured version of this protocol (one JSON object per line) is planned for
the next minor release; see the roadmap.

## Render signature

Callers that cache renders should key them on: the normalized shot, the render
arguments, the Diorama version (`DIORAMA_BUILD … interpreter=V`) and the Blender
version (`blender --version`). Diorama bumps its version for any change that
alters pixels.
