# Parts Library

The manifest of every external file of the parts OpenDAP designs with: datasheets, manufacturer 3D models, IBIS, SPICE, Touchstone and thermal models. The files themselves live in a local cache and are fetched and verified from the manifest ([ADR 0001](docs/adr/0001-part-data-in-repo-and-local-cache.md), [ADR 0002](docs/adr/0002-public-form-of-a-part.md)).

## Layout

- `manifest.toml` — every external file with its official URL, revision, date and sha256; fetch them into `~/.cache/opendap/parts/` with `toolkit/hardware/tools/parts-sync.py`
- `docs/`

A part's public form is its manifest entries, its KiCad generator data (each value citing the datasheet page, with the datasheet's pin table beside it for the pin check) and the generated symbol, footprint and 3D model, all in [`kicad/`](../kicad/README.md) ([ADR 0002](docs/adr/0002-public-form-of-a-part.md)); mechanical parts are in [`freecad/`](../freecad/README.md).

## License

This repository follows the [REUSE](https://reuse.software) layout: license texts live in `LICENSES/` and `REUSE.toml` maps each path to its license.

- Default (manifest, docs): **Creative Commons Attribution-ShareAlike 4.0** (`CC-BY-SA-4.0`)

Copyright © 2026 The OpenDAP Project.
