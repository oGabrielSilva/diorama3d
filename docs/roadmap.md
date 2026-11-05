# Roadmap

Planned, not implemented. Order may change with feedback.

## 0.2

- Structured process protocol: `@@diorama {"v":1,"type":"frame",...}` lines,
  described by `spec/events.schema.json`, next to the current lines.
- Component manifests (id, params schema, anchors, events) as the single
  source for the schema, the rules and the documentation.
- `diorama-cli` on PyPI, outside Blender: finds Blender, validates, splits the
  range across processes, caches by signature and encodes MP4 with FFmpeg.
- CI golden-image tests: Linux, Blender 5.2, Cycles CPU at low resolution,
  perceptual comparison with tolerance.

## 0.3

- `@diorama3d/client` for Node.js and Electron.
- `diorama-mcp`: an MCP server with validate, render and list-components tools
  for agents.
- External component packs loaded only from paths given on the command line.

## 1.0

- `diorama.shot/1` frozen, protocol v1 stable.
- Extension published on extensions.blender.org.
- Documentation site with a gallery: each example with its shot and video.
