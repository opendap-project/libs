# Parts Library

Tool-independent data for every part OpenDAP designs with, shared by every repository: one spec sheet per part transcribed from its datasheet, and the manifest of external files (datasheets, manufacturer 3D models, IBIS, SPICE, Touchstone and thermal models) that live in a local cache ([ADR 0001](docs/adr/0001-part-data-in-repo-and-local-cache.md)).

## Layout

- `<manufacturer>/<MPN>.md` — spec sheet: absolute maximum ratings, operating conditions, power by mode, pinout and package, recommended footprint, application circuit and required passives, interfaces and timing, Linux driver, available simulation models, design notes; each with its datasheet reference. Structure: [spec sheet template](docs/specs/spec-sheet-template.md)
- `manifest.toml` — every external file with its official URL, revision, date and sha256; fetch them into `~/.cache/opendap/parts/` with `toolkit/hardware/tools/parts-sync.py`
- `docs/`

Symbols, footprints and 3D models live in `kicad-lib`; mechanical parts in `freecad-lib`.

## License

This repository follows the [REUSE](https://reuse.software) layout: license texts live in `LICENSES/` and `REUSE.toml` maps each path to its license.

- Default (spec sheets, manifest, docs): **Creative Commons Attribution-ShareAlike 4.0** (`CC-BY-SA-4.0`)

Copyright © 2026 The OpenDAP Project.
