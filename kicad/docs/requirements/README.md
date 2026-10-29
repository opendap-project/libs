# KiCad library requirements

| ID | Requirement | Priority | Status |
|---|---|---|---|
| KLIB-001 | OpenDAP shall maintain its own KiCad parts library, shared by every OpenDAP hardware project. | must | Confirmed |
| KLIB-002 | The library shall include design rules, each with a test board that triggers every rule, for every fab process OpenDAP boards use. | should | Confirmed |
| KLIB-003 | Every OpenDAP board shall follow the OpenDAP PCB craft standard ([`docs/specs/pcb-craft-standard.md`](../specs/pcb-craft-standard.md)), checked by its DRC rule set, `odapkit craft check` and review, each rule at its quality level. | must | Confirmed |

## Context

- KLIB-002 confirmed by the maintainers on 2026-10-24: OpenDAP keeps its own design rules, complementing the fab's, that fit the project's quality requirements. Rule sets: `pcbway-hdi`, `pcbway-flex`, `pcbway-multilayer` in [`design-rules/`](../../design-rules/). Product rules live with each board and are composed on top of a fab set.
- KLIB-003 confirmed by the maintainers on 2026-10-24: OpenDAP's boards should be elegant and visibly made with care for engineering, quality and appearance, beyond function, shared by every board (main boards, faceplates, HATs). The production mask colour and finish (CRAFT-70) stay a proposal for them. Each rule carries its RFC 0010 quality level, so a prototype is held to the Q1 rules and the rest is recorded as debt.
- KLIB-003 extended on 2026-10-24: the maintainers asked for the same care in KiCad schematics (visual quality, simplicity, technical communication, the software's own semantics). The standard's §9 covers schematics and symbols; the drawing sheet, the feature-block template and an example that passes every check are in `drawing-sheets/`, `templates/` and `examples/`, checked by `odapkit craft check` on schematics and symbol libraries.
- Repository layout: consumed by boards as a pinned submodule; STEP files are sources.
- HDI boards need HDI rules and flat cables flex (or rigid-flex) rules. No public rule set covered these; they are written from the prototype fab's published capabilities.
