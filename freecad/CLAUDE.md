# FreeCAD Library

OpenDAP's own FreeCAD parts library (screws, inserts, connectors, battery, display modules, …), shared by every OpenDAP mechanical project.

<!-- >>> odapkit sync: managed block from the workspace templates; edit them, not this block -->
Part of [OpenDAP](https://github.com/opendap-project). This repository is Open Source.

Contributor rules (English, confirmed information only, REUSE licensing, the `docs/` layout and its skills): the [contributor guide](https://github.com/opendap-project/.github/blob/main/CONTRIBUTING.md).
<!-- <<< odapkit sync -->

## Working here

- Context is in `docs/requirements/`. Update it with `/opendap:requirement`; write an ADR (`/opendap:adr`) only for decisions taken.
- Requirements are edited in `docs/requirements/requirements.toml`; `docs/requirements/README.md` is rendered from it with `odapkit req render` and never edited by hand.
- Consumers pin this library by tag. Never change a published part in a way that breaks existing designs; add a new part instead.
