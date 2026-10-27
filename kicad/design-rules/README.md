# Design rules

KiCad custom design rules (`.kicad_dru`) for the fabs OpenDAP uses, and the fab-independent craft rules every OpenDAP board adds on top.

## OpenDAP rule sets

Written from PCBWay's published capabilities as recorded in [`pcbway-capabilities.md`](pcbway-capabilities.md) (pages fetched 2026-10-22). Each folder holds the rules, a README with the process, the stackup assumed, a rule-to-source table, what DRC cannot check and the values still UNVERIFIED, and a generated test board that triggers every rule.

| Set | Process | Rules | For |
|---|---|---|---|
| [`pcbway-hdi/`](pcbway-hdi/) | Advanced HDI: laser microvias, blind and buried vias, 18 µm base copper | 16 | Main board |
| [`pcbway-multilayer/`](pcbway-multilayer/) | Advanced multilayer, through vias only; 18 µm and 35 µm base copper variants | 13 each | HAT device-side piece, rigid faceplate boards |
| [`pcbway-flex/`](pcbway-flex/) | Flexible PCB (FPC) | 6 | HAT flat cable, faceplate cable |

The values are PCBWay's normal values. Tighter published limits are listed in each README as floors, for a product to apply in its own product rules, in a named area or net class. KiCad checks the solder mask in Board Setup, not in custom rules: each README gives the Board Setup values to set.

## Craft rules

Fab-independent: the part of the [PCB craft standard](../docs/specs/pcb-craft-standard.md) that DRC can check, with the same folder layout and test board. Rule names carry the CRAFT ID and the quality level (RFC 0010).

| Set | Scope | Rules | For |
|---|---|---|---|
| [`opendap-craft/`](opendap-craft/) | Silkscreen typeface, sizes, orientations and clearances; 45° geometry, track-width series, via set | 13 | Every OpenDAP board, composed after its fab set |

## Vendored rule sets

`vendor/kicad-druid/`: rules for PCBWay, JLCPCB and a generic set (2, 4 and 6 layers), each with a pass/fail test board, vendored unmodified from [Cimos/kicad-druid](https://github.com/Cimos/kicad-druid) at the commit in `UPSTREAM_COMMIT` (MIT). Checked with KiCad 10.0.7: the PCBWay test board loads the rules and they fire. Use them for simple 2- to 6-layer boards without impedance control.

## Use

List the sets in the board's `<project>.dru.toml` and compose `<project>.kicad_dru` with `odapkit dru compose` ([toolkit-hardware](https://github.com/opendap-project/toolkit-hardware)), in this order: the fab set, `opendap-craft`, then the product rules. Or copy one `.kicad_dru` file next to the KiCad project as `<project>.kicad_dru`. Then set the Board Setup values listed in each set's README. `odapkit craft check <board>.kicad_pcb` checks the rest of the craft standard and reports the board's level.

## Test boards

Each OpenDAP set has `test/make_test_board.py`, which builds the test board from the rules file with KiCad's Python (`pcbnew`), and the shared [`tools/check_drc.py`](tools/check_drc.py), which runs `kicad-cli pcb drc` on it and fails unless every rule fires exactly as expected and nothing else does. A rules file that KiCad cannot compile makes `kicad-cli` report a clean board, so the check also proves the file compiled. For a rule whose name carries a quality level (`[Q0]` to `[Q4]`), it also checks the reported severity: error for Q0–Q1, warning for Q2–Q4.

```sh
KICAD_PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
for set in pcbway-hdi pcbway-multilayer pcbway-flex opendap-craft; do
  $KICAD_PY design-rules/$set/test/make_test_board.py
done
python3 design-rules/tools/check_drc.py design-rules/*/test/*.kicad_pcb
```

`check_drc.py` finds `kicad-cli` in `/Applications/KiCad/KiCad.app` (override with `KICAD_APP`) or on `PATH`. Run both after changing a rules file, and commit the regenerated boards; generation is reproducible, so an unchanged rule set gives unchanged files.

## New rule sets

New sets go next to these as `<fab>-<process>/` with the same layout. Vendored sets under `vendor/` are never edited.

1. Take every value from the fab's published capability page for the process, and record the URL and the date read. A value the fab does not publish is listed as an open question in the README, never guessed.
2. Write the rules in KiCad 10 custom-rule syntax, one comment per rule citing its source.
3. Write `test/make_test_board.py`, which builds a test board with one passing and one failing case per rule, and its `expected.json`.
4. Generate the board and run `tools/check_drc.py` on it (above): every rule fires by name, only on the failing cases.
5. Add the README: source URLs and date, process, stackup assumed, the rule-to-source table, Board Setup values, floors for product rules, and what DRC cannot check.
