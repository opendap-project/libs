# Libraries

OpenDAP's shared design libraries, one folder per tool, used by every OpenDAP hardware, mechanical and render project:

| Folder | Content |
| --- | --- |
| [`kicad/`](kicad/README.md) | KiCad symbols, footprints, 3D models, fab design rules, drawing sheet and colour theme |
| [`parts/`](parts/README.md) | The manifest of external part files (datasheets, manufacturer models), fetched into a local cache |
| [`freecad/`](freecad/README.md) | FreeCAD parts (screws, inserts, connectors, battery, display modules, …) |
| [`blender/`](blender/README.md) | Blender materials, models and scene setups |

Consumers pin this repository by tag. Each folder keeps its own `docs/` (requirements, specs, ADRs) and `REUSE.toml`; the licence texts are in `LICENSES/`. The folders came from the former `kicad-lib`, `parts-lib`, `freecad-lib` and `blender-lib` repositories with their history ([RFC 0017](https://github.com/opendap-project/rfcs/blob/main/text/0017-naming-and-topology.md)).

## Maker keys

Each maker has one key in lowercase kebab case (`texas-instruments`, `diodes-inc`, `rockchip`; `opendap-generic` for generic symbols that are no one maker's part). The key names everything that belongs to the maker in every folder:

| Where | Form |
| --- | --- |
| KiCad libraries | `kicad/symbols/<key>.kicad_sym`, `kicad/footprints/<key>.pretty/`, `kicad/3dmodels/<key>.3dshapes/` |
| Library ids in schematics and boards | `<key>:<symbol or footprint>`, for example `texas-instruments:Texas_DBV0005A_SOT-23-5_1.6x2.9mm_P0.95mm` |
| Generator data | `kicad/generator/parts/<key>/`, `kicad/generator/bga/<key>/`, `library = "<key>"` |
| Spec sheets | `parts/<key>/<MPN>.md` |

The maker's display name is a field, never a key: `manufacturer` in the part data and in `parts/manifest.toml`, and the `Manufacturer` field of each symbol (`Texas Instruments`). The local parts cache follows the display name (`~/.cache/opendap/parts/<manufacturer>/<MPN>/`, named by `parts-sync.py`); the `pdf` path in a BGA part's `[check]` is relative to its maker's cache folder.

## Tests

Tests never inherit a hook's `GIT_*` variables: under pre-commit, git exports `GIT_DIR`, `GIT_INDEX_FILE` and others, and a test whose git inherits them acts on the repository being committed. Each test module in `kicad/generator/` that starts a process removes them after its imports. Each language's protection is in the Developer Toolkit's [rule](https://github.com/opendap-project/tools#tests-never-inherit-a-hooks-git-variables); `odapkit audit` flags a test file that runs git without it.

## License

This repository follows the [REUSE](https://reuse.software) layout: licence texts in `LICENSES/`, and each folder's `REUSE.toml` maps its paths. Copyright © 2026 The OpenDAP Project.
