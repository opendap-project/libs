# pcbway-hdi

KiCad 10 design rules for PCBWay's advanced HDI process: laser microvias, blind and buried vias, fine-pitch BGA. Written for the T1 main board; usable by any OpenDAP board built as HDI at PCBWay.

- Rules: [`pcbway-hdi.kicad_dru`](pcbway-hdi.kicad_dru), 16 rules.
- Test board: [`test/`](test/), one failing and one passing object per rule.

## Process and stackup assumptions

- PCBWay advanced HDI, 1+N+1 to 6+N+6, stacked or staggered copper-filled microvias [P1, P2, P3, P16]. Starting point: 2+N+2, 8 or 10 layers, FR-4 Tg 170, ENIG as the starting point; the build order depends on the RK3566 ball map, which is not known yet.
- 18 µm (½ oz) base copper on every layer. PCBWay publishes the HDI track/space for this copper only.
- Laser microvias span one dielectric of at most 0.15 mm [P3].

## Source

Every value comes from PCBWay's published capability pages, fetched on 2026-10-22 and recorded with their source keys in [`pcbway-capabilities.md`](../pcbway-capabilities.md). Where PCBWay gives a normal value and a tighter limit, the rule uses the normal value; the limit is listed under [Floors](#floors-for-product-rules) for a product to apply in a named area or net class.

| Key | Page |
|---|---|
| P1 | <https://www.pcbway.com/capabilities.html> |
| P2 | <https://www.pcbway.com/advanced-pcb-capabilities.html> |
| P3 | <https://www.pcbway.com/hdi-pcb.html> |
| P10 | <https://www.pcbway.com/pcb_prototype/PCB_BGA.html> |
| P11 | <https://www.pcbway.com/pcb_prototype/PCB_Via_in_Pad.html> |
| P12 | <https://www.pcbway.com/pcb_prototype/Impedance_Control.html> |
| P16 | <https://www.pcbway.com/HighQualityOrderOnline.aspx> |
| P17 | <https://www.pcbway.com/quotesmt.aspx> |

## Rules

| Rule | Applies to | Value | Source |
|---|---|---|---|
| Copper clearance (outer) | all copper, outer layers | 3 mil | P3, P16 (3/3 mil order option) |
| Copper clearance (inner) | all copper, inner layers | 3 mil | P3, P16 |
| BGA pad to track | pads with the "BGA pad" fabrication property, to tracks | 3 mil | P10 (advanced factory) |
| Track width (outer) | tracks, outer layers | 3 mil | P3, P16 |
| Track width (inner) | tracks, inner layers | 3 mil | P3, P16 |
| BGA pad size | "BGA pad" pads | ≥ 0.25 mm both axes | P10 |
| Mechanical drill | pads, through, blind and buried vias | 0.20–6.5 mm | P1 (advanced, normal) |
| Laser microvia drill | microvias | 0.10 mm – 8 mil | P3 (4 mil standard, 0.1 mm published example, 8 mil maximum) |
| Laser microvia annular ring | microvias | 0.075 mm | P2, P3 (3 mil via ring applied to microvias; see UNVERIFIED) |
| Mechanical via annular ring | through, blind and buried vias | 5 mil | P1 (normal) |
| Via hole to hole | mechanical vias | 11 mil | P1 (vias ≤ 0.45 mm) |
| Hole to copper (outer) | mechanical holes, outer layers | 6 mil | P2 |
| Hole to copper (inner) | mechanical holes, inner layers | 9 mil | P1 (8 layers, normal) |
| Copper to board edge | all copper | 0.20 mm | P1 (milled edge) |
| Silkscreen line width | text on silkscreen | 0.15 mm | P1 |
| Silkscreen text height | text on silkscreen | 0.8 mm | P1 |

Mil figures are written in mil in the rules file, exactly as published (1 mil = 0.0254 mm), so a 0.10 mm value is 3.94 mil and fails a 4 mil rule. A mechanical via needs a land of at least 0.20 + 2 × 0.127 = 0.454 mm for the 5 mil ring (arithmetic). The microvia land follows from the drill and ring rules (0.10 + 2 × 0.075 = 0.25 mm), so there is no separate land rule.

## Board Setup values

KiCad checks the solder mask in Board Setup, not through custom rules. Set these in **Board Setup > Board Stackup > Solder Mask/Paste**:

| Setting | Value | Source |
|---|---|---|
| Solder mask expansion | 0.05 mm (opening ≥ 2 mil, normal) | P1 |
| Solder mask minimum web width | 4 mil (green, ≤ 1 oz; 5 mil other colours) | P3 |

KiCad reports a web below the minimum as `solder_mask_bridge`; the test board checks this too. Pads closer than 8 mil keep no bridge [P2], so fine-pitch rows (0.35–0.4 mm pitch) get one opening per row: allow bridged apertures inside footprints, or draw the gang opening in the footprint.

Also keep the Board Setup minimums (Constraints page) at or below the rule values: KiCad applies them on top of the custom rules.

## Not checkable by KiCad DRC

| Capability | Value | Source | How to check |
|---|---|---|---|
| Through-hole aspect ratio | ≤ 8 normal (20:1 maximum); 0.20 mm hole up to 1.6 mm board, 0.25 mm up to 2.0 mm | P1, P2 | Board thickness against the smallest mechanical drill |
| HDI aspect ratio | 14:1 maximum | P3 | Same |
| Laser via dielectric | ≤ 0.15 mm | P3 | Stackup in Board Setup |
| Microvia stacking and fill | Stacked and staggered, copper-filled; via-in-pad resin-filled and capped | P2, P11, P16 | Fab notes and order options |
| Build order and layer count | 1+N+1 to 6+N+6, from 4 layers | P1, P2, P3, P17 | Stackup |
| BGA pitch | 0.4 mm limit, 0.5 mm conventional (advanced factory) | P2, P10 | Footprint choice |
| Silkscreen graphic line width | 0.15 mm | P1 | `text_thickness` covers text only; check lines by eye or in the footprint |
| Solder mask opening in BGA areas | 1 mil | P1 | Footprint or rule area (floor) |
| Impedance | ±10 %, dielectric ≥ 50 µm | P1, P12 | Stackup and PCBWay's impedance calculator; the rules are geometry only |
| Thickness tolerance | ±0.10 mm (T ≤ 1.0 mm) | P1 | Mechanical drawing |
| Track width tolerance | ±20 % normal | P1 | Impedance budget |

## Floors for product rules

Published limits tighter than the rules above. A product rule may use them in a named area (for example the RK3566 escape) or net class, never board-wide.

| Capability | Floor | Source |
|---|---|---|
| Track/space | 0.065 / 0.065 mm (BGA escape area) | P3 |
| Laser drill | 3 mil (reviewed, single 106 prepreg) | P3 |
| Mechanical drill | 0.15 mm | P3 |
| Mechanical via ring | 4 mil medium; 3 mil minimum (advanced) | P1, P2 |
| Hole to inner copper | 7 mil medium; 6 mil high difficulty | P1 |
| BGA pad | 0.20 mm (advanced factory); 0.15 mm sample limit | P10 |
| BGA pad to line | 2.5 mil (prototype limit) | P10 |
| Solder mask web | 3 mil (green, advanced) | P2 |

## UNVERIFIED

PCBWay does not publish these. They stay out of the rules (or are marked) and go to PCBWay's DFM review:

1. **Microvia land and aspect ratio** for rigid HDI. The microvia ring rule applies PCBWay's general 3 mil via ring; confirm it, and whether copper-filled stacked microvias in 0.25 mm pads on a 0.4 mm grid are a normal or a reviewed build.
2. **Microvia hole to hole** and **laser hole to copper**: no figure, no rule.
3. **Hole to inner copper above 8 layers**: PCBWay publishes the 8-layer figure only; a 10-layer build may need more.
4. **Track/space on 35 µm copper in HDI**: not published for HDI.
5. **Through-hole pad ring, NPTH sizes, pad-to-pad spacing and slots**: not recorded in the capability record, so not in these rules.

## Test board

`test/pcbway-hdi-test.kicad_pcb` (6 copper layers) is generated, not drawn: [`test/make_test_board.py`](test/make_test_board.py) reads each rule's value from the rules file and places one object just past the limit (FAIL column) and one just inside it (PASS column), 0.01 mm either side, with the rule name on `Cmts.User`. `test/pcbway-hdi-test.kicad_dru` is a symbolic link to the rules file, as KiCad needs `<project>.kicad_dru` next to the project. The script also writes the project file and `pcbway-hdi-test.expected.json`, the violations the check expects.

```sh
KICAD_PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KICAD_PY design-rules/pcbway-hdi/test/make_test_board.py
python3 design-rules/tools/check_drc.py design-rules/pcbway-hdi/test/pcbway-hdi-test.kicad_pcb
```

The check runs `kicad-cli pcb drc --format json --severity-all` and fails unless every rule fires exactly once, the solder-mask web check fires once, and nothing else is reported. Result with KiCad 10.0.7: 16 of 16 rules fired, 16 rule violations and 1 Board Setup violation, all in the FAIL column.

The test board fails DRC by design, so the `kicad-drc` pre-commit hook skips `design-rules/*/test/`.
