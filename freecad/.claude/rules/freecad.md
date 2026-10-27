---
paths:
  - "case/**"
  - "core/**"
  - "hat-mount/**"
  - "parts/**"
  - "assembly/**"
  - "reference-designs/**/case/**"
---

# FreeCAD (mechanics)

- FreeCAD 1.1. One folder per part with `<part>.FCStd` and `exports/` (STEP, STL where printed); see the folder's `README.md`.
- Shared parts (screws, inserts, connectors, battery, modules) come from OpenDAP's `freecad-lib` (submodule at `lib/opendap`, pinned by tag).
- To use another component, import its `export/` STEP as a single body; never copy its sources.
- `.FCStd` is binary: keep one logical change per commit.
