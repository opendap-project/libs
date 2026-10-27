#!/usr/bin/env python3
"""Generate kicad-lib's generic symbols: parts that are not one orderable MPN, drawn to the craft
standard where KiCad's stock symbol fails it.

Usage:
    python3 generator/generic.py [--check]        (Python 3.11 or later)

Writes symbols/opendap-generic.kicad_sym. The symbols carry no footprint, MPN or datasheet: the
schematic fills them per placement, as with KiCad's Device library (KLC S5.1, generic symbol).

    Crystal         quartz crystal, 2 pins
    Crystal_GND24   quartz crystal in a 4-pad package: 1 and 3 the crystal, 2 and 4 the case
                    (the pad numbering of KiCad's Crystal_SMD_*-4Pin footprints)
    Thermistor_NTC  NTC thermistor, 2 pins, vertical

Why not KiCad's own: Device:Crystal puts its pins at x = +/-3.81 mm, off the 2.54 mm grid
(CRAFT-122), and Device:Crystal_GND24 also stacks the case pads 2 and 4 on one hidden pin
(CRAFT-125). Here every pin is visible and ends on the 2.54 mm grid; the pin length is 2.54 mm
(CRAFT-121), the reference prefix Y (CRAFT-130), the body 0.254 mm with a background fill
(CRAFT-128), text 1.27 mm (CRAFT-129). Device:Thermistor_NTC carries the reference prefix TH,
outside the KLC S6.1 set the craft check holds (CRAFT-130); here it is RT, drawn as IEC 60617
(S00620): a resistor body crossed by a slanted line with a foot, marked -t°.

--check regenerates in memory and exits 1 if the committed file differs.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kigen import GENERATOR, PIN_LEN, ROOT, S, SYM_VERSION, Sym, dump, num  # noqa: E402

LIBRARY = "opendap-generic"
PATH = os.path.join(ROOT, "symbols", LIBRARY + ".kicad_sym")
BODY_W = 0.254   # CRAFT-128
LEAD_W = 0       # KiCad default line width for the leads and the case outline


def font():
    return S("effects", S("font", S("size", 1.27, 1.27)))


def prop(k, v, at, hide=True, left=False):
    eff = font()
    if left:
        eff.append(S("justify", Sym("left")))
    return S("property", k, v, S("at", num(at[0]), num(at[1]), 0),
             *([S("hide", Sym("yes"))] if hide else []), eff)


def line(pts, width, style="default"):
    return S("polyline", S("pts", *[S("xy", num(x), num(y)) for x, y in pts]),
             S("stroke", S("width", width), S("type", Sym(style))), S("fill", S("type", Sym("none"))))


def pin(number, x, y, angle):
    return S("pin", Sym("passive"), Sym("line"), S("at", num(x), num(y), angle), S("length", num(PIN_LEN)),
             S("name", number, font()), S("number", number, font()))


def crystal(name, case):
    """Pins 1 and 2 (or 1 and 3 with case pads) at x = -/+5.08; case pads 2 and 4 at the bottom,
    x = -/+2.54, y = -5.08. Body: the IEC 60617 crystal, a resonator between two plates."""
    value_y = -7.62 if case else -5.08
    # pin numbers shown on the 4-pad form, where they tell the crystal pads from the case pads
    n = S("symbol", name, *([] if case else [S("pin_numbers", S("hide", Sym("yes")))]),
          S("pin_names", S("offset", 1.016), S("hide", Sym("yes"))),
          S("exclude_from_sim", Sym("no")), S("in_bom", Sym("yes")), S("on_board", Sym("yes")),
          prop("Reference", "Y", (0, 5.08), False),
          prop("Value", name, (0, value_y), False),
          prop("Footprint", "", (0, 0)),
          prop("Datasheet", "~", (0, 0)),
          prop("Description", "Quartz crystal" + (", case pads 2 and 4 (to ground)" if case else "")
               + "; pins on the 2.54 mm grid, none hidden", (0, 0)),
          prop("ki_keywords", "quartz crystal resonator", (0, 0)),
          prop("ki_fp_filters", "Crystal*", (0, 0)))
    g = S("symbol", name + "_0_1",
          S("rectangle", S("start", num(-1.016), num(2.032)), S("end", num(1.016), num(-2.032)),
            S("stroke", S("width", BODY_W), S("type", Sym("default"))), S("fill", S("type", Sym("background")))),
          line([(-2.032, 1.524), (-2.032, -1.524)], BODY_W),
          line([(2.032, 1.524), (2.032, -1.524)], BODY_W),
          line([(-2.54, 0), (-2.032, 0)], LEAD_W),
          line([(2.54, 0), (2.032, 0)], LEAD_W))
    if case:  # the case, drawn as KiCad does: a dashed outline joining the two case pads
        g.append(line([(-2.54, -2.54), (-2.54, -3.048), (2.54, -3.048), (2.54, -2.54)], LEAD_W, "dash"))
    n.append(g)
    pins = S("symbol", name + "_1_1", pin("1", -5.08, 0, 0), pin("3" if case else "2", 5.08, 0, 180))
    if case:
        pins += [pin("2", -2.54, -5.08, 90), pin("4", 2.54, -5.08, 90)]
    n.append(pins)
    n.append(S("embedded_fonts", Sym("no")))
    return n


def thermistor(name):
    """Pins 1 (top) and 2 (bottom) at y = +/-5.08, 2.54 mm long; body 2.032 x 5.08 mm."""
    n = S("symbol", name, S("pin_numbers", S("hide", Sym("yes"))),
          S("pin_names", S("offset", 0), S("hide", Sym("yes"))),
          S("exclude_from_sim", Sym("no")), S("in_bom", Sym("yes")), S("on_board", Sym("yes")),
          prop("Reference", "RT", (3.048, 1.27), False, True),
          prop("Value", name, (3.048, -1.27), False, True),
          prop("Footprint", "", (0, 0)),
          prop("Datasheet", "~", (0, 0)),
          prop("Description", "NTC thermistor; reference prefix RT (KLC S6.1), pins on the grid, none hidden",
               (0, 0)),
          prop("ki_keywords", "thermistor NTC resistor temperature sensor", (0, 0)),
          prop("ki_fp_filters", "R_*", (0, 0)))
    g = S("symbol", name + "_0_1",
          S("rectangle", S("start", num(-1.016), num(2.54)), S("end", num(1.016), num(-2.54)),
            S("stroke", S("width", BODY_W), S("type", Sym("default"))), S("fill", S("type", Sym("background")))),
          line([(-2.54, -2.286), (-1.778, -2.286), (1.778, 2.286)], LEAD_W),
          S("text", "-t°", S("at", num(-3.302), num(1.27), 0), font()))
    n.append(g)
    n.append(S("symbol", name + "_1_1", pin("1", 0, 5.08, 270), pin("2", 0, -5.08, 90)))
    n.append(S("embedded_fonts", Sym("no")))
    return n


def library():
    n = S("kicad_symbol_lib", S("version", Sym(SYM_VERSION)), S("generator", GENERATOR),
          S("generator_version", "10.0"))
    n.append(crystal("Crystal", False))
    n.append(crystal("Crystal_GND24", True))
    n.append(thermistor("Thermistor_NTC"))
    return dump(n) + "\n"


def main(argv):
    text = library()
    if "--check" in argv:
        with open(PATH) as fh:
            if fh.read() != text:
                print("out of date: " + os.path.relpath(PATH, ROOT))
                return 1
        return 0
    with open(PATH, "w") as fh:
        fh.write(text)
    print(os.path.relpath(PATH, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
