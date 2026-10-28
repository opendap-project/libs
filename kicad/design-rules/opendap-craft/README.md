# opendap-craft

KiCad 10 design rules for the part of the [OpenDAP PCB craft standard](../../docs/specs/pcb-craft-standard.md) that DRC can check. Fab-independent: every OpenDAP board composes it after its fab rule set and before its product rules.

- Rules: [`opendap-craft.kicad_dru`](opendap-craft.kicad_dru), 13 rules for 12 CRAFT IDs.
- Test board: [`test/`](test/), one failing and one passing object per rule, and two rows of exempt objects that must raise nothing.
- The rest of the standard: `odapkit craft check` ([tools/hardware](https://github.com/opendap-project/tools/tree/main/hardware)) and review.

## Levels

Each rule name carries its CRAFT ID and its quality level ([RFC 0010](https://github.com/opendap-project/rfcs/blob/main/text/0010-quality-levels.md)): `OpenDAP CRAFT-40 [Q2]: …`. Q0–Q1 rules report as errors, Q2–Q4 rules as warnings (`(severity warning)`); `check_drc.py` verifies the severity against the tag. `odapkit craft check` folds these violations into its report by level.

## Rules

| Rule | Level | Constraint | Value |
|---|---|---|---|
| CRAFT-01 Silk text in the stroke font, regular, upright | Q2 | assertion on `Font`, `Italic`, `Bold` | `KiCad Font` |
| CRAFT-02 Silk text size from the set | Q2 | assertion on `Height`, `Width`, `Thickness` | 0.8 × 0.15, 1.0 × 0.15, 1.6 × 0.24, 2.0 × 0.30 mm; width = height |
| CRAFT-03 Silk text at 0 or 90 degrees | Q2 | assertion on `Orientation` | 0°, 90° |
| CRAFT-04 Silk text reads from its own side | Q1 | assertion on `Layer`, `Mirrored` | top unmirrored, bottom mirrored |
| CRAFT-05 Silk line width | Q2 | assertion on `Line_Width` (unfilled graphics) | 0.15 mm |
| CRAFT-07 Silk clearance to pads | Q2 | `silk_clearance` | 0.15 mm |
| CRAFT-07 Silk clearance to vias | Q2 | `silk_clearance` | 0.30 mm to the via hole (0.15 mm to the largest land in the set) |
| CRAFT-09 Silk text clear of other silk | Q2 | `silk_clearance` | 0.15 mm |
| CRAFT-40 Track segments at multiples of 45 degrees | Q2 | assertion on `Start_X/Y`, `End_X/Y` | 0.001 mm tolerance |
| CRAFT-41 Track corners of 135 degrees or more | Q3 | `track_angle` | min 135° |
| CRAFT-43 Track width from the series | Q2 | assertion on `Width` | 0.08 … 5.0 mm series; > 5 mm unchecked |
| CRAFT-45 Via from the set | Q2 | assertion on `Hole`, `Diameter` | 0.10/0.25, 0.20/0.46, 0.30/0.60 mm |
| CRAFT-47 No track segment shorter than 0.1 mm | Q4 | `track_segment_length` | min 0.1 mm |

Exemptions, built into the conditions: impedance-controlled net classes named `<name>_<ohms>D` or `<name>_<ohms>SE` (CRAFT-40, CRAFT-43), and rule areas named `CRAFT-EXEMPT*` or containing `ESCAPE` (CRAFT-40, -41, -43, -47). The standard's [§2](../../docs/specs/pcb-craft-standard.md#2-how-the-standard-is-applied) explains them.

## Board Setup values

Set in **Board Setup > Design Rules > Violation Severity**:

| Check | Severity | Rule |
|---|---|---|
| `silk_over_copper` (silkscreen clipped by solder mask) | Error | CRAFT-06 [Q1] |
| `isolated_copper` | Error | CRAFT-49 [Q2] |
| `mirrored_text_on_front_layer`, `nonmirrored_text_on_back_layer` | Error | CRAFT-04 [Q1] (KiCad's own check, which fires with the rule) |

## What KiCad 10.0.7 can and cannot check

Each property and constraint was tested with kicad-cli 10.0.7 before use, on a failing and a passing object.

| Finding | Consequence |
|---|---|
| An assertion on a property KiCad does not know (`Text_Height`, `Text_Width`) fails on every object, with no error. | Every assertion here has a failing and a passing test object. |
| `track_angle` takes bare degrees, `(min 135)`; `(min 135deg)` makes KiCad drop the whole rules file without an error. It measures the angle between connected segments and reports each corner once per segment. | CRAFT-41 expects two violations per corner. |
| `silk_clearance` measures silk to a via's hole, not its land; silk to pads is measured to the copper and reported as `silk_over_copper`. | CRAFT-07 for vias uses 0.30 mm to the hole. |
| `silk_clearance` against Edge.Cuts skips silk lines and gave 0.8 to 3.0 mm for the same text-to-cutout geometry. | CRAFT-08 is checked by `odapkit craft check`. |
| Silk text is measured through a polygon approximation: the same text-to-line gap read up to about 0.08 mm apart at two positions. | CRAFT-09's test objects sit 0.10 mm inside and 0.25 mm outside the limit, not 0.01 mm. |
| Arcs report `Type == 'Track'` and expose no arc-only property. | CRAFT-42 (arcs only on impedance classes) is checked by `odapkit craft check`. |
| `connection_width` reported nothing for a filled zone with a 1 mm neck against a 2 mm minimum, with and without `--refill-zones`. | Copper slivers are controlled by the zone's minimum width (CRAFT-50, `odapkit craft check`). |
| Net-class and rule-area names accept `*` and `?` wildcards (`A.NetClass == '*_??D'`, `A.intersectsArea('*ESCAPE*')`). | The exemptions use them. |
| Every matching assertion is applied: a later rule cannot relax an earlier assertion. | Exemptions are built into the craft rules' conditions. |

## Test board

`test/opendap-craft-test.kicad_pcb` (4 copper layers) is generated by [`test/make_test_board.py`](test/make_test_board.py) on the shared [`tools/testboard.py`](../tools/testboard.py), like the fab sets. The craft rules are closed sets and geometry, so most rows are drawn by the script itself rather than by a shared fixture: the failing object breaks only its own rule, the passing object is the nearest allowed value. The last rows hold copper that would break CRAFT-40, -41, -43 and -47: in an impedance class (`TEST_90D`) only the corner and the jog fire, since those rules do not exempt impedance classes; in the class `BAT_SENSE`, which ends in `SE` without being an impedance class (impedance classes are named `<NAME>_<ohms>D` or `<NAME>_<ohms>SE`, 10–299 Ω), every rule fires; in a `BGA_ESCAPE` rule area nothing fires.

```sh
KICAD_PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KICAD_PY design-rules/opendap-craft/test/make_test_board.py
python3 design-rules/tools/check_drc.py design-rules/opendap-craft/test/opendap-craft-test.kicad_pcb
```

Result with KiCad 10.0.7: 13 of 13 rules fired, 24 rule violations and KiCad's `mirrored_text_on_front_layer` once, all in the FAIL column, each at the severity of its level.
