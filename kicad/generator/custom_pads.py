"""Custom-shape pads for kigen.py: annular copper rings, segmented ring paste apertures and
polygon pads.

A bottom-port MEMS microphone lands on a copper ring around its acoustic port, with the paste on
that ring split into sectors (for example Infineon IM73D122V01, datasheet v1.00 Figure 13). KiCad
draws both as custom pads: a small circular anchor plus primitives. This module turns the data
tables below into pad dicts that kigen.py places, clips silk around and writes.

    [[footprint.rings]]            copper ring: number, center, inner and outer radius, anchor
                                   diameter; mask opening as the copper, no paste
    [[footprint.paste_sectors]]    paste-only ring sectors: center, inner and outer radius, count,
                                   gap (width of the parallel-sided gaps), first_gap (degrees,
                                   the centre line of the first gap, from +x towards +y)
    [[footprint.polys]]            polygon pads: number, points (the outline, in order, in the
                                   data frame), anchor (a point inside the outline; the pad's
                                   position), anchor_size (side of the square anchor, default
                                   0.2), layers: "smd" (F.Cu, F.Mask, F.Paste: a non-solder-mask-
                                   defined land), "copper" (F.Cu only: the copper of a solder-mask-
                                   defined land, under the mask) or "aperture" (F.Mask and F.Paste
                                   only, no copper: the exposed metal of a solder-mask-defined land,
                                   numbered as its copper)

A solder-mask-defined land is one "copper" pad plus one "aperture" pad with the same number (for
example TI RXS0016A pads 6, 7 and 8, SLVSGC5E PDF p. 65). Polygon corners are sharp.

Coordinates in millimetres, top view, +y down, in the data frame (kigen.frame() moves them).
"""

from __future__ import annotations

import math

ARC_STEPS = 8  # straight segments per sector arc (0.1 mm chord error stays below 0.002 mm at R1)


def ring_pads(fp):
    """One custom copper pad per [[footprint.rings]] entry. The anchor sits on the ring (at its top),
    never on the centre, so no copper lands in the acoustic port."""
    pads = []
    for r in fp.get("rings", []):
        cx, cy = r["center"]
        ri, ro = r["inner"], r["outer"]
        if not 0 < ri < ro:
            raise ValueError("ring %s: inner radius must be positive and below the outer" % r["number"])
        mid, width = (ri + ro) / 2, ro - ri
        anchor = r.get("anchor", round(width * 0.8, 3))
        if anchor > width:
            raise ValueError("ring %s: anchor %.3f wider than the ring %.3f" % (r["number"], anchor, width))
        pads.append({"number": str(r["number"]), "type": "smd", "shape": "custom",
                     "at": [cx, cy - mid], "size": [anchor, anchor], "paste": False,
                     "custom": [("ring", (0.0, mid), mid, width)],
                     "extent": (-ro, mid - ro, ro, mid + ro)})
    return pads


def sector_points(ri, ro, a0, a1, gap):
    """Outline of the ring sector between the gap centre lines at angles a0 < a1 (radians), each
    gap parallel-sided: every straight edge sits gap/2 from its centre line."""
    h = gap / 2
    out0, out1 = a0 + math.asin(h / ro), a1 - math.asin(h / ro)
    in0, in1 = a0 + math.asin(h / ri), a1 - math.asin(h / ri)
    if in1 <= in0:
        raise ValueError("paste sector: gap %.3f leaves nothing at radius %.3f" % (gap, ri))
    pts = [(ro * math.cos(out0 + (out1 - out0) * k / ARC_STEPS), ro * math.sin(out0 + (out1 - out0) * k / ARC_STEPS))
           for k in range(ARC_STEPS + 1)]
    pts += [(ri * math.cos(in1 - (in1 - in0) * k / ARC_STEPS), ri * math.sin(in1 - (in1 - in0) * k / ARC_STEPS))
            for k in range(ARC_STEPS + 1)]
    return pts


def sector_pads(fp):
    """Paste-only custom pads, one per sector of each [[footprint.paste_sectors]] entry; the
    anchor (a small circle) sits at the sector's mid-radius, mid-angle point."""
    pads = []
    for s in fp.get("paste_sectors", []):
        cx, cy = s["center"]
        ri, ro, n, gap = s["inner"], s["outer"], s["count"], s["gap"]
        first = math.radians(s.get("first_gap", 0.0))
        step = 2 * math.pi / n
        mid = (ri + ro) / 2
        anchor = s.get("anchor", round((ro - ri) / 2, 3))
        for k in range(n):
            a0 = first + k * step
            am = a0 + step / 2
            ax, ay = mid * math.cos(am), mid * math.sin(am)
            pts = [(round(x - ax, 4), round(y - ay, 4)) for x, y in sector_points(ri, ro, a0, a0 + step, gap)]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            pads.append({"number": "", "type": "paste", "shape": "custom",
                         "at": [cx + ax, cy + ay], "size": [anchor, anchor],
                         "custom": [("poly", pts)],
                         "extent": (min(xs), min(ys), max(xs), max(ys))})
    return pads


POLY_LAYERS = ("smd", "copper", "aperture")


def _inside(pt, pts):
    """Point strictly inside the polygon pts (even-odd rule); points on an edge count as outside."""
    x, y = pt
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        cross = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
        if abs(cross) < 1e-9 and min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9 \
                and min(y1, y2) - 1e-9 <= y <= max(y1, y2) + 1e-9:
            return False
    hit = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def _crosses(a, b, c, d):
    """Segments a-b and c-d cross at a point inside both (touching at an end does not count)."""
    def ccw(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return ccw(a, b, c) * ccw(a, b, d) < -1e-12 and ccw(c, d, a) * ccw(c, d, b) < -1e-12


def poly_pads(fp):
    """One custom pad per [[footprint.polys]] entry. The outline must be a simple polygon with an
    area, and the square anchor must lie inside it (KiCad adds the anchor to the pad shape)."""
    pads = []
    for e in fp.get("polys", []):
        num = str(e["number"])
        pts = [tuple(float(v) for v in p) for p in e["points"]]
        if e.get("layers") not in POLY_LAYERS:
            raise ValueError("poly %s: layers must be one of %s" % (num, ", ".join(POLY_LAYERS)))
        if len(pts) < 3:
            raise ValueError("poly %s: fewer than 3 points" % num)
        area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / 2
        if abs(area) < 1e-6:
            raise ValueError("poly %s: no area" % num)
        edges = list(zip(pts, pts[1:] + pts[:1]))
        for i in range(len(edges)):
            for j in range(i + 2, len(edges)):
                if i == 0 and j == len(edges) - 1:
                    continue
                if _crosses(*edges[i], *edges[j]):
                    raise ValueError("poly %s: the outline crosses itself" % num)
        ax, ay = e["anchor"]
        h = e.get("anchor_size", 0.2) / 2
        square = [(ax - h, ay - h), (ax + h, ay - h), (ax + h, ay + h), (ax - h, ay + h)]
        if not all(_inside(c, pts) for c in square + [(ax, ay)]) or \
                any(ax - h < x < ax + h and ay - h < y < ay + h for x, y in pts):
            raise ValueError("poly %s: the anchor (%.3f, %.3f) +-%.3f is not inside the outline" % (num, ax, ay, h))
        rel = [(round(x - ax, 4), round(y - ay, 4)) for x, y in pts]
        xs, ys = [p[0] for p in rel], [p[1] for p in rel]
        pads.append({"number": num, "type": {"smd": "smd", "copper": "copper", "aperture": "aperture"}[e["layers"]],
                     "shape": "custom", "at": [ax, ay], "size": [2 * h, 2 * h],
                     "custom": [("poly", rel)], "extent": (min(xs), min(ys), max(xs), max(ys))})
    return pads


def primitives(p, S, Sym, num):
    """The (options …) and (primitives …) nodes of a custom pad."""
    prims = []
    for prim in p["custom"]:
        if prim[0] == "ring":
            _, (x, y), r, w = prim
            prims.append(S("gr_circle", S("center", num(x), num(y)), S("end", num(x + r), num(y)),
                           S("width", num(w)), S("fill", Sym("no"))))
        else:
            prims.append(S("gr_poly", S("pts", *[S("xy", num(x), num(y)) for x, y in prim[1]]),
                           S("width", 0), S("fill", Sym("yes"))))
    return [S("options", S("clearance", Sym("outline")), S("anchor", Sym("circle"))),
            S("primitives", *prims)]
