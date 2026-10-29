#!/usr/bin/env python3
"""Checks for kicad-lib's generated symbols and footprints.

Usage:
    python3 generator/test_library.py [-v]        (Python 3.11 or later)

For every part data file in generator/parts/:

- the library files are up to date with the data (kigen.py --check) and every footprint has its
  STEP model;
- the symbol pins (count, numbers and names) match the datasheet's pin table, transcribed
  separately in generator/parts/<key>/pins/<part>.toml (schema checked: datasheet revision, page
  citation, pin number to name), unless the part records sheet_pins = "none: <reason>";
- [part] lifecycle and second_sources (PLIB-003) follow their schema and are
  present on every part that had them when the fields were introduced;
- no product content in the generator data or the parts manifest (BOM lines, product ADRs, the
  T1's use of a part, a BOM's chosen `second_source`, a read of a board's files);
- the symbol's pin numbers match the footprint's numbered copper pads, and the symbol carries the
  Manufacturer, MPN, Datasheet and Footprint fields (PCB-T-05);
- the pads read back from the .kicad_mod file match the transcribed drawing values ([[checks]]);
- the footprint follows the craft standard's footprint rules: courtyard around pads and body
  (KLC F5.3), silk stroke 0.15 mm and 0.15 mm clear of pads (CRAFT-05, CRAFT-07), reference text
  1.0 x 0.15 mm on the silk (CRAFT-02) and ${REFERENCE} on the fab layer (CRAFT-11), a filled
  pin-1 mark next to pin 1 (CRAFT-13: its centre outside the body and nearer to pin 1's land edge
  than to any other land's edge, the craft check's geometry), SMD anchor at the body centroid
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
import tomllib
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generic  # noqa: E402
import kigen  # noqa: E402

# Tests never inherit a hook's GIT_* variables (HL-64): under pre-commit, git exports GIT_DIR, GIT_INDEX_FILE and
# others, and a fixture's git would act on the repository being committed.
for _k in [k for k in os.environ if k.startswith("GIT_")]:
    del os.environ[_k]

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
    """A pad that is a land of the part: copper on an outer layer with a mask opening, or the
    copper-only SMD pad of a solder-mask-defined land (its opening is a separate aperture pad with
    the same number and no copper, which is not a land)."""
    if p["kind"] == "np_thru_hole":
        return False
    if any(l in ("F.Cu", "*.Cu") for l in p["layers"]) and any("Mask" in l for l in p["layers"]):
        return True
    return p["kind"] == "smd" and p["layers"] == ["F.Cu"]


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


def box_gap(x, y, r):
    return math.hypot(max(r[0] - x, 0, x - r[2]), max(r[1] - y, 0, y - r[3]))


def next_to_pin1(centre, body, lands, first):
    """CRAFT-13 "next to pin 1", as the craft standard states it and the board craft check applies it
    (tools hardware/tools/craft/pin1.py): the mark's centre lies outside the body and nearer to the edge
    of pin 1's land than to the edge of any other land; pads on one land are one land.
    lands: [(number, (x0, y0, x1, y1))]."""
    x, y = centre
    if body[0] + 1e-6 < x < body[2] - 1e-6 and body[1] + 1e-6 < y < body[3] - 1e-6:
        return False
    merged = {}
    for number, r in lands:
        merged.setdefault(tuple(round(v, 4) for v in r), set()).add(number)
    own = [box_gap(x, y, r) for r, numbers in merged.items() if first in numbers]
    others = [box_gap(x, y, r) for r, numbers in merged.items() if first not in numbers]
    return bool(own) and all(min(own) < g - 1e-6 for g in others)


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


# ---------------------------------------------------------------- datasheet pin tables

PIN_TABLE_KEYS = {"datasheet_rev", "cite", "pins"}


def pin_table_path(part):
    """generator/parts/<key>/pins/<part>.toml, next to the part's own data file."""
    d, f = os.path.split(part["_path"])
    return os.path.join(d, "pins", f)


def pin_table_errors(data, part):
    """Schema of a pin table file: datasheet_rev (the part's), cite (a page, table or drawing
    sheet), and [pins] mapping each pin number to its name, both non-empty strings."""
    errs = []
    if set(data) != PIN_TABLE_KEYS:
        errs.append("keys %s, expected %s" % (sorted(data), sorted(PIN_TABLE_KEYS)))
    if data.get("datasheet_rev") != part["part"].get("datasheet_rev"):
        errs.append("datasheet_rev differs from the part's")
    cite = data.get("cite")
    if not isinstance(cite, str) or not re.search(r"\bpp?\. \d|\bsheet \d|SCHEMATIC", cite):
        errs.append("cite names no page, table or drawing sheet: %r" % cite)
    pins = data.get("pins")
    if not isinstance(pins, dict) or not pins:
        errs.append("no [pins]")
    else:
        for n, name in pins.items():
            if not (n.strip() and isinstance(name, str) and name.strip()):
                errs.append("pin %r: empty number or name" % n)
    return errs


def load_pin_table(part):
    path = pin_table_path(part)
    if not os.path.exists(path):
        return None, path
    with open(path, "rb") as fh:
        return tomllib.load(fh), path


def norm(s):
    return re.sub(r"\s+", "", s.replace("~{", "").replace("}", "").replace("−", "-")).upper()


# ---------------------------------------------------------------- lifecycle and second sources (PLIB-003)

# The parts whose lifecycle or second sources were recorded when the fields were introduced
# (2026-10-27); each must keep the field. The data says "Not stated" or [] when the source said none.
LIFECYCLE_EXPECTED = {"SN74AUC1G74DCUR", "SN74LVC2G66DCUR", "TPS6286910CRQYR", "K4UBE3D4AB-MGCL"}
SECOND_SOURCES_EXPECTED = {"70-9258-001-120-006", "LBES5PL2EL-923", "NSC5083D-22.5792M", "SJ2-35954D-SMT-TR",
                           "LMR33630CRNXR", "SN74AUC1G74DCUR", "SN74AXC1T45DCKR", "SN74LVC2G66DCUR",
                           "TPS6286910CRQYR", "MT53E1G32D2FW-046 IT:C"}


# Product content the library data must not carry: BOM lines and versions, product ADRs, the
# T1's use of a part, a BOM's chosen alternative, a read of a board's files.
PRODUCT_CONTENT = re.compile(r"\bBOM v\d|\bBOM line|\bboard ADR\b|\bthe T1\b|\bOpenDAP T1\b|\bT1 (board|main board|pinout)"
                             r"|^second_source\s*=|\bboard_pinout\b")


def part_record_errors(pt):
    """Schema of [part] lifecycle = {status, source, read, note?} (source and read may be left out
    only with status "Not stated") and second_sources = [{part, note?}, ...] ([] = none found)."""
    errs = []
    lc = pt.get("lifecycle")
    if lc is not None:
        if not isinstance(lc, dict) or not set(lc) <= {"status", "source", "read", "note"}:
            errs.append("lifecycle: keys status, source, read, note")
        else:
            if not str(lc.get("status", "")).strip():
                errs.append("lifecycle: no status")
            if lc.get("status") != "Not stated":
                if not str(lc.get("source", "")).strip():
                    errs.append("lifecycle: no source")
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(lc.get("read", ""))):
                    errs.append("lifecycle: read is not a YYYY-MM-DD date")
    ss = pt.get("second_sources")
    if ss is not None:
        if not isinstance(ss, list):
            errs.append("second_sources: a list")
        else:
            for e in ss:
                if not isinstance(e, dict) or not set(e) <= {"part", "note"} or not str(e.get("part", "")).strip():
                    errs.append("second_sources: entries are {part, note?}: %r" % (e,))
    return errs


def all_part_records():
    """[part] tables of every generator part: generator/parts/ and generator/bga/."""
    out = [p["part"] for p in PARTS]
    for path in sorted(glob.glob(os.path.join(ROOT, "generator", "bga", "*", "*.toml"))):
        with open(path, "rb") as fh:
            out.append(tomllib.load(fh)["part"])
    return out


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


class Envelopes(unittest.TestCase):
    """envelopes.toml: every entry cites its source and has its STEP; bad entries are refused."""

    def test_every_envelope_has_its_step(self):
        for e in kigen.load_envelopes():
            with self.subTest(envelope=e["name"]):
                self.assertTrue(e["cite"].strip())
                step = os.path.join(ROOT, "3dmodels", e["key"] + ".3dshapes", e["name"] + ".step")
                self.assertTrue(os.path.exists(step), "missing %s: run generator/model.py" % step)

    def test_bad_entries_refused(self):
        import tempfile
        bad = [
            'version = 1\n[[envelope]]\nkey = "x"\nname = "A"\nland = "l"\nboxes = [{ size = [1, 1, 1], at = [0, 0, 0] }]\n',
            'version = 1\n[[envelope]]\nkey = "x"\nname = "A"\nland = "l"\ncite = "c"\nboxes = [{ size = [1, 0, 1], at = [0, 0, 0] }]\n',
            'version = 1\n' + '[[envelope]]\nkey = "x"\nname = "A"\nland = "l"\ncite = "c"\nboxes = [{ size = [1, 1, 1], at = [0, 0, 0] }]\n' * 2,
        ]
        for text in bad:
            with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as fh:
                fh.write(text)
            try:
                with self.assertRaises(ValueError):
                    kigen.load_envelopes(fh.name)
            finally:
                os.unlink(fh.name)


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

    def test_pins_match_datasheet(self):
        """Symbol pins against the datasheet's pin table, transcribed separately in pins/<part>.toml."""
        for part in PARTS:
            pt = part["part"]
            with self.subTest(part=pt["mpn"]):
                table, path = load_pin_table(part)
                if pt.get("sheet_pins", "").startswith("none:"):
                    self.assertIsNone(table, "%s exists but the part says sheet_pins = none" % path)
                    continue  # the datasheet has no pin table; the reason is recorded in the data
                self.assertIsNotNone(table, "no pin table: write %s or set sheet_pins = \"none: <reason>\"" % path)
                self.assertEqual(pin_table_errors(table, part), [], path)
                table = table["pins"]
                # pins the table does not list (switch and shell terminals) carry not_in_sheet with the reason
                mine = {p.get("sheet_number", p["number"]): p.get("sheet_name", p["name"])
                        for p in part["pins"] if not p.get("not_in_sheet")}
                self.assertEqual(sorted(mine), sorted(table), "pin numbers differ from %s" % path)
                for n, name in mine.items():
                    self.assertEqual(norm(name), norm(table[n]), "pin %s" % n)

    def test_pin_table_schema_rejects(self):
        part = {"part": {"datasheet_rev": "Rev A"}}
        good = {"datasheet_rev": "Rev A", "cite": "Table 2, p. 2", "pins": {"1": "A"}}
        self.assertEqual(pin_table_errors(good, part), [])
        for bad in ({**good, "extra": 1}, {**good, "datasheet_rev": "Rev B"}, {**good, "cite": "Table 2"},
                    {**good, "pins": {}}, {**good, "pins": {"1": ""}}):
            self.assertNotEqual(pin_table_errors(bad, part), [], bad)

    def test_pin_tables_belong_to_parts(self):
        known = {pin_table_path(p) for p in PARTS}
        for path in glob.glob(os.path.join(kigen.PARTS, "*", "pins", "*.toml")):
            self.assertIn(path, known, "pin table without a part data file")

    def test_lifecycle_and_second_sources(self):  # PLIB-003
        records = all_part_records()
        for pt in records:
            with self.subTest(part=pt["mpn"]):
                self.assertEqual(part_record_errors(pt), [])
        have_lc = {pt["mpn"] for pt in records if "lifecycle" in pt}
        have_ss = {pt["mpn"] for pt in records if "second_sources" in pt}
        self.assertEqual(LIFECYCLE_EXPECTED - have_lc, set(), "lifecycle missing")
        self.assertEqual(SECOND_SOURCES_EXPECTED - have_ss, set(), "second_sources missing")

    def test_no_product_content(self):  # libs README: a part's data says what the part is
        """No product content in the library data: no BOM line or version, no product ADR, no T1 use,
        no BOM choice (`second_source`), no read of a board's files. Those live with the board."""
        files = [f for f in glob.glob(os.path.join(HERE, "**", "*.toml"), recursive=True)]
        files.append(os.path.join(ROOT, "..", "parts", "manifest.toml"))
        for f in files:
            with open(f, encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    with self.subTest(file=os.path.relpath(f, ROOT), line=i):
                        self.assertIsNone(PRODUCT_CONTENT.search(line), line.strip())

    def test_no_product_content_pattern(self):
        for bad in ('second_source = "X (BOM v1 line 3)"', "# from board BOM v1.5", "matching BOM v1 line 127",
                    "the T1 fits it under board ADR 0022", "Codec (unused in the T1)", 'board_pinout = "x.csv"',
                    "the T1 configuration", "# replaced in the T1 by the X"):
            self.assertIsNotNone(PRODUCT_CONTENT.search(bad), bad)
        for good in ('second_sources = [{ part = "X" }]', "T1,VSS", "Housing UL94V-HB (drawing BOM items 13-14)",
                     "Maxim T1633-4 package"):
            self.assertIsNone(PRODUCT_CONTENT.search(good), good)

    def test_part_record_schema_rejects(self):
        good = {"lifecycle": {"status": "Active", "source": "TI product page", "read": "2026-10-24"},
                "second_sources": [{"part": "X1", "note": "same land"}]}
        self.assertEqual(part_record_errors(good), [])
        self.assertEqual(part_record_errors({"lifecycle": {"status": "Not stated"}, "second_sources": []}), [])
        for bad in ({"lifecycle": {"status": "Active"}},
                    {"lifecycle": {"status": "Active", "source": "TI", "read": "Oct 2026"}},
                    {"lifecycle": {"status": "Active", "source": "TI", "read": "2026-10-24", "stock": 5}},
                    {"second_sources": "X1"}, {"second_sources": [{"note": "no part"}]},
                    {"second_sources": [{"part": "X1", "price": "1"}]}):
            self.assertNotEqual(part_record_errors(bad), [], bad)

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
                # pin-1 mark (CRAFT-13): a filled silk polygon next to pin 1 (next_to_pin1)
                marks = [pl for pl in find(n, "fp_poly") if one(pl, "layer")[1] == "F.SilkS" and one(pl, "fill")[1] == "yes"]
                first = kigen.pin1_number(part)
                if any(p["number"] == first for p in lands):
                    self.assertTrue(marks, "no pin-1 mark")
                    pts = [(float(x[1]), float(x[2])) for x in find(one(marks[0], "pts"), "xy")]
                    centre = ((min(p[0] for p in pts) + max(p[0] for p in pts)) / 2,
                              (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2)
                    numbered = [(str(p["number"]), rect_of(p)) for p in lands if p["number"]]
                    self.assertTrue(next_to_pin1(centre, body, numbered, first), "pin-1 mark not next to pad %s" % first)
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


class Pin1Geometry(unittest.TestCase):
    """CRAFT-13 "next to pin 1" runs to the lands' edges: a long pin-1 land counts along its length."""

    def test_long_pin1_land(self):
        # TI RGX0011A (TPS62136RGXR): pin 1 is a 2.5 mm bar; its triangle sits past the bar's left end,
        # where pin 11's pad centre is nearer than pin 1's
        part = next(p for p in PARTS if p["part"]["mpn"] == "TPS62136RGXR")
        n, pads = read_fp(fp_path(part))
        _, body, _, _, _ = kigen.frame(part)
        mark = [pl for pl in find(n, "fp_poly") if one(pl, "layer")[1] == "F.SilkS" and one(pl, "fill")[1] == "yes"][0]
        pts = [(float(x[1]), float(x[2])) for x in find(one(mark, "pts"), "xy")]
        centre = ((min(p[0] for p in pts) + max(p[0] for p in pts)) / 2, (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2)
        lands = [(str(p["number"]), rect_of(p)) for p in pads if is_copper_pad(p) and p["number"]]
        self.assertTrue(next_to_pin1(centre, body, lands, "1"))
        by_centre = min(lands, key=lambda nr: math.hypot((nr[1][0] + nr[1][2]) / 2 - centre[0], (nr[1][1] + nr[1][3]) / 2 - centre[1]))
        self.assertNotEqual(by_centre[0], "1")

    def test_fails(self):
        body = (-0.5, -0.5, 0.5, 0.5)
        two = [("1", (-1.3, -0.3, -0.7, 0.3)), ("2", (0.7, -0.3, 1.3, 0.3))]
        self.assertFalse(next_to_pin1((0.0, -1.0), body, two, "1"))   # as near to pin 2: marks neither
        self.assertFalse(next_to_pin1((-0.4, 0.0), body, two, "1"))   # inside the body
        self.assertFalse(next_to_pin1((1.5, 0.0), body, two, "1"))    # at pin 2
        self.assertTrue(next_to_pin1((-1.5, 0.0), body, two, "1"))

    def test_pads_on_one_land(self):
        lands = [("A1", (-3.3, -0.6, -2.7, 0.6)), ("B12", (-3.3, -0.6, -2.7, 0.6)), ("A4", (-2.5, -0.6, -1.9, 0.6))]
        self.assertTrue(next_to_pin1((-3.0, -0.9), (-4.5, 0.5, 4.5, 7.5), lands, "A1"))


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


class PolyPads(unittest.TestCase):
    """The polygon pads (custom_pads.poly_pads) on an inline fixture: an L-shaped NSMD land, and a
    solder-mask-defined land as a copper-only pad plus a mask-and-paste aperture with the same
    number; bad outlines and anchors are refused."""
    L = [[-0.25, -0.3], [0.0, -0.3], [0.0, 0.3], [-0.6, 0.3], [-0.6, 0.05], [-0.25, 0.05]]
    FIXTURE = {"part": {"mpn": "FIXTURE", "library": "Fixture"}, "pins": [{"number": "1"}, {"number": "2"}],
               "footprint": {"name": "Fixture", "body": {"x": 3.0, "y": 3.0, "z": 1.0},
                             "polys": [{"number": "1", "layers": "smd", "anchor": [-0.6, -0.825],
                                        "points": [[x - 0.3, y - 1.0] for x, y in L]},
                                       {"number": "2", "layers": "copper", "anchor": [0.0, 0.9],
                                        "points": [[-0.5, 0.7], [0.5, 0.7], [0.5, 1.3], [-0.5, 1.3]]},
                                       {"number": "2", "layers": "aperture", "anchor": [0.0, 0.9],
                                        "points": [[-0.45, 0.75], [0.45, 0.75], [0.45, 1.25], [0.15, 1.25],
                                                   [0.15, 1.1], [-0.15, 1.1], [-0.15, 1.25], [-0.45, 1.25]]}]}}

    def pads(self):
        text, _ = kigen.footprint(self.FIXTURE)
        path = os.path.join(tempfile.mkdtemp(), "f.kicad_mod")
        with open(path, "w") as fh:
            fh.write(text)
        return read_fp(path)[1], parse(text)

    def outline(self, node):
        at = one(node, "at")
        x0, y0 = float(at[1]), float(at[2])
        return [(round(x0 + float(q[1]), 4), round(y0 + float(q[2]), 4))
                for q in find(one(one(one(node, "primitives"), "gr_poly"), "pts"), "xy")]

    def test_layers_and_outlines(self):
        pads, tree = self.pads()
        by = {(p["number"], tuple(p["layers"])): p for p in pads}
        self.assertEqual(sorted(by), [("1", ("F.Cu", "F.Mask", "F.Paste")), ("2", ("F.Cu",)),
                                      ("2", ("F.Mask", "F.Paste"))])
        nodes = {(n[1], tuple(str(x) for x in one(n, "layers")[1:])): n for n in find(tree, "pad")}
        self.assertEqual(self.outline(nodes[("1", ("F.Cu", "F.Mask", "F.Paste"))]),
                         [(round(x - 0.3, 4), round(y - 1.0, 4)) for x, y in self.L])
        cu, ap = nodes[("2", ("F.Cu",))], nodes[("2", ("F.Mask", "F.Paste"))]
        self.assertEqual(rect_of(by[("2", ("F.Cu",))]), (-0.5, 0.7, 0.5, 1.3))
        # the aperture is the drawn opening: no board-default mask expansion
        self.assertEqual(float(one(ap, "solder_mask_margin")[1]), 0.0)
        self.assertIsNone(one(cu, "solder_mask_margin"))
        # every aperture vertex lies 0.05 inside the copper
        for x, y in self.outline(ap):
            self.assertTrue(-0.45 - EPS <= x <= 0.45 + EPS and 0.75 - EPS <= y <= 1.25 + EPS)
        # the land check: the copper-only pad is pin 2's land, the aperture is not a second one
        lands = [p for p in pads if is_copper_pad(p)]
        self.assertEqual(sorted(p["number"] for p in lands), ["1", "2"])

    def test_bad_polys(self):
        poly = kigen.custom_pads.poly_pads
        sq = [[0, 0], [1, 0], [1, 1], [0, 1]]
        self.assertEqual(len(poly({"polys": [{"number": "1", "layers": "smd", "points": sq, "anchor": [0.5, 0.5]}]})), 1)
        for bad in ({"number": "1", "layers": "smd", "points": sq, "anchor": [1.5, 0.5]},        # anchor outside
                    {"number": "1", "layers": "smd", "points": sq, "anchor": [0.05, 0.5]},       # anchor over the edge
                    {"number": "1", "layers": "smd", "points": sq[:2], "anchor": [0.5, 0.5]},    # not a polygon
                    {"number": "1", "layers": "smd", "points": [[0, 0], [1, 0], [2, 0]], "anchor": [0.5, 0]},  # no area
                    {"number": "1", "layers": "smd", "points": [[0, 0], [1, 1], [1, 0], [0, 1]], "anchor": [0.5, 0.2]},  # crossed
                    {"number": "1", "layers": "paste", "points": sq, "anchor": [0.5, 0.5]}):     # unknown layer set
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                poly({"polys": [bad]})


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
