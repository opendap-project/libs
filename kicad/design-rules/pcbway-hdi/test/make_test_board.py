"""Build test/pcbway-hdi-test.kicad_pcb: one failing and one passing object per rule.

Run with KiCad's Python, from any directory:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      design-rules/pcbway-hdi/test/make_test_board.py
Then check it with design-rules/tools/check_drc.py.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))

import pcbnew  # noqa: E402
from testboard import MIL, TEST_BOARD_IGNORED_CHECKS, TestBoard  # noqa: E402

NAME = "pcbway-hdi-test"
P = "PCBWay HDI: "

# Board Setup values KiCad checks outside the rules file (see README.md):
# solder-mask opening >= 2 mil normal [P1]; mask bridge 4 mil, green, <= 1 oz [P3].
MASK_EXPANSION = 0.05
MASK_MIN_WEB = 4 * MIL


def main():
    tb = TestBoard(NAME, os.path.join(HERE, NAME + ".kicad_dru"), copper_layers=6,
                   mask_expansion=MASK_EXPANSION, mask_min_web=MASK_MIN_WEB)
    w = tb.rule(P + "Track width (outer)").value("track_width") + 0.02
    wi = tb.rule(P + "Track width (inner)").value("track_width") + 0.02
    micro = (pcbnew.VIATYPE_MICROVIA, (pcbnew.F_Cu, pcbnew.In1_Cu))
    mech_ring = tb.rule(P + "Mechanical via annular ring").value("annular_width") + 0.02
    micro_ring = tb.rule(P + "Laser microvia annular ring").value("annular_width") + 0.02

    tb.track_clearance(P + "Copper clearance (outer)", pcbnew.F_Cu, w)
    tb.track_clearance(P + "Copper clearance (inner)", pcbnew.In1_Cu, wi)
    tb.bga_pad_to_track(P + "BGA pad to track", pad=0.3, width=w)
    tb.track_width(P + "Track width (outer)", pcbnew.F_Cu)
    tb.track_width(P + "Track width (inner)", pcbnew.In1_Cu)
    tb.bga_pad_size(P + "BGA pad size", limit=0.25)
    tb.via_drill(P + "Mechanical drill", ring=mech_ring)
    tb.via_drill(P + "Laser microvia drill", ring=micro_ring, vtype=micro[0], layers=micro[1])
    tb.via_ring(P + "Laser microvia annular ring", drill=0.1, vtype=micro[0], layers=micro[1])
    tb.via_ring(P + "Mechanical via annular ring", drill=0.25)
    tb.via_hole_to_hole(P + "Via hole to hole", drill=0.25, diameter=0.25 + 2 * mech_ring)
    tb.hole_to_copper(P + "Hole to copper (outer)", pcbnew.F_Cu, hole=0.6, width=w)
    tb.hole_to_copper(P + "Hole to copper (inner)", pcbnew.In1_Cu, hole=0.6, width=wi)
    tb.edge_clearance(P + "Copper to board edge", width=w)
    tb.silk_thickness(P + "Silkscreen line width", height=1.0)
    tb.silk_height(P + "Silkscreen text height", thickness=0.15)
    tb.mask_web("Board Setup: solder mask minimum web (4 mil)", pad=0.3)

    print(tb.save(HERE, ignore_checks=TEST_BOARD_IGNORED_CHECKS))


if __name__ == "__main__":
    main()
