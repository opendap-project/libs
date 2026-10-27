#!/usr/bin/env python3
"""Checks for kicad-lib's generated symbols and footprints.

Usage:
    python3 generator/test_library.py [-v]        (Python 3.11 or later)

For every part data file in generator/parts/:

- the library files are up to date with the data (kigen.py --check) and every footprint has its
  STEP model;
- the symbol pins (count, numbers and names) match the pin table of the part's parts-lib spec sheet
  (found through the workspace's repos.tsv, or ODAP_PARTS_LIB_DIR); skipped when parts-lib is not
  checked out;
- the symbol's pin numbers match the footprint's numbered copper pads, and the symbol carries the
  Manufacturer, MPN, Datasheet and Footprint fields (PCB-T-05);
- the pads read back from the .kicad_mod file match the transcribed drawing values ([[checks]]);
- the footprint follows the craft standard's footprint rules: courtyard around pads and body
  (KLC F5.3), silk stroke 0.15 mm and 0.15 mm clear of pads (CRAFT-05, CRAFT-07), reference text
  1.0 x 0.15 mm on the silk (CRAFT-02) and ${REFERENCE} on the fab layer (CRAFT-11), a filled
  pin-1 mark outside the body and nearest to pad 1 (CRAFT-13), SMD anchor at the body centroid
  (CRAFT-15);
- every symbol library (kigen.py, bga.py and generic.py output) follows the craft standard's symbol
  rules that a library carries: pin ends on the 2.54 mm grid, 1.27 mm for two-pin discretes
  (CRAFT-122), no hidden pins (CRAFT-125), at most 64 pins per unit (CRAFT-126), reference prefix
  from the KLC set (CRAFT-130), one pin length per symbol, long enough for its longest pin number to
  clear a no-connect flag on the pin end (CRAFT-121: 2.54 mm plus 1.27 mm per character beyond the
  first, at most 7.62 mm); a bad symbol fixture proves each rule fails;
- kicad-cli (KiCad 10) loads, upgrades and plots every footprint and symbol library.

Exit status 0 when every check passes.
"""

from __future__ import annotations

import glob
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generic  # noqa: E402
import kigen  # noqa: E402

ROOT = kigen.ROOT
KICAD_CLI = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli") or \
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
EPS = 1e-4


# ---------------------------------------------------------------- s-expression reader

def parse(text):
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)
    stack = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        elif t.startswith('"'):
            stack[-1].append(bytes(t[1:-1], "utf-8").decode("unicode_escape"))
        else:
            stack[-1].append(kigen.Sym(t))
    return stack[0][0]


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def one(node, key):
    f = find(node, key)
    return f[0] if f else None


def read_fp(path):
    n = parse(open(path).read())
    pads = []
    for p in find(n, "pad"):
        at, size = one(p, "at"), one(p, "size")
        layers = [str(x) for x in one(p, "layers")[1:]]
        pad = {"number": p[1], "kind": str(p[2]), "shape": str(p[3]),
               "at": (float(at[1]), float(at[2])), "size": (float(size[1]), float(size[2])),
               "layers": layers, "drill": one(p, "drill")}
        if pad["shape"] == "custom":
            custom_extent(pad, one(p, "primitives"))
        pads.append(pad)
    return n, pads


def custom_extent(pad, prims):
    """A custom pad's rings ((centre, inner, outer) in board coordinates) and its bounding box,
    anchor included, read from its primitives."""
    x0, y0 = pad["at"]
    a = pad["size"][0] / 2
    box = [x0 - a, y0 - a, x0 + a, y0 + a]
    pad["rings"] = []
    for c in find(prims, "gr_circle"):
        cx, cy = x0 + float(one(c, "center")[1]), y0 + float(one(c, "center")[2])
        r = math.hypot(x0 + float(one(c, "end")[1]) - cx, y0 + float(one(c, "end")[2]) - cy)
        w = float(one(c, "width")[1])
        pad["rings"].append(((cx, cy), r - w / 2, r + w / 2))
        box = [min(box[0], cx - r - w / 2), min(box[1], cy - r - w / 2), max(box[2], cx + r + w / 2), max(box[3], cy + r + w / 2)]
    for pl in find(prims, "gr_poly"):
        for xy in find(one(pl, "pts"), "xy"):
            x, y = x0 + float(xy[1]), y0 + float(xy[2])
            box = [min(box[0], x), min(box[1], y), max(box[2], x), max(box[3], y)]
    pad["bbox"] = tuple(box)


def is_copper_pad(p):
    """A pad that is a land of the part: copper on an outer layer with a mask opening."""
    return any(l in ("F.Cu", "*.Cu") for l in p["layers"]) and any("Mask" in l for l in p["layers"]) \
        and p["kind"] != "np_thru_hole"


def rect_of(p, grow=0.0):
    if p.get("bbox"):
        b = p["bbox"]
        return (b[0] - grow, b[1] - grow, b[2] + grow, b[3] + grow)
    w, h = p["size"]
    if p["drill"] is not None:
        d = [float(x) for x in p["drill"][1:] if not str(x).isalpha()]
        if d:
            w, h = max(w, d[0]), max(h, d[-1])
    x, y = p["at"]
    return (x - w / 2 - grow, y - h / 2 - grow, x + w / 2 + grow, y + h / 2 + grow)


def seg_rect_dist(a, b, r):
    """Distance between segment a-b and the rectangle r (0 if they touch)."""
    def inside(p):
        return r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3]
    if inside(a) or inside(b):
        return 0.0
    best = math.inf
    corners = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    for i in range(4):
        c, d = corners[i], corners[(i + 1) % 4]
        best = min(best, seg_seg(a, b, c, d))
    return best


def seg_point(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def seg_seg(a, b, c, d):
    def ccw(p, q, r):
        return (r[1] - p[1]) * (q[0] - p[0]) - (q[1] - p[1]) * (r[0] - p[0])
    if (ccw(a, c, d) * ccw(b, c, d) < 0) and (ccw(a, b, c) * ccw(a, b, d) < 0):
        return 0.0
    return min(seg_point(a, c, d), seg_point(b, c, d), seg_point(c, a, b), seg_point(d, a, b))


# ---------------------------------------------------------------- parts-lib sheet reader

def parts_lib_dir():
    env = os.environ.get("ODAP_PARTS_LIB_DIR")
    if env:
        return env
    d = ROOT
    for _ in range(6):
        d = os.path.dirname(d)
        tsv = os.path.join(d, "repos.tsv")
        if os.path.exists(tsv):
            for line in open(tsv):
                cols = line.split()
                if len(cols) >= 2 and cols[1].endswith("parts-lib"):
                    return os.path.join(d, cols[0])
            return os.path.join(d, "public", "libs", "parts")
    return None


def expand_numbers(cell):
    cell = cell.replace("**", "").replace("`", "").replace("#", "").strip()
    out = []
    for part in re.split(r",\s*|;\s*|\s+and\s+", cell):
        part = part.strip()
        m = re.fullmatch(r"([A-Za-z]*)(\d+)\s*[–\-]\s*\1?(\d+)", part)
        if m:
            out += ["%s%d" % (m.group(1), i) for i in range(int(m.group(2)), int(m.group(3)) + 1)]
        elif part:
            out.append(part)
    return out


def expand_names(cell):
    """"XIN, XOUT" -> two names; "GPIO0–GPIO3" and "GPIO26_ADC0–GPIO29_ADC3" -> ranges."""
    out = []
    for part in cell.split(", "):
        m = re.fullmatch(r"(\D+)(\d+)(\D*)(\d*)[–\-]\1(\d+)\3(\d*)", part.strip())
        if m and int(m.group(5)) > int(m.group(2)):
            a, b = int(m.group(2)), int(m.group(5))
            for k in range(b - a + 1):
                suffix = m.group(3) + (str(int(m.group(4)) + k) if m.group(4) else "")
                out.append("%s%d%s" % (m.group(1), a + k, suffix))
        else:
            out.append(part.strip())
    return out


def sheet_pins(path, header=None):
    """{number: name} from the sheet's pin table: the first table whose header has a pin column
    and a name column (or the table whose header contains `header`)."""
    lines = open(path).read().splitlines()
    tables, cur = [], []
    for ln in lines:
        if ln.strip().startswith("|"):
            cur.append([c.strip() for c in ln.strip().strip("|").split("|")])
        elif cur:
            tables.append(cur)
            cur = []
    if cur:
        tables.append(cur)
    for t in tables:
        if len(t) < 3:
            continue
        head = [h.lower().replace("*", "") for h in t[0]]
        if header and header.lower() not in " | ".join(head):
            continue
        pcs = [i for i, h in enumerate(head) if re.fullmatch(r"(pin|pins|pin\(s\)|pin no\.?|no\.?|ball|contact|terminal|pad)s?", h)]
        # discretes' tables call the name column "Symbol" (Nexperia: Pin | Symbol | Description)
        ncs = [i for i, h in enumerate(head) if re.search(r"name|signal", h) or h == "symbol"]
        if not ncs:
            ncs = [i for i, h in enumerate(head) if h == "function"]
        if not pcs or not ncs:
            continue
        # a table may carry several pin/name column pairs side by side (USB-C rows A and B)
        pairs = [(pc, min([n for n in ncs if n > pc] or ncs)) for pc in pcs]
        out = {}
        for row in t[2:]:
            for pc, nc in pairs:
                if len(row) <= max(pc, nc):
                    continue
                nums = expand_numbers(row[pc])
                cell = row[nc].replace("**", "").replace("`", "").strip()
                names = expand_names(cell)
                if len(names) != len(nums):
                    names = [cell] * len(nums)
                out.update(zip(nums, names))
        return out
    # no table: an inline list in the pinout section, "pin 1 EN, 2 PG, 3 FB"
    text = "\n".join(lines)
    sec = re.search(r"## Pinout.*?(?=\n## )", text, re.S)
    m = sec and re.search(r"pin (\d+ [^\s,;()]+(?:, \d+ [^\s,;()]+)+)", sec.group(0))
    if m:
        return dict(item.split(" ", 1) for item in m.group(1).split(", "))
    hashed = sec and re.findall(r"#(\d+) ([^,;()]+?)(?=,|\s*\(|;|$)", sec.group(0), re.M)
    if hashed:
        return {n: name.strip() for n, name in hashed}
    return None


def norm(s):
    return re.sub(r"\s+", "", s.replace("~{", "").replace("}", "").replace("−", "-")).upper()


# ---------------------------------------------------------------- tests

PARTS = kigen.load_parts()


def fp_path(part):
    return os.path.join(ROOT, "footprints", part["part"]["library"] + ".pretty",
                        part["footprint"]["name"] + ".kicad_mod")


def sym_of(part):
    lib = parse(open(os.path.join(ROOT, "symbols", part["part"]["library"] + ".kicad_sym")).read())
    name = part["part"].get("symbol", part["part"]["mpn"])
    for s in find(lib, "symbol"):
        if s[1] == name:
            return s
    return None


def sym_pins(sym):
    pins = []
    for unit in find(sym, "symbol"):
        for p in find(unit, "pin"):
            at = one(p, "at")
            pins.append({"type": str(p[1]), "at": (float(at[1]), float(at[2])),
                         "name": one(p, "name")[1], "number": one(p, "number")[1]})
    return pins


class Generated(unittest.TestCase):
    def test_up_to_date(self):
        self.assertEqual(kigen.main(["--check"]), 0, "run generator/kigen.py and commit the result")
        self.assertEqual(generic.main(["--check"]), 0, "run generator/generic.py and commit the result")

    def test_models(self):
        for part in PARTS:
            lib, name = part["part"]["library"], part["footprint"]["name"]
            with self.subTest(part=part["part"]["mpn"]):
                step = os.path.join(ROOT, "3dmodels", lib + ".3dshapes", name + ".step")
                self.assertTrue(os.path.exists(step), "missing %s: run generator/model.py" % step)
                text = open(fp_path(part)).read()
                self.assertIn("%s.3dshapes/%s.step" % (lib, name), text)


class Symbols(unittest.TestCase):
    def test_fields(self):
        for part in PARTS:
            with self.subTest(part=part["part"]["mpn"]):
                sym = sym_of(part)
                self.assertIsNotNone(sym)
                props = {p[1]: p[2] for p in find(sym, "property")}
                for k in ("Manufacturer", "MPN", "Datasheet", "Footprint", "Description"):
                    self.assertTrue(props.get(k), "%s empty" % k)
                self.assertEqual(props["MPN"], part["part"]["mpn"])
                lib, name = props["Footprint"].split(":")
                self.assertTrue(os.path.exists(os.path.join(ROOT, "footprints", lib + ".pretty", name + ".kicad_mod")))

    def test_pins_on_grid(self):  # CRAFT-122: 2.54 mm (this test used to accept 1.27 mm and missed it)
        for part in PARTS:
            with self.subTest(part=part["part"]["mpn"]):
                for p in sym_pins(sym_of(part)):
                    for v in p["at"]:
                        self.assertAlmostEqual(v / 2.54, round(v / 2.54), places=4, msg=p)

    def test_pins_match_sheet(self):
        base = parts_lib_dir()
        if not base or not os.path.isdir(base):
            self.skipTest("parts-lib not checked out (set ODAP_PARTS_LIB_DIR)")
        for part in PARTS:
            pt = part["part"]
            with self.subTest(part=pt["mpn"]):
                if pt.get("sheet_pins", "").startswith("none:"):
                    continue  # the sheet has no pin table; the reason is recorded in the data
                table = sheet_pins(os.path.join(base, pt["sheet"]), pt.get("sheet_pin_table"))
                self.assertIsNotNone(table, "no pin table in %s" % pt["sheet"])
                # pins the sheet does not list (switch and shell terminals) carry not_in_sheet with the reason
                mine = {p.get("sheet_number", p["number"]): p.get("sheet_name", p["name"])
                        for p in part["pins"] if not p.get("not_in_sheet")}
                self.assertEqual(sorted(mine), sorted(table), "pin numbers differ from %s" % pt["sheet"])
                for n, name in mine.items():
                    self.assertEqual(norm(name), norm(table[n]), "pin %s" % n)

    def test_pins_match_pads(self):
        for part in PARTS:
            with self.subTest(part=part["part"]["mpn"]):
                _, pads = read_fp(fp_path(part))
                padnums = {p["number"] for p in pads if is_copper_pad(p) and p["number"]}
                symnums = {p["number"] for p in sym_pins(sym_of(part))}
                self.assertEqual(sorted(symnums), sorted(padnums))
                self.assertEqual(len(symnums), len(part["pins"]), "duplicate pin numbers")


class Footprints(unittest.TestCase):
    def test_drawing_values(self):
        for part in PARTS:
            _, pads = read_fp(fp_path(part))
            lands = [p for p in pads if is_copper_pad(p)]
            self.assertTrue(part.get("checks"), "%s: no [[checks]]" % part["part"]["mpn"])
            for c in part.get("checks", []):
                with self.subTest(part=part["part"]["mpn"], check=c):
                    def pad(n):
                        found = [p for p in lands if p["number"] == str(n)]
                        self.assertTrue(found, "no pad %s" % n)
                        # a land drawn as several copper pieces: the largest is the land's main pad
                        return max(found, key=lambda p: p["size"][0] * p["size"][1])
                    tol = c.get("tolerance", 0.005)
                    k = c["kind"]
                    if k == "pad_count":
                        self.assertEqual(len([p for p in lands if p["number"] or c.get("include_unnumbered")]), c["value"])
                        continue
                    a = pad(c["a"])
                    if k == "ring":  # a copper ring's inner and outer radius
                        self.assertTrue(a.get("rings"), "pad %s has no ring" % c["a"])
                        _, ri, ro = a["rings"][0]
                        self.assertAlmostEqual(ri, c["value"][0], delta=tol)
                        self.assertAlmostEqual(ro, c["value"][1], delta=tol)
                        continue
                    if k == "ring_dy":  # pad a's centre below the centre of pad b's ring
                        (_, cy), _, _ = pad(c["b"])["rings"][0]
                        self.assertAlmostEqual(a["at"][1] - cy, c["value"], delta=tol)
                        continue
                    if k == "pad_size":
                        self.assertAlmostEqual(a["size"][0], c["value"][0], delta=tol)
                        self.assertAlmostEqual(a["size"][1], c["value"][1], delta=tol)
                        continue
                    b = pad(c["b"])
                    dx, dy = b["at"][0] - a["at"][0], b["at"][1] - a["at"][1]
                    got = {"pitch": math.hypot(dx, dy), "dx": dx, "dy": dy}[k]
                    self.assertAlmostEqual(got, c["value"], delta=tol)

    def test_pads_as_transcribed(self):
        for part in PARTS:
            with self.subTest(part=part["part"]["mpn"]):
                want, _, _, _, _ = kigen.frame(part)
                _, pads = read_fp(fp_path(part))
                self.assertEqual(len(want), len(pads))
                key = lambda p: (str(p["number"]), round(p["at"][0], 4), round(p["at"][1], 4))
                for w, g in zip(sorted(want, key=key), sorted(pads, key=key)):
                    self.assertEqual(key(w), key(g))
                    self.assertAlmostEqual(w["size"][0], g["size"][0], places=4)
                    self.assertAlmostEqual(w["size"][1], g["size"][1], places=4)

    def test_craft(self):
        for part in PARTS:
            mpn = part["part"]["mpn"]
            with self.subTest(part=mpn):
                n, pads = read_fp(fp_path(part))
                lands = [p for p in pads if is_copper_pad(p) or p["kind"] == "np_thru_hole"]
                _, body, _, _, _ = kigen.frame(part)
                # courtyard (KLC F5.3)
                crt = [r for r in find(n, "fp_rect") if one(r, "layer")[1] == "F.CrtYd"]
                self.assertEqual(len(crt), 1)
                c = crt[0]
                cb = (float(one(c, "start")[1]), float(one(c, "start")[2]), float(one(c, "end")[1]), float(one(c, "end")[2]))
                for p in lands:
                    r = rect_of(p)
                    self.assertTrue(cb[0] <= r[0] + EPS and cb[1] <= r[1] + EPS and cb[2] >= r[2] - EPS and cb[3] >= r[3] - EPS, p["number"])
                self.assertTrue(cb[0] <= body[0] and cb[1] <= body[1] and cb[2] >= body[2] and cb[3] >= body[3])
                # silk strokes and clearance (CRAFT-05, CRAFT-07)
                silk = [l for l in find(n, "fp_line") if one(l, "layer")[1] == "F.SilkS"]
                for l in silk:
                    w = float(one(one(l, "stroke"), "width")[1])
                    self.assertAlmostEqual(w, 0.15, places=4)
                    a = (float(one(l, "start")[1]), float(one(l, "start")[2]))
                    b = (float(one(l, "end")[1]), float(one(l, "end")[2]))
                    for p in lands:
                        self.assertGreaterEqual(seg_rect_dist(a, b, rect_of(p)) - w / 2, 0.15 - EPS, "silk near pad %s" % p["number"])
                # pin-1 mark (CRAFT-13): a filled silk polygon, outside the body, nearest to pad 1
                marks = [pl for pl in find(n, "fp_poly") if one(pl, "layer")[1] == "F.SilkS" and one(pl, "fill")[1] == "yes"]
                first = kigen.pin1_number(part)
                if any(p["number"] == first for p in lands):
                    self.assertTrue(marks, "no pin-1 mark")
                    pts = [(float(x[1]), float(x[2])) for x in find(one(marks[0], "pts"), "xy")]
                    cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
                    inside = [p for p in pts if body[0] + EPS < p[0] < body[2] - EPS and body[1] + EPS < p[1] < body[3] - EPS]
                    self.assertFalse(inside, "pin-1 mark inside the body")
                    numbered = [p for p in lands if p["number"]]
                    def gap(p):
                        r = rect_of(p)
                        return math.hypot(max(r[0] - cx, 0, cx - r[2]), max(r[1] - cy, 0, cy - r[3]))
                    near = min(numbered, key=gap)
                    if not part["footprint"].get("pin1_mark"):
                        self.assertEqual(near["number"], first, "pin-1 mark nearest to pad %s" % near["number"])
                    for p in lands:
                        r = rect_of(p, 0.15)
                        self.assertFalse(any(r[0] < x < r[2] and r[1] < y < r[3] for x, y in pts), "pin-1 mark near pad %s" % p["number"])
                # texts (CRAFT-02, CRAFT-11)
                props = {p[1]: p for p in find(n, "property")}
                ref = props["Reference"]
                self.assertEqual(one(ref, "layer")[1], "F.SilkS")
                f = one(one(ref, "effects"), "font")
                self.assertEqual((float(one(f, "size")[1]), float(one(f, "thickness")[1])), (1.0, 0.15))
                fabref = [t for t in find(n, "fp_text") if t[2] == "${REFERENCE}" and one(t, "layer")[1] == "F.Fab"]
                self.assertTrue(fabref)
                # anchor (CRAFT-15)
                if part["footprint"].get("attr", "smd") == "smd":
                    self.assertAlmostEqual((body[0] + body[2]) / 2, 0, places=4)
                    self.assertAlmostEqual((body[1] + body[3]) / 2, 0, places=4)


# CRAFT-130: KLC S6.1 designators, plus NT (net tie) and FID (fiducial)
PREFIXES = {"R", "C", "L", "FB", "D", "Q", "U", "J", "P", "SW", "Y", "F", "BT", "H", "JP", "K", "T", "M",
            "LS", "MK", "AE", "RN", "RT", "RV", "TP", "FL", "DS", "A", "Z", "NT", "FID"}
UNIT_MAX_PINS = 64  # CRAFT-126
PIN_LENGTHS = (2.54, 3.81, 5.08, 6.35, 7.62)  # CRAFT-121


def pin_length_for(numbers):
    """CRAFT-121 as kigen.pin_length and bga.pin_length apply it."""
    return min(2.54 + 1.27 * (max([len(n) for n in numbers] + [1]) - 1), 7.62)

BAD_SYMBOL = """(kicad_symbol_lib (version 20251024) (generator "fixture")
 (symbol "Bad" (property "Reference" "X" (at 0 0 0))
  (symbol "Bad_1_1"
   (pin passive line (at -3.81 0 0) (length 2.54) (name "1") (number "1"))
   (pin passive line (at 3.81 0 180) (length 2.54) (name "2") (number "2"))
   (pin passive line (at 0 -5.08 90) (length 2.54) (hide yes) (name "3") (number "3")))
  (symbol "Bad_2_1"
%s)))
""" % "\n".join("   (pin passive line (at -5.08 %s 0) (length 2.54) (name \"P\") (number \"%d\"))"
                % (-2.54 * k, 100 + k) for k in range(65))


def symbol_findings(lib):
    """Findings of CRAFT-121, -122, -125, -126 and -130 on a parsed symbol library: [(rule, text)]."""
    out = []
    for sym in find(lib, "symbol"):
        name = sym[1]
        ref = next((str(p[2]) for p in find(sym, "property") if p[1] == "Reference"), "")
        pfx = re.match(r"[A-Z]*", ref).group(0)
        if pfx not in PREFIXES:
            out.append(("CRAFT-130", "%s: reference prefix %r" % (name, ref)))
        units = {}
        for sub in find(sym, "symbol"):
            unit = int(str(sub[1]).rsplit("_", 2)[1])
            units.setdefault(unit, []).extend(find(sub, "pin"))
        common = units.pop(0, [])
        pins = common + [p for u in units.values() for p in u]
        grid = 2.54 if len(pins) > 2 else 1.27
        for p in pins:
            at = one(p, "at")
            num_ = one(p, "number")[1]
            for v in (float(at[1]), float(at[2])):
                if abs(v / grid - round(v / grid)) > 1e-4:
                    out.append(("CRAFT-122", "%s pin %s at (%s, %s) off the %s mm grid" % (name, num_, at[1], at[2], grid)))
                    break
            hide = one(p, "hide")  # (hide yes), or the bare atom of older files
            if hide is not None and (len(hide) == 1 or str(hide[1]) == "yes") or \
                    "hide" in [str(x) for x in p if not isinstance(x, list)]:
                out.append(("CRAFT-125", "%s pin %s hidden" % (name, num_)))
        if len(pins) > 2:  # KLC S4.1: two-pin discretes keep KiCad's short pins
            lengths = {round(float(one(p, "length")[1]), 4) for p in pins}
            want = round(pin_length_for([str(one(p, "number")[1]) for p in pins]), 4)
            if lengths != {want}:
                out.append(("CRAFT-121", "%s: pin lengths %s, want %s" % (name, sorted(lengths), want)))
        for u, up in sorted(units.items()):
            if len(common) + len(up) > UNIT_MAX_PINS:
                out.append(("CRAFT-126", "%s unit %d: %d pins" % (name, u, len(common) + len(up))))
    return out


class SymbolRules(unittest.TestCase):
    def test_libraries(self):
        for path in sorted(glob.glob(os.path.join(ROOT, "symbols", "*.kicad_sym"))):
            with self.subTest(lib=os.path.basename(path)):
                self.assertEqual(symbol_findings(parse(open(path).read())), [])

    def test_bad_fixture_fails_every_rule(self):
        rules = {r for r, _ in symbol_findings(parse(BAD_SYMBOL))}
        self.assertEqual(rules, {"CRAFT-121", "CRAFT-122", "CRAFT-125", "CRAFT-126", "CRAFT-130"})

    def test_pin_length_rule(self):
        self.assertEqual([pin_length_for(["9" * k]) for k in range(1, 7)], [2.54, 3.81, 5.08, 6.35, 7.62, 7.62])
        for k in range(1, 6):
            self.assertIn(round(pin_length_for(["9" * k]), 4), PIN_LENGTHS)


@unittest.skipUnless(os.path.exists(KICAD_CLI), "kicad-cli not found")
class CustomPads(unittest.TestCase):
    """The ring and ring-sector pads (custom_pads.py) on an inline fixture: radii, gaps, no copper
    in the port, and a ring that cannot hold its anchor is refused."""
    FIXTURE = {"part": {"mpn": "FIXTURE", "library": "Fixture"}, "pins": [{"number": "1"}],
               "footprint": {"name": "Fixture", "body": {"x": 3.0, "y": 3.0, "z": 1.0},
                             "pads": [{"number": "", "type": "np_thru_hole", "shape": "circle",
                                       "at": [0.0, 0.0], "size": [0.8, 0.8], "drill": 0.8}],
                             "rings": [{"number": "1", "center": [0.0, 0.0], "inner": 0.58,
                                        "outer": 1.04, "anchor": 0.4}],
                             "paste_sectors": [{"center": [0.0, 0.0], "inner": 0.6, "outer": 1.0,
                                                "count": 6, "gap": 0.12, "first_gap": 0.0}]}}

    def pads(self):
        text, _ = kigen.footprint(self.FIXTURE)
        path = os.path.join(tempfile.mkdtemp(), "f.kicad_mod")
        with open(path, "w") as fh:
            fh.write(text)
        return read_fp(path)[1]

    def test_ring(self):
        ring = [p for p in self.pads() if p["number"] == "1"][0]
        self.assertEqual(ring["shape"], "custom")
        self.assertNotIn("F.Paste", ring["layers"])
        (cx, cy), ri, ro = ring["rings"][0]
        self.assertAlmostEqual(ri, 0.58, places=4)
        self.assertAlmostEqual(ro, 1.04, places=4)
        self.assertAlmostEqual(math.hypot(cx, cy), 0.0, places=4)
        a = ring["size"][0] / 2  # the anchor stays on the ring, clear of the port
        self.assertGreaterEqual(math.hypot(*ring["at"]) - a, ri - EPS)
        self.assertLessEqual(math.hypot(*ring["at"]) + a, ro + EPS)
        self.assertEqual(rect_of(ring), (-1.04, -1.04, 1.04, 1.04))

    def test_sectors(self):
        secs = [p for p in self.pads() if p["layers"] == ["F.Paste"]]
        self.assertEqual(len(secs), 6)
        text, _ = kigen.footprint(self.FIXTURE)
        polys = [n for n in find(parse(text), "pad") if one(one(n, "primitives") or [], "gr_poly")]
        self.assertEqual(len(polys), 6)
        for n in polys:
            at = one(n, "at")
            x0, y0 = float(at[1]), float(at[2])
            pts = [(x0 + float(q[1]), y0 + float(q[2])) for q in find(one(one(one(n, "primitives"), "gr_poly"), "pts"), "xy")]
            for x, y in pts:
                self.assertTrue(0.6 - EPS <= math.hypot(x, y) <= 1.0 + EPS)
            # the two straight edges (outer arc end to inner arc start, inner end to outer start)
            # each sit gap/2 = 0.06 from a gap centre line at a multiple of 60 degrees
            k = len(pts) // 2
            for a, b in ((pts[k - 1], pts[k]), (pts[-1], pts[0])):
                ang = math.atan2(a[1] + b[1], a[0] + b[0])
                line = round(ang / (math.pi / 3)) * math.pi / 3
                for x, y in (a, b):
                    self.assertAlmostEqual(abs(-math.sin(line) * x + math.cos(line) * y), 0.06, delta=2e-4)

    def test_bad_ring(self):
        bad = {"rings": [{"number": "1", "center": [0, 0], "inner": 0.58, "outer": 1.04, "anchor": 0.6}]}
        with self.assertRaises(ValueError):
            kigen.custom_pads.ring_pads(bad)
        with self.assertRaises(ValueError):
            kigen.custom_pads.ring_pads({"rings": [{"number": "1", "center": [0, 0], "inner": 1.0, "outer": 0.5}]})


class KicadCli(unittest.TestCase):
    def run_cli(self, *args):
        r = subprocess.run([KICAD_CLI, *args], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def test_footprint_libraries(self):
        for lib in sorted(glob.glob(os.path.join(ROOT, "footprints", "*.pretty"))):
            with self.subTest(lib=os.path.basename(lib)), tempfile.TemporaryDirectory() as tmp:
                self.run_cli("fp", "upgrade", lib, "--output", os.path.join(tmp, "up.pretty"), "--force")
                n = len(glob.glob(os.path.join(lib, "*.kicad_mod")))
                self.assertEqual(len(glob.glob(os.path.join(tmp, "up.pretty", "*.kicad_mod"))), n)
                os.makedirs(os.path.join(tmp, "svg"))
                self.run_cli("fp", "export", "svg", lib, "-o", os.path.join(tmp, "svg"))
                self.assertEqual(len(glob.glob(os.path.join(tmp, "svg", "*.svg"))), n)

    def test_symbol_libraries(self):
        for lib in sorted(glob.glob(os.path.join(ROOT, "symbols", "*.kicad_sym"))):
            with self.subTest(lib=os.path.basename(lib)), tempfile.TemporaryDirectory() as tmp:
                self.run_cli("sym", "upgrade", lib, "--output", os.path.join(tmp, "up.kicad_sym"), "--force")
                os.makedirs(os.path.join(tmp, "svg"))
                self.run_cli("sym", "export", "svg", lib, "-o", os.path.join(tmp, "svg"))
                self.assertTrue(glob.glob(os.path.join(tmp, "svg", "*.svg")))


if __name__ == "__main__":
    unittest.main()
