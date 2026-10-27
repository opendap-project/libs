# KiCad Library

OpenDAP's own KiCad library: symbols, footprints, 3D models and fab design rules, shared by every OpenDAP hardware project.

Part of [OpenDAP](https://github.com/opendap-project). This repository is open source.

## Working here

- Write everything in English: code, docs, commit messages.
- Record only information the maintainers confirmed. Do not infer specs, numbers or wording.
- Context is in `docs/requirements/`. Update it with `/opendap:requirement`; write an ADR (`/opendap:adr`) only for decisions taken.
- Consumers pin this library by tag. Never change a published part in a way that breaks existing designs; add a new part instead.
- Licensing follows REUSE (`REUSE.toml`, `LICENSES/`). After adding files or folders, run the `/opendap:license-check` skill.
