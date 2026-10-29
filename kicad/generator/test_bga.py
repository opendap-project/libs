#!/usr/bin/env python3
"""Second, independent reading of kicad-lib's BGA parts (generator/bga/).

Usage:
    python3 generator/test_bga.py [-v]        (Python 3.11 or later)

bga.py builds each part from its [[grid]] tables and pin list. This test does not import bga.py
and does not read [[grid]]: it parses the committed .kicad_mod and .kicad_sym files and checks them
against the other transcriptions of the same datasheet:

- the ball set: the ball-map figure transcribed cell by cell (<part>-ballmap.txt) against the pin
  list table (CSV), the footprint's pads and the symbol's pin numbers, and the ball count the
  datasheet states;
- every pad centre recomputed from the drawing's primary dimensions ([[drawing]]: body, edge-to-
  first-ball distances, outer-ball spans, pitch), with the row letters generated here (JEDEC: no
  I, O, Q, S, X, Z);
- every symbol pin name against the pin list; pin types valid; no hidden pins; alternates equal to
  the pad name's functions; Reference, Value, Footprint, Datasheet, Description, Manufacturer and
  MPN fields filled, the Footprint field naming a footprint that exists;
- the land against the prototype fab's limits (BGA pad >= 0.25 mm, mask web >= 3 mil, copper gap >= 0.065 mm,
  kicad-lib design-rules/pcbway-capabilities.md);
- the pin list re-extracted from the datasheet PDF itself when it is in the local parts cache and
  pdfplumber (or pdftotext) is installed ([check] pdf with pdf_pages, pdf_ballout_page or
  pdf_table_page); skipped otherwise;
- a partial pin table of the datasheet ([check] table_pins: same names, every pin outside
  table_ignore listed) and a reference design's transcription of the same ball map ([check]
  ref_pins, names normalised by ref_rename), when the part lists them;
- bga.py --check (outputs up to date), the STEP model present, and kicad-cli (KiCad 10) loading the
  libraries.
"""

from __future__ import annotations

import csv
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

# Tests never inherit a hook's GIT_* variables (HL-64): under pre-commit, git exports GIT_DIR, GIT_INDEX_FILE and
# others, and a fixture's git would act on the repository being committed.
for _k in [k for k in os.environ if k.startswith("GIT_")]:
    del os.environ[_k]

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "bga")
CACHE = os.path.expanduser("~/.cache/opendap/parts")


def cache_path(part, rel):
    """A file of the local parts cache, <cache>/<manufacturer>/<rel>: the folder follows the maker's display name,
    as parts-sync.py names it, not the library key."""
    return os.path.join(CACHE, re.sub(r"[^A-Za-z0-9._-]+", "-", part["part"]["manufacturer"]), rel)


KICAD_CLI = os.environ.get("KICAD_CLI") or next(
    (c for c in ("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli", shutil.which("kicad-cli") or "")
     if c and os.path.exists(c)), None)
EPS = 0.0005
PIN_TYPES = {"input", "output", "bidirectional", "tri_state", "passive", "free", "unspecified",
             "power_in", "power_out", "open_collector", "open_emitter", "no_connect"}


def jedec_rows(n):
    letters = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c not in "IOQSXZ"]
    out = list(letters)
    for a in letters:
        out += [a + b for b in letters]
    return out[:n]


def parts():
    for path in sorted(glob.glob(os.path.join(DATA, "*", "*.toml"))):
        with open(path, "rb") as fh:
            yield path, tomllib.load(fh)


def read_pins_csv(path):
    with open(path, newline="") as fh:
        return {r["ball"]: r["name"] for r in csv.DictReader(fh)}


def read_ballmap(path):
    """Ball map figure: rows 'XX |cells|', 'o' ball, '-' no ball. Core cells (prefix) follow the
    note in the file's header: the test reads the [[drawing]] tables for the core placement."""
    rows = []
    with open(path) as fh:
        for line in fh:
            if line.startswith("#") or "|" not in line:
                continue
            label, cells = line.split("|")[0].strip(), line.split("|")[1]
            rows.append((label, cells))
    return rows


def ballmap_set(rows, drawing):
    """Balls of every grid in the figure. The first [[drawing]] grid is the figure's own table;
    a second grid (a core drawn inside the table) is located by its first populated cell offsets
    given in the drawing ('map_col0', 'map_row0') or, by default, centred in the table."""
    main = drawing[0]
    labels = [r[0] for r in rows]
    assert labels == jedec_rows(main["rows"]), "ball-map row labels differ from the JEDEC sequence"
    balls = set()
    inner = drawing[1:] if len(drawing) > 1 else []
    in_inner = set()
    for g in inner:
        c0 = g.get("map_col0", (main["cols"] - g["cols"]) // 2)
        r0 = g.get("map_row0", (main["rows"] - g["rows"]) // 2)
        rl = jedec_rows(g["rows"])
        for ri in range(g["rows"]):
            for ci in range(g["cols"]):
                in_inner.add((r0 + ri, c0 + ci))
                if rows[r0 + ri][1][c0 + ci] == "o":
                    balls.add("%s%s%d" % (g["prefix"], rl[ri], ci + 1))
    for ri, (label, cells) in enumerate(rows):
        assert len(cells) == main["cols"], "row %s has %d cells" % (label, len(cells))
        for ci, ch in enumerate(cells):
            if (ri, ci) in in_inner:
                continue
            assert ch in "o- ", "row %s: bad cell %r" % (label, ch)
            if ch == "o":
                balls.add("%s%s%d" % (main["prefix"], label, ci + 1))
    return balls


def expected_xy(part):
    pk = part["package"]
    out = {}
    for g in part["drawing"]:
        rl = jedec_rows(g["rows"])
        x0 = -pk["body_x"] / 2 + g["edge_x"]
        y0 = -pk["body_y"] / 2 + g["edge_y"]
        px, py = g.get("pitch_x", g.get("pitch")), g.get("pitch_y", g.get("pitch"))
        if "span_x" in g:  # the outer-ball spans must agree with pitch and count
            assert abs(g["span_x"] - (g["cols"] - 1) * px) < EPS
            assert abs(g["span_y"] - (g["rows"] - 1) * py) < EPS
            assert abs(x0 + g["span_x"] / 2) < EPS and abs(y0 + g["span_y"] / 2) < EPS, "grid not centred"
        for ri in range(g["rows"]):
            for ci in range(g["cols"]):
                out["%s%s%d" % (g["prefix"], rl[ri], ci + 1)] = (x0 + ci * px, y0 + ri * py)
    return out


def parse_footprint(path):
    with open(path) as fh:
        text = fh.read()
    pads = {}
    for m in re.finditer(r'\(pad "([^"]+)" smd circle \(at ([-\d.]+) ([-\d.]+)\) \(size ([\d.]+) ([\d.]+)\)'
                         r'(.*?)\(uuid', text):
        rest = m.group(6)
        mm = re.search(r"\(solder_mask_margin ([\d.]+)\)", rest)
        pads[m.group(1)] = dict(x=float(m.group(2)), y=float(m.group(3)), d=float(m.group(4)),
                                d2=float(m.group(5)), bga="pad_prop_bga" in rest,
                                mask=float(mm.group(1)) if mm else None)
    return text, pads


def parse_symbols(path):
    """symbol name -> {fields, pins: {number: (name, type, hidden, alternates)}}"""
    with open(path) as fh:
        text = fh.read()
    syms = {}
    for m in re.finditer(r'\n\t\(symbol "([^"]+)"\n(.*?)\n\t\)', text, re.S):
        name, body = m.group(1), m.group(2)
        fields = dict(re.findall(r'\(property "([^"]+)" "([^"]*)"', body))
        pins = {}
        for pm in re.finditer(r'\(pin (\w+) line (.*?)\(name "((?:[^"\\]|\\.)*)" .*?\(number "([^"]+)" [^\n]*', body):
            line = pm.group(0)
            alts = re.findall(r'\(alternate "([^"]+)" (\w+) line\)', line)
            pins[pm.group(4)] = (pm.group(3), pm.group(1), "(hide yes)" in line, alts)
        syms[name] = dict(fields=fields, pins=pins, units=len(re.findall(r'\(unit_name "', body)))
    return syms


def pdf_pinlist(pdf, first, last):
    import pdfplumber  # optional dependency
    out = {}
    with pdfplumber.open(pdf) as doc:
        for pn in range(first, last + 1):
            for t in doc.pages[pn - 1].extract_tables():
                for r in t:
                    if len(r) != 4:
                        continue
                    for name, pin in ((r[0], r[1]), (r[2], r[3])):
                        if pin and re.fullmatch(r"1?[A-Z]{1,2}\d{1,2}", pin.strip()):
                            out[pin.strip()] = (name or "").replace("\n", "")
    return out


def pdf_ballout(pdf, page, cols):
    """Ballout grid table (rows of names under a row letter) re-read from the PDF's text layer with
    poppler's pdftotext; 'NB' (no ball) cells are dropped, footnote marks ('1)') stripped. 'cols'
    is the column count, or the list of column numbers when the figure prints no cell for the
    columns without balls."""
    txt = subprocess.run(["pdftotext", "-layout", "-f", str(page), "-l", str(page), pdf, "-"],
                         capture_output=True, text=True, check=True).stdout
    colnums = list(range(1, cols + 1)) if isinstance(cols, int) else list(cols)
    out = {}
    for line in txt.splitlines():
        m = re.match(r"\s*([A-Z]{1,2})\s{2,}(\S.*)$", line)
        if not m:
            continue
        toks = [re.sub(r"\d\)$", "", t) for t in m.group(2).split()]
        if len(toks) != len(colnums):
            continue
        for c, t in zip(colnums, toks):
            if t != "NB":
                out["%s%d" % (m.group(1), c)] = t
    return out


def pdf_two_column_table(pdf, page):
    import pdfplumber  # optional dependency
    out = {}
    with pdfplumber.open(pdf) as doc:
        for t in doc.pages[page - 1].extract_tables():
            for r in t:
                if len(r) == 2 and r[0] and re.fullmatch(r"[A-Z]{1,2}\d{1,2}", r[0].strip()):
                    out[r[0].strip()] = (r[1] or "").replace("\n", " ").strip()
    return out


def read_pairs(path):
    with open(path, newline="") as fh:
        return {r["ball"]: r["name"] for r in csv.DictReader(fh)}


class BgaParts(unittest.TestCase):

    def test_parts(self):
        found = list(parts())
        self.assertTrue(found, "no part under generator/bga/")
        for path, part in found:
            with self.subTest(part=part["part"]["symbol"]):
                self.check_part(path, part)

    def check_part(self, path, part):
        d = os.path.dirname(path)
        pt, pk, land = part["part"], part["package"], part["land"]
        lib = pt["library"]
        csvpins = read_pins_csv(os.path.join(d, pt["pins"]))
        mapballs = ballmap_set(read_ballmap(os.path.join(d, pt["ballmap"])), part["drawing"])
        fp_path = os.path.join(ROOT, "footprints", lib + ".pretty", part["footprint"]["name"] + ".kicad_mod")
        fptext, pads = parse_footprint(fp_path)
        syms = parse_symbols(os.path.join(ROOT, "symbols", lib + ".kicad_sym"))
        self.assertIn(pt["symbol"], syms)
        sym = syms[pt["symbol"]]

        # 1. the ball set, four ways, and the stated count
        n = part["check"]["balls"]
        self.assertEqual(len(mapballs), n, "ball-map figure count")
        self.assertEqual(len(csvpins), n, "pin-list count")
        self.assertEqual(set(csvpins), mapballs, "pin list vs ball-map figure")
        self.assertEqual(set(pads), mapballs, "footprint pads vs ball-map figure")
        self.assertEqual(set(sym["pins"]), mapballs, "symbol pin numbers vs ball-map figure")

        # 2. every pad centre from the drawing's primary dimensions
        exp = expected_xy(part)
        for b, p in pads.items():
            ex, ey = exp[b]
            self.assertAlmostEqual(p["x"], ex, delta=EPS, msg="pad %s x" % b)
            self.assertAlmostEqual(p["y"], ey, delta=EPS, msg="pad %s y" % b)
        # A1 corner top left, anchor at the body centre (CRAFT-15)
        xs = [p["x"] for p in pads.values()]
        ys = [p["y"] for p in pads.values()]
        self.assertAlmostEqual(min(xs) + max(xs), 0, delta=EPS)
        self.assertAlmostEqual(min(ys) + max(ys), 0, delta=EPS)
        first = min(pads, key=lambda b: (pads[b]["y"], pads[b]["x"]))
        self.assertRegex(first, r"^A1$|^A\d+$")

        # 3. symbol pins against the pin list
        for b, (name, typ, hidden, alts) in sym["pins"].items():
            self.assertEqual(name, csvpins[b], "pin %s name" % b)
            self.assertIn(typ, PIN_TYPES)
            self.assertFalse(hidden, "pin %s hidden" % b)
            want = [] if "/" not in name or typ == "power_in" else \
                list(dict.fromkeys(a for a in name.split("/") if a and a != "-"))
            if len(want) < 2:
                want = []
            self.assertEqual([a for a, _ in alts], want, "pin %s alternates" % b)
        f = sym["fields"]
        for k in ("Reference", "Value", "Footprint", "Datasheet", "Description", "Manufacturer", "MPN"):
            self.assertTrue(f.get(k), "field %s empty" % k)
        self.assertTrue(f["Datasheet"].startswith("https://"))
        self.assertEqual(f["Footprint"], "%s:%s" % (lib, part["footprint"]["name"]))
        self.assertEqual(f["MPN"], pt["mpn"])
        self.assertGreater(sym["units"], 0)

        # 4. land against the prototype fab's limits
        for b, p in pads.items():
            self.assertTrue(p["bga"], "pad %s without the BGA property" % b)
            self.assertGreaterEqual(p["d"], 0.25 - EPS, "pad %s below the prototype fab's 0.25 mm BGA pad" % b)
            self.assertEqual(p["d"], p["d2"])
            self.assertIsNotNone(p["mask"])
        pts = sorted((p["x"], p["y"], p["d"], p["mask"]) for p in pads.values())
        min_gap, min_web = 9.0, 9.0
        for i, (x1, y1, d1, m1) in enumerate(pts):
            for x2, y2, d2, m2 in pts[i + 1:]:
                if x2 - x1 > 1.0:
                    break
                c = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                min_gap = min(min_gap, c - (d1 + d2) / 2)
                min_web = min(min_web, c - (d1 + d2) / 2 - m1 - m2)
        self.assertGreaterEqual(min_gap, 0.065 - EPS, "copper gap")
        self.assertGreaterEqual(min_web, 0.0762 - 0.0015, "mask web below 3 mil")
        self.assertIn('(model "${OPENDAP_KICAD_3DMODELS}/%s.3dshapes/%s.step"' % (
            lib, part["footprint"]["name"]), fptext)
        self.assertTrue(os.path.exists(os.path.join(
            ROOT, "3dmodels", lib + ".3dshapes", part["footprint"]["name"] + ".step")), "STEP missing")

        # 5. optional third reading: the datasheet PDF
        chk = part["check"]
        pdf = cache_path(part, chk["pdf"]) if chk.get("pdf") else None
        if pdf and os.path.exists(pdf):
            try:
                import pdfplumber  # noqa: F401
            except ImportError:
                print("skip: pdfplumber not installed (PDF re-extraction)", file=sys.stderr)
            else:
                with open(pdf, "rb") as fh:
                    self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), chk["pdf_sha256"])
                if chk.get("pdf_pages"):
                    fromp = pdf_pinlist(pdf, *chk["pdf_pages"])
                    self.assertEqual(fromp, csvpins, "pin list CSV vs the datasheet PDF")
                if chk.get("pdf_table_page") and chk.get("table_pins"):
                    fromp = pdf_two_column_table(pdf, chk["pdf_table_page"])
                    self.assertEqual(fromp, read_pairs(os.path.join(d, chk["table_pins"])),
                                     "pin table CSV vs the datasheet PDF")
            if chk.get("pdf_ballout_page"):
                if shutil.which("pdftotext"):
                    fromp = pdf_ballout(pdf, chk["pdf_ballout_page"],
                                        chk.get("pdf_ballout_cols", part["drawing"][0]["cols"]))
                    self.assertEqual(fromp, csvpins, "pin list CSV vs the datasheet PDF ballout")
                else:
                    print("skip: pdftotext not installed (PDF ballout re-extraction)", file=sys.stderr)
        elif pdf:
            print("skip: %s not in the parts cache" % chk["pdf"], file=sys.stderr)
        # a pin table that lists part of the balls (e.g. the named ones): same names, and every
        # pin outside 'table_ignore' listed
        if chk.get("table_pins"):
            tab = read_pairs(os.path.join(d, chk["table_pins"]))
            for b, nm in tab.items():
                self.assertEqual(csvpins.get(b), nm, "pin table ball %s" % b)
            ign = chk.get("table_ignore", "^$")
            self.assertEqual({b for b, nm in csvpins.items() if not re.search(ign, nm)}, set(tab),
                             "pins missing from the pin table")
        # a reference design's transcription of the same (JEDEC) ball map, names normalised
        if chk.get("ref_pins"):
            ref = read_pairs(os.path.join(d, chk["ref_pins"]))
            for pat, rep in chk.get("ref_rename", []):
                ref = {b: re.sub(pat, rep, nm) for b, nm in ref.items()}
            self.assertEqual(ref, csvpins, "reference schematic vs the pin list")

    def test_up_to_date(self):
        r = subprocess.run([sys.executable, os.path.join(HERE, "bga.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipUnless(KICAD_CLI, "kicad-cli not found")
    def test_kicad_loads(self):
        libs = {p["part"]["library"] for _, p in parts()}
        with tempfile.TemporaryDirectory() as tmp:
            for lib in sorted(libs):
                r = subprocess.run([KICAD_CLI, "fp", "upgrade", "--force", "-o", os.path.join(tmp, lib + ".pretty"),
                                    os.path.join(ROOT, "footprints", lib + ".pretty")], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                r = subprocess.run([KICAD_CLI, "sym", "export", "svg", "-o", os.path.join(tmp, lib),
                                    os.path.join(ROOT, "symbols", lib + ".kicad_sym")], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertTrue(glob.glob(os.path.join(tmp, lib, "*.svg")))


if __name__ == "__main__":
    unittest.main()
