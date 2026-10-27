---
paths:
  - "hardware/**"
  - "reference-designs/**/hardware/**"
  - "symbols/**"
  - "footprints/**"
  - "3dmodels/**"
  - "design-rules/**"
---

# KiCad (electronics)

- KiCad 10. One KiCad project per PCB in `hardware/<project>/`; the folder's `README.md` describes the layout.
- Parts come from OpenDAP's `kicad-lib` (submodule at `hardware/lib/opendap`, pinned by tag); project-only parts go in `hardware/lib/`. Reference libraries with `${KIPRJMOD}/../lib/…` paths.
- Each project carries the fab rules it targets as `<project>.kicad_dru`, copied from `kicad-lib/design-rules/`.
- Symbols need `Manufacturer` and `MPN` fields.
- Never commit generated outputs (`fab/`, Gerbers, drill, pick-and-place). Build them with `/opendap:fab-package`.
- ERC and DRC run on every commit through pre-commit; fix violations instead of bypassing them.
