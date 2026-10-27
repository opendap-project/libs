# Libraries

OpenDAP's shared design libraries, one folder per tool, used by every OpenDAP hardware, mechanical and render project:

| Folder | Content |
| --- | --- |
| [`kicad/`](kicad/README.md) | KiCad symbols, footprints, 3D models, fab design rules, drawing sheet and colour theme |
| [`parts/`](parts/README.md) | Tool-independent part data: one spec sheet per part, and the manifest of external files |
| [`freecad/`](freecad/README.md) | FreeCAD parts (screws, inserts, connectors, battery, display modules, …) |
| [`blender/`](blender/README.md) | Blender materials, models and scene setups |

Consumers pin this repository by tag. Each folder keeps its own `docs/` (requirements, specs, ADRs) and `REUSE.toml`; the licence texts are in `LICENSES/`. The folders came from the former `kicad-lib`, `parts-lib`, `freecad-lib` and `blender-lib` repositories with their history ([RFC 0017](https://github.com/opendap-project/rfcs/blob/main/text/0017-naming-and-topology.md)).

## License

This repository follows the [REUSE](https://reuse.software) layout: licence texts in `LICENSES/`, and each folder's `REUSE.toml` maps its paths. Copyright © 2026 The OpenDAP Project.
