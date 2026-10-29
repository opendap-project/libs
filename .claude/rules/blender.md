---
paths:
  - "**/renders/**"
  - "**/materials/**"
  - "**/models/**"
  - "**/scenes/**"
---

# Blender (renders)

- Blender 5.2. One folder per scene with `<scene>.blend`; rendered images go to `out/` and are not committed.
- Materials, models and scene setups come from the `blender/` folder of OpenDAP's `libs` (`opendap/` project assets, `shared/` generic ones; submodule at `lib/opendap`), **linked**, not appended.
- Bring other components in by linking their exported collection or glTF from their `export/`.
- Product-side 3D animations and interactive previews that do not need Blender can be standalone HTML documents (three.js, anime.js…) in `renders/web/`, loading the component's glTF export. Pin library versions.
