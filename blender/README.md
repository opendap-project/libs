# Blender Library

OpenDAP's own Blender asset library: materials, models and scene setups (lighting, studio, camera rigs), shared by every OpenDAP render.

## Layout

- `opendap/` — assets that belong to the OpenDAP project: models of OpenDAP products, their materials and finishes, product scenes.
- `shared/` — generic assets meant for anyone to build on: materials, lighting and studio setups, camera rigs, generic models.
- Each area holds `materials/`, `models/` and `scenes/`.
- `docs/`

## Use

OpenDAP repositories add this library as a git submodule, pinned to a tag, at `lib/opendap` inside their renders folder (for example `renders/lib/opendap`), and **link** assets from it so that a change here propagates to every render.

## Rendering rules

Every render made with this library follows the OpenDAP design language: matte graphite polymer by default, soft studio light, orange only on the Action button and used sparingly elsewhere, plasma effects only in display content or an explicit concept visualisation, and accurate proportions of the real parts. The rules are in the [case industrial-design spec](https://github.com/opendap-project/case/blob/main/docs/specs/industrial-design.md) (§ Rendering rules) and the [design system spec](https://github.com/opendap-project/blackbird/blob/main/ui/docs/specs/design-system.md); materials in `opendap/` implement them.

## License

This repository follows the [REUSE](https://reuse.software) layout: license texts live in `LICENSES/` and `REUSE.toml` maps each path to its license.

- `opendap/`: **Creative Commons Attribution-ShareAlike 4.0** (`CC-BY-SA-4.0`)
- `shared/`: **Creative Commons Attribution 4.0** (`CC-BY-4.0`), so others can use them in their own work freely
- Markdown files and `docs/`: **Creative Commons Attribution-ShareAlike 4.0** (`CC-BY-SA-4.0`)

Copyright © 2026 The OpenDAP Project.
