# pcbway-multilayer

KiCad 10 design rules for PCBWay's advanced multilayer process with through vias only. For any 4- or 6-layer OpenDAP board built at PCBWay without blind, buried or laser vias.

| File | Base copper | Rules |
|---|---|---|
| [`pcbway-multilayer.kicad_dru`](pcbway-multilayer.kicad_dru) | 18 µm (½ oz) on every layer | 13 |
| [`pcbway-multilayer-35um.kicad_dru`](pcbway-multilayer-35um.kicad_dru) | 35 µm (1 oz) on every layer | 13 |

The two files differ only in track width and clearance. A stack that mixes 18 µm and 35 µm layers can use the 35 µm file (its figures are the larger ones) or override the 18 µm layers in its product rules: KiCad rules cannot read the copper thickness from the stackup.

Boards with BGAs, blind, buried or laser vias use [`pcbway-hdi`](../pcbway-hdi/). The vendored kicad-druid PCBWay set stays for simple 2- to 6-layer boards.

## Process and stackup assumptions

- PCBWay advanced multilayer, 4 or 6 layers, FR-4, through vias only, impedance control available, ENIG (hard gold where a contact surface needs it) [P1, P2].
- Base copper as in the table above, before plating.

## Source

Every value comes from PCBWay's published capability pages, fetched on 2026-10-22 and recorded with their source keys in [`pcbway-capabilities.md`](../pcbway-capabilities.md) (rigid boards table). Where PCBWay gives a normal value and a tighter limit, the rule uses the normal value; the limit is listed under [Floors](#floors-for-product-rules).

| Key | Page |
|---|---|
| P1 | <https://www.pcbway.com/capabilities.html> |
| P2 | <https://www.pcbway.com/advanced-pcb-capabilities.html> |
| P12 | <https://www.pcbway.com/pcb_prototype/Impedance_Control.html> |

## Rules

| Rule | Applies to | 18 µm | 35 µm | Source |
|---|---|---|---|---|
| Copper clearance (outer) | all copper, outer layers | 5 mil | 6 mil | P1 (normal) |
| Copper clearance (inner) | all copper, inner layers | 4 mil | 5 mil | P1 (normal) |
| Track width (outer) | tracks, outer layers | 4 mil | 5 mil | P1 (normal) |
| Track width (inner) | tracks, inner layers | 4 mil | 4 mil | P1 (normal) |
| Through vias only | vias | no micro, blind or buried vias | same | process scope of this set |
| Mechanical drill | pads and vias | 0.20–6.5 mm | same | P1 (advanced, normal) |
| Via annular ring | vias | 5 mil | same | P1 (normal, outer, 18–35 µm) |
| Via hole to hole | vias | 11 mil | same | P1 (vias ≤ 0.45 mm) |
| Hole to copper (outer) | holes, outer layers | 6 mil | same | P2 |
| Hole to copper (inner) | holes, inner layers | 8 mil | same | P1 (6 layers; 7 mil for 4 layers) |
| Copper to board edge | all copper | 0.20 mm | same | P1 (milled edge) |
| Silkscreen line width | text on silkscreen | 0.15 mm | same | P1 |
| Silkscreen text height | text on silkscreen | 0.8 mm | same | P1 |

Rule names carry the file: `PCBWay multilayer: …` and `PCBWay multilayer 35um: …`. Mil figures are written in mil, exactly as published (1 mil = 0.0254 mm). A via needs a land of at least 0.20 + 2 × 0.127 = 0.454 mm for the 5 mil ring (arithmetic).

## Board Setup values

KiCad checks the solder mask in Board Setup, not through custom rules. Set these in **Board Setup > Board Stackup > Solder Mask/Paste**:

| Setting | Value | Source |
|---|---|---|
| Solder mask expansion | 0.05 mm (opening ≥ 2 mil, normal) | P1 |
| Solder mask minimum web width | 4 mil (green, 1 oz) | P1 |

KiCad reports a web below the minimum as `solder_mask_bridge`; the test boards check this too. Pads closer than 8 mil keep no bridge [P2], so the 0.4 mm DF40 rows get one opening per row: allow bridged apertures inside footprints, or draw the gang opening in the footprint.

Also keep the Board Setup minimums (Constraints page) at or below the rule values: KiCad applies them on top of the custom rules.

## Not checkable by KiCad DRC

| Capability | Value | Source | How to check |
|---|---|---|---|
| Aspect ratio | ≤ 8 normal; 0.20 mm hole up to 1.6 mm board, 0.25 mm up to 2.0 mm | P1 | Board thickness against the smallest drill |
| Minimum thickness | 4 layers 0.60 mm, 6 layers 0.9 mm (0.40 / 0.70 mm floor) | P1 | Stackup |
| Impedance | ±10 % | P1 | Stackup and PCBWay's impedance calculator; the rules are geometry only |
| Thickness tolerance | ±0.10 mm (T ≤ 1.0 mm); ±0.18 mm (1.6 mm) | P1 | Mechanical drawing |
| Silkscreen graphic line width | 0.15 mm | P1 | `text_thickness` covers text only |

## Floors for product rules

| Capability | Floor | Source |
|---|---|---|
| Outer track/space, 18 µm | 4/4 mil (medium) | P1 |
| Inner track/space, 18 µm | 4/3.5 mil (medium) | P1 |
| Outer track/space, 35 µm | 5/5 mil (medium) | P1 |
| Inner track/space, 35 µm | 4/4 mil (medium) | P1 |
| Via drill / land | 0.15 / 0.35 mm | P1 |
| Via ring | 4 mil medium; 3 mil minimum (advanced) | P1, P2 |
| Hole to inner copper | 6 / 6.5 mil (4 / 6 layers) | P1 |
| Solder mask expansion / web | 0.025 / 0.075 mm | P1, P2 |

## UNVERIFIED

Not in the capability record, so not in the rules; ask in PCBWay's DFM review when a board needs them:

1. **Through-hole pad ring, NPTH sizes, pad-to-pad spacing and slots.**
2. **Hole to hole for holes larger than 0.45 mm** and between vias and pads: the published figure covers vias ≤ 0.45 mm only, so the rule checks via pairs only.
3. **Copper heavier than 35 µm**: PCBWay offers up to 8 oz outer and 4 oz inner [P1], but the capability record has track/space for 18 and 35 µm only.

## Test boards

`test/pcbway-multilayer-test.kicad_pcb` and `test/pcbway-multilayer-35um-test.kicad_pcb` (4 copper layers) are generated, not drawn: [`test/make_test_board.py`](test/make_test_board.py) reads each rule's value from its rules file and places one object just past the limit (FAIL column) and one just inside it (PASS column), 0.01 mm either side, with the rule name on `Cmts.User`. Each `test/<board>.kicad_dru` is a symbolic link to its rules file, as KiCad needs `<project>.kicad_dru` next to the project. The script also writes the project files and the `.expected.json` files the check reads.

```sh
KICAD_PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KICAD_PY design-rules/pcbway-multilayer/test/make_test_board.py
python3 design-rules/tools/check_drc.py design-rules/pcbway-multilayer/test/*.kicad_pcb
```

Result with KiCad 10.0.7, each board: 13 of 13 rules fired, 13 rule violations and 1 Board Setup violation, all in the FAIL column.

The test boards fail DRC by design, so the `kicad-drc` pre-commit hook skips `design-rules/*/test/`.
