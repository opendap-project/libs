"""Build test/opendap-craft-test.kicad_pcb: one failing and one passing object per rule.

Run with KiCad's Python, from any directory:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      design-rules/opendap-craft/test/make_test_board.py
Then check it with design-rules/tools/check_drc.py.

The craft rules are closed sets and geometry, not single limits, so most rows
are drawn here rather than by a shared fixture: the failing object breaks
only its own rule, the passing one is the nearest value the set allows. Two
extra rows hold objects that would fail but are exempt (a Z* net class, a
CRAFT-EXEMPT rule area); they must raise nothing.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))

import pcbnew  # noqa: E402
from testboard import TEST_BOARD_IGNORED_CHECKS, TestBoard  # noqa: E402

NAME = "opendap-craft-test"
P = "OpenDAP "
F_SILK, B_SILK, F_CU = pcbnew.F_SilkS, pcbnew.B_SilkS, pcbnew.F_Cu
W = 0.2  # a track width from the CRAFT-43 series
LINE = 0.15  # the CRAFT-05 silk stroke
# Distance from a 1.0 x 0.15 mm centred text's position to the outer edge of
# its glyphs, below "AB", about as kicad-cli 10.0.7 measures it in DRC. DRC measures text through a polygon approximation whose result
# moves by up to about 0.08 mm with the text's position, so text rows sit
# 0.10 mm inside (FAIL) and 0.25 mm outside (PASS) their limit rather than
# 0.01 mm.
GLYPH_BOTTOM = 0.3393
TEXT_FAIL, TEXT_PASS = -0.10, 0.25


def main():
    tb = TestBoard(NAME, os.path.join(HERE, NAME + ".kicad_dru"), copper_layers=4)
    tb.add_net_class("TEST_90D", "Z*")
    tb.add_net_class("BAT_SENSE", "S*")

    def rule(rid, part=""):
        names = [n for n in tb.rules if n.startswith(P + rid + " ") and part in n]
        if len(names) != 1:
            raise KeyError(f"{rid} {part}: {names}")
        return names[0]

    # --- Silkscreen -------------------------------------------------------
    def font(x, y, fail):
        tb._text(x, y, F_SILK, 1.0, 0.15, italic=fail)
    tb.add_row(rule("CRAFT-01"), font, rule("CRAFT-01"))

    def size(x, y, fail):
        if fail:
            tb._text(x, y, F_SILK, 1.2, 0.18)
        else:
            tb._text(x, y, F_SILK, 1.6, 0.24)
    tb.add_row(rule("CRAFT-02"), size, rule("CRAFT-02"))

    def angle(x, y, fail):
        tb._text(x + 1, y, F_SILK, 1.0, 0.15, angle=45 if fail else 90)
    tb.add_row(rule("CRAFT-03"), angle, rule("CRAFT-03"))

    def side(x, y, fail):
        # failing: mirrored on top; passing: mirrored on the bottom
        tb._text(x + 2, y, F_SILK if fail else B_SILK, 1.0, 0.15, mirrored=True)
    # KiCad's own mirrored_text_on_front_layer check fires on the same text.
    tb.add_row(rule("CRAFT-04"), side, rule("CRAFT-04"), "mirrored_text_on_front_layer")

    def line(x, y, fail):
        tb._silk_line(x, y, x + 3, y, 0.12 if fail else LINE)
    tb.add_row(rule("CRAFT-05"), line, rule("CRAFT-05"))

    gap = 0.15

    def to_pad(x, y, fail):
        fp = tb._footprint(x, y, pcbnew.FP_SMD)
        tb._pad(fp, x, y, 1.0)
        ly = y + 0.5 + (gap - 0.01 if fail else gap + 0.01) + LINE / 2
        tb._silk_line(x - 1, ly, x + 2, ly, LINE)
    tb.add_row(rule("CRAFT-07", "pads"), to_pad, rule("CRAFT-07", "pads"))

    def to_via(x, y, fail):
        # KiCad measures silk to the via hole (0.2 mm drill)
        limit = 0.3
        ly = y + 0.1 + (limit - 0.01 if fail else limit + 0.01) + LINE / 2
        tb._via(x, y, 0.2, 0.46)
        tb._silk_line(x - 1, ly, x + 2, ly, LINE)
    tb.add_row(rule("CRAFT-07", "vias"), to_via, rule("CRAFT-07", "vias"))

    def text_to_silk(x, y, fail):
        tb._text(x, y, F_SILK, 1.0, 0.15, text="AB")
        ly = y + GLYPH_BOTTOM + gap + (TEXT_FAIL if fail else TEXT_PASS) + LINE / 2
        tb._silk_line(x, ly, x + 3, ly, LINE)
    tb.add_row(rule("CRAFT-09"), text_to_silk, rule("CRAFT-09"))

    # --- Routing ----------------------------------------------------------
    def geometry(x, y, fail):
        if fail:
            tb._track(x, y, x + 3, y + 1.5, W, F_CU)  # about 26.6 degrees
        else:
            tb._track(x, y, x + 1.5, y + 1.5, W, F_CU)
    tb.add_row(rule("CRAFT-40"), geometry, rule("CRAFT-40"))

    def corner(x, y, fail):
        net = tb._net()
        tb._track(x, y, x + 2, y, W, F_CU, net)
        if fail:
            tb._track(x + 2, y, x + 2, y + 1.5, W, F_CU, net)  # 90 degrees
        else:
            tb._track(x + 2, y, x + 3.5, y + 1.5, W, F_CU, net)  # 135 degrees
    # KiCad reports a corner once for each of its two segments.
    tb.add_row(rule("CRAFT-41"), corner, rule("CRAFT-41"), count=2)

    def width(x, y, fail):
        tb._track(x, y, x + 3, y, 0.12 if fail else 0.15, F_CU)
    tb.add_row(rule("CRAFT-43"), width, rule("CRAFT-43"))

    def via(x, y, fail):
        tb._via(x + 1, y, 0.2, 0.45 if fail else 0.46)
    tb.add_row(rule("CRAFT-45"), via, rule("CRAFT-45"))

    def jog(x, y, fail):
        tb._track(x, y, x + (0.09 if fail else 0.11), y, W, F_CU)
    tb.add_row(rule("CRAFT-47"), jog, rule("CRAFT-47"))

    # --- Exemptions: would fail CRAFT-40, -41, -43 and -47; must raise nothing
    def odd_copper(x, y, net):
        tb._track(x, y, x + 3, y + 1.5, 0.12, F_CU, net)
        tb._track(x + 3, y + 1.5, x + 3.05, y + 1.5, 0.12, F_CU, net)
        tb._track(x + 3.05, y + 1.5, x + 3.05, y - 0.5, 0.12, F_CU, net)

    def exempt_class(x, y, fail):
        if fail:
            odd_copper(x, y, tb._net("Z"))
    tb.add_row("Exempt: impedance class *_90D (CRAFT-40, -43; corner and jog are not)",
           exempt_class, rule("CRAFT-41"), count=2)
    tb.expected_rules[rule("CRAFT-47")] += 1

    def sense_class(x, y, fail):
        if fail:
            odd_copper(x, y, tb._net("S"))
    tb.add_row("Not exempt: class BAT_SENSE ends in SE but is not an impedance class",
           sense_class, rule("CRAFT-43"), count=3)
    tb.expected_rules[rule("CRAFT-40")] += 1
    tb.expected_rules[rule("CRAFT-41")] += 2
    tb.expected_rules[rule("CRAFT-47")] += 1

    def exempt_area(x, y, fail):
        if fail:
            tb._rule_area("BGA_ESCAPE", x - 0.5, y - 1.0, x + 3.6, y + 2.0)
            odd_copper(x, y, tb._net())
    tb.add_row("Exempt: rule area BGA_ESCAPE (CRAFT-40, -41, -43, -47)", exempt_area)

    print(tb.save(HERE, ignore_checks=TEST_BOARD_IGNORED_CHECKS))


if __name__ == "__main__":
    main()
