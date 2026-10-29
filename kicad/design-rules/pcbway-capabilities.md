# PCBWay published capabilities

PCBWay is the prototype fab whose published processes the `pcbway-*` rule sets target. This file records the figures those rule sets are written from, copied from PCBWay's capability pages and cited by source key (for example [P1]). A figure PCBWay does not publish on those pages is marked **UNVERIFIED**. Arithmetic on published figures (for example a pad gap from a pitch and a land width) is shown as such and is not a PCBWay statement.

## Capability tables

PCBWay publishes two tiers for rigid boards: "Standard PCB" (quick-turn, [P1] first table) and "Advanced PCB" ([P1] second table, [P2]). The advanced table grades each parameter as normal, medium difficulty, high difficulty or non-standard review. The tables below list the normal value first and the limit after it.

### Rigid boards (standard and advanced)

| Parameter | Value | Source |
|---|---|---|
| Layers | Standard 1–14; advanced 3–16 normal, 18–24 medium, ≥ 24 high; up to 64 | P1, P2 |
| Board thickness | Standard 0.2–3.2 mm; advanced 0.21–6.0 mm | P1, P2 |
| Minimum multilayer thickness (through-hole build) | 8 layers ≥ 1.20 mm normal, 1.00 mm medium; 10 layers ≥ 1.40 / 1.20 mm | P1 |
| Thickness tolerance | T ≤ 1.0 mm: ±0.10 mm; 1.6 mm: ±0.18 mm | P1 |
| Outer track/space before compensation, 18 µm copper | ≥ 4/5 mil normal; 4/4 mil medium; locally 3.5/3.5 mil from a BGA-area line to a pad | P1 |
| Outer track/space, 35 µm copper | ≥ 5/6 mil normal; 5/5 mil medium | P1 |
| Inner track/space, 18 µm copper | ≥ 4/4 mil normal; 4/3.5 mil medium | P1 |
| Inner track/space, 35 µm copper | ≥ 4/5 mil normal; 4/4 mil medium | P1 |
| Minimum track/space, advanced | 2/2 mil on parts of the board only (H/H oz inner, 1/3 oz outer) | P2 |
| Track width tolerance | ±20 % normal; ±10 % medium | P1 |
| Mechanical drill | Standard 0.15–6.0 mm; advanced 0.20–6.5 mm normal | P1 |
| Hole size versus board thickness | 0.20 mm up to 1.6 mm thick; 0.25 mm up to 2.0 mm | P1 |
| Aspect ratio (through) | ≤ 8 normal; 20:1 maximum (advanced) | P1, P2 |
| Via annular ring (outer, 18–35 µm) | ≥ 5 mil normal; 4 mil medium; 3 mil minimum (advanced) | P1, P2 |
| Hole to hole, vias ≤ 0.45 mm | ≥ 11 mil | P1 |
| Hole to inner conductor (8 layers) | ≥ 9 mil normal; 7 mil medium; 6 mil high | P1 |
| Hole to conductor (advanced) | 6 mil inner and outer | P2 |
| Copper weights | Outer 1–8 oz, inner 1–4 oz (standard); 1/3 oz base minimum (advanced) | P1, P2 |
| Minimum dielectric | 2 mil (advanced); 50 µm for impedance stack-ups | P2, P12 |
| Impedance tolerance | ±10 %; ±5 Ω at 50 Ω and below | P1, P2 |
| Plugged vias | 0.15 mm (CNC) and 0.10 mm (laser blind/buried) to 0.7 mm | P2 |
| Via-in-pad | Offered; BGA via-in-pad is resin-filled with a plated cap; options "via in pad", "via filled with resin", "all vias filled with resin and capped", "via filled with copper", back drill, custom stack-up | P11, P15, P16 |
| Solder mask | Opening ≥ 2 mil normal, 1 mil only in BGA areas; bridge 4 mil (green, 1 oz); 3 mil minimum (advanced, green), 4 mil (black); IC pads keep a mask bridge from 8 mil pad spacing | P1, P2 |
| BGA pad | Prototype factory ≥ 0.25 mm, pad-to-trace 0.15 mm; advanced factory ≥ 0.2 mm (0.15 mm sample limit), BGA to line 3 mil (2.5 mil prototype limit) | P10 |
| BGA pad by finish | Immersion gold ≥ 11 mil normal, 8 mil medium | P1 |
| BGA pitch | Advanced factory: 0.4 mm limit, 0.5 mm conventional; prototype factory: 0.35 mm pad centre to centre | P2, P10 |
| Line to board edge (milled) | 0.20 mm | P1 |
| Outline tolerance | ±0.2 mm standard; ±0.1 mm advanced | P1, P2 |
| Surface finishes | HASL, lead-free HASL, ENIG, OSP, hard gold, immersion silver, immersion tin, ENEPIG | P1 |
| ENIG thickness | Ni 100–150 µin, Au 1–8 µin normal | P1 |
| Hard gold (gold finger) | Ni 120–150 µin, Au 1–30 µin normal | P1 |
| Materials | FR-4 Tg 140/150/170 (Shengyi S1141, S1000-H, S1000-2/2M), halogen-free, high-speed classes 1–5 G (for example S1165, FR408HR, TU-862), 5–10 G, 10–25 G, > 25 G; Rogers and PTFE | P2, P16 |
| Silkscreen | Line ≥ 0.15 mm, height ≥ 0.8 mm | P1 |
| Acceptance | IPC Class 2 normal; Class 3 on request | P1, P16 |

### HDI

| Parameter | Value | Source |
|---|---|---|
| Via types | Blind, buried, through | P3 |
| Builds | 1+N+1, 2+N+2 … 6+N+6 (≥ 6 orders reviewed); the roadmap lists 7+N+7 with stacked and staggered vias; any-layer HDI is "high difficulty" | P1, P2, P3 |
| Layers | Up to 60 (reviewed above 30) | P3 |
| Finished copper | 18–70 µm | P3 |
| Minimum track/space | 0.065/0.065 mm | P3 |
| Thickness | 0.1–8.0 mm (reviewed below 0.2 mm) | P3 |
| Laser drill | 4 mil standard; 3 mil reviewed (single 106 prepreg); 8 mil maximum, dielectric ≤ 0.15 mm | P3 |
| Laser hole (roadmap) | 0.076 mm finished | P2 |
| Mechanical drill | 0.15 mm | P3 |
| Aspect ratio | 14:1 maximum | P3 |
| Resin-filled vias | 0.254–6.5 mm | P3 |
| Solder mask bridge | 4 mil green, 5 mil other colours (≤ 1 oz) | P3 |
| Hole filling | Plating line with "HDI hole filling capability" | P3 |
| Published examples | 8 layers, 3rd order, 1.0 ± 0.1 mm, laser 0.1 mm, mechanical 0.20 mm, 55/55 µm, ENIG + OSP; 10 layers, 2nd order, 1.3 mm, 65/65 µm, ENEPIG; 14 layers any-layer (6th order), 1.6 mm, laser 0.15 mm, 75/75 µm | P3 |
| Minimum layer count for HDI | 4 | P17 |

PCBWay does not publish a microvia land size or a microvia aspect ratio for rigid HDI (**UNVERIFIED**). The rigid-flex page gives 1:1 for blind holes [P6].

### Flex (FPC)

| Parameter | Value | Source |
|---|---|---|
| Layers | 1–12 (capability page); 1–16 (order form) | P5, P13 |
| Base | Polyimide (adhesive and adhesiveless), PET, high-frequency SF230 (DK ≤ 3.6) | P5, P13 |
| Thickness without stiffener | 4–40 mil; order steps 0.025–0.34 mm, ≥ 0.35 mm, ≥ 0.4 mm | P5, P13 |
| Standard stack-ups | 2 layers 0.1–0.38 mm; 4 layers 0.2–0.33 mm; 6 layers 0.3–0.42 mm; 8–16 layers 0.45–0.91 mm; air-gap 2/4/6/8 layers 0.16/0.24/0.37/0.5 mm | P14 |
| PI dielectric | 12.5–125 µm; DK 3.5 with adhesive, 3.3 adhesiveless | P14 |
| Thickness tolerance | Single layer ±1.0 mil; two layers (≤ 12 mil) ±1.2 mil; multilayer ≤ 12 mil ±1.2 mil; 12–32 mil ±8 %; with PI stiffener: no value published (**UNVERIFIED**) | P5 |
| Track/space | 2/2 mil inner and outer (page); ≥ 0.06 mm (order form) | P5, P13 |
| Hole / pad | Mechanical 4 mil (page); ≥ 0.15 / 0.35 mm (order form) | P5, P13 |
| Impedance tolerance | ±4 Ω (≤ 50 Ω); ±7 % (> 50 Ω) | P5 |
| Coverlay | Yellow, white, black, transparent; minimum coverlay bridge 8 mil | P5, P13 |
| Solder mask on flex | Green, black | P5 |
| Bend radius | Single layer 3–6 × thickness; two layers 7–10 ×; multilayer 10–15 × | P5 |
| Copper | Finished outer 9–88 µm; inner 12, 18, 35 µm | P13 |
| Stiffeners | PI 0.05–0.25 mm; FR-4 0.2–1.5 mm (0.1 mm unusual); black FR-4 0.2–1.5 mm; stainless steel 0.1–0.5 mm; aluminium 0.2–1.5 mm; top, bottom or both | P13 |
| Tapes | 3M 467, Tesa 8853/8854, 3M 9495LE (3M parts "not for reflow"); conductive tape HT-A1134 | P13 |
| EMI shielding film | HCF-6000G, PC800; top, bottom or both | P13 |
| Other options | Via filled with copper, air-gap FPC, impedance control, edge plating, castellated holes | P13 |
| Finishes | ENIG, ENEPIG (default Ni 200 µin, Pd 2 µin, Au 2 µin), hard gold, immersion silver, immersion tin, OSP, soft gold | P5, P13 |
| Size | Minimum 0.0788 × 0.1576 in; maximum 8.668 × 27.5 in (about 220 × 698 mm) | P5 |
| Routing accuracy | Laser ±2 mil; punching ±2–6 mil | P5 |

### Rigid-flex

| Parameter | Value | Source |
|---|---|---|
| Layers | Up to 26 | P4, P6 |
| Published builds | 1R+2F+1R (0.35 mm), 2R+2F+2R, 4R+2F+4R (1.0 mm), 4R+4F+4R HDI (1.70 mm), (2+1+2F+1+2) HDI 8 layers | P4, P6 |
| Thickness | 0.25–6.0 mm | P6 |
| Track/space | 0.065/0.065 mm; 3 mil standard, 2 mil special | P6 |
| Hole / pad | 0.10 / 0.35 mm; drilled 6 mil standard | P6 |
| Via ring | 6 mil standard, 5 mil special | P6 |
| Aspect ratio | Through 8:1 standard, 10:1 for holes ≥ 0.30 mm; blind 1:1 | P6 |
| Registration | ±3 mil; ±2 mil with LDI | P6 |
| Outline tolerance | ±0.10 mm standard, ±0.05 mm special | P6 |
| Impedance tolerance | ±7.5 % | P6 |
| Copper | Flex part 0.5–2 oz; rigid part 1–4 oz | P6 |
| Finishes | ENIG, electrolytic gold, immersion silver, HASL, immersion tin, OSP, Ni-Pd-Au | P6 |

### Assembly, stencils and parts

| Parameter | Value | Source |
|---|---|---|
| Passives | 01005, 0201, 0402 and up | P8, P9 |
| BGA pitch | 0.3 mm on rigid boards, 0.4 mm on flex, with X-ray [P8]; 0.25 mm [P9]; the BGA page shows "0.25 mm" and "0.3 mm" side by side [P7]. Take 0.3 mm (rigid) and 0.4 mm (flex) as the conservative published figures | P7, P8, P9 |
| BGA types | PBGA, CBGA, micro BGA, fine-pitch BGA, stacked BGA, PoP | P7, P18 |
| Fine pitch | 0.25 mm leaded parts; "small chip packages 0.2 mm pitch" | P8, P18 |
| Sides | Single or double-sided placement; SMT, THT and mixed | P8, P18 |
| Inspection | 3D SPI, AOI, X-ray (100 % X-ray of BGA on samples), flying probe, ICT, functional test | P8, P18, P19 |
| Optional services | Conformal coating, press-fit, box build, cable and harness assembly, firmware loading | P19 |
| Flex and rigid-flex assembly | Offered; limits not published ("contact service") | P8, P19 |
| Board size | 10 × 10 mm minimum [P8] or 50 × 100 mm [P9]; smaller or non-rectangular boards are panelised with rails; rails required when copper is closer than 3.5 mm to the edge | P8, P9, P20 |
| Stencils | Laser-cut stainless steel, framed or frameless; 0.08–0.3 mm (order form), 0.1–0.2 mm (page); step stencil option; electropolishing; nano coating on request | P8, P13, P21 |
| Component packaging | Reels, cut tape, tubes, trays, loose parts | P8 |

### Mechanics and finishes

| Service | Value | Source |
|---|---|---|
| CNC materials | Aluminium 6061-T6/T651, 6063-T5/T6, 6082, 7075-T6/T651, 5052, 2A12; ABS, PC, PMMA, POM, nylon, PEEK and others | P22 |
| CNC tolerances | Parts to 300 mm: ±0.125 mm, angularity ±0.5°; "±0.005–0.01 in depending on specs" | P22 |
| CNC size | 2 mm to 1,000 mm; minimum diameter 0.3 mm | P22 |
| CNC finishes | As-milled (Ra 125 µin), smooth machining (Ra 1.6 µm), bead blast, brushed, anodised, bead blast + anodised colour, hard anodising (Type III), powder coat, plating, PVD, laser engraving, chem film, electropolishing | P22, P23 |
| Anodising colours (aluminium) | Natural, black, grey, gold, rose gold, red, blue, champagne, brown, purple, green, orange | P23 |
| Anodising thickness (sheet metal page) | Type II 8–12 µm clear, 4–8 µm colour; "black, clear or any RAL or Pantone"; Type III for wear | P26 |
| Painting on polymers | Spray painting in any Pantone colour on ABS, PC, PP, nylon, POM, PMMA and others; bead blast also on ABS and PC | P23 |
| SLA | Up to 2100 × 800 × 700 mm; minimum wall 0.8 mm; ±0.2 mm below 100 mm, ±0.2 % above; Ra 3–10 µm; clear resin UTR-8100, polishable | P24 |
| SLS | Nylon 12 and PA12 GF; minimum wall 1 mm; ±0.25 mm below 100 mm; threads and inserts as secondary options | P25 |
| MJF | HP PA12, HP PA12 40 % GF; ±0.25 % of length (100 mm) | P27 |
| SLM (metal) | AlSi10Mg, stainless steel, titanium TC4, tool steel; minimum wall 1 mm; ±0.3 mm below 100 mm | P27, P28 |
| FDM | Includes PC, PC-FR and carbon-filled grades (PA6-CF, PLA-CF, PETG-CF, ASA-CF, PPS-CF) | P27 |
| Vacuum casting | Silicone moulds, two-component polyurethanes; listed materials ABS, POM, nylon, PC, PE, PP, PS, TPU, rubber | P29 |
| Sheet metal | Laser cutting 0.5–10 mm, bending 0.5–6 mm; cut ±0.2 mm, bend ±1.0°, bend to edge ±0.254 mm; aluminium 5052/6061, stainless 301/304/316, copper, brass | P26 |
| Injection moulding | Plastic injection, LSR, overmoulding and insert moulding; PC, ABS, PC-ABS, PMMA, TPE, TPU, LSR and others. Tolerances, minimum wall and texture grades: **UNVERIFIED** (not on the page) | P30 |
| Glass | Not offered on any fetched page | — |

## Constraints the rule sets carry

These follow from the figures above and from the part sheets. They are design-rule facts, not PCBWay statements.

1. **Mask bridge threshold.** Pads closer than 8 mil (0.203 mm) do not keep a solder-mask bridge [P2]: RK809 (0.35 mm), DF40 headers and receptacles, and some 0.4 mm QFNs get one opening per row.
2. **0.4 mm BGA.** Pad ≥ 0.2 mm [P10], ring ≥ 3 mil around a 0.10 mm laser via [P2, P3], hence a 0.25 mm pad when the via sits in the pad. Mask opening 1 mil in the BGA area [P1].
3. **Through-hole aspect ratio** limits a 0.20 mm hole to 1.6 mm of board [P1]; it binds only boards thicker than that.
4. **Coverlay** bridge 8 mil (0.2 mm) on flex [P5]; coverlay opening and copper-to-outline rules on flex are not published (**UNVERIFIED**), so the flex rule set keeps the rigid 0.20 mm edge clearance until PCBWay's DFM answers.
5. **Flex bends** at 10–15 × thickness for multilayer [P5]; stiffened areas (connectors) must not bend.

## Sources

All pages fetched on 2026-10-22.

| Key | Page |
|---|---|
| P1 | PCB Capabilities (standard and advanced tables): <https://www.pcbway.com/capabilities.html> |
| P2 | Advanced PCB Capabilities: <https://www.pcbway.com/advanced-pcb-capabilities.html> |
| P3 | HDI PCB: <https://www.pcbway.com/hdi-pcb.html> |
| P4 | Flex and rigid-flex overview: <https://www.pcbway.com/fpc-rigid-flex-pcb.html> |
| P5 | Flexible PCB: <https://www.pcbway.com/fpc-rigid-flex-pcb/flex-pcb.html> |
| P6 | Rigid-flex PCB: <https://www.pcbway.com/fpc-rigid-flex-pcb/rigid-flex-pcb.html> |
| P7 | BGA Assembly Capabilities: <https://www.pcbway.com/pcb_prototype/BGA_Assembly_Capabilities.html> |
| P8 | Assembly capabilities: <https://www.pcbway.com/assembly-capabilities.html> |
| P9 | PCB assembly capabilities: <https://www.pcbway.com/pcb_prototype/PCB_assembly_Capabilities.html> |
| P10 | PCB BGA (fab capability): <https://www.pcbway.com/pcb_prototype/PCB_BGA.html> |
| P11 | Via-in-Pad: <https://www.pcbway.com/pcb_prototype/PCB_Via_in_Pad.html> |
| P12 | Impedance Control: <https://www.pcbway.com/pcb_prototype/Impedance_Control.html> |
| P13 | FPC order form (options and stencil): <https://www.pcbway.com/flexible.aspx> |
| P14 | Stack-up for FPC: <https://www.pcbway.com/pcb_prototype/Stack_up_for_FPC.html> |
| P15 | PCB Assembly: <https://www.pcbway.com/pcb-assembly.html> |
| P16 | Advanced PCB order form (options): <https://www.pcbway.com/HighQualityOrderOnline.aspx> |
| P17 | Assembly order form, PCB section (track/space options, HDI from 4 layers): <https://www.pcbway.com/quotesmt.aspx> |
| P18 | SMT Assembly Capabilities: <https://www.pcbway.com/pcb_prototype/SMT_Assembly_Capabilities.html> |
| P19 | Assembly order form, assembly options: <https://www.pcbway.com/quotesmt.aspx> |
| P20 | PCB Assembly Special Reminders: <https://www.pcbway.com/assembly-special-remind.html> |
| P21 | SMT stencil: <https://www.pcbway.com/pcb_prototype/SMT_stencil_and_Laser_Stencil.html> |
| P22 | CNC machining: <https://www.pcbway.com/rapid-prototyping/cnc-machining/> |
| P23 | Surface finishing: <https://www.pcbway.com/rapid-prototyping/Surface-Finishing.html> |
| P24 | SLA: <https://www.pcbway.com/rapid-prototyping/3D-Printing/3D-Printing-SLA.html> |
| P25 | SLS: <https://www.pcbway.com/rapid-prototyping/3D-Printing/3D-Printing-SLS.html> |
| P26 | Sheet metal: <https://www.pcbway.com/rapid-prototyping/sheet-metal/> |
| P27 | 3D printing overview (tolerances, materials): <https://www.pcbway.com/rapid-prototyping/3d-printing/> |
| P28 | SLM: <https://www.pcbway.com/rapid-prototyping/3D-Printing/3D-Printing-SLM.html> |
| P29 | Vacuum casting: <https://www.pcbway.com/rapid-prototyping/3D-Printing/3D-Printing-VC.html> |
| P30 | Injection moulding: <https://www.pcbway.com/rapid-prototyping/injection-molding/> |
