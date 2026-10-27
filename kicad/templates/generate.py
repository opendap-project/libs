#!/usr/bin/env python3
"""Generate the OpenDAP schematic templates and the example block from one source.

Writes, relative to the repository root:

- drawing-sheets/opendap.kicad_wks       the drawing sheet (A4 and A3: every item is anchored to
                                         a page corner, so one file serves both sizes)
- templates/feature-block/feature-block.kicad_sch   the sheet template for one feature block
- examples/load-switch/                  a complete example project that passes every check of
                                         `odapkit craft check` (toolkit-hardware)

Run from anywhere with Python 3.9 or later: python3 templates/generate.py
Then normalise the files with KiCad's own writer: the script calls `kicad-cli sch upgrade --force`
on every schematic it writes when kicad-cli is found ($KICAD_CLI, KiCad.app, or the PATH).

Standard: docs/specs/pcb-craft-standard.md, section 9. The example's part data (manufacturer part
numbers, data sheet links) is illustrative and was not checked against stock.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KICAD_APP = os.environ.get("KICAD_APP", "/Applications/KiCad/KiCad.app")
STOCK = os.path.join(KICAD_APP, "Contents", "SharedSupport", "symbols")
NS = uuid.UUID("6f0b2d3e-8a51-4d0e-9a39-0d1f0e0da0a1")
DATE = "2026-10-24"
REV = "A"
HOLDER = "The OpenDAP Project"
G = 1.27  # the 50 mil grid


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(map(str, parts))))


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def n(v):
    v = round(float(v), 4)
    return f"{v:g}" if v != int(v) else str(int(v))


def eff(size=1.27, hide=False, justify=None, bold=False):
    font = f"(font (size {n(size)} {n(size)}){' (bold yes)' if bold else ''})"
    j = f" (justify {justify})" if justify else ""
    return f"(effects {font}{j})" + (" (hide yes)" if hide else "")


# ---------------------------------------------------------------- drawing sheet

# The title block's Variant: KiCad 10's ${VARIANT} names the design variant a plot was made for and is
# empty for the base design (KiCad's default variant, which cannot be renamed). A project names its
# base design in the text variable OPENDAP_BASE_VARIANT ("full", CRAFT-147); the expression shows it
# when ${VARIANT} is empty, and shows nothing if the project does not define it (an undefined
# variable stays "${...}", whose part before "$" is empty). A project text variable named VARIANT
# does not work: KiCad resolves its own first (kicad-cli 10.0.7, 2026-10-26).
VARIANT_TEXT = '@{if("${VARIANT}" == "", beforefirst("${OPENDAP_BASE_VARIANT}", "$"), "${VARIANT}")}'


def drawing_sheet():
    """The OpenDAP drawing sheet: frame with zone references and the title block.

    Coordinates: KiCad's drawing-sheet editor measures from the corner named in each item
    (rbcorner by default: x to the left, y upward). Text sizes 1.0 / 1.5 / 2.5 mm, lines 0.15 mm,
    the frame 0.25 mm: a closed set (CRAFT-102).
    """
    W, H = 130.0, 32.0  # title block
    L = []
    a = L.append
    a("(kicad_wks (version 20231118) (generator \"opendap-templates\")")
    a("  (setup (textsize 1.5 1.5) (linewidth 0.15) (textlinewidth 0.15)")
    a("    (left_margin 10) (right_margin 10) (top_margin 10) (bottom_margin 10))")
    # frame: outer border, inner border 4 mm in; zone references between them (IEC 61082-1, ISO 5457)
    a("  (rect (name \"frame\") (start 0 0 ltcorner) (end 0 0 rbcorner) (linewidth 0.25))")
    a("  (rect (name \"frame-inner\") (start 4 4 ltcorner) (end 4 4 rbcorner) (linewidth 0.15))")
    for corner_t, corner_b in (("ltcorner", "lbcorner"),):
        a(f"  (line (name \"zone-col-top\") (start 50 0 {corner_t}) (end 50 4 {corner_t}) (repeat 30) (incrx 50))")
        a(f"  (line (name \"zone-col-bottom\") (start 50 0 {corner_b}) (end 50 4 {corner_b}) (repeat 30) (incrx 50))")
        a(f"  (tbtext \"1\" (name \"zone-num-top\") (pos 25 2 {corner_t}) (font (size 1.5 1.5)) (justify center) (repeat 30) (incrx 50))")
        a(f"  (tbtext \"1\" (name \"zone-num-bottom\") (pos 25 2 {corner_b}) (font (size 1.5 1.5)) (justify center) (repeat 30) (incrx 50))")
    a("  (line (name \"zone-row-left\") (start 0 50 ltcorner) (end 4 50 ltcorner) (repeat 30) (incry 50))")
    a("  (line (name \"zone-row-right\") (start 0 50 rtcorner) (end 4 50 rtcorner) (repeat 30) (incry 50))")
    a("  (tbtext \"A\" (name \"zone-letter-left\") (pos 2 25 ltcorner) (font (size 1.5 1.5)) (justify center) (repeat 30) (incry 50))")
    a("  (tbtext \"A\" (name \"zone-letter-right\") (pos 2 25 rtcorner) (font (size 1.5 1.5)) (justify center) (repeat 30) (incry 50))")
    # title block, anchored at the inner frame's bottom-right corner (rbcorner, offset 4 mm)
    o = 4.0
    x0, x1 = o, o + W

    def line(xa, ya, xb, yb, name):
        a(f"  (line (name \"{name}\") (start {n(xa)} {n(ya)}) (end {n(xb)} {n(yb)}) (linewidth 0.15))")

    def label(x, y, text, name):
        a(f"  (tbtext {q(text)} (name \"{name}\") (pos {n(x)} {n(y)}) (font (size 1 1)) (justify left))")

    def value(x, y, text, name, size=1.5, bold=False, maxlen=None):
        b = " bold" if bold else ""
        ml = f" (maxlen {n(maxlen)})" if maxlen else ""
        a(f"  (tbtext {q(text)} (name \"{name}\") (pos {n(x)} {n(y)}) (font{b} (size {n(size)} {n(size)})) (justify left){ml})")

    a(f"  (rect (name \"title-block\") (start {n(x1)} {n(o + H)}) (end {n(x0)} {n(o)}) (linewidth 0.25))")
    # rows from the bottom: 0-6 holder/licence/source, 6-13 project/variant/rev/date/sheet,
    # 13-20 purpose, 20-32 title and block
    for y in (6, 13, 20):
        line(x1, o + y, x0, o + y, f"tb-row-{y}")
    pad = 1.6
    # row 4: title (left), block (right)
    blk_w = 38.0
    line(x0 + blk_w, o + H, x0 + blk_w, o + 20, "tb-col-block")
    label(x1 - pad, o + H - 2.0, "Title", "tb-l-title")
    value(x1 - pad, o + 24.5, "${TITLE}", "tb-title", size=2.5, bold=True, maxlen=W - blk_w - 2 * pad)
    label(x0 + blk_w - pad, o + H - 2.0, "Block", "tb-l-block")
    value(x0 + blk_w - pad, o + 24.5, "${COMMENT1}", "tb-block", maxlen=blk_w - 2 * pad)
    # row 3: purpose
    label(x1 - pad, o + 18.2, "Purpose", "tb-l-purpose")
    value(x1 - pad, o + 15.0, "${COMMENT2}", "tb-purpose", maxlen=W - 2 * pad)
    # row 2: project and board | variant | revision | date | sheet
    cols = [(x1, "Project, board", "${OPENDAP_PROJECT}, ${OPENDAP_BOARD}", 44.0),
            (x1 - 44.0, "Variant", VARIANT_TEXT, 24.0),
            (x1 - 68.0, "Rev", "${REVISION}", 12.0),
            (x1 - 80.0, "Date", "${ISSUE_DATE}", 24.0),
            (x1 - 104.0, "Sheet", "${#} / ${##}", 26.0)]
    for i, (xr, lab, val, w) in enumerate(cols):
        if i:
            line(xr, o + 13, xr, o + 6, f"tb-col-{i}")
        label(xr - pad, o + 11.2, lab, f"tb-l-{i}")
        value(xr - pad, o + 8.0, val, f"tb-v-{i}", maxlen=w - 2 * pad)
    # row 1: holder, licence, source; sheet path at the right
    value(x1 - pad, o + 3.0, "© ${COMPANY} · ${OPENDAP_LICENCE} · ${OPENDAP_SOURCE}", "tb-terms", size=1.0,
          maxlen=W - 40.0)
    a(f"  (tbtext \"${{SHEETPATH}}\" (name \"tb-path\") (pos {n(x0 + pad)} {n(o + 3.0)}) (font (size 1 1)) (justify right) (maxlen 36))")
    a(")")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- library symbols

def stock(lib, name):
    """A symbol from KiCad's installed library, as text, renamed to lib:name for embedding."""
    path = os.path.join(STOCK, lib + ".kicad_sym")
    with open(path, encoding="utf-8") as fh:
        t = fh.read()
    i = t.find(f'\t(symbol "{name}"\n')
    if i < 0:
        raise SystemExit(f"generate: {lib}:{name} not found in {STOCK}")
    depth = 0
    for j in range(i + 1, len(t)):
        if t[j] == "(":
            depth += 1
        elif t[j] == ")":
            depth -= 1
            if depth == 0:
                body = t[i + 1:j + 1]
                return body.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
    raise SystemExit("generate: unbalanced library file")


def pin(kind, x, y, angle, name, number, length=2.54):
    return (f"(pin {kind} line (at {n(x)} {n(y)} {angle}) (length {n(length)}) "
            f"(name {q(name)} {eff()}) (number {q(number)} {eff()}))")


def example_switch_symbol(prefix=""):
    """TPS22919 load switch, drawn to the OpenDAP rules: no hidden pins (the NC pin is visible and
    takes a no-connect flag), supply in at the left as a converter (KLC S4.2 exception), output at
    the right, ground at the bottom, 2.54 mm pins on the 2.54 mm grid, 0.254 mm body, background fill."""
    name = f"{prefix}TPS22919DCK"
    short = "TPS22919DCK"
    props = [
        ("Reference", "U", (-7.62, 7.62), False, "left"),
        ("Value", "TPS22919DCK", (7.62, 7.62), False, "right"),
        ("Footprint", "Package_TO_SOT_SMD:SOT-363_SC-70-6", (0, -12.7), True, None),
        ("Datasheet", "https://www.ti.com/lit/ds/symlink/tps22919.pdf", (0, -15.24), True, None),
        ("Description", "Load switch, 1.6 V to 5.5 V, 1.5 A, 90 mΩ, quick output discharge, SC-70-6", (0, -17.78), True, None),
        ("Manufacturer", "Texas Instruments", (0, -20.32), True, None),
        ("MPN", "TPS22919DCKR", (0, -22.86), True, None),
        ("ki_keywords", "load switch power distribution", (0, 0), True, None),
        ("ki_fp_filters", "SOT?363*", (0, 0), True, None),
    ]
    out = [f"(symbol {q(name)} (pin_names (offset 0.508)) (exclude_from_sim no) (in_bom yes) (on_board yes)"]
    for k, v, (x, y), hide, just in props:
        out.append(f"  (property {q(k)} {q(v)} (at {n(x)} {n(y)} 0) {eff(hide=hide, justify=just)})")
    out.append(f"  (symbol \"{short}_0_1\" (rectangle (start -7.62 5.08) (end 7.62 -7.62) "
               "(stroke (width 0.254) (type default)) (fill (type background))))")
    pins = [
        pin("power_in", -10.16, 2.54, 0, "IN", "1"),
        pin("input", -10.16, -2.54, 0, "ON", "3"),
        pin("no_connect", -10.16, -5.08, 0, "NC", "4"),
        pin("power_in", 0, -10.16, 90, "GND", "2"),
        pin("power_out", 10.16, 2.54, 180, "OUT", "6"),
        pin("passive", 10.16, -2.54, 180, "QOD", "5"),
    ]
    out.append(f"  (symbol \"{short}_1_1\" " + " ".join(pins) + ")")
    out.append("  (embedded_fonts no))")
    return "\n".join(out)


# ---------------------------------------------------------------- schematic writer

class Sch:
    def __init__(self, name, project, title, role, purpose, paper="A4", page_uuid=None):
        self.name, self.project = name, project
        self.uuid = page_uuid or uid(project, name)
        self.title, self.role, self.purpose, self.paper = title, role, purpose, paper
        self.lib, self.items = {}, []
        self.root_path = None  # instance path of this sheet, set by the project

    def use(self, lib_id, text):
        self.lib[lib_id] = text

    def add(self, s):
        self.items.append(s)

    # primitives -------------------------------------------------------------
    def wire(self, *pts):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            self.add(f"(wire (pts (xy {n(x1)} {n(y1)}) (xy {n(x2)} {n(y2)})) (stroke (width 0) (type default)) "
                     f"(uuid {q(uid(self.project, self.name, 'w', x1, y1, x2, y2))}))")

    def junction(self, x, y):
        self.add(f"(junction (at {n(x)} {n(y)}) (diameter 0) (color 0 0 0 0) (uuid {q(uid(self.project, self.name, 'j', x, y))}))")

    def nc(self, x, y):
        self.add(f"(no_connect (at {n(x)} {n(y)}) (uuid {q(uid(self.project, self.name, 'nc', x, y))}))")

    def label(self, text, x, y, angle=0):
        just = "left bottom" if angle in (0, 90) else "right bottom"
        self.add(f"(label {q(text)} (at {n(x)} {n(y)} {angle}) {eff(justify=just)} (uuid {q(uid(self.project, self.name, 'l', text, x, y))}))")

    def hlabel(self, text, shape, x, y, angle):
        just = "left" if angle in (0, 90) else "right"
        self.add(f"(hierarchical_label {q(text)} (shape {shape}) (at {n(x)} {n(y)} {angle}) {eff(justify=just)} "
                 f"(uuid {q(uid(self.project, self.name, 'hl', text))}))")

    def text(self, s, x, y, size=1.27, bold=False):
        self.add(f"(text {q(s)} (exclude_from_sim no) (at {n(x)} {n(y)} 0) {eff(size, justify='left bottom', bold=bold)} "
                 f"(uuid {q(uid(self.project, self.name, 't', s[:40], x, y))}))")

    def text_box(self, s, x, y, w, h=None):
        if h is None:  # fit the text: about 2.2 mm per line at 1.27 mm, plus the margins, on the grid
            h = G * -(-(len(s.split("\n")) * 2.2 + 3.81) // G)
        self.add(f"(text_box {q(s)} (exclude_from_sim no) (at {n(x)} {n(y)} 0) (size {n(w)} {n(h)}) "
                 "(margins 1.905 1.905 1.905 1.905) (stroke (width 0) (type default)) (fill (type none)) "
                 f"{eff(justify='left top')} (uuid {q(uid(self.project, self.name, 'tb', s[:40]))}))")

    def group_box(self, title, x, y, w, h):
        """A titled grouping rectangle (CRAFT-174): thin dashed line, no fill, title at 2.54 mm."""
        self.add(f"(rectangle (start {n(x)} {n(y)}) (end {n(x + w)} {n(y + h)}) (stroke (width 0) (type dash)) "
                 f"(fill (type none)) (uuid {q(uid(self.project, self.name, 'r', title))}))")
        self.text(title, x + G, y - G, size=2.54)

    def table(self, x, y, widths, rows, key):
        """A KiCad table (CRAFT-176). rows: list of lists of strings; the first row is the header."""
        h = 2 * 2.54
        cells = []
        for r, row in enumerate(rows):
            cx = x
            for ci, cell in enumerate(row):
                w = widths[ci]
                cells.append(f"(table_cell {q(cell)} (exclude_from_sim no) (at {n(cx)} {n(y + r * h)} 0) (size {n(w)} {n(h)}) "
                             f"(margins 0.9525 0.9525 0.9525 0.9525) (span 1 1) (fill (type none)) "
                             f"{eff(justify='left top', bold=(r == 0))} "
                             f"(uuid {q(uid(self.project, self.name, key, r, ci))}))")
                cx += w
        self.add(f"(table (column_count {len(widths)}) (border (external yes) (header yes) (stroke (width 0) (type solid))) "
                 f"(separators (rows yes) (cols yes) (stroke (width 0) (type solid))) "
                 f"(column_widths {' '.join(n(w) for w in widths)}) (row_heights {' '.join(n(h) for _ in rows)}) "
                 f"(cells {' '.join(cells)}))")

    def symbol(self, lib_id, ref, value, x, y, angle=0, fields=None, ref_at=None, val_at=None,
               in_bom=True, on_board=True, pins=("1", "2"), extra_shown=None, dnp=False, val_justify="left"):
        fields = dict(fields or {})
        rx, ry = ref_at or (x + 2.54, y - 1.27)
        vx, vy = val_at or (x + 2.54, y + 1.27)
        is_power = ref.startswith("#")
        props = [("Reference", ref, rx, ry, is_power, "left"), ("Value", value, vx, vy, False, val_justify)]
        sx, sy = vx, vy + 2.54
        for k, v in (extra_shown or {}).items():
            props.append((k, v, sx, sy, False, "left"))
            sy += 2.54
        for k, v in fields.items():
            props.append((k, v, x, y, True, None))
        body = [f"(symbol (lib_id {q(lib_id)}) (at {n(x)} {n(y)} {angle}) (unit 1) (body_style 1) "
                f"(exclude_from_sim no) (in_bom {'yes' if in_bom else 'no'}) (on_board {'yes' if on_board else 'no'}) "
                f"(dnp {'yes' if dnp else 'no'}) (uuid {q(uid(self.project, self.name, 's', ref))})"]
        for k, v, px, py, hide, just in props:
            # KiCad stores a field's angle relative to the symbol: a rotated symbol keeps its text
            # horizontal with the same angle on its fields
            body.append(f"  (property {q(k)} {q(v)} (at {n(px)} {n(py)} {angle if angle in (90, 270) else 0}) "
                        f"{eff(hide=hide, justify=None if angle in (90, 270) else just)})")
        for p in pins:
            body.append(f"  (pin {q(p)} (uuid {q(uid(self.project, self.name, 'p', ref, p))}))")
        body.append(f"  (instances (project {q(self.project)} (path {q(self.root_path)} (reference {q(ref)}) (unit 1)))))")
        self.add("\n".join(body))

    def power(self, lib_id, net, x, y, angle=0, idx=[0]):
        idx[0] += 1
        ref = f"#PWR{idx[0]:03d}" if not lib_id.endswith("PWR_FLAG") else f"#FLG{idx[0]:03d}"
        down = net == "GND"
        vy = y + 3.81 if down else y - 3.81
        self.symbol(lib_id, ref, net, x, y, angle, ref_at=(x, y), val_at=(x, vy), pins=("1",), val_justify=None)

    def sheet(self, child, x, y, w, h, pins, block=None, page="2"):
        """A sheet symbol. pins: (name, shape, side, offset along the edge)."""
        out = [f"(sheet (at {n(x)} {n(y)}) (size {n(w)} {n(h)}) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) "
               f"(fields_autoplaced yes) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) "
               f"(uuid {q(child.sheet_uuid)})",
               f"  (property \"Sheetname\" {q(child.title)} (at {n(x)} {n(y - 0.7116)} 0) {eff(justify='left bottom')})",
               f"  (property \"Sheetfile\" {q(child.name)} (at {n(x)} {n(y + h + 0.5884)} 0) {eff(justify='left top')})"]
        if block:
            out.append(f"  (property \"Block\" {q(block)} (at {n(x)} {n(y + h + 3.1284)} 0) {eff(justify='left top')})")
        for name, shape, side, off in pins:
            if side == "left":
                px, py, a, j = x, y + off, 180, "left"
            elif side == "right":
                px, py, a, j = x + w, y + off, 0, "right"
            elif side == "top":
                px, py, a, j = x + off, y, 90, "right"
            else:
                px, py, a, j = x + off, y + h, 270, "left"
            out.append(f"  (pin {q(name)} {shape} (at {n(px)} {n(py)} {a}) {eff(justify=j)} "
                       f"(uuid {q(uid(self.project, child.name, 'sp', name))}))")
        out.append(f"  (instances (project {q(self.project)} (path {q(self.root_path)} (page {q(page)}))))")
        out.append(")")
        self.add("\n".join(out))

    def render(self, root=False, pages=None):
        tb = [f"(title {q(self.title)})", f"(date {q(DATE)})", f"(rev {q(REV)})", f"(company {q(HOLDER)})",
              f"(comment 1 {q(self.role)})", f"(comment 2 {q(self.purpose)})"]
        out = ["(kicad_sch (version 20260306) (generator \"eeschema\") (generator_version \"10.0\")",
               f"(uuid {q(self.uuid)})", f"(paper {q(self.paper)})",
               "(title_block " + " ".join(tb) + ")",
               "(lib_symbols " + "\n".join(self.lib[k] for k in sorted(self.lib)) + ")"]
        out += self.items
        if root:
            out.append("(sheet_instances (path \"/\" (page \"1\")))")
        out.append("(embedded_fonts no))")
        return "\n".join(out) + "\n"


# ---------------------------------------------------------------- example project

PARTS = {
    "R_100k": dict(Footprint="Resistor_SMD:R_0402_1005Metric",
                   Datasheet="https://www.yageo.com/upload/media/product/productsearch/datasheet/rchip/PYu-RC_Group_51_RoHS_L_12.pdf",
                   Description="Resistor, 100 kΩ, 1 %, 1/16 W, 0402", Manufacturer="YAGEO", MPN="RC0402FR-07100KL"),
    "R_1": dict(Footprint="Resistor_SMD:R_0603_1608Metric",
                Datasheet="https://www.yageo.com/upload/media/product/productsearch/datasheet/rchip/PYu-RC_Group_51_RoHS_L_12.pdf",
                Description="Resistor, 1 Ω, 1 %, 1/10 W, 0603: measurement link (shunt)", Manufacturer="YAGEO",
                MPN="RC0603FR-071RL"),
    "C_1u": dict(Footprint="Capacitor_SMD:C_0402_1005Metric",
                 Datasheet="https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM155R61A105KE15-01.pdf",
                 Description="Capacitor, 1 µF, 10 V, X5R, 0402", Manufacturer="Murata", MPN="GRM155R61A105KE15D"),
    "C_100n": dict(Footprint="Capacitor_SMD:C_0402_1005Metric",
                   Datasheet="https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM155R71C104KA88-01.pdf",
                   Description="Capacitor, 100 nF, 16 V, X7R, 0402", Manufacturer="Murata", MPN="GRM155R71C104KA88D"),
    "J_4": dict(Footprint="Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
                Datasheet="https://www.we-online.com/components/products/datasheet/61300411121.pdf",
                Description="Pin header, 1x04, 2.54 mm, vertical", Manufacturer="Wurth Elektronik", MPN="61300411121"),
    "TP": dict(Footprint="TestPoint:TestPoint_Pad_D1.0mm", Datasheet="~",
               Description="Test pad, 1.0 mm, Kelvin sense of the measurement link"),
}


def fields(key, block, **extra):
    f = dict(PARTS[key])
    f["Block"] = block
    f.update(extra)
    return f


def build_example(out_dir):
    project = "load-switch"
    lib_nick = "OpenDAP_Example"
    root = Sch("load-switch.kicad_sch", project, "Block diagram", "root",
               "The example board's blocks in signal-flow order, with the overview sheets")
    power = Sch("power.kicad_sch", project, "Power overview", "power",
                "Rails of the example board: source, switch, consumers and measurement")
    inter = Sch("interconnect.kicad_sch", project, "Interconnect overview", "interconnect",
                "External connections of the example board: J201 pin map")
    header = Sch("header.kicad_sch", project, "Input header", "blk.header",
                 "Supply input, switched output and enable on one 4-pin header (J201)")
    sw = Sch("periph-switch.kicad_sch", project, "Peripheral supply switch", "blk.periph-switch",
             "Switches VIN onto VOUT for one peripheral block; off by default, measured by a shunt link")
    root_path = "/" + root.uuid
    for s in (power, inter, header, sw):
        s.sheet_uuid = uid(project, "sheet", s.name)
        s.root_path = f"{root_path}/{s.sheet_uuid}"
    root.root_path = root_path

    r_sym, c_sym = stock("Device", "R"), stock("Device", "C")
    gnd, flag, vcc = stock("power", "GND"), stock("power", "PWR_FLAG"), stock("power", "VCC")
    tp, conn = stock("Connector", "TestPoint"), stock("Connector_Generic", "Conn_01x04")
    sw_sym = example_switch_symbol(lib_nick + ":")

    # ---- blk.periph-switch -------------------------------------------------
    # Signal flow left to right: interface labels at the left edge (supply first), input
    # capacitor, switch, measurement link with its Kelvin pads, output capacitor, output label at
    # the right edge. Every ground symbol sits on one baseline at the bottom of the circuit.
    s = sw
    for k, t in (("Device:R", r_sym), ("Device:C", c_sym), ("power:GND", gnd), ("Connector:TestPoint", tp),
                 ("power:PWR_FLAG", flag), (f"{lib_nick}:TPS22919DCK", sw_sym)):
        s.use(k, t)
    blk = "blk.periph-switch"
    y_rail, y_en, y_gnd = 55.88, 60.96, 81.28
    ux, uy = 104.14, 58.42  # U101: IN (93.98, 55.88), ON (93.98, 60.96), NC (93.98, 63.5), GND (104.14, 68.58)
    x_in, x_out = 38.1, 254.0  # room for the longest interface name inside the frame
    s.hlabel("VIN", "input", x_in, y_rail, 180)
    s.hlabel("EN", "input", x_in, y_en, 180)
    s.hlabel("VOUT", "output", x_out, y_rail, 0)
    # input capacitor
    s.wire((x_in, y_rail), (93.98, y_rail))
    cx = 59.69
    s.junction(cx, y_rail)
    s.wire((cx, y_rail), (cx, 63.5))
    s.symbol("Device:C", "C101", "1 µF", cx, 67.31, fields=fields("C_1u", blk), extra_shown={"Spec": "10 V X5R"},
             ref_at=(cx + 2.54, 66.04), val_at=(cx + 2.54, 68.58))
    s.wire((cx, 71.12), (cx, y_gnd))
    s.power("power:GND", "GND", cx, y_gnd)
    # enable and the switch
    s.wire((x_in, y_en), (93.98, y_en))
    s.symbol(f"{lib_nick}:TPS22919DCK", "U101", "TPS22919DCK", ux, uy, fields={
        "Footprint": "Package_TO_SOT_SMD:SOT-363_SC-70-6",
        "Datasheet": "https://www.ti.com/lit/ds/symlink/tps22919.pdf",
        "Description": "Load switch, 1.6 V to 5.5 V, 1.5 A, 90 mΩ, quick output discharge, SC-70-6",
        "Manufacturer": "Texas Instruments", "MPN": "TPS22919DCKR", "Block": blk},
        ref_at=(ux - 7.62, uy - 8.89), val_at=(ux - 7.62, uy - 6.35), pins=("1", "2", "3", "4", "5", "6"))
    s.nc(93.98, 63.5)
    s.wire((ux, 68.58), (ux, y_gnd))
    s.power("power:GND", "GND", ux, y_gnd)
    # output: QOD joins OUT; the measurement link between its Kelvin pads
    s.wire((114.3, y_rail), (149.86, y_rail))
    s.wire((114.3, 60.96), (119.38, 60.96), (119.38, y_rail))
    s.junction(119.38, y_rail)
    tp1, tp2 = 139.7, 167.64
    s.junction(tp1, y_rail)
    s.symbol("Connector:TestPoint", "TP101", "VOUT_SW", tp1, y_rail, fields=fields("TP", blk), in_bom=False,
             ref_at=(tp1 + 1.27, 48.26), val_at=(tp1 + 1.27, 50.8), pins=("1",))
    s.symbol("Device:R", "R102", "1 Ω", 153.67, y_rail, angle=90, fields=fields("R_1", blk),
             ref_at=(153.67, 60.96), val_at=(153.67, 63.5), extra_shown={"Spec": "1 % 0603"})
    s.wire((157.48, y_rail), (x_out, y_rail))
    s.junction(tp2, y_rail)
    s.symbol("Connector:TestPoint", "TP102", "VOUT", tp2, y_rail, fields=fields("TP", blk), in_bom=False,
             ref_at=(tp2 + 1.27, 48.26), val_at=(tp2 + 1.27, 50.8), pins=("1",))
    # output capacitor; PWR_FLAG: VOUT is driven through the link, which ERC cannot see
    fx, ox = 194.31, 208.28
    s.junction(fx, y_rail)
    s.wire((fx, y_rail), (fx, 63.5))
    s.power("power:PWR_FLAG", "PWR_FLAG", fx, 63.5, angle=180)
    s.junction(ox, y_rail)
    s.wire((ox, y_rail), (ox, 63.5))
    s.symbol("Device:C", "C102", "100 nF", ox, 67.31, fields=fields("C_100n", blk), extra_shown={"Spec": "16 V X7R"},
             ref_at=(ox + 2.54, 66.04), val_at=(ox + 2.54, 68.58))
    s.wire((ox, 71.12), (ox, y_gnd))
    s.power("power:GND", "GND", ox, y_gnd)
    # groups: one titled box per function, a gap of one grid step between them
    top, hgt = 40.64, 48.26
    s.group_box("Input", 48.26, top, 25.4, hgt)
    s.group_box("Switch", 82.55, top, 41.91, hgt)
    s.group_box("Measurement link", 133.35, top, 45.72, hgt)
    s.group_box("Output", 187.96, top, 38.1, hgt)
    # interface and rail tables, notes
    s.text("Interface", 19.05, 104.14, size=2.54)
    s.table(19.05, 106.68, [22.86, 20.32, 83.82], [
        ["Net", "Direction", "Absent state (block not fitted)"],
        ["VIN", "Supply in", "VSYS_LV stays live; nothing in this block loads it"],
        ["EN", "Input", "Held low by R201 on the host side (blk.header)"],
        ["VOUT", "Supply out", "Unpowered; the consumer block sees 0 V"],
    ], "iface")
    s.text("Rails", 19.05, 135.89, size=2.54)
    s.table(19.05, 138.43, [22.86, 25.4, 78.74], [
        ["Rail", "Capacitors", "Requirement"],
        ["VIN", "C101 1 µF", "Input capacitor of the data sheet's typical application"],
        ["VOUT", "C102 100 nF", "Load capacitor of the data sheet's typical application"],
    ], "rails")
    s.text_box("Notes\n"
               "1. Default off: EN is low until the host drives it (pull-down R201 in blk.header).\n"
               "2. Absent state: see the interface table. Nothing floats; nothing is back-powered.\n"
               "3. Measurement: R102 is a 1 Ω link in the full variant and 0 Ω in production;\n"
               "   TP101 and TP102 are its Kelvin pads (RFC 0011 rule 3).\n"
               "4. C101 and C102 follow the TPS22919 data sheet's typical application\n"
               "   (section not cited here: UNVERIFIED).\n"
               "5. Unless noted: resistors 1 %; capacitors X5R or X7R, rated at least twice the rail.",
               152.4, 101.6, 129.54)
    pages = {"power": "2", "interconnect": "3", "header": "4", "switch": "5"}

    # ---- blk.header --------------------------------------------------------
    h = header
    for k, t in (("Device:R", r_sym), ("power:GND", gnd), ("power:PWR_FLAG", flag), ("power:VCC", vcc),
                 ("Connector_Generic:Conn_01x04", conn)):
        h.use(k, t)
    hb = "blk.header"
    jx, jy = 55.88, 60.96
    h.symbol("Connector_Generic:Conn_01x04", "J201", "Conn_01x04", jx, jy, angle=0,
             fields=fields("J_4", hb), ref_at=(jx - 3.81, jy - 5.08), val_at=(jx - 3.81, jy + 10.16),
             pins=("1", "2", "3", "4"))
    # Conn_01x04 draws its pins on the left; mirrored, they face the circuit on the right
    h.items[-1] = h.items[-1].replace(f"(at {n(jx)} {n(jy)} 0) (unit 1)", f"(at {n(jx)} {n(jy)} 0) (mirror y) (unit 1)")
    pxs = jx + 5.08
    py = [jy - 2.54, jy, jy + 2.54, jy + 5.08]
    # rails nest: pin 1 turns up first, pin 2 further right, so no wire crosses another
    h.wire((pxs, py[0]), (91.44, py[0]), (91.44, 48.26))
    h.power("power:VCC", "VSYS_LV", 91.44, 48.26)
    h.junction(76.2, py[0])
    h.wire((76.2, py[0]), (76.2, 52.07))
    h.power("power:PWR_FLAG", "PWR_FLAG", 76.2, 52.07)
    h.wire((pxs, py[1]), (109.22, py[1]), (109.22, 48.26))
    h.power("power:VCC", "PERIPH_3V3", 109.22, 48.26)
    # pin 3: the enable, with the host-side pull-down that sets the switch block's absent state
    h.wire((pxs, py[2]), (167.64, py[2]))
    h.hlabel("EN_PERIPH", "output", 167.64, py[2], 0)
    h.junction(129.54, py[2])
    h.wire((129.54, py[2]), (129.54, 67.31))
    h.symbol("Device:R", "R201", "100 kΩ", 129.54, 71.12, fields=fields("R_100k", hb), ref_at=(132.08, 69.85),
             val_at=(132.08, 72.39))
    h.wire((129.54, 74.93), (129.54, 81.28))
    h.power("power:GND", "GND", 129.54, 81.28)
    # pin 4: ground, flagged as driven from outside the board
    h.wire((pxs, py[3]), (71.12, py[3]), (71.12, 81.28))
    h.power("power:GND", "GND", 71.12, 81.28)
    h.junction(71.12, 72.39)
    h.wire((71.12, 72.39), (64.77, 72.39), (64.77, 74.93))
    h.power("power:PWR_FLAG", "PWR_FLAG", 64.77, 74.93, angle=180)
    h.group_box("Header J201", 38.1, 40.64, 106.68, 48.26)
    h.text("Rails", 19.05, 104.14, size=2.54)
    h.table(19.05, 106.68, [27.94, 22.86, 78.74], [
        ["Rail", "Capacitors", "Requirement"],
        ["VSYS_LV", "none here", "Decoupled at its consumer (C101 in blk.periph-switch)"],
    ], "rails")
    h.text_box("Notes\n"
               "1. J201 is the example board's only external connection (interconnect overview).\n"
               "2. R201 holds EN_PERIPH low while no host drives it: blk.periph-switch is off by\n"
               "   default, and its absent state never depends on its own parts (RFC 0011 rule 2).\n"
               "3. Absent state: this block is always fitted; it is the board's input.\n"
               "4. PWR_FLAG marks VSYS_LV and GND as driven from outside the board.",
               152.4, 101.6, 129.54)

    # ---- overviews -----------------------------------------------------------
    p = power
    p.text("Power tree", 19.05, 30.48, size=2.54)
    p.add(f"(rectangle (start 19.05 38.1) (end 49.53 48.26) (stroke (width 0) (type solid)) (fill (type none)) (uuid {q(uid(project, 'p', 'r1'))}))")
    p.text("J201 pin 1", 21.59, 41.91)
    p.text("VSYS_LV, external", 21.59, 45.72)
    p.add(f"(polyline (pts (xy 49.53 43.18) (xy 69.85 43.18)) (stroke (width 0) (type solid)) (fill (type none)) (uuid {q(uid(project, 'p', 'l1'))}))")
    p.add(f"(rectangle (start 69.85 38.1) (end 110.49 48.26) (stroke (width 0) (type solid)) (fill (type none)) (uuid {q(uid(project, 'p', 'r2'))}))")
    p.text("blk.periph-switch, U101", 72.39, 41.91)
    p.text("EN_PERIPH, default off", 72.39, 45.72)
    p.add(f"(polyline (pts (xy 110.49 43.18) (xy 130.81 43.18)) (stroke (width 0) (type solid)) (fill (type none)) (uuid {q(uid(project, 'p', 'l2'))}))")
    p.add(f"(rectangle (start 130.81 38.1) (end 166.37 48.26) (stroke (width 0) (type solid)) (fill (type none)) (uuid {q(uid(project, 'p', 'r3'))}))")
    p.text("PERIPH_3V3", 133.35, 41.91)
    p.text("J201 pin 2", 133.35, 45.72)
    p.text("Rail table", 19.05, 62.23, size=2.54)
    p.table(19.05, 64.77, [27.94, 22.86, 38.1, 33.02, 38.1, 33.02], [
        ["Rail", "Voltage", "Source", "Switch", "Consumers", "Measure"],
        ["VSYS_LV", "3.0-5.5 V", "J201 (external)", "none", "blk.periph-switch", "none"],
        ["PERIPH_3V3", "= VSYS_LV", "U101 (blk.periph-switch)", "EN_PERIPH", "J201 pin 2", "R102, TP101, TP102"],
        ["GND", "0 V", "J201 pin 4", "none", "all", "none"],
    ], "rails")
    p.text_box("Notes\n"
               "1. Rail names here are the names used on every sheet (CRAFT-84): the power tree is their source.\n"
               "2. Voltages are the example's; a board takes them from its power tree document.",
               19.05, 99.06, 129.54)
    i = inter
    i.text("J201, input header", 19.05, 30.48, size=2.54)
    i.table(19.05, 33.02, [12.7, 30.48, 25.4, 38.1, 60.96], [
        ["Pin", "Net", "Direction", "Block", "Notes"],
        ["1", "VSYS_LV", "Supply in", "blk.header", "3.0-5.5 V from outside the board"],
        ["2", "PERIPH_3V3", "Supply out", "blk.periph-switch", "Switched VSYS_LV, measured by R102"],
        ["3", "EN_PERIPH", "Input", "blk.header", "Pulled low by R201: switch off"],
        ["4", "GND", "Ground", "blk.header", "Board ground"],
    ], "j201")
    i.text_box("Notes\n"
               "1. One row per contact of every external connector, named as on the block sheets.",
               19.05, 64.77, 129.54)

    # ---- root: block diagram -------------------------------------------------
    r = root
    for k, t in (("power:VCC", vcc),):
        r.use(k, t)
    r.text("Overviews", 25.4, 30.48, size=2.54)
    r.sheet(power, 25.4, 35.56, 38.1, 10.16, [], page=pages["power"])
    r.sheet(inter, 76.2, 35.56, 38.1, 10.16, [], page=pages["interconnect"])
    r.text("Blocks, in signal-flow order", 25.4, 68.58, size=2.54)
    # header: EN_PERIPH out on the right
    r.sheet(header, 25.4, 78.74, 38.1, 20.32, [("EN_PERIPH", "output", "right", 10.16)], block="blk.header",
            page=pages["header"])
    # switch: VIN on top, EN left, VOUT right
    r.sheet(sw, 101.6, 78.74, 45.72, 20.32, [("VIN", "input", "top", 7.62), ("EN", "input", "left", 10.16),
                                            ("VOUT", "output", "right", 10.16)], block="blk.periph-switch",
            page=pages["switch"])
    r.wire((63.5, 88.9), (101.6, 88.9))
    r.label("EN_PERIPH", 76.2, 88.9)
    r.wire((109.22, 78.74), (109.22, 71.12))
    r.power("power:VCC", "VSYS_LV", 109.22, 71.12)
    r.wire((147.32, 88.9), (167.64, 88.9), (167.64, 78.74))
    r.power("power:VCC", "PERIPH_3V3", 167.64, 78.74)
    r.text_box("Notes\n"
               "1. Reading order: overviews first, then blocks left to right as the signal flows;\n"
               "   page numbers follow it (CRAFT-111).\n"
               "2. Rails cross the hierarchy as power symbols named as the power tree; signals as\n"
               "   sheet pins named as each block's interface (CRAFT-112).",
               25.4, 114.3, 129.54)

    files = {}
    files["load-switch.kicad_sch"] = r.render(root=True)
    for s in (power, inter, header, sw):
        files[s.name] = s.render()
    # the example's symbol library: the same text the schematic embeds
    lib_sym = example_switch_symbol().replace('(symbol "TPS22919DCK"', '(symbol "TPS22919DCK"', 1)
    files["example.kicad_sym"] = ("(kicad_symbol_lib (version 20251024) (generator \"opendap-templates\") "
                                  "(generator_version \"10.0\")\n" + lib_sym + ")\n")
    # The project names every library it uses, so it opens the same way on any machine: KiCad's
    # stock libraries through KiCad's own path variables, the example's symbol next to it.
    stock_syms = ("power", "Device", "Connector", "Connector_Generic")
    files["sym-lib-table"] = "(sym_lib_table\n  (version 7)\n" + "".join(
        f"  (lib (name \"{l}\")(type \"KiCad\")(uri \"${{KICAD10_SYMBOL_DIR}}/{l}.kicad_sym\")(options \"\")(descr \"KiCad stock library\"))\n"
        for l in stock_syms) + (
        "  (lib (name \"OpenDAP_Example\")(type \"KiCad\")(uri \"${KIPRJMOD}/example.kicad_sym\")"
        "(options \"\")(descr \"Symbols of the example\"))\n)\n")
    stock_fps = ("Capacitor_SMD", "Connector_PinHeader_2.54mm", "Package_TO_SOT_SMD", "Resistor_SMD", "TestPoint")
    files["fp-lib-table"] = "(fp_lib_table\n  (version 7)\n" + "".join(
        f"  (lib (name \"{l}\")(type \"KiCad\")(uri \"${{KICAD10_FOOTPRINT_DIR}}/{l}.pretty\")(options \"\")(descr \"KiCad stock library\"))\n"
        for l in stock_fps) + ")\n"
    return files


NETCLASSES = """# Net classes of the example: the contract between the schematic and the board's rules,
# in the format of the T1 board's hardware/rules/netclasses.toml. The project's net classes and
# patterns are generated from this file; odapkit craft check compares them (CRAFT-155).

version = 1

[[class]]
name = "PWR_PERIPH"
signals = "PERIPH_3V3: the switched output of blk.periph-switch to J201 pin 2"
design_current_a = 0.5
"""


def project_file(name, wks_rel, classes=(), patterns=()):
    import json
    # CRAFT-158: the craft checks at error (KiCad 10 key names); the rest at KiCad's defaults
    erc_errors = ["endpoint_off_grid", "four_way_junction", "pin_not_connected", "label_dangling",
                  "hier_label_mismatch", "power_pin_not_driven", "unresolved_variable", "unannotated",
                  "duplicate_reference", "missing_power_pin", "multiple_net_names", "similar_labels",
                  "similar_power", "similar_label_and_power", "same_local_global_label",
                  "same_local_global_power", "no_connect_connected", "no_connect_dangling",
                  "wire_dangling", "unconnected_wire_endpoint", "pin_not_driven", "undefined_netclass",
                  "ground_pin_not_ground"]
    sev = {k: "error" for k in erc_errors}
    sev.update({"lib_symbol_issues": "warning", "lib_symbol_mismatch": "warning", "footprint_link_issues": "warning",
                "footprint_filter": "ignore", "single_global_label": "warning", "isolated_pin_label": "warning",
                "missing_input_pin": "warning", "missing_bidi_pin": "warning", "missing_unit": "warning",
                "net_not_bus_member": "warning", "pin_to_pin": "warning", "simulation_model_issue": "ignore",
                "bus_definition_conflict": "error", "bus_entry_needed": "error", "bus_to_bus_conflict": "error",
                "bus_to_net_conflict": "error", "different_unit_footprint": "error", "different_unit_net": "error",
                "duplicate_sheet_names": "error", "extra_units": "error", "label_multiple_wires": "warning",
                "unit_value_mismatch": "error", "stacked_pin_name": "warning", "field_name_whitespace": "warning"})
    pro = {
        "meta": {"filename": name + ".kicad_pro", "version": 3},
        "erc": {"erc_exclusions": [], "meta": {"version": 0}, "rule_severities": sev},
        "schematic": {
            "page_layout_descr_file": wks_rel,
            "connection_grid_size": 50.0,
            "annotate_start_num": 0,
            # multi-unit references read "U1.A", "U3501.System" (Schematic Setup > Formatting, ".A")
            "subpart_id_separator": 46,
            "subpart_first_id": 65,
            "drawing": {"default_text_size": 50.0, "default_line_thickness": 6.0, "default_wire_thickness": 6.0,
                        "default_bus_thickness": 12.0, "default_junction_size": 40.0, "junction_size_choice": 3,
                        "label_size_ratio": 0.3, "pin_symbol_size": 25.0, "text_offset_ratio": 0.3,
                        "intersheets_ref_show": True, "intersheets_ref_short": False,
                        "intersheets_ref_prefix": "[", "intersheets_ref_suffix": "]",
                        "intersheets_ref_own_page": False,
                        "field_names": [{"name": n_, "url": n_ == "Datasheet", "visible": n_ == "Spec"}
                                        for n_ in ("Manufacturer", "MPN", "Spec", "Block", "Constraints",
                                                   "Manufacturer_2", "MPN_2", "Alternate")]},
            "meta": {"version": 1},
        },
        "net_settings": {"classes": [{"name": "Default", "priority": 2147483647, "wire_width": 6, "bus_width": 12,
                                      "clearance": 0.2, "track_width": 0.2, "via_diameter": 0.6, "via_drill": 0.3,
                                      "microvia_diameter": 0.3, "microvia_drill": 0.1, "diff_pair_width": 0.2,
                                      "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "line_style": 0,
                                      "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}]
                         + [{"name": c_, "priority": i_, "schematic_color": "rgba(0, 0, 0, 0.000)",
                             "pcb_color": "rgba(0, 0, 0, 0.000)"} for i_, c_ in enumerate(classes)],
                         "meta": {"version": 4}, "netclass_assignments": None,
                         "netclass_patterns": [{"netclass": c_, "pattern": p_} for c_, p_ in (patterns or [])]},
        "text_variables": {"OPENDAP_PROJECT": "OpenDAP example", "OPENDAP_BOARD": "load-switch block",
                           "OPENDAP_LICENCE": "CERN-OHL-W-2.0",
                           "OPENDAP_SOURCE": "github.com/opendap-project/kicad-lib",
                           "OPENDAP_BASE_VARIANT": "full"},
        "sheets": [],
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
    }
    return json.dumps(pro, indent=2) + "\n"


def feature_block_template():
    """The sheet template for one feature block, laid out as the example's block sheets: circuit in
    the upper band between titled groups, interface labels on the edges, the interface and rail
    tables at the lower left, the notes above the title block. Placeholders in <angle brackets>."""
    t = Sch("feature-block.kicad_sch", "feature-block", "<Function, in sentence case>", "blk.<id>",
            "<One sentence: what this block does and for whom>")
    t.root_path = "/" + t.uuid
    t.hlabel("<SUPPLY_IN>", "input", 38.1, 55.88, 180)
    t.hlabel("<SIGNAL_IN>", "input", 38.1, 60.96, 180)
    t.hlabel("<SIGNAL_OUT>", "output", 254, 60.96, 0)
    t.group_box("<Group title>", 48.26, 40.64, 72.39, 48.26)
    t.group_box("<Next group>", 133.35, 40.64, 72.39, 48.26)
    t.text("Supplies enter first at the left (or top), inputs left, outputs right; ground symbols on one baseline.",
           48.26, 96.52)
    t.text("Interface", 19.05, 104.14, size=2.54)
    t.table(19.05, 106.68, [22.86, 20.32, 83.82], [
        ["Net", "Direction", "Absent state (block not fitted)"],
        ["<NET>", "<Input>", "<What holds it, and where (host side)>"],
    ], "iface")
    t.text("Rails", 19.05, 135.89, size=2.54)
    t.table(19.05, 138.43, [22.86, 25.4, 78.74], [
        ["Rail", "Capacitors", "Requirement"],
        ["<RAIL>", "<C1xx value>", "<Data sheet requirement, with its section>"],
    ], "rails")
    t.text_box("Notes\n"
               "1. Function: <what the block does>.\n"
               "2. Absent state: <what every interface net does with the block unfitted or unpowered>.\n"
               "3. Constraints: <PCB-x-nn IDs this sheet implements>.\n"
               "4. Decisions: <ADR numbers, one line each>.\n"
               "5. Unless noted: <default tolerance, dielectric, voltage rating>.",
               152.4, 101.6, 129.54)
    return t.render(root=True)


# ---------------------------------------------------------------- main

def kicad_cli():
    env = os.environ.get("KICAD_CLI")
    bundled = os.path.join(KICAD_APP, "Contents", "MacOS", "kicad-cli")
    return env or (bundled if os.path.exists(bundled) else shutil.which("kicad-cli"))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def main():
    write(os.path.join(ROOT, "drawing-sheets", "opendap.kicad_wks"), drawing_sheet())
    tdir = os.path.join(ROOT, "templates", "feature-block")
    write(os.path.join(tdir, "feature-block.kicad_sch"), feature_block_template())
    edir = os.path.join(ROOT, "examples", "load-switch")
    for name, text in build_example(edir).items():
        write(os.path.join(edir, name), text)
    write(os.path.join(edir, "load-switch.kicad_pro"),
          project_file("load-switch", "${KIPRJMOD}/../../drawing-sheets/opendap.kicad_wks",
                       classes=["PWR_PERIPH"], patterns=[("PWR_PERIPH", "PERIPH_3V3")]))
    write(os.path.join(edir, "netclasses.toml"), NETCLASSES)
    cli = kicad_cli()
    if cli:
        for d in (edir, tdir):
            for f in sorted(os.listdir(d)):
                if f.endswith(".kicad_sch"):
                    subprocess.run([cli, "sch", "upgrade", "--force", os.path.join(d, f)], check=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("generated: drawing-sheets/opendap.kicad_wks, templates/feature-block/, examples/load-switch/")


if __name__ == "__main__":
    main()
