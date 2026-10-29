#!/usr/bin/env python3
"""Generate kicad-lib symbols, footprints and 3D envelope models from part data files.

Usage:
    kigen.py [--check] [--out DIR] [PART.toml ...]

Each part is one TOML file under generator/parts/<key>/ (schema: generator/README.md). Every
dimension in it cites the manufacturer document and page it was transcribed from. The generator
writes:

    symbols/<key>.kicad_sym                     one symbol per part (Manufacturer and MPN fields)
    footprints/<key>.pretty/<name>.kicad_mod     one footprint per distinct footprint name
    generator/models/<key>/<name>.json          the envelope boxes for generator/model.py (STEP)

and, from generator/envelopes.toml, the envelope boxes of lands the library does not draw (KiCad
stock footprints without a KiCad 10 model, project lands of OpenDAP boards).

Conventions (kicad-lib docs/specs/pcb-craft-standard.md and the KiCad Library Conventions, KLC):
SMD anchor at the body centroid, THT anchor at pin 1 (CRAFT-15); silk 0.15 mm stroke (CRAFT-05),
0.15 mm clear of pads (CRAFT-07), reference 1.0 x 0.15 mm (CRAFT-02); filled pin-1 triangle without
stroke, outside the body (CRAFT-13); fab body outline 0.10 mm with a pin-1 chamfer and
${REFERENCE} (KLC F5.2, CRAFT-11); courtyard 0.05 mm on a 0.01 mm grid, clearance by class
(KLC F5.3), grown to cover the pin-1 mark.

--check regenerates into a temporary directory and exits 1 if any committed file differs.
Needs Python 3.11 or later (tomllib).
"""

from __future__ import annotations

import json
import math
import os
import shutil
import sys
import tempfile
import tomllib

import custom_pads
import symlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, "generator", "parts")
ENVELOPES = os.path.join(ROOT, "generator", "envelopes.toml")
FP_VERSION = "20260206"
SYM_VERSION = "20251024"
GENERATOR = "opendap-kigen"
MODEL_PATH = "${OPENDAP_KICAD_3DMODELS}/%s.3dshapes/%s.step"

SILK_W = 0.15          # CRAFT-05
SILK_PAD_CLR = 0.15    # CRAFT-07
SILK_BODY_OFFSET = 0.1  # silk outline outside the fab outline
FAB_W = 0.10           # KLC F5.2
CRT_W = 0.05           # KLC F5.3
CRT_CLASS = {"small": 0.15, "default": 0.25, "connector": 0.5, "bga": 1.0}  # KLC F5.3
TRI_BASE, TRI_H = 0.6, 0.45  # pin-1 triangle
REF_SIZE, REF_W = 1.0, 0.15  # CRAFT-02
G = 2.54               # symbol grid
PIN_LEN = 2.54         # CRAFT-121: the base length; pin_length() adds to it for long pin numbers
PIN_LEN_MAX = 7.62


def pin_length(numbers):
    """One pin length per symbol (CRAFT-121): 2.54 mm, plus 1.27 mm per pin-number character beyond
    the first (a stroke-font character is about 1.1 mm at 1.27 mm), at most 7.62 mm. The number sits
    centred on its pin, so this keeps it about 0.15 mm or more clear of a no-connect flag (a
    1.22 mm cross) on the pin end; at 2.54 mm a two-digit number met the flag (visual review,
    2026-10-26)."""
    longest = max([len(str(s)) for s in numbers] + [1])
    return min(PIN_LEN + 1.27 * (longest - 1), PIN_LEN_MAX)


def grid_pad(length):
    """What a body half-size grows by so that the pin ends, a pin length away, stay on the 2.54 mm
    grid (CRAFT-122) when the length is an odd multiple of 1.27 mm."""
    return round((-length) % G, 6) % G

PIN_TYPES = {"input", "output", "bidirectional", "tri_state", "passive", "free", "unspecified",
             "power_in", "power_out", "open_collector", "open_emitter", "no_connect"}


# ---------------------------------------------------------------- s-expressions

class Sym(str):
    """An unquoted s-expression atom."""


def num(v: float) -> Sym:
    v = round(float(v), 6)
    if v == 0:
        v = 0.0
    s = ("%.6f" % v).rstrip("0").rstrip(".")
    return Sym(s if s not in ("-0", "") else "0")


def q(s: str) -> str:
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def dump(node, depth=0) -> str:
    if not isinstance(node, list):
        if isinstance(node, Sym):
            return str(node)
        if isinstance(node, bool):
            return "yes" if node else "no"
        if isinstance(node, (int, float)):
            return str(num(node))
        return q(node)
    if all(not isinstance(c, list) for c in node):
        return "(" + " ".join(dump(c) for c in node) + ")"
    head = [c for c in node if not isinstance(c, list)]
    out = "(" + " ".join(dump(c) for c in head)
    for c in node:
        if isinstance(c, list):
            out += "\n" + "\t" * (depth + 1) + dump(c, depth + 1)
    return out + "\n" + "\t" * depth + ")"


def S(*items):
    return [Sym(items[0])] + list(items[1:])


# ---------------------------------------------------------------- loading

def load_parts(paths=None):
    if not paths:
        paths = []
        for lib in sorted(os.listdir(PARTS)):
            d = os.path.join(PARTS, lib)
            if os.path.isdir(d):
                paths += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".toml")]
    parts = []
    for p in paths:
        with open(p, "rb") as fh:
            data = tomllib.load(fh)
        data["_path"] = p
        parts.append(data)
    return parts


def expand_pads(fp):
    """Every pad of the footprint in the data frame: dicts with number, at, size, shape, type…"""
    pads = []
    for p in fp.get("pads", []):
        pads.append(dict(p))
    for r in fp.get("rows", []):
        for i in range(r["count"]):
            d = {k: v for k, v in r.items() if k not in ("first", "count", "step", "start", "pitch")}
            d["number"] = str(r["first"] + i * r.get("step", 1))
            d["at"] = [r["start"][0] + i * r["pitch"][0], r["start"][1] + i * r["pitch"][1]]
            pads.append(d)
    for v in fp.get("vias", []):
        for ix in range(v["count"][0]):
            for iy in range(v["count"][1]):
                pads.append({"number": v["number"], "type": "via", "shape": "circle",
                             "at": [v["start"][0] + ix * v["pitch"][0], v["start"][1] + iy * v["pitch"][1]],
                             "size": [v["diameter"], v["diameter"]], "drill": v["drill"]})
    for a in fp.get("paste", []):
        for ix in range(a["count"][0]):
            for iy in range(a["count"][1]):
                pads.append({"number": "", "type": "paste", "shape": a.get("shape", "roundrect"),
                             "rratio": a.get("rratio", 0.25),
                             "at": [a["start"][0] + ix * a["pitch"][0], a["start"][1] + iy * a["pitch"][1]],
                             "size": list(a["size"])})
    pads += custom_pads.ring_pads(fp) + custom_pads.sector_pads(fp) + custom_pads.poly_pads(fp)
    for p in pads:
        p.setdefault("type", "smd")
        p.setdefault("shape", "roundrect" if p["type"] == "smd" else "circle")
        p["number"] = str(p["number"])
    return pads


def anchor(fp, pads):
    """Translation that puts the anchor at (0, 0): body centroid (SMD) or pin 1 (THT only)."""
    if fp.get("attr", "smd") == "through_hole" and not any(p["type"] == "smd" for p in pads):
        p1 = [p for p in pads if p["number"] == "1"][0]
        return -p1["at"][0], -p1["at"][1]
    off = fp.get("body_offset", [0.0, 0.0])
    return -off[0], -off[1]


def frame(part):
    """The footprint in the anchor frame: pads, body rect, extra fab outline, model boxes."""
    fp = part["footprint"]
    pads = expand_pads(fp)
    dx, dy = anchor(fp, pads)
    for p in pads:
        p["at"] = [round(p["at"][0] + dx, 6), round(p["at"][1] + dy, 6)]
    b = fp["body"]
    off = fp.get("body_offset", [0.0, 0.0])
    cx, cy = off[0] + dx, off[1] + dy
    body = (cx - b["x"] / 2, cy - b["y"] / 2, cx + b["x"] / 2, cy + b["y"] / 2)
    outline = [[x + dx, y + dy] for x, y in fp.get("fab_outline", [])]
    boxes = []
    for m in fp.get("model", []):
        boxes.append({"size": m["size"], "at": [m["at"][0] + dx, m["at"][1] + dy, m["at"][2]]})
    if not boxes:
        boxes = [{"size": [b["x"], b["y"], b["z"] - b.get("standoff", 0.0)],
                  "at": [cx, cy, b.get("standoff", 0.0)]}]
    mark = fp.get("pin1_mark")
    if mark:
        mark = {"at": [mark["at"][0] + dx, mark["at"][1] + dy], "direction": mark["direction"]}
    return pads, body, outline, boxes, mark


# ---------------------------------------------------------------- geometry helpers

def pad_box(p, grow=0.0):
    if p.get("extent"):  # a custom pad: its primitives' box, relative to the pad position
        e, (x, y) = p["extent"], p["at"]
        return (x + e[0] - grow, y + e[1] - grow, x + e[2] + grow, y + e[3] + grow)
    w, h = p["size"]
    if p["type"] in ("thru_hole", "np_thru_hole", "via") and p.get("drill"):
        d = p["drill"]
        dw, dh = (d, d) if not isinstance(d, list) else d
        w, h = max(w, dw), max(h, dh)
    x, y = p["at"]
    return (x - w / 2 - grow, y - h / 2 - grow, x + w / 2 + grow, y + h / 2 + grow)


def copper(pads):
    """Pads that keep silk and courtyard away: every pad but paste-only apertures (a mask aperture
    of a solder-mask-defined land counts, as its opening exposes metal)."""
    return [p for p in pads if p["type"] != "paste"]


def union(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def clip_segment(a, b, keepouts):
    """Split the axis-aligned segment a-b by removing the parts inside the keepout boxes."""
    horiz = abs(a[1] - b[1]) < 1e-9
    if horiz:
        lo, hi, c = min(a[0], b[0]), max(a[0], b[0]), a[1]
    else:
        lo, hi, c = min(a[1], b[1]), max(a[1], b[1]), a[0]
    cuts = []
    for k in keepouts:
        if horiz and k[1] < c < k[3]:
            cuts.append((k[0], k[2]))
        elif not horiz and k[0] < c < k[2]:
            cuts.append((k[1], k[3]))
    spans = [(lo, hi)]
    for c0, c1 in cuts:
        nxt = []
        for s0, s1 in spans:
            if c1 <= s0 or c0 >= s1:
                nxt.append((s0, s1))
                continue
            if c0 > s0:
                nxt.append((s0, c0))
            if c1 < s1:
                nxt.append((c1, s1))
        spans = nxt
    out = []
    for s0, s1 in spans:
        if s1 - s0 < 0.2:  # stubs shorter than 0.2 mm read as dirt, drop them
            continue
        out.append(((s0, c), (s1, c)) if horiz else ((c, s0), (c, s1)))
    return out


def grid_out(v, g=0.01, up=True):
    f = math.ceil if up else math.floor
    return round(f(round(v / g, 6)) * g, 2)


def triangle(at, direction):
    x, y = at
    h, b = TRI_H, TRI_BASE / 2
    # the tip is at `at`, the base behind it
    if direction == "right":
        return [[x, y], [x - h, y - b], [x - h, y + b]]
    if direction == "left":
        return [[x, y], [x + h, y - b], [x + h, y + b]]
    if direction == "down":
        return [[x, y], [x - b, y - h], [x + b, y - h]]
    return [[x, y], [x - b, y + h], [x + b, y + h]]  # up


def tri_box(pts):
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def pin1_number(part):
    """Pad that carries the pin-1 mark: [footprint] pin1, else "1", else the first listed pin."""
    fp = part["footprint"]
    if fp.get("pin1"):
        return fp["pin1"]
    nums = [str(p["number"]) for p in part["pins"]]
    return "1" if "1" in nums else nums[0]


def pin1_triangle(pads, body, first="1"):
    p1s = [p for p in copper(pads) if p["number"] == first]
    if not p1s:
        return None
    p1 = p1s[0]
    pb = pad_box(p1)
    gap = SILK_PAD_CLR + 0.05
    keep = [pad_box(p, SILK_PAD_CLR) for p in copper(pads)]
    sb = (body[0] - SILK_BODY_OFFSET - SILK_W, body[1] - SILK_BODY_OFFSET - SILK_W,
          body[2] + SILK_BODY_OFFSET + SILK_W, body[3] + SILK_BODY_OFFSET + SILK_W)
    x, y = p1["at"]
    # outward from pad 1, nearest body side first; the tip outside both the pad and the body
    sides = sorted([("left", x - body[0]), ("right", body[2] - x), ("top", y - body[1]), ("bottom", body[3] - y)],
                   key=lambda t: t[1])
    cands = []
    for side, _ in sides:
        if side == "left":
            cands.append(([min(pb[0] - gap, sb[0] - 0.05), y], "right"))
        elif side == "right":
            cands.append(([max(pb[2] + gap, sb[2] + 0.05), y], "left"))
        elif side == "top":
            cands.append(([x, min(pb[1] - gap, sb[1] - 0.05)], "down"))
        else:
            cands.append(([x, max(pb[3] + gap, sb[3] + 0.05)], "up"))
    cands.append(([sb[0] - 0.05, sb[1] - 0.05], "right"))
    for at, d in cands:
        pts = triangle(at, d)
        tb = tri_box(pts)
        if overlaps(tb, (body[0], body[1], body[2], body[3])):
            continue
        if any(overlaps(tb, k) for k in keep):
            continue
        return pts
    return None


# ---------------------------------------------------------------- footprint

def font(size, thick):
    return S("effects", S("font", S("size", num(size), num(size)), S("thickness", num(thick))))


def line(a, b, layer, w):
    return S("fp_line", S("start", num(a[0]), num(a[1])), S("end", num(b[0]), num(b[1])),
             S("stroke", S("width", num(w)), S("type", Sym("solid"))), S("layer", layer))


def poly(pts, layer, w, fill):
    return S("fp_poly", S("pts", *[S("xy", num(x), num(y)) for x, y in pts]),
             S("stroke", S("width", num(w)), S("type", Sym("solid"))),
             S("fill", Sym("yes" if fill else "no")), S("layer", layer))


def rect(b, layer, w):
    return S("fp_rect", S("start", num(b[0]), num(b[1])), S("end", num(b[2]), num(b[3])),
             S("stroke", S("width", num(w)), S("type", Sym("solid"))), S("fill", Sym("no")),
             S("layer", layer))


def pad_node(p):
    t = p["type"]
    kind = {"smd": "smd", "paste": "smd", "copper": "smd", "aperture": "smd", "thru_hole": "thru_hole",
            "via": "thru_hole", "np_thru_hole": "np_thru_hole"}[t]
    shape = p["shape"]
    node = S("pad", p["number"], Sym(kind), Sym(shape), S("at", num(p["at"][0]), num(p["at"][1])),
             S("size", num(p["size"][0]), num(p["size"][1])))
    if t in ("thru_hole", "np_thru_hole", "via"):
        d = p["drill"]
        if isinstance(d, list):
            node.append(S("drill", Sym("oval"), num(d[0]), num(d[1])))
        else:
            node.append(S("drill", num(d)))
    if t == "via":
        node.append(S("property", Sym("pad_prop_heatsink")))
    if t == "smd":
        layers = ["F.Cu", "F.Mask"] + (["F.Paste"] if p.get("paste", True) else [])
    elif t == "paste":
        layers = ["F.Paste"]
    elif t == "copper":  # the copper of a solder-mask-defined land: covered by the mask
        layers = ["F.Cu"]
    elif t == "aperture":  # its exposed metal: mask opening and paste, no copper
        layers = ["F.Mask", "F.Paste"]
    elif t == "via":
        layers = ["*.Cu"]
    else:
        layers = ["*.Cu", "*.Mask"]
    node.append(S("layers", *layers))
    if t == "via" or t == "thru_hole":
        node.append(S("remove_unused_layers", Sym("no")))
    if shape == "roundrect":
        node.append(S("roundrect_rratio", num(p.get("rratio", 0.25))))
    if p.get("mask_margin"):
        node.append(S("solder_mask_margin", num(p["mask_margin"])))
    elif t == "aperture":  # the opening is the drawn exposed metal: no board-default expansion
        node.append(S("solder_mask_margin", 0))
    if shape == "custom":
        node += custom_pads.primitives(p, S, Sym, num)
    return node


def footprint(part):
    fp = part["footprint"]
    lib = part["part"]["library"]
    pads, body, outline, boxes, mark = frame(part)
    cu = copper(pads)
    crt_clr = CRT_CLASS[fp.get("courtyard_class", "default")]
    allb = union([pad_box(p) for p in cu] + [body])
    crt = (grid_out(allb[0] - crt_clr, up=False), grid_out(allb[1] - crt_clr, up=False),
           grid_out(allb[2] + crt_clr), grid_out(allb[3] + crt_clr))
    tri = pin1_triangle(pads, body, pin1_number(part)) if not mark else triangle(mark["at"], mark["direction"])
    if tri:  # the courtyard covers the pin-1 mark too, so a neighbour's silk never meets it (CRAFT-13)
        tb = tri_box(tri)
        crt = (min(crt[0], grid_out(tb[0], up=False)), min(crt[1], grid_out(tb[1], up=False)),
               max(crt[2], grid_out(tb[2])), max(crt[3], grid_out(tb[3])))

    n = S("footprint", fp["name"], S("version", Sym(FP_VERSION)), S("generator", GENERATOR),
          S("layer", "F.Cu"), S("descr", fp.get("description", "")), S("tags", fp.get("tags", "")))
    prop = lambda k, v, at, layer, hide=False: S(
        "property", k, v, S("at", num(at[0]), num(at[1]), 0), S("layer", layer),
        *([S("hide", Sym("yes"))] if hide else []), font(1.0, 0.15))
    top = min([crt[1]] + ([pt[1] for pt in tri] if tri else []))
    bot = max([crt[3]] + ([pt[1] for pt in tri] if tri else []))
    n.append(prop("Reference", "REF**", (0, round(top - 0.7, 2)), "F.SilkS"))
    n.append(prop("Value", fp["name"], (0, round(bot + 0.7, 2)), "F.Fab"))
    # a land shared by several parts names the document of its drawing (footprint.datasheet), so
    # the footprint file is the same whichever part writes it
    n.append(prop("Datasheet", fp.get("datasheet", part["part"].get("datasheet", "")), (0, 0), "F.Fab", True))
    n.append(prop("Description", fp.get("description", ""), (0, 0), "F.Fab", True))
    n.append(S("attr", Sym(fp.get("attr", "smd"))))
    n.append(S("duplicate_pad_numbers_are_jumpers", Sym("no")))

    # silk: body outline outside the fab outline, clipped clear of every pad (CRAFT-07)
    o = SILK_BODY_OFFSET + SILK_W / 2
    sb = (body[0] - o, body[1] - o, body[2] + o, body[3] + o)
    corners = [(sb[0], sb[1]), (sb[2], sb[1]), (sb[2], sb[3]), (sb[0], sb[3])]
    keep = [pad_box(p, SILK_PAD_CLR + SILK_W / 2) for p in cu]
    for i in range(4):
        for a, b in clip_segment(corners[i], corners[(i + 1) % 4], keep):
            n.append(line(a, b, "F.SilkS", SILK_W))
    if tri:
        n.append(poly(tri, "F.SilkS", 0, True))

    # fab: body with a pin-1 chamfer (KLC F5.2) unless an explicit outline is given
    if outline:
        n.append(poly(outline, "F.Fab", FAB_W, False))
    else:
        c = min(1.0, 0.25 * min(body[2] - body[0], body[3] - body[1]))
        n.append(poly([[body[0] + c, body[1]], [body[2], body[1]], [body[2], body[3]],
                       [body[0], body[3]], [body[0], body[1] + c]], "F.Fab", FAB_W, False))
    n.append(rect(crt, "F.CrtYd", CRT_W))
    fsize = max(0.5, min(1.0, round(0.25 * min(body[2] - body[0], body[3] - body[1]), 2)))
    n.append(S("fp_text", Sym("user"), "${REFERENCE}",
               S("at", num((body[0] + body[2]) / 2), num((body[1] + body[3]) / 2), 0),
               S("layer", "F.Fab"), font(fsize, round(fsize * 0.15, 3))))

    def key(p):
        order = {"paste": 0, "via": 2}.get(p["type"], 1)
        nm = p["number"]
        return (order, (0, int(nm)) if nm.isdigit() else (1, nm), p["at"][0], p["at"][1])
    for p in sorted(pads, key=key):
        n.append(pad_node(p))
    n.append(S("embedded_fonts", Sym("no")))
    n.append(S("model", MODEL_PATH % (lib, fp["name"]), S("offset", S("xyz", 0, 0, 0)),
               S("scale", S("xyz", 1, 1, 1)), S("rotate", S("xyz", 0, 0, 0))))
    model = {"name": fp["name"], "library": lib, "boxes": boxes,
             "source": "envelope from %s" % fp["body"].get("cite", "")}
    return dump(n) + "\n", model


# ---------------------------------------------------------------- symbol

def text_len(s):
    return len(s.replace("~{", "").replace("}", "")) * 1.27 * 0.75


def side_of(p):
    if p.get("side"):
        return p["side"]
    if p["type"] == "power_in":
        return "bottom" if "GND" in p["name"].upper() or p["name"].upper().startswith("VSS") else "top"
    return "right" if p["type"] in ("output", "power_out", "open_collector", "open_emitter", "tri_state") else "left"


def pin_node(p, x, y, ang, length=PIN_LEN):
    return S("pin", Sym(p["type"]), Sym("line"), S("at", num(x), num(y), ang), S("length", num(length)),
             S("name", p["name"], S("effects", S("font", S("size", 1.27, 1.27)))),
             S("number", p["number"], S("effects", S("font", S("size", 1.27, 1.27)))))


def unit_body(pins, length=PIN_LEN):
    """Rectangle half-sizes and pin nodes of one unit: inputs left, outputs right, supplies top,
    grounds bottom, pins on the 2.54 mm grid (KLC S4.1, S4.2)."""
    sides = {"left": [], "right": [], "top": [], "bottom": []}
    for p in pins:
        if p["type"] not in PIN_TYPES:
            raise ValueError("pin %s: bad type %s" % (p["number"], p["type"]))
        sides[side_of(p)].append(p)

    def slots(lst):
        out, k = [], 0
        for p in lst:
            if p.get("gap") and out:
                k += 1
            out.append((k, p))
            k += 1
        return out, k
    sl = {s: slots(v) for s, v in sides.items()}
    rows = max(sl["left"][1], sl["right"][1], 1)
    cols = max(sl["top"][1], sl["bottom"][1], 0)
    lw = max([text_len(p["name"]) for p in sides["left"]] + [0])
    rw = max([text_len(p["name"]) for p in sides["right"]] + [0])
    top_res = max([text_len(p["name"]) for p in sides["top"]] + [-G]) + G
    bot_res = max([text_len(p["name"]) for p in sides["bottom"]] + [-G]) + G
    width = max(lw + rw + 2 * G, (cols + 1) * G, 4 * G)
    width = math.ceil(width / (2 * G)) * 2 * G
    height = top_res + bot_res + (rows + 2) * G
    height = math.ceil(height / (2 * G)) * 2 * G
    hw, hh = width / 2 + grid_pad(length), height / 2 + grid_pad(length)
    pn = []
    # left and right: pins from the top down, below the top pins' names
    spare = height - top_res - bot_res - (rows - 1) * G
    top_y = math.floor((hh - top_res - spare / 2) / G + 1e-9) * G
    for side, x, ang in (("left", -hw - length, 0), ("right", hw + length, 180)):
        for k, p in sl[side][0]:
            y = round(round((top_y - k * G) / 1.27) * 1.27, 4)
            pn.append(pin_node(p, x, y, ang, length))
    for side, y, ang in (("top", hh + length, 270), ("bottom", -hh - length, 90)):
        lst, cnt = sl[side]
        for k, p in lst:
            # centred on x = 0 and on the 2.54 mm grid (CRAFT-122): an odd count has a pin at 0, an
            # even count leaves 0 empty (-2.54, 2.54 for two pins) instead of landing on ±1.27
            slot = k - cnt // 2
            if cnt % 2 == 0 and slot >= 0:
                slot += 1
            pn.append(pin_node(p, slot * G, y, ang, length))
    return hw, hh, bool(sides["top"]), pn


def symbol(part):
    pt = part["part"]
    name = pt.get("symbol", pt["mpn"])
    units = part.get("units") or [{"name": ""}]
    bodies = []
    length = pin_length(p["number"] for p in part["pins"])
    for i, u in enumerate(units, 1):
        pins = [p for p in part["pins"] if p.get("unit", 1) == i]
        if not pins:
            raise ValueError("%s: unit %d has no pins" % (name, i))
        bodies.append((u, unit_body(pins, length)))
    if any(not 1 <= p.get("unit", 1) <= len(units) for p in part["pins"]):
        raise ValueError("%s: pin with an undefined unit" % name)
    hw, hh, top, _ = bodies[0][1]
    bottom = any(side_of(p) == "bottom" for p in part["pins"] if p.get("unit", 1) == 1)
    ty = hh + (length + 1.27 if top else 1.27)
    vy = -hh - (length + 2.54 if bottom else 1.27)
    fpname = "%s:%s" % (pt["library"], part["footprint"]["name"])

    def prop(k, v, at, hide=True, justify=None):
        eff = S("effects", S("font", S("size", 1.27, 1.27)))
        if justify:
            eff.append(S("justify", Sym(justify)))
        return S("property", k, v, S("at", num(at[0]), num(at[1]), 0),
                 *([S("hide", Sym("yes"))] if hide else []), eff)
    n = S("symbol", name, S("pin_names", S("offset", 1.016)), S("exclude_from_sim", Sym("no")),
          S("in_bom", Sym("yes")), S("on_board", Sym("yes")),
          prop("Reference", pt.get("reference", "U"), (-hw, ty), False, "left"),
          prop("Value", name, (-hw, vy), False, "left"),
          prop("Footprint", fpname, (0, 0)),
          prop("Datasheet", pt.get("datasheet", ""), (0, 0)),
          prop("Description", pt.get("description", ""), (0, 0)),
          prop("Manufacturer", pt["manufacturer"], (0, 0)),
          prop("MPN", pt["mpn"], (0, 0)))
    if len(units) > 1:
        n.append(prop("ki_locked", "", (0, 0)))
    n.append(prop("ki_keywords", pt.get("keywords", ""), (0, 0)))
    n.append(prop("ki_fp_filters", part["footprint"]["name"] + "*", (0, 0)))
    for i, (u, (uw, uh, _, pn)) in enumerate(bodies, 1):
        sub = S("symbol", "%s_%d_1" % (name, i))
        if u.get("name"):
            sub.append(S("unit_name", u["name"]))
        sub.append(S("rectangle", S("start", num(-uw), num(uh)), S("end", num(uw), num(-uh)),
                     S("stroke", S("width", 0.254), S("type", Sym("default"))),
                     S("fill", S("type", Sym("background")))))
        sub += pn
        n.append(sub)
    n.append(S("embedded_fonts", Sym("no")))
    return n


def symbol_lib(parts):
    n = S("kicad_symbol_lib", S("version", Sym(SYM_VERSION)), S("generator", GENERATOR),
          S("generator_version", "10.0"))
    for p in sorted(parts, key=lambda p: p["part"].get("symbol", p["part"]["mpn"])):
        n.append(symbol(p))
    return dump(n) + "\n"


# ---------------------------------------------------------------- build

def load_envelopes(path=ENVELOPES):
    """The [[envelope]] entries of envelopes.toml: key, name, land, cite, boxes."""
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    out = data.get("envelope", [])
    seen = set()
    for e in out:
        for k in ("key", "name", "land", "cite", "boxes"):
            if not e.get(k):
                raise ValueError("envelope %s: no %s" % (e.get("name"), k))
        if (e["key"], e["name"]) in seen:
            raise ValueError("envelope %s/%s twice" % (e["key"], e["name"]))
        seen.add((e["key"], e["name"]))
        for b in e["boxes"]:
            if len(b["size"]) != 3 or len(b["at"]) != 3 or min(b["size"]) <= 0:
                raise ValueError("envelope %s: a box needs size [x, y, z] > 0 and at [x, y, z0]" % e["name"])
    return out


def envelope_model(e):
    return {"name": e["name"], "library": e["key"], "source": "envelope from %s" % e["cite"],
            "boxes": [{"size": [float(v) for v in b["size"]], "at": [float(v) for v in b["at"]]} for b in e["boxes"]]}


def build(out, parts, envelopes=None):
    libs = {}
    written = []
    for e in (load_envelopes() if envelopes is None else envelopes):
        path = os.path.join(out, "generator", "models", e["key"], e["name"] + ".json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(envelope_model(e), fh, indent=2, sort_keys=True)
            fh.write("\n")
        written.append(path)
    for p in parts:
        libs.setdefault(p["part"]["library"], []).append(p)
    for lib, lp in sorted(libs.items()):
        path = os.path.join(out, "symbols", lib + ".kicad_sym")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(symlib.merged(lib, GENERATOR, symbol_lib(lp)))
        written.append(path)
        seen = {}
        for p in lp:
            text, model = footprint(p)
            name = p["footprint"]["name"]
            if name in seen:
                if seen[name] != text:
                    raise ValueError("%s: footprint %s differs between parts" % (lib, name))
                continue
            seen[name] = text
            path = os.path.join(out, "footprints", lib + ".pretty", name + ".kicad_mod")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                fh.write(text)
            written.append(path)
            path = os.path.join(out, "generator", "models", lib, name + ".json")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                json.dump(model, fh, indent=2, sort_keys=True)
                fh.write("\n")
            written.append(path)
    return written


def main(argv):
    check = "--check" in argv
    out = ROOT
    args = [a for a in argv if not a.startswith("--")]
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        args = [a for a in args if a != out]
    parts = load_parts(args or None)
    if not check:
        for w in build(out, parts):
            print(os.path.relpath(w, out))
        return 0
    tmp = tempfile.mkdtemp()
    try:
        bad = []
        for w in build(tmp, parts):
            rel = os.path.relpath(w, tmp)
            mine = os.path.join(ROOT, rel)
            if not os.path.exists(mine) or open(mine).read() != open(w).read():
                bad.append(rel)
        for b in bad:
            print("out of date: " + b)
        return 1 if bad else 0
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
