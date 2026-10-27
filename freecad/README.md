# FreeCAD Library

OpenDAP's own FreeCAD parts library (screws, inserts, connectors, battery, display modules, …), shared by every OpenDAP mechanical project.

## Layout

- `parts/<category>/<part>/` — `<part>.FCStd` plus `exports/` with STEP (and STL where printed)
- `docs/`

## Use

OpenDAP repositories add this library as a git submodule, pinned to a tag, at `lib/opendap` inside their mechanics folder (for example `case/lib/opendap`), and link parts from it.

## License

This repository follows the [REUSE](https://reuse.software) layout: license texts live in `LICENSES/` and `REUSE.toml` maps each path to its license.

- Default: **CERN Open Hardware Licence v2 – Weakly Reciprocal** (`CERN-OHL-W-2.0`)
- Markdown files: **Creative Commons Attribution-ShareAlike 4.0** (`CC-BY-SA-4.0`)

Copyright © 2026 The OpenDAP Project.
