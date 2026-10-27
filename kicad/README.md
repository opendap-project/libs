# KiCad Library

OpenDAP's own KiCad library: symbols, footprints, 3D models and fab design rules, shared by every OpenDAP hardware project.

## Layout

- `symbols/` — symbol libraries (`*.kicad_sym`): one per manufacturer, plus `OpenDAP_Device` for generic symbols drawn to the craft standard where KiCad's stock one fails it (crystals)
- `footprints/` — footprint libraries (`<name>.pretty/`)
- `3dmodels/` — 3D models. STEP is the source for each part; other formats are generated from it.
- `design-rules/` — fab design rules and the craft rules (`.kicad_dru`) with their test boards
- `drawing-sheets/` — the OpenDAP drawing sheet (`.kicad_wks`)
- `colour-themes/` — the OpenDAP schematic colour theme
- `templates/` — the feature-block sheet template and the generator of the schematic files ([README](templates/README.md))
- `examples/` — an example project that passes every schematic check
- `docs/` — requirements, decisions and the [PCB craft standard](docs/specs/pcb-craft-standard.md) (layout, schematics and symbols)

## Use

OpenDAP repositories add this library as a git submodule at `hardware/lib/opendap`, pinned to a tag, and reference it from their library tables with `${KIPRJMOD}/../lib/opendap/…`.

## License

This repository follows the [REUSE](https://reuse.software) layout: license texts live in `LICENSES/` and `REUSE.toml` maps each path to its license.

- Default: **CERN Open Hardware Licence v2 – Weakly Reciprocal** (`CERN-OHL-W-2.0`)
- Markdown files: **Creative Commons Attribution-ShareAlike 4.0** (`CC-BY-SA-4.0`)
- Python scripts (design-rule test tooling): **GNU General Public License v3.0 or later** (`GPL-3.0-or-later`)
- `design-rules/vendor/kicad-druid/`: **MIT** (`MIT`), © 2023 Cimos, vendored unmodified

Copyright © 2026 The OpenDAP Project.
