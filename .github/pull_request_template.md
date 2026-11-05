## What and why

<!-- One topic per PR. Link the issue, if any. -->

## Checklist

- [ ] Commits are signed off (`git commit -s`, see CONTRIBUTING.md).
- [ ] `python -m unittest discover -s tests` passes (and with Blender's Python for `diorama3d/core/` changes).
- [ ] Shots stay data: nothing from a shot is executed, imported or opened as a path.
- [ ] Animation derives only from the frame (no clock, no unseeded randomness).
- [ ] Pixels changed → `__version__` and the manifest version were bumped.
- [ ] Format changed → `spec/shot.schema.json`, its copy in `diorama3d/core/`, conformance cases and CHANGELOG were updated.
- [ ] Visual change → before/after images attached.
