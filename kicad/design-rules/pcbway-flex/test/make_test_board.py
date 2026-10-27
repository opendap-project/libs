"""Build test/pcbway-flex-test.kicad_pcb: one failing and one passing object per rule.

Run with KiCad's Python, from any directory:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      design-rules/pcbway-flex/test/make_test_board.py
Then check it with design-rules/tools/check_drc.py.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))

import pcbnew  # noqa: E402
from testboard import MIL, TEST_BOARD_IGNORED_CHECKS, TestBoard  # noqa: E402

NAME = "pcbway-flex-test"
P = "PCBWay flex: "

# Board Setup value KiCad checks outside the rules file (see README.md): the
# coverlay is drawn on the solder-mask layers; minimum coverlay bridge 8 mil
# [P5]. PCBWay publishes no coverlay opening (expansion), so the test board
# uses none.
MASK_EXPANSION = 0.0
MASK_MIN_WEB = 8 * MIL


def main():
    tb = TestBoard(NAME, os.path.join(HERE, NAME + ".kicad_dru"), copper_layers=2,
                   mask_expansion=MASK_EXPANSION, mask_min_web=MASK_MIN_WEB)
    w = tb.rule(P + "Track width").value("track_width") + 0.02
    drill = tb.rule(P + "Drill").value("hole_size") + 0.02
    dia = tb.rule(P + "Via pad diameter").value("via_diameter") + 0.02

    tb.track_clearance(P + "Copper clearance", pcbnew.F_Cu, w)
    tb.track_width(P + "Track width", pcbnew.F_Cu)
    tb.via_drill(P + "Drill", ring=dia / 2)
    tb.via_diameter(P + "Via pad diameter", drill=drill)
    tb.pad_size_pth(P + "Plated hole pad size", limit=0.35, drill=drill)
    tb.edge_clearance(P + "Copper to outline (UNVERIFIED)", width=w)
    tb.mask_web("Board Setup: coverlay minimum bridge (8 mil)", pad=0.3)

    print(tb.save(HERE, ignore_checks=TEST_BOARD_IGNORED_CHECKS))


if __name__ == "__main__":
    main()
