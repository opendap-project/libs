# pcbway-flex

KiCad 10 design rules for PCBWay's flexible PCB (FPC) process. For any OpenDAP flex circuit built at PCBWay, such as flat cables between boards.

- Rules: [`pcbway-flex.kicad_dru`](pcbway-flex.kicad_dru), 6 rules.
- Test board: [`test/`](test/), one failing and one passing object per rule.

## Process and stackup assumptions

- PCBWay FPC, adhesiveless polyimide, ENIG, coverlay, 1–12 layers on the capability page (16 on the order form) [P5, P13].
- Starting point: 2 layers for the faceplate cable (FH35C tail 0.2 mm with a PI stiffener) and 4 layers for the HAT flat cable (0.2–0.33 mm, air-gap stack-up as an option) [P14]. These layer counts are proposals.
- Finished copper: outer 9–88 µm, inner 12, 18 or 35 µm [P13]. PCBWay publishes one track/space figure for every flex layer and copper, so every rule applies to all copper layers.
- Coverlay is drawn on the solder-mask layers.

## Source

Every value comes from PCBWay's published capability pages, fetched on 2026-10-22 and recorded with their source keys in [`pcbway-capabilities.md`](../pcbway-capabilities.md) (flex table). Where PCBWay gives a normal value and a tighter limit, the rule uses this set's default; the limit is listed under [Floors](#floors-for-product-rules).

| Key | Page |
|---|---|
| P1 | <https://www.pcbway.com/capabilities.html> |
| P5 | <https://www.pcbway.com/fpc-rigid-flex-pcb/flex-pcb.html> |
| P13 | <https://www.pcbway.com/flexible.aspx> |
| P14 | <https://www.pcbway.com/pcb_prototype/Stack_up_for_FPC.html> |

## Rules

| Rule | Applies to | Value | Source |
|---|---|---|---|
| Copper clearance | all copper, all layers | 3 mil | P5, P13 (set default) |
| Track width | tracks, all layers | 3 mil | P5, P13 (set default) |
| Drill | pads and vias | ≥ 0.15 mm | P13 (hole/pad 0.15/0.35 mm) |
| Via pad diameter | vias | ≥ 0.35 mm | P13 |
| Plated hole pad size | through-hole pads | ≥ 0.35 mm both axes | P13 |
| Copper to outline (UNVERIFIED) | all copper | 0.20 mm | P1, the rigid milled-edge figure: PCBWay publishes none for flex |

Mil figures are written in mil, exactly as published (1 mil = 0.0254 mm).

## Board Setup values

KiCad checks the solder mask (here, the coverlay) in Board Setup, not through custom rules. Set this in **Board Setup > Board Stackup > Solder Mask/Paste**:

| Setting | Value | Source |
|---|---|---|
| Solder mask minimum web width (coverlay bridge) | 8 mil | P5, P13 |
| Solder mask expansion (coverlay opening) | **UNVERIFIED**: not published | — |

KiCad reports a web below the minimum as `solder_mask_bridge`; the test board checks this too. The DF40 receptacles (0.4 mm pitch, 0.20 mm lands, 0.20 mm gap) sit below the 8 mil bridge, so each row gets one coverlay opening, or LPI solder mask on flex (green or black [P5]) in that area.

Also keep the Board Setup minimums (Constraints page) at or below the rule values: KiCad applies them on top of the custom rules.

## Not checkable by KiCad DRC

| Capability | Value | Source | How to check |
|---|---|---|---|
| Bend radius | Single layer 3–6 × thickness; two layers 7–10 ×; multilayer 10–15 × | P5 | Case drawing: bend radius against the flex thickness. Keep components, vias and stiffeners out of bend zones, with keep-out rule areas in the product |
| Stiffeners | PI 0.05–0.25 mm; FR-4 0.2–1.5 mm; stainless steel 0.1–0.5 mm; aluminium 0.2–1.5 mm | P13 | Fab drawing; stiffened areas must not bend |
| Thickness tolerance | ±1.2 mil for two layers ≤ 12 mil; ±8 % for 12–32 mil | P5 | Mechanical drawing (the FH35C tail needs 0.2 ± 0.03 mm) |
| Outline tolerance | ±2 mil laser; ±2–6 mil punching | P5 | Mechanical drawing (FH35C outline 15.6 ± 0.05 mm) |
| Impedance | ±4 Ω (≤ 50 Ω); ±7 % (> 50 Ω) | P5 | Stack-up and PCBWay's impedance calculator; the rules are geometry only |
| Size | 0.0788 × 0.1576 in to 8.668 × 27.5 in | P5 | Outline |

## Floors for product rules

| Capability | Floor | Source |
|---|---|---|
| Track/space | 2/2 mil (page); 0.06 mm (order form) | P5, P13 |
| Mechanical hole | 4 mil | P5 |

## UNVERIFIED

PCBWay does not publish these for flex. They stay out of the rules, except copper to outline, which keeps the rigid figure until PCBWay answers. Ask in PCBWay's DFM review:

1. **Copper to outline on flex**: the rule uses the rigid 0.20 mm milled-edge figure [P1].
2. **Coverlay opening** (expansion) rules.
3. **Thickness tolerance with a PI stiffener**, at the FH35C mating area (target 0.2 ± 0.03 mm).
4. **Hole to hole, hole to copper and annular ring** on flex.
5. **Silkscreen** on flex (line width, height).
6. **Blind, buried or laser vias** on flex.
7. **Flex assembly limits** (fine pitch, connectors on a stiffened area, panelisation).

## Test board

`test/pcbway-flex-test.kicad_pcb` (2 copper layers) is generated, not drawn: [`test/make_test_board.py`](test/make_test_board.py) reads each rule's value from the rules file and places one object just past the limit (FAIL column) and one just inside it (PASS column), 0.01 mm either side, with the rule name on `Cmts.User`. `test/pcbway-flex-test.kicad_dru` is a symbolic link to the rules file, as KiCad needs `<project>.kicad_dru` next to the project. The script also writes the project file and `pcbway-flex-test.expected.json`, the violations the check expects.

```sh
KICAD_PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KICAD_PY design-rules/pcbway-flex/test/make_test_board.py
python3 design-rules/tools/check_drc.py design-rules/pcbway-flex/test/pcbway-flex-test.kicad_pcb
```

Result with KiCad 10.0.7: 6 of 6 rules fired, 6 rule violations and 1 Board Setup violation (coverlay bridge), all in the FAIL column.

The test board fails DRC by design, so the `kicad-drc` pre-commit hook skips `design-rules/*/test/`.
