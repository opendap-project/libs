# Blender Library

OpenDAP's own Blender asset library: materials, models and scene setups (lighting, studio, camera rigs), shared by every OpenDAP render.

## Working here

- Context is in `docs/requirements/`. Update it with `/opendap:requirement`; write an ADR (`/opendap:adr`) only for decisions taken.
- Requirements are edited in `docs/requirements/requirements.toml`; `docs/requirements/README.md` is rendered from it with `odapkit req render` and never edited by hand.
- Consumers pin this library by tag. Never change a published part in a way that breaks existing designs; add a new part instead.
