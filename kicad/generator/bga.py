#!/usr/bin/env python3
"""Generate kicad-lib's BGA parts (symbol, footprint, 3D model data) from transcribed datasheet data.

Usage:
    python3 generator/bga.py [--check] [PART.toml ...]      (Python 3.11 or later)

Each part is generator/bga/<Library>/<Part>.toml (geometry, land, units, pin types, each value with
its datasheet page) plus a pin list CSV (ball, name, io_domain, source page). With no argument, every
part under generator/bga/ is built. The script writes:

    symbols/<Library>.kicad_sym                     every BGA part of the library, one multi-unit
                                                    symbol each (Manufacturer and MPN fields)
    footprints/<Library>.pretty/<footprint>.kicad_mod
    generator/bga/<Library>/<footprint>.model.json  body and balls for generator/bga_model.py (STEP)

Conventions, shared with generator/kigen.py: the KiCad Library Conventions (KLC) and kicad-lib's
PCB craft standard. Anchor at the body centre and ball A1 top left (CRAFT-15); silk 0.15 mm
(CRAFT-05) and clear of pads; filled pin-1 triangle outside the body (CRAFT-13); fab outline
0.10 mm with a pin-1 chamfer and ${REFERENCE} (KLC F5.2); courtyard 0.05 mm, 1.0 mm from the body
for a BGA (KLC F5.3). Pads carry the BGA fabrication property, which the fab rule sets key on.

Symbols: one unit per function or IO power domain; inputs left, outputs and passives right,
bidirectional left, supplies on top, grounds at the bottom; no hidden pins; each pin keeps the
datasheet's full pad name, and a multiplexed pad lists its functions as KiCad alternates.

--check regenerates in memory and exits 1 if a committed file differs. Output is byte-stable
(UUIDs derived from names).
"""

from __future__ import annotations

import csv
import glob
import json
import math
import os
import re
import sys
import tomllib
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "generator", "bga")
FP_VERSION = "20260206"
SYM_VERSION = "20251024"
GENERATOR = "opendap-bga"
MODEL_PATH = "${KIPRJMOD}/../lib/opendap/3dmodels/%s.3dshapes/%s.step"
NS = uuid.UUID("6f1d3a52-5b8e-4f43-9a51-0d1a0c3f0b7e")

SILK_W, SILK_PAD_CLR, FAB_W, CRT_W, CRT_BGA = 0.15, 0.15, 0.10, 0.05, 1.0
G, PIN_LEN, FONT = 2.54, 2.54, 1.27
PIN_LEN_MAX = 7.62


def pin_length(balls):
    """One pin length per symbol (CRAFT-121), as kigen.pin_length: 2.54 mm plus 1.27 mm per
    ball-name character beyond the first, at most 7.62 mm, so a ball name ("AA38") stays clear of
    the pin name and of a no-connect flag on the pin end."""
    longest = max([len(b) for b in balls] + [1])
    return min(PIN_LEN + 1.27 * (longest - 1), PIN_LEN_MAX)


def grid_pad(length):
    """Body half-size growth that keeps the pin ends on the 2.54 mm grid (CRAFT-122)."""
    return round((-length) % G, 6) % G


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def n(v):
    v = round(float(v), 4)
    if v == 0:
        v = 0.0
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return s


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


# ------------------------------------------------------------------ data

def load(path):
    with open(path, "rb") as fh:
        part = tomllib.load(fh)
    d = os.path.dirname(path)
    with open(os.path.join(d, part["part"]["pins"]), newline="") as fh:
        part["pinlist"] = list(csv.DictReader(fh))
    part["dir"] = d
    return part


def ball_xy(part):
    """Ball name -> (x, y) in mm from the grid definitions."""
    out = {}
    for g in part["grid"]:
        for ri, r in enumerate(g["rows"]):
            for c in range(1, g["cols"] + 1):
                name = "%s%s%d" % (g["prefix"], r, c)
                pitch_x = g.get("pitch_x", g.get("pitch"))
                pitch_y = g.get("pitch_y", g.get("pitch"))
                out[name] = (round(g["first_x"] + (c - 1) * pitch_x, 4),
                             round(g["first_y"] + ri * pitch_y, 4))
    return out


def pads(part):
    xy = ball_xy(part)
    res = []
    for row in part["pinlist"]:
        b = row["ball"]
        if b not in xy:
            raise ValueError("%s: ball %s is outside every grid" % (part["part"]["symbol"], b))
        res.append((b, xy[b]))
    if len({b for b, _ in res}) != len(res):
        raise ValueError("duplicate ball")
    return res


# ------------------------------------------------------------------ footprint

def font(size, thick):
    return "(effects (font (size %s %s) (thickness %s)))" % (n(size), n(size), n(thick))


def footprint(part):
    fp, pk, land = part["footprint"], part["package"], part["land"]
    name = fp["name"]
    bx, by = pk["body_x"] / 2, pk["body_y"] / 2
    pl = pads(part)
    out = []
    w = out.append
    w("(footprint %s" % q(name))
    w("\t(version %s)" % FP_VERSION)
    w("\t(generator %s)" % q(GENERATOR))
    w("\t(layer \"F.Cu\")")
    descr = "%s %s, %s, %d balls, %s land %s mm (mask opening %s mm), %s" % (
        part["part"]["manufacturer"], pk["name"], "%sx%s mm" % (n(pk["body_x"]), n(pk["body_y"])),
        len(pl), land["type"], n(land["pad"]), n(land["pad"] + 2 * land["mask_margin"]),
        fp.get("source", part["part"]["datasheet"]))
    w("\t(descr %s)" % q(descr))
    w("\t(tags %s)" % q(fp["tags"]))
    crt = (math.ceil((bx + CRT_BGA) * 100 - 1e-9) / 100, math.ceil((by + CRT_BGA) * 100 - 1e-9) / 100)

    def prop(k, v, at, layer, hide):
        h = " (hide yes)" if hide else ""
        return "\t(property %s %s (at %s %s 0) (layer %s)%s (uuid %s) %s)" % (
            q(k), q(v), n(at[0]), n(at[1]), q(layer), h, q(uid(name, "prop", k)), font(1.0, 0.15))
    w(prop("Reference", "REF**", (0, -crt[1] - 0.8), "F.SilkS", False))
    w(prop("Value", name, (0, crt[1] + 0.8), "F.Fab", False))
    w(prop("Datasheet", fp.get("source", part["part"]["datasheet"]), (0, 0), "F.Fab", True))
    w(prop("Description", descr, (0, 0), "F.Fab", True))
    w("\t(attr smd)")
    w("\t(duplicate_pad_numbers_are_jumpers no)")
    k = [0]

    def gline(a, b, layer, width):
        k[0] += 1
        w("\t(fp_line (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (layer %s) (uuid %s))" % (
            n(a[0]), n(a[1]), n(b[0]), n(b[1]), n(width), q(layer), q(uid(name, "g", k[0]))))

    def gpoly(pts, layer, width, fill):
        k[0] += 1
        w("\t(fp_poly (pts %s) (stroke (width %s) (type solid)) (fill %s) (layer %s) (uuid %s))" % (
            " ".join("(xy %s %s)" % (n(x), n(y)) for x, y in pts), n(width), "yes" if fill else "no",
            q(layer), q(uid(name, "g", k[0]))))

    # silk: body outline 0.1 mm outside the body (the outer balls are 0.35 mm or more inside it,
    # so the stroke stays clear of every pad), corner brackets, open at the A1 corner for the mark
    o = 0.1 + SILK_W / 2
    sx, sy = bx + o, by + o
    arm = 1.5
    for cx, cy in ((1, 1), (1, -1), (-1, 1)):
        gline((cx * sx, cy * sy), (cx * sx - cx * arm, cy * sy), "F.SilkS", SILK_W)
        gline((cx * sx, cy * sy), (cx * sx, cy * sy - cy * arm), "F.SilkS", SILK_W)
    gline((-sx + 0.6, -sy), (-sx + arm, -sy), "F.SilkS", SILK_W)
    gline((-sx, -sy + 0.6), (-sx, -sy + arm), "F.SilkS", SILK_W)
    # pin-1 mark: filled triangle outside the body, at the A1 corner, pointing at it
    t = -sx - 0.1
    gpoly([(t - 0.0, -sy - 0.1), (t - 0.6, -sy - 0.1), (t - 0.0, -sy + 0.5)], "F.SilkS", 0, True)
    # fab: body with a 1 mm chamfer at A1
    c = 1.0
    gpoly([(-bx + c, -by), (bx, -by), (bx, by), (-bx, by), (-bx, -by + c)], "F.Fab", FAB_W, False)
    k[0] += 1
    w("\t(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer \"F.CrtYd\") (uuid %s))" % (
        n(-crt[0]), n(-crt[1]), n(crt[0]), n(crt[1]), n(CRT_W), q(uid(name, "crt"))))
    w("\t(fp_text user \"${REFERENCE}\" (at 0 0 0) (layer \"F.Fab\") (uuid %s) %s)" % (
        q(uid(name, "fabref")), font(1.0, 0.15)))
    for b, (x, y) in pl:
        w("\t(pad %s smd circle (at %s %s) (size %s %s) (property pad_prop_bga) (layers \"F.Cu\" \"F.Mask\" \"F.Paste\") (solder_mask_margin %s) (uuid %s))" % (
            q(b), n(x), n(y), n(land["pad"]), n(land["pad"]), n(land["mask_margin"]), q(uid(name, "pad", b))))
    w("\t(embedded_fonts no)")
    w("\t(model %s (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))" % q(
        MODEL_PATH % (part["part"]["library"], name)))
    w(")")
    model = {"name": name, "library": part["part"]["library"],
             "body": [pk["body_x"], pk["body_y"], round(pk["height_nom"] - pk["standoff_nom"], 4)],
             "standoff": pk["standoff_nom"], "ball": pk["ball_nom"],
             "balls": [[x, y] for _, (x, y) in pl],
             "source": "envelope from %s" % pk["cite"]}
    return "\n".join(out) + "\n", model


# ------------------------------------------------------------------ symbol

def classify(part):
    """Pin rows with unit index (1-based) and electrical type. A [[unit]] rule matches by pin name
    (name_re), IO power domain (domain_re) or ball (ball_re, optionally narrowed by pin_re: splits a
    large group of same-named balls, such as NC, below CRAFT-126's 64 pins per unit); first match wins."""
    units = part["unit"]
    res = []
    for row in part["pinlist"]:
        nm, dom = row["name"], row.get("io_domain", "")
        u = None
        for i, rule in enumerate(units, 1):
            if "name_re" in rule and re.search(rule["name_re"], nm):
                u = i
                break
            if "domain_re" in rule and dom and re.search(rule["domain_re"], dom):
                u = i
                break
            if "ball_re" in rule and re.search(rule["ball_re"], row["ball"]) and (
                    "pin_re" not in rule or re.search(rule["pin_re"], nm)):
                u = i
                break
        if u is None:
            raise ValueError("pin %s %s matches no unit" % (row["ball"], nm))
        t = next(r["type"] for r in part["ptype"] if re.search(r["name_re"], nm))
        res.append(dict(row, unit=u, type=t))
    return res


def is_ground(p):
    return p["type"] == "power_in" and "VSS" in p["name"]


def side(p):
    if p["type"] == "power_in":
        return "bottom" if is_ground(p) else "top"
    if p["type"] in ("output", "passive", "power_out", "tri_state"):
        return "right"
    return "left"


def alternates(p):
    if "/" not in p["name"] or p["type"] == "power_in":
        return []
    seen, out = set(), []
    for a in p["name"].split("/"):
        a = a.strip()
        if a and a != "-" and a not in seen:
            seen.add(a)
            out.append(a)
    return out if len(out) > 1 else []


def tlen(s):
    # stroke-font advance of an upper-case name, measured on kicad-cli plots: about 0.91 x the
    # text size per character (1.16 mm at 1.27 mm); a smaller factor lets left and right pin
    # names meet inside the body
    return len(s) * FONT * 0.915


def natural(b):
    m = re.fullmatch(r"(\d?)([A-Z]+)(\d+)", b)
    return (m.group(1), len(m.group(2)), m.group(2), int(m.group(3)))


def pin_sort(p):
    return (natural_name(p["name"]), natural(p["ball"]))


def natural_name(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def pin_text(p, x, y, ang, length=PIN_LEN, indent="\t\t\t"):
    eff = "(effects (font (size %s %s)))" % (n(FONT), n(FONT))
    s = "%s(pin %s line (at %s %s %d) (length %s) (name %s %s) (number %s %s)" % (
        indent, p["type"], n(x), n(y), ang, n(length), q(p["name"]), eff, q(p["ball"]), eff)
    alts = alternates(p)
    if alts:
        s += "".join(" (alternate %s %s line)" % (q(a), p["type"]) for a in alts)
    return s + ")"


def unit_geometry(pins, length=PIN_LEN):
    sides = {"left": [], "right": [], "top": [], "bottom": []}
    for p in sorted(pins, key=pin_sort):
        sides[side(p)].append(p)
    rows = max(len(sides["left"]), len(sides["right"]), 1)
    cols = max(len(sides["top"]), len(sides["bottom"]), 0)
    lw = max([tlen(p["name"]) for p in sides["left"]] + [0])
    rw = max([tlen(p["name"]) for p in sides["right"]] + [0])
    top_res = max([tlen(p["name"]) for p in sides["top"]] + [-G]) + G
    bot_res = max([tlen(p["name"]) for p in sides["bottom"]] + [-G]) + G
    width = max(lw + rw + 2 * G, (cols + 1) * G, 6 * G)
    width = math.ceil(width / (2 * G) - 1e-9) * 2 * G
    height = top_res + bot_res + (rows + 1) * G
    height = math.ceil(height / (2 * G) - 1e-9) * 2 * G
    hw, hh = width / 2 + grid_pad(length), height / 2 + grid_pad(length)
    placed = []
    y0 = math.floor((hh - top_res - G) / G + 1e-9) * G
    for s, x, ang in (("left", -hw - length, 0), ("right", hw + length, 180)):
        for i, p in enumerate(sides[s]):
            placed.append((p, x, y0 - i * G, ang))
    for s, y, ang in (("top", hh + length, 270), ("bottom", -hh - length, 90)):
        cnt = len(sides[s])
        x0 = -math.floor((cnt - 1) / 2) * G
        for i, p in enumerate(sides[s]):
            placed.append((p, x0 + i * G, y, ang))
    return hw, hh, placed


def symbol(part):
    pt = part["part"]
    name = pt["symbol"]
    pins = classify(part)
    fpname = "%s:%s" % (pt["library"], part["footprint"]["name"])
    geos = []
    length = pin_length(p["ball"] for p in pins)
    for i, u in enumerate(part["unit"], 1):
        up = [p for p in pins if p["unit"] == i]
        if not up:
            raise ValueError("%s: unit %s has no pins" % (name, u["name"]))
        geos.append((u, unit_geometry(up, length)))
    hw, hh, _ = geos[0][1]
    ty = hh + length + 1.27 + max([tlen(p["name"]) for p, _, _, a in geos[0][1][2] if a == 270] + [0])
    out = []
    w = out.append
    w("\t(symbol %s" % q(name))
    w("\t\t(pin_names (offset 1.016))")
    w("\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes)")
    w("\t\t(duplicate_pin_numbers_are_jumpers no)")
    eff = "(effects (font (size 1.27 1.27))"

    def prop(k, v, at, hide=True, justify=None):
        j = " (justify %s)" % justify if justify else ""
        h = " (hide yes)" if hide else ""
        w("\t\t(property %s %s (at %s %s 0)%s %s%s))" % (q(k), q(v), n(at[0]), n(at[1]), h, eff, j))
    prop("Reference", pt.get("reference", "U"), (-hw, math.ceil(ty / 1.27) * 1.27), False, "left")
    if 2 * hw >= tlen(pt.get("reference", "U") + "??") + tlen(name) + G:
        prop("Value", name, (hw, math.ceil(ty / 1.27) * 1.27), False, "right")
    else:  # narrow first unit: the value above the reference, so the two never overlap
        prop("Value", name, (-hw, math.ceil(ty / 1.27) * 1.27 + G), False, "left")
    prop("Footprint", fpname, (0, 0))
    prop("Datasheet", pt["datasheet"], (0, 0))
    prop("Description", pt["description"], (0, 0))
    prop("Manufacturer", pt["manufacturer"], (0, 0))
    prop("MPN", pt["mpn"], (0, 0))
    prop("ki_keywords", pt.get("keywords", ""), (0, 0))
    prop("ki_fp_filters", part["footprint"]["name"] + "*", (0, 0))
    for i, (u, (uhw, uhh, placed)) in enumerate(geos, 1):
        w("\t\t(symbol %s" % q("%s_%d_1" % (name, i)))
        w("\t\t\t(unit_name %s)" % q(u["name"]))
        w("\t\t\t(rectangle (start %s %s) (end %s %s) (stroke (width 0.254) (type default)) (fill (type background)))" % (
            n(-uhw), n(uhh), n(uhw), n(-uhh)))
        for p, x, y, ang in placed:
            w(pin_text(p, x, y, ang, length))
        w("\t\t)")
    w("\t\t(embedded_fonts no)")
    w("\t)")
    return "\n".join(out)


def symbol_lib(parts):
    body = "\n".join(symbol(p) for p in sorted(parts, key=lambda p: p["part"]["symbol"]))
    return "(kicad_symbol_lib\n\t(version %s)\n\t(generator %s)\n\t(generator_version \"10.0\")\n%s\n)\n" % (
        SYM_VERSION, q(GENERATOR), body)


# ------------------------------------------------------------------ build

def outputs(paths):
    parts = [load(p) for p in paths]
    files = {}
    libs = {}
    models = {}
    for p in parts:
        libs.setdefault(p["part"]["library"], []).append(p)
        text, model = footprint(p)
        lib = p["part"]["library"]
        fpath = os.path.join("footprints", lib + ".pretty", p["footprint"]["name"] + ".kicad_mod")
        if files.get(fpath, text) != text:
            raise ValueError("parts sharing footprint %s generate different footprints" % fpath)
        files[fpath] = text
        # parts sharing a footprint (one package, several heights): the model is their envelope
        mpath = os.path.join("generator", "bga", lib, p["footprint"]["name"] + ".model.json")
        if mpath in models and models[mpath]["body"][2] >= model["body"][2]:
            model = models[mpath]
        models[mpath] = model
        files[mpath] = json.dumps(model, indent=1) + "\n"
    for lib, ps in libs.items():
        files[os.path.join("symbols", lib + ".kicad_sym")] = symbol_lib(ps)
    return files


def part_paths(argv):
    return argv or sorted(glob.glob(os.path.join(DATA, "*", "*.toml")))


def main(argv):
    check = "--check" in argv
    argv = [a for a in argv if a != "--check"]
    files = outputs(part_paths(argv))
    bad = 0
    for rel, text in sorted(files.items()):
        path = os.path.join(ROOT, rel)
        old = open(path).read() if os.path.exists(path) else None
        if check:
            if old != text:
                print("stale: %s" % rel)
                bad = 1
        elif old != text:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                fh.write(text)
            print("wrote %s" % rel)
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
