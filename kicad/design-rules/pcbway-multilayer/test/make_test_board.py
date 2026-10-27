"""Build the pcbway-multilayer test boards: one failing and one passing object per rule.

One board per rules file: test/pcbway-multilayer-test.kicad_pcb (18 um base
copper) and test/pcbway-multilayer-35um-test.kicad_pcb (35 um base copper).

Run with KiCad's Python, from any directory:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      design-rules/pcbway-multilayer/test/make_test_board.py
Then check them with design-rules/tools/check_drc.py.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))

import pcbnew  # noqa: E402
from testboard import MIL, TEST_BOARD_IGNORED_CHECKS, TestBoard  # noqa: E402

VARIANTS = (
    ("pcbway-multilayer-test", "PCBWay multilayer: "),
    ("pcbway-multilayer-35um-test", "PCBWay multilayer 35um: "),
)

# Board Setup values KiCad checks outside the rules file (see README.md):
# solder-mask opening >= 2 mil normal [P1]; mask bridge 4 mil, green, 1 oz [P1].
MASK_EXPANSION = 0.05
MASK_MIN_WEB = 4 * MIL


def build(name, p):
    tb = TestBoard(name, os.path.join(HERE, name + ".kicad_dru"), copper_layers=4,
                   mask_expansion=MASK_EXPANSION, mask_min_web=MASK_MIN_WEB)
    w = tb.rule(p + "Track width (outer)").value("track_width") + 0.02
    wi = tb.rule(p + "Track width (inner)").value("track_width") + 0.02
    ring = tb.rule(p + "Via annular ring").value("annular_width") + 0.02

    tb.track_clearance(p + "Copper clearance (outer)", pcbnew.F_Cu, w)
    tb.track_clearance(p + "Copper clearance (inner)", pcbnew.In1_Cu, wi)
    tb.track_width(p + "Track width (outer)", pcbnew.F_Cu)
    tb.track_width(p + "Track width (inner)", pcbnew.In1_Cu)
    tb.disallowed_via(p + "Through vias only", pcbnew.VIATYPE_MICROVIA,
                      (pcbnew.F_Cu, pcbnew.In1_Cu), drill=0.25, diameter=0.25 + 2 * ring)
    tb.via_drill(p + "Mechanical drill", ring=ring)
    tb.via_ring(p + "Via annular ring", drill=0.25)
    tb.via_hole_to_hole(p + "Via hole to hole", drill=0.25, diameter=0.25 + 2 * ring)
    tb.hole_to_copper(p + "Hole to copper (outer)", pcbnew.F_Cu, hole=0.6, width=w)
    tb.hole_to_copper(p + "Hole to copper (inner)", pcbnew.In1_Cu, hole=0.6, width=wi)
    tb.edge_clearance(p + "Copper to board edge", width=w)
    tb.silk_thickness(p + "Silkscreen line width", height=1.0)
    tb.silk_height(p + "Silkscreen text height", thickness=0.15)
    tb.mask_web("Board Setup: solder mask minimum web (4 mil)", pad=0.3)
    print(tb.save(HERE, ignore_checks=TEST_BOARD_IGNORED_CHECKS))


def main():
    for name, prefix in VARIANTS:
        build(name, prefix)


if __name__ == "__main__":
    main()
